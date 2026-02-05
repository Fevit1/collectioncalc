"""
CollectionCalc - WSGI Entry Point (v4.2.2)
Flask routes for the CollectionCalc API

New in v4.2.2:
- Content moderation via AWS Rekognition
- Images checked BEFORE processing or storage
- Blocks explicit/violent/drug/hate content
- Admin endpoint: /api/admin/moderation
- content_incidents table for logging

New in v4.2.1:
- Reprint filter! FMV excludes reprints (barcode-detected + text-detected)
- Filters: "2nd print", "3rd print", "reprint" in titles

New in v4.2:
- FMV endpoint now pulls from both Whatnot AND eBay sales
- Filters out facsimiles, lots, bundles from eBay data
- Response includes source breakdown (whatnot vs ebay counts)

New in v4.1:
- Barcode backfill endpoint for existing R2 images
- Barcode stats endpoint for monitoring coverage

New in v4.0:
- Barcode scanning and storage for sales
- Docker deployment with pyzbar/libzbar0
- UPC data stored in market_sales and ebay_sales

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
import hashlib
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

# Import existing modules (with fallbacks for mismatched function names)
try:
    from ebay_valuation import get_valuation_with_ebay, search_ebay_sold
except ImportError as e:
    print(f"ebay_valuation import error: {e}")
    get_valuation_with_ebay = None
    search_ebay_sold = None

try:
    from ebay_oauth import get_auth_url, exchange_code_for_token, get_user_token, is_user_connected
except ImportError as e:
    print(f"ebay_oauth import error: {e}")
    get_auth_url = None
    exchange_code_for_token = None
    get_user_token = None
    is_user_connected = None

try:
    from ebay_listing import create_listing, upload_image_to_ebay
except ImportError as e:
    print(f"ebay_listing import error: {e}")
    create_listing = None
    upload_image_to_ebay = None

try:
    from ebay_description import generate_description
except ImportError as e:
    print(f"ebay_description import error: {e}")
    generate_description = None

try:
    from comic_extraction import extract_from_base64
except ImportError as e:
    print(f"comic_extraction import error: {e}")
    extract_from_base64 = None

# R2 Storage for images
try:
    from r2_storage import (
        upload_sale_image, upload_submission_image, upload_temp_image,
        move_temp_to_sale, check_r2_connection, get_image_url
    )
    R2_AVAILABLE = True
except ImportError as e:
    print(f"r2_storage import error: {e}")
    R2_AVAILABLE = False
    upload_sale_image = None
    upload_submission_image = None
    upload_temp_image = None

# Optional: Anthropic for AI features
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Barcode scanning (Docker only - requires libzbar0)
try:
    from pyzbar import pyzbar
    from pyzbar.pyzbar import ZBarSymbol
    from PIL import Image
    import io
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False

# Content moderation (AWS Rekognition)
try:
    from content_moderation import (
        moderate_image, log_moderation_incident, get_image_hash,
        get_moderation_incidents, get_moderation_stats, MODERATION_AVAILABLE
    )
except ImportError as e:
    print(f"content_moderation import error: {e}")
    MODERATION_AVAILABLE = False
    moderate_image = None


def scan_barcode_from_base64(image_data):
    """
    Scan barcode from base64 image data.
    Returns dict with upc_main, upc_addon, is_reprint or None if not found.
    """
    if not BARCODE_AVAILABLE:
        return None
    
    try:
        import base64
        
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Try rotations
        for rotation in [0, 90, 180, 270]:
            if rotation == 0:
                rotated = image
            else:
                rotated = image.rotate(-rotation, expand=True)
            
            barcodes = pyzbar.decode(rotated, symbols=[ZBarSymbol.UPCA, ZBarSymbol.EAN13, ZBarSymbol.UPCE])
            if not barcodes:
                barcodes = pyzbar.decode(rotated)
            
            if barcodes:
                for barcode in barcodes:
                    code = barcode.data.decode('utf-8')
                    if len(code) >= 12:
                        upc_main = code[:12] if len(code) >= 12 else code
                        upc_addon = None
                        is_reprint = False
                        
                        if len(code) >= 17:
                            upc_addon = code[12:17]
                            # Check if reprint (5th digit > 1)
                            if len(upc_addon) >= 5:
                                try:
                                    printing = int(upc_addon[4])
                                    is_reprint = printing > 1
                                except ValueError:
                                    pass
                        
                        print(f"[Barcode] Found at {rotation}°: {upc_main} / {upc_addon} (reprint: {is_reprint})")
                        return {
                            'upc_main': upc_main,
                            'upc_addon': upc_addon,
                            'is_reprint': is_reprint,
                            'rotation': rotation
                        }
        
        return None
    except Exception as e:
        print(f"[Barcode] Scan error: {e}")
        return None


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# ============================================
# eBAY SALES API ENDPOINTS
# ============================================

@app.route('/api/ebay-sales/batch', methods=['POST'])
def add_ebay_sales_batch():
    """Batch insert eBay sales from browser extension with R2 image backup."""
    import psycopg2
    import requests
    import base64
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from r2_storage import upload_image
    
    database_url = os.environ.get('DATABASE_URL')
    conn = None
    
    def backup_image_to_r2(sale):
        """Download image from eBay and upload to R2."""
        try:
            image_url = sale.get('image_url', '')
            ebay_item_id = sale.get('ebay_item_id', '')
            
            if not image_url or not ebay_item_id:
                return None
            
            # Download from eBay
            response = requests.get(image_url, timeout=10)
            if response.status_code != 200:
                return None
            
            # Convert to base64
            image_b64 = base64.b64encode(response.content).decode('utf-8')
            
            # Determine content type
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            ext = 'webp' if 'webp' in content_type else 'jpg'
            
            # Upload to R2
            path = f"ebay-covers/{ebay_item_id}.{ext}"
            result = upload_image(image_b64, path, content_type)
            
            if result.get('success'):
                return {'ebay_item_id': ebay_item_id, 'r2_url': result['url']}
            return None
        except Exception as e:
            print(f"Image backup error for {sale.get('ebay_item_id')}: {e}")
            return None
    
    try:
        data = request.get_json()
        sales = data.get('sales', [])
        
        if not sales:
            return jsonify({'error': 'No sales provided'}), 400
        
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        saved = 0
        duplicates = 0
        saved_sales = []  # Track which sales were actually saved
        
        # Step 1: Insert all sales to database
        for sale in sales:
            content = f"{sale.get('raw_title', '')}|{sale.get('sale_price', '')}|{sale.get('sale_date', '')}"
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:32]
            
            try:
                cur.execute("""
                    INSERT INTO ebay_sales (
                        raw_title, parsed_title, issue_number, publisher,
                        sale_price, sale_date, condition, graded, grade,
                        listing_url, image_url, ebay_item_id, content_hash
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ebay_item_id) DO NOTHING
                """, (
                    sale.get('raw_title'),
                    sale.get('parsed_title'),
                    sale.get('issue_number'),
                    sale.get('publisher'),
                    sale.get('sale_price'),
                    sale.get('sale_date'),
                    sale.get('condition'),
                    sale.get('graded', False),
                    sale.get('grade'),
                    sale.get('listing_url'),
                    sale.get('image_url'),
                    sale.get('ebay_item_id'),
                    content_hash
                ))
                
                if cur.rowcount > 0:
                    saved += 1
                    saved_sales.append(sale)
                else:
                    duplicates += 1
                    
                conn.commit()
                
            except Exception as e:
                duplicates += 1
                conn.rollback()
        
        # Step 2: Parallel image backup for newly saved sales (max 5 concurrent)
        images_backed_up = 0
        if saved_sales:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(backup_image_to_r2, sale): sale for sale in saved_sales}
                
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        # Update database with R2 URL
                        try:
                            cur.execute("""
                                UPDATE ebay_sales 
                                SET r2_image_url = %s 
                                WHERE ebay_item_id = %s
                            """, (result['r2_url'], result['ebay_item_id']))
                            conn.commit()
                            images_backed_up += 1
                        except Exception as e:
                            print(f"Error updating R2 URL: {e}")
                            conn.rollback()
        
        return jsonify({
            'success': True,
            'saved': saved,
            'duplicates': duplicates,
            'images_backed_up': images_backed_up,
            'total': len(sales)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/ebay-sales/stats', methods=['GET'])
def get_ebay_sales_stats():
    """Get statistics about collected eBay sales."""
    import psycopg2
    database_url = os.environ.get('DATABASE_URL')
    conn = None
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM ebay_sales")
        total = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(*) FROM ebay_sales 
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
        """)
        last_week = cur.fetchone()[0]
        
        return jsonify({
            'total_sales': total,
            'last_7_days': last_week
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()



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

@app.route('/api/debug/prompt-check')
def debug_prompt():
    from comic_extraction import EXTRACTION_PROMPT
    return jsonify({
        'prompt_length': len(EXTRACTION_PROMPT),
        'has_new_schema': 'YOU MUST RETURN EXACTLY' in EXTRACTION_PROMPT,
        'first_100_chars': EXTRACTION_PROMPT[:100]
    })

# ============================================
# HEALTH CHECK
# ============================================

@app.route('/')
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'version': '4.2.2', 'barcode': BARCODE_AVAILABLE, 'moderation': MODERATION_AVAILABLE})


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


