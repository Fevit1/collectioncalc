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
import time
from decimal import Decimal
from flask import Blueprint, jsonify, request, g
import psycopg2
import db as _dbpool
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
    # ⚠️ HARD CONSTRAINT FOR ANYONE DESIGNING A CONFIDENCE BOUND ON FMV
    # (recorded 2026-08-05, Mike). Below $1,000 this is a fixed tier table and
    # cost is independent of FMV. ABOVE $1,000 the fee is 4% of FMV (min $135),
    # so cost SCALES WITH THE NUMBER BEING BOUNDED.
    # Consequence: bounding FMV downward also bounds cost downward, which
    # NARROWS the ROI gap instead of widening it. A naive pessimistic bound
    # therefore produces a FLATTERED worst case — the exact opposite of what a
    # safety bound is for. Any bound must move both terms together.
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


# ══════════════════════════════════════════════════════════════════════════════
# EDITION-SPAN DETECTION (Fix F)
# ══════════════════════════════════════════════════════════════════════════════
#
# THE CASE. X-Men #1 at grade 9.0 returns $36.00 with verdict_reliable TRUE and
# confidence HIGH, on a six-figure book. Both the 1963 and the 1991 volumes carry
# canonical_title = 'X-Men', so branch A admits them into one pool and the 1991
# copies outvote the 1963 ones.
#
# WORSE THAN THE INFLATION CASE, in the way that matters. Wolverine #181 at
# $6,735 was inflated, and a user holding a common book might sanity-check it.
# This is DEFLATED on a genuine key: $36 looks plausible, the verdict is
# confident, and the user walks away from a six-figure comic.
#
# ⚠️ BETWEEN-CLUSTER, NOT WITHIN-GRADE. Within-grade dispersion is a PROXY that
# also catches signed and pedigree copies, which is why it wrongly flagged
# Batman #423 through a $60 virgin variant and a $3,300 McFarlane-signed copy in
# the same 1988 edition. That failure has nothing to do with editions. This
# splits the pool by YEAR first and compares medians BETWEEN the resulting
# clusters, so intra-edition spread cannot trigger it.
#
# ⚠️ BOTH SIGNALS REQUIRED, AND EACH REJECTS THE OTHER'S FALSE POSITIVE:
#   · YEAR alone hedges ASM #300 at two grades — a §2C anchor, wrongly, twice.
#   · PRICE alone over-flags Absolute Batman #1 and New Mutants #98, both
#     single-volume §2B/§2C anchors.
# The AND is not conservatism; it is the mechanism.
#
# ⚠️ THE SIGNAL READS THE WHOLE GRADED POOL, THE GATE APPLIES AT ONE GRADE.
# Edition ambiguity is a property of the BOOK's comp pool, not of one bucket —
# X-Men #1's grade-9.0 bucket is 4×1991 plus 8 year-unknown and contains no 1963
# sale at all, so a bucket-local span would be 0 and would miss the case
# entirely. The gate (fmv_method == 'exact') is what confines the effect.
#
# ⚠️ TRIMMED MEDIANS ONLY. Any ratio that reaches a user must be the trimmed one
# — 422× on X-Men #1, not the untrimmed 1,429×. Both cluster medians therefore
# go through percentile_trim() exactly as exact_avg does.

# ⚠️ FITTED, NOT DERIVED — named rather than buried as literals so the next
# reader knows what they are. Revisit together, and re-measure before moving
# either: they are jointly tuned and the AND means a change to one silently
# changes the other's effective strictness.
#
# EDITION_YEAR_SPAN_YEARS = 15
#   Carried from the earlier volume work (Superman vol.1 1952 / vol.2 1993).
#   Separates genuine reprint-era volumes from ordinary catalogue drift.
#
# EDITION_PRICE_RATIO = 20.0
#   FITTED TO 14 OBSERVATIONS, 2026-08-13. Small sample; treat as provisional.
#   The risk argument attached to it was: "Amazing Fantasy #15 (26.9×) and
#   Batman #423 (22.3×) both sit close to the line under trimmed data, so a
#   downward move reaches real single-edition books quickly."
#   ⚠️ THAT ARGUMENT IS UNVERIFIED AND ITS FIGURES DO NOT REPRODUCE. Measured
#   2026-08-13 against the live corpus using the shipped matcher
#   (qualifier_title_clause on canonical_title, issue-filtered, days=365,
#   variants excluded in Python, ebay_sales ∪ market_sales):
#       Amazing Fantasy #15 → 185.5× (fires; nowhere near the line)
#       Batman #423        → does not fire (sole candidate split has a
#                            one-comp cluster)
#       X-Men #1           → 84.7× at the 1963|1990 boundary, not 422×
#   The divergence may be methodology — a different pool construction, window,
#   or issue filter in the original analysis — rather than either set of figures
#   being wrong, and it has NOT been resolved. DO NOT move this constant on the
#   strength of the near-the-line reasoning above until the two methodologies
#   are reconciled; there is currently no measured evidence that anything sits
#   near 20×.
#   What IS measured about the constant's EFFECT, on 481 production-shaped
#   (title, issue) cells: 6 fire, all six genuinely multi-edition, zero false
#   positives.
#
# MIN_EDITION_CLUSTER_COMPS = 3
#   CHOSEN, not fitted — matched to the exact_count >= 3 evidence bar the
#   'exact' tier already uses, so a cluster cannot speak with less support than
#   the figure it is contradicting. Two 1-sale "clusters" 28 years apart would
#   otherwise produce a 400× ratio from two rows.
EDITION_YEAR_SPAN_YEARS = 15
EDITION_PRICE_RATIO = 20.0
MIN_EDITION_CLUSTER_COMPS = 3


