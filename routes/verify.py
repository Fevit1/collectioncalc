"""
Verify Blueprint - Public serial number lookup for theft protection
Routes: /api/verify/lookup/:serial_number, /api/verify/watermark/:serial_number,
        /api/verify/report-sighting
"""
import os
import io
import json
import requests as http_requests
import psycopg2
import resend
from flask import Blueprint, jsonify, request, send_file
from datetime import datetime, timedelta
from auth import verify_jwt

TURNSTILE_SECRET = os.environ.get('TURNSTILE_SECRET_KEY', '')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'noreply@slabworthy.com')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://slabworthy.com')

# Initialize Resend for sighting alert emails
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Rate limits for sighting reports
SIGHTING_RATE_PER_SERIAL = 3    # max reports per serial per 24h (prevent owner harassment)
SIGHTING_RATE_PER_IP = 20       # max reports per IP per 24h (prevent bot abuse)
SIGHTING_AUTO_BLOCK_IP = 100    # if an IP hits this in 24h, auto-block future reports

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
                'error': 'Invalid serial number format. Expected: SW-YYYY-XXXXXX'
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


def _verify_turnstile(token, remote_ip):
    """Verify Cloudflare Turnstile token. Returns True if valid."""
    if not TURNSTILE_SECRET:
        return True  # Skip in dev mode
    if not token:
        return False
    try:
        resp = http_requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': TURNSTILE_SECRET,
                'response': token,
                'remoteip': remote_ip,
            },
            timeout=5,
        )
        return resp.json().get('success', False)
    except Exception:
        return False


