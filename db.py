"""Shared PostgreSQL connection pool for the web path.

This module is the ONLY place web-path code should open database connections.
Call sites keep their existing pattern — `conn = get_db()` ... `conn.close()` —
because get_db() returns a PooledConnection proxy whose close() RETURNS the
connection to the pool instead of closing it. Row flavor is preserved per
checkout: get_db(dict_rows=True) gives RealDictCursor rows (the auth/admin/
waitlist flavor), plain get_db() gives tuple rows (billing/monitor/verify).

Why a pool at all: every call site used to open a fresh psycopg2 connection
(~130 sites, 4+ per authed grade request) with no reuse and no finally-close,
against a Render Postgres ceiling of max_connections=103. Adding gunicorn
workers/threads without this multiplies that into a `too many connections`
cascade (LAUNCH_READINESS sequence item 2b).

Operational notes:
- Pool is lazy and per-process (pid-checked), so it is fork-safe under
  gunicorn with or without --preload: each worker builds its own pool on
  first use. Sizing: DB_POOL_MIN/DB_POOL_MAX env vars (default 1/8);
  global ceiling = DB_POOL_MAX x workers + overflow, vs ~100 usable.
- Every checkout is pre-pinged (SELECT 1). A connection severed while parked
  (server restart, idle kill, network blip — the "SSL connection has been
  closed unexpectedly" class) is discarded and replaced instead of surfacing
  to the caller.
- Pool exhaustion does NOT fail the request: it serves a loudly-logged direct
  connection (overflow) whose close() really closes. Overflow in the logs is
  the leak signal, not an outage.
- DB_POOL_DISABLED=1 reverts get_db() to raw per-call connections (the
  pre-pool behavior) without a code revert — the rollback lever.
- get_db_readonly() is a SEPARATE path for the admin NLQ handler, on the
  SELECT-only `nlq_readonly` role (DATABASE_URL_NLQ). It is deliberately
  unpooled and fails closed — see its docstring.
- Scripts and migrations (db_migrate_*, scripts/) deliberately do NOT use
  this module; a one-shot process should hold a plain connection.
"""

import os
import threading

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool, PoolError

DB_POOL_MIN = int(os.environ.get('DB_POOL_MIN', '1'))
DB_POOL_MAX = int(os.environ.get('DB_POOL_MAX', '8'))

_lock = threading.Lock()
_pool = None
_pool_pid = None

_stats_lock = threading.Lock()
_stats = {
    'checkouts': 0,           # total get_db() calls served from the pool
    'overflow': 0,            # pool-exhausted direct connections served
    'preping_replaced': 0,    # stale connections discarded by the pre-ping
    'leaks_returned': 0,      # connections force-returned by the teardown net
}


def _count(key, n=1):
    with _stats_lock:
        _stats[key] += n


def _dsn():
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable not set")
    return url


def _connect_kwargs():
    # Match the strictest pre-pool behavior (ebay_* passed sslmode='require');
    # defer to the URL if it already pins a mode.
    if 'sslmode=' in _dsn():
        return {}
    return {'sslmode': 'require'}


def _get_pool():
    """Lazy, per-process pool. The pid check makes this fork-safe: a pool
    created in one process must never be used from a forked child (shared
    sockets), so each gunicorn worker builds its own on first use."""
    global _pool, _pool_pid
    pid = os.getpid()
    if _pool is None or _pool_pid != pid:
        with _lock:
            if _pool is None or _pool_pid != pid:
                _pool = ThreadedConnectionPool(
                    DB_POOL_MIN, DB_POOL_MAX, dsn=_dsn(), **_connect_kwargs()
                )
                _pool_pid = pid
    return _pool


def _checkout():
    """Take a validated connection from the pool.

    Returns (conn, pooled) — pooled=False means an overflow direct connection
    that must genuinely be closed, not returned."""
    pool = _get_pool()
    try:
        conn = pool.getconn()
    except PoolError:
        # Exhausted — likely a leak upstream. Serve the request anyway on a
        # direct connection and make the condition impossible to miss.
        print(f"[DB] POOL EXHAUSTED (max={DB_POOL_MAX}, pid={os.getpid()}) — "
              f"serving overflow direct connection; investigate connection leaks")
        _count('overflow')
        return psycopg2.connect(_dsn(), **_connect_kwargs()), False

    # Pre-ping: a connection severed while parked (server restart, idle kill,
    # network drop) raises here instead of inside a request handler.
    try:
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.fetchone()
        cur.close()
        conn.rollback()  # leave no open transaction from the ping
    except Exception:
        _count('preping_replaced')
        try:
            pool.putconn(conn, close=True)  # discard the corpse
        except Exception:
            pass
        conn = pool.getconn()  # a second failure propagates — that's real
    return conn, True


