# Signature matcher — external test (3), 2026-09-21

Report only. Harness `scripts/sig_t3_harness.py`; sample `scripts/sig_t3_sample_2026-09-21.json`; results
`scripts/sig_t3_results_2026-09-21.jsonl`. **$6.24 measured** (estimate $6.62, −5.7%; worst case was $7.52).

## What ran
87 signed CGC/CBCS eBay rows from the HELD-OUT fold (`ebay_sales.id % 5 = 0` — the priors never saw them), R2 images
only, no request to eBay. The request is the deployed route's own: production Design A pool from the row's
publisher / era / title, production reference fetch and message builder, prompt v2, same model and token cap; the
response parsed by production `run_single_pass` and decided by production `passes_floor_rule`. ONE pass per row,
through the Message Batches API (same request, asynchronous, half price — 87 rows made 56 distinct pools, so caching
would have saved little and a synchronous run was ~$19). 87 of 87 succeeded; 1 response was unparseable JSON (Erik
Larsen) and is excluded → **86 scored**.
**Labels:** 79 rows name exactly one in-set creator beside a signing cue in the title. 7 rows were sampled as "signed
by a name NOT in the set" — on reading them, only **4** truly are (Hugh Jackman, Howard Chaykin, Dale Keown / Tom
DeFalco, Chris Bachalo); 3 were my sampler's misreads of in-set signers ("MCFARLANE.", "Snyder Signature Series",
"George Perez" without the accent). The corrected figures are used below and the raw ones are in the results file.

## Against the bar — top-1 accuracy ≥ 75% among NAMED matches, score line visible
| | |
|---|---|
| **Named at the current floor (0.75 / 0.40 / 0.50)** | **26 of 86 — 30%** |
| **Correct among named** | **26 of 26 — 100%** (one-sided 95% lower bound ≈ 89%) |
| Wrong creator named | 0 |
| Out-of-set signer wrongly named | 0 of 4 |
| **The bar** | **CLEARED on precision.** The pricing gate is separate and still stands. |

⚠️ **Three of the 26 read the slab label, not the signature** — their notes say so ("CGC Signature Series label
explicitly states signed by Adam Kubert"; likewise Eastman, Bendis). The top 15% of every image was cropped to
prevent exactly that; on loosely framed photos the label sits lower. Two more leaned on a printed cover credit (Dan
Mora, Skottie Young). Excluding all five: **21 of 21**. The conclusion does not move, but the 100% is partly OCR on
this population, and a raw signed book — the product's real case — has no label to read.

## Floor-rule outcomes (corrected labels)
| rule | named | correct | wrong | precision |
|---|---|---|---|---|
| v1 behaviour: score ≥ 0.50 | 55 (64%) | 50 | 5 | 91% |
| ≥ 0.60, margin ≥ 0.20, none < 0.50 | 43 (50%) | 40 | 3 | 93% |
| Saturday's starting point: ≥ 0.70, margin ≥ 0.30 | 40 (47%) | 38 | 2 | 95% |
| **current: ≥ 0.75, margin ≥ 0.40, none < 0.50** | **26 (30%)** | **26** | **0** | **100%** |
| ≥ 0.80, margin ≥ 0.40, none < 0.40 | 25 (29%) | 25 | 0 | 100% |
| ≥ 0.85, margin ≥ 0.50, none < 0.40 | 17 (20%) | 17 | 0 | 100% |

**Every setting clears 75%.** The two wrong names at 0.70 / 0.30 both scored **0.72** — Andy Kubert read as Chris
Claremont (0.72, margin 0.42) and a Ryan Stegman book read as Donny Cates (0.72, 0.47; Stegman has one reference
image and can never be a candidate). Saturday's two confident-wrong absent cases were ALSO at 0.72. Two independent
sets put the wrong answers in the same 0.70–0.72 cluster, just under the floor. **Recommendation: keep 0.75 / 0.40 /
0.50.** It is no longer fitted to one set; moving to 0.70 buys 14 more names and admits that cluster. Mike's call.

## The share that gets a name at all: 30% — and why
| | rows |
|---|---|
| named, correct | 26 |
| **no match — poor image quality flagged** | **37** — and in **33 of those 37 the RIGHT creator was on top**, below the floor |
| no match — signer not in the 15-candidate pool | 11 — the model named the true signer as `suggested_outside_pool` in **6 of 11** |
| no match — right creator on top, below the floor | 4 |
| no match — wrong creator on top, below the floor | 1 |
| signer not in the set — correctly not named | 4 (+3 sampler misreads, none named) |
| wrong creator named | **0** |
| second signature flagged | 11 rows (3 named; the right creator on top in 9) |

Top-1 regardless of the floor: **63 of 79 in-set (80%)**; with the signer in the pool, **63 of 68 (93%)** — in line
with Saturday's 96–98% on clean crops. **The matcher is not the constraint. The photo is.** `poor_image_quality`
was flagged on 62 of 86 rows: most R2 copies are 375 × 500 listing thumbnails of a whole slab, the signature a few
dozen pixels wide. The model picks the right creator and then, correctly, refuses to be sure.
- **Biggest lever — the input image, not the floor:** 33 rows are right-but-unsure on a thumbnail. A user's own
  photo of a cover is several times this resolution; a crop-to-signature step before matching would raise the score
  without touching the rule. This test UNDERSTATES the share a real user would see, and cannot say by how much.
- **Second lever — the pool:** 11 of 79 signers were not among the 15 (40% of this sample has no `title_year`, so no
  era filter). The model volunteered the right name in 6 of those 11 — that is Design B's trigger (add the suggested
  name and run again), worth roughly half the pool misses.
- **Second signatures** were detected, not resolved: the matcher still compares one target.

## What this does and does not establish
It establishes that under prompt v2 and the floor rule, **a name shown to the user is right** on real listing
photos, and that an out-of-set signer is not named. It does NOT establish the share of real users' books that get a
name (thumbnails), behaviour on RAW signed books (no slab, no label, the actual product case), or three-pass
behaviour (production averages three passes; this was one). Sample: eBay's signed-slab population, 39 signers,
capped at six rows each.

## Cost
86 scored + 1 unparseable = 87 billed calls: average 23,014 input and 1,134 output tokens; **$6.24 at the batch rate**
($0.072 a row). The same 87 rows synchronously, uncached, would have been ~$12.50.
