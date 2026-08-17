# Slab Guard — True-Positive (Recovery Sensitivity) Reshoot Protocol

**Purpose:** measure the one number still missing — **recovery sensitivity (true-positive rate)**:
the *same physical comic* photographed on *two different phones* must match (`same_copy`).
The cross-camera **false-positive** rate is already locked at **0/12** (front covers, three runs).
TP is the gating item before any positive "we can recover your stolen comic" claim.

> **GRADE CEILING — read before interpreting any TP number.** Copy discrimination is
> **wear-carried** (the vision arbiter matches copy-unique physical defects; print only
> establishes same-issue — see the Session 110 architecture finding). So sensitivity is
> **structurally weakest on high-grade / low-wear books** — little wear = little copy-unique
> signal, and every layer then defaults toward `different_copy`/`uncertain` (a **false
> negative / missed match**, not a false positive — the FP=0 result holds across all grades).
> **A clean TP on worn books does NOT generalize to mint.** Grade stratification (§7) is
> REQUIRED, and TP numbers must not be interpreted until the grade of each shot copy is noted.

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

## 7. Grade stratification — REQUIRED before any sensitivity claim

Because discrimination is wear-carried, a TP rate is only meaningful **per wear band**. Report the
TP rate stratified by grade, not as a single blended number, and ensure the set spans the range:

- **At least one deliberately HIGH-GRADE / low-wear RAW copy** (target NM-ish, ~9.0+, or the
  cleanest raw book you own), shot on both cameras. **This is the decisive sensitivity test** — it
  probes the band where wear-matching is weakest and where the high-value stolen books actually sit.
  A `same_copy` here is the result that would justify a recovery-sensitivity claim for raw books.
- A mid-grade copy (moderate, well-distributed wear) — the band where photo-matching is strongest.
- A heavily worn copy — the easy case (abundant copy-unique defects); a near-floor on difficulty.

If the high-grade copy comes back `different_copy`/`uncertain` while worn copies match, that is the
**grade ceiling made visible** — and it confirms the routing in §9, it does not invalidate the system.

> Slabbed / mint books are intentionally **out of scope for photo-matching** — they route to
> cert-number recovery (§9). Do not shoot slabs for this test; use the cleanest **raw** copy.

## 8. Grades of the books already shot (this TP run) — Mike to confirm actual grades

Provisional **visual wear read** from the front-cover photos only (NOT a grade; confirm/replace with
the real CGC or observed grade). Captured so the first TP numbers can be read in context:

| Issue | Provisional wear (front only) | Mike's actual grade |
|---|---|---|
| Wolverine_And_The_Incredible_Hulk_1 | **Low** — clean, glossy, sharp corners (weakest wear signal → hardest TP case in this set) | _____ |
| Iron_Man_200 | Low–moderate — clean, glossy, sharp | _____ |
| Heros_For_Hope | Low–moderate — clean, glossy | _____ |
| Marvel_Universe_2 | Low–moderate — fairly clean, minor edge/spine wear, slight tan | _____ |
| Marvel_Universe_1 | Moderate — visible spine stress/crease near top, surface wear | _____ |
| The_Invaders_41 | **Heavy** — edge wear, spine stress, corner wear, tanning, edge chips (strongest wear signal → easiest TP case) | _____ |

**Interpretation caveat:** none of these 6 is slabbed/mint and there is **no decisive high-grade
copy** in the set, so even a clean 6/6 on this run does **not** establish sensitivity for high-grade
books. It would establish sensitivity for **raw books with at least some wear** — which is the
correct, claimable scope (see §9). Add the high-grade copy from §7 before extending the claim upward.

## 9. Routing — what a TP result does and doesn't license

The wear-carried architecture means recovery should be **routed by book type**, and the market aligns:

- **Slabbed / high-grade → cert-number recovery** (wear-independent). The CGC/CBCS cert is already
  OCR'd, stored and indexed at grading; it just needs the lookup wired. This is the recovery path for
  the high-value books photo-matching is weakest on.
- **Raw / mid-grade with genuine wear → wear-based photo matching** (this harness's path), where the
  copy-unique wear signal is strong.

A passing TP on this set licenses a recovery-sensitivity claim **scoped to raw books with real wear** —
not slabbed, not mint. Slabbed recovery rides the cert path, not photo-matching.
