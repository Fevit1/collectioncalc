"""
Run orchestrator v2 migrations against Render PostgreSQL.
Usage (PowerShell):
    python run_migrations.py "postgresql://user:pass@host:5432/dbname"
"""
import sys
import psycopg2

if len(sys.argv) < 2:
    print("Usage: python run_migrations.py <DATABASE_URL>")
    sys.exit(1)

db_url = sys.argv[1]
conn = psycopg2.connect(db_url)
conn.autocommit = True
cur = conn.cursor()

print("=" * 60)
print("MIGRATION 1: add_orchestrator_columns.sql")
print("=" * 60)
with open("migrations/add_orchestrator_columns.sql", "r") as f:
    sql = f.read()
cur.execute(sql)
print("Done!")

print()
print("=" * 60)
print("MIGRATION 2: add_signature_identification_log.sql")
print("=" * 60)
with open("migrations/add_signature_identification_log.sql", "r") as f:
    sql = f.read()
cur.execute(sql)
print("Done!")

print()
print("=" * 60)
print("VALIDATION: migration_validation view")
print("=" * 60)
cur.execute("SELECT creator_name, reference_image_count, count_check FROM migration_validation ORDER BY creator_name")
rows = cur.fetchall()
for row in rows:
    status = "OK" if row[2] == "OK" else "MISMATCH"
    print(f"  {row[0]:30s} | images: {row[1]:3d} | {status}")

mismatches = [r for r in rows if r[2] != "OK"]
if mismatches:
    print(f"\nWARNING: {len(mismatches)} count mismatches found!")
else:
    print(f"\nAll {len(rows)} creators validated OK!")

cur.close()
conn.close()
print("\nMigrations complete. Next: python seed_creator_metadata.py <DATABASE_URL>")
