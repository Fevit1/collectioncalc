"""
Authentication module for CollectionCalc.
Handles user signup, login, email verification, password reset,
beta code validation, and admin approval workflow.

Uses:
    - bcrypt for password hashing
    - PyJWT for token generation
    - Resend for transactional emails
"""

import os
import logging
import secrets
import bcrypt
import jwt
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from functools import wraps
from flask import g, jsonify
import resend

logger = logging.getLogger(__name__)

# ============================================
# CONFIGURATION
# ============================================

_INSECURE_JWT_DEFAULT = 'change-me-in-production'
JWT_SECRET = os.environ.get('JWT_SECRET', '')
# Render sets RENDER=true in the runtime environment; use it as the production
# signal. (Local/dev has no RENDER var.)
_IS_PRODUCTION = bool(os.environ.get('RENDER'))

if not JWT_SECRET or JWT_SECRET == _INSECURE_JWT_DEFAULT:
    # ASCII-only messages (L-2026-015: non-ASCII crashes Windows cp1252 stdout;
    # this warning path runs on the local dev workstation).
    _jwt_msg = ("JWT_SECRET is unset or equals the known insecure default -- auth "
                "tokens would be signed with a public value and become forgeable")
    if _IS_PRODUCTION:
        # Fail loud: refuse to start rather than silently issue forgeable tokens.
        raise RuntimeError(
            f"FATAL: {_jwt_msg}. Refusing to start in production. Set a strong "
            "random JWT_SECRET on the Render service "
            "(e.g. `python -c \"import secrets; print(secrets.token_urlsafe(48))\"`)."
        )
    # Local/dev convenience: allow startup but warn loudly on every boot.
    print(f"WARNING: {_jwt_msg}. Using an insecure dev default -- DO NOT deploy like this.")
    JWT_SECRET = _INSECURE_JWT_DEFAULT

JWT_EXPIRY_DAYS = 30  # Token valid for 30 days
VERIFICATION_EXPIRY_HOURS = 24  # Email verification link valid for 24 hours
RESET_EXPIRY_HOURS = 24  # Password reset link valid for 24 hours

RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'noreply@slabworthy.com')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://slabworthy.com')

# Initialize Resend
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# ============================================
# DATABASE HELPERS
# ============================================

def get_db_connection():
    """Get database connection from environment."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

def get_user_by_email(email):
    """Find user by email address."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM users WHERE email = %s", (email.lower(),))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()

def get_user_by_id(user_id):
    """Find user by ID."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()

# ============================================
# PASSWORD HELPERS
# ============================================

def hash_password(password):
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

# ============================================
# JWT HELPERS
# ============================================

def generate_jwt(user_id, email, is_admin=False, is_approved=False):
    """Generate a JWT token for authenticated user."""
    payload = {
        'user_id': user_id,
        'email': email,
        'is_admin': is_admin,
        'is_approved': is_approved,
        'exp': datetime.utcnow() + timedelta(days=JWT_EXPIRY_DAYS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt(token):
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# ============================================
# BETA CODE FUNCTIONS
# ============================================

def validate_beta_code(code):
    """
    Validate a beta code.
    Returns: dict with success status and code info or error
    """
    if not code:
        return {'success': False, 'error': 'Beta code is required'}
    
    code = code.upper().strip()
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT * FROM beta_codes 
            WHERE code = %s AND is_active = TRUE
        """, (code,))
        
        beta_code = cur.fetchone()
        
        if not beta_code:
            return {'success': False, 'error': 'Invalid beta code'}
        
        if beta_code['uses_remaining'] <= 0:
            return {'success': False, 'error': 'This beta code has already been used'}
        
        if beta_code['expires_at'] and beta_code['expires_at'] < datetime.utcnow():
            return {'success': False, 'error': 'This beta code has expired'}

        result = {
            'success': True,
            'code': code,
        }

        # Batch 6: waitlist-invite codes carry the invited address in their note
        # (set by /api/admin/waitlist/invite as "Waitlist invite: <email>").
        # Surface ONLY the parsed invite email so the signup form can pre-fill +
        # lock the field instead of asking the invited user to retype the address
        # they already confirmed. We deliberately do NOT return the raw `note` —
        # this endpoint is unauthenticated, and notes can hold the invited email
        # or internal admin remarks that shouldn't be exposed. `email_verified`
        # is computed server-side so the "verified" indicator can't be spoofed.
        note = beta_code['note'] or ''
        _invite_prefix = 'Waitlist invite: '
        if note.startswith(_invite_prefix):
            invite_email = note[len(_invite_prefix):].strip().lower()
            if invite_email:
                result['invite_email'] = invite_email
                result['email_verified'] = _is_waitlist_confirmed(invite_email)

        return result
    finally:
        cur.close()
        conn.close()

