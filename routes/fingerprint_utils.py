"""
Fingerprint Utilities — Shared image preprocessing for Slab Guard
=================================================================

Centralized functions used by multiple modules to ensure consistent
fingerprinting across registration, monitoring, and SIFT comparison.

CRITICAL: These functions MUST produce identical results everywhere they're
used. If you change preprocessing here, ALL existing fingerprints in the
database become invalid (hashes computed with old preprocessing won't match
hashes computed with new preprocessing). Re-fingerprinting the database is
required after any change to these functions.

Used by:
  - routes/registry.py — fingerprint generation at registration time
  - routes/monitor.py — fingerprint generation for query images
  - routes/slab_guard_cv.py — auto-orientation before SIFT comparison

History:
  Session 51: Added auto_orient_pil() — fixed perceptual hash rotation-invariance
    problem. Iron Man #200 hash distance dropped from 113 to 62, enabling marketplace
    matching. Without this, rotated phone photos are blocked by the 77 threshold.
  Session 53: Extracted from monitor.py and registry.py into shared module to
    eliminate code duplication. Both files had identical implementations with
    comments saying "Must match the other file exactly" — a maintenance hazard.
"""

from PIL import Image, ImageFilter, ImageOps, ImageStat


def auto_orient_pil(img):
    """
    Auto-orient a PIL image for consistent fingerprinting.

    Two-step correction:
      1. EXIF transpose — applies camera orientation metadata (handles phone
         photos that embed rotation in EXIF rather than pixel data).
      2. Aspect ratio heuristic — if the image is landscape (wider than tall),
         rotate 90° CW to portrait. Comic books are always taller than wide,
         so a landscape image means the photo was taken sideways.

    Session 51: This fixed hash distances for rotated Iron Man #200 registrations
    (113 → 62 for IM-012, enabling it to pass the 77 composite threshold).
    Also fixed same-copy detection for IM-010 vs IM-011 (dilated_iou 0.11 → 0.27).

    WHY 270° NOT 90°: Testing confirmed 270° CW (PIL rotate(270)) correctly orients
    phone photos taken with home button on right (most common landscape orientation).
    90° CCW gave hash distance 116 vs 60 for 270° CW.

    WHY THIS MATTERS: Perceptual hashes (pHash, dHash, aHash, wHash) are NOT
    rotation-invariant. Without auto-rotation, a 90° rotated registration photo
    gets hash distance 103-113 against the same comic (blocked by 77 threshold).
    """
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass  # No EXIF or unsupported — continue with raw pixels

    w, h = img.size
    if w > h:
        img = img.rotate(270, expand=True)

    return img


def preprocess_for_fingerprint(img):
    """
    Normalize an image before perceptual hash fingerprinting.

    Makes fingerprints robust to real-world phone photo variation:
      - Rotated phone photos → auto-orient (Session 51)
      - Different lighting conditions → autocontrast
      - Different backgrounds → auto-crop to content bounding box
      - Different phone distances → resize to standard 256×256
      - Compression artifacts → light Gaussian blur

    Pipeline: auto-orient → grayscale → auto-crop → resize 256×256 → autocontrast → blur

    Testing showed this cuts same-comic hash distances roughly in half:
      - Raw worst case: 72/256 per angle
      - Preprocessed worst case: 36/256 per angle

    ⚠️ CHANGING THIS FUNCTION INVALIDATES ALL EXISTING FINGERPRINTS IN THE DATABASE.
    If you modify the pipeline, you must re-fingerprint all registered comics.
    """
    # 0. Auto-orient: EXIF transpose + landscape→portrait heuristic (Session 51)
    img = auto_orient_pil(img)

    # 1. Convert to grayscale (removes color/white-balance variation)
    img = img.convert('L')

    # 2. Auto-crop: trim uniform borders (removes background variation)
    width, height = img.size
    pixels = img.load()

    # Estimate background color from corners
    corner_size = max(5, min(width, height) // 20)
    corners = []
    for region in [
        (0, 0, corner_size, corner_size),
        (width - corner_size, 0, width, corner_size),
        (0, height - corner_size, corner_size, height),
        (width - corner_size, height - corner_size, width, height)
    ]:
        corner_img = img.crop(region)
        corner_stat = ImageStat.Stat(corner_img)
        corners.append(corner_stat.mean[0])
    bg_color = sum(corners) / len(corners)

    # Find bounding box of content (pixels differing from background by 30+)
    left, top, right, bottom = width, height, 0, 0
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            if abs(pixels[x, y] - bg_color) > 30:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)

    # Add small padding and crop if content area is meaningful
    pad_x = max(5, int(width * 0.02))
    pad_y = max(5, int(height * 0.02))
    left = max(0, left - pad_x)
    top = max(0, top - pad_y)
    right = min(width, right + pad_x)
    bottom = min(height, bottom + pad_y)

    if right - left > width * 0.3 and bottom - top > height * 0.3:
        img = img.crop((left, top, right, bottom))

    # 3. Resize to standard 256×256 (removes scale/distance variation)
    img = img.resize((256, 256), Image.LANCZOS)

    # 4. Normalize contrast (removes brightness/lighting variation)
    img = ImageOps.autocontrast(img, cutoff=2)

    # 5. Light Gaussian blur (removes noise/compression artifacts)
    img = img.filter(ImageFilter.GaussianBlur(radius=1))

    return img
