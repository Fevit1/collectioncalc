"""
Migration: Add title_year column to ebay_sales and backfill from raw_title.

Usage:
    python db_migrate_title_year.py

This will:
1. Add title_year INTEGER column to ebay_sales (if not exists)
2. Re-extract year from raw_title for all existing rows
3. Report stats on how many rows got a year
"""

import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    exit(1)


def extract_year(raw_title):
    """Extract publication year from a raw eBay title."""
    if not raw_title:
        return None
    # Pattern 1: (1991) in parens — most reliable
    m = re.search(r'\((\d{4})\)', raw_title)
    if m:
        y = int(m.group(1))
        if 1930 <= y <= 2029:
            return y
    # Pattern 2: standalone 4-digit year
    matches = re.findall(r'\b(19[3-9]\d|20[0-2]\d)\b', raw_title)
    for ym in matches:
        y = int(ym)
        if 1930 <= y <= 2029:
            return y
    return None


def migrate():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()

    # Step 1: Add column if not exists
    print("Adding title_year column...")
    cur.execute("""
        ALTER TABLE ebay_sales
        ADD COLUMN IF NOT EXISTS title_year INTEGER
    """)
    conn.commit()
    print("✅ Column added (or already exists)")

    # Step 2: Get all rows with raw_title
    print("Fetching all rows for year extraction...")
    cur.execute("SELECT id, raw_title FROM ebay_sales WHERE raw_title IS NOT NULL")
    rows = cur.fetchall()
    print(f"  Total rows: {len(rows)}")

    # Step 3: Extract and update in batches
    updated = 0
    batch = []
    batch_size = 500

    for row in rows:
        year = extract_year(row['raw_title'])
        if year:
            batch.append((year, row['id']))
            if len(batch) >= batch_size:
                cur.executemany("UPDATE ebay_sales SET title_year = %s WHERE id = %s", batch)
                conn.commit()
                updated += len(batch)
                batch = []

    # Final batch
    if batch:
        cur.executemany("UPDATE ebay_sales SET title_year = %s WHERE id = %s", batch)
        conn.commit()
        updated += len(batch)

    print(f"✅ Updated {updated}/{len(rows)} rows with title_year")

    # Step 4: Stats
    cur.execute("SELECT COUNT(*) as total FROM ebay_sales")
    total = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) as with_year FROM ebay_sales WHERE title_year IS NOT NULL")
    with_year = cur.fetchone()['with_year']
    cur.execute("""
        SELECT title_year, COUNT(*) as count
        FROM ebay_sales
        WHERE title_year IS NOT NULL
        GROUP BY title_year
        ORDER BY count DESC
        LIMIT 15
    """)
    year_dist = cur.fetchall()

    print(f"\nStats:")
    print(f"  Total sales:     {total}")
    print(f"  With year:       {with_year} ({with_year/total*100:.1f}%)")
    print(f"  Without year:    {total - with_year} ({(total-with_year)/total*100:.1f}%)")
    print(f"\nYear distribution (top 15):")
    for yd in year_dist:
        print(f"  {yd['title_year']}: {yd['count']} sales")

    cur.close()
    conn.close()


if __name__ == '__main__':
    migrate()
