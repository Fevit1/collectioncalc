"""
One-time data fix: approve accounts left stranded by the removed beta-code gate.

Context (2026-07-29): before the gate was removed, signup() set
    auto_approve = bool(beta_code) or waitlist_confirmed
so anyone who signed up WITHOUT a code and WITHOUT a confirmed waitlist entry
landed at is_approved=FALSE and could not log in at all — login() refuses them with
"Your account is pending approval." Removing the gate fixes this for NEW signups
only; accounts already in that state stay locked out until this runs.

Scope: verified, non-admin, not-yet-approved accounts. Expected to match exactly 1
row at time of writing. Unverified accounts are deliberately left alone — email
verification is now THE gate, so approving someone who never proved inbox control
would defeat the thing that replaced the beta code.

    python db_migrate_approve_pending_users.py --dry-run    # shows rows, ROLLS BACK
    python db_migrate_approve_pending_users.py              # commits

Idempotent: re-running matches nothing once the accounts are approved.
"""

import os
import sys
import argparse

# Cross-project L-2026-015: UTF-8 stdout on Windows (this prints check marks).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import psycopg2
from psycopg2.extras import RealDictCursor

parser = argparse.ArgumentParser(description="Approve accounts stranded by the removed beta gate.")
parser.add_argument("--dry-run", action="store_true",
                    help="Show what would change, then ROLL BACK.")
args = parser.parse_args()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 72)
print("Approve stranded accounts" + ("  [DRY RUN — will ROLL BACK]" if args.dry_run else ""))
print("=" * 72)

try:
    cur.execute("""
        SELECT current_database() AS db, current_user AS usr,
               inet_server_addr()::text AS host
    """)
    t = cur.fetchone()
    print(f"\nTARGET  db={t['db']}  user={t['usr']}  host={t['host'] or 'local'}")
    print("^ confirm this is the intended database before committing.\n")

    # Show the candidates BEFORE touching them.
    cur.execute("""
        SELECT id, email, email_verified, is_approved, is_admin,
               created_at::date AS created, last_login::date AS last_login
        FROM users
        WHERE is_approved = FALSE AND is_admin = FALSE AND email_verified = TRUE
        ORDER BY id
    """)
    candidates = cur.fetchall()
    print(f"[1] CANDIDATES (verified, non-admin, unapproved): {len(candidates)}")
    for c in candidates:
        print(f"    id={c['id']:<4} {c['email'][:44]:44} created={c['created']} "
              f"last_login={c['last_login'] or 'NEVER'}")

    # For contrast: who is deliberately NOT being touched.
    cur.execute("""
        SELECT COUNT(*) AS n FROM users
        WHERE is_approved = FALSE AND is_admin = FALSE AND email_verified = FALSE
    """)
    skipped = cur.fetchone()["n"]
    print(f"\n[2] DELIBERATELY SKIPPED (unapproved but UNVERIFIED): {skipped}")
    print("    Email verification is now the gate — these must verify first.")

    if not candidates:
        print("\nNothing to do. (Already approved, or none stranded.)")
        conn.rollback()
        sys.exit(0)

    cur.execute("""
        UPDATE users SET is_approved = TRUE, approved_at = NOW()
         WHERE is_approved = FALSE AND is_admin = FALSE AND email_verified = TRUE
        RETURNING id, email, is_approved
    """)
    updated = cur.fetchall()
    print(f"\n[3] UPDATED {len(updated)} row(s):")
    for u in updated:
        print(f"    id={u['id']:<4} {u['email'][:44]:44} is_approved={u['is_approved']}")

    ok = len(updated) == len(candidates) and all(u["is_approved"] for u in updated)
    print("\n    " + ("✓ all candidates approved" if ok else "✗ MISMATCH — review"))

    if args.dry_run:
        conn.rollback()
        print("\n[DRY RUN] rolled back — no changes persisted.")
    elif not ok:
        conn.rollback()
        print("\n✗ rolled back — verification failed.")
        sys.exit(1)
    else:
        conn.commit()
        print("\n✓ COMMITTED.")

except Exception as e:
    conn.rollback()
    print(f"\n✗ ERROR — rolled back: {e}")
    raise
finally:
    cur.close()
    conn.close()
