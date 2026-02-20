"""
Slab Guard CV — Computer Vision Engine for Copy-Level Identification
=====================================================================

Hybrid approach combining:
  1. SIFT-based image alignment (geometric correction)
  2. Edge IoU computation (quantitative copy fingerprint)
  3. Claude Vision "Difference Finder" (semantic interpretation)

Usage from monitor.py:
  from routes.slab_guard_cv import compare_covers, compare_covers_with_vision

Thresholds (Session 48-50, validated with real phone photos):
  - dilated edge_iou ≥ 0.13: SAME_COPY (3px tolerance for phone photo shifts)
  - border_inliers ≥ 2: SAME_COPY (SIFT matches on physical defects in border)
  - strict edge_iou ≤ 0.010 AND border_inliers == 0: DIFFERENT_COPY
  - otherwise: UNCERTAIN → Claude Vision resolves with zoomed edge + corner crops

═══════════════════════════════════════════════════════════════════════
⚠️  APPROACHES TESTED AND FAILED FOR COPY-LEVEL IDENTIFICATION
═══════════════════════════════════════════════════════════════════════

These were exhaustively tested in Sessions 48-53 (Feb 2026) on real phone photos
of Handbook of the Marvel Universe #2 and Iron Man #200.

Each entry follows the format:
  APPROACH → GOAL → WHAT HAPPENED → WHY IT DOESN'T WORK FOR THIS USE CASE
  (The approach itself may be valid for other problems — these notes are specific
  to the problem of distinguishing same vs different physical comic book copies
  from phone photos.)

PIXEL/TEXTURE-BASED APPROACHES:
  ❌ LBP (Local Binary Patterns) texture analysis
     GOAL: Use local texture patterns to fingerprint physical paper surface.
     RESULT: Same-copy and different-copy score distributions overlap completely.
     WHY: LBP captures micro-texture, but phone photo variation (lighting angle,
     camera sensor noise, white balance) creates larger texture differences between
     two photos of the SAME comic than the physical differences between two
     DIFFERENT comics. LBP might work with controlled imaging (e.g., scanner or
     fixed camera rig) but not with casual phone photos.

  ❌ Wavelet detail band analysis
     GOAL: Extract high-frequency detail coefficients to detect physical defects.
     RESULT: Complete overlap between same-copy and different-copy distributions.
     WHY: High-frequency wavelet bands are dominated by camera sensor noise and
     JPEG compression artifacts, not physical defects. The defect signal (a crease
     or chip) is subtle relative to the noise floor of a phone camera. Might work
     with RAW sensor data or high-end imaging, but not consumer phone JPEGs.

  ❌ High-pass filtering / gradient magnitude
     GOAL: Isolate edge/defect information by removing low-frequency (lighting).
     RESULT: No separation between same and different copies.
     WHY: Same fundamental problem as wavelets — camera sensor noise in the high-
     frequency domain overwhelms the subtle physical defect signal. Additionally,
     printed artwork has strong high-frequency content (halftone dots, fine lines)
     that dominates over physical wear features.

  ❌ PatchCore anomaly detection (Anomalib-style, using pretrained ImageNet backbone)
     GOAL: Use deep CNN features to detect anomalous regions (physical defects) that
     differ between copies. PatchCore is state-of-the-art for industrial surface
     defect detection (scratches on metal, fabric flaws).
     RESULT: Complete distribution overlap. PatchCore scored similar anomaly levels
     for same-copy and different-copy pairs.
     WHY: The ImageNet-pretrained backbone (e.g., WideResNet50) extracts SEMANTIC
     features — it understands "comic book cover," "Iron Man helmet," "red and gold
     color scheme." It does NOT encode physical paper properties like "crease at
     position X" or "chip on left edge." The feature space simply doesn't represent
     the signal we need. PatchCore excels at industrial QC where defects are visually
     obvious against uniform surfaces; comic covers have complex printed artwork that
     drowns the defect signal in the feature space. A PatchCore model fine-tuned on
     comic book defect data might work, but off-the-shelf ImageNet features do not.

  ❌ Self-referencing PatchCore (using one photo as its own reference distribution)
     GOAL: Instead of building a PatchCore model from multiple reference images, use
     the single registration photo as the reference and detect what's "anomalous"
     in the test photo relative to it.
     RESULT: Minimal separation (0.05 gap in edge correlation between same/diff).
     WHY: Same backbone limitation as standard PatchCore — the features don't encode
     physical surface properties. Additionally, using a single reference image gives
     a very noisy baseline, making anomaly detection even less reliable.

  ❌ Edge strip v3 perceptual hash thresholds (8 regions × 4 algorithms = 32 hashes)
     GOAL: Compare perceptual hashes of edge strip regions (top, bottom, left, right,
     corners) to detect manufacturing trim differences between copies.
     RESULT: Session 47 found 14.5pt gap on initial test pair; Session 48 found only
     1.5pt gap on new registrations with different photos. Not generalizable.
     WHY: Perceptual hash distances in small regions are highly sensitive to photo
     framing, rotation, and lighting. The 14.5pt gap was specific to two photos
     taken under very similar conditions. New photos with slightly different framing
     collapsed the gap. The approach might work with extremely standardized photo
     conditions (same camera, same angle, same lighting) but not with casual photos.

SIFT-BASED APPROACHES:
  ❌ SIFT-aligned pixel residual (compute difference image after SIFT alignment)
     GOAL: After aligning two photos using SIFT, compute pixel-level residual. Same
     copy should have low residual (same defects), different copy higher residual.
     RESULT: Counter-intuitive — DIFFERENT copies sometimes had LOWER residual than
     SAME copies.
     WHY: After SIFT alignment, the printed artwork aligns perfectly for ALL copies
     (same issue, same print plate). The residual therefore mostly captures PHOTO
     differences (lighting, camera response, color balance), not physical differences.
     Two photos from different cameras of different copies can have lower residual
     than two photos from the same camera of the same copy if the camera settings
     happen to produce similar tonal response. The residual measures photography
     consistency, not physical copy identity.

CLAUDE VISION APPROACHES:
  ❌ Vision defect annotation v1 (describe defects in each photo independently)
     GOAL: Have Claude describe physical defects in Photo A, then separately in Photo
     B, then compare the text descriptions to find matches.
     RESULT: 2/4 correct. Same physical crease described as "horizontal" in one
     analysis and "diagonal" or "vertical" in another.
     WHY: Claude Vision doesn't have consistent spatial reference when analyzing
     images independently. The same feature can be described differently depending
     on what else is in the image, how it's oriented, and what Claude focuses on.
     Text-based descriptions of physical features are inherently lossy and
     inconsistent. Direct visual comparison (both images in same prompt) works
     much better than independent description + text matching.

  ❌ Vision defect annotation v2 (use printed artwork landmarks as reference points)
     GOAL: Fix the inconsistency problem by asking Claude to describe defect positions
     relative to specific printed artwork landmarks (e.g., "3cm below Iron Man's left
     repulsor blast").
     RESULT: 2/4 correct. Landmark-relative descriptions still varied.
     WHY: Claude doesn't reliably estimate distances or positions relative to
     landmarks across separate analyses. The same defect near Iron Man's knee was
     described as "just below the knee" in one photo and "at mid-thigh level" in
     another. Relative spatial reasoning from images is not precise enough for
     forensic-level matching.

  ❌ Vision direct side-by-side v1 (show both photos, ask "same or different copy?")
     GOAL: Let Claude compare both photos directly in a single prompt without
     structured analysis steps.
     RESULT: Fixed SAME_COPY cases (correctly identified matching copies) but broke
     DIFFERENT_COPY cases (called different copies "same").
     WHY: Without a structured analysis framework, Claude defaults to "these look
     very similar" for any two copies of the same ISSUE. Comics from the same print
     run ARE visually near-identical — the differences are subtle physical wear, not
     obvious visual differences. An unstructured prompt lets Claude focus on the
     overwhelming printed content similarity instead of the subtle physical
     differences. The "difference finder" structured prompt (✅ what works) solves
     this by forcing region-by-region physical defect analysis.

  ❌ Passing quantitative metrics to Vision prompt (IoU values, border inlier counts)
     GOAL: Give Vision the SIFT metrics as context to help it make a better decision.
     RESULT: Vision's verdicts became correlated with the metrics shown, even when
     the metrics were wrong. For example, if we showed "dilated IoU: 0.18" (high),
     Vision was more likely to say SAME_COPY regardless of what it saw in the images.
     WHY: Anchoring bias — a well-documented cognitive bias where an initial number
     influences subsequent judgment. By showing metrics first, Vision's independent
     visual analysis was compromised. Metrics MUST be withheld so Vision makes a
     genuinely independent assessment. We combine the two verdicts programmatically
     after both have been computed independently.

CONTOUR/GEOMETRY APPROACHES:
  ❌ Corner-focused contour detection (detect comic outline quadrilateral, compare)
     GOAL: Detect the comic book's rectangular outline via contour detection, then
     compare corner geometry between photos to detect different physical copies.
     RESULT: Results went in WRONG direction on some test pairs (same-copy scored
     as more different than different-copy).
     WHY: Contour detection (Canny + findContours + polygon approximation) produces
     inconsistent quadrilaterals depending on the background. A comic on a dark
     blanket gives a different contour than the same comic on a white table. The
     detected "corners" jump around with background changes, making the geometry
     comparison meaningless. Might work with background removal (chroma key) or
     controlled imaging, but not with casual photos on varied surfaces.

TEXTURE FINGERPRINTING APPROACHES (Session 54):
  ❌ Bandpass filtering (4 scales: sigma 1-10, 2-20, 3-40, 5-50)
     GOAL: Isolate halftone dot / paper fiber frequency band. Remove low-freq
     lighting AND high-freq sensor noise, keeping only physical texture signal.
     RESULT: Complete overlap. Best NCC was 0.634 same-copy vs 0.492-0.730 different.
     WHY: Even with noise floor removal via bandpass, camera sensor variation STILL
     overwhelms physical texture signal. Phone sensors differ in pixel size, Bayer
     pattern, noise characteristics — these create per-camera texture signatures that
     dominate over the physical paper/ink texture.

  ❌ Phase correlation (FFT phase in 4 frequency bands)
     GOAL: Compare structural positions via FFT phase. Phase encodes WHERE structures
     are (positions) while magnitude encodes HOW STRONG (intensity). Phase should be
     more robust to camera exposure changes.
     RESULT: Complete overlap in all bands. Mid-freq phase consistency was 0.536 for
     same-copy vs 0.470-0.787 for different — inverted for same-camera pairs.
     WHY: After SIFT alignment, the PRINTED CONTENT phase is near-identical for ALL
     copies (same print plate). Phase consistency was actually HIGHER for different-copy
     same-camera pairs (0.77 mid-freq) because the print dominates. Physical defects
     are too small relative to the print content signal in the phase domain.

  ❌ Gabor filter bank (6 orientations × 4 wavelengths)
     GOAL: Multi-scale, multi-orientation texture analysis. Compute mean energy and
     std at each (scale, orientation) to create texture descriptor vector.
     RESULT: Cosine similarity 0.995-0.998 for ALL pairs — no discrimination.
     Interior-only showed 0.0002 gap — too small for reliable thresholding.
     WHY: Gabor captures the DISTRIBUTION of texture energy across scales/orientations.
     This distribution is dominated by the printed artwork (same for all copies).
     Physical wear changes specific texture at specific locations, but the GLOBAL
     energy distribution barely changes. Gabor might work if applied only to small
     patches around known defect regions, but not as a global descriptor.

  ❌ DCT mid-frequency block energy (8×8 blocks, excluding DC and highest AC)
     GOAL: Capture structured detail via DCT coefficients (like JPEG does). Compare
     mid-frequency energy distribution across blocks.
     RESULT: Overlap. Cosine sim 0.859 same-copy vs 0.809-0.866 different same-camera.
     WHY: Camera exposure changes shift DCT coefficients globally, creating larger
     variation between photos than the physical surface differences create. The DC-
     excluded mid-frequency band still captures camera-dependent tonal response.

CROSS-CAMERA SPECIFIC FAILURES (Session 51-53):
  ❌ Canny edge overlay as evidence for Vision (cross-camera marketplace photos)
     GOAL: Show Vision a color-coded Canny edge comparison overlay (GREEN=matching
     edges, RED/BLUE=mismatching) to help it assess physical defect similarity.
     RESULT: Vision called different copies "same_copy" because the overlay showed
     "predominantly green matching along the spine" and "strong GREEN overlap in
     border regions." All 2 of 3 wrong verdicts cited the Canny overlay as evidence.
     WHY: After SIFT alignment, PRINTED CONTENT edges align perfectly across ALL
     copies of the same issue (same print plate = same edges). This creates false
     green signal in the overlay. The overlay is dominated by printed artwork edges,
     not physical defect edges. For same-camera comparisons, the relative difference
     between green (matching) and red/blue (mismatching) is informative because
     camera conditions are consistent. For cross-camera, the noise floor shifts and
     the overlay becomes meaningless. REMOVED from marketplace mode in Session 53.

═══════════════════════════════════════════════════════════════════════
✅  WHAT WORKS (and critical limitations)
═══════════════════════════════════════════════════════════════════════

SAME-CAMERA comparisons (registration vs re-verification, similar setup):
  ✅ SIFT-aligned edge IoU — 7x separation ratio, 6/6 correct on test set
  ✅ Border inlier counting — 3-4 for SAME, 0 for DIFF, perfect discrimination
  ✅ Claude Vision "difference finder" — 3/4 correct with structured checklist prompt
  ✅ Canny edge overlay — reliable diagnostic for same-camera, helps Vision analysis

CROSS-CAMERA / MARKETPLACE comparisons (eBay listing vs registration photo):
  ⚠️ SIFT-aligned edge IoU — UNRELIABLE. Dilated IoU separates CAMERA CONDITIONS
     (0.14-0.18 cross-camera vs 0.26-0.27 same-camera) but CANNOT discriminate
     physical copy identity. Background noise (blanket, mylar bag, table) creates
     false edge matches after alignment. (Session 51 finding)
  ⚠️ Border inliers — UNRELIABLE CROSS-CAMERA. Background textures near comic edges
     generate spurious SIFT keypoints that falsely count as border inliers. Example:
     eBay Iron Man vs registration got 2 border inliers (false positive) with high
     avg distance 158 (indicating poor quality matches). (Session 51-53 finding)
  ⚠️ Canny edge overlay — MISLEADING CROSS-CAMERA. Printed content edges match
     across all copies (same issue), creating false green (matching) signal. Vision
     was fooled into calling different copies "same_copy" because overlay showed
     "predominantly green." REMOVED from marketplace mode in Session 53.
  ✅ Claude Vision "difference finder" WITH marketplace prompt — Vision is the PRIMARY
     verdict in marketplace mode. Cross-camera prompt warns about environmental
     differences, removes Canny overlay, requires specific locatable physical defects
     (not general wear patterns). (Session 53)
  🔬 LPQ (Local Phase Quantization) — PROMISING, needs more testing. (Session 54)
     Uses STFT phase (blur-invariant). Chi-squared distance: SAME=0.055, DIFF=0.154-0.335.
     Gap of +0.099 — largest separation of any metric tested. Works cross-camera.
     KEY INSIGHT: LPQ power comes from BORDER WEAR PATTERNS, not paper fiber/halftone.
     Interior-only LPQ showed NO separation (0.011 same vs 0.013-0.083 diff — overlap).
     Threshold recommendation: chi2 < 0.10 → SAME_COPY, > 0.15 → DIFFERENT_COPY.
     ⚠️ Only 1 same-copy pair and 5 different-copy pairs tested — tiny sample size.
     Must validate on more data before deploying as production metric.
  🔬 Difference RMS (normalized, full image) — PROMISING, narrower gap. (Session 54)
     SAME=0.826, DIFF=0.903-1.141, gap=+0.076. But one cross-camera pair had
     interior RMS of 0.559 (dangerously close to same-copy range).

AUTO-ROTATION:
  ✅ EXIF transpose + aspect ratio heuristic (landscape→portrait via 270° CW)
     WHY 270° NOT 90°: Testing confirmed 270° CW (PIL rotate(270)) correctly orients
     phone photos taken with home button on right. 90° CCW gave hash distance 116
     vs 60 for 270° CW. This is the most common phone landscape orientation.
     WHY THIS MATTERS: Perceptual hashes (pHash, dHash, aHash, wHash) are NOT
     rotation-invariant. Without auto-rotation, a 90° rotated registration photo
     gets hash distance 103-113 against the same comic (blocked by 77 threshold).
     Auto-rotation dropped this to 60-88, enabling marketplace mode. (Session 51)

═══════════════════════════════════════════════════════════════════════
FUTURE RESEARCH DIRECTIONS (Updated Session 54)
═══════════════════════════════════════════════════════════════════════

The fundamental limitation of the current approach is that SIFT + edge IoU matches
VISUAL APPEARANCE, which is camera-dependent. Session 54 tested 7 texture approaches
and found that:
  - Paper fiber / halftone dot texture is NOT extractable from phone photos (sensor
    noise overwhelms physical texture at all tested frequency bands and scales)
  - The discriminative signal lives in BORDER WEAR PATTERNS, not interior content
  - LPQ (blur-invariant STFT phase) captures border wear robustly across cameras

Remaining research directions:

  1. INTEGRATE LPQ — Add as supplementary metric alongside edge IoU. Use as primary
     quantitative signal for marketplace mode (where edge IoU fails). Validate on
     more data before making it the sole metric. Threshold: chi2 < 0.10 → SAME,
     > 0.15 → DIFFERENT, 0.10-0.15 → UNCERTAIN → Vision resolves.

  2. Geometric distortion signatures — printing press creates unique distortions in
     color separation alignment. Positional (not photometric), so camera-invariant.
     Not yet tested. Would need color channel separation and sub-pixel registration.

  3. Deep contrastive learning (Siamese networks) — train on same-comic cross-camera
     pairs to learn what's invariant. This is how person re-ID solved cross-camera.
     Requires significant training data (many comic pairs photographed under varying
     conditions). Most viable as a long-term approach.

  4. Border-region-only LPQ variants — Since the signal is in the borders, test LPQ
     on ONLY the 4 edge strips (not full image). May improve signal-to-noise ratio.

See WHERE_WE_LEFT_OFF.md for full session history and test results.

═══════════════════════════════════════════════════════════════════════

Session 50 improvements:
  - Border inlier counting: SIFT inliers in border strips discriminate same-copy
    (3-4 border inliers) from different-copy (0 border inliers) — 6/6 correct
  - Added 4x-zoom corner crops (highest-signal regions for fingerprinting)
  - Structured checklist prompt forces systematic per-region analysis
  - Metrics withheld from Vision to prevent anchoring bias
  - Void region detection: black warp artifacts excluded from IoU and Vision crops
  - Canny edge overlay diagnostic image for Vision

Session 51 improvements:
  - Auto-rotation: EXIF orientation correction + aspect ratio heuristic
    Phone photos taken sideways (landscape) are rotated to portrait orientation.
    This fixes perceptual hash distances for rotated registration photos
    (e.g., Iron Man #200: hash distance dropped from 113 to 62 after rotation).

Session 53 improvements:
  - Refactoring: auto_orient_pil/preprocess moved to routes/fingerprint_utils.py
  - Marketplace mode: Vision as primary verdict (quant unreliable cross-camera)
  - Cross-camera Vision prompt: removes Canny overlay, adds environmental warnings,
    requires specific locatable defects for SAME_COPY verdict
  - Institutional knowledge embedded in code (this docstring)

Session 54 findings (texture fingerprinting prototype):
  - Tested 7 approaches: bandpass filtering, phase correlation, Gabor filter bank,
    LPQ, DCT energy, gradient orientation, difference texture analysis
  - LPQ (Local Phase Quantization) is the only metric with clear separation across
    cameras: chi2 SAME=0.055 vs DIFF=0.154-0.335 (gap +0.099)
  - LPQ works because STFT phase is blur-invariant (robust to camera focus changes)
  - Critical insight: discriminative signal is in BORDER WEAR, not paper fiber/halftone
  - Interior-only LPQ showed NO separation — the printed content dominates interior
  - All 4 "texture" approaches (bandpass, phase, Gabor, DCT) failed because camera
    sensor noise overwhelms physical texture signal at all frequency bands
  - Next: integrate LPQ as supplementary metric, validate on more data

Dependencies: opencv-python-headless, numpy, anthropic (optional)
"""

