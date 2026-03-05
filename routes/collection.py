"""
Collection Blueprint - User comic collection management endpoints
Routes: /api/collection/*
"""
import os
from flask import Blueprint, jsonify, request, g
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Create blueprint
collection_bp = Blueprint('collection', __name__, url_prefix='/api/collection')

# Import auth decorators
from auth import require_auth, require_approved


@collection_bp.route('', methods=['GET'])
@require_auth
@require_approved
def api_get_collection():
    """Get user's saved comic collection"""
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.user_id, c.title, c.issue, c.publisher, c.year, c.grade, c.grade_label,
               c.confidence, c.defects, c.photos, c.raw_value, c.slabbed_value, c.roi, c.verdict,
               c.my_valuation, c.grading_id, c.is_slabbed, c.slab_cert_number, c.slab_company,
               c.slab_grade, c.slab_label_type, c.created_at, c.updated_at,
               cr.serial_number AS registry_serial,
               cr.status AS registry_status,
               cr.registration_date AS registry_date
        FROM collections c
        LEFT JOIN comic_registry cr ON cr.comic_id = c.id
        WHERE c.user_id = %s
        ORDER BY c.created_at DESC
    """, (g.user_id,))
    items = cur.fetchall()
    cur.close()
    conn.close()
    
    items_list = []
    for item in items:
        i = dict(item)
        
        # Convert datetime to ISO format
        for key, val in i.items():
            if hasattr(val, 'isoformat'):
                i[key] = val.isoformat()
            elif hasattr(val, '__float__'):
                i[key] = float(val)
        
        # Parse JSON fields
        if i.get('defects') and isinstance(i['defects'], str):
            i['defects'] = json.loads(i['defects'])
        if i.get('photos') and isinstance(i['photos'], str):
            i['photos'] = json.loads(i['photos'])
            
        items_list.append(i)
    
    return jsonify({'success': True, 'items': items_list})


@collection_bp.route('/save', methods=['POST'])
@require_auth
@require_approved
def api_save_collection():
    """Save items to user's collection"""
    data = request.get_json() or {}
    items = data.get('items', [])
    
    # Support both single item and items array
    if not items:
        # Check if data itself is a single item
        if data.get('title') or data.get('grade'):
            items = [data]
        else:
            return jsonify({'success': False, 'error': 'No items to save'}), 400
    
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    saved_ids = []
    for item in items:
        # Convert defects and photos to JSON strings if they're dicts
        defects_json = json.dumps(item.get('defects')) if item.get('defects') else None
        photos_json = json.dumps(item.get('photos')) if item.get('photos') else None
        
        cur.execute("""
            INSERT INTO collections (
                user_id, title, issue, publisher, year, grade, grade_label,
                confidence, defects, photos, raw_value, slabbed_value, roi, verdict,
                my_valuation, grading_id,
                is_slabbed, slab_cert_number, slab_company, slab_grade, slab_label_type
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            g.user_id,
            item.get('title'),
            item.get('issue'),
            item.get('publisher'),
            item.get('year'),
            item.get('grade'),
            item.get('grade_label'),
            item.get('confidence'),
            defects_json,
            photos_json,
            item.get('raw_value'),
            item.get('slabbed_value'),
            item.get('roi'),
            item.get('verdict'),
            item.get('my_valuation'),
            item.get('grading_id'),
            item.get('is_slabbed', False),
            item.get('slab_cert_number'),
            item.get('slab_company'),
            item.get('slab_grade'),
            item.get('slab_label_type')
        ))
        saved_ids.append(cur.fetchone()['id'])
    
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True, 'saved': len(saved_ids), 'ids': saved_ids})


@collection_bp.route('/<int:item_id>', methods=['DELETE'])
@require_auth
@require_approved
def api_delete_collection_item(item_id):
    """Delete an item from user's collection (cascades to registry, sightings)"""
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()

    try:
        # Verify the item belongs to this user first
        cur.execute("SELECT id FROM collections WHERE id = %s AND user_id = %s", (item_id, g.user_id))
        if not cur.fetchone():
            return jsonify({'success': False, 'error': 'Item not found'}), 404

        # Delete dependent rows in order (FK constraints)
        # Use savepoints so missing tables don't abort the transaction

        # 1. Sighting reports referencing this comic's registry entry
        try:
            cur.execute("SAVEPOINT sp_sightings")
            cur.execute("""
                DELETE FROM sighting_reports
                WHERE serial_number IN (
                    SELECT serial_number FROM comic_registry WHERE comic_id = %s
                )
            """, (item_id,))
            cur.execute("RELEASE SAVEPOINT sp_sightings")
        except Exception:
            cur.execute("ROLLBACK TO SAVEPOINT sp_sightings")

        # 2. Match reports referencing this comic's registry entry
        try:
            cur.execute("SAVEPOINT sp_matches")
            cur.execute("""
                DELETE FROM match_reports
                WHERE serial_number IN (
                    SELECT serial_number FROM comic_registry WHERE comic_id = %s
                )
            """, (item_id,))
            cur.execute("RELEASE SAVEPOINT sp_matches")
        except Exception:
            cur.execute("ROLLBACK TO SAVEPOINT sp_matches")

        # 3. Comic registry entries
        try:
            cur.execute("SAVEPOINT sp_registry")
            cur.execute("DELETE FROM comic_registry WHERE comic_id = %s", (item_id,))
            cur.execute("RELEASE SAVEPOINT sp_registry")
        except Exception:
            cur.execute("ROLLBACK TO SAVEPOINT sp_registry")

        # 4. Finally delete the collection item itself
        cur.execute("DELETE FROM collections WHERE id = %s AND user_id = %s RETURNING id", (item_id, g.user_id))
        deleted = cur.fetchone()
        conn.commit()

        if deleted:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Item not found'}), 404
    except Exception as e:
        conn.rollback()
        print(f"[Collection] Delete error for item {item_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@collection_bp.route('/<int:item_id>/valuation', methods=['PATCH'])
@require_auth
@require_approved
def api_update_valuation(item_id):
    """Update my_valuation for a collection item"""
    data = request.get_json() or {}
    my_valuation = data.get('my_valuation')
    
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE collections 
        SET my_valuation = %s, updated_at = NOW()
        WHERE id = %s AND user_id = %s 
        RETURNING id, my_valuation
    """, (my_valuation, item_id, g.user_id))
    
    updated = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    if updated:
        return jsonify({'success': True, 'comic_id': updated['id'], 'my_valuation': float(updated['my_valuation']) if updated['my_valuation'] else None})
    else:
        return jsonify({'success': False, 'error': 'Item not found'}), 404
