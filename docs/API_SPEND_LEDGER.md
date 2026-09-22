# Anthropic API Spend Ledger

Durable running total for the **$10/day aggregate ceiling** (CLAUDE.md →
*Mandatory: API Spend Ceiling*, effective 2026-08-14).

**Scope:** Anthropic API spend Claude *initiates* — vision samples, backfills,
sweeps, batch jobs. **Excludes** the app's normal per-request grading cost
(user-driven, not a run Claude chooses to start).

## How to use this file

- **Append a row BEFORE the run**, with the estimate. Never after.
- **Correct the row AFTER**, with the actual from `response.usage`
  (`input_tokens + cache_creation_input_tokens + cache_read_input_tokens`,
  `output_tokens`). Estimate-vs-actual drift is the calibration signal — keep
  both columns, do not overwrite the estimate.
- **Report the running total with every estimate**, in the form:
  *"This run is $1.39, today's total is $2.75."*
- A run that would push the day's total over **$10.00** needs Mike's written
  permission **before it starts**.

Rates used (Sonnet 5, from the claude-api reference): $3.00/$15.00 per MTok
standard; **intro $2.00/$10.00 through 2026-08-31**; Batch API −50%; cache
write 1.25× (5m TTL), cache read 0.10×. Minimum cacheable prefix 1,024 tokens.

---

## 2026-08-14 — running total: **$1.40** (standard) / **$0.94** (intro rate billed)

| # | run | est. | actual | notes |
|---|-----|------|--------|-------|
| 1 | CP-1 smoke test — 1 scoring call | ~$0.01 | $0.007 | Pre-flight before firing 300; caught nothing, which is the point. |
| 2 | CP-1 paired vision sample — 100 books × {s-l500, s-l800, s-l1600} = 300 calls | **$1.390** | **$1.397** | **+0.5%.** 300/300 succeeded. Approved by Mike in advance. |

**Totals:** 301 calls · input 339,510 · cache_write 0 · cache_read 541,500 ·
output 14,405. **$1.397 at standard $3/$15; $0.931 at the intro $2/$10 that
actually applies through 2026-08-31.**

### Estimate calibration — the reason both columns exist

- **Estimate $1.390 → actual $1.397. Off by 0.5%.** The measured-token method
  (real image dimensions, `count_tokens` on the rubric) works.
- ⚠️ **A mid-run "correction" to ~$1.55 was WRONG and the original estimate was
  right.** It was extrapolated from 4 probe images rather than the 100 actually
  sampled. Lesson: do not re-estimate from a smaller sample than the one already
  in hand — the correction was less grounded than the thing it corrected.
- Output ran **48.0 tokens/call vs the 45 specified** (+6.7%). `output_config.format`
  held the shape; the drift is basis-string length, not preamble.
- **Caching worked and was verified, not assumed:** rubric measured at 1,471
  tokens (floor is 1,024 — a pre-flight abort was wired in case it came up
  short), `cache_read_input_tokens` = 541,500 across the run, `cache_write` = 0
  because the smoke test had already warmed it. Without caching this run would
  have cost ~$3.7 instead of $1.4.

**Non-API cost on the same run:** 200 live GETs to `i.ebayimg.com` outside the
capture path — approved in advance as a deliberate one-off, paced as Poisson
arrivals (mean 17s, clamped [4s, 70s]) over 56.0 min. 200/200 succeeded at the
requested size; the `_upsize_ebay_image_url` fallback never fired and remains
untested against a real 404. See CLAUDE.md → *eBay Capture Safety*.

---

## Estimate basis for the CP-1 sample (so the actual can be graded against it)

Per-call, measured not modelled:

| component | tokens | source |
|---|---|---|
| image @ s-l500 | 245 | measured, 30 real covers, all exactly 500px long edge |
| image @ s-l800 | 640 | measured, 4 real covers via CDN size-token rewrite |
| image @ s-l1600 | 2,560 | measured, same 4 covers; s-l2400 returns an identical file |
| row text (title + price) | 60 | estimated |
| rubric, cache read | 120 | 1,200-token rubric × 0.10 |
| output (schema-constrained) | 45 | `{band, conf, basis<=12w}` via `output_config.format` |

Total ≈ **$1.39** at standard rates, no batch (the sample is interactive).

⚠️ Two settings this estimate depends on — both silent if wrong:
- `thinking: {"type": "disabled"}` — adaptive thinking is **ON by omission** on
  Sonnet 5 (inverted from 4.6) and bills at output rates.
