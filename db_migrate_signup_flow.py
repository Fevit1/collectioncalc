"""
Database migration: Unit D signup-flow columns.

Adds:
  users.email_canonical    TEXT      -- alias-collapsed email, for the signup dup-check
  users.has_selected_plan  BOOLEAN   -- has this user chosen a plan yet?

Run in the Render shell AFTER deploying (or before — see ORDERING below):
    python db_migrate_signup_flow.py --dry-run    # does everything, then ROLLS BACK
    python db_migrate_signup_flow.py              # commits

────────────────────────────────────────────────────────────────────────────────
ORDERING — why this migration is safe to run BEFORE the Unit D code ships
────────────────────────────────────────────────────────────────────────────────
Both columns are backward-compatible with the currently-deployed code:

  * email_canonical is NULLABLE. The live signup() does not know about it, so new
    rows created between this migration and the Unit D deploy simply get NULL.
    It is deliberately NOT "NOT NULL" — that constraint would make every signup
    fail with NotNullViolation until the code that populates it goes out.
    (Tighten to NOT NULL in a follow-up migration once signup() writes it.)
    Postgres unique indexes permit multiple NULLs, so the unique index below
    does not block those interim rows.

  * has_selected_plan is NOT NULL DEFAULT FALSE, so INSERTs that omit it (i.e.
    every INSERT in the currently-deployed code) still succeed and get FALSE —
    which is the correct semantic for a brand-new account.

────────────────────────────────────────────────────────────────────────────────
BACKFILL POLICY — decided with Mike 2026-07-29
────────────────────────────────────────────────────────────────────────────────
  * email_canonical = email, verbatim. NO canonicalisation of existing rows.
    Canonicalisation applies to NEW SIGNUPS ONLY. Reason (measured): 11 of the
    existing accounts are mikeberrysc+<something>@gmail.com aliases; collapsing
    them would merge 11 live accounts into one and break those logins. Verified
    safe: email is already UNIQUE (users_email_key), 0 rows differ from
    lower(email), and 0 pairs collide under lower() — so canonical stays unique.

  * has_selected_plan = TRUE where EITHER
        last_login IS NOT NULL                 (you've actually used the product)
     OR COALESCE(plan,'free') <> 'free'        (you're already on a paid plan,
                                                which IS a plan selection)
    Those users keep what they have and are never interrupted by a plan page.
    The second clause protects paid accounts with no recorded login — e.g. the
    deliberate test-dealer fixture and any DB-granted tier — from being shown the
    page and having their tier clobbered by whatever gets picked.

    Everyone else stays FALSE and sees the page at first login. That is the right
    moment to present it, and it matters because the free tier sunsets ~Sept 4 —
    never-activated waitlist accounts should be choosing a plan, not silently
    inheriting a closing tier. New rows also default to FALSE and will see it.

This script is idempotent — safe to re-run.
"""

import os
import sys
import argparse

# Cross-project L-2026-015: this prints check marks/arrows; a cp1252 console
# would die with UnicodeEncodeError mid-migration. Harmless on Render (Linux).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import psycopg2
from psycopg2.extras import RealDictCursor

parser = argparse.ArgumentParser(description="Unit D signup-flow migration.")
parser.add_argument("--dry-run", action="store_true",
                    help="Apply everything, print the verification, then ROLL BACK.")
args = parser.parse_args()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False          # one transaction; --dry-run rolls it back
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 72)
print("Unit D signup-flow migration" + ("  [DRY RUN — will ROLL BACK]" if args.dry_run else ""))
print("=" * 72)


def column_exists(table, column):
    cur.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return cur.fetchone() is not None


def index_exists(name):
    cur.execute("SELECT 1 FROM pg_class WHERE relname = %s AND relkind = 'i'", (name,))
    return cur.fetchone() is not None