def use_beta_code(code, user_id):
    """
    Mark a beta code as used by a user.
    Decrements uses_remaining.
    """
    code = code.upper().strip()
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Decrement uses_remaining
        cur.execute("""
            UPDATE beta_codes 
            SET uses_remaining = uses_remaining - 1
            WHERE code = %s AND uses_remaining > 0
            RETURNING id
        """, (code,))
        
        result = cur.fetchone()
        
        if result:
            # Update user with the beta code used
            cur.execute("""
                UPDATE users 
                SET beta_code_used = %s
                WHERE id = %s
            """, (code, user_id))
            conn.commit()
            return True
        
        return False
    except Exception as e:
        conn.rollback()
        print(f"Error using beta code: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def create_beta_code(admin_id, note=None, uses_allowed=1, expires_days=None):
    """
    Create a new beta code (admin only).
    Returns the generated code.
    """
    # Generate a unique code
    code = f"BETA-{secrets.token_hex(3).upper()}"
    
    expires_at = None
    if expires_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO beta_codes (code, created_by, uses_allowed, uses_remaining, expires_at, note)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING code
        """, (code, admin_id, uses_allowed, uses_allowed, expires_at, note))
        
        conn.commit()
        return cur.fetchone()['code']
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def list_beta_codes(include_inactive=False):
    """Get all beta codes (admin only)."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if include_inactive:
            cur.execute("""
                SELECT bc.*, u.email as created_by_email
                FROM beta_codes bc
                LEFT JOIN users u ON bc.created_by = u.id
                ORDER BY bc.created_at DESC
            """)
        else:
            cur.execute("""
                SELECT bc.*, u.email as created_by_email
                FROM beta_codes bc
                LEFT JOIN users u ON bc.created_by = u.id
                WHERE bc.is_active = TRUE
                ORDER BY bc.created_at DESC
            """)
        
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

# ============================================
# USER APPROVAL FUNCTIONS
# ============================================

def approve_user(user_id, admin_id):
    """
    Approve a user (admin only).
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE users 
            SET is_approved = TRUE, 
                approved_at = NOW(),
                approved_by = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, email
        """, (admin_id, user_id))
        
        result = cur.fetchone()
        conn.commit()
        
        if result:
            # Send approval email
            send_approval_email(result['email'])
            return {'success': True, 'user_id': user_id, 'email': result['email']}
        
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        cur.close()
        conn.close()

