"""
Registry Blueprint - Comic fingerprinting and theft recovery
Routes: /api/registry/register, /api/registry/status

Fingerprinting uses TWO complementary approaches:
  1. Composite hashing (pHash + dHash + aHash + wHash) on full image
     - Good at: confirming same comic re-photographed (low distance)
     - Weak at: distinguishing different copies of same issue
  2. Edge strip hashing (v3) - hashes of thin edge crops
     - Good at: distinguishing different copies via manufacturing trim differences
     - Each physical copy is cut slightly differently at the printer
     - Edge strip distances show 5-8 point gap between same vs different copy

Testing history (Feb 2026):
  - Composite alone: same-comic 120 vs different-copy 128 → overlap possible
  - Edge strips alone (5% width): same-comic max 121 vs diff-copy min 125 → separated
  - Combined approach: composite for issue-level matching + edge for copy-level ID
"""
import os
import json
import psycopg2
from datetime import datetime
from flask import Blueprint, jsonify, request, g
from auth import require_auth, require_approved

# Create blueprint
registry_bp = Blueprint('registry', __name__, url_prefix='/api/registry')

# These will be set by wsgi.py
imagehash = None
PIL_Image = None

def init_modules(imagehash_lib, pil_image):
    """Initialize modules from wsgi.py"""
    global imagehash, PIL_Image
    imagehash = imagehash_lib
    PIL_Image = pil_image


def _contains_offensive(suffix):
    """
    Check if a serial number suffix contains offensive words or patterns.
    Returns True if the suffix should be rejected.
    """
    s = suffix.upper()

    # Profanity and slurs (check if any appear as substrings)
    BAD_WORDS = [
        'FUC', 'FUK', 'FKN', 'SHT', 'ASS', 'ARS', 'DMN', 'DAM',
        'BTH', 'CKS', 'DCK', 'DCK', 'CNT', 'CUM', 'TIT', 'NUT',
        'SUK', 'SUC', 'HOR', 'FAG', 'FAT', 'GAY', 'JEW', 'NIG',
        'NGA', 'WET', 'WTF', 'STF', 'KKK', 'NAZ', 'KYS',
        'SEX', 'XXX', 'DIK', 'DIE', 'KIL', 'RAP', 'PEN',
    ]

    # Offensive number patterns
    BAD_NUMBERS = [
        '666',   # devil / satanic
        '69',    # sexual
        '88',    # white supremacist
        '14',    # white supremacist (when paired with 88)
        '1488',  # white supremacist combo
        '420',   # drug reference
        '911',   # sensitive
    ]

    for word in BAD_WORDS:
        if word in s:
            return True

    for num in BAD_NUMBERS:
        if num in s:
            return True

    return False


def generate_serial_number():
    """
    Generate unique serial number: SW-YYYY-XXXXXX
    where XXXXXX is a random 6-character alphanumeric suffix.

    Uses an unambiguous character set (no 0/O/1/I/L) so serials are
    easy to read on a slab label and hard for bots to guess.
    ~887 million combinations per year.

    Filters out offensive words, slurs, and sensitive number patterns.
    """
    import secrets

    # Unambiguous alphanumeric: removed 0, O, 1, I, L
    CHARSET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'

    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    year = datetime.now().year

    # Generate random suffix, retry on collision or offensive content
    for _ in range(50):
        suffix = ''.join(secrets.choice(CHARSET) for _ in range(6))

        if _contains_offensive(suffix):
            continue

        serial = f"SW-{year}-{suffix}"

        cur.execute("""
            SELECT 1 FROM comic_registry WHERE serial_number = %s
        """, (serial,))

        if not cur.fetchone():
            cur.close()
            conn.close()
            return serial

    cur.close()
    conn.close()
    raise Exception("Failed to generate unique serial number after 50 attempts")


# Session 53: Shared preprocessing — single source of truth in fingerprint_utils.py
# Previously duplicated here and in monitor.py with "must match exactly" comments.
from routes.fingerprint_utils import auto_orient_pil, preprocess_for_fingerprint


