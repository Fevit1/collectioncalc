"""
SlabGuard Routes — Scam Detection Intake + Admin Review Queue
=============================================================
Blueprint: slabguard_bp
Public:    POST /api/slabguard/submit      — extension submits a suspected scam listing
           POST /api/slabguard/check       — extension checks a listing against approved DB
Admin:     GET  /api/admin/slabguard/queue — review queue (pending submissions)
           GET  /api/admin/slabguard/stats — queue stats for admin dashboard
           POST /api/admin/slabguard/<id>/approve — approve + hash image → flagged DB
           POST /api/admin/slabguard/<id>/reject  — reject submission

Rate limits (anti-bot):
  - Must be authenticated (Bearer JWT)
  - Account must be ≥ 7 days old
  - Max 5 submissions per user per calendar day
  - Duplicate eBay item IDs silently discarded
"""

import os
import hashlib
import requests as http_requests
from datetime import date, datetime, timezone
from io import BytesIO

from flask import Blueprint, jsonify, request, g
import psycopg2
from psycopg2.extras import RealDictCursor

from auth import require_auth, require_admin_auth

# ── pHash implementation (pure Python, no OpenCV dep) ──────────────────────
# Using PIL + DCT-based perceptual hash (same algorithm as imagehash.phash)
try:
    from PIL import Image
    import numpy as np
    PHASH_AVAILABLE = True
except ImportError:
    PHASH_AVAILABLE = False
    print("⚠️ PIL/numpy not available — pHash disabled (install Pillow + numpy)")


def _compute_phash(image_bytes: bytes, hash_size: int = 8) -> str | None:
    """
    Compute DCT-based perceptual hash of image bytes.
    Returns 64-char hex string (8x8 = 64 bits → 16 hex chars, zero-padded to 64).
    Two images with hamming distance ≤ 10 are considered a match.
    """
    if not PHASH_AVAILABLE:
        return None
    try:
        img = Image.open(BytesIO(image_bytes)).convert('L')  # grayscale
        img = img.resize((hash_size * 4, hash_size * 4), Image.LANCZOS)
        pixels = np.array(img, dtype=float)

        # DCT (discrete cosine transform)
        from scipy.fft import dct
        dct_result = dct(dct(pixels, axis=0), axis=1)
        dct_low = dct_result[:hash_size, :hash_size]

        median = np.median(dct_low)
        bits = (dct_low > median).flatten()
        # Convert bits to hex
        val = int(''.join('1' if b else '0' for b in bits), 2)
        return format(val, '016x').zfill(64)
    except Exception as e:
        print(f"[SlabGuard] pHash error: {e}")
        return None


def _hamming_distance(h1: str, h2: str) -> int:
    """Hamming distance between two hex-encoded hashes."""
    try:
        b1 = bin(int(h1, 16))[2:].zfill(64)
        b2 = bin(int(h2, 16))[2:].zfill(64)
        return sum(c1 != c2 for c1, c2 in zip(b1, b2))
    except Exception:
        return 999


def _get_db():
    database_url = os.environ.get('DATABASE_URL')
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


DAILY_LIMIT = 5          # max submissions per user per day
ACCOUNT_MIN_DAYS = 7     # account must be this many days old
PHASH_MATCH_THRESHOLD = 10  # hamming distance ≤ 10 = match


slabguard_bp = Blueprint('slabguard', __name__, url_prefix='/api/slabguard')
admin_slabguard_bp = Blueprint('admin_slabguard', __name__, url_prefix='/api/admin/slabguard')


# ═══════════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS (authenticated users)
# ═══════════════════════════════════════════════════════════════════

