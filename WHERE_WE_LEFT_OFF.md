# Where We Left Off - Mar 7, 2026

## Session 85 (Mar 7, 2026) — v2 First Test Success + pass_count Bug Fix

### What Was Done
- **First v2 match test succeeded!** Jim Lee identified at 0.96 confidence (high) via PowerShell curl
- **Found and fixed pass_count=1 bug** — 2 of 3 Opus passes were silently failing and being dropped. Added retry logic, degraded_result flag, passes_attempted tracking.

### First v2 Test Results (Jim Lee)
- **Top result:** Jim Lee at 0.96 confidence (high)
- **#2:** J. Scott Campbell at 0.02 (speculative)
- **#3:** Frank Miller at 0.01 (speculative)
- **Difficulty:** easy
- **Latency:** 37,443ms (~37 seconds)
- **pass_count:** 1 (BUG — expected 3, only 1 Opus pass succeeded)
- **Stability scores:** all 1.0 for top 5
- **Flags:** no forgery, no poor quality, no confusion pair
- **Context match:** "Jim Lee was a major DC artist in the 1990s" — publisher/era metadata pre-filter working

### pass_count=1 Bug — Root Cause & Fix
**Root cause:** `run_single_pass()` catches API errors and JSON parse failures, returning `PassResult(rankings=[])`. The orchestrator then silently filtered these out with `if result.rankings:`, so 2 failed passes were invisible — no warning, no retry, no flag.

**Fix (routes/signature_orchestrator.py):**
1. **Failed passes now tracked separately** — logged with `logger.warning()` showing temperature and failure flags
2. **Automatic retry** — failed passes get one retry before being abandoned (API errors are often transient)
3. **New `degraded_result` flag** — set in `merged_flags` when fewer passes succeeded than attempted
4. **New `passes_attempted` field** — response now shows `pass_count` (succeeded) AND `passes_attempted` (total)
5. **`needs_review` includes degraded** — degraded results auto-flagged for human review in DB log
6. **Summary logging** — "DEGRADED: Only 2/3 passes succeeded" warning in server logs

### Files Modified
- **routes/signature_orchestrator.py** — Retry logic for failed passes, degraded_result flag, passes_attempted field in AggregatedResult + API response, better logging

### What's Next (Priority Order)
1. **Deploy fix + retest** — push, deploy, re-run Jim Lee test and confirm pass_count=3
2. **A/B test v1 vs v2** — compare accuracy on same test images (multiple artists)
3. **Check Render logs** — understand what specifically caused 2/3 passes to fail (timeout? rate limit? JSON parse?)
4. **Fix style_notes** (Mike manual task) + source better Bendis/Claremont reference images
5. **Target 87%+ accuracy** before advertising signature feature publicly

---

## Session 84 (Mar 7, 2026) — Signature Orchestrator v2 Integration + Haiku Revert

### What Was Done
Integrated the signature orchestrator v2 (designed in Session 83) into the codebase. Found and fixed 7 integration issues. Also tested and reverted the two-stage Haiku prefilter approach from Session 82.

### Deploy Progress
- ✅ Migrations run on Render PostgreSQL via `run_migrations.py` (psql not available on Render container — used psycopg2 instead)
- ✅ Seed script run: `python seed_creator_metadata.py <DATABASE_URL>` — 41 creators populated
- ✅ Fixed `cs.name`/`cs.slug` bug in migration validation view (would have failed on production schema)
- ✅ Code deployed to Render
- ✅ v2 endpoint tested — Jim Lee correctly identified at 0.96 confidence

---

## Session 83 (Mar 7, 2026) — Signature Orchestrator v2 Architecture

### What Was Built
Designed and built a complete 3-pass Opus 4.6 orchestration layer for signature identification. This session was architecture + code generation — **nothing deployed yet**.

### Problem Being Solved
Current v1 `/api/signatures/match` sends all reference images in a single Sonnet call. At 43 artists × 2 images = 86 images per call, and growing toward 100 artists × 4 images = 400 images, cost and accuracy both degrade. Jim Lee is still confused with 3 other creators.

### Files Created (downloaded, not yet in repo)

**routes/signature_orchestrator.py**
- Flask blueprint at `/api/signatures/v2/`
- Two endpoints: `POST /match` and `GET /match/stats`
- Full orchestration pipeline:
  1. `prefilter_candidates()` — PostgreSQL metadata query (era, publisher) narrows 100 → 15 creators
  2. `fetch_images_from_r2()` — boto3 S3-compatible R2 fetch, 4 images per creator
  3. `run_orchestrated_identification()` — fires 3 parallel Opus calls via ThreadPoolExecutor
  4. `aggregate_passes()` — averages confidence scores, detects rank instability, normalizes to sum=1.0
  5. `log_result_to_db()` — writes result + flags to PostgreSQL review queue (non-blocking)
- Model: `claude-opus-4-6`
- 3 passes at temperatures: 0.2 (deterministic), 0.5 (moderate), 0.7 (exploratory)
- Flags: `low_confidence_match` (<0.50), `high_confusion_pair` (rank1/rank2 within 0.10), `stability_score`

