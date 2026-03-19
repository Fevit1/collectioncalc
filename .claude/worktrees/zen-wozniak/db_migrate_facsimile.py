"""
Database Migration: Add facsimile detection
Run this on Render shell: python db_migrate_facsimile.py
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
    
    migrations = [
        # Add is_facsimile to market_sales
        ("ALTER TABLE market_sales ADD COLUMN IF NOT EXISTS is_facsimile BOOLEAN DEFAULT FALSE",
         "Added is_facsimile to market_sales"),
        
        # Add is_facsimile to collections
        ("ALTER TABLE collections ADD COLUMN IF NOT EXISTS is_facsimile BOOLEAN DEFAULT FALSE",
         "Added is_facsimile to collections"),
    ]
    
    for sql, description in migrations:
        try:
            cur.execute(sql)
            print(f"✅ {description}")
        except Exception as e:
            print(f"⚠️ {description}: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    print("\n✅ Facsimile migration complete!")

if __name__ == "__main__":
    migrate()
