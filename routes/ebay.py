"""
eBay Blueprint - eBay OAuth, listing, and image upload endpoints
Routes: /api/ebay/*
"""
import os
from flask import Blueprint, jsonify, request, g

# Create blueprint
ebay_bp = Blueprint('ebay', __name__, url_prefix='/api/ebay')

# Import auth decorators
from auth import require_auth, require_approved
from admin import log_api_usage

# Module imports (will be set by wsgi.py)
get_auth_url = None
exchange_code_for_token = None
get_user_token = None
is_user_connected = None
create_listing = None
upload_image_to_ebay = None
generate_description = None


def init_modules(auth_url_func, exchange_func, get_token_func, is_connected_func,
                 create_listing_func, upload_image_func, gen_desc_func):
    """Initialize modules from wsgi.py"""
    global get_auth_url, exchange_code_for_token, get_user_token, is_user_connected
    global create_listing, upload_image_to_ebay, generate_description
    
    get_auth_url = auth_url_func
    exchange_code_for_token = exchange_func
    get_user_token = get_token_func
    is_user_connected = is_connected_func
    create_listing = create_listing_func
    upload_image_to_ebay = upload_image_func
    generate_description = gen_desc_func


@ebay_bp.route('/account-deletion', methods=['POST'])
def api_ebay_account_deletion():
    """
    eBay Marketplace Account Deletion Notification endpoint.
    Called by eBay when a user requests account deletion (GDPR compliance).
    """
    try:
        from ebay_oauth import delete_user_by_ebay_id
        
        data = request.get_json() or {}
        
        # eBay sends notification with user info
        # The exact format depends on eBay's notification structure
        ebay_user_id = data.get('userId') or data.get('user_id') or data.get('username')
        
        if not ebay_user_id:
            # Silently acknowledge - these are eBay users who never used our app
            return jsonify({'success': True, 'message': 'Notification received'}), 200
        
        # Delete user data
        deleted = delete_user_by_ebay_id(ebay_user_id)
        
        if deleted:
            print(f"Successfully deleted data for eBay user: {ebay_user_id}")
        else:
            print(f"No data found for eBay user: {ebay_user_id}")
        
        # Always return 200 to acknowledge receipt
        return jsonify({'success': True, 'deleted': deleted}), 200
        
    except Exception as e:
        print(f"Error processing eBay deletion notification: {e}")
        # Still return 200 to prevent eBay from retrying
        return jsonify({'success': False, 'error': str(e)}), 200


@ebay_bp.route('/auth', methods=['GET'])
@require_auth
@require_approved
def api_ebay_auth():
    """Get eBay OAuth authorization URL"""
    if not get_auth_url:
        return jsonify({'success': False, 'error': 'eBay module not available'}), 503
    url = get_auth_url(g.user_id)
    return jsonify({'success': True, 'url': url})


@ebay_bp.route('/callback', methods=['GET'])
def api_ebay_callback():
    """eBay OAuth callback endpoint"""
    if not exchange_code_for_token:
        return jsonify({'success': False, 'error': 'eBay module not available'}), 503
    
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code:
        return jsonify({'success': False, 'error': 'No code provided'}), 400
    
    try:
        from ebay_oauth import save_user_token
        token_data = exchange_code_for_token(code)
        if state:  # state contains user_id
            save_user_token(state, token_data)
        
        frontend_url = os.environ.get('FRONTEND_URL', 'https://collectioncalc.com')
        return f'<script>window.location.href = "{frontend_url}?ebay=connected";</script>'
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@ebay_bp.route('/status', methods=['GET'])
@require_auth
@require_approved
def api_ebay_status():
    """Check if user has connected eBay account"""
    if not get_user_token:
        return jsonify({'success': False, 'error': 'eBay module not available'}), 503
    token_data = get_user_token(str(g.user_id))
    if token_data and token_data.get('access_token'):
        return jsonify({'success': True, 'connected': True})
    return jsonify({'success': True, 'connected': False})


@ebay_bp.route('/generate-description', methods=['POST'])
@require_auth
@require_approved
def api_generate_description():
    """Generate eBay listing description using AI"""
    if not generate_description:
        return jsonify({'success': False, 'error': 'Description module not available'}), 503
    data = request.get_json() or {}
    result = generate_description(
        data.get('title', ''),
        data.get('issue', ''),
        data.get('grade', 'VF'),
        data.get('price', 0)
    )
    if result.get('success'):
        log_api_usage(g.user_id, '/api/ebay/generate-description', 'claude-sonnet-4-20250514',
                      result.get('input_tokens', 0), result.get('output_tokens', 0))
    return jsonify(result)


@ebay_bp.route('/upload-image', methods=['POST'])
@require_auth
@require_approved
def api_ebay_upload_image():
    """Upload image to eBay for listing"""
    if not upload_image_to_ebay or not get_user_token:
        return jsonify({'success': False, 'error': 'eBay module not available'}), 503
    data = request.get_json() or {}
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({'success': False, 'error': 'Image data required'}), 400
    
    token_data = get_user_token(str(g.user_id))
    if not token_data or not token_data.get('access_token'):
        return jsonify({'success': False, 'error': 'eBay not connected'}), 401
    
    result = upload_image_to_ebay(token_data['access_token'], image_data)
    return jsonify(result)


@ebay_bp.route('/list', methods=['POST'])
@require_auth
@require_approved
def api_ebay_list():
    """Create eBay listing"""
    if not create_listing or not get_user_token:
        return jsonify({'success': False, 'error': 'eBay module not available'}), 503
    data = request.get_json() or {}
    
    token_data = get_user_token(str(g.user_id))
    if not token_data or not token_data.get('access_token'):
        return jsonify({'success': False, 'error': 'eBay not connected'}), 401
    
    result = create_listing(
        str(g.user_id),
        data.get('title', ''),
        data.get('issue', ''),
        data.get('price', 0),
        data.get('grade', 'VF'),
        data.get('description'),
        data.get('publish', False),
        data.get('image_urls')
    )
    return jsonify(result)
