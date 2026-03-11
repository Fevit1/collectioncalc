"""
Admin Blueprint - Admin dashboard, user management, NLQ, and signature endpoints
Routes: /api/admin/*
"""
import os
import uuid
import resend
from flask import Blueprint, jsonify, request, g
import psycopg2
from psycopg2.extras import RealDictCursor

RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'noreply@slabworthy.com')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://slabworthy.com')

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Import admin functions from parent directory modules
from auth import (
    require_admin_auth, get_all_users, approve_user, reject_user,
    create_beta_code, list_beta_codes
)
from admin import (
    get_dashboard_stats, get_recent_errors, get_anthropic_usage_summary,
    natural_language_query
)

# Moderation functions (will be passed in via init_modules if available)
get_moderation_incidents = None
get_moderation_stats = None

# Module imports (will be set by wsgi.py)
MODERATION_AVAILABLE = False
BARCODE_AVAILABLE = False
R2_AVAILABLE = False
scan_barcode_from_base64 = None


def init_modules(moderation_available, barcode_available, r2_available, scan_barcode_func,
                 get_mod_incidents_func=None, get_mod_stats_func=None):
    """Initialize modules from wsgi.py"""
    global MODERATION_AVAILABLE, BARCODE_AVAILABLE, R2_AVAILABLE, scan_barcode_from_base64
    global get_moderation_incidents, get_moderation_stats
    
    MODERATION_AVAILABLE = moderation_available
    BARCODE_AVAILABLE = barcode_available
    R2_AVAILABLE = r2_available
    scan_barcode_from_base64 = scan_barcode_func
    get_moderation_incidents = get_mod_incidents_func
    get_moderation_stats = get_mod_stats_func


@admin_bp.route('/dashboard', methods=['GET'])
@require_admin_auth
def api_admin_dashboard():
    """Get admin dashboard stats"""
    stats = get_dashboard_stats()
    return jsonify({'success': True, 'stats': stats})


