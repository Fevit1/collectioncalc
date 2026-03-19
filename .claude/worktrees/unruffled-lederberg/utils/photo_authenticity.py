"""
Photo Authenticity Detector for Slab Guard
==========================================
Detects whether an uploaded image is:
  - An original photo taken with a camera/phone (AUTHENTIC)
  - A screenshot from a website/app (SUSPICIOUS)
  - A photo of a screen displaying an image (SUSPICIOUS)
  - A re-saved/downloaded image from the web (SUSPICIOUS)

Uses multiple signals:
  1. EXIF metadata analysis (camera info, GPS, etc.)
  2. Moiré pattern detection (FFT frequency analysis)
  3. Compression artifact analysis (double-JPEG detection)
  4. Color/lighting uniformity (screens are unnaturally flat)
  5. Resolution & dimension analysis (screenshot vs camera resolution)

Usage:
  python photo_authenticity.py <image_path>

Returns JSON with overall score and per-check breakdown.
"""

import json
import struct
import sys
import os
import math
from io import BytesIO
from PIL import Image, ExifTags
import numpy as np
from scipy import fft as scipy_fft


# =============================================================================
# 1. EXIF METADATA ANALYSIS
# =============================================================================
def analyze_exif(image_path):
    """
    Check EXIF data for camera-originated signals.

    Original photos have rich EXIF: camera model, focal length, exposure,
    GPS, etc. Screenshots have minimal or no EXIF. Web-saved images
    typically have EXIF stripped.

    Returns:
      score (0-100): Higher = more likely authentic
      details (dict): What was found/missing
    """
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
    except Exception:
        return 25, {"error": "Could not read EXIF", "verdict": "No EXIF data — may be messaging-compressed or web-saved"}

    if exif_data is None:
        return 30, {
            "verdict": "No EXIF metadata — may be web-saved, screenshot, or sent via messaging app (WhatsApp, iMessage, etc. strip EXIF)",
            "has_exif": False,
            "note": "Missing EXIF alone is not conclusive — messaging apps strip metadata from legitimate photos"
        }

    # Map tag IDs to names
    decoded = {}
    for tag_id, value in exif_data.items():
        tag_name = ExifTags.TAGS.get(tag_id, tag_id)
        decoded[tag_name] = value

    score = 20  # Base score for having any EXIF
    details = {"has_exif": True, "fields_found": []}

    # Camera make/model — strong signal
    if "Make" in decoded:
        score += 15
        details["camera_make"] = str(decoded["Make"]).strip()
        details["fields_found"].append("Make")
    if "Model" in decoded:
        score += 15
        details["camera_model"] = str(decoded["Model"]).strip()
        details["fields_found"].append("Model")

    # Focal length — only real cameras have this
    if "FocalLength" in decoded:
        score += 10
        details["focal_length"] = str(decoded["FocalLength"])
        details["fields_found"].append("FocalLength")

    # Exposure settings — strong camera signal
    if "ExposureTime" in decoded:
        score += 5
        details["fields_found"].append("ExposureTime")
    if "FNumber" in decoded:
        score += 5
        details["fields_found"].append("FNumber")
    if "ISOSpeedRatings" in decoded:
        score += 5
        details["fields_found"].append("ISOSpeedRatings")

    # GPS data — very strong signal (phone photo)
    if "GPSInfo" in decoded:
        score += 15
        details["has_gps"] = True
        details["fields_found"].append("GPSInfo")
    else:
        details["has_gps"] = False

    # Software field — can indicate screenshot tools
    if "Software" in decoded:
        sw = str(decoded["Software"]).lower()
        details["software"] = decoded["Software"]
        details["fields_found"].append("Software")
        # Screenshot indicators
        screenshot_indicators = ["screenshot", "snip", "grab", "capture", "snagit", "lightshot"]
        if any(ind in sw for ind in screenshot_indicators):
            score = max(score - 30, 5)
            details["screenshot_software_detected"] = True

    # DateTime — original datetime is good
    if "DateTimeOriginal" in decoded:
        score += 5
        details["datetime_original"] = str(decoded["DateTimeOriginal"])
        details["fields_found"].append("DateTimeOriginal")

    score = min(score, 100)
    details["verdict"] = (
        "Rich EXIF — likely original camera photo" if score >= 70
        else "Some EXIF but incomplete — uncertain origin" if score >= 40
        else "Minimal EXIF — likely not an original photo"
    )

    return score, details


