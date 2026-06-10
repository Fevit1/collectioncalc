# Sales Data Coverage Audit — 2026-06-08

**Run by:** Claude (read-only, `DATABASE_URL_RO`)
**Purpose:** Feed the capture-schedule rebuild and the launch data-readiness check.
**Method:** Read-only SELECTs against production Postgres. No writes. Valuation logic
mirrored from `routes/sales_valuation.py` (`/api/sales/valuation`).

> ⚠️ **All queries were read-only.** Nothing in the DB was changed. This document is
> the only artifact written, and it lives in the repo, not the database.

---

## TL;DR

- **Two sales tables:** `ebay_sales` (38,352 rows, eBay only) and `market_sales`
  (9,398 rows, **100% Whatnot**). They are separate stores, not a unified table.
- **Collection has been STALLED since ~March 30–31, 2026.** Both feeds went dark for
  **~67–68 days** and only just trickled back on **2026-06-06** (this weekend): **42**
  new eBay rows + **3** new Whatnot rows. That is a restart heartbeat, not a recovered pipeline.
- **Breadth is good, depth is thin.** 15,010 distinct series+issue keys exist, but
  **94.5% of them rest on fewer than 5 sales, and 75% on a single sale.** Only ~772 keys
  (5.5%) have ≥5 sales backing their valuation.
- **Well-known keys:** of 50 representative keys, **41 are usable** (36 strong), **8 are
  thin (<5 sales)**, **1 is raw-only** (no graded sales → slab FMV is interpolated).
  The weak spots are scarce high-dollar vintage, not the liquid modern/bronze keys.
- **Latent landmine:** `/api/sales/fmv` filters sales by `created_at` within **90 days**.
  Because capture stalled in March, that 90-day window is now nearly empty — that endpoint
  is largely running on the estimate fallback right now. (`/api/sales/valuation` uses 365
  days and is unaffected so far.)

---

## 1. Sales data shape

| Metric | eBay (`ebay_sales`) | Whatnot (`market_sales`) |
|---|---|---|
| Total rows | **38,352** | **9,398** |
| Graded rows | 4,065 | 4,547 (grade not null) |
| Raw/ungraded rows | 34,287 | 4,851 |
| Sale-date range | 2019-02-17 → 2026-06-06 | 2026-01-24 → 2026-06-06 |
| Capture range (`created_at`) | 2026-02-02 → 2026-06-06 | 2026-01-24 → 2026-06-06 |
| Distinct series | **10,049** | 35 (col barely populated) |
| Distinct series+issue keys | **15,010** | — (series col unusable) |

**Combined corpus: 47,750 sale rows.**

**Rows added since 2026-03-24:** eBay **9,086**, Whatnot **112** → ~9,198 total. But this is
misleading as a "still running" signal: virtually all of it landed in a **single batch on
2026-03-30/31**, after which capture flatlined. See §2.

**Did collection stall?** Yes. Daily capture (`created_at`):

```
eBay:    ... 2026-03-20: 211 | 2026-03-30: 9,044 | [nothing] | 2026-06-06: 42
Whatnot: ... 2026-03-20: 255 | 2026-03-30: 89 | 2026-03-31: 20 | [nothing] | 2026-06-06: 3
```

No rows were captured in **all of April or May 2026** on either feed.

---

## 2. By source — eBay vs Whatnot, and the Whatnot dark period

The two sources are physically separate tables, so the breakout is clean.

| | Last capture before the gap | First capture after the gap | Dark span |
|---|---|---|---|
| **eBay** | 2026-03-30 (bulk, 9,044 rows) | 2026-06-06 (42 rows) | **~68 days** |
| **Whatnot** | 2026-03-31 16:18 UTC | 2026-06-06 20:03 UTC | **~67 days** |

**Whatnot was dark for roughly 67 days (March 31 → June 6).** The extension came back
online this weekend (2026-06-06) but has only logged **3 Whatnot sales** so far — the feed
is reconnected but not yet flowing at volume. eBay is in the same state: reconnected
(42 rows on 06-06) but nowhere near the Feb–March cadence.

**Most-recent actual sale captured:** both sources max out at **2026-06-06**, consistent
with a weekend restart capturing fresh sales.

**Data-quality note on Whatnot:** `market_sales.series` has only **35 distinct values**, and
`canonical_title` is dominated by stream/lot noise ("Bid", "Single", "Auction", "EC Comics",
"Asm Bananas!!"). 8,233 / 9,398 rows do carry a parsed `issue`, but series-level matching on
Whatnot is unreliable. In practice the valuation engine leans on `ebay_sales` for clean
series+issue matching and uses Whatnot as a supplementary `LIKE` match.

---

## 3. Distribution — top 20 and the tail

**Top 20 series+issue keys by eBay sales count:**

| Rank | Key | Sales | Rank | Key | Sales |
|---|---|---|---|---|---|
| 1 | X-Men #1 | 285 | 11 | Infinity Gauntlet #1 | 135 |
| 2 | Spider-Man #1 | 218 | 12 | Uncanny X-Men #266 | 129 |
| 3 | Amazing Spider-Man #300 | 174 | 13 | Dark Knight Returns #1 | 128 |
| 4 | Venom: Lethal Protector #1 | 168 | 14 | Incredible Hulk #181 | 125 |
| 5 | Ultimate Spider-Man #1 | 167 | 15 | Batman #655 | 121 |
| 6 | Amazing Fantasy #15 | 166 | 16 | Batman #404 | 115 |
| 7 | Something is Killing the Children #1 | 142 | 17 | Ghost Rider #1 | 114 |
| 8 | Teenage Mutant Ninja Turtles #1 | 141 | 18 | Watchmen #1 | 112 |
| 9 | Youngblood #1 | 139 | 19 | Giant-Size X-Men #1 | 111 |
| 10 | New Mutants #98 | 136 | 20 | Sex Criminals #1 | 109 |

