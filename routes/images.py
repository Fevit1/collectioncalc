"""
Images Blueprint - R2 storage and image upload endpoints
Routes: /api/images/*
"""
import os
from flask import Blueprint, jsonify, request, g
import psycopg2

# Create blueprint
images_bp = Blueprint('images', __name__, url_prefix='/api/images')

# Module imports (will be set by wsgi.py)
R2_AVAILABLE = False
upload_sale_image = None
upload_temp_image = None
upload_submission_image = None
check_r2_connection = None
scan_barcode_from_base64 = None
moderate_image = None
log_moderation_incident = None
get_image_hash = None


def init_modules(r2_available, upload_sale_func, upload_temp_func, upload_sub_func, 
                 check_r2_func, scan_barcode_func, mod_image_func, log_mod_func, hash_func):
    """Initialize modules from wsgi.py"""
    global R2_AVAILABLE, upload_sale_image, upload_temp_image, upload_submission_image
    global check_r2_connection, scan_barcode_from_base64, moderate_image
    global log_moderation_incident, get_image_hash
    
    R2_AVAILABLE = r2_available
    upload_sale_image = upload_sale_func
    upload_temp_image = upload_temp_func
    upload_submission_image = upload_sub_func
    check_r2_connection = check_r2_func
    scan_barcode_from_base64 = scan_barcode_func
    moderate_image = mod_image_func
    log_moderation_incident = log_mod_func
    get_image_hash = hash_func


@images_bp.route('/upload', methods=['POST'])
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


@images_bp.route('/upload-for-sale', methods=['POST'])
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
    barcode_result = scan_barcode_from_base64(image_data) if scan_barcode_from_base64 else None
    upc_main = barcode_result.get('upc_main') if barcode_result else None
    upc_addon = barcode_result.get('upc_addon') if barcode_result else None
    is_reprint = barcode_result.get('is_reprint', False) if barcode_result else False
    
    # Update database with new image URL and barcode data
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


@images_bp.route('/submission', methods=['POST'])
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


@images_bp.route('/status', methods=['GET'])
def api_images_status():
    """Check R2 storage connection status"""
    if not R2_AVAILABLE:
        return jsonify({'connected': False, 'error': 'R2 module not loaded'})
    
    result = check_r2_connection() if check_r2_connection else {'connected': False}
    return jsonify(result)
