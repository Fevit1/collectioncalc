"""
Verify Blueprint - Public serial number lookup for theft protection
Routes: /api/verify/lookup/:serial_number, /api/verify/watermark/:serial_number
"""
import os
import io
import json
import requests as http_requests
import psycopg2
from flask import Blueprint, jsonify, request, send_file
from datetime import datetime

TURNSTILE_SECRET = os.environ.get('TURNSTILE_SECRET_KEY', '')

# Create blueprint (no auth required - this is public)
verify_bp = Blueprint('verify', __name__, url_prefix='/api/verify')

# These will be set by wsgi.py
imagehash = None
PIL_Image = None
PIL_ImageDraw = None
PIL_ImageFont = None

def init_modules(imagehash_lib, pil_image, pil_draw, pil_font):
    """Initialize modules from wsgi.py"""
    global imagehash, PIL_Image, PIL_ImageDraw, PIL_ImageFont
    imagehash = imagehash_lib
    PIL_Image = pil_image
    PIL_ImageDraw = pil_draw
    PIL_ImageFont = pil_font

def get_db():
    """Get database connection"""
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    return conn

def hash_email(email):
    """Obscure email for privacy: mike@gmail.com -> m***e@g***l.com"""
    if not email or '@' not in email:
        return "Anonymous User"

    local, domain = email.split('@', 1)
    domain_parts = domain.split('.')

    # Obscure local part
    if len(local) <= 2:
        local_obscured = local[0] + '*'
    else:
        local_obscured = local[0] + ('*' * (len(local) - 2)) + local[-1]

    # Obscure domain
    if len(domain_parts[0]) <= 2:
        domain_obscured = domain_parts[0][0] + '*'
    else:
        domain_obscured = domain_parts[0][0] + ('*' * (len(domain_parts[0]) - 2)) + domain_parts[0][-1]

    return f"{local_obscured}@{domain_obscured}.{'.'.join(domain_parts[1:])}"

def watermark_image(image_url, serial_number):
    """Add visible watermark to cover photo"""
    import requests
    from io import BytesIO

    # Download image
    response = requests.get(image_url, timeout=10)
    img = PIL_Image.open(BytesIO(response.content)).convert('RGBA')

    # Create overlay layer
    txt_layer = PIL_Image.new('RGBA', img.size, (255, 255, 255, 0))
    draw = PIL_ImageDraw.Draw(txt_layer)

    # Try to load a nice font, fall back to default
    try:
        font_size = max(24, int(img.width * 0.04))  # 4% of image width
        font = PIL_ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = PIL_ImageFont.load_default()

    # Add serial number in top-right corner (30% opacity white text)
    text = serial_number
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = img.width - text_width - 20
    y = 20

    # Add semi-transparent background for better readability
    padding = 10
    draw.rectangle(
        [(x - padding, y - padding), (x + text_width + padding, y + text_height + padding)],
        fill=(0, 0, 0, 128)  # 50% opacity black background
    )

    # Add text (white with 80% opacity)
    draw.text((x, y), text, fill=(255, 255, 255, 204), font=font)

    # Add "SLABWORTHY.COM" watermark at bottom
    try:
        small_font = PIL_ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(font_size * 0.6))
    except:
        small_font = font

    bottom_text = "SLABWORTHY.COM"
    bbox = draw.textbbox((0, 0), bottom_text, font=small_font)
    bottom_width = bbox[2] - bbox[0]
    bottom_height = bbox[3] - bbox[1]

    bottom_x = (img.width - bottom_width) // 2
    bottom_y = img.height - bottom_height - 20

    draw.rectangle(
        [(bottom_x - padding, bottom_y - padding), (bottom_x + bottom_width + padding, bottom_y + bottom_height + padding)],
        fill=(0, 0, 0, 128)
    )
    draw.text((bottom_x, bottom_y), bottom_text, fill=(255, 255, 255, 153), font=small_font)  # 60% opacity

    # Combine layers
    watermarked = PIL_Image.alpha_composite(img, txt_layer)

    return watermarked.convert('RGB')