**prompts/signature_identification_system.md**
- Full system prompt for Opus — forensic signature expert persona
- Structured JSON output format (top 5 rankings, match_evidence, contra_evidence, flags)
- Disambiguation guidance for initials-based sigs, cursive sigs, era context
- Multi-pass aggregation instructions (for orchestrator, not shown to user)
- Context injection template (publisher/era/slab_label prepended to each call)
- Claude Code implementation notes (R2 key pattern, pre-filter, review queue)

**migrations/add_orchestrator_columns.sql**
- Adds to `creator_signatures`: career_start, career_end, publisher_affiliations (text[]), signature_style, reference_image_count, active, notes
- Adds to `signature_images`: r2_key, sort_order, source_url, approximate_year, image_notes
- 4 indexes including GIN index on publisher_affiliations for array containment queries
- Auto-trigger `trg_update_image_count` keeps reference_image_count in sync on INSERT/UPDATE/DELETE
- Backfill query for existing rows
- Validation view `migration_validation` — shows count_check OK/MISMATCH per creator

**migrations/add_signature_identification_log.sql**
- New table `signature_identification_log` — stores every identification result
- Columns: top_creator, top_confidence, top5_json, flags_json, comic_context_json, stability_scores_json, needs_review, reviewed, correct_creator
- 3 indexes for review queue and per-creator analysis
- Views: `signature_review_queue` (unreviewed flagged items) and `signature_confusion_summary` (per-creator confusion matrix for tuning)

### Deploy Sequence (Next Session)
```
1. psql → run add_orchestrator_columns.sql
2. psql → run add_signature_identification_log.sql
3. Run migration_validation view — confirm all count_check = 'OK'
4. Seed creator metadata (career_start, publisher_affiliations, signature_style) for all 43 creators
5. git add routes/signature_orchestrator.py prompts/signature_identification_system.md migrations/
6. Register blueprint in wsgi.py:
   from routes.signature_orchestrator import signatures_bp as signatures_v2_bp
   app.register_blueprint(signatures_v2_bp)
7. git commit -m "Add signature orchestrator v2 + DB migrations" ; git push ; deploy ; purge
8. Test POST /api/signatures/v2/match with known signed book image
9. Check GET /api/signatures/v2/match/stats
10. A/B compare v1 (/api/signatures/match) vs v2 accuracy on same test set
```

### Key Architecture Decisions
- **v1 stays live** — v2 is at `/api/signatures/v2/` so both run in parallel for A/B testing
- **Pre-filter via PostgreSQL metadata** — publisher_affiliations will directly address Jim Lee confusion (he and his lookalikes work for different publishers in different eras)
- **CLIP embeddings deferred** — PostgreSQL metadata pre-filter is sufficient for now; revisit if accuracy plateaus at 90%+
- **Confidence normalization** — all 5 scores always sum to 1.0, forces honest uncertainty
- **Review queue** — every low_confidence or confusion_pair result auto-flagged for human review; builds ground truth dataset over time

### What's Next (Priority Order)
1. **Run DB migrations** — columns first, then log table
2. **Seed creator metadata** — career_start/publisher_affiliations/signature_style for 43 creators
3. **Add files to repo + register blueprint**
4. **Deploy + test**
5. **Fix style_notes** (Mike manual task) + source better Bendis/Claremont reference images
6. **Target 87%+ accuracy** before advertising signature feature publicly

---

## Session 82 (Mar 7, 2026) — Signature Recognition Accuracy Improvements

### Problem
Cross-validation accuracy was **73.9% (17/23)** — 6 artists misidentified at HIGH confidence (0.82-0.92). Key failure: Jim Lee was being confused with Grant Morrison.

### Root Cause Analysis (5 issues identified)
1. **Only 1 reference image per artist** — not enough to capture natural signature variation
2. **No system prompt** — no forensic expertise context for the model
3. **Bad reference image selection** — "largest file = best quality" heuristic fails for images with busy backgrounds or logo overlaps
4. **Inaccurate style_notes metadata** — Claude Sonnet wrote the descriptions, they don't match reality (fix deferred to Mike)
5. **Cross-validation data leakage bug** — test image wasn't excluded from the reference set

### Fixes Implemented

**1. Added `preferred_images` to all 23 artists in `signatures_db.json`**
- Manually curated best 2 reference images per artist
- Avoided bad references: `BrianMichaelBendis_Signature_5_2003.jpg` (white pen on busy comic cover), `Jim_Starlin_Signature_2.jpg` (Infinity Gauntlet logo overlap)

**2. Added `select_reference_images()` helper function**
- Priority: preferred_images first → fallback to largest files by size
- Accepts `exclude_image` param for cross-validation
- Added to both `routes/signatures.py` and `signatures/signature_matcher.py`

**3. Added `SIGNATURE_MATCHING_SYSTEM_PROMPT` constant**
- Expert forensic document examiner context
- Emphasizes structural features, natural variation, conservative matching
- Applied to all 3 `client.messages.create()` calls via `system=` parameter

**4. Updated `/match` endpoint (`routes/signatures.py`)**
- Now sends 2 reference images per artist (was 1)
- Increased `max_tokens` from 1500 → 2000

**5. Updated `_step2_match_signatures()` (`routes/signatures.py`)**
- Now sends up to 3 images per candidate artist from PostgreSQL
- Added system prompt

