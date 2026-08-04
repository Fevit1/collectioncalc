# Post-Mortem: NLQ Read-Only Role and the Two-Day Push Gap

**Date:** 2026-08-04
**Project:** Slab Worthy
**Severity:** No outage. Security exposure open longer than necessary; no evidence of exploitation.
**Related commits:** 8709518 (local, 2026-08-02), 5f2deb5 (pushed 2026-08-04)
**Related lesson:** L-SW-2026-019

---

## 1. Summary

A security review of the admin NLQ handler on 2026-08-02 found that Claude-generated SQL was being passed to `cur.execute()` on the app's read-write connection pool, guarded only by a `SELECT`-prefix check and a keyword denylist with no `create` entry. `SELECT 1; CREATE TABLE x AS SELECT * FROM users` passed both checks. The fix was written the same session but did not reach production until 2026-08-04, because a local commit was mistaken for a completed push and nobody verified. Root cause of the vulnerability: model-authored SQL executed with privileges far wider than the operation required. Root cause of the delay: an unverified assumption about git state.

---

## 2. Timeline

### 2026-08-02

- Architecture discussion of semantic layers leads to inspection of SW's NLQ implementation.
- DO reports the chain: `admin_routes.py:341` to `natural_language_query()` at `admin.py:383` to prompt with hardcoded `DB_SCHEMA` to `client.messages.create()` to `response.content[0].text.strip()` to markdown-fence stripping to `cur.execute()` on `get_db_connection()`.
- Guards identified at `admin.py:436-454`: lowercase `select` prefix check, regex denylist for `insert|update|delete|drop|truncate|alter|grant|revoke`. No `create`.
- Fix scoped: SELECT-only Postgres role, unpooled, fails closed, history INSERT split onto the read-write pool.
- Commit 8709518 created locally. **Not pushed.** Believed shipped.

### 2026-08-04, morning

- Follow-up work begins on the assumption the fix is live.
- DO's verification probe finds: `nlq_readonly` does not exist, remote main is 3a630f0, `admin_nlq_history` latest row is id=42 dated 2026-07-16. Nothing deployed. 19 days since the last NLQ run.
- User reports "ran the commit" was accurate and incomplete: commit succeeded, push did not.
- Push executed. `3a630f0..5f2deb5`. Verified with `git log origin/main --oneline -1`.

### 2026-08-04, grants

- Part A run on admin connection. `CREATE ROLE nlq_readonly WITH LOGIN PASSWORD '<fakepassword>'` executed with the angle brackets intact. Password became the literal string including brackets. Detected at DBeaver connection test. Corrected with `ALTER ROLE`.
- New DBeaver connection created by duplicating the working connection rather than building from scratch.
- Part B initially attempted on the admin connection tab. Caught before execution.
- Part B on the correct connection: three session settings confirmed, positive control returned 3 user rows and 9,972, six refusals all genuine.
- Part C via catalog ACLs: 31 columns on `users` without `password_hash`, 9 tables in the table-level grant with `users` absent.

### 2026-08-04, deploy

- `DATABASE_URL_NLQ` added to Render. `jdbc:` prefix correctly omitted, `?sslmode=require` appended.
- Deploy at 5f2deb5.
- Post-deploy NLQ run returned 8 rows in 3,312ms, all `source = 'whatnot'`.
- `admin_nlq_history` row 43 confirmed with `result_count` 8, `execution_time_ms` 3312. History split verified working.

### 2026-08-04, view fix

- View filter fix approved as a single edit: remove `WHERE market_sales.source = 'whatnot'`.
- DO found during implementation that the second leg emitted `'whatnot'::text` as a hardcoded literal, not the column. The approved single edit would have caused a future non-Whatnot row to be included and mislabelled as whatnot.
- Two edits made. Before and after counts both 173,346, delta 0. `pg_get_viewdef` confirmed literal gone, `WHERE` gone, `market_sales.source` present. ACL byte-identical, 9 rows.

