# Fingerprint Testing - Session 47 Results (Updated)
## February 17, 2026 — Extended Session

### Test Setup
- 4 registrations of the SAME physical comic (002, 003, 004) — re-photographed
- 1 registration of a DIFFERENT physical copy of the same issue (005)
- Comic: The Official Handbook of the Marvel Universe #2
- 004 was intentionally photographed at an angle to stress-test

### Approach 1: Composite pHash (existing system)
**Result: FAILED for real-world use**
- Same comic re-photographed: 41-137/256 per angle (huge variance)
- 004 (angled photo) scored 119-137/256 — classified as "different comic"
- Current thresholds (≤73) only caught 1 of 4 angles
- Root cause: pHash compares global pixel patterns, which change completely with camera angle/orientation
- Preprocessing (grayscale, auto-crop, resize, autocontrast, blur) doesn't correct perspective distortion

### Approach 2: Perspective Correction + pHash
**Result: PARTIALLY HELPED**
- 002 vs 003 (both straight-on): improved dramatically — 64.5 → 17.5 avg
- 002/003 vs 004 (angled): still ~131/256 — perspective correction couldn't reliably detect comic edges in angled photos
- Not robust enough for production

### Approach 3: Feature-Based Matching (SIFT/ORB/AKAZE)
**Result: WRONG APPROACH for this problem**
- All 3 algorithms found STRONG MATCH for same comic (good)
- But ALSO found STRONG MATCH for different copy (bad!)
- Complete overlap — no separation between same comic and different copy
- Root cause: feature matching finds matches on PRINTED CONTENT (cover art, text, layout) which is identical between copies
- The unique physical defects are drowned out by shared content signal

### Key Insight: Defect-Based Fingerprinting
The fundamental problem: printed content is identical between copies. The differentiating signal is physical defects — spine ticks, color breaks, corner dings, creases, print imperfections.

**Next approach should be:**
1. Use Claude Vision to identify and locate specific defects (already done during grading!)
2. Crop/extract defect regions from the photos
3. Fingerprint ONLY the defect regions, not the whole cover
4. Match on defect patterns: type, location, size, shape, relative positions

**Market segmentation:**
- Raw comics below 9.2 grade: plenty of visible defects for fingerprinting
- Slabbed comics 9.2+: the SLAB CASE itself has unique scratches/scuffs/label marks
- Above 9.2 raw: fewer defects = harder to fingerprint, but these will likely get slabbed anyway

### Decisions Made
- **Ignore spine photos** — too noisy (narrow geometry, inconsistent framing)
- **Ignore centerfold photos** — users may open to different pages
- **Focus on front + back covers only** — reliable, flat surfaces
- **DB fix applied:** fingerprint_hash VARCHAR(16→64), fingerprint_algorithm VARCHAR(20→50)

### Files Created This Session
- compare_fingerprints.py — Initial pHash comparison script
- analyze_thresholds.py — Deep threshold analysis
- test_perspective_correction.py — Perspective correction prototype
- test_feature_matching.py — SIFT/ORB/AKAZE comparison
- FINGERPRINT_TEST_SESSION47.md — This file

### Approach 4: Defect-Region Fingerprinting (tested while Mike was out)

**Grading pipeline analysis:** Claude Vision returns TEXT defect descriptions only (e.g., "minor corner wear"), no coordinates or bounding boxes. Can't crop specific defect locations from existing data.

**Alternative: Pure image processing approaches tested:**

**4a. Corner Region Matching (crop 4 corners, AKAZE match)**
- Result: Too few keypoints in small crops (0-7 matches typical)
- One bright spot: Back cover BR corner showed separation (gap +0.083)
- Problem: Noisy, unreliable with so few keypoints

**4b. Edge Region Matching (crop edge strips)**
- Result: Front bottom edge showed STRONG separation (gap +0.773!)
- Other edges: mostly overlap
- Suggests: edge wear is detectable but inconsistent across regions

**4c. High-Pass Filtering (remove artwork, keep texture/wear)**
- Gaussian HP (k=21, k=41) and Laplacian tested
- Result: Complete overlap on full images
- At normal photo resolution, surface texture too similar between copies

**4d. High-Pass + Corner Regions Combined**
- Some promise: Front TR corner (gap +0.063), Back BR corner (gap +0.036)
- Better than raw corners but still inconsistent

**Core Finding:** At standard phone photo resolution (~1024px), physical defects are sub-pixel. Feature matching can't reliably distinguish copies at this resolution.

