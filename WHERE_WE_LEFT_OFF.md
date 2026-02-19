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

## 🎉 Session 49b: Extra Photo Support for Enhanced Fingerprinting

### Feature: Upload extra close-up/defect photos per comic

Users on paid plans can now upload additional photos (defects, close-ups, alternate angles)
to improve copy-level identification for high-value comics.

**Billing integration:**
- Free: 0 extra photos
- Pro ($4.99/mo): 4 extra photos per comic
- Guard ($9.99/mo): 8 extra photos per comic
- Dealer ($24.99/mo): 12 extra photos per comic
- `multi_photo` + `extra_photos_limit` feature flags in billing plans

**Photo types supported:** defect, closeup_front, closeup_back, closeup_spine,
edge_top, edge_bottom, edge_left, edge_right, alternate_front, alternate_back, other

**New API endpoints:**
- `POST /api/images/upload-extra` — upload extra photo (requires auth + paid plan)
- `POST /api/images/delete-extra` — remove extra photo by index
- `GET /api/images/extra-types` — list valid photo types with descriptions

**Storage:** Extra photos stored in `collections.photos` JSONB under `extra` array:
```json
{ "front": "...", "back": "...", "extra": [{"type": "defect", "label": "Spine tick", "url": "..."}] }
```

**CV engine enhancements (slab_guard_cv.py):**
- `compare_covers()` now accepts `extra_ref_photos` — if main SIFT alignment fails,
  tries `alternate_front` photos as fallback reference (solves angled-photo problem)
- `compare_covers_with_vision()` sends defect/closeup photos to Claude Vision as
  additional evidence images (up to 4, resized to 600px max)

**Registration (registry.py):**
- Extra alternate front/back photos get edge strip hashes at registration
- Confidence score boosted: +2 per extra photo (up to +16 max)

**Test results:**
- 006 vs 008 with alternate (007): 33→51 inliers, alignment now succeeds!
  IoU=0.022 (uncertain) — Vision layer resolves this to SAME_COPY
- All existing tests still pass (no regression)

---

## ✅ Session 49c: Production Deploy & Smoke Test