- `output_config: {"effort": "low"}` — the default is `high`.

Assert `cache_read_input_tokens > 0` on the first calls: a silent cache miss is
a 2.7× cost event, and a rubric under 1,024 tokens does not cache at all.

---

## 2026-08-30 — running total: **$3.49** (standard rates) · est. before runs 2-4

**Scope note:** in-scope. The re-grade harness is a Claude-initiated sweep, not
user-driven grading — Mike chooses to start it and it re-grades retained photos
against rubric variants. Purpose: establish the noise floor and measure whether
passing publication year to the prompt breaks the 9.0 grading ceiling.

| # | run | est. | actual | notes |
|---|-----|------|--------|-------|
| 3 | Re-grade harness smoke test — 3 books, variant baseline | ~$0.100 | **$0.094** | −6%. Pipeline proof before spending on the full set. All 3 grades identical to stored; defect flags moved. |
| 4 | Re-grade harness — 36 books, variant baseline (run 1 of 2) | **$1.132** | | Noise floor, first half. |
| 5 | Re-grade harness — 36 books, variant baseline (run 2 of 2) | **$1.132** | | Noise floor, second half. Run 4 vs run 5 **is** the measurement. |
| 6 | Re-grade harness — 36 books, variant A (year passed to prompt) | **$1.132** | | Read only against the run-4/run-5 delta. Primary question: does any book cross 9.0? |

**Estimated session total: $3.49** at standard $3/$15. Under the $10 ceiling, so
no written permission needed. Model: `claude-sonnet-4-6`, temperature 0.

⚠️ **Rate question, unresolved:** the header records an intro rate of $2/$10
through 2026-08-31, attributed to Sonnet 5. These runs are on
`claude-sonnet-4-6`. If the intro rate applies here, the session is ~$2.33
rather than $3.49. Recorded at standard rates because assuming the discount
would understate the ceiling. Verify against the actual invoice.

### Estimate calibration — the smoke test already moved the number

- **Frodo's basis was 7,100 input tokens per 4-photo book. Actual: 6,207. The
  estimate ran 12.6% high.** Output was 855 against a basis of 850, within 1%.
- The per-run figure was therefore revised **$1.22 → $1.132** before spending
  anything, and the three-run total from $3.66 to $3.40. The smoke test paid for
  itself in estimate accuracy before it proved the pipeline.
- Consistent with the 2026-08-14 lesson in reverse: re-estimating from a *larger*
  in-hand sample is exactly when a correction is warranted. The CP-1 mistake was
  re-estimating from a smaller one.

---

## 2026-09-18 — running total: **~$0.66** (probe $0.0002 actual + proof call ~$0.66 est., usage not captured) · Opus 4.8 at $5 / $25 per MTok

**Housekeeping:** this file was found UTF-16LE in the working tree (git saw it as binary, 4,389 → 13,430
bytes; a PowerShell redirect is the likely cause). Converted back to UTF-8 / LF on Mike's go, content
unchanged: HEAD's text is a byte-for-byte prefix of the decoded file, and the 2026-08-30 section above is
the only addition it carried. ⚠️ Runs 4–6 of 2026-08-30 still have no actuals recorded.

| # | run | est. | actual | notes |
|---|-----|------|--------|-------|
| 7 | Signature matcher probe — 1 text-only call to `claude-opus-4-8` with `temperature=0.2`, `max_tokens=5` | ~$0.0001 | **$0.0002** | **RESULT: 400 — "`temperature` is deprecated for this model."** Control without the parameter → 200 (16 in / 4 out, the only billed call). Does the model the v2 matcher calls accept the parameter the matcher sends? A 400 costs nothing. Approved by Mike 2026-09-18. |
| 8 | Signature matcher post-deploy proof — ONE real POST to `/api/signatures/v2/match` (3 passes × ~38.9k input, uncached, known reference image as target) | **$0.66** ($0.70 worst case) | **~$0.66, NOT MEASURED** | **RAN 2026-09-19 03:28:45Z as Mike's second "ID Sigs" click (ASM #252) — `signature_identification_log` row 16, 3 passes, 71.4 s, 200.** The route does not store `response.usage`, so there is no actual; the estimate stands as the charge until the Anthropic console is read. The first click (old build) was six 400s, zero billed. Runs only after Mike's commit + `deploy` of the matcher fix. Expected: 200 with a ranked `top5`. Day's total after it: **$0.66**. Mike's decision 1, 2026-09-18. |

