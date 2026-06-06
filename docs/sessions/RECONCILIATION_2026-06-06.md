# Slab Worthy — Reconciliation Pass (2026-06-06)

**Type:** Read-only state report. No code modified, nothing committed, nothing deployed.
**Author:** Claude (Opus 4.8), per `DO_BRIEF_RECONCILIATION_2026-06-06.md`.
**Method:** Verified against repo code + live production GET endpoints. Items that could not be
confirmed are marked **UNVERIFIED** with the reason. No assumptions promoted to "done."

**Access available this pass:** local git repo; public/unauthenticated production GET endpoints
(`/health`, `/api/signatures/db-stats`, `/api/sales/valuation`).
**Access NOT available:** admin JWT (so `/api/admin/*` and `/api/signatures/v2/*` → 401), direct
DB (no `DATABASE_URL`, no `psql`), Render dashboard/logs, Stripe dashboard. Gaps are called out per
section — no silent omissions.

---

## 1. Repo state

- **Branch:** `main`
- **Last commit:** `989287c` — 2026-06-01 11:30 -0700 — "Add eBay account-deletion endpoint self-health-check to dependency monitor"
- **Local vs origin:** `main` == `origin/main` (both at `989287c`). **In sync.**
- **Commits since 2026-03-24 (3 total):**
  - `989287c` 2026-06-01 — Add eBay account-deletion endpoint self-health-check to dependency monitor
  - `793897d` 2026-06-01 — Add eBay account-deletion GET challenge handler
  - `80a8997` 2026-05-26 — Repo cleanup: archive stale assets, organize sessions, add LOCATIONS.md
- **Working tree (`git status`) — 2 modified, uncommitted:**
  - `docs/SW_BO_PRIMER.md` — **WIP, legitimate.** A docs file (the BO-project primer mirror per CLAUDE.md). Looks like in-progress doc editing, not junk.
  - `.claude/worktrees/elegant-swirles/.claude/settings.local.json` — **junk / never-commit.** This is a `.claude/` worktree artifact; CLAUDE.md's git rule explicitly says never commit worktree files. Should be left alone (or git-ignored), not staged.
  - No other untracked work-in-progress.
- **Deployed build vs latest commit:** `/health` reports `version: 5.6.0`, which **matches** the `version` string hard-coded in `routes/utils.py` at HEAD. That's a strong signal the deployed build is current, but **UNVERIFIED at the commit level** — I have no Render dashboard/API access to read the deployed commit SHA. Version-string match only.

---

## 2. Production health

- **`GET /health` → HTTP 200.** Body:
  ```json
  {"barcode":true,"dependency_check_error":"'list' object has no attribute 'get'","moderation":true,"status":"ok","version":"5.6.0"}
  ```
  Core service is **up** (status ok, barcode + moderation subsystems available). **But** there is a live
  `dependency_check_error`. See the bug below — this is the top finding of the pass.

- **`GET /api/admin/dependency-status` → HTTP 401** `{"error":"Authentication required"}`. **UNVERIFIED** — requires an admin JWT I don't have. Could not read the per-service status (Anthropic/eBay/Stripe/account-deletion self-check) from this endpoint. However, the `/health` error below tells us what its result would be.

