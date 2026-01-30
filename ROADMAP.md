# CollectionCalc / Slab Worthy Roadmap

## Current Version: 2.98.0 (January 30, 2026)

### 🎉 PATENT PENDING
Provisional patent filed for multi-angle comic grading system.

---

## Recently Completed

### v2.98.0 - Single Source of Truth & Deterministic Grading (Session 18) 🆕
- [x] **Slab Worthy uses backend extraction** - Step 1 now calls /api/extract (same as Photo Upload)
- [x] **barcode_digits field added** - Extracts 5-digit UPC add-on code for print/variant identification
- [x] **Deterministic grading** - Added temperature=0 to all Claude API calls
- [x] **wsgi.py media_type passthrough** - /api/extract properly handles PNG, HEIC, WebP
- [x] **UI Polish:**
  - "Upload from Gallery" → "Upload" (shorter, cleaner)
  - "💰 Should You Grade This?" → Slab icon + "Should You Slab It?"
  - Warning message clarified (about photo count, not quality)
- [x] **Thinking animation code** - Progress messages during valuation (needs debugging)

### v2.97.0 - Mobile Fixes & Gallery Upload (Sessions 15-17)
- [x] **Login persistence fixed** - Token now properly loads from localStorage
- [x] **Mobile extraction working** - Was auth issue, not extraction bug
- [x] **Rotation detection improved** - AI checks TEXT only, ignores artistic elements
- [x] **Upload from Gallery** - Slab Worthy now has "Take Photo" + "Upload" buttons
- [x] **Server slowdown diagnosed** - Whatnot extension was polling with null issue
- [x] **Auto-rotation prompts for steps 2-4** - Added is_upside_down check (needs testing)
- [x] **Cache key crash fix** - issue.strip() on integers
- [x] **Search logging added** - Diagnose Spawn #1 reprint confusion

### v2.96.0 - Auto-Rotation & Code Split (Session 13-14)
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

---

## In Progress / Known Bugs

### Bugs to Fix
- [ ] 🐛 **Thinking animation not showing** - Code added but not appearing in Slab Worthy Step 5
- [ ] 🐛 **Photo Upload missing thinking animation** - Needs same treatment as Slab Worthy
- [ ] 🐛 **Auto-rotation steps 2-4** - Code added but not working
- [ ] 🐛 **Whatnot extension polling** - Hammers server with null issue, doesn't stop on tab close
- [ ] 🐛 **Hide "Take Photo" on desktop** - Only show "Upload" button on non-mobile

### Valuation Accuracy
- [ ] **Spawn #1 reprint confusion** - Returns ~$25 instead of $300-400 for first prints
- [ ] **Barcode decoder logic** - Interpret 5-digit codes by publisher (DC, Marvel, etc.)
- [ ] **Key issue sanity check** - Database of floor prices to catch bad values

### Performance
- [ ] **Valuation speed** - "Should you slab it?" calculation takes time (thinking animation helps UX)

---

## Backlog

### High Priority
- [ ] **Fix Whatnot Extension** - Critical for collecting real sales data
  - Polling with null issue hammers server
  - Doesn't stop when tab closed
  - Need this working to improve valuations with real data
- [ ] **Debug thinking animation** - Fix not appearing in Slab Worthy
- [ ] **Add thinking animation to Photo Upload** - Same treatment in app.js
- [ ] **Barcode-based variant detection** - Use 5-digit code to identify prints/variants
- [ ] **Test barcode with modern comics** - Need high-res Absolute Batman image
- [ ] **Whatnot Auction Integration** - Create auctions/sales from graded comics
  - Similar flow to eBay QuickList
  - AI-generated descriptions
  - Pre-fill pricing from valuations
  - Direct listing creation via Whatnot API
- [ ] **Save graded comic to collection**
- [ ] **Grade report sharing/export**

### Medium Priority
- [ ] **Slab Premium Admin Panel** - Data-driven premium model management
  - "Run Analysis" button triggers eBay data collection
  - Shows proposed tiers vs current model in side-by-side comparison
  - "Approve" saves new model to database, "Reject" discards
  - Logs all model changes with timestamp
  - Store tiers in database (not hardcoded in JS)
  - Collect raw→slabbed value pairs from real sales
  - Age tier data with recency weighting
- [ ] **Valuation Engine Improvements**
  - ✅ Exponential decay for recency (30-day half-life) - Implemented
  - Configurable half-life in admin
  - Add standard deviation outlier check (supplement IQR)
  - Minimum sample warning (<3 sales = flag as unreliable)
  - Store/display valuation confidence reasoning
- [ ] **Prompt Management Admin Page** - View/edit all prompts in one place
  - List all prompts (extraction, grading steps 1-4, signature matching)
  - Read/Edit/Test views
  - Store in database instead of hardcoded
  - Test interface: upload image, run prompt, see raw output
- [ ] **True Meta-Optimization for prompts** (Level 4)
  - Send extraction + image to second Claude call
  - Ask: "Did this extraction miss anything? How could the prompt be improved?"
  - Log suggestions, human reviews, update prompt
  - Continuous improvement feedback loop
- [ ] **Value tracking over time**
- [ ] **Collection analytics**
- [ ] **Batch grading (multiple comics)**
- [ ] **Price alerts**
- [ ] **FAQ content** (pressing, newsstand vs direct, valuation methodology)

### Low Priority / Future
- [ ] **Sports cards support**
- [ ] **Pokemon cards support**
- [ ] **Other collectibles**
- [ ] **Social features (share collection)**
- [ ] **Marketplace integration beyond eBay**
- [ ] **Slab Worthy mobile app**

---

## Business/Legal

### Trademark Evaluation
- [ ] "Slab Worthy" - core brand name
- [ ] "Slab Report" - distinctive output term

### CGC Partnership Exploration
- [ ] Affiliate/referral commission for grading submissions
- [ ] User discounts for using our recommendation
- [ ] Attribution tracking

### Product Decisions Needed
- [ ] **Photo Upload mode** - Keep or deprecate now that Slab Worthy exists?
- [ ] **Collection-centric UX** - Restructure around collection as hub?
- [ ] **Pricing model** - Free tier vs paid tiers

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
9. Barcode-based variant identification (potential addition)

**Status:** Provisional filed January 27, 2026
**Next:** File utility patent within 12 months (by January 27, 2027)

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 2.98.0 | Jan 30, 2026 | 🎯 Single source extraction, deterministic grading, UI polish |
| 2.97.0 | Jan 29, 2026 | 📱 Mobile fixes, Gallery upload |
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

*Last updated: January 30, 2026*
