"""
Database Migration: Backfill year for existing comics in collections
Run this on Render shell: python db_migrate_backfill_years.py
"""

import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

def migrate():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        return

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Known publication years for comics missing year data
    # Format: (title, issue, year)
    known_years = [
        ('Iron Man', '198', 1985),
        ('Iron Man', '200', 1985),
        ('The Invincible Iron Man', '110', 1978),
        ('The Invaders', '13', 1977),
    ]

    updated = 0
    for title, issue, year in known_years:
        try:
            cur.execute("""
                UPDATE collections
                SET year = %s
                WHERE title = %s AND issue = %s AND year IS NULL
            """, (year, title, issue))
            rows = cur.rowcount
            if rows > 0:
                print(f"  Updated: {title} #{issue} -> {year} ({rows} row(s))")
                updated += rows
            else:
                print(f"  Skipped: {title} #{issue} (already has year or not found)")
        except Exception as e:
            print(f"  ERROR on {title} #{issue}: {e}")

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nDone! Updated {updated} records.")

if __name__ == '__main__':
    migrate()
