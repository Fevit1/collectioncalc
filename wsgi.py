"""
CollectionCalc - WSGI Entry Point (v4.3.0 - Blueprint Refactor)
Flask routes for the CollectionCalc API

New in v4.3.0:
- MAJOR REFACTOR: Blueprints! Split 2,198-line monolith into modular route files
- 9 blueprints in routes/ directory (utils, auth, admin, grading, sales, images, barcodes, ebay, collection)
- 54 routes organized by functionality
- Easier to maintain, test, and extend
- Same API, cleaner code

Routes now in /routes:
- utils.py: health, debug, beta validation (3 routes)
- auth_routes.py: signup, login, verify, password reset (7 routes)
- admin_routes.py: dashboard, users, NLQ, signatures, barcode backfill (18 routes)
- grading.py: valuate, extract, cache, AI proxy (4 routes)
- sales.py: ebay-sales, market sales, FMV calculation (6 routes)
- images.py: R2 storage, uploads (4 routes)
- barcodes.py: scanning, testing (2 routes)
- ebay.py: OAuth, listing, image upload (7 routes)
- collection.py: user collection management (3 routes)

Previous version history in v4.2.2 and earlier.
"""

import os
import time
import json
import hashlib
from functools import wraps
from flask import Flask, request, jsonify, g
from flask_cors import CORS

# ============================================
# MODULE IMPORTS (with fallbacks)
# ============================================

# Import our core modules
from auth import (
    signup, login, verify_email, resend_verification, 
    forgot_password, reset_password, get_current_user,
    validate_beta_code, create_beta_code, list_beta_codes,
    approve_user, reject_user, get_pending_users, get_all_users,
    require_admin, verify_jwt, get_user_by_id, require_auth, require_approved
)
from admin import (
    log_request, log_api_usage, get_dashboard_stats,
    get_recent_errors, get_endpoint_stats, get_device_breakdown,
    natural_language_query, get_nlq_history, get_anthropic_usage_summary
)

# Import existing modules (with fallbacks)
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
        move_temp_to_sale, check_r2_connection, get_image_url, upload_image, upload_to_r2
    )
    R2_AVAILABLE = True
except ImportError as e:
    print(f"r2_storage import error: {e}")
    R2_AVAILABLE = False
    upload_sale_image = None
    upload_submission_image = None
    upload_temp_image = None
    upload_image = None
    upload_to_r2 = None

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
    log_moderation_incident = None
    get_image_hash = None


# ============================================
# BARCODE SCANNING HELPER
# ============================================

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


# ============================================
# FLASK APP SETUP
# ============================================

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')


# ============================================
# IMPORT AND REGISTER BLUEPRINTS
# ============================================

# Import all blueprints
from routes.utils import utils_bp, init_globals as utils_init_globals
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp, init_modules as admin_init_modules
from routes.grading import grading_bp, init_modules as grading_init_modules
from routes.sales import sales_bp, init_modules as sales_init_modules
from routes.images import images_bp, init_modules as images_init_modules
from routes.barcodes import barcodes_bp
from routes.ebay import ebay_bp, init_modules as ebay_init_modules
from routes.collection import collection_bp

# Initialize blueprint modules with global variables
utils_init_globals(BARCODE_AVAILABLE, MODERATION_AVAILABLE)
admin_init_modules(
    MODERATION_AVAILABLE, BARCODE_AVAILABLE, R2_AVAILABLE, scan_barcode_from_base64,
    get_moderation_incidents if MODERATION_AVAILABLE else None,
    get_moderation_stats if MODERATION_AVAILABLE else None
)
grading_init_modules(
    get_valuation_with_ebay, extract_from_base64, moderate_image,
    log_moderation_incident, get_image_hash, ANTHROPIC_API_KEY, anthropic, ANTHROPIC_AVAILABLE
)
sales_init_modules(R2_AVAILABLE, upload_sale_image, upload_image, scan_barcode_from_base64)
images_init_modules(
    R2_AVAILABLE, upload_sale_image, upload_temp_image, upload_submission_image,
    check_r2_connection, scan_barcode_from_base64, moderate_image,
    log_moderation_incident, get_image_hash
)
ebay_init_modules(
    get_auth_url, exchange_code_for_token, get_user_token, is_user_connected,
    create_listing, upload_image_to_ebay, generate_description
)

# Register all blueprints
app.register_blueprint(utils_bp)       # /, /health, /api/debug/*, /api/beta/validate
app.register_blueprint(auth_bp)        # /api/auth/*
app.register_blueprint(admin_bp)       # /api/admin/*
app.register_blueprint(grading_bp)     # /api/valuate, /api/extract, /api/cache/*, /api/messages
app.register_blueprint(sales_bp)       # /api/sales/*, /api/ebay-sales/*
app.register_blueprint(images_bp)      # /api/images/*
app.register_blueprint(barcodes_bp)    # /api/barcode-*
app.register_blueprint(ebay_bp)        # /api/ebay/*
app.register_blueprint(collection_bp)  # /api/collection/*

print("✅ All blueprints registered successfully!")


# ============================================
# REQUEST LOGGING MIDDLEWARE
# ============================================

@app.before_request
def before_request():
    """Set up request context"""
    g.start_time = time.time()
    g.user_id = None
    g.admin_id = None
    
    # Check auth token
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        payload = verify_jwt(token)
        if payload:
            g.user_id = payload.get('user_id')
            # Admin check
            user = get_user_by_id(g.user_id)
            if user and user.get('is_admin'):
                g.admin_id = g.user_id
    
    # Device type detection
    ua = request.headers.get('User-Agent', '').lower()
    if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
        g.device_type = 'mobile'
    elif 'tablet' in ua or 'ipad' in ua:
        g.device_type = 'tablet'
    else:
        g.device_type = 'desktop'


@app.after_request
def after_request(response):
    """Log requests (skip health checks)"""
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
            device_type=getattr(g, 'device_type', 'unknown'),
            error_message=error_message
        )
    except Exception as e:
        print(f"Logging error: {e}")
    
    return response


# ============================================
# RUN SERVER
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"""
╔══════════════════════════════════════════╗
║   CollectionCalc API v4.3.0 (Blueprints) ║
╠══════════════════════════════════════════╣
║  Port: {port}                              ║
║  Barcode: {BARCODE_AVAILABLE}                        ║
║  Moderation: {MODERATION_AVAILABLE}                      ║
║  R2 Storage: {R2_AVAILABLE}                       ║
║  Anthropic: {ANTHROPIC_AVAILABLE}                       ║
╚══════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=port, debug=False)