### 2026-08-04, Phase 1

- `all_comic_sales` added to `DB_SCHEMA` (3,609 to 4,889 chars) and granted.
- Verified: ten objects granted, `users` still absent, source split returns ebay 163,374 and whatnot 9,972, raw `ebay_sales` still denied.
- 8,429 staged `.claude` deletions detected in the index before commit and cleared with `git reset -- .claude`.
- Committed, pushed, deployed.

---

## 3. What worked

- **Verifying deploy artifacts against the catalog rather than against belief.** DO's probe used a positive control (five roles visible) so the absence of `nlq_readonly` was a real finding, not a broken query. This is the check that surfaced the two-day gap.
- **DO catching its own broken verification.** `information_schema.column_privileges` is filtered to currently-enabled roles, so DO's earlier offer to verify grants from `DATABASE_URL_RO` would have returned zero rows whether or not the grants existed. A guaranteed false negative. Caught and replaced with catalog ACL queries before it was relied on.
- **Failing closed on the missing env var.** `get_db_readonly()` raises rather than falling back to `DATABASE_URL`. A fallback would have silently restored the read-write role while looking like a working config.
- **Splitting the history INSERT onto the read-write pool.** The new role cannot write by design. Bundling the audit write with the query would have broken logging at deploy.
- **Duplicating the working DBeaver connection instead of building a new one.** Host, port, database, and SSL settings carried over unchanged, removing four typo opportunities.
- **Requiring `pg_get_viewdef` as the evidence for the view change.** Row counts were identical before and after by construction, so they could only prove nothing broke. The definition text was the only thing that could prove the change took.
- **Checking the index before committing.** The 8,429 staged `.claude` deletions would have entered the Phase 1 commit, including four skills referenced in CLAUDE.md.

---

## 4. What didn't work

- **A local commit was mistaken for a completed push.** Two days of exposure on a fix that was already written. The standing rule "verify pushes explicitly, never assume success" exists for exactly this and was not applied.
- **Claude sequenced the verification wrong.** The instruction was to run the positive control before creating the role. Run as the admin user against tables that already existed, it proved only that the admin could read them. The correct order is create the role, connect as the role, then verify. Caught by the user asking how to proceed rather than by Claude.
- **Claude put the fix command above the cautions in the `.claude` cleanup message.** Read top to bottom, that reads as a sequence, and `git rm -r --cached .claude` was run before scoping. No damage, since the index change is reversible and removes nothing from disk, but the ordering was the cause.
- **A bracketed placeholder was run literally.** The password ended up containing the angle brackets. The standing rule against bracketed placeholders in command blocks exists for this. Cost: one confusing auth failure.
- **The view filter scope saw one edit where there were two.** The diagnosis was correct and the edit count was wrong. The `WHERE` clause and the `'whatnot'::text` literal encoded the same premise twice. Removing one turned the other from redundant into silently wrong. Caught in implementation, not in scoping, by DO.
- **Claude recommended revoking the `market_sales` grant without knowing what it removed.** DO's scoping found 19 columns lost, including `is_facsimile` and `is_reprint` at 100% population, which are comp-quality filters. The recommendation was directionally right and unpriced.
- **`.claude/worktrees` has been polluting `git status` since 2026-03-19.** 8,424 files of noise across every status check. It contributed to the missed push by burying the signal. The March 19 commit that caused it is the same commit that added CLAUDE.md carrying the "never `git add -A`" rule.

---

## 5. Root cause

### For the vulnerability: three factors that were individually defensible

1. NLQ was built as a single-user admin tool where the operator designed the schema, so a permissive execution context was never questioned.
2. The guard was written as a denylist, which enumerates known-bad rather than permitting known-good. It caught what it was told to catch. `create` was not on the list, and `psycopg2` executes multi-statement strings.
3. The execution privilege was inherited from the app's general-purpose pool rather than scoped to the operation. Nothing about the NLQ path required write access; it had it because that was the connection available.