try:
    # ── PRE-FLIGHT: prove the backfill can't violate uniqueness ────────────
    print("\n[0] PRE-FLIGHT")

    # Say out loud which database is about to be written to. This script MUST NOT
    # be pointed at a read-only URL (it would fail) or at the wrong database (it
    # would succeed, which is worse). Check this line before letting it commit.
    cur.execute("""
        SELECT current_database() AS db, current_user AS usr,
               inet_server_addr()::text AS host, inet_server_port() AS port
    """)
    tgt = cur.fetchone()
    print(f"    TARGET  db={tgt['db']}  user={tgt['usr']}  "
          f"host={tgt['host'] or 'local'}:{tgt['port']}")
    print("    ^ confirm this is the intended database before committing.")

    cur.execute("SELECT COUNT(*) AS n FROM users")
    total = cur.fetchone()["n"]
    cur.execute("SELECT COUNT(*) AS n FROM users WHERE email <> lower(email)")
    non_lower = cur.fetchone()["n"]
    cur.execute("""
        SELECT COUNT(*) AS n FROM (
            SELECT lower(email) FROM users GROUP BY 1 HAVING COUNT(*) > 1
        ) d
    """)
    collisions = cur.fetchone()["n"]
    print(f"    users rows                     : {total}")
    print(f"    rows where email <> lower(email): {non_lower}")
    print(f"    lower(email) collisions         : {collisions}")
    if collisions:
        print("    ✗ ABORT — backfilling email_canonical would violate the unique index.")
        conn.rollback()
        sys.exit(1)
    print("    ✓ safe to backfill email_canonical = email")

    # ── 1. email_canonical ────────────────────────────────────────────────
    print("\n[1] users.email_canonical")
    if column_exists("users", "email_canonical"):
        print("    ✓ column already exists")
    else:
        cur.execute("ALTER TABLE users ADD COLUMN email_canonical TEXT")
        print("    + column added (TEXT, NULLABLE by design — see ORDERING in the docstring)")

    cur.execute("UPDATE users SET email_canonical = email WHERE email_canonical IS NULL")
    print(f"    + backfilled {cur.rowcount} row(s) with email VERBATIM (no canonicalisation)")

    if index_exists("idx_users_email_canonical"):
        print("    ✓ unique index already exists")
    else:
        cur.execute("CREATE UNIQUE INDEX idx_users_email_canonical ON users (email_canonical)")
        print("    + unique index idx_users_email_canonical created")

    # ── 2. has_selected_plan ──────────────────────────────────────────────
    print("\n[2] users.has_selected_plan")
    if column_exists("users", "has_selected_plan"):
        print("    ✓ column already exists")
        newly_added = False
    else:
        cur.execute(
            "ALTER TABLE users ADD COLUMN has_selected_plan BOOLEAN NOT NULL DEFAULT FALSE"
        )
        print("    + column added (NOT NULL DEFAULT FALSE — safe for existing INSERTs)")
        newly_added = True

    if newly_added:
        # Grandfather (Mike, 2026-07-29), two independent reasons to keep what you have:
        #   (a) last_login IS NOT NULL  -- you've actually used the product; never
        #       interrupt an active user with a plan-selection page.
        #   (b) plan <> 'free'          -- you are already ON a paid plan, which IS a
        #       plan selection. Without this, a paid account with no recorded login
        #       (e.g. the deliberate test-dealer fixture, or a DB-granted tier) would
        #       be shown the page and could have its tier clobbered by whatever it picks.
        # Everyone else stays FALSE and sees the page at first login -- the right moment,
        # especially with the free tier sunsetting ~Sept 4.
        # COALESCE keeps this NULL-safe: plan is a nullable column, and a NULL plan is
        # semantically free, so it must NOT count as a selection.
        # Runs only on first add, so a re-run never re-flags accounts that legitimately
        # became FALSE afterwards.
        cur.execute("""
            UPDATE users SET has_selected_plan = TRUE
             WHERE last_login IS NOT NULL
                OR COALESCE(plan, 'free') <> 'free'
        """)
        grandfathered = cur.rowcount
        cur.execute("""
            SELECT COUNT(*) AS n FROM users
             WHERE last_login IS NULL AND COALESCE(plan, 'free') = 'free'
        """)
        left_false = cur.fetchone()["n"]
        print(f"    + grandfathered {grandfathered} row(s) to TRUE "
              f"(active OR already on a paid plan)")
        print(f"    · {left_false} row(s) left FALSE — they will see the plan page")
    else:
        print("    · skipped grandfather UPDATE (column pre-existed; re-run is a no-op)")

    # ── 3. VERIFY ─────────────────────────────────────────────────────────
    print("\n[3] VERIFICATION")
    cur.execute("""
        SELECT COUNT(*) AS total,
               COUNT(email_canonical) AS canon_set,
               COUNT(*) FILTER (WHERE email_canonical = email) AS canon_matches_email,
               COUNT(*) FILTER (WHERE has_selected_plan) AS selected_true,
               COUNT(*) FILTER (WHERE NOT has_selected_plan) AS selected_false
        FROM users
    """)
    v = cur.fetchone()
    for k, val in v.items():
        print(f"    {k:22} {val}")

    cur.execute("""
        SELECT COUNT(*) AS n FROM (
            SELECT email_canonical FROM users
            WHERE email_canonical IS NOT NULL
            GROUP BY 1 HAVING COUNT(*) > 1
        ) d
    """)
    dupes = cur.fetchone()["n"]
    print(f"    duplicate canonicals   {dupes}")

    # The grandfather assertion only holds on the FIRST run. On a re-run, genuine
    # new signups will legitimately be has_selected_plan=FALSE, so asserting
    # selected_true == total would fail spuriously and roll back a healthy DB.
    checks = {
        "every row has a canonical":      v["canon_set"] == v["total"],
        "canonical == email (no backfill canonicalisation)":
                                          v["canon_matches_email"] == v["total"],
        "no duplicate canonicals":        dupes == 0,
    }
    if newly_added:
        # Same predicate as the UPDATE, so the assertion can't drift from the action.
        cur.execute("""
            SELECT COUNT(*) FILTER (
                     WHERE last_login IS NOT NULL OR COALESCE(plan,'free') <> 'free'
                   ) AS should_be_true,
                   COUNT(*) FILTER (
                     WHERE last_login IS NULL AND COALESCE(plan,'free') = 'free'
                   ) AS should_be_false
            FROM users
        """)
        a = cur.fetchone()
        checks["grandfathered == active OR paid"] = \
            v["selected_true"] == a["should_be_true"]
        checks["left FALSE == never-logged-in AND free (will see the plan page)"] = \
            v["selected_false"] == a["should_be_false"]
    else:
        print("    · grandfather assertion skipped (re-run; FALSE rows may be real new signups)")

    for label, passed in checks.items():
        print(f"    {'✓' if passed else '✗'} {label}")
    ok = all(checks.values())
    print("\n    " + ("✓ all checks pass" if ok else "✗ CHECKS FAILED — review before committing"))

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

# ──────────────────────────────────────────────────────────────────────────
# REJECTED ALTERNATIVE (do not reinstate without asking): grandfathering EVERY
# existing row via a bare `UPDATE users SET has_selected_plan = TRUE`.
# Mike chose the active-only policy on 2026-07-29: never-activated accounts
# should be asked to choose a plan at first login rather than silently keeping
# a free tier that closes in September.
# ──────────────────────────────────────────────────────────────────────────
