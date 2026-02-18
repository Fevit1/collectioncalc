"""
Slab Guard CV — Computer Vision Engine for Copy-Level Identification
=====================================================================

Hybrid approach combining:
  1. SIFT-based image alignment (geometric correction)
  2. Edge IoU computation (quantitative copy fingerprint)
  3. Claude Vision "Difference Finder" (semantic interpretation)

Usage from monitor.py:
  from routes.slab_guard_cv import compare_covers, compare_covers_with_vision

Session 48 test results (4/4 accuracy):
  - edge_iou ≥ 0.025: SAME_COPY
  - edge_iou ≤ 0.010: DIFFERENT_COPY
  - 0.010 < edge_iou < 0.025: UNCERTAIN → use Claude Vision

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

# ── THRESHOLDS (tuned from Session 48 testing) ─────────────────────
EDGE_IOU_SAME_COPY = 0.025     # Above = same physical copy
EDGE_IOU_DIFF_COPY = 0.010     # Below = different physical copy
MIN_SIFT_INLIERS = 50          # Minimum for reliable alignment
EDGE_WIDTH_PX = 50             # Edge strip width in pixels
TARGET_SIZE = (800, 1200)      # Standard comparison size


def _download_image(url, timeout=15):
    """Download image from URL, return as cv2 BGR array."""
    import requests
    from io import BytesIO
    from PIL import Image as PILImage

    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    img_pil = PILImage.open(BytesIO(response.content)).convert('RGB')
    img_np = np.array(img_pil)
    return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)


def _resize_standard(img, size=TARGET_SIZE):
    """Resize image to standard comparison size."""
    return cv2.resize(img, size)


def _sift_align(ref, test):
    """
    SIFT-align test image to reference image.

    Returns:
        aligned: Warped test image aligned to ref coordinate space
        stats: Dict with alignment quality metrics
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

    inliers = int(mask.ravel().sum())
    stats['inliers'] = inliers
    stats['inlier_ratio'] = float(inliers / len(good))
    stats['aligned'] = inliers >= MIN_SIFT_INLIERS

    h, w = ref.shape[:2]
    aligned = cv2.warpPerspective(test, M, (w, h))

    return aligned, stats


def _compute_edge_iou(ref, aligned, edge_width=EDGE_WIDTH_PX):
    """
    Compute Canny edge IoU for each edge region after alignment.

    Returns:
        avg_iou: Average IoU across all 4 edges (the primary metric)
        per_edge: Dict with per-edge IoU values
        avg_ssim: Average SSIM across all 4 edges
    """
    h, w = ref.shape[:2]
    ew = edge_width

    edges = {
        'top': (ref[:ew, :], aligned[:ew, :]),
        'bottom': (ref[-ew:, :], aligned[-ew:, :]),
        'left': (ref[:, :ew], aligned[:, :ew]),
        'right': (ref[:, -ew:], aligned[:, -ew:]),
    }

    per_edge = {}
    all_ious = []
    all_ssims = []

    for name, (r_region, a_region) in edges.items():
        # Canny edge IoU
        r_canny = cv2.Canny(r_region, 50, 150)
        a_canny = cv2.Canny(a_region, 50, 150)

        intersection = cv2.bitwise_and(r_canny, a_canny).sum()
        union = cv2.bitwise_or(r_canny, a_canny).sum()
        iou = float(intersection / (union + 1e-8))
        per_edge[name] = {'iou': iou}
        all_ious.append(iou)

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
        all_ssims.append(ssim)

    return float(np.mean(all_ious)), per_edge, float(np.mean(all_ssims))