@admin_bp.route('/users', methods=['GET'])
@require_admin_auth
def api_admin_users():
    """Get all users with activity data (collections, API calls, last active)"""
    users = get_all_users()
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()

    try:
        # Collection counts per user
        cur.execute("""
            SELECT user_id, COUNT(*) as count
            FROM collections
            GROUP BY user_id
        """)
        collection_counts = {r['user_id']: r['count'] for r in cur.fetchall()}

        # Slab Guard registrations per user
        cur.execute("""
            SELECT cr.user_id, COUNT(*) as count
            FROM comic_registry cr
            GROUP BY cr.user_id
        """)
        registry_counts = {r['user_id']: r['count'] for r in cur.fetchall()}

        # API calls per user (from request_logs) + last activity + endpoint breakdown
        cur.execute("""
            SELECT user_id, COUNT(*) as calls,
                   MAX(created_at) as last_activity
            FROM request_logs
            WHERE user_id IS NOT NULL
            GROUP BY user_id
        """)
        activity_map = {}
        for r in cur.fetchall():
            activity_map[r['user_id']] = {
                'calls': r['calls'],
                'last_activity': r['last_activity']
            }

        # Top endpoints per user (for activity breakdown)
        cur.execute("""
            SELECT user_id, endpoint, COUNT(*) as count
            FROM request_logs
            WHERE user_id IS NOT NULL
            GROUP BY user_id, endpoint
            ORDER BY user_id, count DESC
        """)
        endpoint_map = {}
        for r in cur.fetchall():
            uid = r['user_id']
            if uid not in endpoint_map:
                endpoint_map[uid] = {}
            # Simplify endpoint names
            ep = r['endpoint']
            if '/grade' in ep:
                label = 'grading'
            elif '/valuation' in ep or '/value' in ep:
                label = 'valuation'
            elif '/collection' in ep:
                label = 'collection'
            elif '/slab-guard' in ep or '/registry' in ep:
                label = 'slab_guard'
            elif '/signature' in ep:
                label = 'signatures'
            elif '/search' in ep or '/lookup' in ep:
                label = 'search'
            elif '/sell' in ep or '/listing' in ep:
                label = 'sell'
            else:
                label = ep.split('/')[-1] if '/' in ep else ep
            endpoint_map[uid][label] = endpoint_map[uid].get(label, 0) + r['count']

        # AI usage cost per user
        cur.execute("""
            SELECT user_id, COUNT(*) as calls,
                   SUM(COALESCE(estimated_cost_usd, 0)) as total_cost
            FROM api_usage
            WHERE user_id IS NOT NULL
            GROUP BY user_id
        """)
        ai_usage_map = {}
        for r in cur.fetchall():
            ai_usage_map[r['user_id']] = {
                'ai_calls': r['calls'],
                'ai_cost': float(r['total_cost'] or 0)
            }

        # Feedback count per user
        cur.execute("""
            SELECT user_id, COUNT(*) as count, AVG(rating) as avg_rating
            FROM user_feedback
            WHERE user_id IS NOT NULL
            GROUP BY user_id
        """)
        feedback_map = {}
        for r in cur.fetchall():
            feedback_map[r['user_id']] = {
                'count': r['count'],
                'avg_rating': round(float(r['avg_rating'] or 0), 1)
            }

        users_list = []
        for u in users:
            uid = u['id']
            act = activity_map.get(uid, {})
            ai = ai_usage_map.get(uid, {})
            fb = feedback_map.get(uid, {})
            last_act = act.get('last_activity')

            users_list.append({
                'id': uid,
                'email': u['email'],
                'display_name': u.get('display_name'),
                'email_verified': u['email_verified'],
                'is_approved': u.get('is_approved', False),
                'is_admin': u.get('is_admin', False),
                'beta_code_used': u.get('beta_code_used'),
                'created_at': u['created_at'].isoformat() if u['created_at'] else None,
                'approved_at': u['approved_at'].isoformat() if u.get('approved_at') else None,
                'last_login': u['last_login'].isoformat() if u.get('last_login') else None,
                # Activity data
                'collections': collection_counts.get(uid, 0),
                'slab_guard': registry_counts.get(uid, 0),
                'api_calls': act.get('calls', 0),
                'last_activity': last_act.isoformat() if last_act else None,
                'top_actions': endpoint_map.get(uid, {}),
                'ai_calls': ai.get('ai_calls', 0),
                'ai_cost': round(ai.get('ai_cost', 0), 4),
                'feedback_count': fb.get('count', 0),
                'feedback_avg': fb.get('avg_rating', 0)
            })

        # Sort by most recent activity first
        users_list.sort(key=lambda u: u['last_activity'] or u['created_at'] or '', reverse=True)

        return jsonify({'success': True, 'users': users_list})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


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
    
    if MODERATION_AVAILABLE and get_moderation_incidents and get_moderation_stats:
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
        # Get creators (optionally include archived)
        include_archived = request.args.get('include_archived', 'false').lower() == 'true'
        if include_archived:
            cur.execute("""
                SELECT id, creator_name, role, signature_style,
                       COALESCE(style_confidence, 0.5) AS style_confidence,
                       COALESCE(style_source, 'ai_assigned') AS style_source,
                       verified, source, notes, created_at, archived_at
                FROM creator_signatures
                ORDER BY archived_at IS NOT NULL, creator_name
            """)
        else:
            cur.execute("""
                SELECT id, creator_name, role, signature_style,
                       COALESCE(style_confidence, 0.5) AS style_confidence,
                       COALESCE(style_source, 'ai_assigned') AS style_source,
                       verified, source, notes, created_at, archived_at
                FROM creator_signatures
                WHERE archived_at IS NULL
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
            if item.get('archived_at'):
                item['archived_at'] = item['archived_at'].isoformat()
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


@admin_bp.route('/signatures/<int:sig_id>/archive', methods=['PUT'])
@require_admin_auth
def api_archive_signature(sig_id):
    """Archive a creator (soft-delete — hides from matching but preserves all data)"""
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()

    try:
        cur.execute("SELECT id, creator_name FROM creator_signatures WHERE id = %s", (sig_id,))
        creator = cur.fetchone()
        if not creator:
            return jsonify({'success': False, 'error': 'Creator not found'}), 404

        creator_name = creator['creator_name']

        cur.execute("UPDATE creator_signatures SET archived_at = NOW() WHERE id = %s", (sig_id,))
        conn.commit()

        print(f"Archived creator '{creator_name}'")

        return jsonify({'success': True, 'creator_name': creator_name, 'archived': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/signatures/<int:sig_id>/unarchive', methods=['PUT'])
@require_admin_auth
def api_unarchive_signature(sig_id):
    """Unarchive a creator (restore to active matching)"""
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()

    try:
        cur.execute("SELECT id, creator_name FROM creator_signatures WHERE id = %s", (sig_id,))
        creator = cur.fetchone()
        if not creator:
            return jsonify({'success': False, 'error': 'Creator not found'}), 404

        creator_name = creator['creator_name']

        cur.execute("UPDATE creator_signatures SET archived_at = NULL WHERE id = %s", (sig_id,))
        conn.commit()

        print(f"Unarchived creator '{creator_name}'")

        return jsonify({'success': True, 'creator_name': creator_name, 'archived': False})
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


@admin_bp.route('/signatures/<int:sig_id>/style', methods=['PUT'])
@require_admin_auth
def api_update_style(sig_id):
    """Update signature style with source + confidence tracking.
    When admin sets style, source='admin' and confidence=1.0 (ground truth).
    """
    data = request.get_json() or {}
    new_style = data.get('signature_style', '').strip().lower()
    valid_styles = {'initials', 'cursive', 'stylized', 'print', 'mixed'}

    if new_style not in valid_styles:
        return jsonify({'success': False, 'error': f'Invalid style. Must be one of: {", ".join(sorted(valid_styles))}'}), 400

    style_source = data.get('style_source', 'admin')
    style_confidence = float(data.get('style_confidence', 1.0))

    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE creator_signatures
            SET signature_style = %s,
                style_source = %s,
                style_confidence = %s
            WHERE id = %s
            RETURNING id, creator_name
        """, (new_style, style_source, style_confidence, sig_id))

        result = cur.fetchone()
        conn.commit()

        if result:
            return jsonify({'success': True, 'id': result[0], 'creator_name': result[1],
                           'signature_style': new_style, 'style_source': style_source,
                           'style_confidence': style_confidence})
        else:
            return jsonify({'success': False, 'error': 'Creator not found'}), 404
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


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


