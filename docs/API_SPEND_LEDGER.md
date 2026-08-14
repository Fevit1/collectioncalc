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
