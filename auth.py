"""
Authentication module for CollectionCalc.
Handles user signup, login, email verification, and password reset.

Uses:
    - bcrypt for password hashing
    - PyJWT for token generation
    - Resend for transactional emails
"""

import os
import secrets
import bcrypt
import jwt
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import resend

# ============================================
# CONFIGURATION
# ============================================

JWT_SECRET = os.environ.get('JWT_SECRET', 'change-me-in-production')
JWT_EXPIRY_DAYS = 30  # Token valid for 30 days
VERIFICATION_EXPIRY_HOURS = 24  # Email verification link valid for 24 hours
RESET_EXPIRY_HOURS = 1  # Password reset link valid for 1 hour

RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'noreply@collectioncalc.com')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://collectioncalc.com')

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

def generate_jwt(user_id, email):
    """Generate a JWT token for authenticated user."""
    payload = {
        'user_id': user_id,
        'email': email,
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
# EMAIL HELPERS
# ============================================

def send_verification_email(email, token):
    """Send email verification link."""
    if not RESEND_API_KEY:
        print(f"[DEV MODE] Verification email for {email}: {FRONTEND_URL}/verify?token={token}")
        return True
    
    verify_url = f"{FRONTEND_URL}/verify?token={token}"
    
    try:
        resend.Emails.send({
            "from": f"CollectionCalc <{RESEND_FROM_EMAIL}>",
            "to": [email],
            "subject": "Verify your CollectionCalc account",
            "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #6366f1;">Welcome to CollectionCalc!</h2>
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
        print(f"Failed to send verification email: {e}")
        return False

def send_password_reset_email(email, token):
    """Send password reset link."""
    if not RESEND_API_KEY:
        print(f"[DEV MODE] Password reset for {email}: {FRONTEND_URL}/reset-password?token={token}")
        return True
    
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    
    try:
        resend.Emails.send({
            "from": f"CollectionCalc <{RESEND_FROM_EMAIL}>",
            "to": [email],
            "subject": "Reset your CollectionCalc password",
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
                        This link expires in 1 hour. If you didn't request a password reset, you can ignore this email.
                    </p>
                </div>
            """
        })
        return True
    except Exception as e:
        print(f"Failed to send password reset email: {e}")
        return False

# ============================================
# AUTH FUNCTIONS
# ============================================

def signup(email, password):
    """
    Create a new user account.
    Returns: dict with success status and user info or error
    """
    email = email.lower().strip()
    
    # Validate email format (basic check)
    if not email or '@' not in email or '.' not in email:
        return {'success': False, 'error': 'Invalid email address'}
    
    # Validate password strength
    if len(password) < 8:
        return {'success': False, 'error': 'Password must be at least 8 characters'}
    
    # Check if user already exists
    existing = get_user_by_email(email)
    if existing:
        return {'success': False, 'error': 'An account with this email already exists'}
    
    # Generate verification token
    verification_token = secrets.token_urlsafe(32)
    verification_expires = datetime.utcnow() + timedelta(hours=VERIFICATION_EXPIRY_HOURS)
    
    # Hash password and create user
    password_hash = hash_password(password)
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (email, password_hash, email_verification_token, email_verification_expires)
            VALUES (%s, %s, %s, %s)
            RETURNING id, email, email_verified, created_at
        """, (email, password_hash, verification_token, verification_expires))
        
        user = cur.fetchone()
        conn.commit()
        
        # Send verification email
        send_verification_email(email, verification_token)
        
        return {
            'success': True,
            'message': 'Account created. Please check your email to verify.',
            'user': {
                'id': user['id'],
                'email': user['email'],
                'email_verified': user['email_verified']
            }
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
    Returns: dict with success status, token, and user info or error
    """
    email = email.lower().strip()
    
    # Find user
    user = get_user_by_email(email)
    if not user:
        return {'success': False, 'error': 'Invalid email or password'}
    
    # Verify password
    if not verify_password(password, user['password_hash']):
        return {'success': False, 'error': 'Invalid email or password'}
    
    # Check if email is verified
    if not user['email_verified']:
        return {
            'success': False, 
            'error': 'Please verify your email before logging in',
            'needs_verification': True
        }
    
    # Update last login
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE users SET last_login = NOW(), updated_at = NOW()
            WHERE id = %s
        """, (user['id'],))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    
    # Generate JWT
    token = generate_jwt(user['id'], user['email'])
    
    return {
        'success': True,
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'email_verified': user['email_verified']
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
        
        # Generate JWT so user is logged in after verification
        jwt_token = generate_jwt(user['id'], user['email'])
        
        return {
            'success': True,
            'message': 'Email verified successfully!',
            'token': jwt_token,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'email_verified': True
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
        
        # Send verification email
        send_verification_email(email, verification_token)
        
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
            SELECT pr.id, pr.user_id, pr.expires_at, u.email
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
        jwt_token = generate_jwt(reset['user_id'], reset['email'])
        
        return {
            'success': True,
            'message': 'Password reset successfully!',
            'token': jwt_token,
            'user': {
                'id': reset['user_id'],
                'email': reset['email'],
                'email_verified': True
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
            'created_at': user['created_at'].isoformat() if user['created_at'] else None
        }
    }
