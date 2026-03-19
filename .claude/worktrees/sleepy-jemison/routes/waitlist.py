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
    <div style="font-family: Arial, Helvetica, sans-serif; max-width: 600px; margin: 0 auto; background: #0a0a12; border-radius: 12px; overflow: hidden;">
      <div style="background: linear-gradient(135deg, #1e1b4b 0%, #0a0a12 50%, #1e1b4b 100%); padding: 40px 30px 30px; text-align: center; position: relative;">
        <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: radial-gradient(circle, rgba(99,102,241,0.08) 1px, transparent 1px); background-size: 12px 12px;"></div>
        <div style="position: relative;">
          <h1 style="font-family: Arial, Helvetica, sans-serif; font-size: 36px; font-weight: 900; color: #facc15; margin: 0; letter-spacing: 2px; text-shadow: 0 0 20px rgba(250,204,21,0.3);">SLAB WORTHY&trade;</h1>
          <p style="color: #a78bfa; font-size: 13px; margin: 6px 0 0; letter-spacing: 3px; text-transform: uppercase;">AI-Powered Comic Grading</p>
        </div>
        <div style="width: 60px; height: 3px; background: linear-gradient(90deg, #6366f1, #facc15); margin: 20px auto 0; border-radius: 2px;"></div>
      </div>
      <div style="padding: 32px 30px;">
        <h2 style="color: #ffffff; font-size: 24px; font-weight: 800; margin: 0 0 8px; text-align: center;">You're In. Almost.</h2>
        <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; text-align: center; margin: 0 0 28px;">One click confirms your spot on the early access list. You'll be the first to know when we launch &mdash; and the first to try what we've been building.</p>
        <div style="text-align: center; margin: 0 0 32px;">
          <a href="{verify_url}" style="background: linear-gradient(135deg, #facc15, #f59e0b); color: #0a0a12; padding: 16px 44px; text-decoration: none; border-radius: 8px; font-size: 17px; font-weight: 800; display: inline-block; letter-spacing: 0.5px; box-shadow: 0 4px 20px rgba(250,204,21,0.25);">CONFIRM MY SPOT &rarr;</a>
        </div>
        <div style="width: 100%; height: 1px; background: linear-gradient(90deg, transparent, #2d2b55, transparent); margin: 4px 0 28px;"></div>
        <p style="color: #a78bfa; font-size: 11px; letter-spacing: 3px; text-transform: uppercase; font-weight: 700; margin: 0 0 16px; text-align: center;">What's Coming</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 0 0 24px;">
          <tr>
            <td width="50%" style="padding: 0 6px 12px 0; vertical-align: top;">
              <div style="background: linear-gradient(135deg, #1a1744, #1e1b4b); border: 1px solid rgba(99,102,241,0.15); border-radius: 10px; padding: 18px 16px;">
                <div style="font-size: 24px; margin-bottom: 8px;">&#x1F4F7;</div>
                <div style="color: #facc15; font-size: 14px; font-weight: 700; margin-bottom: 4px;">AI Grading</div>
                <div style="color: #94a3b8; font-size: 12px; line-height: 1.5;">4 photos. Instant grade estimate with defect analysis.</div>
              </div>
            </td>
            <td width="50%" style="padding: 0 0 12px 6px; vertical-align: top;">
              <div style="background: linear-gradient(135deg, #1a1744, #1e1b4b); border: 1px solid rgba(99,102,241,0.15); border-radius: 10px; padding: 18px 16px;">
                <div style="font-size: 24px; margin-bottom: 8px;">&#x1F6E1;</div>
                <div style="color: #facc15; font-size: 14px; font-weight: 700; margin-bottom: 4px;">Slab Guard&trade;</div>
                <div style="color: #94a3b8; font-size: 12px; line-height: 1.5;">Fingerprint your comics. Prove ownership. Deter theft.</div>
              </div>
            </td>
          </tr>
          <tr>
            <td width="50%" style="padding: 0 6px 0 0; vertical-align: top;">
              <div style="background: linear-gradient(135deg, #1a1744, #1e1b4b); border: 1px solid rgba(99,102,241,0.15); border-radius: 10px; padding: 18px 16px;">
                <div style="font-size: 24px; margin-bottom: 8px;">&#x1F4C8;</div>
                <div style="color: #facc15; font-size: 14px; font-weight: 700; margin-bottom: 4px;">Sell Now Alerts</div>
                <div style="color: #94a3b8; font-size: 12px; line-height: 1.5;">Know when to sell &mdash; and list directly through our auction partners.</div>
              </div>
            </td>
            <td width="50%" style="padding: 0 0 0 6px; vertical-align: top;">
              <div style="background: linear-gradient(135deg, #1a1744, #1e1b4b); border: 1px solid rgba(99,102,241,0.15); border-radius: 10px; padding: 18px 16px;">
                <div style="font-size: 24px; margin-bottom: 8px;">&#x1F4B0;</div>
                <div style="color: #facc15; font-size: 14px; font-weight: 700; margin-bottom: 4px;">Live Valuations</div>
                <div style="color: #94a3b8; font-size: 12px; line-height: 1.5;">AI-powered fair market values updated daily for every book you own.</div>
              </div>
            </td>
          </tr>
        </table>
        <div style="background: rgba(99,102,241,0.06); border: 1px solid rgba(99,102,241,0.12); border-radius: 8px; padding: 16px 20px; text-align: center; margin: 0 0 4px;">
          <p style="color: #c4b5fd; font-size: 13px; margin: 0; line-height: 1.6;">&#x26A1; Built by a collector, for collectors. Three patent-pending technologies. Launching Summer 2026.</p>
        </div>
      </div>
      <div style="background: #08080f; padding: 24px 30px; text-align: center; border-top: 1px solid #1e1b4b;">
        <p style="color: #475569; font-size: 12px; margin: 0 0 6px; line-height: 1.5;">You'll only hear from us when it matters. No spam, ever.</p>
        <p style="color: #334155; font-size: 11px; margin: 0;">&copy; 2026 Slab Worthy&trade; &bull; Patent Pending &bull; San Jose, CA</p>
      </div>
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
            "SELECT id, verified, interests FROM waitlist WHERE verification_token = %s",
            (token,)
        )
        row = cur.fetchone()

        if not row:
            return redirect(f"{FRONTEND_URL}/waitlist-confirmed.html?status=invalid")

        if row['verified']:
            return redirect(f"{FRONTEND_URL}/waitlist-confirmed.html?status=already")

        cur.execute(
            """UPDATE waitlist
               SET verified = TRUE, verified_at = NOW(), verification_token = NULL
               WHERE id = %s""",
            (row['id'],)
        )
        conn.commit()

        # Pass interests to confirmation page for personalization
        interests = row.get('interests') or []
        interests_param = ','.join(interests) if interests else ''
        return redirect(f"{FRONTEND_URL}/waitlist-confirmed.html?status=confirmed&interests={interests_param}")

    except Exception as e:
        print(f"[Waitlist] Verify error: {e}")
        return redirect(f"{FRONTEND_URL}/waitlist-confirmed.html?status=error")
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