The combination meant a probabilistic generator authored a string that a deterministic executor ran faithfully with full privileges. Neither component was wrong in isolation.

### For the two-day delay: one factor

The commit succeeded and the push did not, and the state was never checked. `git status` was unusable because of the `.claude` pollution, which removed the ambient signal that would normally have caught it. This is the second-order cost of tolerating noise in a status display.

---

## 6. Action items

### Shipped already

- `nlq_readonly` role: SELECT-only, unpooled, 15s statement timeout, read-only session, fails closed on missing `DATABASE_URL_NLQ`
- `users` granted at column level excluding `password_hash`, and deliberately absent from the table-level grant since privileges are additive
- `admin_nlq_history` INSERT split onto the read-write pool; logging failure no longer fails the query
- Denylist and prefix check retained as first layer
- `migrations/nlq_readonly_role.sql` committed with placeholder password and a comment explaining the `users` omission
- `all_comic_sales` view: `WHERE` clause removed and `'whatnot'::text` literal replaced with `market_sales.source`
- Phase 1: `all_comic_sales` in `DB_SCHEMA` and granted
- `DATABASE_URL_NLQ` documented in `ARCHITECTURE.txt`

### Queued, not urgent

All tracked in Todoist under Slab Worthy.

- `.claude/worktrees` untrack, keep `.claude/skills` tracked, `.gitignore` restructure
- `git gc` (5,144 loose objects, 119.66 MiB, never packed)
- Phase 2: view extension plus `market_sales` revoke as one unit, with the ordering inverted from Phase 1
- Sync-check script enforcing described-equals-granted
- Phase 3: Tier A newcomers
- Polysemy audit across 472 columns
- `graded_comics` identification
- R2 close-out
- `R2_CUTOVER_RUNBOOK.md` date drift

### Process and lesson changes

- **L-SW-2026-019 (written):** removing a filter and removing the hardcoded assumption it protected are two edits. A scope that sees only the filter ships a new bug while closing an old one. Generalizes past SQL: validated-input check plus downstream cast, length guard plus fixed buffer, feature flag plus hardcoded branch. Candidate for cross-project promotion.
- **New, not yet written:** a verification query must be provable to fail. If the query would return the same empty result whether the thing exists or not, it is not a verification. Run a positive control first. Adjacent to L-2026-024 and may belong as an extension rather than a new entry. Cross-project.
- **New, not yet written:** identity of the executing role is part of a verification's meaning. The same query run as owner, grantee, or third party can return three different answers, and two of them are misleading. Name the connection in the instruction, not just the SQL. Cross-project.
- **Reinforce, do not rewrite:** the push-verification rule and the bracketed-placeholder rule both already exist and both were violated. The gap is application, not authorship. The `.claude` cleanup is the concrete remediation for the push case, since it restores `git status` as a usable signal.
- **For Claude specifically:** cautions belong above the command they qualify, never below. A numbered sequence will be read as a sequence.

---

## Appendix: the thread underneath

The day started as a conversation about model tiers and semantic layers and ended in DBA work, but the question was constant: where does a probabilistic guess sit, and does its failure announce itself.

The recurring move was eliminate versus observe. The read-only role eliminates arbitrary writes rather than watching for them. Deriving the source label eliminates mislabelling rather than monitoring for it. Revoking the `market_sales` grant in Phase 2 would eliminate the wrong-corpus answer rather than steering away from it.

L-SW-2026-019's shape appeared three separate times in one day: the filter and the literal, the revoke and the `DB_SCHEMA` entry, the grant and the description. One decision, two edits, every time.

The sharpened form of the standing thesis: "AI on the edges, deterministic core in the middle" is not really about AI. It is about where an unfindable failure is acceptable. A wrong SQL query and a wrong git assumption are both wrong. Only one of them tells you.
