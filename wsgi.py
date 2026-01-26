"""
CollectionCalc - WSGI Entry Point (v3.9)
Flask routes for the CollectionCalc API

New in v3.9:
- Beta code validation and management
- User approval workflow
- Admin dashboard endpoints
- Natural Language Query (NLQ)
- Request logging for debugging
- API usage tracking
"""

import os
import time
import json
from functools import wraps
from flask import Flask, request, jsonify, g
from flask_cors import CORS

# Import our modules
from auth import (
    signup, login, verify_email, resend_verification, 
    forgot_password, reset_password, get_current_user,
    validate_beta_code, create_beta_code, list_beta_codes,
    approve_user, reject_user, get_pending_users, get_all_users,
    require_admin, verify_jwt, get_user_by_id
)
from admin import (
    log_request, log_api_usage, get_dashboard_stats,
    get_recent_errors, get_endpoint_stats, get_device_breakdown,
    natural_language_query, get_nlq_history, get_anthropic_usage_summary
)

# Import existing modules
from ebay_valuation import get_ebay_valuation, search_ebay_sold
from ebay_oauth import get_auth_url, exchange_code, get_valid_token, get_ebay_user_info
from ebay_listing import create_ebay_listing, upload_image_to_ebay
from ebay_description import generate_ebay_description
from comic_extraction import extract_comic_from_image

# Optional: Anthropic for AI features
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')


# ============================================
# REQUEST LOGGING MIDDLEWARE
# ============================================

@app.before_request
def before_request():
    g.start_time = time.time()
    g.user_id = None
    
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        payload = verify_jwt(token)
        if payload:
            g.user_id = payload.get('user_id')
    
    ua = request.headers.get('User-Agent', '').lower()
    if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
        g.device_type = 'mobile'
    elif 'tablet' in ua or 'ipad' in ua:
        g.device_type = 'tablet'
    else:
        g.device_type = 'desktop'


@app.after_request
def after_request(response):
    if request.path in ['/', '/health', '/favicon.ico']:
        return response
    
    try:
        response_time = int((time.time() - g.start_time) * 1000)
        error_message = None
        if response.status_code >= 400:
            try:
                data = response.get_json()
                error_message = data.get('error') if data else None
            except:
                pass
        
        log_request(
            user_id=g.user_id,
            endpoint=request.path,
            method=request.method,
            status_code=response.status_code,
            response_time_ms=response_time,
            error_message=error_message,
            request_size=request.content_length,
            response_size=response.content_length,
            user_agent=request.headers.get('User-Agent'),
            ip_address=request.remote_addr,
            device_type=g.device_type
        )
    except Exception as e:
        print(f"Error logging request: {e}")
    
    return response


# ============================================
# AUTH DECORATORS
# ============================================

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        token = auth_header[7:]
        payload = verify_jwt(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401
        
        g.user_id = payload['user_id']
        g.user_email = payload['email']
        g.is_admin = payload.get('is_admin', False)
        g.is_approved = payload.get('is_approved', False)
        
        return f(*args, **kwargs)
    return decorated


def require_admin_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        token = auth_header[7:]
        user, error = require_admin(token)
        if error:
            return jsonify({'success': False, 'error': error}), 403
        
        g.admin_id = user['id']
        g.admin_email = user['email']
        
        return f(*args, **kwargs)
    return decorated


def require_approved(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.is_approved and not g.is_admin:
            return jsonify({'success': False, 'error': 'Account pending approval'}), 403
        return f(*args, **kwargs)
    return decorated


# ============================================
# HEALTH CHECK
# ============================================

@app.route('/')
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'version': '3.9'})


# ============================================
# BETA CODE ENDPOINTS
# ============================================

@app.route('/api/beta/validate', methods=['POST'])
def api_validate_beta():
    data = request.get_json() or {}
    code = data.get('code', '')
    result = validate_beta_code(code)
    return jsonify(result)


# ============================================
# AUTH ENDPOINTS
# ============================================

@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    data = request.get_json() or {}
    result = signup(data.get('email', ''), data.get('password', ''), data.get('beta_code'))
    return jsonify(result)


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    result = login(data.get('email', ''), data.get('password', ''))
    return jsonify(result)


