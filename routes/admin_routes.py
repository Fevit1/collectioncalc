"""
Admin Blueprint - Admin dashboard, user management, NLQ, and signature endpoints
Routes: /api/admin/*
"""
import os
import uuid
from flask import Blueprint, jsonify, request, g
import psycopg2
from psycopg2.extras import RealDictCursor

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Import admin functions from parent directory modules
from auth import (
    require_admin_auth, get_all_users, approve_user, reject_user,
    create_beta_code, list_beta_codes
)
from admin import (
    get_dashboard_stats, get_recent_errors, get_anthropic_usage_summary,
    natural_language_query, get_moderation_incidents, get_moderation_stats
)

# Module imports (will be set by wsgi.py)
MODERATION_AVAILABLE = False
BARCODE_AVAILABLE = False
R2_AVAILABLE = False
scan_barcode_from_base64 = None


def init_modules(moderation_available, barcode_available, r2_available, scan_barcode_func):
    """Initialize modules from wsgi.py"""
    global MODERATION_AVAILABLE, BARCODE_AVAILABLE, R2_AVAILABLE, scan_barcode_from_base64
    MODERATION_AVAILABLE = moderation_available
    BARCODE_AVAILABLE = barcode_available
    R2_AVAILABLE = r2_available
    scan_barcode_from_base64 = scan_barcode_func


@admin_bp.route('/dashboard', methods=['GET'])
@require_admin_auth
def api_admin_dashboard():
    """Get admin dashboard stats"""
    stats = get_dashboard_stats()
    return jsonify({'success': True, 'stats': stats})


@admin_bp.route('/users', methods=['GET'])
@require_admin_auth
def api_admin_users():
    """Get all users"""
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


@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@require_admin_auth
def api_approve_user(user_id):
    """Approve a user"""
    result = approve_user(user_id, g.admin_id)
    return jsonify(result)


@admin_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@require_admin_auth
def api_reject_user(user_id):
    """Reject a user"""
    data = request.get_json() or {}
    result = reject_user(user_id, g.admin_id, data.get('reason'))
    return jsonify(result)


@admin_bp.route('/beta-codes', methods=['GET'])
@require_admin_auth
def api_get_beta_codes():
    """Get all beta codes"""
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


@admin_bp.route('/beta-codes', methods=['POST'])
@require_admin_auth
def api_create_beta_code():
    """Create a new beta code"""
    data = request.get_json() or {}
    try:
        code = create_beta_code(g.admin_id, data.get('note'), data.get('uses_allowed', 1), data.get('expires_days'))
        return jsonify({'success': True, 'code': code})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/errors', methods=['GET'])
@require_admin_auth
def api_get_errors():
    """Get recent errors"""
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


@admin_bp.route('/usage', methods=['GET'])
@require_admin_auth
def api_get_usage():
    """Get Anthropic API usage stats"""
    days = request.args.get('days', 30, type=int)
    usage = get_anthropic_usage_summary(days)
    return jsonify({'success': True, 'usage': usage})


@admin_bp.route('/moderation', methods=['GET'])
@require_admin_auth
def api_get_moderation():
    """Get moderation incidents and stats"""
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


@admin_bp.route('/nlq', methods=['POST'])
@require_admin_auth
def api_nlq():
    """Natural language query endpoint"""
    data = request.get_json() or {}
    question = data.get('question', '')
    if not question:
        return jsonify({'success': False, 'error': 'Question is required'}), 400
    result = natural_language_query(question, g.admin_id)
    return jsonify(result)


@admin_bp.route('/signatures', methods=['GET'])
@require_admin_auth
def api_get_signatures():
    """Get all creator signatures with their images"""
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


@admin_bp.route('/signatures', methods=['POST'])
@require_admin_auth
def api_add_signature():
    """Add a new creator signature"""
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


@admin_bp.route('/signatures/<int:sig_id>/images', methods=['POST'])
@require_admin_auth
def api_add_signature_image(sig_id):
    """Add a reference image to a creator"""
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


@admin_bp.route('/signatures/images/<int:image_id>', methods=['DELETE'])
@require_admin_auth
def api_delete_signature_image(image_id):
    """Delete a signature reference image"""
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


@admin_bp.route('/signatures/<int:sig_id>/image', methods=['POST'])
@require_admin_auth
def api_upload_signature_image(sig_id):
    """Upload or replace signature reference image (legacy endpoint)"""
    # Redirect to new endpoint
    return api_add_signature_image(sig_id)


@admin_bp.route('/signatures/<int:sig_id>/verify', methods=['POST'])
@require_admin_auth
def api_verify_signature(sig_id):
    """Mark a signature as verified"""
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


@admin_bp.route('/backfill-barcodes', methods=['POST'])
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


@admin_bp.route('/barcode-stats', methods=['GET'])
@require_admin_auth
def api_barcode_stats():
    """Get statistics on barcode coverage in market_sales"""
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
