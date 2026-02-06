"""
Collection Blueprint - User comic collection management endpoints
Routes: /api/collection/*
"""
import os
from flask import Blueprint, jsonify, request, g
import psycopg2
from psycopg2.extras import RealDictCursor

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


@collection_bp.route('/save', methods=['POST'])
@require_auth
@require_approved
def api_save_collection():
    """Save items to user's collection"""
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


@collection_bp.route('/<int:item_id>', methods=['DELETE'])
@require_auth
@require_approved
def api_delete_collection_item(item_id):
    """Delete an item from user's collection"""
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