@app.route('/api/auth/verify/<token>', methods=['GET'])
def api_verify_email(token):
    result = verify_email(token)
    return jsonify(result)


@app.route('/api/auth/resend-verification', methods=['POST'])
def api_resend_verification():
    data = request.get_json() or {}
    result = resend_verification(data.get('email', ''))
    return jsonify(result)


@app.route('/api/auth/forgot-password', methods=['POST'])
def api_forgot_password():
    data = request.get_json() or {}
    result = forgot_password(data.get('email', ''))
    return jsonify(result)


@app.route('/api/auth/reset-password', methods=['POST'])
def api_reset_password():
    data = request.get_json() or {}
    result = reset_password(data.get('token', ''), data.get('password', ''))
    return jsonify(result)


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def api_get_me():
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


# ============================================
# ADMIN ENDPOINTS
# ============================================

@app.route('/api/admin/dashboard', methods=['GET'])
@require_admin_auth
def api_admin_dashboard():
    stats = get_dashboard_stats()
    return jsonify({'success': True, 'stats': stats})


@app.route('/api/admin/users', methods=['GET'])
@require_admin_auth
def api_admin_users():
    users = get_all_users()
    users_list = []
    for u in users:
        users_list.append({
            'id': u['id'],
            'email': u['email'],
            'email_verified': u['email_verified'],
            'is_approved': u.get('is_approved', False),
            'is_admin': u.get('is_admin', False),
            'beta_code_used': u.get('beta_code_used'),
            'created_at': u['created_at'].isoformat() if u['created_at'] else None,
            'approved_at': u['approved_at'].isoformat() if u.get('approved_at') else None
        })
    return jsonify({'success': True, 'users': users_list})


@app.route('/api/admin/users/<int:user_id>/approve', methods=['POST'])
@require_admin_auth
def api_approve_user(user_id):
    result = approve_user(user_id, g.admin_id)
    return jsonify(result)


@app.route('/api/admin/users/<int:user_id>/reject', methods=['POST'])
@require_admin_auth
def api_reject_user(user_id):
    data = request.get_json() or {}
    result = reject_user(user_id, g.admin_id, data.get('reason'))
    return jsonify(result)


@app.route('/api/admin/beta-codes', methods=['GET'])
@require_admin_auth
def api_get_beta_codes():
    codes = list_beta_codes(include_inactive=True)
    codes_list = []
    for c in codes:
        codes_list.append({
            'id': c['id'],
            'code': c['code'],
            'note': c['note'],
            'uses_allowed': c['uses_allowed'],
            'uses_remaining': c['uses_remaining'],
            'is_active': c['is_active'],
            'created_at': c['created_at'].isoformat() if c['created_at'] else None,
            'created_by_email': c.get('created_by_email')
        })
    return jsonify({'success': True, 'codes': codes_list})


@app.route('/api/admin/beta-codes', methods=['POST'])
@require_admin_auth
def api_create_beta_code():
    data = request.get_json() or {}
    try:
        code = create_beta_code(g.admin_id, data.get('note'), data.get('uses_allowed', 1), data.get('expires_days'))
        return jsonify({'success': True, 'code': code})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/errors', methods=['GET'])
@require_admin_auth
def api_get_errors():
    limit = request.args.get('limit', 20, type=int)
    errors = get_recent_errors(limit)
    errors_list = []
    for e in errors:
        errors_list.append({
            'id': e['id'],
            'endpoint': e['endpoint'],
            'method': e['method'],
            'status_code': e['status_code'],
            'error_message': e['error_message'],
            'device_type': e['device_type'],
            'user_email': e.get('user_email'),
            'created_at': e['created_at'].isoformat() if e['created_at'] else None
        })
    return jsonify({'success': True, 'errors': errors_list})


@app.route('/api/admin/usage', methods=['GET'])
@require_admin_auth
def api_get_usage():
    days = request.args.get('days', 30, type=int)
    usage = get_anthropic_usage_summary(days)
    return jsonify({'success': True, 'usage': usage})


