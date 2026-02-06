"""
Auth Blueprint - Authentication and user management endpoints
Routes: /api/auth/*
"""
from flask import Blueprint, jsonify, request, g

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Import auth functions (from auth.py module in parent directory)
from auth import (
    signup, login, verify_email, resend_verification,
    forgot_password, reset_password, get_user_by_id, require_auth
)


@auth_bp.route('/signup', methods=['POST'])
def api_signup():
    """User signup"""
    data = request.get_json() or {}
    result = signup(data.get('email', ''), data.get('password', ''), data.get('beta_code'))
    return jsonify(result)


@auth_bp.route('/login', methods=['POST'])
def api_login():
    """User login"""
    data = request.get_json() or {}
    result = login(data.get('email', ''), data.get('password', ''))
    return jsonify(result)


@auth_bp.route('/verify/<token>', methods=['GET'])
def api_verify_email(token):
    """Verify email address"""
    result = verify_email(token)
    return jsonify(result)


@auth_bp.route('/resend-verification', methods=['POST'])
def api_resend_verification():
    """Resend verification email"""
    data = request.get_json() or {}
    result = resend_verification(data.get('email', ''))
    return jsonify(result)


@auth_bp.route('/forgot-password', methods=['POST'])
def api_forgot_password():
    """Request password reset"""
    data = request.get_json() or {}
    result = forgot_password(data.get('email', ''))
    return jsonify(result)


@auth_bp.route('/reset-password', methods=['POST'])
def api_reset_password():
    """Reset password with token"""
    data = request.get_json() or {}
    result = reset_password(data.get('token', ''), data.get('password', ''))
    return jsonify(result)


@auth_bp.route('/me', methods=['GET'])
@require_auth
def api_get_me():
    """Get current user info"""
    user = get_user_by_id(g.user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'email_verified': user['email_verified'],
            'is_approved': user.get('is_approved', False),
            'is_admin': user.get('is_admin', False)
        }
    })