Note, not counted: `signature_identification_log` row 17 (2026-09-19 03:38:25Z, 3 passes, 72.1 s) is Mike's own
"ID Sigs" click after the showToast purge — user-driven app use, outside this ledger's scope; ~$0.66 by the same
estimate. The route keeps no `response.usage`, so neither row 16 nor row 17 has a measured cost.

Queued behind Mike's design choice, NOT approved, NOT run: signature cross-validation (one pass, cached)
**$5.70** est. / $7.00 worst case; external 100-row test (one pass, cached) **$8.10** est. / $9.40 worst
case. Together $13.80 — over the ceiling on one day. Basis: `count_tokens` on a real 15 × 4 + 1 request =
38,903 input tokens; output assumed 1,000 per pass (unmeasured; cap 1,500).
Detail: `docs/technical/SIGNATURE_MEASUREMENT_PREP_2026-09-18.md`.

---

## 2026-09-19 — running total: **~$6.62** (row 18 ~$0.66 by estimate + (2) $5.96 measured) · Opus 4.8 at $5 / $25 per MTok

| # | run | est. | actual | notes |
|---|-----|------|--------|-------|
| 9 | ASM #252 — ONE "ID Sigs" click after the logging and pool deploys (the logging assert and the first pool test in one) | **$0.66** ($0.70 worst case) | **~$0.66, NOT MEASURED** | **RAN 2026-09-20 01:31:09Z — log row 18, Stan Lee 0.882, matched, 3 passes, 75.7 s.** Two earlier clicks failed in the browser (CORS) and never reached the backend: $0. Planned by Mike as part of today's sequence. Pass = Render prints the pre-filter line with Stan Lee in the 15. Day's total after it: **$0.66**. No measured actual is possible until the route keeps `response.usage` (ROADMAP item 24). |
| 10 | Signature cross-validation (2) — 97 held-out queries, ONE pass each, fixed pools, cached reference block; harness imports the production functions | **$5.70** ($7.00 worst case) | **$5.96 MEASURED** (run 1 $1.52 + run 2 $4.45; +4.6%, the overrun is the restart) | Approved in principle by Mike ("(2) at $5.70 if the day's spend allows"). Day's total after it: **$6.36** est. / $7.70 worst case — under $10. The harness records `response.usage`, so this one WILL have a measured actual. Output tokens per pass are still an assumption (1,000); the first five calls re-base the estimate before the rest run. **Run 1 (stopped by me at 37 of 97, 2026-09-20 ~02:00Z): $1.52 measured, 37/37 top-1 correct, output ~980 tok/call, cache reads on every call after each pool's first.** Stopped because Mike ruled that (2) is scored on the model's RAW per-candidate score and run 1 kept only the route's normalised share. **Run 2 restarts all 97 with raw scores recorded: est. $4.20 (97 × ~$0.035 + 7 pool writes); (2) total est. $5.72; day's total est. $6.38 — under $10.** The 37 repeated queries are not waste: they are a second sample of the same query, i.e. the run-to-run variance read. |

---

## 2026-09-20 — running total: **~$4.78** ($4.12 measured + the ASM #252 proof click ~$0.66 by estimate, log row 19) · Opus 4.8 at $5 / $25 / cache write $6.25 / cache read $0.50 per MTok

