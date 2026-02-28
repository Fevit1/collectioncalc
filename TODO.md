# Slab Worthy — Master To-Do List
**Updated:** February 28, 2026 (Session 69)
**Target:** GalaxyCon San Jose Alpha Launch — Aug 21-23, 2026 (~25 weeks out)
**Soft Launch:** July 21, 2026 (~21 weeks out)
**Solo Founder:** Mike Berry — estimates assume ~15-20 hrs/week on Slab Worthy

**Estimation notes:**
- Claude coding sessions: estimated at 2x speed (we consistently deliver faster than expected)
- ⏱ = estimated session time (Claude + Mike working together)
- 👤 = Mike-only time (testing on devices, business tasks, manual work)
- 🔗 = dependency on another task
- ⚠️ = testing-heavy (may take longer — depends on Mike's device time)

---

## ✅ DONE (Session 64-69)

- [x] **Sortable collection columns** — Session 69: All list view columns (Title, Year, Issue, Grade, FMV, My Valuation) are clickable to sort ascending/descending with arrow indicators.
- [x] **Optimistic delete UI** — Session 69: Collection delete now removes row instantly (150ms fade), API fires in background. Rollback on failure with toast notification.
- [x] **Smart delete confirmation** — Session 69: Custom modal with "Don't show this warning again" checkbox replaces browser confirm(). Preference stored in localStorage.
- [x] **Fix collection delete FK cascade** — Session 69: SAVEPOINT-based cascade delete handles FK constraints across comic_registry, sighting_reports, match_reports tables.
- [x] **Documentation overhaul** — Session 69: Rewrote DATABASE_PRODUCTION.md (16 tables), ROUTE_MAPPING.md (87 routes), updated COMIC_REGISTRY_SCHEMA.md + API_REFERENCE.md.
- [x] **Signature image delete visibility** — Session 69: Made per-image delete button always visible (was hidden behind hover).
- [x] **Auction price validation** — Session 69: Client-side validation for price relationships (reserve > start, BIN > reserve).
- [x] **Signature page deletion** — Session 69: Added "Delete Creator" button to admin signatures page. Backend `DELETE /api/admin/signatures/<id>` endpoint cascades to remove all reference images. Confirmation dialog prevents accidents.
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
- [x] **Photo authenticity detector prototype** — 7-check system, tested with real images
- [x] **Slab Guard white paper draft** — For Mike's review
- [x] **FAQ updates** — 3 new Slab Guard entries (photo quality, verification, flagging)
- [x] **Signature database progress** — 23 of 42 artists collected (4 sigs each)

---

## P0 — THE CREDIBILITY FIX (Next 2 weeks)

> If someone grades the same comic twice at your booth and gets different numbers, nothing else matters.

- [x] ~~**Fix AI grading inconsistency**~~ ✅ Session 66
  - Rebuilt from holistic → structured 8-category scoring
  - New `grading_engine.py` + `/api/grade` endpoint + multi-run support
  - 10 unit tests passing, live consistency test harness built
  - 🔗 UNBLOCKED: demo mode, GalaxyCon prep, grading accuracy test

- [x] ~~**Update hardcoded CGC grading costs**~~ ✅ Session 66
  - Updated to 2026 pricing: Modern $30, Vintage $45, High Value $105, Unlimited 4% ($135 min)
  - Centralized `get_cgc_grading_cost()` function + `CGC_GRADING_COSTS` config in sales_valuation.py
  - Now factors in modern vs vintage (pre-1975) pricing
  - All 3 hardcoded locations replaced

- [x] ~~**Push Session 65 code**~~ ✅ Done

---

## P1 — COLLECTION & SELLING TOOLS (Weeks 3-6, March)

> Make the collection page a selling powerhouse. Grade → value → list → sell.

### Product

- [x] ~~**eBay auction listing support**~~ ✅ Session 69
  - Fixed Price / Auction toggle in listing modal
  - Auction fields: starting bid, duration, reserve, Buy It Now
  - Backend + route + UI all updated

- [x] ~~**Signature page deletion**~~ ✅ Session 69
  - Added "Delete Creator" button + backend DELETE endpoint
  - Cascading delete removes all reference images

- [ ] **eBay listing end-to-end test** 👤⏱ 1 session ⚠️
  - Test OAuth flow, connect eBay account
  - Test fixed-price listing (draft + publish)
  - Test auction listing (all field combos)
  - 🔗 Depends on: eBay developer account approved for production

- [ ] **Whatnot listing prep tool** ⏱ 1 session
  - "Prep for Whatnot" button generates title, description, suggested starting bid
  - Copy-to-clipboard for pasting into Whatnot seller dashboard
  - Whatnot has no public listing API — this is the best we can do
  - 🔗 No blockers

### Testing ⚠️

- [ ] **Valuation endpoint testing** 👤⏱ 1 session
  - 12-case test plan (grade-specific FMV with slabbing ROI)
  - 🔗 Depends on: CGC cost update

- [x] ~~**Run title normalizer backfill**~~ ✅ Session 68
  - 376 NULLs all edge cases (lot #s, non-comics, art prints). Not actionable.

- [ ] **Mobile testing (full grading flow)** 👤 2-3 hours across devices ⚠️
  - Grading, collection, pricing, verify on real phones (Android + iOS)
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
  - Remaining: run cross-validation, tune confidence thresholds, per-creator premiums (need more data)
  - 🔗 Depends on: Mike collecting 5 more priority artists

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
- [ ] **Comic identification bug** ⏱ 1 session — Ghost Rider reboot vs original
- [ ] **Auto-rotation steps 2-4** ⏱ 30 min — Code added but not working
- [ ] **Single-page upload missing extraction** ⏱ 30 min — Front photo doesn't call API
- [ ] **Cover not displaying** ⏱ 30 min — Iron Man #200 in collection

### Features (Post-Launch)
- [ ] Grade report sharing/export (shareable link or PDF)
- [ ] Batch grading (multiple comics per session)
- [ ] Price alerts (notify when comics hit thresholds)
- [ ] Second opinion mode (run extraction twice, compare)
- [ ] Slab label valuation adjustments (signature series, restored, etc.)
- [ ] Two-factor authentication
- [ ] Multi-vertical expansion (baseball cards, coins, sneakers)

---

## Critical Path Visualization

```
WEEKS 1-2 (P0):
  Fix grading consistency ──┐
  Update CGC costs ─────────┤
  Push code ────────────────┘
                            │
WEEKS 3-6 (P1):            ▼
  eBay auction support ✅    Sig page deletion
  eBay e2e testing ⚠️       Whatnot prep tool
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

| Phase | Items | Est. Sessions | Calendar |
|-------|-------|---------------|----------|
| P0 — Credibility Fix | 3 | 2 sessions | Weeks 1-2 |
| P1 — Collection & Selling | 4 | 3 sessions + eBay testing ⚠️ | Weeks 3-6 |
| P2 — Launch Prep | 12 | 10 sessions + device testing ⚠️ | Weeks 7-16 |
| P3 — Marketing | 5 | 5 sessions | Weeks 17-21 |
| P4 — Booth Demo + GalaxyCon | 7 | 5 sessions + shopping 👤 | Weeks 17-25 |
| P5 — Tech Debt | 4+7 | As time permits | Anytime |
| **Total** | **37+** | **~25 sessions** | **25 weeks** |

**At ~1-2 sessions/week, this is tight but very doable.** The key is staying disciplined about P0 → P1 → P2 order and not getting pulled into P5 polish work before the core demo flow is bulletproof.
