import psycopg2

DB_URL = "postgresql://collectioncalc_db_user:iGCXbv2dk3P5aoNvKghOVqE9Q4wgW8ue@dpg-d5knv4koud1c73dt21pg-a.oregon-postgres.render.com/collectioncalc_db"

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# Check current state
cur.execute("SELECT id, ebay_item_id, seller_id, phash FROM slabguard_flagged_images")
rows = cur.fetchall()
print("Current flagged_images rows:")
for r in rows:
    print(f"  id={r[0]}, item={r[1]}, seller_id={r[2]}, phash={r[3][:16] if r[3] else None}...")

# Update seller_id
cur.execute(
    "UPDATE slabguard_flagged_images SET seller_id = %s WHERE ebay_item_id = %s",
    ('as-882232', '317977767993')
)
conn.commit()
print("\n✅ seller_id updated to 'as-882232' for item 317977767993")

# Also check submissions table has the column
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name IN ('slabguard_flagged_images', 'slabguard_submissions')
    AND column_name = 'seller_id'
""")
cols = cur.fetchall()
print(f"seller_id column exists in {len(cols)} table(s) — {'✅ migration ran' if len(cols) == 2 else '❌ migration may not have run yet'}")

cur.close()
conn.close()
