"""
eBay Sales Blueprint - Batch ingestion, title backfill, and stats
Routes: /api/ebay-sales/*
"""
import os
import re
import base64
import hashlib
import threading
import requests
from flask import Blueprint, jsonify, request
import psycopg2
from psycopg2.extras import execute_values
import db as _dbpool

# NORMALIZATION IMPORT
from title_normalizer import normalize_title

# Create blueprint
ebay_sales_bp = Blueprint('ebay_sales', __name__, url_prefix='/api')

# Module imports (will be set by wsgi.py)
upload_image = None
R2_AVAILABLE = False


def init_modules(r2_available, upload_image_func):
    """Initialize modules from wsgi.py"""
    global R2_AVAILABLE, upload_image
    R2_AVAILABLE = r2_available
    upload_image = upload_image_func


# ─────────────────────────────────────────────────────────────────────────────
# R2 cover backup — moved OFF the request path (2026-08-02)
#
# WHY: downloading + re-uploading ~240 covers INSIDE the request was the bulk
# of the response time measured in `request_logs` on 2026-08-02: 293 batch
# requests, ALL status 200, avg 41,552ms, max 184,417ms. The requests were
# succeeding; the client timed out waiting and the extension mislabelled it
# "backend offline". Backup now runs on a daemon thread AFTER the response,
# same fire-and-forget contract as grade_retention.persist_grade_submission_async
# and lookup_demand.record_lookup_async: never blocks, never raises, no-ops
# when R2 is unconfigured.
#
# ⚠️ SILENT-FAILURE GUARD. Off the response path, nothing surfaces a permanent
# R2 outage. Two independent signals:
#   1. DURABLE (primary) — the data reports on itself. `ebay_sales.r2_image_url`
#      stays NULL when a backup did not happen, and `image_url` is ALWAYS
#      retained, so a failed/shed backup is re-runnable and is never data loss.
#      Detection query is in the Unit 1 notes; no code can silence it.
#   2. IN-PROCESS — _r2_stats counters + ONE WARN line at 25 consecutive
#      failures, then every 250, so a broken R2 shows in Render logs without
#      flooding them. Recovery logs once.
#
# ⚠️ MEMORY BOUND (L-SW-2026-012). Each cover is held in memory as bytes AND as
# base64. Unbounded overlapping batches on a 2GB instance is exactly the July
# OOM shape, so concurrent backup batches are capped and excess batches are
# SHED (counted + logged), never queued.
# ─────────────────────────────────────────────────────────────────────────────

_r2_stats = {
    'succeeded': 0,
    'failed': 0,
    'skipped_no_image': 0,
    'shed_overloaded': 0,
    'consecutive_failures': 0,
    'last_error': None,
}
_r2_lock = threading.Lock()
_r2_inflight = 0

_R2_MAX_INFLIGHT_BATCHES = 2    # concurrent backup batches; excess is shed
_R2_WORKERS = 5                 # per-batch image concurrency (unchanged)
_R2_ALERT_AT = 25               # first WARN after N consecutive failures
_R2_ALERT_EVERY = 250           # then every N, to cap log volume


def _r2_note(kind, error=None):
    """Record one image outcome. Emits a WARN line when failures look systemic.

    Distinguishing 'skipped_no_image' from 'failed' is the point: the previous
    nested helper returned None for both, so a totally broken R2 was
    indistinguishable from a batch of listings that had no images."""
    with _r2_lock:
        _r2_stats[kind] = _r2_stats.get(kind, 0) + 1
        if kind == 'failed':
            _r2_stats['consecutive_failures'] += 1
            _r2_stats['last_error'] = str(error)[:200] if error else 'unknown'
            cf = _r2_stats['consecutive_failures']
            if cf == _R2_ALERT_AT or (cf > _R2_ALERT_AT and cf % _R2_ALERT_EVERY == 0):
                print(f"[R2Backup] WARNING: {cf} consecutive cover-backup failures "
                      f"(ok={_r2_stats['succeeded']} failed={_r2_stats['failed']}). "
                      f"Last error: {_r2_stats['last_error']}")
        elif kind == 'succeeded':
            cf = _r2_stats['consecutive_failures']
            if cf >= _R2_ALERT_AT:
                print(f"[R2Backup] RECOVERED after {cf} consecutive failures")
            _r2_stats['consecutive_failures'] = 0