@app.route('/api/admin/moderation', methods=['GET'])
@require_admin_auth
def api_get_moderation():
    """Get moderation incidents and stats."""
    limit = request.args.get('limit', 50, type=int)
    blocked_only = request.args.get('blocked_only', 'false').lower() == 'true'
    
    if MODERATION_AVAILABLE:
        incidents = get_moderation_incidents(limit=limit, blocked_only=blocked_only)
        stats = get_moderation_stats()
    else:
        incidents = []
        stats = {'total_incidents': 0, 'total_blocked': 0, 'total_warnings': 0, 'users_blocked': 0}
    
    return jsonify({
        'success': True,
        'moderation_enabled': MODERATION_AVAILABLE,
        'stats': stats,
        'incidents': incidents
    })


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
# SIGNATURE ADMIN ENDPOINTS
# ============================================

@app.route('/api/admin/signatures', methods=['GET'])
@require_admin_auth
def api_get_signatures():
    """Get all creator signatures with their images."""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    try:
        # Get all creators
        cur.execute("""
            SELECT id, creator_name, role, signature_style, verified, source, notes, created_at
            FROM creator_signatures
            ORDER BY creator_name
        """)
        creators = cur.fetchall()
        
        # Get all images
        cur.execute("""
            SELECT id, creator_id, image_url, era, notes, source, created_at
            FROM signature_images
            ORDER BY created_at
        """)
        images = cur.fetchall()
        
        # Group images by creator
        images_by_creator = {}
        for img in images:
            cid = img['creator_id']
            if cid not in images_by_creator:
                images_by_creator[cid] = []
            images_by_creator[cid].append({
                'id': img['id'],
                'image_url': img['image_url'],
                'era': img['era'],
                'notes': img['notes'],
                'source': img['source']
            })
        
        # Build result
        result = []
        for c in creators:
            item = dict(c)
            if item.get('created_at'):
                item['created_at'] = item['created_at'].isoformat()
            item['images'] = images_by_creator.get(c['id'], [])
            result.append(item)
        
        total_images = len(images)
        
        return jsonify({'success': True, 'signatures': result, 'total_images': total_images})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/admin/signatures', methods=['POST'])
