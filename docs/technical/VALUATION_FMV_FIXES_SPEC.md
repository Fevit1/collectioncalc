# Valuation FMV Fixes — Spec (Fix A + Fix B)

**Status (updated 2026-07-10):** ⚰️ the "DRAFT — no code changed" framing below is HISTORICAL — **both fixes SHIPPED + verified in prod:** Fix A `c688bce`, Fix B `cecbaa5` (both 2026-06-27, S111). This doc remains the decision record for A/B (corpus proofs, scope decisions, backlog survey). **Companion narrative:** `docs/SW_NORMALIZATION_ARC_FOR_BS.md` — the plain-language summary of the whole normalization arc, including the LATER Cover-A/cross-title fix (`15cb459`, 2026-07-10) which is NOT specced here (its decision record lives in `docs/LAUNCH_READINESS.md` item 6). Keep status changes in LAUNCH_READINESS; this spec is frozen history plus the backlog table at the bottom.

**Original status:** DRAFT for review — no code changed. **Sequence:** spec A (this doc) → Mike review → build/ship A → then B. B is drafted here in parallel (independent of A's matching logic).
**Origin:** ASM #41 (first Rhino) ~10× undervaluation. Full diagnosis in `docs/sessions/WHERE_WE_LEFT_OFF.md` (Session 111, Valuation Diagnosis Tombstone).
**Date:** 2026-06-27.

---

## Problem recap (proven, read-only)

The actual logged lookup (`lookup_demand`) was title=`"The Amazing Spider-Man"`, issue 41, grade 6.0 → **comp_count=0, fmv_method=`estimated`, no_data=True**. The corpus stores `canonical_title="Amazing Spider-Man"` (no article). `title_matching.qualifier_title_clause` does a **normalized EXACT match** on `canonical_title`; the leading "The" breaks it and the substring-LIKE fallback can't recover it (column `"amazing spider man"` does not *contain* `"the amazing spider man"`). Zero comps → generic `grade_baselines` estimate (key-blind) → ~$47 → "probably not worth grading." Real 6.0 median ≈ **$550** (7 comps/365d) → correct verdict is "worth grading."

Two separable defects:
- **A — leading-article title-normalization bug** (narrow, wide blast radius).
- **B — structural: the slab verdict ignores the data-sufficiency signals the system already computes** (renders a confident verdict off a no-comp estimate).

---

## FIX A — Leading-article title normalization

### Rule
Strip a leading **`the `** from the normalized title on **BOTH** sides (query term AND `canonical_title`/like-columns), inside the two normalizers that the matcher already keeps in lockstep — `title_matching._norm()` (Python) and `title_matching._norm_sql()` (SQL). Symmetric stripping handles all four cases ("The X"↔"X", "X"↔"The X", "The X"↔"The X", "X"↔"X").

**Scope decision: strip `the` ONLY. Do NOT strip `a`/`an`** (evidence below: zero value today, small forward risk).

### Proposed code change (NOT applied — for review)
```python
# _norm(): append after existing normalization
n = re.sub(r'\s+', ' ', (s or '').replace('-', ' ')).strip().lower()
return re.sub(r'^the ', '', n)

# _norm_sql(): wrap the existing expression
base = r"regexp_replace(btrim(replace(lower(coalesce(%s,'')), '-', ' ')), '\s+', ' ', 'g')" % col
return r"regexp_replace(%s, '^the ', '')" % base
```
Both must change together (the module comment already mandates `_norm`/`_norm_sql` produce identical output). No call-site changes — every valuation/fmv query routes through `qualifier_title_clause`, which uses these two.

### Corpus before/after (read-only, `ebay_sales.canonical_title`, 14,033 distinct titles)

**Scope of change:** 1,031 titles lead with `the`; **5 lead with `a`, 1 with `an`.**

**Every merge stripping `the` creates is a correct SAME-SERIES unification — ZERO false merges across all 14,033 titles.** The collision scan (de-articled keys that unify ≥2 distinct normalized titles) returned **only `{X, "the X"}` pairs** — i.e. a title merging with its own article-variant. No two genuinely-different series collide. Representative rescues (currently split, would unify → full comp pool):

| Article form (rows) | Merges into (rows) |
|---|---|
| The Amazing Spider-Man (61) | Amazing Spider-Man (3,401) |
| The X-Men (66) | X-Men (807) |
| The Uncanny X-Men (10) | Uncanny X-Men (1,135) |
| The Incredible Hulk (21) | Incredible Hulk (1,033) |
| The Flash (123) | Flash (161) |
| The Walking Dead (47) | Walking Dead (188) |
| The Darkness (147) | Darkness (6) |
| The Avengers (9) | Avengers (254) |
| The Punisher (11) | Punisher (199) |
| The New Mutants (16) | New Mutants (648) |

**"Article-as-name" cases are SAFE** (Mike's explicit concern): "The Walking Dead"/"The Darkness"/"The Authority"/"The Defenders" each already exist in the corpus BOTH with and without the article, referring to the **same series** — so unifying them is correct, not a false merge. There is no *different* series named "Walking Dead"/"Darkness" without the article. Symmetric stripping also means a query of the article form still matches the article-form rows (no title is broken).

**Why NOT `a`/`an`:** only 6 titles lead with them and **zero** merge into an existing de-articled title — so stripping them rescues nothing today, while carrying a small forward risk (e.g. a future "A-Force" → "a force" → "force" could false-merge with a "Force" series). Net: no upside, nonzero risk → exclude. (The 6 are flagged for Mike's eyeball.)

### Out of scope (adjacent normalization gaps found — NOT this fix)
- **"Spiderman" vs "Spider-Man":** `"amazing spiderman"` and `"amazing spider man"` remain distinct keys (hyphen/spacing of "Spider-Man"), a separate normalization gap.
- **Missing connective "of":** `"department truth"` vs `"department of truth"` are distinct keys.
- **"Marvel's …" possessive prefix:** separate from articles; not addressed here.
These are real but independent; flag for a follow-up normalization pass, do not bundle into A.

### Verification plan for A (before ship, all read-only/offline)
1. Re-run the corpus collision scan post-rule → confirm still zero non-article false merges.
2. Re-run the candidate-title query for the 11 known "The…" titles → confirm each now retrieves its full comp pool.
3. Targeted ASM #41 offline check: title `"The Amazing Spider-Man"`, issue 41, grade 6.0 → expect 6.0 median ≈ $550, ROI positive, verdict "Worth grading."

---

## FIX B — Data-sufficiency verdict gating (draft for parallel review)

### Principle
Same lesson as the Slab Guard arc: **never let a low-confidence inference drive a confident product verdict.** When the FMV is an estimate / there are no real comps / confidence is `very_low`, the slab/no-slab verdict must **abstain or flag explicitly low-confidence**, regardless of the ROI sign. The signals already exist (`estimated`, `fmv_method`, `confidence`, `exact_count`); today the verdict block (`sales_valuation.py` ~500–519) ignores them.

### Gating (DRAFTED into `sales_valuation.py` — for review)
**Launch scope = the FABRICATION tier ONLY** (`estimated` / `estimated_from_raw` — graded FMV invented from baselines or raw×1.5, zero real graded comps, the ASM #41 class):
```python
estimated_flag = estimated or fmv_method in ('estimated', 'estimated_from_raw')
verdict_reliable = not estimated_flag
# in the ROI branch:
if not verdict_reliable:
    verdict = ('Not enough recent sales to value this reliably — '
               'rough estimate only, treat with caution')
elif slabbing_roi > 50:  verdict = 'Worth grading'
elif slabbing_roi > 0:   verdict = 'Marginal - consider volume'
else:                    verdict = 'Probably not worth grading'
```
`verdict_reliable` added to the JSON response so the **frontend renders the low-confidence verdict distinctly** (neutral/caution styling, not a confident green/red) — `app.html` `resultVerdictBadge`/`resultVerdictTagline` (companion frontend change, not yet drafted).

### RESOLVED — scope decision (was the open question)
Original proposal was `estimated OR very_low`. **Corrected to `estimated`-only** because `confidence=='very_low'` *always* sweeps in `exact_thin` (`exact_thin ⟹ total_graded<3 ⟹ very_low`), and Mike scoped exact_thin (1–2 real comps — thin-but-real, a different risk tier than fabricated) **POST-LAUNCH**. So launch gates fabrication only.
**⏰ POST-LAUNCH confidence-tuning (do not forget):** extend the gate to `very_low` (adds exact_thin + thin-interpolated). Tracked in-code with a ⏰ comment.

### Why B is still needed after A
A removes the article-bug *triggers* (flagships now retrieve real comps). B protects the **next genuinely sparse key** — a real no-comp book where `estimated` is the honest state — from shipping a confident wrong verdict. A fixes the known misses; B makes the fabrication failure mode safe by construction.

---

## VERIFICATION RESULTS (Fix A built + run, read-only, 2026-06-27)

1. **Normalizer lockstep:** `_norm("The Amazing Spider-Man") == _norm("Amazing Spider-Man") == "amazing spider man"`; `"Theater"`/`"Thee"` NOT stripped (requires trailing space). ✓
2. **Collision scan post-rule (shipped normalizer, all 14,033 titles):** 109 de-articled keys unify >1 prior key; **FALSE MERGES = 0** — every introduced merge is `{X, "the X"}`. ✓
3. **Flagship rescue (graded comps/365d, updated clause):** The Amazing Spider-Man **1230**, The X-Men 436, The Incredible Hulk 377, The Uncanny X-Men 193, The Punisher 186, The New Mutants 255, The Avengers 81, The Flash 72, The Walking Dead 59, The Invincible Iron Man 47, The Defenders 14 (all previously exact-match-missing). ✓
4. **ASM #41 end-to-end** (title=`"The Amazing Spider-Man"`, issue 41, grade 6.0): graded 6.0 median **$550** (7 comps), raw median $250, ROI **+$255 → "Worth grading"**, `verdict_reliable=True`. The exact failing input now produces the correct verdict. ✓

## REMAINING TITLE-MATCHING BACKLOG (the "size the rest" survey)
Of **64** distinct `lookup_demand` no-data/estimated lookup titles, after Fix A's de-articling:
| Bucket | Count | Examples |
|---|---|---|
| matches at title level (article-rescued or already-matching) | 25 | the avengers, fantastic four, tomb of dracula |
| spacing/hyphen (e.g. Spiderman vs Spider-Man) | **0** | — (exists in corpus, no lookup hit it yet) |
| possessive ("'s" / Marvel's) | **0** | — |
| connective/token (missing word, vol/roman-numeral) | 5 | teenage mutant ninja turtles iii, marvel knights spider-man, weird war tales |
| partial/subtitle/colon/accent | 9 | pokémon: the first movie, batman beyond: return of the joker, dark horse presents: black cross |
| genuinely absent / junk | 25 | auction #176, auction #177, infinity inc., unknown - skull/horror themed, raccolta super-eroi (foreign) |

**Shape of what's left:** the article class was the dominant title-matching bug; the remaining *normalization* backlog is **small (~14 titles** across subtitle/colon, accent, roman-numeral/volume, token-order) and the **~25 "absent" are mostly junk** (auction noise, foreign, unidentifiable) — genuine no-data, not matching-fixable. Spacing/hyphen + possessive classes exist in the corpus but **no lookup has hit them yet** (lookup_demand is small early-beta traffic — treat as a shape indicator, not exhaustive). Net: Fix A clears the big one; a *small* long-tail normalization pass (colon/subtitle + accent + token-order) is the next title-matching increment, post-launch.