**6. Updated CLI matcher (`signatures/signature_matcher.py`)**
- Same multi-reference + system prompt pattern
- Fixed cross-validation data leakage: test image now excluded from references

### Results: 78.3% accuracy (18/23) — up from 73.9% (17/23)

| Category | Artists | Details |
|----------|---------|---------|
| ✅ Fixed (3) | Jae Lee, Jim Lee, Jim Steranko | Previously wrong, now correct |
| ❌ Still failing (3) | Bendis, Claremont, Geoff Johns | Persistent misidentifications |
| ❌ New failures (2) | Art Adams, Grant Morrison | Appeared after changes |

**Note:** Cross-validation uses random image selection per run, so results have variance. The test is now harder/fairer due to the exclude_image bug fix.

### Token Cost Impact
- `/match`: 23 → 46 reference images (~$0.11/call additional)
- `/identify` step 2: minimal increase (only candidate artists)

### Files Modified
- `signatures/signatures_db.json` — added `preferred_images` to all 23 artists
- `routes/signatures.py` — helper function, system prompt, `/match` multi-reference, `_step2_match_signatures` multi-reference
- `signatures/signature_matcher.py` — helper function, system prompt, prompt builder, cross-validate bug fix

### What's Next (to push toward 87%+ target)
1. **Fix `style_notes` metadata** — Mike needs to correct the inaccurate descriptions (Claude Sonnet wrote them)
2. **Source better reference images** — especially for Bendis (noisy backgrounds) and Claremont
3. **Deploy to production** — changes only tested locally via CLI, need to push + deploy on Render
4. **Run server-based tests** — use `test_signature_matcher.py` against production API

---

## Session 81 (Mar 6, 2026) — Collection Page Refactor + Sort Fix

### Collection.html Refactored into Modular Files ✅
Split the 3,925-line monolith into 5 clean files:
- `collection.html` (410 lines) — Pure HTML shell with auth gate inline script
- `js/collection.css` (1,745 lines) — All CSS (collection page, sell dropdown, guard buttons, eBay modal, marketplace modal, responsive)
- `js/collection.js` (922 lines) — Core collection logic (26 functions: load, filter, sort, display, CRUD, sell, guard, gallery export)
- `js/ebay-modal.js` (453 lines) — eBay listing modal (open/close, populate, generate description, upload photos, create listing)
- `js/marketplace-modal.js` (406 lines) — Generic marketplace prep modal for 8 platforms (Whatnot, Mercari, Facebook, Heritage, ComicConnect, MyComicShop, COMC, Hip Comics)

Script loading order preserved: utils.js → auth.js → collection.js → ebay-modal.js → marketplace-modal.js → sidebar.js

### Sort Dropdown Bug Fixed ✅
**Bug:** Sort dropdown in list view did nothing. Filter and era dropdowns worked fine.
**Root cause:** Two `<select>` elements both had `id="sortSelect"` — one for list view (values: date-desc, value-desc, etc.) and one for gallery view (values: series, value-high, etc.). `getElementById` always grabbed the first one. The list view sort values didn't match any switch case in `filterAndDisplay()`, so they fell to `default: return 0` (no sort).
**Fix:**
- Gave unique IDs: `listSortSelect` and `gallerySortSelect`
- Wrapped in container divs (`listSortGroup` / `gallerySortGroup`) with show/hide on view toggle
- Added switch cases for list sort values (date-desc, date-asc, value-desc, value-asc, grade-desc, title-asc)
- Column header sorting still works — clicking a column header overrides the dropdown, changing the dropdown clears column sort state

### Testing Results
1. ✅ Page loads correctly
2. ⏳ Gallery view needs work (deferred)
3. ✅ Sort fixed (was broken, now works)
4. ✅ Sell dropdown works
5. ✅ Guard actions work
6. ✅ eBay modal works
7. ✅ Marketplace prep modal works
8. ✅ Gallery expand works
9. ℹ️ Bulk actions are stubbed out (Export/Delete say "coming soon")
10. ⏳ Mobile responsive — added to TODO for later testing

### Files Modified
- `collection.html` — Slimmed to 410-line HTML shell with unique sort dropdown IDs
- `js/collection.css` — NEW (1,745 lines extracted CSS)
- `js/collection.js` — NEW (922 lines core logic + sort fix)
- `js/ebay-modal.js` — NEW (453 lines eBay modal)
- `js/marketplace-modal.js` — NEW (406 lines marketplace modal)
- `TODO.md` — Updated to Session 81
- `ROADMAP.txt` — Added Session 81, bumped to v5.5.0
- `README.md` — Updated architecture section + session number
- `WHERE_WE_LEFT_OFF.md` — This file

### Deploy Checklist
```
git add collection.html js/collection.css js/collection.js js/ebay-modal.js js/marketplace-modal.js TODO.md ROADMAP.txt README.md WHERE_WE_LEFT_OFF.md ; git commit -m "Refactor collection.html into modular files + fix sort dropdowns" ; git push ; deploy ; purge
```

### What's Next
1. **Deploy sort fix** — run git add/commit/push/deploy/purge
2. **Test sort on production** — list sort dropdown + column header clicks + gallery sort
3. **Gallery view improvements** — noted during testing as needing work
4. **Mobile responsive testing** — post-refactor CSS check on real devices
5. **Wire up bulk actions** — checkboxes per comic card, export/delete implementation
6. **Baseball card vertical planning** — architecture decisions for multi-vertical support

---

## Session 80 (Mar 6, 2026) — Register/Stolen E2E Test + UI Fixes + P&L Projection

### Register/Report Stolen — Full E2E Test on Production ✅
Tested the entire Slab Guard state machine on slabworthy.com:
- Registered Atari Force comic → got serial SW-2026-JNZ5HR ✅
- Reported it stolen → button changed to 🚨 stolen state ✅
- Checked verify page for stolen comic → showed "REPORTED STOLEN" badge + "Report a Sighting" button ✅
- Checked verify page for active comic (SW-2026-6N6QMS, Amethyst) → no sighting button ✅
- Marked recovered → button changed to ✅ recovered with "Report Stolen Again" ✅
- EXIF rotation verified working on verify page ✅

### UI/UX Fixes (5 Issues from Testing)
1. **Sell button brand fix** — Changed from purple/gold gradient to dark fill with brand-purple border/text (matches other buttons)
2. **Larger serial numbers** — Increased `.guard-serial` from 0.65rem→0.8rem, opacity 0.7→0.9, added font-weight 600
3. **Animated ellipsis during registration** — CSS `@keyframes guardEllipsis` with `steps(4, end)`, pointer-events disabled while registering
4. **Removed all alert/confirm modals** — Chrome extension can't interact with native modals. Rewrote `registerComic()`, `reportStolenComic()`, `markRecoveredComic()` to use inline button state changes (color flash → auto-reload)
5. **Sighting notifications in My Collection** — Red badge on guard button showing sighting count, "View Sightings" dropdown link → new sightings.html page

### New File: sightings.html
Full sighting details page for comic owners:
- Auth-gated, reads comic_id and serial from URL params
- Calls `/api/registry/my-sightings` API, filters by serial
- Shows comic info bar with title, issue, status badge, serial tag
- Sighting cards with: reporter email, date, listing URL, message
- Owner response buttons: "That's mine" / "Not mine" / "Investigating"
- All user content escaped with `escapeHtml()` for XSS prevention

### Collection API Updated
- Added `sighting_count` via LEFT JOIN subquery on `sighting_reports` table
- Grouped by `serial_number` with COALESCE for null handling

### Year 1 P&L Projection (Business Planning)
Built comprehensive P&L spreadsheet for investor/planning purposes:
- **v1:** Comics only (5,000 users) → $200K annual profit, 81% margin
- **v2:** Added baseball cards (10,000 users, 2× API rate) → $544K profit, 74% margin
- **v3 (final):** Full startup costs (employee + marketing + G&A) → **$379K profit, 51% net margin**
- File: `docs/business/SlabWorthy_Year1_PnL.xlsx` (3 tabs: Assumptions, P&L Summary, Scenarios)

### TAM Research
- Comic collectors (US): ~2-5 million individuals, ~3,700-4,700 shops
- Sports card collectors (US): ~15-20 million households, ~3,000-5,000+ shops
- 15,000 user target = <0.1% of individual TAM (very achievable)
- Shop targets (500 comic / 1,000 card) are aggressive for Y1 (11-33% penetration); more realistic: 150-400 shops per vertical

### Anthropic API Token Cost Analysis
| Endpoint | Model | Max Tokens | Est. Cost/Call |
|----------|-------|-----------|----------------|
| Grading (Vision) | Sonnet 4 | 2,048 | $0.035 |
| Listing gen | Sonnet 4 | 600 | $0.010 |
| Slab Guard CV | Sonnet 4 | 1,500 | $0.024 |
| Signature match | Sonnet 4.5 | 1,500 | $0.024 |
| Card equivalents | — | — | 2× above |

### Security Fixes
- **XSS in sightings.html** — Applied `escapeHtml()` to all interpolated values (serial, listing_url, reporter_email, etc.)
- **Missing URI encoding** — Added `encodeURIComponent()` for serial parameter in View Sightings URL

### Files Modified
- `collection.html` — Sell button CSS, guard-serial CSS, registering animation, guardButton() JS, registerComic/reportStolen/markRecovered rewritten (no modals), sighting badge + dropdown
- `routes/collection.py` — Added sighting_count LEFT JOIN subquery
- `sightings.html` — NEW file (sighting details page)
- `docs/business/SlabWorthy_Year1_PnL.xlsx` — NEW file (Year 1 P&L v3)

### Deploy Checklist
```
git add collection.html routes/collection.py sightings.html ; git commit -m "No-modal guard actions + sighting page + sell button brand fix" ; git push ; deploy ; purge
```

### What's Next
1. **Deploy Session 80 code** — Mike to run deploy
2. **Test the no-modal flows on production** — register, report stolen, recover (all inline now)
3. **Baseball card vertical planning** — architecture decisions for multi-vertical support
4. **Hire first employee** — Marketing + front-end design role ($75K + benefits)
5. **Test marketplace prep** — Download All Photos, Copy All, multiple platforms

---

## Session 79 (Mar 5, 2026) — Register/Stolen Buttons + Verify Page Polish

### Whatnot Modal Crash Fix
**Bug:** Clicking Sell → Whatnot did nothing. eBay worked fine.
**Root cause:** When we cleaned up the Photos section in Session 78 and removed the "Right-click > Save Image" hint element (`mpPhotoHint`), the JS reference on line 3288 was left behind: `document.getElementById('mpPhotoHint').textContent = ...`. Since the element no longer exists, `getElementById` returns `null`, and `.textContent` on `null` throws a `TypeError` that kills the entire `openMarketplacePrepModal()` function before the modal opens.
**Fix:** Removed the dead reference line, added `?.` null safety to `copyMpField()` and `copyAllMp()`.

### Human-Friendly Verify Page (Auto-Lookup)
**Problem:** Slab Guard verify links in marketplace prep notes pointed to the raw API endpoint (`/api/verify/lookup/SW-2026-...`) which returned JSON — unusable for buyers.
**Fix:**
- Updated `verify.html` to read `?serial=` URL parameter on page load
- Auto-calls API via GET (no Turnstile needed for direct links) and displays results immediately
- Updated verify URL format in both `whatnot_description.py` and `collection.html` fallback notes to: `https://slabworthy.com/verify.html?serial=SW-2026-XXXXX`
- Manual lookups (typing serial on the page) still require Turnstile via POST

### Cover Image EXIF Rotation Fix
**Problem:** Cover image on verify page displayed rotated (phone photos have EXIF orientation data).
**Fix:** Added `from PIL import ImageOps` and `ImageOps.exif_transpose(img)` before `.convert('RGBA')` in `watermark_image()` function in `routes/verify.py`.

### Register + Report Stolen Buttons in Collection
**New collection page buttons** — conditional per comic based on registration status:
- **Not registered** → 🛡️ Register button (calls existing `/api/registry/register`)
- **Active (registered)** → 🚨 Report Stolen button
- **Reported stolen** → Red "Stolen" badge + ✅ Recovered button
- **Recovered** → Amber "Recovered" badge

**New helper function** `guardButton(comic, stopProp)` generates the right button for both list and gallery views.

**New API endpoints** (in `routes/registry.py`):
- `POST /api/registry/report-stolen/<comic_id>` — changes status from `active` → `reported_stolen`, sets `reported_stolen_date`
- `POST /api/registry/mark-recovered/<comic_id>` — changes status from `reported_stolen` → `recovered`, sets `recovery_date`

Both require auth + approved. Owner-only with proper status transition guards.

### Collection API Enhanced
Added `cr.status AS registry_status` and `cr.registration_date AS registry_date` to the SELECT query in `routes/collection.py`. These auto-serialize via the existing `dict(item)` loop.

### Verify Page Sighting Restriction
Changed "Report a Sighting" visibility from `active || reported_stolen` to just `reported_stolen`. Only stolen comics show the sighting form.

### Mike's Vision for Future Sighting Flow
Ideal case: Slab Guard Chrome extension running on buyer's browser → extension knows which comics are registered/stolen → when one appears on eBay, user clicks extension button → auto-fills report-sighting form with URL, email, timestamp. Extension already has partial support built.

### Files Modified This Session
- `collection.html` — Fixed mpPhotoHint crash, null safety on copy functions, verify URL update, Register/Stolen/Recovered buttons (CSS + HTML + JS in both views)
- `verify.html` — Auto-lookup from URL params, GET support for direct links, sighting restricted to stolen only
- `routes/verify.py` — EXIF rotation fix in watermark_image()
- `routes/registry.py` — New report-stolen and mark-recovered endpoints
- `routes/collection.py` — Added registry_status and registry_date to response
- `whatnot_description.py` — Updated verify URL to slabworthy.com/verify.html?serial=...
- `TODO.md` — Updated to Session 79
- `WHERE_WE_LEFT_OFF.md` — Updated to Session 79

### What's Next (Priority Order)
1. **Test Register + Report Stolen flow** — register a comic, report stolen, mark recovered, verify page behavior
2. **Test marketplace prep** — Download All Photos, Copy All, verify links, multiple platforms
3. **Test eBay draft + auction listings** — remaining from P1
4. **Refactor collection.html** — 3,583 lines, needs splitting into CSS/JS modules (discussed but deferred)
5. **Chrome extension enhancement** — auto-detect registered/stolen comics on eBay, one-click sighting report

### Deploy Checklist
```
git add collection.html verify.html routes/verify.py routes/registry.py routes/collection.py whatnot_description.py ; git commit -m "Register/Report Stolen buttons + verify page auto-lookup + EXIF fix" ; git push ; deploy ; purge
```
Already deployed by Mike before break.

---

## Session 78 (Mar 5, 2026) — Whatnot Modal Invisible Text Fix + UI Polish

### The Big Fix: Invisible Text in Marketplace Prep Modal (3 Sessions to Solve)
**Problem:** Listing Title, Description, and Show Prep Notes fields in the Whatnot marketplace prep modal showed invisible text. Two previous sessions of CSS fixes (`color: #ffffff !important`, `-webkit-text-fill-color: #ffffff !important`, JS force-apply, setAttribute, requestAnimationFrame) all failed.

