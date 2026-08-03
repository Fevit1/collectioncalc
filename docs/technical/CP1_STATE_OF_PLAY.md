# CP-1 — Valuation Honesty: State of Play

**Audit date:** 2026-08-02 · **Method:** read-only (code inspection + `DATABASE_URL_RO`, role `do_readonly`)
**Status:** findings only. **Nothing in this document has been fixed.**

> **MOST RECENT CHANGE (Rule 5):** this audit **corrects `docs/LAUNCH_READINESS.md:9`**, which states
> confidence is *"computed + stored, displayed nowhere."* **"Displayed nowhere" is DEAD — it is false.**
> Confidence is rendered in **two** live surfaces in `app.html`. Supersedes every prior framing of CP-1 as
> a "wire up the display" task. The real defect is different and worse: **five inconsistent notions of
> confidence with five different threshold sets, and a label that is systematically too generous.**

> ⚠️ **Corpus figures are a moving target.** All derived analysis below comes from ONE
> `REPEATABLE READ` snapshot at **2026-08-02 23:27:37 UTC**. Capture was running live during the audit:
> `ebay_sales` went 85,330 → 89,950 → 95,169 within a single hour. Re-run the queries rather than
> quoting these numbers as current.

---

## Contents

1. [Where confidence is computed](#1-where-confidence-is-computed)
2. [Where it is stored and displayed](#2-where-it-is-stored-and-displayed)
3. [Thresholds](#3-thresholds)
4. [What the user actually sees](#4-what-the-user-actually-sees)
5. [How often each case occurs](#5-how-often-each-case-occurs)
6. [Does confidence track accuracy?](#6-does-confidence-track-accuracy)
7. [Pre-existing partial work](#7-pre-existing-partial-work)
8. [Code/doc contradictions](#8-codedoc-contradictions)
9. [Agreed remediation order](#9-agreed-remediation-order)
10. [Reproducing the queries](#10-reproducing-the-queries)

---

## 1. Where confidence is computed

**Five implementations.** Not one.

| # | Location | Notion | Inputs |
|---|---|---|---|
| 1 | `routes/sales_valuation.py:505-512` | `high`/`medium`/`low`/`very_low` | `exact_count`, `total_graded` |
| 2 | `routes/sales_valuation.py:923-930` | same 4 labels, **different cutoffs** | `fmv_sample` (count in the priced tier) |
| 3 | `routes/sales_valuation.py:805` | hardcoded `'very_low'` | none — the no-data branch |
| 4 | `valuation_model.py:482-486` | `confidence_score` 0–100 | product of source-quality factors |
| 5 | `js/app.js:1242-1247` | High/Medium/Low/Very Low | client-side re-bucketing of #4 |

### What feeds #1 — counts only

```python
# routes/sales_valuation.py:505-512
if exact_count >= 10:                          confidence = 'high'
elif exact_count >= 3 or total_graded >= 10:   confidence = 'medium'
elif total_graded >= 3:                        confidence = 'low'
else:                                          confidence = 'very_low'
```

Explicitly **not** inputs:

- **Price spread** — computed as `min_price`/`max_price` in `price_curve` (`:563-564`) and discarded.
- **Recency** — only a hard 365-day cutoff (`:252`, `:286`, `:317`, `:338`). A comp from 360 days ago
  counts exactly as much as yesterday's.
- **Grade proximity** — changes the *number* via interpolation (`:392-424`) but never the label.

### #4 is a different animal

`valuation_model.py:414-486` multiplies source-quality weights — `price_from_db` vs `price_from_web` vs
`price_estimated`; `grade_verified` (1.00) vs `grade_estimated` (0.85); CGC forces grade → 1.0.
**Sample size is not an input at all.** Reaches the client via `/api/valuate`
(`routes/grading.py:56-83` → `ebay_valuation.get_valuation_with_ebay`).

### Bootstrap CI vs stored confidence — two different notions, and the CI is stricter

`bootstrap_ci_median` (`sales_valuation.py:142-158`), 1000 iterations, `seed=42`:

```python
if not values or len(values) < 5:
    return None, None
```

It runs on the **trimmed** exact-grade pool (`:390`), so a cell with `exact_count = 6` can still yield no
CI after `percentile_trim`. Consequence: **`confidence = 'medium'` at `exact_count` 3–4 always has a null
CI** — the label says medium while the only real uncertainty measure declines to answer. Nothing
reconciles the two.

---

## 2. Where it is stored and displayed

### Stored

The `/sales/valuation` confidence **label is never persisted** — only its inputs, in `lookup_demand`
(`lookup_demand.py:43-47`).

| Table | Column | Actually holds |
|---|---|---|
| `lookup_demand` | `comp_count`, `exact_count`, `fmv_method`, `estimated`, `no_data` | valuation confidence **inputs** |
| `search_cache` | `confidence`, `confidence_score`, `quick_sale_confidence`, `fair_value_confidence`, `high_end_confidence` | notion #4 — 80 rows: `MEDIUM` 34, `LOW` 26, `MEDIUM-HIGH` 15, `VERY LOW` 5 |
| `collections` | `confidence` (int) | **grading** confidence, not valuation (`app.html:3170`) |
| `grade_submissions` | `confidence` (int) | grading confidence |

So "computed + stored" is half true: notion #4 is stored; notion #1's label is ephemeral.

### Displayed — in two places

**Surface A — grading results (`/sales/valuation`).** Static label `app.html:1227-1230`, populated
`app.html:2714-2722`:

```javascript
const confLabels = { high: 'High', medium: 'Medium', low: 'Low', very_low: 'Limited' };
const confColors = { high: '#10b981', medium: '#3b82f6', low: '#f59e0b', very_low: '#ef4444' };
```

User sees `Data confidence: High` (green) / `Medium` (blue) / `Low` (amber) / **`Limited`** (red).
`very_low` renders as "Limited" — softer than the internal name.

**A bug in this surface:** the wrapper `<div class="valuation-confidence">` at `:1227` has no
`display:none`, but the value `<span id="resultConfidence">` at `:1229` does. On the API-error early
return (`:2640-2642`) the label renders with nothing after it — the user sees a bare **"Data
confidence: "**. There is also no legend anywhere explaining what "Limited" means or what is being
measured.

**Surface B — manual "Get Valuation" (`/api/valuate`).** Live: button `app.html:1037`, results
`app.html:1371-1372`, rendered by `js/app.js:1288-1300` (loaded at `app.html:1600`):

```
Confidence
  Quick Sale   High (85%)
  Fair Value   Medium (60%)
  High End     Low (40%)
```

Three percentages from notion #4, bucketed by a fifth threshold set, with no relationship to the comp
counts driving Surface A.

### Not displayed

- **Bootstrap CI is never rendered.** `ci_95_low`/`ci_95_high` returned at `:599-600`; zero frontend
  consumers. *(Positive control: `variant_disclosure`, a sibling field from the same payload, is found at
  `app.html:2727-2728`, so the probe can find payload references in HTML.)*
- **`/sales/fmv` confidence is returned but never rendered by its only consumer.** Sole caller is
  `CCExtensions/whatnot-valuator/lib/collectioncalc.js:175`, which has **0** occurrences of "confidence"
  *(positive control: 10 occurrences of "fmv" in the same file)*. Confirms the still-open TODO at
  `sales_valuation.py:920-921`: *"this only EXPOSES the signal; the overlay must still render it."*
- **Market Pulse and Price Lookup show nothing** — stubs: `js/sidebar.js:433`
  `alert('Market Pulse — coming soon!')`, `:436` `alert('Price Lookup — coming soon!')`.
- `collection.html` — no confidence surface.

---

## 3. Thresholds

Bucketed four ways, all hardcoded, no shared constant:

| Source | high | medium | low | very_low |
|---|---|---|---|---|
| `sales_valuation.py:505-512` | `exact≥10` | `exact≥3` **or** `total_graded≥10` | `total_graded≥3` | else |
| `sales_valuation.py:923-930` | `sample≥10` | `sample≥5` | `sample≥2` | else |
| `js/app.js:1242-1247` | `≥70` | `≥50` | `≥30` | else |
| `valuation_model.py:124-126` | *(no buckets — raw 0–100 product)* | | | |

Two extra independent booleans: `low_confidence = fmv_sample < 5` (`:951`) and `verdict_reliable`
(`:527`), which gates on fabrication rather than on confidence.

`sales_valuation.py:521-525` documents that the gate deliberately excludes `very_low`:

> *"NOTE: gating on confidence=='very_low' would ALSO sweep exact_thin in (exact_thin ⟹ total_graded<3 ⟹
> very_low), which Mike scoped POST-LAUNCH — so the launch gate is estimated-only, NOT very_low."*

---

## 4. What the user actually sees

All cases run through `window.calculateGradingRecommendation` (`app.html:2579`).
**In every case a dollar figure is displayed. There is no blank, no error, no "we don't know" state.**

### Case 1 — many recent comps at the exact grade (`exact_count ≥ 10`)
`fmv_method='exact'` (`:429`), `confidence='high'`, `verdict_reliable=true`, CI computed and discarded.

- `Data confidence: High` (green)
- Badge **`WORTH THE SLAB`** / **`KEEP IT RAW`** (`:2697`)
- *"You'll gain an estimated **$481** after grading fees. Based on 34 sales."* (`:2708`) or
  *"Grading costs **exceed** the expected value increase. Better to enjoy it unslabbed."* (`:2710`)

### Case 2 — 1–2 comps ⚠️ the honesty gap
`fmv_method` = `'blended'` if grades above and below exist (`:434`, weight `exact_count/3.0`), else
`'exact_thin'` (`:437`).

**`verdict_reliable` stays `true`** — the fabrication gate does not fire, so the user gets a fully
confident verdict off one or two sales, styled identically to Case 1. And if the book has ≥10 graded
comps at *any* grade, the label reads **`Medium` (blue)** via the `total_graded >= 10` clause.

### Case 3 — estimated / interpolated
Three mechanically distinct things:

- **`interpolated`** (`:397-408`) — no comps at the requested grade but comps above *and* below; linear
  interpolation on grade distance. One-sided extrapolation is **±20% per grade point** (`:415`, `:422`)
  with a floor of `above_median * 0.25` (`:424`). **`verdict_reliable = true`** → confident verdict on a
  number no sale supports.
- **`estimated_from_raw`** (`:494`) — raw sales, zero graded; `graded_fmv = raw_fmv * 1.5`. Gated.
- **`estimated`** (`:461-489`) — zero comps of any kind. Gated. Mechanically:

```
raw    = grade_baselines[closest_grade]   # 9.8→45, 6.5→12, 5.0→8, 1.0→2
       × publisher                        # marvel|dc 1.3 · image|dark horse|idw 1.1
       × era                              # <1970 2.0 · <1984 1.5 · <1992 1.2
graded = raw × 1.5
```

**This is key-blind.** No notion of first appearance, key status, or scarcity — `is_key_issue` exists on
both tables and is never consulted. A 1966 Marvel at 6.5 returns the same figure whether it is the first
Rhino appearance or a filler issue.

### Case 4 — no usable comps at all
`fmv_method='estimated'`, `estimated=true`, `confidence='very_low'`, `verdict_reliable=false`. Verbatim:

- `Data confidence: Limited` (red `#ef4444`)
- Badge **`ROUGH ESTIMATE`** (`:2693`), amber
- Tagline (`:2706`): **"Not enough recent sales to value this reliably."** then *"The figures above are a
  rough estimate from grade, publisher, and era — treat with caution."*
- Net ROI neutral amber rather than green/red (`:2687-2688`)
- The three tiles still show **specific dollar amounts**, rounded, no range, no hedge in the tiles

`/sales/fmv` equivalent copy — `sales_valuation.py:808`:
*"Estimate based on grade/publisher/era - limited sales data available"* — never rendered.

**Assessment: Case 4 is the best-handled case in the product.** Cases 2 and 3-interpolated are the
dangerous ones — a confident green/red verdict with no caution state at all.

---

## 5. How often each case occurs

Snapshot **2026-08-02 23:27:37 UTC**. `ebay_sales` 89,950 + `market_sales` 9,964 = **99,914**.

Graded comp pool — 365-day window, variants/reprints/lots/facsimiles excluded exactly as the endpoint
does: **11,650 comps · 5,509 (title, issue, grade) cells · 3,370 (title, issue) books.**

| Same-grade comps | Cells | Share |
|---|---|---|
| exactly 1 | 4,065 | **73.8%** |
| exactly 2 | 596 | 10.8% |
| 3–4 | 426 | 7.7% |
| 5–9 | 261 | 4.7% |
| 10+ | 161 | **2.9%** |

### Prior figures — CORRECTED

| Prior claim | Corrected | Note |
|---|---|---|
| "89% of titles have only 1–2 comps" | **84.6%** (4,661 / 5,509) | directionally right, overstated |
| "grade-specific FMV reliable on ~268 books" | **314 books** (848 cells) reach `exact_count ≥ 3` | improved with capture |
| — | `exact_count ≥ 10` reachable on **161 cells** only | |

### Confidence label distribution

Requested grade **has** ≥1 comp (best case):

| Label | Cells | Share |
|---|---|---|
| high | 161 | 2.9% |
| medium | 1,389 | 25.2% |
| low | 855 | 15.5% |
| very_low | 3,104 | 56.3% |

Requested grade has **zero** exact comps: `very_low` 84.3% · `low` 10.7% · `medium` 5.1%.

### ⚠️ The `total_graded >= 10` defect, quantified

Of **1,389** cells labelled `medium`, **702 (50.5%)** are backed by only **1–2** same-grade comps, and
**451** by exactly **one**. That is **12.7% of every priceable cell** showing blue "Medium" on ≤2 sales.

The deep, liquid keys are the worst offenders — high `total_graded` is precisely what buys an unearned
"Medium" at sparse grades:

```
absolute batman      #1   grade 1.0   exact_count=1   total_graded=341
amazing spider-man   #300 grade 3.0   exact_count=1   total_graded=323
new mutants          #98  grade 1.0   exact_count=1   total_graded=278
```

### Real lookup traffic — with a caveat that undercuts the question

`lookup_demand`: 1,239 rows, 2026-06-21 → 2026-08-02.

| Endpoint | `is_internal` | Rows |
|---|---|---|
| `fmv` | false | **1,220** |
| `valuation` | true | 11 |
| `valuation` | false | **8** |

Of 1,228 external lookups: **577 (47.0%)** returned `no_data` **and** `estimated`.
`exact_count = 0` on **99.6%**; `exact_count ≥ 10` on **2**.

⚠️ **1,220 of 1,239 rows hit `/api/sales/fmv`, whose only caller is the Whatnot valuator extension** —
Mike's own tooling, not website users (`is_internal` derives from `g.admin_id` —
`routes/sales_valuation.py:47`, passed through at `lookup_demand.py:62` — so his own non-admin traffic
reads as external). **The website's valuation path has 8 external lookups total.** The corpus is demonstrably thin; **how often a real user hits the thin case is not yet
answerable** and won't be until post-launch traffic accumulates.

---

## 6. Does confidence track accuracy?

**The general question is unanswerable — no ground truth exists.** All 39 tables enumerated:
`grade_submissions` (18 rows) and `collections.confidence` hold *grading* confidence; `match_reports` is
**empty**; `user_feedback` has 11 rows. **Nothing records what a book actually sold for after a
valuation.** No column, table, or feedback path captures realized price. Any claim that high confidence
is more accurate would be speculation.

**But the "tight comps, wrong variant" hypothesis is CONFIRMED — via a different mechanism.**

### ⚠️ Signed copies are never excluded from comp pools

`routes/sales_valuation.py` filters `is_reprint`, `is_lot`, and (Python-side, `:368-371`) `is_variant`.
It **never references `is_signed`** *(positive control: `is_signed` is used in `ebay_valuation.py`,
`normalize_batch.py`, `routes/monitor.py`, `routes/sales_ebay.py` — the column is real and used
elsewhere)*.

Measured on the eBay graded pool (365d; `is_variant`/`is_reprint`/`is_lot` excluded; **`raw_title` junk
filters not applied and `market_sales` not included** — a slightly wider basis than the 11,650 figure
above, stated so the numbers aren't mixed):

- **829 of 9,570** graded comps (**8.7%**) are `is_signed = true`
- **290 cells** contain both a signed and an unsigned comp at the same title+issue+grade
- Median signed/unsigned price ratio **1.72×**, range **0.02× – 68.46×**

| Title | Issue | Grade | Signed | Unsigned | Ratio |
|---|---|---|---|---|---|
| Watchmen | 1 | 8.5 | $6,500 | $95 | **68.46×** |
| X-Men | 141 | 9.8 | $1,225 | $36 | 34.04× |
| Amazing Fantasy | 15 | 9.8 | $1,997 | $146 | 13.69× |
| Absolute Wonder Woman | 15 | 9.8 | $450 | $42 | 10.82× |
| Saga | 1 | 9.8 | $3,300 | $326 | 10.11× |
| Uncanny X-Men | 120 | 7.0 | $660 | $68 | 9.72× |
| Absolute Batman | 16 | 9.8 | $899 | $96 | 9.37× |

### ASM #41 — misattributed, but it contains a live instance

ASM #41 today has **106 rows**, 47 graded comps spanning $191–$3,200. It is well covered.

**The historic `~$47` was the fabrication branch, not tight-but-wrong comps.** The arithmetic identifies
it exactly:

```
grade 6.5 → baseline 12 × 1.3 (Marvel) × 2.0 (1966) = $31.20 raw
                                       × 1.5        = $46.80 graded
```

That is `fmv_method='estimated'` with `confidence='very_low'` — a **zero-comp** result caused by
title-matching failure (the L-SW-2026-009 / L-SW-2026-011 normalization bugs), since fixed. It was
low-confidence-and-wrong, not high-confidence-and-wrong. *(Whether it also displayed the `ROUGH ESTIMATE`
caution depends on whether that sighting predates Fix B, 2026-06-27 — not establishable from code.)*

**ASM #41 does contain a live instance of the real defect:**

```
grade 3.0   n=1   signed=1   $1,275      ← reported "Medium" confidence
grade 3.5   n=3   signed=0   $330 avg
grade 2.5   n=4   signed=0   $230 avg
```

A user grading their ASM #41 at 3.0 is told **$1,275** at **Medium** confidence, from a single Stan
Lee–signed comp, when the surrounding grades say ~$280. **≈4.5× overvaluation, blue label.** Every one of
its 16 grades reports `medium`, because `total_graded = 47 ≥ 10`.

---

## 7. Pre-existing partial work

1. **Dead element** — `app.html:1208-1210`:
   `<div class="grade-quality-warning" id="gradeQualityWarning" style="display:none">` containing
   *"Grade based on limited photos. Add more angles for higher confidence."* The id is referenced
   **nowhere** in JS. Copy written for exactly this problem, never wired. The comment claims *"shown if
   < 75% confidence"* — that logic does not exist.
2. **`/sales/fmv` confidence** — built, returned, never rendered (`:915-930`, TODO at `:920-921`).
3. **Bootstrap CI** — fully implemented (`:142-158`), returned (`:599-600`), zero consumers.
4. **A whole second live confidence UI** — Surface B (`js/app.js:1288-1300`), contradicting Surface A on
   the same book.
5. **Multi-run voting** — `app.html:2355` hardcodes `runs: 1` with *"Single run by default; set to 2-3
   for higher confidence"*. Server support exists, client never uses it. (Grading, not valuation — same
   displayed-nowhere pattern.)
6. **A post-launch TODO already in the code** — `sales_valuation.py:524-525`:
   *"⏰ POST-LAUNCH confidence-tuning: extend the gate to very_low (adds exact_thin + thin-interpolated).
   Do not forget. (Mike, 2026-06-27.)"*

---

## 8. Code/doc contradictions

| Claim | Where | Reality |
|---|---|---|
| "confidence computed + stored, **displayed nowhere**" | `LAUNCH_READINESS.md:9` | Displayed in two live surfaces |
| "bootstrap 95% confidence intervals" as a user feature | `README.md:11` | Computed, **never displayed** |
| "powered by **24,000+** eBay sales" | `README.md:11` | 95,169 at 2026-08-02 23:34 UTC — understated ~4× |
| `/api/sales/fmv` uses a 90-day `created_at` window | `COVERAGE_AUDIT_2026-06-08.md:26,173` | Fixed — `COALESCE(sale_date, created_at)` over 365d (`:252`, note at `:242-245`) |
| "89% of titles have 1–2 comps" | prior state records | 84.6% |
| "grade-specific FMV reliable on ~268 books" | prior state records | 314 books |

### 📌 `README.md:11` — logged, deliberately NOT fixed

One sentence, two problems: the stale **24,000+** figure (actual **95,169**, ~4× understated and moving
by thousands per hour during active capture), and **bootstrap 95% confidence intervals advertised as a
user-facing feature** when they are rendered by zero consumers. Deferred here on purpose so it is
corrected **with** the CP-1 display work rather than in an unrelated commit — fixing the number alone
would leave the false CI claim standing.

---

## 9. Agreed remediation order

Set by Mike, 2026-08-02. Not started.

1. **Signed-comp contamination** — correctness bug. `is_signed` never filtered; 8.7% of the pool;
   median 1.72× premium; live 4.5× error on ASM #41 @ 3.0.
2. **The 11 out-of-range grades** — `grade > 10` in `ebay_sales`: distinct values `11.0, 60.0, 94.0,
   98.0`, almost certainly "9.4"/"9.8" parsed without the decimal (`market_sales` has 0). They form
   phantom grade cells that enter comp pools and interpolation endpoints — corrupting rather than merely
   thinning. `amazing spider-man #300 grade 94.0` appears in the medium-confidence set.
3. **The `total_graded >= 10` clause** — 702 of 1,389 "Medium" labels rest on ≤2 same-grade comps.
4. **Display consolidation** — five notions, five threshold sets, two contradicting live surfaces; plus
   the bare `"Data confidence: "` render bug (`app.html:1227-1230`) and the missing legend. Fix
   `README.md:11` as part of this.

---

## 10. Reproducing the queries

Read-only, `DATABASE_URL_RO` (role `do_readonly`). Use a `REPEATABLE READ` snapshot — capture is live and
counts drift between statements.

```python
c = psycopg2.connect(url)
c.set_session(readonly=True, isolation_level='REPEATABLE READ')
```

**Graded comp pool** — mirrors `/api/sales/valuation` exactly: 365-day `COALESCE(sale_date, created_at)`
window; `is_variant` / `is_reprint` / `is_lot` excluded; `raw_title` junk filters (`facsimile`,
`reprint`, `lot of`, `bundle`, `complete set`, `complete run`, `full run`, `all covers`); `sale_price > 5`
on eBay, `price > 2` on Whatnot; **both tables** unioned on
`(lower(canonical_title), issue, grade)`.

⚠️ **Query both tables.** `market_sales` is 100% Whatnot (`sales_market.py:127` defaults `source`);
counting either alone yields the opposite wrong answer with equal confidence — see L-SW-2026-014.

**Confidence buckets** are derived in Python from the pool, mirroring `sales_valuation.py:505-512`; they
are not stored, so they cannot be queried directly.

**Signed contamination** — group by `(canonical_title, issue_number, grade)`, `AVG` split on `is_signed`,
keep cells having both.

**Lookup traffic** — `lookup_demand`, filter `is_internal = false`, and check the `endpoint` split before
interpreting: `fmv` is extension traffic, `valuation` is the website.

---

*Generated read-only 2026-08-02. No code changed. Queries reproducible against `DATABASE_URL_RO`
(SELECT-only).*
