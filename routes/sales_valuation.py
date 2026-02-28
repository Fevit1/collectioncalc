"""
Valuation Blueprint - FMV calculation and grade-specific pricing
Routes: /api/sales/valuation, /api/sales/fmv
"""
import os
import re
import json
from decimal import Decimal
from flask import Blueprint, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor

# Create blueprint
valuation_bp = Blueprint('valuation', __name__, url_prefix='/api')


# ──────────────────────────────────────────────
# CGC Grading Cost Configuration (2026 pricing)
# Updated: January 6, 2026
# Source: https://www.cgccomics.com/submit/services-fees/cgc-grading/
# ──────────────────────────────────────────────

CGC_GRADING_COSTS = {
    "version": "2026-01-06",
    "last_updated": "2026-01-06",
    "source": "CGC official fee schedule",
    "tiers": [
        # Modern comics (1975-present), standard (non-bulk)
        {"name": "Modern",      "fee": 30, "max_value": 400, "era": "modern",  "min_year": 1975, "bulk": False},
        # Modern bulk (25+ books)
        {"name": "Modern Bulk", "fee": 27, "max_value": 400, "era": "modern",  "min_year": 1975, "bulk": True},
        # Vintage comics (pre-1975), standard
        {"name": "Vintage",      "fee": 45, "max_value": 400, "era": "vintage", "min_year": None, "bulk": False},
        # Vintage bulk (25+ books)
        {"name": "Vintage Bulk", "fee": 42, "max_value": 400, "era": "vintage", "min_year": None, "bulk": True},
        # High value (any era, $400-$1000)
        {"name": "High Value",   "fee": 105, "max_value": 1000, "era": "any",   "min_year": None, "bulk": False},
        # Unlimited value ($1000+) — 4% of FMV, $135 minimum
        {"name": "Unlimited",    "fee_pct": 0.04, "fee_min": 135, "max_value": None, "era": "any", "min_year": None, "bulk": False},
    ],
    "handling_fee": 5,  # per online invoice
}


def get_cgc_grading_cost(fmv: float, year: int = None) -> int:
    """
    Calculate CGC grading cost based on comic's fair market value and year.

    Args:
        fmv: Fair market value of the comic (raw or best estimate)
        year: Publication year (used to determine modern vs vintage tier)
              If None, assumes modern pricing (conservative — modern is cheaper)

    Returns:
        Estimated grading cost in dollars (integer, rounded up)
    """
    if fmv is None or fmv <= 0:
        fmv = 0

    is_vintage = year is not None and year < 1975

    # Unlimited value tier ($1000+)
    if fmv >= 1000:
        cost = max(fmv * 0.04, 135)
        return int(round(cost))

    # High value tier ($400-$1000)
    if fmv >= 400:
        return 105

    # Standard tier (under $400) — depends on era
    if is_vintage:
        return 45  # Vintage standard (non-bulk; bulk = 42)
    else:
        return 30  # Modern standard (non-bulk; bulk = 27)