@app.route('/api/admin/nlq', methods=['POST'])
@require_admin_auth
def api_nlq():
    data = request.get_json() or {}
    question = data.get('question', '')
    if not question:
        return jsonify({'success': False, 'error': 'Question is required'}), 400
    result = natural_language_query(question, g.admin_id)
    return jsonify(result)


# ============================================
# VALUATION ENDPOINTS
# ============================================

@app.route('/api/valuate', methods=['POST'])
@require_auth
@require_approved
def api_valuate():
    data = request.get_json() or {}
    title = data.get('title', '')
    issue = data.get('issue', '')
    
    if not title or not issue:
        return jsonify({'success': False, 'error': 'Title and issue are required'}), 400
    
    result = get_ebay_valuation(title, issue, data.get('grade', 'VF'), data.get('publisher'), data.get('year'))
    
    if result.get('source') == 'web_search':
        log_api_usage(g.user_id, '/api/valuate', 'claude-sonnet-4-20250514', 
                      result.get('input_tokens', 0), result.get('output_tokens', 0))
    
    return jsonify(result)


@app.route('/api/extract', methods=['POST'])
@require_auth
@require_approved
def api_extract():
    data = request.get_json() or {}
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({'success': False, 'error': 'Image data is required'}), 400
    
    result = extract_comic_from_image(image_data)
    
    if result.get('success'):
        log_api_usage(g.user_id, '/api/extract', 'claude-sonnet-4-20250514',
                      result.get('input_tokens', 0), result.get('output_tokens', 0))
    
    return jsonify(result)


# ============================================
# ANTHROPIC PROXY
# ============================================

@app.route('/api/messages', methods=['POST'])
@require_auth
@require_approved
def api_messages():
    if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
        return jsonify({'error': 'Anthropic API not available'}), 503
    
    data = request.get_json() or {}
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    try:
        response = client.messages.create(**data)
        
        log_api_usage(g.user_id, '/api/messages', data.get('model', 'unknown'),
                      response.usage.input_tokens, response.usage.output_tokens)
        
        response_data = {
            'id': response.id,
            'type': response.type,
            'role': response.role,
            'content': [{'type': block.type, 'text': getattr(block, 'text', '')} for block in response.content],
            'usage': {'input_tokens': response.usage.input_tokens, 'output_tokens': response.usage.output_tokens}
        }
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# EBAY ENDPOINTS
# ============================================

@app.route('/api/ebay/auth', methods=['GET'])
@require_auth
@require_approved
def api_ebay_auth():
    url = get_auth_url(g.user_id)
    return jsonify({'success': True, 'url': url})


@app.route('/api/ebay/callback', methods=['GET'])
def api_ebay_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code:
        return jsonify({'success': False, 'error': 'No code provided'}), 400
    
    result = exchange_code(code, state)
    
    if result.get('success'):
        frontend_url = os.environ.get('FRONTEND_URL', 'https://collectioncalc.com')
        return f'<script>window.location.href = "{frontend_url}?ebay=connected";</script>'
    else:
        return jsonify(result), 400


@app.route('/api/ebay/status', methods=['GET'])
@require_auth
@require_approved
def api_ebay_status():
    token = get_valid_token(g.user_id)
    if token:
        user_info = get_ebay_user_info(token)
        return jsonify({'success': True, 'connected': True, 'user': user_info})
    return jsonify({'success': True, 'connected': False})


@app.route('/api/ebay/generate-description', methods=['POST'])
@require_auth
@require_approved
def api_generate_description():
    data = request.get_json() or {}
    result = generate_ebay_description(data)
    if result.get('success'):
        log_api_usage(g.user_id, '/api/ebay/generate-description', 'claude-sonnet-4-20250514',
                      result.get('input_tokens', 0), result.get('output_tokens', 0))
    return jsonify(result)


@app.route('/api/ebay/upload-image', methods=['POST'])
@require_auth
@require_approved
def api_upload_image():
    data = request.get_json() or {}
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({'success': False, 'error': 'Image data required'}), 400
    
    token = get_valid_token(g.user_id)
    if not token:
        return jsonify({'success': False, 'error': 'eBay not connected'}), 401
    
    result = upload_image_to_ebay(token, image_data)
    return jsonify(result)


