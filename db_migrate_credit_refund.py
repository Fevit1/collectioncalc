"""
Migration: credit-refund-on-refused-FMV unit (2026-08-27).

Adds:
  - grade_submissions.grading_uuid  (text, unique when present) — the client-
    facing grading identifier. Minted server-side in /api/grade BEFORE the
    async retention persist, returned in the grade response, and passed back
    by the frontend to /api/sales/valuation. Closes part of LAUNCH_READINESS
    item 118's "no client grading_id".
  - grade_submissions.credit_refunded (bool, default false) — the idempotency
    flag: one credit refund per grading, ever. The flag flip IS the gate; the
    counter decrement only runs when this row transitions false -> true.
  - lookup_demand.verdict_basis (text) — makes multi_edition (and every other
    verdict tier) countable in telemetry. Before this, refund-qualifying
    refusals were invisible: fmv_method stays 'exact' when the gate fires.

Idempotent: every statement is ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT
EXISTS. Run in the Render shell (needs DATABASE_URL, i.e. the read-write env):

    python db_migrate_credit_refund.py

Run BEFORE deploying the code that references these columns.
"""

import os
import sys
import psycopg2

STATEMENTS = [
    ("grade_submissions.grading_uuid",
     "ALTER TABLE grade_submissions ADD COLUMN IF NOT EXISTS grading_uuid TEXT"),
    ("grade_submissions.credit_refunded",
     "ALTER TABLE grade_submissions ADD COLUMN IF NOT EXISTS credit_refunded BOOLEAN NOT NULL DEFAULT FALSE"),
    ("unique index on grading_uuid",
     "CREATE UNIQUE INDEX IF NOT EXISTS idx_grade_submissions_grading_uuid "
     "ON grade_submissions (grading_uuid) WHERE grading_uuid IS NOT NULL"),
    ("lookup_demand.verdict_basis",
     "ALTER TABLE lookup_demand ADD COLUMN IF NOT EXISTS verdict_basis TEXT"),
]


def main():
    url = os.environ.get('DATABASE_URL')
    if not url:
        print("DATABASE_URL not set — run this in the Render shell, not locally.")
        sys.exit(1)
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    for label, sql in STATEMENTS:
        cur.execute(sql)
        print(f"ok: {label}")
    conn.commit()
    cur.close()
    conn.close()
    print("migration complete.")


if __name__ == '__main__':
    main()