# =============================================================================
# 2. MOIRÉ PATTERN DETECTION (photo of screen)
# =============================================================================
def detect_moire(image_path):
    """
    Detect moiré patterns that appear when photographing screens.

    When a camera photographs a screen, the camera sensor grid and
    screen pixel grid interfere, creating periodic patterns visible
    in the frequency domain (FFT).

    Returns:
      score (0-100): Higher = more likely authentic (no moiré)
      details (dict): Analysis results
    """
    try:
        img = Image.open(image_path).convert("L")  # Grayscale
        # Resize to standard size for consistent analysis
        img = img.resize((512, 512), Image.LANCZOS)
        arr = np.array(img, dtype=np.float64)
    except Exception as e:
        return 50, {"error": str(e), "verdict": "Could not analyze"}

    # Apply 2D FFT
    f_transform = scipy_fft.fft2(arr)
    f_shift = scipy_fft.fftshift(f_transform)
    magnitude = np.abs(f_shift)

    # Log magnitude for analysis
    log_magnitude = np.log1p(magnitude)

    # Analyze high-frequency energy distribution
    rows, cols = magnitude.shape
    center_r, center_c = rows // 2, cols // 2

    # Create distance map from center
    y, x = np.ogrid[:rows, :cols]
    distance = np.sqrt((x - center_c) ** 2 + (y - center_r) ** 2)
    max_dist = np.sqrt(center_r ** 2 + center_c ** 2)

    # Divide into frequency bands
    low_mask = distance < (max_dist * 0.15)
    mid_mask = (distance >= max_dist * 0.15) & (distance < max_dist * 0.5)
    high_mask = distance >= max_dist * 0.5

    low_energy = np.mean(magnitude[low_mask])
    mid_energy = np.mean(magnitude[mid_mask])
    high_energy = np.mean(magnitude[high_mask])

    total_energy = low_energy + mid_energy + high_energy
    if total_energy == 0:
        return 50, {"verdict": "Could not compute frequency distribution"}

    high_ratio = high_energy / total_energy
    mid_ratio = mid_energy / total_energy

    # Moiré creates distinctive peaks in mid-high frequencies
    # Look for periodic spikes (peaks significantly above neighbors)
    # Analyze radial profile for unusual peaks
    radial_bins = 50
    radial_profile = np.zeros(radial_bins)
    radial_counts = np.zeros(radial_bins)

    for i in range(rows):
        for j in range(cols):
            d = math.sqrt((i - center_r) ** 2 + (j - center_c) ** 2)
            bin_idx = min(int(d / max_dist * radial_bins), radial_bins - 1)
            radial_profile[bin_idx] += magnitude[i, j]
            radial_counts[bin_idx] += 1

    # Average per bin
    radial_counts[radial_counts == 0] = 1
    radial_profile /= radial_counts

    # Look for spikes in mid-to-high frequency range (bins 10-40)
    mid_high_profile = radial_profile[10:40]
    if len(mid_high_profile) > 0 and np.std(mid_high_profile) > 0:
        mean_val = np.mean(mid_high_profile)
        std_val = np.std(mid_high_profile)
        peak_count = np.sum(mid_high_profile > mean_val + 2 * std_val)
        spike_ratio = peak_count / len(mid_high_profile)
    else:
        spike_ratio = 0

    # Score: moiré shows as high spike_ratio and elevated high_ratio
    moire_indicators = 0
    details = {
        "high_freq_ratio": round(float(high_ratio), 4),
        "mid_freq_ratio": round(float(mid_ratio), 4),
        "spike_ratio": round(float(spike_ratio), 4),
        "indicators": []
    }

    if high_ratio > 0.15:
        moire_indicators += 1
        details["indicators"].append("Elevated high-frequency energy")
    if spike_ratio > 0.15:
        moire_indicators += 1
        details["indicators"].append("Periodic frequency spikes detected")
    if mid_ratio > 0.45:
        moire_indicators += 1
        details["indicators"].append("Unusual mid-frequency concentration")

    if moire_indicators >= 2:
        score = 25
        details["verdict"] = "Possible moiré patterns — may be photo of screen"
    elif moire_indicators == 1:
        score = 60
        details["verdict"] = "Mild frequency anomaly — inconclusive"
    else:
        score = 90
        details["verdict"] = "No moiré patterns detected — consistent with original photo"

    return score, details