def reject_user(user_id, admin_id, reason=None):
    """
    Reject/delete a user (admin only).
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Get user email first
        cur.execute("SELECT email FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        # Delete the user
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        
        # Optionally send rejection email
        if reason:
            send_rejection_email(user['email'], reason)
        
        return {'success': True, 'email': user['email']}
    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        cur.close()
        conn.close()

def get_pending_users():
    """Get list of users awaiting approval."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, email, created_at, email_verified, beta_code_used
            FROM users 
            WHERE is_approved = FALSE AND is_admin = FALSE
            ORDER BY created_at DESC
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def get_all_users(include_pending=True):
    """Get all users (admin only)."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if include_pending:
            cur.execute("""
                SELECT id, email, created_at, email_verified, is_approved, is_admin,
                       approved_at, beta_code_used, last_login, display_name
                FROM users
                ORDER BY created_at DESC
            """)
        else:
            cur.execute("""
                SELECT id, email, created_at, email_verified, is_approved, is_admin,
                       approved_at, beta_code_used, last_login, display_name
                FROM users
                WHERE is_approved = TRUE
                ORDER BY created_at DESC
            """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def is_user_admin(user_id):
    """Check if user is an admin."""
    user = get_user_by_id(user_id)
    return user and user.get('is_admin', False)

def is_user_approved(user_id):
    """Check if user is approved."""
    user = get_user_by_id(user_id)
    return user and user.get('is_approved', False)

# ============================================
# WAITLIST LINKAGE / EMAIL DIAGNOSTICS
# ============================================

def _is_waitlist_confirmed(email):
    """Return True if `email` has a CONFIRMED waitlist entry.

    'Confirmed' (waitlist.verified = TRUE) means someone clicked the confirm
    link that was sent to that inbox, so we don't make them confirm the SAME
    address again at signup (Batch 6 task 1). `email` must already be in the
    normalized form signup uses (lower().strip()); the waitlist stores emails
    the same way.

    SECURITY NOTE: this trusts a PAST click that proves "someone controlled
    this inbox once," not "this signer controls it now." Acceptable during the
    beta-code-gated beta (the beta wall + password-reset recovery bound the
    blast radius of email-squatting). REVISIT before the public soft launch
    when the beta wall comes down — consider a signed continuity token minted
    by the waitlist-confirm click instead of a bare email match.

    Fails CLOSED (returns False) on any DB error so a lookup problem can never
    silently grant verification.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT verified FROM waitlist WHERE email = %s", (email,))
            row = cur.fetchone()
            return bool(row and row['verified'])
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.warning(f"waitlist confirm-state lookup failed at signup: {e}")
        return False


_email_failures_table_ready = False  # one-time-per-process DDL guard


