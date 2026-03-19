"""
Feedback Blueprint - User feedback collection endpoints
Routes: /api/feedback/grading, /api/feedback/general, /api/admin/feedback
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Blueprint, jsonify, request, g
from auth import require_auth, require_admin_auth

# Create blueprint
feedback_bp = Blueprint('feedback', __name__, url_prefix='/api')


@feedback_bp.route('/feedback/grading', methods=['POST'])
@require_auth
def api_feedback_grading():
    """Save post-grading thumbs up/down feedback."""
    data = request.get_json() or {}
    rating = data.get('rating')  # 1 = thumbs up, 0 = thumbs down
    comment = data.get('comment', '').strip()
    grading_id = data.get('grading_id')
    page_context = data.get('page_context', '').strip()

    if rating is None or rating not in (0, 1):
        return jsonify({'success': False, 'error': 'Rating must be 0 or 1'}), 400

    database_url = os.environ.get('DATABASE_URL')
    conn = None
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO user_feedback (user_id, feedback_type, rating, comment, page_url)
               VALUES (%s, 'grading_rating', %s, %s, %s)""",
            (g.user_id, rating, comment or None,
             page_context or (f'Grading #{grading_id}' if grading_id else None))
        )
        conn.commit()
        cur.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] Feedback save failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


@feedback_bp.route('/feedback/general', methods=['POST'])
@require_auth
def api_feedback_general():
    """Save general feedback (5-star rating + comment)."""
    data = request.get_json() or {}
    rating = data.get('rating')  # 1-5 stars
    comment = data.get('comment', '').strip()
    page_url = data.get('page_url', '').strip()

    if rating is None or not (1 <= int(rating) <= 5):
        return jsonify({'success': False, 'error': 'Rating must be 1-5'}), 400

    if not comment:
        return jsonify({'success': False, 'error': 'Comment is required'}), 400

    database_url = os.environ.get('DATABASE_URL')
    conn = None
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO user_feedback (user_id, feedback_type, rating, comment, page_url)
               VALUES (%s, 'general', %s, %s, %s)""",
            (g.user_id, int(rating), comment, page_url or None)
        )
        conn.commit()
        cur.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] General feedback save failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


@feedback_bp.route('/admin/feedback', methods=['GET'])
@require_admin_auth
def api_admin_feedback():
    """Get all feedback entries with summary stats (admin only)."""
    database_url = os.environ.get('DATABASE_URL')
    conn = None
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        # Get all feedback entries with user email + nearby collection context
        cur.execute("""
            SELECT f.id, f.feedback_type, f.rating, f.comment, f.page_url,
                   f.grading_id, f.created_at, f.user_id, u.email,
                   c.title AS comic_title, c.issue AS comic_issue,
                   c.grade AS comic_grade, c.grade_label, c.photos AS comic_photos
            FROM user_feedback f
            LEFT JOIN users u ON f.user_id = u.id
            LEFT JOIN LATERAL (
                SELECT title, issue, grade, grade_label, photos
                FROM collections
                WHERE collections.user_id = f.user_id
                  AND collections.created_at BETWEEN f.created_at - INTERVAL '10 minutes'
                                                AND f.created_at + INTERVAL '10 minutes'
                ORDER BY ABS(EXTRACT(EPOCH FROM (collections.created_at - f.created_at)))
                LIMIT 1
            ) c ON f.feedback_type = 'grading_rating'
            ORDER BY f.created_at DESC
            LIMIT 200
        """)
        rows = cur.fetchall()

        entries = []
        for r in rows:
            # Build context: prefer page_url (new format), fall back to matched collection
            context = r['page_url']
            comic_info = None
            if r.get('comic_title'):
                comic_info = {
                    'title': r['comic_title'],
                    'issue': r['comic_issue'],
                    'grade': float(r['comic_grade']) if r['comic_grade'] else None,
                    'grade_label': r['grade_label'],
                    'photos': r['comic_photos']
                }
                if not context:
                    context = f"{r['comic_title']} #{r['comic_issue']}" if r['comic_issue'] else r['comic_title']
                    if r['comic_grade']:
                        context += f" Grade: {r['comic_grade']}"

            entries.append({
                'id': r['id'],
                'email': r['email'],
                'feedback_type': r['feedback_type'],
                'rating': r['rating'],
                'comment': r['comment'],
                'page_url': context,
                'grading_id': r['grading_id'],
                'comic': comic_info,
                'created_at': r['created_at'].isoformat() if r['created_at'] else None
            })

        # Summary stats
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE feedback_type = 'grading_rating') as grading_count,
                COUNT(*) FILTER (WHERE feedback_type = 'general') as general_count,
                COUNT(*) FILTER (WHERE feedback_type = 'grading_rating' AND rating = 1) as thumbs_up,
                COUNT(*) FILTER (WHERE feedback_type = 'grading_rating' AND rating = 0) as thumbs_down,
                ROUND(AVG(rating) FILTER (WHERE feedback_type = 'general'), 1) as avg_general_rating
            FROM user_feedback
        """)
        stats_row = cur.fetchone()

        grading_total = (stats_row['thumbs_up'] or 0) + (stats_row['thumbs_down'] or 0)
        positive_pct = round((stats_row['thumbs_up'] or 0) / grading_total * 100) if grading_total > 0 else 0

        stats = {
            'total': stats_row['total'] or 0,
            'grading_count': stats_row['grading_count'] or 0,
            'general_count': stats_row['general_count'] or 0,
            'thumbs_up': stats_row['thumbs_up'] or 0,
            'thumbs_down': stats_row['thumbs_down'] or 0,
            'positive_pct': positive_pct,
            'avg_general_rating': float(stats_row['avg_general_rating']) if stats_row['avg_general_rating'] else None
        }

        cur.close()
        return jsonify({'success': True, 'entries': entries, 'stats': stats})

    except Exception as e:
        print(f"[ERROR] Admin feedback fetch failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass
