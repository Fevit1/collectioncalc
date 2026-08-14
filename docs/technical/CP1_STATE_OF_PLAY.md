# CP-1 — Valuation Honesty: State of Play

**Audit date:** 2026-08-02 · **Re-measured:** 2026-08-03 (§5B)
**Method:** read-only (code inspection + `DATABASE_URL_RO`, role `do_readonly`)
**Status:** findings only. **Nothing in this document has been fixed.**

> **MOST RECENT CHANGE (Rule 5):** **2026-08-03 — the remediation order was REVISED and canonical
> "of" fragmentation (§5C) was promoted to first**, displacing signed-comp contamination. See the
> tombstone in §9. A second dated snapshot was appended as §5B; the 2026-08-02 figures below are
> **deliberately NOT overwritten** — two readings show direction, and the direction is itself a
> finding (20,587 new rows made the thin-data ratio slightly *worse*).

> **PRIOR CHANGE (Rule 5):** this audit **corrects `docs/LAUNCH_READINESS.md:9`**, which states
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
5. [How often each case occurs — snapshot 1, 2026-08-02](#5-how-often-each-case-occurs)
   · **[5B. Snapshot 2, 2026-08-03 — and the direction](#5b-second-snapshot--2026-08-03)**
   · **[5C. Canonical "of" fragmentation — priority 1](#5c-canonical-of-fragmentation--priority-1)**
6. [Does confidence track accuracy?](#6-does-confidence-track-accuracy)
7. [Pre-existing partial work](#7-pre-existing-partial-work)
8. [Code/doc contradictions](#8-codedoc-contradictions)
9. [Remediation order](#9-remediation-order)
10. [Reproducing the queries](#10-reproducing-the-queries)
11. [Newly logged, not yet scheduled](#11-newly-logged-not-yet-scheduled)

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
answerable.**

⚠️ **AMENDED 2026-08-03 (Mike's correction).** An earlier version of this section said that answer
arrives "post-launch," implying the Aug 4 soft-launch date. **Aug 4 is not a live date and never was** —
I asserted it from stale docs without checking. The real gate is **first cold traffic (paid ads or an
organic group post), and it is NOT SCHEDULED.** CP-1's remaining fixes sit **upstream** of that gate.

**Consequence for this section: `lookup_demand` cannot be treated as a near-term input to CP-1.** The
demand-ranked backfill loop has no traffic to rank until cold traffic is deliberately turned on, so
assume the 8-external-lookup figure holds indefinitely. **Every fix in §9 must be justified on the
corpus evidence in §5 / §5B — not deferred pending real-user data that is not arriving on any known
date.**

---

## 5B. Second snapshot — 2026-08-03

Single `REPEATABLE READ` transaction at **2026-08-03 03:08:35 UTC**, after a heavy Bronze Age capture
run (Daredevil plus ~28 further titles). Same filters as §5 throughout.

> **The direction is the finding.** 20,587 new eBay rows made the thin-data ratio **slightly worse**,
> not better. Breadth grew faster than depth: +1,207 cells but only +139 reaching ≥3 comps. That is the
> expected shape for Bronze Age keys — individually scarce, so each new issue/grade combination arrives
> as a fresh 1-comp cell. **Capture volume alone will not fix the confidence problem.**

### Corpus

| | 2026-08-02 | 2026-08-03 | Δ |
|---|---|---|---|
| `ebay_sales` | 89,950 → 95,169¹ | **115,756** | **+20,587** |
| `market_sales` | 9,964 | **9,964** | +1 |
| Total | 105,132 | **125,720** | +20,588 |

¹ the 2026-08-02 corpus moved during that audit; 95,169 was the last reading that day.
Split is now **92.1% eBay / 7.9% Whatnot**. 44,104 rows landed in the 12h to 03:05 UTC.

### Comp-count distribution — 13,732 comps · 6,716 cells · 4,004 books

| Same-grade comps | Aug 2 | Aug 3 |
|---|---|---|
| exactly 1 | 73.8% | **74.3%** |
| exactly 2 | 10.8% | 11.0% |
| 3–4 | 7.7% | 7.4% |
| 5–9 | 4.7% | 4.6% |
| 10+ | 2.9% | **2.7%** |
| **≤2** | **84.6%** | **85.3%** ▲ |

### Well-backed keys, confidence, and the `total_graded >= 10` defect

| Metric | Aug 2 | Aug 3 |
|---|---|---|
| `exact_count ≥ 3` | 848 cells / 314 books | **987 cells / 364 books** |
| `exact_count ≥ 10` | 161 cells | **181 cells / 85 books** |
| confidence `high` (grade has ≥1 comp) | 2.9% | 2.7% |
| confidence `medium` | 25.2% | 25.0% |
| confidence `low` | 15.5% | 17.7% |
| confidence `very_low` | 56.3% | 54.7% |
| `very_low` when grade has 0 exact comps | 84.3% | 83.6% |
| **`medium` cells** | 1,389 | **1,676** |
| **…backed by ≤2 comps** | **702 (50.5%)** | **870 (51.9%)** ▲ |
| …backed by exactly 1 | 451 | **572** |

⚠️ **The `total_graded >= 10` defect gets worse with every capture run.** Deepening the liquid titles is
exactly what grants unearned "Medium" labels at sparse grades.

### Signed-comp contamination — measured on the §6 basis

| | Aug 2 | Aug 3 |
|---|---|---|
| Signed share of graded pool | 829 / 9,570 = **8.7%** | 921 / 11,835 = **7.8%** |
| Mixed cells (signed + unsigned, same title+issue+grade) | 290 | **325** |
| Median signed/unsigned ratio | 1.72× | **1.73×** |

The Bronze-Age-clusters-signed hypothesis did **not** hold: rows captured in the last 12h were **7.7%**
signed, essentially the corpus rate, so the share drifted down on dilution. Absolute problem grew (+92
signed comps, +35 mixed cells); the ratio is stable. **1.73× is the number for the fix.**

### ⚠️ Out-of-range grades — the parser bug is LIVE, not a one-off

| | Total | Added in last 12h |
|---|---|---|
| `ebay_sales` grade > 10 | **13** (was 11) | **5** |
| `market_sales` | 0 | 0 |

New distinct value appeared: **85.0**. Full set now `11.0, 60.0, 85.0, 94.0, 98.0`. The cause is visible
in the raw titles — the listing omits the decimal and the parser takes the number literally:

```
grade=94.0  2026-08-03  Star Wars 1 CGC 94 1st Print   Marvel Comics 1977
grade=85.0  2026-08-03  Brand  Marvel Star Wars 1 Reprint CGC 85 1977
grade=60.0  2026-08-02  Giant Size X-Men #1 1975 Marvel Comics CGC 60
grade=94.0  2026-08-02  AMAZING SPIDERMAN 300 1988 CGC 94 OWW 1ST APPEARANCE OF VENO
```

`CGC 94` → 94.0 instead of 9.4. **This changes remediation item 3 from a data cleanup to a cleanup PLUS
a parser fix.** Rate is ~5 per 5,136 graded rows (~0.1%) — slow, but monotonic, and every one creates a
phantom grade cell that feeds interpolation endpoints.

### Bronze Age coverage after the run

Aggregate for the captured titles: **158 / 794 cells at ≥3 comps = 19.9%**, versus 14.7% corpus-wide.
Better than average, still thin.

| Verdict | Titles |
|---|---|
| **SOLID** (≥30% of cells at ≥3) | Captain America · Tomb of Dracula · Hero for Hire · Ghost Rider · Nova · Conan the Barbarian · Star Wars |
| **IMPROVING** (15–30%) | Eternals · Astonishing Tales · Red Sonja · Howard the Duck |
| **STILL THIN** | Daredevil · Marvel Team-Up · Defenders · Man-Thing · Marvel Two-in-One · Jungle Action · Warlock · Power Man and Iron Fist |

Daredevil is the instructive case: 534 comps across 285 cells, but **208 cells sit on a single comp** —
heavy capture spread thin across issues and grades rather than deepening any one of them.

---

## 5C. Canonical "of" fragmentation — PRIORITY 1

**Found 2026-08-03 by a positive control, not by looking for it.** Seven of the captured titles returned
zero graded data. Per L-SW-2026-015 an absence is not a result until the probe is shown capable of
finding something — the control proved three were genuinely absent and **two were a canonicalization
bug**:

```
Master of Kung Fu      -> stored as "Master Kung Fu"       140 rows,  8 graded
                          + "Master Kung-Fu" 20 · "Master Kung Fu Vol." 39 · "Master Kung Fu Annual" 9
Savage Sword of Conan  -> stored as "Savage Sword Conan"   552 rows, 30 graded
                          + "The Savage Sword Conan"       225 rows,  3 graded
```

The word **"of" is dropped inconsistently**. `Tomb of Dracula` exists *both* ways — 308 rows / 83 graded
under `Tomb of Dracula` **and** 66 rows / 23 graded under `Tomb Dracula`.

### Whether it actually costs comps — checked, not assumed

`title_matching._norm` / `_norm_sql` (`title_matching.py:29-38`, `:59-66`) strip a leading `"the "` on
**both** sides. So:

- **Leading-"The" fragmentation is HARMLESS.** 206 pairs / 1,813 rows unify correctly at match time.
  Do not "fix" it.
- **"of" is normalized on NEITHER side, so it is real loss.** Exact match fails, and the `parsed_title`
  LIKE fallback (`%master of kung fu%`) fails too.

| Scope | Measured |
|---|---|
| Title pairs with **both** forms present | **17** |
| Rows in the smaller pool of each pair | **393 (73 graded)** — never join the larger pool |
| Worst pairs | Tomb of Dracula · House of Secrets · Web of Spider-Man · Edge of Spider-Verse · Tales of Suspense · Saga of Swamp Thing · Department of Truth · Birds of Prey |

⚠️ **The 17-pair / 393-row figure is a FLOOR, not a total.** That measurement only finds titles where
*both* forms exist in the corpus. Where the canonical dropped "of" **universally** — Master of Kung Fu,
Savage Sword of Conan — the pair never appears, yet a naturally-titled query matches **nothing**: all
140 and all 777 rows respectively are unreachable. **Sizing the universally-dropped population is part
of the fix work**; it has not been measured.

Same family as **L-SW-2026-009** (per-token support guard) and **L-SW-2026-011** (cleanup stripper
truncating entity names) — a cleanup step mangling entity names, damage invisible until someone queries
the natural title.

**Why it is first:** the cost compounds with capture activity. Tonight's run put 900+ rows into pools the
valuation path cannot reach, so continued capture on affected titles is partly wasted effort until this
is fixed.

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

## 9. Remediation order

### ⚰️ TOMBSTONE — the 2026-08-02 order is SUPERSEDED

**DEAD:** the order set 2026-08-02, which opened on **signed-comp contamination**.
**REPLACED BY:** the 2026-08-03 order below, which opens on **canonical "of" fragmentation (§5C)**.
**REASON:** §5C did not exist on 2026-08-02 — it was found the next night by a positive control. It
displaces signed-comp contamination because its cost **compounds with capture activity**, which is the
work being done most. Signed-comp contamination is stationary at ~7.8%; fragmentation gets worse every
run that touches an affected title.
**SUPERSEDES:** any plan that starts CP-1 with signed-comp filtering. Do not re-derive the old order
from §6 alone — §6 is still accurate as a *finding*, it is simply no longer first.

### Current order — set by Mike, 2026-08-03. Not started.

1. **Canonical "of" fragmentation** (§5C) — silently zeroes comp pools. 17 pairs / 393 rows / 73 graded
   is a **floor**; sizing the universally-dropped-"of" population is part of the work. Same family as
   L-SW-2026-009 / L-SW-2026-011. Leading-"The" fragmentation is already handled correctly — do not
   touch it.
2. **Signed-comp contamination** (§6) — `is_signed` never filtered; **7.8%** of the pool; **325** mixed
   cells; median **1.73×** premium; live ~4.5× error on ASM #41 @ grade 3.0.
3. **Out-of-range grades** (§5B) — **cleanup PLUS a parser fix**, not cleanup alone: 13 rows and
   **5 arrived on 2026-08-03**, so the bug is live and monotonic. `CGC 94` in a listing title parses as
   grade 94.0.
4. **The `total_graded >= 10` clause** (§5B) — **870 of 1,676** "Medium" labels rest on ≤2 same-grade
   comps, 572 on exactly one. Degrades every run.
5. **Display consolidation** (§1–§3) — five notions, five threshold sets, two contradicting live
   surfaces; plus the bare `"Data confidence: "` render bug (`app.html:1227-1230`) and the missing
   legend. Fix `README.md:11` as part of this.

**Next session opens on item 1.**

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

## 11. Newly logged, not yet scheduled

Found 2026-08-03. Recorded so they are not rediscovered from scratch; **not** in the §9 order yet.

### 11.1 Star Wars #1 — variant stripping is the serious failure mode

Probed because the 1977 Marvel issue has a 30¢ regular and a 35¢ price variant with an
order-of-magnitude gap at the same grade. **580 rows · 130 flagged `is_variant` · 182 graded.**

**The dangerous direction is the opposite of what was expected.** Flagged variants are excluded from the
graded buckets (`sales_valuation.py:368-371`) **and** the raw pool (`:285`, `:337`) and routed to **no
separate pool** — `compute_variant_disclosure` only counts them for a disclosure string. So all 130 rows
are **unpriceable**. A genuine 35¢ variant sold at **$6,422** at grade 8.0; the regular pool median at
8.0 is **$272**. The variant's owner is told **$272 — roughly 24× under.**

**Leaking is negligible for this book.** Of 30 unflagged titles mentioning a cent price, only **2** reach
the graded pool (grades 9.0 and 8.5), moving the median by **≤1%**. Most are raw or reprints where the
seller merely mentioned the cover price. Regular-copy FMV is *not* meaningfully inflated here.

**The price-variant regex is effectively dead code.** `title_normalizer.py:274`:

```python
(r'\b(35|30)\s*[¢c]\s*(price\s*)?variant\b', None),
```

`[¢c]` consumes the "C" of "Cent", after which `variant` must match "ent Price Variant" — it fails.
Tested against all **63** real Star Wars #1 titles mentioning a 30/35¢ price:

| Pattern | Fires on |
|---|---|
| price-variant regex `:274` — the one meant for this | **1 of 63** |
| generic `\bvariant\b` `:283` | 31 |
| `\bnewsstand\b` `:281` | 5 |
| **nothing fires → leaks to the regular pool** | **30** |

Effective detection is therefore *"does the title contain the word 'variant'"*. Keyword reliability
against real titles: `price variant` 11/11 · `variant` 90/95 · `30 cent` 18/27 · **`35 cent` 11/22** ·
`35¢` 3/8 · `35c` 1/4 · `30c` 0/2.

**Connects to the existing variant-subtyping backlog item** — fixing detection without giving variants
their own comp pool would deepen the stripping problem, not fix it.

### 11.2 Non-variant contamination survives the filters

After variant exclusion, Star Wars #1 grade **9.8** still spans **$80 – $5,200** (median $3,150, n=15).
A 65× intra-grade spread in a supposedly clean pool means reprints and Whitman multipacks are reaching
it — some carrying **"REPRINT" in the raw title**, which the `is_reprint` flag and the
`LOWER(raw_title) NOT LIKE '%reprint%'` filter should both have caught. **That filter is not working**;
scope unmeasured.

### 11.3 Whatnot capture is dark

`market_sales` has taken **+1 row since 2026-07-01**. Not a bug — stated so it is not mistaken for a
live second source. Whatnot is now **7.9%** of the corpus and shrinking as a share with every eBay run.
Its title normalization also remains unusable for series matching (35 distinct `series` values) — see
L-SW-2026-014.

---

*Snapshot 1 generated read-only 2026-08-02; snapshot 2 appended read-only 2026-08-03. No code changed by
either. Queries reproducible against `DATABASE_URL_RO` (SELECT-only).*

---

# Snapshot 3 — 2026-08-14 — condition estimation: MEASURED, and NOT BUILT

**MOST RECENT CHANGE: condition estimation is DEFERRED behind Units 1a/1b/2, on measurement
rather than on cost.** Supersedes any framing of it as a budget question. Sequence is
unchanged: **1a → 1b → Unit 2 design → revisit condition against a clean pool.**

## What was run

A paired vision sample: **100 raw sold listings, each scored at s-l500 / s-l800 / s-l1600**
(300 Sonnet 5 calls, **$1.397**, estimate $1.390). Images fetched with Poisson pacing over
56 min as an approved one-off — see `CLAUDE.md` → *eBay Capture Safety*.

## Finding 1 — resolution is not the constraint; photo composition is

| arm | usable (high+med) | recovered from unusable | mean band shift |
|---|---|---|---|
| s-l500 | 80% | — | — |
| s-l800 | 83% | 4 / 100 | −0.02 |
| s-l1600 | 84% | 5 / 100 (vs 500) | −0.01 |

10× the tokens buys 4 points. 26 of 100 books changed band across the full range with **zero
net drift** — adjacent-band churn, not correction.

**The mechanism:** sellers photograph the cover art flat and cropped, so the **spine and
corners are not in the frame** at any resolution. Low-confidence reasons say so directly
(*"close-up cropped cover art, no spine or corners visible"*, *"angled distant photo"*,
*"flat frontal stock-style image"*). ⚠️ **This is a fact about eBay listings; no budget fixes
it.** Do not re-open this as a resolution or spend question.

## Finding 2 — the product is 2–3 bands, not 7

`high` confidence is **4–5 of 100 at every resolution**; `med` is ~78%. Per the rubric's own
definition `med` means *"can tell a used copy from a clean one, not VG from FN."* The model
is reporting it can deliver *beaten-up / mid / nice*.

## Finding 3 — ⚠️ ACCURACY WAS NOT MEASURED

The sample measured **stability and self-reported confidence only**. 74/100 unchanged across
resolution is equally consistent with *consistently right* and *consistently wrong the same
way*. Two signals point at optimism bias: **55–60% VF/NM flat across every price band**
(not a modern-books artifact) and **FR = 0** in all three arms against PR = 5. **Unresolved
until Mike's 50-cover blind ground truth returns.** If bias is confirmed it reaches past
CP-1 — the same model family does user grading.

## Finding 4 — vision is a better JUNK DETECTOR than grader

**7 of 100 sampled rows are not comics** — a fuel pump ($999.99), a Ford Coupe top rail
($250), a YoungLA Batman hoodie ($159), a Cadillac fender grill ($89.95), a steering column
($53.81), a carburetor ($51.19), an LED fog-light switch ($18.99). All seven returned
`conf: low` in **every** arm — a more reliable signal than the bands are. Evidence that a
cheap "is this even a comic" pass would work, if one is ever wanted.

**They are inert for valuation, and why matters:** only 5 of 44 such rows have both a
`canonical_title` and an `issue_number`, and the keys are `Genuine Holley` / `Nos Stewart
Warner` / `Vauxhall Corsa Power Ste` — nothing collides under normalized exact equality.
⚠️ **This retroactively vindicates the 2026-08-07 branch-B removal**: `Genuine Holley`
issue 12 is precisely the shape the LIKE fallback could have dragged into a real pool.

## Finding 5 — slab detection: a ceiling Unit 1b cannot see past

**6 of 100** rows with **no cert string in the title** are visibly in a graded case, stable
across all three arms (1 flip). 95% CI ≈ 3–13% → roughly **4,000–18,000 rows**. Unit 1's
regex can never catch these — there is nothing in the title to catch. **Scoping input for
1b, not a reason to change 1a.**

## Not changed by this

`title_year` remains NULL on **38.5%** of raw rows, worst (~48%) in the $50–199 bands,
unrecoverable (0.5% carry a year in the title), and a 16+ year pool span is the **majority**
state at 55% of rows. Unit 2 still cannot lean on year.

## Queue item — `canonical_title` repair: add "issue number absorbed into the title"

**Logged 2026-08-14, NOT chased.** Found by Mike in a fresh Werewolf by Night capture:

```
canonical_title = "Werewolf. 32"      issue_number = NULL
```

The issue number was absorbed into the title and the issue field left empty, so the row
cannot match any query for Werewolf #32 — the valuation path appends
`AND issue_number = %s` whenever a caller supplies an issue, which is the normal case.
**Captured today, so the normalization that produced it is live**, not historical residue.

Scoped rather than investigated (one query, so the queue item carries a denominator):

| shape | rows |
|---|---|
| `<word>. <number>` at end of `canonical_title`, `issue_number` NULL | **62** (58 distinct titles, first seen 2026-03-02, still occurring 2026-08-14) |
| any `canonical_title` ending in a number, `issue_number` NULL | **764** (630 raw) |
| **raw rows with `issue_number` NULL, all causes** | **22,623 of 214,285 — 10.6%** |

The 62-row shape is several distinct defects wearing one pattern:
- **`No.` / `Vol.` absorbed** — `The Flash No. 123`, `X-Men No. 14`, `Justice League
  International Pt. 1( Collection Vol. 70`
- **Barcodes absorbed** — `Spawn 1a. 4694840025`, `Cyberforce 1a. 1264042004`. eBay item
  specifics leaking into the identity key.
- **Quote characters retained** — `'shade, the Changing Man Omnibus'`,
  `"elfquest - Ayoooah! the Warning & The" - Vol. 2, No. 13`

⚠️ **Do not read 22,623 as a defect count.** A trade, omnibus or collection legitimately has
no issue number, and the examples above include several. The split between *legitimate no-issue*
and *parse failure* is unmeasured, and that measurement is the first task of the queue item —
not an assumption to build on. What is certain: **every one of those rows is excluded from any
issue-filtered valuation query**, correctly or otherwise.

Sits with the other `canonical_title` residue already recorded: 3,586 normalized titles carrying
non-ASCII (5,458 rows), 410 NULL/empty canonical titles, ~1,159 truncated at ingest. Still a
normal queue item, still **not** a prerequisite for Unit 2 — the article-split evidence that
briefly argued otherwise was retracted (see `docs/LESSONS.md` L-SW-2026-024).

---

*Snapshot 3: 300 vision calls + read-only DB queries. One code change shipped alongside
(`_backup_one_image` s-l500 → s-l1600), whose stated rationale this snapshot refutes — kept
for other uses, annotated in place. See `docs/LESSONS.md` L-SW-2026-024. s-l1600 verified live
by Mike 2026-08-14: Werewolf by Night capture at 1200×1600, ~7.7× the pixels, same request
count, capture unblocked.*
