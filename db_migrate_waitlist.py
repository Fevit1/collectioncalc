"""
Database migration: Create waitlist table for pre-launch signups.
Run: python db_migrate_waitlist.py
Safe to re-run — checks for existing table before creating.
"""
import os
import psycopg2

def migrate():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        return

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    # Check if table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'waitlist'
        )
    """)
    table_exists = cur.fetchone()[0]

    if not table_exists:
        cur.execute("""
            CREATE TABLE waitlist (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                interests TEXT[] DEFAULT '{}',
                verified BOOLEAN DEFAULT FALSE,
                verification_token TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                verified_at TIMESTAMPTZ,
                ip_address TEXT
            )
        """)
        print("  CREATED: waitlist table")

        # Index on verification token for fast lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_waitlist_verification_token
            ON waitlist(verification_token) WHERE verification_token IS NOT NULL
        """)
        print("  ADDED: index on waitlist.verification_token")

        # Index on email for duplicate checks
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_waitlist_email
            ON waitlist(email)
        """)
        print("  ADDED: index on waitlist.email")
    else:
        print("  EXISTS: waitlist table (no changes needed)")

    # Add invited tracking columns (safe to re-run)
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'waitlist' AND column_name = 'invited'
    """)
    if not cur.fetchone():
        cur.execute("ALTER TABLE waitlist ADD COLUMN invited BOOLEAN DEFAULT FALSE")
        cur.execute("ALTER TABLE waitlist ADD COLUMN invited_at TIMESTAMPTZ")
        print("  ADDED: invited, invited_at columns to waitlist")
    else:
        print("  EXISTS: invited columns (no changes needed)")

    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete!")

if __name__ == '__main__':
    migrate()