# ─── Photo Quality Gate (Session 56) ───────────────────────────────────────
# Thresholds calibrated against real phone photos from Sessions 48-55.
# All test photos (4080x3072, good phone camera) scored well above these.
# These thresholds target genuinely poor submissions: tiny screenshots,
# blurry thumbnails, heavily cropped images.
QUALITY_MIN_DIMENSION = 500       # Block: either side < 500px
QUALITY_WARN_DIMENSION = 1000     # Warn: either side < 1000px
QUALITY_MIN_BLUR = 100            # Block: Laplacian variance < 100 (extremely blurry)
QUALITY_WARN_BLUR = 500           # Warn: Laplacian variance < 500
QUALITY_MIN_SIFT_KPS = 500        # Block: fewer than 500 SIFT keypoints (at 800px resize)
QUALITY_WARN_SIFT_KPS = 1500      # Warn: fewer than 1500 SIFT keypoints


def assess_photo_quality(photo_url, timeout=10):
    """
    Assess photo quality for Slab Guard registration.

    Checks resolution, sharpness (blur), and feature richness (SIFT keypoints).
    Returns a quality report with pass/warn/fail status and actionable tips.

    Session 56: Added to prevent registration of photos too poor for
    reliable SIFT copy matching. Block truly bad photos, warn on marginal.

    Args:
        photo_url: URL of the photo to assess
        timeout: Download timeout in seconds

    Returns dict:
        overall: 'pass' | 'warn' | 'fail'
        checks: dict of individual check results
        warnings: list of human-readable warning messages
        tips: list of actionable improvement suggestions
    """
    import requests
    from io import BytesIO
    import numpy as np

    try:
        import cv2
        cv_available = True
    except ImportError:
        cv_available = False

    result = {
        'overall': 'pass',
        'checks': {},
        'warnings': [],
        'tips': [],
        'exif_rotated': False,
    }

    try:
        response = requests.get(photo_url, timeout=timeout)
        response.raise_for_status()
        img_bytes = response.content

        img_pil = PIL_Image.open(BytesIO(img_bytes))

        # Check EXIF rotation
        exif = img_pil.getexif() if hasattr(img_pil, 'getexif') else {}
        orientation = exif.get(274, 1)  # 274 = Orientation tag, 1 = normal
        if orientation and orientation != 1:
            result['exif_rotated'] = True
            result['warnings'].append(
                'Photo was rotated — auto-corrected. For best results, hold your phone upright when photographing.'
            )

        # Auto-orient
        img_pil = auto_orient_pil(img_pil).convert('RGB')
        width, height = img_pil.size

        # ── Resolution check ──
        min_side = min(width, height)
        result['checks']['resolution'] = {
            'width': width,
            'height': height,
            'min_side': min_side,
        }
        if min_side < QUALITY_MIN_DIMENSION:
            result['checks']['resolution']['status'] = 'fail'
            result['overall'] = 'fail'
            result['warnings'].append(
                f'Image too small ({width}×{height}). Minimum {QUALITY_MIN_DIMENSION}px on shortest side required.'
            )
            result['tips'].append('Use your phone camera at full resolution — avoid screenshots or thumbnails.')
        elif min_side < QUALITY_WARN_DIMENSION:
            result['checks']['resolution']['status'] = 'warn'
            if result['overall'] == 'pass':
                result['overall'] = 'warn'
            result['warnings'].append(
                f'Image is small ({width}×{height}). Higher resolution improves fingerprint reliability.'
            )
            result['tips'].append('Move closer or use a higher resolution camera setting.')
        else:
            result['checks']['resolution']['status'] = 'pass'

        # Skip CV-dependent checks if OpenCV not available
        if not cv_available:
            result['checks']['blur'] = {'status': 'skipped', 'reason': 'OpenCV not available'}
            result['checks']['sift_keypoints'] = {'status': 'skipped', 'reason': 'OpenCV not available'}
            return result

        # Convert to CV2 for blur and SIFT checks
        img_np = np.array(img_pil)
        img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        # Resize to standard analysis size (800px max side)
        h, w = img_cv.shape[:2]
        scale = 800 / max(h, w)
        resized = cv2.resize(img_cv, (int(w * scale), int(h * scale)))
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        # ── Blur check (Laplacian variance) ──
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        result['checks']['blur'] = {
            'score': round(blur_score, 1),
        }
        if blur_score < QUALITY_MIN_BLUR:
            result['checks']['blur']['status'] = 'fail'
            result['overall'] = 'fail'
            result['warnings'].append(
                f'Image is too blurry (sharpness score: {blur_score:.0f}, minimum: {QUALITY_MIN_BLUR}).'
            )
            result['tips'].append('Hold your phone steady and make sure the comic is in focus. Tap the screen to focus before shooting.')
        elif blur_score < QUALITY_WARN_BLUR:
            result['checks']['blur']['status'] = 'warn'
            if result['overall'] == 'pass':
                result['overall'] = 'warn'
            result['warnings'].append(
                f'Image could be sharper (score: {blur_score:.0f}). Sharper photos produce stronger fingerprints.'
            )
            result['tips'].append('Try better lighting and hold your phone steady.')
        else:
            result['checks']['blur']['status'] = 'pass'

        # ── SIFT keypoints check ──
        sift = cv2.SIFT_create(nfeatures=5000)
        keypoints = sift.detect(gray, None)
        kp_count = len(keypoints)

        result['checks']['sift_keypoints'] = {
            'count': kp_count,
        }
        if kp_count < QUALITY_MIN_SIFT_KPS:
            result['checks']['sift_keypoints']['status'] = 'fail'
            result['overall'] = 'fail'
            result['warnings'].append(
                f'Not enough visual detail detected ({kp_count} features, minimum: {QUALITY_MIN_SIFT_KPS}). '
                'This photo cannot be reliably matched.'
            )
            result['tips'].append(
                'Make sure the full comic cover is visible, well-lit, and against a clean background.'
            )
        elif kp_count < QUALITY_WARN_SIFT_KPS:
            result['checks']['sift_keypoints']['status'] = 'warn'
            if result['overall'] == 'pass':
                result['overall'] = 'warn'
            result['warnings'].append(
                f'Low visual detail ({kp_count} features). Fingerprint may be less reliable for copy matching.'
            )
            result['tips'].append('Improve lighting and ensure the comic cover fills most of the frame.')
        else:
            result['checks']['sift_keypoints']['status'] = 'pass'

        # Add general tips if any warnings
        if result['overall'] == 'warn' and not result['tips']:
            result['tips'].append('Retake with better lighting for a stronger fingerprint.')

        return result

    except requests.RequestException as e:
        return {
            'overall': 'error',
            'checks': {},
            'warnings': [f'Could not download photo: {str(e)}'],
            'tips': ['Check that the photo URL is accessible.'],
            'exif_rotated': False,
        }
    except Exception as e:
        return {
            'overall': 'error',
            'checks': {},
            'warnings': [f'Photo quality check failed: {str(e)}'],
            'tips': [],
            'exif_rotated': False,
        }