import numpy as np
import os

# OpenCV import with fallback
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️ OpenCV not available — SIFT copy matching disabled")

# Anthropic import with fallback
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# ── THRESHOLDS (Session 48-49d, validated with real phone photos) ──
# 49c: real-photo testing confirmed 0.010 for DIFF. Kept strict SAME at 0.025.
# 49d: Dilated IoU (3px) separates same-copy (0.14-0.19) from diff (0.09-0.12).
#   Threshold 0.13 correctly classifies all 5 test pairs.
#   Vision with zoomed edge crops went 5/5 on diff-copy detection.
EDGE_IOU_SAME_COPY = 0.025     # Strict IoU: above = same physical copy
EDGE_IOU_DIFF_COPY = 0.010     # Strict IoU: below = different physical copy
DILATED_IOU_SAME_COPY = 0.13   # Dilated IoU (3px tolerance): above = same copy
                                # Session 49d: same-copy pairs 0.140-0.189, diff pairs 0.088-0.119
MIN_SIFT_INLIERS = 50          # Minimum for reliable alignment
BORDER_INLIER_SAME_COPY = 2   # Session 50: ≥2 border inliers = same physical copy
                                # Same-copy pairs: 3-4 border inliers (defect features match)
                                # Diff-copy pairs: 0 border inliers (no shared defects)
                                # ⚠️ SAME-CAMERA ONLY. Cross-camera marketplace photos
                                # generate false border inliers from background texture
                                # (blanket fibers, table edges, mylar bag). Use Vision as
                                # primary verdict in marketplace_mode. (Session 51-53)