| # | run | est. | actual | notes |
|---|-----|------|--------|-------|
| 11 | Prompt VERSION 2 validation — the "after" of a before/after whose "before" is run 2 of 2026-09-19 (prompt v1, all 97, already paid). One pass per query, same pools, same held-out images, cached reference block. **~70 PRESENT queries** (every third creator skipped, but all 17 of v1's misses and soft-band creators kept) **+ 14 ABSENT queries** (2 per pool: a real held-out signature whose owner is NOT among the candidates — the case v1 could not express and (2) could not see) | **$4.55** (84 × ~$0.048 measured per cached call + 7 pool cache writes ≈ $0.55); harness stops itself above a **$4.80** projection | **$4.12 MEASURED** (−9.5%; 86 calls, 0 errors) | Approved by Mike 2026-09-20 ("validate it with the $4.50 before-and-after run today; that is today's spend"). Day's total after it: **$4.55**. v2 output may run longer than v1's 1,037 tokens (three new fields) — the re-base at five calls catches it. |
| 12 | ASM #252 — ONE click after the prompt-v2 deploy (Mike, the unit's planned proof) | **$0.66** | **~$0.66, NOT MEASURED** | Log row 19, 2026-09-20 22:32:34Z: Stan Lee 0.937, matched, 3 passes, 66.8 s, `prompt_version: "2"`. The route still discards usage; the cache unit (deploys Monday after (3)) is what finally records it. |

**Queued, approved by Mike, not yet run:** Monday 2026-09-21 — external test (3), one pass, **$8.10** est. / $9.40 worst case, then ONE ASM #252 proof click after the cache deploy (~$0.37 expected) → Monday ≈ **$8.47**, under $10 only if (3) holds its estimate; the harness stops itself at a $9.00 projection. Tuesday 2026-09-22 — one-pass vs three-pass on a 40-creator subset, **~$3.70**.

---

## 2026-09-21 — running total: **$6.50** (measured: $6.24 external test + $0.26 unit B proof click) · Opus 4.8 BATCH rate $2.50 / $12.50 per MTok (50%)

| # | run | est. | actual | notes |
|---|-----|------|--------|-------|
| 13 | External test (3) — 87 signed CGC/CBCS eBay rows from the HELD-OUT fold (`id % 5 = 0`), R2 images only, one pass each, the deployed route's own request (Design A pool, prompt v2, floor rule), sent through the Message Batches API | **$6.62** (87 × ~25,090 measured input tokens + ~1,067 output, at the batch rate); **worst case $7.52** (every request at the largest measured input and the 1,500-token output cap) | **$6.24 MEASURED** (−5.7%; 87 calls, avg 23,014 in / 1,134 out; 1 unparseable response, billed) | Approved by Mike at $8.10 with a $9.00 stop. **Why batch:** Design A pools depend on the title, so 87 rows make 56 distinct pools — prompt caching saves little and a synchronous run would be ~$19. A batch cannot be stopped mid-run, so the stop is enforced BEFORE submit: the worst case is computed from `count_tokens` on four real requests (free) and sits under $9.00. Day's total after it: **$6.62** est. The unit B proof click later today (~$0.37) would make it ~$6.99. |
| 14 | Unit B proof — ONE ASM #252 click after the cache-breakpoint deploy (`d21fdc9`) | ~$0.37 | **$0.2634 MEASURED — the first identification with a measured cost** | Log row 20, 16:07:36Z: input 2,373 · cache_write 22,678 · cache_read 45,356 · output 3,483; pass 1 $0.174, passes 2 and 3 $0.045 each. Uncached the same three passes = $0.439 → the cache saves 40%. The estimate was high because it assumed a 38.9k-token pool; Design A pools average ~23k. |

**Queued for Tuesday 2026-09-22, approved in principle by Mike, estimate to be restated before each starts:** image lever — 40 creators × {full resolution, thumbnail-size}, one pass, three cached pools ≈ **$3.00**; then one-pass vs three-pass — two more passes on the same 40 ≈ **$2.80**. Both ≈ **$5.80**; stop at the $10 ceiling.

---

## 2026-09-22 — running total: **$6.37** (measured; final for the day) · Opus 4.8 $5 / $25, cache write $6.25, cache read $0.50 per MTok

| # | run | est. | actual | notes |
|---|-----|------|--------|-------|
| 15 | IMAGE LEVER — 42 creators from (2)'s pools 0–2, each held-out signature sent at full resolution and again downscaled to an 80 px long edge (a listing-thumbnail signature), one pass each = 84 calls, three cached pools | **$3.05** (84 × $0.0322 measured per cached call on these pools + 3 cache writes ≈ $0.35); worst case $3.60 | | Approved by Mike 2026-09-21 ("the image lever first, about $3.00"). Harness stops above a $3.60 projection at the sixth call. Day's total after it: $3.05. **$3.14 MEASURED** (+3%; 84 calls, 0 errors). |
| 16 | ONE PASS vs THREE — two more full-resolution passes on the same 42 creators (labels 0.5 and 0.7; with arm 1's full pass that is three, aggregated by production `aggregate_passes`) = 84 calls, three cached pools | **$2.80** (84 × $0.0315 measured on these pools + 3 cache writes); worst case $3.30 | | Approved by Mike 2026-09-21 ("then one-pass against three-pass, about $2.80"). Stop above a $3.30 projection. Day's total after it: **$5.94** est. **$3.23 MEASURED** (+15%: output ran ~1,250 tokens a call, not 1,067; 84 calls, 0 errors). |

**OFFLINE WINDOW 2026-09-23 → ~09-28: Claude-initiated spend is $0 by rule — no run of any kind. Any console spend in the window is user-driven grading or nobody's.**
