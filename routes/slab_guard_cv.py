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
BORDER_INLIER_EDGE_WIDTH = 60  # Wider border for inlier counting (60px sweet spot)
                                # 50px too narrow for Iron Man, 70px+ too noisy
BORDER_INLIER_RUNS = 3         # Run SIFT align N times, take max border inliers
                                # RANSAC non-determinism can drop 3→0; 3 runs stabilizes
EDGE_WIDTH_PX = 50             # Edge strip width for IoU computation
TARGET_SIZE = (800, 1200)      # Standard comparison size


def _auto_orient_image(img_pil):
    """
    Auto-orient a PIL image for consistent fingerprinting.

    Two-step correction:
      1. EXIF transpose — applies camera orientation metadata (handles phone
         photos that embed rotation in EXIF rather than pixel data).
      2. Aspect ratio heuristic — if the image is landscape (wider than tall),
         rotate 90° CCW to portrait. Comic books are always taller than wide,
         so a landscape image means the photo was taken sideways.

    Session 51: This fixed hash distances for rotated Iron Man #200 registrations
    (113 → 62 for IM-012, enabling it to pass the 77 composite threshold).
    Also fixed same-copy detection for IM-010 vs IM-011 (dilated_iou 0.11 → 0.27).
    """
    from PIL import ImageOps

    # Step 1: Apply EXIF orientation if present
    try:
        img_pil = ImageOps.exif_transpose(img_pil)
    except Exception:
        pass  # No EXIF or unsupported — continue with raw pixels

    # Step 2: Aspect ratio heuristic — comics are portrait
    w, h = img_pil.size
    if w > h:
        # Landscape → rotate 90° CW to portrait.
        # PIL rotate(270) = 90° clockwise. This matches the most common phone
        # landscape orientation (home button on right). Testing confirmed 270°
        # gives correct right-side-up orientation (dist=60 vs 116 for 90° CCW).
        img_pil = img_pil.rotate(270, expand=True)

    return img_pil


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

        # Determine verdict using dilated IoU, strict IoU, AND border inlier count.
        # Session 50: border_inliers is the strongest same-copy signal —
        # physical defects in border regions create unique SIFT features that
        # only match between photos of the same physical copy.
        border_inliers = align_stats.get('border_inliers', 0)

        if avg_dilated_iou >= DILATED_IOU_SAME_COPY:
            verdict = 'same_copy'
            confidence = min(0.95, 0.7 + (avg_dilated_iou - DILATED_IOU_SAME_COPY) * 5)
        elif border_inliers >= BORDER_INLIER_SAME_COPY:
            # Border inlier evidence overrides low IoU (e.g., Iron Man 010v011
            # where poor framing dragged IoU down but border defects still matched)
            verdict = 'same_copy'
            confidence = min(0.92, 0.70 + border_inliers * 0.05)
        elif border_inliers == 0 and avg_dilated_iou < DILATED_IOU_SAME_COPY:
            # No border inliers AND dilated IoU below same-copy threshold
            # Zero border inliers is strong DIFF evidence — physical defects
            # don't match. Confidence scales with how far IoU is from same threshold.
            verdict = 'different_copy'
            confidence = min(0.90, 0.65 + (DILATED_IOU_SAME_COPY - avg_dilated_iou) * 3)
        elif avg_iou <= EDGE_IOU_DIFF_COPY:
            # Low IoU but some border inliers — conflicting signals
            verdict = 'uncertain'
            confidence = 0.5
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
                                timeout=15):
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

        # Quantitative verdict (dilated IoU + strict IoU + border inlier count)
        border_inliers = align_stats.get('border_inliers', 0)

        if avg_dilated_iou >= DILATED_IOU_SAME_COPY:
            quant_verdict = 'same_copy'
        elif border_inliers >= BORDER_INLIER_SAME_COPY:
            quant_verdict = 'same_copy'
        elif border_inliers == 0 and avg_dilated_iou < DILATED_IOU_SAME_COPY:
            quant_verdict = 'different_copy'
        elif avg_iou <= EDGE_IOU_DIFF_COPY:
            quant_verdict = 'uncertain'  # conflicting signals
        else:
            quant_verdict = 'uncertain'

        # Generate visual aids for Claude: corner crops + edge crops + Canny overlay + overview
        corner_crops, skipped_corners = _create_corner_crop_comparisons(ref_img, aligned)
        edge_crops, skipped_edges = _create_edge_crop_comparisons(ref_img, aligned)
        canny_b64, canny_match_pct = _create_canny_overlay(ref_img, aligned)
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

        prompt = f"""You are comparing two photographs of the SAME comic book ISSUE to determine
whether they show the SAME physical copy or two DIFFERENT physical copies.

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
3. CANNY EDGE OVERLAY — a diagnostic image showing detected edge structure in border
   strips only. GREEN = edges present in BOTH photos (matching physical structure),
   RED = edges in REF only, BLUE = edges in TEST only. High green percentage suggests
   the physical edge structure matches. Use this to SEE where physical features are.
4. Overview side-by-side (small, for general orientation only).

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

STEP 4 — CANNY EDGE OVERLAY CHECK:
  Examine the Canny edge overlay image. This shows detected edge structure in the
  border strips. Spine stress marks, creases, and paper texture create edge patterns.
  a) Is the overlay mostly GREEN in areas where both photos have content? Green means
     the physical edge structure matches between both photos.
  b) Are there large RED or BLUE regions indicating edge structure that exists in only
     one photo? That suggests different physical features.
  c) Use this as SUPPORTING evidence — it helps you see subtle physical texture that
     may not be obvious in the color photos.

DECISION RULES:
- SAME_COPY: You found specific physical defects (not printed features) that match in
  precise position between REF and TEST. Physical texture patterns (spine stress marks,
  paper creases, surface wear) matching across multiple regions also count — these are
  physical features of the paper, not the print. The Canny overlay helps confirm this:
  high green overlap in border strips supports same-copy.
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
  "canny_overlay": "what the edge overlay shows — mostly green (matching) or mixed?",
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
        except:
            import re
            m = re.search(r'\{[\s\S]*\}', raw)
            parsed = json_mod.loads(m.group()) if m else {
                'verdict': 'UNCERTAIN', 'confidence': 0.5, 'reasoning': 'parse error', 'observations': []}

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

        # Combined verdict: quant has priority, vision resolves uncertainty
        if quant_verdict == vision_verdict:
            final_verdict = quant_verdict
            final_confidence = max(vision_confidence, 0.85)
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
            'vision_verdict': vision_verdict,
            'vision_confidence': round(vision_confidence, 3),
            'vision_reasoning': parsed.get('reasoning', ''),
            'vision_observations': observations,
            'vision_corners': vision_corners,
            'vision_spine': vision_spine,
            'vision_edges': vision_edges,
            'final_verdict': final_verdict,
            'final_confidence': round(final_confidence, 3),
            'cost_usd': round(cost, 5),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        # Fall back to quantitative only
        result = compare_covers(ref_url, test_url, timeout)
        result['vision_error'] = str(e)
        result['final_verdict'] = result.get('verdict')
        result['final_confidence'] = result.get('confidence')
        return result
