# R2 → img.slabworthy.com Cutover Runbook

> **Status:** DRAFT for manual execution. Mike runs every step himself and verifies before
> moving to the next. Nothing in here is auto-run, committed, or deployed by Claude.
> **Drafted:** 2026-06-15 · **Decision:** migrate R2 bucket to custom domain before July 21 soft launch.
> **Why:** the `pub-*.r2.dev` dev domain is rate-limited (~hundreds req/s → 429) and uncached;
> a custom domain adds edge caching + unblocks the ID Sigs CORS fix. See scoping report (Session ~102).

## Constants used throughout

- **OLD prefix:** `https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev`
- **NEW prefix:** `https://img.slabworthy.com` — **no trailing slash** (code does `f"{R2_PUBLIC_URL}/{path}"` in `r2_storage.py:93`)
- **Known-good object key for verify:** `sales/3699/front.jpg`
- **Bucket:** `collectioncalc-images`
- **Affected tables (all PK = `id`), single prefix, 54,539 rows total:**

| Table.column | Type | Rows |
|---|---|---|
| `creator_signatures.reference_image_url` | text | 1 |
| `collections.photos` | jsonb | 26 |
| `signature_images.image_url` | text | 203 |
| `market_sales.image_url` | text | 3,816 |
| `ebay_sales.r2_image_url` | text | 50,493 |

**No change needed:** `signature_identification_log.unknown_image_key` and
`signature_review_queue.unknown_image_key` store *relative* keys (e.g. `unknown/1772926100.jpg`) —
domain-agnostic, leave alone. There is **no hardcoded `r2.dev`** in the frontend (verified by grep),
so the DB rewrite + env flip fully covers the client.

**Tool legend:** 🟦 DBeaver (SQL) · 🟧 Cloudflare dashboard · 🟩 Render dashboard · ⬛ PowerShell

> **Global guardrail:** In DBeaver, run every UPDATE on the **read-write** connection (the
> `DATABASE_URL` one). The `DATABASE_URL_RO` connection rejects writes — a safe failure, but a
> time-waster. Confirm the active connection before Step 4.

> **Order matters:** Do NOT start Step 4 until Steps 1–3 are each verified green. Steps 1–3 are
> non-destructive and individually reversible; Step 4 is the only one that touches data, and it is
> snapshot-protected + transaction-wrapped per table.

---

## STEP 0 — Backup (non-negotiable, first)

Two layers: a file-level dump (belt) + in-DB column snapshots (suspenders & fast rollback).

### 0a. File-level dump ⬛ PowerShell
Grab the **External Database URL** (read-write) from Render → Postgres → Connect → External.
Paste it inline below (do not paste into chat/logs).

```powershell
New-Item -ItemType Directory -Force "C:\Users\mberr\backups" | Out-Null
$bk = "C:\Users\mberr\backups\sw_r2_premigration_20260615.dump"
pg_dump "<PASTE-READWRITE-DATABASE-URL>" `
  -t public.ebay_sales -t public.market_sales -t public.signature_images `
  -t public.creator_signatures -t public.collections `
  -Fc -f $bk
