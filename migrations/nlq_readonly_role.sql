-- =====================================================================
-- nlq_readonly — SELECT-only Postgres role for the admin NLQ handler
-- =====================================================================
--
-- WHAT THIS IS
--   The role that executes model-generated SQL from `/api/admin/nlq`
--   (admin.py:natural_language_query). The handler reaches it through
--   DATABASE_URL_NLQ via db.get_db_readonly(); it never touches the app's
--   read-write DATABASE_URL.
--
-- WHY
--   The handler's original guards were a SELECT-prefix check and a keyword
--   denylist. The denylist has no 'create' entry and psycopg2 executes
--   multi-statement strings, so
--       SELECT 1; CREATE TABLE x AS SELECT * FROM users
--   passed both checks and ran on the read-write role. The denylist is
--   retained as the first layer; THIS is the layer that holds when it
--   doesn't.
--
-- HOW TO RUN
--   By hand, in DBeaver, as the database owner, in statement order.
--   Nothing runs this automatically — it is not wired into any migration
--   runner, and it is not idempotent (step 1 errors if the role exists).
--
-- PASSWORD
--   Step 1 carries a PLACEHOLDER. Generate a real password yourself and
--   substitute it at run time. Never commit a real password to this file
--   and never paste one into a chat session.
--
-- AFTER RUNNING
--   Set DATABASE_URL_NLQ on the collectioncalc-docker Render service:
--   same host/db as DATABASE_URL, user nlq_readonly, ?sslmode=require.
--   The env change needs a redeploy AND a fresh shell (L-SW-2026-004).
--   Without it the NLQ endpoint fails closed with "NLQ read-only role not
--   configured" — by design; it does not fall back to DATABASE_URL.
--
-- RELATED
--   docs/sessions/WHERE_WE_LEFT_OFF.md — 2026-08-04 entry
--   docs/technical/ARCHITECTURE.txt    — DATABASE_URL_NLQ row
--   admin.py                           — DB_SCHEMA known-limitation comment
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Role
-- ---------------------------------------------------------------------
CREATE ROLE nlq_readonly WITH LOGIN PASSWORD '<GENERATE_A_PASSWORD_YOURSELF>';


-- ---------------------------------------------------------------------
-- 2. Connect + schema usage
-- ---------------------------------------------------------------------
-- Database name verified against the live catalog 2026-08-04: collectioncalc_db
-- (NOT "collectioncalc" — an earlier draft of this file had that wrong and
-- would have errored here).
GRANT CONNECT ON DATABASE collectioncalc_db TO nlq_readonly;
GRANT USAGE ON SCHEMA public TO nlq_readonly;


-- ---------------------------------------------------------------------
-- 3. Table-level SELECT on 9 of the 10 tables named in DB_SCHEMA.
--
--    ⚠️ `users` IS DELIBERATELY ABSENT FROM THIS LIST. DO NOT ADD IT.
--    It gets column-level grants at step 4, excluding password_hash.
--    PostgreSQL SUMS table-level and column-level privileges — a
--    table-level grant is NOT diminished by a column-level one, and there
--    is no column-level revoke that undoes it. So adding `users` here
--    re-exposes password_hash to the NLQ role SILENTLY: no error, no
--    warning, and step 4 still appears to have worked
--    (information_schema.column_privileges will still list the granted
--    columns). The ONLY thing keeping password_hash out of reach is that
--    this list omits `users`. If you ever re-run this block, re-read this
--    comment first.
--
--    `ebay_sales` is also absent, and that is deliberate: it is not in
--    DB_SCHEMA either, so the model cannot see it. Prompt and grants are
--    kept consistent on purpose — widening one without the other is the
--    failure mode. See the known-limitation comment in admin.py.
-- ---------------------------------------------------------------------
GRANT SELECT ON
    beta_codes,
    request_logs,
    api_usage,
    market_sales,
    collections,
    search_cache,
    comic_registry,
    sighting_reports,
    blocked_reporters
TO nlq_readonly;


-- ---------------------------------------------------------------------
-- 3b. all_comic_sales — the complete sales corpus (VIEW).  [Phase 1, 2026-08-04]
--
--    THE INVARIANT: the set of objects described in admin.py's DB_SCHEMA
--    equals the set granted here. This grant is the second half of the
--    same unit that added `all_comic_sales` to DB_SCHEMA. Never ship one
--    without the other — a described-but-ungranted object throws a
--    permission error (loud, safe), a granted-but-undescribed object
--    silently widens the role's reach with no reason on record.
--
--    ⚠️ Granting the VIEW does NOT grant `ebay_sales`. A view executes
--    against its OWNER's rights on the base tables, so nlq_readonly reads
--    the full 173k-row corpus through this view while still being denied
--    raw `ebay_sales`. That is deliberate, not an oversight.
--
--    Why this exists: before Phase 1, `ebay_sales` (163,374 rows, 94.2%)
--    was invisible to NLQ and `market_sales` (9,972, 5.8%) was not, so
--    sales questions were answered from under 6% of the corpus and read
--    as complete. The first production NLQ run, 2026-08-04, returned 8
--    rows all sourced 'whatnot' — the hole, live.
-- ---------------------------------------------------------------------
GRANT SELECT ON all_comic_sales TO nlq_readonly;