# eBay's image CDN encodes the served size in the path: .../s-l500.webp. The
# collector reads imageEl.src off the SEARCH RESULTS page, where eBay renders
# s-l500 -- and _backup_one_image mirrors those bytes verbatim (there is no
# resize on our side), so the whole corpus sat at 500px on the long edge:
# 30 of 30 sampled covers, every price band, zero variance.
#
# 500px (~0.17MP) is marginal for reading condition off a cover -- plausibly
# enough to separate PR/FR from NM, plausibly not enough for GD/VG/FN, which is
# where the raw pool's dispersion actually lives.
#
# Rewriting the size token fixes it for ZERO extra requests: this function
# already makes exactly one CDN GET per image, and this only changes the URL
# string of that same GET. No item pages, no pagination, no collector change --
# the capture-safety invariant is untouched.
#
# Measured 2026-08-14 on 4 real sold listings: s-l1600 returns 3-10x the pixels
# of s-l500 (800x1200 .. 1600x1200). s-l2400 returns a BYTE-IDENTICAL file, so
# 1600 is the real ceiling, not an arbitrary pick -- do not raise it expecting
# more.
#
# GOING FORWARD ONLY. The 143,118 covers already in R2 stay at 500px; the
# original eBay URL is retained in ebay_sales.image_url so a backfill is
# possible, but 143k CDN GETs is well above normal batch rate and is NOT
# authorized. Do not add one without Mike's explicit go.
_EBAY_SIZE_TOKEN = re.compile(r's-l\d+')
_EBAY_TARGET_SIZE = 's-l1600'


def _upsize_ebay_image_url(url):
    """Point an eBay CDN thumbnail URL at the full-size variant.

    Returns (preferred_url, fallback_url). Non-eBay or unrecognized URLs come
    back unchanged with no fallback. The fallback matters: a listing whose
    seller image has no 1600px variant must still back up at its original size
    rather than losing the cover entirely."""
    if 'ebayimg.com' not in url or not _EBAY_SIZE_TOKEN.search(url):
        return url, None
    upsized = _EBAY_SIZE_TOKEN.sub(_EBAY_TARGET_SIZE, url)
    return (upsized, url) if upsized != url else (url, None)


def _backup_one_image(sale):
    """Download one cover from eBay, upload to R2. Returns dict or None. Never raises."""
    image_url = sale.get('image_url', '')
    ebay_item_id = sale.get('ebay_item_id', '')
    if not image_url or not ebay_item_id:
        _r2_note('skipped_no_image')
        return None
    try:
        fetch_url, fallback_url = _upsize_ebay_image_url(image_url)
        resp = requests.get(fetch_url, timeout=10)
        # Fall back to the as-captured URL if the upsized variant is missing, so
        # a 404 on s-l1600 degrades to the old 500px behaviour instead of
        # dropping the cover.
        if resp.status_code != 200 and fallback_url:
            resp = requests.get(fallback_url, timeout=10)
        if resp.status_code != 200:
            _r2_note('failed', f"eBay image GET returned {resp.status_code}")
            return None
        content_type = resp.headers.get('Content-Type', 'image/jpeg')
        ext = 'webp' if 'webp' in content_type else 'jpg'
        image_b64 = base64.b64encode(resp.content).decode('utf-8')
        result = upload_image(image_b64, f"ebay-covers/{ebay_item_id}.{ext}", content_type)
        if result and result.get('success'):
            _r2_note('succeeded')
            return {'ebay_item_id': ebay_item_id, 'r2_url': result['url']}
        _r2_note('failed', (result or {}).get('error', 'upload_image reported no success'))
        return None
    except Exception as e:
        _r2_note('failed', e)
        return None


