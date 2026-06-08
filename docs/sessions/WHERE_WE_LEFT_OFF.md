# Where We Left Off - Jun 8, 2026

## Session 99 (Jun 8, 2026) — Batch 7: decouple quality gates + surface real errors

**STATUS: code complete, verified, NOT committed.** Files: `routes/fingerprint_utils.py`,
`routes/grading.py`, `app.html`. Mike runs all git/deploy/purge (L-SW-2026-001).

**Root cause recap (DO's prior trace):** Giant-Size X-Men #1 = a 394×572 eBay cover hit the
pre-vision quality gate (`GRADE_QUALITY_MIN_DIMENSION=400`) and was rejected by 6px — vision model
never called — and the frontend showed a generic "Could not identify comic automatically." Confirmed
from `request_logs`: most recent `/api/extract` = HTTP 400 "Photo is too small (394×572px)".

**Task 1 — decouple the gate by purpose (🔴).** `check_photo_quality_base64(base64_data, purpose='grade')`
now takes a purpose: `extract` uses a lenient floor (`EXTRACT_QUALITY_MIN_DIMENSION=250`), `grade`
keeps the strict `400`. Also returns measured `width`/`height`. `/api/extract` passes `purpose='extract'`;
`/api/messages` + `/api/grade` pass `purpose='grade'`. Verified with a real 394×572 JPEG: **extract
ok=True, grade ok=False** with message "This photo's too small for an accurate grade (394×572px)…"; a
140×200 image still fails extract. So a legible eBay cover now identifies the book but is correctly
held back from grading.

**Task 2 — honest grade-time UX (🟡).** When `/api/grade` returns 400 `quality_fail`, app.html now shows
an amber "we identified the comic, but need a larger photo to grade it accurately" state (with the book
title from `extractedData` + the backend's tip), instead of a red "Error/Failed". Does NOT grade at
unreliable quality. Check lives at grade-time using the gate's dimension data (grade endpoints now also
return `width`/`height`).

**Task 3 — stop swallowing the real error (🟡).** `extractComicData` previously threw on `!response.ok`
before reading the body, so quality rejections showed the generic line. Now it reads the body first and,
when `quality_issue`/`quality_fail` is set, surfaces the backend's real `quality_message` + `tip`.
(Same swallowed-error pattern fixed in signup/Batch 6.)

**Bonus fix (from review):** the grade flow read the Response body twice on a non-`monthly_limit` 429
(body can only be consumed once → real error lost). Restructured to read the body ONCE and reuse it
across the limit/quality/error/success branches.

**Verification:** real-image gate test (above); `node` syntax check of app.html inline scripts (0
errors); `py_compile` clean. code-reviewer agent: the double-read was the one critical item — **fixed**;
scopes/field-names/floors confirmed correct. Noted latent (accepted, not active): backend quality
strings are interpolated into innerHTML — currently server-static (dimensions + fixed tips), no
user-input path; revisit if message text ever includes user content.

### Open / watch after deploy (Batch 7)
- **Purge IS load-bearing** — `app.html` changed (Tasks 2 & 3). Deploy (backend: fingerprint_utils,
  grading) + purge (frontend).
- Headline live check: re-run the 394px Giant-Size X-Men #1 cover → should now **identify** (reach the
  vision model, return a title); a genuinely small cover → identifies, then at grade shows the honest
  "too small to grade — upload larger" message; a true quality reject → shows the precise backend
  message + tip, not the generic line.

## Session 98 (Jun 8, 2026) — Batch 5: valuation date-filter fix + confidence-labeling audit

**STATUS: code complete, verified read-only against prod corpus, NOT committed.** One file:
`routes/sales_valuation.py`. Mike runs all git/deploy (L-SW-2026-001).

**RECONCILIATION (corrects an earlier overstatement of mine).** The stall was REAL — the audit was
right. Capture is MANUAL (Mike gathers by hand): created_at histogram shows 24,629 rows (Feb) + 13,681
(Mar), then **ZERO in Apr and May**, then a **42-row revival on Jun 6** (Mike resumed this weekend). My
first-pass claim that "capture is current" was wrong — I over-read `max(created_at)=2026-06-06` as
healthy capture when it's a tiny revival after a real ~2-month gap. The audit's OTHER findings ALSO hold
against current data: shallow distribution = **79.1% single-sale, 95.5% <5 comps** (audit said 75% /
94.5% — confirmed, slightly worse); **Whatnot-dark** = market_sales is **19.7%** of the 47,750 corpus.
So the audit is trustworthy; the only "discrepancy" was timing (audit = pre-revival, my read = post-).

