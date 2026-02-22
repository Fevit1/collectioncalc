"""
Texture Fingerprinting Prototype — Camera-Invariant Copy Identification
========================================================================

Testing whether high-frequency texture features (paper fiber, halftone dots,
physical micro-defects) can replace edge IoU for cross-camera copy matching.

HYPOTHESIS: After SIFT alignment, the printed artwork is identical across copies.
The remaining signal in specific frequency bands captures physical characteristics
(paper texture, ink absorption, manufacturing defects) that are:
  - UNIQUE per physical copy
  - INVARIANT to camera changes (lighting, sensor, angle)

Previous failures documented in slab_guard_cv.py:
  ❌ LBP: camera variation > physical differences
  ❌ Wavelet detail: sensor noise dominates
  ❌ High-pass: noise + printed artwork dominate

This prototype tries TARGETED approaches:
  1. Bandpass filtering (isolate halftone/texture frequency band, exclude noise)
  2. Phase correlation (structural positions, robust to intensity changes)
  3. Gabor filter bank (multi-scale texture at specific orientations)
  4. Local Phase Quantization (blur-invariant texture descriptor)
  5. DCT block energy (discrete cosine transform mid-frequency energy)
  6. Gradient orientation histogram
  7. Difference texture analysis (spatial structure of residual)

Test data: Iron Man #200 registrations
  - SW-2026-000010 (Copy A, photo 1) vs SW-2026-000011 (Copy A, photo 2): SAME copy
  - SW-2026-000010 (Copy A) vs SW-2026-000012 (Copy B): DIFFERENT copy
  - eBay listing vs each: DIFFERENT copy, DIFFERENT camera
"""

import numpy as np
import cv2
import requests
from io import BytesIO
from PIL import Image as PILImage, ImageOps
import json
import sys
import os
import time

# Add project root to path for imports
sys.path.insert(0, '/sessions/brave-admiring-volta/mnt/V2')

# ── Configuration ──
API_BASE = "https://collectioncalc-docker.onrender.com"
EBAY_IMAGE = "https://i.ebayimg.com/images/g/cGUAAeSwW1Vpf7O4/s-l1600.jpg"
TARGET_SIZE = (800, 1200)

SERIAL_NUMBERS = ['SW-2026-000010', 'SW-2026-000011', 'SW-2026-000012']
# Copy A: SW-2026-000010, SW-2026-000011 (same physical comic, different photos)
# Copy B: SW-2026-000012 (different physical comic)


def auto_orient_pil(img):
    """Auto-orient: EXIF transpose + landscape→portrait."""
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    w, h = img.size
    if w > h:
        img = img.rotate(270, expand=True)
    return img


def download_image(url, timeout=15):
    """Download image, auto-orient, return as cv2 BGR array."""
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    img_pil = PILImage.open(BytesIO(response.content)).convert('RGB')
    img_pil = auto_orient_pil(img_pil)
    img_np = np.array(img_pil)
    return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)


def resize_standard(img, size=TARGET_SIZE):
    """Resize to standard comparison size."""
    return cv2.resize(img, size)


def sift_align(ref, test):
    """SIFT-align test to ref. Returns (aligned, success, stats)."""
    gray_r = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    gray_t = cv2.cvtColor(test, cv2.COLOR_BGR2GRAY)

    sift = cv2.SIFT_create(nfeatures=5000)
    kp1, des1 = sift.detectAndCompute(gray_r, None)
    kp2, des2 = sift.detectAndCompute(gray_t, None)

    if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
        return test, False, {'error': 'insufficient_keypoints'}

    flann = cv2.FlannBasedMatcher(
        dict(algorithm=1, trees=5), dict(checks=100))
    matches = flann.knnMatch(des1, des2, k=2)

    good = [m for m, n in matches if m.distance < 0.7 * n.distance]
    if len(good) < 10:
        return test, False, {'error': 'insufficient_matches'}

    src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

    M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
    if M is None:
        return test, False, {'error': 'homography_failed'}

    inliers = int(mask.ravel().sum())
    if inliers < 50:
        return test, False, {'error': 'too_few_inliers', 'inliers': inliers}

    h, w = ref.shape[:2]
    aligned = cv2.warpPerspective(test, M, (w, h))
    return aligned, True, {'inliers': inliers, 'good_matches': len(good)}


