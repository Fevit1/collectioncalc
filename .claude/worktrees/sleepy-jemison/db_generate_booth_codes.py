"""
Generate beta codes for Oakland Comic Con booth (May 9-10, 2026).

Creates:
  - 1 universal booth code: OAKLAND2026 (200 uses, expires June 1 2026)
    → Print this on flyers, banners, and signs at the booth
  - 50 single-use backup codes (BETA-XXXXXX format, expire June 1 2026)
    → Optional: hand out individually if needed

Run in Render shell:
    python db_generate_booth_codes.py
"""

import os
import secrets
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

EXPIRES_AT = datetime(2026, 6, 1)  # expires after Oakland weekend buffer

print("Generating Oakland Comic Con booth codes...\n")

# ── 1. Universal booth code ──────────────────────────────────────────────────
BOOTH_CODE = "OAKLAND2026"
cur.execute("SELECT code FROM beta_codes WHERE code = %s", (BOOTH_CODE,))
if cur.fetchone():
    print(f"  ✓ {BOOTH_CODE} already exists (skipping)")
else:
    cur.execute("""
        INSERT INTO beta_codes (code, created_by, uses_allowed, uses_remaining, expires_at, note)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (BOOTH_CODE, 1, 200, 200, EXPIRES_AT, 'Oakland Comic Con May 2026 — universal booth code'))
    print(f"  + Created universal code: {BOOTH_CODE} (200 uses, expires June 1 2026)")

# ── 2. Single-use backup codes ───────────────────────────────────────────────
print("\n  Generating 50 single-use backup codes...")
backup_codes = []
for i in range(50):
    code = f"OAK-{secrets.token_hex(3).upper()}"
    cur.execute("""
        INSERT INTO beta_codes (code, created_by, uses_allowed, uses_remaining, expires_at, note)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING code
    """, (code, 1, 1, 1, EXPIRES_AT, f'Oakland Comic Con May 2026 — single use #{i+1}'))
    backup_codes.append(cur.fetchone()['code'])

conn.commit()

print(f"  + Created 50 single-use backup codes\n")

# ── Summary ───────────────────────────────────────────────────────────────────
print("=" * 50)
print("OAKLAND COMIC CON BETA CODES")
print("=" * 50)
print(f"\n🎪 UNIVERSAL BOOTH CODE (put on flyers/signs):")
print(f"   {BOOTH_CODE}")
print(f"   200 uses · expires June 1, 2026\n")
print(f"📋 SINGLE-USE BACKUP CODES:")
for code in backup_codes:
    print(f"   {code}")

print(f"\n✅ Done! Push OAKLAND2026 to your flyers and booth signage.")
print(f"   Verify codes in DBeaver: SELECT * FROM beta_codes WHERE note LIKE '%Oakland%';")

cur.close()
conn.close()
