"""
Migration: Create match_reports table for Slab Guard marketplace monitoring.
Run: python db_migrate_match_reports.py
"""
import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

def migrate():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("Creating match_reports table...")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS match_reports (
            id SERIAL PRIMARY KEY,
            registry_id INTEGER REFERENCES comic_registry(id) ON DELETE CASCADE,
            reporter_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            marketplace VARCHAR(50) DEFAULT 'ebay',
            listing_url TEXT NOT NULL,
            listing_item_id VARCHAR(100),
            listing_image_url TEXT,
            listing_fingerprint VARCHAR(16),
            hamming_distance INTEGER,
            confidence_score DECIMAL(5,2),
            status VARCHAR(20) DEFAULT 'pending',
            reported_at TIMESTAMP DEFAULT NOW(),
            reviewed_at TIMESTAMP,
            reviewer_notes TEXT
        );
    """)

    # Indexes
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_match_reports_registry
        ON match_reports(registry_id);
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_match_reports_reporter
        ON match_reports(reporter_user_id);
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_match_reports_status
        ON match_reports(status);
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_match_reports_listing
        ON match_reports(listing_item_id);
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("match_reports table created successfully!")


if __name__ == '__main__':
    migrate()