@valuation_bp.route('/sales/valuation', methods=['GET'])
def api_sales_valuation():
    """
    Enhanced valuation endpoint for the grading results page.
    Returns grade-specific pricing with raw vs slabbed comparison and ROI.

    Uses canonical_title for precise matching, falls back to LIKE matching.
    Pulls from BOTH ebay_sales and market_sales for maximum coverage.

    Query params:
        title: Comic title (required) - matches against canonical_title first
        issue: Issue number (optional)
        grade: Numeric grade from AI grading (required, e.g. 9.6)
        days: Lookback window in days (default 365 - wider window for more data)
    """
    title = request.args.get('title', '').strip()
    issue = request.args.get('issue', '').strip()
    grade = request.args.get('grade', type=float)
    days = request.args.get('days', 365, type=int)

    if not title:
        return jsonify({'success': False, 'error': 'Title is required'}), 400
    if grade is None:
        return jsonify({'success': False, 'error': 'Grade is required'}), 400

    # Reject garbage
    if len(title) < 3 or re.match(r'^[\d\s$#%.,]+$', title):
        return jsonify({'success': False, 'error': 'Invalid title'}), 400

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'success': False, 'error': 'Database not configured'}), 500

    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        # ---------- EBAY: graded sales for this title ----------
        ebay_graded_query = """
            SELECT grade, sale_price as price, sale_date as sold_date, 'ebay' as source
            FROM ebay_sales
            WHERE graded = true AND grade IS NOT NULL AND sale_price > 5
              AND (is_reprint IS NULL OR is_reprint = false)
              AND (is_lot IS NULL OR is_lot = false)
              AND created_at > NOW() - INTERVAL '%s days'
              AND LOWER(raw_title) NOT LIKE '%%facsimile%%'
              AND LOWER(raw_title) NOT LIKE '%%reprint%%'
              AND LOWER(raw_title) NOT LIKE '%%lot of%%'
              AND LOWER(raw_title) NOT LIKE '%%bundle%%'
        """
        ebay_graded_params = [days]

        # Prefer canonical_title match, fall back to LIKE
        ebay_graded_query += """
              AND (
                  LOWER(canonical_title) = LOWER(%s)
                  OR LOWER(parsed_title) LIKE LOWER(%s)
              )
        """
        ebay_graded_params.extend([title, f'%{title}%'])

        if issue and issue not in ['null', 'undefined', 'None']:
            ebay_graded_query += " AND issue_number = %s"
            ebay_graded_params.append(str(issue))

        cur.execute(ebay_graded_query, ebay_graded_params)
        ebay_graded = cur.fetchall()

        # ---------- EBAY: raw (ungraded) sales for this title ----------
        ebay_raw_query = """
            SELECT sale_price as price, sale_date as sold_date, 'ebay' as source
            FROM ebay_sales
            WHERE (graded = false OR graded IS NULL) AND sale_price > 2
              AND (is_reprint IS NULL OR is_reprint = false)
              AND (is_lot IS NULL OR is_lot = false)
              AND created_at > NOW() - INTERVAL '%s days'
              AND LOWER(raw_title) NOT LIKE '%%facsimile%%'
              AND LOWER(raw_title) NOT LIKE '%%reprint%%'
              AND LOWER(raw_title) NOT LIKE '%%lot of%%'
              AND LOWER(raw_title) NOT LIKE '%%bundle%%'
              AND (
                  LOWER(canonical_title) = LOWER(%s)
                  OR LOWER(parsed_title) LIKE LOWER(%s)
              )
        """
        ebay_raw_params = [days, title, f'%{title}%']

        if issue and issue not in ['null', 'undefined', 'None']:
            ebay_raw_query += " AND issue_number = %s"
            ebay_raw_params.append(str(issue))

        cur.execute(ebay_raw_query, ebay_raw_params)
        ebay_raw = cur.fetchall()

        # ---------- MARKET_SALES: graded ----------
        market_graded_query = """
            SELECT grade, price, sold_at as sold_date, 'whatnot' as source
            FROM market_sales
            WHERE grade IS NOT NULL AND price > 2
              AND (is_reprint IS NULL OR is_reprint = false)
              AND (is_lot IS NULL OR is_lot = false)
              AND created_at > NOW() - INTERVAL '%s days'
              AND (
                  LOWER(canonical_title) = LOWER(%s)
                  OR LOWER(title) LIKE LOWER(%s)
                  OR LOWER(series) LIKE LOWER(%s)
              )
        """
        market_graded_params = [days, title, f'%{title}%', f'%{title}%']

        if issue and issue not in ['null', 'undefined', 'None']:
            market_graded_query += " AND (issue = %s OR issue = %s)"
            market_graded_params.extend([str(issue), issue])

        cur.execute(market_graded_query, market_graded_params)
        market_graded = cur.fetchall()

        # ---------- MARKET_SALES: raw (ungraded) ----------
        market_raw_query = """
            SELECT price, sold_at as sold_date, 'whatnot' as source
            FROM market_sales
            WHERE (grade IS NULL) AND price > 1
              AND (is_reprint IS NULL OR is_reprint = false)
              AND (is_lot IS NULL OR is_lot = false)
              AND created_at > NOW() - INTERVAL '%s days'
              AND (
                  LOWER(canonical_title) = LOWER(%s)
                  OR LOWER(title) LIKE LOWER(%s)
                  OR LOWER(series) LIKE LOWER(%s)
              )
        """
        market_raw_params = [days, title, f'%{title}%', f'%{title}%']

        if issue and issue not in ['null', 'undefined', 'None']:
            market_raw_query += " AND (issue = %s OR issue = %s)"
            market_raw_params.extend([str(issue), issue])

        cur.execute(market_raw_query, market_raw_params)
        market_raw = cur.fetchall()

        cur.close()
        conn.close()

        # ---------- Combine graded sales ----------
        all_graded = list(ebay_graded) + list(market_graded)
        all_raw = list(ebay_raw) + list(market_raw)

        # Convert Decimal to float
        def to_float(val):
            if isinstance(val, Decimal):
                return float(val)
            return float(val) if val else 0.0

        # ---------- Grade-specific analysis ----------
        # Group graded sales by grade
        grade_buckets = {}
        for sale in all_graded:
            g = to_float(sale.get('grade'))
            p = to_float(sale.get('price'))
            if g > 0 and p > 0:
                if g not in grade_buckets:
                    grade_buckets[g] = []
                grade_buckets[g].append(p)

        # 1. Exact grade match
        exact_match = grade_buckets.get(grade)
        exact_avg = None
        exact_count = 0
        if exact_match and len(exact_match) >= 1:
            exact_avg = round(sum(exact_match) / len(exact_match), 2)
            exact_count = len(exact_match)

        # 2. Nearest grade interpolation if no exact match (or supplement thin data)
        interpolated_avg = None
        grades_below = sorted([g for g in grade_buckets if g < grade], reverse=True)
        grades_above = sorted([g for g in grade_buckets if g > grade])

        if grades_below and grades_above:
            below_grade = grades_below[0]
            above_grade = grades_above[0]
            below_avg = sum(grade_buckets[below_grade]) / len(grade_buckets[below_grade])
            above_avg = sum(grade_buckets[above_grade]) / len(grade_buckets[above_grade])

            # Linear interpolation based on grade distance
            total_dist = above_grade - below_grade
            if total_dist > 0:
                weight_above = (grade - below_grade) / total_dist
                weight_below = 1 - weight_above
                interpolated_avg = round(below_avg * weight_below + above_avg * weight_above, 2)
        elif grades_below:
            # Only data below - extrapolate conservatively
            below_grade = grades_below[0]
            below_avg = sum(grade_buckets[below_grade]) / len(grade_buckets[below_grade])
            # Higher grade = higher price, add ~10% per half grade
            grade_diff = grade - below_grade
            interpolated_avg = round(below_avg * (1 + 0.2 * grade_diff), 2)
        elif grades_above:
            # Only data above - extrapolate conservatively
            above_grade = grades_above[0]
            above_avg = sum(grade_buckets[above_grade]) / len(grade_buckets[above_grade])
            # Lower grade = lower price, subtract ~10% per half grade
            grade_diff = above_grade - grade
            interpolated_avg = round(above_avg * (1 - 0.2 * grade_diff), 2)
            if interpolated_avg < 0:
                interpolated_avg = round(above_avg * 0.25, 2)

        # Pick the best graded FMV
        if exact_avg and exact_count >= 3:
            graded_fmv = exact_avg
            fmv_method = 'exact'
        elif exact_avg and interpolated_avg:
            # Blend thin exact data with interpolation
            weight = min(exact_count / 3.0, 1.0)
            graded_fmv = round(exact_avg * weight + interpolated_avg * (1 - weight), 2)
            fmv_method = 'blended'
        elif exact_avg:
            graded_fmv = exact_avg
            fmv_method = 'exact_thin'
        elif interpolated_avg:
            graded_fmv = interpolated_avg
            fmv_method = 'interpolated'
        else:
            graded_fmv = None
            fmv_method = 'none'

        # ---------- Raw FMV ----------
        raw_prices = [to_float(s.get('price')) for s in all_raw if to_float(s.get('price')) > 0]
        raw_fmv = round(sum(raw_prices) / len(raw_prices), 2) if raw_prices else None
        raw_count = len(raw_prices)

        # ---------- Fallback estimates when data is thin ----------
        comic_year = request.args.get('year', type=int, default=None)
        publisher = request.args.get('publisher', '').lower()
        estimated = False

        if graded_fmv is None and raw_fmv is None:
            # No sales data at all — generate estimate from grade/publisher/era
            grade_baselines = {
                10.0: 50, 9.8: 45, 9.6: 40, 9.4: 35, 9.2: 30, 9.0: 25,
                8.5: 20, 8.0: 18, 7.5: 16, 7.0: 14, 6.5: 12, 6.0: 10,
                5.5: 9, 5.0: 8, 4.5: 7, 4.0: 6, 3.5: 5, 3.0: 4, 2.0: 3, 1.0: 2
            }
            # Find closest grade baseline
            closest_grade = min(grade_baselines.keys(), key=lambda g: abs(g - grade))
            raw_fmv = float(grade_baselines[closest_grade])

            # Publisher multiplier
            if any(pub in publisher for pub in ['marvel', 'dc']):
                raw_fmv *= 1.3
            elif any(pub in publisher for pub in ['image', 'dark horse', 'idw']):
                raw_fmv *= 1.1

            # Era adjustment
            if comic_year:
                if comic_year < 1970:
                    raw_fmv *= 2.0
                elif comic_year < 1984:
                    raw_fmv *= 1.5
                elif comic_year < 1992:
                    raw_fmv *= 1.2

            raw_fmv = round(raw_fmv, 2)
            graded_fmv = round(raw_fmv * 1.5, 2)
            fmv_method = 'estimated'
            raw_count = 0
            estimated = True

        elif graded_fmv is None and raw_fmv is not None:
            # Have raw data but no graded sales — estimate graded as 1.5x raw
            graded_fmv = round(raw_fmv * 1.5, 2)
            fmv_method = 'estimated_from_raw'
            estimated = True

        # ---------- Grading cost (tiered by CGC 2026 schedule) ----------
        base_value = graded_fmv or raw_fmv or 0
        grading_cost = get_cgc_grading_cost(base_value, comic_year)

        # ---------- ROI calculation ----------
        slabbing_roi = None
        roi_percentage = None
        verdict = 'Insufficient data'

        if graded_fmv and raw_fmv:
            slabbing_roi = round(graded_fmv - raw_fmv - grading_cost, 2)
            if raw_fmv > 0:
                roi_percentage = round((slabbing_roi / raw_fmv) * 100, 1)

            if slabbing_roi > 50:
                verdict = 'Worth grading'
            elif slabbing_roi > 0:
                verdict = 'Marginal - consider volume'
            else:
                verdict = 'Probably not worth grading'
        elif graded_fmv:
            verdict = 'Limited raw data - compare manually'
        elif raw_fmv:
            verdict = 'No graded sales data - cannot calculate ROI'

        # ---------- Confidence score ----------
        total_graded = sum(len(v) for v in grade_buckets.values())
        if exact_count >= 10:
            confidence = 'high'
        elif exact_count >= 3 or total_graded >= 10:
            confidence = 'medium'
        elif total_graded >= 3:
            confidence = 'low'
        else:
            confidence = 'very_low'

        # ---------- Build grade price curve (for chart display) ----------
        price_curve = []
        for g in sorted(grade_buckets.keys()):
            prices = grade_buckets[g]
            price_curve.append({
                'grade': g,
                'avg_price': round(sum(prices) / len(prices), 2),
                'sales_count': len(prices),
                'min_price': round(min(prices), 2),
                'max_price': round(max(prices), 2)
            })

        # ---------- Source counts ----------
        ebay_count = len(ebay_graded) + len(ebay_raw)
        whatnot_count = len(market_graded) + len(market_raw)

        return jsonify({
            'success': True,
            'title': title,
            'issue': issue or None,
            'grade': grade,

            # Core valuation
            'graded_fmv': graded_fmv,
            'graded_sample_size': exact_count,
            'graded_total_sales': total_graded,
            'fmv_method': fmv_method,

            'raw_fmv': raw_fmv,
            'raw_sample_size': raw_count,

            # ROI
            'grading_cost': grading_cost,
            'slabbing_roi': slabbing_roi,
            'roi_percentage': roi_percentage,
            'verdict': verdict,
            'confidence': confidence,

            # Grade price curve for charts
            'price_curve': price_curve,

            # Data sources
            'sources': {
                'ebay': ebay_count,
                'whatnot': whatnot_count,
                'total': ebay_count + whatnot_count
            },

            # Metadata
            'lookback_days': days,
            'estimated': estimated or fmv_method in ['estimated', 'estimated_from_raw']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@valuation_bp.route('/sales/fmv', methods=['GET'])
def api_sales_fmv():
    """
    Get Fair Market Value data for a comic based on sales history.
    Groups sales by grade tier and returns averages.
    Now pulls from BOTH market_sales (Whatnot) AND ebay_sales.

    Query params:
        title: Comic title (required)
        issue: Issue number (optional)
        days: Number of days to look back (default 90)
    """
    title = request.args.get('title', '')
    issue = request.args.get('issue', '')
    days = request.args.get('days', 90, type=int)

    # Reject literal "null" or "undefined" issue values
    if issue in ['null', 'undefined', 'None', 'NaN']:
        issue = ''

    if not title:
        return jsonify({'success': False, 'error': 'Title is required'}), 400

    # Server-side garbage title filter (belt & suspenders with extension filter)
    if len(title) < 3:
        return jsonify({'success': False, 'count': 0, 'tiers': None})

    # Skip titles that are just numbers/symbols
    if re.match(r'^[\d\s$#%.,]+$', title):
        return jsonify({'success': False, 'count': 0, 'tiers': None})

    # Skip known garbage patterns
    title_lower = title.lower()
    garbage_patterns = [
        'available', 'remaining', 'left', 'in stock', 'bid now', 'starting',
        'mystery', 'random', 'surprise', 'bundle', 'lot of', 'choice', 'pick',
        'awesome comic', 'comic on screen', 'on screen', 'product', 'item', 'listing'
    ]
    if any(p in title_lower for p in garbage_patterns):
        return jsonify({'success': False, 'count': 0, 'tiers': None})

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'success': False, 'error': 'Database not configured'}), 500

    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        # Query 1: market_sales (Whatnot data)
        # Filter out reprints if barcode detected them
        market_query = """
            SELECT grade, price, 'whatnot' as source
            FROM market_sales
            WHERE (
                LOWER(title) LIKE LOWER(%s)
                OR LOWER(series) LIKE LOWER(%s)
                OR LOWER(raw_title) LIKE LOWER(%s)
            )
            AND price > 0
            AND (is_reprint IS NULL OR is_reprint = false)
            AND created_at > NOW() - INTERVAL '%s days'
        """
        market_params = [f'%{title}%', f'%{title}%', f'%{title}%', days]

        if issue:
            market_query += " AND (issue = %s OR issue = %s)"
            market_params.extend([str(issue), issue])

        cur.execute(market_query, market_params)
        market_sales = cur.fetchall()

        # Query 2: ebay_sales (eBay Collector data)
        # Filter out facsimiles, lots, bundles, reprints, and very low prices
        ebay_query = """
            SELECT grade, sale_price as price, 'ebay' as source
            FROM ebay_sales
            WHERE (
                LOWER(parsed_title) LIKE LOWER(%s)
                OR LOWER(raw_title) LIKE LOWER(%s)
            )
            AND sale_price > 5
            AND (is_reprint IS NULL OR is_reprint = false)
            AND created_at > NOW() - INTERVAL '%s days'
            AND LOWER(parsed_title) NOT LIKE '%%facsimile%%'
            AND LOWER(raw_title) NOT LIKE '%%facsimile%%'
            AND LOWER(parsed_title) NOT LIKE '%%reprint%%'
            AND LOWER(raw_title) NOT LIKE '%%reprint%%'
            AND LOWER(raw_title) NOT LIKE '%%2nd print%%'
            AND LOWER(raw_title) NOT LIKE '%%3rd print%%'
            AND LOWER(raw_title) NOT LIKE '%%4th print%%'
            AND LOWER(parsed_title) NOT LIKE '%%lot %%'
            AND LOWER(raw_title) NOT LIKE '%%lot of%%'
            AND LOWER(parsed_title) NOT LIKE '%%set of%%'
            AND LOWER(raw_title) NOT LIKE '%%bundle%%'
        """
        ebay_params = [f'%{title}%', f'%{title}%', days]

        if issue:
            ebay_query += " AND issue_number = %s"
            ebay_params.append(str(issue))

        cur.execute(ebay_query, ebay_params)
        ebay_sales = cur.fetchall()

        cur.close()
        conn.close()

        # Combine both sources
        all_sales = list(market_sales) + list(ebay_sales)

        if not all_sales:
            # No sales data found - provide intelligent fallback estimates
            grade_param = request.args.get('grade', type=float)
            publisher = request.args.get('publisher', '').lower()
            year = request.args.get('year', type=int)

            # Grade-based baseline values (raw comics)
            grade_baselines = {
                10.0: 50, 9.8: 45, 9.6: 40, 9.4: 35, 9.2: 30, 9.0: 25,
                8.5: 20, 8.0: 18, 7.5: 16, 7.0: 14, 6.5: 12, 6.0: 10,
                5.5: 9, 5.0: 8, 4.5: 7, 4.0: 6, 3.5: 5, 3.0: 4, 2.0: 3, 1.0: 2
            }

            # Get baseline from grade
            raw_estimate = grade_baselines.get(grade_param, 8)  # Default to $8

            # Publisher multiplier (Big 2 worth more)
            if any(pub in publisher for pub in ['marvel', 'dc']):
                raw_estimate *= 1.3
            elif any(pub in publisher for pub in ['image', 'dark horse', 'idw']):
                raw_estimate *= 1.1

            # Era adjustment (older = more valuable generally)
            if year:
                if year < 1970:  # Silver Age
                    raw_estimate *= 2.0
                elif year < 1984:  # Bronze Age
                    raw_estimate *= 1.5
                elif year < 1992:  # Copper Age
                    raw_estimate *= 1.2
                # Modern age (1992+) = no multiplier

            # Slabbed premium (typically 40-60% for raw comics without known value)
            slabbed_estimate = raw_estimate * 1.5
            grading_cost = get_cgc_grading_cost(raw_estimate, year)  # CGC 2026 schedule

            # Round to 2 decimals
            raw_estimate = round(raw_estimate, 2)
            slabbed_estimate = round(slabbed_estimate, 2)

            return jsonify({
                'success': True,
                'count': 0,
                'tiers': None,
                'raw_fmv': raw_estimate,
                'slabbed_fmv': slabbed_estimate,
                'grading_cost': grading_cost,
                'estimated': True,
                'note': 'Estimate based on grade/publisher/era - limited sales data available'
            })

        # Group by grade tiers
        tiers = {
            'low': [],    # < 4.5
            'mid': [],    # 4.5 - 7.9
            'high': [],   # 8.0 - 8.9
            'top': []     # 9.0+
        }

        whatnot_count = 0
        ebay_count = 0

        for sale in all_sales:
            sale_grade = sale.get('grade')
            price = float(sale.get('price', 0))
            source = sale.get('source', 'unknown')

            if price <= 0:
                continue

            # Count by source
            if source == 'whatnot':
                whatnot_count += 1
            elif source == 'ebay':
                ebay_count += 1

            if sale_grade is None:
                tiers['mid'].append(price)
            elif sale_grade >= 9.0:
                tiers['top'].append(price)
            elif sale_grade >= 8.0:
                tiers['high'].append(price)
            elif sale_grade >= 4.5:
                tiers['mid'].append(price)
            else:
                tiers['low'].append(price)

        # Calculate averages
        result_tiers = {}
        tier_labels = {
            'low': '<4.5',
            'mid': '4.5-7.9',
            'high': '8.0-8.9',
            'top': '9.0+'
        }

        for tier, prices in tiers.items():
            if prices:
                result_tiers[tier] = {
                    'avg': round(sum(prices) / len(prices), 2),
                    'min': round(min(prices), 2),
                    'max': round(max(prices), 2),
                    'count': len(prices),
                    'grades': tier_labels[tier]
                }

        # Calculate raw_fmv and slabbed_fmv from tier data based on user's grade
        grade_param = request.args.get('grade', 5.0, type=float)

        # Determine which tier the user's grade falls into
        if grade_param >= 9.0:
            user_tier = 'top'
        elif grade_param >= 8.0:
            user_tier = 'high'
        elif grade_param >= 4.5:
            user_tier = 'mid'
        else:
            user_tier = 'low'

        # Get raw FMV from the user's tier, or fall back to nearest available tier
        tier_priority = {
            'top': ['top', 'high', 'mid', 'low'],
            'high': ['high', 'mid', 'top', 'low'],
            'mid': ['mid', 'high', 'low', 'top'],
            'low': ['low', 'mid', 'high', 'top']
        }

        raw_fmv = 0
        for t in tier_priority.get(user_tier, ['mid']):
            if t in result_tiers:
                raw_fmv = result_tiers[t]['avg']
                break

        # Slabbed FMV: use the next tier up if available, otherwise apply 1.5x premium
        slabbed_fmv = raw_fmv * 1.5  # Default: 50% slab premium
        tier_order = ['low', 'mid', 'high', 'top']
        user_tier_idx = tier_order.index(user_tier) if user_tier in tier_order else 1
        for i in range(user_tier_idx + 1, len(tier_order)):
            higher_tier = tier_order[i]
            if higher_tier in result_tiers:
                slabbed_fmv = result_tiers[higher_tier]['avg']
                break

        # Ensure slabbed is always >= raw
        if slabbed_fmv < raw_fmv:
            slabbed_fmv = raw_fmv * 1.5

        comic_year = request.args.get('year', type=int, default=None)
        grading_cost = get_cgc_grading_cost(raw_fmv, comic_year)

        raw_fmv = round(raw_fmv, 2)
        slabbed_fmv = round(slabbed_fmv, 2)

        return jsonify({
            'success': True,
            'title': title,
            'issue': issue,
            'count': len(all_sales),
            'sources': {
                'whatnot': whatnot_count,
                'ebay': ebay_count
            },
            'tiers': result_tiers if result_tiers else None,
            'raw_fmv': raw_fmv,
            'slabbed_fmv': slabbed_fmv,
            'grading_cost': grading_cost
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
