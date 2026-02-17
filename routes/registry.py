"""
Registry Blueprint - Comic fingerprinting and theft recovery
Routes: /api/registry/register, /api/registry/status

Fingerprinting uses multi-algorithm composite (pHash + dHash + aHash + wHash)
for robust matching. Testing showed:
  - Single pHash: only 4-bit margin between same-comic re-photo and different copies
  - Composite (4 algos): 13-bit margin per angle, 187-bit margin full composite
  - Biggest risk factor: cropping (different framing between photos)
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


def generate_fingerprint(photo_url):
    """
    Generate multi-algorithm composite fingerprint from photo URL.
    Returns dict with phash, dhash, ahash, whash (16 hex chars each).

    Composite approach tested Feb 2026:
    - pHash alone: 4-bit separation margin (fragile with cropping)
    - Composite 4-algo: 13-bit margin per angle (robust)
    - Full multi-angle composite: 187-bit margin (excellent)
    """
    if not imagehash or not PIL_Image:
        return None

    try:
        import requests
        from io import BytesIO

        # Download image
        response = requests.get(photo_url, timeout=10)
        img = PIL_Image.open(BytesIO(response.content))

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
    Generate composite fingerprints for all 4 photo angles.
    Returns dict: { 'front': {phash, dhash, ahash, whash}, 'back': {...}, ... }
    """
    all_fingerprints = {}
    angle_map = {
        'front': 'front',
        'spine': 'spine',
        'back': 'back',
        'centerfold': 'centerfold'
    }

    for angle_key, angle_name in angle_map.items():
        url = photos_dict.get(angle_key)
        if url:
            fp = generate_fingerprint(url)
            if fp:
                all_fingerprints[angle_name] = fp

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

        # Calculate confidence based on number of angles fingerprinted
        num_angles = len(all_fingerprints) if all_fingerprints else 0
        # 4 angles = 95 confidence, 3 = 88, 2 = 80, 1 = 70
        confidence_score = min(95.0, 60.0 + (num_angles * 8.75))

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
            'composite_v1',
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
