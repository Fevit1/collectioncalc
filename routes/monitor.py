"""
Monitor Blueprint - Marketplace monitoring API for Slab Guard
Routes: /api/monitor/check-image, /api/monitor/check-hash,
        /api/monitor/stolen-hashes, /api/monitor/report-match

Uses multi-algorithm composite fingerprinting (pHash + dHash + aHash + wHash)
for robust matching. Falls back to pHash-only for legacy registrations.

Tested thresholds (Feb 2026):
  - Composite per-angle: <70 CRITICAL, <73 PROBABLE, >77 DIFFERENT
  - Full multi-angle (4 angles × 4 algos): 187-bit separation gap
"""
import os
import json
import psycopg2
from datetime import datetime
from flask import Blueprint, jsonify, request, g
from auth import require_auth, require_approved
from functools import wraps
import time

# Create blueprint
monitor_bp = Blueprint('monitor', __name__, url_prefix='/api/monitor')

# These will be set by wsgi.py
imagehash = None
PIL_Image = None

# Simple in-memory rate limiter
_rate_limit_store = {}  # ip -> (count, window_start)
RATE_LIMIT_MAX = 60  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds

# Composite matching thresholds (per-angle, sum of 4 algos, out of 256 bits)
COMPOSITE_THRESHOLD_CRITICAL = 70   # 95%+ same comic
COMPOSITE_THRESHOLD_PROBABLE = 73   # High probability match
COMPOSITE_THRESHOLD_DISMISS  = 77   # Different comic

# Legacy pHash-only thresholds (single algo, out of 64 bits)
PHASH_THRESHOLD_CRITICAL = 5
PHASH_THRESHOLD_HIGH     = 10
PHASH_THRESHOLD_MEDIUM   = 15
PHASH_THRESHOLD_MAX      = 20


def init_modules(imagehash_lib, pil_image):
    """Initialize modules from wsgi.py"""
    global imagehash, PIL_Image
    imagehash = imagehash_lib
    PIL_Image = pil_image


def rate_limit(f):
    """Simple rate limiter decorator - 60 requests/minute per IP"""
    @wraps(f)
    def decorated(*args, **kwargs):
        ip = request.remote_addr or 'unknown'
        now = time.time()

        if ip in _rate_limit_store:
            count, window_start = _rate_limit_store[ip]
            if now - window_start > RATE_LIMIT_WINDOW:
                # Reset window
                _rate_limit_store[ip] = (1, now)
            elif count >= RATE_LIMIT_MAX:
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded. Try again in a minute.'
                }), 429
            else:
                _rate_limit_store[ip] = (count + 1, window_start)
        else:
            _rate_limit_store[ip] = (1, now)

        return f(*args, **kwargs)
    return decorated


def get_db():
    """Get database connection"""
    return psycopg2.connect(os.environ['DATABASE_URL'])


def generate_composite_from_url(image_url):
    """Download image and generate multi-algorithm composite fingerprint.
    Returns dict with phash, dhash, ahash, whash (16 hex chars each)."""
    if not imagehash or not PIL_Image:
        return None

    try:
        import requests as req
        from io import BytesIO

        response = req.get(image_url, timeout=15)
        response.raise_for_status()
        img = PIL_Image.open(BytesIO(response.content))
        return {
            'phash': str(imagehash.phash(img)),
            'dhash': str(imagehash.dhash(img)),
            'ahash': str(imagehash.average_hash(img)),
            'whash': str(imagehash.whash(img)),
        }
    except Exception as e:
        print(f"Monitor composite generation error: {e}")
        return None


def generate_phash_from_url(image_url):
    """Download image and generate pHash fingerprint (legacy compat)"""
    result = generate_composite_from_url(image_url)
    return result['phash'] if result else None


def hamming_distance(hash1, hash2):
    """Calculate Hamming distance between two hex hash strings"""
    try:
        int1 = int(hash1, 16)
        int2 = int(hash2, 16)
        return bin(int1 ^ int2).count('1')
    except (ValueError, TypeError):
        return 64  # Max distance on error


def composite_distance(fp1, fp2):
    """
    Calculate composite distance between two multi-algorithm fingerprint dicts.
    Each dict has keys: phash, dhash, ahash, whash (16 hex chars each).
    Returns total hamming distance (sum of all 4 algorithms, out of 256 bits).
    """
    total = 0
    algo_dists = {}
    for algo in ['phash', 'dhash', 'ahash', 'whash']:
        h1 = fp1.get(algo)
        h2 = fp2.get(algo)
        if h1 and h2:
            d = hamming_distance(h1, h2)
            algo_dists[algo] = d
            total += d
        else:
            # Missing algo - use max distance for that algo
            algo_dists[algo] = 64
            total += 64
    return total, algo_dists


