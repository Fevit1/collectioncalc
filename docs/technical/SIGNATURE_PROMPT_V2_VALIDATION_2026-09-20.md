# Signature prompt version 2 — before / after, 2026-09-20

Report only. "Before" = prompt v1, run 2 of 2026-09-19 (all 97, already paid). "After" = prompt v2, today:
`scripts/sig_cv_results_v2_2026-09-20.jsonl`. Same harness (`scripts/sig_cv_harness.py`, production functions
imported), same pools, same held-out images, one pass per query, no comic context.

## What ran
- **72 PRESENT queries** — the signer is among the 14 candidates. Every third creator skipped, but all 17 of v1's
  misses and soft-band creators kept.
- **14 ABSENT queries** — 2 per pool: a real held-out signature whose owner is NOT among the candidates (taken from
  the next pool, so the cached reference block is unchanged). The case v1 could not express and (2) could not see.
- **Cost: $4.12 measured** (estimate $4.55, −9.5%). 86 calls; input 40,363 · cache write 134,586 · cache read
  1,514,640 · output 92,716. Median output 1,068 tokens — v2's three new fields cost ~30 tokens a call.

## Result
| | prompt v1 (same 72 creators) | prompt v2 |
|---|---|---|
| Top-1 correct, signer present | 70 / 72 | **69 / 72 (95.8%)** |
| Misses | Liefeld→Jim Lee, Ennis→Alex Ross | the same two **+ John Byrne→George Pérez (0.68, margin 0.13)** |
| Sum of the five scores | 1.00 in every call | **1.15 – 2.27** (median 1.48): the scores are independent now |
| Top score when correct (median) | 0.85 | **0.90**; `none_of_these` median **0.05** |
| v1's soft band (17 creators under 0.60) | — | 12 of the 14 still-correct ones scored HIGHER (e.g. Pérez 0.55 → 0.82, Dell'Otto 0.55 → 0.78, Hickman 0.50 → 0.72) |

One extra miss in 72 single-pass queries is inside run-to-run noise; v2 did not buy accuracy and was not meant to.
It bought the two things v1 could not give:

**The absent signer (14 queries):** top score median **0.20** (v1 would have forced ~0.25–0.60 onto someone);
`none_of_these` median **0.86**; the model named the TRUE signer outright in **5 of 14** (Bendis, Gleason, Ottley,
Siegel, Ditko — it read the signature) and offered some name in 8. Two were confidently wrong: **Jim Lee read as Jim
Starlin (0.72, margin 0.37, none 0.25)** and **Leinil Yu as Bendis (0.72 / 0.32 / 0.25)**. Jim Lee vs Jim Starlin
is the confusion pair the v1 prompt's own notes already warned about.
**Found on the way:** the model sometimes wrote the name it READ into `rankings` at a token score although that
creator was not a candidate ("Ryan Ottley 0.05"). The route now drops any ranked name that is not in the pool; an
outside name belongs in `suggested_outside_pool`.

## Floor rule — values SET from this run
A creator is named only when all three hold (`passes_floor_rule`, the one decision point for the page, the Guard cap
and the harness):

| rule | present: named (correct / wrong) | absent: wrongly named |
|---|---|---|
| v1 behaviour: top ≥ 0.50 | 71 of 72 (68 / **3**) | **4** of 14 |
| starting point: ≥ 0.70, margin ≥ 0.30, none < 0.50 | 61 (60 / **1**) | **2** of 14 |
| **≥ 0.75, margin ≥ 0.40, none_of_these < 0.50** ← SET | **56 of 72 (56 / 0)** | **0 of 14** |
| ≥ 0.85, margin ≥ 0.50, none < 0.40 | 48 (48 / 0) | 0 |

**`SIG_MATCH_FLOOR=0.75`, `SIG_MATCH_MARGIN=0.40`, `SIG_NONE_OF_THESE_CEILING=0.50`** — the loosest setting with no
wrong name in either set. It names 78% of present signers; the other 22% get the honest no-confident-match block,
which now leads with "Closest resemblance: X — not among the creators we compared" when the model offers a name.
Env-overridable, so a retune is not a code deploy. ⚠️ Fitted to 86 single-pass queries on clean crops with 14
candidates. Production runs three passes and averages, which steadies the score. **(3) on Monday is the real test
and the values are re-set from it.** `none_of_these` did not bind at this setting (the score and margin terms did
the work) — it is kept because its failure mode is the dangerous one: a high score beside a model that doubts the pool.

## What ships with it
Prompt file (new, versioned; v1 untouched; `SIG_PROMPT_VERSION=1` rolls back by env var) · route: no
renormalisation under v2, the floor rule, non-candidate names dropped, labels "strong / close / partial / weak
match" instead of "high / medium / low / speculative", the response and the logged flags carry `score_kind`,
`prompt_version`, `margin`, `none_of_these`, `suggested_outside_pool` · page: no percentage and no "high"; the badge
reads "Stan Lee · signature match"; the result block reads "Match score 0.88 of 1 · next closest 0.04" and "A match
to our reference signatures, not authentication".