- **🔴 LIVE BUG — the entire dependency monitor is failing on every health check.**
  - **Symptom:** `dependency_check_error: "'list' object has no attribute 'get'"` on `/health`.
  - **Root cause (confirmed, not inferred):** `dependency_monitor.check_anthropic()` does `data.get("items", [])` at `dependency_monitor.py:131`. That line is **outside** the function's try/except (which only wraps the HTTP fetch at lines 120–126). I fetched `https://deprecations.info/v1/deprecations.json` directly this pass: it now returns a **top-level JSON array** (`[ {...}, ... ]`), not the `{"items": [...]}` object the code expects. Calling `.get()` on a `list` raises `AttributeError: 'list' object has no attribute 'get'`.
  - **Blast radius:** `check_all()` (`dependency_monitor.py:370`) calls `check_anthropic()` **first**, then eBay RSS, then the eBay account-deletion self-check, then Stripe. Because `check_anthropic()` throws before returning, `check_all()` propagates the exception and **none of the other three checks run.** The exception is swallowed by `/health`'s generic `except` (`routes/utils.py:37-38`), so the service stays up but the **monitor is silently dead.**
  - **Notable consequence:** The eBay account-deletion self-health-check added in the last two commits (`793897d`, `989287c`) — the entire point of the most recent work — **is not actually executing in production.** It's masked by the upstream `check_anthropic` failure.
  - **Secondary issue (same function):** Even if `data.get("items")` is fixed, the deprecations.info **schema also changed**. Items are now flat (`provider`, `model_id`, `shutdown_date`, `replacement_models` at top level) — the code still reads the old nested shape (`item.get("_deprecation", {})`, `dep.get("model_name")`, `dep.get("provider")` at lines 131–146). So the Anthropic model-retirement check would parse nothing even after the crash is fixed. Doubly broken.
  - *(Findings only — not fixed, per brief.)*

- **Recent Render logs (last 7 days):** **UNVERIFIED — no access** to Render dashboard/logs this pass.

---

## 3. Billing (Stripe)

**State: fully wired in code; test-mode-verified per old notes; no automated tests; env undocumented.**

- **Four tiers** live in `routes/billing.py` `PLANS` dict (lines ~54–113):
  | Tier | Price | Valuations | Slab Guard regs | Notes |
  |------|-------|-----------|-----------------|-------|
  | `free` | $0 | 10/mo | 3 | no extra photos |
  | `pro` | $4.99/mo · $49.99/yr | unlimited | 25 | |
  | `guard` | $9.99/mo · $89.99/yr | unlimited | unlimited (−1) | + monitoring |
  | `dealer` | $24.99/mo · $239.99/yr | unlimited | unlimited (−1) | API/bulk/white-label |
- **Where gating lives:** `check_feature_access()` in `billing.py` (~line 219) — gates `valuations` and `slab_guard_registrations` against the plan limits; `-1` = unlimited; non-free plans must be `active`. Stripe price IDs are pulled from env per tier/period (`stripe_monthly_price_id` / `stripe_annual_price_id`).
- **Webhook handler** (`POST /api/billing/webhook`, `billing.py:468`) — **signature verified** when `STRIPE_WEBHOOK_SECRET` is set (warns + processes unverified if unset — a soft spot). Handles **5 events**:
  - `checkout.session.completed` → `handle_checkout_completed` → set plan `active` (from session metadata user_id/plan/period).
  - `customer.subscription.updated` → `handle_subscription_updated` → look up user by `stripe_customer_id`, update plan/status/period-end.
  - `customer.subscription.deleted` → `handle_subscription_deleted` → revert user to `free`, status `canceled`.
  - `invoice.payment_succeeded` → `handle_payment_succeeded` → log only.
  - `invoice.payment_failed` → `handle_payment_failed` → mark subscription `past_due`.
- **End-to-end test evidence:**
  - **No automated Stripe test scripts** in the repo (no `test_*stripe*.py`).
  - A manual helper exists: `.claude/skills/stripe-test/SKILL.md` (the `/stripe-test` skill).
  - `docs/sessions/CLAUDE_NOTES.txt:172` records: *"Stripe Live: Test mode — checkout, customer portal, webhooks verified"* and `:458` *"Webhook configured and tested"* — historical (≈Session 44 era), not re-verified this pass. **Live-mode validation remains Mike's separate task** (per brief).
