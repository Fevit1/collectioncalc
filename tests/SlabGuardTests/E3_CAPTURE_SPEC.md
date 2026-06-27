> # ⛔ SUPERSEDED — DO NOT EXECUTE (tombstoned 2026-06-27)
> **DEAD:** the controlled-background re-capture / re-shoot described in this entire document.
> **REPLACED BY:** E3 runs on **SAM masks of the EXISTING captures** (`TPTests/`, `FalsePostiveTest/`)
> via `scripts/e3_edge_sequence_test.py` — no re-shoot.
> **REASON:** the SAM run got **24/24 clean masks incl. white-on-white Marvel**; classical contour
> reliably segmented only **~6/24**. SAM answers the science question (does edge-sequence matching
> recover?) AND the production question (segment arbitrary backgrounds) at once, so the clean-input
> re-capture is no longer needed to isolate the variable.
> **DECISION:** 2026-06-27 (Session 111). See `docs/sessions/WHERE_WE_LEFT_OFF.md` (Session 111 entry).
> Everything below is retained for history ONLY. Do not source a plan from it.

---

# E3 Science-Test Capture Spec — controlled-background re-shoot (front-only) — ⛔ SUPERSEDED, see header

**Purpose:** answer the SCIENCE question — *does continuous edge-sequence matching actually recover
the same copy cross-camera?* — on **clean input that isolates the variable.** A controlled background
lets us extract the comic's physical edge reliably (classical contour detection), so the experiment
tests sequence-matching itself, not edge detection.

> **THIS IS TEST ISOLATION, NOT THE PRODUCTION ASSUMPTION.** Production recovery photos arrive on
> arbitrary real-world backgrounds (carpet, wood, busy bedspreads, white-on-white). Robust edge
> extraction there is a **learned-segmentation** problem (SAM2 / a custom comic-segmentation model),
> NOT classical contour detection — and it is a **post-launch build, queued and gated on E3 validating
> on this clean input.** We prove the method on easy input before building the hard input pipeline.

---

## Background — the one thing that matters
- **Matte, non-reflective, uniform, saturated solid color that no comic edge shares.** Recommend
  **dark green or royal blue** (chroma-key principle — segment the book by the background's known hue,
  works regardless of cover lightness).
- **Avoid black** (low contrast against dark-bordered covers, e.g. Iron Man's black border) **and white**
  (low contrast against white covers, e.g. Marvel Universe). A single dark-matte fails half the set;
  a saturated chroma contrasts both light and dark covers.
- Cheap options: matte green/blue posterboard, foam board, or a non-glossy fabric pulled flat (no
  wrinkles — wrinkle shadows read as false edges).

## Lighting & framing
- **Even, diffuse light; NO glare/hotspots** (matte background + matte covers help) and **no harsh
  shadows** around the comic (a cast shadow on the background creates a false edge for segmentation).
- **Leave a clear margin of background on ALL FOUR sides** of the comic — the full paper edge must sit
  inside the frame with background visible all around it (this is what makes edge extraction trivial).
- Square-on, minimal tilt; full-res phone camera; cover fills ~70–85% of frame (margin matters more
  here than maximal fill).

## What to shoot — two sets, front cover only

### Set 1 — TRUE POSITIVE (same physical copy, both phones)
For each of the 6 issues, shoot the **same physical book** on **both** phones. Copy number ties the
book across phones (copy 1 on Pixel = copy 1 on iPhone = the same book — shoot one book at a time).
```
tests/SlabGuardTests/E3Test/TP/Pixel/<Issue>_Front_1.jpg
tests/SlabGuardTests/E3Test/TP/iPhone/<Issue>_Front_1.jpeg
```
→ 12 photos, ingests with the harness `copynum` default (`--phone1 .../TP/Pixel --phone2 .../TP/iPhone`).

### Set 2 — FALSE POSITIVE (different physical copies, same issue, both phones)
For each of the 6 issues, the Pixel folder holds **a different physical copy** than the iPhone folder
(same issue, different book → must NOT match).
```
tests/SlabGuardTests/E3Test/FP/PixelPhotos/<Issue>_Front_Pixel.jpg
tests/SlabGuardTests/E3Test/FP/iPhonePhotos/<Issue>_Front_iPhone.jpeg
```
→ 12 photos, ingests with `--layout crosscam-fp`.

### Issue names (copy-paste, identical in both folders of each set)
```
Iron_Man_200
Heros_For_Hope
Marvel_Universe_1
Marvel_Universe_2
The_Invaders_41
Wolverine_And_The_Incredible_Hulk_1
```
Extension = whatever the camera outputs (.jpg/.jpeg both ingest).

## After capture
E3 (contour-follow physical-edge unroll + homography correspondence + sequence-matching arbiter) gets
drafted against this set, then the **both-sets gate** runs (front-only, same session, validity gate
cost>0 / no `vision=None`): **TP must improve AND cross-camera FP exactly 0/6, watched at per-pair
confidence** (continuous-edge exposure is a real new FP vector — shared printed trade dress / coincidental
wear alignment between different copies). E3 keeps the reject-default and FP strictness; it changes what
the arbiter sees and the matching operation, not the bar.

## Decision this test settles
- **E3 validates on clean input** → edge-sequence matching recovers; single-image is NOT ceilinged;
  the learned-segmentation production front-end is justified → goes on the roadmap (it also lifts
  grading/valuation image quality — not single-purpose).
- **E3 fails on clean input** → single-image cross-camera raw recovery is genuinely ceilinged (now tested
  with the demonstrated-working method on clean input); segmentation is moot; multi-view becomes primary.