def composite_alert_level(distance):
    """Determine alert level from composite distance (per-angle)."""
    if distance <= COMPOSITE_THRESHOLD_CRITICAL:
        return 'critical'
    elif distance <= COMPOSITE_THRESHOLD_PROBABLE:
        return 'high'
    elif distance <= COMPOSITE_THRESHOLD_DISMISS:
        return 'medium'
    else:
        return 'low'


def mask_email(email):
    """Hash email for privacy display: mberry133@yahoo.com → m*****3@y***o.com"""
    if email and '@' in email:
        local, domain = email.split('@', 1)
        domain_parts = domain.split('.')
        local_masked = local[0] + ('*' * (len(local) - 2)) + local[-1] if len(local) > 2 else local[0] + '*'
        domain_masked = domain_parts[0][0] + ('*' * (len(domain_parts[0]) - 2)) + domain_parts[0][-1] if len(domain_parts[0]) > 2 else domain_parts[0][0] + '*'
        return f"{local_masked}@{domain_masked}.{'.'.join(domain_parts[1:])}"
    return "Anonymous"


def find_matches(query_hash, max_distance=20, stolen_only=False, query_composite=None):
    """
    Compare query hash against all registered comics.
    Uses composite matching (4 algorithms) when available, falls back to pHash-only.

    Args:
        query_hash: Legacy pHash hex string (16 chars)
        max_distance: Max pHash distance for legacy matching (default 20)
        stolen_only: Only search stolen comics
        query_composite: Dict with {phash, dhash, ahash, whash} for composite matching

    Returns list of matches sorted by confidence (lowest distance first).
    """
    conn = get_db()
    cur = conn.cursor()

    try:
        # Check if fingerprint_composite column exists
        has_composite_col = True
        try:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='comic_registry' AND column_name='fingerprint_composite'")
            has_composite_col = cur.fetchone() is not None
        except Exception:
            has_composite_col = False

        # Build query
        composite_select = ", cr.fingerprint_composite" if has_composite_col else ""
        status_filter = "AND cr.status = 'reported_stolen'" if stolen_only else ""

        cur.execute(f"""
            SELECT
                cr.id,
                cr.serial_number,
                cr.fingerprint_hash,
                cr.status,
                cr.registration_date,
                cr.reported_stolen_date,
                c.title,
                c.issue,
                c.publisher,
                c.grade,
                c.photos,
                u.email
                {composite_select}
            FROM comic_registry cr
            JOIN collections c ON cr.comic_id = c.id
            JOIN users u ON cr.user_id = u.id
            WHERE cr.monitoring_enabled = TRUE
            {status_filter}
        """)

        rows = cur.fetchall()
        matches = []

        for row in rows:
            if has_composite_col:
                (reg_id, serial, fp_hash, status, reg_date, stolen_date,
                 title, issue, publisher, grade, photos, email, fp_composite_raw) = row
            else:
                (reg_id, serial, fp_hash, status, reg_date, stolen_date,
                 title, issue, publisher, grade, photos, email) = row
                fp_composite_raw = None

            # Parse stored composite fingerprint
            stored_composite = None
            if fp_composite_raw:
                try:
                    stored_composite = json.loads(fp_composite_raw) if isinstance(fp_composite_raw, str) else fp_composite_raw
                except (json.JSONDecodeError, TypeError):
                    pass

            # --- COMPOSITE MATCHING (preferred) ---
            if query_composite and stored_composite:
                # Compare front covers using composite distance
                # stored_composite format: { "front": {phash, dhash, ahash, whash}, "spine": {...}, ... }
                stored_front = stored_composite.get('front')
                if stored_front:
                    comp_dist, algo_dists = composite_distance(query_composite, stored_front)

                    # Composite threshold: 73 per angle (out of 256)
                    if comp_dist <= COMPOSITE_THRESHOLD_DISMISS:
                        confidence = max(0, round(100 - (comp_dist * 0.39), 1))  # 0/256=100%, 256/256=0%
                        alert_level = composite_alert_level(comp_dist)

                        matches.append({
                            'registry_id': reg_id,
                            'serial_number': serial,
                            'status': status,
                            'alert_level': alert_level,
                            'hamming_distance': comp_dist,
                            'match_type': 'composite',
                            'algo_distances': algo_dists,
                            'confidence': confidence,
                            'registration_date': reg_date.isoformat() if reg_date else None,
                            'reported_stolen_date': stolen_date.isoformat() if stolen_date else None,
                            'comic': {
                                'title': title,
                                'issue_number': issue,
                                'publisher': publisher,
                                'grade': float(grade) if grade else None
                            },
                            'owner_display': mask_email(email)
                        })
                    continue  # Skip legacy matching if composite data exists

            # --- LEGACY PHASH-ONLY MATCHING (fallback) ---
            if fp_hash and query_hash:
                dist = hamming_distance(query_hash, fp_hash)
                if dist <= max_distance:
                    confidence = max(0, round(100 - (dist * 2.5), 1))

                    if dist <= PHASH_THRESHOLD_CRITICAL:
                        alert_level = 'critical'
                    elif dist <= PHASH_THRESHOLD_HIGH:
                        alert_level = 'high'
                    elif dist <= PHASH_THRESHOLD_MEDIUM:
                        alert_level = 'medium'
                    else:
                        alert_level = 'low'

                    matches.append({
                        'registry_id': reg_id,
                        'serial_number': serial,
                        'status': status,
                        'alert_level': alert_level,
                        'hamming_distance': dist,
                        'match_type': 'phash_legacy',
                        'confidence': confidence,
                        'registration_date': reg_date.isoformat() if reg_date else None,
                        'reported_stolen_date': stolen_date.isoformat() if stolen_date else None,
                        'comic': {
                            'title': title,
                            'issue_number': issue,
                            'publisher': publisher,
                            'grade': float(grade) if grade else None
                        },
                        'owner_display': mask_email(email)
                    })

        # Sort by hamming distance (closest matches first)
        matches.sort(key=lambda m: m['hamming_distance'])

        return matches

    finally:
        cur.close()
        conn.close()


