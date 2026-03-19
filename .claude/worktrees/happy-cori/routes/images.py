"""
Images Blueprint - R2 storage and image upload endpoints
Routes: /api/images/*

Includes extra photo uploads for Slab Guard enhanced fingerprinting.
Extra photos (close-ups, defects, alternate angles) are stored in the
collections.photos JSONB under an 'extra' array.
"""
import os
import json
from flask import Blueprint, jsonify, request, g
import psycopg2
from auth import require_auth, require_approved

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


# ============================================================
# EXTRA PHOTOS — Enhanced Slab Guard fingerprinting
# ============================================================

EXTRA_PHOTO_TYPES = [
    'defect',           # Close-up of a specific defect (spine tick, corner ding, crease)
    'closeup_front',    # Zoomed-in front cover detail
    'closeup_back',     # Zoomed-in back cover detail
    'closeup_spine',    # Zoomed-in spine detail
    'edge_top',         # High-res crop of top edge
    'edge_bottom',      # High-res crop of bottom edge
    'edge_left',        # High-res crop of left edge
    'edge_right',       # High-res crop of right edge
    'alternate_front',  # Different photo of front cover (different angle/lighting)
    'alternate_back',   # Different photo of back cover
    'other',            # Anything else the user wants to document
]


@images_bp.route('/upload-extra', methods=['POST'])
@require_auth
@require_approved
def api_upload_extra_photo():
    """
    Upload an extra photo for enhanced Slab Guard fingerprinting.
    Extra photos are stored in the collections.photos JSONB under an 'extra' array.

    Body: {
        "image": "base64 encoded image data",
        "comic_id": 123,
        "photo_type": "defect" | "closeup_front" | "edge_top" | ... (see EXTRA_PHOTO_TYPES),
        "label": "Spine tick at 2 o'clock position"  // optional user description
    }

    Requires multi_photo feature (paid plans only).
    Limits: pro=4, guard=8, dealer=12 extra photos per comic.
    """
    if not R2_AVAILABLE:
        return jsonify({'success': False, 'error': 'Image storage not configured'}), 503

    data = request.get_json() or {}
    image_data = data.get('image')
    comic_id = data.get('comic_id')
    photo_type = data.get('photo_type', 'other')
    label = data.get('label', '')

    if not image_data:
        return jsonify({'success': False, 'error': 'image is required'}), 400
    if not comic_id:
        return jsonify({'success': False, 'error': 'comic_id is required'}), 400
    if photo_type not in EXTRA_PHOTO_TYPES:
        return jsonify({
            'success': False,
            'error': f'photo_type must be one of: {", ".join(EXTRA_PHOTO_TYPES)}'
        }), 400

    # Check billing: extra photos require paid plan
    try:
        from routes.billing import check_feature_access, PLANS, get_user_plan
        allowed, message = check_feature_access(g.user_id, 'extra_photos')
        if not allowed:
            return jsonify({
                'success': False,
                'error': message,
                'upgrade_required': True,
                'upgrade_url': '/pricing.html'
            }), 403

        # Get the per-comic limit for this plan
        user_plan = get_user_plan(g.user_id)
        plan_key = user_plan['plan'] if user_plan else 'free'
        plan = PLANS.get(plan_key, PLANS['free'])
        extra_limit = plan.get('extra_photos_limit', 0)
    except ImportError:
        extra_limit = 4  # Default if billing module unavailable

    database_url = os.environ.get('DATABASE_URL')
    conn = None

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # Verify comic belongs to user and get current photos
        cur.execute(
            "SELECT photos FROM collections WHERE id = %s AND user_id = %s",
            (comic_id, g.user_id)
        )
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Comic not found or access denied'}), 404

        photos = row[0]
        if photos and isinstance(photos, str):
            photos = json.loads(photos)
        if not photos or not isinstance(photos, dict):
            photos = {}

        # Check extra photo count against plan limit
        extras = photos.get('extra', [])
        if len(extras) >= extra_limit:
            return jsonify({
                'success': False,
                'error': f'Extra photo limit reached ({extra_limit} per comic on your plan)',
                'current_count': len(extras),
                'limit': extra_limit,
                'upgrade_required': True,
            }), 403

        # Content moderation check
        if moderate_image:
            mod_result = moderate_image(image_data)
            if mod_result.get('blocked'):
                if log_moderation_incident and get_image_hash:
                    log_moderation_incident(
                        g.user_id, '/api/images/upload-extra',
                        mod_result, get_image_hash(image_data)
                    )
                return jsonify({
                    'success': False,
                    'error': 'Image rejected: inappropriate content detected.',
                    'moderation': True
                }), 400

        # Upload to R2: collections/{comic_id}/extra_{index}.jpg
        extra_index = len(extras)
        r2_path = f"collections/{comic_id}/extra_{extra_index}.jpg"

        try:
            from r2_storage import upload_image
            upload_result = upload_image(image_data, r2_path)
        except ImportError:
            return jsonify({'success': False, 'error': 'R2 storage module not available'}), 503

        if not upload_result.get('success'):
            return jsonify(upload_result), 500

        photo_url = upload_result['url']

        # Append to extras array
        extras.append({
            'type': photo_type,
            'label': label,
            'url': photo_url,
        })
        photos['extra'] = extras

        # Update DB
        cur.execute(
            "UPDATE collections SET photos = %s, updated_at = NOW() WHERE id = %s AND user_id = %s",
            (json.dumps(photos), comic_id, g.user_id)
        )
        conn.commit()

        return jsonify({
            'success': True,
            'url': photo_url,
            'photo_type': photo_type,
            'label': label,
            'index': extra_index,
            'extra_count': len(extras),
            'limit': extra_limit,
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Upload extra photo error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if conn:
            cur.close()
            conn.close()


@images_bp.route('/delete-extra', methods=['POST'])
@require_auth
@require_approved
def api_delete_extra_photo():
    """
    Delete an extra photo from a comic's enhanced fingerprint set.

    Body: {
        "comic_id": 123,
        "index": 2       // index in the extras array to remove
    }
    """
    data = request.get_json() or {}
    comic_id = data.get('comic_id')
    index = data.get('index')

    if not comic_id or index is None:
        return jsonify({'success': False, 'error': 'comic_id and index are required'}), 400

    database_url = os.environ.get('DATABASE_URL')
    conn = None

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # Get current photos
        cur.execute(
            "SELECT photos FROM collections WHERE id = %s AND user_id = %s",
            (comic_id, g.user_id)
        )
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Comic not found or access denied'}), 404

        photos = row[0]
        if photos and isinstance(photos, str):
            photos = json.loads(photos)
        if not photos or not isinstance(photos, dict):
            return jsonify({'success': False, 'error': 'No photos found'}), 404

        extras = photos.get('extra', [])
        if index < 0 or index >= len(extras):
            return jsonify({'success': False, 'error': f'Invalid index {index} (have {len(extras)} extras)'}), 400

        # Remove the photo (R2 object remains — could add cleanup later)
        removed = extras.pop(index)
        photos['extra'] = extras

        cur.execute(
            "UPDATE collections SET photos = %s, updated_at = NOW() WHERE id = %s AND user_id = %s",
            (json.dumps(photos), comic_id, g.user_id)
        )
        conn.commit()

        return jsonify({
            'success': True,
            'removed': removed,
            'extra_count': len(extras),
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Delete extra photo error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if conn:
            cur.close()
            conn.close()


@images_bp.route('/extra-types', methods=['GET'])
def api_extra_photo_types():
    """Return the list of valid extra photo types with descriptions."""
    types = [
        {'type': 'defect', 'description': 'Close-up of a specific defect (spine tick, corner ding, crease)'},
        {'type': 'closeup_front', 'description': 'Zoomed-in front cover detail'},
        {'type': 'closeup_back', 'description': 'Zoomed-in back cover detail'},
        {'type': 'closeup_spine', 'description': 'Zoomed-in spine detail'},
        {'type': 'edge_top', 'description': 'High-resolution crop of top edge'},
        {'type': 'edge_bottom', 'description': 'High-resolution crop of bottom edge'},
        {'type': 'edge_left', 'description': 'High-resolution crop of left edge'},
        {'type': 'edge_right', 'description': 'High-resolution crop of right edge'},
        {'type': 'alternate_front', 'description': 'Different photo of front cover (different angle/lighting)'},
        {'type': 'alternate_back', 'description': 'Different photo of back cover'},
        {'type': 'other', 'description': 'Any other identifying detail'},
    ]
    return jsonify({'success': True, 'types': types})