- **Env vars — expected vs documented:** `stripe>=7.0.0` pinned in `requirements.txt`. Code **expects**: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and 6 price IDs (`STRIPE_PRO_MONTHLY_PRICE`, `STRIPE_PRO_ANNUAL_PRICE`, `STRIPE_GUARD_MONTHLY_PRICE`, `STRIPE_GUARD_ANNUAL_PRICE`, `STRIPE_DEALER_MONTHLY_PRICE`, `STRIPE_DEALER_ANNUAL_PRICE`). **None are documented** in `docs/technical/ARCHITECTURE.txt` — its env-var table lists only `EBAY_VERIFICATION_TOKEN`. (Also undocumented there: `RESEND_API_KEY`, `ADMIN_EMAIL`, `RESEND_FROM_EMAIL`, `ANTHROPIC_API_KEY`, `DATABASE_URL`, R2 creds, eBay OAuth creds.) This **violates CLAUDE.md's mandatory dependency rule #3** ("Document env vars in ARCHITECTURE.txt"). See §8.

---

## 4. Data coverage

**Mostly UNVERIFIED — no DB or admin access. What I could confirm via the public valuation endpoint:**

- **Total rows / distinct titles / rows added since 2026-03-24 / top-20 titles / tail distribution:** **UNVERIFIED.** No `DATABASE_URL`, no `psql`, and the admin/stats endpoints require auth (401). Cannot run `SELECT COUNT(*)` or aggregate.
  - *Last-known historical figure (not current):* `docs/sessions/CLAUDE_NOTES.txt:109` references a title-year backfill over **24,629 rows** (15,381 backfilled = 62.5%) at that session. Treat as a stale lower-bound, not a current count.
- **Data is live and non-trivial:** `GET /api/sales/valuation?title=Amazing+Spider-Man&issue=300&grade=9.8` returned a real blended FMV ($2,082.06), `graded_total_sales: 74`, a populated `price_curve` across grades 4.5→9.8, 365-day lookback. So the sales table is populated and queryable for at least mainstream issues.
- **Collection running or stalled?** **UNVERIFIED** — can't see row timestamps or recent-insert counts without DB/admin access.
- **Whatnot source — live or eBay-only?** **eBay-only in practice.** `routes/whatnot.py` is explicitly **content-generation only** ("No OAuth or direct API integration (Whatnot has no public API)") — it produces listing copy for sellers to paste, it does **not ingest sales.** Actual sales data comes from the **eBay Collector** extension → `ebay_sales` (per `ARCHITECTURE.txt`). `routes/sales_market.py` exposes a manual "record a sale from Whatnot extension" endpoint, but whether any rows have been recorded through it is **UNVERIFIED** (needs DB). Bottom line: for the valuation engine, the live data source is eBay.

---

## 5. Signature v2

**Confirmed from the public `GET /api/signatures/db-stats` (HTTP 200) — live production data:**

> **⚠️ CORRECTION (added after first draft).** My initial numbers here came from the public
> `GET /api/signatures/db-stats` endpoint. That endpoint reads a **stale static file**, not the
> live DB — see the "stale endpoint" finding below. The authoritative live figures (from the admin
> Signatures page → `/api/admin/signatures` → `creator_signatures` table, confirmed by Mike's
> screenshot 2026-06-06) supersede the db-stats numbers. The corrected picture follows.

