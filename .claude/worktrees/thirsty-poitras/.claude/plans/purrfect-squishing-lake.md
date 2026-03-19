# Plan: Signature ID Monthly Usage Cap (10/month)

## Context
Signature ID uses 3 sequential Opus passes per request (~$0.50-0.75 each). With 25 gradings/month and auto-sig-check after each, a single beta tester could cost $12-19/month in Opus alone. Need to cap at 10/month for free users, with auto-check counting toward that cap.

## How It Works Today
- **v2 endpoint:** `POST /api/signatures/v2/match` in `routes/signature_orchestrator.py` (line 761)
- **Auto-check:** `runSignatureCheck()` in `app.html` (line 2517) — runs after every grading, calls v2
- **Manual "ID Sigs":** `handleCollectionIdentifySignatures()` in `js/collection.js` (line 993) — calls `identifySignaturesV2()` in `js/utils.js` (line 327), which calls v2
- **No existing cap or counter** — completely unlimited right now
- Decorators: `@require_auth`, `@require_approved` — no admin exemption currently

---

## Step 1: Migration — Add sig check counter columns

**File:** `migrations/add_sig_check_cap.sql` (NEW)

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS sig_checks_this_month INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS sig_checks_reset_date TIMESTAMPTZ;
```

Same pattern as `gradings_this_month` / `gradings_reset_date`.

---

## Step 2: Backend — Cap check in v2 match endpoint

**File:** `routes/signature_orchestrator.py` (MODIFY — insert at line ~787, before image parsing)

- Query `sig_checks_this_month` + `sig_checks_reset_date` from users table
- Reset counter if new month (same logic as grading cap)
- If `sig_checks_this_month >= 10` and user is not admin → return 429 with `{ error: 'sig_limit', limit: 10, used: N, resets_at: "Apr 1" }`
- After successful match (before return), increment counter
- Admin users (`is_admin = true`) exempt

Cap value: **10/month** for free plan users.

---

## Step 3: Frontend — Auto-check handles 429 gracefully

**File:** `app.html` (MODIFY — in `runSignatureCheck()` function, line ~2552)

When the auto-check after grading gets a 429 back:
- Don't show an error — just silently skip the signature section
- Optionally show a subtle note: "Signature ID limit reached this month" in the sig section area

---

## Step 4: Frontend — Manual "ID Sigs" handles 429

**File:** `js/collection.js` (MODIFY — in `handleCollectionIdentifySignatures()`, line ~993)

When manual ID Sigs button gets a 429:
- Show toast: "You've used all 10 signature checks this month. Resets on Apr 1."

**File:** `js/utils.js` (MODIFY — in `identifySignaturesV2()`, line ~327)

Can also handle 429 at the shared API function level so both callers benefit.

---

## Files Summary

| File | Change |
|------|--------|
| `migrations/add_sig_check_cap.sql` | NEW — 2 columns on users table |
| `routes/signature_orchestrator.py` | MODIFY — cap check before Opus calls + increment after |
| `app.html` | MODIFY — `runSignatureCheck()` handles 429 gracefully |
| `js/utils.js` | MODIFY — `identifySignaturesV2()` returns structured error on 429 |
| `js/collection.js` | MODIFY — toast message on sig limit reached |

---

## Verification

1. Grade a comic as non-admin → sig auto-check runs → counter increments
2. After 10 sig checks → next grading auto-check silently skips sig section
3. Manual "ID Sigs" on collection after limit → shows toast with reset date
4. Admin user → unlimited sig checks (exempt)
5. Month rolls over → counter resets