class PooledConnection:
    """Thin proxy over a psycopg2 connection. close() returns the connection
    to the shared pool (after rollback) instead of closing it; everything
    else delegates to the real connection. close() is idempotent, matching
    psycopg2 semantics, so existing double-close-safe code keeps working."""

    def __init__(self, conn, pooled):
        object.__setattr__(self, '_conn', conn)
        object.__setattr__(self, '_pooled', pooled)
        object.__setattr__(self, '_returned', False)

    def close(self):
        if object.__getattribute__(self, '_returned'):
            return
        object.__setattr__(self, '_returned', True)
        conn = object.__getattribute__(self, '_conn')
        if not object.__getattribute__(self, '_pooled'):
            try:
                conn.close()
            except Exception:
                pass
            return
        try:
            if not conn.closed:
                conn.rollback()             # never park a connection mid-transaction
                conn.cursor_factory = None  # don't leak row flavor to the next user
        except Exception:
            pass
        try:
            _get_pool().putconn(conn, close=bool(getattr(conn, 'closed', False)))
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, '_conn'), name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, '_conn'), name, value)

    # `with conn:` passthrough (psycopg2: commit/rollback on exit, no close)
    def __enter__(self):
        return object.__getattribute__(self, '_conn').__enter__()

    def __exit__(self, *exc):
        return object.__getattribute__(self, '_conn').__exit__(*exc)


def get_db(dict_rows=False):
    """Checkout a pooled connection. dict_rows=True → RealDictCursor rows.

    Existing call-site pattern is unchanged: conn = get_db(); ...; conn.close().
    """
    if os.environ.get('DB_POOL_DISABLED') == '1':
        # Rollback lever: pre-pool behavior, one env flip, no code revert.
        conn = psycopg2.connect(_dsn(), **_connect_kwargs())
        if dict_rows:
            conn.cursor_factory = RealDictCursor
        return conn

    conn, pooled = _checkout()
    conn.cursor_factory = RealDictCursor if dict_rows else None
    _count('checkouts')
    proxy = PooledConnection(conn, pooled)
    _register_for_teardown(proxy)
    return proxy


def get_db_readonly():
    """Connection for the admin NLQ path, on the SELECT-only `nlq_readonly`
    role (DATABASE_URL_NLQ) instead of the app's read-write DSN.

    Rows are RealDictCursor, matching what get_db(dict_rows=True) hands the
    NLQ caller today.

    Deliberately NOT pooled: /api/admin/nlq is admin-only and low-frequency,
    and a second pool would add DB_POOL_MAX x workers to the connection
    ceiling (max_connections=103) to serve a handful of queries a day. This
    connection's close() genuinely closes.

    FAILS CLOSED. If DATABASE_URL_NLQ is unset this raises rather than falling
    back to DATABASE_URL. A fallback would hand the NLQ path the read-write
    role again while looking exactly like a working configuration — the shape
    L-SW-2026-018 is about. The raised message is the observable artifact that
    the env var is missing.

    set_session(readonly=True) is a second, independent guard on top of the
    role's grants: the transaction refuses writes even if the grants are later
    widened. statement_timeout is NOT set here — it rides on the role
    (ALTER ROLE nlq_readonly SET statement_timeout), so it cannot be lost by a
    code change to this function.
    """
    url = os.environ.get('DATABASE_URL_NLQ')
    if not url:
        raise ValueError(
            "DATABASE_URL_NLQ environment variable not set — the NLQ SELECT-only "
            "role is required; refusing to fall back to the read-write DATABASE_URL"
        )
    kwargs = {} if 'sslmode=' in url else {'sslmode': 'require'}
    conn = psycopg2.connect(url, **kwargs)
    conn.cursor_factory = RealDictCursor
    conn.set_session(readonly=True)
    return conn


# Pure forwarders to db.get_db. Every route module keeps a local accessor of
# this shape: routes/verify.py:47, routes/billing.py:167, routes/monitor.py:149,
# routes/waitlist.py:41, auth.py:68, admin.py:30, plus ebay_oauth.py and
# ebay_valuation.py. 67 of the ~136 checkout sites in this codebase reach the
# pool through one of them.
#
# A naive sys._getframe(2) resolves to "whoever called db.get_db", which for all
# of those is the forwarder itself. That is worse than the bare count it
# replaces: it is a confident, constant, WRONG file:line pointing at a
# three-line function that provably cannot leak, and nothing in the output
# distinguishes it from a correct answer. So we walk past them, and when we
# cannot vouch for a frame we say "<unresolved>" instead of naming one.
_FORWARDER_NAMES = frozenset((
    'get_db', 'get_db_connection', 'get_conn', 'get_connection',
))
_MAX_FRAME_WALK = 12      # bounded: never walk an arbitrarily deep stack
_MAX_SITES_LOGGED = 5     # bounded: one leak line must not become unbounded


def _short_path(path):
    """Last two path segments. Bare basename collapses routes/monitor.py and any
    same-named root module to 'monitor.py'."""
    parts = str(path).replace('\\', '/').rstrip('/').split('/')
    return '/'.join(parts[-2:]) if len(parts) >= 2 else parts[-1]


