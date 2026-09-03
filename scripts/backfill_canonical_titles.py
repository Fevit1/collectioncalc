#!/usr/bin/env python3
"""Re-derive canonical_title from the retained raw_title.

WHY THIS SHIPS WITH ITS CODE CHANGE AND NEVER SEPARATELY
--------------------------------------------------------
The normalizer fix is forward-only. Ship it alone and new rows get the correct
canonical while ~274,000 existing rows keep the old one, so every affected book
splits into TWO pools instead of sitting in one wrong pool. That is strictly
worse than today. Code fix and backfill are one unit, always.

WHAT MAKES THIS SAFE - AND WHAT IT DOES NOT CHECK
-------------------------------------------------
canonical_title is a pure function of raw_title, and raw_title is retained on
100% of rows and is never modified here. That is the safety property.

The FLAT-BASELINE property ("stored canonical == what the current code produces,
so every row this run changes is attributable to the code change alone") is NOT
a property of this script. It is a property of the corpus at a moment in time,
and this script does not verify it - it only reports the total it would rewrite.

  - It was true on 2026-08-17: the then-current normalizer reproduced the stored
    canonical on 274,344 of 274,344 rows.
  - It was FALSE by 2026-09-02: the corpus was 308,152 rows and 720 of them
    (719 ebay_sales + 1 market_sales, all Werewolf By Night) differed from HEAD,
    because the 2026-08-17 guard commit shipped without this backfill ever being
    run in production. Captures after 08-17 stored the HEAD output; captures
    before it kept the old one. This script's docstring asserted "the baseline
    is flat" throughout those two weeks, and nothing checked it.

So on ANY future run: re-verify flatness first (run the corpus differential -
current HEAD vs stored - and account for every non-zero row) rather than
assuming it. A dry-run total that is larger than the code change's own
differential is the tell that an earlier change was never backfilled. That is
not a reason to stop, but it is a reason to know which rows are which before
--execute. A script that asserts a state it does not check is the same defect
class as copy that asserts what the mechanism does not do (L-SW-2026-028).

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
    """Return (rows_seen, [(id, before, after)], Counter(pairs), Counter(source_totals))."""
    cur.execute(
        'SELECT id, raw_title, canonical_title FROM {} '
        'WHERE raw_title IS NOT NULL ORDER BY id'.format(table))
    changes, pairs, seen = [], collections.Counter(), 0
    source_totals = collections.Counter()
    for r in cur.fetchall():
        seen += 1
        # ⚠️ KNOWN DEFECT, NOT FIXED (2026-09-02): these three lines key on the
        # EXACT stored spelling - Counter keys and a raw != - so a CASE split is
        # invisible to the drain report below. When one book ends up stored as
        # both 'Werewolf By Night' (assigned verbatim from known_titles.json) and
        # 'Werewolf by Night' (title-caser output; the canonical-assigning match
        # is still case-sensitive), drain_report() prints two fully-drained
        # sources instead of ONE PARTIALLY-DRAINED BOOK. Nine titles / 1,461 rows
        # already sit in that condition. Do not read a FULL/FULL pair of
        # case-variant sources as "no split". Fix belongs to the
        # case-insensitive-matcher unit, with its own differential.
        source_totals[r['canonical_title']] += 1
        after = normalize_title(r['raw_title']).get('canonical_title')
        if after != r['canonical_title']:
            changes.append((r['id'], r['canonical_title'], after))
            pairs[(r['canonical_title'], after)] += 1
    return seen, changes, pairs, source_totals


def drain_report(pairs, source_totals):
    """For every source canonical being rewritten: how many rows move, how many
    stay, and whether the source is FULLY or PARTIALLY drained.

    ⚠️ A PARTIALLY DRAINED SOURCE IS A SPLIT BY CONSTRUCTION. Half a book's rows
    move to the corrected name and half keep the old one, so the comp pool is
    divided in two — which is the exact failure the ship-together constraint
    exists to prevent, arriving by a different route. It is invisible in a plain
    pair list, because a pair list reports what MOVED and says nothing about what
    was left behind. Found 2026-08-17 only because the operator compared a row
    count against a figure he remembered from another document. That is not a
    process, so the script reports it instead.

    A partial drain is not automatically wrong — the remainder may be genuinely
    different books — but it must be looked at rather than assumed.
    """
    moved = collections.Counter()
    for (before, _after), n in pairs.items():
        moved[before] += n
    rows = []
    for before, n_moved in moved.most_common():
        total = source_totals.get(before, n_moved)
        rows.append((before, n_moved, total - n_moved, total))
    return rows


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
        seen, changes, pairs, source_totals = scan(cur, table)
        grand += len(changes)
        print('=' * 72)
        print('{}: {} rows scanned, {} would change, {} distinct pairs'
              .format(table, seen, len(changes), len(pairs)))
        print('=' * 72)
        for (before, after), n in pairs.most_common(40):
            print('   {:<34} -> {:<34} {}'.format(str(before)[:34], str(after)[:34], n))
        if len(pairs) > 40:
            print('   ... and {} more pairs'.format(len(pairs) - 40))

        drains = drain_report(pairs, source_totals)
        partial = [d for d in drains if d[2] > 0]
        print()
        print('   SOURCE DRAIN — what moves, what is LEFT BEHIND:')
        print('   {:<34} {:>7} {:>7} {:>7}  {}'.format('source canonical', 'moving', 'staying', 'total', 'drain'))
        for before, mv, stay, total in drains[:25]:
            print('   {:<34} {:>7} {:>7} {:>7}  {}'.format(
                str(before)[:34], mv, stay, total, 'FULL' if stay == 0 else 'PARTIAL <-- LOOK'))
        if len(drains) > 25:
            print('   ... and {} more sources'.format(len(drains) - 25))
        if partial:
            print()
            print('   ⚠ {} SOURCE(S) ONLY PARTIALLY DRAINED. Each one splits a pool: some rows'
                  .format(len(partial)))
            print('     take the corrected name and the rest keep the old one. Confirm the rows left')
            print('     behind are genuinely a DIFFERENT book before running --execute.')
        else:
            print('   all sources fully drained - no pool is split by this run.')

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
