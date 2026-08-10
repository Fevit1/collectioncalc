"""
Utils Blueprint - Health checks, debug routes, and utility endpoints
"""
from flask import Blueprint, jsonify, request, send_from_directory
from auth import validate_beta_code
import os

# Create blueprint
utils_bp = Blueprint('utils', __name__)

# These will be set by wsgi.py when registering the blueprint
BARCODE_AVAILABLE = False
MODERATION_AVAILABLE = False

def init_globals(barcode_available, moderation_available):
    """Called from wsgi.py to set global flags"""
    global BARCODE_AVAILABLE, MODERATION_AVAILABLE
    BARCODE_AVAILABLE = barcode_available
    MODERATION_AVAILABLE = moderation_available


_HEALTH_VERSION = '5.6.0'


@utils_bp.route('/')
@utils_bp.route('/health')
def health():
    """Health check endpoint — minimal public response.

    check_all() must still RUN here: the dependency monitor has no cron — its
    scheduling piggybacks on health-check polling, and the state-change alert
    email fires from inside check_all(). Only the OUTPUT stays private:
    installed versions, dependency gaps, and monitoring notes are recon
    material, so the detail (plus runtime flags like barcode/moderation) lives
    behind /api/admin/dependency-status. `version` is kept for deploy
    verification.

    Item 2(d): the probe also proves DB liveness — SELECT 1 on the shared
    pool; unreachable DB → 503 'degraded'. With Render's healthCheckPath set
    to /health, a deploy with a broken DB config never receives traffic and a
    dead DB flips the service unhealthy instead of answering ok. The monitor
    check above must never fail the probe; the DB check is the only thing
    allowed to."""
    try:
        from dependency_monitor import check_all
        check_all()  # side effects only — never expose results, never fail the probe
    except Exception as e:
        print(f"[Health] dependency check error: {e}")
    try:
        import db as _db
        conn = _db.get_db()
        try:
            cur = conn.cursor()
            cur.execute('SELECT 1')
            cur.fetchone()
            cur.close()
        finally:
            conn.close()
    except Exception as e:
        print(f"[Health] DB check FAILED: {e}")
        return jsonify({'status': 'degraded', 'version': _HEALTH_VERSION}), 503

    _assert_canonical_title_index()

    return jsonify({'status': 'ok', 'version': _HEALTH_VERSION})


def _assert_canonical_title_index():
    """⚠️ DRIFT GUARD. Asserts the planner CHOOSES the canonical_title expression
    index — not merely that the index exists.

    WHY THIS EXISTS. The valuation comp query filters on a NORMALIZED
    canonical_title, and only an index built on the IDENTICAL expression can serve
    it. That means the normalization is encoded in two places: `_norm_sql()` in
    title_matching.py, and the index definition in the database. If either drifts
    by one character the planner silently stops using the index and the query
    returns to a ~7 s bitmap-heap scan over the 73,818 rows that share
    issue_number='1' — CORRECT RESULTS, NO ERROR, ten times slower. That is
    L-SW-2026-026 in a new place: one assumption written twice.

    WHY AN EXPLAIN AND NOT AN EXISTENCE CHECK. Three drift modes, one probe:
    (1) the expression changed in Python, (2) the index was dropped, (3) the index
    is present but INVALID — which is the normal residue of a failed
    CREATE INDEX CONCURRENTLY, stays visible in pg_indexes, and is ignored by the
    planner. An existence check passes on (1) and (3). Asserting the index NAME
    appears in the chosen plan catches all three.

    It is a positive control by construction: the probe can only pass when the
    thing it is testing for is actually happening.

    EXPLAIN without ANALYZE, so the query is planned and never executed — no rows
    read, sub-millisecond, safe on every health poll. Never fails the probe: a
    performance regression is not an outage, and /health gates Render traffic via
    healthCheckPath. It logs loudly instead, which is the whole point — the
    failure mode being guarded against is silence.
    """
    INDEX_NAME = 'idx_ebay_sales_canonical_title_norm'
    try:
        from title_matching import _norm_sql
        import db as _db
        # The expression comes from the SAME function the query uses, so this
        # check cannot drift from the query even if both drift from the index.
        sql = ("EXPLAIN SELECT 1 FROM ebay_sales WHERE %s = %%s AND issue_number = %%s"
               % _norm_sql('canonical_title'))
        conn = _db.get_db()
        try:
            cur = conn.cursor()
            cur.execute(sql, ('terminator', '1'))
            plan = ' '.join(str(r[0]) for r in cur.fetchall())
            cur.close()
        finally:
            conn.close()
        if INDEX_NAME not in plan:
            print('[Health] ⚠️ INDEX DRIFT: the planner is NOT using %s. '
                  'The valuation comp query has silently reverted to a full scan '
                  '(~7s). Check that the index exists, is valid (pg_index.indisvalid), '
                  'and was built on exactly title_matching._norm_sql(\'canonical_title\'). '
                  'Chosen plan: %s' % (INDEX_NAME, plan[:400]))
    except Exception as e:
        print('[Health] index drift check could not run: %s: %s' % (type(e).__name__, e))


@utils_bp.route('/api/debug/prompt-check')
def debug_prompt():
    """Debug endpoint to check extraction prompt"""
    from comic_extraction import EXTRACTION_PROMPT
    return jsonify({
        'prompt_length': len(EXTRACTION_PROMPT),
        'has_new_schema': 'YOU MUST RETURN EXACTLY' in EXTRACTION_PROMPT,
        'first_100_chars': EXTRACTION_PROMPT[:100]
    })


@utils_bp.route('/api/beta/validate', methods=['POST'])
def api_validate_beta():
    """Validate a beta access code"""
    data = request.get_json() or {}
    code = data.get('code', '')
    result = validate_beta_code(code)
    return jsonify(result)


@utils_bp.route('/verify')
def serve_verify():
    """Serve the public verify page"""
    # Get the directory where this file is located, then go up one level to project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return send_from_directory(base_dir, 'verify.html')
