"""
Contact Form Blueprint - /api/contact
Receives contact form submissions, validates with Turnstile, sends via Resend.

Session 61: Created for contact.html form
"""
import os
import time
import requests
from flask import Blueprint, jsonify, request

import resend

# Create blueprint
contact_bp = Blueprint('contact', __name__, url_prefix='/api')

# Config
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'noreply@slabworthy.com')
SUPPORT_EMAIL = 'support@slabworthy.com'
TURNSTILE_SECRET = os.environ.get('TURNSTILE_SECRET_KEY', '')

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Simple in-memory rate limit: max 5 submissions per IP per hour
_contact_rate = {}  # ip -> (count, window_start)
CONTACT_RATE_MAX = 5
CONTACT_RATE_WINDOW = 3600  # 1 hour

VALID_TOPICS = {
    'grading': 'Grading Questions',
    'slab-guard': 'Slab Guard',
    'account': 'Account & Billing',
    'bug': 'Bug Report',
    'other': 'Other',
}


def _verify_turnstile(token, remote_ip):
    """Verify Cloudflare Turnstile token."""
    if not TURNSTILE_SECRET:
        return True  # Skip if not configured

    try:
        resp = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': TURNSTILE_SECRET,
                'response': token,
                'remoteip': remote_ip
            },
            timeout=5
        )
        result = resp.json()
        return result.get('success', False)
    except Exception as e:
        print(f"[Contact] Turnstile verify error: {e}")
        return False


def _check_rate_limit(ip):
    """Returns True if request is allowed, False if rate limited."""
    now = time.time()

    if ip in _contact_rate:
        count, window_start = _contact_rate[ip]
        if now - window_start > CONTACT_RATE_WINDOW:
            _contact_rate[ip] = (1, now)
            return True
        elif count >= CONTACT_RATE_MAX:
            return False
        else:
            _contact_rate[ip] = (count + 1, window_start)
            return True
    else:
        _contact_rate[ip] = (1, now)
        return True


@contact_bp.route('/contact', methods=['POST'])
def submit_contact():
    """
    Handle contact form submission.

    Request body:
        name: sender name
        email: sender email
        topic: one of grading, slab-guard, account, bug, other
        subject: message subject
        message: message body
        turnstile_token: Cloudflare Turnstile token

    Returns:
        JSON with success status
    """
    data = request.get_json() or {}

    # Extract fields
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    topic = (data.get('topic') or '').strip()
    subject = (data.get('subject') or '').strip()
    message = (data.get('message') or '').strip()
    turnstile_token = data.get('turnstile_token', '')

    # Validate required fields
    if not all([name, email, topic, subject, message]):
        return jsonify({
            'success': False,
            'error': 'All fields are required.'
        }), 400

    # Validate email format (basic)
    if '@' not in email or '.' not in email:
        return jsonify({
            'success': False,
            'error': 'Please enter a valid email address.'
        }), 400

    # Validate topic
    if topic not in VALID_TOPICS:
        return jsonify({
            'success': False,
            'error': 'Please select a valid topic.'
        }), 400

    # Rate limit by IP
    remote_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    if not _check_rate_limit(remote_ip):
        return jsonify({
            'success': False,
            'error': 'Too many messages. Please try again later.'
        }), 429

    # Verify Turnstile
    if TURNSTILE_SECRET:
        if not turnstile_token:
            return jsonify({
                'success': False,
                'error': 'Please complete the verification check.'
            }), 400

        if not _verify_turnstile(turnstile_token, remote_ip):
            return jsonify({
                'success': False,
                'error': 'Verification failed. Please refresh and try again.'
            }), 400

    # Build email
    topic_label = VALID_TOPICS.get(topic, topic)
    email_subject = f"[{topic_label}] {subject}"

    email_body = f"""New contact form submission from slabworthy.com

From: {name} <{email}>
Topic: {topic_label}
Subject: {subject}

Message:
{message}

---
IP: {remote_ip}
"""

    # Send via Resend
    if not RESEND_API_KEY:
        print(f"[Contact] RESEND_API_KEY not set. Would have sent:")
        print(f"  To: {SUPPORT_EMAIL}")
        print(f"  Subject: {email_subject}")
        print(f"  From: {name} <{email}>")
        return jsonify({'success': True})

    try:
        resend.Emails.send({
            "from": f"Slab Worthy Contact <{RESEND_FROM_EMAIL}>",
            "to": SUPPORT_EMAIL,
            "reply_to": email,
            "subject": email_subject,
            "text": email_body
        })

        print(f"[Contact] Message sent: [{topic_label}] {subject} from {email}")
        return jsonify({'success': True})

    except Exception as e:
        print(f"[Contact] Send error: {e}")
        return jsonify({
            'success': False,
            'error': 'Could not send message. Please try emailing us directly at support@slabworthy.com.'
        }), 500
