# CollectionCalc / Slab Worthy Roadmap

## Current Version: 3.0.0 (February 2, 2026)

### 🎉 PATENT PENDING
Provisional patent filed for multi-angle comic grading system.

---

## Recently Completed

### v3.0.0 - 🎉 BARCODE SCANNING LIVE! (Session 22) 🆕
- [x] **Docker Deployment** - Migrated from Python to Docker on Render
  - Dockerfile with libzbar0 system library
  - pyzbar barcode scanning now works!
  - Production URL: `collectioncalc-docker.onrender.com`
- [x] **Barcode Endpoints Added:**
  - `/api/barcode-test` - Verify pyzbar loads
  - `/api/barcode-scan` - Direct barcode scanning
- [x] **Barcode Integration in Extraction:**
  - `scan_barcode()` tries 0°, 90°, 180°, 270° rotations
  - Extracts `upc_main` (12 digits) + `upc_addon` (5 digits)
  - Returns barcode data in `/api/extract` response
- [x] **Frontend Updated:**
  - `js/utils.js` API_URL points to Docker backend
- [x] **Cost Savings:**
  - Suspended old Python service (-$7/mo)

**Test Result (Amethyst #1):**
```json
{
  "barcode_scanned": {
    "type": "UPCA",
    "upc_main": "070989311176",
    "rotation": 0
  },
  "title": "Amethyst Princess of Gemworld",
  "issue": "1"
}
```

### v2.99.0 - eBay Collector Extension (Session 21)
- [x] **eBay Collector Extension v1.0.3** - Passively collects comic sale data from eBay sold listings
  - Parses: title, issue, price, date, condition, grade, publisher, image
  - Fixed selectors for eBay's 2026 HTML structure (`li.s-card`)
  - Popup shows stats and manual Sync button
- [x] **R2 Image Backup** - Permanent storage for cover images
  - Parallel processing (5 concurrent) for speed
  - Images stored at `ebay-covers/{item_id}.webp`
  - ~10-15 seconds for 60 images
- [x] **Database Schema** - `ebay_sales` table with full sale data
  - `comic_fmv` view for 90-day rolling FMV calculations
  - Deduplication via `ebay_item_id` unique constraint
- [x] **Whatnot Extension Fix** - v2.41.2 storage quota fix
  - Was storing base64 images (500MB+), now stripped before storage
- [x] **wsgi.py cleanup** - Silenced eBay deletion notification spam

### v2.98.0 - Single Source of Truth & Deterministic Grading (Session 18-20)
- [x] **Slab Worthy uses backend extraction** - Step 1 now calls /api/extract (same as Photo Upload)
- [x] **barcode_digits field added** - Extracts 5-digit UPC add-on code for print/variant identification
- [x] **Deterministic grading** - Added temperature=0 to all Claude API calls
- [x] **wsgi.py media_type passthrough** - /api/extract properly handles PNG, HEIC, WebP
- [x] **Writer/Artist extraction** - New schema fields working
- [x] **UI Polish:**
  - "Upload from Gallery" → "Upload" (shorter, cleaner)
  - "💰 Should You Grade This?" → Slab icon + "Should You Slab It?"
  - Warning message clarified (about photo count, not quality)

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

## In Progress

### 🚧 Phase 2: Database Schema for Barcode Storage
**Status:** Ready to implement

**Tasks:**
- [ ] Add `upc_main`, `upc_addon`, `is_reprint` columns to `market_sales`
- [ ] Add `upc_main`, `upc_addon`, `is_reprint` columns to `ebay_sales`
- [ ] Store barcode data when Whatnot extension uploads images
- [ ] No extension changes needed (server-side only)

### 🚧 Phase 3: Backfill Existing Images
**Status:** After Phase 2

**Tasks:**
- [ ] Create `/api/admin/backfill-barcodes` endpoint
- [ ] Fetch all sales with R2 image URLs
- [ ] Download and scan each image with pyzbar
- [ ] Update database with barcode data
- [ ] Batch processing with progress tracking

---

## Known Bugs

- [ ] 🐛 **Thinking animation not showing** - Code added but not appearing in Slab Worthy Step 5
- [ ] 🐛 **Photo Upload missing thinking animation** - Needs same treatment as Slab Worthy
- [ ] 🐛 **Auto-rotation steps 2-4** - Code added but not working
- [ ] 🐛 **Hide "Take Photo" on desktop** - Only show "Upload" button on non-mobile

---

## Backlog

### High Priority
- [ ] **Phase 2: Store barcode data in database** - #1 PRIORITY
- [ ] **Phase 3: Backfill existing images with barcodes**
- [ ] **Use barcode to filter reprints from valuations** - Spawn #1 fix!
- [ ] **Reprint/variant warnings in UI** - Alert users when detected
- [ ] **Use eBay Collector data in valuations** - FMV from real sales
- [ ] **Debug thinking animation** - Fix not appearing in Slab Worthy
- [ ] **Whatnot Auction Integration** - Create auctions from graded comics
- [ ] **Save graded comic to collection**
- [ ] **Grade report sharing/export**

### Medium Priority
- [ ] **Slab Premium Admin Panel** - Data-driven premium model management
- [ ] **Valuation Engine Improvements** - Confidence reasoning, outlier detection
- [ ] **Prompt Management Admin Page** - View/edit all prompts in one place
- [ ] **Value tracking over time**
- [ ] **Collection analytics**
- [ ] **Batch grading (multiple comics)**
- [ ] **Price alerts**

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
9. **Barcode-based variant/reprint identification** ✅ NOW WORKING

**Status:** Provisional filed January 27, 2026
**Next:** File utility patent within 12 months (by January 27, 2027)

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 3.0.0 | Feb 2, 2026 | 🎉 BARCODE SCANNING LIVE! Docker deployment |
| 2.99.0 | Feb 1, 2026 | 📊 eBay Collector extension, R2 image backup |
| 2.98.0 | Jan 30, 2026 | 🎯 Single source extraction, deterministic grading |
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

*Last updated: February 2, 2026*