@slabguard_bp.route('/submit', methods=['POST'])
@require_auth
def submit_suspected_scam():
    """
    Extension submits a suspected scam listing for human review.

    Body:
      ebay_item_id  str   eBay item number  (required)
      ebay_url      str   Full listing URL  (required)
      risk_score    int   0-100 computed by extension
      signals       dict  {"zero_feedback": true, "single_photo": true, ...}

    Protections:
      - Auth required (no anonymous)
      - Account ≥ 7 days old
      - Max 5 submissions/day
      - Duplicate item IDs silently discarded
    """
    data = request.get_json() or {}
    ebay_item_id = str(data.get('ebay_item_id', '')).strip()
    ebay_url = str(data.get('ebay_url', '')).strip()

    if not ebay_item_id or not ebay_url:
        return jsonify({'success': False, 'error': 'ebay_item_id and ebay_url required'}), 400

    conn = None
    try:
        conn = _get_db()
        cur = conn.cursor()

        # ── 1. Account age gate ──
        cur.execute("SELECT created_at FROM users WHERE id = %s", (g.user_id,))
        user = cur.fetchone()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        account_age_days = (datetime.now(timezone.utc) - user['created_at'].replace(tzinfo=timezone.utc)).days
        if account_age_days < ACCOUNT_MIN_DAYS:
            return jsonify({
                'success': False,
                'error': f'Account must be at least {ACCOUNT_MIN_DAYS} days old to submit reports'
            }), 403

        # ── 2. Dedup: already pending or approved for this item? ──
        cur.execute("""
            SELECT id, status FROM slabguard_submissions
            WHERE ebay_item_id = %s AND status IN ('pending', 'approved')
            LIMIT 1
        """, (ebay_item_id,))
        existing = cur.fetchone()
        if existing:
            # Silent discard — don't tell the user if it's already approved (anti-enumeration)
            return jsonify({'success': True, 'queued': False, 'note': 'Already in review'})

        # ── 3. Daily rate limit ──
        today = date.today()
        cur.execute("""
            INSERT INTO slabguard_rate_limits (user_id, submission_date, count)
            VALUES (%s, %s, 1)
            ON CONFLICT (user_id, submission_date)
            DO UPDATE SET count = slabguard_rate_limits.count + 1
            RETURNING count
        """, (g.user_id, today))
        daily_count = cur.fetchone()['count']

        if daily_count > DAILY_LIMIT:
            # Roll back the increment
            cur.execute("""
                UPDATE slabguard_rate_limits SET count = count - 1
                WHERE user_id = %s AND submission_date = %s
            """, (g.user_id, today))
            conn.commit()
            return jsonify({
                'success': False,
                'error': f'Daily submission limit of {DAILY_LIMIT} reached. Thank you for helping the community!'
            }), 429

        # ── 4. Insert into queue ──
        cur.execute("""
            INSERT INTO slabguard_submissions
                (submitted_by, ebay_item_id, ebay_url, risk_score, signals)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            g.user_id,
            ebay_item_id,
            ebay_url,
            data.get('risk_score', 0),
            psycopg2.extras.Json(data.get('signals', {}))
        ))
        new_id = cur.fetchone()['id']
        conn.commit()

        print(f"[SlabGuard] Queued submission #{new_id} — item {ebay_item_id} by user {g.user_id}")
        return jsonify({'success': True, 'queued': True, 'submission_id': new_id})

    except Exception as e:
        if conn:
            conn.rollback()
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@slabguard_bp.route('/check', methods=['POST'])
@require_auth
def check_listing():
    """
    Extension checks a listing against the approved scam image DB.

    Body:
      ebay_item_id  str   Check for exact item match first (fast path)
      image_url     str   (optional) URL of listing image to pHash-check

    Returns:
      matched       bool
      match_type    "item_id" | "phash" | null
      risk_boost    int   additional risk points to add to extension score
    """
    data = request.get_json() or {}
    ebay_item_id = str(data.get('ebay_item_id', '')).strip()
    image_url = str(data.get('image_url', '')).strip()

    conn = None
    try:
        conn = _get_db()
        cur = conn.cursor()

        # ── Fast path: item ID already approved ──
        if ebay_item_id:
            cur.execute("""
                SELECT id FROM slabguard_submissions
                WHERE ebay_item_id = %s AND status = 'approved'
                LIMIT 1
            """, (ebay_item_id,))
            if cur.fetchone():
                return jsonify({'success': True, 'matched': True, 'match_type': 'item_id', 'risk_boost': 40})

        # ── pHash check against approved flagged images ──
        if image_url and PHASH_AVAILABLE:
            try:
                resp = http_requests.get(image_url, timeout=8)
                if resp.status_code == 200:
                    incoming_hash = _compute_phash(resp.content)
                    if incoming_hash:
                        cur.execute("SELECT phash FROM slabguard_flagged_images")
                        for row in cur.fetchall():
                            if _hamming_distance(incoming_hash, row['phash']) <= PHASH_MATCH_THRESHOLD:
                                return jsonify({
                                    'success': True,
                                    'matched': True,
                                    'match_type': 'phash',
                                    'risk_boost': 40
                                })
            except Exception as e:
                print(f"[SlabGuard] pHash check error: {e}")
                # Non-fatal — continue

        return jsonify({'success': True, 'matched': False, 'match_type': None, 'risk_boost': 0})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@admin_slabguard_bp.route('/queue', methods=['GET'])
@require_admin_auth
def get_queue():
    """Get pending submissions for admin review."""
    status_filter = request.args.get('status', 'pending')
    limit = min(request.args.get('limit', 50, type=int), 200)

    conn = None
    try:
        conn = _get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                s.id,
                s.ebay_item_id,
                s.ebay_url,
                s.risk_score,
                s.signals,
                s.status,
                s.review_note,
                s.reviewed_at,
                s.created_at,
                u.email AS submitter_email,
                u.created_at AS submitter_account_age,
                reviewer.email AS reviewer_email,
                COUNT(*) OVER (PARTITION BY s.ebay_item_id) AS duplicate_count
            FROM slabguard_submissions s
            JOIN users u ON s.submitted_by = u.id
            LEFT JOIN users reviewer ON s.reviewed_by = reviewer.id
            WHERE s.status = %s
            ORDER BY s.created_at DESC
            LIMIT %s
        """, (status_filter, limit))

        rows = cur.fetchall()
        submissions = []
        for r in rows:
            submissions.append({
                'id': r['id'],
                'ebay_item_id': r['ebay_item_id'],
                'ebay_url': r['ebay_url'],
                'risk_score': r['risk_score'],
                'signals': r['signals'],
                'status': r['status'],
                'review_note': r['review_note'],
                'reviewed_at': r['reviewed_at'].isoformat() if r['reviewed_at'] else None,
                'created_at': r['created_at'].isoformat() if r['created_at'] else None,
                'submitter_email': r['submitter_email'],
                'submitter_account_age_days': (
                    (datetime.now(timezone.utc) - r['submitter_account_age'].replace(tzinfo=timezone.utc)).days
                    if r['submitter_account_age'] else None
                ),
                'reviewer_email': r['reviewer_email'],
                'duplicate_count': r['duplicate_count'],
            })

        return jsonify({'success': True, 'submissions': submissions, 'count': len(submissions)})

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@admin_slabguard_bp.route('/stats', methods=['GET'])
@require_admin_auth
def get_stats():
    """Queue stats for admin dashboard tile."""
    conn = None
    try:
        conn = _get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'pending')  AS pending,
                COUNT(*) FILTER (WHERE status = 'approved') AS approved,
                COUNT(*) FILTER (WHERE status = 'rejected') AS rejected,
                COUNT(*)                                     AS total
            FROM slabguard_submissions
        """)
        counts = dict(cur.fetchone())

        cur.execute("SELECT COUNT(*) AS flagged FROM slabguard_flagged_images")
        counts['flagged_images'] = cur.fetchone()['flagged']

        return jsonify({'success': True, **counts})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@admin_slabguard_bp.route('/<int:submission_id>/approve', methods=['POST'])
@require_admin_auth
def approve_submission(submission_id):
    """
    Admin approves a submission:
    1. Fetch the listing image from eBay URL
    2. Compute pHash server-side
    3. Insert into slabguard_flagged_images
    4. Mark submission approved
    """
    data = request.get_json() or {}
    note = data.get('note', '')

    conn = None
    try:
        conn = _get_db()
        cur = conn.cursor()

        # Get submission
        cur.execute("""
            SELECT id, ebay_item_id, ebay_url, status
            FROM slabguard_submissions WHERE id = %s
        """, (submission_id,))
        sub = cur.fetchone()
        if not sub:
            return jsonify({'success': False, 'error': 'Submission not found'}), 404
        if sub['status'] != 'pending':
            return jsonify({'success': False, 'error': f'Submission is already {sub["status"]}'}), 400

        # ── Fetch image from eBay and compute pHash ──
        phash_value = None
        image_fetch_error = None
        try:
            # Try to get the primary image from the eBay listing
            # eBay item images follow a predictable CDN pattern; we try the URL directly
            ebay_url = sub['ebay_url']
            item_id = sub['ebay_item_id']

            # Try eBay image CDN URL first
            img_url = f"https://i.ebayimg.com/images/g/{item_id}/s-l1600.jpg"
            resp = http_requests.get(img_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})

            if resp.status_code != 200:
                # Fallback: try scraping the listing page for og:image (simplified)
                page_resp = http_requests.get(ebay_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                if page_resp.status_code == 200:
                    import re
                    m = re.search(r'<meta property="og:image" content="([^"]+)"', page_resp.text)
                    if m:
                        resp = http_requests.get(m.group(1), timeout=10)

            if resp.status_code == 200 and PHASH_AVAILABLE:
                phash_value = _compute_phash(resp.content)
            else:
                image_fetch_error = f"Image fetch returned HTTP {resp.status_code}"

        except Exception as img_err:
            image_fetch_error = str(img_err)
            print(f"[SlabGuard] Image fetch error for submission {submission_id}: {img_err}")

        # ── Insert into approved DB ──
        cur.execute("""
            INSERT INTO slabguard_flagged_images
                (phash, ebay_item_id, ebay_url, submission_id, notes, added_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (phash) DO NOTHING
            RETURNING id
        """, (
            phash_value or f"manual_{submission_id}",  # fallback key if hash failed
            sub['ebay_item_id'],
            sub['ebay_url'],
            submission_id,
            note or image_fetch_error,
            g.admin_id
        ))
        flagged_id = cur.fetchone()
        flagged_id = flagged_id['id'] if flagged_id else None

        # ── Mark submission approved ──
        cur.execute("""
            UPDATE slabguard_submissions
            SET status = 'approved',
                reviewed_by = %s,
                review_note = %s,
                reviewed_at = NOW(),
                phash = %s
            WHERE id = %s
        """, (g.admin_id, note, phash_value, submission_id))

        conn.commit()

        return jsonify({
            'success': True,
            'submission_id': submission_id,
            'flagged_image_id': flagged_id,
            'phash': phash_value,
            'phash_available': phash_value is not None,
            'image_fetch_error': image_fetch_error
        })

    except Exception as e:
        if conn:
            conn.rollback()
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@admin_slabguard_bp.route('/<int:submission_id>/reject', methods=['POST'])
@require_admin_auth
def reject_submission(submission_id):
    """Admin rejects a submission — discards it with an optional note."""
    data = request.get_json() or {}
    note = data.get('note', '')

    conn = None
    try:
        conn = _get_db()
        cur = conn.cursor()

        cur.execute("""
            UPDATE slabguard_submissions
            SET status = 'rejected',
                reviewed_by = %s,
                review_note = %s,
                reviewed_at = NOW()
            WHERE id = %s AND status = 'pending'
            RETURNING id
        """, (g.admin_id, note, submission_id))

        result = cur.fetchone()
        conn.commit()

        if result:
            return jsonify({'success': True, 'submission_id': submission_id})
        else:
            return jsonify({'success': False, 'error': 'Submission not found or already reviewed'}), 404

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