def generate_edge_strip_hashes(img_bytes, strip_pct=5, hash_size=16):
    """
    Generate perceptual hashes of thin edge strips around the comic cover.

    Edge strips capture manufacturing trim differences — every physical copy
    is cut slightly differently at the printer, so the exact artwork visible
    at each edge varies between copies. This is a copy-level fingerprint.

    Testing showed (Feb 2026):
      - Same comic re-photographed: avg distance ~121 (out of 256)
      - Different copy same issue: avg distance ~129
      - Clean separation when photos are taken consistently

    Args:
        img_bytes: Raw image bytes
        strip_pct: Width of edge strip as % of image dimension (default 5%)
        hash_size: Hash size for perceptual hashing (default 16 = 256 bits)

    Returns dict with edge strip hashes for 8 regions:
        { 'top': {phash, dhash, ahash, whash},
          'bottom': {...}, 'left': {...}, 'right': {...},
          'top_left': {...}, 'top_right': {...},
          'bottom_left': {...}, 'bottom_right': {...} }
    """
    from io import BytesIO
    from PIL import ImageOps

    try:
        img = PIL_Image.open(BytesIO(img_bytes))

        # Auto-orient before any processing (Session 51)
        img = auto_orient_pil(img)

        w, h = img.size

        # Convert to grayscale and normalize
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
        print(f"Edge strip hash error: {e}")
        return None


