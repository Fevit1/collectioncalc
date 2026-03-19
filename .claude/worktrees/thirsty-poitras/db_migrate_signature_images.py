"""
Database migration: Add signature_images table for multiple reference images per creator.

Run this on Render shell:
    python db_migrate_signature_images.py
"""

import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

def run_migration():
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return False
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        # Create signature_images table
        print("Creating signature_images table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS signature_images (
                id SERIAL PRIMARY KEY,
                creator_id INTEGER REFERENCES creator_signatures(id) ON DELETE CASCADE,
                image_url TEXT NOT NULL,
                era VARCHAR(100),
                notes TEXT,
                source VARCHAR(255),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        print("✅ signature_images table created")
        
        # Create index for fast lookups by creator
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_signature_images_creator 
            ON signature_images(creator_id)
        """)
        print("✅ Index on creator_id created")
        
        # Migrate existing reference_image_url to new table
        print("Migrating existing reference images...")
        cur.execute("""
            INSERT INTO signature_images (creator_id, image_url, notes, created_at)
            SELECT id, reference_image_url, 'Migrated from original reference', NOW()
            FROM creator_signatures
            WHERE reference_image_url IS NOT NULL
            AND reference_image_url != ''
            AND NOT EXISTS (
                SELECT 1 FROM signature_images 
                WHERE signature_images.creator_id = creator_signatures.id
            )
        """)
        migrated = cur.rowcount
        print(f"✅ Migrated {migrated} existing images")
        
        conn.commit()
        print("\n✅ Migration complete!")
        
        # Show stats
        cur.execute("SELECT COUNT(*) FROM signature_images")
        total = cur.fetchone()[0]
        print(f"\n📊 Total signature images: {total}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        return False
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    run_migration()