# =============================================================================
# 3. JPEG COMPRESSION ARTIFACT ANALYSIS
# =============================================================================
def analyze_compression(image_path):
    """
    Detect signs of double compression (re-saved JPEGs) and
    screenshot-specific compression patterns.

    Double-compressed images (saved from web, then re-saved) show
    characteristic blocking artifacts at misaligned 8x8 grids.
    Screenshots saved as PNG then converted to JPEG also have
    distinctive patterns.

    Returns:
      score (0-100): Higher = more likely authentic
      details (dict): Analysis results
    """
    details = {}

    try:
        img = Image.open(image_path)
    except Exception as e:
        return 50, {"error": str(e)}

    fmt = img.format
    details["format"] = fmt
    details["mode"] = img.mode

    # PNG is suspicious for photos (phones save as JPEG/HEIF)
    # Screenshots are typically PNG
    if fmt == "PNG":
        details["verdict"] = "PNG format — unusual for camera photos, common for screenshots"
        return 30, details

    if fmt not in ("JPEG", "MPO"):
        details["verdict"] = f"Unusual format ({fmt}) — not typical camera output"
        return 40, details

    # For JPEGs, analyze quantization tables
    # Double-compressed JPEGs have specific quantization artifacts
    score = 70  # Default for JPEG

    # Check JPEG quality estimate via file size vs dimensions
    file_size = os.path.getsize(image_path)
    width, height = img.size
    pixels = width * height

    if pixels > 0:
        bytes_per_pixel = file_size / pixels
        details["bytes_per_pixel"] = round(bytes_per_pixel, 3)
        details["file_size_kb"] = round(file_size / 1024, 1)
        details["dimensions"] = f"{width}x{height}"
        details["megapixels"] = round(pixels / 1_000_000, 1)

        # High-quality camera photos: typically 1.5-4 bytes/pixel
        # Messaging-compressed (WhatsApp, iMessage): typically 0.1-0.5 bytes/pixel
        # Web-saved/compressed: typically 0.2-0.8 bytes/pixel
        # Screenshots saved as JPEG: varies widely
        if bytes_per_pixel >= 1.2:
            score = 90
            details["compression_quality"] = "High — consistent with camera original (RAW/minimal compression)"
        elif bytes_per_pixel >= 0.4:
            score = 75
            details["compression_quality"] = "Good — consistent with camera or cloud photo service (Google Photos, iCloud)"
        elif bytes_per_pixel >= 0.15:
            score = 55
            details["compression_quality"] = "Medium — could be cloud-optimized, messaging-compressed, or web source"
        elif bytes_per_pixel >= 0.05:
            score = 35
            details["compression_quality"] = "Heavy compression — consistent with messaging apps or web source"
        else:
            score = 20
            details["compression_quality"] = "Extremely compressed — likely web thumbnail or heavily processed"

    # Analyze 8x8 block boundary artifacts (sign of JPEG double compression)
    try:
        gray = np.array(img.convert("L"), dtype=np.float64)

        # Compute block boundary differences
        # In single-compressed JPEG, 8x8 block boundaries are smooth
        # In double-compressed, they show distinct steps
        h_diffs = []
        v_diffs = []

        # Horizontal block boundaries
        for col in range(8, gray.shape[1] - 1, 8):
            diff = np.mean(np.abs(gray[:, col] - gray[:, col - 1]))
            h_diffs.append(diff)

        # Vertical block boundaries
        for row in range(8, gray.shape[0] - 1, 8):
            diff = np.mean(np.abs(gray[row, :] - gray[row - 1, :]))
            v_diffs.append(diff)

        # Compare block boundary diffs to non-boundary diffs
        non_boundary_diffs = []
        for col in range(1, min(gray.shape[1] - 1, 200)):
            if col % 8 != 0:
                diff = np.mean(np.abs(gray[:, col] - gray[:, col - 1]))
                non_boundary_diffs.append(diff)

        if h_diffs and non_boundary_diffs:
            boundary_mean = np.mean(h_diffs + v_diffs)
            non_boundary_mean = np.mean(non_boundary_diffs)

            if non_boundary_mean > 0:
                block_ratio = boundary_mean / non_boundary_mean
                details["block_boundary_ratio"] = round(float(block_ratio), 3)

                # Ratio significantly > 1.0 suggests visible block boundaries
                # which can indicate double compression
                if block_ratio > 1.3:
                    score = max(score - 20, 20)
                    details["double_compression"] = "Possible — elevated block boundary artifacts"
                else:
                    details["double_compression"] = "Not detected"
    except Exception:
        details["block_analysis"] = "Could not perform block boundary analysis"

    details["verdict"] = (
        "JPEG with high quality — likely original" if score >= 75
        else "JPEG with moderate quality — possibly re-compressed" if score >= 50
        else "JPEG with compression artifacts — likely not original capture"
    )

    return score, details


