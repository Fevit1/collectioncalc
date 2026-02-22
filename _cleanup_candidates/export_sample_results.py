"""Export detailed normalization results for review"""

import psycopg2
from psycopg2.extras import RealDictCursor
from title_normalizer import normalize_title
import sys

def export_results(database_url, limit=100, output_file='normalization_results.txt'):
    """Export normalized results to a text file for review"""

    conn = psycopg2.connect(database_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Fetch records - use random sampling for variety
    cursor.execute("""
        SELECT id, raw_title
        FROM ebay_sales
        WHERE raw_title IS NOT NULL AND raw_title != ''
        ORDER BY RANDOM()
        LIMIT %s
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    # Process and write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write(f"NORMALIZATION RESULTS - First {limit} Records\n")
        f.write("=" * 100 + "\n\n")

        for i, row in enumerate(rows, 1):
            result = normalize_title(row['raw_title'])

            f.write(f"\n{'─' * 100}\n")
            f.write(f"[{i}] ID: {row['id']}\n")
            f.write(f"{'─' * 100}\n")
            f.write(f"RAW: {row['raw_title']}\n\n")

            f.write(f"  Canonical Title:  {result['canonical_title']}\n")
            f.write(f"  Issue Number:     {result['issue_number']}\n")

            # Grade info
            if result['grade_from_title']:
                f.write(f"  Grade:            {result['grade_from_title']} ({result['grading_company'] or 'raw'})\n")
            else:
                f.write(f"  Grade:            None\n")

            # Flags
            flags = []
            if result['is_signed']:    flags.append('SIGNED')
            if result['is_variant']:   flags.append('VARIANT')
            if result['is_lot']:       flags.append('LOT')
            if result['is_facsimile']: flags.append('FACSIMILE')
            if result['is_reprint']:   flags.append('REPRINT')
            if result['is_key_issue']: flags.append('KEY')

            if flags:
                f.write(f"  Flags:            {', '.join(flags)}\n")

            # Additional fields
            if result['creators']:
                f.write(f"  Creators:         {result['creators']}\n")

            if result['key_issue_claim']:
                f.write(f"  Key Issue Claim:  {result['key_issue_claim']}\n")

            if result['publisher']:
                f.write(f"  Publisher:        {result['publisher']}\n")

            if result['title_notes']:
                f.write(f"  Notes:            {result['title_notes']}\n")

        # Summary stats
        f.write(f"\n\n{'=' * 100}\n")
        f.write("SUMMARY STATISTICS\n")
        f.write(f"{'=' * 100}\n\n")

        stats = {
            'has_title': 0,
            'has_issue': 0,
            'has_grade': 0,
            'signed': 0,
            'variant': 0,
            'lot': 0,
            'facsimile': 0,
            'reprint': 0,
            'key_issue': 0,
            'has_creators': 0,
        }

        for row in rows:
            result = normalize_title(row['raw_title'])
            if result['canonical_title']: stats['has_title'] += 1
            if result['issue_number']: stats['has_issue'] += 1
            if result['grade_from_title']: stats['has_grade'] += 1
            if result['is_signed']: stats['signed'] += 1
            if result['is_variant']: stats['variant'] += 1
            if result['is_lot']: stats['lot'] += 1
            if result['is_facsimile']: stats['facsimile'] += 1
            if result['is_reprint']: stats['reprint'] += 1
            if result['is_key_issue']: stats['key_issue'] += 1
            if result['creators']: stats['has_creators'] += 1

        total = len(rows)
        f.write(f"  Total Records:     {total}\n")
        f.write(f"  Has Title:         {stats['has_title']} ({stats['has_title']/total*100:.1f}%)\n")
        f.write(f"  Has Issue:         {stats['has_issue']} ({stats['has_issue']/total*100:.1f}%)\n")
        f.write(f"  Has Grade:         {stats['has_grade']} ({stats['has_grade']/total*100:.1f}%)\n")
        f.write(f"  Signed:            {stats['signed']} ({stats['signed']/total*100:.1f}%)\n")
        f.write(f"  Variant:           {stats['variant']} ({stats['variant']/total*100:.1f}%)\n")
        f.write(f"  Lot:               {stats['lot']} ({stats['lot']/total*100:.1f}%)\n")
        f.write(f"  Facsimile:         {stats['facsimile']} ({stats['facsimile']/total*100:.1f}%)\n")
        f.write(f"  Reprint:           {stats['reprint']} ({stats['reprint']/total*100:.1f}%)\n")
        f.write(f"  Key Issue:         {stats['key_issue']} ({stats['key_issue']/total*100:.1f}%)\n")
        f.write(f"  Has Creators:      {stats['has_creators']} ({stats['has_creators']/total*100:.1f}%)\n")

    print(f"✓ Exported {len(rows)} records to {output_file}")

if __name__ == '__main__':
    db_url = sys.argv[1] if len(sys.argv) > 1 else None
    if not db_url:
        print("Usage: python export_sample_results.py <database_url>")
        sys.exit(1)

    export_results(db_url, limit=100, output_file='/sessions/nifty-affectionate-dijkstra/mnt/CC/first_100_normalized.txt')
