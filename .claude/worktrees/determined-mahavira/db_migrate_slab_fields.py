"""
Database Migration: Add slab detection fields to collections and comic_registry tables.

Run: python db_migrate_slab_fields.py

Adds to collections:
  - is_slabbed (boolean)
  - slab_cert_number (varchar)
  - slab_company (varchar)
  - slab_grade (varchar)
  - slab_label_type (varchar)

Adds to comic_registry:
  - slab_cert_number (varchar) — alternate unique identifier for slabbed comics
  - slab_company (varchar)
  - slab_label_type (varchar)
"""
import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

migrations = [
    # Collections table — store extraction data
    ("collections", "is_slabbed", "ALTER TABLE collections ADD COLUMN is_slabbed BOOLEAN DEFAULT FALSE"),
    ("collections", "slab_cert_number", "ALTER TABLE collections ADD COLUMN slab_cert_number VARCHAR(30)"),
    ("collections", "slab_company", "ALTER TABLE collections ADD COLUMN slab_company VARCHAR(10)"),
    ("collections", "slab_grade", "ALTER TABLE collections ADD COLUMN slab_grade VARCHAR(10)"),
    ("collections", "slab_label_type", "ALTER TABLE collections ADD COLUMN slab_label_type VARCHAR(30)"),

    # Comic registry table — for Slab Guard identification
    ("comic_registry", "slab_cert_number", "ALTER TABLE comic_registry ADD COLUMN slab_cert_number VARCHAR(30)"),
    ("comic_registry", "slab_company", "ALTER TABLE comic_registry ADD COLUMN slab_company VARCHAR(10)"),
    ("comic_registry", "slab_label_type", "ALTER TABLE comic_registry ADD COLUMN slab_label_type VARCHAR(30)"),
]

for table, column, sql in migrations:
    try:
        # Check if column already exists
        cur.execute("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        """, (table, column))

        if cur.fetchone():
            print(f"  SKIP: {table}.{column} already exists")
        else:
            cur.execute(sql)
            print(f"  ADDED: {table}.{column}")
    except Exception as e:
        print(f"  ERROR on {table}.{column}: {e}")
        conn.rollback()

# Add index on slab_cert_number for lookups
try:
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_registry_slab_cert
        ON comic_registry (slab_cert_number)
        WHERE slab_cert_number IS NOT NULL
    """)
    print("  ADDED: index on comic_registry.slab_cert_number")
except Exception as e:
    print(f"  ERROR on index: {e}")
    conn.rollback()

try:
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_collections_slab_cert
        ON collections (slab_cert_number)
        WHERE slab_cert_number IS NOT NULL
    """)
    print("  ADDED: index on collections.slab_cert_number")
except Exception as e:
    print(f"  ERROR on index: {e}")
    conn.rollback()

conn.commit()
cur.close()
conn.close()
print("\nMigration complete!")
