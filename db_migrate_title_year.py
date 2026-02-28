"""
Migration: Add title_year column to ebay_sales and backfill from raw_title.

Usage:
    python db_migrate_title_year.py <DATABASE_URL>
    python db_migrate_title_year.py                  # falls back to DATABASE_URL env var

This will:
1. Add title_year INTEGER column to ebay_sales (if not exists)
2. Extract year from raw_title using server-side SQL (fast, no round trips)
3. Report stats on how many rows got a year
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ Usage: python db_migrate_title_year.py <DATABASE_URL>")
    print("   Or set DATABASE_URL environment variable")
    exit(1)


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

    # Step 2: Backfill using server-side SQL — single UPDATE, no round trips
    # Priority 1: year in parens like (1991) — most reliable
    # Priority 2: standalone 4-digit year 1930-2029
    print("Backfilling title_year from raw_title (server-side SQL)...")
    cur.execute("""
        UPDATE ebay_sales
        SET title_year = COALESCE(
            -- Priority 1: year in parentheses like (1991)
            CASE
                WHEN raw_title ~ '\\(\\d{4}\\)'
                THEN (
                    SELECT m[1]::int FROM regexp_matches(raw_title, '\\((\\d{4})\\)') AS r(m)
                    WHERE m[1]::int BETWEEN 1930 AND 2029
                    LIMIT 1
                )
            END,
            -- Priority 2: standalone 4-digit year (word boundary)
            CASE
                WHEN raw_title ~ '\\m(19[3-9]\\d|20[0-2]\\d)\\M'
                THEN (
                    SELECT m[1]::int FROM regexp_matches(raw_title, '\\m(19[3-9]\\d|20[0-2]\\d)\\M', 'g') AS r(m)
                    WHERE m[1]::int BETWEEN 1930 AND 2029
                    LIMIT 1
                )
            END
        )
        WHERE raw_title IS NOT NULL
    """)
    updated = cur.rowcount
    conn.commit()
    print(f"✅ Processed {updated} rows")

    # Step 3: Stats
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