- **Live creator/reference coverage (AUTHORITATIVE — admin UI, 2026-06-06):**
  - **99 creators** (≈ the planned 100 — essentially landed, not 80).
  - **203 reference images.**
  - **50 verified.**
  - Roughly **~52 creators have the full 4 reference images each; ~47 have none** (Mike's count; 52×4≈208 ≈ 203, allowing for a few with 3). So **refs uploaded ≈ 27–29 of the 57 new creators** (≈52 with images − 23 original) — about **half the new batch done**, not zero. Example: Adam Kubert (a "new" creator) shows 4 images + Verified.
- **🟡 Stale-endpoint finding:** `GET /api/signatures/db-stats` ([routes/signatures.py:844](routes/signatures.py:844)) calls `load_signature_db()`, which reads the bundled snapshot file **`signatures_db.json`** ([routes/signatures.py:26](routes/signatures.py:26)) — **not** the `creator_signatures` Postgres table. That snapshot is frozen at **80 creators / 97 images / 23-with-refs**, which is what produced my wrong first-pass §5. The live admin endpoint ([admin_routes.py:355](routes/admin_routes.py:355), reads `creator_signatures`) and the **v2 matcher** ([signature_orchestrator.py:190](routes/signature_orchestrator.py:190), also reads the live table) are correct. So **grading/matching is unaffected** — but any human or tool that trusts `db-stats` (or the legacy v1 matcher that uses the same JSON) gets a months-old picture. This endpoint is a reconciliation landmine and should either be repointed at the live table or removed.
- **Last measured accuracy:** **78.3% (18/23 artists), Session 82.** Unchanged — this is about *measurement*, not coverage. No newer cross-validation run found in code or docs; the 87% target has **not** been re-measured against the now-larger corpus. (`CLAUDE_NOTES.txt:563-565`.) Worth re-running now that ~50 creators have refs.
- **`/api/signatures/v2/match` live in user flow?** **Yes.** Wired into the grading flow at `app.html:2813` (helper `js/utils.js:340`). Registered as `signatures_v2_bp` in `wsgi.py:328`.
- **Gated/labeled?** Soft-gated, not labeled "beta":
  - Per-tier **monthly usage limit** — HTTP 429 returns `used/limit`; frontend shows "Signature ID limit reached (n/10 this month)".
  - **Confidence threshold** — section hidden unless top match `confidence ≥ 0.40`.
  - No explicit "beta/experimental" badge in the UI path I read.
- `GET /api/signatures/v2/match/stats` → 401 (needs auth); couldn't pull v2-specific corpus stats directly — live figures above are from the admin UI.

---

## 6. eBay listing

- **Fixed-price flow — last known working.** First live listing published Session 74; OAuth, R2 image proxy, KEY-ISSUE titles, AI descriptions all confirmed working in prior sessions. **TODO still lists "Test fixed-price draft listing" as unchecked** (`TODO.md:113`) — i.e. a clean publish has worked, but a draft test hasn't been re-run.
- **Auction flow — code exists, untested.** `ebay_listing.py` (lines ~288–478) supports `listing_format` FIXED_PRICE/AUCTION with `auction_duration` (DAYS_1/3/5/7/10), `start_price`, `reserve_price` (validated > start), `buy_it_now_price` (validated > reserve/start). UI toggle added Session 69. **TODO:** "Test auction listing (all field combos)" — **unchecked** (`TODO.md:114`). No evidence of a successful live auction. **UNVERIFIED in production.**
- **OAuth token refresh — implemented; live behavior UNVERIFIED.** `ebay_oauth.py`: `get_user_access_token` (~line 269) reads stored token, and if within 5 min of expiry and a `refresh_token` exists, calls `refresh_access_token` (`grant_type=refresh_token`, line 170) and upserts the new token (`COALESCE` keeps the refresh token). Logic is present and correct-looking. I cannot exercise a live refresh without a connected eBay account, so **"confirmed working" = UNVERIFIED**; code path exists.
- **Account-deletion compliance (the recent commits):** GET challenge handler present at `routes/ebay.py:49` — computes `sha256(challenge_code + EBAY_VERIFICATION_TOKEN + endpoint)`. ⚠️ **Caveat from `ARCHITECTURE.txt:88`:** eBay's portal URL was historically registered against the now-**SUSPENDED** `collectioncalc` (non-`-docker`) host and must point to the `-docker` host. The recent work targets the `-docker` endpoint; whether the eBay portal registration + token actually match in production is **UNVERIFIED** (the self-check that would catch a mismatch is currently dead — see §2).

---

## 7. Mobile (Session 90 fixes)

**All three Session 90 fixes are present in the code at HEAD** (and, by version-string inference, deployed):

- **2048px canvas resize:** `js/grading.js:1313` — `const MAX_IMAGE_DIM = 2048;`
- **EXIF orientation parser:** present in `js/app.js`, `js/grading.js`, `js/utils.js` (orientation handling).
- **Non-comic-cover validation:** `comic_extraction.py` — `is_comic_cover` in the extraction prompt (line 199) and early-return when false (`:439`).
- **Deployed?** Inferred present (HEAD == origin == version 5.6.0 in prod). Not commit-level confirmed (no Render access).
- **Mobile issues logged since Session 90?** None found — there are **no session notes after Session 90**, so nothing has been logged either way. Note that full mobile device testing **remains open** in `TODO.md:157` ("Mobile testing (full grading flow)" — unchecked). So: fixes shipped, broad device testing still pending.

---

## 8. Docs state

- **`docs/sessions/WHERE_WE_LEFT_OFF.md`** — top entry **Session 90 (Mar 24, 2026)**. Does **not** mention the May–June eBay account-deletion work (commits `793897d`/`989287c`) → docs lag the repo by the two most recent sessions.
- **`TODO.md`** — header "Updated March 24, 2026 (Session 90)". Still the live task list; P1 contains the open eBay/auction/mobile/marketplace test items noted above.
- **`docs/sessions/ROADMAP.txt`** — last updated **Feb 25, 2026 (Session 64)**. Stale (planning + historical log mix, as CLAUDE.md warns).
- **In-progress items the repo contradicts / docs drift:**
  1. **Signatures expansion HAS largely landed** (corrected §5): live DB shows **99 creators / 203 refs / 50 verified** (~half the 57 new creators have images). The drift is *the other way* — the public `/api/signatures/db-stats` endpoint serves a stale bundled `signatures_db.json` (80/97) that disagrees with the live `creator_signatures` table. Docs aren't wrong here; a legacy endpoint is.
  2. **`ARCHITECTURE.txt` env-var table is effectively empty** (only `EBAY_VERIFICATION_TOKEN`) while code depends on ~12+ env vars (Stripe×8, Resend×3, Anthropic, DB, R2, eBay OAuth). Directly contravenes **CLAUDE.md mandatory rule #3.**
  3. **Dependency monitor described as "runs on every Render health check"** (Session 90 notes) — true that it's *invoked*, but it's currently *throwing* (§2), so the described monitoring is not actually happening.

---

```
RECONCILIATION SUMMARY — 2026-06-06
Repo:        clean (in sync, local==origin/main @ 989287c), commits since Mar 24: 3; 2 uncommitted working-tree files (1 legit doc WIP, 1 .claude worktree junk)
Production:  up but DEGRADED — /health 200 (v5.6.0) yet dependency monitor is fully down (deprecations.info shape change crashes check_anthropic, aborts all checks)
Billing:     wired (4 tiers, 5 webhook events, entitlement updates) / test-mode-verified per old notes, no automated tests / env vars undocumented in ARCHITECTURE.txt
Data:        UNVERIFIED totals (no DB/admin access); valuation endpoint live & populated (ASM#300 9.8 → 74 graded sales); Whatnot is content-gen only — eBay is the real data source
Signatures:  accuracy 78.3% (18/23, Session 82, not re-measured); LIVE DB = 99 creators / 203 refs / 50 verified (~half the 57 new creators have images — expansion largely landed); v2 /match live, soft-gated (monthly limit + 0.40 confidence). NB: public /api/signatures/db-stats is STALE (static JSON snapshot: 80/97) — do not trust it.
Top 3 surprises:
  1. The dependency monitor is DEAD in prod — the exact system Session 90 built and the June commits extended (eBay account-deletion self-check) never runs; upstream deprecations.info now returns a JSON array, crashing check_anthropic before any other check executes.
  2. The /api/signatures/db-stats endpoint serves a stale static-JSON snapshot (80 creators/97 imgs) that disagrees with the live DB (99/203/50). It nearly produced a wrong "expansion didn't land" conclusion in this very report — corrected against Mike's admin-UI screenshot. The live signature expansion is in good shape; the legacy endpoint is the problem.
  3. ARCHITECTURE.txt documents only 1 env var (EBAY_VERIFICATION_TOKEN) despite ~12+ in use — a direct miss against CLAUDE.md's own mandatory dependency rule, and the Stripe webhook will process unverified if STRIPE_WEBHOOK_SECRET is unset.
```

*Findings only. No fixes applied — prioritize separately.*
