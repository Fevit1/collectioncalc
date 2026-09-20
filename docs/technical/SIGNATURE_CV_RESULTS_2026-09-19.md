# Signature matcher — cross-validation (2), 2026-09-19

Report only. Harness: `scripts/sig_cv_harness.py` (imports the production functions; adds the held-out candidate
list, a cache breakpoint after the reference block, and `response.usage`). Raw results:
`scripts/sig_cv_results_2026-09-19.jsonl` (rows without `raw` are run 1).

## The split
97 creators with ≥ 3 reference images. Held out: each creator's LAST image in the route's own order. References: the
rest (≤ 4; 3 for most). One query per creator, ONE pass, no comic context. Creators sorted by `career_start` into
seven fixed pools (14 × 6 + 13); every query in a pool sees the same candidates, and the true signer is always among
them. Not tested: Whilce Portacio (0 images), Ryan Stegman (1), Warren Ellis (1).

## Result
| | |
|---|---|
| **Top-1 accuracy** | **95 / 97 = 97.9%** |
| Misses | Rob Liefeld → Jim Lee (0.60, truth 0.18); Garth Ennis → Alex Ross (0.55, truth 0.20) |
| Per pool | 14/14, 14/14, 13/14, 13/14, 14/14, 14/14, 13/13 |
| Run-to-run (37 queries run twice) | same top-1 in **37 / 37**; score moved by a median 0.000, max 0.110 |
| Top-1 score when correct | min 0.40 / median 0.85 / max 0.95; margin over #2: 0.18 / 0.80 / 0.93 |
| Top-1 score when wrong | 0.55 and 0.60; margins 0.35 and 0.42 |

"Top ten confusion pairs" does not exist at this accuracy: there are two confusions, each seen once. The soft spot is
not pairs but a band — **15 correct answers scored below 0.60** (Claremont 0.44, Morrison 0.44, Geoff Johns 0.42,
Jason Aaron 0.42, Jenny Frison 0.40, Hickman 0.50, Jae Lee 0.50, and eight at 0.55), the same band both misses sit
in. Writers' signatures are over-represented there.

## ⚠️ There is no raw score. Mike's scoring rule cannot be applied as written
Mike ruled that (2) and (3) be scored on the model's raw per-candidate score, with the normalised share as display
only. Run 2 recorded every score exactly as the model returned it, and **the five scores sum to 1.00 in 97 of 97
calls; raw and share are identical to the third decimal.** The cause is the prompt, not the aggregation:
`prompts/signature_identification_system.md:85` — *"The 'rankings' array MUST contain exactly 5 entries. Confidence
scores across all 5 MUST sum to 1.0."* The model is instructed to hand back a distribution over five names. The
route's renormalisation is a no-op on a single pass. So:
- The score was never a confidence. It answers "of these five, how is my belief split", never "is it any of them".
- The prompt has **no "none of these" outcome**. When the signer is absent the mass still has to go somewhere:
  rows 16 and 17 (Stan Lee absent) gave 0.24 / 0.26 to John Romita Sr. — a near-even five-way split. That is the
  only signal of absence the design has, and it is accidental.
- (2) cannot see this failure, because in (2) the signer is always present. It is what (3) will measure.

## What (2) does and does not show
It is an UPPER bound: signer guaranteed in the pool, 14 candidates not 15, a clean reference-style crop as the
target, no cover art, no second signature, one reference fewer per creator than production. It shows that
**discrimination is not the problem** — given the right pool and a legible signature, the matcher is right 98% of the
time and stable across runs. With pool recall at ~94.5% on the held-out fold, the product of the two (~92%) clears
the 87% bar ON PAPER; the gap between that and real covers is what (3) exists to measure.

## Floor rule — proposal (after (2), as asked)
Numbers on this set, naming a creator only when the rule passes:

| rule | names | correct | wrong |
|---|---|---|---|
| today: top-1 ≥ 0.50 | 92 / 97 (95%) | 90 | **2** |
| top-1 ≥ 0.60 and margin ≥ 0.20 | 81 (84%) | 80 | 1 |
| **top-1 ≥ 0.70 and margin ≥ 0.30** | **76 (78%)** | **76** | **0** |
| top-1 ≥ 0.80 and margin ≥ 0.40 | 60 (62%) | 60 | 0 |

**Proposed: name a creator only at top-1 ≥ 0.70 AND margin ≥ 0.30; otherwise the no-confident-match note.** Both
misses and the whole soft band fall below it; it costs 19 correct names in 97 on this set. The margin term is what
makes the share usable: a share of 0.70 with 0.30 clear of second place cannot be produced by an even split. Hold
the exact numbers until (3) — (2) has only two wrong answers to fit against, and they are clean crops.
**The real fix is the prompt, versioned (L-2026-006):** ask for an independent 0–1 match score per candidate
(not summing to anything) plus an explicit `none_of_these` score, and a `suggested_outside_pool` name. Then "raw
score" exists, absence is a first-class answer, and Design B has its trigger. That is a prompt change with its own
before/after run (~$4.50), not a threshold tweak.
**Badge copy, scoped with it:** drop "high / moderate / speculative" and the bare percentage. Until the score means
confidence: "Matches our Stan Lee references" + "Not authentication — for that, CGC Signature Series or CBCS", with
the number, if shown at all, labelled "share of the five closest candidates". Files: `js/utils.js`
(`displaySignatureV2Results`, the matched branch), the saved badge renderer in `js/collection.js`, and
`_confidence_label` in the route (it writes "high" into `signature_data`).

## Cost — measured
| run | calls | cost | note |
|---|---|---|---|
| 1 (stopped at 37; share only) | 37 | **$1.52** | not scorable under the raw rule; kept as the variance sample |
| 2 (all 97, scores as returned) | 97 | **$4.45** | in 43,794 · cache write 131,002 · cache read 1,681,942 · out 102,781 |
| **(2) total** | 134 | **$5.96** | estimate $5.70 (+4.6%); the overrun is the restart |

Per query, cached: **$0.046**. Output median 1,037 tokens (assumed 1,000). 16 s per query. Caching cut the input
bill by ~85%: uncached, run 2's input alone would have been ~$9.3.
**What this says about production:** the same breakpoint in `build_identification_messages` would take a 3-pass
identification from ~$0.66 to roughly $0.35–0.45 (passes 2 and 3 read the prefix at 0.1×). Separate unit.
