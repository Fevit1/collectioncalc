"""
Migration: Create sighting_reports + blocked_reporters tables for Report to Owner feature.
Run once against your production database.

Usage:
    python db_migrate_sightings.py
    # or with explicit DATABASE_URL:
    DATABASE_URL=postgres://... python db_migrate_sightings.py
"""

import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is required.")
    print("Usage: DATABASE_URL=postgres://... python db_migrate_sightings.py")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# --- sighting_reports ---
print("Creating sighting_reports table...")
cur.execute("""
    CREATE TABLE IF NOT EXISTS sighting_reports (
        id SERIAL PRIMARY KEY,
        serial_number VARCHAR(20) NOT NULL REFERENCES comic_registry(serial_number),
        listing_url TEXT NOT NULL,
        reporter_email VARCHAR(255),
        message TEXT,
        reporter_ip VARCHAR(45),
        created_at TIMESTAMP DEFAULT NOW(),
        owner_notified BOOLEAN DEFAULT FALSE,
        owner_response VARCHAR(50)  -- 'confirmed_mine', 'not_mine', 'investigating', NULL
    );
""")

cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_sighting_serial ON sighting_reports(serial_number);
""")
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_sighting_created ON sighting_reports(created_at);
""")
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_sighting_ip ON sighting_reports(reporter_ip);
""")

# --- blocked_reporters ---
print("Creating blocked_reporters table...")
cur.execute("""
    CREATE TABLE IF NOT EXISTS blocked_reporters (
        id SERIAL PRIMARY KEY,
        ip_address VARCHAR(45) NOT NULL UNIQUE,
        reason VARCHAR(100) DEFAULT 'auto: rate limit exceeded',
        blocked_at TIMESTAMP DEFAULT NOW(),
        expires_at TIMESTAMP,  -- NULL = permanent, or set a date to auto-expire
        blocked_by VARCHAR(50) DEFAULT 'system'  -- 'system' (auto) or 'admin' (manual)
    );
""")
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_blocked_ip ON blocked_reporters(ip_address);
""")

conn.commit()
cur.close()
conn.close()

print("Done! sighting_reports + blocked_reporters tables created successfully.")
