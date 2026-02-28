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


# -------------------------------------------------------------------
# Route: Signed premium analysis — compare signed vs unsigned FMV
# -------------------------------------------------------------------
@signatures_bp.route('/premium-analysis', methods=['GET'])
def api_premium_analysis():
    """
    Analyze the price premium of signed comics vs unsigned.
    Uses a single SQL query with CTEs for performance.

    Title collision handling: when unsigned comps have a very wide price range
    (max > 5x min), the pair is flagged. Post-query Python filters these
    by matching the signed sale to the nearest price tier.

    Query params:
        min_comps: minimum unsigned comparables required (default 3)
        min_price: minimum sale price to include (default 10)
    """
    import math

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'error': 'Database not configured'}), 503

    min_comps = int(request.args.get('min_comps', 3))
    min_price = float(request.args.get('min_price', 10))

    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    try:
        # Single-pass: join signed sales to unsigned aggregate stats
        # Uses title_year for disambiguation when available (prevents
        # X-Men #1 1963 vs 1991 collision). Falls back to title-only
        # matching when neither side has a year.
        cur.execute("""
            WITH signed AS (
                SELECT id, canonical_title, issue_number, grade, sale_price,
                       creators, raw_title, title_year
                FROM ebay_sales
                WHERE is_signed = TRUE
                  AND canonical_title IS NOT NULL
                  AND issue_number IS NOT NULL
                  AND sale_price > %(min_price)s
            ),
            unsigned_graded AS (
                SELECT canonical_title, issue_number, grade, title_year,
                       COUNT(*) as comp_count,
                       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sale_price) as median_price,
                       AVG(sale_price) as mean_price,
                       MIN(sale_price) as min_price,
                       MAX(sale_price) as max_price,
                       ARRAY_AGG(sale_price ORDER BY sale_price) as all_prices
                FROM ebay_sales
                WHERE is_signed = FALSE
                  AND canonical_title IS NOT NULL
                  AND issue_number IS NOT NULL
                  AND grade IS NOT NULL
                  AND sale_price > %(min_price)s
                GROUP BY canonical_title, issue_number, grade, title_year
                HAVING COUNT(*) >= %(min_comps)s
            ),
            unsigned_raw AS (
                SELECT canonical_title, issue_number,
                       NULL::numeric as grade, title_year,
                       COUNT(*) as comp_count,
                       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sale_price) as median_price,
                       AVG(sale_price) as mean_price,
                       MIN(sale_price) as min_price,
                       MAX(sale_price) as max_price,
                       ARRAY_AGG(sale_price ORDER BY sale_price) as all_prices
                FROM ebay_sales
                WHERE is_signed = FALSE
                  AND canonical_title IS NOT NULL
                  AND issue_number IS NOT NULL
                  AND grade IS NULL
                  AND graded = FALSE
                  AND sale_price > %(min_price)s
                GROUP BY canonical_title, issue_number, title_year
                HAVING COUNT(*) >= %(min_comps)s
            )
            -- Graded: match on title+issue+grade, with year when both have it
            SELECT
                s.canonical_title, s.issue_number,
                s.grade as signed_grade, s.sale_price as signed_price,
                s.creators, s.raw_title, s.title_year as signed_year,
                u.comp_count, u.median_price, u.mean_price,
                u.min_price, u.max_price, u.all_prices
            FROM signed s
            JOIN unsigned_graded u
                ON s.canonical_title = u.canonical_title
                AND s.issue_number = u.issue_number
                AND s.grade IS NOT NULL
                AND ABS(s.grade - u.grade) <= 0.5
                AND (
                    -- Both have year: must match (±2 years for reprints)
                    (s.title_year IS NOT NULL AND u.title_year IS NOT NULL
                     AND ABS(s.title_year - u.title_year) <= 2)
                    -- One or both missing year: allow match (fallback)
                    OR s.title_year IS NULL
                    OR u.title_year IS NULL
                )

            UNION ALL

            -- Raw: match on title+issue, with year when both have it
            SELECT
                s.canonical_title, s.issue_number,
                s.grade as signed_grade, s.sale_price as signed_price,
                s.creators, s.raw_title, s.title_year as signed_year,
                u.comp_count, u.median_price, u.mean_price,
                u.min_price, u.max_price, u.all_prices
            FROM signed s
            JOIN unsigned_raw u
                ON s.canonical_title = u.canonical_title
                AND s.issue_number = u.issue_number
                AND s.grade IS NULL
                AND (
                    (s.title_year IS NOT NULL AND u.title_year IS NOT NULL
                     AND ABS(s.title_year - u.title_year) <= 2)
                    OR s.title_year IS NULL
                    OR u.title_year IS NULL
                )

            ORDER BY signed_price DESC
        """, {'min_price': min_price, 'min_comps': min_comps})

        rows = cur.fetchall()

        # Also get total signed count for stats
        cur.execute("""
            SELECT COUNT(*) as total FROM ebay_sales
            WHERE is_signed = TRUE AND canonical_title IS NOT NULL
              AND issue_number IS NOT NULL AND sale_price > %s
        """, (min_price,))
        total_signed = cur.fetchone()['total']

        # Process rows with collision handling in Python
        pairs = []
        skipped_collision = 0

        for row in rows:
            signed_price = float(row['signed_price'])
            comp_min = float(row['min_price'])
            comp_max = float(row['max_price'])
            comp_count = row['comp_count']
            median_price = float(row['median_price'])
            mean_price = float(row['mean_price'])
            all_prices = [float(p) for p in row['all_prices']] if row['all_prices'] else []

            collision_detected = comp_max > comp_min * 5 and comp_count >= 6

            if collision_detected and all_prices:
                # Split into tiers on log scale
                log_mid = (math.log(comp_min) + math.log(comp_max)) / 2
                mid_price = math.exp(log_mid)

                lower_tier = [p for p in all_prices if p <= mid_price]
                upper_tier = [p for p in all_prices if p > mid_price]

                lower_median = sorted(lower_tier)[len(lower_tier)//2] if lower_tier else 0
                upper_median = sorted(upper_tier)[len(upper_tier)//2] if upper_tier else 0

                if abs(signed_price - lower_median) < abs(signed_price - upper_median):
                    tier = lower_tier
                else:
                    tier = upper_tier

                if len(tier) < min_comps:
                    skipped_collision += 1
                    continue

                median_price = sorted(tier)[len(tier)//2]
                mean_price = sum(tier) / len(tier)
                comp_count = len(tier)

            premium_vs_median = ((signed_price - median_price) / median_price) * 100
            premium_vs_mean = ((signed_price - mean_price) / mean_price) * 100

            grade_val = float(row['signed_grade']) if row['signed_grade'] is not None else None

            pairs.append({
                'comic': f"{row['canonical_title']} #{row['issue_number']}",
                'grade': grade_val,
                'signed_price': signed_price,
                'unsigned_median': round(median_price, 2),
                'unsigned_mean': round(mean_price, 2),
                'num_comps': comp_count,
                'premium_vs_median': round(premium_vs_median, 1),
                'premium_vs_mean': round(premium_vs_mean, 1),
                'collision_adjusted': collision_detected,
                'creator': row.get('creators') or ''
            })

        # Aggregate stats
        skipped_no_comps = total_signed - len(rows) - skipped_collision

        # Outlier trimming: drop top/bottom N% of premiums
        trim_pct = float(request.args.get('trim_pct', 5))  # default 5%

        def trim_outliers(values, pct):
            """Remove top and bottom pct% of values."""
            if not values or pct <= 0:
                return values
            n = len(values)
            cut = max(1, int(n * pct / 100))
            if cut * 2 >= n:
                return values  # too few to trim
            s = sorted(values)
            return s[cut:-cut]

        if pairs:
            premiums_all = sorted([p['premium_vs_median'] for p in pairs])
            premiums_trimmed = trim_outliers(premiums_all, trim_pct)
            positive_all = [p for p in premiums_all if p > 0]
            positive_trimmed = [p for p in premiums_trimmed if p > 0]

            graded_pairs = [p for p in pairs if p['grade'] is not None]
            raw_pairs = [p for p in pairs if p['grade'] is None]
            high_grade = [p for p in graded_pairs if p['grade'] and p['grade'] >= 9.0]
            mid_grade = [p for p in graded_pairs if p['grade'] and 7.0 <= p['grade'] < 9.0]
            low_grade = [p for p in graded_pairs if p['grade'] and p['grade'] < 7.0]

            def tier_stats(tier_pairs, apply_trim=True):
                if not tier_pairs:
                    return None
                prems = sorted([p['premium_vs_median'] for p in tier_pairs])
                raw_stats = {
                    'count': len(prems),
                    'mean': round(sum(prems) / len(prems), 1),
                    'median': round(prems[len(prems)//2], 1),
                    'min': round(min(prems), 1),
                    'max': round(max(prems), 1)
                }
                if apply_trim and len(prems) >= 10:
                    trimmed = trim_outliers(prems, trim_pct)
                    if trimmed:
                        raw_stats['trimmed_mean'] = round(sum(trimmed) / len(trimmed), 1)
                        raw_stats['trimmed_median'] = round(trimmed[len(trimmed)//2], 1)
                        raw_stats['trimmed_count'] = len(trimmed)
                return raw_stats

            summary = {
                'total_signed_sales': total_signed,
                'matched_pairs': len(pairs),
                'skipped_no_comps': skipped_no_comps,
                'skipped_collision': skipped_collision,
                'trim_pct': trim_pct,
                'overall_raw': {
                    'mean_premium': round(sum(premiums_all) / len(premiums_all), 1),
                    'median_premium': round(premiums_all[len(premiums_all)//2], 1),
                    'min_premium': round(min(premiums_all), 1),
                    'max_premium': round(max(premiums_all), 1),
                    'positive_count': len(positive_all),
                    'positive_pct': round(len(positive_all) / len(premiums_all) * 100, 1)
                },
                'overall_trimmed': {
                    'mean_premium': round(sum(premiums_trimmed) / len(premiums_trimmed), 1) if premiums_trimmed else None,
                    'median_premium': round(premiums_trimmed[len(premiums_trimmed)//2], 1) if premiums_trimmed else None,
                    'min_premium': round(min(premiums_trimmed), 1) if premiums_trimmed else None,
                    'max_premium': round(max(premiums_trimmed), 1) if premiums_trimmed else None,
                    'positive_count': len(positive_trimmed),
                    'positive_pct': round(len(positive_trimmed) / len(premiums_trimmed) * 100, 1) if premiums_trimmed else None,
                    'count': len(premiums_trimmed)
                },
                'by_grade_tier': {
                    'high_grade_9plus': tier_stats(high_grade),
                    'mid_grade_7to9': tier_stats(mid_grade),
                    'low_grade_under7': tier_stats(low_grade),
                    'raw_ungraded': tier_stats(raw_pairs)
                }
            }
        else:
            summary = {
                'total_signed_sales': total_signed,
                'matched_pairs': 0,
                'skipped_no_comps': skipped_no_comps,
                'skipped_collision': skipped_collision,
                'note': 'No matched pairs found. Need more unsigned comparables.'
            }

        pairs.sort(key=lambda x: -x['premium_vs_median'])

        return jsonify({
            'success': True,
            'summary': summary,
            'pairs': pairs[:50],
            'methodology': {
                'description': 'Each signed sale matched against unsigned sales of same title+issue at same grade (±0.5). Premium = (signed_price - unsigned_median) / unsigned_median.',
                'collision_handling': 'When unsigned comps span >5x price range with 6+ sales, prices are split into tiers and signed sale is matched to nearest tier.',
                'outlier_trimming': f'Top and bottom {trim_pct}% of premiums removed for trimmed stats. Adjustable via ?trim_pct=N.',
                'min_comps': min_comps,
                'min_price': min_price
            }
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500
    finally:
        cur.close()
        conn.close()