**Task 1 — date filter `created_at` → sale date (6 queries) + fmv window 90→180.** All six window
filters now use `COALESCE(sale_date, created_at)` (ebay) / `COALESCE(sold_at, created_at)` (market) —
4 in `/api/sales/valuation`, **2 in `/api/sales/fmv`** (brief said "4"; there were 6). COALESCE =
documented explicit NULL fallback. Plus the fmv default lookback widened **90→180 days** (Mike's call):
sale-date-filtered 90d is too sparse; 180d restores healthy samples without reaching stale pricing.
Before/after comp counts (read-only prod RO replica):

| key | 90d OLD | 90d NEW | **180d NEW** | 365d NEW |
|---|---|---|---|---|
| X-Men #1 | 172 | 106 | **592** | 670 |
| Batman #1 | 159 | 102 | **627** | 737 |
| Amazing Spider-Man #300 | 51 | 42 | **187** | 210 |
| Incredible Hulk #181 | 42 | 23 | **134** | 145 |

(Why the fix matters: the Feb–Mar bulk has created_at within ~90d but sale_dates spread over time, so the
old created_at-90d window counts stale sales as "recent"; sale-date-90d is honest but sparse → 180d is
the sweet spot. And once the Feb–Mar captures age past 90d created_at with capture stalled, the OLD
filter would serve fallback for the WHOLE corpus — the sale-date filter is what keeps real comps flowing.)

**Task 2 — confidence-labeling audit (investigate + low-risk wiring).** Findings: **in-app is fine** —
`/api/sales/valuation` returns `confidence` (exact_count/total_graded → high/medium/low/very_low),
app.html maps `very_low→"Limited"`, and a single-sale key resolves to very_low and always shows the
label alongside any point estimate (+ `estimated` note on the fallback). **Gap = the Whatnot extension
via `/api/sales/fmv`**, which returned **no confidence field at all** — just tier point-estimates (a tier
`avg` can be one sale, rounded to the cent) with a bare count → false precision. **Low-risk wiring fix
(done):** `/api/sales/fmv` now returns `confidence` / `fmv_sample_size` / `low_confidence`, computed from
the count of sales in the tier the FMV was actually priced from (thresholds 10/5/2), on both the main and
no-sales-fallback returns. Verified on real tier counts: X-Men#1@9.4 (16)→high, Batman#1@9.4 (6)→medium,
Hulk#181@9.4 (4)→low, a real 1-sale key→very_low. **FLAGGED for Mike (NOT built — bigger):** the Whatnot
overlay still has to *render* this new signal (a "Limited data" badge); that's an extension UI change +
republish, his call.

**Verification:** read-only harness against prod RO replica (`DATABASE_URL_RO` from `.env`, no writes);
code-reviewer agent — **no critical/important blocking issues** (COALESCE columns match SELECTs, vars
initialized, `used_tier=None` safe, valuation confidence untouched). Reviewer flag (out of scope, NOT
touched per brief): future-dated `sale_date` rows now pass the window — best fixed with a `sale_date <=
NOW()` guard in the eBay scraper at ingest, not here.

**Out of scope / untouched:** capture pipeline, valuation math, sales-table writes.

### Open / watch after deploy (Batch 5)
- **Purge: NOT load-bearing** — backend-only (`routes/sales_valuation.py`); no `js/`/frontend change.
  Render deploy only.
- Headline live check post-deploy: value a well-covered key (X-Men #1 / Batman #1) — real FMV +
  confidence band; fmv now uses a 180-day window.
- **Batch 5B (approved by Mike, separate — extension code + republish):** (1) Whatnot overlay renders the
  new `low_confidence`/`confidence` signal as a "Limited data" badge; (2) ingest-time `sale_date <= NOW()`
  guard in the eBay scraper (future-dated rows now pass the sale-date window).
- Bigger picture: capture is manual and currently only barely revived (42 rows Jun 6); the date-filter
  fix uses correct semantics but does NOT substitute for resuming real capture.

## Session 97 (Jun 8, 2026) — Batch 6: collapse new-user double email-confirm + dead-code cleanup

**STATUS: code complete, verified, NOT committed.** Mike runs commit/push/deploy. Files: `auth.py`,
`login.html` (Batch 6); plus `slab_premium_analysis.py` **deleted** (separate cleanup, staged).

**Cleanup (pre-Batch-6).** Deleted orphaned `slab_premium_analysis.py` — standalone research script
built entirely on eBay's decommissioned Finding API (`findCompletedItems`, dead since 2026-02-05).
Nothing imports it (the live `search_ebay_sold` in `ebay_valuation.py` is a different function). See
`docs/sessions/EBAY_API_SOLD_DATA_INVESTIGATION_2026-06-08.md`. Stale doc ref left at
`docs/technical/ARCHITECTURE.txt:122` (env-var table) — flagged, not yet fixed.

**Investigation (prior turns).** Mapped the full new-user flow: a beta-code stranger hits TWO gates —
beta code → email verification — then auto-login (beta code auto-approves, so the admin-approval gate
is dormant). The "verify twice" friction is **cross-funnel**: a waitlist person confirms their email to
join the list (`waitlist.verified`), then verifies the SAME email again at signup. Verification-email
non-delivery (mikeberry+5) traced to the send path being code-identical to working emails → Resend-side,
not our code; and the send result was being silently discarded.

**Task 1 — pre-verify confirmed-waitlist emails (🔴).** `signup()` now calls `_is_waitlist_confirmed(email)`
(SELECT `verified` FROM waitlist by normalized email, **fails closed**). If confirmed: user created
`email_verified=TRUE`, no verification token stored, **no second email**, JWT returned → frontend
auto-logs-in. ⚠️ **SECURITY CAVEAT (documented in code, [auth.py](../../auth.py) `_is_waitlist_confirmed`):**
email-match trusts a PAST click ("someone controlled this inbox once"), not "this signer controls it now"
— residual email-squatting risk, bounded in beta by the beta-code wall + password-reset recovery.
**REVISIT before public launch** when the beta wall comes down (consider a signed continuity token minted
by the waitlist-confirm click). I surfaced this fork to Mike; proceeded with the brief's primary
email-match approach per his stated risk tolerance.

**Task 2 — auto-approve waitlist signups (🟡).** `auto_approve = bool(beta_code) or waitlist_confirmed`.
Beta-code wall and admin-approval machinery left intact (out of scope). Confirmed-waitlist signup lands
`is_approved=TRUE`, skips the pending panel.

**Task 3 — fix swallowed send result (🔴).** `signup()` now checks `send_verification_email()`'s return.
On failure: returns `email_send_failed=True` + honest message (account still created); frontend shows a
"Couldn't send your email" state with a **Resend** button (hits existing `/api/auth/resend-verification`,
which now also surfaces failures). Failures persisted to a new `email_send_failures` table (lazy-created
once/process) + `logger.error` instead of bare `print`.

**Task 4 — pre-fill + lock email for waitlist invites (🟡, Mike add-on).** The Create Account form asked
invited users to retype the email they'd already confirmed (felt like "they forgot me"; let them type a
DIFFERENT address than the one verified). **Plumbing required** — the verified email wasn't available to
the form (beta codes aren't email-bound; `/api/beta/validate` returned no email). Fix: waitlist-invite
codes already store `note = "Waitlist invite: <email>"` (`/api/admin/waitlist/invite`), so
`validate_beta_code` now parses that and returns `invite_email` + a **server-computed** `email_verified`
(= `_is_waitlist_confirmed`, can't be spoofed client-side). `login.html` pre-fills + locks (`readOnly`)
`#signupEmail`, shows a "✓ Verified" badge (only when server says so), with a **"change it" escape hatch**
(opting out drops pre-verify — correct, it's no longer the confirmed address). Field kept (it's account
identity), not removed. ⚠️ Privacy fix from review: `validate_beta_code` **no longer returns the raw
`note`** (unauthenticated endpoint; note holds the invited email / internal admin remarks). Note wording
gated on `email_verified` so an invited-but-unconfirmed email doesn't falsely read "you confirmed."
Optional follow-up (NOT done): add `?code=...` to the invite link ([admin_routes.py:925](../../routes/admin_routes.py)) so users don't hand-type the code.

**Verification.** Throwaway harness exercised all four signup paths (confirmed-waitlist → no email +
auto-login + approved; unconfirmed-waitlist → normal verify; never-waitlisted+beta → normal verify +
approved; send-fail → honest flag, no token) — all assertions passed. code-reviewer agent: **no critical
bugs**; INSERT placeholders aligned, fails-closed correct, no auto-verify-without-waitlist path, XSS-safe
(textContent). Addressed its one actionable item (moved per-call `CREATE TABLE` behind a once/process
guard).

### Open / watch after deploy (Batch 6)
- **Purge IS load-bearing** — `login.html` (frontend signup flow) changed → Cloudflare cache purge required.
- Post-deploy check: sign up a **fresh, copy-pasted** confirmed-waitlist test email → should NOT re-verify,
  lands in app approved. Then a never-waitlisted email → SHOULD still get a verification email.
- New `email_send_failures` table is lazy-created on first failure; no migration wired. If you want it
  pre-created, add to a startup migration later.
- Still pending (separate batches, NOT this one): Resend monitoring/webhook in `dependency_monitor.py`;
  public-launch gating decision (beta wall + admin gate); ARCHITECTURE.txt:122 stale ref.

## Session 96 (Jun 7, 2026) — Batch 4C: signature 413 chain + grade CGC snap + calibration tooling

Five tasks. Protocol: reproduce → fix → verify → verification agent. **SHIPPED** — Mike committed +
pushed + deployed (Render + Cloudflare purge) + field-verified live 2026-06-07: 413 gone (/v2/match
returns 200), eBay 401 gone on load, grade displays on-scale. HEAD has moved past `8a9e3ae`. Files:
`js/utils.js`, `app.html`, `js/grading.js`, `routes/grading.py`, `routes/signature_orchestrator.py`,
`wsgi.py`, `js/app.js`, `test_haiku_vs_sonnet.py`, `test_grading_consistency.py`.

### ⚠️ Open for tomorrow (from Mike's live testing 2026-06-07 — do NOT act tonight)
1. **Spinner orphan on `matched:false`.** `/v2/match` returns 200 with a correct no-match (Part A
   floor working), but the client only handles error + confident-match — the successful-no-match case
   orphans the "Checking for signatures…" spinner. Fix: on `matched:false`, render the `message`
   field and clear the checking state. (app.html `runSignatureCheck` + js/utils.js `identifySignaturesV2`
   / collection.js consumer.)
2. **`raw_grade` not observed in the live `/api/grade` response** (Mike saw only `grade:7.5`). I added
   `result['raw_grade']` in `routes/grading.py` before `jsonify(result)` — VERIFY tomorrow where it
   actually lands (response field name / serialization / whether the inspected payload was the grade
   object). Calibration (task 4) needs raw QUERYABLE → if it's not a DB column, **adding one is the
   prerequisite** (this is the gap, not the response field).
3. **Signature MATCHING never actually tested this weekend.** All of Mike's test comics have PRINTED
   credits, not hand-signed autographs, so only the REJECTION/no-match path was validated. The
   confident-match path is unverified. Mike has a reframe coming tomorrow.

**Task 1 — signature match 413 (🔴 root cause found).** Client posted the cover base64 as a multipart
TEXT field (`formData.append('image', base64)`); Werkzeug 3.1.3 caps non-file form fields at
`max_form_memory_size` = **500 KB** and raises 413 during form parsing — AFTER the entitlement gate
(matches "gate passed, died on body size"). Server already reads `request.files["image"]` (a file), so
the field upload was also contract-wrong. Verified: 2 MB field @500 KB → 413; file part @500 KB → 200.
Fix: (a) `resizeBase64ToJpegBlob()` in `utils.js` resizes to 1568 px long-edge (Anthropic's vision cap
— no model-visible loss) and returns a JPEG **Blob**; `identifySignaturesV2` + app.html
`runSignatureCheck` append it as a FILE part. (b) `match_signature` accepts a `request.form["image"]`
base64 fallback too. (c) `wsgi.py` sets `MAX_FORM_MEMORY_SIZE=25 MB` as a transitional safety net
(does NOT touch `MAX_CONTENT_LENGTH`, so the JSON multi-image `/api/grade` path is uncapped). Prefer-
shrink honored: full-res cover base64 (~MBs) → ~200–400 KB file.

**Task 2 — orphan spinner (🔴, pairs with 1).** `runSignatureCheck` now wraps the fetch in an
AbortController **120 s timeout** and resolves the "Checking for signatures…" state on EVERY outcome:
403 → hide silently; other non-OK (413/5xx) → "Signature check unavailable"; catch (network/timeout)
→ same. `collection.js` already cleared via `finally` (unchanged). Closes the Friday "flicker" item too.

**Task 3 — grade CGC snap (🟡, "Defensive + store raw" per Mike).** KEY FINDING: the LIVE app.html
path (`/api/grade` → `grading_engine.compute_grade` → `snap_to_cgc_grade`) ALREADY snaps and retains
`raw_score`; the override's catch shows Error (no fallback), and grading.js's `/api/messages`
comprehensive grade is overridden/unused by app.html. So no current live path can show 7.6 (the
5-book grades 7.5/6.0/8.0/5.0 confirm). RESOLVED: the 7.6 was Mike's typo — a re-run displayed 7.5;
production snapping confirmed working, drift hypothesis dead, repo read was correct. Final shape
per Mike: (a) `api_grade` re-snaps `final_grade` via the canonical `snap_to_cgc_grade` (defensive
belt-and-suspenders guard — kept), sets `raw_grade` = unsnapped weighted avg, logs both — the
raw retention has real value for task-4 calibration. (b) the dead grading.js `/api/messages`
comprehensive-grade path was DELETED (replaced with a no-op stub that points to /api/grade), NOT
snapped client-side — confirmed app.html overrides `generateGradeReport` and nothing executes the
stub's body (the step-skip caller at the old line 2050 resolves to the override). No duplicated
grade list anywhere; valuation consumes the snapped `final_grade` (app.html + grading.js paths).
(c) app.html `saveToCollection` sends `raw_grade`. Verified snap: 7.6→7.5, 7.74→7.5, 8.1→8.0,
7.75→8.0 (ties round UP), 0.7→0.5; Python↔JS parity confirmed. NOTE: raw is currently retained via
server LOG + response + save payload; DB persistence of `raw_grade` needs a column (follow-up — not
done, to avoid an unscoped migration).

**Task 4 — calibration tooling + protocol proposal (🟡, measure-don't-fix).** `test_haiku_vs_sonnet.py`
and `test_grading_consistency.py` moved off the retired `claude-sonnet-4-20250514` onto `models.py`
`get_model()` tiers (single source of truth — no future retired-string drift). No prompt changes.
**Proposed measurement protocol for the Sonnet-4.6 grade-lean hypothesis (Mike's call to run):**
  1. Priors = grades already stored in the collection DB (NOT memory). Pull N≥20 books with a stored
     grade + their 4 photos (R2 URLs).
  2. Re-grade each on the current `sonnet` tier (4.6) via `/api/grade` (or the pinned script), 3 runs
     each, recording BOTH snapped `final_grade` and `raw_grade` (raw avoids snap-quantization masking
     the lean).
  3. Report delta distribution: `raw_grade − stored_prior` per book — mean, median, stdev, histogram.
     A consistent +0.3..+0.7 mean across the upright control set ⇒ confirms the ~half-step lean.
  4. THEN (separate decision) calibrate via a prompt nudge or a post-hoc offset; re-measure.

**Task 5 — eBay 401 on load (🟢).** `checkEbayConnection` (`js/app.js`) called `/api/ebay/status`
(which is `@require_auth`) with no token → 401 on every load. Now skips when no `cc_token` and sends
`Authorization: Bearer` when present.

### Verification
- Task 1: Flask/Werkzeug 3.1.3 test — field @500 KB → 413 (repro), field @25 MB → 200 (safety net),
  file part @500 KB → 200 (primary fix bypasses the limit). py_compile + `node --check` all green.
- Task 3: `snap_to_cgc_grade` unit cases + JS parity (above).
- Tasks 2/5: client-side, reviewed (no browser/API here); 4: scripts compile, retired string gone.
- Verification agent (code-reviewer): no critical/important regressions. Latent note (resize assumes
  JPEG bare-base64 — true for all callers; clarified in docstring). Pre-existing (NOT this batch):
  `parse_multi_run_responses` bare `json.loads` → one bad pass 500s the whole multi-run (no partial
  fallback); worth a separate fix.

### Deploy / watch list for Mike
- **Cloudflare Pages purge is LOAD-BEARING:** `js/utils.js`, `js/grading.js`, `js/app.js`, `app.html`
  all changed — frontend must redeploy + cache purge or the 413/spinner/snap/eBay fixes won't ship.
- Render backend: `wsgi.py` (form limit), `routes/grading.py`, `routes/signature_orchestrator.py`.
- Correction to Part B note: app.html DOES use `/api/grade` (its inline override) — `/api/grade` is
  NOT dead. (Part B's "dead" note was from grepping only `js/`, missing app.html's inline script.)
- Post-deploy watch: real sig-check on the failing covers (Amethyst/Micronauts/Invaders) → 200, not
  413; grade displays an on-scale number; no `/api/ebay/status` 401 in console on load.
- Follow-ups surfaced (NOT this batch): persist `raw_grade` to DB (column); `parse_multi_run_responses`
  partial-failure handling; `/api/grade` dead-code cleanup is moot (it's live).

---

## Session 95 (Jun 7, 2026) — Batch 4 Part B: grading-input orientation pipeline

Items 1+2 of Batch 4. Protocol: reproduce → fix → verify → verification agent → STOP (NOT
committed — awaiting Mike). Files: `comic_extraction.py`, `routes/grading.py`, `js/grading.js`
(+ this notes file and the Part A `(c)` doc note still staged, all ride one commit).

**Item 1 — per-photo grading-input normalization (server-side, authoritative).** Grading uses 4
photos: front/spine/back (portrait when correct) + centerfold (legitimately LANDSCAPE — two-page
spread). Repro confirmed: `extract_from_base64` hardcoded `assume_portrait=True` (would force-rotate
a landscape centerfold to portrait), and `/api/messages` (spine/back/centerfold, one image per call)
did ZERO server-side normalization. Fix: new `assume_portrait_for(photo_type)` +
`normalize_for_photo_type()` in `comic_extraction.py` — policy in ONE place: centerfold/center/interior
→ EXIF-only, everything else (incl. unknown) → assume portrait. `photo_type` threaded from the
frontend through `/api/extract` (default `'front'`) and `/api/messages` (popped before forwarding to
Anthropic; absent → skip, preserving the follow-up-chat caller). Backend-first deploy is safe: old JS
sends no `photo_type` → messages-path normalization simply no-ops (never force-rotates an unlabeled
centerfold). Frontend (`js/grading.js`) now sends `photo_type` for all 4 steps — needs a Cloudflare
Pages deploy for full effect.

**Item 2 — 180° low-confidence extraction fallback (server-side).** Repro: a 180° flip is
dimensionally identical, so the dimension-based heuristic can NEVER catch it. Fix: `extract_from_base64`
runs one pass (`_run_vision_pass`); if low-confidence (`_extraction_low_confidence`: unparseable /
model-flagged is_upside_down / not-a-cover / no-title) it re-reads ONCE on a 180°-rotated copy and
keeps the higher-scoring pass (`_extraction_score`; ties keep pass 1). At most 2 vision calls. Every
retry logged `[VISION CALL #2 — doubled cost]` so the doubled cost is visible. Server is now
authoritative on orientation: the chosen result ALWAYS returns `is_upside_down=False` (pass-2 win sets
`orientation_corrected='180'`), so the grading.js client never re-rotates on top of the server.

### Verification
- Repro harness (real `normalize_orientation_b64`): centerfold force-rotated under old behavior;
  preserved under EXIF-only; 180° flip dimensionally invisible.
- Verify harness drove the REAL `extract_from_base64` with `_run_vision_pass` monkeypatched to scripted
  passes: no-retry on good pass1 (1 call); retry on each low-confidence reason (2 calls, never more);
  better pass wins; not-a-cover pass1 gets a 180° rescue before giving up; flags set correctly. Item-1
  policy + case/space tolerance + landscape→portrait vs centerfold-preserved all pass.
- Verification agent (code-reviewer): 2 real findings FIXED + re-verified — (1) `json.JSONDecodeError`
  from a regex-matched-but-invalid fragment escaped the orchestration and skipped the retry → now
  caught in `_run_vision_pass` (returns None = unparseable → retry); (2) pass-1-kept after an
  `is_upside_down` flag left `is_upside_down=True` → client would redundantly re-rotate → now suppressed
  (server authoritative). Issue 3 (quality gate pre-normalization) assessed NON-issue: the gate uses
  `min(w,h)` + Laplacian blur, both rotation-invariant. Issue 4 informational.
- Live-API JSON (real extraction + grading) is Mike's post-deploy check — no local ANTHROPIC_API_KEY.

### Revenue-path / deploy notes for Mike
- `/api/messages` IS the live grading path (Batch 3 flagged grading-input normalization as needing a
  re-spot-check; this is that change, now authorized). Spot-check a few real grades post-deploy.
- `/api/grade` (the labeled comprehensive endpoint) is DEAD in the live flow — no JS calls it; left
  untouched. Possible separate cleanup.
- Known cosmetic trade-off: for an upside-down FRONT, the server now corrects the READ but does not
  return the rotated image, and returns `is_upside_down=False`, so the client preview may show the
  original orientation (data is correct). Ties into the deferred item 3 (preview). Easy follow-up:
  return the corrected image from `/api/extract`.

---

## Session 94 (Jun 6, 2026) — Batch 4 Part A: Sig-ID gating, barcode, dep-monitor email

Batch 4 split into Part A (correctness/billing/monitoring) + Part B (image pipeline). Part A
COMMITTED + DEPLOYED as `d254309` (pushed to origin/main; Free-tier 403 + seed-email field tests
confirmed live, per Mike 2026-06-07). Part B = items 1+2 (Session 95 above); item 3 preview deferred.

**Item 4 — server-side signature-ID tier gating** (`routes/billing.py`, `routes/signature_orchestrator.py`).
Added `signature_id_per_month` to PLANS (free=0, pro=0, guard=10, dealer=-1) and
`get_signature_id_entitlement(user_id)` (fails CLOSED on DB error/unknown user; admin=unlimited;
paid plans need active subscription). `match_signature` now gates BEFORE the expensive match:
error→503, no_access→403, capped plan over limit→429 (fail CLOSED on usage-read error too),
unlimited→proceed. Replaced the old flat `MONTHLY_SIG_LIMIT=10`-for-all + fail-OPEN logic. Usage
Tier policy per Mike 2026-06-06. NOTE: Mike's log confirmed the earlier "flicker" was UI-only (no
/match fired) → that's on the UI-polish list; this gating stands on code grounds.
  - **Amendment (Mike, pre-commit):** (a) CAP SEMANTICS — the Guard cap counts CONFIDENT matches
    only (top confidence >= LOW_CONFIDENCE_THRESHOLD 0.50). Increment happens AFTER the result is
    known and ONLY for capped plans; no-match/below-floor/error never count; blocked calls (403/429)
    never process/bill. Dealer/admin are NOT counted in the cap column (it never resets for them) —
    their usage is monitored via the per-call `[SigID] match served ... cap_counted=...` log instead.
    (b) NO-MATCH HONESTY — `/v2/match` previously force-matched (returned nearest-neighbour top5 + a
    `low_confidence_match` flag). Now returns `matched: false` + "Signature not in our reference set"
    when top confidence < floor, rather than attributing the nearest neighbour. `matched` is the
    authoritative signal; top5 retained as transparency/candidates. Same no-confident-hallucination
    rule as Batch 3 extraction. Verification agent flagged dealer counter-increment (resolved as
    above — log-based visibility, counter is Guard-only).
    (c) THRESHOLD CONFIG — `LOW_CONFIDENCE_THRESHOLD` now reads `SIG_LOW_CONFIDENCE_THRESHOLD`
    (default 0.50), so floor + cap boundary retune via env, no code change. Marked PROVISIONAL —
    calibrate at the signature-v2 accuracy re-measurement (87% target). Single-definition property
    preserved (one constant feeds both the no-match floor and the cap boundary). Cap semantics
    verified locally: Guard no-match → counter unchanged; confident → +1 (true RETURNING count);
    9/10 + no-match + confident → ends at 10, not 11.

**Item 5 — barcode decoder addon-None** (`comic_extraction.py`). `decode_barcode` now runs ONLY when
`barcode_source == 'pyzbar'` (a scanner-confirmed addon), never on the vision model's guessed
`barcode_digits`. Without a confirmed addon: keep main UPC (series ID) only, mark
`barcode_source='vision_unverified'`, don't derive issue/printing/variant. Fixes false decodes like
Amethyst Annual #1 (no post-2008 add-on) → "issue 251".

**Item 6 — dep-monitor emails on state change, not every boot** (`dependency_monitor.py`).
`_send_alert_email` dedups against a self-creating DB table `dependency_alerts` (CREATE TABLE IF NOT
EXISTS — no migration needed) so a permanent state (eBay `unmonitorable`) emails once, not on every
Render restart. Prunes resolved keys so recurrence re-alerts. Falls back to in-memory `_emailed_keys`
(now also pruned) if DB unavailable.

### Verification
All three verified locally: entitlement across all tiers incl. fail-closed; barcode gate (pyzbar
decodes, model-guess doesn't); dep-monitor new→email, reboot→silent, resolved→prune, recurs→re-alert
(DB + in-memory paths). Verification agent: 1 false positive (claimed tz-naive/aware datetime crash —
code compares .year/.month ints, no datetime comparison; matches existing valuations/grading caps),
2 real findings FIXED (Dealer usage log always said used=1 → now RETURNING true count; in-memory
fallback didn't prune → now does).

### Files Modified (Batch 4 Part A)
- `routes/billing.py`, `routes/signature_orchestrator.py`, `comic_extraction.py`, `dependency_monitor.py`

### Still to do
- Part B: item 1 (grading-input normalization, per-photo) + item 2 (CCW 180° low-confidence fallback).
- Deferred: item 3 (preview — only if on-device still sideways). UI-polish: sig-section flicker.

---

## Session 93 (Jun 6, 2026) — Batch 3: Extraction & Orientation Regression

Four items (reproduce → fix → verify → agent → STOP). NOT committed/deployed — awaiting Mike.
Batches 1 (`cf9c3a2`) and 2 (`7d8aad7`) already deployed.

1. **Orientation pipeline (extraction) — root cause + fix.** `app.html`'s `extractComicData`
   (line 1789) sends the RAW front photo to `/api/extract` with no normalization, bypassing the
   client EXIF/canvas code (utils.js `processImageForExtraction`, grading.js
   `processImageWithOrientation`). Server-side did zero normalization. The Anthropic vision API
   ignores EXIF and reads raw pixels → 90deg-rotated covers read as garbled/hallucinated titles
   (Hercules→"Power of The Force", Invaders→"Marvel Comics #60", Atari Force→"Sgt. Rock #5").
   - **Fix (authoritative, server-side):** new `comic_extraction.normalize_orientation_b64()` —
     (a) `ImageOps.exif_transpose` (handles rotated-WITH-EXIF, the real phone→app.html upload, with
     correct direction + strips tag); (b) `assume_portrait` heuristic: if still landscape after EXIF,
     rotate 90deg CCW to portrait (handles hard-rotated NO-EXIF images, e.g. Google Photos
     re-exports, which the test fixtures turned out to be). Runs before BOTH barcode scan and the
     vision call; fails loud on undecodable input; tolerates data-URL prefix. Extraction calls it
     with `assume_portrait=True` (front cover is always portrait).
   - **Key discovery:** the supplied test fixtures (FromGooglePhotos) are landscape `4080x3072` with
     EXIF orientation=1 (tag stripped, rotation NOT baked) — so `exif_transpose` alone was a no-op on
     them; that's why the portrait heuristic was needed. Real phone uploads carry EXIF and are fixed
     by part (a). Direction empirically CCW (verified by rendering all 3 covers).
2. **Extraction model routing.** Extraction still correctly uses the `haiku` tier
   (`call_with_fallback(_client, 'haiku', ...)`); Batch 2 did NOT sweep it to Sonnet. Only the
   `/api/extract` usage LOG mislabeled it `SONNET` → fixed to `get_model('haiku')`.
3. **Re-test failing set (acceptance for 1+2).** Could not run a live extraction (no local
   ANTHROPIC_API_KEY; prod still pre-fix). VISUAL acceptance instead: ran the actual
   `normalize_orientation_b64(assume_portrait=True)` on all 5 covers and rendered outputs — all three
   failing covers now upright + fully legible (Atari Force, Hercules: Prince of Power #1, The Invaders
   #41 with 60c price clearly separate from issue 41); controls (Amethyst, Micronauts) untouched.
   Live-API JSON confirmation is Mike's post-deploy check. PROPOSED (not built): add these 5 covers
   as a permanent extraction regression fixture once the pinned-model test scripts are updated.
4. **Mobile 3-photo slab report.** Reproduction in code found NO 4-photo gate: the grading-report
   path requires only the FRONT cover (app.html:2195-2196); "of 4" is a label and "<4" a non-blocking
   warning; FAQ confirms "front required at minimum, proceed with fewer"; git history shows no 3->4
   change. So NOT a code regression in the visible path — likely stale cached JS, a mobile rendering
   issue, or a different flow. Needs a device repro/screenshot from Mike. No code change.

### Verification agent
Ran twice (after core fix, then after the portrait heuristic). No critical/correctness issues.
First-pass finding (data-URL prefix robustness) addressed. Confirmed: no double-rotation, gate
correct, CCW direction matches intent, only the front-cover path uses assume_portrait.

### Items needing Mike's call (NOT changed)
- **Symptom #3 (preview shows un-corrected):** display is separate from the API payload (uses the
  client raw image). Modern browsers auto-orient `<img>` by EXIF, so the raw-with-EXIF preview likely
  shows upright already; if not, return the normalized image from `/api/extract` for the preview.
- **Grading inputs:** brief says "before any API call," but grading is out-of-scope + passed.
  `/api/grade` and `/api/messages` still send un-normalized images. Applying the same normalization
  there would fix grading orientation but changes the revenue-path inputs (re-spot-check needed).

### Files Modified (Batch 3)
- `comic_extraction.py`, `routes/grading.py`

---

## Session 92 (Jun 6, 2026) — Batch 2: Model Migration + Hardening

Three tightly-scoped items (reproduce/establish → fix → verify → verification agent). NOT yet
committed/deployed — awaiting Mike's authorization. Batch 1 (`cf9c3a2`) is already deployed live.

1. **Migrated off `claude-sonnet-4-20250514`** (retires 2026-06-15 — deadline-driven). `models.py`
   sonnet chain → `claude-sonnet-4-6` (the deprecations.info-listed replacement), removed the
   retiring string from both `sonnet` and `sonnet-new` plus the aged `claude-3-5-sonnet-latest`.
   Centralized both grading paths through `models.py` + `call_with_fallback`: `/api/messages`
   (`routes/grading.py`) now ignores any client-supplied `model` and uses tier (default 'sonnet');
   `/api/grade` `run_grading` switched from `create(model=SONNET)` to `call_with_fallback`. Frontend
   `js/grading.js` (2 spots) now sends `tier: 'sonnet'` instead of the hardcoded retiring model.
   Added a thread-safety lock to `_active_index` (the threaded multi-run grading path now mutates it).
   - **Deprecation sweep:** on the Anthropic API, ONLY `claude-sonnet-4-20250514` was on a near
     clock. Other feed hits (3-5-sonnet/Vertex, sonnet-4/Bedrock, haiku-4-5 & sonnet-4-5/Azure,
     opus-4-6/Azure) are OTHER platforms (Vertex/Bedrock/Azure), not our direct Anthropic API.
   - ⚠️ **Revenue path:** grading model changed Sonnet 4 → Sonnet 4.6. Mike should spot-check a few
     real grades after deploy (a live grading call needs ANTHROPIC_API_KEY, only set in prod).
2. **JWT_SECRET fail-loud** (`auth.py`): if unset or == 'change-me-in-production', refuse to start in
   production (detected via Render's `RENDER` env var); in dev, warn loudly and use the dev default.
   ASCII-only messages (L-2026-015 — emoji crashed Windows cp1252 stdout in the dev path).
3. **eBay RSS 403** (`dependency_monitor.py`): diagnosed as site-wide Akamai bot-wall on
   developer.ebay.com (all paths, any User-Agent, incl. from Render). No automatable eBay
   deprecation source exists. Reclassified the eBay check from `error` to `status: unmonitorable`
   (honest degradation, cached 24h, retries daily in case the wall lifts) with manual-tracking
   guidance. `check_all()` still runs all four checks isolated.

### Verification
- Reproduced/established each item first (sonnet call-site grep + deprecation sweep; JWT default;
  eBay 403 with default + browser UA across multiple paths).
- All verified locally: models chains clean + fallback (incl. 8-thread concurrency, no index
  overrun); `/api/messages` overrides old model → 4-6; JWT refuse/warn across prod/dev contexts;
  eBay → unmonitorable; monitor no longer warns about a model we use.
- Verification agent: 3 findings. #2 (thread-unsafe `_active_index`) FIXED (lock + over-advance
  guard). #1 (`SONNET` static constant / dead `_ModelProxy`) — pre-existing, logging-only,
  left as-is (converting risks passing non-str to DB logging). #3 (auth import-raise on Render
  shell) — latent only; scripts don't import auth and Render shell inherits JWT_SECRET.

### Files Modified (Batch 2)
- `models.py`, `routes/grading.py`, `js/grading.js`, `auth.py`, `dependency_monitor.py`

### Still open / follow-ups
- `_ModelProxy` dead code + `SONNET`/`HAIKU` static constants (logging accuracy in
  `/api/valuate`, `/api/extract`) — separate cleanup.
- Frontend `js/grading.js` deploys via Cloudflare Pages (separate from Render). Backend ignores the
  client `model` regardless, so deploy order doesn't matter — but the JS cleanup needs a Pages deploy.
- CLAUDE.md deploy-note fix (auto-deploy unreliable) — spawned as a separate task.

---

## Session 91 (Jun 6, 2026) — Reconciliation + Fixes Batch 1

### What Was Done

Ran a read-only reconciliation pass (`docs/sessions/RECONCILIATION_2026-06-06.md`), then
implemented Fixes Batch 1 (reproduce-before-fix; verified; NOT yet committed/deployed — awaiting
Mike's authorization).

1. **Fixed the dead dependency monitor** (`dependency_monitor.py`). Root cause: `deprecations.info`
   changed its JSON from `{"items":[...]}` to a top-level array, so `check_anthropic()` crashed on
   `data.get("items")` — and because it ran first in `check_all()`, it killed every check (eBay RSS,
   Stripe, and the new eBay account-deletion self-check never ran). Fix: shape-tolerant parsing
   (handles both dict+array, `model_id`/`model_name`), all parsing inside try/except, each check
   isolated in `check_all()` so one failure can't block others, failed checks now surface a loud
   `status: error` entry (with a ~5 min backoff so an outage doesn't hammer upstream).
2. **Hardened the Stripe webhook** (`routes/billing.py`). Was processing events UNVERIFIED when
   `STRIPE_WEBHOOK_SECRET` was unset (forgeable → self-upgrade to paid tier). Now: unset secret →
   500 + refuse; bad signature → 400 + refuse; valid → process. Secret read per-request.
3. **Repointed `/api/signatures/db-stats`** (`routes/signatures.py`) from the stale bundled
   `signatures_db.json` snapshot to the live `creator_signatures` + `signature_images` tables (the
   stale endpoint reported 80/97 vs the live 99/203). Graceful 503 if no DB; backward-compatible
   response keys. The v1 matcher still reads the JSON snapshot — left untouched (separate cleanup).
4. **Documented all env vars** in `docs/technical/ARCHITECTURE.txt` (was 1 of ~32) — name, purpose,
   reading module, unset behavior. Flagged `JWT_SECRET`'s insecure `'change-me-in-production'`
   default (auth.py NOT changed this batch).

### Verification
- Reproduced bugs #1 and #2 first (tracebacks / code-path quotes captured in session).
- All fixes verified locally (monitor: all checks run + isolation + backoff; webhook: 500/400/200
  with no handler calls when rejected; db-stats: 503 + correct aggregation). Ran a code-review
  verification agent; its 3 findings (retry backoff, `none` quality bucket, per-request secret read)
  were all addressed and re-verified.

### Follow-ups surfaced (NOT in this batch — own briefs)
- 🔴 **`claude-sonnet-4-20250514` retires 2026-06-15** (the now-working monitor caught it) — Sonnet
  migration gets its own brief.
- 🟡 **eBay RSS feed returns 403** (`developer.ebay.com/rss/api-status`) — check can't fetch; needs
  a new URL or a User-Agent header.
- 🟡 **v1 signature matcher** still on the stale JSON snapshot.
- 🟡 **`JWT_SECRET` insecure default** in `auth.py` — harden separately.

### Files Modified (Batch 1)
- `dependency_monitor.py`, `routes/billing.py`, `routes/signatures.py`, `docs/technical/ARCHITECTURE.txt`
- `docs/sessions/RECONCILIATION_2026-06-06.md` (new, from the reconciliation pass)

---

## Session 90 (Mar 24, 2026) — Mobile Extraction Fix + Dependency Monitor

### What Was Done

1. **Fixed mobile image extraction** — Three bugs causing extraction failures on mobile:
   - Images now always go through canvas (max 2048px, JPEG normalized) — fixes oversized payloads
   - Rewrote EXIF orientation parser — was bailing early on valid JPEG segments, sending rotated photos uncorrected
   - Added `is_comic_cover` validation to extraction prompt — non-comic photos get a clear error

2. **Fixed Haiku model retirement** — `claude-3-5-haiku-latest` returned 404, broke all extraction. Updated to `claude-haiku-4-5-20251001`. Migrated `comic_extraction.py` from raw `requests.post()` to Anthropic SDK with `call_with_fallback()`.

3. **Built automated dependency monitoring** — `dependency_monitor.py` checks three services:
   - Anthropic model retirements (via deprecations.info)
   - eBay API deprecations (via developer.ebay.com RSS)
   - Stripe SDK version drift (via PyPI)
   - Email alerts + admin dashboard warning banner
   - Runs on every Render health check, cached 24h

4. **Added enforcement rules** — CLAUDE.md now mandates all new third-party services be registered in dependency monitor. Saved as persistent memory.

5. **Consolidated report loading UI** — Replaced 3 simultaneous loading indicators with single animated gradient spinner + cycling status messages. Works above the fold on mobile.

6. **Fixed health endpoint crash** — `dependency_monitor.py` was taking down the `/health` endpoint. Wrapped in try/except, made resend import optional.

7. **Fixed grading report error** — Loading spinner refactor accidentally removed `defectsGrid` variable declaration, causing ReferenceError that showed "Error/FAILED" even though grading succeeded. One-line fix.

8. **Updated MASSE + TheFormOf CLAUDE.md** — Added mandatory dependency monitoring rules to both projects. TFO version includes Layer 2 (client app dependencies) and billable "Managed Updates" service concept.

### Files Created
- `dependency_monitor.py`

### Files Modified
- `js/grading.js`, `comic_extraction.py`, `models.py`, `routes/utils.py`, `routes/admin_routes.py`, `admin.html`, `app.html`, `CLAUDE.md`

### Next Up
- Continue mobile testing (extraction + grading confirmed working)

---

## Session 89 (Mar 11-12, 2026) — Admin Insights + Unified AdminHub Dashboard

### What Was Done

1. **Enhanced Admin Users Tab** — Rewrote `/api/admin/users` to JOIN with collections, comic_registry, request_logs, api_usage, user_feedback tables. Each user row now shows: collections count, slab guard registrations, API calls, AI cost, last activity, top actions breakdown, feedback count/avg. Expandable rows show full detail. Committed and pushed.

2. **Enhanced Feedback Endpoint** — Updated `/api/admin/feedback` to JOIN with collections table via `grading_id`, returning comic title, issue number, grade, and photo URLs alongside each feedback entry. Feedback now shows what comic was being graded when the user left feedback.

3. **AdminHub — Unified Cross-Domain Dashboard** — Built a single-page admin dashboard that aggregates data from both SlabWorthy and MASSE into one view. Located at `C:/Users/mberr/theformof/`.
   - **Dual auth engine**: JWT for SlabWorthy, Supabase SDK for MASSE
   - **Connection dots**: Green/red per-app status in header
   - **Overview tab**: Aggregated stats across all apps
   - **Per-app tabs**: Users, Beta Codes, Errors, Usage, Waitlist, Feedback, NLQ Query
   - **Modular config**: Adding a 3rd app = one config object in the APPS array
   - **Runs locally**: `node serve.js` → `http://localhost:8080`
   - **Future-ready**: TheFormOf placeholder tab (greyed out) already in place

4. **MASSE CORS Update** — Added `localhost:8080` and `127.0.0.1:8080` to MASSE backend CORS whitelist so AdminHub can call MASSE APIs cross-origin. Committed and pushed.

5. **Bug Fixes**
   - Fixed SlabWorthy login URL in AdminHub (`/api/login` → `/api/auth/login`)
   - Fixed race condition where `closeLoginModal()` nulled `loginTargetApp` before the post-login code could use it
   - Fixed `substring()` error on numeric SlabWorthy user IDs (MASSE uses UUID strings)

### Files Created
- `C:/Users/mberr/theformof/index.html` — AdminHub dashboard (~1200 lines, single-file)
- `C:/Users/mberr/theformof/serve.js` — Express static file server
- `C:/Users/mberr/theformof/package.json` — Express dependency

### Files Modified
- `routes/admin_routes.py` — Enhanced `/api/admin/users` with 6 additional SQL joins; enhanced `/api/admin/feedback` with collection/comic context
- `admin.html` — Enhanced Users tab (10 columns, expandable rows, timeAgo, activity chips)
- MASSE `backend/server.js` — Added localhost:8080 to CORS origins
- MASSE `backend/routes/admin.js` — Enhanced `/api/admin/users` with companies, invite_codes, token_usage joins

### Planning Docs
- `docs/UNIFIED_ADMIN_PLAN.md` — Updated to reflect AdminHub is built (Phases 1-3 complete)
- Same doc mirrored in MASSE repo

### What's Next
- **Deploy to Render** — Run `deploy` CLI command to push enhanced admin API endpoints live. The AdminHub dashboard calls the production APIs, so the enriched user data (activity, costs, feedback context) will only show once the backend is redeployed.
- **TheFormOf** — When the 3rd app is built, add one config object to AdminHub's APPS array and it auto-integrates.
- **Phase 4** — Cross-app user matching (same email across apps), unified cost dashboard, cross-app NLQ queries.

### Previous Session
- Session 88 (Mar 8) — Beta User Management: Grading Cap (25/month) + Feedback System + Waitlist Admin + Invite Flow
