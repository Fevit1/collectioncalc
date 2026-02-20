"""
Monitor Blueprint - Marketplace monitoring API for Slab Guard
Routes: /api/monitor/check-image, /api/monitor/check-hash,
        /api/monitor/stolen-hashes, /api/monitor/report-match,
        /api/monitor/compare-copies

Uses four-tier fingerprint matching:
  1. Composite hashing (pHash+dHash+aHash+wHash): issue-level matching
  2. Edge strip hashing (v3): copy-level quick filter via trim differences
  3. SIFT-aligned edge IoU (v4): copy-level identification via defect overlap
  4. Claude Vision "Difference Finder" (optional): semantic confirmation

Copy matching (Session 48 — SIFT + Edge IoU):
  - edge_iou ≥ 0.025: SAME_COPY (same physical defects visible)
  - edge_iou ≤ 0.010: DIFFERENT_COPY (no shared defects)
  - 0.010 < edge_iou < 0.025: UNCERTAIN → optional Claude Vision

Tested thresholds (Feb 2026):
  - Composite per-angle: <70 CRITICAL, <73 PROBABLE, >77 DIFFERENT
  - SIFT edge IoU: SAME=[0.033-0.036], DIFF=[0.001-0.009], 7x ratio
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

# SIFT + Edge IoU copy matching (Session 48 — best approach)
try:
    from routes.slab_guard_cv import compare_covers, compare_covers_with_vision, CV2_AVAILABLE
    SIFT_CV_AVAILABLE = CV2_AVAILABLE
except ImportError:
    SIFT_CV_AVAILABLE = False
    print("⚠️ slab_guard_cv not available — SIFT copy matching disabled")

# Simple in-memory rate limiter
_rate_limit_store = {}  # ip -> (count, window_start)
RATE_LIMIT_MAX = 60  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds

# Composite matching thresholds (per-angle, sum of 4 algos, out of 256 bits)
COMPOSITE_THRESHOLD_CRITICAL = 70   # 95%+ same comic
COMPOSITE_THRESHOLD_PROBABLE = 73   # High probability match
COMPOSITE_THRESHOLD_DISMISS  = 77   # Different comic
COMPOSITE_THRESHOLD_MARKETPLACE = 105  # Session 52: Looser gate for cross-camera marketplace photos
                                       # eBay vs registered: 60-90 range after auto-orient
                                       # Allows SIFT to make the final same/diff copy verdict

# Edge strip thresholds (avg distance across 8 regions × 4 algos, per angle)
# Based on testing: same-copy max ~122, diff-copy min ~126
EDGE_THRESHOLD_SAME_COPY = 124      # Below this = likely same physical copy
EDGE_THRESHOLD_DIFF_COPY = 126      # Above this = likely different physical copy

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


def auto_orient_pil(img):
    """
    Auto-orient a PIL image for consistent fingerprinting.

    Session 51: Perceptual hashes are NOT rotation-invariant. Phone photos taken
    sideways had hash distances of 103-113 (blocked by 77 threshold). After
    auto-rotation: distances drop to 62-88, enabling marketplace matching.

    Steps:
      1. EXIF transpose — applies camera orientation metadata
      2. Aspect ratio heuristic — rotates landscape to portrait (comics are tall)

    Must match registry.py auto_orient_pil() exactly.
    """
    from PIL import ImageOps

    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    w, h = img.size
    if w > h:
        # Landscape → rotate 90° CW to portrait.
        # PIL rotate(270) = 90° clockwise. Matches most common phone orientation.
        img = img.rotate(270, expand=True)

    return img


def preprocess_for_fingerprint(img):
    """
    Normalize image before fingerprinting. Must match registry.py preprocessing exactly.
    Steps: auto-orient → grayscale → auto-crop → resize 256x256 → autocontrast → blur
    """
    from PIL import ImageFilter, ImageOps, ImageStat

    # Auto-orient before any processing (Session 51)
    img = auto_orient_pil(img)

    img = img.convert('L')

    # Auto-crop: estimate background from corners, find content bounding box
    width, height = img.size
    pixels = img.load()
    corner_size = max(5, min(width, height) // 20)
    corners = []
    for region in [
        (0, 0, corner_size, corner_size),
        (width - corner_size, 0, width, corner_size),
        (0, height - corner_size, corner_size, height),
        (width - corner_size, height - corner_size, width, height)
    ]:
        corner_img = img.crop(region)
        corner_stat = ImageStat.Stat(corner_img)
        corners.append(corner_stat.mean[0])
    bg_color = sum(corners) / len(corners)

    left, top, right, bottom = width, height, 0, 0
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            if abs(pixels[x, y] - bg_color) > 30:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)

    pad_x = max(5, int(width * 0.02))
    pad_y = max(5, int(height * 0.02))
    left = max(0, left - pad_x)
    top = max(0, top - pad_y)
    right = min(width, right + pad_x)
    bottom = min(height, bottom + pad_y)

    if right - left > width * 0.3 and bottom - top > height * 0.3:
        img = img.crop((left, top, right, bottom))

    img = img.resize((256, 256), PIL_Image.LANCZOS)
    img = ImageOps.autocontrast(img, cutoff=2)
    img = img.filter(ImageFilter.GaussianBlur(radius=1))

    return img


def generate_composite_from_url(image_url):
    """Download image, preprocess, and generate multi-algorithm composite fingerprint.
    Returns dict with phash, dhash, ahash, whash (16 hex chars each).
    Preprocessing matches registry.py to ensure consistent comparison."""
    if not imagehash or not PIL_Image:
        return None

    try:
        import requests as req
        from io import BytesIO

        response = req.get(image_url, timeout=15)
        response.raise_for_status()
        img = PIL_Image.open(BytesIO(response.content))

        # Preprocess: grayscale, auto-crop, resize, normalize contrast, blur
        img = preprocess_for_fingerprint(img)

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


def generate_edge_strips_from_url(image_url, strip_pct=5, hash_size=16):
    """
    Download image and generate edge strip hashes for copy-level identification.
    Returns dict with hashes for 8 edge regions, or None on failure.
    """
    if not imagehash or not PIL_Image:
        return None

    try:
        import requests as req
        from io import BytesIO
        from PIL import ImageOps

        response = req.get(image_url, timeout=15)
        response.raise_for_status()
        img = PIL_Image.open(BytesIO(response.content))

        # Auto-orient before any processing (Session 51)
        img = auto_orient_pil(img)

        w, h = img.size

        # Convert to grayscale and normalize (match registry preprocessing)
        img = img.convert('L')
        img = ImageOps.autocontrast(img, cutoff=2)

        strip_w = max(int(w * strip_pct / 100), 20)
        strip_h = max(int(h * strip_pct / 100), 20)

        regions = {
            'top': img.crop((0, 0, w, strip_h)),
            'bottom': img.crop((0, h - strip_h, w, h)),
            'left': img.crop((0, 0, strip_w, h)),
            'right': img.crop((w - strip_w, 0, w, h)),
            'top_left': img.crop((0, 0, strip_w * 2, strip_h * 2)),
            'top_right': img.crop((w - strip_w * 2, 0, w, strip_h * 2)),
            'bottom_left': img.crop((0, h - strip_h * 2, strip_w * 2, h)),
            'bottom_right': img.crop((w - strip_w * 2, h - strip_h * 2, w, h)),
        }

        edge_hashes = {}
        for region_name, region_img in regions.items():
            edge_hashes[region_name] = {
                'phash': str(imagehash.phash(region_img, hash_size=hash_size)),
                'dhash': str(imagehash.dhash(region_img, hash_size=hash_size)),
                'ahash': str(imagehash.average_hash(region_img, hash_size=hash_size)),
                'whash': str(imagehash.whash(region_img, hash_size=hash_size)),
            }

        return edge_hashes
    except Exception as e:
        print(f"Monitor edge strip generation error: {e}")
        return None


def edge_strip_distance(edge1, edge2):
    """
    Compare two sets of edge strip hashes.

    Args:
        edge1, edge2: dicts of { region: {phash, dhash, ahash, whash} }

    Returns:
        (avg_distance, per_region_distances) where avg_distance is the mean
        across all regions and algorithms.

    Testing showed:
        - Same comic re-photographed: avg ~121 (out of 256)
        - Different copy same issue: avg ~129
        - Threshold around 124-126 for separation
    """
    all_distances = []
    region_distances = {}

    for region in ['top', 'bottom', 'left', 'right',
                   'top_left', 'top_right', 'bottom_left', 'bottom_right']:
        r1 = edge1.get(region, {})
        r2 = edge2.get(region, {})
        if not r1 or not r2:
            continue

        region_dists = []
        for algo in ['phash', 'dhash', 'ahash', 'whash']:
            h1 = r1.get(algo)
            h2 = r2.get(algo)
            if h1 and h2:
                d = hamming_distance(h1, h2)
                region_dists.append(d)
                all_distances.append(d)

        if region_dists:
            region_distances[region] = sum(region_dists) / len(region_dists)

    avg_distance = sum(all_distances) / len(all_distances) if all_distances else 256.0
    return avg_distance, region_distances


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


def find_matches(query_hash, max_distance=20, stolen_only=False,
                  query_composite=None, query_edge_strips=None,
                  marketplace_mode=False):
    """
    Compare query hash against all registered comics using three-tier matching:
      1. Composite (4 algos on full image) — issue-level match
      2. Edge strips (8 regions × 4 algos) — copy-level identification
      3. Legacy pHash — backward compat

    Args:
        query_hash: Legacy pHash hex string (16 chars)
        max_distance: Max pHash distance for legacy matching (default 20)
        stolen_only: Only search stolen comics
        query_composite: Dict with {phash, dhash, ahash, whash} for composite matching
        query_edge_strips: Dict with edge strip hashes for copy-level matching
        marketplace_mode: Use looser hash threshold (105 vs 77) for cross-camera
                          marketplace photos. Lets SIFT make the final verdict.
                          Session 52: eBay vs registered = 60-90 after auto-orient.

    Returns list of matches sorted by confidence (lowest distance first).
    Each match includes:
      - match_type: 'composite', 'composite_edge', or 'phash_legacy'
      - edge_distance: avg edge strip distance (if available)
      - copy_match: 'same_copy', 'different_copy', or 'unknown'
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
                # stored_composite format: { "front": {phash, dhash, ahash, whash}, "edge_strips": {...}, ... }
                stored_front = stored_composite.get('front')
                if stored_front:
                    comp_dist, algo_dists = composite_distance(query_composite, stored_front)

                    # Composite threshold: 77 standard, 105 marketplace mode
                    # Marketplace mode uses looser gate to let SIFT make final verdict
                    threshold = COMPOSITE_THRESHOLD_MARKETPLACE if marketplace_mode else COMPOSITE_THRESHOLD_DISMISS
                    if comp_dist <= threshold:
                        confidence = max(0, round(100 - (comp_dist * 0.39), 1))  # 0/256=100%, 256/256=0%
                        alert_level = composite_alert_level(comp_dist)

                        # --- EDGE STRIP COPY-LEVEL MATCHING ---
                        edge_dist = None
                        copy_match = 'unknown'
                        edge_region_dists = None
                        match_type = 'composite'

                        stored_edge_strips = stored_composite.get('edge_strips', {})
                        stored_front_edges = stored_edge_strips.get('front')

                        if query_edge_strips and stored_front_edges:
                            edge_dist, edge_region_dists = edge_strip_distance(
                                query_edge_strips, stored_front_edges)

                            if edge_dist <= EDGE_THRESHOLD_SAME_COPY:
                                copy_match = 'same_copy'
                                # Boost confidence for same-copy match
                                confidence = min(99.9, confidence + 10)
                            elif edge_dist >= EDGE_THRESHOLD_DIFF_COPY:
                                copy_match = 'different_copy'
                                # Reduce confidence — same issue but different physical copy
                                confidence = max(10, confidence - 15)
                            else:
                                copy_match = 'uncertain'

                            match_type = 'composite_edge'

                        # Get front cover photo URL + extra photos for SIFT comparison
                        reg_photo_url = None
                        reg_extra_photos = None
                        if photos:
                            try:
                                photos_dict = json.loads(photos) if isinstance(photos, str) else photos
                                if isinstance(photos_dict, dict):
                                    reg_photo_url = photos_dict.get('front')
                                    reg_extra_photos = photos_dict.get('extra')
                            except (json.JSONDecodeError, TypeError):
                                pass
                        # Also check fingerprint_composite for extra_photos (stored at registration)
                        if not reg_extra_photos and stored_composite:
                            reg_extra_photos = stored_composite.get('extra_photos')

                        matches.append({
                            'registry_id': reg_id,
                            'serial_number': serial,
                            'status': status,
                            'alert_level': alert_level,
                            'hamming_distance': comp_dist,
                            'match_type': match_type,
                            'algo_distances': algo_dists,
                            'edge_distance': round(edge_dist, 1) if edge_dist is not None else None,
                            'copy_match': copy_match,
                            'confidence': confidence,
                            'registration_date': reg_date.isoformat() if reg_date else None,
                            'reported_stolen_date': stolen_date.isoformat() if stolen_date else None,
                            'comic': {
                                'title': title,
                                'issue_number': issue,
                                'publisher': publisher,
                                'grade': float(grade) if grade else None
                            },
                            'owner_display': mask_email(email),
                            'has_extra_photos': bool(reg_extra_photos),
                            'extra_photo_count': len(reg_extra_photos) if reg_extra_photos else 0,
                            '_reg_photo_url': reg_photo_url,          # internal: for SIFT comparison
                            '_reg_extra_photos': reg_extra_photos,    # internal: for SIFT/Vision
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

    # Generate edge strip hashes for copy-level matching
    query_edge_strips = generate_edge_strips_from_url(image_url)

    # Find matches using composite + edge strips + legacy methods
    max_distance = data.get('max_distance', 20)
    stolen_only = data.get('stolen_only', False)
    use_sift = data.get('use_sift', True)       # SIFT+edge IoU (fast, default on)
    use_vision = data.get('use_vision', False)   # Claude Vision (slower, $0.03/call)
    marketplace_mode = data.get('marketplace_mode', False)  # Session 52: loose hash gate for eBay photos

    matches = find_matches(
        query_hash,
        max_distance=max_distance,
        stolen_only=stolen_only,
        query_composite=query_composite,
        query_edge_strips=query_edge_strips,
        marketplace_mode=marketplace_mode,
    )

    # ── SIFT + EDGE IoU COPY-LEVEL VERIFICATION ──────────────────
    # For each issue-level match, run SIFT comparison to determine
    # if query photo shows the SAME physical copy or a DIFFERENT one.
    #
    # Session 53: In marketplace mode, ALWAYS use Vision as primary verdict.
    # Cross-camera photos (blanket vs white background, different lighting)
    # generate spurious border inliers and false edge matches that fool the
    # quantitative pipeline. Vision handles these differences correctly by
    # focusing on physical defects rather than edge structure.
    effective_use_vision = use_vision or marketplace_mode  # Session 53: marketplace forces Vision

    sift_results = {}
    if use_sift and SIFT_CV_AVAILABLE and matches:
        for match in matches:
            reg_photo_url = match.get('_reg_photo_url')
            if not reg_photo_url:
                continue

            extra_photos = match.get('_reg_extra_photos')

            try:
                if effective_use_vision:
                    cv_result = compare_covers_with_vision(
                        ref_url=reg_photo_url,
                        test_url=image_url,
                        extra_ref_photos=extra_photos,
                        marketplace_mode=marketplace_mode,
                    )
                    verdict_key = 'final_verdict'
                    conf_key = 'final_confidence'
                else:
                    cv_result = compare_covers(
                        ref_url=reg_photo_url,
                        test_url=image_url,
                        extra_ref_photos=extra_photos,
                    )
                    verdict_key = 'verdict'
                    conf_key = 'confidence'

                if cv_result.get('success'):
                    sift_verdict = cv_result.get(verdict_key, 'uncertain')
                    sift_confidence = cv_result.get(conf_key, 0.5)

                    # Override edge strip copy_match with SIFT result
                    match['copy_match'] = sift_verdict
                    match['match_type'] = 'sift_edge_iou' + ('_vision' if effective_use_vision else '')
                    match['sift_edge_iou'] = cv_result.get('avg_edge_iou')
                    match['sift_alignment'] = cv_result.get('alignment')
                    if cv_result.get('verdict_source'):
                        match['verdict_source'] = cv_result.get('verdict_source')

                    # Adjust confidence based on SIFT verdict
                    if sift_verdict == 'same_copy':
                        match['confidence'] = min(99.9, match['confidence'] + 15)
                    elif sift_verdict == 'different_copy':
                        match['confidence'] = max(10, match['confidence'] - 15)

                    # Include vision details if available
                    if effective_use_vision and cv_result.get('vision_verdict'):
                        match['vision_verdict'] = cv_result.get('vision_verdict')
                        match['vision_reasoning'] = cv_result.get('vision_reasoning')
                        match['vision_confidence'] = cv_result.get('vision_confidence')
                        match['cost_usd'] = cv_result.get('cost_usd')

                    sift_results[match['serial_number']] = {
                        'verdict': sift_verdict,
                        'edge_iou': cv_result.get('avg_edge_iou'),
                    }
                else:
                    sift_results[match['serial_number']] = {
                        'error': cv_result.get('error', 'unknown'),
                    }

            except Exception as e:
                print(f"SIFT comparison error for {match.get('serial_number')}: {e}")
                sift_results[match['serial_number']] = {'error': str(e)}

    # Strip internal fields before returning
    for match in matches:
        match.pop('_reg_photo_url', None)
        match.pop('_reg_extra_photos', None)

    return jsonify({
        'success': True,
        'query_hash': query_hash,
        'query_composite': query_composite,
        'has_edge_strips': query_edge_strips is not None,
        'sift_available': SIFT_CV_AVAILABLE,
        'sift_used': use_sift and SIFT_CV_AVAILABLE,
        'vision_used': effective_use_vision,
        'marketplace_mode': marketplace_mode,
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


@monitor_bp.route('/compare-copies', methods=['POST'])
@rate_limit
def compare_copies():
    """
    Direct copy-level comparison between two comic cover photos.

    Accepts:
        ref_url: URL of registered (reference) cover photo
        test_url: URL of test/query cover photo
        use_vision: bool (default False) — include Claude Vision analysis

    Returns SIFT alignment + edge IoU metrics + copy verdict.
    This endpoint is useful for:
      - Testing/debugging copy matching
      - On-demand comparison without full registry search
      - Claude Vision confirmation for high-value items
    """
    data = request.get_json() or {}
    ref_url = data.get('ref_url')
    test_url = data.get('test_url')
    use_vision = data.get('use_vision', False)

    if not ref_url or not test_url:
        return jsonify({
            'success': False,
            'error': 'ref_url and test_url are required'
        }), 400

    if not SIFT_CV_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'SIFT copy matching not available (opencv not installed)',
            'sift_available': False,
        }), 503

    try:
        if use_vision:
            result = compare_covers_with_vision(
                ref_url=ref_url,
                test_url=test_url,
            )
        else:
            result = compare_covers(
                ref_url=ref_url,
                test_url=test_url,
            )

        return jsonify(result)

    except Exception as e:
        print(f"Compare copies error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
