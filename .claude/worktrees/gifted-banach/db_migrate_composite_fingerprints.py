#!/usr/bin/env python3
"""
Database Migration: Add composite fingerprint column to comic_registry
======================================================================

Adds fingerprint_composite column (JSONB) to store multi-algorithm
fingerprints (pHash + dHash + aHash + wHash) for all 4 photo angles.

Format:
{
    "front":     {"phash": "abc123...", "dhash": "def456...", "ahash": "...", "whash": "..."},
    "spine":     {"phash": "...", "dhash": "...", "ahash": "...", "whash": "..."},
    "back":      {"phash": "...", "dhash": "...", "ahash": "...", "whash": "..."},
    "centerfold": {"phash": "...", "dhash": "...", "ahash": "...", "whash": "..."}
}

Why: Single pHash has only 4-bit separation margin. Composite provides 13-bit
margin per angle and 187-bit margin across all angles. See test results from
Feb 16, 2026 in fingerprint_test.py / fingerprint_composite_test.py.

Run: python db_migrate_composite_fingerprints.py
"""

import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

def migrate():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        return False

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        # Check if column already exists
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'comic_registry'
            AND column_name = 'fingerprint_composite'
        """)

        if cur.fetchone():
            print("Column fingerprint_composite already exists. Skipping.")
        else:
            # Add composite fingerprint column (JSONB for flexible storage)
            cur.execute("""
                ALTER TABLE comic_registry
                ADD COLUMN fingerprint_composite JSONB
            """)
            print("Added fingerprint_composite JSONB column to comic_registry")

        # Update fingerprint_algorithm for existing records to indicate legacy
        cur.execute("""
            UPDATE comic_registry
            SET fingerprint_algorithm = 'phash_legacy'
            WHERE fingerprint_algorithm = 'phash'
            AND fingerprint_composite IS NULL
        """)
        updated = cur.rowcount
        if updated > 0:
            print(f"Marked {updated} existing records as phash_legacy")

        # Add index on the composite column for future querying
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_comic_registry_composite
            ON comic_registry USING GIN (fingerprint_composite)
        """)
        print("Created GIN index on fingerprint_composite")

        conn.commit()
        print("\nMigration complete!")
        print("Existing registrations will continue to work with legacy pHash matching.")
        print("New registrations will use composite fingerprinting (4 algorithms × 4 angles).")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    migrate()