```

**Verify before proceeding:**
```powershell
pg_restore --list $bk | Select-String "TABLE DATA"   # must list all 5 tables
(Get-Item $bk).Length                                 # must be > 0, non-trivial
```
✅ Proceed only if all 5 `TABLE DATA` lines appear and the file is non-empty.
⚠️ **Failure mode:** `pg_dump` major version must match the server (Render is PG 16). On
`server version mismatch`, use a matching client. A tiny dump = wrong DB/permissions — check the list.

### 0b. In-DB column snapshots 🟦 DBeaver (read-write) — fast rollback
```sql
CREATE TABLE _bak_creator_signatures_20260615 AS SELECT id, reference_image_url FROM creator_signatures;
CREATE TABLE _bak_collections_20260615        AS SELECT id, photos              FROM collections;
CREATE TABLE _bak_signature_images_20260615   AS SELECT id, image_url           FROM signature_images;
CREATE TABLE _bak_market_sales_20260615       AS SELECT id, image_url           FROM market_sales;
CREATE TABLE _bak_ebay_sales_20260615         AS SELECT id, r2_image_url        FROM ebay_sales;
```
**Verify snapshot counts match live:**
```sql
SELECT 'creator_signatures' t, count(*) FROM _bak_creator_signatures_20260615
UNION ALL SELECT 'collections',        count(*) FROM _bak_collections_20260615
UNION ALL SELECT 'signature_images',   count(*) FROM _bak_signature_images_20260615
UNION ALL SELECT 'market_sales',       count(*) FROM _bak_market_sales_20260615
UNION ALL SELECT 'ebay_sales',         count(*) FROM _bak_ebay_sales_20260615;
```
**Rollback for this step:** `DROP TABLE _bak_*` — only after the whole migration succeeds (Step 6).

---

## STEP 1 — Attach img.slabworthy.com to the bucket 🟧 Cloudflare

1. Cloudflare → **R2** → bucket `collectioncalc-images` → **Settings** → **Custom Domains** → **Add**.
2. Enter `img.slabworthy.com` → **Continue** → review the auto-created CNAME → **Connect Domain**.
3. Status **Initializing → Active** in a few minutes (refresh). SSL auto-provisions; "Active" implies
   the edge cert is issued. **r2.dev stays enabled the whole time.**

**VERIFY (before anything else):** ⬛ PowerShell
```powershell
curl.exe -I https://img.slabworthy.com/sales/3699/front.jpg
```
✅ Expect `HTTP/2 200` and `content-type: image/jpeg`.
⚠️ **Failure modes:** stuck *Initializing* → **… → Retry connection**, check no pre-existing `img`
DNS record conflicts. `525/526` → cert still provisioning, wait and re-curl. `404` → wrong key;
re-pull with `SELECT image_url FROM market_sales LIMIT 1;`.

**Rollback:** Custom Domains → **… → Remove domain**. Zero user impact (r2.dev still serving).

---

## STEP 2 — Bucket CORS policy (also fixes ID Sigs) 🟧 Cloudflare

> **First, save the current policy for rollback:** R2 → bucket → Settings → **CORS Policy** → copy
> existing contents to a scratch file. (Likely empty/missing — that's the bug.)

Set CORS policy to:
```json
[
  {
    "AllowedOrigins": ["https://slabworthy.com", "https://www.slabworthy.com"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```
> Add your Cloudflare Pages preview origin (`https://<branch>.collectioncalc.pages.dev`) only if you
> test ID Sigs from preview deployments. Path-agnostic — covers both r2.dev and img.slabworthy.com.

**VERIFY:** ⬛ PowerShell
```powershell
curl.exe -I -H "Origin: https://slabworthy.com" https://img.slabworthy.com/sales/3699/front.jpg
```
✅ Expect header `access-control-allow-origin: https://slabworthy.com`.

⚠️ **Honest CORS scope:** CORS headers only matter for JS `fetch()`/XHR — that's the **ID Sigs**
client-side fetch. Comic-cover `<img>` tags do **not** need CORS (browsers render cross-origin images
fine). So this step fixes the **ID Sigs CORS half**; the **broken collection covers** were the
r2.dev 503/rate-limit half, fixed by the custom domain + edge cache (Steps 1/3/4), not by CORS. If a
cover still 404s after cutover, that row points at an object missing from the bucket — a pre-existing
data gap, not something this migration creates.

**Rollback:** paste the saved prior policy back (or clear it).

---

## STEP 3 — Flip R2_PUBLIC_URL on Render 🟩 Render

1. Render → `collectioncalc-docker` → **Environment** → set
   `R2_PUBLIC_URL = https://img.slabworthy.com` — **no trailing slash**.
   (If the var doesn't exist, it was defaulting to the pub-… URL in code — add it now.)
2. Save → triggers a redeploy. **Render auto-deploy is unreliable** (per CLAUDE.md) — confirm in
   **Events** that a deploy started; if not, **Manual Deploy → Deploy latest commit**.

New uploads now write `img.slabworthy.com` URLs; existing rows still resolve on r2.dev → **no gap**.

**VERIFY:** after deploy is live, run one real upload through the app and inspect the stored URL —
should start with `https://img.slabworthy.com/`. Or `curl https://collectioncalc-docker.onrender.com/health`
to confirm the deploy, then check the next-written row.
⚠️ **Failure mode:** trailing slash → `img.slabworthy.com//sales/...` (double slash). Fix and redeploy.

**Rollback:** set `R2_PUBLIC_URL` back to `https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev`, redeploy.

---

## STEP 4 — Data rewrite 🟦 DBeaver (read-write) — run AFTER 1–3 verified

For every table: run the BEFORE count, then the transaction, check AFTER = 0 **before** `COMMIT`.
If anything looks off, `ROLLBACK`. Smallest first to prove the pattern.

### 4.1 — creator_signatures (text, expect 1)
```sql
SELECT count(*) FROM creator_signatures WHERE reference_image_url LIKE 'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';  -- expect 1
BEGIN;
UPDATE creator_signatures
SET reference_image_url = REPLACE(reference_image_url,
  'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev', 'https://img.slabworthy.com')
WHERE reference_image_url LIKE 'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';
SELECT count(*) FROM creator_signatures WHERE reference_image_url LIKE 'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';  -- expect 0
COMMIT;  -- ROLLBACK if after-count <> 0
```

### 4.2 — collections (jsonb, expect 26) — different pattern, verify carefully
```sql
SELECT count(*) FROM collections WHERE photos::text LIKE '%https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';  -- expect 26
BEGIN;
UPDATE collections
SET photos = REPLACE(photos::text,
  'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev', 'https://img.slabworthy.com')::jsonb
WHERE photos::text LIKE '%https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';
SELECT count(*) FROM collections WHERE photos::text LIKE '%https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';  -- expect 0
SELECT id, photos FROM collections WHERE photos::text LIKE '%img.slabworthy.com%' LIMIT 2;  -- sanity: valid JSON, swapped
COMMIT;
```
⚠️ The `::jsonb` cast errors if a value isn't valid JSON — at 26 rows the sanity SELECT confirms a
clean round-trip. On error you're still in the transaction → `ROLLBACK`, nothing lost.

### 4.3 — signature_images (text, expect 203)
```sql
SELECT count(*) FROM signature_images WHERE image_url LIKE 'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';  -- expect 203
BEGIN;
UPDATE signature_images
SET image_url = REPLACE(image_url,
  'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev', 'https://img.slabworthy.com')
WHERE image_url LIKE 'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';
SELECT count(*) FROM signature_images WHERE image_url LIKE 'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';  -- expect 0
COMMIT;
```

### 4.4 — market_sales (text, expect 3,816)
```sql
SELECT count(*) FROM market_sales WHERE image_url LIKE 'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';  -- expect 3816
BEGIN;
UPDATE market_sales
SET image_url = REPLACE(image_url,
  'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev', 'https://img.slabworthy.com')
WHERE image_url LIKE 'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';
SELECT count(*) FROM market_sales WHERE image_url LIKE 'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';  -- expect 0
COMMIT;
```

### 4.5 — ebay_sales (text, expect 50,493) — the big one, last
```sql
SELECT count(*) FROM ebay_sales WHERE r2_image_url LIKE 'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';  -- expect 50493
BEGIN;
UPDATE ebay_sales
SET r2_image_url = REPLACE(r2_image_url,
  'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev', 'https://img.slabworthy.com')
WHERE r2_image_url LIKE 'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';
SELECT count(*) FROM ebay_sales WHERE r2_image_url LIKE 'https://pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';  -- expect 0
COMMIT;
```
Still a small write for Postgres (seconds). If DBeaver's grid fetch-limit/timeout trips, raise the
statement timeout or run outside a fetch-limited result grid.

**Rollback (per table) from snapshot:**
```sql
UPDATE ebay_sales e SET r2_image_url = b.r2_image_url
FROM _bak_ebay_sales_20260615 b
WHERE e.id = b.id AND e.r2_image_url IS DISTINCT FROM b.r2_image_url;
```
(Same shape for the other four tables/columns.) Snapshots only revert rows that existed at Step 0;
rows created during the window already carry the correct new URL from Step 3 — correct, not a gap.

---

## STEP 5 — Post-cutover verification

1. 🟧/browser: hard-refresh the **collection page** (Ctrl-F5) → covers load from `img.slabworthy.com`.
   DevTools → Network → image requests show the new host and `200`.
2. Run **ID Sigs** end-to-end → client-side `fetch()` succeeds, no CORS error in console.
3. ⬛ Spot-check rewritten URLs resolve:
```powershell
curl.exe -I https://img.slabworthy.com/sales/3699/front.jpg
# grab an ebay key: SELECT r2_image_url FROM ebay_sales LIMIT 1;  then:
curl.exe -I "<paste-an-img.slabworthy.com-ebay-url>"
```
4. ⬛/🟦 Confirm zero stragglers anywhere (should total 0):
```sql
SELECT 'ebay_sales' t, count(*) n FROM ebay_sales WHERE r2_image_url LIKE '%pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%'
UNION ALL SELECT 'market_sales', count(*) FROM market_sales WHERE image_url LIKE '%pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%'
UNION ALL SELECT 'signature_images', count(*) FROM signature_images WHERE image_url LIKE '%pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%'
UNION ALL SELECT 'creator_signatures', count(*) FROM creator_signatures WHERE reference_image_url LIKE '%pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%'
UNION ALL SELECT 'collections', count(*) FROM collections WHERE photos::text LIKE '%pub-c8c9fda2fea943719a90e664c2aba0e3.r2.dev%';
```
✅ All zero.

⚠️ **ID Sigs beyond CORS?** None code-side — no hardcoded r2.dev in the frontend (verified); ID Sigs
fetches the stored URL, now `img.slabworthy.com`. CORS policy (Step 2) + rewrite (Step 4) is the
complete ID Sigs fix. Residual risk = the "missing object in bucket" case: if a cover 404s on the new
domain, `curl -I` the same key on r2.dev; a 404 there too means the object was never uploaded
(pre-existing data gap, unrelated to this migration).

---

## STEP 6 — Leave r2.dev as the safety net; clean up later

- **Leave r2.dev enabled now.** No rows reference it anymore; it is the instant fallback for the first days.
- **Later, once confident (separate session):**
  - 🟧 R2 → bucket → Settings → Public Development URL → **Disable** (only after days of clean
    operation, and only if you also want WAF/Access lockdown — otherwise leaving it costs nothing).
  - 🟦 `DROP TABLE _bak_creator_signatures_20260615, _bak_collections_20260615, _bak_signature_images_20260615, _bak_market_sales_20260615, _bak_ebay_sales_20260615;`
  - ⬛ Keep the `.dump` file until a week of clean image serving is confirmed.

---

## One-screen rollback summary

| Step | Revert action | Tool |
|---|---|---|
| 1 | Remove custom domain (r2.dev still serves) | 🟧 |
| 2 | Paste prior CORS policy back | 🟧 |
| 3 | `R2_PUBLIC_URL` → old pub-… value, redeploy | 🟩 |
| 4 | `UPDATE … FROM _bak_*` per table | 🟦 |
| any | Full restore: `pg_restore` from the `.dump` | ⬛ |