### Approach 5: Full Resolution Testing (4000px+)
- Tested all approaches again at full resolution (up to 4080x3072) — no downscaling
- **Result: No improvement.** Full resolution actually made some comparisons worse.
- Front TR corner showed tiny gap (+0.021), everything else overlap or worse
- **Conclusion: Pixel-level image comparison CANNOT distinguish copies of the same issue from phone photos, regardless of resolution.** The printed content dominates at any scale.

### DEFINITIVE CONCLUSION
All pixel-based approaches exhausted:
- pHash/dHash/aHash/wHash (Approach 1-2): Can't handle angle variation
- SIFT/ORB/AKAZE feature matching (Approach 3): Matches printed content, not defects
- Corner/edge region cropping (Approach 4a-b): Too few keypoints, noisy
- High-pass filtering (Approach 4c-d): Texture too similar between copies
- Full resolution (Approach 5): No improvement over 1024px

**The answer is NOT pixel comparison. It's SEMANTIC defect analysis.**

### THE PATH FORWARD: Structural Defect Fingerprinting
Use Claude Vision to create a structured "defect map" — NOT pixel matching:

1. **Claude Vision defect localization** — Modify grading prompt to return:
   - Defect type (spine tick, corner ding, crease, color break, etc.)
   - Normalized location (percentage coordinates: "32% from top of spine")
   - Severity (minor, moderate, major)
   - Direction/angle for linear defects (creases, color breaks)

2. **Defect map comparison** — Compare maps structurally:
   - Same comic: defect types match, locations match within tolerance
   - Different copy: different defect types, different locations
   - Example: Copy A has "spine tick at 30%, corner ding at TR" vs Copy B has "spine tick at 65%, crease at BL" — clearly different

3. **Macro/close-up photos** — Consider adding a 5th photo: close-up of the most distinctive defect. At macro distance, pixel matching WOULD work.

4. **Slab-case fingerprinting** for high-grade (9.2+) comics — match on case scratches/scuffs

5. Store defect map as JSON fingerprint: `{defects: [{type, location_pct, severity, angle}, ...]}`

### Approach 6: Claude Vision Structural Defect Mapping
**Result: FAILED — defects too generic**
- Claude finds the same defects on every copy (rounded corners, edge wear, tanning)
- v1 (generic defects): complete overlap, no separation
- v2 (unique defects only): still overlapped — both copies share center crease
- Direct comparison: correctly IDs same comic (6/6) but says SAME for different copy too (0/6)
- Forensic + lineup prompts: same result — model can't see micro-differences at phone resolution
- Root cause: both copies genuinely share similar macro-defects (same age, similar handling)

### Approach 7: Edge Strip Hashing ✅ WINNER
**Result: CLEAN SEPARATION (excluding angled photos)**
- Key insight from user: differences between copies are at the EDGES (trim position, edge wear)
- Every comic is cut slightly differently at the printer — trim offset is a manufacturing fingerprint
- Method: hash thin edge strips (5% width, 8 regions, 4 hash algos) from front + back covers

**Results (combined front+back):**
| Comparison | Score | Expected | Result |
|-----------|-------|----------|--------|
| 002 vs 003 | 116.5 | SAME | ✅ same_copy |
| 002 vs 005 | 136.1 | DIFF | ✅ different_copy |
| 003 vs 005 | 131.0 | DIFF | ✅ different_copy |

**Gap: same max 116.5 vs diff min 131.0 = 14.5 points!**

**Thresholds established:**
- `<= 124`: SAME_COPY (same physical comic re-photographed)
- `>= 126`: DIFFERENT_COPY (different physical copy of same issue)
- `124-126`: UNCERTAIN (needs more photos or manual review)

**Critical requirement:** Photos must be taken in consistent portrait orientation. Angled/landscape photos (like 004) break the system completely.

**Integrated into production code:**
- `registry.py`: generates edge strip hashes during registration, stored in `fingerprint_composite` JSONB
- `monitor.py`: compares edge strips during monitoring, returns `copy_match` field
- Algorithm version: `comp_v3_edge`

---

## Cross-Project Idea: Chrome Extension Onboarding (from Tax Session)

**Inspiration:** Rakuten's Chrome extension install flow — pop-up prompt, one click to Chrome Web Store, instant activation.

**Apply to Slab Guard Monitor extension:**
- When user visits slabworthy.com/verify or registers a comic, show a non-intrusive prompt: "Protect your comics on eBay — Add Slab Guard to Chrome"
- One click → Chrome Web Store listing
- Extension auto-activates after install
- Same frictionless flow for eBay, Whatnot, Mercari marketplace monitoring
- Reference: Rakuten, Honey, Capital One Shopping all use this pattern effectively