def _record_email_failure(email, kind, error):
    """Persist a transactional-email send failure so it's diagnosable beyond
    ephemeral stdout (Batch 6 task 3). Lazily creates its table once per
    process (so we don't take a catalog lock on every failure under load);
    never raises into the caller.
    """
    global _email_failures_table_ready
    logger.error(f"Email send failed kind={kind} to={email}: {error}")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            if not _email_failures_table_ready:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS email_send_failures (
                        id SERIAL PRIMARY KEY,
                        email TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        error TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                _email_failures_table_ready = True
            cur.execute(
                "INSERT INTO email_send_failures (email, kind, error) VALUES (%s, %s, %s)",
                (email, kind, str(error)[:1000])
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        logger.error(f"Failed to persist email-failure record: {e}")


# ============================================
# EMAIL HELPERS
# ============================================

def send_verification_email(email, token):
    """Send email verification link."""
    if not RESEND_API_KEY:
        print(f"[DEV MODE] Verification email for {email}: {FRONTEND_URL}/login.html?token={token}")
        return True
    
    # Use query param instead of path for Cloudflare Pages SPA
    verify_url = f"{FRONTEND_URL}/login.html?token={token}"
    
    try:
        resend.Emails.send({
            "from": f"Slab Worthy <{RESEND_FROM_EMAIL}>",
            "to": [email],
            "subject": "Verify your Slab Worthy account",
            "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #6366f1;">Welcome to Slab Worthy!</h2>
                    <p>Thanks for signing up. Please verify your email address by clicking the button below:</p>
                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{verify_url}" 
                           style="background: linear-gradient(135deg, #6366f1, #8b5cf6); 
                                  color: white; 
                                  padding: 12px 30px; 
                                  text-decoration: none; 
                                  border-radius: 6px;
                                  display: inline-block;">
                            Verify Email
                        </a>
                    </p>
                    <p style="color: #666; font-size: 14px;">
                        Or copy this link: <br>
                        <a href="{verify_url}" style="color: #6366f1;">{verify_url}</a>
                    </p>
                    <p style="color: #999; font-size: 12px; margin-top: 30px;">
                        This link expires in 24 hours. If you didn't create an account, you can ignore this email.
                    </p>
                </div>
            """
        })
        return True
    except Exception as e:
        _record_email_failure(email, 'verification', e)
        return False

def send_password_reset_email(email, token):
    """Send password reset link."""
    if not RESEND_API_KEY:
        print(f"[DEV MODE] Password reset for {email}: {FRONTEND_URL}/login.html?action=reset-password&token={token}")
        return True
    
    # Use query params instead of path for Cloudflare Pages SPA
    reset_url = f"{FRONTEND_URL}/login.html?action=reset-password&token={token}"
    
    try:
        resend.Emails.send({
            "from": f"Slab Worthy <{RESEND_FROM_EMAIL}>",
            "to": [email],
            "subject": "Reset your Slab Worthy password",
            "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #6366f1;">Reset Your Password</h2>
                    <p>We received a request to reset your password. Click the button below to choose a new one:</p>
                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}" 
                           style="background: linear-gradient(135deg, #6366f1, #8b5cf6); 
                                  color: white; 
                                  padding: 12px 30px; 
                                  text-decoration: none; 
                                  border-radius: 6px;
                                  display: inline-block;">
                            Reset Password
                        </a>
                    </p>
                    <p style="color: #666; font-size: 14px;">
                        Or copy this link: <br>
                        <a href="{reset_url}" style="color: #6366f1;">{reset_url}</a>
                    </p>
                    <p style="color: #999; font-size: 12px; margin-top: 30px;">
                        This link expires in 24 hours. If you didn't request a password reset, you can ignore this email.
                    </p>
                </div>
            """
        })
        return True
    except Exception as e:
        print(f"Failed to send password reset email: {e}")
        return False

def send_approval_email(email):
    """Send approval notification email."""
    if not RESEND_API_KEY:
        print(f"[DEV MODE] Approval email for {email}")
        return True
    
    try:
        resend.Emails.send({
            "from": f"Slab Worthy <{RESEND_FROM_EMAIL}>",
            "to": [email],
            "subject": "You're approved for Slab Worthy!",
            "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #6366f1;">You're In!</h2>
                    <p>Great news! Your Slab Worthy account has been approved.</p>
                    <p>You can now log in and start assessing your comics:</p>
                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{FRONTEND_URL}" 
                           style="background: linear-gradient(135deg, #6366f1, #8b5cf6); 
                                  color: white; 
                                  padding: 12px 30px; 
                                  text-decoration: none; 
                                  border-radius: 6px;
                                  display: inline-block;">
                            Go to Slab Worthy
                        </a>
                    </p>
                    <p style="color: #666; font-size: 14px;">
                        Thanks for being part of our beta program!
                    </p>
                </div>
            """
        })
        return True
    except Exception as e:
        print(f"Failed to send approval email: {e}")
        return False

def send_rejection_email(email, reason=None):
    """Send rejection notification email."""
    if not RESEND_API_KEY:
        print(f"[DEV MODE] Rejection email for {email}: {reason}")
        return True
    
    reason_text = f"<p style='color: #666;'>Reason: {reason}</p>" if reason else ""
    
    try:
        resend.Emails.send({
            "from": f"Slab Worthy <{RESEND_FROM_EMAIL}>",
            "to": [email],
            "subject": "Slab Worthy account update",
            "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #6366f1;">Account Update</h2>
                    <p>Unfortunately, we're unable to approve your Slab Worthy account at this time.</p>
                    {reason_text}
                    <p style="color: #666; font-size: 14px;">
                        If you have questions, please contact us at support@slabworthy.com.
                    </p>
                </div>
            """
        })
        return True
    except Exception as e:
        print(f"Failed to send rejection email: {e}")
        return False

# ============================================
# AUTH FUNCTIONS
# ============================================

def signup(email, password, beta_code=None, display_name=None, phone=None, marketing_consent=False):
    """
    Create a new user account.
    Requires valid beta code during beta period.
    Returns: dict with success status and user info or error
    """
    email = email.lower().strip()

    # Sanitize optional profile fields
    if display_name:
        display_name = display_name.strip()[:100]
    if phone:
        phone = phone.strip()[:20]
    
    # Validate email format (basic check)
    if not email or '@' not in email or '.' not in email:
        return {'success': False, 'error': 'Invalid email address'}
    
    # Validate password strength
    if len(password) < 8:
        return {'success': False, 'error': 'Password must be at least 8 characters'}
    
    # Validate beta code
    if beta_code:
        beta_result = validate_beta_code(beta_code)
        if not beta_result['success']:
            return beta_result
    
    # Check if user already exists
    existing = get_user_by_email(email)
    if existing:
        return {'success': False, 'error': 'An account with this email already exists'}
    
    # Batch 6 task 1: a person who already confirmed THIS email on the waitlist
    # has proven inbox control once — don't make them confirm the same address
    # again at signup. (See _is_waitlist_confirmed for the security caveat.)
    waitlist_confirmed = _is_waitlist_confirmed(email)

    # Generate verification token (unused / not stored when we pre-verify)
    verification_token = secrets.token_urlsafe(32)
    verification_expires = datetime.utcnow() + timedelta(hours=VERIFICATION_EXPIRY_HOURS)

    # Hash password and create user
    password_hash = hash_password(password)

    # Auto-approve users who sign up with a valid beta code OR who are already
    # confirmed on the waitlist (Batch 6 task 2: open approval for waitlist).
    auto_approve = bool(beta_code) or waitlist_confirmed

    # Confirmed-waitlist signups are created already-verified and carry no
    # pending verification token (there is nothing left to verify).
    email_verified = waitlist_confirmed
    stored_token = None if waitlist_confirmed else verification_token
    stored_expires = None if waitlist_confirmed else verification_expires

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (
                email, password_hash, email_verification_token,
                email_verification_expires, email_verified,
                is_approved, is_admin, beta_code_used,
                display_name, phone, marketing_consent
            )
            VALUES (%s, %s, %s, %s, %s, %s, FALSE, %s, %s, %s, %s)
            RETURNING id
        """, (email, password_hash, stored_token, stored_expires, email_verified,
              auto_approve,
              beta_code.upper().strip() if beta_code else None,
              display_name, phone, bool(marketing_consent)))

        user_id = cur.fetchone()['id']
        conn.commit()

        # Mark beta code as used
        if beta_code:
            use_beta_code(beta_code, user_id)

        # If this email is on the waitlist, mark as registered
        try:
            wl_conn = get_db_connection()
            wl_cur = wl_conn.cursor()
            wl_cur.execute("UPDATE waitlist SET registered = TRUE, registered_at = NOW() WHERE email = %s", (email,))
            wl_conn.commit()
            wl_cur.close()
            wl_conn.close()
        except Exception:
            pass  # Don't block signup if waitlist update fails

        # Batch 6 task 1: pre-verified (confirmed-waitlist) users skip the second
        # verification email entirely and are logged straight in.
        if waitlist_confirmed:
            token = generate_jwt(user_id, email, is_admin=False,
                                 is_approved=auto_approve)
            return {
                'success': True,
                'message': 'Welcome back! Your account is ready.',
                'user_id': user_id,
                'email': email,
                'token': token,
                'user': {
                    'id': user_id,
                    'email': email,
                    'email_verified': True,
                    'is_approved': auto_approve,
                    'is_admin': False
                },
                'requires_approval': not auto_approve
            }

        # Batch 6 task 3: check the send result instead of pretending it worked.
        # The account WAS created, so we still return success — but we tell the
        # client the email didn't go out so it can offer Resend / support
        # instead of a false "Check Your Email" screen.
        email_sent = send_verification_email(email, verification_token)
        if not email_sent:
            return {
                'success': True,
                'email_send_failed': True,
                'message': ("Account created, but we couldn't send your "
                            "verification email. Tap Resend, or contact "
                            "support@slabworthy.com if it keeps failing."),
                'user_id': user_id,
                'email': email,
                'requires_approval': not auto_approve
            }

        return {
            'success': True,
            'message': 'Account created! Please check your email to verify your account.',
            'user_id': user_id,
            'email': email,
            'requires_approval': not auto_approve
        }
    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        cur.close()
        conn.close()

def login(email, password):
    """
    Authenticate user and return JWT token.
    Checks for email verification and approval status.
    Returns: dict with success status and token or error
    """
    email = email.lower().strip()
    user = get_user_by_email(email)
    
    if not user:
        return {'success': False, 'error': 'Invalid email or password'}
    
    if not verify_password(password, user['password_hash']):
        return {'success': False, 'error': 'Invalid email or password'}
    
    # Check if email is verified
    if not user['email_verified']:
        return {
            'success': False,
            'error': 'Please verify your email address',
            'needs_verification': True
        }
    
    # Check if user is approved (admins are always approved)
    if not user.get('is_approved', False) and not user.get('is_admin', False):
        return {
            'success': False,
            'error': 'Your account is pending approval. You\'ll receive an email when approved.',
            'pending_approval': True
        }
    
    # Update last_login timestamp
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass  # Don't block login if update fails

    # Generate JWT with admin/approval info
    token = generate_jwt(
        user['id'],
        user['email'],
        is_admin=user.get('is_admin', False),
        is_approved=user.get('is_approved', False)
    )

    return {
        'success': True,
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'email_verified': user['email_verified'],
            'is_approved': user.get('is_approved', False),
            'is_admin': user.get('is_admin', False)
        }
    }

def verify_email(token):
    """
    Verify user's email address using token from email link.
    Returns: dict with success status and message or error
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Find user with this verification token
        cur.execute("""
            SELECT id, email, email_verified, email_verification_expires 
            FROM users 
            WHERE email_verification_token = %s
        """, (token,))
        
        user = cur.fetchone()
        
        if not user:
            return {'success': False, 'error': 'Invalid or expired verification link'}
        
        if user['email_verified']:
            return {'success': True, 'message': 'Email already verified'}
        
        # Check if token expired
        if user['email_verification_expires'] < datetime.utcnow():
            return {'success': False, 'error': 'Verification link has expired. Please request a new one.'}
        
        # Mark email as verified
        cur.execute("""
            UPDATE users 
            SET email_verified = TRUE, 
                email_verification_token = NULL,
                email_verification_expires = NULL,
                updated_at = NOW()
            WHERE id = %s
        """, (user['id'],))
        
        conn.commit()
        
        # Check if user needs approval
        cur.execute("SELECT is_approved, is_admin FROM users WHERE id = %s", (user['id'],))
        approval_status = cur.fetchone()
        
        if approval_status['is_approved'] or approval_status['is_admin']:
            # User is approved, generate JWT
            jwt_token = generate_jwt(user['id'], user['email'], 
                                     is_admin=approval_status['is_admin'],
                                     is_approved=approval_status['is_approved'])
            return {
                'success': True,
                'message': 'Email verified successfully!',
                'token': jwt_token,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'email_verified': True,
                    'is_approved': True
                }
            }
        else:
            # User needs approval
            return {
                'success': True,
                'message': 'Email verified! Your account is pending approval. You\'ll receive an email when approved.',
                'pending_approval': True,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'email_verified': True,
                    'is_approved': False
                }
            }
    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        cur.close()
        conn.close()

