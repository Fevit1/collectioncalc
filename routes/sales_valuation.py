"""
Valuation Blueprint - FMV calculation and grade-specific pricing
Routes: /api/sales/valuation, /api/sales/fmv

Methodology (Session 68+):
- Median-based FMV (resistant to outliers vs arithmetic mean)
- Percentile outlier trimming (top/bottom 5%)
- Bootstrap 95% confidence intervals (1000 iterations, seed=42)
"""
import os
import re
import json
import random
from decimal import Decimal
from flask import Blueprint, jsonify, request, g
import psycopg2
from psycopg2.extras import RealDictCursor
from title_matching import qualifier_title_clause, compose_qualified_title
from lookup_demand import record_lookup_async

# Create blueprint
valuation_bp = Blueprint('valuation', __name__, url_prefix='/api')


def _record_demand(endpoint, title, issue, issue_type, requested_grade,
                   comp_count, graded_count, exact_count, fmv_method, estimated):
    """Fire-and-forget demand log for a completed lookup. NEVER raises, NEVER
    blocks the response (the actual insert is on a daemon thread). user_id /
    admin flag come from the request context that before_request() populated."""
    try:
        record_lookup_async(
            os.environ.get('DATABASE_URL'),
            endpoint=endpoint,
            title=title or None,
            canonical_title=compose_qualified_title(title, issue_type) if title else None,
            issue=str(issue) if issue not in (None, '') else None,
            issue_type=issue_type or None,
            requested_grade=requested_grade,
            comp_count=comp_count,
            graded_count=graded_count,
            exact_count=exact_count,
            fmv_method=fmv_method,
            estimated=bool(estimated),
            no_data=(not comp_count),
            user_id=getattr(g, 'user_id', None),
            is_internal=bool(getattr(g, 'admin_id', None)),
        )
    except Exception:
        pass  # instrumentation must never affect the valuation response


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


# ──────────────────────────────────────────────
# Statistical Utility Functions
# Same methodology as premium analysis engine
# ──────────────────────────────────────────────

def percentile_trim(prices, pct=5):
    """Remove top/bottom pct% of prices. Returns trimmed sorted list."""
    if not prices or pct <= 0:
        return prices
    n = len(prices)
    cut = max(1, int(n * pct / 100))
    if cut * 2 >= n:
        return prices  # Too few to trim
    s = sorted(prices)
    return s[cut:-cut]