def generate_fingerprint(photo_url):
    """
    Generate multi-algorithm composite fingerprint from photo URL.
    Returns dict with phash, dhash, ahash, whash (16 hex chars each).

    Images are preprocessed before hashing to normalize for real-world
    photo variation (lighting, background, framing, compression).

    Composite approach tested Feb 2026:
    - pHash alone: 4-bit separation margin (fragile with cropping)
    - Composite 4-algo: 13-bit margin per angle (robust)
    - Full multi-angle composite: 187-bit margin (excellent)
    - With preprocessing: worst-case same-comic 36/256 vs 72/256 raw
    """
    if not imagehash or not PIL_Image:
        return None

    try:
        import requests
        from io import BytesIO

        # Download image
        response = requests.get(photo_url, timeout=10)
        img = PIL_Image.open(BytesIO(response.content))

        # Preprocess: grayscale, auto-crop, resize, normalize contrast, blur
        img = preprocess_for_fingerprint(img)

        # Generate all 4 hash algorithms
        fingerprints = {
            'phash': str(imagehash.phash(img)),
            'dhash': str(imagehash.dhash(img)),
            'ahash': str(imagehash.average_hash(img)),
            'whash': str(imagehash.whash(img)),
        }
        return fingerprints
    except Exception as e:
        print(f"Fingerprint generation error: {e}")
        return None


def generate_all_fingerprints(photos_dict):
    """
    Generate composite fingerprints + edge strip hashes for all photo angles.

    Returns dict:
    {
      'front': {phash, dhash, ahash, whash},       # full-image composite
      'back': {...},
      'edge_strips': {                               # edge-level copy ID
        'front': { 'top': {phash,dhash,ahash,whash}, 'bottom': {...}, ... },
        'back': { 'top': {...}, ... }
      },
      'edge_version': 'v3_5pct'                      # version tag for compat
    }
    """
    import requests as req

    all_fingerprints = {}
    edge_strips = {}

    angle_map = {
        'front': 'front',
        'spine': 'spine',
        'back': 'back',
        'centerfold': 'centerfold'
    }

    for angle_key, angle_name in angle_map.items():
        url = photos_dict.get(angle_key)
        if url:
            # Generate full-image composite fingerprint (existing approach)
            fp = generate_fingerprint(url)
            if fp:
                all_fingerprints[angle_name] = fp

            # Generate edge strip hashes for front and back only
            # (spine and centerfold are too variable per our testing)
            if angle_key in ('front', 'back'):
                try:
                    response = req.get(url, timeout=10)
                    edge_fp = generate_edge_strip_hashes(response.content)
                    if edge_fp:
                        edge_strips[angle_name] = edge_fp
                except Exception as e:
                    print(f"Edge strip generation failed for {angle_name}: {e}")

    if edge_strips:
        all_fingerprints['edge_strips'] = edge_strips
        all_fingerprints['edge_version'] = 'v3_5pct'

    # ── EXTRA PHOTOS (enhanced fingerprinting) ───────────────────
    # Process alternate front/back photos for additional edge strip hashes.
    # Close-ups and defect photos are stored as URLs for the CV engine
    # to use at comparison time (no hashing needed — they're for Vision).
    extra_photos = photos_dict.get('extra', [])
    if extra_photos:
        alt_edge_strips = {}
        extra_urls = []

        for i, extra in enumerate(extra_photos):
            if not isinstance(extra, dict) or not extra.get('url'):
                continue

            url = extra['url']
            ptype = extra.get('type', 'other')

            # Fingerprint alternate front/back covers (useful for SIFT fallback)
            if ptype in ('alternate_front', 'alternate_back'):
                angle = 'front' if 'front' in ptype else 'back'
                try:
                    response = req.get(url, timeout=10)
                    edge_fp = generate_edge_strip_hashes(response.content)
                    if edge_fp:
                        alt_edge_strips[f'{angle}_alt_{i}'] = edge_fp
                except Exception as e:
                    print(f"Edge strip generation failed for extra {i} ({ptype}): {e}")

            # Store all extra photo URLs for the CV engine
            extra_urls.append({
                'type': ptype,
                'label': extra.get('label', ''),
                'url': url,
            })

        if alt_edge_strips:
            edge_strips_data = all_fingerprints.get('edge_strips', {})
            edge_strips_data.update(alt_edge_strips)
            all_fingerprints['edge_strips'] = edge_strips_data

        if extra_urls:
            all_fingerprints['extra_photos'] = extra_urls
            all_fingerprints['extra_count'] = len(extra_urls)

    return all_fingerprints if all_fingerprints else None