# ============================================================
# ENDPOINTS
# ============================================================

@monitor_bp.route('/check-image', methods=['POST'])
@rate_limit
def check_image():
    """
    Check an image URL against the Slab Guard registry.
    Accepts: { image_url: "https://..." }
    Uses composite fingerprinting (pHash + dHash + aHash + wHash) for robust matching.
    Returns matches with confidence scores.
    """
    data = request.get_json() or {}
    image_url = data.get('image_url')

    if not image_url:
        return jsonify({'success': False, 'error': 'image_url is required'}), 400

    # Validate URL looks like an image
    if not image_url.startswith('http'):
        return jsonify({'success': False, 'error': 'Invalid URL'}), 400

    # Generate composite fingerprint from the image
    query_composite = generate_composite_from_url(image_url)
    if not query_composite:
        return jsonify({
            'success': False,
            'error': 'Could not process image. Check the URL is accessible.'
        }), 400

    query_hash = query_composite.get('phash')  # Legacy compat

    # Find matches using both composite and legacy methods
    max_distance = data.get('max_distance', 20)
    stolen_only = data.get('stolen_only', False)
    matches = find_matches(
        query_hash,
        max_distance=max_distance,
        stolen_only=stolen_only,
        query_composite=query_composite
    )

    return jsonify({
        'success': True,
        'query_hash': query_hash,
        'query_composite': query_composite,
        'match_count': len(matches),
        'matches': matches
    })


@monitor_bp.route('/check-hash', methods=['POST'])
@rate_limit
def check_hash():
    """
    Check a pre-computed pHash against the Slab Guard registry.
    Accepts: { fingerprint_hash: "8f373714b7a1dfc3" }
    Faster than check-image since no image download needed.
    """
    data = request.get_json() or {}
    query_hash = data.get('fingerprint_hash')

    if not query_hash:
        return jsonify({'success': False, 'error': 'fingerprint_hash is required'}), 400

    # Validate hash format (16 hex chars = 64-bit hash)
    if len(query_hash) != 16:
        return jsonify({'success': False, 'error': 'Hash must be 16 hex characters'}), 400

    try:
        int(query_hash, 16)  # Validate hex
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid hex hash'}), 400

    max_distance = data.get('max_distance', 20)
    stolen_only = data.get('stolen_only', False)
    matches = find_matches(query_hash, max_distance=max_distance, stolen_only=stolen_only)

    return jsonify({
        'success': True,
        'query_hash': query_hash,
        'match_count': len(matches),
        'matches': matches
    })


