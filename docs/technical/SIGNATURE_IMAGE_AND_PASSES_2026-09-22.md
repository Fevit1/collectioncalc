# Signature matcher — the image lever, and one pass against three — 2026-09-22

Report only. Harness `scripts/sig_t4_harness.py` (production functions; prompt v2; the (2) split); results
`scripts/sig_t4_image_2026-09-22.jsonl`, `scripts/sig_t4_passes_2026-09-22.jsonl`. 42 creators = pools 0–2 of (2)
(creators sorted by career start; the signer is always among the 14 candidates; the target is the creator's
held-out reference image, a clean crop). **$6.37 measured** (arm 1 $3.14 est. $3.05; arm 2 $3.23 est. $2.80 — the
second arm's output ran longer than the first's).

## Arm 1 — the image lever: full resolution vs an 80-px thumbnail signature
The same 42 held-out signatures, one pass each, at full resolution (long edge median ~875 px) and downscaled so the
long edge is 80 px — the size a signature has on the 375 × 500 listing thumbnails (3) was scored on.

| | full resolution | 80-px thumbnail |
|---|---|---|
| top-1 correct | 41 / 42 (98%) | 32 / 42 (76%) |
| **named at the floor (0.75 / 0.40 / 0.50)** | **35 (83%)** | **29 (69%)** |
| named and correct | 35 | 28 |
| **named and WRONG** | **0** | **1** — Herb Trimpe read as Stan Lee at 0.88, margin 0.66 |
| median score | 0.93 | 0.88 |
| `poor_image_quality` flagged | 10 | 37 |
| same top-1 as full | — | 31 / 42 |

Six signers named at full resolution lose their name at thumbnail size; none gain one.
**What it says.** (3) named 30% of eBay rows; the same matcher on a full-resolution crop names **83%**. The share a
user's own photo would get is closer to the second figure than the first, on the two conditions that hold here and
did not in (3): the signer is in the pool, and the target is a crop, not a whole cover. **And the floor is not
enough on its own at thumbnail size:** the one wrong name of the whole programme on a clean crop appeared at 0.88
with a 0.66 margin — the model was as sure as it is when right. (3)'s 100% precision leaned partly on the model
refusing to be sure at that size; make the image good and the refusals go away in both directions. The lever to
pull is the INPUT: crop to the signature (or ask the user for a close photo of it) before matching, and treat a
target under ~150 px on its long edge as "can't tell from this photo" regardless of score.

## Arm 2 — one pass against three
Two more full-resolution passes on the same 42 (labels 0.5 and 0.7), aggregated with arm 1's full pass by
production `aggregate_passes`, exactly as the route does.

| | one pass | three passes |
|---|---|---|
| top-1 correct | 41 / 42 | 41 / 42 |
| top-1 agreement | — | **42 / 42 (100%)** |
| named at the floor | 35 | 35 |
| named and correct / wrong | 35 / 0 | 35 / 0 |
| floor decision identical | — | **42 / 42** |

**Passes 2 and 3 changed nothing on this set** — not one top-1, not one floor decision. With `temperature` gone
(Opus 4.8 rejects it) the three passes are three samples of the same distribution, and on a clean target that
distribution is tight: Saturday's 37 repeated queries agreed 37 / 37 too. Where the passes could still earn their
cost is the soft case — a marginal target where the single pass lands near the floor — and this set has few of
those (the one miss, Rob Liefeld, missed all three times). Not measured here: three passes on THUMBNAIL targets,
which is where the variance would be.

## The numbers for the pricing decision (Mike's two shapes)
| configuration | cost per identification | basis |
|---|---|---|
| three passes, cache breakpoint (deployed today) | **$0.263** | measured in production, log row 20 |
| three passes, uncached | $0.439 | same call, arithmetic |
| **one pass** | **$0.174** | pass 1 of row 20 (it pays the cache write; with no later pass to read it, the write is wasted — $0.15 without the breakpoint) |
One pass gives the same answer as three on 42 of 42 here at 57–66% of the cost. **Recommendation, Mike's call:**
ship ONE pass with the breakpoint OFF (~$0.15), and re-run three only when the single pass lands inside a band
around the floor (say 0.65–0.80) — that keeps the ensemble where it might matter and pays for it on the minority of
books. At ~$0.15, a Pro cap of 5 a month costs $0.75 against $4.99; at $0.26, $1.32. A per-use credit at $0.99
clears either cost several times over.

## Caveats
Clean crops, signer always in the pool, 42 creators from the earliest three pools (Siegel through the 1980s — the
older, more distinctive hands). Not raw covers, not the pool-miss case, not thumbnails under three passes.