@registry_bp.route('/register', methods=['POST'])
@require_auth
@require_approved
def register_comic():
    """Register a comic for theft protection"""
    # Check plan registration limit
    try:
        from routes.billing import check_feature_access
        allowed, message = check_feature_access(g.user_id, 'slab_guard_registrations')
        if not allowed:
            return jsonify({
                'success': False,
                'error': message,
                'upgrade_required': True,
                'upgrade_url': '/pricing.html'
            }), 403
    except ImportError:
        pass  # Billing module not available, allow registration

    data = request.get_json() or {}
    comic_id = data.get('comic_id')

    if not comic_id:
        return jsonify({'success': False, 'error': 'comic_id is required'}), 400

    database_url = os.environ.get('DATABASE_URL')
    conn = None

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # Check if comic exists and belongs to user
        cur.execute("""
            SELECT id, title, issue, grade, photos,
                   is_slabbed, slab_cert_number, slab_company, slab_label_type
            FROM collections
            WHERE id = %s AND user_id = %s
        """, (comic_id, g.user_id))

        comic = cur.fetchone()
        if not comic:
            return jsonify({'success': False, 'error': 'Comic not found or access denied'}), 404

        comic_id, title, issue, grade, photos, is_slabbed, slab_cert_number, slab_company, slab_label_type = comic

        # Ensure photos is a dict (may come back as JSON string from DB)
        if photos and isinstance(photos, str):
            try:
                photos = json.loads(photos)
            except (json.JSONDecodeError, TypeError):
                photos = None

        # Check if already registered
        cur.execute("""
            SELECT serial_number, registration_date
            FROM comic_registry
            WHERE comic_id = %s
        """, (comic_id,))

        existing = cur.fetchone()
        if existing:
            return jsonify({
                'success': True,
                'already_registered': True,
                'serial_number': existing[0],
                'registration_date': existing[1].isoformat()
            })

        # ── Photo Quality Gate (Session 56) ──
        # Check front cover quality before spending time on fingerprint generation.
        # Block truly bad photos, warn on marginal, pass good ones.
        photo_quality = None
        if photos and isinstance(photos, dict):
            front_url = photos.get('front')
            if front_url:
                photo_quality = assess_photo_quality(front_url)

                if photo_quality['overall'] == 'fail':
                    return jsonify({
                        'success': False,
                        'error': 'Photo quality too low for reliable fingerprinting',
                        'photo_quality': photo_quality,
                        'quality_failed': True,
                    }), 400

        # Generate composite fingerprints from all available photos
        all_fingerprints = None
        fingerprint_hash = None  # Legacy pHash for backward compat

        if photos and isinstance(photos, dict):
            # Generate multi-algorithm fingerprints for all angles
            all_fingerprints = generate_all_fingerprints(photos)

            # Also generate legacy pHash from front cover
            front_url = photos.get('front')
            if front_url and all_fingerprints and 'front' in all_fingerprints:
                fingerprint_hash = all_fingerprints['front']['phash']

        if not fingerprint_hash:
            return jsonify({
                'success': False,
                'error': 'Could not generate fingerprint - photo may be missing or invalid'
            }), 400

        # Calculate confidence based on angles + edge strips + extra photos
        non_meta_keys = ('edge_strips', 'edge_version', 'extra_photos', 'extra_count')
        num_angles = len([k for k in all_fingerprints if k not in non_meta_keys]) if all_fingerprints else 0
        has_edge_strips = 'edge_strips' in all_fingerprints if all_fingerprints else False
        num_extras = all_fingerprints.get('extra_count', 0) if all_fingerprints else 0
        # Base: 4 angles = 85, 3 = 78, 2 = 70, 1 = 62
        # +10 bonus for edge strips (copy-level ID capability)
        # +2 per extra photo (up to +16 max) — more reference data = better matching
        extra_bonus = min(16.0, num_extras * 2.0)
        # Session 56: Reduce confidence if photo quality is marginal
        quality_penalty = 5.0 if (photo_quality and photo_quality['overall'] == 'warn') else 0.0
        confidence_score = min(99.0, 52.0 + (num_angles * 8.75) + (10.0 if has_edge_strips else 0.0) + extra_bonus - quality_penalty)

        # Generate serial number
        serial_number = generate_serial_number()

        # Serialize composite fingerprints as JSON
        composite_json = json.dumps(all_fingerprints) if all_fingerprints else None

        # Insert into registry
        cur.execute("""
            INSERT INTO comic_registry (
                user_id,
                comic_id,
                fingerprint_hash,
                fingerprint_composite,
                serial_number,
                fingerprint_algorithm,
                confidence_score,
                status,
                monitoring_enabled,
                slab_cert_number,
                slab_company,
                slab_label_type
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, registration_date
        """, (
            g.user_id,
            comic_id,
            fingerprint_hash,
            composite_json,
            serial_number,
            'comp_v3_edge',
            confidence_score,
            'active',
            True,
            slab_cert_number,
            slab_company,
            slab_label_type
        ))

        registry_id, registration_date = cur.fetchone()
        conn.commit()

        response_data = {
            'success': True,
            'serial_number': serial_number,
            'registration_date': registration_date.isoformat(),
            'fingerprint_hash': fingerprint_hash,
            'fingerprint_angles': num_angles,
            'confidence_score': confidence_score,
            'comic': {
                'title': title,
                'issue': issue,
                'grade': float(grade) if grade else None,
                'is_slabbed': is_slabbed or False,
                'slab_cert_number': slab_cert_number,
                'slab_company': slab_company,
                'slab_label_type': slab_label_type
            }
        }

        # Include photo quality warnings if any (Session 56)
        if photo_quality and photo_quality['overall'] == 'warn':
            response_data['photo_quality'] = photo_quality

        return jsonify(response_data)

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Registration error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if conn:
            cur.close()
            conn.close()


