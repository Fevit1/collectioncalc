"""Lookup-demand instrumentation.

Logs one lightweight row per valuation lookup (/api/sales/valuation and
/api/sales/fmv) so that real usage becomes a DEMAND-RANKED backfill list:
"which titles do users search that return NO or THIN data?" — the signal that
tells us where to deepen coverage (and validates the variant-reclamation work).

Design constraints (see DO brief): this must NEVER add latency to, or risk
breaking, a valuation response. So the insert runs on a daemon thread (same
pattern as grade_retention.persist_grade_submission_async) and every failure is
swallowed + logged. All Flask request state (g.user_id etc.) is resolved by the
caller and passed in — this code runs outside the request context.

Purely additive: writes to the new lookup_demand table only; touches nothing in
the existing valuation logic or response shape.
"""
import threading
import psycopg2


def record_lookup_async(database_url, **fields):
    """Fire-and-forget: spawn a daemon thread to write one lookup_demand row.

    Never blocks the caller; never raises. If database_url is missing we no-op
    (so the valuation path is unaffected when the env isn't configured)."""
    if not database_url:
        return
    try:
        t = threading.Thread(target=_record_lookup, args=(database_url, fields), daemon=True)
        t.start()
    except Exception as e:  # thread creation itself must never break a response
        print(f"[LookupDemand] could not start logger thread (non-fatal): {e}")


def _record_lookup(database_url, f):
    """Insert one row. Never raises."""
    conn = None
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO lookup_demand
                 (endpoint, title, canonical_title, issue, issue_type,
                  requested_grade, comp_count, graded_count, exact_count,
                  fmv_method, estimated, no_data, user_id, is_internal)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                f.get('endpoint'),
                f.get('title'),
                f.get('canonical_title'),
                f.get('issue'),
                f.get('issue_type'),
                f.get('requested_grade'),
                f.get('comp_count'),
                f.get('graded_count'),
                f.get('exact_count'),
                f.get('fmv_method'),
                bool(f.get('estimated')),
                bool(f.get('no_data')),
                f.get('user_id'),
                bool(f.get('is_internal')),
            ),
        )
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"[LookupDemand] record failed (non-fatal): {e}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