def extract_interior_region(img, margin_pct=0.08):
    """Extract interior region, excluding border strips (background contamination)."""
    h, w = img.shape[:2]
    mx = int(w * margin_pct)
    my = int(h * margin_pct)
    return img[my:h-my, mx:w-mx]


def extract_border_strips(img, edge_width=50):
    """Extract just the border strips (where physical wear is most visible)."""
    h, w = img.shape[:2]
    ew = edge_width
    # Create mask for border strips
    mask = np.zeros((h, w), dtype=bool)
    mask[:ew, :] = True       # top
    mask[-ew:, :] = True      # bottom
    mask[:, :ew] = True       # left
    mask[:, -ew:] = True      # right
    return img, mask


# ══════════════════════════════════════════════════════════════
# TEXTURE FINGERPRINTING APPROACHES
# ══════════════════════════════════════════════════════════════

def approach_1_bandpass(ref_gray, test_gray):
    """
    Bandpass filtering — isolate texture frequency band.

    Subtracts two Gaussian blurs to isolate mid-frequency texture:
    halftone dots, paper fiber, micro-defects. Excludes low-freq lighting
    and high-freq sensor noise. Measures NCC of bandpass images.
    """
    ref_f = ref_gray.astype(np.float64)
    test_f = test_gray.astype(np.float64)
    results = {}

    for low_s, high_s, label in [
        (1, 10, "fine_texture"),
        (2, 20, "medium_texture"),
        (3, 40, "coarse_texture"),
        (5, 50, "broad_texture"),
    ]:
        ref_low = cv2.GaussianBlur(ref_f, (0, 0), high_s)
        ref_high = cv2.GaussianBlur(ref_f, (0, 0), low_s)
        ref_band = ref_high - ref_low

        test_low = cv2.GaussianBlur(test_f, (0, 0), high_s)
        test_high = cv2.GaussianBlur(test_f, (0, 0), low_s)
        test_band = test_high - test_low

        ref_norm = ref_band - np.mean(ref_band)
        test_norm = test_band - np.mean(test_band)
        ref_std = np.std(ref_norm)
        test_std = np.std(test_norm)

        if ref_std > 1e-6 and test_std > 1e-6:
            ncc = float(np.mean(ref_norm * test_norm) / (ref_std * test_std))
        else:
            ncc = 0.0
        results[label] = round(ncc, 6)

    return results


def approach_2_phase_correlation(ref_gray, test_gray):
    """
    Phase correlation — compare structural positions via FFT phase.
    Phase encodes WHERE structures are (camera-invariant position info).
    """
    ref_f = ref_gray.astype(np.float64)
    test_f = test_gray.astype(np.float64)

    h, w = ref_f.shape
    hann_y = np.hanning(h).reshape(-1, 1)
    hann_x = np.hanning(w).reshape(1, -1)
    window = hann_y * hann_x

    ref_fft = np.fft.fft2(ref_f * window)
    test_fft = np.fft.fft2(test_f * window)

    # Phase-only correlation
    ref_phase = ref_fft / (np.abs(ref_fft) + 1e-10)
    test_phase = test_fft / (np.abs(test_fft) + 1e-10)
    cross = ref_phase * np.conj(test_phase)
    poc = np.fft.ifft2(cross)
    peak = float(np.max(np.real(poc)))

    results = {'peak_correlation': round(peak, 6)}

    # Band-specific phase consistency
    freq_y = np.fft.fftfreq(h).reshape(-1, 1)
    freq_x = np.fft.fftfreq(w).reshape(1, -1)
    freq_mag = np.sqrt(freq_y**2 + freq_x**2)

    phase_diff = np.angle(ref_fft) - np.angle(test_fft)
    phase_diff = np.arctan2(np.sin(phase_diff), np.cos(phase_diff))

    for band_name, f_low, f_high in [
        ("low_freq", 0.0, 0.05),
        ("mid_freq", 0.05, 0.15),
        ("high_freq", 0.15, 0.35),
        ("very_high", 0.35, 0.5),
    ]:
        band_mask = (freq_mag >= f_low) & (freq_mag < f_high)
        if np.sum(band_mask) > 0:
            consistency = float(np.mean(np.cos(phase_diff[band_mask])))
        else:
            consistency = 0.0
        results[f"{band_name}_phase"] = round(consistency, 6)

    return results