@registry_bp.route('/my-sightings', methods=['GET'])
@require_auth
def get_my_sightings():
    """
    Get all sighting reports for the authenticated user's registered comics.
    Returns sightings grouped by serial number, newest first.
    """
    database_url = os.environ.get('DATABASE_URL')
    conn = None

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                sr.id,
                sr.serial_number,
                sr.listing_url,
                sr.reporter_email,
                sr.message,
                sr.created_at,
                sr.owner_notified,
                sr.owner_response,
                c.title,
                c.issue,
                cr.status as registration_status
            FROM sighting_reports sr
            JOIN comic_registry cr ON sr.serial_number = cr.serial_number
            JOIN collections c ON cr.comic_id = c.id
            WHERE cr.user_id = %s
            ORDER BY sr.created_at DESC
        """, (g.user_id,))

        columns = [
            'id', 'serial_number', 'listing_url', 'reporter_email',
            'message', 'created_at', 'owner_notified', 'owner_response',
            'title', 'issue', 'registration_status'
        ]
        sightings = []
        for row in cur.fetchall():
            s = dict(zip(columns, row))
            s['created_at'] = s['created_at'].isoformat() if s['created_at'] else None
            # Obscure reporter email for privacy
            if s['reporter_email']:
                parts = s['reporter_email'].split('@')
                if len(parts) == 2:
                    local = parts[0]
                    domain = parts[1]
                    s['reporter_email'] = local[0] + '***@' + domain
            sightings.append(s)

        # Count unresponded sightings
        unresponded = sum(1 for s in sightings if not s['owner_response'])

        return jsonify({
            'success': True,
            'sightings': sightings,
            'total': len(sightings),
            'unresponded': unresponded,
        })

    except Exception as e:
        print(f"Error fetching my sightings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if conn:
            cur.close()
            conn.close()


@registry_bp.route('/sighting-response', methods=['POST'])
@require_auth
def respond_to_sighting():
    """
    Let an owner respond to a sighting report.
    Body: { sighting_id: int, response: 'confirmed_mine' | 'not_mine' | 'investigating' }

    Only the owner of the registered comic can respond.
    """
    data = request.get_json() or {}
    sighting_id = data.get('sighting_id')
    response_value = data.get('response', '').strip()

    valid_responses = ('confirmed_mine', 'not_mine', 'investigating')
    if not sighting_id or response_value not in valid_responses:
        return jsonify({
            'success': False,
            'error': f'Valid sighting_id and response ({", ".join(valid_responses)}) required.'
        }), 400

    database_url = os.environ.get('DATABASE_URL')
    conn = None

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # Verify this sighting belongs to a comic owned by the authenticated user
        cur.execute("""
            SELECT sr.id
            FROM sighting_reports sr
            JOIN comic_registry cr ON sr.serial_number = cr.serial_number
            WHERE sr.id = %s AND cr.user_id = %s
        """, (sighting_id, g.user_id))

        if not cur.fetchone():
            return jsonify({
                'success': False,
                'error': 'Sighting not found or access denied.'
            }), 404

        # Update the response
        cur.execute("""
            UPDATE sighting_reports
            SET owner_response = %s
            WHERE id = %s
        """, (response_value, sighting_id))

        conn.commit()

        return jsonify({
            'success': True,
            'message': 'Response recorded.',
            'sighting_id': sighting_id,
            'response': response_value,
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error responding to sighting: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if conn:
            cur.close()
            conn.close()


@registry_bp.route('/status/<int:comic_id>', methods=['GET'])
@require_auth
@require_approved
def get_registration_status(comic_id):
    """Check if a comic is registered"""
    database_url = os.environ.get('DATABASE_URL')
    conn = None

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                cr.serial_number,
                cr.registration_date,
                cr.status,
                cr.monitoring_enabled
            FROM comic_registry cr
            JOIN collections c ON cr.comic_id = c.id
            WHERE c.id = %s AND c.user_id = %s
        """, (comic_id, g.user_id))

        result = cur.fetchone()

        if result:
            return jsonify({
                'success': True,
                'registered': True,
                'serial_number': result[0],
                'registration_date': result[1].isoformat(),
                'status': result[2],
                'monitoring_enabled': result[3]
            })
        else:
            return jsonify({
                'success': True,
                'registered': False
            })

    except Exception as e:
        print(f"Status check error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if conn:
            cur.close()
            conn.close()


@registry_bp.route('/report-stolen/<int:comic_id>', methods=['POST'])
@require_auth
@require_approved
def report_comic_stolen(comic_id):
    """Mark a registered comic as reported stolen. Only the owner can do this."""
    database_url = os.environ.get('DATABASE_URL')
    conn = None

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # Verify comic is registered to this user
        cur.execute("""
            SELECT cr.id, cr.status, cr.serial_number
            FROM comic_registry cr
            WHERE cr.comic_id = %s AND cr.user_id = %s
        """, (comic_id, g.user_id))

        result = cur.fetchone()
        if not result:
            return jsonify({
                'success': False,
                'error': 'Comic not found or not registered'
            }), 404

        registry_id, current_status, serial_number = result

        if current_status not in ('active', 'recovered'):
            return jsonify({
                'success': False,
                'error': f'Cannot report stolen from current status: {current_status}'
            }), 400

        cur.execute("""
            UPDATE comic_registry
            SET status = 'reported_stolen',
                reported_stolen_date = NOW()
            WHERE id = %s
            RETURNING serial_number, reported_stolen_date
        """, (registry_id,))

        updated = cur.fetchone()
        conn.commit()

        return jsonify({
            'success': True,
            'serial_number': updated[0],
            'reported_stolen_date': updated[1].isoformat(),
            'message': 'Comic reported as stolen. Slab Guard is now actively monitoring for this comic.'
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Report stolen error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if conn:
            cur.close()
            conn.close()


@registry_bp.route('/mark-recovered/<int:comic_id>', methods=['POST'])
@require_auth
@require_approved
def mark_comic_recovered(comic_id):
    """Mark a stolen comic as recovered. Only the owner can do this."""
    database_url = os.environ.get('DATABASE_URL')
    conn = None

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        cur.execute("""
            SELECT cr.id, cr.status, cr.serial_number
            FROM comic_registry cr
            WHERE cr.comic_id = %s AND cr.user_id = %s
        """, (comic_id, g.user_id))

        result = cur.fetchone()
        if not result:
            return jsonify({
                'success': False,
                'error': 'Comic not found or not registered'
            }), 404

        registry_id, current_status, serial_number = result

        if current_status != 'reported_stolen':
            return jsonify({
                'success': False,
                'error': f'Only stolen comics can be marked as recovered. Current status: {current_status}'
            }), 400

        cur.execute("""
            UPDATE comic_registry
            SET status = 'recovered',
                recovery_date = NOW()
            WHERE id = %s
            RETURNING serial_number, recovery_date
        """, (registry_id,))

        updated = cur.fetchone()
        conn.commit()

        return jsonify({
            'success': True,
            'serial_number': updated[0],
            'recovery_date': updated[1].isoformat(),
            'message': 'Comic marked as recovered. Glad you got it back!'
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Mark recovered error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if conn:
            cur.close()
            conn.close()