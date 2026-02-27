# Slab Worthy — Master To-Do List
**Created:** February 25, 2026 (Session 64)
**Target:** GalaxyCon San Jose Alpha Launch — Aug 21-23, 2026 (~25 weeks out)

---

## P0 — DO THIS WEEK (Critical Path)

### Business
- [x] **File signature identification patent on USPTO** — ✅ FILED Feb 25, 2026. Application # 63/990,743, Confirmation # 9241. $65 micro entity. Set reminder: December 2026 to file non-provisional.

### Build
- [ ] **Push Session 64 code** — waitlist.html, waitlist-confirmed.html, index.html, login.html, routes/waitlist.py, mockup_waitlist_confirmed.html
- [ ] **GalaxyCon sprint plan** — Formal milestones from now to Aug 21

### Test
- [ ] **Test waitlist confirmation page on production** — After push, sign up with new email, click confirm link, verify personalized landing page works with interests
- [ ] **Test standalone waitlist.html page** — Verify form submits, counter loads, success state, link back to login works
- [ ] **Test login.html waitlist CTA** — Verify "Join the Waitlist" button inside beta card links correctly

---

## P1 — THIS MONTH (GalaxyCon Prep - Core Product)

### Build
- [ ] **Grading flow polish** — Speed up (remove 2-sec artificial delay), photo upload instructions, "Grade Next" reset button, valuation on results page
- [ ] **Wire valuation into grading results** — Show grade + FMV + slabbing ROI together on the results screen
- [ ] **Booth demo mode** — Streamlined flow for live demos at GalaxyCon (skip non-essential steps)
- [ ] **Sign-up/onboarding flow under 60 seconds** — For booth visitors scanning QR code, minimal friction to first grade
- [ ] **Offline fallback** — Graceful handling if network drops mid-demo at the convention

### Test
- [ ] **Valuation endpoint testing** — `/api/sales/valuation` needs 12-case test plan executed (grade-specific FMV with slabbing ROI)
- [ ] **Run title normalizer backfill** — `curl -X POST .../api/ebay-sales/backfill-titles` to fix 369 legacy NULL titles
- [ ] **Live Slab Guard registration test** — Register a comic on production, verify composite fingerprinting stores correctly
- [ ] **Mobile testing (full app flow)** — Grading, collection, pricing, verify — on real phones (Android + iOS)
- [ ] **PWA testing** — Install via "Add to Home Screen" on Android and iOS, verify offline behavior

---

## P2 — BEFORE GALAXYCON (March - July)

### Build
- [ ] **QR code / booth materials** — Landing page or redirect for convention signage
- [ ] **Data collection ramp** — More eBay/Whatnot sales data for better valuations (especially key titles)
- [ ] **Email drip for waitlist** — Follow-up emails to keep waitlist engaged pre-launch

### Test
- [ ] **Session 59 test plan** — ~40 of 47 tests still formally untested (auth, billing, grading, collection, fingerprinting, etc.)
- [ ] **End-to-end grading accuracy test** — Grade 10+ comics, compare AI grades to known CGC grades
- [ ] **Stripe billing flow on mobile** — Checkout, plan upgrade, customer portal on real devices

### Business
- [ ] **GalaxyCon logistics** — Booth setup, equipment (iPad/phone stand, power bank, signage), demo script

---

## P3 — NICE TO HAVE (Post-GalaxyCon or If Time Permits)

### Build
- [ ] **Facebook/social media presence** — Deferred to June pre-launch (batch content creation)
- [ ] **Grade report sharing/export** — Shareable link or PDF of grading results
- [ ] **Batch grading** — Grade multiple comics in one session
- [ ] **Price alerts** — Notify users when their comics hit price thresholds

### Fix (Technical Debt)
- [ ] **AI grading inconsistency** — Same 4 images give different grades across runs (8.5 → 9.2 → 8.5). Needs prompt tuning or scoring calibration
- [ ] **Comic identification bug** — Ghost Rider reboot #1 sometimes identified as original series #1
- [ ] **Auto-rotation steps 2-4** — Code added but not working
- [ ] **Single-page upload missing extraction** — Front photo doesn't call extraction API
- [ ] **Cover not displaying** — Iron Man #200 photos not showing in collection

### Backlog (Post-Launch)
- [ ] Two-factor authentication (TOTP)
- [ ] AI-powered support inbox
- [ ] NLQ database queries for premium users
- [ ] Social features
- [ ] Multi-vertical expansion (baseball cards, coins, sneakers)

---

## Summary

| Priority | Build | Test | Business | Total |
|----------|-------|------|----------|-------|
| P0 (This Week) | 2 | 3 | 1 | **6** |
| P1 (This Month) | 5 | 5 | 0 | **10** |
| P2 (Before GalaxyCon) | 3 | 3 | 1 | **7** |
| P3 (Nice to Have) | 4 | 0 | 0 | **4** |
| P3 (Tech Debt) | 5 | 0 | 0 | **5** |
| P3 (Backlog) | 5 | 0 | 0 | **5** |
| **Total** | **24** | **11** | **2** | **37** |

**Critical path to GalaxyCon:** P0 + P1 = 15 items over the next month, then P2 fills March through July. Extra runway means more polish time.