BORDER_INLIER_EDGE_WIDTH = 60  # Wider border for inlier counting (60px sweet spot)
                                # 50px too narrow for Iron Man, 70px+ picks up printed content
BORDER_INLIER_RUNS = 3         # Run SIFT align N times, take max border inliers
                                # RANSAC non-determinism can drop 3→0; 3 runs stabilizes
EDGE_WIDTH_PX = 50             # Edge strip width for IoU computation
TARGET_SIZE = (800, 1200)      # Standard comparison size

# ── LPQ THRESHOLDS (Session 54, validated on Iron Man #200 test set) ──
# LPQ (Local Phase Quantization) uses STFT phase — blur-invariant, works cross-camera.
# Chi-squared distance on 256-bin LPQ histograms:
#   SAME-COPY:  0.055 (1 pair tested)
#   DIFF-COPY same-camera: 0.196-0.212
#   DIFF-COPY cross-camera: 0.154-0.335
# Gap: +0.099 — largest separation of any metric tested.
# KEY INSIGHT: Signal lives in BORDER WEAR, not paper fiber/halftone.
# Interior-only LPQ shows NO separation (printed content dominates).
# ⚠️ Tiny sample size (1 same, 5 diff) — validate on more data.
LPQ_SAME_COPY = 0.10          # chi2 < 0.10 → SAME_COPY
LPQ_DIFF_COPY = 0.15          # chi2 > 0.15 → DIFFERENT_COPY
                                # 0.10-0.15 → UNCERTAIN (Vision resolves)
LPQ_WIN_SIZE = 5               # STFT window size for LPQ computation


# Session 53: Shared auto-orient — single source of truth in fingerprint_utils.py
from routes.fingerprint_utils import auto_orient_pil as _auto_orient_image


def _download_image(url, timeout=15):
    """Download image from URL, auto-orient, return as cv2 BGR array."""
    import requests
    from io import BytesIO
    from PIL import Image as PILImage

    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    img_pil = PILImage.open(BytesIO(response.content)).convert('RGB')
    img_pil = _auto_orient_image(img_pil)
    img_np = np.array(img_pil)
    return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)


def _resize_standard(img, size=TARGET_SIZE):
    """Resize image to standard comparison size."""
    return cv2.resize(img, size)


def _sift_align(ref, test, edge_width=EDGE_WIDTH_PX):
    """
    SIFT-align test image to reference image.

    Session 50: Now also computes border_inliers — the count of SIFT inlier
    matches that fall within the border strip region of the REF image. This is
    a powerful same-copy discriminator: physical defects in border regions create
    unique SIFT features that only match between photos of the same physical copy.
    Different copies share printed content (interior matches) but NOT physical
    defects (zero border matches).

    In testing: SAME pairs had 3-4 border inliers, DIFF pairs had exactly 0.

    Returns:
        aligned: Warped test image aligned to ref coordinate space
        stats: Dict with alignment quality metrics including border_inliers
    """
    gray_r = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    gray_t = cv2.cvtColor(test, cv2.COLOR_BGR2GRAY)

    sift = cv2.SIFT_create(nfeatures=5000)
    kp1, des1 = sift.detectAndCompute(gray_r, None)
    kp2, des2 = sift.detectAndCompute(gray_t, None)

    stats = {
        'kp_ref': len(kp1) if kp1 else 0,
        'kp_test': len(kp2) if kp2 else 0,
        'aligned': False,
        'border_inliers': 0,
        'interior_inliers': 0,
    }

    if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
        stats['error'] = 'insufficient_keypoints'
        return test, stats

    # FLANN-based matching
    FLANN_INDEX_KDTREE = 1
    flann = cv2.FlannBasedMatcher(
        dict(algorithm=FLANN_INDEX_KDTREE, trees=5),
        dict(checks=100)
    )
    matches = flann.knnMatch(des1, des2, k=2)

    # Lowe's ratio test
    good = [m for m, n in matches if m.distance < 0.7 * n.distance]
    stats['good_matches'] = len(good)

    if len(good) < 10:
        stats['error'] = 'insufficient_matches'
        return test, stats

    src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

    # Find homography with RANSAC
    M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)

    if M is None:
        stats['error'] = 'homography_failed'
        return test, stats

    inlier_mask = mask.ravel().astype(bool)
    inliers = int(inlier_mask.sum())
    stats['inliers'] = inliers
    stats['inlier_ratio'] = float(inliers / len(good))
    stats['aligned'] = inliers >= MIN_SIFT_INLIERS

    h, w = ref.shape[:2]

    # ── Session 50: Count border vs interior inliers ──
    # Physical defects in border regions create unique SIFT features.
    # Same-copy pairs have border inliers; different-copy pairs have zero.
    ew = edge_width
    border_count = 0
    interior_count = 0
    border_match_dists = []

    for i, (m, is_inlier) in enumerate(zip(good, inlier_mask)):
        if not is_inlier:
            continue
        x, y = int(kp1[m.queryIdx].pt[0]), int(kp1[m.queryIdx].pt[1])
        in_border = (y < ew or y >= h - ew or x < ew or x >= w - ew)
        if in_border:
            border_count += 1
            border_match_dists.append(m.distance)
        else:
            interior_count += 1

    stats['border_inliers'] = border_count
    stats['interior_inliers'] = interior_count
    stats['border_inlier_pct'] = float(border_count / inliers) if inliers > 0 else 0
    if border_match_dists:
        stats['border_avg_distance'] = float(np.mean(border_match_dists))

    aligned = cv2.warpPerspective(test, M, (w, h))

    return aligned, stats


def _sift_align_with_stable_border(ref, test, runs=BORDER_INLIER_RUNS):
    """
    Run SIFT alignment multiple times and take the run with the highest
    border_inliers count. RANSAC is non-deterministic — same-copy pairs
    may get 0 or 3 border inliers depending on the random seed. Running
    3 times and taking the max stabilizes the signal.

    Uses BORDER_INLIER_EDGE_WIDTH (60px) for border inlier counting
    but returns the alignment from the best run (which uses EDGE_WIDTH_PX
    for the actual alignment).

    ⚠️ CROSS-CAMERA LIMITATION (Session 51-53):
    Border inliers are reliable ONLY for same-camera/same-background comparisons.
    Cross-camera marketplace photos (e.g., eBay listing vs registration on blanket)
    create FALSE border inliers from background texture (blanket fibers, table edges,
    mylar bag reflections). The border_avg_distance metric can help flag these — real
    defect matches have low distance (~50-80), while false matches from background
    noise have high distance (~150+). However, the signal is not reliable enough for
    automated thresholding. In marketplace_mode, use Vision as primary verdict instead
    of trusting border inlier counts.
    """
    best_aligned = None
    best_stats = None
    best_border = -1

    for _ in range(runs):
        aligned, stats = _sift_align(ref, test, edge_width=BORDER_INLIER_EDGE_WIDTH)
        bi = stats.get('border_inliers', 0)
        if bi > best_border or best_aligned is None:
            best_border = bi
            best_aligned = aligned
            best_stats = stats
        # Early exit: if we found border inliers, no need to keep trying
        if bi >= BORDER_INLIER_SAME_COPY:
            break

    return best_aligned, best_stats


def _compute_edge_iou(ref, aligned, edge_width=EDGE_WIDTH_PX, dilate_px=3):
    """
    Compute Canny edge IoU for each edge region after alignment.

    Computes both strict (pixel-exact) and dilated edge IoU. Dilation allows
    for 1-3px positional shifts caused by photo variation (lighting, angle).
    Same-copy pairs benefit more from dilation because their edges are in
    nearly the right spots; different-copy pairs don't benefit as much.

    Session 50: Edges where the aligned image is mostly black (warp void) are
    excluded from the averages to prevent misaligned framing from dragging down
    the score. Per-edge results still include them (marked void=True).

    ⚠️ CROSS-CAMERA LIMITATION (Session 51):
    Dilated IoU separates CAMERA CONDITIONS (0.14-0.18 cross-camera vs 0.26-0.27
    same-camera) but CANNOT discriminate COPY IDENTITY for marketplace photos.
    Background differences (blanket vs white) and lighting create camera-specific
    edge patterns that overwhelm the subtle physical defect signal. Printed content
    edges dominate after SIFT alignment, and those match across ALL copies of the
    same issue. In marketplace_mode, use Vision as primary verdict.

    Returns:
        avg_iou: Average strict IoU across valid (non-void) edges
        per_edge: Dict with per-edge strict iou, dilated iou, ssim, and void flag
        avg_ssim: Average SSIM across valid edges
        avg_dilated_iou: Average dilated IoU across valid edges
    """
    h, w = ref.shape[:2]
    ew = edge_width

    edges = {
        'top': (ref[:ew, :], aligned[:ew, :]),
        'bottom': (ref[-ew:, :], aligned[-ew:, :]),
        'left': (ref[:, :ew], aligned[:, :ew]),
        'right': (ref[:, -ew:], aligned[:, -ew:]),
    }

    dilate_kernel = np.ones((dilate_px * 2 + 1, dilate_px * 2 + 1), np.uint8)

    per_edge = {}
    all_ious = []
    all_dilated_ious = []
    all_ssims = []

    for name, (r_region, a_region) in edges.items():
        # Check for warp void (mostly black aligned region)
        is_void = _region_is_black(a_region, threshold=10, min_pct=0.6)

        # Canny edge detection
        r_canny = cv2.Canny(r_region, 50, 150)
        a_canny = cv2.Canny(a_region, 50, 150)

        # Strict (pixel-exact) IoU
        intersection = cv2.bitwise_and(r_canny, a_canny).sum()
        union = cv2.bitwise_or(r_canny, a_canny).sum()
        iou = float(intersection / (union + 1e-8))
        per_edge[name] = {'iou': iou, 'void': is_void}

        # Dilated IoU — allow positional tolerance
        r_dilated = cv2.dilate(r_canny, dilate_kernel, iterations=1)
        a_dilated = cv2.dilate(a_canny, dilate_kernel, iterations=1)
        d_intersection = cv2.bitwise_and(r_dilated, a_dilated).sum()
        d_union = cv2.bitwise_or(r_dilated, a_dilated).sum()
        d_iou = float(d_intersection / (d_union + 1e-8))
        per_edge[name]['dilated_iou'] = d_iou

        # SSIM
        r_gray = cv2.cvtColor(r_region, cv2.COLOR_BGR2GRAY).astype(float) / 255.0
        a_gray = cv2.cvtColor(a_region, cv2.COLOR_BGR2GRAY).astype(float) / 255.0
        mu1 = cv2.GaussianBlur(r_gray, (11, 11), 1.5)
        mu2 = cv2.GaussianBlur(a_gray, (11, 11), 1.5)
        s1 = cv2.GaussianBlur(r_gray**2, (11, 11), 1.5) - mu1**2
        s2 = cv2.GaussianBlur(a_gray**2, (11, 11), 1.5) - mu2**2
        s12 = cv2.GaussianBlur(r_gray * a_gray, (11, 11), 1.5) - mu1 * mu2
        C1, C2 = 0.01**2, 0.03**2
        ssim_map = ((2*mu1*mu2+C1)*(2*s12+C2)) / ((mu1**2+mu2**2+C1)*(s1+s2+C2))
        ssim = float(np.mean(ssim_map))
        per_edge[name]['ssim'] = ssim

        # Only include non-void edges in averages
        if not is_void:
            all_ious.append(iou)
            all_dilated_ious.append(d_iou)
            all_ssims.append(ssim)

    # Fallback: if ALL edges are void (extreme case), use all values
    if not all_ious:
        all_ious = [per_edge[n]['iou'] for n in per_edge]
        all_dilated_ious = [per_edge[n]['dilated_iou'] for n in per_edge]
        all_ssims = [per_edge[n]['ssim'] for n in per_edge]

    return (float(np.mean(all_ious)), per_edge, float(np.mean(all_ssims)),
            float(np.mean(all_dilated_ious)))