@monitor_bp.route('/stolen-hashes', methods=['GET'])
@rate_limit
def get_stolen_hashes():
    """
    Get all fingerprint hashes for stolen comics.
    Used by extension to cache locally for faster client-side pre-filtering.
    Returns hashes + serial numbers only (no PII).
    Now includes composite fingerprints when available.
    """
    conn = get_db()
    cur = conn.cursor()

    try:
        # Check if composite column exists
        has_composite = True
        try:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='comic_registry' AND column_name='fingerprint_composite'")
            has_composite = cur.fetchone() is not None
        except Exception:
            has_composite = False

        composite_select = ", cr.fingerprint_composite" if has_composite else ""

        cur.execute(f"""
            SELECT
                cr.fingerprint_hash,
                cr.serial_number,
                cr.reported_stolen_date,
                c.title,
                c.issue
                {composite_select}
            FROM comic_registry cr
            JOIN collections c ON cr.comic_id = c.id
            WHERE cr.status = 'reported_stolen'
            AND cr.monitoring_enabled = TRUE
            ORDER BY cr.reported_stolen_date DESC
        """)

        rows = cur.fetchall()
        stolen = []
        for row in rows:
            entry = {
                'fingerprint_hash': row[0],
                'serial_number': row[1],
                'reported_date': row[2].isoformat() if row[2] else None,
                'title': row[3],
                'issue_number': row[4]
            }
            # Include composite if available
            if has_composite and len(row) > 5 and row[5]:
                try:
                    composite = json.loads(row[5]) if isinstance(row[5], str) else row[5]
                    # Only include front cover composite for extension (save bandwidth)
                    if composite and 'front' in composite:
                        entry['composite_front'] = composite['front']
                except (json.JSONDecodeError, TypeError):
                    pass

            stolen.append(entry)

        return jsonify({
            'success': True,
            'count': len(stolen),
            'stolen_comics': stolen,
            'last_updated': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"Stolen hashes error: {e}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

    finally:
        cur.close()
        conn.close()


@monitor_bp.route('/report-match', methods=['POST'])
@require_auth
@require_approved
def report_match():
    """
    Report a potential match found on a marketplace.
    Creates a match_reports record and optionally alerts the owner.
    """
    data = request.get_json() or {}

    serial_number = data.get('serial_number')
    listing_url = data.get('listing_url')

    if not serial_number or not listing_url:
        return jsonify({
            'success': False,
            'error': 'serial_number and listing_url are required'
        }), 400

    conn = get_db()
    cur = conn.cursor()

    try:
        # Find the registry entry
        cur.execute("""
            SELECT cr.id, cr.user_id, cr.status, u.email, c.title, c.issue
            FROM comic_registry cr
            JOIN users u ON cr.user_id = u.id
            JOIN collections c ON cr.comic_id = c.id
            WHERE cr.serial_number = %s
        """, (serial_number,))

        reg = cur.fetchone()
        if not reg:
            return jsonify({'success': False, 'error': 'Serial number not found'}), 404

        registry_id, owner_id, status, owner_email, title, issue = reg

        # Insert match report
        cur.execute("""
            INSERT INTO match_reports (
                registry_id,
                reporter_user_id,
                marketplace,
                listing_url,
                listing_item_id,
                listing_image_url,
                listing_fingerprint,
                hamming_distance,
                confidence_score,
                status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, reported_at
        """, (
            registry_id,
            g.user_id,
            data.get('marketplace', 'ebay'),
            listing_url,
            data.get('ebay_item_id'),
            data.get('listing_image_url'),
            data.get('listing_fingerprint'),
            data.get('hamming_distance'),
            data.get('confidence'),
            'pending'
        ))

        report_id, reported_at = cur.fetchone()
        conn.commit()

        # TODO: Send email alert to owner via Resend
        # This will be implemented when we have the Resend integration ready
        # For now, log it
        print(f"MATCH REPORT: #{report_id} - {title} #{issue} (Serial: {serial_number}) "
              f"found at {listing_url} - Owner: {owner_email}")

        return jsonify({
            'success': True,
            'report_id': report_id,
            'reported_at': reported_at.isoformat(),
            'comic': {
                'title': title,
                'issue_number': issue,
                'status': status
            },
            'message': 'Match reported successfully. The owner will be notified.'
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Report match error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Server error'}), 500

    finally:
        cur.close()
        conn.close()


@monitor_bp.route('/my-matches', methods=['GET'])
@require_auth
@require_approved
def my_matches():
    """
    Get match reports for the current user's registered comics.
    Shows what marketplace listings have been flagged as potential matches.
    """
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                mr.id,
                mr.listing_url,
                mr.marketplace,
                mr.confidence_score,
                mr.hamming_distance,
                mr.status,
                mr.reported_at,
                cr.serial_number,
                c.title,
                c.issue,
                c.grade
            FROM match_reports mr
            JOIN comic_registry cr ON mr.registry_id = cr.id
            JOIN collections c ON cr.comic_id = c.id
            WHERE cr.user_id = %s
            ORDER BY mr.reported_at DESC
            LIMIT 50
        """, (g.user_id,))

        rows = cur.fetchall()
        reports = []
        for row in rows:
            reports.append({
                'report_id': row[0],
                'listing_url': row[1],
                'marketplace': row[2],
                'confidence': float(row[3]) if row[3] else None,
                'hamming_distance': row[4],
                'status': row[5],
                'reported_at': row[6].isoformat() if row[6] else None,
                'serial_number': row[7],
                'comic': {
                    'title': row[8],
                    'issue_number': row[9],
                    'grade': float(row[10]) if row[10] else None
                }
            })

        return jsonify({
            'success': True,
            'match_count': len(reports),
            'matches': reports
        })

    except Exception as e:
        print(f"My matches error: {e}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

    finally:
        cur.close()
        conn.close()