**Debug confirmation:** Added a debug strip that showed `DEBUG (ai): Title[15]="Iron Man #7 6.5" | Desc[131]="Classic mid-80s Iron Man from..."` — values WERE being set correctly but remained invisible in the form inputs.

**Root cause:** WebKit's internal form input `.value` rendering pipeline ignores standard CSS color overrides in certain dark-theme contexts. The `.value` property has a separate rendering path from normal DOM text.

**Solution:** Replaced all `<input>` and `<textarea>` elements with `<div contenteditable="true">` elements that render text as normal DOM text using `.textContent` instead of `.value`.

**Changes:**
- HTML: `<input>` → `<div class="form-input mp-editable" contenteditable="true" role="textbox">`
- HTML: `<textarea>` → `<div class="form-input mp-editable mp-multiline" contenteditable="true" role="textbox">`
- JS: All `.value` references → `.textContent` across 6+ functions (mpSetField, copyMpField, copyAllMp, generateMarketplaceContent, fallback population)
- CSS: New `.mp-editable` class with `white-space: pre-wrap; word-wrap: break-word; outline: none; cursor: text;`
- CSS: `.mp-editable:empty::before { content: attr(data-placeholder); }` for placeholder text

### Flex Layout Fix
**Problem:** After contenteditable switch, user screenshot showed text squeezed into thin strips on left, copy buttons taking 80% width.
**Root cause:** Contenteditable divs with `flex: 1` but no `min-width: 0` — flexbox default `min-width: auto` caused content-based sizing.
**Fix:** `.mp-editable { flex: 1 1 0%; min-width: 0; }` and `.copy-btn { flex: 0 0 36px; width: 36px; height: 36px; }`

### API Guard Conditions
**Problem:** `generateMarketplaceContent()` was overwriting fallback values with empty strings when API returned empty/missing fields.
**Fix:** Guard conditions — only overwrite if `data.listing_title && data.listing_title.trim()` (same for description and show_notes).

### Download All Photos Button
- Added `⬇ Download All Photos` button above the photo grid
- `downloadAllMpPhotos()` function downloads front/spine/back/centerfold photos sequentially with 300ms delays
- Button hidden by default, shown when photos are available