def backup_images_async(sales):
    """Fire-and-forget cover backup for freshly-inserted sales.

    Never blocks the caller, never raises. No-ops when R2 is unconfigured.
    Sheds (does not queue) work beyond _R2_MAX_INFLIGHT_BATCHES so peak memory
    stays bounded; a shed batch keeps its image_url and stays re-runnable."""
    global _r2_inflight
    if not sales:
        return
    if not R2_AVAILABLE or upload_image is None:
        return          # R2 not configured — image_url is still stored on the row
    with _r2_lock:
        if _r2_inflight >= _R2_MAX_INFLIGHT_BATCHES:
            _r2_stats['shed_overloaded'] += 1
            shed = _r2_stats['shed_overloaded']
            if shed == 1 or shed % 50 == 0:
                print(f"[R2Backup] shed batch of {len(sales)} — "
                      f"{_r2_inflight} batches already in flight ({shed} shed total). "
                      f"image_url retained; recoverable by backfill.")
            return
        _r2_inflight += 1
    try:
        threading.Thread(target=_backup_images, args=(list(sales),), daemon=True).start()
    except Exception as e:
        with _r2_lock:
            _r2_inflight -= 1
        print(f"[R2Backup] could not start backup thread (non-fatal): {e}")


def _backup_images(sales):
    """Back up a batch of covers, then write r2_image_url in ONE commit. Never raises."""
    global _r2_inflight
    from concurrent.futures import ThreadPoolExecutor, as_completed
    conn = None
    try:
        updates = []
        with ThreadPoolExecutor(max_workers=_R2_WORKERS) as executor:
            futures = [executor.submit(_backup_one_image, s) for s in sales]
            for future in as_completed(futures):
                try:
                    r = future.result()
                except Exception as e:
                    _r2_note('failed', e)
                    continue
                if r:
                    updates.append((r['r2_url'], r['ebay_item_id']))
        if updates:
            conn = _dbpool.get_db()
            cur = conn.cursor()
            # ONE commit for the whole batch (was one commit per image).
            cur.executemany(
                "UPDATE ebay_sales SET r2_image_url = %s WHERE ebay_item_id = %s",
                updates)
            conn.commit()
            cur.close()
    except Exception as e:
        print(f"[R2Backup] batch failed (non-fatal): {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        with _r2_lock:
            _r2_inflight -= 1


def normalize_ebay_sale(sale_dict):
    """
    Normalize an eBay sale dictionary in-place.
    Call this for each sale before INSERT.
    """
    raw_title = sale_dict.get('raw_title')

    if raw_title:
        try:
            normalized = normalize_title(raw_title)

            # Add normalized fields
            sale_dict['canonical_title'] = normalized['canonical_title']
            sale_dict['issue_number'] = normalized['issue_number']
            sale_dict['title_year'] = normalized.get('title_year')
            sale_dict['grade_from_title'] = normalized['grade_from_title']
            sale_dict['grading_company'] = normalized['grading_company']
            sale_dict['is_facsimile'] = normalized['is_facsimile']
            sale_dict['is_reprint'] = normalized['is_reprint']
            sale_dict['is_variant'] = normalized['is_variant']
            sale_dict['is_signed'] = normalized['is_signed']
            sale_dict['is_lot'] = normalized['is_lot']
            sale_dict['is_key_issue'] = normalized['is_key_issue']
            sale_dict['key_issue_claim'] = normalized['key_issue_claim']
            sale_dict['creators'] = normalized['creators']
            sale_dict['title_notes'] = normalized['title_notes']
        except Exception as e:
            print(f"Title normalization failed for: {raw_title}")
            print(f"Error: {str(e)}")
            # Continue without normalization - sale still gets saved

    return sale_dict


@ebay_sales_bp.route('/ebay-sales/batch', methods=['POST'])
def add_ebay_sales_batch():
    """Batch insert eBay sales from the browser extension.

    Response time is the DB insert ONLY. Cover backup to R2 runs after the
    response on a daemon thread (backup_images_async) — see the module header
    for why and for the silent-failure guard.
    """
    database_url = os.environ.get('DATABASE_URL')
    conn = None

    try:
        data = request.get_json()
        sales = data.get('sales', [])

        if not sales:
            return jsonify({'error': 'No sales provided'}), 400

        # NORMALIZE EACH SALE BEFORE INSERT
        for sale in sales:
            sale = normalize_ebay_sale(sale)

        conn = _dbpool.get_db()
        cur = conn.cursor()

        saved = 0
        duplicates = 0
        saved_sales = []  # Track which sales were actually saved
        poisoned = False  # transaction unrecoverably aborted mid-batch
        row_errors = 0    # fallback rows that RAISED (vs were cleanly deduped)
        last_row_error = None

        # ── Step 1: insert the batch ────────────────────────────────────────
        #
        # SHAPE: optimistic BULK insert, with the per-row loop kept as a FALLBACK.
        #
        # WHY BULK: the per-row loop is ROUND-TRIP bound, not commit bound.
        # Measured on deploy a80b5cd (~1,000 sales): avg 9,721ms / max 40,055ms
        # for ~240-row batches. At 3 statements per row that is ~720 round trips,
        # implying ~14–40ms RTT to Render Postgres — an order of magnitude above
        # the 1–3ms assumed when the loop was written. Collapsing the inserts into
        # ONE statement makes the whole batch 5 round trips:
        #   BEGIN · SAVEPOINT · execute_values · RELEASE · COMMIT
        # (psycopg2 issues the implicit BEGIN as its own round trip; db.py also adds
        # a SELECT 1 pre-ping per pool checkout. Both immaterial to the win, but the
        # count is stated honestly because this comment is a measured-claims record.)
        #
        # ✅ VERIFIED IN PRODUCTION on deploy 680f243 (2026-08-03):
        #     19:52   7 reqs  avg 44,083ms   <- last v2 minute
        #     19:57  12 reqs  avg    848ms  max 2,207ms
        #     19:58  10 reqs  avg    547ms  max 1,706ms
        #     19:59  12 reqs  avg    940ms  max 3,233ms
        # Sub-second at 10–12 req/min — HEAVIER concurrency than any minute in the
        # v2 data — and the self-congestion ramp is gone. ~50x off the original
        # 41.5s baseline. No 10s+ readings, which is the tell that the bulk path is
        # SUCCEEDING rather than aborting into the per-row fallback: the untargeted
        # ON CONFLICT (see below) is what makes that true. If avg ever climbs back
        # toward 10s, suspect the fallback firing and check for the
        # "[eBayBatch] bulk insert failed" log line before anything else.
        #
        # ⚠️ PER-ROW ERROR ISOLATION IS NOT GIVEN UP. A bulk statement aborts
        # entirely on one malformed row, which would resurrect exactly the
        # regression the SAVEPOINT was added to prevent. So the bulk attempt is
        # itself wrapped in a savepoint: if it raises for ANY reason, we ROLLBACK
        # TO that savepoint (which clears psycopg2's aborted-transaction state)
        # and re-run the SAME batch through the unchanged per-row loop, which
        # isolates the offending row and counts it as a duplicate exactly as
        # before. Cost of one bad row: a wasted bulk attempt, then old behaviour.
        # Nothing is committed until after whichever path ran.
        #
        # This also retires cost 3 from the previous revision (subtransaction-cache
        # overflow): the happy path now creates ONE subtransaction, not ~240.
        # Costs 1 and 2 still stand and are restated at the commit below.

        INSERT_COLUMNS = (
            'raw_title', 'parsed_title', 'issue_number', 'publisher',
            'sale_price', 'sale_date', 'condition', 'graded', 'grade',
            'listing_url', 'image_url', 'ebay_item_id', 'content_hash',
            'canonical_title', 'grade_from_title', 'grading_company',
            'is_facsimile', 'is_reprint', 'is_variant', 'is_signed', 'is_lot',
            'is_key_issue', 'key_issue_claim', 'creators', 'title_notes',
            'title_year',
        )

        def _row_tuple(sale):
            """Positional values for INSERT_COLUMNS. Same fields/defaults as before."""
            content = f"{sale.get('raw_title', '')}|{sale.get('sale_price', '')}|{sale.get('sale_date', '')}"
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:32]
            return (
                sale.get('raw_title'),
                sale.get('parsed_title'),
                sale.get('issue_number'),
                sale.get('publisher'),
                sale.get('sale_price'),
                sale.get('sale_date'),
                sale.get('condition'),
                sale.get('graded', False),
                sale.get('grade'),
                sale.get('listing_url'),
                sale.get('image_url'),
                sale.get('ebay_item_id'),
                content_hash,
                # Normalized fields
                sale.get('canonical_title'),
                sale.get('grade_from_title'),
                sale.get('grading_company'),
                sale.get('is_facsimile', False),
                sale.get('is_reprint', False),
                sale.get('is_variant', False),
                sale.get('is_signed', False),
                sale.get('is_lot', False),
                sale.get('is_key_issue', False),
                sale.get('key_issue_claim'),
                sale.get('creators'),
                sale.get('title_notes'),
                sale.get('title_year'),
            )

        _COL_SQL = ', '.join(INSERT_COLUMNS)

        # --- fast path -------------------------------------------------------
        bulk_ok = False
        try:
            cur.execute("SAVEPOINT sw_bulk")
            returned = execute_values(
                cur,
                # ⚠️ UNTARGETED `ON CONFLICT DO NOTHING` — deliberate. ebay_sales
                # has TWO unique indexes, not one:
                #     ebay_sales_ebay_item_id_key  UNIQUE (ebay_item_id)
                #     ebay_sales_content_hash_key  UNIQUE (content_hash)
                # A targeted `ON CONFLICT (ebay_item_id)` absorbs conflicts on that
                # index ONLY, so a content_hash collision raises UniqueViolation and
                # aborts the WHOLE bulk statement — forcing the per-row fallback and
                # making the batch strictly slower than the per-row version this
                # replaces. content_hash is sha256(raw_title|sale_price|sale_date),
                # and sale_date is DATE-granular, so two different listings of the
                # same book at the same price on the same day collide. That is
                # common: 1,585 (raw_title, sale_price) pairs recur in the corpus,
                # the worst 9 times. Those collisions have ALWAYS been rejected —
                # which is why the table shows 101,064 rows / 101,064 distinct
                # hashes; the uniqueness is the constraint working, not the data
                # being naturally unique.
                # Untargeted absorbs any unique violation, which is exactly the
                # EFFECTIVE behaviour of both previous versions (they caught the
                # exception and counted it as a duplicate) — same counts, no abort.
                f"INSERT INTO ebay_sales ({_COL_SQL}) VALUES %s "
                f"ON CONFLICT DO NOTHING RETURNING ebay_item_id",
                [_row_tuple(s) for s in sales],
                # page_size bounds the SQL STRING size, not a parameter count:
                # execute_values interpolates client-side via cur.mogrify and sends
                # one literal statement with ZERO bind parameters, so Postgres'
                # 65,535-parameter limit does not apply here at all. fetch=True
                # accumulates RETURNING rows across every page (psycopg2 extends
                # one result list per page), so `saved` is correct above 500 rows.
                page_size=500,
                fetch=True,
            )
            cur.execute("RELEASE SAVEPOINT sw_bulk")
            bulk_ok = True
        except Exception as bulk_err:
            print(f"[eBayBatch] bulk insert failed ({bulk_err}) — "
                  f"falling back to per-row for this batch of {len(sales)}")
            try:
                cur.execute("ROLLBACK TO SAVEPOINT sw_bulk")
                cur.execute("RELEASE SAVEPOINT sw_bulk")
            except Exception:
                poisoned = True

        if bulk_ok:
            # DEDUP ACCOUNTING. RETURNING yields one row per ACTUALLY INSERTED
            # row; skipped conflicts return nothing. So there is no per-row
            # `rowcount` to read and the duplicate count is arithmetic:
            #     saved      = len(returned)
            #     duplicates = len(sales) - saved
            # This is exactly equivalent to the old per-row tally:
            #   · already-committed conflict → not returned → duplicate ✔
            #   · duplicate WITHIN this batch → ON CONFLICT DO NOTHING skips it
            #     silently (the "cannot affect row a second time" error is
            #     DO UPDATE-only), so it is not returned → duplicate ✔
            #   · genuinely new row → returned → saved ✔
            saved = len(returned)
            duplicates = len(sales) - saved

            # Rebuild saved_sales (needed for the R2 dispatch) by id. Dedup the
            # walk: an intra-batch duplicate id appears twice in `sales` but was
            # inserted once, and double-counting it here would make
            # len(saved_sales) exceed `saved`.
            inserted_ids = {r[0] for r in returned if r and r[0] is not None}
            seen_ids = set()
            for sale in sales:
                sid = sale.get('ebay_item_id')
                if sid in inserted_ids and sid not in seen_ids:
                    seen_ids.add(sid)
                    saved_sales.append(sale)
            # NOTE: a row with a NULL ebay_item_id still inserts (NULLs do not
            # conflict in a unique index) and is counted in `saved`, but cannot be
            # matched back here — so len(saved_sales) may be < saved. Not a
            # regression: backup_images_async already skips ids that are falsy,
            # and the extension filters such rows out before sending.

        elif not poisoned:
            # --- fallback: per-row, unchanged behaviour -----------------------
            for sale in sales:
                try:
                    cur.execute("SAVEPOINT sw_row")
                    # Untargeted for the same reason as the bulk path: absorbs a
                    # content_hash collision as rowcount 0 instead of raising into
                    # the handler below. Same duplicate count either way, one fewer
                    # savepoint round trip per collision.
                    cur.execute(
                        f"INSERT INTO ebay_sales ({_COL_SQL}) "
                        f"VALUES ({', '.join(['%s'] * len(INSERT_COLUMNS))}) "
                        f"ON CONFLICT DO NOTHING",
                        _row_tuple(sale))

                    if cur.rowcount > 0:
                        saved += 1
                        saved_sales.append(sale)
                    else:
                        duplicates += 1

                    cur.execute("RELEASE SAVEPOINT sw_row")

                except Exception as e:
                    # ⚠️ This still counts a genuine failure (deadlock, serialization
                    # failure, unadaptable value) as a "duplicate" and returns
                    # success:True — pre-existing behaviour, NOT introduced here. But
                    # v3 routes EVERY bulk failure through this loop, widening the
                    # error class that lands in it, so the count is now tracked and
                    # logged separately instead of vanishing into `duplicates`.
                    row_errors += 1
                    last_row_error = str(e)[:200]
                    duplicates += 1
                    try:
                        cur.execute("ROLLBACK TO SAVEPOINT sw_row")
                        cur.execute("RELEASE SAVEPOINT sw_row")
                    except Exception:
                        # Could not unwind. The transaction is aborted, every later
                        # row would fail, and psycopg2's commit() on an aborted
                        # transaction silently becomes ROLLBACK — which would return
                        # success:True having written NOTHING. Fail loudly instead.
                        poisoned = True
                        break

        if poisoned:
            conn.rollback()
            return jsonify({'error': 'transaction aborted mid-batch; no rows written'}), 500

        # ONE commit for the whole batch. Two standing costs of batching (both
        # unchanged by the bulk fast path):
        #   1. DURABILITY GRANULARITY — a crash mid-batch loses the whole batch
        #      rather than the rows already committed. Acceptable: the extension
        #      still holds them and re-sending is idempotent.
        #   2. CONFLICT WAITS + A REAL DEADLOCK WINDOW — ON CONFLICT against an
        #      UNCOMMITTED duplicate takes XactLockTableWait on the inserting
        #      transaction, not an index check, so a concurrent overlapping batch
        #      waits for this whole batch. Two overlapping batches touching the
        #      same ids in different orders CAN deadlock (DO NOTHING removes the
        #      row-update conflict class, not the xact wait); Postgres aborts one,
        #      surfacing as a 500 — safe (no lost write, extension buffers,
        #      re-sync idempotent) but not "no deadlock". Rare with a single
        #      operator, and the shorter transaction narrows the window further.
        conn.commit()

        # Step 2: cover backup — dispatched AFTER the rows are durable and
        # returns immediately; the work happens on a daemon thread. Must come
        # after commit() so the UPDATE in that thread can see the rows.
        backup_images_async(saved_sales)

        if row_errors:
            print(f"[eBayBatch] {row_errors} of {len(sales)} rows RAISED in the per-row "
                  f"fallback and are counted in `duplicates`. Last error: {last_row_error}")

        return jsonify({
            'success': True,
            'saved': saved,
            'duplicates': duplicates,
            # >0 means some of `duplicates` were genuine errors, not dedup.
            'row_errors': row_errors,
            # Renamed from images_backed_up: backup is now asynchronous, so the
            # response cannot know the outcome. This is what was DISPATCHED.
            'images_queued': len(saved_sales),
            'total': len(sales)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@ebay_sales_bp.route('/ebay-sales/backfill-titles', methods=['POST'])
def backfill_canonical_titles():
    """
    Re-run title_normalizer on all ebay_sales with NULL canonical_title.
    POST /api/ebay-sales/backfill-titles
    Optional query param: ?limit=100 (default: all)
    """
    database_url = os.environ.get('DATABASE_URL')
    conn = None
    try:
        limit = request.args.get('limit', type=int)
        conn = _dbpool.get_db()
        cur = conn.cursor()

        # Fetch all records with NULL canonical_title
        query = "SELECT id, raw_title FROM ebay_sales WHERE canonical_title IS NULL"
        if limit:
            query += f" LIMIT {limit}"
        cur.execute(query)
        rows = cur.fetchall()

        if not rows:
            return jsonify({'success': True, 'message': 'No NULL canonical_titles found', 'updated': 0})

        updated = 0
        failed = 0
        failures = []

        for row_id, raw_title in rows:
            if not raw_title:
                failed += 1
                continue

            try:
                normalized = normalize_title(raw_title)
                canonical = normalized.get('canonical_title')

                if canonical:
                    cur.execute("""
                        UPDATE ebay_sales SET
                            canonical_title = %s,
                            grade_from_title = %s,
                            grading_company = %s,
                            is_facsimile = %s,
                            is_reprint = %s,
                            is_variant = %s,
                            is_signed = %s,
                            is_lot = %s,
                            is_key_issue = %s,
                            key_issue_claim = %s,
                            creators = %s,
                            title_notes = %s,
                            title_year = %s
                        WHERE id = %s
                    """, (
                        canonical,
                        normalized.get('grade_from_title'),
                        normalized.get('grading_company'),
                        normalized.get('is_facsimile', False),
                        normalized.get('is_reprint', False),
                        normalized.get('is_variant', False),
                        normalized.get('is_signed', False),
                        normalized.get('is_lot', False),
                        normalized.get('is_key_issue', False),
                        normalized.get('key_issue_claim'),
                        normalized.get('creators'),
                        normalized.get('title_notes'),
                        normalized.get('title_year')
                    ))
                    updated += 1
                else:
                    failed += 1
                    failures.append({'id': row_id, 'raw_title': raw_title, 'reason': 'normalizer returned None'})
            except Exception as e:
                failed += 1
                failures.append({'id': row_id, 'raw_title': raw_title, 'reason': str(e)})

        conn.commit()

        return jsonify({
            'success': True,
            'total_null': len(rows),
            'updated': updated,
            'still_null': failed,
            'sample_failures': failures[:20]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@ebay_sales_bp.route('/ebay-sales/stats', methods=['GET'])
def get_ebay_sales_stats():
    """Get statistics about collected eBay sales"""
    database_url = os.environ.get('DATABASE_URL')
    conn = None
    try:
        conn = _dbpool.get_db()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM ebay_sales")
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM ebay_sales
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
        """)
        last_week = cur.fetchone()[0]

        return jsonify({
            'total_sales': total,
            'last_7_days': last_week
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()
