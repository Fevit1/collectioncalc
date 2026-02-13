"""
Registry Blueprint - Comic fingerprinting and theft recovery
Routes: /api/registry/register, /api/registry/status
"""
import os
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
    """Generate pHash fingerprint from photo URL"""
    if not imagehash or not PIL_Image:
        return None

    try:
        import requests
        from io import BytesIO

        # Download image
        response = requests.get(photo_url, timeout=10)
        img = PIL_Image.open(BytesIO(response.content))

        # Generate pHash
        hash_value = imagehash.phash(img)
        return str(hash_value)
    except Exception as e:
        print(f"Fingerprint generation error: {e}")
        return None


@registry_bp.route('/register', methods=['POST'])
@require_auth
@require_approved
def register_comic():
    """Register a comic for theft protection"""
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
            SELECT id, title, issue_number, grade, photos
            FROM graded_comics
            WHERE id = %s AND user_id = %s
        """, (comic_id, g.user_id))

        comic = cur.fetchone()
        if not comic:
            return jsonify({'success': False, 'error': 'Comic not found or access denied'}), 404

        comic_id, title, issue, grade, photos = comic

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

        # Generate fingerprint from front cover photo
        fingerprint_hash = None
        if photos and isinstance(photos, dict):
            front_url = photos.get('front')
            if front_url:
                fingerprint_hash = generate_fingerprint(front_url)

        if not fingerprint_hash:
            return jsonify({
                'success': False,
                'error': 'Could not generate fingerprint - photo may be missing or invalid'
            }), 400

        # Generate serial number
        serial_number = generate_serial_number()

        # Insert into registry
        cur.execute("""
            INSERT INTO comic_registry (
                user_id,
                comic_id,
                fingerprint_hash,
                serial_number,
                fingerprint_algorithm,
                confidence_score,
                status,
                monitoring_enabled
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, registration_date
        """, (
            g.user_id,
            comic_id,
            fingerprint_hash,
            serial_number,
            'phash',
            85.0,  # Base confidence score for pHash
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
            JOIN graded_comics gc ON cr.comic_id = gc.id
            WHERE gc.id = %s AND gc.user_id = %s
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
