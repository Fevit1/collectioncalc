"""
eBay Sales Blueprint - Batch ingestion, title backfill, and stats
Routes: /api/ebay-sales/*
"""
import os
import base64
import hashlib
import threading
import requests
from flask import Blueprint, jsonify, request
import psycopg2
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


def _backup_one_image(sale):
    """Download one cover from eBay, upload to R2. Returns dict or None. Never raises."""
    image_url = sale.get('image_url', '')
    ebay_item_id = sale.get('ebay_item_id', '')
    if not image_url or not ebay_item_id:
        _r2_note('skipped_no_image')
        return None
    try:
        resp = requests.get(image_url, timeout=10)
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

        # Step 1: insert every sale in ONE transaction (was one commit PER ROW —
        # 240 sequential fsync round-trips to Render Postgres per batch).
        #
        # ⚠️ The per-row SAVEPOINT is load-bearing, not decoration. With a single
        # transaction, the pre-existing `except: conn.rollback()` would discard
        # the ENTIRE batch on one malformed row instead of just that row. The
        # savepoint preserves the old per-row error isolation. ROLLBACK TO
        # SAVEPOINT also clears psycopg2's aborted-transaction state, so the loop
        # can continue after a bad row.
        #
        # ON CONFLICT (ebay_item_id) DO NOTHING is UNAFFECTED by the change — it
        # resolves against the unique index, not against commit boundaries:
        #   · conflict with an already-committed row  → rowcount 0, as before
        #   · conflict with a row inserted EARLIER IN THIS BATCH → the pending
        #     tuple is already in the index inside this transaction, so it still
        #     conflicts → rowcount 0, as before
        #   · conflict with a row a CONCURRENT request has inserted but not yet
        #     committed → resolves as a no-op, but see the cost below
        #
        # Three costs this DOES introduce — recorded rather than glossed:
        #   1. DURABILITY GRANULARITY. A crash mid-batch now loses the whole batch
        #      rather than the rows already committed. Acceptable: the extension
        #      still holds them locally and re-sending is idempotent.
        #   2. LONGER CONFLICT WAITS + A REAL DEADLOCK WINDOW. ON CONFLICT against
        #      an uncommitted duplicate does NOT resolve at the index — it takes
        #      XactLockTableWait on the inserting transaction. Previously that
        #      released after one row; now a concurrent overlapping batch waits for
        #      THIS ENTIRE batch to commit. Two overlapping batches touching the
        #      same ids in different orders CAN deadlock (DO NOTHING removes the
        #      row-update conflict class, not the xact wait). Postgres detects it
        #      and aborts one, which surfaces as a 500 — safe (no lost write, the
        #      extension buffers and re-sync is idempotent), but it is not "no
        #      deadlock". Single-operator capture makes this rare, not impossible.
        #   3. SUBTRANSACTION PRESSURE. Every write-bearing SAVEPOINT consumes a
        #      subtransaction XID; a backend caches only 64 in PGPROC, so a ~240-row
        #      batch overflows that cache on EVERY request and other backends fall
        #      back to the pg_subtrans SLRU for visibility checks. RELEASE does not
        #      reclaim the XID. Low impact at current concurrency (and the shorter
        #      transaction reduces overlap), but it is the price of keeping per-row
        #      error isolation. If this ever shows up, the fix is an optimistic
        #      no-savepoint fast path with a per-row retry only on failure.
        for sale in sales:
            content = f"{sale.get('raw_title', '')}|{sale.get('sale_price', '')}|{sale.get('sale_date', '')}"
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:32]

            try:
                cur.execute("SAVEPOINT sw_row")
                cur.execute("""
                    INSERT INTO ebay_sales (
                        raw_title, parsed_title, issue_number, publisher,
                        sale_price, sale_date, condition, graded, grade,
                        listing_url, image_url, ebay_item_id, content_hash,
                        canonical_title, grade_from_title, grading_company,
                        is_facsimile, is_reprint, is_variant, is_signed, is_lot,
                        is_key_issue, key_issue_claim, creators, title_notes,
                        title_year
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ebay_item_id) DO NOTHING
                """, (
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
                    sale.get('title_year')
                ))

                if cur.rowcount > 0:
                    saved += 1
                    saved_sales.append(sale)
                else:
                    duplicates += 1

                cur.execute("RELEASE SAVEPOINT sw_row")

            except Exception as e:
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

        conn.commit()   # ONE commit for the whole batch

        # Step 2: cover backup — dispatched AFTER the rows are durable and
        # returns immediately; the work happens on a daemon thread. Must come
        # after commit() so the UPDATE in that thread can see the rows.
        backup_images_async(saved_sales)

        return jsonify({
            'success': True,
            'saved': saved,
            'duplicates': duplicates,
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
