"""
Database migration script to add authentication tables.
Run this once to set up users, collections, and password_resets tables.

Usage:
    python db_migrate_auth.py

Tables created:
    - users: User accounts with email/password
    - collections: Saved comics per user
    - password_resets: Password reset tokens
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """Get database connection from environment."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)

def run_migration():
    """Create auth-related tables."""
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # ============================================
        # USERS TABLE
        # ============================================
        print("Creating users table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email_verified BOOLEAN DEFAULT FALSE,
                email_verification_token TEXT,
                email_verification_expires TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                last_login TIMESTAMP,
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Index for email lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """)
        
        # Index for verification token lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_verification_token 
            ON users(email_verification_token) 
            WHERE email_verification_token IS NOT NULL;
        """)
        
        print("✅ users table created")
        
        # ============================================
        # COLLECTIONS TABLE
        # ============================================
        print("Creating collections table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                comic_data JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Index for user's collection lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_collections_user_id ON collections(user_id);
        """)
        
        # Index for searching within comic_data (title, issue)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_collections_comic_title 
            ON collections((comic_data->>'title'));
        """)
        
        print("✅ collections table created")
        
        # ============================================
        # PASSWORD RESETS TABLE
        # ============================================
        print("Creating password_resets table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS password_resets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token TEXT NOT NULL UNIQUE,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Index for token lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_password_resets_token 
            ON password_resets(token) 
            WHERE used = FALSE;
        """)
        
        # Index to clean up old tokens
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_password_resets_expires 
            ON password_resets(expires_at);
        """)
        
        print("✅ password_resets table created")
        
        # ============================================
        # COMMIT
        # ============================================
        conn.commit()
        print("\n🎉 Migration complete! All auth tables created.")
        
        # Show table info
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'collections', 'password_resets')
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        print(f"\nTables in database: {[t['table_name'] for t in tables]}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    run_migration()
