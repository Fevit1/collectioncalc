# Slab Guard CV — How It Works (Product Overview)

*Last updated: February 20, 2026*

---

## What It Does

Slab Guard CV answers one question: **"Is this the same physical comic book, or a different copy?"**

Two copies of Iron Man #200 in VF condition look nearly identical — same cover art, same colors, same print. But every physical copy has its own unique wear pattern: a specific spine tick here, a corner bend there, a tiny edge chip in a unique spot. Slab Guard CV detects these differences.

---

## When It's Used

There are two scenarios:

**1. Same-camera (re-verification)**
The owner registered their comic with photos, and later takes new photos to prove they still have it — or to verify a comic they're buying in person. Both photo sets come from similar phones and environments.

**2. Cross-camera / marketplace (theft recovery)**
A comic was stolen. The owner finds it on eBay. They grab the seller's listing photo and compare it against their original registration photos. The two photos come from completely different cameras, lighting, and backgrounds.

These two scenarios are handled differently because the second one is much harder.

---

## The Pipeline (Step by Step)

### Step 1 — Issue Matching (Hash Gate)

**What it does:** Confirms both photos show the same comic book issue.

**How:** When a comic is registered, we generate a "composite fingerprint" — four different perceptual hash algorithms (pHash, dHash, aHash, wHash) that create a compact numerical summary of the cover image. When a new photo comes in, we generate the same hashes and compare.

**Thresholds:**
- Distance ≤ 77 → same issue (standard mode)
- Distance ≤ 105 → same issue (marketplace mode, looser because cross-camera photos look more different)
- Distance > threshold → not a match, stop here

**Speed:** Instant. This is the cheap filter that prevents us from running expensive analysis on unrelated comics.

---

### Step 2 — SIFT Alignment

**What it does:** Geometrically aligns the two photos so the cover art overlaps perfectly, pixel for pixel.

**How:** SIFT (Scale-Invariant Feature Transform) finds distinctive visual landmarks in both photos — things like the corner of a word balloon, the tip of a character's weapon, the edge of a logo. It matches these landmarks across photos and computes the geometric transformation (rotation, scale, perspective) needed to warp one photo onto the other.

**Quality check:** We need at least 50 matching landmarks ("inliers") for a reliable alignment. Blurry, tiny, or heavily angled photos may fail this check.

**Why it matters:** Everything downstream depends on the photos being aligned. If Iron Man's helmet is at pixel (200, 300) in the reference photo, it needs to be at (200, 300) in the test photo too, so we can compare the physical wear around it.

---

### Step 3 — Quantitative Comparison (Three Metrics)

After alignment, we measure three things:

#### 3a. Edge IoU (Intersection over Union)

**Plain English:** After alignment, we detect all the sharp edges in both photos (using Canny edge detection) and measure how much they overlap in the border regions (top, bottom, left, right strips of the cover).

**Why borders?** Physical wear — spine ticks, corner dents, edge chips — lives in the borders. The interior is mostly pristine printed art that looks the same across all copies.

**Same copy →** high overlap (same physical dents create the same edge patterns)
**Different copy →** low overlap (different dents in different places)

**Limitation:** Works great when both photos come from similar cameras. Falls apart cross-camera because lighting and background differences create false edges.

#### 3b. Border Inliers

**Plain English:** During SIFT alignment, some of those matched landmarks land in the border region of the comic. If they match well, it means both photos share specific physical features in their borders — strong evidence of the same copy.

**Same copy →** 2+ border inliers (matching spine ticks, corner bends)
**Different copy →** 0 border inliers (no shared physical wear features)

**Limitation:** Background textures (blanket fibers, table grain) near the comic's edge can create false border matches, especially cross-camera. LPQ (below) catches these false positives.

#### 3c. LPQ (Local Phase Quantization)

**Plain English:** LPQ analyzes the texture pattern of the border regions using a technique that's designed to be robust to blur and camera differences. It creates a histogram of local texture patterns and compares them.

**Why it helps:** LPQ is more camera-robust than raw edge comparison because it uses phase information (the *structure* of texture) rather than intensity (which changes with lighting). When border inliers give a false "same copy" signal from background noise, LPQ's high distance score catches the error and downgrades the verdict to "uncertain."

**Same copy →** low distance (chi² ~0.05–0.12)
**Different copy →** high distance (chi² ~0.15–1.4)

