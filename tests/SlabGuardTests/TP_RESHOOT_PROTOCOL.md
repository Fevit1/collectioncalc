# Slab Guard — True-Positive (Recovery Sensitivity) Reshoot Protocol

**Purpose:** measure the one number still missing — **recovery sensitivity (true-positive rate)**:
the *same physical comic* photographed on *two different phones* must match (`same_copy`).
The cross-camera **false-positive** rate is already locked at **0/12** (front covers, three runs).
TP is the gating item before any positive "we can recover your stolen comic" claim.

**Why a reshoot is needed:** in the existing top-level `PixelPhotos`/`iPhonePhotos`, copy numbering
was **not tracked across phones** — `Iron_Man_200_Front_1` on Pixel is not known to be the same book
as `_1` on iPhone — so there is no valid same-book cross-camera pair. This protocol fixes that by
tracking copy identity across the two phones.

---

## 1. Folders (new, kept separate from the unaligned set)

```
tests/SlabGuardTests/TruePositiveTest/PixelPhotos     <- phone 1
tests/SlabGuardTests/TruePositiveTest/iPhonePhotos    <- phone 2
```

## 2. What to shoot

- **Front cover only.** Backs are deprecated as a matching surface (same-issue back covers are
  frequently the identical mass-printed full-page ad — the matcher agrees on shared *print*, not
  shared *wear*, so backs can't discriminate copies).
- For each issue, photograph each physical copy's **front** on **both** phones.
- **THE ONE CRITICAL RULE — copy number ties a physical book across the two phones.**
  `Iron_Man_200_Front_1.jpg` (PixelPhotos) and `Iron_Man_200_Front_1.jpeg` (iPhonePhotos) **must be
  the same physical comic.** Work **one book at a time**: pick up book #1 → shoot on Pixel as
  `_Front_1` → shoot on iPhone as `_Front_1` → set it aside → next book is `_2`, etc. Do not batch
  by phone; batch by book, so the numbering can't drift.

## 3. Naming — `copynum` layout (the default mode)

```
<Issue_Name>_Front_<copyNumber>.<ext>
```

Exact issue spellings (copy-paste; must be identical in both folders):

```
Iron_Man_200
Heros_For_Hope
Marvel_Universe_1
Marvel_Universe_2
The_Invaders_41
Wolverine_And_The_Incredible_Hulk_1
```

`<ext>` = whatever the camera outputs (`.jpg/.jpeg/.png/.webp` all ingest; the two phones may
differ in extension — that's fine, only the stem is parsed).

## 4. Shot list

| Scope | Per issue | Pairs produced (front) | Notes |
|---|---|---|---|
| **Minimum viable** | 1 tracked copy | **6 cross-camera TP** | enough to report a TP rate |
| **Recommended** | 2+ tracked copies | **TP + cross-camera FP + same-phone FP** | a complete clean TP+FP matrix in one set; supersedes the unaligned top-level folders |

Use the copies you physically own (you already have up to 3 of Heros_For_Hope and
Wolverine_And_The_Incredible_Hulk_1). More tracked copies = more data points, no downside.

## 5. Run (copynum is the DEFAULT — no `--layout` needed)

```powershell
$env:ANTHROPIC_API_KEY = "<your key>"
python scripts/slabguard_crosscamera_test.py `
  --phone1 "C:/Users/mberr/CC/SW/tests/SlabGuardTests/TruePositiveTest/PixelPhotos" `
  --phone2 "C:/Users/mberr/CC/SW/tests/SlabGuardTests/TruePositiveTest/iPhonePhotos" `
  --side front `
  --csv "tests/SlabGuardTests/truepositive_results.csv"
```

Read the **TRUE-POSITIVE rate** line — want it high (every same-book cross-camera pair → `same_copy`).
If you shot ≥2 copies/issue, the two FALSE-POSITIVE lines (cross-camera + same-phone) also populate.
If the report prints `INVALID RUN — no Vision arbiter`, the API key isn't set — fix before trusting numbers.
Cost ≈ one Opus 4.8 call per pair (6 pairs minimum; a 2-copy full set ≈ 36 front calls).

## 6. Mechanics confirmed

`build_pairs` was verified against this exact layout: aligned numbering across the two folders yields
TP = `copyN/phone1` vs `copyN/phone2` (`expect=same_copy`); 1 copy/issue → 6 TP, 2 copies/issue →
12 TP + 12 cross-camera FP + 12 same-phone FP. No code change needed — the default `copynum` mode
already does this.