# =============================================================================
# 4. COLOR/LIGHTING UNIFORMITY ANALYSIS
# =============================================================================
def analyze_lighting(image_path):
    """
    Analyze lighting patterns. Original photos of physical objects
    have natural lighting variation (shadows, highlights, depth).
    Screenshots are perfectly flat. Photos of screens show
    characteristic brightness falloff and color temperature shifts.

    Returns:
      score (0-100): Higher = more likely authentic
      details (dict): Analysis results
    """
    try:
        img = Image.open(image_path).convert("RGB")
        img_resized = img.resize((256, 256), Image.LANCZOS)
        arr = np.array(img_resized, dtype=np.float64)
    except Exception as e:
        return 50, {"error": str(e)}

    # Analyze brightness distribution
    gray = np.mean(arr, axis=2)

    # Divide into quadrants and compare brightness
    h, w = gray.shape
    quadrants = {
        "top_left": gray[:h//2, :w//2],
        "top_right": gray[:h//2, w//2:],
        "bottom_left": gray[h//2:, :w//2],
        "bottom_right": gray[h//2:, w//2:],
    }

    q_means = {k: float(np.mean(v)) for k, v in quadrants.items()}
    q_values = list(q_means.values())
    brightness_range = max(q_values) - min(q_values)
    brightness_std = float(np.std(q_values))

    details = {
        "quadrant_brightness": {k: round(v, 1) for k, v in q_means.items()},
        "brightness_range": round(brightness_range, 1),
        "brightness_std": round(brightness_std, 1),
    }

    # Analyze color channel consistency
    # Screens have very uniform color temperature
    # Natural photos have slight color shifts across the frame
    r_mean = np.mean(arr[:, :, 0])
    g_mean = np.mean(arr[:, :, 1])
    b_mean = np.mean(arr[:, :, 2])

    # Check color temperature variation across image
    top_half = arr[:h//2, :, :]
    bottom_half = arr[h//2:, :, :]

    top_temp = float(np.mean(top_half[:, :, 0]) - np.mean(top_half[:, :, 2]))
    bottom_temp = float(np.mean(bottom_half[:, :, 0]) - np.mean(bottom_half[:, :, 2]))
    temp_variation = abs(top_temp - bottom_temp)

    details["color_temp_variation"] = round(temp_variation, 2)

    # Analyze local contrast (texture presence)
    # Real photos of comics have lots of texture; screenshots are smoother
    local_std = float(np.mean([np.std(gray[i:i+16, j:j+16])
                                for i in range(0, h-16, 16)
                                for j in range(0, w-16, 16)]))
    details["local_contrast"] = round(local_std, 2)

    # Scoring
    score = 50  # Neutral start
    indicators = []

    # Natural photos have brightness variation > 5
    if brightness_range > 10:
        score += 15
        indicators.append("Natural lighting variation present")
    elif brightness_range < 3:
        score -= 15
        indicators.append("Very uniform brightness — screen-like")

    # Color temperature should vary slightly in natural photos
    if temp_variation > 2:
        score += 10
        indicators.append("Natural color temperature variation")
    elif temp_variation < 0.5:
        score -= 10
        indicators.append("Very uniform color temperature — screen-like")

    # Good local contrast indicates texture (physical object)
    if local_std > 30:
        score += 15
        indicators.append("Rich texture/detail — consistent with physical photo")
    elif local_std < 15:
        score -= 10
        indicators.append("Low texture — could be flat/digital source")

    score = max(min(score, 100), 0)
    details["indicators"] = indicators
    details["verdict"] = (
        "Natural lighting patterns — consistent with original photo" if score >= 65
        else "Mixed signals — lighting analysis inconclusive" if score >= 40
        else "Uniform lighting — consistent with screenshot or photo of screen"
    )

    return score, details


# =============================================================================
# 5. RESOLUTION & DIMENSION ANALYSIS
# =============================================================================
def analyze_dimensions(image_path):
    """
    Analyze image dimensions and resolution for origin clues.

    Camera photos: typically 8-108 MP (3264x2448 to 12000x9000)
    Screenshots: match device screen resolution exactly
    Web images: typically small (800-1600px max dimension)

    Common screenshot resolutions:
      iPhone: 1170x2532, 1284x2778, 1290x2796
      Android: 1080x1920, 1080x2340, 1440x3200
      Desktop: 1920x1080, 2560x1440, 3840x2160

    Returns:
      score (0-100): Higher = more likely authentic
      details (dict): Analysis results
    """
    try:
        img = Image.open(image_path)
    except Exception as e:
        return 50, {"error": str(e)}

    width, height = img.size
    pixels = width * height
    mp = pixels / 1_000_000
    aspect_ratio = width / height if height > 0 else 0

    details = {
        "width": width,
        "height": height,
        "megapixels": round(mp, 1),
        "aspect_ratio": round(aspect_ratio, 3),
    }

    # Known screenshot resolutions
    screenshot_resolutions = {
        (1170, 2532), (2532, 1170),  # iPhone 12/13/14
        (1284, 2778), (2778, 1284),  # iPhone 12/13/14 Pro Max
        (1290, 2796), (2796, 1290),  # iPhone 15 Pro Max
        (1179, 2556), (2556, 1179),  # iPhone 15 Pro
        (1080, 1920), (1920, 1080),  # Common Android / Full HD
        (1440, 3200), (3200, 1440),  # Samsung Galaxy S series
        (1080, 2340), (2340, 1080),  # Common Android
        (1440, 3120), (3120, 1440),  # LG, etc.
        (2560, 1440), (1440, 2560),  # QHD
        (3840, 2160), (2160, 3840),  # 4K
        (2880, 1800), (1800, 2880),  # MacBook Pro Retina
        (3024, 1964), (1964, 3024),  # MacBook Pro 14"
        (3456, 2234), (2234, 3456),  # MacBook Pro 16"
    }

    score = 50  # Neutral

    # Check for exact screenshot resolution match
    if (width, height) in screenshot_resolutions:
        score = 20
        details["screenshot_resolution_match"] = True
        details["verdict"] = "Exact screenshot resolution match — very likely a screenshot"
        return score, details

    details["screenshot_resolution_match"] = False

    # Camera photos are typically 8+ MP
    # But messaging apps (WhatsApp, Messenger) compress to ~1600px max = ~1.5-2.5 MP
    if mp >= 8:
        score = 85
        details["resolution_class"] = "High resolution — consistent with camera photo"
    elif mp >= 3:
        score = 65
        details["resolution_class"] = "Medium resolution — could be camera or cropped"
    elif mp >= 1:
        score = 50
        details["resolution_class"] = "Moderate resolution — consistent with messaging-app compression or web source"
        details["note"] = "WhatsApp/Messenger typically output 1-2.5 MP images"
    elif mp >= 0.3:
        score = 35
        details["resolution_class"] = "Low resolution — likely web-sourced, cropped, or heavily compressed"
    else:
        score = 15
        details["resolution_class"] = "Very low resolution — likely thumbnail or web image"

    # Very small images (under 500px both dimensions) are suspicious regardless
    if max(width, height) <= 500:
        score = max(score - 15, 10)
        details["tiny_image"] = True

    # File size as a signal
    # Real camera photos: typically 1.5-8+ MB
    # WhatsApp-compressed: typically 100-300 KB
    # Screengrabs/web-saves: typically 50-150 KB
    file_size_kb = os.path.getsize(image_path) / 1024
    details["file_size_kb"] = round(file_size_kb, 1)

    if file_size_kb >= 1500:
        score = min(score + 10, 100)
        details["file_size_signal"] = "Large file — consistent with camera original"
    elif file_size_kb >= 500:
        score = min(score + 5, 100)
        details["file_size_signal"] = "Medium file — could be camera or cloud-compressed"
    elif file_size_kb <= 120:
        score = max(score - 10, 5)
        details["file_size_signal"] = "Very small file — consistent with screengrab or web thumbnail"

    # Camera aspect ratios: 4:3 (phone), 3:2 (DSLR), 16:9 (phone wide)
    camera_ratios = [(4/3, 0.05), (3/2, 0.05), (16/9, 0.05), (3/4, 0.05), (2/3, 0.05), (9/16, 0.05)]
    ratio_match = any(abs(aspect_ratio - r) < tol for r, tol in camera_ratios)

    if ratio_match:
        score = min(score + 10, 100)
        details["standard_camera_ratio"] = True

    details["verdict"] = (
        "Resolution and dimensions consistent with camera photo" if score >= 65
        else "Dimensions are ambiguous" if score >= 40
        else "Resolution suggests web-sourced or screenshot origin"
    )

    return score, details


# =============================================================================
# 6. EDGE SHARPNESS & DETAIL ANALYSIS
# =============================================================================
def analyze_sharpness(image_path):
    """
    Analyze image sharpness and detail level.

    Original camera photos have crisp edges — text is sharp, lines are clean.
    Screenshots of photos, web-saved images, and photos-of-screens have
    softer edges due to resampling, compression, and resolution loss.

    Uses Laplacian variance as a sharpness metric, plus analysis of
    high-frequency detail density.

    Returns:
      score (0-100): Higher = more likely authentic
      details (dict): Analysis results
    """
    try:
        img = Image.open(image_path).convert("L")
        # Don't resize — analyze at native resolution for true sharpness
        arr = np.array(img, dtype=np.float64)
    except Exception as e:
        return 50, {"error": str(e)}

    # Laplacian kernel for edge detection
    laplacian_kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)

    # Apply Laplacian via convolution (manual, no cv2 dependency)
    h, w = arr.shape
    if h < 10 or w < 10:
        return 50, {"error": "Image too small for sharpness analysis"}

    # Pad the array
    padded = np.pad(arr, 1, mode='edge')
    laplacian = np.zeros_like(arr)

    for i in range(h):
        for j in range(w):
            region = padded[i:i+3, j:j+3]
            laplacian[i, j] = np.sum(region * laplacian_kernel)

    # Laplacian variance — classic sharpness metric
    lap_var = float(np.var(laplacian))
    lap_mean = float(np.mean(np.abs(laplacian)))

    # Strong edges percentage (pixels with high Laplacian response)
    threshold = np.percentile(np.abs(laplacian), 90)
    strong_edge_pct = float(np.mean(np.abs(laplacian) > threshold) * 100)

    # Gradient magnitude for additional detail
    grad_x = np.diff(arr, axis=1)
    grad_y = np.diff(arr, axis=0)
    grad_mag_x = float(np.mean(np.abs(grad_x)))
    grad_mag_y = float(np.mean(np.abs(grad_y)))
    avg_gradient = (grad_mag_x + grad_mag_y) / 2

    details = {
        "laplacian_variance": round(lap_var, 1),
        "laplacian_mean_abs": round(lap_mean, 2),
        "strong_edge_pct": round(strong_edge_pct, 2),
        "avg_gradient": round(avg_gradient, 2),
        "native_resolution": f"{w}x{h}",
    }

    # Scoring based on sharpness
    # Camera photos of comics: high laplacian variance (sharp text, ink lines)
    # Web-saved/screenshot: lower variance (resampling blurs edges)
    # The key insight: normalize by resolution — small images CAN'T be as sharp
    pixels = w * h
    mp = pixels / 1_000_000

    # Sharpness relative to what we'd expect at this resolution
    # Higher MP images should have higher absolute sharpness
    if mp >= 1:
        # At 1+ MP, we expect decent sharpness from a real photo
        if lap_var >= 800:
            score = 90
            details["sharpness_class"] = "Very sharp — consistent with original camera photo"
        elif lap_var >= 300:
            score = 70
            details["sharpness_class"] = "Moderately sharp — could be original or lightly compressed"
        elif lap_var >= 100:
            score = 50
            details["sharpness_class"] = "Somewhat soft — consistent with messaging compression"
        else:
            score = 30
            details["sharpness_class"] = "Soft/blurry — consistent with heavy compression or web source"
    else:
        # Under 1MP — small images have inherently less detail
        if lap_var >= 400:
            score = 60
            details["sharpness_class"] = "Sharp for size — but low resolution limits confidence"
        elif lap_var >= 150:
            score = 45
            details["sharpness_class"] = "Moderate for size — could be cropped or web-sourced"
        else:
            score = 25
            details["sharpness_class"] = "Soft for size — likely heavily processed"

    # Bonus: comic book photos should have lots of strong edges (ink lines, text)
    if avg_gradient > 15:
        score = min(score + 5, 100)
        details["detail_density"] = "High detail density"
    elif avg_gradient < 5:
        score = max(score - 5, 0)
        details["detail_density"] = "Low detail density"

    details["verdict"] = (
        "Sharp detail — consistent with original photo" if score >= 70
        else "Moderate detail — inconclusive" if score >= 45
        else "Soft/blurry — consistent with web-saved or screenshot"
    )

    return score, details


# =============================================================================
# 7. ERROR LEVEL ANALYSIS (ELA)
# =============================================================================
def analyze_ela(image_path):
    """
    Error Level Analysis — detects compression inconsistencies.

    Original single-compressed JPEGs have uniform error levels across
    the entire image. Recaptured, spliced, or double-compressed images
    show non-uniform error patterns because different regions have
    different compression histories.

    Method: Re-save image at a known quality (90%), compute the
    difference between original and re-saved version, analyze the
    uniformity of the error map.

    Returns:
      score (0-100): Higher = more likely authentic
      details (dict): Analysis results
    """
    try:
        img = Image.open(image_path).convert("RGB")
    except Exception as e:
        return 50, {"error": str(e), "verdict": "Could not analyze"}

    # ELA only works well on JPEGs — PNG/other formats don't have
    # the same compression artifact structure
    try:
        original_format = Image.open(image_path).format
    except Exception:
        original_format = None

    if original_format == "PNG":
        return 50, {
            "verdict": "ELA is not reliable for PNG images (lossless compression)",
            "format": "PNG",
            "note": "ELA depends on JPEG lossy compression artifacts"
        }

    # Re-save at quality 90
    buffer = BytesIO()
    img.save(buffer, "JPEG", quality=90)
    buffer.seek(0)
    resaved = Image.open(buffer).convert("RGB")

    # Compute difference (error level map)
    original_arr = np.array(img, dtype=np.float64)
    resaved_arr = np.array(resaved, dtype=np.float64)
    ela_map = np.abs(original_arr - resaved_arr)

    # Scale for visibility (multiply by a factor)
    scale_factor = 10
    ela_scaled = np.clip(ela_map * scale_factor, 0, 255)

    # Analyze the ELA map
    ela_mean = float(np.mean(ela_map))
    ela_std = float(np.std(ela_map))
    ela_max = float(np.max(ela_map))

    # Analyze uniformity across regions
    # Divide into a grid and compare error levels across blocks
    h, w = ela_map.shape[:2]
    block_size = max(h, w) // 8  # 8x8 grid of blocks
    if block_size < 10:
        block_size = 10

    block_means = []
    for y in range(0, h - block_size, block_size):
        for x in range(0, w - block_size, block_size):
            block = ela_map[y:y+block_size, x:x+block_size]
            block_means.append(float(np.mean(block)))

    if len(block_means) > 1:
        block_std = float(np.std(block_means))
        block_range = max(block_means) - min(block_means)
        block_cv = block_std / max(np.mean(block_means), 0.001)  # Coefficient of variation
    else:
        block_std = 0
        block_range = 0
        block_cv = 0

    details = {
        "ela_mean": round(ela_mean, 2),
        "ela_std": round(ela_std, 2),
        "ela_max": round(ela_max, 1),
        "block_uniformity_std": round(block_std, 3),
        "block_range": round(block_range, 3),
        "block_cv": round(block_cv, 3),
        "num_blocks_analyzed": len(block_means),
    }

    # Scoring
    # Original single-compressed JPEG: uniform ELA (low block CV)
    # Double-compressed / recaptured: non-uniform ELA (high block CV)
    # Very low ELA mean = heavily compressed (most information lost)
    # Moderate ELA mean = normal compression
    # High ELA mean = minimal compression (close to original)

    score = 50  # Neutral start

    # Block uniformity — most important ELA signal
    # Lower CV = more uniform = more likely single-compression = authentic
    if block_cv < 0.3:
        score += 20
        details["uniformity"] = "Highly uniform — consistent with single compression (original)"
    elif block_cv < 0.5:
        score += 10
        details["uniformity"] = "Moderately uniform — mostly consistent compression"
    elif block_cv < 0.8:
        score -= 5
        details["uniformity"] = "Some non-uniformity — possible double compression"
    else:
        score -= 15
        details["uniformity"] = "Non-uniform — strong indicator of manipulation or recapture"

    # ELA mean level
    # Very low mean = image has been compressed many times (info lost)
    # Moderate mean = normal
    if ela_mean < 1.0:
        score -= 10
        details["compression_history"] = "Very low error levels — heavily compressed, little original data remains"
    elif ela_mean < 3.0:
        score += 5
        details["compression_history"] = "Low-moderate error — consistent with standard JPEG"
    elif ela_mean < 8.0:
        score += 10
        details["compression_history"] = "Moderate error levels — consistent with high-quality original"
    else:
        score += 5
        details["compression_history"] = "High error levels — minimal prior compression"

    score = max(min(score, 100), 0)

    details["verdict"] = (
        "Uniform error levels — consistent with original photo" if score >= 65
        else "Moderate ELA consistency — inconclusive" if score >= 40
        else "Non-uniform error levels — possible recapture or manipulation"
    )

    return score, details


# =============================================================================
# OVERALL AUTHENTICITY SCORE
# =============================================================================
def check_authenticity(image_path):
    """
    Run all checks and produce an overall authenticity assessment.

    Returns dict with:
      - overall_score (0-100)
      - overall_verdict (string)
      - checks (dict of individual check results)
      - recommendation (string for Slab Guard)
    """
    results = {}

    # Run all checks
    exif_score, exif_details = analyze_exif(image_path)
    results["exif"] = {"score": exif_score, "details": exif_details}

    moire_score, moire_details = detect_moire(image_path)
    results["moire"] = {"score": moire_score, "details": moire_details}

    comp_score, comp_details = analyze_compression(image_path)
    results["compression"] = {"score": comp_score, "details": comp_details}

    light_score, light_details = analyze_lighting(image_path)
    results["lighting"] = {"score": light_score, "details": light_details}

    dim_score, dim_details = analyze_dimensions(image_path)
    results["dimensions"] = {"score": dim_score, "details": dim_details}

    sharp_score, sharp_details = analyze_sharpness(image_path)
    results["sharpness"] = {"score": sharp_score, "details": sharp_details}

    ela_score, ela_details = analyze_ela(image_path)
    results["ela"] = {"score": ela_score, "details": ela_details}

    # Weighted overall score
    # Dimensions (resolution + file size) is strongest differentiator from real testing
    # Lighting is most resilient signal (survives messaging compression)
    # Sharpness helps distinguish real photos from screenshots-of-photos
    # ELA adds compression history analysis
    # EXIF is strong when present but messaging apps strip it (less penalty)
    weights = {
        "exif": 0.12,
        "moire": 0.08,
        "compression": 0.08,
        "lighting": 0.18,
        "dimensions": 0.22,
        "sharpness": 0.17,
        "ela": 0.15,
    }

    overall = sum(results[k]["score"] * weights[k] for k in weights)
    overall = round(overall, 1)

    # Determine verdict
    # Thresholds calibrated against real-world testing:
    #   - Original Pixel 7 Pro photo via Google Photos: ~70-75
    #   - eBay screengrabs: ~58-63
    #   - WhatsApp-compressed real photo: ~55-60
    #   - Synthetic screenshots/web-saves: ~30-40
    if overall >= 68:
        verdict = "AUTHENTIC — High confidence this is an original camera photo"
        recommendation = "ALLOW — Registration can proceed normally"
    elif overall >= 52:
        verdict = "UNCERTAIN — Mixed signals, may be legitimate but compressed/transferred"
        recommendation = "FLAG — Allow registration but flag for review. Consider requesting additional proof of possession."
    elif overall >= 35:
        verdict = "SUSPICIOUS — Multiple indicators suggest this is not an original photo"
        recommendation = "CHALLENGE — Require proof of possession (e.g., photo with handwritten note or specific angle request)"
    else:
        verdict = "LIKELY FRAUDULENT — Strong indicators of screenshot, web-saved, or photo-of-screen"
        recommendation = "BLOCK — Do not allow registration without manual review and proof of possession"

    return {
        "image": os.path.basename(image_path),
        "overall_score": overall,
        "overall_verdict": verdict,
        "recommendation": recommendation,
        "checks": results,
    }


def print_report(result):
    """Pretty-print the authenticity report."""
    print("=" * 70)
    print(f"  SLAB GUARD PHOTO AUTHENTICITY REPORT")
    print(f"  Image: {result['image']}")
    print("=" * 70)
    print()
    print(f"  OVERALL SCORE: {result['overall_score']}/100")
    print(f"  VERDICT: {result['overall_verdict']}")
    print(f"  ACTION:  {result['recommendation']}")
    print()
    print("-" * 70)

    check_names = {
        "exif": "EXIF Metadata",
        "moire": "Moiré Detection (FFT)",
        "compression": "Compression Analysis",
        "lighting": "Lighting/Color",
        "dimensions": "Resolution/Dimensions",
        "sharpness": "Edge Sharpness/Detail",
        "ela": "Error Level Analysis (ELA)",
    }

    for key, name in check_names.items():
        check = result["checks"][key]
        print(f"\n  [{check['score']:3d}/100] {name}")
        print(f"          {check['details'].get('verdict', 'N/A')}")

        # Print key details for each check
        d = check["details"]
        if key == "exif":
            if d.get("camera_make"):
                print(f"          Camera: {d.get('camera_make', '?')} {d.get('camera_model', '')}")
            if d.get("has_gps"):
                print(f"          GPS: Present")
            print(f"          Fields found: {len(d.get('fields_found', []))}")
        elif key == "compression":
            if d.get("format"):
                print(f"          Format: {d['format']}, {d.get('dimensions', '?')}")
            if d.get("bytes_per_pixel"):
                print(f"          Quality: {d['bytes_per_pixel']} bytes/pixel")
        elif key == "dimensions":
            if d.get("screenshot_resolution_match"):
                print(f"          ⚠ EXACT SCREENSHOT RESOLUTION MATCH")
            print(f"          {d.get('megapixels', '?')} MP, ratio {d.get('aspect_ratio', '?')}")

    print("\n" + "=" * 70)


# =============================================================================
# CLI
# =============================================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python photo_authenticity.py <image_path> [--json]")
        print("       python photo_authenticity.py <image_path> --json  (for JSON output)")
        sys.exit(1)

    image_path = sys.argv[1]
    json_output = "--json" in sys.argv

    if not os.path.exists(image_path):
        print(f"Error: File not found: {image_path}")
        sys.exit(1)

    result = check_authenticity(image_path)

    if json_output:
        print(json.dumps(result, indent=2, default=str))
    else:
        print_report(result)