def _generate_residual_heatmap(ref, aligned, edge_width=EDGE_WIDTH_PX):
    """
    Generate Canny edge comparison heatmap as JPEG bytes for Claude Vision.

    Shows actual edge structure overlap (the same signal used for IoU computation):
      GREEN = Canny edges present in BOTH photos (matching physical features)
      RED   = Canny edge in ONE photo only (mismatching physical features)
      DARK  = No edges detected in either (background paper)

    Only the border strip regions are shown (where physical wear lives).
    """
    import base64

    h, w = ref.shape[:2]
    ew = edge_width

    # Build edge mask for border strips only
    edge_mask = np.zeros((h, w), dtype=np.uint8)
    edge_mask[:ew, :] = 255
    edge_mask[-ew:, :] = 255
    edge_mask[:, :ew] = 255
    edge_mask[:, -ew:] = 255

    # Compute Canny edges on the full images
    ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    aligned_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    canny_ref = cv2.Canny(ref_gray, 50, 150)
    canny_aligned = cv2.Canny(aligned_gray, 50, 150)

    # Mask to border strips only
    canny_ref = cv2.bitwise_and(canny_ref, edge_mask)
    canny_aligned = cv2.bitwise_and(canny_aligned, edge_mask)

    # Build color-coded overlay:
    # GREEN channel = edges in BOTH (intersection = matching features)
    # RED channel = edges in EITHER but not BOTH (XOR = mismatching features)
    intersection = cv2.bitwise_and(canny_ref, canny_aligned)
    xor_diff = cv2.bitwise_xor(canny_ref, canny_aligned)

    # Create RGB overlay image
    overlay = np.zeros((h, w, 3), dtype=np.uint8)
    overlay[:, :, 1] = intersection  # Green = matching edges
    overlay[:, :, 2] = xor_diff      # Red = mismatching edges

    # Dilate for visibility (edges are 1px thin)
    kernel = np.ones((3, 3), np.uint8)
    overlay[:, :, 1] = cv2.dilate(overlay[:, :, 1], kernel, iterations=1)
    overlay[:, :, 2] = cv2.dilate(overlay[:, :, 2], kernel, iterations=1)

    # Composite: darkened reference + edge overlay in border strips
    ref_dark = (ref.astype(float) * 0.3).astype(np.uint8)
    # Only apply overlay in border strip regions
    mask_3ch = cv2.merge([edge_mask, edge_mask, edge_mask])
    result = np.where(mask_3ch > 0,
                      cv2.addWeighted(ref_dark, 1.0, overlay, 1.0, 0),
                      ref_dark)

    # Count pixels for annotation
    green_px = int(np.sum(intersection > 0))
    red_px = int(np.sum(xor_diff > 0))
    total_edge = green_px + red_px
    match_pct = (green_px / total_edge * 100) if total_edge > 0 else 0

    cv2.putText(result, f"Canny Edge Comparison — Border Strips Only", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    cv2.putText(result, f"GREEN=matching edges  RED=mismatching edges", (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(result, f"Match: {match_pct:.1f}% ({green_px} green / {red_px} red)", (10, 75),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    _, buf = cv2.imencode('.jpg', result, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return base64.standard_b64encode(buf).decode('utf-8')


def _create_side_by_side(img_a, img_b, max_height=400):
    """Create compact side-by-side comparison as base64 JPEG (reduced size to save tokens)."""
    import base64

    h = min(img_a.shape[0], img_b.shape[0], max_height)
    a_r = cv2.resize(img_a, (int(img_a.shape[1] * h / img_a.shape[0]), h))
    b_r = cv2.resize(img_b, (int(img_b.shape[1] * h / img_b.shape[0]), h))
    gap = np.ones((h, 8, 3), dtype=np.uint8) * 128
    combined = np.hstack([a_r, gap, b_r])

    _, buf = cv2.imencode('.jpg', combined, [cv2.IMWRITE_JPEG_QUALITY, 75])
    return base64.standard_b64encode(buf).decode('utf-8')


def _region_is_black(region, threshold=10, min_pct=0.35):
    """Check if a region has significant black areas (warp artifact from SIFT alignment).

    Returns True if more than min_pct of the region has all channels < threshold.
    Session 50: Lowered from 0.6 to 0.35 — even partial void corrupts IoU since
    the black area contributes no edges (dragging IoU to zero for that region).
    """
    if region.size == 0:
        return True
    dark_mask = np.all(region < threshold, axis=2)
    return float(np.mean(dark_mask)) > min_pct


def _compute_lpq_histogram(img_gray, win_size=LPQ_WIN_SIZE):
    """
    Compute Local Phase Quantization (LPQ) histogram for a grayscale image.

    LPQ uses Short-Term Fourier Transform (STFT) phase at 4 frequency pairs.
    For each pixel, 8 phase responses (4 freq × real+imag) are thresholded to
    produce an 8-bit code. The resulting 256-bin histogram is the texture descriptor.

    WHY LPQ WORKS FOR THIS USE CASE (Session 54):
      - STFT phase is blur-invariant — robust to camera focus differences
      - The discriminative signal comes from BORDER WEAR patterns (crunched corners,
        spine ticks, edge chips), NOT paper fiber or halftone dots
      - Interior-only LPQ showed NO separation — printed content dominates interior
      - Full-image LPQ captures border wear because wear features have distinctive
        phase signatures at the image boundaries

    Args:
        img_gray: Grayscale uint8 image
        win_size: STFT window size (default 5, from Session 54 testing)

    Returns:
        Normalized 256-bin histogram (np.float64 array)
    """
    h, w = img_gray.shape
    img_f = img_gray.astype(np.float64)

    # 4 frequency direction pairs for STFT
    freqs = [(1, 0), (0, 1), (1, 1), (1, -1)]
    responses = []

    for fx, fy in freqs:
        x_r = np.arange(-(win_size // 2), win_size // 2 + 1)
        y_r = np.arange(-(win_size // 2), win_size // 2 + 1)
        xx, yy = np.meshgrid(x_r, y_r)
        fnx, fny = fx / win_size, fy / win_size
        # Real and imaginary STFT kernels
        kr = np.cos(2 * np.pi * (fnx * xx + fny * yy))
        ki = np.sin(2 * np.pi * (fnx * xx + fny * yy))
        responses.append(cv2.filter2D(img_f, cv2.CV_64F, kr))
        responses.append(cv2.filter2D(img_f, cv2.CV_64F, ki))

    # Encode 8 responses into 8-bit code per pixel
    code = np.zeros((h, w), dtype=np.uint8)
    for i, resp in enumerate(responses):
        code += ((resp >= 0).astype(np.uint8) << i)

    # Build normalized histogram
    hist, _ = np.histogram(code.ravel(), bins=256, range=(0, 256))
    hist = hist.astype(np.float64)
    hist /= (hist.sum() + 1e-10)
    return hist


def _compute_lpq_distance(ref_img, aligned_img, win_size=LPQ_WIN_SIZE,
                           edge_width=EDGE_WIDTH_PX):
    """
    Compute LPQ chi-squared distance between reference and aligned images.

    Computes both full-image and border-only LPQ distances. The border-only
    variant may have better signal-to-noise since Session 54 showed the
    discriminative power comes from border wear, not interior content.

    Session 54 thresholds (chi2 distance):
      Full image:  SAME=0.055, DIFF=0.154-0.335, threshold 0.10/0.15
      Border-only: Not yet validated — included for testing

    Args:
        ref_img: Reference BGR image (standard size)
        aligned_img: SIFT-aligned test BGR image
        win_size: LPQ window size
        edge_width: Border strip width for border-only computation

    Returns dict:
        lpq_chi2: Full-image chi-squared distance (primary metric)
        lpq_border_chi2: Border-only chi-squared distance (experimental)
        lpq_verdict_hint: 'same_copy' | 'different_copy' | 'uncertain'
    """
    ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
    aligned_gray = cv2.cvtColor(aligned_img, cv2.COLOR_BGR2GRAY)

    # ── Full-image LPQ ──
    ref_hist = _compute_lpq_histogram(ref_gray, win_size)
    aligned_hist = _compute_lpq_histogram(aligned_gray, win_size)
    chi2_full = float(np.sum((ref_hist - aligned_hist) ** 2 /
                              (ref_hist + aligned_hist + 1e-10)))

    # ── Border-only LPQ (experimental — Session 54 insight) ──
    # Extract 4 border strips, concatenate into a single image for LPQ
    h, w = ref_gray.shape
    ew = edge_width

    # Build border strip images (concatenate all 4 strips)
    ref_borders = np.concatenate([
        ref_gray[:ew, :].ravel(),          # top
        ref_gray[-ew:, :].ravel(),         # bottom
        ref_gray[ew:-ew, :ew].ravel(),     # left (excluding corners already in top/bottom)
        ref_gray[ew:-ew, -ew:].ravel(),    # right
    ])
    aligned_borders = np.concatenate([
        aligned_gray[:ew, :].ravel(),
        aligned_gray[-ew:, :].ravel(),
        aligned_gray[ew:-ew, :ew].ravel(),
        aligned_gray[ew:-ew, -ew:].ravel(),
    ])

    # Reshape to 2D for LPQ (make it a wide strip)
    border_len = ref_borders.shape[0]
    strip_h = max(win_size + 2, 10)  # minimum height for LPQ kernels
    strip_w = border_len // strip_h
    # Trim to exact multiple
    usable = strip_h * strip_w
    ref_border_2d = ref_borders[:usable].reshape(strip_h, strip_w)
    aligned_border_2d = aligned_borders[:usable].reshape(strip_h, strip_w)

    ref_border_hist = _compute_lpq_histogram(ref_border_2d, win_size)
    aligned_border_hist = _compute_lpq_histogram(aligned_border_2d, win_size)
    chi2_border = float(np.sum((ref_border_hist - aligned_border_hist) ** 2 /
                                (ref_border_hist + aligned_border_hist + 1e-10)))

    # Verdict hint based on full-image chi2 (the validated metric)
    if chi2_full < LPQ_SAME_COPY:
        verdict_hint = 'same_copy'
    elif chi2_full > LPQ_DIFF_COPY:
        verdict_hint = 'different_copy'
    else:
        verdict_hint = 'uncertain'

    return {
        'lpq_chi2': round(chi2_full, 6),
        'lpq_border_chi2': round(chi2_border, 6),
        'lpq_verdict_hint': verdict_hint,
    }


def _create_canny_overlay(ref, aligned, edge_width=EDGE_WIDTH_PX):
    """
    Create a Canny edge comparison overlay focused on border strips.

    Shows both images' Canny edges overlaid on the reference, with:
      GREEN = edges present in BOTH images (matching physical structure)
      RED = edges in REF only (structure missing from TEST)
      BLUE = edges in TEST only (structure missing from REF)

    This helps Vision distinguish physical defects (which produce edges)
    from smooth printed areas (which don't). Same-copy pairs should show
    mostly green edges in the border strips.

    ⚠️ DO NOT USE FOR CROSS-CAMERA / MARKETPLACE COMPARISONS (Session 53):
    When photos come from different cameras/lighting/backgrounds, the Canny overlay
    is actively MISLEADING. Printed content edges match across ALL copies (same issue),
    creating false green signal. Vision was fooled into calling different copies
    "same_copy" because overlay showed "predominantly green matching along the spine."
    The green was from PRINTED artwork edges, not physical defect edges.
    In marketplace_mode, this function is skipped entirely — do not re-enable it
    without solving the printed-content-edge-dominance problem.
    """
    import base64

    h, w = ref.shape[:2]
    ew = edge_width

    ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    aligned_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)

    # Detect warp black regions in aligned image
    black_mask = np.all(aligned < 10, axis=2).astype(np.uint8) * 255

    # Canny edges
    canny_ref = cv2.Canny(ref_gray, 50, 150)
    canny_aligned = cv2.Canny(aligned_gray, 50, 150)

    # Mask out black warp regions from aligned edges
    canny_aligned = cv2.bitwise_and(canny_aligned, cv2.bitwise_not(black_mask))

    # Border strip mask
    edge_mask = np.zeros((h, w), dtype=np.uint8)
    edge_mask[:ew, :] = 255
    edge_mask[-ew:, :] = 255
    edge_mask[:, :ew] = 255
    edge_mask[:, -ew:] = 255

    canny_ref = cv2.bitwise_and(canny_ref, edge_mask)
    canny_aligned = cv2.bitwise_and(canny_aligned, edge_mask)

    # Color overlay
    both = cv2.bitwise_and(canny_ref, canny_aligned)       # matching edges
    ref_only = cv2.bitwise_and(canny_ref, cv2.bitwise_not(canny_aligned))
    test_only = cv2.bitwise_and(canny_aligned, cv2.bitwise_not(canny_ref))

    # Dilate for visibility
    kernel = np.ones((2, 2), np.uint8)
    both = cv2.dilate(both, kernel)
    ref_only = cv2.dilate(ref_only, kernel)
    test_only = cv2.dilate(test_only, kernel)

    # Build overlay on darkened reference
    overlay = (ref.astype(float) * 0.25).astype(np.uint8)
    overlay[both > 0] = [0, 255, 0]          # Green = matching
    overlay[ref_only > 0] = [0, 0, 255]      # Red = REF only
    overlay[test_only > 0] = [255, 100, 0]   # Blue = TEST only

    # Mark black warp regions
    black_3ch = cv2.merge([black_mask, black_mask, black_mask])
    overlay = np.where(black_3ch > 0, np.array([40, 40, 40], dtype=np.uint8), overlay)

    # Legend
    cv2.putText(overlay, "Canny Edge Overlay — Border Strips", (10, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(overlay, "GREEN=both  RED=REF only  BLUE=TEST only  DARK=warp void", (10, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)

    # Count matching
    green_px = int(np.sum(both > 0))
    total_px = green_px + int(np.sum(ref_only > 0)) + int(np.sum(test_only > 0))
    match_pct = (green_px / total_px * 100) if total_px > 0 else 0
    cv2.putText(overlay, f"Edge match: {match_pct:.0f}%", (10, 62),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    _, buf = cv2.imencode('.jpg', overlay, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return base64.standard_b64encode(buf).decode('utf-8'), match_pct


def _create_corner_crop_comparisons(ref, aligned, corner_size=120, zoom=4):
    """
    Create zoomed corner crop comparisons for all 4 corners.

    Corners are the highest-signal regions for fingerprinting — they accumulate
    the most distinctive wear (bends, dings, rounding, creases). By isolating
    them at high zoom, we give Claude Vision the best possible detail for
    matching specific localized defects.

    Returns a list of (name, base64_jpeg) tuples.
    """
    import base64

    h, w = ref.shape[:2]
    cs = corner_size

    corners = {
        'top-left':     (ref[:cs, :cs],           aligned[:cs, :cs]),
        'top-right':    (ref[:cs, w-cs:],          aligned[:cs, w-cs:]),
        'bottom-left':  (ref[h-cs:, :cs],          aligned[h-cs:, :cs]),
        'bottom-right': (ref[h-cs:, w-cs:],        aligned[h-cs:, w-cs:]),
    }

    results = []
    skipped = []
    for name, (r_corner, a_corner) in corners.items():
        # Skip corners where the aligned image is mostly black (warp artifact)
        if _region_is_black(a_corner):
            skipped.append(name)
            continue

        # Scale up for visibility
        r_big = cv2.resize(r_corner, (r_corner.shape[1] * zoom, r_corner.shape[0] * zoom),
                           interpolation=cv2.INTER_LINEAR)
        a_big = cv2.resize(a_corner, (a_corner.shape[1] * zoom, a_corner.shape[0] * zoom),
                           interpolation=cv2.INTER_LINEAR)

        # Add labels
        label_h = 30
        r_labeled = np.zeros((r_big.shape[0] + label_h, r_big.shape[1], 3), dtype=np.uint8)
        r_labeled[label_h:] = r_big
        cv2.putText(r_labeled, f"REF — {name} corner", (5, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        a_labeled = np.zeros((a_big.shape[0] + label_h, a_big.shape[1], 3), dtype=np.uint8)
        a_labeled[label_h:] = a_big
        cv2.putText(a_labeled, f"TEST — {name} corner", (5, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Stack vertically (ref on top, test on bottom)
        gap = np.ones((4, r_labeled.shape[1], 3), dtype=np.uint8) * 128
        combined = np.vstack([r_labeled, gap, a_labeled])

        _, buf = cv2.imencode('.jpg', combined, [cv2.IMWRITE_JPEG_QUALITY, 92])
        results.append((name, base64.standard_b64encode(buf).decode('utf-8')))

    return results, skipped


def _create_edge_crop_comparisons(ref, aligned, edge_width=EDGE_WIDTH_PX, zoom=4):
    """
    Create zoomed side-by-side comparisons of each border strip.

    For each edge (top/bottom/left/right), crops the border strip from both
    the reference and aligned images, scales up for visibility, and places
    them vertically for comparison. Returns a list of (name, base64_jpeg) tuples.

    Session 50: Increased zoom from 3x to 4x. Now takes full strip width
    (no center-crop truncation) so corners are preserved in context.
    """
    import base64

    h, w = ref.shape[:2]
    ew = edge_width

    strips = {
        'top':    (ref[:ew, :],    aligned[:ew, :]),
        'bottom': (ref[-ew:, :],   aligned[-ew:, :]),
        'left':   (ref[:, :ew],    aligned[:, :ew]),
        'right':  (ref[:, -ew:],   aligned[:, -ew:]),
    }

    results = []
    skipped = []
    for name, (r_strip, a_strip) in strips.items():
        # Skip edges where the aligned image is mostly black (warp artifact)
        if _region_is_black(a_strip):
            skipped.append(name)
            continue

        # Scale up for visibility
        r_big = cv2.resize(r_strip, (r_strip.shape[1] * zoom, r_strip.shape[0] * zoom),
                           interpolation=cv2.INTER_LINEAR)
        a_big = cv2.resize(a_strip, (a_strip.shape[1] * zoom, a_strip.shape[0] * zoom),
                           interpolation=cv2.INTER_LINEAR)

        # Cap dimensions to stay within API limits (8000px max per dimension)
        # After stacking ref + test vertically with labels+gap, total height ≈ 2*h + 64
        # So each strip's height must be < 3950px. Width capped at 3200px.
        max_w = 3200
        max_h = 3900
        if r_big.shape[1] > max_w:
            cx = r_big.shape[1] // 2
            hw = max_w // 2
            r_big = r_big[:, cx - hw:cx + hw]
            a_big = a_big[:, cx - hw:cx + hw]
        if r_big.shape[0] > max_h:
            # For left/right strips (tall): take center section
            cy = r_big.shape[0] // 2
            hh = max_h // 2
            r_big = r_big[cy - hh:cy + hh, :]
            a_big = a_big[cy - hh:cy + hh, :]

        # Add labels
        label_h = 30
        r_labeled = np.zeros((r_big.shape[0] + label_h, r_big.shape[1], 3), dtype=np.uint8)
        r_labeled[label_h:] = r_big
        cv2.putText(r_labeled, f"REF — {name} edge", (5, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        a_labeled = np.zeros((a_big.shape[0] + label_h, a_big.shape[1], 3), dtype=np.uint8)
        a_labeled[label_h:] = a_big
        cv2.putText(a_labeled, f"TEST — {name} edge", (5, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Stack vertically (ref on top, test on bottom)
        gap = np.ones((4, r_labeled.shape[1], 3), dtype=np.uint8) * 128
        combined = np.vstack([r_labeled, gap, a_labeled])

        _, buf = cv2.imencode('.jpg', combined, [cv2.IMWRITE_JPEG_QUALITY, 90])
        results.append((name, base64.standard_b64encode(buf).decode('utf-8')))

    return results, skipped


def compare_covers(ref_url, test_url, extra_ref_photos=None, timeout=15):
    """
    Compare two comic cover photos using SIFT alignment + edge IoU.

    This is the fast, quantitative comparison (~3-8 seconds).
    No external API calls needed.

    Args:
        ref_url: URL of registered (reference) cover photo
        test_url: URL of test/query cover photo
        extra_ref_photos: Optional list of extra photo dicts from registration
            [{'type': 'alternate_front', 'url': '...', 'label': '...'}]
            If main alignment fails, alternate_front photos are tried as fallback.
        timeout: Download timeout in seconds

    Returns dict:
        success: bool
        verdict: 'same_copy' | 'different_copy' | 'uncertain' | 'error'
        confidence: 0.0-1.0
        avg_edge_iou: float (primary metric)
        avg_edge_ssim: float
        per_edge: dict with per-edge metrics
        alignment: dict with SIFT quality metrics
        error: str (if success=False)
    """
    if not CV2_AVAILABLE:
        return {
            'success': False,
            'verdict': 'error',
            'error': 'opencv_not_available',
        }

    try:
        # Download and resize
        ref_img = _resize_standard(_download_image(ref_url, timeout))
        test_img = _resize_standard(_download_image(test_url, timeout))

        # SIFT align (multi-run for stable border inlier count)
        aligned, align_stats = _sift_align_with_stable_border(ref_img, test_img)

        # If alignment fails, try alternate front photos as fallback
        used_alternate = False
        if not align_stats.get('aligned') and extra_ref_photos:
            alt_fronts = [p for p in extra_ref_photos
                          if p.get('type') in ('alternate_front',) and p.get('url')]
            for alt in alt_fronts:
                try:
                    alt_img = _resize_standard(_download_image(alt['url'], timeout))
                    alt_aligned, alt_stats = _sift_align_with_stable_border(alt_img, test_img)
                    if alt_stats.get('aligned'):
                        # Use this alternate reference instead
                        ref_img = alt_img
                        aligned = alt_aligned
                        align_stats = alt_stats
                        align_stats['used_alternate'] = alt.get('label', alt['url'])
                        used_alternate = True
                        break
                except Exception:
                    continue

        if not align_stats.get('aligned'):
            return {
                'success': True,
                'verdict': 'uncertain',
                'confidence': 0.3,
                'avg_edge_iou': None,
                'avg_edge_ssim': None,
                'per_edge': None,
                'alignment': align_stats,
                'alternates_tried': len([p for p in (extra_ref_photos or [])
                                         if p.get('type') == 'alternate_front']),
                'note': 'Alignment failed — photo quality may be insufficient',
            }

        # Compute edge IoU (strict and dilated)
        avg_iou, per_edge, avg_ssim, avg_dilated_iou = _compute_edge_iou(ref_img, aligned)

        # Compute LPQ distance (Session 54 — blur-invariant texture metric)
        lpq_result = _compute_lpq_distance(ref_img, aligned)
        lpq_chi2 = lpq_result['lpq_chi2']

        # Determine verdict using dilated IoU, strict IoU, border inliers, AND LPQ.
        # Session 50: border_inliers is the strongest same-copy signal —
        # physical defects in border regions create unique SIFT features that
        # only match between photos of the same physical copy.
        # Session 54: LPQ chi2 is supplementary — used to boost/reduce confidence
        # and break ties. Not yet primary due to tiny validation set.
        border_inliers = align_stats.get('border_inliers', 0)

        if avg_dilated_iou >= DILATED_IOU_SAME_COPY:
            # High dilated IoU — strong SAME signal from edge structure
            # Session 54: LPQ can validate or challenge this
            if lpq_chi2 < LPQ_SAME_COPY:
                verdict = 'same_copy'
                confidence = min(0.97, 0.75 + (avg_dilated_iou - DILATED_IOU_SAME_COPY) * 5)
            elif lpq_chi2 > LPQ_DIFF_COPY:
                # LPQ disagrees — dilated IoU may be inflated by cross-camera noise
                # Downgrade to uncertain, let Vision resolve
                verdict = 'uncertain'
                confidence = 0.55
            else:
                verdict = 'same_copy'
                confidence = min(0.90, 0.7 + (avg_dilated_iou - DILATED_IOU_SAME_COPY) * 5)
        elif border_inliers >= BORDER_INLIER_SAME_COPY:
            # Session 54: Border inliers can be FALSE POSITIVES from background
            # texture (blanket fibers, table edges). LPQ is more reliable because
            # it's blur-invariant and captures actual border wear patterns.
            # When LPQ strongly disagrees (chi2 > LPQ_DIFF_COPY), downgrade to
            # uncertain rather than trusting potentially spurious border inliers.
            if lpq_chi2 > LPQ_DIFF_COPY:
                # LPQ says DIFFERENT but border inliers say SAME — conflicting
                # This pattern matches known false-positive scenarios:
                # 010 vs 012 (border_inliers=3, lpq=0.209) and
                # 010 vs eBay (border_inliers=2, lpq=0.327)
                verdict = 'uncertain'
                confidence = 0.50
            elif lpq_chi2 < LPQ_SAME_COPY:
                # Both LPQ and border inliers agree → strong SAME signal
                verdict = 'same_copy'
                confidence = min(0.95, 0.75 + border_inliers * 0.05)
            else:
                # LPQ in uncertain range, border inliers say same
                verdict = 'same_copy'
                confidence = min(0.85, 0.65 + border_inliers * 0.05)
        elif border_inliers == 0 and avg_dilated_iou < DILATED_IOU_SAME_COPY:
            verdict = 'different_copy'
            confidence = min(0.90, 0.65 + (DILATED_IOU_SAME_COPY - avg_dilated_iou) * 3)
            # LPQ can boost or reduce confidence for DIFF verdict
            if lpq_chi2 > LPQ_DIFF_COPY:
                confidence = min(0.95, confidence + 0.05)  # LPQ agrees → boost
            elif lpq_chi2 < LPQ_SAME_COPY:
                # LPQ says same but IoU+border say diff — conflicting, lower confidence
                confidence = max(0.50, confidence - 0.15)
        elif avg_iou <= EDGE_IOU_DIFF_COPY:
            # Low IoU but some border inliers — conflicting signals
            # Session 54: LPQ can break the tie
            if lpq_chi2 < LPQ_SAME_COPY:
                verdict = 'same_copy'
                confidence = 0.65  # LPQ-driven, moderate confidence
            elif lpq_chi2 > LPQ_DIFF_COPY:
                verdict = 'different_copy'
                confidence = 0.65
            else:
                verdict = 'uncertain'
                confidence = 0.5
        else:
            # General uncertain case — LPQ can break the tie
            if lpq_chi2 < LPQ_SAME_COPY:
                verdict = 'same_copy'
                confidence = 0.60
            elif lpq_chi2 > LPQ_DIFF_COPY:
                verdict = 'different_copy'
                confidence = 0.60
            else:
                verdict = 'uncertain'
                confidence = 0.5

        result = {
            'success': True,
            'verdict': verdict,
            'confidence': round(confidence, 3),
            'avg_edge_iou': round(avg_iou, 5),
            'avg_dilated_iou': round(avg_dilated_iou, 5),
            'avg_edge_ssim': round(avg_ssim, 4),
            'per_edge': {k: {kk: round(vv, 5) for kk, vv in v.items()}
                        for k, v in per_edge.items()},
            'alignment': align_stats,
            'lpq_chi2': lpq_result['lpq_chi2'],
            'lpq_border_chi2': lpq_result['lpq_border_chi2'],
            'lpq_verdict_hint': lpq_result['lpq_verdict_hint'],
        }
        if used_alternate:
            result['used_alternate_ref'] = True
        return result

    except Exception as e:
        return {
            'success': False,
            'verdict': 'error',
            'error': str(e),
        }


def compare_covers_with_vision(ref_url, test_url,
                                extra_ref_photos=None,
                                anthropic_api_key=None,
                                model="claude-sonnet-4-20250514",
                                timeout=15,
                                marketplace_mode=False):
    """
    Full hybrid comparison: SIFT + edge IoU + Claude Vision interpretation.

    This is the comprehensive comparison (~10-15 seconds, ~$0.015/call).
    Uses Claude Vision to interpret residual heatmaps for cases where
    quantitative metrics alone are uncertain.

    Args:
        ref_url: URL of registered cover photo
        test_url: URL of test/query cover photo
        extra_ref_photos: Optional list of extra photo dicts from registration.
            Alternate fronts used as SIFT fallback. Defect/closeup photos sent
            to Claude Vision as additional evidence.
        anthropic_api_key: Anthropic API key (or from ANTHROPIC_API_KEY env var)
        model: Claude model to use
        timeout: Download timeout
        marketplace_mode: If True, Vision is the PRIMARY verdict. Cross-camera
            marketplace photos (different lighting, backgrounds, angles) fool
            the quantitative pipeline with spurious border inliers and false
            edge matches. Vision handles this correctly by comparing physical
            defects. Session 53: quant is still computed for diagnostics but
            Vision verdict takes priority in marketplace mode.

    Returns dict with all fields from compare_covers() plus:
        vision_verdict: Claude's verdict
        vision_confidence: Claude's confidence
        vision_reasoning: Human-readable explanation
        vision_observations: List of visual observations
        final_verdict: Combined verdict (quant + vision)
        final_confidence: Combined confidence
        cost_usd: Estimated API cost
    """
    if not CV2_AVAILABLE:
        return {
            'success': False,
            'verdict': 'error',
            'error': 'opencv_not_available',
        }

    api_key = anthropic_api_key or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key or not ANTHROPIC_AVAILABLE:
        # Fall back to quantitative-only
        result = compare_covers(ref_url, test_url, extra_ref_photos, timeout)
        result['vision_available'] = False
        result['final_verdict'] = result.get('verdict')
        result['final_confidence'] = result.get('confidence')
        if marketplace_mode:
            # Session 53: Warn that marketplace verdict is unreliable without Vision
            result['marketplace_warning'] = (
                'Vision API unavailable — marketplace verdict uses quantitative metrics only, '
                'which are unreliable for cross-camera comparisons. Results may contain false positives.')
            result['final_confidence'] = min(result.get('final_confidence', 0.5), 0.5)
        return result

    try:
        import json as json_mod
        import base64

        # Download and resize
        ref_img = _resize_standard(_download_image(ref_url, timeout))
        test_img = _resize_standard(_download_image(test_url, timeout))

        # SIFT align (multi-run for stable border inlier count, with alternate fallback)
        aligned, align_stats = _sift_align_with_stable_border(ref_img, test_img)

        if not align_stats.get('aligned') and extra_ref_photos:
            alt_fronts = [p for p in extra_ref_photos
                          if p.get('type') in ('alternate_front',) and p.get('url')]
            for alt in alt_fronts:
                try:
                    alt_img = _resize_standard(_download_image(alt['url'], timeout))
                    alt_aligned, alt_stats = _sift_align_with_stable_border(alt_img, test_img)
                    if alt_stats.get('aligned'):
                        ref_img = alt_img
                        aligned = alt_aligned
                        align_stats = alt_stats
                        align_stats['used_alternate'] = alt.get('label', alt['url'])
                        break
                except Exception:
                    continue

        if not align_stats.get('aligned'):
            return {
                'success': True,
                'verdict': 'uncertain',
                'final_verdict': 'uncertain',
                'confidence': 0.3,
                'final_confidence': 0.3,
                'alignment': align_stats,
                'note': 'Alignment failed',
            }

        # Compute edge IoU (strict and dilated)
        avg_iou, per_edge, avg_ssim, avg_dilated_iou = _compute_edge_iou(ref_img, aligned)

        # Compute LPQ distance (Session 54)
        lpq_result = _compute_lpq_distance(ref_img, aligned)
        lpq_chi2 = lpq_result['lpq_chi2']

        # Quantitative verdict (dilated IoU + strict IoU + border inlier count + LPQ)
        border_inliers = align_stats.get('border_inliers', 0)

        if avg_dilated_iou >= DILATED_IOU_SAME_COPY:
            quant_verdict = 'same_copy'
        elif border_inliers >= BORDER_INLIER_SAME_COPY:
            quant_verdict = 'same_copy'
        elif border_inliers == 0 and avg_dilated_iou < DILATED_IOU_SAME_COPY:
            quant_verdict = 'different_copy'
        elif avg_iou <= EDGE_IOU_DIFF_COPY:
            # Session 54: LPQ can break the tie in conflicting signal cases
            if lpq_chi2 < LPQ_SAME_COPY:
                quant_verdict = 'same_copy'
            elif lpq_chi2 > LPQ_DIFF_COPY:
                quant_verdict = 'different_copy'
            else:
                quant_verdict = 'uncertain'
        else:
            if lpq_chi2 < LPQ_SAME_COPY:
                quant_verdict = 'same_copy'
            elif lpq_chi2 > LPQ_DIFF_COPY:
                quant_verdict = 'different_copy'
            else:
                quant_verdict = 'uncertain'

        # Generate visual aids for Claude: corner crops + edge crops + Canny overlay + overview
        # Session 53: Skip Canny overlay in marketplace mode — cross-camera lighting/background
        # differences create false green (matching) edges from printed content, misleading Vision
        # into calling different copies "same_copy". Corner/edge crops are the reliable evidence.
        corner_crops, skipped_corners = _create_corner_crop_comparisons(ref_img, aligned)
        edge_crops, skipped_edges = _create_edge_crop_comparisons(ref_img, aligned)
        if not marketplace_mode:
            canny_b64, canny_match_pct = _create_canny_overlay(ref_img, aligned)
        else:
            canny_b64, canny_match_pct = None, 0.0
        sbs_b64 = _create_side_by_side(ref_img, test_img)

        # Build Claude Vision prompt — NO METRICS to prevent anchoring bias
        # Vision makes its own independent judgment; we combine verdicts programmatically
        align_quality_note = ""
        if align_stats.get('inliers', 0) < 100:
            align_quality_note = (
                "\nNOTE: The geometric alignment between these two photos is LOW quality. "
                "Small positional shifts may exist — account for this when comparing features.")

        # Note about skipped regions (black warp artifacts)
        skipped_note = ""
        all_skipped = skipped_corners + skipped_edges
        if all_skipped:
            skipped_note = (
                f"\nNOTE: Some regions were skipped because the geometric alignment caused "
                f"black void areas (the test photo didn't fully cover the reference frame). "
                f"Skipped: {', '.join(all_skipped)}. Focus your analysis on the provided regions only.")

        # Session 53: Marketplace-specific warning about cross-camera conditions
        marketplace_note = ""
        if marketplace_mode:
            marketplace_note = """
CRITICAL — CROSS-CAMERA MARKETPLACE COMPARISON:
These two photos were taken with DIFFERENT cameras, lighting, and backgrounds (e.g., one on
a blanket, one on white background for an eBay listing). This means:
  - Overall edge structure, lighting gradients, and color tones WILL differ between REF and
    TEST — this is NOT evidence of different copies, just different photography conditions.
  - Background textures (blanket fibers, table surface, mylar bag reflections) may appear in
    border regions — IGNORE these completely. They are not comic book features.
  - Spine stress marks, paper texture patterns, and edge wear may LOOK different due to
    lighting angle — a crease that catches light in one photo may be invisible in another.
  - You MUST find SPECIFIC, LOCATABLE physical defects (a chip at a precise position, a
    crease crossing specific artwork, a tear with a specific shape) that match in BOTH photos
    to call SAME_COPY. General texture similarity or "consistent wear patterns" is NOT enough
    because two copies in the same grade will show similar general wear.
  - Your DEFAULT verdict should be DIFFERENT_COPY. Only override to SAME_COPY if you find
    a specific physical defect that is uniquely identifiable in both images by its exact
    position and shape relative to the printed artwork."""

        prompt = f"""You are comparing two photographs of the SAME comic book ISSUE to determine
whether they show the SAME physical copy or two DIFFERENT physical copies.
{marketplace_note}
CRITICAL CONTEXT — READ CAREFULLY:
Both images have been geometrically aligned using the printed artwork as anchor points.
After alignment, ALL PRINTED CONTENT (artwork, text, colors, line art) is pixel-aligned
between REF and TEST. This means:
  - The printed artwork WILL look identical in both images — this is EXPECTED and proves
    NOTHING about whether they are the same physical copy.
  - Matching ink patterns, color gradients, printed lines, or artwork features are NOT
    evidence of same copy — they are just the same print run.
  - ONLY physical defects that BREAK or DEVIATE from the printed pattern matter:
    creases that cross printed lines, paper tears, corner bends, chips missing from
    the edge, foxing/browning spots, spine tick indentations, staple rust stains,
    scratches in the cover coating.
{align_quality_note}{skipped_note}
IMAGES PROVIDED (examine in this order):
1. CORNER CROPS at 4x zoom — only non-void corners are included.
   Corners accumulate the most distinctive wear. These are your primary evidence.
2. EDGE STRIP crops at 4x zoom — only non-void edges are included.
   Full border strips showing spine ticks, edge chips, color breaks.
{"3. CANNY EDGE OVERLAY — a diagnostic image showing detected edge structure in border strips only. GREEN = edges present in BOTH photos (matching physical structure), RED = edges in REF only, BLUE = edges in TEST only. High green percentage suggests the physical edge structure matches. Use this to SEE where physical features are." if not marketplace_mode else ""}
{"4" if not marketplace_mode else "3"}. Overview side-by-side (small, for general orientation only).

WHAT TO IGNORE (these are NOT evidence):
  ❌ "Similar blue-gray tones" — that's the printed ink, not a physical feature
  ❌ "Matching vertical lines in the artwork" — same print plate made both copies
  ❌ "Similar color distribution" — same artwork
  ❌ "Clean corner with same edge profile" — absence of defects proves nothing
  ❌ "General condition similarity" — two copies in the same grade look similar

WHAT COUNTS AS EVIDENCE (physical defects only):
  ✅ A specific crease that crosses printed artwork at a unique angle and position
  ✅ A chip or tear in the paper at a precise location along an edge
  ✅ A spine tick mark at a specific measured position (e.g., "3cm from top")
  ✅ A foxing/browning spot at a precise location
  ✅ Corner rounding or bend with a specific shape and severity
  ✅ A scratch or scuff in the cover coating at a specific position

STRUCTURED ANALYSIS — Complete each section:

STEP 1 — CORNER ANALYSIS (most important):
For EACH of the 4 corners:
  a) Identify physical DEFECTS (not printed content) in REF. If no defects visible, say so.
  b) Identify physical DEFECTS in TEST at the same corner.
  c) Do any defects match in EXACT position? Or are there defects in one that are
     ABSENT from the other?

STEP 2 — SPINE & EDGE ANALYSIS:
  a) Identify spine tick marks, stress indentations, or staple rust in REF — by position.
  b) Check if the SAME marks appear at the SAME position in TEST.
  c) Any marks in one image ABSENT from the other?

STEP 3 — TOP & BOTTOM EDGE ANALYSIS:
  a) Any chips, tears, foxing spots along top/bottom edges in REF?
  b) Same in TEST? Matching positions or different?

{"STEP 4 — CANNY EDGE OVERLAY CHECK:" + chr(10) + "  Examine the Canny edge overlay image. This shows detected edge structure in the" + chr(10) + "  border strips. Spine stress marks, creases, and paper texture create edge patterns." + chr(10) + "  a) Is the overlay mostly GREEN in areas where both photos have content? Green means" + chr(10) + "     the physical edge structure matches between both photos." + chr(10) + "  b) Are there large RED or BLUE regions indicating edge structure that exists in only" + chr(10) + "     one photo? That suggests different physical features." + chr(10) + "  c) Use this as SUPPORTING evidence — it helps you see subtle physical texture that" + chr(10) + "     may not be obvious in the color photos." if not marketplace_mode else ""}

DECISION RULES:
- SAME_COPY: You found specific physical defects (not printed features) that match in
  precise position between REF and TEST.{" Physical texture patterns (spine stress marks, paper creases, surface wear) matching across multiple regions also count — these are physical features of the paper, not the print. The Canny overlay helps confirm this: high green overlap in border strips supports same-copy." if not marketplace_mode else " In a cross-camera marketplace comparison, ONLY call SAME_COPY if you found a SPECIFIC, UNIQUELY IDENTIFIABLE defect (not general wear) visible in both photos at the same position relative to the printed artwork."}
- DIFFERENT_COPY: DEFAULT VERDICT when you cannot find matching physical defects OR
  when specific defects appear in different positions between REF and TEST. Two copies
  of the same issue are EXPECTED to look nearly identical in printed content. If you
  see no distinguishing physical defects, or defects are in different positions, the
  copies are different. When in doubt, lean toward DIFFERENT_COPY.
- UNCERTAIN: ONLY if images are too blurry/dark/low-res to see physical details at all.

Respond in JSON:
{{
  "corners": {{
    "top_left": "physical defects found and comparison result",
    "top_right": "physical defects found and comparison result",
    "bottom_left": "physical defects found and comparison result",
    "bottom_right": "physical defects found and comparison result"
  }},
  "spine": "spine tick/stress mark findings and comparison",
  "edges": "top/bottom/right edge defect findings and comparison",
  {"" if marketplace_mode else '"canny_overlay": "what the edge overlay shows — mostly green (matching) or mixed?",'}
  "verdict": "SAME_COPY" or "DIFFERENT_COPY" or "UNCERTAIN",
  "confidence": 0.0-1.0,
  "reasoning": "2-3 sentences citing the specific PHYSICAL DEFECTS (not artwork) that drove your verdict"
}}"""

        # ── Build message content: corners first (primary evidence), then edges, then overview ──
        msg_content = []

        # 1. Corner crops — highest signal, shown first for primacy
        msg_content.append({"type": "text", "text": "CORNER CROPS (4x zoom, REF on top, TEST on bottom):"})
        for corner_name, crop_b64 in corner_crops:
            msg_content.append({"type": "text", "text": f"{corner_name} corner:"})
            msg_content.append({"type": "image", "source": {
                "type": "base64", "media_type": "image/jpeg", "data": crop_b64}})

        # 2. Edge strip crops — secondary evidence
        msg_content.append({"type": "text", "text": "EDGE STRIP CROPS (4x zoom, REF on top, TEST on bottom):"})
        for edge_name, crop_b64 in edge_crops:
            msg_content.append({"type": "text", "text": f"{edge_name} edge:"})
            msg_content.append({"type": "image", "source": {
                "type": "base64", "media_type": "image/jpeg", "data": crop_b64}})

        # 3. Canny edge overlay — diagnostic image showing physical edge structure
        # Session 53: Skip in marketplace mode — cross-camera noise makes overlay misleading
        if not marketplace_mode and canny_b64:
            msg_content.append({"type": "text", "text": f"CANNY EDGE OVERLAY (border strips only — GREEN=both, RED=REF only, BLUE=TEST only, edge match {canny_match_pct:.0f}%):"})
            msg_content.append({"type": "image", "source": {
                "type": "base64", "media_type": "image/jpeg", "data": canny_b64}})

        # 4. Compact overview (orientation only)
        msg_content.append({"type": "text", "text": "Overview (for general orientation):"})
        msg_content.append({"type": "image", "source": {
            "type": "base64", "media_type": "image/jpeg", "data": sbs_b64}})

        # 5. Add defect/closeup reference photos if available (up to 4 to stay under token limits)
        extra_detail_types = ('defect', 'closeup_front', 'closeup_back', 'closeup_spine',
                              'edge_top', 'edge_bottom', 'edge_left', 'edge_right')
        extra_detail_photos = [p for p in (extra_ref_photos or [])
                               if p.get('type') in extra_detail_types and p.get('url')][:4]

        if extra_detail_photos:
            labels = []
            for ep in extra_detail_photos:
                try:
                    ep_img = _download_image(ep['url'], timeout=10)
                    # Resize to max 600px on longest side to save tokens
                    h, w = ep_img.shape[:2]
                    scale = min(600 / max(h, w), 1.0)
                    if scale < 1.0:
                        ep_img = cv2.resize(ep_img, (int(w * scale), int(h * scale)))
                    _, buf = cv2.imencode('.jpg', ep_img, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    ep_b64 = base64.standard_b64encode(buf).decode('utf-8')

                    desc = ep.get('label') or ep.get('type', 'detail')
                    labels.append(desc)
                    msg_content.append({"type": "text", "text": f"Owner's reference detail — {desc}:"})
                    msg_content.append({"type": "image", "source": {
                        "type": "base64", "media_type": "image/jpeg", "data": ep_b64}})
                except Exception:
                    continue

            if labels:
                prompt += (f"\n\nThe owner also provided {len(labels)} reference close-up(s): "
                          f"{', '.join(labels)}. "
                          "Cross-reference these with the corner/edge crops. "
                          "Specific defects visible in these close-ups should appear in the "
                          "corresponding corner or edge crop of the TEST image if it's the same copy.")

        # 5. The prompt goes last, after all images
        msg_content.append({"type": "text", "text": prompt})

        # Call Claude Vision
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1500,
            system="You are a forensic comic book authentication specialist. Your expertise is identifying individual physical copies through PHYSICAL WEAR PATTERNS — creases, tears, chips, spine ticks, foxing spots, corner bends. You IGNORE printed artwork similarities because all copies of the same issue share identical printed content. After SIFT alignment, the print is pixel-matched — only physical defects differ between copies. Your default assumption is DIFFERENT_COPY unless you find compelling matching physical defects. You are methodical: you examine each region, cite specific physical features by position, and commit to a verdict.",
            messages=[{"role": "user", "content": msg_content}],
        )

        raw = response.content[0].text
        cost = (response.usage.input_tokens * 3 / 1e6) + (response.usage.output_tokens * 15 / 1e6)

        # Parse Claude response
        try:
            text = raw.strip()
            if text.startswith('```'):
                text = text.split('\n', 1)[1].rsplit('```', 1)[0]
            parsed = json_mod.loads(text)
        except (json_mod.JSONDecodeError, ValueError, KeyError) as parse_err:
            import re
            m = re.search(r'\{[\s\S]*\}', raw)
            parsed = json_mod.loads(m.group()) if m else {
                'verdict': 'UNCERTAIN', 'confidence': 0.5,
                'reasoning': f'JSON parse error: {str(parse_err)[:100]}', 'observations': []}

        vision_verdict = parsed.get('verdict', 'UNCERTAIN').lower()
        # Normalize to our format
        if vision_verdict in ('same_copy', 'same'):
            vision_verdict = 'same_copy'
        elif vision_verdict in ('different_copy', 'different'):
            vision_verdict = 'different_copy'
        else:
            vision_verdict = 'uncertain'

        vision_confidence = float(parsed.get('confidence', 0.5))

        # Extract structured corner/edge findings (Session 50 prompt format)
        vision_corners = parsed.get('corners', {})
        vision_spine = parsed.get('spine', '')
        vision_edges = parsed.get('edges', '')

        # Build observations list from structured findings for backward compat
        observations = parsed.get('observations', [])
        if not observations and vision_corners:
            observations = [f"{k}: {v}" for k, v in vision_corners.items() if v]
            if vision_spine:
                observations.append(f"spine: {vision_spine}")
            if vision_edges:
                observations.append(f"edges: {vision_edges}")

        # Combined verdict logic
        # Session 53: marketplace_mode flips priority — Vision is primary because
        # cross-camera photos (different lighting, background, angle) generate
        # spurious border inliers and false edge matches that fool quant metrics.
        # Standard mode: quant has priority, Vision resolves uncertainty.
        if marketplace_mode:
            # ── MARKETPLACE MODE: Vision is PRIMARY ──
            # Quant metrics (IoU, border inliers) are unreliable cross-camera
            # (Session 51 finding). Trust Vision's physical defect analysis.
            # Session 54: LPQ IS reliable cross-camera (blur-invariant, tested).
            # Use LPQ as supplementary signal to boost/reduce Vision confidence,
            # and as tiebreaker when Vision is uncertain.
            if vision_verdict != 'uncertain':
                final_verdict = vision_verdict
                # Boost confidence if LPQ agrees with Vision
                if (vision_verdict == 'same_copy' and lpq_chi2 < LPQ_SAME_COPY) or \
                   (vision_verdict == 'different_copy' and lpq_chi2 > LPQ_DIFF_COPY):
                    final_confidence = max(vision_confidence, 0.92)
                elif quant_verdict == vision_verdict:
                    final_confidence = max(vision_confidence, 0.90)
                else:
                    final_confidence = vision_confidence
            else:
                # Vision uncertain — LPQ is best tiebreaker for marketplace mode
                # (IoU/border inliers unreliable cross-camera, but LPQ works)
                lpq_hint = lpq_result['lpq_verdict_hint']
                if lpq_hint != 'uncertain':
                    final_verdict = lpq_hint
                    final_confidence = 0.60  # LPQ-driven, moderate confidence
                elif quant_verdict != 'uncertain':
                    final_verdict = quant_verdict
                    final_confidence = 0.45  # quant unreliable in marketplace
                else:
                    final_verdict = 'uncertain'
                    final_confidence = 0.4
        else:
            # ── STANDARD MODE: Quant has priority ──
            if quant_verdict == vision_verdict:
                final_verdict = quant_verdict
                final_confidence = max(vision_confidence, 0.85)
                # LPQ triple-agreement → highest confidence
                if (quant_verdict == 'same_copy' and lpq_chi2 < LPQ_SAME_COPY) or \
                   (quant_verdict == 'different_copy' and lpq_chi2 > LPQ_DIFF_COPY):
                    final_confidence = max(final_confidence, 0.95)
            elif quant_verdict == 'uncertain':
                # Vision is the tiebreaker for uncertain cases — its primary role
                final_verdict = vision_verdict
                final_confidence = vision_confidence
            elif vision_verdict == 'uncertain':
                final_verdict = quant_verdict
                final_confidence = 0.7
            else:
                # Disagreement: trust quantitative (it showed clean separation in testing)
                final_verdict = quant_verdict
                final_confidence = 0.6

        return {
            'success': True,
            'verdict': quant_verdict,
            'confidence': round(float(
                0.85 if avg_dilated_iou >= DILATED_IOU_SAME_COPY
                else min(0.92, 0.70 + border_inliers * 0.05) if border_inliers >= BORDER_INLIER_SAME_COPY
                else min(0.90, 0.65 + (DILATED_IOU_SAME_COPY - avg_dilated_iou) * 3) if border_inliers == 0 and avg_dilated_iou < DILATED_IOU_SAME_COPY
                else 0.5), 3),
            'avg_edge_iou': round(avg_iou, 5),
            'avg_dilated_iou': round(avg_dilated_iou, 5),
            'avg_edge_ssim': round(avg_ssim, 4),
            'per_edge': {k: {kk: round(vv, 5) for kk, vv in v.items()}
                        for k, v in per_edge.items()},
            'alignment': align_stats,
            'lpq_chi2': lpq_result['lpq_chi2'],
            'lpq_border_chi2': lpq_result['lpq_border_chi2'],
            'lpq_verdict_hint': lpq_result['lpq_verdict_hint'],
            'vision_verdict': vision_verdict,
            'vision_confidence': round(vision_confidence, 3),
            'vision_reasoning': parsed.get('reasoning', ''),
            'vision_observations': observations,
            'vision_corners': vision_corners,
            'vision_spine': vision_spine,
            'vision_edges': vision_edges,
            'final_verdict': final_verdict,
            'final_confidence': round(final_confidence, 3),
            'marketplace_mode': marketplace_mode,
            'verdict_source': 'vision_primary' if marketplace_mode else 'quant_primary',
            'cost_usd': round(cost, 5),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        # Fall back to quantitative only
        try:
            result = compare_covers(ref_url, test_url, extra_ref_photos, timeout)
        except Exception as fallback_err:
            return {
                'success': False,
                'verdict': 'error',
                'final_verdict': 'error',
                'error': (f'Vision failed: {e.__class__.__name__}: {str(e)[:150]}. '
                          f'Quant fallback also failed: {str(fallback_err)[:150]}'),
            }
        result['vision_error'] = f'{e.__class__.__name__}: {str(e)[:200]}'
        result['final_verdict'] = result.get('verdict')
        result['final_confidence'] = result.get('confidence')
        if marketplace_mode:
            result['marketplace_warning'] = (
                'Vision failed — marketplace verdict uses quantitative metrics only, '
                'which are unreliable for cross-camera comparisons.')
            result['final_confidence'] = min(result.get('final_confidence', 0.5), 0.5)
        return result
