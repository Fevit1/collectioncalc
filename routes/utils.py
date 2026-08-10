"""
Utils Blueprint - Health checks, debug routes, and utility endpoints
"""
from flask import Blueprint, jsonify, request, send_from_directory
from auth import validate_beta_code
import os
import time

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

    ⚠️ REPORTING IS TRANSITION-DRIVEN, NOT PER-CALL — see _report_index_state.
    The original version printed on every observation. /health is polled about
    every 5s (and '/' shares this handler), so a persistent drift emitted ~17k
    lines/day at ~700 chars — which does not merely cost storage, it BURIES the
    signal the next incident needs, including the [VALUATION-TIMING] lines added
    alongside this guard. Correct behaviour, wrong volume (Mike, 2026-08-10).
    """
    INDEX_NAME = 'idx_ebay_sales_canonical_title_norm'

    # Probe throttle. The index cannot change between health ticks, so probing
    # every 5s buys nothing but ~17k DB round trips/day. This bounds detection
    # lag for a NEW drift at _DRIFT_PROBE_MIN_INTERVAL_SEC; it does NOT throttle
    # reporting (that is the transition logic below) — the two are separate
    # dials on purpose.
    now = time.monotonic()
    if _drift_state['last_probe'] and \
            (now - _drift_state['last_probe']) < _DRIFT_PROBE_MIN_INTERVAL_SEC:
        return
    _drift_state['last_probe'] = now

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
        if INDEX_NAME in plan:
            _report_index_state('ok', INDEX_NAME, plan)
        else:
            _report_index_state('drift', INDEX_NAME, plan)
    except Exception as e:
        _report_index_state('error', INDEX_NAME,
                            '%s: %s' % (type(e).__name__, e))


# ── Drift-guard reporting state ──────────────────────────────────────────────
# Deliberately PER-WORKER module state, with no shared store. L-SW-2026-013 is
# the lesson that shared alert dedup + per-replica observations is the exact
# recipe for an alert storm (2026-07-16: ~1 email per 5-15s for hours, because
# one worker's cached failure kept re-inserting a key another worker kept
# pruning). Per-worker state cannot storm: the worst case is one extra line per
# worker, which is the cost of honesty about who observed what.
_DRIFT_PROBE_MIN_INTERVAL_SEC = int(os.environ.get('INDEX_DRIFT_PROBE_SEC', '60'))
_DRIFT_HEARTBEAT_SEC = int(os.environ.get('INDEX_DRIFT_HEARTBEAT_SEC', '3600'))

_drift_state = {
    'status': None,       # None = not yet probed by THIS worker | ok | drift | error
    'since': 0.0,         # monotonic: when the current status began
    'observations': 0,    # probes that have seen the current status
    'last_logged': 0.0,   # monotonic: last line emitted for the current status
    'last_probe': 0.0,
}


def _fmt_duration(seconds):
    m, s = divmod(int(max(0, seconds)), 60)
    h, m = divmod(m, 60)
    if h:
        return '%dh%02dm' % (h, m)
    if m:
        return '%dm%02ds' % (m, s)
    return '%ds' % s


def _report_index_state(status, index_name, detail):
    """Silent when healthy, loud on transition, heartbeat-floored while broken.

    THE THREE REQUIREMENTS, and how each is met (Mike, 2026-08-10):

      silent when healthy      — a steady 'ok' emits NOTHING after the arming
                                 line. Zero lines/day in the normal case.
      loud on transition       — any status change emits immediately, and an
                                 ok→drift transition carries the FULL plan text.
                                 That 700-char plan is what made the finding
                                 legible on 2026-08-10 and is kept verbatim.
      never so quiet that a    — while drift persists, a one-line heartbeat
      regression waits for       every _DRIFT_HEARTBEAT_SEC. So the most recent
      someone to look            evidence in the log is never more than an hour
                                 stale. Pure state-change logging fails exactly
                                 here: one line at 3am, silence after, and by
                                 09:00 a grep of the last hour is empty —
                                 indistinguishable from healthy. That is
                                 L-2026-024 (absence is not evidence) applied to
                                 our own guard.

    ⚠️ THE ARMING LINE IS NOT NOISE, IT IS THE POSITIVE CONTROL. A guard that is
    silent when healthy is indistinguishable from a guard that is not running,
    was never registered, or is throwing before it reaches the probe. One line
    per worker at first observation makes subsequent silence MEAN something.
    Without it we would have replaced a volume problem with an epistemic one
    (L-SW-2026-017: a step whose completion is not observable is
    indistinguishable from one that was skipped).
    """
    try:
        now = time.monotonic()
        st = _drift_state
        prev, prev_since = st['status'], st['since']

        if status != prev:
            st.update(status=status, since=now, observations=1, last_logged=now)
            held = _fmt_duration(now - prev_since) if prev is not None else None

            if status == 'drift':
                # Transition INTO drift — the full plan, unabridged. This is the
                # one place the 700 chars earn their cost.
                print('[Health] ⚠️ INDEX DRIFT: the planner is NOT using %s. '
                      'The valuation comp query has silently reverted to a full scan '
                      '(~7s). Check that the index exists, is valid (pg_index.indisvalid), '
                      'and was built on exactly title_matching._norm_sql(\'canonical_title\'). '
                      'Repeating hourly until resolved. Chosen plan: %s'
                      % (index_name, detail[:400]))
            elif status == 'ok' and prev == 'drift':
                # The RECOVERY artifact. Derived from the planner's own choice,
                # not declared — so it is real evidence that a CREATE INDEX took
                # (L-SW-2026-017: name the artifact, and make it derived).
                print('[Health] ✅ INDEX DRIFT RESOLVED: the planner is now using %s '
                      '(was drifting for %s). Valuation comp queries should return to '
                      'index-scan latency; confirm with the next [GRADE-TIMING] / '
                      '[VALUATION-TIMING] line.' % (index_name, held))
            elif status == 'ok':
                # First healthy observation by this worker: the arming line.
                print('[Health] index drift guard armed: planner is using %s. '
                      'Silent while healthy; hourly heartbeat if it drifts.' % index_name)
            elif status == 'error':
                print('[Health] ⚠️ index drift check could not run (guard is BLIND, '
                      'not clear): %s' % detail[:400])
            return

        # Same status as last time — heartbeat only, and only while not healthy.
        st['observations'] += 1
        if status == 'ok':
            return
        if (now - st['last_logged']) < _DRIFT_HEARTBEAT_SEC:
            return
        st['last_logged'] = now
        if status == 'drift':
            print('[Health] ⚠️ INDEX DRIFT ONGOING for %s (%d checks): planner still '
                  'not using %s. Full plan logged at onset.'
                  % (_fmt_duration(now - st['since']), st['observations'], index_name))
        else:
            print('[Health] ⚠️ index drift check STILL failing for %s (%d checks): %s'
                  % (_fmt_duration(now - st['since']), st['observations'], detail[:200]))
    except Exception:
        # Reporting must never break the probe, and the probe must never break
        # /health — which Render acts on via healthCheckPath.
        pass


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
