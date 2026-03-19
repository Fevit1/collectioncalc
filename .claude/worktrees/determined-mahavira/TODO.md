# Slab Worthy — Master To-Do List
**Updated:** March 7, 2026 (Session 82)
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

## ✅ DONE (Session 64-81)

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

- [ ] **Signature identification v1 — testing & tuning** ⏱ 1-2 sessions
  - ✅ Reference DB built (23 artists, 97 images)
  - ✅ API endpoints built + deployed (match, db-stats, signed-sales, premium-analysis)
  - ✅ Test suite built (`test_signature_matcher.py`)
  - ✅ Title year collision fix deployed + migrated (62.5% year coverage)
  - ✅ Premium analysis engine deployed: time-windowed, log-transform, bootstrap CI
  - ✅ Baseline results: +40-57% premium, 95% CI [+27%, +59%], 72% positive
  - ✅ Session 82: Cross-validation baseline 73.9% → improved to 78.3% with multi-reference + system prompt + preferred_images
  - ✅ Session 82: Fixed cross-validation data leakage bug (test image excluded from references)
  - ✅ Session 82: Jim Lee, Jae Lee, Jim Steranko now correctly identified
  - Remaining: fix style_notes metadata (Mike), source better reference images, deploy changes, target 87%+
  - 🔗 Depends on: Mike fixing style_notes + collecting better reference images for Bendis/Claremont

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

- [ ] **Test Haiku 4.5 for extraction** ⏱ 1 session
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
