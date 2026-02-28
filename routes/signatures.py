"""
Signatures Blueprint - Signature identification and matching
Routes: /api/signatures/match, /api/signatures/db-stats, /api/signatures/signed-sales
"""
import os
import json
import base64
from pathlib import Path
from flask import Blueprint, jsonify, request, g
import psycopg2
from psycopg2.extras import RealDictCursor

from auth import require_auth, require_approved

# Create blueprint
signatures_bp = Blueprint('signatures', __name__, url_prefix='/api/signatures')

# Module imports (set by wsgi.py)
ANTHROPIC_API_KEY = None
ANTHROPIC_AVAILABLE = False
anthropic = None

SIGNATURES_DIR = Path(__file__).parent.parent / 'signatures'
DB_PATH = SIGNATURES_DIR / 'signatures_db.json'


def init_modules(anthropic_key, anthropic_lib, anthropic_avail):
    """Initialize modules from wsgi.py"""
    global ANTHROPIC_API_KEY, anthropic, ANTHROPIC_AVAILABLE
    ANTHROPIC_API_KEY = anthropic_key
    anthropic = anthropic_lib
    ANTHROPIC_AVAILABLE = anthropic_avail


def load_signature_db():
    """Load the local signature reference database."""
    with open(DB_PATH, 'r') as f:
        return json.load(f)


def image_to_base64(image_path):
    """Convert an image file to base64 string."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def get_media_type(filename):
    """Get MIME type from filename."""
    ext = filename.lower().split('.')[-1]
    return {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif'}.get(ext, 'image/jpeg')


# -------------------------------------------------------------------
# Route: Match an unknown signature against the reference database
# -------------------------------------------------------------------
@signatures_bp.route('/match', methods=['POST'])
@require_auth
@require_approved
def api_match_signature():
    """
    Match an unknown signature image against the reference database.

    Accepts:
        image: base64-encoded signature image
        media_type: MIME type (default image/jpeg)
        sale_id: optional — link result to an eBay/market sale

    Returns:
        matches: top 3 artist matches with confidence scores
        best_match: most likely artist name (or "UNKNOWN")
        best_confidence: confidence score 0.0-1.0
        is_confident_match: true if best_confidence >= 0.7
    """
    if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
        return jsonify({'error': 'Anthropic API not available'}), 503

    data = request.get_json() or {}
    unknown_b64 = data.get('image', '')
    media_type = data.get('media_type', 'image/jpeg')
    sale_id = data.get('sale_id')

    if not unknown_b64:
        return jsonify({'error': 'No signature image provided'}), 400

    # Load reference DB
    try:
        db = load_signature_db()
    except Exception as e:
        return jsonify({'error': f'Failed to load signature database: {e}'}), 500

    # Build the comparison prompt
    content = []

    # Unknown signature first
    content.append({"type": "text", "text": "UNKNOWN SIGNATURE TO IDENTIFY (Image 1):"})
    content.append({
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": unknown_b64}
    })

    # Add one reference per artist (best quality = largest file)
    ref_index = 2
    for artist in db["artists"]:
        best_image = None
        best_size = 0
        for img_file in artist["images"]:
            img_path = SIGNATURES_DIR / img_file
            if img_path.exists():
                size = img_path.stat().st_size
                if size > best_size:
                    best_size = size
                    best_image = img_file

        if best_image:
            img_path = SIGNATURES_DIR / best_image
            img_b64 = image_to_base64(img_path)
            img_media = get_media_type(best_image)

            content.append({"type": "text", "text": f"\nREFERENCE {ref_index} — {artist['name']}:"})
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": img_media, "data": img_b64}
            })
            ref_index += 1

    # Matching instruction
    content.append({"type": "text", "text": """
Analyze the UNKNOWN SIGNATURE (Image 1) and compare it against all the reference signatures shown above.

For each reference artist, evaluate:
1. Letter formation and style similarity
2. Stroke weight and pressure patterns
3. Overall flow and slant
4. Character shapes and proportions
5. Any distinctive flourishes or marks

Return your analysis as JSON with this exact format:
{
    "matches": [
        {
            "artist": "Artist Name",
            "confidence": 0.85,
            "reasoning": "Brief explanation of why this matches or doesn't"
        }
    ],
    "best_match": "Artist Name or UNKNOWN",
    "best_confidence": 0.85,
    "is_confident_match": true,
    "notes": "Any additional observations about the signature"
}