@require_admin_auth
def api_add_signature():
    """Add a new creator signature."""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    data = request.get_json() or {}
    creator_name = data.get('creator_name', '').strip()
    
    if not creator_name:
        return jsonify({'success': False, 'error': 'Creator name is required'}), 400
    
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT id FROM creator_signatures WHERE LOWER(creator_name) = LOWER(%s)", (creator_name,))
        if cur.fetchone():
            return jsonify({'success': False, 'error': 'Creator already exists'}), 400
        
        cur.execute("""
            INSERT INTO creator_signatures (creator_name, role, signature_style, source)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            creator_name,
            data.get('role', 'artist'),
            data.get('signature_style'),
            data.get('source')
        ))
        
        new_id = cur.fetchone()['id']
        conn.commit()
        
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/admin/signatures/<int:sig_id>/images', methods=['POST'])
@require_admin_auth
def api_add_signature_image(sig_id):
    """Add a reference image to a creator."""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import uuid
    
    data = request.get_json() or {}
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({'success': False, 'error': 'Image data required'}), 400
    
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    try:
        # Check creator exists
        cur.execute("SELECT id, creator_name FROM creator_signatures WHERE id = %s", (sig_id,))
        creator = cur.fetchone()
        if not creator:
            return jsonify({'success': False, 'error': 'Creator not found'}), 404
        
        # Upload to R2
        if R2_AVAILABLE:
            from r2_storage import upload_to_r2
            filename = f"signatures/{sig_id}_{uuid.uuid4().hex[:8]}.jpg"
            result = upload_to_r2(filename, image_data)
            
            if not result.get('success'):
                return jsonify({'success': False, 'error': 'Failed to upload image'}), 500
            
            image_url = result['url']
        else:
            return jsonify({'success': False, 'error': 'Image storage not configured'}), 503
        
        # Insert into signature_images table
        cur.execute("""
            INSERT INTO signature_images (creator_id, image_url, era, notes, source)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            sig_id,
            image_url,
            data.get('era'),
            data.get('notes'),
            data.get('source')
        ))
        
        new_id = cur.fetchone()['id']
        conn.commit()
        
        return jsonify({'success': True, 'id': new_id, 'url': image_url})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/admin/signatures/images/<int:image_id>', methods=['DELETE'])
@require_admin_auth
def api_delete_signature_image(image_id):
    """Delete a signature reference image."""
    import psycopg2
    
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    try:
        cur.execute("DELETE FROM signature_images WHERE id = %s RETURNING id", (image_id,))
        result = cur.fetchone()
        conn.commit()
        
        if result:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Image not found'}), 404
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route('/api/admin/signatures/<int:sig_id>/image', methods=['POST'])
@require_admin_auth
def api_upload_signature_image(sig_id):
    """Upload or replace signature reference image (legacy endpoint)."""
    # Redirect to new endpoint
    return api_add_signature_image(sig_id)


@app.route('/api/admin/signatures/<int:sig_id>/verify', methods=['POST'])
@require_admin_auth
def api_verify_signature(sig_id):
    """Mark a signature as verified."""
    import psycopg2
    
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE creator_signatures 
            SET verified = TRUE, updated_at = NOW()
            WHERE id = %s
            RETURNING id
        """, (sig_id,))
        
        result = cur.fetchone()
        conn.commit()
        
        if result:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Creator not found'}), 404
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ============================================
# VALUATION ENDPOINTS
# ============================================

@app.route('/api/valuate', methods=['POST'])
@require_auth
@require_approved
def api_valuate():
    if not get_valuation_with_ebay:
        return jsonify({'success': False, 'error': 'Valuation module not available'}), 503
    
    data = request.get_json() or {}
    title = data.get('title', '')
    issue = data.get('issue', '')
    
    if not title or not issue:
        return jsonify({'success': False, 'error': 'Title and issue are required'}), 400
    
    result = get_valuation_with_ebay(title, issue, data.get('grade', 'VF'), data.get('publisher'), data.get('year'))
    
    # Log API usage if result indicates web search was used
    if isinstance(result, dict) and result.get('source') == 'web_search':
        log_api_usage(g.user_id, '/api/valuate', 'claude-sonnet-4-20250514', 
                      result.get('input_tokens', 0), result.get('output_tokens', 0))
    
    # Convert dataclass to dict if needed
    if hasattr(result, '__dict__') and not isinstance(result, dict):
        result = result.__dict__
    
    return jsonify(result)


@app.route('/api/cache/check', methods=['POST'])
@require_auth  
@require_approved
def api_cache_check():
    """Check if a comic title/issue combination exists in search_cache."""
    import psycopg2
    
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    issue = data.get('issue', '').strip()
    
    if not title or not issue:
        return jsonify({'success': False, 'error': 'Title and issue are required'}), 400
    
    # Build search key matching existing format: "title|issue" (lowercase, no grade)
    search_key = f"{title.lower()}|{issue}"
    
    database_url = os.environ.get('DATABASE_URL')
    conn = None
    
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Check if cache entry exists (recent within 48 hours)
        cur.execute("""
            SELECT cached_at 
            FROM search_cache 
            WHERE search_key = %s 
            AND cached_at > CURRENT_TIMESTAMP - INTERVAL '48 hours'
        """, (search_key,))
        
        result = cur.fetchone()
        
        if result:
            return jsonify({
                'success': True,
                'cached': True,
                'lastChecked': result[0].isoformat()
            })
        else:
            return jsonify({
                'success': True, 
                'cached': False,
                'lastChecked': None
            })
            
    except Exception as e:
        print(f"Cache check error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
        
    finally:
        if conn:
            cur.close()
            conn.close()


@app.route('/api/extract', methods=['POST'])
@require_auth
@require_approved
def api_extract():
    if not extract_from_base64:
        return jsonify({'success': False, 'error': 'Extraction module not available'}), 503
    
    data = request.get_json() or {}
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({'success': False, 'error': 'Image data is required'}), 400
    
    # Content moderation check BEFORE processing
    if moderate_image:
        mod_result = moderate_image(image_data)
        if mod_result.get('blocked'):
            log_moderation_incident(g.user_id, '/api/extract', mod_result, get_image_hash(image_data))
            return jsonify({
                'success': False, 
                'error': 'Image rejected: inappropriate content detected.',
                'moderation': True
            }), 400
        # Log warnings (but allow through)
        if mod_result.get('warnings'):
            log_moderation_incident(g.user_id, '/api/extract', mod_result, get_image_hash(image_data))
    
    media_type = data.get('media_type', 'image/jpeg')
    result = extract_from_base64(image_data, media_type)
    
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
    
    # Content moderation: check any images in the messages
    if moderate_image:
        for msg in data.get('messages', []):
            content = msg.get('content', [])
            if isinstance(content, list):
                for block in content:
                    if block.get('type') == 'image' and block.get('source', {}).get('type') == 'base64':
                        image_data = block['source'].get('data', '')
                        if image_data:
                            mod_result = moderate_image(image_data)
                            if mod_result.get('blocked'):
                                log_moderation_incident(g.user_id, '/api/messages', mod_result, get_image_hash(image_data))
                                return jsonify({
                                    'error': 'Image rejected: inappropriate content detected.',
                                    'moderation': True
                                }), 400
                            if mod_result.get('warnings'):
                                log_moderation_incident(g.user_id, '/api/messages', mod_result, get_image_hash(image_data))
    
    data['temperature'] = 0  # Force deterministic responses for consistent grading
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

@app.route('/api/ebay/account-deletion', methods=['POST'])
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


@app.route('/api/ebay/auth', methods=['GET'])
@require_auth
@require_approved
def api_ebay_auth():
    if not get_auth_url:
        return jsonify({'success': False, 'error': 'eBay module not available'}), 503
    url = get_auth_url(g.user_id)
    return jsonify({'success': True, 'url': url})


@app.route('/api/ebay/callback', methods=['GET'])
def api_ebay_callback():
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


@app.route('/api/ebay/status', methods=['GET'])
@require_auth
@require_approved
def api_ebay_status():
    if not get_user_token:
        return jsonify({'success': False, 'error': 'eBay module not available'}), 503
    token_data = get_user_token(str(g.user_id))
    if token_data and token_data.get('access_token'):
        return jsonify({'success': True, 'connected': True})
    return jsonify({'success': True, 'connected': False})


@app.route('/api/ebay/generate-description', methods=['POST'])
@require_auth
@require_approved
def api_generate_description():
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


@app.route('/api/ebay/upload-image', methods=['POST'])
@require_auth
@require_approved
def api_ebay_upload_image():
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


@app.route('/api/ebay/list', methods=['POST'])
@require_auth
@require_approved
def api_ebay_list():
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


# ============================================
# SALES DATA ENDPOINTS
# ============================================

@app.route('/api/sales/record', methods=['POST'])
def api_record_sale():
    """
    Record a sale from Whatnot extension.
    Optionally accepts 'image' field with base64 data to upload to R2.
    Now includes barcode scanning when image provided.
    """
    data = request.get_json() or {}
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'success': False, 'error': 'Database not configured'}), 500
    
    # Check if image data is included
    image_data = data.get('image')
    image_url = data.get('image_url')  # Existing URL (legacy)
    
    # Barcode fields - can come from request or be scanned from image
    upc_main = data.get('upc_main')
    upc_addon = data.get('upc_addon')
    is_reprint = data.get('is_reprint', False)
    
    # If image provided and no barcode data, try to scan it
    if image_data and not upc_main:
        barcode_result = scan_barcode_from_base64(image_data)
        if barcode_result:
            upc_main = barcode_result.get('upc_main')
            upc_addon = barcode_result.get('upc_addon')
            is_reprint = barcode_result.get('is_reprint', False)
    
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO market_sales (source, title, series, issue, grade, grade_source, slab_type,
                variant, is_key, is_facsimile, price, sold_at, raw_title, seller, bids, viewers, 
                image_url, source_id, upc_main, upc_addon, is_reprint)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_id) DO UPDATE SET 
                price = EXCLUDED.price, 
                sold_at = EXCLUDED.sold_at,
                upc_main = COALESCE(EXCLUDED.upc_main, market_sales.upc_main),
                upc_addon = COALESCE(EXCLUDED.upc_addon, market_sales.upc_addon),
                is_reprint = COALESCE(EXCLUDED.is_reprint, market_sales.is_reprint)
            RETURNING id
        """, (data.get('source', 'whatnot'), data.get('title'), data.get('series'), data.get('issue'),
              data.get('grade'), data.get('grade_source'), data.get('slab_type'), data.get('variant'),
              data.get('is_key', False), data.get('is_facsimile', False), data.get('price'), data.get('sold_at'), 
              data.get('raw_title'), data.get('seller'), data.get('bids'), data.get('viewers'), 
              image_url, data.get('source_id'), upc_main, upc_addon, is_reprint))
        
        sale_id = cur.fetchone()['id']
        conn.commit()
        
        # If image data was provided, upload to R2 and update the record
        if image_data and R2_AVAILABLE:
            r2_result = upload_sale_image(sale_id, image_data, 'front')
            if r2_result.get('success'):
                cur.execute(
                    "UPDATE market_sales SET image_url = %s WHERE id = %s",
                    (r2_result['url'], sale_id)
                )
                conn.commit()
                image_url = r2_result['url']
        
        cur.close()
        conn.close()
        return jsonify({
            'success': True, 
            'id': sale_id, 
            'image_url': image_url,
            'upc_main': upc_main,
            'upc_addon': upc_addon,
            'is_reprint': is_reprint
        })
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