def compute_median(prices):
    """Simple median of a list of numbers."""
    if not prices:
        return None
    s = sorted(prices)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def bootstrap_ci_median(values, n_iter=1000, ci=95):
    """
    Bootstrap 95% confidence interval for median.
    Returns (ci_lo, ci_hi) or (None, None) if < 5 values.
    Deterministic seed=42 for reproducibility.
    """
    if not values or len(values) < 5:
        return None, None
    rng = random.Random(42)
    medians = []
    for _ in range(n_iter):
        sample = sorted([rng.choice(values) for _ in range(len(values))])
        medians.append(sample[len(sample) // 2])
    medians.sort()
    lo_idx = int(n_iter * (100 - ci) / 200)
    hi_idx = int(n_iter * (100 + ci) / 200)
    return round(medians[lo_idx], 2), round(medians[hi_idx], 2)


def compute_variant_disclosure(base_count, excluded_variant_count,
                               pct_threshold=30.0, min_excluded=3, min_total=5):
    """Disclosure ABOUT the base-cover FMV — never changes the number itself.
    Fires only when excluded variants are a material share AND the sample is big
    enough that the % isn't thin-data noise (thin samples already read low via the
    sample-size confidence score)."""
    total = base_count + excluded_variant_count
    pct = round(100.0 * excluded_variant_count / total, 1) if total else 0.0
    fires = (total >= min_total and excluded_variant_count >= min_excluded
             and pct >= pct_threshold)
    return {
        'variant_excluded': fires,
        'variant_excluded_pct': pct,
        'variant_excluded_count': excluded_variant_count,
        'variant_disclosure': (
            "Estimate reflects the standard cover; variant sales excluded."
            if fires else None),
    }


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
    issue_type = request.args.get('issue_type', '').strip()  # Batch 8: series-type qualifier
    grade = request.args.get('grade', type=float)
    days = request.args.get('days', 365, type=int)

    if not title:
        return jsonify({'success': False, 'error': 'Title is required'}), 400
    if grade is None:
        return jsonify({'success': False, 'error': 'Grade is required'}), 400

    # Reject garbage
    if len(title) < 3 or re.match(r'^[\d\s$#%.,]+$', title):
        return jsonify({'success': False, 'error': 'Invalid title'}), 400

    # Honesty gate (server belt — non-negotiable backstop). Without a known issue,
    # the per-table queries below simply OMIT the issue filter and blend EVERY
    # issue of the title into one confident FMV. Refuse to price instead: the
    # client shows the grade and an editable issue field. The signal is OBJECTIVE
    # (issue empty/sentinel ⇒ unknown), never model self-report — a weak extractor
    # reports confident-wrong, so self-report is untrustworthy. '?' is the app's
    # own unknown-issue sentinel; treat it (and the null/undefined strings) as empty.
    if not issue or issue in ('null', 'undefined', 'None', '?'):
        return jsonify({
            'success': False,
            'issue_required': True,
            'error': 'Issue number needed to price this comic'
        }), 200

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'success': False, 'error': 'Database not configured'}), 500

    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        # Batch 8: qualifier-precise title match (shared helper). A qualified
        # query ("Giant-Size X-Men") matches only its own rows; a plain query
        # ("X-Men") excludes Giant-Size/Annual/Special. Per-table column sets.
        ebay_title_sql, ebay_title_params = qualifier_title_clause(
            'canonical_title', ['parsed_title'], title, issue_type)
        market_title_sql, market_title_params = qualifier_title_clause(
            'canonical_title', ['title', 'series'], title, issue_type)

        # ---------- EBAY: graded sales for this title ----------
        # Batch 5: filter on the actual SALE date, not created_at (the capture
        # timestamp). created_at goes empty during a capture stall and silently
        # ages out the whole corpus. COALESCE keeps rows whose sale_date is NULL
        # by falling back to created_at (documented mixed-semantics fallback).
        ebay_graded_query = """
            SELECT grade, sale_price as price, sale_date as sold_date, 'ebay' as source, is_variant
            FROM ebay_sales
            WHERE graded = true AND grade IS NOT NULL AND sale_price > 5
              AND (is_reprint IS NULL OR is_reprint = false)
              AND (is_lot IS NULL OR is_lot = false)
              AND COALESCE(sale_date, created_at) > NOW() - INTERVAL '%s days'
              AND LOWER(raw_title) NOT LIKE '%%facsimile%%'
              AND LOWER(raw_title) NOT LIKE '%%reprint%%'
              AND LOWER(raw_title) NOT LIKE '%%lot of%%'
              AND LOWER(raw_title) NOT LIKE '%%bundle%%'
              AND LOWER(raw_title) NOT LIKE '%%complete set%%'
              AND LOWER(raw_title) NOT LIKE '%%complete run%%'
              AND LOWER(raw_title) NOT LIKE '%%full run%%'
              AND LOWER(raw_title) NOT LIKE '%%all covers%%'
              AND raw_title !~* '\\d+\\s+(extra|more)\\s+(book|comic|issue)s?'
              AND raw_title !~* '#\\s*\\d{1,4}\\s*[-–]\\s*\\d{2,4}'
              AND raw_title !~* '[a-z]\\s*#?\\d{1,4}\\s*[+&]\\s*[a-z][a-z0-9 .''-]*?\\d{1,4}'
        """
        ebay_graded_params = [days]

        # Batch 8: qualifier-precise title match (was canonical=OR parsed LIKE)
        ebay_graded_query += f" AND {ebay_title_sql}"
        ebay_graded_params.extend(ebay_title_params)

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
              AND (is_variant IS NULL OR is_variant = false)
              AND COALESCE(sale_date, created_at) > NOW() - INTERVAL '%s days'
              AND LOWER(raw_title) NOT LIKE '%%facsimile%%'
              AND LOWER(raw_title) NOT LIKE '%%reprint%%'
              AND LOWER(raw_title) NOT LIKE '%%lot of%%'
              AND LOWER(raw_title) NOT LIKE '%%bundle%%'
              AND LOWER(raw_title) NOT LIKE '%%complete set%%'
              AND LOWER(raw_title) NOT LIKE '%%complete run%%'
              AND LOWER(raw_title) NOT LIKE '%%full run%%'
              AND LOWER(raw_title) NOT LIKE '%%all covers%%'
              AND raw_title !~* '\\d+\\s+(extra|more)\\s+(book|comic|issue)s?'
              AND raw_title !~* '#\\s*\\d{1,4}\\s*[-–]\\s*\\d{2,4}'
              AND raw_title !~* '[a-z]\\s*#?\\d{1,4}\\s*[+&]\\s*[a-z][a-z0-9 .''-]*?\\d{1,4}'
        """
        # Batch 8: qualifier-precise title match
        ebay_raw_query += f" AND {ebay_title_sql}"
        ebay_raw_params = [days] + list(ebay_title_params)

        if issue and issue not in ['null', 'undefined', 'None']:
            ebay_raw_query += " AND issue_number = %s"
            ebay_raw_params.append(str(issue))

        cur.execute(ebay_raw_query, ebay_raw_params)
        ebay_raw = cur.fetchall()

        # ---------- MARKET_SALES: graded ----------
        market_graded_query = """
            SELECT grade, price, sold_at as sold_date, 'whatnot' as source, is_variant
            FROM market_sales
            WHERE grade IS NOT NULL AND price > 2
              AND (is_reprint IS NULL OR is_reprint = false)
              AND (is_lot IS NULL OR is_lot = false)
              AND COALESCE(sold_at, created_at) > NOW() - INTERVAL '%s days'
        """
        # Batch 8: qualifier-precise title match
        market_graded_query += f" AND {market_title_sql}"
        market_graded_params = [days] + list(market_title_params)

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
              AND (is_variant IS NULL OR is_variant = false)
              AND COALESCE(sold_at, created_at) > NOW() - INTERVAL '%s days'
        """
        # Batch 8: qualifier-precise title match
        market_raw_query += f" AND {market_title_sql}"
        market_raw_params = [days] + list(market_title_params)

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
        excluded_variant_count = 0   # variants set aside from the comp pool (for disclosure only)
        for sale in all_graded:
            if sale.get('is_variant'):
                excluded_variant_count += 1
                continue   # keep the priced pool to the standard cover (identical to Bucket 1)
            g = to_float(sale.get('grade'))
            p = to_float(sale.get('price'))
            if g > 0 and p > 0:
                if g not in grade_buckets:
                    grade_buckets[g] = []
                grade_buckets[g].append(p)

        # 1. Exact grade match — median with outlier trimming
        exact_match = grade_buckets.get(grade)
        exact_avg = None
        exact_count = 0
        ci_95_low = None
        ci_95_high = None
        if exact_match and len(exact_match) >= 1:
            trimmed = percentile_trim(exact_match)
            exact_avg = round(compute_median(trimmed), 2)
            exact_count = len(exact_match)
            # Bootstrap CI on the trimmed data
            ci_95_low, ci_95_high = bootstrap_ci_median(trimmed)

        # 2. Nearest grade interpolation if no exact match (or supplement thin data)
        interpolated_avg = None
        grades_below = sorted([g for g in grade_buckets if g < grade], reverse=True)
        grades_above = sorted([g for g in grade_buckets if g > grade])

        if grades_below and grades_above:
            below_grade = grades_below[0]
            above_grade = grades_above[0]
            below_median = compute_median(percentile_trim(grade_buckets[below_grade]))
            above_median = compute_median(percentile_trim(grade_buckets[above_grade]))

            # Linear interpolation based on grade distance
            total_dist = above_grade - below_grade
            if total_dist > 0:
                weight_above = (grade - below_grade) / total_dist
                weight_below = 1 - weight_above
                interpolated_avg = round(below_median * weight_below + above_median * weight_above, 2)
        elif grades_below:
            # Only data below - extrapolate conservatively
            below_grade = grades_below[0]
            below_median = compute_median(percentile_trim(grade_buckets[below_grade]))
            # Higher grade = higher price, add ~10% per half grade
            grade_diff = grade - below_grade
            interpolated_avg = round(below_median * (1 + 0.2 * grade_diff), 2)
        elif grades_above:
            # Only data above - extrapolate conservatively
            above_grade = grades_above[0]
            above_median = compute_median(percentile_trim(grade_buckets[above_grade]))
            # Lower grade = lower price, subtract ~10% per half grade
            grade_diff = above_grade - grade
            interpolated_avg = round(above_median * (1 - 0.2 * grade_diff), 2)
            if interpolated_avg < 0:
                interpolated_avg = round(above_median * 0.25, 2)

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

        # ---------- Raw FMV — median with outlier trimming ----------
        raw_prices = [to_float(s.get('price')) for s in all_raw if to_float(s.get('price')) > 0]
        if raw_prices:
            trimmed_raw = percentile_trim(raw_prices)
            raw_fmv = round(compute_median(trimmed_raw), 2)
        else:
            raw_fmv = None
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
        # Conditional variant-exclusion disclosure (does NOT change the FMV).
        disclosure = compute_variant_disclosure(total_graded, excluded_variant_count)
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
            trimmed_curve = percentile_trim(prices)
            price_curve.append({
                'grade': g,
                'avg_price': round(compute_median(trimmed_curve), 2),
                'sales_count': len(prices),
                'min_price': round(min(prices), 2),
                'max_price': round(max(prices), 2)
            })

        # ---------- Source counts ----------
        ebay_count = len(ebay_graded) + len(ebay_raw)
        whatnot_count = len(market_graded) + len(market_raw)

        # Lookup-demand instrumentation (non-blocking, additive — see lookup_demand.py)
        _record_demand('valuation', title, issue, issue_type, grade,
                       total_graded + raw_count, total_graded, exact_count,
                       fmv_method,
                       estimated or fmv_method in ['estimated', 'estimated_from_raw'])

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

            # Variant-exclusion disclosure ABOUT the base-cover number (FMV unchanged)
            'variant_excluded': disclosure['variant_excluded'],
            'variant_excluded_pct': disclosure['variant_excluded_pct'],
            'variant_excluded_count': disclosure['variant_excluded_count'],
            'variant_disclosure': disclosure['variant_disclosure'],

            'raw_fmv': raw_fmv,
            'raw_sample_size': raw_count,

            # Confidence interval (null when interpolated/estimated or < 5 exact matches)
            'ci_95_low': ci_95_low,
            'ci_95_high': ci_95_high,

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
        days: Number of days to look back (default 180)
    """
    title = request.args.get('title', '')
    issue = request.args.get('issue', '')
    issue_type = request.args.get('issue_type', '').strip()  # Batch 8: series-type qualifier
    # Batch 5: default lookback widened 90 -> 180 days. Now that the window
    # filters on actual sale date (not capture time), 90 days of true sales is
    # sparser; 180 keeps tier sample sizes healthy without reaching into stale
    # pricing. Callers may still override via ?days=.
    days = request.args.get('days', 180, type=int)

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

        # Batch 8: qualifier-precise title match (shared helper). fmv column sets
        # add raw_title to the LIKE fallback vs the valuation endpoint.
        fmv_ebay_title_sql, fmv_ebay_title_params = qualifier_title_clause(
            'canonical_title', ['parsed_title', 'raw_title'], title, issue_type)
        fmv_market_title_sql, fmv_market_title_params = qualifier_title_clause(
            'canonical_title', ['title', 'series', 'raw_title'], title, issue_type)

        # Query 1: market_sales (Whatnot data)
        # Filter out reprints if barcode detected them
        # Batch 5: filter on actual sale date (sold_at), fallback to created_at
        # when NULL — created_at alone ages out the corpus during capture stalls.
        market_query = f"""
            SELECT grade, price, 'whatnot' as source
            FROM market_sales
            WHERE {fmv_market_title_sql}
            AND price > 0
            AND (is_reprint IS NULL OR is_reprint = false)
            AND (is_lot IS NULL OR is_lot = false)
            AND (is_variant IS NULL OR is_variant = false)
            AND COALESCE(sold_at, created_at) > NOW() - INTERVAL '%s days'
        """
        market_params = list(fmv_market_title_params) + [days]

        if issue:
            market_query += " AND (issue = %s OR issue = %s)"
            market_params.extend([str(issue), issue])

        cur.execute(market_query, market_params)
        market_sales = cur.fetchall()

        # Query 2: ebay_sales (eBay Collector data)
        # Filter out facsimiles, lots, bundles, reprints, and very low prices
        # Batch 8: qualifier-precise title match (replaces the parsed/raw LIKE pair).
        ebay_query = f"""
            SELECT grade, sale_price as price, 'ebay' as source
            FROM ebay_sales
            WHERE {fmv_ebay_title_sql}
            AND sale_price > 5
            AND (is_reprint IS NULL OR is_reprint = false)
            AND (is_variant IS NULL OR is_variant = false)
            AND COALESCE(sale_date, created_at) > NOW() - INTERVAL '%s days'
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
        ebay_params = list(fmv_ebay_title_params) + [days]

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

            # Lookup-demand: this is the NO-DATA branch — the highest-value signal
            # (a title users search that we can't price). Non-blocking, additive.
            _record_demand('fmv', title, issue, issue_type,
                           request.args.get('grade', type=float),
                           0, None, None, 'estimated', True)

            return jsonify({
                'success': True,
                'count': 0,
                'tiers': None,
                'raw_fmv': raw_estimate,
                'slabbed_fmv': slabbed_estimate,
                'grading_cost': grading_cost,
                'estimated': True,
                'confidence': 'very_low',
                'fmv_sample_size': 0,
                'low_confidence': True,
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
        used_tier = None
        for t in tier_priority.get(user_tier, ['mid']):
            if t in result_tiers:
                raw_fmv = result_tiers[t]['avg']
                used_tier = t
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

        # Batch 5: confidence signal for the displayed FMV, based on how many
        # sales back the tier we actually priced from (mirrors the
        # /sales/valuation thresholds). Previously fmv returned a point-estimate
        # tier average — possibly off a SINGLE sale — with no confidence at all,
        # so consumers like the Whatnot overlay could show false precision.
        # NOTE: this only EXPOSES the signal; the overlay must still render it
        # (tracked as a separate UI follow-up, see Batch 5 notes).
        fmv_sample = result_tiers.get(used_tier, {}).get('count', 0) if used_tier else 0
        if fmv_sample >= 10:
            confidence = 'high'
        elif fmv_sample >= 5:
            confidence = 'medium'
        elif fmv_sample >= 2:
            confidence = 'low'
        else:
            confidence = 'very_low'

        # Lookup-demand instrumentation (non-blocking, additive — see lookup_demand.py)
        _record_demand('fmv', title, issue, issue_type, grade_param,
                       len(all_sales), None, None, used_tier, False)

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
            'grading_cost': grading_cost,
            'confidence': confidence,
            'fmv_sample_size': fmv_sample,
            'low_confidence': fmv_sample < 5
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