def _resolve_checkout_site():
    """Name the handler that checked a connection out, or admit it could not.

    Walks out of this module, then past any pure forwarder (see
    _FORWARDER_NAMES). Returns "<unresolved...>" rather than naming a frame it
    cannot vouch for — an honest gap is useful, a confident wrong file is not.
    Never raises; the caller must always get a string.
    """
    try:
        import sys as _sys
        f = _sys._getframe(1)
    except Exception:
        return "<unresolved: no frame access>"
    skipped = 0
    try:
        for _ in range(_MAX_FRAME_WALK):
            if f is None:
                return "<unresolved: end of stack>"
            if f.f_globals.get('__name__', '') == __name__:
                f = f.f_back           # still inside db.py
                continue
            if f.f_code.co_name in _FORWARDER_NAMES:
                skipped += 1
                f = f.f_back           # a shim, not the handler
                continue
            via = " (via %d forwarder%s)" % (skipped, "" if skipped == 1 else "s") if skipped else ""
            return "%s:%d in %s()%s" % (
                _short_path(f.f_code.co_filename), f.f_lineno, f.f_code.co_name, via)
        return "<unresolved: walk limit>"
    except Exception:
        return "<unresolved: frame walk failed>"


def _register_for_teardown(proxy):
    """Track request-scoped checkouts on flask.g so the wsgi teardown hook can
    force-return anything a handler leaked on an exception path. Outside an
    app context (background threads, scripts) this is a no-op — those callers
    must close explicitly, as they already do."""
    try:
        from flask import g, has_app_context
        if has_app_context():
            conns = getattr(g, '_db_pool_conns', None)
            if conns is None:
                conns = []
                g._db_pool_conns = conns
            # Capture the checkout SITE so return_leaked() can name the handler
            # that forgot to close instead of only counting it. Frame walking is
            # O(depth) with no source reads, unlike traceback.extract_stack(),
            # which walks AND formats the whole stack on every checkout.
            # Only frame metadata (str, int) is kept — no frame object escapes
            # this call, so there is no reference cycle.
            # NOTE: entries are (proxy, site) tuples. return_leaked() unpacks
            # them, and tolerates a bare proxy if this ever changes.
            conns.append((proxy, _resolve_checkout_site()))
    except Exception:
        pass


def return_leaked():
    """wsgi teardown hook: return any connection the ending request checked
    out but never closed (a missing finally on an exception path). Makes
    close-not-in-finally harmless in the web path."""
    returned = 0
    failures = 0
    sites = {}
    try:
        from flask import g
        conns = getattr(g, '_db_pool_conns', None) or []
    except Exception:
        return 0
    try:
        for entry in conns:
            # PER-ENTRY isolation, deliberately. This loop previously sat inside
            # one blanket `except Exception: pass`, so a single malformed entry
            # raised, aborted the loop, left EVERY other connection in the
            # request checked out, skipped the list clear, returned 0 and logged
            # nothing. A pool-exhaustion guard that fails silently and
            # successfully is the exact defect class it exists to prevent.
            try:
                if isinstance(entry, tuple) and len(entry) == 2:
                    proxy, site = entry
                else:
                    proxy, site = entry, "<unresolved: malformed entry>"
                if object.__getattribute__(proxy, '_returned'):
                    continue
                proxy.close()
                returned += 1
                sites[site] = sites.get(site, 0) + 1
            except Exception:
                failures += 1
    finally:
        # Always clear, even if every entry above failed. A retained list would
        # be re-walked by the next teardown on this (recycled) context.
        try:
            g._db_pool_conns = []
        except Exception:
            pass
    if returned or failures:
        if returned:
            _count('leaks_returned', returned)
        # Dedupe with counts: a leak inside a loop is one site N times, not N
        # sites. Capped so one request cannot emit an unbounded log line.
        ranked = sorted(sites.items(), key=lambda kv: -kv[1])
        parts = ["%s (x%d)" % (s, n) if n > 1 else s for s, n in ranked[:_MAX_SITES_LOGGED]]
        if len(ranked) > _MAX_SITES_LOGGED:
            parts.append("... +%d more site(s)" % (len(ranked) - _MAX_SITES_LOGGED))
        where = ", ".join(parts) if parts else "<unresolved>"
        extra = f"; {failures} entr(ies) could not be returned" if failures else ""
        print(f"[DB] teardown returned {returned} leaked connection(s) — "
              f"checked out at {where}; that handler is missing close(); "
              f"pool unharmed{extra}")
    return returned


def pool_stats():
    """Diagnostics for /api/admin/dependency-status (item 2f). Per-process:
    each gunicorn worker reports its own pool."""
    with _stats_lock:
        snapshot = dict(_stats)
    in_use = 0
    if _pool is not None and _pool_pid == os.getpid():
        try:
            in_use = len(_pool._used)  # psycopg2 internal, diagnostics only
        except Exception:
            in_use = -1
    snapshot.update({
        'pid': os.getpid(),
        'pool_max': DB_POOL_MAX,
        'in_use': in_use,
        'disabled': os.environ.get('DB_POOL_DISABLED') == '1',
    })
    return snapshot