def _detect_multi_edition(graded_sales):
    """Does this comp pool hold more than one EDITION of the issue?

    Splits the year-known sales at their largest year gap, then requires BOTH
    a wide span and a large trimmed price ratio between the two sides.

    Returns (is_multi_edition, trimmed_ratio, year_low, year_high) — the ratio
    rounded for display, or (False, None, None, None) when the signal does not
    fire or cannot be computed.

    Year-UNKNOWN sales are excluded from the signal entirely and are never
    treated as evidence of one edition or two. On X-Men #1 they are the
    majority of the grade-9.0 bucket; silence about them is the honest handling.
    """
    # ⚠️ Conversion is done inline, NOT via the handler's to_float(). That helper
    # is defined INSIDE get_valuation() (a closure, not a module-level function),
    # so calling it from here is a NameError at request time that py_compile
    # cannot see. Caught in review 2026-08-13; same class as a missing import.
    def _num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    dated = []
    for s in graded_sales:
        if s.get('is_variant'):
            continue                      # variants are out of the priced pool already
        y = s.get('title_year')
        p = _num(s.get('price'))
        if y and p > 0:
            try:
                dated.append((int(y), p))
            except (TypeError, ValueError):
                continue

    # Need enough dated sales for two clusters that each clear the bar.
    if len(dated) < MIN_EDITION_CLUSTER_COMPS * 2:
        return False, None, None, None

    dated.sort(key=lambda t: t[0])
    years = [y for y, _ in dated]

    # ⚰️ DEAD (2026-08-13, before ship): "split at the single widest year gap,
    #    after a whole-range span test."
    # REPLACED BY: evaluate EVERY candidate split and fire if ANY of them
    #    satisfies all three conditions.
    # REASON: the widest-gap rule is decided by outlier years, and the
    #    cluster-size floor then rejected the WHOLE DETECTION rather than the
    #    bad split — there was no fallback to the next candidate. Measured on
    #    the live corpus, X-Men #1 (the originating case) has years
    #    1963:n=27 · 1990:n=4 · 1991:n=242 · 2021:n=1. The real edition
    #    boundary 1963→1990 is a 27-year gap splitting 27/247 at 84.7×. But
    #    1991→2021 is THIRTY years, so the split landed there, produced a
    #    hi_cluster of exactly ONE comp, failed MIN_EDITION_CLUSTER_COMPS, and
    #    returned False. **A single $110 eBay row disarmed the hedge on a
    #    six-figure book.** Delete that one row and the old code fired.
    #    Batman #423 has the identical structure (a lone 2022 row wins the gap)
    #    and returned the DESIRED answer by accident rather than by mechanism,
    #    which is the more disturbing half.
    # SUPERSEDES any "the widest gap is the discontinuity by definition"
    #    reasoning. It is the discontinuity only when the tails are populated,
    #    and in a comp corpus they are not.
    #
    # ⚠️ THE YEAR TEST ALSO MOVED, and this is a correctness change, not a
    # refactor. It used to be a precondition on the WHOLE dated range; it is
    # now the gap AT THE CANDIDATE SPLIT. Whole-range span answers "does this
    # pool cover a long period", which is true of almost any long-running title
    # and is not the question. The gap at the split answers "are these two
    # groups separated in time", which is what "between-cluster" means.
    #
    # Among qualifying splits, the one with the LARGEST price ratio is reported:
    # the strongest price discontinuity is the best evidence of which boundary
    # is the edition boundary.
    best = None   # (ratio, boundary_low_year, boundary_high_year)
    for i in range(1, len(dated)):
        if years[i] - years[i - 1] <= EDITION_YEAR_SPAN_YEARS:
            continue                       # clusters not separated in time here
        lo_cluster = dated[:i]
        hi_cluster = dated[i:]
        if (len(lo_cluster) < MIN_EDITION_CLUSTER_COMPS
                or len(hi_cluster) < MIN_EDITION_CLUSTER_COMPS):
            continue                       # reject THIS split, keep looking
        lo_med = compute_median(percentile_trim([p for _, p in lo_cluster]))
        hi_med = compute_median(percentile_trim([p for _, p in hi_cluster]))
        if not lo_med or not hi_med or lo_med <= 0 or hi_med <= 0:
            continue
        ratio = max(lo_med, hi_med) / min(lo_med, hi_med)
        if ratio < EDITION_PRICE_RATIO:
            continue
        if best is None or ratio > best[0]:
            best = (ratio, years[i - 1], years[i])

    if best is None:
        return False, None, None, None

    # The boundary years, NOT the whole range — they identify the edition break
    # that actually fired, which is what a log line needs to be checkable.
    return True, round(best[0], 1), best[1], best[2]


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