def approach_3_gabor_texture(ref_gray, test_gray):
    """Gabor filter bank texture descriptor — cosine similarity."""
    ref_f = ref_gray.astype(np.float64) / 255.0
    test_f = test_gray.astype(np.float64) / 255.0

    orientations = [0, np.pi/6, np.pi/3, np.pi/2, 2*np.pi/3, 5*np.pi/6]
    wavelengths = [4, 8, 16, 32]

    ref_features, test_features = [], []

    for wavelength in wavelengths:
        for theta in orientations:
            sigma = wavelength * 0.5
            ks = int(6 * sigma) | 1
            kernel = cv2.getGaborKernel((ks, ks), sigma, theta, wavelength, 0.5, 0, ktype=cv2.CV_64F)

            ref_resp = cv2.filter2D(ref_f, cv2.CV_64F, kernel)
            test_resp = cv2.filter2D(test_f, cv2.CV_64F, kernel)

            ref_features.extend([float(np.mean(np.abs(ref_resp))), float(np.std(ref_resp))])
            test_features.extend([float(np.mean(np.abs(test_resp))), float(np.std(test_resp))])

    ref_vec = np.array(ref_features)
    test_vec = np.array(test_features)

    cosine = float(np.dot(ref_vec, test_vec) / (np.linalg.norm(ref_vec) * np.linalg.norm(test_vec) + 1e-10))
    l2 = float(np.linalg.norm(ref_vec - test_vec) / (np.linalg.norm(ref_vec) + 1e-10))

    return {'cosine_similarity': round(cosine, 6), 'l2_distance': round(l2, 6)}