def _generate_residual_heatmap(ref, aligned, edge_width=EDGE_WIDTH_PX):
    """Generate edge-focused residual heatmap as JPEG bytes for Claude Vision."""
    import base64

    h, w = ref.shape[:2]
    ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY).astype(float)
    aligned_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY).astype(float)
    residual = np.abs(ref_gray - aligned_gray)

    # Amplify and apply colormap
    res_norm = np.clip(residual * 3, 0, 255).astype(np.uint8)
    heatmap = cv2.applyColorMap(res_norm, cv2.COLORMAP_JET)

    # Edge mask
    ew = edge_width
    edge_mask = np.zeros((h, w), dtype=np.uint8)
    edge_mask[:ew, :] = 255
    edge_mask[-ew:, :] = 255
    edge_mask[:, :ew] = 255
    edge_mask[:, -ew:] = 255

    edge_heatmap = cv2.bitwise_and(heatmap, heatmap, mask=edge_mask)

    # Overlay on darkened reference
    ref_dark = (ref.astype(float) * 0.4).astype(np.uint8)
    overlay = cv2.addWeighted(ref_dark, 1.0, edge_heatmap, 0.8, 0)

    cv2.putText(overlay, "Edge Residual (3x amp)", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    _, buf = cv2.imencode('.jpg', overlay, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.standard_b64encode(buf).decode('utf-8')


def _create_side_by_side(img_a, img_b, max_height=700):
    """Create side-by-side comparison as base64 JPEG."""
    import base64

    h = min(img_a.shape[0], img_b.shape[0], max_height)
    a_r = cv2.resize(img_a, (int(img_a.shape[1] * h / img_a.shape[0]), h))
    b_r = cv2.resize(img_b, (int(img_b.shape[1] * h / img_b.shape[0]), h))
    gap = np.ones((h, 8, 3), dtype=np.uint8) * 128
    combined = np.hstack([a_r, gap, b_r])

    _, buf = cv2.imencode('.jpg', combined, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.standard_b64encode(buf).decode('utf-8')


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

        # SIFT align
        aligned, align_stats = _sift_align(ref_img, test_img)

        # If alignment fails, try alternate front photos as fallback
        used_alternate = False
        if not align_stats.get('aligned') and extra_ref_photos:
            alt_fronts = [p for p in extra_ref_photos
                          if p.get('type') in ('alternate_front',) and p.get('url')]
            for alt in alt_fronts:
                try:
                    alt_img = _resize_standard(_download_image(alt['url'], timeout))
                    alt_aligned, alt_stats = _sift_align(alt_img, test_img)
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

        # Compute edge IoU
        avg_iou, per_edge, avg_ssim = _compute_edge_iou(ref_img, aligned)

        # Determine verdict
        if avg_iou >= EDGE_IOU_SAME_COPY:
            verdict = 'same_copy'
            confidence = min(0.95, 0.7 + (avg_iou - EDGE_IOU_SAME_COPY) * 10)
        elif avg_iou <= EDGE_IOU_DIFF_COPY:
            verdict = 'different_copy'
            confidence = min(0.95, 0.7 + (EDGE_IOU_DIFF_COPY - avg_iou) * 20)
        else:
            verdict = 'uncertain'
            confidence = 0.5

        result = {
            'success': True,
            'verdict': verdict,
            'confidence': round(confidence, 3),
            'avg_edge_iou': round(avg_iou, 5),
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

        # SIFT align (with alternate fallback)
        aligned, align_stats = _sift_align(ref_img, test_img)

        if not align_stats.get('aligned') and extra_ref_photos:
            alt_fronts = [p for p in extra_ref_photos
                          if p.get('type') in ('alternate_front',) and p.get('url')]
            for alt in alt_fronts:
                try:
                    alt_img = _resize_standard(_download_image(alt['url'], timeout))
                    alt_aligned, alt_stats = _sift_align(alt_img, test_img)
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

        # Compute edge IoU
        avg_iou, per_edge, avg_ssim = _compute_edge_iou(ref_img, aligned)

        # Quantitative verdict
        if avg_iou >= EDGE_IOU_SAME_COPY:
            quant_verdict = 'same_copy'
        elif avg_iou <= EDGE_IOU_DIFF_COPY:
            quant_verdict = 'different_copy'
        else:
            quant_verdict = 'uncertain'

        # Generate visual aids for Claude
        sbs_b64 = _create_side_by_side(ref_img, test_img)
        heatmap_b64 = _generate_residual_heatmap(ref_img, aligned)

        # Build Claude Vision prompt
        metrics_text = (
            f"  avg_edge_iou:  {avg_iou:.4f}  "
            f"({'→ SAME indicator' if avg_iou >= EDGE_IOU_SAME_COPY else '→ DIFF indicator' if avg_iou <= EDGE_IOU_DIFF_COPY else '→ UNCERTAIN'}\n"
            f"  avg_edge_ssim: {avg_ssim:.4f}\n"
            f"  Per-edge IoU:  " + ", ".join(f"{k}={v['iou']:.4f}" for k, v in per_edge.items()) + "\n"
            f"  SIFT inliers:  {align_stats.get('inliers', 0)} ({align_stats.get('inlier_ratio', 0):.1%})"
        )

        align_note = ""
        if align_stats.get('inliers', 0) < 100:
            align_note = (f"NOTE: SIFT alignment quality is LOW ({align_stats.get('inliers')} inliers). "
                         "Metrics may be less reliable.")

        prompt = f"""A computer vision system compared two comic book cover photos. Metrics:

{metrics_text}

INTERPRETATION: avg_edge_iou ≥ 0.025 → SAME copy, ≤ 0.010 → DIFFERENT copy
{align_note}

I'm showing: (1) original photos side by side, (2) edge residual heatmap after alignment (blue=identical, red=different).

Based on metrics + visual inspection, respond in JSON:
{{"verdict": "SAME_COPY"/"DIFFERENT_COPY"/"UNCERTAIN", "confidence": 0.0-1.0, "reasoning": "2-3 sentences", "observations": ["list"]}}"""

        # Build message content with core images
        msg_content = [
            {"type": "text", "text": "Original photos:"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": sbs_b64}},
            {"type": "text", "text": "Edge residual heatmap:"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": heatmap_b64}},
        ]

        # Add defect/closeup reference photos if available (up to 4 to stay under token limits)
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
                    msg_content.append({"type": "text", "text": f"Reference detail — {desc}:"})
                    msg_content.append({"type": "image", "source": {
                        "type": "base64", "media_type": "image/jpeg", "data": ep_b64}})
                except Exception:
                    continue

            if labels:
                prompt += (f"\n\nThe owner also provided {len(labels)} reference close-up(s): "
                          f"{', '.join(labels)}. "
                          "Use these to look for matching or missing physical features "
                          "that would confirm whether this is the same physical copy.")

        msg_content.append({"type": "text", "text": prompt})

        # Call Claude Vision
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            system="You are a forensic print authentication specialist interpreting CV system results.",
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

        # Combined verdict: quant has priority, vision resolves uncertainty
        if quant_verdict == vision_verdict:
            final_verdict = quant_verdict
            final_confidence = max(vision_confidence, 0.85)
        elif quant_verdict == 'uncertain':
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
            'confidence': round(float(avg_iou >= EDGE_IOU_SAME_COPY and 0.85 or
                                      avg_iou <= EDGE_IOU_DIFF_COPY and 0.85 or 0.5), 3),
            'avg_edge_iou': round(avg_iou, 5),
            'avg_edge_ssim': round(avg_ssim, 4),
            'per_edge': {k: {kk: round(vv, 5) for kk, vv in v.items()}
                        for k, v in per_edge.items()},
            'alignment': align_stats,
            'vision_verdict': vision_verdict,
            'vision_confidence': round(vision_confidence, 3),
            'vision_reasoning': parsed.get('reasoning', ''),
            'vision_observations': parsed.get('observations', []),
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