def resend_verification(email):
    """
    Resend verification email to user.
    Returns: dict with success status and message or error
    """
    email = email.lower().strip()
    user = get_user_by_email(email)
    
    if not user:
        # Don't reveal if email exists
        return {'success': True, 'message': 'If an account exists, a verification email has been sent.'}
    
    if user['email_verified']:
        return {'success': False, 'error': 'Email is already verified'}
    
    # Generate new verification token
    verification_token = secrets.token_urlsafe(32)
    verification_expires = datetime.utcnow() + timedelta(hours=VERIFICATION_EXPIRY_HOURS)
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE users 
            SET email_verification_token = %s,
                email_verification_expires = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (verification_token, verification_expires, user['id']))
        conn.commit()

        # Send verification email — surface a real failure instead of claiming
        # success (Batch 6 task 3). The failure is also persisted/logged inside
        # send_verification_email via _record_email_failure.
        if not send_verification_email(email, verification_token):
            return {'success': False, 'error': ("We couldn't send the verification "
                    "email right now. Please try again shortly, or contact "
                    "support@slabworthy.com.")}

        return {'success': True, 'message': 'Verification email sent. Please check your inbox.'}
    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        cur.close()
        conn.close()

def forgot_password(email):
    """
    Send password reset email.
    Returns: dict with success status and message
    """
    email = email.lower().strip()
    user = get_user_by_email(email)
    
    # Always return success to prevent email enumeration
    if not user:
        return {'success': True, 'message': 'If an account exists, a password reset email has been sent.'}
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=RESET_EXPIRY_HOURS)
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Invalidate any existing reset tokens
        cur.execute("""
            UPDATE password_resets SET used = TRUE
            WHERE user_id = %s AND used = FALSE
        """, (user['id'],))
        
        # Create new reset token
        cur.execute("""
            INSERT INTO password_resets (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """, (user['id'], reset_token, expires_at))
        
        conn.commit()
        
        # Send reset email
        send_password_reset_email(email, reset_token)
        
        return {'success': True, 'message': 'If an account exists, a password reset email has been sent.'}
    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        cur.close()
        conn.close()