def _send_sighting_email(owner_email, serial_number, title, issue, status,
                         listing_url, reporter_email, message):
    """Send sighting alert email to the comic's registered owner via Resend."""
    reporter_display = reporter_email if reporter_email else "Anonymous"
    message_display = message if message else "(no message)"
    status_display = status.replace('_', ' ').title()

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #6366f1;">
            <span style="font-size: 24px;">&#128737;</span> Slab Guard Alert
        </h2>
        <p>Someone found a comic that may match your Slab Guard registration.</p>

        <div style="background: #f9fafb; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Registration:</strong> {serial_number}</p>
            <p style="margin: 4px 0;"><strong>Title:</strong> {title} #{issue}</p>
            <p style="margin: 4px 0;"><strong>Status:</strong> {status_display}</p>
        </div>

        <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <p style="margin: 4px 0;"><strong>Listing URL:</strong>
                <a href="{listing_url}" style="color: #6366f1;">{listing_url}</a>
            </p>
            <p style="margin: 4px 0;"><strong>Reporter's message:</strong> {message_display}</p>
            <p style="margin: 4px 0;"><strong>Reporter's email:</strong> {reporter_display}</p>
        </div>

        <h3 style="color: #1f2937;">What to do next</h3>
        <ul style="color: #4b5563; line-height: 1.8;">
            <li>Review the listing to see if it's your comic</li>
            <li>If you believe it's stolen, contact the marketplace directly</li>
            <li>You can update your comic's status at
                <a href="{FRONTEND_URL}" style="color: #6366f1;">slabworthy.com</a>
            </li>
        </ul>

        <p style="color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #e5e7eb; padding-top: 16px;">
            This alert was sent by Slab Guard &mdash; Slab Worthy's theft recovery system.<br>
            You received this because you registered {serial_number} with Slab Guard.
        </p>
    </div>
    """

    if not RESEND_API_KEY:
        print(f"[DEV MODE] Sighting alert for {owner_email}: {listing_url}")
        return True

    try:
        resend.Emails.send({
            "from": f"Slab Guard <{RESEND_FROM_EMAIL}>",
            "to": [owner_email],
            "subject": f"Slab Guard Alert — Someone spotted your comic {serial_number}",
            "html": html_body,
        })
        return True
    except Exception as e:
        print(f"Failed to send sighting email: {e}")
        return False


@verify_bp.route('/report-sighting', methods=['POST'])
def report_sighting():
    """
    Report a sighting of a registered comic (e.g. on eBay).
    Sends an alert email to the registered owner without exposing their email.

    POST JSON body:
        serial_number   (required) - e.g. "SW-2026-000014"
        listing_url     (required) - marketplace listing URL
        reporter_email  (optional) - so the owner can respond
        message         (optional) - short note from the reporter
        turnstile_token (required) - Cloudflare Turnstile verification

    Rate limit: max 3 reports per serial number per 24 hours.
    No authentication required — anyone can report.
    """
    try:
        body = request.get_json(silent=True) or {}
        serial_number = (body.get('serial_number') or '').strip().upper()
        listing_url = (body.get('listing_url') or '').strip()
        reporter_email = (body.get('reporter_email') or '').strip() or None
        message = (body.get('message') or '').strip() or None
        turnstile_token = body.get('turnstile_token', '')

        # --- Validation ---
        if not serial_number or not serial_number.startswith('SW-'):
            return jsonify({
                'success': False,
                'error': 'Invalid serial number format.'
            }), 400

        if not listing_url or not listing_url.startswith('http'):
            return jsonify({
                'success': False,
                'error': 'A valid listing URL is required.'
            }), 400

        # Authentication: accept either Turnstile token OR Bearer auth token
        # (Chrome extension users are already authenticated, no Turnstile needed)
        is_authenticated = False
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            jwt_token = auth_header.split(' ', 1)[1]
            payload = verify_jwt(jwt_token)
            if payload and payload.get('user_id'):
                is_authenticated = True

        if not is_authenticated and not _verify_turnstile(turnstile_token, request.remote_addr):
            return jsonify({
                'success': False,
                'error': 'Security verification failed. Please try again.'
            }), 403

        # Sanitize inputs
        if message and len(message) > 1000:
            message = message[:1000]
        if reporter_email and len(reporter_email) > 255:
            reporter_email = reporter_email[:255]
        if len(listing_url) > 2000:
            return jsonify({
                'success': False,
                'error': 'Listing URL is too long.'
            }), 400

        conn = get_db()
        cur = conn.cursor()
        reporter_ip = request.remote_addr

        # --- Check if IP is blocked ---
        cur.execute("""
            SELECT id FROM blocked_reporters
            WHERE ip_address = %s
              AND (expires_at IS NULL OR expires_at > NOW())
        """, (reporter_ip,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Reporting is temporarily unavailable. Please try again later.'
            }), 429

        # --- Rate limit: per serial (prevent owner harassment) ---
        cur.execute("""
            SELECT COUNT(*) FROM sighting_reports
            WHERE serial_number = %s
              AND created_at > NOW() - INTERVAL '24 hours'
        """, (serial_number,))
        serial_count = cur.fetchone()[0]

        if serial_count >= SIGHTING_RATE_PER_SERIAL:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'This comic has already been reported recently. Please try again later.'
            }), 429

        # --- Rate limit: per IP (prevent bot abuse) ---
        cur.execute("""
            SELECT COUNT(*) FROM sighting_reports
            WHERE reporter_ip = %s
              AND created_at > NOW() - INTERVAL '24 hours'
        """, (reporter_ip,))
        ip_count = cur.fetchone()[0]

        if ip_count >= SIGHTING_RATE_PER_IP:
            # Auto-block if they've hit the hard ceiling
            if ip_count >= SIGHTING_AUTO_BLOCK_IP:
                cur.execute("""
                    INSERT INTO blocked_reporters (ip_address, reason, blocked_by)
                    VALUES (%s, 'auto: exceeded 100 reports in 24h', 'system')
                    ON CONFLICT (ip_address) DO NOTHING
                """, (reporter_ip,))
                conn.commit()
                print(f"[SIGHTING] Auto-blocked IP {reporter_ip} — {ip_count} reports in 24h")
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'You have submitted too many reports today. Please try again tomorrow.'
            }), 429

        # --- Look up the registration + owner email ---
        cur.execute("""
            SELECT
                cr.serial_number,
                cr.status,
                c.title,
                c.issue,
                u.email
            FROM comic_registry cr
            JOIN collections c ON cr.comic_id = c.id
            JOIN users u ON cr.user_id = u.id
            WHERE cr.serial_number = %s
        """, (serial_number,))

        result = cur.fetchone()
        if not result:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Serial number not found in the registry.'
            }), 404

        _, status, title, issue, owner_email = result

        # --- Store the sighting report ---
        cur.execute("""
            INSERT INTO sighting_reports
                (serial_number, listing_url, reporter_email, message, reporter_ip, owner_notified)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            serial_number,
            listing_url,
            reporter_email,
            message,
            reporter_ip,
            False,
        ))
        report_id = cur.fetchone()[0]

        # --- Send email to owner ---
        email_sent = _send_sighting_email(
            owner_email=owner_email,
            serial_number=serial_number,
            title=title,
            issue=issue,
            status=status,
            listing_url=listing_url,
            reporter_email=reporter_email,
            message=message,
        )

        # Update owner_notified flag
        if email_sent:
            cur.execute("""
                UPDATE sighting_reports SET owner_notified = TRUE WHERE id = %s
            """, (report_id,))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'The owner has been notified. Thank you for helping protect collectors.',
            'report_id': report_id,
            'owner_notified': email_sent,
        })

    except Exception as e:
        print(f"Error in report_sighting: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Failed to submit sighting report. Please try again.'
        }), 500
