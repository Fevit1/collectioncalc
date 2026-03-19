"""
Batch normalize all ebay_sales titles.
Reads raw_title, runs through title_normalizer, updates structured columns.

Usage:
    DATABASE_URL=postgres://... python normalize_batch.py
    python normalize_batch.py --db "postgres://..."
    python normalize_batch.py --dry-run  (preview only, no DB writes)

Safe to re-run: overwrites normalized columns but never touches raw_title.
"""

import os
import sys
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
from title_normalizer import normalize_title


def run_batch(database_url, dry_run=False, limit=None):
    """Process all ebay_sales rows and update normalized columns."""

    conn = psycopg2.connect(database_url)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Count total
    cur.execute("SELECT COUNT(*) as cnt FROM ebay_sales")
    total = cur.fetchone()['cnt']
    print(f"\nTotal ebay_sales rows: {total:,}")

    # Fetch all rows (just id and raw_title to minimize memory)
    query = "SELECT id, raw_title FROM ebay_sales ORDER BY id"
    if limit:
        query += f" LIMIT {limit}"
    cur.execute(query)
    rows = cur.fetchall()

    print(f"Processing {len(rows):,} rows{'  (DRY RUN)' if dry_run else ''}...\n")

    # Stats
    stats = {
        'processed': 0,
        'updated': 0,
        'skipped_no_title': 0,
        'has_grade': 0,
        'has_issue': 0,
        'signed': 0,
        'variant': 0,
        'lot': 0,
        'facsimile': 0,
        'reprint': 0,
        'key_issue': 0,
        'has_creators': 0,
        'errors': 0,
    }

    # Batch update for efficiency
    update_sql = """
        UPDATE ebay_sales SET
            canonical_title = %s,
            issue_number = COALESCE(%s, issue_number),
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
            title_notes = %s
        WHERE id = %s
    """

    batch_params = []
    BATCH_SIZE = 500

    for i, row in enumerate(rows):
        raw = row['raw_title']
        row_id = row['id']

        if not raw:
            stats['skipped_no_title'] += 1
            continue

        try:
            result = normalize_title(raw)

            # Collect stats
            stats['processed'] += 1
            if result['grade_from_title']:  stats['has_grade'] += 1
            if result['issue_number']:      stats['has_issue'] += 1
            if result['is_signed']:         stats['signed'] += 1
            if result['is_variant']:        stats['variant'] += 1
            if result['is_lot']:            stats['lot'] += 1
            if result['is_facsimile']:      stats['facsimile'] += 1
            if result['is_reprint']:        stats['reprint'] += 1
            if result['is_key_issue']:      stats['key_issue'] += 1
            if result['creators']:          stats['has_creators'] += 1

            if not dry_run:
                batch_params.append((
                    result['canonical_title'],
                    result['issue_number'],
                    result['grade_from_title'],
                    result['grading_company'],
                    result['is_facsimile'],
                    result['is_reprint'],
                    result['is_variant'],
                    result['is_signed'],
                    result['is_lot'],
                    result['is_key_issue'],
                    result['key_issue_claim'],
                    result['creators'],
                    result['title_notes'],
                    row_id
                ))

                # Execute batch
                if len(batch_params) >= BATCH_SIZE:
                    cur.executemany(update_sql, batch_params)
                    conn.commit()
                    stats['updated'] += len(batch_params)
                    batch_params = []

            # Progress
            if (i + 1) % 2000 == 0:
                print(f"  ... {i + 1:,} / {len(rows):,} processed")

        except Exception as e:
            stats['errors'] += 1
            if stats['errors'] <= 5:
                print(f"  ERROR on row {row_id}: {e}")
                print(f"    raw_title: {raw[:80]}")

    # Flush remaining batch
    if batch_params and not dry_run:
        cur.executemany(update_sql, batch_params)
        conn.commit()
        stats['updated'] += len(batch_params)

    cur.close()
    conn.close()

    # Print results
    print(f"\n{'=' * 60}")
    print(f"NORMALIZATION COMPLETE{'  (DRY RUN)' if dry_run else ''}")
    print(f"{'=' * 60}")
    print(f"  Processed:    {stats['processed']:,}")
    print(f"  Updated:      {stats['updated']:,}")
    print(f"  Skipped:      {stats['skipped_no_title']:,} (no raw_title)")
    print(f"  Errors:       {stats['errors']:,}")
    print(f"")
    print(f"  Has grade:    {stats['has_grade']:,}  ({pct(stats['has_grade'], stats['processed'])})")
    print(f"  Has issue:    {stats['has_issue']:,}  ({pct(stats['has_issue'], stats['processed'])})")
    print(f"  Signed:       {stats['signed']:,}  ({pct(stats['signed'], stats['processed'])})")
    print(f"  Variant:      {stats['variant']:,}  ({pct(stats['variant'], stats['processed'])})")
    print(f"  Lot:          {stats['lot']:,}  ({pct(stats['lot'], stats['processed'])})")
    print(f"  Facsimile:    {stats['facsimile']:,}  ({pct(stats['facsimile'], stats['processed'])})")
    print(f"  Reprint:      {stats['reprint']:,}  ({pct(stats['reprint'], stats['processed'])})")
    print(f"  Key Issue:    {stats['key_issue']:,}  ({pct(stats['key_issue'], stats['processed'])})")
    print(f"  Has Creators: {stats['has_creators']:,}  ({pct(stats['has_creators'], stats['processed'])})")

    return stats