@app.route('/api/sales/fmv', methods=['GET'])
def api_sales_fmv():
    """
    Get Fair Market Value data for a comic based on sales history.
    Groups sales by grade tier and returns averages.
    Now pulls from BOTH market_sales (Whatnot) AND ebay_sales.
    
    Query params:
        title: Comic title (required)
        issue: Issue number (optional)
        days: Number of days to look back (default 90)
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    title = request.args.get('title', '')
    issue = request.args.get('issue', '')
    days = request.args.get('days', 90, type=int)
    
    # Reject literal "null" or "undefined" issue values
    if issue in ['null', 'undefined', 'None', 'NaN']:
        issue = ''
    
    if not title:
        return jsonify({'success': False, 'error': 'Title is required'}), 400
    
    # Server-side garbage title filter (belt & suspenders with extension filter)
    if len(title) < 3:
        return jsonify({'success': False, 'count': 0, 'tiers': None})
    
    # Skip titles that are just numbers/symbols
    import re
    if re.match(r'^[\d\s$#%.,]+$', title):
        return jsonify({'success': False, 'count': 0, 'tiers': None})
    
    # Skip known garbage patterns
    title_lower = title.lower()
    garbage_patterns = [
        'available', 'remaining', 'left', 'in stock', 'bid now', 'starting',
        'mystery', 'random', 'surprise', 'bundle', 'lot of', 'choice', 'pick',
        'awesome comic', 'comic on screen', 'on screen', 'product', 'item', 'listing'
    ]
    if any(p in title_lower for p in garbage_patterns):
        return jsonify({'success': False, 'count': 0, 'tiers': None})
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'success': False, 'error': 'Database not configured'}), 500
    
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        # Query 1: market_sales (Whatnot data)
        # Filter out reprints if barcode detected them
        market_query = """
            SELECT grade, price, 'whatnot' as source
            FROM market_sales
            WHERE (
                LOWER(title) LIKE LOWER(%s) 
                OR LOWER(series) LIKE LOWER(%s)
                OR LOWER(raw_title) LIKE LOWER(%s)
            )
            AND price > 0
            AND (is_reprint IS NULL OR is_reprint = false)
            AND created_at > NOW() - INTERVAL '%s days'
        """
        market_params = [f'%{title}%', f'%{title}%', f'%{title}%', days]
        
        if issue:
            market_query += " AND (issue = %s OR issue = %s)"
            market_params.extend([str(issue), issue])
        
        cur.execute(market_query, market_params)
        market_sales = cur.fetchall()
        
        # Query 2: ebay_sales (eBay Collector data)
        # Filter out facsimiles, lots, bundles, reprints, and very low prices
        ebay_query = """
            SELECT grade, sale_price as price, 'ebay' as source
            FROM ebay_sales
            WHERE (
                LOWER(parsed_title) LIKE LOWER(%s) 
                OR LOWER(raw_title) LIKE LOWER(%s)
            )
            AND sale_price > 5
            AND (is_reprint IS NULL OR is_reprint = false)
            AND created_at > NOW() - INTERVAL '%s days'
            AND LOWER(parsed_title) NOT LIKE '%%facsimile%%'
            AND LOWER(raw_title) NOT LIKE '%%facsimile%%'
            AND LOWER(parsed_title) NOT LIKE '%%reprint%%'
            AND LOWER(raw_title) NOT LIKE '%%reprint%%'
            AND LOWER(raw_title) NOT LIKE '%%2nd print%%'
            AND LOWER(raw_title) NOT LIKE '%%3rd print%%'
            AND LOWER(raw_title) NOT LIKE '%%4th print%%'
            AND LOWER(parsed_title) NOT LIKE '%%lot %%'
            AND LOWER(raw_title) NOT LIKE '%%lot of%%'
            AND LOWER(parsed_title) NOT LIKE '%%set of%%'
            AND LOWER(raw_title) NOT LIKE '%%bundle%%'
        """
        ebay_params = [f'%{title}%', f'%{title}%', days]
        
        if issue:
            ebay_query += " AND issue_number = %s"
            ebay_params.append(str(issue))
        
        cur.execute(ebay_query, ebay_params)
        ebay_sales = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Combine both sources
        all_sales = list(market_sales) + list(ebay_sales)
        
        if not all_sales:
            return jsonify({'success': True, 'count': 0, 'tiers': None})
        
        # Group by grade tiers
        tiers = {
            'low': [],    # < 4.5
            'mid': [],    # 4.5 - 7.9
            'high': [],   # 8.0 - 8.9
            'top': []     # 9.0+
        }
        
        whatnot_count = 0
        ebay_count = 0
        
        for sale in all_sales:
            grade = sale.get('grade')
            price = float(sale.get('price', 0))
            source = sale.get('source', 'unknown')
            
            if price <= 0:
                continue
            
            # Count by source
            if source == 'whatnot':
                whatnot_count += 1
            elif source == 'ebay':
                ebay_count += 1
                
            if grade is None:
                tiers['mid'].append(price)
            elif grade >= 9.0:
                tiers['top'].append(price)
            elif grade >= 8.0:
                tiers['high'].append(price)
            elif grade >= 4.5:
                tiers['mid'].append(price)
            else:
                tiers['low'].append(price)
        
        # Calculate averages
        result_tiers = {}
        tier_labels = {
            'low': '<4.5',
            'mid': '4.5-7.9',
            'high': '8.0-8.9',
            'top': '9.0+'
        }
        
        for tier, prices in tiers.items():
            if prices:
                result_tiers[tier] = {
                    'avg': round(sum(prices) / len(prices), 2),
                    'min': round(min(prices), 2),
                    'max': round(max(prices), 2),
                    'count': len(prices),
                    'grades': tier_labels[tier]
                }
        
        return jsonify({
            'success': True,
            'title': title,
            'issue': issue,
            'count': len(all_sales),
            'sources': {
                'whatnot': whatnot_count,
                'ebay': ebay_count
            },
            'tiers': result_tiers if result_tiers else None
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# IMAGE UPLOAD ENDPOINTS (R2 Storage)
# ============================================

@app.route('/api/images/upload', methods=['POST'])
def api_r2_upload_image():
    """
    Upload an image to R2 storage.
    Used by Whatnot extension to upload sale images.
    
    Body: {
        "image": "base64 encoded image data",
        "sale_id": 123,  // optional - if provided, stores as sales/{id}/front.jpg
        "type": "front"  // optional - front, back, spine, centerfold (for B4Cert)
    }
    """
    if not R2_AVAILABLE:
        return jsonify({'success': False, 'error': 'Image storage not configured'}), 503
    
    data = request.get_json() or {}
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({'success': False, 'error': 'Image data required'}), 400
    
    sale_id = data.get('sale_id')
    image_type = data.get('type', 'front')
    
    if sale_id:
        # Upload directly to sale path
        result = upload_sale_image(sale_id, image_data, image_type)
    else:
        # Upload to temp location
        result = upload_temp_image(image_data, 'whatnot')
    
    return jsonify(result)


@app.route('/api/images/upload-for-sale', methods=['POST'])
def api_upload_image_for_sale():
    """
    Upload an image and associate it with a sale record.
    Updates the market_sales.image_url field.
    Now includes barcode scanning.
    
    Body: {
        "image": "base64 encoded image data",
        "sale_id": 123
    }
    """
    if not R2_AVAILABLE:
        return jsonify({'success': False, 'error': 'Image storage not configured'}), 503
    
    data = request.get_json() or {}
    image_data = data.get('image')
    sale_id = data.get('sale_id')
    
    if not image_data:
        return jsonify({'success': False, 'error': 'Image data required'}), 400
    if not sale_id:
        return jsonify({'success': False, 'error': 'sale_id required'}), 400
    
    # Upload to R2
    result = upload_sale_image(sale_id, image_data, 'front')
    
    if not result.get('success'):
        return jsonify(result), 500
    
    # Scan barcode from image
    barcode_result = scan_barcode_from_base64(image_data)
    upc_main = barcode_result.get('upc_main') if barcode_result else None
    upc_addon = barcode_result.get('upc_addon') if barcode_result else None
    is_reprint = barcode_result.get('is_reprint', False) if barcode_result else False
    
    # Update database with new image URL and barcode data
    import psycopg2
    database_url = os.environ.get('DATABASE_URL')
    
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("""
            UPDATE market_sales 
            SET image_url = %s,
                upc_main = COALESCE(%s, upc_main),
                upc_addon = COALESCE(%s, upc_addon),
                is_reprint = COALESCE(%s, is_reprint)
            WHERE id = %s
        """, (result['url'], upc_main, upc_addon, is_reprint, sale_id))
        conn.commit()
        cur.close()
        conn.close()
        
        result['upc_main'] = upc_main
        result['upc_addon'] = upc_addon
        result['is_reprint'] = is_reprint
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/images/submission', methods=['POST'])
def api_upload_submission_image():
    """
    Upload an image for a B4Cert submission (future).
    Supports front, back, spine, centerfold.
    
    Body: {
        "image": "base64 encoded image data",
        "submission_id": "uuid-string",
        "type": "front" | "back" | "spine" | "centerfold"
    }
    """
    if not R2_AVAILABLE:
        return jsonify({'success': False, 'error': 'Image storage not configured'}), 503
    
    data = request.get_json() or {}
    image_data = data.get('image')
    submission_id = data.get('submission_id')
    image_type = data.get('type', 'front')
    
    if not image_data:
        return jsonify({'success': False, 'error': 'Image data required'}), 400
    if not submission_id:
        return jsonify({'success': False, 'error': 'submission_id required'}), 400
    if image_type not in ['front', 'back', 'spine', 'centerfold']:
        return jsonify({'success': False, 'error': 'type must be front, back, spine, or centerfold'}), 400
    
    # Content moderation check BEFORE storing
    if moderate_image:
        user_id = getattr(g, 'user_id', None)
        mod_result = moderate_image(image_data)
        if mod_result.get('blocked'):
            log_moderation_incident(user_id, '/api/images/submission', mod_result, get_image_hash(image_data))
            return jsonify({
                'success': False,
                'error': 'Image rejected: inappropriate content detected.',
                'moderation': True
            }), 400
        if mod_result.get('warnings'):
            log_moderation_incident(user_id, '/api/images/submission', mod_result, get_image_hash(image_data))
    
    result = upload_submission_image(submission_id, image_data, image_type)
    return jsonify(result)


@app.route('/api/images/status', methods=['GET'])
def api_images_status():
    """Check R2 storage connection status."""
    if not R2_AVAILABLE:
        return jsonify({'connected': False, 'error': 'R2 module not loaded'})
    
    result = check_r2_connection()
    return jsonify(result)


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
# BARCODE SCANNING (Docker only)
# ============================================

@app.route('/api/barcode-test', methods=['GET'])
def barcode_test():
    """Test if pyzbar/libzbar0 is working (requires Docker deployment)."""
    try:
        from pyzbar import pyzbar
        from PIL import Image
        import io
        
        # Create a tiny test image to verify full pipeline works
        test_image = Image.new('RGB', (10, 10), color='white')
        
        # Try to decode it (will find nothing, but proves library loads)
        results = pyzbar.decode(test_image)
        
        return jsonify({
            'status': 'success',
            'message': 'pyzbar and libzbar0 loaded successfully',
            'test_decode': 'working',
            'barcodes_found': len(results)  # Should be 0 for blank image
        })
    except ImportError as e:
        return jsonify({
            'status': 'error',
            'message': f'pyzbar import failed: {str(e)}',
            'hint': 'This endpoint requires Docker deployment with libzbar0'
        }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/barcode-scan', methods=['POST'])
def barcode_scan():
    """
    Scan barcode from comic cover image.
    Returns UPC code including 5-digit add-on (used to identify reprints/variants).
    Automatically tries 0°, 90°, 180°, 270° rotations to find barcode.
    
    Body: {
        "image": "base64 encoded image data"
    }
    """
    try:
        from pyzbar import pyzbar
        from pyzbar.pyzbar import ZBarSymbol
        from PIL import Image
        import io
        import base64
        
        data = request.get_json() or {}
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'error': 'Image data required'}), 400
        
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64 to image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary (pyzbar works better with RGB)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Try scanning at different rotations (0°, 90°, 180°, 270°)
        barcodes = []
        rotation_found = 0
        
        for rotation in [0, 90, 180, 270]:
            if rotation == 0:
                rotated = image
            else:
                rotated = image.rotate(-rotation, expand=True)  # Negative for clockwise
            
            # Scan for barcodes
            found = pyzbar.decode(rotated, symbols=[ZBarSymbol.UPCA, ZBarSymbol.EAN13, ZBarSymbol.UPCE, ZBarSymbol.CODE128])
            
            if not found:
                # Try without symbol filter as fallback
                found = pyzbar.decode(rotated)
            
            if found:
                barcodes = found
                rotation_found = rotation
                break
        
        results = []
        for barcode in barcodes:
            results.append({
                'data': barcode.data.decode('utf-8'),
                'type': barcode.type,
                'rect': {
                    'left': barcode.rect.left,
                    'top': barcode.rect.top,
                    'width': barcode.rect.width,
                    'height': barcode.rect.height
                }
            })
        
        # Extract 5-digit add-on if present (used for print run identification)
        # Comics typically have UPC + 5-digit add-on
        upc_main = None
        upc_addon = None
        
        for result in results:
            code = result['data']
            # Full UPC with add-on is typically 17 digits (12 + 5)
            if len(code) >= 17:
                upc_main = code[:12]
                upc_addon = code[12:17]
            elif len(code) == 12:
                upc_main = code
            elif len(code) == 13:  # EAN-13
                upc_main = code
        
        return jsonify({
            'success': True,
            'barcodes': results,
            'count': len(results),
            'upc_main': upc_main,
            'upc_addon': upc_addon,
            'rotation_detected': rotation_found,
            'hint': 'upc_addon identifies print run: 00111 = 1st print issue 1, 00211 = 2nd print issue 1'
        })
        
    except ImportError as e:
        return jsonify({
            'success': False,
            'error': f'pyzbar not available: {str(e)}',
            'hint': 'Barcode scanning requires Docker deployment'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# BARCODE BACKFILL (Admin)
# ============================================

@app.route('/api/admin/backfill-barcodes', methods=['POST'])
@require_admin_auth
def api_backfill_barcodes():
    """
    Backfill barcode data for existing market_sales images stored in R2.
    Downloads each image, scans for barcode, updates database.
    
    Body: {
        "limit": 100,      # Max records to process (default 100, max 500)
        "dry_run": false   # If true, scan but don't update DB
    }
    
    Returns stats on processed/found/updated counts.
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import requests
    import base64
    
    if not BARCODE_AVAILABLE:
        return jsonify({
            'success': False, 
            'error': 'Barcode scanning not available (requires Docker deployment)'
        }), 503
    
    data = request.get_json() or {}
    limit = min(data.get('limit', 100), 500)  # Cap at 500 to avoid timeout
    dry_run = data.get('dry_run', False)
    
    database_url = os.environ.get('DATABASE_URL')
    conn = None
    
    stats = {
        'processed': 0,
        'barcodes_found': 0,
        'updated': 0,
        'errors': 0,
        'already_have_barcode': 0,
        'remaining': 0,
        'dry_run': dry_run,
        'details': []  # First few results for verification
    }
    
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        # Find records with R2 images but no barcode data
        cur.execute("""
            SELECT id, title, issue, image_url
            FROM market_sales
            WHERE image_url LIKE '%%.r2.dev%%'
              AND upc_main IS NULL
            ORDER BY id
            LIMIT %s
        """, (limit,))
        
        records = cur.fetchall()
        
        # Count remaining for progress tracking
        cur.execute("""
            SELECT COUNT(*) as count
            FROM market_sales
            WHERE image_url LIKE '%%.r2.dev%%'
              AND upc_main IS NULL
        """)
        total_remaining = cur.fetchone()['count']
        stats['remaining'] = total_remaining - len(records)
        
        for record in records:
            stats['processed'] += 1
            sale_id = record['id']
            image_url = record['image_url']
            
            try:
                # Download image from R2
                response = requests.get(image_url, timeout=10)
                if response.status_code != 200:
                    stats['errors'] += 1
                    continue
                
                # Convert to base64
                image_b64 = base64.b64encode(response.content).decode('utf-8')
                
                # Scan for barcode
                barcode_result = scan_barcode_from_base64(image_b64)
                
                if barcode_result:
                    stats['barcodes_found'] += 1
                    upc_main = barcode_result.get('upc_main')
                    upc_addon = barcode_result.get('upc_addon')
                    is_reprint = barcode_result.get('is_reprint', False)
                    
                    # Add to details (first 10 only)
                    if len(stats['details']) < 10:
                        stats['details'].append({
                            'id': sale_id,
                            'title': record['title'],
                            'issue': record['issue'],
                            'upc_main': upc_main,
                            'upc_addon': upc_addon,
                            'is_reprint': is_reprint
                        })
                    
                    if not dry_run:
                        # Update database
                        cur.execute("""
                            UPDATE market_sales
                            SET upc_main = %s,
                                upc_addon = %s,
                                is_reprint = %s
                            WHERE id = %s
                        """, (upc_main, upc_addon, is_reprint, sale_id))
                        conn.commit()
                        stats['updated'] += 1
                    else:
                        stats['updated'] += 1  # Would have updated
                        
            except Exception as e:
                stats['errors'] += 1
                print(f"[Backfill] Error processing sale {sale_id}: {e}")
                continue
        
        return jsonify({
            'success': True,
            **stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/admin/barcode-stats', methods=['GET'])
@require_admin_auth
def api_barcode_stats():
    """Get statistics on barcode coverage in market_sales."""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    database_url = os.environ.get('DATABASE_URL')
    conn = None
    
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        # Overall stats
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE image_url LIKE '%%.r2.dev%%') as has_r2_image,
                COUNT(*) FILTER (WHERE upc_main IS NOT NULL) as has_barcode,
                COUNT(*) FILTER (WHERE is_reprint = true) as reprints_detected,
                COUNT(*) FILTER (WHERE image_url LIKE '%%.r2.dev%%' AND upc_main IS NULL) as needs_scan
            FROM market_sales
        """)
        stats = dict(cur.fetchone())
        
        # Recent barcodes found
        cur.execute("""
            SELECT title, issue, upc_main, upc_addon, is_reprint
            FROM market_sales
            WHERE upc_main IS NOT NULL
            ORDER BY id DESC
            LIMIT 10
        """)
        stats['recent_barcodes'] = [dict(r) for r in cur.fetchall()]
        
        return jsonify({'success': True, **stats})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


# ============================================
# RUN SERVER
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
