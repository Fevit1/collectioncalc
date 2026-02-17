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


def generate_serial_number():
    """Generate unique serial number: SW-YYYY-NNNNNN"""
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    year = datetime.now().year

    # Get max serial for current year
    cur.execute("""
        SELECT MAX(CAST(SUBSTRING(serial_number FROM 9) AS INTEGER))
        FROM comic_registry
        WHERE serial_number LIKE %s
    """, (f"SW-{year}-%",))

    result = cur.fetchone()[0]
    next_num = (result or 0) + 1

    cur.close()
    conn.close()

    return f"SW-{year}-{next_num:06d}"


def preprocess_for_fingerprint(img):
    """
    Normalize an image before fingerprinting to remove environmental noise.
    Makes fingerprints robust to real-world photo variation:
    - Different lighting conditions (autocontrast)
    - Different backgrounds (auto-crop)
    - Different phone distances (resize)
    - Compression artifacts (blur)

    Testing showed this cuts same-comic distances roughly in half:
    - Raw worst case: 72/256 per angle
    - Preprocessed worst case: 36/256 per angle
    """
    from PIL import ImageFilter, ImageOps, ImageStat

    # 1. Convert to grayscale (removes color/white-balance variation)
    img = img.convert('L')

    # 2. Auto-crop: trim uniform borders (removes background variation)
    width, height = img.size
    pixels = img.load()

    # Estimate background color from corners
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

    # Find bounding box of content (pixels differing from background by 30+)
    left, top, right, bottom = width, height, 0, 0
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            if abs(pixels[x, y] - bg_color) > 30:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)

    # Add small padding and crop if content area is meaningful
    pad_x = max(5, int(width * 0.02))
    pad_y = max(5, int(height * 0.02))
    left = max(0, left - pad_x)
    top = max(0, top - pad_y)
    right = min(width, right + pad_x)
    bottom = min(height, bottom + pad_y)

    if right - left > width * 0.3 and bottom - top > height * 0.3:
        img = img.crop((left, top, right, bottom))

    # 3. Resize to standard 256x256 (removes scale/distance variation)
    img = img.resize((256, 256), PIL_Image.LANCZOS)

    # 4. Normalize contrast (removes brightness/lighting variation)
    img = ImageOps.autocontrast(img, cutoff=2)

    # 5. Light Gaussian blur (removes noise/compression artifacts)
    img = img.filter(ImageFilter.GaussianBlur(radius=1))

    return img


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
            SELECT id, title, issue, grade, photos
            FROM collections
            WHERE id = %s AND user_id = %s
        """, (comic_id, g.user_id))

        comic = cur.fetchone()
        if not comic:
            return jsonify({'success': False, 'error': 'Comic not found or access denied'}), 404

        comic_id, title, issue, grade, photos = comic

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

        # Calculate confidence based on angles + edge strip availability
        num_angles = len([k for k in all_fingerprints if k not in ('edge_strips', 'edge_version')]) if all_fingerprints else 0
        has_edge_strips = 'edge_strips' in all_fingerprints if all_fingerprints else False
        # Base: 4 angles = 85, 3 = 78, 2 = 70, 1 = 62
        # +10 bonus for edge strips (copy-level ID capability)
        confidence_score = min(95.0, 52.0 + (num_angles * 8.75) + (10.0 if has_edge_strips else 0.0))

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
                monitoring_enabled
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            True
        ))

        registry_id, registration_date = cur.fetchone()
        conn.commit()

        return jsonify({
            'success': True,
            'serial_number': serial_number,
            'registration_date': registration_date.isoformat(),
            'fingerprint_hash': fingerprint_hash,
            'fingerprint_angles': num_angles,
            'confidence_score': confidence_score,
            'comic': {
                'title': title,
                'issue': issue,
                'grade': float(grade) if grade else None
            }
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Registration error: {e}")
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