class _Timings:
    """Whole-request stopwatch for /api/sales/valuation. Brackets the ENTIRE
    request, not just the queries, because a DevTools capture on 2026-08-08
    showed this one call still pending at 35,000 ms on The Terminator #1 while
    `extract` and `grade` had both returned 200 — and the measured SQL for that
    exact book is only ~6-7 s server-side. Something owns 25+ s and we do not
    know what. Read-only DB probes ruled the database itself out as the cause:
    13 of 103 connections, one active query, zero lock waits, no autovacuum
    running, 9% dead tuples, 235 MB heap almost entirely in shared_buffers
    (EXPLAIN showed 7,790 buffer hits against 11 reads).

    ⚠️ DO NOT DELETE THIS ONCE THE INDEX LANDS. The expression index fixes a
    measured 6-7 s. If the unattributed time survives it, that is the LARGER
    finding, and this is the only thing that will say so. Both numbers get
    reported, not just the improvement.

    Segments, in order, so a gap can be attributed rather than theorised
    (L-2026-022: make the failure self-report before generating causes):
      receipt→handler  before_request stamped g.start_time → this handler ran.
                       Non-zero here means routing/middleware/WSGI, not us.
      handler→pool     arg parsing and the honesty gates. Should be ~0.
      pool             _dbpool.get_db() + cursor. Isolated deliberately: pool
                       checkout pre-pings with SELECT 1 and falls back to an
                       overflow connection, so a slow or churning pool shows
                       up HERE rather than smeared across the queries.
      q1..q4           each query, elapsed AND row count. Both, because
                       "2.2 s for 0 rows" and "2.2 s for 400 rows" are
                       different problems (Mike, 2026-08-08).
      post_sql         last query → response built. All the Python math:
                       percentile_trim, the bootstrap CI, the verdict ladder.
      total            receipt → response. The number to compare against what
                       DevTools shows; a gap between them is network or WSGI.

    ⚠️ WHAT THIS CANNOT SEE, AND IT IS THE PRIME SUSPECT. `total` starts when
    this handler runs, and before_request runs immediately before it, so
    before_request_to_handler is ~0 by construction and is NOT "time since the
    request arrived." Any time the request spent QUEUED IN GUNICORN — waiting for
    a free sync worker while the long `grade` AI call held one, or a worker being
    reaped and respawned (there was a Starter-tier OOM incident 2026-07-16) — is
    invisible here. That is exactly the shape of the 35 s pending request.
    To capture it, set gunicorn's access log format to include %(D)s (request
    time in microseconds, measured by gunicorn) and compare it against `total`
    below. The DIFFERENCE is queueing plus WSGI overhead, and if the 25 s lives
    there, no amount of SQL work fixes it.
    """
    __slots__ = ('t0', 't0_wall', 'marks', 'queries')

    def __init__(self):
        # perf_counter for durations (monotonic); a wall-clock twin because
        # g.start_time is time.time() and the two clocks are not comparable.
        self.t0 = time.perf_counter()
        self.t0_wall = time.time()
        self.marks = {}
        self.queries = []

    def mark(self, name):
        self.marks[name] = time.perf_counter()

    def query(self, label, ms, rows):
        self.queries.append((label, ms, rows))

    def emit(self, title, issue, outcome):
        """One greppable line. print() on purpose: it is what this module
        already uses, and PYTHONUNBUFFERED=1 is set in the Dockerfile (the live
        deploy path — note render.yaml is stale and names api_server_v3), so it
        flushes immediately instead of being held until process exit
        (L-2026-020). One write syscall per request; no measurable cost."""
        try:
            span = lambda a, b: (self.marks[b] - self.marks[a]) * 1000.0 \
                if a in self.marks and b in self.marks else -1.0
            total_ms = (time.perf_counter() - self.t0) * 1000.0
            # Wall-clock on both sides, because g.start_time is time.time().
            # Expected to be ~0: Flask runs before_request immediately before the
            # view. It is logged anyway as a CONTROL — if it is ever non-trivial,
            # something is happening in middleware, and that is worth knowing
            # rather than assuming.
            try:
                receipt_ms = max(0.0, (self.t0_wall - g.start_time) * 1000.0)
            except Exception:
                receipt_ms = -1.0
            parts = [
                'total=%.0fms' % total_ms,
                'before_request_to_handler=%.0fms' % receipt_ms,
                'handler_to_pool=%.0fms' % span('handler', 'pool_start'),
                'pool=%.0fms' % span('pool_start', 'pool_done'),
            ]
            for label, ms, rows in self.queries:
                parts.append('%s=%.0fms/%drows' % (label, ms, rows))
            parts.append('post_sql=%.0fms' % span('sql_done', 'response'))
            parts.append('outcome=%s' % outcome)
            parts.append('title=%r' % (title or '')[:60])
            parts.append('issue=%r' % (issue or ''))
            print('[VALUATION-TIMING] ' + ' '.join(parts))
        except Exception:
            # Instrumentation must never break the endpoint it measures.
            pass


def _timed_query(cur, timings, label, sql, params):
    """Execute + fetchall, recording elapsed and row count. The row count is
    half the signal: a slow query returning 0 rows is a selectivity/index
    problem, a slow query returning 400 is a volume problem."""
    t = time.perf_counter()
    cur.execute(sql, params)
    rows = cur.fetchall()
    timings.query(label, (time.perf_counter() - t) * 1000.0, len(rows))
    return rows


