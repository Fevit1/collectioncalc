"""
Database migration: Add billing/subscription columns to users table
Run this in Render shell AFTER deploying the code:
    python db_migrate_billing.py
"""

import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("Adding billing columns to users table...")

# Add columns one at a time (IF NOT EXISTS via checking information_schema)
columns_to_add = [
    ("plan", "VARCHAR(20) DEFAULT 'free'"),
    ("stripe_customer_id", "VARCHAR(255)"),
    ("stripe_subscription_id", "VARCHAR(255)"),
    ("subscription_status", "VARCHAR(20) DEFAULT 'none'"),
    ("billing_period", "VARCHAR(10) DEFAULT 'monthly'"),
    ("current_period_end", "TIMESTAMP"),
    ("valuations_this_month", "INTEGER DEFAULT 0"),
    ("valuations_reset_date", "TIMESTAMP"),
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

# Add index on stripe_customer_id for webhook lookups
cur.execute("""
    SELECT indexname FROM pg_indexes
    WHERE tablename = 'users' AND indexname = 'idx_users_stripe_customer_id'
""")
if not cur.fetchone():
    cur.execute("CREATE INDEX idx_users_stripe_customer_id ON users(stripe_customer_id)")
    print("  + Added index on stripe_customer_id")
else:
    print("  ✓ Index on stripe_customer_id already exists")

conn.commit()
cur.close()
conn.close()

print("\n✅ Billing migration complete!")
print("\nNext steps:")
print("1. Add these environment variables in Render:")
print("   STRIPE_SECRET_KEY=sk_test_...")
print("   STRIPE_WEBHOOK_SECRET=whsec_...")
print("   STRIPE_PRO_MONTHLY_PRICE_ID=price_...")
print("   STRIPE_PRO_ANNUAL_PRICE_ID=price_...")
print("   STRIPE_GUARD_MONTHLY_PRICE_ID=price_...")
print("   STRIPE_GUARD_ANNUAL_PRICE_ID=price_...")
print("   STRIPE_DEALER_MONTHLY_PRICE_ID=price_...")
print("   STRIPE_DEALER_ANNUAL_PRICE_ID=price_...")
print("   FRONTEND_URL=https://slabworthy.com")
print("\n2. Create these products/prices in Stripe Dashboard")
print("3. Set up webhook endpoint: https://your-api.onrender.com/api/billing/webhook")
print("   Events to listen for:")
print("   - checkout.session.completed")
print("   - customer.subscription.updated")
print("   - customer.subscription.deleted")
print("   - invoice.payment_succeeded")
print("   - invoice.payment_failed")
