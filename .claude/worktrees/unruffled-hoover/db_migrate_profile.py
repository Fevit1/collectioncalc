"""
Database migration: Add profile/contact columns to users table
Run this in Render shell AFTER deploying the code:
    python db_migrate_profile.py

Adds:
    - display_name: User's chosen name (for booth giveaways, personalization)
    - phone: Phone number (for giveaway contact, future SMS notifications)
    - phone_verified: Whether phone has been verified via SMS
    - marketing_consent: TCPA compliance flag for text/email marketing
"""

import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("Adding profile/contact columns to users table...")

# Add columns one at a time (IF NOT EXISTS via checking information_schema)
columns_to_add = [
    ("display_name", "VARCHAR(100)"),
    ("phone", "VARCHAR(20)"),
    ("phone_verified", "BOOLEAN DEFAULT FALSE"),
    ("marketing_consent", "BOOLEAN DEFAULT FALSE"),
]

for col_name, col_type in columns_to_add:
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = %s
    """, (col_name,))

    if cur.fetchone():
        print(f"  ✓ {col_name} already exists")
    else:
        cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        print(f"  + Added {col_name}")

conn.commit()
cur.close()
conn.close()

print("\n✅ Profile migration complete!")
print("\nNew fields available on users table:")
print("  - display_name (VARCHAR 100) - user's chosen name")
print("  - phone (VARCHAR 20) - phone number")
print("  - phone_verified (BOOLEAN) - SMS verification flag")
print("  - marketing_consent (BOOLEAN) - TCPA opt-in for texts/marketing")