def approach_4_lpq(ref_gray, test_gray, win_size=5):
    """Local Phase Quantization — blur-invariant texture histogram."""
    def compute_lpq(img, ws):
        h, w = img.shape
        img_f = img.astype(np.float64)
        freqs = [(1, 0), (0, 1), (1, 1), (1, -1)]
        responses = []
        for fx, fy in freqs:
            x_r = np.arange(-(ws//2), ws//2 + 1)
            y_r = np.arange(-(ws//2), ws//2 + 1)
            xx, yy = np.meshgrid(x_r, y_r)
            fnx, fny = fx / ws, fy / ws
            kr = np.cos(2 * np.pi * (fnx * xx + fny * yy))
            ki = np.sin(2 * np.pi * (fnx * xx + fny * yy))
            responses.append(cv2.filter2D(img_f, cv2.CV_64F, kr))
            responses.append(cv2.filter2D(img_f, cv2.CV_64F, ki))

        code = np.zeros((h, w), dtype=np.uint8)
        for i, resp in enumerate(responses):
            code += ((resp >= 0).astype(np.uint8) << i)

        hist, _ = np.histogram(code.ravel(), bins=256, range=(0, 256))
        hist = hist.astype(np.float64)
        hist /= (hist.sum() + 1e-10)
        return hist

    rh = compute_lpq(ref_gray, win_size)
    th = compute_lpq(test_gray, win_size)

    chi2 = float(np.sum((rh - th)**2 / (rh + th + 1e-10)))
    intersection = float(np.sum(np.minimum(rh, th)))
    bc = float(np.sum(np.sqrt(rh * th)))

    return {'chi2_distance': round(chi2, 6), 'intersection': round(intersection, 6), 'bhattacharyya': round(bc, 6)}


def approach_5_dct_energy(ref_gray, test_gray, block_size=8):
    """DCT mid-frequency energy — texture similarity via block DCT."""
    ref_f = ref_gray.astype(np.float64)
    test_f = test_gray.astype(np.float64)

    h_b = ref_f.shape[0] // block_size
    w_b = ref_f.shape[1] // block_size
    ref_c = ref_f[:h_b * block_size, :w_b * block_size]
    test_c = test_f[:h_b * block_size, :w_b * block_size]

    mid_mask = np.ones((block_size, block_size), dtype=bool)
    mid_mask[:2, :2] = False
    mid_mask[-3:, -3:] = False

    ref_e, test_e = [], []
    for by in range(h_b):
        for bx in range(w_b):
            y0, x0 = by * block_size, bx * block_size
            rb = ref_c[y0:y0+block_size, x0:x0+block_size]
            tb = test_c[y0:y0+block_size, x0:x0+block_size]
            ref_e.append(np.sum(cv2.dct(rb)[mid_mask]**2))
            test_e.append(np.sum(cv2.dct(tb)[mid_mask]**2))

    rv = np.array(ref_e)
    tv = np.array(test_e)
    rv = rv / (np.linalg.norm(rv) + 1e-10)
    tv = tv / (np.linalg.norm(tv) + 1e-10)

    cosine = float(np.dot(rv, tv))
    pearson = float(np.corrcoef(rv, tv)[0, 1]) if len(rv) > 1 else 0.0

    return {'cosine_similarity': round(cosine, 6), 'pearson': round(pearson, 6)}


def approach_6_gradient_orientation(ref_gray, test_gray):
    """Gradient orientation histogram — edge direction distribution."""
    def grad_hist(gray, n_bins=36):
        dx = cv2.Sobel(gray.astype(np.float64), cv2.CV_64F, 1, 0, ksize=3)
        dy = cv2.Sobel(gray.astype(np.float64), cv2.CV_64F, 0, 1, ksize=3)
        mag = np.sqrt(dx**2 + dy**2)
        orient = np.arctan2(dy, dx)
        bins = np.linspace(-np.pi, np.pi, n_bins + 1)
        hist = np.zeros(n_bins)
        for i in range(n_bins):
            mask = (orient >= bins[i]) & (orient < bins[i+1])
            hist[i] = np.sum(mag[mask])
        hist /= (hist.sum() + 1e-10)
        return hist

    rh = grad_hist(ref_gray)
    th = grad_hist(test_gray)

    chi2 = float(np.sum((rh - th)**2 / (rh + th + 1e-10)))
    cosine = float(np.dot(rh, th) / (np.linalg.norm(rh) * np.linalg.norm(th) + 1e-10))

    return {'chi2_distance': round(chi2, 6), 'cosine_similarity': round(cosine, 6)}


def approach_7_difference_texture(ref_gray, test_gray):
    """
    Difference image analysis — spatial structure of residual.
    Same-copy → structured residual (camera-only); different-copy → chaotic.
    """
    ref_f = ref_gray.astype(np.float64)
    test_f = test_gray.astype(np.float64)

    ref_norm = (ref_f - np.mean(ref_f)) / (np.std(ref_f) + 1e-10)
    test_norm = (test_f - np.mean(test_f)) / (np.std(test_f) + 1e-10)

    diff = ref_norm - test_norm
    rms = float(np.sqrt(np.mean(diff**2)))

    diff_m = diff - np.mean(diff)
    var = np.var(diff_m) + 1e-10
    ac_h = float(np.mean(diff_m[:, :-1] * diff_m[:, 1:]) / var) if diff_m.shape[1] > 1 else 0
    ac_v = float(np.mean(diff_m[:-1, :] * diff_m[1:, :]) / var) if diff_m.shape[0] > 1 else 0

    # Frequency distribution of residual
    diff_fft = np.fft.fft2(diff)
    diff_mag = np.abs(diff_fft)
    h, w = diff.shape
    freq_y = np.fft.fftfreq(h).reshape(-1, 1)
    freq_x = np.fft.fftfreq(w).reshape(1, -1)
    freq_r = np.sqrt(freq_y**2 + freq_x**2)

    low_e = float(np.sum(diff_mag[freq_r < 0.05]**2))
    mid_e = float(np.sum(diff_mag[(freq_r >= 0.05) & (freq_r < 0.2)]**2))
    high_e = float(np.sum(diff_mag[freq_r >= 0.2]**2))
    total = low_e + mid_e + high_e + 1e-10

    return {
        'rms_residual': round(rms, 6),
        'autocorr_h': round(ac_h, 6),
        'autocorr_v': round(ac_v, 6),
        'low_freq_ratio': round(low_e / total, 6),
        'mid_freq_ratio': round(mid_e / total, 6),
        'high_freq_ratio': round(high_e / total, 6),
    }


# ══════════════════════════════════════════════════════════════
# MAIN TEST RUNNER
# ══════════════════════════════════════════════════════════════

def run_all_approaches(ref_gray, test_gray, label):
    """Run all texture approaches and return results dict."""
    results = {}
    results['bandpass'] = approach_1_bandpass(ref_gray, test_gray)
    results['phase'] = approach_2_phase_correlation(ref_gray, test_gray)
    results['gabor'] = approach_3_gabor_texture(ref_gray, test_gray)
    results['lpq'] = approach_4_lpq(ref_gray, test_gray)
    results['dct'] = approach_5_dct_energy(ref_gray, test_gray)
    results['gradient'] = approach_6_gradient_orientation(ref_gray, test_gray)
    results['diff_texture'] = approach_7_difference_texture(ref_gray, test_gray)
    return results


def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  TEXTURE FINGERPRINTING PROTOTYPE — Iron Man #200 Testing  ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # Step 1: Get registration photo URLs
    print("\n1. Fetching photo URLs from verify endpoint...")
    photo_urls = {}
    for sn in SERIAL_NUMBERS:
        try:
            resp = requests.get(f"{API_BASE}/api/verify/lookup/{sn}", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('success'):
                    url = data.get('comic', {}).get('cover_url')
                    if url:
                        photo_urls[sn] = url
                        print(f"   ✅ {sn}: {url[:70]}...")
                    else:
                        print(f"   ❌ {sn}: no cover_url in response")
                else:
                    print(f"   ❌ {sn}: {data.get('error')}")
            else:
                print(f"   ❌ {sn}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"   ❌ {sn}: {e}")

    if len(photo_urls) < 3:
        print(f"\n   Only found {len(photo_urls)}/3 registration photos.")
        print("   Proceeding with available photos + eBay image.")

    # Step 2: Download all images
    print("\n2. Downloading and resizing images...")
    images = {}

    for sn, url in photo_urls.items():
        try:
            img = resize_standard(download_image(url))
            images[sn] = img
            print(f"   ✅ {sn}: {img.shape}")
        except Exception as e:
            print(f"   ❌ {sn}: download failed: {e}")

    # Download eBay image
    try:
        ebay_img = resize_standard(download_image(EBAY_IMAGE))
        images['eBay'] = ebay_img
        print(f"   ✅ eBay: {ebay_img.shape}")
    except Exception as e:
        print(f"   ❌ eBay: download failed: {e}")

    if len(images) < 2:
        print("\n   Not enough images to compare. Exiting.")
        return

    # Step 3: Define comparison pairs
    # Expected verdicts:
    #   SW-000010 vs SW-000011: SAME_COPY (Copy A photo 1 vs Copy A photo 2)
    #   SW-000010 vs SW-000012: DIFFERENT_COPY (Copy A vs Copy B, same camera)
    #   SW-000011 vs SW-000012: DIFFERENT_COPY (Copy A vs Copy B, same camera)
    #   eBay vs SW-000010: DIFFERENT_COPY (different copy, different camera)
    #   eBay vs SW-000011: DIFFERENT_COPY (different copy, different camera)
    #   eBay vs SW-000012: DIFFERENT_COPY (different copy, different camera)

    pairs = []
    sn_short = {
        'SW-2026-000010': '010',
        'SW-2026-000011': '011',
        'SW-2026-000012': '012',
        'eBay': 'eBay',
    }

    if 'SW-2026-000010' in images and 'SW-2026-000011' in images:
        pairs.append(('SW-2026-000010', 'SW-2026-000011', 'SAME_COPY', 'same_camera'))
    if 'SW-2026-000010' in images and 'SW-2026-000012' in images:
        pairs.append(('SW-2026-000010', 'SW-2026-000012', 'DIFFERENT_COPY', 'same_camera'))
    if 'SW-2026-000011' in images and 'SW-2026-000012' in images:
        pairs.append(('SW-2026-000011', 'SW-2026-000012', 'DIFFERENT_COPY', 'same_camera'))
    if 'eBay' in images:
        for sn in SERIAL_NUMBERS:
            if sn in images:
                pairs.append((sn, 'eBay', 'DIFFERENT_COPY', 'cross_camera'))

    print(f"\n3. Running {len(pairs)} comparison pairs...")

    # Step 4: Run comparisons
    all_results = {}

    for ref_key, test_key, expected, camera_type in pairs:
        pair_name = f"{sn_short[ref_key]} vs {sn_short[test_key]}"
        print(f"\n{'='*60}")
        print(f"PAIR: {pair_name} — expected: {expected} ({camera_type})")
        print(f"{'='*60}")

        ref_img = images[ref_key]
        test_img = images[test_key]

        # SIFT align
        t0 = time.time()
        aligned, success, stats = sift_align(ref_img, test_img)
        align_time = time.time() - t0

        if not success:
            print(f"  ❌ SIFT alignment failed: {stats}")
            all_results[pair_name] = {'error': 'alignment_failed', 'expected': expected}
            continue

        print(f"  ✅ Aligned in {align_time:.1f}s (inliers: {stats.get('inliers')})")

        # Convert to grayscale
        ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
        aligned_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)

        # Also get interior-only (no border contamination)
        ref_int = cv2.cvtColor(extract_interior_region(ref_img), cv2.COLOR_BGR2GRAY)
        ali_int = cv2.cvtColor(extract_interior_region(aligned), cv2.COLOR_BGR2GRAY)

        # Run all approaches on FULL image
        print("\n  [Full image]")
        t0 = time.time()
        full_results = run_all_approaches(ref_gray, aligned_gray, pair_name)
        full_time = time.time() - t0
        print(f"  Computed in {full_time:.1f}s")

        # Run on interior only
        print("  [Interior only]")
        t0 = time.time()
        int_results = run_all_approaches(ref_int, ali_int, f"{pair_name}_interior")
        int_time = time.time() - t0
        print(f"  Computed in {int_time:.1f}s")

        # Also compute baseline edge IoU
        from routes.slab_guard_cv import _compute_edge_iou
        avg_iou, per_edge, avg_ssim, avg_dilated_iou = _compute_edge_iou(ref_img, aligned)

        all_results[pair_name] = {
            'expected': expected,
            'camera_type': camera_type,
            'alignment': stats,
            'full': full_results,
            'interior': int_results,
            'baseline': {
                'strict_iou': round(avg_iou, 5),
                'dilated_iou': round(avg_dilated_iou, 5),
                'ssim': round(avg_ssim, 4),
            }
        }

    # Step 5: Summary comparison table
    print("\n\n" + "="*80)
    print("SUMMARY — SEPARATION ANALYSIS")
    print("="*80)
    print("\nLooking for metrics where SAME_COPY and DIFFERENT_COPY distributions don't overlap.")
    print("Good metric = clear gap between same-copy values and different-copy values.\n")

    # Collect metrics by category
    same_pairs = {k: v for k, v in all_results.items() if v.get('expected') == 'SAME_COPY' and 'error' not in v}
    diff_same_cam = {k: v for k, v in all_results.items() if v.get('expected') == 'DIFFERENT_COPY' and v.get('camera_type') == 'same_camera' and 'error' not in v}
    diff_cross_cam = {k: v for k, v in all_results.items() if v.get('expected') == 'DIFFERENT_COPY' and v.get('camera_type') == 'cross_camera' and 'error' not in v}

    def print_metric(metric_path, label, higher_is_same=True):
        """Print a metric across all pairs for comparison."""
        def get_val(result, path):
            parts = path.split('.')
            v = result
            for p in parts:
                if isinstance(v, dict):
                    v = v.get(p)
                else:
                    return None
            return v

        same_vals = [get_val(v, metric_path) for v in same_pairs.values() if get_val(v, metric_path) is not None]
        diff_sc_vals = [get_val(v, metric_path) for v in diff_same_cam.values() if get_val(v, metric_path) is not None]
        diff_cc_vals = [get_val(v, metric_path) for v in diff_cross_cam.values() if get_val(v, metric_path) is not None]

        if not same_vals or (not diff_sc_vals and not diff_cc_vals):
            return

        same_str = f"{min(same_vals):.4f}-{max(same_vals):.4f}" if len(same_vals) > 1 else f"{same_vals[0]:.4f}"
        diff_sc_str = f"{min(diff_sc_vals):.4f}-{max(diff_sc_vals):.4f}" if len(diff_sc_vals) > 1 else (f"{diff_sc_vals[0]:.4f}" if diff_sc_vals else "N/A")
        diff_cc_str = f"{min(diff_cc_vals):.4f}-{max(diff_cc_vals):.4f}" if len(diff_cc_vals) > 1 else (f"{diff_cc_vals[0]:.4f}" if diff_cc_vals else "N/A")

        # Check separation
        all_diff = diff_sc_vals + diff_cc_vals
        if all_diff and same_vals:
            if higher_is_same:
                gap = min(same_vals) - max(all_diff)
                sep = "✅ SEP" if gap > 0 else "❌ OVERLAP"
            else:
                gap = min(all_diff) - max(same_vals)
                sep = "✅ SEP" if gap > 0 else "❌ OVERLAP"
        else:
            sep = "?"
            gap = 0

        print(f"  {label:45s} | SAME: {same_str:15s} | DIFF-sc: {diff_sc_str:15s} | DIFF-cc: {diff_cc_str:15s} | {sep} (gap={gap:+.4f})")

    # Baseline
    print("\n── BASELINE (current edge IoU) ──")
    print_metric('baseline.dilated_iou', 'Dilated IoU', higher_is_same=True)
    print_metric('baseline.strict_iou', 'Strict IoU', higher_is_same=True)
    print_metric('baseline.ssim', 'SSIM', higher_is_same=True)

    # Full image approaches
    print("\n── APPROACH 1: Bandpass Filtering (full image) ──")
    for band in ['fine_texture', 'medium_texture', 'coarse_texture', 'broad_texture']:
        print_metric(f'full.bandpass.{band}', f'Bandpass NCC — {band}', higher_is_same=True)

    print("\n── APPROACH 1: Bandpass Filtering (interior only) ──")
    for band in ['fine_texture', 'medium_texture', 'coarse_texture', 'broad_texture']:
        print_metric(f'interior.bandpass.{band}', f'Bandpass NCC — {band} (int)', higher_is_same=True)

    print("\n── APPROACH 2: Phase Correlation (full image) ──")
    print_metric('full.phase.peak_correlation', 'Phase peak', higher_is_same=True)
    for band in ['low_freq_phase', 'mid_freq_phase', 'high_freq_phase', 'very_high_phase']:
        print_metric(f'full.phase.{band}', f'Phase consistency — {band}', higher_is_same=True)

    print("\n── APPROACH 2: Phase Correlation (interior) ──")
    print_metric('interior.phase.peak_correlation', 'Phase peak (int)', higher_is_same=True)
    for band in ['low_freq_phase', 'mid_freq_phase', 'high_freq_phase', 'very_high_phase']:
        print_metric(f'interior.phase.{band}', f'Phase — {band} (int)', higher_is_same=True)

    print("\n── APPROACH 3: Gabor Texture (full image) ──")
    print_metric('full.gabor.cosine_similarity', 'Gabor cosine sim', higher_is_same=True)
    print_metric('full.gabor.l2_distance', 'Gabor L2 distance', higher_is_same=False)

    print("\n── APPROACH 3: Gabor Texture (interior) ──")
    print_metric('interior.gabor.cosine_similarity', 'Gabor cosine sim (int)', higher_is_same=True)
    print_metric('interior.gabor.l2_distance', 'Gabor L2 distance (int)', higher_is_same=False)

    print("\n── APPROACH 4: LPQ Descriptor (full image) ──")
    print_metric('full.lpq.chi2_distance', 'LPQ chi2', higher_is_same=False)
    print_metric('full.lpq.intersection', 'LPQ intersection', higher_is_same=True)
    print_metric('full.lpq.bhattacharyya', 'LPQ Bhattacharyya', higher_is_same=True)

    print("\n── APPROACH 5: DCT Energy (full image) ──")
    print_metric('full.dct.cosine_similarity', 'DCT cosine sim', higher_is_same=True)
    print_metric('full.dct.pearson', 'DCT Pearson corr', higher_is_same=True)

    print("\n── APPROACH 6: Gradient Orientation (full image) ──")
    print_metric('full.gradient.chi2_distance', 'Gradient chi2', higher_is_same=False)
    print_metric('full.gradient.cosine_similarity', 'Gradient cosine sim', higher_is_same=True)

    print("\n── APPROACH 7: Difference Texture (full image) ──")
    print_metric('full.diff_texture.rms_residual', 'Diff RMS', higher_is_same=False)
    print_metric('full.diff_texture.autocorr_h', 'Diff autocorr-H', higher_is_same=True)
    print_metric('full.diff_texture.autocorr_v', 'Diff autocorr-V', higher_is_same=True)
    print_metric('full.diff_texture.mid_freq_ratio', 'Diff mid-freq ratio', higher_is_same=False)

    print("\n── APPROACH 7: Difference Texture (interior) ──")
    print_metric('interior.diff_texture.rms_residual', 'Diff RMS (int)', higher_is_same=False)
    print_metric('interior.diff_texture.autocorr_h', 'Diff autocorr-H (int)', higher_is_same=True)
    print_metric('interior.diff_texture.autocorr_v', 'Diff autocorr-V (int)', higher_is_same=True)

    # Raw results dump
    print("\n\n" + "="*80)
    print("RAW RESULTS")
    print("="*80)
    for pair_name, result in all_results.items():
        print(f"\n{pair_name} (expected: {result.get('expected')}, {result.get('camera_type', '?')}):")
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
            continue
        print(f"  Baseline: {result['baseline']}")
        print(f"  Full image:")
        for approach, vals in result.get('full', {}).items():
            print(f"    {approach}: {vals}")
        print(f"  Interior:")
        for approach, vals in result.get('interior', {}).items():
            print(f"    {approach}: {vals}")


if __name__ == '__main__':
    main()