def pct(n, total):
    if total == 0:
        return "0%"
    return f"{n / total * 100:.1f}%"


def preview_samples(database_url, count=10):
    """Show a preview of normalization on random samples."""
    conn = psycopg2.connect(database_url)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(f"SELECT id, raw_title FROM ebay_sales ORDER BY RANDOM() LIMIT {count}")
    rows = cur.fetchall()

    print(f"\n{'=' * 100}")
    print(f"PREVIEW: {count} random samples")
    print(f"{'=' * 100}")

    for row in rows:
        result = normalize_title(row['raw_title'])
        print(f"\n  RAW: {row['raw_title']}")
        print(f"  →  title: {result['canonical_title']}")
        print(f"     issue: {result['issue_number']}", end="")
        if result['grade_from_title']:
            print(f"  |  grade: {result['grade_from_title']} ({result['grading_company']})", end="")
        flags = []
        if result['is_signed']:    flags.append('SIGNED')
        if result['is_variant']:   flags.append('VARIANT')
        if result['is_lot']:       flags.append('LOT')
        if result['is_facsimile']: flags.append('FAC')
        if result['is_reprint']:   flags.append('REPRINT')
        if result['is_key_issue']: flags.append('KEY')
        if flags:
            print(f"  |  [{', '.join(flags)}]", end="")
        print()
        if result['key_issue_claim']:
            print(f"     key: {result['key_issue_claim']}")
        if result['creators']:
            print(f"     creators: {result['creators']}")
        if result['title_notes']:
            print(f"     notes: {result['title_notes']}")

    cur.close()
    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Batch normalize ebay_sales titles')
    parser.add_argument('--db', help='DATABASE_URL (or set env var)')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, no DB writes')
    parser.add_argument('--preview', type=int, default=0, help='Show N random samples first')
    parser.add_argument('--limit', type=int, default=None, help='Process only N rows')
    args = parser.parse_args()

    db_url = args.db or os.environ.get('DATABASE_URL')
    if not db_url:
        print("ERROR: Provide DATABASE_URL via --db flag or environment variable")
        sys.exit(1)

    if args.preview:
        preview_samples(db_url, args.preview)
        print()

    if args.dry_run:
        run_batch(db_url, dry_run=True, limit=args.limit)
    elif args.preview and not args.limit:
        resp = input("\nRun full batch update? [y/N] ")
        if resp.lower() == 'y':
            run_batch(db_url, limit=args.limit)
        else:
            print("Aborted.")
    else:
        run_batch(db_url, limit=args.limit)