--    ⚠️ KNOWINGLY UNREACHABLE — DECIDED 2026-08-04, DO NOT RE-LITIGATE.
--    `market_sales.grade_source` and `market_sales.slab_type` will become
--    unreachable to nlq_readonly when Phase 2 revokes the market_sales
--    grant, and they CANNOT be added to all_comic_sales: ebay_sales has no
--    equivalent for either, and any fill would be fabricated (NULL would
--    assert "eBay grades have no source", which is false — eBay grades have
--    a source, it just is not stored; a synthesised slab_type would
--    manufacture a value outright). Both are Whatnot capture-pipeline
--    metadata, not comp data.
--    A narrow column-level grant on market_sales limited to those columns
--    was considered and REJECTED — more grants-file complexity than it
--    returns. If they are ever needed, query them on the read-write
--    connection; do not widen nlq_readonly.


-- ---------------------------------------------------------------------
-- 4. users — every column EXCEPT password_hash.
--
--    Derived from information_schema, never typed out. Verified against the
--    live catalog 2026-08-04: `users` has 32 columns; DB_SCHEMA lists 11 and
--    DATABASE_PRODUCTION.md lists 26. Both sources lag the database, so a
--    hand-written list would be wrong the day it was written.
--
--    Consequence: a column added by a future migration is NOT granted
--    until this block is re-run. That is fail-closed and intended.
--
--    Known cost: `SELECT * FROM users` now FAILS for this role, because
--    the expansion includes password_hash. The model writes SELECT *
--    routinely, so some user-related NLQ questions return a permission
--    error instead of rows. Do not read the first such failure as a
--    broken deploy.
-- ---------------------------------------------------------------------
DO $$
DECLARE cols text;
BEGIN
    SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position)
      INTO cols
      FROM information_schema.columns
     WHERE table_schema = 'public'
       AND table_name   = 'users'
       AND column_name <> 'password_hash';

    IF cols IS NULL THEN
        RAISE EXCEPTION 'No columns found for public.users — refusing to grant nothing';
    END IF;

    EXECUTE format('GRANT SELECT (%s) ON public.users TO nlq_readonly', cols);
    RAISE NOTICE 'Granted SELECT on users columns: %', cols;
END $$;


-- ---------------------------------------------------------------------
-- 5. Role-level guards. Inherited by every session this role opens.
--    statement_timeout lives HERE, not in application code, so a code
--    edit cannot silently drop it.
-- ---------------------------------------------------------------------
ALTER ROLE nlq_readonly SET statement_timeout = '15s';
ALTER ROLE nlq_readonly SET idle_in_transaction_session_timeout = '30s';
ALTER ROLE nlq_readonly SET default_transaction_read_only = on;


-- =====================================================================
-- VERIFICATION — run these AS nlq_readonly, not as the owner.
--
-- The two SUCCEED queries are the positive control (L-2026-024): they
-- prove the role can connect and return a hit, so the failures below
-- are real refusals and not a broken connection. Run them FIRST.
-- =====================================================================
--
-- Should SUCCEED:
--   SELECT id, email, plan, is_admin FROM users LIMIT 3;
--   SELECT count(*) FROM market_sales;
--
-- Should EACH FAIL:
--   SELECT password_hash FROM users LIMIT 1;   -- permission denied for column
--   SELECT * FROM users LIMIT 1;               -- expansion includes password_hash
--   INSERT INTO users (email) VALUES ('nope@example.com');
--   CREATE TABLE nlq_probe AS SELECT 1;
--   SELECT count(*) FROM ebay_sales;
--   SELECT count(*) FROM admin_nlq_history;
--
-- Confirm what actually landed (run as owner):
--   SELECT column_name FROM information_schema.column_privileges
--    WHERE grantee = 'nlq_readonly' AND table_name = 'users'
--    ORDER BY column_name;
--   -- must list the columns and must NOT contain password_hash
--
--   SELECT rolname, rolconfig FROM pg_roles WHERE rolname = 'nlq_readonly';
--   -- rolconfig must show all three settings from step 5
-- =====================================================================
