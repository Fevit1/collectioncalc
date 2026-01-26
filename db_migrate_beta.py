"""
Database Migration: Beta Gate, User Approval, and Request Logging

Run this once to add:
1. is_approved and is_admin columns to users table
2. beta_codes table for access control
3. request_logs table for debugging/analytics
4. api_usage table for tracking Anthropic costs

Usage:
    python db_migrate_beta.py
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
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("=" * 60)
    print("CollectionCalc Database Migration: Beta System")
    print("=" * 60)
    
    try:
        # ============================================
        # 1. Add columns to users table
        # ============================================
        print("\n1. Adding is_approved and is_admin columns to users...")
        
        # Check if columns exist
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'is_approved'
        """)
        
        if not cur.fetchone():
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN is_approved BOOLEAN DEFAULT FALSE,
                ADD COLUMN is_admin BOOLEAN DEFAULT FALSE,
                ADD COLUMN approved_at TIMESTAMPTZ,
                ADD COLUMN approved_by INTEGER REFERENCES users(id),
                ADD COLUMN beta_code_used TEXT
            """)
            print("   ✅ Added columns to users table")
        else:
            print("   ⏭️  Columns already exist, skipping")
        
        # ============================================
        # 2. Create beta_codes table
        # ============================================
        print("\n2. Creating beta_codes table...")
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS beta_codes (
                id SERIAL PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                created_by INTEGER REFERENCES users(id),
                uses_allowed INTEGER DEFAULT 1,
                uses_remaining INTEGER DEFAULT 1,
                expires_at TIMESTAMPTZ,
                note TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        print("   ✅ Created beta_codes table")
        
        # Create index for fast code lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_beta_codes_code 
            ON beta_codes(code) WHERE is_active = TRUE
        """)
        print("   ✅ Created index on beta_codes")
        
        # ============================================
        # 3. Create request_logs table
        # ============================================
        print("\n3. Creating request_logs table...")
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS request_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                status_code INTEGER,
                response_time_ms INTEGER,
                error_message TEXT,
                request_size_bytes INTEGER,
                response_size_bytes INTEGER,
                user_agent TEXT,
                ip_address TEXT,
                device_type TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                request_data JSONB,
                response_summary TEXT
            )
        """)
        print("   ✅ Created request_logs table")
        
        # Create indexes for common queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_logs_user 
            ON request_logs(user_id, created_at DESC)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_logs_endpoint 
            ON request_logs(endpoint, created_at DESC)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_logs_errors 
            ON request_logs(created_at DESC) 
            WHERE error_message IS NOT NULL
        """)
        print("   ✅ Created indexes on request_logs")
        
        # ============================================
        # 4. Create api_usage table (Anthropic costs)
        # ============================================
        print("\n4. Creating api_usage table...")
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                endpoint TEXT NOT NULL,
                model TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                estimated_cost_usd NUMERIC(10, 6),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        print("   ✅ Created api_usage table")
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_usage_user 
            ON api_usage(user_id, created_at DESC)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_usage_date 
            ON api_usage(created_at DESC)
        """)
        print("   ✅ Created indexes on api_usage")
        
        # ============================================
        # 5. Create admin_nlq_history table
        # ============================================
        print("\n5. Creating admin_nlq_history table...")
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin_nlq_history (
                id SERIAL PRIMARY KEY,
                admin_id INTEGER REFERENCES users(id),
                natural_query TEXT NOT NULL,
                generated_sql TEXT,
                result_count INTEGER,
                execution_time_ms INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        print("   ✅ Created admin_nlq_history table")
        
        # ============================================
        # 6. Insert default beta codes
        # ============================================
        print("\n6. Creating initial beta codes...")
        
        # Check if codes already exist
        cur.execute("SELECT COUNT(*) as count FROM beta_codes")
        if cur.fetchone()['count'] == 0:
            initial_codes = [
                ('BETA-MIKE', 'Mike (owner)'),
                ('BETA-001', 'Friend #1'),
                ('BETA-002', 'Friend #2'),
                ('BETA-003', 'Friend #3'),
                ('BETA-004', 'Friend #4'),
                ('BETA-005', 'Friend #5'),
            ]
            
            for code, note in initial_codes:
                cur.execute("""
                    INSERT INTO beta_codes (code, note, uses_allowed, uses_remaining)
                    VALUES (%s, %s, 1, 1)
                """, (code, note))
            
            print(f"   ✅ Created {len(initial_codes)} initial beta codes")
        else:
            print("   ⏭️  Beta codes already exist, skipping")
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        
        # Print summary
        print("\n📋 Summary:")
        print("   - users table: added is_approved, is_admin, approved_at, approved_by, beta_code_used")
        print("   - beta_codes table: created")
        print("   - request_logs table: created")
        print("   - api_usage table: created")
        print("   - admin_nlq_history table: created")
        
        print("\n🔑 Beta codes created:")
        cur.execute("SELECT code, note FROM beta_codes ORDER BY code")
        for row in cur.fetchall():
            print(f"   {row['code']} - {row['note']}")
        
        print("\n⚠️  Next steps:")
        print("   1. Set yourself as admin: UPDATE users SET is_admin = TRUE, is_approved = TRUE WHERE email = 'your@email.com';")
        print("   2. Deploy the updated auth.py and wsgi.py")
        print("   3. Deploy the new landing page")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
