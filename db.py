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
            conns.append(proxy)
    except Exception:
        pass


def return_leaked():
    """wsgi teardown hook: return any connection the ending request checked
    out but never closed (a missing finally on an exception path). Makes
    close-not-in-finally harmless in the web path."""
    returned = 0
    try:
        from flask import g
        conns = getattr(g, '_db_pool_conns', None) or []
        for proxy in conns:
            if not object.__getattribute__(proxy, '_returned'):
                proxy.close()
                returned += 1
        g._db_pool_conns = []
    except Exception:
        pass
    if returned:
        _count('leaks_returned', returned)
        print(f"[DB] teardown returned {returned} leaked connection(s) — "
              f"a handler in this request is missing close(); pool unharmed")
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