@app.route('/api/ebay/list', methods=['POST'])
@require_auth
@require_approved
def api_ebay_list():
    data = request.get_json() or {}
    token = get_valid_token(g.user_id)
    if not token:
        return jsonify({'success': False, 'error': 'eBay not connected'}), 401
    result = create_ebay_listing(token, data)
    return jsonify(result)


# ============================================
# SALES DATA ENDPOINTS
# ============================================

@app.route('/api/sales/record', methods=['POST'])
def api_record_sale():
    data = request.get_json() or {}
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'success': False, 'error': 'Database not configured'}), 500
    
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO market_sales (source, title, series, issue, grade, grade_source, slab_type,
                variant, is_key, price, sold_at, raw_title, seller, bids, viewers, image_url, source_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_id) DO UPDATE SET price = EXCLUDED.price, sold_at = EXCLUDED.sold_at
            RETURNING id
        """, (data.get('source', 'whatnot'), data.get('title'), data.get('series'), data.get('issue'),
              data.get('grade'), data.get('grade_source'), data.get('slab_type'), data.get('variant'),
              data.get('is_key', False), data.get('price'), data.get('sold_at'), data.get('raw_title'),
              data.get('seller'), data.get('bids'), data.get('viewers'), data.get('image_url'), data.get('source_id')))
        
        sale_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'id': sale_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sales/count', methods=['GET'])
def api_sales_count():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'count': 0})
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM market_sales")
        count = cur.fetchone()['count']
        cur.close()
        conn.close()
        return jsonify({'count': count})
    except:
        return jsonify({'count': 0})


@app.route('/api/sales/recent', methods=['GET'])
def api_sales_recent():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    limit = request.args.get('limit', 20, type=int)
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        return jsonify({'success': False, 'error': 'Database not configured'}), 500
    
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        cur.execute("SELECT * FROM market_sales ORDER BY created_at DESC LIMIT %s", (limit,))
        sales = cur.fetchall()
        cur.close()
        conn.close()
        
        sales_list = []
        for s in sales:
            sale = dict(s)
            for key, val in sale.items():
                if hasattr(val, 'isoformat'):
                    sale[key] = val.isoformat()
                elif hasattr(val, '__float__'):
                    sale[key] = float(val)
            sales_list.append(sale)
        
        return jsonify({'success': True, 'sales': sales_list})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# COLLECTION ENDPOINTS
# ============================================

@app.route('/api/collection', methods=['GET'])
@require_auth
@require_approved
def api_get_collection():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    cur.execute("SELECT * FROM collections WHERE user_id = %s ORDER BY created_at DESC", (g.user_id,))
    items = cur.fetchall()
    cur.close()
    conn.close()
    
    items_list = []
    for item in items:
        i = dict(item)
        for key, val in i.items():
            if hasattr(val, 'isoformat'):
                i[key] = val.isoformat()
            elif hasattr(val, '__float__'):
                i[key] = float(val)
        items_list.append(i)
    
    return jsonify({'success': True, 'items': items_list})


@app.route('/api/collection/save', methods=['POST'])
@require_auth
@require_approved
def api_save_collection():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    data = request.get_json() or {}
    items = data.get('items', [])
    if not items:
        return jsonify({'success': False, 'error': 'No items to save'}), 400
    
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    saved_ids = []
    for item in items:
        cur.execute("""
            INSERT INTO collections (user_id, title, issue, grade, value)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (g.user_id, item.get('title'), item.get('issue'), item.get('grade'), item.get('value')))
        saved_ids.append(cur.fetchone()['id'])
    
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True, 'saved': len(saved_ids), 'ids': saved_ids})


@app.route('/api/collection/<int:item_id>', methods=['DELETE'])
@require_auth
@require_approved
def api_delete_collection_item(item_id):
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    cur.execute("DELETE FROM collections WHERE id = %s AND user_id = %s RETURNING id", (item_id, g.user_id))
    deleted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    if deleted:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Item not found'}), 404


# ============================================
# RUN SERVER
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
