"""
Waitlist Blueprint - /api/waitlist
Pre-launch email signup with verification and interest tracking.

Session 65: Created for landing page waitlist capture.
"""
import os
import re
import time
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Blueprint, jsonify, request, redirect

import resend

# Create blueprint
waitlist_bp = Blueprint('waitlist', __name__, url_prefix='/api')

# Config
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'noreply@slabworthy.com')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://slabworthy.com')
API_BASE_URL = os.environ.get('API_BASE_URL', 'https://collectioncalc-docker.onrender.com')

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Seed offset: 6 beta testers + Mike = 7
WAITLIST_SEED_COUNT = 7

# Valid interest options
VALID_INTERESTS = {'grading', 'slab_guard', 'sell_alerts', 'collection'}

# Rate limiting: 3 per IP per hour
_waitlist_rate = {}
RATE_MAX = 3
RATE_WINDOW = 3600


def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not set")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


def _check_rate_limit(ip):
    """Returns True if request is allowed."""
    now = time.time()
    if ip in _waitlist_rate:
        count, window_start = _waitlist_rate[ip]
        if now - window_start > RATE_WINDOW:
            _waitlist_rate[ip] = (1, now)
            return True
        elif count >= RATE_MAX:
            return False
        else:
            _waitlist_rate[ip] = (count + 1, window_start)
            return True
    else:
        _waitlist_rate[ip] = (1, now)
        return True


def _validate_email(email):
    """Basic email format validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def _send_waitlist_confirmation(email, token):
    """Send the waitlist confirmation email."""
    verify_url = f"{API_BASE_URL}/api/waitlist/verify?token={token}"

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a0a12; color: #e2e8f0; padding: 40px 30px; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="font-family: Arial, sans-serif; font-size: 28px; color: #facc15; margin: 0;">SLAB WORTHY&trade;</h1>
            <p style="color: #a78bfa; font-size: 14px; margin: 4px 0 0;">AI for Comic Collectors</p>
        </div>

        <h2 style="color: #e2e8f0; font-size: 20px; margin-bottom: 16px;">You're one click away from the list.</h2>

        <p style="color: #94a3b8; font-size: 15px; line-height: 1.6;">
            Thanks for your interest in Slab Worthy! We're building something new for comic collectors:
        </p>

        <div style="background: #1e1b4b; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <p style="color: #c4b5fd; font-size: 14px; margin: 0 0 10px;"><strong style="color: #facc15;">AI Grading</strong> &mdash; Snap 4 photos, get an instant grade estimate with defect analysis</p>
            <p style="color: #c4b5fd; font-size: 14px; margin: 0 0 10px;"><strong style="color: #facc15;">Slab Guard&trade;</strong> &mdash; Fingerprint your comics for theft protection and authentication</p>
            <p style="color: #c4b5fd; font-size: 14px; margin: 0 0 10px;"><strong style="color: #facc15;">Sell Now Alerts</strong> &mdash; Get notified when the market says it's time to sell</p>
            <p style="color: #c4b5fd; font-size: 14px; margin: 0;"><strong style="color: #facc15;">Collection Tracking</strong> &mdash; Know exactly what your collection is worth, updated daily</p>
        </div>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{verify_url}"
               style="background: linear-gradient(135deg, #6366f1, #8b5cf6);
                      color: white;
                      padding: 14px 36px;
                      text-decoration: none;
                      border-radius: 8px;
                      font-size: 16px;
                      font-weight: bold;
                      display: inline-block;">
                Confirm My Spot
            </a>
        </p>

        <p style="color: #64748b; font-size: 13px; text-align: center;">
            Or copy this link:<br>
            <a href="{verify_url}" style="color: #818cf8; word-break: break-all;">{verify_url}</a>
        </p>

        <hr style="border: none; border-top: 1px solid #1e1b4b; margin: 30px 0;">

        <p style="color: #475569; font-size: 12px; text-align: center;">
            You'll be among the first to know when we launch. No spam, ever.<br>
            &copy; 2026 Slab Worthy&trade; &mdash; Patent Pending
        </p>
    </div>
    """

    if not RESEND_API_KEY:
        print(f"[DEV MODE] Waitlist confirmation for {email}: {verify_url}")
        return True

    try:
        resend.Emails.send({
            "from": f"Slab Worthy <{RESEND_FROM_EMAIL}>",
            "to": [email],
            "subject": "You're almost on the list \u2014 confirm your spot",
            "html": html_content
        })
        print(f"[Waitlist] Confirmation sent to {email}")
        return True
    except Exception as e:
        print(f"[Waitlist] Email send error: {e}")
        return False


