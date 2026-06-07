# Where We Left Off - Jun 7, 2026

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