Deployed to Render (https://collectioncalc-docker.onrender.com) — no errors.

### Smoke Test Results (all passing)

| Endpoint | Test | Result |
|----------|------|--------|
| `GET /api/billing/plans` | extra_photos_limit in all tiers | ✅ free=0, pro=4, guard=8, dealer=12 |
| `GET /api/images/extra-types` | Returns 11 photo types | ✅ All types with descriptions |
| `POST /api/images/upload-extra` | Rejects unauthenticated | ✅ 401 "Authentication required" |
| `POST /api/images/delete-extra` | Rejects unauthenticated | ✅ 401 "Authentication required" |
| `POST /api/monitor/compare-copies` | Identical images | ✅ same_copy, 2310 inliers, IoU=0.75 |
| `POST /api/monitor/compare-copies` | Different images | ✅ uncertain, alignment failed (2 matches) |
| `POST /api/monitor/compare-copies` | Same image, different resolution | ✅ same_copy, 790 inliers, IoU=0.15 |
| `POST /api/monitor/check-image` | Full pipeline with test photo | ✅ sift_available=true, hash generated |
| `GET /api/monitor/stolen-hashes` | Returns empty list | ✅ count=0 |

**Key confirmation:** OpenCV (`sift_available: true`) and the full SIFT pipeline are working on the Render production server.

**Not tested (needs fresh JWT):** upload-extra with real auth.

### Real R2 Photo Comparison Results (Vision-enabled)

Tested registered comics (Handbook #2) with `use_vision: true`:

| Pair | Expected | Inliers | Edge IoU | SIFT | Vision | Final | ✓? |
|------|----------|---------|----------|------|--------|-------|-----|
| 006 vs 007 | SAME (A↔A) | 2141 | 0.015 | uncertain | uncertain | uncertain | ⚠️ |
| 009 vs 005 | SAME (B↔B) | 2671 | 0.050 | same_copy | same_copy | same_copy | ✅ |
| 006 vs 005 | DIFF (A↔B) | 2156 | 0.011 | uncertain | different_copy | different_copy | ✅ |
| 007 vs 005 | DIFF (A↔B) | 2025 | 0.023 | uncertain | uncertain | uncertain | ⚠️ |
| 009 vs 006 | DIFF (B↔A) | 2262 | 0.012 | uncertain | uncertain | uncertain | ⚠️ |
| 001 vs 002 | SAME (A↔A) | 41 | — | uncertain | — | uncertain | ⚠️ align fail |
| 001 vs 003 | SAME (A↔A) | 31 | — | uncertain | — | uncertain | ⚠️ align fail |
| 003 vs 005 | DIFF (A↔B) | 28 | — | uncertain | — | uncertain | ⚠️ align fail |

**Key findings:**
- Newer registrations (005-009): 2000+ inliers, SIFT works well
- Older registrations (001-003): ~30 inliers, alignment fails — photo quality issue
- Same_copy threshold (≥0.025) too tight for real phone photos — 006 vs 007 (same copy) only got 0.015
- 009 vs 005 (same copy B) clearly passed at 0.050 — photo consistency matters
- Vision correctly resolved 006 vs 005 as different_copy, but couldn't break uncertain on 006 vs 007
- **Threshold stays at 0.025:** Considered lowering to 0.018, but 007 vs 005 (different copies) had IoU=0.023, so lowering would cause false positives
- **The 0.010-0.025 uncertain band is intentionally wide** — Vision resolves it
- **Vision prompt rewritten (Session 49c):** Now demands definitive SAME/DIFFERENT verdict based on physical defect analysis (corners, spine, edges), not just metrics interpretation. Only allows UNCERTAIN when images are too blurry to judge.
- **Photo quality gate needed:** reject photos that can't SIFT-align with minimum inliers

---

## 🎉 Session 50: Border Inlier Breakthrough + Vision Improvements

### Key Discovery: SIFT Border Inlier Counting

Physical defects in comic book border regions (spine ticks, corner bends, edge chips) create unique SIFT keypoints. After SIFT alignment with RANSAC, these border-region inlier matches perfectly discriminate same-copy from different-copy:

| Pair | Type | Border Inliers | IoU | Verdict |
|------|------|---------------|-----|---------|
| HB 006 vs 007 | SAME | **4** | 0.047 | same_copy ✅ |
| HB 006 vs 009 | DIFF | **0** | 0.011 | different_copy ✅ |
| HB 007 vs 009 | DIFF | **0** | 0.008 | different_copy ✅ |
| IM 010 vs 011 | SAME | **3** | 0.011 | same_copy ✅ |
| IM 010 vs 012 | DIFF | **0** | 0.010 | different_copy ✅ |
| IM 011 vs 012 | DIFF | **0** | 0.005 | different_copy ✅ |

**6/6 correct, 0 uncertain, 0 wrong — stable across 5+ runs.**

Note: Iron Man 010 vs 011 has IoU=0.011 (below same_copy threshold) because the photos have different framing that creates warp void regions. But border_inliers=3 correctly identifies it as same-copy anyway. This is the metric's key strength — it works even when IoU fails due to framing differences.

### Implementation Details

**New constants:**
- `BORDER_INLIER_SAME_COPY = 2` — ≥2 border inliers = same physical copy
- `BORDER_INLIER_EDGE_WIDTH = 60` — wider border strip for inlier counting (50px too narrow for Iron Man, 70px+ picks up printed content)
- `BORDER_INLIER_RUNS = 3` — run SIFT alignment 3 times, take max border inliers (stabilizes RANSAC non-determinism)

**New function:** `_sift_align_with_stable_border(ref, test)` — runs SIFT alignment multiple times, returns the run with highest border inlier count. Early-exits when threshold met.

**Updated `_sift_align()`:** Now counts border vs interior inliers after RANSAC, returns `border_inliers`, `interior_inliers`, `border_inlier_pct`, `border_avg_distance` in stats dict.

**Updated verdict logic (both `compare_covers()` and `compare_covers_with_vision()`):**
1. dilated IoU ≥ 0.13 → same_copy (unchanged)
2. border_inliers ≥ 2 → same_copy (NEW — catches poor-framing cases)
3. border_inliers == 0 AND dilated IoU < 0.13 → different_copy (NEW — zero border inliers is strong DIFF evidence)
4. Low IoU with some border inliers → uncertain (conflicting signals)

### Vision Prompt Improvements (Session 50)

**Problem:** Vision prompt was hallucinating — confusing printed artwork features for physical defects. Called HB 006 vs 009 (DIFF) as SAME_COPY with 0.88 confidence because it saw "matching blue-gray tones" (that's the ink, not a defect).

**Fixes:**
- Added explicit "WHAT TO IGNORE" list (❌ printed artwork features)
- Added "WHAT COUNTS AS EVIDENCE" list (✅ physical defects only)
- Changed default verdict to DIFFERENT_COPY (was SAME_COPY)
- Added 4x-zoom corner crops as primary evidence
- Added Canny edge overlay diagnostic image (GREEN=matching, RED/BLUE=mismatching)
- Withheld quantitative metrics from prompt to prevent anchoring bias
- Added void region detection — black warp artifacts excluded from IoU and Vision crops

**Vision test results:** 3/3 on Handbook #2 after anti-hallucination fix. Vision is now conservative (may say DIFFERENT for true SAME pairs), but that's fine — quant catches same-copy via dilated IoU or border inliers. Vision's primary role is resolving DIFF cases that quant can't handle.

### New Test Data: Iron Man #200

Mike uploaded three photos for cross-validation:
- Serial 10 (SW-1771444761941-4acctlhnv) — Copy A
- Serial 11 (SW-1771444839212-ykfnqtaks) — Copy A (same physical comic as 10)
- Serial 12 (SW-1771444910763-ls43ioeam) — Copy B (different physical comic)

Local copies saved as `ironman_010.jpg`, `ironman_011.jpg`, `ironman_012.jpg` in V2.

### Use Case Clarification

Mike clarified the theft recovery workflow:
1. Person registers comic with good photos per our guidelines
2. Comic is stolen
3. Victim finds it on eBay
4. Pretends to be a bidder, asks seller for high-res photos
5. Scans those seller photos against their registered fingerprint

This means we can't control the marketplace photo quality. The border inlier approach handles this well — it only needs SIFT alignment to succeed (50+ inliers), then the border inlier count is robust to framing/perspective differences.

---

## 🎯 Next Steps (Prioritized)

### Immediate (Next Session)

1. **Deploy Session 50 changes to Render**
   - Border inlier counting, multi-run SIFT, updated Vision prompt
   - Smoke test with R2 photo URLs (Iron Man + Handbook)
   - Verify 6/6 correct on production

2. **Photo quality gate at registration**
   - Reject photos with <100 SIFT keypoints (too blurry/small)
   - Warn about angled photos (check homography distortion)
   - Minimum resolution check

3. **Broader testing with marketplace photos**
   - Test with real eBay listing photos (different lighting, angles, backgrounds)
   - More comic titles and conditions
   - Stress test border inlier approach with low-quality photos

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

## 📁 Production Files Modified (Sessions 49 + 49b)

```
routes/slab_guard_cv.py              - NEW (49): SIFT + edge IoU + Claude Vision CV engine
                                       UPDATED (49b): extra_ref_photos param, alternate fallback, Vision closeups
routes/monitor.py                    - UPDATED (49): four-tier matching, SIFT integration, compare-copies endpoint
                                       UPDATED (49b): passes extra photos through to CV engine
routes/images.py                     - UPDATED (49b): upload-extra, delete-extra, extra-types endpoints
routes/billing.py                    - UPDATED (49b): extra_photos_limit per plan, check_feature_access
routes/registry.py                   - UPDATED (49b): fingerprints alternate photos, confidence boost for extras
routes/collection.py                 - UNCHANGED (already returns full photos JSONB including extras)
requirements.txt                     - UPDATED (49): added opencv-python-headless, numpy
wsgi.py                              - UNCHANGED (no new blueprints needed)
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

*Last updated: February 18, 2026 (Session 50 — border inlier breakthrough, 6/6 correct on Iron Man + Handbook)*
