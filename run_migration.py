import psycopg2

DB_URL = "postgresql://collectioncalc_db_user:iGCXbv2dk3P5aoNvKghOVqE9Q4wgW8ue@dpg-d5knv4koud1c73dt21pg-a.oregon-postgres.render.com/collectioncalc_db"

statements = [
    """
    CREATE TABLE IF NOT EXISTS slabguard_submissions (
        id              SERIAL PRIMARY KEY,
        submitted_by    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        ebay_item_id    VARCHAR(50) NOT NULL,
        ebay_url        TEXT NOT NULL,
        phash           VARCHAR(64),
        risk_score      INTEGER DEFAULT 0,
        signals         JSONB DEFAULT '{}',
        status          VARCHAR(20) DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'rejected')),
        reviewed_by     INTEGER REFERENCES users(id),
        review_note     TEXT,
        reviewed_at     TIMESTAMPTZ,
        created_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_slabguard_submissions_item_pending
        ON slabguard_submissions (ebay_item_id)
        WHERE status = 'pending'
    """,
    "CREATE INDEX IF NOT EXISTS idx_slabguard_submissions_status ON slabguard_submissions (status)",
    "CREATE INDEX IF NOT EXISTS idx_slabguard_submissions_user   ON slabguard_submissions (submitted_by)",
    """
    CREATE TABLE IF NOT EXISTS slabguard_flagged_images (
        id              SERIAL PRIMARY KEY,
        phash           VARCHAR(64) NOT NULL UNIQUE,
        ebay_item_id    VARCHAR(50),
        ebay_url        TEXT,
        submission_id   INTEGER REFERENCES slabguard_submissions(id),
        notes           TEXT,
        added_by        INTEGER REFERENCES users(id),
        created_at      TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_slabguard_phash ON slabguard_flagged_images (phash)",
    """
    CREATE TABLE IF NOT EXISTS slabguard_rate_limits (
        user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        submission_date DATE NOT NULL DEFAULT CURRENT_DATE,
        count           INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, submission_date)
    )
    """,
]

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

for i, sql in enumerate(statements, 1):
    try:
        cur.execute(sql)
        print(f"  [{i}/{len(statements)}] ✅ OK")
    except Exception as e:
        print(f"  [{i}/{len(statements)}] ❌ {e}")
        conn.rollback()
        break
else:
    conn.commit()
    print("\n✅ All SlabGuard tables created successfully")

cur.close()
conn.close()
