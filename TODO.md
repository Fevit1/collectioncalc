# Slab Worthy — Master To-Do List
**Updated:** June 19, 2026 (Session 107)
**Target:** GalaxyCon San Jose Alpha Launch — Aug 21-23, 2026 (~24 weeks out)
**Soft Launch:** July 21, 2026 (~20 weeks out)
**Founder:** Mike Berry — estimates assume ~15-20 hrs/week on Slab Worthy
**First Hire:** Marketing + Front-End Design (planned)

**Estimation notes:**
- Claude coding sessions: estimated at 2x speed (we consistently deliver faster than expected)
- ⏱ = estimated session time (Claude + Mike working together)
- 👤 = Mike-only time (testing on devices, business tasks, manual work)
- 🔗 = dependency on another task
- ⚠️ = testing-heavy (may take longer — depends on Mike's device time)

---

## 🚦 OPEN — LAUNCH-READINESS CAPTURE (Sessions 101–104)

**Launch posture (decided):** public beta = **GATED / BATCHED** — keep `require_approved` + waitlist + beta codes, admit users in waves. **HARD gates:** billing end-to-end + valuation/identification honesty. Core-flow/mobile fixes are buffered by the gated intake (not hard blockers).

- [x] ~~**1. Identification trustworthiness build**~~ ✅ SHIPPED & VERIFIED (Session 105, Jun 16) — extraction flip Haiku→Sonnet (verified live on Absolute Batman #19 / Atari Force #4) + honesty gate (always-editable ID field, `|| '1'` default removed, server `issue_required` belt in `sales_valuation.py` so an unknown issue is never priced). Grade shows; valuation/verdict HALT on unknown issue. Happy path verified on mobile.
- [x] ~~**Re-grade hang (re-submit identical photos → ~5 min → "Could not identify")**~~ ✅ ROOT-CAUSED & FIXED (Session 105) — was the post-grade signature **auto-fire** (Opus, rate-limit-constrained) racing the next extract, not image-identity/dedup. Disconnected the auto-fire (Commit 1, `app.html`); signature pipeline fully preserved. Verified: quick re-grade no longer hangs. Blast radius was Guard/Dealer/admin only (Free/Pro get an instant 403, zero Opus work).
- [x] ~~**Extraction resilience (Commit 2)**~~ ✅ SHIPPED (Session 106, Jun 18) — `comic_extraction.py` client `timeout=30.0/max_retries=1` + `app.html` `/api/extract` AbortController (75s, try/finally) + honest "Our identifier is busy right now" copy on backend timeout (Request timed out / 503 / 504 / overloaded) AND client AbortError. Deployed + purged.
- [x] ~~**Tier Honesty Pass (Section D reconciliation → commits A–D)**~~ ✅ SHIPPED (Session 106) — storefront now matches the product. **A:** per-tier grading cap wired to PLANS (`billing.py` + `grading.py`) — Free 25 / Pro 100 / Guard 250 / Dealer 1000, admins exempt, live `gradings_this_month` counter; verified `/api/billing/plans`. **B:** `fetchImageAsBase64` `response.ok` guard (`js/utils.js`) — honest "Couldn't load image" (surfaced the real ID Sigs CORS bug, #4). **C:** `pricing.html` honesty — real caps (no "Unlimited"), export trimmed, Dealer "Coming Soon"/Notify-Me (no checkout), Guard ownership-certs removed, Signature ID surfaced as Guard coming-soon. **D:** `create-checkout` refuses `plan='dealer'` server-side (coming-soon enforced, not just displayed). All deployed + purged.
- [ ] **"0 used" usage meter bug** (freemium pass) — `account.html` reads the DEAD `valuations_this_month` counter (always shows 0); real enforcement uses `gradings_this_month`. Reconcile the meter to the live counter. Not a launch blocker.
- [ ] **Stale PLANS config booleans** (low priority) — `export` / `api_access` / `ownership_certificates` still read `true` for some tiers in `PLANS` but are read by nothing (dead flags). Trimmed from the PAGE already (Session 106); tidy the dead config so it doesn't mislead a future dev.
- [ ] **Freemium upgrade-prompt mechanic** (freemium pass) — the only paywall that fires in normal use is the 4th Slab Guard registration; the grading-cap over-limit returns **429 but no upgrade CTA**. Decide the intended conversion moment(s) and wire prompts. The Free→paid conversion mechanic effectively doesn't exist yet.
- [ ] **Dealer webhook hardening** (optional, low priority) — `handle_checkout_completed` still accepts any plan string; harmless now (no route starts a Dealer checkout after Commit D), tidy later.
- [ ] **Signatures v2 — when it ships** (deferred; full design in `docs/technical/SIGNATURES_V2_DESIGN.md`). Grouped: (a) **detection gate** — add an "is a signature visually present?" step before attribution (mirror `routes/signatures.py` Step-1 → abstain at 0); this is the **false-positive correctness fix** (Alex-Ross-on-unsigned-cover) AND a cost saver. ⚠️ NB "abstain on zero pre-filter candidates" is the WRONG lever (pre-filter is era/publisher creator-narrowing, not signature detection). (b) decoupled **user-initiated** delivery (collection-based, not auto on every grade); (c) confidence-verify UX ("we're N% confident — confirm?"); (d) tier-gated **visibility** (don't show the control to Free/Pro); (e) threshold alignment (frontend 0.40 → server floor 0.50, `LOW_CONFIDENCE_THRESHOLD`); (f) multi-signature handling (later).
- [ ] **Year/edition not in the valuation comp-query key** (architecture item, post-launch) — `/api/sales/valuation` filters on title+issue+issue_type only; `year` affects only the CGC fee tier + the no-data fallback estimate, never comp selection (confirmed Session 105 via the Giant-Size X-Men #1 1975→1976 test = identical output). Same root cause as the X-Men #1 edition blending (1963 vs 1991 vs 2024 collapse to "X-Men #1"). Needs a year/edition/volume axis in the comp query + tagged sales data.
- [ ] **Admin Feedback tab truncates comments (~100 chars)** — can't read full user bug reports in the admin Feedback view. Widen/expand the comment display.
- [x] ~~**Grade-submission retention — persist + admin find/delete**~~ ✅ DRAFTED (Session 107, awaiting Mike's git/deploy) — privacy disclosure LIVE (privacy.html) unblocked the build. `migrations/add_grade_submissions.sql` (new table) + `grade_retention.py` (background persist after the grade response, no added latency; cascade-delete + erasure helpers) + `/api/grade` persist hook + admin `/api/admin/grade-submissions` find/view (presigned R2 image URLs) & DELETE (cascades DB row **and** R2 objects) + admin.html "🔬 Grade Subs" tab & one-click hook from Feedback. Design: `docs/technical/GRADE_RETENTION_SPEC.md`. NB: `reread_fired` column is **N/A/NULL** (no 180° re-read in grading). Follow-up: backlink `saved_collection_id` on save (currently always NULL — small wire-up in the collection-save path).
- [ ] ⏰ **Grade-retention 90-day PURGE (fast-follow — HARD DEADLINE ~2026-09-17)** — the auto-purge is NOT in the persist pass above. **Deadline: before the first persisted grade submission turns 90 days old** — persist deployed 2026-06-19, so **~2026-09-17** (comfortably AFTER soft launch Jul 21 + GalaxyCon Aug 21-23 — no launch-crunch competition, but a real published-policy obligation; don't slip the date). Without it our LIVE privacy promise ("retained up to 90 days then deleted") becomes false (retain-forever). Mechanism: scheduled job deletes `grade_submissions` rows **and their R2 objects** where `images_purge_after < now()` AND `pinned = FALSE` (reuse `grade_retention.delete_grade_submission`; the `idx_grade_submissions_purge` index + `images_purge_after`/`pinned` columns already exist). Pin rule: when a user files grading feedback, set `pinned = TRUE` on their recent submissions so a complaint's evidence survives.
- [x] ~~**Section E billing PREP — runbook + read-only pre-flight**~~ ✅ DONE & GREEN (Session 107) — `docs/technical/STRIPE_TEST_BILLING_RUNBOOK.md` (setup map + safe test runbook) + `scripts/stripe_preflight.py` (read-only: `Price.retrieve` + `WebhookEndpoint.list` + optional `--check-db` SELECT). Pre-flight passes GREEN in Render shell: key=TEST; all 4 prices resolve `livemode=False` (Pro $4.99/$49.99, Guard $9.99/$89.99); webhook endpoint enabled at `/api/billing/webhook` with all required events. **Item #2 (webhook signing secret == Render `STRIPE_WEBHOOK_SECRET`) now MANUALLY VERIFIED → all 3 config items confirmed; Section E config FULLY verified, next session is the LIVE TEST ONLY.** Lessons L-SW-2026-004 (Render env change needs redeploy + fresh shell) and L-SW-2026-005 (read-only pre-flight before billing ops) logged.
- [ ] **~30s comic-ID progress messaging** — staged honest "still working" messaging during the ~30s identification wait (messaging ONLY — no accuracy-costing speedups). Brief drafted, not yet shipped. Queued.
- [ ] **Email setup (mike@/support@slabworthy.com)** — Resend is **outbound-only**; no real inbox confirmed. **Gates the matbanshee reply** (and any inbound support). Deliberately held — not started.
- [x] ~~**Data deletion-request runbook**~~ ✅ WRITTEN & COMMITTED (Session 107) — `docs/SW_deletion_request_runbook.md`. Manual erasure procedure that pairs with the admin grade-submission delete tool until the 90-day purge automates the time-based side: verify requester by registered-email ownership (confirm-to-account-email on mismatch), scope incl. unsaved grade submissions, delete with R2 cascade (R2 first, then rows), confirm `images_deleted`, confirm back, within 30 days, never auto-delete. (Earlier "not found in repo" flag resolved — it didn't exist; now drafted fresh.)
- [ ] **2. CGC cost-sourcing investigation** (read-only, not yet started) — slab-ROI integrity. How does the slab-ROI calc source CGC grading costs — hardcoded, scraped, or DB table? Is the method robust or silently stale? Is it registered in `dependency_monitor.py`? Is the cost-**tier** selection correct for a book's value? (Relates to the parked "Automated CGC price checker" feature under P5, but this is the read-only audit of the *current* sourcing first.)
- [ ] **3. Readiness pass — Sections E–F UN-RUN** ⚠️ — **← NEXT SESSION OPENER (Section E billing E2E, Stripe TEST mode, using the Stripe test-mode setup map + safe billing runbook).** A–D done. **D (tier gates) run Session 106** → drove the Tier Honesty Pass (above). Remaining: **E** billing end-to-end (the HARD gate — ⚠️ Checkout footgun: `create-checkout` writes `stripe_customer_id` immediately; **never** run real Checkout/portal from a `test-*` account — webhooks then clobber the tier) — **likely next session's opener**; **F** mobile + load.
- [ ] **4. ID Sigs CORS image-fetch bug** — DIAGNOSED Session 106; queued to **Signatures v2** bucket; **NOT a launch blocker** (ID Sigs is coming-soon / unreachable from upload). The `response.ok` gap is **FIXED** (Commit B) — honest errors now surface. The *remaining* failure is **cross-origin CORS**: `<img>` display is CORS-exempt but `fetch()→blob()` is enforced, and `img.slabworthy.com` doesn't reliably return ACAO for the page origin (+ uncached fetch → R2 origin 503). Same URL for thumbnail and fetch (mismatch ruled out). **Preferred fix = server-side image fetch** in `/api/signatures/v2/match` (accept `comic_id`/URL). Full diagnosis in `docs/technical/SIGNATURES_V2_DESIGN.md` ("Image-fetch (CORS)" section + build-checklist item 7).

### Section C (collection management) — findings (Session ~104)
- [ ] **MUST-FIX before public: DELETE has no confirmation** — trash icon deletes a comic immediately, no "are you sure?", no undo. Accidental data loss (esp. mobile mis-tap) is a trust-breaker for a collection product. Add a confirm dialog — small, standard, land before public beta.
- [ ] **DECISION: comic detail view not built** — clicking a comic row does nothing (confirmed across comics/accounts), but the row LOOKS clickable → a stranger reads "broken," not "not offered." Either build the detail view OR neutralize the click affordance. **Minimum launch fix = stop implying it exists.**
- ✅ **Verified working (no action):** covers load from img.slabworthy.com (slightly slow on cold load w/ many; edge cache handles repeats); sort/filter/search; Slab Guard registration; eBay listing (saved-item path) + Whatnot content gen; Edit MY VAL. Era filter intentionally removed (stale checklist item).
- [ ] **5. Resilience gap (model audit, June 15)** — 8 of 12 model call sites pass static constants with NO `call_with_fallback` (Chrome vision, signature v1/v2, Slab Guard CV, eBay gen, admin); they'd break with no auto-fallback if a head model string retires. Harden later via `call_with_fallback`. Not urgent.

### 🟡 Polish (grade-results / UX, captured Sessions 101–104)
- [ ] Grade-results page shows "**Slab Worthy" twice** + a blank image area; **thumbs/comment appear before the grade returns** — move them to after the grade; consider dropping "add comment" (Feedback widget already exists).
- [ ] **"Photo too small" error doesn't say WHICH photo** — name the offending photo (front/back/spine/centerfold).
- [ ] **Duplicate "grade a comic" link** on the landing page — de-dupe.
- [ ] **Grade-presentation honesty / confidence surfacing** — show the user the internal confidence and which angles were/weren't visible, so a single-photo or partial-angle grade is **labeled as such** (e.g. "graded from front only — lower confidence") instead of presented as authoritative. Ties to grade-submission retention (`docs/technical/GRADE_RETENTION_SPEC.md` §6): retention is what makes accuracy improvable; honest confidence is what sets user expectations at grade time. Pairs with the matbanshee finding (old-photo confound). Consider an explicit "obstruction/glare" caveat given the grader has no obstruction penalty today.

---

## ✅ DONE (Session 64-81)

- [x] **Signature DB expanded 43 → 100 creators** — Session 86: Selected 57 new creators with weighted criteria + confusion risk screening. SQL migration, JSON entries, seed script, UI fix, verification queries all created. Pending: run migration on Render, then upload reference images via admin UI.
- [x] **Signature orchestrator v2 integrated** — Session 84: Integrated orchestrator into repo with 7 fixes (cs.creator_name, removed cs.slug, HTTP R2 fetch, os.environ DB URL, auth decorators, init_modules pattern, removed unused imports). Registered blueprint in wsgi.py. Created seed_creator_metadata.py (41 creators). Created prompts/signature_identification_system.md. Two-stage Haiku prefilter tested and reverted (52.2% accuracy). Pre-deploy: needs migrations + seed + deploy.
- [x] **Signature matching accuracy improvements** — Session 82: Improved cross-validation from 73.9% → 78.3% (17/23 → 18/23). Added multi-reference images (2 per artist), forensic expert system prompt, preferred_images curation for all 23 artists, fixed cross-validation data leakage bug. Jim Lee now correctly identified (was misidentified as Grant Morrison). Target 87%+ still needs style_notes fix + better reference images.
- [x] **Refactor collection.html into modular files** — Session 81: Split 3,925-line monolith into 5 files: collection.html (410 lines, HTML shell), collection.css (1,745 lines), collection.js (922 lines), ebay-modal.js (453 lines), marketplace-modal.js (406 lines). Fixed duplicate sortSelect IDs — list and gallery views now have separate sort dropdowns that show/hide on view toggle.
- [x] **Register/Stolen E2E test passed** — Session 80: Full state machine tested on production (register → stolen → recovered → verify page behavior). All transitions working correctly.
- [x] **Sell button brand fix** — Session 80: Changed from gradient to dark fill with brand-purple border/text to match other buttons.
- [x] **Guard serial readability** — Session 80: Increased font size (0.65→0.8rem), opacity (0.7→0.9), added font-weight 600.
- [x] **Remove all guard modals** — Session 80: Replaced alert()/confirm() in registerComic, reportStolenComic, markRecoveredComic with inline button state changes. Chrome extension can't interact with native modals.
- [x] **Animated ellipsis during registration** — Session 80: CSS keyframes with steps(4, end), pointer-events disabled while processing.
- [x] **Sighting notifications in My Collection** — Session 80: Red badge on guard button showing count, "View Sightings" dropdown link. New sightings.html page with owner response buttons.
- [x] **Year 1 P&L projection** — Session 80: Full startup P&L (comics + baseball cards, 15K users, employee + marketing). $739K revenue, $379K profit, 51% net margin. File: `docs/business/SlabWorthy_Year1_PnL.xlsx`.
- [x] **TAM analysis** — Session 80: Comic collectors ~2-5M, card collectors ~15-20M households. 15K user target is <0.1% penetration (very achievable). Shop targets aggressive for Y1.
- [x] **Whatnot modal crash fix** — Session 79: Removed dead `mpPhotoHint` JS reference that crashed `openMarketplacePrepModal()`. Added null safety (`?.`) to `copyMpField()` and `copyAllMp()`.
- [x] **Human-friendly verify page** — Session 79: Verify links now point to `slabworthy.com/verify.html?serial=SW-2026-XXXXX` instead of raw API JSON. Auto-lookup on page load via GET (no Turnstile needed for direct links). Updated URLs in both `whatnot_description.py` and `collection.html` fallback notes.
- [x] **Cover image EXIF rotation fix** — Session 79: Added `ImageOps.exif_transpose()` to `watermark_image()` in `verify.py`. Phone photos now display correctly oriented on the verify page.
- [x] **Register + Report Stolen buttons** — Session 79: Collection page now shows conditional guard buttons per comic: 🛡️ Register (unregistered) → 🚨 Report Stolen (active) → ✅ Recovered (stolen). Both list and gallery views. New API endpoints: `POST /api/registry/report-stolen/<comic_id>` and `POST /api/registry/mark-recovered/<comic_id>`.
- [x] **Verify page sighting restriction** — Session 79: "Report a Sighting" section now only shows for stolen comics, not active ones.
- [x] **Collection API enhanced** — Session 79: Added `registry_status` and `registry_date` to collection response via LEFT JOIN.
- [x] **Facebook page assets created** — Session 77: Profile pic (170px + 512px) with "$LAB WORTHY" in Bangers font, gold on dark circle. Cover photo (820x462) with comic-panel collage background, purple overlay, gold wordmark + tagline. Multiple iterations refined with user feedback.
- [x] **FMV is_slabbed fix** — Session 76: Collection list always showed `raw_value` even for slabbed comics. Backend fix: added `is_slabbed, slab_cert_number, slab_company, slab_grade, slab_label_type` to SELECT query in `collection.py`. Frontend fix: all 6 FMV references now check `comic.is_slabbed` to show `slabbed_value` or `raw_value` correctly. Labels show "FMV (Slabbed)" or "FMV (Raw)" in detail view.
- [x] **Marketplace prep modal photo fix** — Session 76: Modal used flat properties (`mpComic.front_image`) but API returns nested `comic.photos.front`. Fixed 3 locations: preview image, photo grid slots, debug logging. All 8 non-eBay platforms (Whatnot, Mercari, Facebook, Heritage, ComicConnect, MyComicShop, COMC, Hip Comics) now populate photos correctly.
- [x] **Favicon selected and deployed** — Session 76: Mike picked favicon from options page.
- [x] **Deploy + verify** — Session 76: Code deployed to production.
- [x] **CGC pricing update** — Session 76: Updated hardcoded CGC grading costs.
- [x] **AI grading improvements** — Session 76: Grading consistency improved (needs continued testing).
- [x] **First successful eBay listing published!** — Session 74: Fixed grade type crash (numeric grades like 8.5 crashed `.upper()`), added NUMERIC_TO_LETTER mapping for all CGC grades. Fixed eBay URL policy violation (removed external URL from description). Added KEY ISSUE detection in listing titles. Synced frontend editable title to backend. Fixed OAuth callback redirect to account.html. Added eBay Identity API username fetch. Fixed closeUserMenu null reference.
- [x] **eBay listing image upload fixes** — Session 73: Fixed photo URL mismatch (currentComic.photos.* vs flat properties). Fixed CORS by switching to server-side R2 proxy fetch. Added sell.marketing OAuth scope. Added disconnect endpoint + Connected Accounts UI to account.html.
- [x] **Test sidebar + footer across all pages** ✅ Session 73
- [x] **eBay OAuth + listing bug fixes** — Session 72: Fixed connectToEbay() missing JWT header (was bare window.location.href → now fetches auth URL with Bearer token then redirects). Fixed image upload mismatch (FormData → base64 JSON frontend, added base64 decode in backend). Fixed stale CollectionCalc branding in ebay_listing.py (4 references → Slab Worthy). Updated eBay Developer Portal RuName callback URLs to collectioncalc-docker.onrender.com.
- [x] **Shared sidebar component (`js/sidebar.js`)** — Session 71: Extracted sidebar into single source of truth. All 6 auth pages (dashboard, app, collection, account, admin, signatures) now use shared component. sw- prefixed CSS, auto-detect active page, admin-conditional items. ~400 lines removed from dashboard.html.
- [x] **Logged-in dashboard with collapsible sidebar** — Session 70: New `dashboard.html` as post-login landing page. Collapsible sidebar nav (remembers state), real portfolio stats from collection API, top 5 most valuable comics, market movers (sample data), empty state, mobile drawer nav. Login redirect updated.
- [x] **SVG favicon** — Session 70: Created `favicon.svg` (purple/gold SW), added to all 17 HTML pages.
- [x] **README.md rewrite** — Session 70: Was still "CollectionCalc/SQLite/portfolio project". Now accurately documents Slab Worthy.
- [x] **Sortable collection columns** — Session 69: All list view columns (Title, Year, Issue, Grade, FMV, My Valuation) are clickable to sort ascending/descending with arrow indicators.
- [x] **Optimistic delete UI** — Session 69: Collection delete now removes row instantly (150ms fade), API fires in background. Rollback on failure with toast notification.
- [x] **Smart delete confirmation** — Session 69: Custom modal with "Don't show this warning again" checkbox replaces browser confirm(). Preference stored in localStorage.
- [x] **Fix collection delete FK cascade** — Session 69: SAVEPOINT-based cascade delete handles FK constraints across comic_registry, sighting_reports, match_reports tables.
- [x] **Documentation overhaul** — Session 69: Rewrote DATABASE_PRODUCTION.md (16 tables), ROUTE_MAPPING.md (87 routes), updated COMIC_REGISTRY_SCHEMA.md + API_REFERENCE.md.
- [x] **Signature image delete visibility** — Session 69: Made per-image delete button always visible (was hidden behind hover).
- [x] **Auction price validation** — Session 69: Client-side validation for price relationships (reserve > start, BIN > reserve).
- [x] **Signature page deletion** — Session 69: Added "Delete Creator" button + backend DELETE endpoint. Cascading delete removes all reference images.
- [x] **eBay auction listing support** — Session 69: Added Fixed Price / Auction format toggle to listing modal. Auction fields: starting bid, duration (1-10 days), reserve price, Buy It Now. Backend + route + UI all updated. Backward compatible.
- [x] **Push Session 65 code** — Done by Mike.
- [x] **Homepage Sign In / Sign Up** — Session 68b: Added top-right auth nav to hero (Option A). Gold "Sign Up" pill + "Sign In" text link. Zero impact on hero layout.
- [x] **Valuation endpoint upgrade** — Session 68b: Applied premium analysis methodology to `/api/sales/valuation`. Replaced arithmetic mean with median + 5% outlier trimming + bootstrap 95% CI. All existing response fields preserved, new `ci_95_low`/`ci_95_high` additive. No frontend changes needed.
- [x] **Signed premium analysis engine** — Session 68: Professional-grade methodology with time-windowed comps (±90 days), log-transform geometric mean, bootstrap 95% CI, percentile outlier trimming. Result: signing adds +40-57% to value, 95% CI [+27%, +59%], 72% positive. Deployed and tested on production.
- [x] **Title year extraction (collision fix)** — Session 68: Added `title_year` column, server-side SQL backfill (62.5% coverage), collisions dropped from hundreds to 4. Deployed and migrated.
- [x] **Signature matching system v1** — Session 68: Reference DB (23 artists, 97 images), Flask blueprint (4 endpoints), standalone CLI matcher, production test suite. Deployed and verified.
- [x] **Title normalizer backfill** — Session 68: 376 NULLs all edge cases (lot numbers, non-comics). Not actionable.
- [x] **Upgrade valuation on grading results** — Session 67: Switched from grade-blind `/api/sales/fmv` to grade-specific `/api/sales/valuation` with interpolation, fallback estimates, confidence indicator
- [x] **Grading flow polish** — Session 67: Confirmed all items done (delay removed S66, instructions not needed, Grade Another already exists, valuation now wired)
- [x] **Fix AI grading inconsistency** — Session 66: Rebuilt from holistic to structured 8-category scoring. New `grading_engine.py`, `/api/grade` endpoint, multi-run support. Unit tests passing.
- [x] **File signature identification patent** — Application # 63/990,743, Feb 25, 2026
- [x] **Push Session 64 code** — Waitlist pages, confirmation flow
- [x] **Test all waitlist pages on production** — All 4 passing

---

## P0 — THE CREDIBILITY FIX (Next 2 weeks)

> If someone grades the same comic twice at your booth and gets different numbers, nothing else matters.

- [x] ~~**Fix AI grading inconsistency**~~ ✅ Session 66
- [x] ~~**Update hardcoded CGC grading costs**~~ ✅ Session 66
- [x] ~~**Push Session 65 code**~~ ✅ Done

---

## P1 — COLLECTION & SELLING TOOLS (Weeks 3-6, March)

> Make the collection page a selling powerhouse. Grade → value → list → sell.

### Product

- [x] ~~**eBay auction listing support**~~ ✅ Session 69
- [x] ~~**Signature page deletion**~~ ✅ Session 69

- [x] ~~**Test sidebar + footer across all pages**~~ ✅ Session 73 (confirmed working)
  - Sidebar renders correctly on all 6 auth pages (dashboard, app, collection, account, admin, signatures)
  - Collapse/expand works and persists across page navigations
  - Active page highlighting correct on each page
  - Admin-only items hidden for non-admin users
  - Mobile drawer works on <900px
  - Footer still renders on all public pages (index, login, faq, pricing, about, contact, etc.)
  - No CSS conflicts or layout breaks

- [ ] **eBay listing end-to-end test** 👤⏱ 1 session ⚠️
  - ✅ OAuth flow working (Session 72)
  - ✅ Image upload via R2 proxy working (Session 73-74)
  - ✅ Fixed-price publish working — first listing live! (Session 74)
  - ✅ KEY ISSUE detection in titles working (Session 74)
  - ✅ AI description generation working (Session 74)
  - ✅ eBay username root cause found & fixed (Session 75)
  - ✅ Favicon picked + deployed (Session 76)
  - 🔜 Test fixed-price draft listing
  - 🔜 Test auction listing (all field combos)

- [x] ~~**Multi-platform marketplace prep**~~ ✅ Session 76-78
  - Whatnot, Mercari, Facebook, Heritage, ComicConnect, MyComicShop, COMC, Hip Comics
  - AI content generation per platform via `/api/marketplace/generate-content`
  - Dedicated Whatnot endpoint `/api/whatnot/generate-content` with live-auction-optimized prompts
  - Photo population fixed (nested photos object)
  - FMV display fixed (is_slabbed-aware pricing)
  - Copy-to-clipboard for pasting into seller dashboards
  - ✅ Session 78: Fixed invisible text bug — replaced input/textarea with contenteditable divs (WebKit rendering issue)
  - ✅ Session 78: Fixed flex layout — copy buttons compact (36px), text fields full width
  - ✅ Session 78: Added "Download All Photos" button (downloads front/spine/back/centerfold sequentially)
  - ✅ Session 78: Added Slab Guard verification URL to show prep notes (if registered)
  - ✅ Session 78: Collection API now includes registry_serial via LEFT JOIN to comic_registry
  - ✅ Session 78: Cleaned up modal UI — removed redundant labels/hints, moved paste instructions below buttons

- [ ] **Test marketplace prep on production** 👤⏱ 30 min ⚠️
  - ✅ Whatnot text fields now populate and display correctly
  - ✅ AI content generating (confirmed via debug strip)
  - ✅ Session 79: Whatnot modal crash fixed (mpPhotoHint null ref)
  - ✅ Session 79: Verify links now human-friendly (auto-lookup on page load)
  - 🔜 Test Download All Photos button
  - 🔜 Test Copy All clipboard
  - 🔜 Verify Slab Guard serial appears for registered comics
  - 🔜 Test Mercari, Facebook, Heritage platforms
  - 🔜 Test with both raw and slabbed comics

- [x] ~~**Test Register + Report Stolen flow**~~ ✅ Session 80
  - ✅ Register an unregistered comic → serial SW-2026-JNZ5HR assigned
  - ✅ Report registered comic as stolen → status changed, button updated
  - ✅ Mark stolen comic as recovered → status changed, "Report Stolen Again" option
  - ✅ Visit verify page for stolen comic → "REPORTED STOLEN" badge + sighting form
  - ✅ Visit verify page for active comic → no sighting form (correct)
  - ✅ Cover image EXIF rotation working on verify page

### Testing ⚠️

- [ ] **Valuation endpoint testing** 👤⏱ 1 session
  - 12-case test plan (grade-specific FMV with slabbing ROI)
  - 🔗 Depends on: CGC cost update

- [x] ~~**Run title normalizer backfill**~~ ✅ Session 68

- [ ] **Mobile testing (full grading flow)** 👤 2-3 hours across devices ⚠️
  - Grading, collection, pricing, verify on real phones (Android + iOS)
  - Also test collection page responsive styles post-refactor (Session 81)
  - 🔗 Depends on: grading flow polish

- [ ] **Live Slab Guard registration test** 👤⏱ 1 session ⚠️
  - Register comic on production, verify fingerprinting
  - 🔗 No blockers

---

## P2 — LAUNCH PREP (Weeks 7-16, April-June)

> Build the moat and fill the pipeline. This is where Slab Worthy goes from "demo" to "product."

### Product

- [ ] **Integrate photo authenticity into Slab Guard** ⏱ 1-2 sessions
  - Wire photo_authenticity.py into registration endpoint
  - Store scores in DB, add to admin dashboard
  - Challenge flow for suspicious uploads
  - 🔗 Depends on: Live Slab Guard registration test

- [ ] **Signature identification v2 — deploy orchestrator** ⏱ 1 session
  - ✅ Reference DB built (43 artists, 172 images in R2)
  - ✅ API endpoints v1 built + deployed (match, db-stats, signed-sales, premium-analysis)
  - ✅ Session 82: Cross-validation 73.9% → 78.3% with multi-reference + system prompt + preferred_images
  - ✅ Session 82: Fixed cross-validation data leakage bug; Jim Lee, Jae Lee, Jim Steranko now correct
  - ✅ Session 83: Orchestrator v2 built (3-pass Opus 4.6, metadata pre-filter, parallel calls, aggregation)
  - ✅ Session 83: System prompt file written (prompts/signature_identification_system.md)
  - ✅ Session 83: DB migrations written (add_orchestrator_columns.sql + add_signature_identification_log.sql)
  - ✅ Session 84: Orchestrator integrated into repo with 7 integration fixes (column names, R2 HTTP fetch, auth decorators, init_modules pattern, removed boto3)
  - ✅ Session 84: Blueprint registered in wsgi.py (signatures_v2_bp)
  - ✅ Session 84: Seed script created (seed_creator_metadata.py — 41 creators with career dates, publishers, signature style)
  - ✅ Session 84: Two-stage Haiku prefilter tested and reverted (52.2% accuracy, 60.9% Haiku recall — not viable)
  - ✅ Session 84: Migrations run on Render PostgreSQL (columns + log table)
  - ✅ Session 84: Seed script run — 41 creators populated with metadata
  - ✅ Session 84: Code deployed to Render
  - ✅ Session 85: First v2 test — Jim Lee at 0.96 confidence (high)
  - ✅ Session 85: Fixed pass_count=1 bug (2/3 Opus passes silently failing; added retry + degraded_result flag)
  - ✅ Session 85: Sequential passes deployed — 3/3 passes working, 99s latency (rate limit: 30K tokens/min on Opus 4.6)
  - ✅ Session 86: Expanded signature DB from 43 → 100 creators (SQL migration + JSON + seed script + UI fix)
  - 🔜 Run migration on Render: `migrations/add_57_new_creators.sql`
  - 🔜 Run seed script for new creators: `python seed_creator_metadata.py <DATABASE_URL>`
  - 🔜 Upload reference images for 57 new creators via /signatures.html admin UI
  - 🔜 A/B test v1 vs v2 (curl test — no in-app UI yet)
  - 🔜 Fix style_notes metadata (Mike) + source better Bendis/Claremont reference images
  - 🔜 Target 87%+ accuracy before advertising signature feature

- [ ] **Sell Now Alerts v1** ⏱ 2 sessions
  - When incoming eBay sale exceeds FMV by >25%, alert users who own that title
  - Email + in-app badge on My Collection
  - Killer feature nobody else has
  - 🔗 Depends on: valuation endpoint working + data ramp

- [ ] **Data collection ramp** 👤 ongoing
  - More eBay/Whatnot sales for better valuations
  - Focus on GalaxyCon-relevant titles (popular at conventions)
  - No dependencies — can run anytime

- [ ] **Email drip for waitlist** ⏱ 1 session
  - 3-4 email sequence to keep waitlist warm pre-launch
  - Send every 3-4 weeks: feature previews, behind-the-scenes
  - 🔗 Depends on: having waitlist signups (start after marketing push)

- [x] **Test Haiku 4.5 for extraction** ⏱ 1 session — Session 90: Migrated to claude-haiku-4-5-20251001 (old model retired). Wired to call_with_fallback for auto-recovery. Mobile testing pending.
  - Run against 10-20 reference comics vs Sonnet
  - If quality is adequate, massive cost savings on API calls
  - No dependencies

- [ ] **Automated CGC price checker + admin approval** ⏱ 2-3 sessions
  - Weekly scheduled job scrapes CGC fee page, compares to stored config
  - DB table `pricing_config` for active prices + pending proposals
  - Admin dashboard "Pricing Updates" tab with approve/reject buttons
  - On approval, swaps active config; rejected = discarded
  - Low urgency — CGC changes prices ~once/year (last: Jan 2026)
  - 🔗 No blockers

### Testing ⚠️

- [ ] **Session 59 test plan** 👤⏱ 2-3 sessions ⚠️
  - ~40 of 47 tests still formally untested
  - Auth, billing, grading, collection, fingerprinting
  - 🔗 Depends on: grading consistency fix (many tests involve grading)

- [ ] **End-to-end grading accuracy test** 👤⏱ 1-2 sessions ⚠️
  - Grade 10+ comics with known CGC grades, compare
  - This IS the calibration test suite
  - 🔗 Depends on: grading consistency fix

- [ ] **Stripe billing flow on mobile** 👤 1-2 hours ⚠️
  - Checkout, plan upgrade, customer portal on real devices
  - No code dependency, just needs Mike's time

- [ ] **PWA testing** 👤 1-2 hours ⚠️
  - Install via "Add to Home Screen" on Android and iOS
  - Test offline behavior
  - 🔗 Depends on: offline fallback feature

### Business

- [ ] **LLC formation** 👤 1-2 weeks (paperwork + processing)
  - Needed before: accepting real payments, assigning patents
  - 🔗 Blocks: Stripe going live, patent assignment

- [ ] **Review & approve white paper** 👤 1-2 hours
  - Line-by-line review of SlabGuard_WhitePaper_DRAFT.docx
  - 🔗 No blockers

---

## P3 — PRE-LAUNCH MARKETING (Weeks 17-21, June-July)

> Don't market early — wait until the product is polished. Then push hard for 4 weeks before soft launch.

- [ ] **SEO / content marketing** ⏱ 2-3 sessions
  - Blog posts: "Is my ASM #300 worth grading?" powered by real sales data
  - Start 6-8 weeks before July 21 soft launch
  - 🔗 Depends on: valuation + grading working reliably

- [ ] **Social media presence** 👤⏱ 1 session to set up, then ongoing
  - ✅ Facebook page assets created (Session 77): profile pic + cover photo
  - 🔜 Facebook page setup (working with Sonnet 4.6)
  - Instagram, Twitter/X, TikTok — batch content creation
  - Convention-focused: "We'll be at GalaxyCon" campaign
  - 🔗 Depends on: having polished demo screenshots/video

- [ ] **Competitive positioning pages** ⏱ 1 session
  - "Slab Worthy vs CLZ" and "Slab Worthy vs ComicSnap"
  - 🔗 Depends on: product being feature-complete

- [ ] **Landing page polish** ⏱ 1 session
  - For organic traffic and post-announcement Googlers
  - Shareable white paper link
  - 🔗 Depends on: white paper approved

- [ ] **Google Play Store production** 👤 1-2 hours
  - Promote TWA from Internal Testing
  - 🔗 Depends on: mobile testing passing

---

## P4 — BOOTH-READY DEMO & GALAXYCON LOGISTICS (Weeks 17-25, June-August)

> The GalaxyCon pitch loop: scan QR → sign up → grade a comic → see value → wow.

### Booth Demo
- [ ] **Booth demo mode** ⏱ 1 session
  - Cached/pre-loaded results for repeat demos (save API costs)
  - Skip non-essential steps
  - 🔗 Depends on: grading flow polish

- [ ] **Sign-up/onboarding under 60 seconds** ⏱ 1 session
  - QR scan → minimal form → first grade
  - GalaxyCon-specific booth codes
  - 🔗 Depends on: grading flow polish

- [ ] **Offline fallback** ⏱ 1 session
  - Graceful handling when convention WiFi drops
  - Queue submissions, show cached results
  - 🔗 Depends on: demo mode

### Logistics
- [ ] **Booth materials** 👤⏱ 1 session + print time
  - QR codes, flyers, signage, demo script
  - Landing page redirect for convention signage
  - 🔗 Depends on: final product URL/flow confirmed

- [ ] **Equipment & setup** 👤 shopping + prep
  - iPad/phone stand, power bank, signage, backup phone
  - 🔗 No blockers — can buy anytime

- [ ] **Demo script & training** 👤⏱ 1 session
  - 60-second pitch, FAQ card, edge case handling
  - 🔗 Depends on: demo mode working

- [ ] **New booth/beta codes** ⏱ 30 min
  - Generate GalaxyCon-specific codes
  - 🔗 Depends on: sign-up flow finalized

---

## P5 — TECH DEBT & NICE-TO-HAVE (As Time Permits)

### Bugs to Fix
- [x] ~~**eBay OAuth callback redirect**~~ ✅ Session 74 — now redirects to account.html
- [x] ~~**eBay username shows as "user"**~~ ✅ Session 75 — Root cause: missing `commerce.identity.readonly` scope. Fixed in `ebay_oauth.py`. Fallback changed to "Connected". Needs disconnect/reconnect after deploy to verify.
- [ ] **Comic identification bug** ⏱ 1 session — Ghost Rider reboot vs original
- [x] ~~**Auto-rotation steps 2-4**~~ ✅ FIXED
- [ ] **Single-page upload missing extraction** ⏱ 30 min — Front photo doesn't call API (needs verification)
- [x] ~~**Cover not displaying**~~ ✅ FIXED — Iron Man #200 now showing
- [x] ~~**Identification trustworthiness fix**~~ ✅ SHIPPED & VERIFIED (Session 105, Jun 16) — extraction flip Haiku→Sonnet (`comic_extraction.py` `_run_vision_pass` tier + `routes/grading.py` cost-log label) + honesty gate (always-editable ID field, `|| '1'` default removed, `syncIdentityFields()`, server `issue_required` belt in `sales_valuation.py`). Verified live on Absolute Batman #19 / Atari Force #4 + mobile happy path. Plan: `docs/technical/IDENTIFICATION_FIX_PLAN_OF_RECORD.md`. **Still parked (open):** barcode-issue writeback, mylar grade-inflation, model-call-site fallback hardening (8/12 sites), GCD/ComicVine catalog (post-launch), pricing-tier review, year/edition comp-key gap (see 🚦 section).
- [ ] **ID Sigs BROKEN — image fetch/decode failing** ⚠️ LAUNCH GATE for Guard/Dealer paid feature (priority BUMPED — scope grew). **Scope correction (Session ~104, June 15 PM):** earlier framing ("R2 migration fixed the fetch; residual = cosmetic `messageToast is not defined`") is INCOMPLETE. Tonight's testing: ID Sigs throws **"Error: Image decode failed" almost INSTANTLY on TWO different comics** — i.e. it now dies UPSTREAM at the image fetch/decode, not at the toast/display step. Not a per-comic missing-image gap (fails on multiple comics). The morning `messageToast` error was likely a one-off on a comic that fetched cleanly. **Leading hypothesis (our own earlier finding):** `fetchImageAsBase64` (`js/utils.js:359` area) never checks `response.ok` before decoding — a non-image response (error body / 403 / redirect / empty) gets base64-encoded and chokes in decode → "decode failed" instantly, every comic, regardless of CORS. The instant timing fits (not waiting on a real image round-trip). **Read-only investigation:** (1) confirm `fetchImageAsBase64` still lacks the `response.ok` check, and what the fetch actually returns now (200 image vs error/redirect/empty — Network tab or trace built URL vs DB-stored `img.slabworthy.com` URL); (2) is it fetching the RIGHT url — built from the rewritten stored URL, not a stale/derived path still pointing at r2.dev or a wrong key? (3) does `messageToast` still occur on any comic, or is it now uniformly "decode failed"? (4) reconcile: `<img>` covers load fine but ID Sigs `fetch()` fails — is this the `response.ok` gap, a URL-construction bug, or a residual CORS/edge case the migration missed for this specific fetch? Don't fix yet — investigate read-only and report.

### Features (Post-Launch)
- [ ] **🃏 Baseball card vertical** ⏱ 3-5 sessions — TAM: 15-20M households, $2-13B market
  - Grading engine adaptation (centering, surface, corners, edges — different from comics)
  - Card-specific extraction (player, year, set, card number, parallel/insert)
  - eBay sales data pipeline for baseball cards
  - PSA/BGS/SGC cost calculator (equivalent of CGC for cards)
  - 2× API cost per call vs comics (more surface area analysis)
  - P&L projects 10K card users adding $493K annual revenue
- [ ] Grade report sharing/export (shareable link or PDF)
- [ ] Batch grading (multiple comics per session)
- [ ] Price alerts (notify when comics hit thresholds)
- [ ] Second opinion mode (run extraction twice, compare)
- [ ] Slab label valuation adjustments (signature series, restored, etc.)
- [ ] Two-factor authentication
- [ ] Add display_name to /api/auth/me (replace email-derived name)
- [ ] Backend trending endpoint for Market Movers panel (real ebay_sales data)

### Business (In Progress)
- [ ] **Hire first employee** — Marketing + front-end design ($75K + 30% benefits = $97.5K/yr)
- [ ] **Marketing budget** — $4,500/mo (ads $2,500, content $1,000, conventions $500, tools $500)
- [x] **Year 1 P&L** ✅ Session 80 — docs/business/SlabWorthy_Year1_PnL.xlsx
- [x] **TAM analysis** ✅ Session 80 — Comics + baseball cards, 15K target achievable
- [ ] **LLC formation** 👤 — Needed before: accepting real payments, assigning patents

---

## Critical Path Visualization

```
WEEKS 1-2 (P0):
  Fix grading consistency ──┐
  Update CGC costs ─────────┤
  Push code ────────────────┘
                            │
WEEKS 3-6 (P1):            ▼
  eBay auction support ✅    Sig page deletion ✅
  eBay e2e testing ⚠️ 🔜    Whatnot prep tool
  Mobile testing ⚠️
                            │
WEEKS 7-16 (P2):           ▼
  Photo auth integration    Sell Now Alerts
  Signature ID v1           Data ramp (ongoing)
  Session 59 tests ⚠️      LLC formation 👤
  Grading accuracy ⚠️      Haiku 4.5 test
                            │
WEEKS 17-21 (P3):          ▼
  SEO/blog content          Social media push
  Landing page polish       Google Play production
                            │
WEEKS 17-25 (P4):          ▼
  Demo mode ──► Offline     Booth materials
  Onboarding flow           Demo script + codes
                            │
                            ▼
  ┌─────────────────────────────────┐
  │  JULY 21: SOFT LAUNCH          │
  │  AUG 21-23: GALAXYCON SAN JOSE │
  └─────────────────────────────────┘
```

## Summary

| Phase | Items | Est. Sessions | Calendar | Status |
|-------|-------|---------------|----------|--------|
| P0 — Credibility Fix | 3 | 2 sessions | Weeks 1-2 | ✅ COMPLETE |
| P1 — Collection & Selling | 4 | 3 sessions + eBay testing ⚠️ | Weeks 3-6 | 🟡 eBay e2e + marketplace test remaining; Slab Guard ✅ |
| P2 — Launch Prep | 12 | 10 sessions + device testing ⚠️ | Weeks 7-16 | Upcoming |
| P3 — Marketing | 5 | 5 sessions | Weeks 17-21 | 🟡 FB assets done, P&L + TAM done |
| P4 — Booth Demo + GalaxyCon | 7 | 5 sessions + shopping 👤 | Weeks 17-25 | Not started |
| P5 — Tech Debt + Expansion | 3+8 | As time permits | Anytime | Baseball card vertical planned |
| **Total** | **38+** | **~25 sessions** | **24 weeks** | |

**At ~1-2 sessions/week, this is tight but very doable.** Key: stay disciplined P0→P1→P2 order. Baseball card vertical is post-launch but P&L shows it triples the business. First hire (marketing + front-end) budgeted at $97.5K/yr all-in.