def reset_password(token, new_password):
    """
    Reset user's password using token from email link.
    Returns: dict with success status and message or error
    """
    # Validate new password
    if len(new_password) < 8:
        return {'success': False, 'error': 'Password must be at least 8 characters'}
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Find valid reset token
        cur.execute("""
            SELECT pr.id, pr.user_id, pr.expires_at, u.email, u.is_admin, u.is_approved
            FROM password_resets pr
            JOIN users u ON u.id = pr.user_id
            WHERE pr.token = %s AND pr.used = FALSE
        """, (token,))
        
        reset = cur.fetchone()
        
        if not reset:
            return {'success': False, 'error': 'Invalid or expired reset link'}
        
        # Check if token expired
        if reset['expires_at'] < datetime.utcnow():
            return {'success': False, 'error': 'Reset link has expired. Please request a new one.'}
        
        # Hash new password
        password_hash = hash_password(new_password)
        
        # Update password
        cur.execute("""
            UPDATE users 
            SET password_hash = %s, updated_at = NOW()
            WHERE id = %s
        """, (password_hash, reset['user_id']))
        
        # Mark token as used
        cur.execute("""
            UPDATE password_resets SET used = TRUE
            WHERE id = %s
        """, (reset['id'],))
        
        conn.commit()
        
        # Generate JWT so user is logged in after reset
        jwt_token = generate_jwt(
            reset['user_id'], 
            reset['email'],
            is_admin=reset.get('is_admin', False),
            is_approved=reset.get('is_approved', False)
        )
        
        return {
            'success': True,
            'message': 'Password reset successfully!',
            'token': jwt_token,
            'user': {
                'id': reset['user_id'],
                'email': reset['email'],
                'email_verified': True,
                'is_approved': reset.get('is_approved', False),
                'is_admin': reset.get('is_admin', False)
            }
        }
    except Exception as e:
        conn.rollback()
        return {'success': False, 'error': str(e)}
    finally:
        cur.close()
        conn.close()

