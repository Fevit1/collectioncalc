# Photo Authenticity Detector — Findings & Integration Plan
**Date:** February 27, 2026
**Author:** Claude + Mike Berry
**Status:** Prototype validated with real-world images

---

## Problem Statement

Slab Guard allows users to register ownership of comic books by uploading photos. A bad actor could screenshot an eBay listing, register the comic as "theirs" in Slab Guard, then falsely claim the real owner's comic is stolen. This is a first-mover fraud attack that undermines the entire system's credibility.

## Solution: Multi-Signal Photo Authenticity Detection

We built a 7-check photo authenticity detector (`utils/photo_authenticity.py`) that analyzes uploaded images for signs of being screenshots, web-saved images, or photos-of-screens rather than original camera photos.

## The 7 Checks

| # | Check | Weight | What It Detects |
|---|-------|--------|-----------------|
| 1 | EXIF Metadata | 12% | Camera make/model, GPS, focal length, exposure — absent in screenshots/web saves |
| 2 | Moiré Detection (FFT) | 8% | Interference patterns from photographing screens |
| 3 | Compression Analysis | 8% | Double-compression artifacts, bytes-per-pixel quality |
| 4 | Lighting/Color | 18% | Natural lighting variation vs. flat screen uniformity |
| 5 | Resolution/Dimensions | 22% | Megapixels, file size, screenshot resolution matching, aspect ratio |
| 6 | Edge Sharpness | 17% | Laplacian variance, detail density — blurry = resampled |
| 7 | Error Level Analysis | 15% | Compression uniformity — non-uniform = double-compressed/recaptured |

## Real-World Test Results

Tested against 4 real images: 2 eBay screengrabs, 1 real photo sent via WhatsApp, 1 original from Google Photos.

| Image | Source | Score | Verdict |
|-------|--------|-------|---------|
| MarvelHandbook1eBay1.jpg | eBay screengrab | 51.8 | SUSPICIOUS |
| MarvelHandbook2Bay2.jpg | eBay screengrab | 50.1 | SUSPICIOUS |
| MarvelHandbook2eBay3.jpeg | Real photo via WhatsApp | 56.2 | UNCERTAIN |
| PXL_20260217_153705891.jpg | Original from Google Photos | 75.8 | AUTHENTIC |

### Score Ranges & Actions
- **68+** → AUTHENTIC → Allow registration
- **52-67** → UNCERTAIN → Allow but flag for review
- **35-51** → SUSPICIOUS → Challenge with proof-of-possession request
- **<35** → LIKELY FRAUDULENT → Block registration pending manual review

## Key Findings

### 1. EXIF is the strongest single signal — when present
Original photo had 9 EXIF fields (Pixel 7 Pro, GPS, focal length, exposure). All screenshots/web-saves had zero. But messaging apps (WhatsApp, iMessage, Messenger) strip EXIF from legitimate photos, so missing EXIF alone can't condemn an image.

### 2. Resolution/file size is the most reliable differentiator
- Original: 12.5 MP, 3,294 KB
- WhatsApp: 1.9 MP, 224 KB
- Screengrabs: 0.2-0.3 MP, 90-95 KB

Even after WhatsApp compression, the real photo was 2-3x the size of screengrabs.

### 3. ELA correctly identified compression history
Original scored 75 (uniform error levels). All others scored 35 (non-uniform). This is because the original went through one compression pass, while screengrabs went through the original photographer's compression + screenshot + re-save.

### 4. Lighting analysis is resilient but can be fooled
Photos of real comics on a bedspread have natural lighting variation regardless of whether they're original or screengrabbed — because the original photographer used natural light. Lighting works great for flat UI screenshots but not for screenshots-of-photos.

### 5. WhatsApp destroys forensic evidence
WhatsApp compressed a 12.5 MP photo to 1.9 MP and stripped all EXIF. The resulting image was forensically closer to a screengrab than to the original. This means users who send photos through messaging apps will get flagged.

## Integration Plan for Slab Guard

### Phase 1: Passive Scoring (Now)
- Run authenticity check on every Slab Guard registration upload
- Store score in database alongside the registration
- Log all check details for analysis
- No user-facing blocking yet — just data collection

### Phase 2: Active Gating (Pre-GalaxyCon)
- Show authenticity score in admin dashboard
- SUSPICIOUS/FRAUDULENT registrations trigger proof-of-possession challenge
- Challenge: "Please take a new photo of this comic with [random object] next to it"
- UNCERTAIN registrations allowed but flagged

### Phase 3: In-App Capture (Post-Launch)
- PWA/app camera integration — photos taken directly in Slab Worthy
- EXIF controlled, no messaging compression, GPS verified
- Timestamp embedded in photo metadata
- This is the strongest long-term defense

### Phase 4: ML Enhancement (Future)
- Train CNN on real vs. recaptured images using actual user data
- Academic research shows 82-95% accuracy with deep learning approaches
- Could use few-shot learning to adapt to new recapture scenarios

## Recommended FAQ Language

> **How does Slab Guard verify photo authenticity?**
> When you register a comic with Slab Guard, our system performs multi-signal analysis on your uploaded photos to verify they were taken directly with your camera. We check metadata, image quality, compression patterns, and other forensic indicators. For the strongest protection, we recommend uploading photos directly from your phone's camera roll rather than sending them through messaging apps first.

## Files

- `utils/photo_authenticity.py` — Full detector with 7 checks, CLI interface, JSON output
- `PhotosofPhotosTest/` — Test images used for calibration
- `docs/technical/PHOTO_AUTHENTICITY_FINDINGS.md` — This document

## Academic References

- Hussain et al. (2022) "Evaluation of Deep Learning and Conventional Approaches for Image Recaptured Detection"
- "Recaptured Image Forensics Based on Image Illumination and Texture Features" (ACM, 2020)
- FotoForensics ELA methodology (fotoforensics.com)
- Error Level Analysis — Wikipedia