**Key insight:** Like Edge IoU, LPQ's discriminative power comes from the borders (physical wear), not the interior (printed art). Border-only LPQ has 4.7× stronger separation than full-image LPQ.

---

### Step 4 — Claude Vision (AI Interpretation)

**What it does:** Shows Claude both photos side-by-side, zoomed into corners and edges, and asks it to find physical differences.

**When it runs:**
- Always in marketplace mode (cross-camera, where quantitative metrics are unreliable)
- On request for same-camera mode (high-value items, or when quant says "uncertain")

**How the prompt works:** Claude gets a structured checklist:
1. Examine each corner (zoomed 4×)
2. Examine each edge strip (spine, top, bottom, right)
3. Classify every visible difference as PHOTO artifact (lighting, angle) vs. PHYSICAL defect (real wear difference)
4. Only call SAME_COPY if specific, locatable physical defects match in both photos

**Anti-hallucination safeguards:**
- Default verdict is DIFFERENT_COPY (conservative — must prove they match)
- We do NOT show Vision the quantitative metrics (prevents anchoring bias)
- In marketplace mode, we warn Vision about cross-camera environmental differences
- In marketplace mode, the Canny edge overlay is NOT shown (it was misleading Vision — printed art edges look like matches)

**Cost:** ~$0.015 per comparison (Claude Sonnet)

---

### Step 5 — Verdict Logic

The final verdict combines quant and Vision depending on mode:

**Same-camera mode (quant is primary):**
| Condition | Verdict |
|-----------|---------|
| Edge IoU ≥ 0.13 | SAME_COPY |
| Border inliers ≥ 2 AND LPQ agrees (chi² < 0.15) | SAME_COPY |
| Border inliers ≥ 2 BUT LPQ disagrees (chi² > 0.15) | UNCERTAIN → Vision resolves |
| Border inliers = 0 AND Edge IoU < 0.13 | DIFFERENT_COPY |
| Everything else | UNCERTAIN → Vision resolves |

**Marketplace mode (Vision is primary):**
| Condition | Verdict |
|-----------|---------|
| Vision says SAME and quant doesn't contradict | SAME_COPY |
| Vision says DIFFERENT | DIFFERENT_COPY |
| Vision uncertain, LPQ clearly different (chi² > 0.40) | DIFFERENT_COPY |
| Vision uncertain, LPQ unclear | UNCERTAIN |

---

## Current Accuracy

**Same-camera pairs:** 6/6 correct across Handbook #2 and Iron Man #200

**Cross-camera/marketplace pairs:** 6/6 correct or acceptable (3 definitive, 3 "uncertain" that Vision resolves correctly when enabled)

**Sample size caveat:** Only 1 confirmed same-copy pair and 5 different-copy pairs tested. More test data needed before these numbers mean much statistically.

---

## What We Tried That Didn't Work

We tested 20+ approaches before landing on this pipeline. The short version of why most failed: **phone photo variation (lighting, camera sensor, angle, background) creates bigger visual differences than the physical wear differences between two copies of the same comic.** Most computer vision techniques measure visual similarity, but we need to measure *physical* similarity through imperfect visual data.

The approaches that work (SIFT alignment + edge IoU + border inliers + LPQ + Vision) succeed because they either focus specifically on border wear patterns or use techniques designed to be robust to camera differences.

---

## API Endpoints

| Endpoint | Purpose | Speed | Cost |
|----------|---------|-------|------|
| `POST /api/monitor/check-image` | Full pipeline: hash gate → SIFT → quant → optional Vision | 3–15s | $0–0.015 |
| `POST /api/monitor/compare-copies` | Direct two-photo comparison (no registry search) | 3–15s | $0–0.015 |

Both accept `marketplace_mode: true` for cross-camera eBay/marketplace photos.

---

## Key Limitations

1. **Photo quality matters.** Blurry, tiny, or heavily angled photos may not SIFT-align (< 50 inliers). We need a photo quality gate at registration.

2. **Cross-camera is harder.** Same-camera comparisons are reliable with just the quantitative metrics. Marketplace comparisons need Vision ($0.015/call) and are inherently less certain.

3. **Small test dataset.** Only 2 comic titles tested (Handbook #2, Iron Man #200), only 1 same-copy pair per title. Need more data to validate thresholds.

4. **Background noise.** Comics photographed on textured surfaces (blankets, wood tables) create false signals. Clean, flat backgrounds produce better results.
