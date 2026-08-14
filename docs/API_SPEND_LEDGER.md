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

## 2026-08-14 — running total: **$0.00**

| # | run | est. | actual | notes |
|---|-----|------|--------|-------|
| — | *(no API calls made)* | — | $0.00 | `ANTHROPIC_API_KEY` was absent from `.env` for the whole session; `count_tokens` and the CP-1 sample were both blocked on it. All measurement this session was DB + image-dimension work at zero API cost. |

**Queued, not yet authorized to run:**

| run | est. | gate |
|-----|------|------|
| CP-1 paired vision sample — 100 books × {s-l500, s-l800, s-l1600} = 300 calls | **$1.39** | Awaiting go on 200 live `i.ebayimg.com` GETs (see below) |

**Non-API cost flagged on the same run:** the s-l800 and s-l1600 arms are not in
R2 (which holds s-l500 only), so they require **200 live GETs to
`i.ebayimg.com`** outside the normal capture path. That is eBay traffic, and the
no-automation capture constraint has never been traded — it needs its own
explicit go, separate from the dollar figure.

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