### Slab Guard Verification URL in Prep Notes
- **What Mike wanted:** Slab Guard serial number (SW-2026-XXXXX) with verification URL in show prep notes — NOT plain assessment ID (#47 isn't useful to buyers)
- **Backend:** Added `_append_sw_ids()` helper to `whatnot_description.py` that appends Slab Guard serial + verify URL to show notes
- **Frontend:** Fallback notes also include Slab Guard serial + verify URL when `mpComic.registry_serial` exists
- **Collection API:** Added LEFT JOIN to `comic_registry` table to include `registry_serial` in collection data
- **Verify URL format:** `https://collectioncalc-docker.onrender.com/api/verify/lookup/SW-2026-XXXXX`

### UI Polish
- **Debug strip hidden** — `dbg.style.display = 'block'` commented out (HTML kept for future debugging)
- **Photos section cleaned up** — removed "Photos" label and "Right-click > Save Image" hint
- **Footer restructured** — Close/Copy All buttons in `.mp-footer-buttons` div, paste hint moved below buttons
- **Paste hint** shows platform-specific instructions (e.g. "Open Whatnot seller dashboard → paste each field")

### Files Modified This Session
- `collection.html` — Major modal rewrite (contenteditable divs, flex layout, Download All Photos, footer restructure, Slab Guard in fallback notes, debug strip hidden, photos section cleanup)
- `whatnot_description.py` — Updated function signature for assessment_id/registry_serial, added `_append_sw_ids()` helper
- `routes/whatnot.py` — Pass through assessment_id and registry_serial to content generator
- `routes/collection.py` — LEFT JOIN comic_registry for registry_serial
- `TODO.md` — Updated to Session 78
- `WHERE_WE_LEFT_OFF.md` — Updated to Session 78

### What's Next (Priority Order)
1. **Git push + deploy** — all Session 78 changes need pushing (see deploy checklist below)
2. **Test marketplace prep on production** — Download All Photos, Copy All, Slab Guard serial for registered comics, other platforms (Mercari, Facebook, Heritage), raw vs slabbed comics
3. **Test eBay draft + auction listings** — remaining from P1
4. **Upload FB assets to Facebook page** — profile pic + cover photo ready in SW folder
5. **Facebook page go-live** — finish setup
6. **Remove debug strip HTML** — currently hidden but still in DOM

### Deploy Checklist
```
git add collection.html whatnot_description.py routes/whatnot.py routes/collection.py TODO.md WHERE_WE_LEFT_OFF.md ; git commit -m "Fix invisible text in marketplace modal + Slab Guard verify URL + UI polish" ; git push
```
Then: deploy on Render, purge Cloudflare cache.

---

## Session 77 (Mar 5, 2026) — Facebook Page Assets + FMV is_slabbed Fix

### Facebook Page Assets — FINAL Versions Ready
Working with Sonnet 4.6 on Facebook page setup; Opus handling asset creation.
Multiple iterations throughout session — started with generated collages, evolved to real photos.

**Profile Picture (170px + 512px) — FINAL:**
- Mike's real comic collection photo (Punisher #1, Secret Wars #8, X-Men, Wolverine, etc.) as circle-cropped background
- Light purple tint overlay (~30%) to tie to brand
- SW favicon (purple circle, gold "SW") centered on top with dark backdrop behind it
- Gold ring border
- Files: `slab-worthy-fb-profile-512.png`, `slab-worthy-fb-profile-170.png`

**Cover Photo (820x462) — FINAL:**
- Real comic collection photo as full-bleed background with heavy dark overlay (~87%) for subtle texture
- "$LAB WORTHY™" wordmark in gold Bangers font, centered on left half, large and readable
- Tagline: "Know what your collection is worth." + "AI-Powered Comic Grading & Valuation"
- Real app screenshot (Hulk #340 grading report) in phone frame on right side
- Shows actual product: grade circle, "KEEP IT RAW" verdict, FMV values, grade breakdown, defects
- File: `slab-worthy-fb-cover-final.png`

**Also generated (earlier iterations, kept for reference):**
- `slab-worthy-fb-cover-premium.png` — Comic collage overlay version (no screenshot)
- `slab-worthy-fb-cover-4boxes.png`, `slab-worthy-fb-cover-5boxes.png` — Feature box layouts
- `slab-worthy-mobile-mockup.png` — Full mobile mockup of grading report (X-Men #94 at 8.5)
- `slab-worthy-report-512.png`, `slab-worthy-report-170.png` — Mockup square crops

### FMV is_slabbed Bug Fixed (Session 76)
**Problem:** Collection list showed $21.84 (raw_value) but Whatnot modal showed $32.76 (slabbed_value || raw_value) for the same comic.

**Backend fix (`routes/collection.py`):**
- Added `is_slabbed, slab_cert_number, slab_company, slab_grade, slab_label_type` to SELECT query

**Frontend fix (`collection.html` — 6 locations):**
- Collection list FMV column
- Detail view (added "FMV (Slabbed)"/"FMV (Raw)" labels)
- Marketplace prep modal fallback price
- Marketplace AI generation price
- eBay auction hint
- eBay listing suggested price
- All now use: `comic.is_slabbed ? (slabbed_value || raw_value) : raw_value`

### Marketplace Prep Modal Photo Fix (Session 76)
**Problem:** Photos not populating for Whatnot and other non-eBay platforms.
**Root cause:** Modal used `mpComic.front_image` (flat) but API returns `comic.photos.front` (nested).
**Fix:** Added `const mpPhotos = mpComic.photos || {};` and updated 3 locations (preview, photo grid, debug).

### Files Modified (Sessions 76-77)
- `collection.html` — FMV is_slabbed fix (6 locations) + marketplace modal photo fix (3 locations)
- `routes/collection.py` — Added slab fields to SELECT query
- `TODO.md` — Updated to Session 77
- `WHERE_WE_LEFT_OFF.md` — Updated to Session 77
- New FB assets (final): `slab-worthy-fb-profile-512.png`, `slab-worthy-fb-profile-170.png`, `slab-worthy-fb-cover-final.png`
- New FB assets (drafts): `slab-worthy-fb-cover-premium.png`, `slab-worthy-fb-cover-4boxes.png`, `slab-worthy-fb-cover-5boxes.png`
- New mockup: `slab-worthy-mobile-mockup.png`, `slab-worthy-report-512.png`, `slab-worthy-report-170.png`
- Mike's comic photos in: `FBCoverrImages/` folder (4 WhatsApp photos + Hulk #340 screenshot)

### What's Next (Priority Order)
1. **Upload FB assets to Facebook page** — profile pic + cover photo are ready in SW folder
2. **Facebook page go-live** — finish setup with Sonnet 4.6
3. **Consider swapping cover screenshot** — use a "WORTH THE SLAB" result instead of "KEEP IT RAW" for more aspirational first impression
4. **Test marketplace prep on production** — verify photo slots, FMV values, AI content for Whatnot/Mercari/Facebook
5. **Test eBay draft + auction listings** — remaining eBay e2e items
6. **Git push latest changes** — `collection.html`, `routes/collection.py`, `TODO.md`, `WHERE_WE_LEFT_OFF.md`

### Deploy Checklist
Code needs git push: `collection.html`, `routes/collection.py`
```
git add collection.html routes/collection.py TODO.md WHERE_WE_LEFT_OFF.md ; git commit -m "Fix FMV is_slabbed display + marketplace modal photos + update docs" ; git push
```
Then: deploy on Render, purge Cloudflare cache.

---

## Session 75 (Mar 4, 2026) — eBay Username Root Cause + Favicon Redesign

### eBay Username Bug — Root Cause Found & Fixed
**The mystery is solved:** OAuth scopes were missing `commerce.identity.readonly`.
- The eBay Identity API requires this scope to call `/commerce/identity/v1/user/`
- Without it, the API returned 403 — caught silently by try/except, username never saved
- The backfill in `/api/ebay/status` also failed for the same reason
- **Fix:** Added `commerce.identity.readonly` to `EBAY_SCOPES` in `ebay_oauth.py`
- Changed fallback text from "user" to "Connected" in collection.html and modal-ebay-listing.html
- **Action required:** Mike needs to disconnect and reconnect eBay after deploying to get a new token with the updated scope

### Favicon Redesign (In Progress)
- Current favicon: circle with gradient bg + gradient gold text → blurry/unreadable at 16px
- Created `favicon-options.html` comparison page with 6 options at 64/32/16px + tab simulations
- Options include: solid indigo, purple, dark bg, gradient bg — with white or gold text
- Both dark and light tab bar simulations included
- **Waiting for Mike's pick** before replacing `favicon.svg`

### Code Review: Draft + Auction Flows
- Reviewed `ebay_listing.py` `create_listing()` — draft flow (publish=False) creates inventory item + offer but skips publish, returns Seller Hub drafts URL
- Auction flow sends `start_price`, `auction_duration`, `reserve_price`, `buy_it_now_price` with proper validation
- Frontend `createListing(false)` for draft, `createListing(true)` for publish — both look clean
- No bugs found in code review — ready for live testing

### Files Modified This Session
- `ebay_oauth.py` — Added `commerce.identity.readonly` to EBAY_SCOPES
- `collection.html` — Changed username fallback from "user" to "Connected"
- `modal-ebay-listing.html` — Fixed `data.username` → `data.ebay_username`, fallback "Connected"
- `favicon-options.html` — New comparison page (6 favicon options)

### What's Next (Priority Order)
1. **Deploy + reconnect eBay** — verify username now displays correctly
2. **Pick favicon** — Mike to choose from options page, then replace favicon.svg
3. **Test fixed-price draft listing** — click "Save as Draft" instead of Publish
4. **Test auction listing** — toggle to Auction, set starting bid, duration, reserve, BIN
5. **Plan Whatnot integration** — research seller tools, design "Prep for Whatnot" feature
6. **Valuation endpoint testing** — 12-case test plan
7. **Mobile testing** — full grading flow on real devices

---

## Session 74 (Mar 4, 2026) — eBay Listing E2E: First Successful Publish!

### Major Milestone
**First successful eBay listing published via Slab Worthy!**
- Listing URL: https://www.ebay.com/itm/147183901233
- All 4 photos uploaded successfully via R2 proxy → eBay createImageFromUrl
- AI-generated description with Slab Worthy Assessment ID footer
- KEY ISSUE detection in listing titles working

### Bugs Fixed This Session (7 commits)

**1. eBay username not saving after OAuth (`routes/ebay.py`):**
- Added eBay Identity API call (`/commerce/identity/v1/user/`) in OAuth callback
- Saves username via `save_ebay_user_id()` after token exchange
- Added backfill logic in `/api/ebay/status` — if DB has no username, fetches from API and saves (self-healing for existing connections)

**2. OAuth callback redirect (`routes/ebay.py`):**
- Changed redirect from `{FRONTEND_URL}?ebay=connected` → `{FRONTEND_URL}/account.html?ebay=connected`
- Fixed stale default FRONTEND_URL from `collectioncalc.com` → `slabworthy.com`

**3. Grade type crash causing 500 on /api/ebay/list (`ebay_listing.py`):**
- Root cause: `grade.upper()` fails when grade is numeric (8.5, 9.8 float from JSON)
- Lines 322-323 were OUTSIDE the try/except block, so error returned HTML not JSON
- Fix: Added NUMERIC_TO_LETTER mapping for all CGC grades → eBay condition codes
- Listing title shows original numeric grade (e.g. "9.8") for buyer clarity

**4. closeUserMenu null reference (`js/auth.js`):**
- `document.getElementById('userMenuDropdown')` returns null on pages without the element
- Fix: added null check (`if (dropdown) dropdown.classList.remove(...)`)

**5. eBay URL policy violation (`collection.html`):**
- eBay flagged listings with slabworthy.com URL as "Offering to buy/sell outside eBay"
- Changed footer from full URL to just: `Slab Worthy™ Assessment ID: {id}`

**6. KEY ISSUE in listing title (`ebay_listing.py` + `collection.html`):**
- Frontend: after AI generates description, detects "KEY ISSUE" and updates title field
  e.g. "Iron Man #7 KEY ISSUE Comic Book - 6.5"
- User can still manually edit title before publishing
- Backend: accepts `listing_title` from frontend, uses it if provided

**7. Frontend title synced to backend (`routes/ebay.py` + `ebay_listing.py`):**
- Frontend sends user-editable `listingTitle` as `listing_title` in API call
- Backend uses provided title instead of auto-generating (respects user edits)
- Fallback auto-generation still works if no title provided

---

## Session 73 (Mar 3, 2026) — eBay Image Upload Debug Marathon

### Context
AWS UAE data center was struck by objects (drone/missile) on March 1, causing AWS outages
that affected Anthropic/Claude infrastructure throughout this session.

### What We Fixed
- Fixed photo URL mismatch (`currentComic.photos.*` vs flat properties)
- Fixed CORS by switching to server-side R2 proxy fetch
- Added `sell.marketing` OAuth scope
- Added disconnect endpoint + Connected Accounts UI to account.html
- Confirmed sidebar + footer working across all pages
