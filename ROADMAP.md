# CollectionCalc / Slab Worthy Roadmap

## Current Version: 2.96.0 (January 28, 2026)

### 🎉 PATENT PENDING
Provisional patent filed for multi-angle comic grading system.

---

## Recently Completed

### v2.96.0 - Auto-Rotation & Code Split (Session 13) 🆕
- [x] **Auto-rotate landscape→portrait** - Comics are always taller than wide
- [x] **Auto-detect upside-down** - AI checks orientation, rotates 180° if needed
- [x] **Split app.js into 4 modules** - Prevents file truncation on low-memory systems
  - `js/utils.js` - Shared state, image processing, UI helpers
  - `js/auth.js` - Authentication, user menu, collection
  - `js/app.js` - eBay, photo upload, valuation, manual entry
  - `js/grading.js` - Slab Worthy 4-photo flow
- [x] **"Upright" instruction text** - Guides users to reduce re-analysis costs
- [x] **Rotate button debounce** - 2.5s cooldown prevents rapid clicks

### v2.95.0 - Slab Worthy Live! (Session 12)
- [x] **Fixed truncated app.html** - Missing script tag caused setMode undefined
- [x] **Added defensive null checks** - Grading report won't crash on missing elements
- [x] **Slab Worthy deployed to production** - Feature is LIVE

### v2.94.0 - Slab Worthy! (Session 11)
- [x] **Provisional patent filed** - USPTO, Small Entity
- [x] **"Slab Worthy?" tab** - 4-photo grading assessment
- [x] Custom slab icon with question mark
- [x] Sequential photo capture flow (Front → Spine → Back → Centerfold → Report)
- [x] Device detection (mobile camera vs desktop upload)
- [x] Photo quality feedback (blur, dark, glare warnings)
- [x] Grade report with defects by area
- [x] "Should you grade?" economic recommendation
- [x] Confidence scaling (65% → 94% based on photos)
- [x] Additional photos support
- [x] Photo tips modal

### v2.93.0 - Signature & Facsimile Detection (Session 10)
- [x] Facsimile edition detection in extension
- [x] Signature database (40+ creators)
- [x] Signatures admin page
- [x] FMV endpoint for extension
- [x] Admin button in header
- [x] Extension auto-scan improvements
- [x] slabworthy.com domain registered

### v2.92.0 - NLQ & Admin (Session 9)
- [x] Natural Language Query for database
- [x] Admin dashboard with NLQ
- [x] Beta code management
- [x] User approval system

### v2.91.0 - eBay QuickList (Sessions 7-8)
- [x] Batch photo processing
- [x] AI-generated descriptions
- [x] eBay draft listing creation
- [x] R2 image storage

### v2.90.0 - Authentication (Sessions 5-6)
- [x] User signup/login with JWT
- [x] Email verification via Resend
- [x] Password reset flow
- [x] Beta code gating
- [x] Collection saving

---

## In Progress

### Performance Improvements
- [ ] **Valuation speed** - "Should you grade?" calculation is slow
- [ ] **FMV caching audit** - Verify cache is working (same comic+grade shouldn't re-call API)

### Business/Legal
- [ ] **Trademark evaluation:**
  - "Slab Worthy" - core brand name
  - "Slab Report" - distinctive output term
- [ ] **CGC partnership exploration:**
  - Affiliate/referral commission for grading submissions
  - User discounts for using our recommendation
  - Attribution tracking (blockchain?)

### Product Decisions Needed
- [ ] **Photo Upload mode** - Keep or deprecate now that Slab Worthy exists?
- [ ] **Batch grading** - Multiple comics at once? How would UX work?
- [ ] **Collection-centric UX** - Restructure around collection as hub?
- [ ] **FAQ page** - Common questions, pricing info
- [ ] **Pricing model** - Free tier vs paid tiers

### Testing Slab Worthy
- [ ] Real comic photo testing (various conditions)
- [ ] Compare 1-photo vs 4-photo accuracy
- [ ] Validate against known CGC grades
- [x] ~~Test rotated/sideways photos~~ - Auto-rotation implemented!

---

## Backlog

### High Priority
- [ ] Save graded comic to collection
- [ ] Grade report sharing/export
- [ ] Slab Worthy for mobile app (future)
- [ ] Mobile parity fixes (Slab Worthy on phones)

### Medium Priority
- [ ] Value tracking over time
- [ ] Collection analytics
- [ ] Batch grading (multiple comics)
- [ ] Price alerts

### Low Priority / Future
- [ ] Sports cards support
- [ ] Pokemon cards support
- [ ] Other collectibles
- [ ] Social features (share collection)
- [ ] Marketplace integration beyond eBay

---

## Patent Coverage

**Title:** System and Method for Automated Comic Book Condition Assessment Using Multi-Angle Imaging and Artificial Intelligence

**Key Claims:**
1. Multi-angle photography method (front, spine, back, centerfold)
2. AI defect detection across multiple views
3. Confidence scaling based on photo count
4. Image quality feedback loop
5. Economic decision engine ("should you grade?")
6. Signature detection module
7. Facsimile detection module
8. Auto-orientation correction (landscape/upside-down)

**Status:** Provisional filed January 27, 2026
**Next:** File utility patent within 12 months (by January 27, 2027)

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 2.96.0 | Jan 28, 2026 | 🔄 Auto-rotation, JS modular split |
| 2.95.0 | Jan 28, 2026 | 🚀 Slab Worthy LIVE, bug fixes |
| 2.94.0 | Jan 27, 2026 | 🔲 Slab Worthy!, Patent filed |
| 2.93.0 | Jan 26, 2026 | Signature/facsimile detection |
| 2.92.0 | Jan 25, 2026 | NLQ, Admin dashboard |
| 2.91.0 | Jan 24, 2026 | eBay QuickList |
| 2.90.0 | Jan 22, 2026 | Authentication, beta codes |
| 2.80.0 | Jan 20, 2026 | Photo extraction, bulk upload |
| 2.70.0 | Jan 18, 2026 | Three-tier valuation |
| 2.60.0 | Jan 15, 2026 | Whatnot extension |
| 2.50.0 | Jan 12, 2026 | Market data integration |

---

*Last updated: January 28, 2026*