@admin_bp.route('/waitlist', methods=['GET'])
@require_admin_auth
def api_admin_waitlist():
    """Get all waitlist entries with summary stats"""
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()

    try:
        # Get all entries
        cur.execute("""
            SELECT id, email, interests, verified, created_at, verified_at, ip_address
            FROM waitlist
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()

        entries = []
        for r in rows:
            entries.append({
                'id': r['id'],
                'email': r['email'],
                'interests': r['interests'] or [],
                'verified': r['verified'],
                'created_at': r['created_at'].isoformat() if r['created_at'] else None,
                'verified_at': r['verified_at'].isoformat() if r['verified_at'] else None,
                'ip_address': r['ip_address']
            })

        # Summary stats
        total = len(entries)
        verified = sum(1 for e in entries if e['verified'])
        unverified = total - verified

        return jsonify({
            'success': True,
            'entries': entries,
            'stats': {
                'total': total,
                'verified': verified,
                'unverified': unverified
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@admin_bp.route('/waitlist/invite', methods=['POST'])
@require_admin_auth
def api_admin_waitlist_invite():
    """Generate a beta code and send invite email to a waitlist user"""
    data = request.get_json() or {}
    email = data.get('email', '').strip()

    if not email:
        return jsonify({'success': False, 'error': 'Email is required'}), 400

    try:
        # Create a beta code
        code = create_beta_code(g.admin_id, f'Waitlist invite: {email}', 1, None)

        # Send invite email via Resend
        if not RESEND_API_KEY:
            print(f"[DEV MODE] Invite email for {email} with code {code}")
            return jsonify({'success': True, 'code': code, 'email_sent': False, 'dev_mode': True})

        resend.Emails.send({
            "from": f"Slab Worthy <{RESEND_FROM_EMAIL}>",
            "to": [email],
            "subject": "You're invited to Slab Worthy!",
            "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0f0f23; color: #ffffff; padding: 40px 30px; border-radius: 12px;">
                    <h1 style="color: #6366f1; margin-bottom: 8px;">$LAB WORTHY\u2122</h1>
                    <p style="color: #a1a1aa; font-size: 14px; margin-top: 0;">AI-Powered Comic Grading &amp; Valuation</p>

                    <h2 style="color: #ffffff; margin-top: 30px;">You're Invited!</h2>
                    <p style="color: #d4d4d8;">Thanks for signing up for the Slab Worthy waitlist. We're excited to have you join our beta program!</p>

                    <p style="color: #d4d4d8;">Use this beta code to create your account:</p>

                    <div style="background: #1a1a2e; border: 2px solid #6366f1; border-radius: 8px; padding: 20px; text-align: center; margin: 24px 0;">
                        <span style="font-family: monospace; font-size: 24px; font-weight: 700; color: #f59e0b; letter-spacing: 2px;">{code}</span>
                    </div>

                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{FRONTEND_URL}/login.html"
                           style="background: linear-gradient(135deg, #6366f1, #8b5cf6);
                                  color: white;
                                  padding: 14px 36px;
                                  text-decoration: none;
                                  border-radius: 8px;
                                  display: inline-block;
                                  font-weight: 600;
                                  font-size: 16px;">
                            Create Your Account
                        </a>
                    </p>

                    <h3 style="color: #ffffff; margin-top: 30px;">What You Get</h3>
                    <ul style="color: #d4d4d8; line-height: 1.8;">
                        <li><strong>AI Comic Grading</strong> \u2014 Get an estimated grade from photos of your comics</li>
                        <li><strong>Fair Market Valuation</strong> \u2014 Know what your comics are actually worth</li>
                        <li><strong>Slab Guard\u2122</strong> \u2014 Register and protect your collection</li>
                        <li><strong>Signature ID</strong> \u2014 Identify creator signatures on signed comics</li>
                    </ul>

                    <div style="background: #1a1a2e; border: 1px solid #27272a; border-radius: 8px; padding: 16px; margin-top: 24px;">
                        <p style="color: #f59e0b; font-weight: 600; margin: 0 0 8px 0; font-size: 14px;">\u2728 You're one of our first beta testers!</p>
                        <p style="color: #d4d4d8; margin: 0; font-size: 13px; line-height: 1.6;">
                            As an early tester, you get <strong>25 free gradings per month</strong>. We're actively building based on your input \u2014 look for the <strong style="color: #8b5cf6;">Feedback</strong> button on every page to tell us what's working and what isn't. We read every single response.
                        </p>
                    </div>

                    <p style="color: #71717a; font-size: 12px; margin-top: 30px; border-top: 1px solid #27272a; padding-top: 20px;">
                        This invite was sent to {email}. If you didn't sign up for the Slab Worthy waitlist, you can ignore this email.
                    </p>
                </div>
            """
        })

        return jsonify({'success': True, 'code': code, 'email_sent': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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


# ─── Slab Guard Stats (Session 57) ─────────────────────────────────────────

@admin_bp.route('/slab-guard-stats', methods=['GET'])
@require_admin_auth
def api_slab_guard_stats():
    """
    Slab Guard operational dashboard — registrations, sightings, theft reports.
    Admin only.
    """
    conn = None
    try:
        database_url = os.environ.get('DATABASE_URL')
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        stats = {}

        # --- Registration totals by status ---
        cur.execute("""
            SELECT status, COUNT(*) as count
            FROM comic_registry
            GROUP BY status
        """)
        status_counts = {r['status']: r['count'] for r in cur.fetchall()}
        stats['registrations'] = {
            'total': sum(status_counts.values()),
            'active': status_counts.get('active', 0),
            'reported_stolen': status_counts.get('reported_stolen', 0),
            'recovered': status_counts.get('recovered', 0),
        }

        # --- Registrations over time (last 30 days) ---
        cur.execute("""
            SELECT DATE(registration_date) as date, COUNT(*) as count
            FROM comic_registry
            WHERE registration_date > NOW() - INTERVAL '30 days'
            GROUP BY DATE(registration_date)
            ORDER BY date
        """)
        stats['registrations_by_day'] = [
            {'date': str(r['date']), 'count': r['count']} for r in cur.fetchall()
        ]

        # --- Sighting reports ---
        cur.execute("SELECT COUNT(*) as total FROM sighting_reports")
        total_sightings = cur.fetchone()['total']

        cur.execute("""
            SELECT COUNT(*) as count FROM sighting_reports
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
        sightings_week = cur.fetchone()['count']

        cur.execute("""
            SELECT COUNT(*) as count FROM sighting_reports
            WHERE created_at > NOW() - INTERVAL '30 days'
        """)
        sightings_month = cur.fetchone()['count']

        cur.execute("""
            SELECT COUNT(*) as count FROM sighting_reports
            WHERE owner_notified = TRUE
        """)
        notified = cur.fetchone()['count']

        stats['sightings'] = {
            'total': total_sightings,
            'last_7_days': sightings_week,
            'last_30_days': sightings_month,
            'owner_notified': notified,
        }

        # --- Sightings by day (last 30 days) ---
        cur.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM sighting_reports
            WHERE created_at > NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        stats['sightings_by_day'] = [
            {'date': str(r['date']), 'count': r['count']} for r in cur.fetchall()
        ]

        # --- Top reported serials ---
        cur.execute("""
            SELECT sr.serial_number, COUNT(*) as report_count,
                   c.title, c.issue, cr.status
            FROM sighting_reports sr
            JOIN comic_registry cr ON sr.serial_number = cr.serial_number
            JOIN collections c ON cr.comic_id = c.id
            GROUP BY sr.serial_number, c.title, c.issue, cr.status
            ORDER BY report_count DESC
            LIMIT 10
        """)
        stats['top_reported'] = [dict(r) for r in cur.fetchall()]

        # --- Recent sighting reports ---
        cur.execute("""
            SELECT sr.id, sr.serial_number, sr.listing_url,
                   sr.reporter_email, sr.message, sr.created_at,
                   sr.owner_notified, sr.owner_response,
                   c.title, c.issue
            FROM sighting_reports sr
            JOIN comic_registry cr ON sr.serial_number = cr.serial_number
            JOIN collections c ON cr.comic_id = c.id
            ORDER BY sr.created_at DESC
            LIMIT 20
        """)
        stats['recent_sightings'] = [
            {**dict(r), 'created_at': str(r['created_at'])} for r in cur.fetchall()
        ]

        # --- Blocked reporters ---
        cur.execute("""
            SELECT COUNT(*) as count FROM blocked_reporters
            WHERE expires_at IS NULL OR expires_at > NOW()
        """)
        stats['blocked_ips'] = cur.fetchone()['count']

        # --- Owner response rates ---
        cur.execute("""
            SELECT owner_response, COUNT(*) as count
            FROM sighting_reports
            WHERE owner_response IS NOT NULL
            GROUP BY owner_response
        """)
        stats['owner_responses'] = {r['owner_response']: r['count'] for r in cur.fetchall()}

        # --- Match reports (from extension/API) ---
        try:
            cur.execute("SELECT COUNT(*) as total FROM match_reports")
            total_matches = cur.fetchone()['total']

            cur.execute("""
                SELECT status, COUNT(*) as count
                FROM match_reports
                GROUP BY status
            """)
            match_statuses = {r['status']: r['count'] for r in cur.fetchall()}

            stats['match_reports'] = {
                'total': total_matches,
                'pending': match_statuses.get('pending', 0),
                'confirmed': match_statuses.get('confirmed', 0),
                'dismissed': match_statuses.get('dismissed', 0),
            }
        except Exception:
            # match_reports table may not exist yet
            stats['match_reports'] = {'total': 0, 'note': 'table not yet created'}

        cur.close()
        return jsonify({'success': True, **stats})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