Rules:
- List the top 3 most likely matches, sorted by confidence (highest first)
- Confidence ranges: 0.0-0.3 (no match), 0.3-0.6 (possible), 0.6-0.8 (likely), 0.8-1.0 (confident match)
- Set is_confident_match to true only if best_confidence >= 0.7
- If nothing matches well, set best_match to "UNKNOWN" with confidence < 0.3
- Be conservative — a false positive is worse than a false negative
"""})

    # Call Claude Vision
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1500,
            messages=[{"role": "user", "content": content}]
        )

        response_text = response.content[0].text

        # Parse JSON from response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            result = json.loads(response_text[json_start:json_end])
        else:
            return jsonify({'error': 'No valid JSON in API response', 'raw': response_text[:500]}), 500

    except json.JSONDecodeError:
        return jsonify({'error': 'Failed to parse API response', 'raw': response_text[:500]}), 500
    except Exception as e:
        return jsonify({'error': f'API call failed: {str(e)}'}), 500

    # Optionally save match result to DB
    if sale_id and result.get('best_match') and result.get('best_confidence', 0) >= 0.5:
        try:
            _save_match_result(sale_id, result)
        except Exception as e:
            result['db_save_error'] = str(e)

    result['success'] = True
    return jsonify(result)


def _save_match_result(sale_id, result):
    """Save a match result to the signature_matches table."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return

    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    try:
        # Find or create the creator in creator_signatures
        artist_name = result['best_match']
        cur.execute("SELECT id FROM creator_signatures WHERE LOWER(creator_name) = LOWER(%s)", (artist_name,))
        row = cur.fetchone()

        if row:
            sig_id = row['id']
        else:
            # Create the creator entry
            cur.execute("""
                INSERT INTO creator_signatures (creator_name, source)
                VALUES (%s, 'signature_matcher_v1')
                RETURNING id
            """, (artist_name,))
            sig_id = cur.fetchone()['id']

        # Insert the match
        cur.execute("""
            INSERT INTO signature_matches (sale_id, signature_id, confidence, match_method)
            VALUES (%s, %s, %s, %s)
        """, (sale_id, sig_id, result.get('best_confidence', 0), 'claude_vision_v1'))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


# -------------------------------------------------------------------
# Route: Get reference database stats
# -------------------------------------------------------------------
@signatures_bp.route('/db-stats', methods=['GET'])
def api_db_stats():
    """Return stats about the local signature reference database."""
    try:
        db = load_signature_db()
        return jsonify({
            'success': True,
            'version': db.get('version'),
            'total_artists': db['stats']['total_artists'],
            'total_images': db['stats']['total_images'],
            'quality_breakdown': {
                'high': db['stats']['high_quality'],
                'medium': db['stats']['medium_quality'],
                'low': db['stats']['low_quality']
            },
            'artists': [{'name': a['name'], 'quality': a['quality_rating'], 'image_count': len(a['images'])} for a in db['artists']],
            'missing_priority': db.get('missing_priority_artists', [])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# -------------------------------------------------------------------
# Route: Query signed eBay sales (for testing matcher against real data)
# -------------------------------------------------------------------
@signatures_bp.route('/signed-sales', methods=['GET'])
def api_signed_sales():
    """
    Get eBay sales flagged as signed, with optional creator filter.
    Useful for testing the signature matcher against real sales images.

    Query params:
        creator: filter by creator name (partial match)
        limit: max results (default 20, max 100)
        has_image: only return sales with image_url (default true)
    """
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'error': 'Database not configured'}), 503

    creator = request.args.get('creator', '')
    limit = min(int(request.args.get('limit', 20)), 100)
    has_image = request.args.get('has_image', 'true').lower() == 'true'

    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    try:
        query = """
            SELECT id, raw_title, parsed_title, canonical_title, issue_number,
                   sale_price, sale_date, grade, grading_company, creators,
                   image_url, listing_url, ebay_item_id
            FROM ebay_sales
            WHERE is_signed = TRUE
        """
        params = []

        if has_image:
            query += " AND image_url IS NOT NULL AND image_url != ''"

        if creator:
            query += " AND (creators ILIKE %s OR raw_title ILIKE %s)"
            params.extend([f'%{creator}%', f'%{creator}%'])

        query += " ORDER BY sale_date DESC NULLS LAST LIMIT %s"
        params.append(limit)

        cur.execute(query, params)
        sales = cur.fetchall()

        # Convert dates to strings
        for s in sales:
            if s.get('sale_date'):
                s['sale_date'] = s['sale_date'].isoformat()

        # Get total count
        count_query = "SELECT COUNT(*) as total FROM ebay_sales WHERE is_signed = TRUE"
        if has_image:
            count_query += " AND image_url IS NOT NULL AND image_url != ''"
        cur.execute(count_query)
        total = cur.fetchone()['total']

        # Get creator breakdown
        cur.execute("""
            SELECT creators, COUNT(*) as count
            FROM ebay_sales
            WHERE is_signed = TRUE AND creators IS NOT NULL AND creators != ''
            GROUP BY creators
            ORDER BY count DESC
            LIMIT 30
        """)
        creator_breakdown = cur.fetchall()

        return jsonify({
            'success': True,
            'total_signed': total,
            'returned': len(sales),
            'sales': sales,
            'creator_breakdown': creator_breakdown
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()
