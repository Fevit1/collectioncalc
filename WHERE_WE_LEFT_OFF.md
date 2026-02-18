# Where We Left Off - Feb 18, 2026

## 🎉 Session 48 Accomplishments

### Problem: Edge Strip v3 Thresholds Didn't Generalize

Tested new registrations (006-009) against v3 edge strip fingerprinting. Results:
- 006 vs 007 (SAME): edge score = 111.9
- 006 vs 009 (DIFF): edge score = 113.4
- **Gap: only 1.5 points** (vs Session 47's 14.5 point gap)

Session 47 thresholds (≤124 SAME, ≥126 DIFF) were overfitted to those specific test photos. The threshold values didn't generalize to new registrations.

### Comprehensive Approach Testing (Session 48)

Tested 10+ approaches to distinguish same-copy from different-copy:

| # | Approach | Result | Notes |
|---|---------|--------|-------|
| 1 | Edge strip v3 (existing) | 1.5pt gap, unreliable | Overfitted thresholds |
| 2 | LBP texture analysis | Complete overlap ❌ | Photo variation dominates |
| 3 | Wavelet detail bands | Complete overlap ❌ | Same issue |
| 4 | SIFT-aligned residual | Complete overlap ❌ | DIFF had LOWER residual than SAME |
| 5 | Claude Vision defect annotation v1 | 2/4 correct ❌ | Inconsistent descriptions between photos |
| 6 | Claude Vision defect annotation v2 (artwork landmarks) | 2/4 correct ❌ | Same crease described as "horizontal" then "vertical" |
| 7 | Claude Vision direct side-by-side | 2/4 correct ❌ | Fixed SAME cases, broke DIFF cases |
| 8 | **Claude Vision "difference finder"** | **3/4 correct** ✅ | Best Vision approach |
| 9 | PatchCore anomaly detection | Near-complete overlap ❌ | Photo variation drowns defect signals |
| 10 | Self-referencing PatchCore | Minimal separation ❌ | Edge correlation showed 0.05 gap |
| 11 | Corner-focused with contour detection | Wrong direction ❌ | Contour detection gave inconsistent quads |
| 12 | **SIFT-aligned edge IoU** | **Clean separation** ✅✅ | **BEST APPROACH** |

### ✅ Winner: SIFT-Aligned Edge IoU

After SIFT aligning images using printed content as anchors, the Canny edge overlap (IoU) in edge regions cleanly separates same-copy from different-copy:

| Metric | SAME range | DIFF range | Separation |
|--------|-----------|-----------|------------|
| edge_edge_iou | [0.033, 0.036] | [0.001, 0.009] | ✅ NO OVERLAP, 7x ratio |
| edge_ssim | [0.558, 0.684] | [0.441, 0.535] | ✅ NO OVERLAP |
| corner_edge_iou | [0.011, 0.037] | [0.006, 0.008] | ✅ NO OVERLAP |
| all_edge_iou | [0.022, 0.037] | [0.003, 0.009] | ✅ NO OVERLAP |

**Why this works:** SIFT aligns the printed artwork perfectly. After alignment, edge structures from same-copy pairs overlap (same physical defects visible), while different-copy pairs only share printed content edges — their physical defects are in different locations, reducing IoU.

**Key limitation:** Angled photo (008) only achieved 30 SIFT inliers (vs 2000+ for straight photos). The approach needs decent photo quality for reliable SIFT matching.

### ✅ Claude Vision "Difference Finder" (Supplementary Layer)

Best prompt approach: ask Claude to enumerate ALL visible differences, classify each as PHOTO (lighting/angle artifact), PHYSICAL (real defect difference), or AMBIGUOUS.

Results:
- 006 vs 007 (SAME): ✅ SAME_COPY (0 physical diffs, conf 0.75)
- 006 vs 009 (DIFF): 🔶 UNCERTAIN (0 physical, 2 ambiguous, conf 0.40)
- 007 vs 009 (DIFF): ✅ DIFFERENT_COPY (3 physical diffs, conf 0.80)
- 006 vs 008 (SAME): ✅ SAME_COPY (0 physical diffs, conf 0.95)

Cost: ~$0.03 per comparison (Claude Sonnet). Good as interpretability/confirmation layer.

### ✅ Anomalib Research & Decision

Mike asked about RT-DETR, U-Net++, Raster Vision. Research found:
- RT-DETR: Wrong paradigm (object detection, not defect detection)
- U-Net++: High annotation burden, medical focus
- Raster Vision: Wrong domain (geospatial)
- **Anomalib (PatchCore/EfficientAD)**: Best fit for unsupervised defect detection

Implemented PatchCore directly (full Anomalib framework too large for dev environment). Found that deep CNN features from pretrained ImageNet models are too semantic — they capture object recognition patterns, not physical surface defects. The SIFT-aligned edge IoU approach outperforms PatchCore for this specific use case.

### Preference Saved

Mike requested: "Look outside existing stack when facing challenging hurdles, and make recommendations." Saved to Claude memory/preferences.

---

## 🎯 Recommended Production Architecture

### Multi-Layer Copy Verification Pipeline

**Layer 1: Issue Matching (existing, fast)**
- Composite hash (pHash + dHash + aHash + wHash)
- Confirms the image shows the correct comic ISSUE
- Threshold: composite_distance ≤ 77

**Layer 2: Copy Matching (NEW — SIFT + Edge IoU)**
- SIFT-align verification photo to registered photo
- Compute Canny edge IoU in edge regions (top/bottom/left/right strips)
- SAME_COPY: edge_iou ≥ 0.025
- DIFFERENT_COPY: edge_iou ≤ 0.010
- UNCERTAIN: 0.010 - 0.025
- Fast (~8 seconds on CPU, could be faster on GPU)

**Layer 3: Claude Vision Confirmation (optional, for high-value items)**
- "Difference finder" prompt comparing both photos
- Classifies differences as PHOTO vs PHYSICAL
- Good for generating human-readable verification reports
- Cost: ~$0.03 per comparison

### Registration Requirements
- Front-facing photo (reject heavily angled submissions)
- SIFT keypoints extracted and stored at registration time
- Canny edge map of edge regions stored for comparison
- Existing composite hash + edge strip fingerprint still generated for backward compatibility

### Verification Flow
1. Issue match via composite hash → quick rejection of non-matches
2. SIFT alignment → if <50 inliers, flag as "photo quality insufficient"
3. Edge IoU computation → SAME_COPY / DIFFERENT_COPY / UNCERTAIN
4. (Optional) Claude Vision for UNCERTAIN cases or high-value items

---

## 🎉 Session 49 Accomplishments

### Production Integration: SIFT + Edge IoU + Claude Vision

Created `routes/slab_guard_cv.py` — standalone CV engine module:
- `compare_covers(ref_url, test_url)` — fast quantitative comparison (~3-8s)
- `compare_covers_with_vision(ref_url, test_url)` — full hybrid with Claude Vision (~10-15s, ~$0.015/call)
- Graceful fallbacks: if OpenCV unavailable returns error; if Anthropic unavailable falls back to quantitative-only
- All Session 48 thresholds baked in: `EDGE_IOU_SAME_COPY=0.025`, `EDGE_IOU_DIFF_COPY=0.010`, `MIN_SIFT_INLIERS=50`

Updated `routes/monitor.py` — now four-tier matching:
- `/api/monitor/check-image` enhanced with `use_sift` (default: true) and `use_vision` (default: false) params
- After issue-level composite matching, runs SIFT+edge IoU on each match to determine copy identity
- Match results now include `sift_edge_iou`, `sift_alignment`, and optional `vision_verdict`/`vision_reasoning`
- New endpoint: `/api/monitor/compare-copies` for direct two-photo copy comparison

Updated `requirements.txt`:
- Added `opencv-python-headless>=4.8.0` and `numpy>=1.24.0`

### Integration Test Results (local photos)
```
006 vs 007 (SAME):    edge_iou=0.0473 → same_copy     ✅
006 vs 009 (DIFF):    edge_iou=0.0102 → uncertain      ✅ (Vision resolves this)
007 vs 009 (DIFF):    edge_iou=0.0016 → different_copy  ✅
006 vs 008 (SAME):    30 inliers → uncertain            ✅ (angled photo, expected)
```

### Architecture Note: No Registration Changes Needed
SIFT comparison is performed on-the-fly by downloading both photos. No SIFT descriptors or edge maps need to be stored at registration time — the existing photo URLs in the `collections.photos` JSONB column are sufficient.

---

## 🎯 Next Steps (Prioritized)

### Immediate (Next Session)

1. **Photo quality gate at registration**
   - Reject photos with <100 SIFT keypoints (too blurry/small)
   - Warn about angled photos (check homography distortion)
   - Minimum resolution check

2. **Broader testing**
   - Test with more comic titles, conditions, and lighting scenarios
   - Tune edge_iou thresholds with more data
   - Test with marketplace listing photos (eBay, etc.)

3. **Deploy & smoke test**
   - Deploy updated code to Railway/production
   - Run check-image against test registrations via API
   - Verify SIFT comparison works end-to-end in production

### Short-Term

4. **Perspective correction for angled photos**
   - Use SIFT matches to warp angled photos to front-facing orientation
   - Then apply edge IoU analysis on corrected images
   - Improves handling of marketplace listing photos

5. **Combine front + back cover scores**
   - Currently only comparing front covers
   - Back cover edge IoU would provide additional discrimination

6. **Performance optimization**
   - Cache SIFT keypoints at registration time (avoid re-downloading + re-extracting)
   - Limit SIFT comparison to top-N composite matches (avoid N² comparisons)

---

## 📋 Other Pending Tasks

### Tax Season
- [ ] TurboTax Premier from Costco at $82.99
- [ ] Need Johnny's 1098-T from Carleton for $2,500 AOTC credit
- [ ] Expected federal refund ~$20,800

### Home
- [ ] Door lock installation — postponed due to storm

### Cross-Project Idea
- [ ] Chrome extension onboarding (Rakuten-style: pop-up → Chrome Store → boom)

---

## 📁 Test Files Created (Session 48)

All in working directory (not in V2):
```
test_v3_fingerprints.py              - v3 edge strip threshold test (FAILED - 1.5pt gap)
test_improved_fingerprint.py         - LBP, wavelet, high-pass, color, gradient tests
test_improved_v2.py                  - Comic detection + normalized comparison
test_sift_compare.py                 - SIFT-aligned full-image residual analysis
test_defect_annotation.py            - Claude Vision defect mapping v1
test_defect_v2.py                    - Claude Vision v2 (artwork landmarks)
test_direct_compare_v2.py            - Claude Vision direct side-by-side
test_difference_finder.py            - Claude Vision "difference finder" (BEST VISION)
test_patchcore.py                    - PatchCore anomaly detection
test_patchcore_v2.py                 - Self-referencing PatchCore
test_corner_focus.py                 - Corner-focused with contour detection
test_sift_corners.py                 - SIFT-aligned edge IoU (BEST OVERALL)
save_test_photos.py                  - Download test photos for inspection
```

Generated output files:
```
heatmap_A_*.png, heatmap_B_*.png     - PatchCore anomaly heatmaps
heatmap_selfref_*.png                - Self-referencing PatchCore heatmaps
corrected_*.jpg                      - Perspective-corrected images
sift_compare_*_vs_*.png              - SIFT alignment visualizations
Various *_results.json               - Detailed test results
```

## 📁 Production Files Modified (Session 49)

```
routes/slab_guard_cv.py              - NEW: SIFT + edge IoU + Claude Vision CV engine
routes/monitor.py                    - UPDATED: four-tier matching, SIFT integration, compare-copies endpoint
requirements.txt                     - UPDATED: added opencv-python-headless, numpy
routes/registry.py                   - UNCHANGED (no registration changes needed)
wsgi.py                              - UNCHANGED (slab_guard_cv imported by monitor.py directly)
```

## 🔑 Test Comics in Database

| Serial | Physical Copy | Photo Type | Notes |
|--------|--------------|------------|-------|
| SW-2026-000001 | Copy A | Straight | Legacy phash_legacy only |
| SW-2026-000002 | Copy A | Straight | Composite v2 |
| SW-2026-000003 | Copy A | Straight | Composite v2 |
| SW-2026-000004 | Copy A | Angled | Composite v2, breaks edge matching |
| SW-2026-000005 | Copy B | Straight | Composite v2, different physical copy |
| SW-2026-000006 | Copy A | Straight | Composite v3_edge, new registration |
| SW-2026-000007 | Copy A | Straight | Composite v3_edge, same as 006 |
| SW-2026-000008 | Copy A | Angled | Composite v3_edge, same as 006 |
| SW-2026-000009 | Copy B | Straight | Composite v3_edge, different physical copy |

All are: The Official Handbook of the Marvel Universe #2

---

*Last updated: February 18, 2026 (Session 49)*