@verify_bp.route('/lookup/<serial_number>', methods=['GET', 'POST'])
def lookup_serial(serial_number):
    """
    Public lookup of serial number
    Returns comic details without PII
    Requires Cloudflare Turnstile verification (POST with turnstile_token)
    """
    try:
        # Verify Turnstile token (required for POST, skip if GET for backward compat)
        if request.method == 'POST' and TURNSTILE_SECRET:
            body = request.get_json(silent=True) or {}
            turnstile_token = body.get('turnstile_token', '')

            if not turnstile_token:
                return jsonify({
                    'success': False,
                    'error': 'Security check required. Please complete the verification.'
                }), 403

            # Verify with Cloudflare
            verify_response = http_requests.post(
                'https://challenges.cloudflare.com/turnstile/v0/siteverify',
                data={
                    'secret': TURNSTILE_SECRET,
                    'response': turnstile_token,
                    'remoteip': request.remote_addr
                },
                timeout=5
            )
            verify_result = verify_response.json()

            if not verify_result.get('success'):
                return jsonify({
                    'success': False,
                    'error': 'Security verification failed. Please try again.'
                }), 403

        # Validate serial number format (SW-YYYY-NNNNNN)
        if not serial_number or not serial_number.startswith('SW-'):
            return jsonify({
                'success': False,
                'error': 'Invalid serial number format. Expected: SW-YYYY-NNNNNN'
            }), 400

        conn = get_db()
        cur = conn.cursor()

        # Query registry with comic and user details
        cur.execute("""
            SELECT
                cr.serial_number,
                cr.status,
                cr.registration_date,
                cr.reported_stolen_date,
                cr.recovery_date,
                c.title,
                c.issue,
                c.publisher,
                c.year,
                c.grade,
                c.photos,
                u.email
            FROM comic_registry cr
            JOIN collections c ON cr.comic_id = c.id
            JOIN users u ON cr.user_id = u.id
            WHERE cr.serial_number = %s
        """, (serial_number,))

        result = cur.fetchone()
        cur.close()
        conn.close()

        if not result:
            return jsonify({
                'success': False,
                'error': 'Serial number not found'
            }), 404

        # Parse result
        (serial, status, reg_date, stolen_date, recovery_date,
         title, issue, publisher, pub_year, grade, photos,
         email) = result

        # Parse photos JSON
        import json
        photos_data = json.loads(photos) if isinstance(photos, str) else photos
        cover_url = photos_data.get('front') if photos_data else None

        # Build response with privacy protections
        response = {
            'success': True,
            'serial_number': serial,
            'status': status,
            'registration_date': reg_date.isoformat() if reg_date else None,
            'comic': {
                'title': title,
                'issue_number': issue,
                'publisher': publisher,
                'publication_year': pub_year,
                'grade': grade,
                'cover_url': cover_url,
                'watermarked_url': f'/api/verify/watermark/{serial_number}' if cover_url else None
            },
            'owner': {
                'display_name': hash_email(email) if email else "Anonymous"
            }
        }

        # Add theft details if reported stolen
        if status == 'reported_stolen' and stolen_date:
            response['stolen_date'] = stolen_date.isoformat()

        # Add recovery details if recovered
        if status == 'recovered' and recovery_date:
            response['recovery_date'] = recovery_date.isoformat()

        return jsonify(response)

    except Exception as e:
        print(f"Error in lookup_serial: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@verify_bp.route('/watermark/<serial_number>', methods=['GET'])
def get_watermarked_image(serial_number):
    """
    Return watermarked cover image for a serial number
    """
    try:
        if not PIL_Image or not PIL_ImageDraw:
            return jsonify({
                'success': False,
                'error': 'Image processing not available'
            }), 503

        conn = get_db()
        cur = conn.cursor()

        # Get cover photo URL
        cur.execute("""
            SELECT c.photos
            FROM comic_registry cr
            JOIN collections c ON cr.comic_id = c.id
            WHERE cr.serial_number = %s
        """, (serial_number,))

        result = cur.fetchone()
        cur.close()
        conn.close()

        if not result:
            return jsonify({'success': False, 'error': 'Serial number not found'}), 404

        # Parse photos
        import json
        photos_data = json.loads(result[0]) if isinstance(result[0], str) else result[0]
        cover_url = photos_data.get('front') if photos_data else None

        if not cover_url:
            return jsonify({'success': False, 'error': 'No cover image available'}), 404

        # Generate watermarked image
        watermarked_img = watermark_image(cover_url, serial_number)

        # Convert to bytes
        img_io = io.BytesIO()
        watermarked_img.save(img_io, 'JPEG', quality=85)
        img_io.seek(0)

        return send_file(img_io, mimetype='image/jpeg')

    except Exception as e:
        print(f"Error in get_watermarked_image: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Failed to generate watermarked image'
        }), 500