**The tail is very thin** (eBay, grouped by series+issue, lots excluded — 13,962 keys):

| Backing sales | Keys | Share |
|---|---|---|
| Exactly 1 sale | 10,467 | **75.0%** |
| Fewer than 5 sales | 13,190 | **94.5%** |
| ≥ 5 sales | 772 | 5.5% |
| ≥ 10 sales | 321 | 2.3% |

**Interpretation:** the catalog is wide but shallow. For ~19 of every 20 keys, a user's
valuation is computed from fewer than five comps — and for three of every four keys, from a
**single** sale. The statistical machinery in `sales_valuation.py` (median trimming, bootstrap
95% CI) only meaningfully engages above ~5 comps; the bootstrap CI is explicitly suppressed
below 5 values, so the vast majority of keys return a point estimate with no confidence band.
This is the single biggest data-readiness gap for launch.

---

## 4. Coverage gaps — 50 well-known keys

Each key was run through the actual `/api/sales/valuation` match logic (canonical exact OR
parsed_title/title/series LIKE, + exact issue, reprint/lot/facsimile filtered, 365-day
`created_at` window). Counts are eBay total / eBay graded / Whatnot total.

**Classification:** USABLE(strong) ≥10 total · USABLE 5–9 · RAW-ONLY ≥5 but 0 graded
(slab FMV is interpolated) · THIN <5 (estimate-leaning).

| Result | Count of 50 |
|---|---|
| ✅ USABLE (strong, ≥10 comps) | 36 |
| ✅ USABLE (5–9 comps) | 5 |
| ⚠️ RAW-ONLY (no graded comps) | 1 |
| ❌ THIN (<5 comps) | 8 |

**Thin / weak keys (would give a user a "no data"-grade or low-confidence result):**

| Key | eBay / grd / What | Why it matters |
|---|---|---|
| Incredible Hulk #180 | 2 / 0 / 2 | 1st Wolverine cameo — scarce, expensive |
| Incredible Hulk #271 | 1 / 0 / 2 | 1st Rocket Raccoon |
| Iron Man #55 | 3 / 1 / 1 | 1st Thanos |
| Captain America #117 | 1 / 0 / 1 | 1st Falcon |
| Batman #227 | 1 / 0 / 0 | Neal Adams homage cover |
| Batman #232 | 1 / 0 / 0 | 1st Ra's al Ghul |
| Batman #423 | 1 / 0 / 3 | McFarlane cover — high demand |
| Detective Comics #880 | 1 / 0 / 0 | Iconic Joker cover |
| X-Men #94 (RAW-ONLY) | 3 / 0 / 2 | New team begins — 5 comps but **0 graded**, so slab FMV is interpolated |

**Pattern:** coverage is **strong on liquid modern + bronze keys** (ASM #300=208, X-Men #1=665,
Batman #1=722, Venom #1=366, Hulk #181=130, New Mutants #98=173, Giant-Size X-Men #1=120,
Amazing Fantasy #15=90, Tales of Suspense #39=54) and **weak on scarce, high-dollar vintage**.
That is the expected shape — expensive books change hands less often, so eBay sold-listing
capture yields fewer comps — but it means the keys a user is most anxious to value correctly
(four-figure books) are exactly the ones with the thinnest backing. Several first-appearance
bronze keys (Hulk 180/271, Iron Man 55, Cap 117) are effectively running on the estimate
fallback today.

> Note: the truly elite keys (Action Comics #1, Detective #27, Amazing Fantasy #15) actually
> show usable counts here (58 / 43 / 90) because the LIKE match also catches reprints/facsimile
> chatter and lower-grade copies; treat their *graded* counts (14 / 10 / 27) as the real
> slab-FMV backing.

---

## Recommendations for the capture-schedule rebuild

1. **Restart and verify both feeds at volume.** As of 2026-06-06 only 42 eBay + 3 Whatnot
   rows have come in. Confirm the eBay collector and the Whatnot extension are running on a
   schedule, not a one-off manual kick.
2. **Fix the `/api/sales/fmv` 90-day window mismatch.** With capture stalled, the 90-day
   `created_at` filter starves that endpoint. Either widen it to match `/valuation` (365d) or
   filter on `sale_date`/`sold_at` instead of `created_at`. Right now `/fmv` is largely
   serving estimates even for well-covered keys.
3. **Prioritize depth on keys, not just breadth.** 772 keys have ≥5 comps; the launch-critical
   set (top ~500 keys by collector demand) should be driven to ≥5–10 graded comps each. Targeted
   backfill of the thin vintage keys in §4 would close the most visible gaps.
4. **Consider `created_at`-vs-`sale_date` semantics globally.** Filtering eligibility by capture
   date means a capture stall silently ages out the whole corpus. Sale-date-based windows would
   be more robust to collection gaps.
5. **Whatnot normalization.** The `series`/`canonical_title` fields are too noisy to matter for
   series matching (35 distinct series). If Whatnot is meant to be a real second source,
   its title parsing needs the same canonicalization eBay rows get.

---

*Generated read-only. Queries available in session transcript; reproduce against
`DATABASE_URL_RO` (SELECT-only).*