# ─── ROUTES ───────────────────────────────────────────────

@waitlist_bp.route('/waitlist', methods=['POST'])
def subscribe():
    """
    Add email to waitlist and send confirmation.

    Request body:
        email: email address (required)
        interests: list of strings from: grading, slab_guard, sell_alerts, collection (optional)

    Returns:
        JSON with success status
    """
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    interests = data.get('interests', [])

    # Validate email
    if not email:
        return jsonify({'success': False, 'error': 'Email is required.'}), 400

    if not _validate_email(email):
        return jsonify({'success': False, 'error': 'Please enter a valid email address.'}), 400

    # Validate interests (filter to valid options)
    if isinstance(interests, list):
        interests = [i for i in interests if i in VALID_INTERESTS]
    else:
        interests = []

    # Rate limit
    remote_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    if not _check_rate_limit(remote_ip):
        return jsonify({'success': False, 'error': 'Too many requests. Please try again later.'}), 429

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check if email already exists
        cur.execute("SELECT id, verified FROM waitlist WHERE email = %s", (email,))
        existing = cur.fetchone()

        if existing:
            if existing['verified']:
                return jsonify({
                    'success': True,
                    'message': "You're already on the list! We'll let you know when we launch."
                })
            else:
                # Resend verification — generate new token
                token = str(uuid.uuid4())
                cur.execute(
                    "UPDATE waitlist SET verification_token = %s, interests = %s WHERE email = %s",
                    (token, interests, email)
                )
                conn.commit()
                _send_waitlist_confirmation(email, token)
                return jsonify({
                    'success': True,
                    'message': "We sent another confirmation email. Check your inbox!"
                })

        # New signup
        token = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO waitlist (email, interests, verification_token, ip_address)
               VALUES (%s, %s, %s, %s)""",
            (email, interests, token, remote_ip)
        )
        conn.commit()

        # Send confirmation email
        _send_waitlist_confirmation(email, token)

        return jsonify({
            'success': True,
            'message': "Check your email to confirm your spot on the waitlist!"
        })

    except Exception as e:
        print(f"[Waitlist] Subscribe error: {e}")
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': 'Something went wrong. Please try again.'}), 500
    finally:
        if conn:
            conn.close()


@waitlist_bp.route('/waitlist/verify', methods=['GET'])
def verify():
    """
    Verify waitlist email via token from confirmation email.
    Redirects to landing page with confirmation parameter.
    """
    token = request.args.get('token', '').strip()

    if not token:
        return redirect(f"{FRONTEND_URL}/?waitlist=invalid")

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id, verified FROM waitlist WHERE verification_token = %s",
            (token,)
        )
        row = cur.fetchone()

        if not row:
            return redirect(f"{FRONTEND_URL}/?waitlist=invalid")

        if row['verified']:
            return redirect(f"{FRONTEND_URL}/?waitlist=already")

        cur.execute(
            """UPDATE waitlist
               SET verified = TRUE, verified_at = NOW(), verification_token = NULL
               WHERE id = %s""",
            (row['id'],)
        )
        conn.commit()

        return redirect(f"{FRONTEND_URL}/?waitlist=confirmed")

    except Exception as e:
        print(f"[Waitlist] Verify error: {e}")
        return redirect(f"{FRONTEND_URL}/?waitlist=error")
    finally:
        if conn:
            conn.close()


@waitlist_bp.route('/waitlist/count', methods=['GET'])
def count():
    """
    Public endpoint: returns verified waitlist count + seed offset.
    No authentication required.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM waitlist WHERE verified = TRUE")
        result = cur.fetchone()
        total = (result['cnt'] if result else 0) + WAITLIST_SEED_COUNT

        return jsonify({'count': total})
    except Exception as e:
        print(f"[Waitlist] Count error: {e}")
        return jsonify({'count': WAITLIST_SEED_COUNT})
    finally:
        if conn:
            conn.close()