def get_current_user(token):
    """
    Get current user from JWT token.
    Returns: dict with success status and user info or error
    """
    payload = verify_jwt(token)
    if not payload:
        return {'success': False, 'error': 'Invalid or expired token'}
    
    user = get_user_by_id(payload['user_id'])
    if not user:
        return {'success': False, 'error': 'User not found'}
    
    return {
        'success': True,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'email_verified': user['email_verified'],
            'is_approved': user.get('is_approved', False),
            'is_admin': user.get('is_admin', False),
            'created_at': user['created_at'].isoformat() if user['created_at'] else None
        }
    }

# ============================================
# ADMIN AUTH DECORATOR HELPER
# ============================================

def require_admin(token):
    """
    Verify token and check if user is admin.
    Returns: (user_dict, error_message)
    """
    if not token:
        return None, 'Authentication required'
    
    payload = verify_jwt(token)
    if not payload:
        return None, 'Invalid or expired token'
    
    user = get_user_by_id(payload['user_id'])
    if not user:
        return None, 'User not found'
    
    if not user.get('is_admin', False):
        return None, 'Admin access required'
    
    return user, None


# ============================================
# FLASK DECORATORS (for route protection)
# ============================================

def require_auth(f):
    """
    Decorator to require authentication.
    Expects g.user_id to be set by middleware.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_id') or g.user_id is None:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_approved(f):
    """
    Decorator to require user to be approved.
    Expects g.user_id to be set by middleware.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_id') or g.user_id is None:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user = get_user_by_id(g.user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        if not user.get('is_approved', False) and not user.get('is_admin', False):
            return jsonify({'success': False, 'error': 'Account pending approval'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def require_admin_auth(f):
    """
    Decorator to require admin authentication.
    Expects g.user_id to be set by middleware.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_id') or g.user_id is None:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user = get_user_by_id(g.user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        if not user.get('is_admin', False):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        # Set admin_id in g for use in route functions
        g.admin_id = user['id']
        
        return f(*args, **kwargs)
    return decorated_function


# Blueprint decorators added v4.3.0