@valuation_bp.route('/sales/valuation', methods=['GET'])
def api_sales_valuation():
    """
    Enhanced valuation endpoint for the grading results page.
    Returns grade-specific pricing with raw vs slabbed comparison and ROI.

    Matches on canonical_title by normalized EXACT equality only. The base-title
    LIKE fallback was removed 2026-08-07 (commit 1430b64) — see
    title_matching.qualifier_title_clause for the measurement and for why no
    softened variant replaces it.
    Pulls from BOTH ebay_sales and market_sales for maximum coverage.

    Query params:
        title: Comic title (required) - matches against canonical_title first
        issue: Issue number (optional)
        grade: Numeric grade from AI grading (required, e.g. 9.6)
        days: Lookback window in days (default 365 - wider window for more data)
    """
    _t = _Timings()
    _t.mark('handler')
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
        # Logged too. A gate that returns in 3 ms and a gate that returns in
        # 3 s look identical to the client, and an unlogged early return is a
        # blind spot in exactly the request we are trying to account for.
        _t.mark('response')
        _t.emit(title, issue, 'issue_required')
        return jsonify({
            'success': False,
            'issue_required': True,
            'error': 'Issue number needed to price this comic'
        }), 200

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'success': False, 'error': 'Database not configured'}), 500

    try:
        # Pool checkout timed on its own: get_db() pre-pings with SELECT 1 and
        # falls back to a logged overflow connection when the pool is exhausted,
        # so churn or slow connection setup lands here rather than being smeared
        # across q1.
        _t.mark('pool_start')
        conn = _dbpool.get_db(dict_rows=True)
        cur = conn.cursor()
        _t.mark('pool_done')

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
            SELECT grade, sale_price as price, sale_date as sold_date, 'ebay' as source, is_variant,
                   title_year
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
              -- Multi-issue range in the title = several books sold as one listing.
              -- ⚠️ The SECOND number was bounded '\\d{2,4}' until 2026-08-14, so
              -- "#1-15" was excluded and "#1-4" / "#1-8" were NOT: every
              -- single-digit-ended run sailed straight into the comp pool.
              -- Measured against this complete filter chain, 2,405 such rows are
              -- live today (244 of them >= $100) -- Vampirella #1 at $1,169.99
              -- (actually #1-5), Venom Lethal Protector #1 at $600 (#1-6),
              -- Wolverine Limited Series #1 at $599.99 (#1-4).
              --
              -- Widening to '\\d{1,4}' alone misfires on four real shapes, so each
              -- is guarded separately rather than folded into one dense pattern.
              -- Rows each guard rescues, measured 2026-08-14 over the 6,031 the
              -- widening newly captures:
              --   ordinal    "Chew #1 - 4th print"            1,734
              --   descending "#8 - 1" is not a run            1,857
              --   grade      "TMNT ... #1-5 NM"                 203
              --   decimal    "New Mutants #98 - 8.0"             50
              -- Net effect: 3,954 newly matched here, 1,549 rescued, 2,405 excluded.
              AND NOT (
                      raw_title ~* '#\\s*\\d{1,4}\\s*[-–]\\s*\\d'
                  AND raw_title !~* '#\\s*\\d{1,4}\\s*[-–]\\s*\\d\\s*(st|nd|rd|th)\\M'
                  AND raw_title !~* '#\\s*\\d{1,4}\\s*[-–]\\s*\\d\\s*[.,]\\d'
                  AND raw_title !~* '#\\s*\\d{1,4}\\s*[-–]\\s*\\d\\s*(\\.\\d)?\\s*(vf|nm|fn|vg|gd|fr|pr|cgc|cbcs|psa)\\M'
                  -- a range must ascend; NULL from a non-matching title makes the
                  -- AND chain false, so a title with no range is never excluded here
                  AND (substring(raw_title from '#\\s*(\\d{1,4})\\s*[-–]\\s*\\d'))::int
                    < (substring(raw_title from '#\\s*\\d{1,4}\\s*[-–]\\s*(\\d)'))::int
              )
              AND raw_title !~* '[a-z]\\s*#?\\d{1,4}\\s*[+&]\\s*[a-z][a-z0-9 .''-]*?\\d{1,4}'
        """
        ebay_graded_params = [days]

        # Batch 8: qualifier-precise title match (was canonical=OR parsed LIKE)
        ebay_graded_query += f" AND {ebay_title_sql}"
        ebay_graded_params.extend(ebay_title_params)

        if issue and issue not in ['null', 'undefined', 'None']:
            ebay_graded_query += " AND issue_number = %s"
            ebay_graded_params.append(str(issue))

        ebay_graded = _timed_query(cur, _t, 'q1_ebay_graded', ebay_graded_query, ebay_graded_params)

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
              -- Multi-issue range in the title = several books sold as one listing.
              -- ⚠️ The SECOND number was bounded '\\d{2,4}' until 2026-08-14, so
              -- "#1-15" was excluded and "#1-4" / "#1-8" were NOT: every
              -- single-digit-ended run sailed straight into the comp pool.
              -- Measured against this complete filter chain, 2,405 such rows are
              -- live today (244 of them >= $100) -- Vampirella #1 at $1,169.99
              -- (actually #1-5), Venom Lethal Protector #1 at $600 (#1-6),
              -- Wolverine Limited Series #1 at $599.99 (#1-4).
              --
              -- Widening to '\\d{1,4}' alone misfires on four real shapes, so each
              -- is guarded separately rather than folded into one dense pattern.
              -- Rows each guard rescues, measured 2026-08-14 over the 6,031 the
              -- widening newly captures:
              --   ordinal    "Chew #1 - 4th print"            1,734
              --   descending "#8 - 1" is not a run            1,857
              --   grade      "TMNT ... #1-5 NM"                 203
              --   decimal    "New Mutants #98 - 8.0"             50
              -- Net effect: 3,954 newly matched here, 1,549 rescued, 2,405 excluded.
              AND NOT (
                      raw_title ~* '#\\s*\\d{1,4}\\s*[-–]\\s*\\d'
                  AND raw_title !~* '#\\s*\\d{1,4}\\s*[-–]\\s*\\d\\s*(st|nd|rd|th)\\M'
                  AND raw_title !~* '#\\s*\\d{1,4}\\s*[-–]\\s*\\d\\s*[.,]\\d'
                  AND raw_title !~* '#\\s*\\d{1,4}\\s*[-–]\\s*\\d\\s*(\\.\\d)?\\s*(vf|nm|fn|vg|gd|fr|pr|cgc|cbcs|psa)\\M'
                  -- a range must ascend; NULL from a non-matching title makes the
                  -- AND chain false, so a title with no range is never excluded here
                  AND (substring(raw_title from '#\\s*(\\d{1,4})\\s*[-–]\\s*\\d'))::int
                    < (substring(raw_title from '#\\s*\\d{1,4}\\s*[-–]\\s*(\\d)'))::int
              )
              AND raw_title !~* '[a-z]\\s*#?\\d{1,4}\\s*[+&]\\s*[a-z][a-z0-9 .''-]*?\\d{1,4}'
        """
        # Batch 8: qualifier-precise title match
        ebay_raw_query += f" AND {ebay_title_sql}"
        ebay_raw_params = [days] + list(ebay_title_params)

        if issue and issue not in ['null', 'undefined', 'None']:
            ebay_raw_query += " AND issue_number = %s"
            ebay_raw_params.append(str(issue))

        ebay_raw = _timed_query(cur, _t, 'q2_ebay_raw', ebay_raw_query, ebay_raw_params)

        # ---------- MARKET_SALES: graded ----------
        market_graded_query = """
            -- NULL title_year: market_sales has no year column at all, so Whatnot
            -- comps are year-unknown by construction and can never contribute to
            -- the edition-span signal. Selected explicitly so the union is uniform
            -- and _detect_multi_edition() does not have to know which table a row
            -- came from.
            SELECT grade, price, sold_at as sold_date, 'whatnot' as source, is_variant,
                   NULL::int AS title_year
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

        market_graded = _timed_query(cur, _t, 'q3_mkt_graded', market_graded_query, market_graded_params)

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

        market_raw = _timed_query(cur, _t, 'q4_mkt_raw', market_raw_query, market_raw_params)
        _t.mark('sql_done')

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
        #
        # 2026-08-05 Unit 3 — MINIMUM SOURCE SUPPORT. A source bucket must hold
        # at least MIN_SOURCE_COMPS sales before it may anchor an interpolation;
        # thinner buckets are SKIPPED and the next populated bucket is used.
        #
        # Why: the path had no evidence requirement at all, only grade distance.
        # Measured on the live corpus, 95.6% of interpolated cells are one-sided
        # ±20%/grade extrapolation and 90.0% of those anchor on a bucket holding
        # a SINGLE sale. Worked example — Spider-Man #1 @ 9.8, true median $110
        # from 315 same-grade comps: the 9.9 bucket held exactly one genuine
        # $4,449.99 sale, and interpolating 9.6→9.9 returned $2,999.66, a 2,627%
        # error. One sale outvoted 315. With K=2 the 9.9 bucket is skipped, the
        # 9.6 bucket (n=74) anchors instead, and the result is $102.95 — 6.4%.
        #
        # This is a TAIL fix, not a central-tendency fix: backtest median error
        # moves only 19.3% → 18.1%. It exists to remove catastrophic single-sale
        # anchors, and to make any future confidence bound trustworthy — a bound
        # keyed on source support is meaningless while 90% of sources are n=1.
        MIN_SOURCE_COMPS = 2
        interpolated_avg = None
        _all_below = sorted([g for g in grade_buckets if g < grade], reverse=True)
        _all_above = sorted([g for g in grade_buckets if g > grade])
        grades_below = [g for g in _all_below
                        if len(grade_buckets[g]) >= MIN_SOURCE_COMPS]
        grades_above = [g for g in _all_above
                        if len(grade_buckets[g]) >= MIN_SOURCE_COMPS]
        # Nearby sales EXIST but none carry enough evidence to anchor from. This
        # is a different state from "no sales at all" and must not be described
        # as one — see verdict_basis 'low_support' below.
        low_support_only = (bool(_all_below or _all_above)
                            and not (grades_below or grades_above))
        # How many nearby sales there actually are. When low_support_only holds,
        # every nearby bucket is by definition below MIN_SOURCE_COMPS — but there
        # can be SEVERAL of them (9.0 with one sale AND 9.6 with one sale is two
        # nearby sales, not one). The copy must state the real number rather than
        # assume one, or it repeats the very defect this tier was added to avoid.
        nearby_thin_comps = sum(len(grade_buckets[g])
                                for g in (_all_below + _all_above))

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
            # ⚠️ `<= 0`, NOT `< 0`. Boundary bug fixed 2026-08-08. At a grade_diff of
            # EXACTLY 5.0 the factor (1 - 0.2*5.0) is 0, so interpolated_avg is 0.0.
            # `0.0 < 0` is False, so the floor did not fire; 0.0 is falsy, so both
            # `elif exact_avg and interpolated_avg` and `elif interpolated_avg` below
            # failed, fmv_method became 'none', and the cell fell through to the
            # fabricated/raw_only fallback DESPITE having >=2 real comps at a nearby
            # grade. Reachable: grade 4.0 priced against comps only at 9.0. A gap
            # GREATER than 5.0 always worked, because then the factor is negative and
            # the floor fired — which is why this survived.
            # This also made two user-facing strings false: the `thin` tier's "too few
            # at nearby grades to cross-check" and the `fabricated` tier's "no usable
            # sales", for exactly these cells.
            # ⏰ The queued max-grade-distance unit may delete this whole branch and
            # the 0.25 floor with it. Fixed anyway: a correct boundary today beats a
            # false string waiting on a redesign.
            if interpolated_avg <= 0:
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

        # ---------- Confidence score (computed BEFORE the verdict so the verdict can gate on it) ----------
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

        # ---------- Fix B: data-sufficiency verdict gate ----------
        # Never let a low-confidence inference drive a confident slab/no-slab verdict
        # (same lesson as the Slab Guard arc). LAUNCH SCOPE = the FABRICATION tier ONLY:
        # estimated/estimated_from_raw (graded FMV invented from grade/publisher/era
        # baselines or raw×1.5 — KEY-BLIND, zero real graded comps; the ASM #41 class).
        # Deliberately NOT gated at launch: 'exact_thin' (1-2 real same-grade comps) and
        # thin 'interpolated' — genuinely low-confidence but a DIFFERENT risk tier
        # (thin-but-real, not fabricated). NOTE: gating on confidence=='very_low' would
        # ALSO sweep exact_thin in (exact_thin ⟹ total_graded<3 ⟹ very_low), which Mike
        # scoped POST-LAUNCH — so the launch gate is estimated-only, NOT very_low.
        # ⏰ POST-LAUNCH confidence-tuning: extend the gate to very_low (adds exact_thin +
        # thin-interpolated). Do not forget. (Mike, 2026-06-27.)
        estimated_flag = estimated or fmv_method in ('estimated', 'estimated_from_raw')

        # 2026-08-05: the deferred very_low extension, taken BEFORE cold traffic.
        # Evidence: the old fabrication-only gate hedged 0.0% of the §2A starved
        # keys and 0.0% of the §2C blue-chip anchors — none of the 24 books cold
        # traffic will actually type. A leave-one-grade-out backtest of the
        # interpolation path over 1,292 cells (production filters, facsimiles
        # excluded) gives 20.7% median absolute error, only 49.1% within ±20%,
        # p90 77.4%, and it is WORST at 9.6-9.8 where the dollars are largest
        # (35.1% median error at a 0.2-grade gap vs 8.5% at 0.5). Interpolation
        # is inaccurate, not merely unlabelled.
        #
        # ⚠️ `blended` IS gated (Mike, 2026-08-05), and the reason it was nearly
        # missed matters: B-vs-C measured identical only because `exact_thin` is
        # essentially EMPTY on the keys that matter. A thin exact bucket becomes
        # `blended` rather than `exact_thin` whenever neighbouring grades exist,
        # which on flagship keys they always do. So "the very_low extension is
        # free" was free because it was VACUOUS. The real thin-evidence tier on
        # the keys cold traffic will type is `blended`: 21.7% of the §2A starved
        # keys and 15.7% of the §2C anchors, versus 0% for exact_thin.
        # Gating exact_thin but not blended is not a policy — it is an artifact
        # of which neighbouring grades happened to exist.
        #
        # Direction of error: gating too much makes the product quiet, which is
        # reversible. Gating too little ships a ~$75 recommendation off two
        # comps, which is not. Same asymmetry as undergrading beating
        # overgrading. Ship gated, measure, revisit.
        NO_SAME_GRADE_EVIDENCE = ('interpolated',)              # 0 same-grade comps
        THIN_SAME_GRADE = ('exact_thin', 'blended')             # 1-2 same-grade comps

        # ── Fix F: edition span ──────────────────────────────────────────────
        # ⚠️ GATED ON fmv_method == 'exact', AND THE GATE IS THE DESIGN, not a
        # performance shortcut. Two things follow from it, both load-bearing:
        #
        #   1. IT MAKES THE COPY PROBLEM STRUCTURALLY UNREACHABLE RATHER THAN
        #      FIXED. Every other tier is ALREADY hedged by the three conditions
        #      above, so F can only ever fire where a confident verdict would
        #      otherwise escape. There is no cell where F's string competes with
        #      another tier's string, because no other tier reaches here.
        #
        #   2. IT GUARANTEES THE STRING'S OWN PRECONDITION. `exact` requires
        #      exact_count >= 3, so "These N sales at grade X" always has a real
        #      N of at least 3 to name. The string cannot be reached in a state
        #      where it would have to say "these 0 sales".
        #
        # Do not widen this to other tiers to "catch more". A widened F would
        # double-hedge already-hedged cells and would need a precedence rule
        # between its string and theirs — which is the coupling the collapsed
        # ROUGH ESTIMATE badge exists to avoid.
        multi_edition, edition_price_ratio, _ed_lo, _ed_hi = (False, None, None, None)
        if fmv_method == 'exact':
            multi_edition, edition_price_ratio, _ed_lo, _ed_hi = \
                _detect_multi_edition(all_graded)
            if multi_edition:
                print(f"[VALUATION-F] multi-edition hedge: ratio={edition_price_ratio}x "
                      f"years={_ed_lo}-{_ed_hi} exact_count={exact_count}")

        verdict_reliable = not (
            estimated_flag
            or fmv_method in NO_SAME_GRADE_EVIDENCE
            or fmv_method in THIN_SAME_GRADE
            or multi_edition
        )

        # Which TIER the hedge is in, so the client can say something true.
        # The old copy ("rough estimate from grade, publisher, and era") is
        # correct ONLY for fabrication; saying it about an interpolated figure
        # would misdescribe real comps at neighbouring grades as a baseline.
        # `blended` and `exact_thin` are separated because only blended pulls in
        # neighbouring grades — the copy says so.
        # 'low_support' exists because Unit 3's K=2 rule moves ~90% of previously
        # interpolated cells into the fabrication branch, and the fabricated copy
        # ("No recent sales found for this book… a rough estimate from grade,
        # publisher, and era — not from sales") is FALSE for a cell that has one
        # real sale at a nearby grade. Same failure as the recency-weighting
        # claim: copy asserting something the mechanism does not do. The tier is
        # carried in the DATA regardless of what the copy eventually says.
        # ⚠️ CHECKED FIRST, and it can only be true when fmv_method == 'exact'.
        # Every branch below keys on estimated_flag or on a non-'exact' method,
        # so this is not a precedence choice between competing descriptions —
        # the branches are disjoint by construction. It is first so a reader
        # sees the gate before the ladder rather than having to prove the
        # disjointness themselves.
        if multi_edition:
            verdict_basis = 'multi_edition'
        elif estimated_flag and low_support_only:
            # Named for the CONDITION (insufficient support), not for a count —
            # 'single_comp' would be wrong whenever several thin buckets exist.
            # Checked FIRST: when thin graded sales exist near this grade, that
            # is the more specific true statement, and 'raw_only' below would
            # wrongly claim there are no graded sales at all.
            verdict_basis = 'low_support'
        elif estimated_flag and fmv_method == 'estimated_from_raw':
            # 2026-08-07. 'estimated_from_raw' means: real RAW sales exist, zero
            # graded sales, and graded_fmv = raw_fmv * 1.5. It was falling into
            # 'fabricated', whose copy reads "No recent sales found for this
            # book … not from sales" — FALSE on both clauses for this tier, and
            # a fifth L-SW-2026-020 instance (copy asserting something the
            # mechanism does not do).
            # PRE-EXISTING, not introduced by the branch-B removal: 195 of 594
            # real lookups already reach this tier today. Removing branch B
            # adds 21 more, which is why it is corrected in the same unit
            # rather than left for later.
            verdict_basis = 'raw_only'
        elif estimated_flag:
            verdict_basis = 'fabricated'
        elif fmv_method in NO_SAME_GRADE_EVIDENCE:
            verdict_basis = 'interpolated'
        elif fmv_method == 'blended':
            verdict_basis = 'blended'
        elif fmv_method == 'exact_thin':
            verdict_basis = 'thin'
        else:
            verdict_basis = 'supported'

        # ---------- ROI calculation ----------
        slabbing_roi = None
        roi_percentage = None
        verdict = 'Insufficient data'

        if graded_fmv and raw_fmv:
            if not verdict_reliable:
                # 2026-08-08 — ROI IS NOW WITHHELD, NOT MERELY HEDGED.
                # ⚰️ DEAD: "keep the number but refuse a confident call" (the old
                # comment on this branch, which computed slabbing_roi anyway).
                # REPLACED BY: slabbing_roi and roi_percentage stay None.
                # REASON: in the `fabricated` tier this number carries ZERO
                # information about the book. raw_fmv is itself overwritten by the
                # synthetic grade/publisher/era baseline above (see the estimated
                # fallback), and graded_fmv is set to raw_fmv * 1.5 — so
                # slabbing_roi reduces to (0.5 * baseline) - grading_cost, a
                # deterministic function of grade, publisher and era. It is not a
                # weak estimate of this comic's ROI; it is not about this comic.
                # A hedge sentence beside it asked the reader to discount a number
                # that should never have been produced. The client's hedge
                # paragraph is removed in the same unit, so leaving the number
                # would have stripped the caveat and kept what it was attached to.
                # SUPERSEDES any client-side hiding of ROI: it must be absent from
                # the payload, because the client used to RECOMPUTE it from
                # graded_fmv/raw_fmv/grading_cost when it was null.
                verdict = ('Not enough recent sales to value this reliably — '
                           'rough estimate only, treat with caution')
            else:
                slabbing_roi = round(graded_fmv - raw_fmv - grading_cost, 2)
                if raw_fmv > 0:
                    roi_percentage = round((slabbing_roi / raw_fmv) * 100, 1)

                if slabbing_roi > 50:
                    verdict = 'Worth grading'
                elif slabbing_roi > 0:
                    # ⚠️ LOGGED 2026-08-08, NOT FIXED HERE: the client badges this
                    # band as 'WORTH THE SLAB' for any roi > 0, so a $5 gain reads
                    # as a recommendation. Own unit.
                    verdict = 'Marginal - consider volume'
                else:
                    verdict = 'Probably not worth grading'
        elif graded_fmv:
            verdict = 'Limited raw data - compare manually'
        elif raw_fmv:
            verdict = 'No graded sales data - cannot calculate ROI'

        # ---------- Build grade price curve (for chart display) ----------
        #
        # ⚠️⚠️ READ THIS BEFORE DRAWING THIS CURVE ANYWHERE. On a multi-edition
        # book this is TWO COMICS INTERLEAVED, and it will look like a coherent
        # price curve with a cliff in it. Measured on X-Men #1, 2026-08-13:
        #
        #     grade 3.5   $9,060   n=2                              ← 1963
        #     grade 5.0  $13,500   n=3   min $142.50  max $16,000   ← BOTH
        #     grade 7.0  $10,856   n=3   min $17.50   max $25,000   ← BOTH
        #     grade 8.0      $18   n=6                              ← 1991
        #     grade 9.8      $78   n=300                            ← 1991
        #
        # The apparent cliff at 8.0 is not a market phenomenon; it is the point
        # where the 1991 volume starts outnumbering the 1963 one. And the
        # min/max spreads show the editions mixed WITHIN buckets, so no
        # per-point filter cleans it — grade 1.0 runs $44 to $3,499.
        #
        # NOTHING RENDERS THIS TODAY. Verified 2026-08-13: three references, all
        # in this file, and zero readers in any .html or .js. Market Pulse is a
        # SOON badge in js/sidebar.js with no implementation. So whoever builds
        # that chart INHERITS this defect rather than introducing it, and will
        # inherit it silently because the curve looks plausible.
        #
        # Fix F detects the condition and already emits `edition_price_ratio`
        # beside this payload — but F is GATED ON fmv_method == 'exact', so the
        # flag is absent on exactly the thin-bucket grades where the curve is
        # most misleading. Do not treat `edition_price_ratio` being null as
        # evidence the curve is clean. If you are building a chart from this,
        # the honest options are: suppress it when the pool spans editions,
        # split the series by edition, or plot only the cluster that matches the
        # user's book. Plotting it as one series is the defect.
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
        # Marked BEFORE _record_demand so post_sql measures OUR work. If the
        # daemon-thread handoff ever starts blocking, it lands in the gap between
        # this mark and the client's observed time rather than hiding inside it.
        _t.mark('response')
        _t.emit(title, issue, 'ok')

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
            # slabbing_roi / roi_percentage are None whenever verdict_reliable is
            # false (2026-08-08). ⚠️ roi_percentage and `verdict` below are read by
            # NO client — app.html builds its own verdict and its own copy. Changing
            # the `verdict` strings here ships nothing user-visible; do not "fix the
            # hedge copy" in this file. Verified by grep 2026-08-08.
            'slabbing_roi': slabbing_roi,
            'roi_percentage': roi_percentage,
            'verdict': verdict,
            'verdict_reliable': verdict_reliable,   # Fix B: false ⇒ render verdict as low-confidence/caution
            'verdict_basis': verdict_basis,         # fabricated|raw_only|low_support|interpolated|blended|thin|multi_edition|supported
            # TRIMMED ratio, or None. js/verdict_basis.js interpolates it into
            # the multi_edition string, so it is the figure a user reads — and it
            # must never be the untrimmed one (1,429× vs 422× on X-Men #1).
            # None on every other tier, and the string is written to be correct
            # with or without it.
            'edition_price_ratio': edition_price_ratio,
            'nearby_thin_comps': nearby_thin_comps,  # sales near this grade that were too thin to anchor from
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
        # ⚠️ The failure path is logged too, and this is the one that matters
        # most for the 25 s we cannot account for. A request that spends 28 s and
        # THEN raises produces a 500 the client shows as a generic failure; without
        # this, the elapsed time and the segment it was spent in are lost, and the
        # slowest requests would be exactly the ones we have no data for
        # (L-2026-022: treat "I can't see it" as the first problem to fix).
        _t.mark('response')
        _t.emit(title, issue, 'error:%s' % type(e).__name__)
        print('[VALUATION-ERROR] %s: %s' % (type(e).__name__, e))
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
        conn = _dbpool.get_db(dict_rows=True)
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
