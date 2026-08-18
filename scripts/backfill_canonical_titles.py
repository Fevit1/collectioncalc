#!/usr/bin/env python3
"""Re-derive canonical_title from the retained raw_title.

WHY THIS SHIPS WITH ITS CODE CHANGE AND NEVER SEPARATELY
--------------------------------------------------------
The normalizer fix is forward-only. Ship it alone and new rows get the correct
canonical while ~274,000 existing rows keep the old one, so every affected book
splits into TWO pools instead of sitting in one wrong pool. That is strictly
worse than today. Code fix and backfill are one unit, always.

WHAT MAKES THIS SAFE
--------------------
canonical_title is a pure function of raw_title. Verified 2026-08-17: re-running
the UNCHANGED normalizer over stored raw_title reproduced the stored canonical on
274,344 of 274,344 rows - zero differences. The baseline is flat, so every row
this changes is attributable to the code change alone, and a second run is a
no-op. raw_title is retained on 100% of rows and is never modified here.

IDEMPOTENT: re-running after a successful pass reports 0 changes. That is the
verification, not a side effect.
RESUMABLE: rows are processed in id order and committed per batch. An interrupted
run leaves completed batches committed; re-running simply finds nothing to do for
them.
CONCURRENCY-SAFE: each UPDATE is conditional on the row still holding the value we
read, so rows written by live capture mid-run are never clobbered.

USAGE (Render shell - needs DATABASE_URL, which local .env does not have):
    python scripts/backfill_canonical_titles.py              # DRY RUN, writes nothing
    python scripts/backfill_canonical_titles.py --execute    # writes
"""
import argparse
import collections
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)          # resolve the repo root from __file__, never from cwd

try:
    sys.stdout.reconfigure(encoding='utf-8')   # L-2026-015
except Exception:
    pass

import psycopg2
from psycopg2.extras import RealDictCursor
from title_normalizer import normalize_title

TABLES = ('ebay_sales', 'market_sales')
BATCH = 500


def scan(cur, table):
    """Return (rows_seen, [(id, before, after)], Counter(pairs))."""
    cur.execute(
        'SELECT id, raw_title, canonical_title FROM {} '
        'WHERE raw_title IS NOT NULL ORDER BY id'.format(table))
    changes, pairs, seen = [], collections.Counter(), 0
    for r in cur.fetchall():
        seen += 1
        after = normalize_title(r['raw_title']).get('canonical_title')
        if after != r['canonical_title']:
            changes.append((r['id'], r['canonical_title'], after))
            pairs[(r['canonical_title'], after)] += 1
    return seen, changes, pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--execute', action='store_true',
                    help='write the changes; omitted means dry run')
    ap.add_argument('--table', choices=TABLES, help='limit to one table')
    args = ap.parse_args()

    dsn = os.environ.get('DATABASE_URL')
    if not dsn:
        sys.exit('DATABASE_URL is not set. This runs in the Render shell; the local '
                 '.env carries only DATABASE_URL_RO, which cannot write.')

    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT current_user')                      # L-2026-025: name the principal
    print('principal: {}'.format(cur.fetchone()['current_user']))
    print('MODE     : {}'.format('EXECUTE (writes)' if args.execute else 'DRY RUN (writes nothing)'))
    print()

    grand = 0
    for table in ([args.table] if args.table else TABLES):
        seen, changes, pairs = scan(cur, table)
        grand += len(changes)
        print('=' * 72)
        print('{}: {} rows scanned, {} would change, {} distinct pairs'
              .format(table, seen, len(changes), len(pairs)))
        print('=' * 72)
        for (before, after), n in pairs.most_common(40):
            print('   {:<34} -> {:<34} {}'.format(str(before)[:34], str(after)[:34], n))
        if len(pairs) > 40:
            print('   ... and {} more pairs'.format(len(pairs) - 40))

        if not changes:
            print('   nothing to do.')
            continue

        print()
        print('   ROLLBACK for this table, if it is ever needed:')
        print('   re-run this script against the commit BEFORE the normalizer change.')
        print('   canonical_title is derived, so the prior state is reproducible from')
        print('   raw_title - nothing here is lost, and raw_title is never written.')

        if not args.execute:
            print('\n   DRY RUN - no rows written. Re-run with --execute to apply.')
            continue

        done = 0
        for i in range(0, len(changes), BATCH):
            for rid, before, after in changes[i:i + BATCH]:
                cur.execute(
                    'UPDATE {} SET canonical_title = %s '
                    'WHERE id = %s AND canonical_title IS NOT DISTINCT FROM %s'.format(table),
                    (after, rid, before))
                done += cur.rowcount
            conn.commit()
            print('   committed {}/{}'.format(min(i + BATCH, len(changes)), len(changes)))
        print('   {} rows updated ({} skipped - changed by live capture mid-run)'
              .format(done, len(changes) - done))

    conn.close()
    print()
    print('TOTAL rows {}: {}'.format('updated' if args.execute else 'that would change', grand))
    if args.execute:
        print('VERIFY: re-run WITHOUT --execute. A correct run reports 0 would change.')


if __name__ == '__main__':
    main()
