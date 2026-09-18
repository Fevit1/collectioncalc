# Where We Left Off - Sep 17, 2026

## 2026-09-17 — 🔧 **LABEL TESTS BUILT (Q1 accepted: Annual and Vol-parse rows, not the reprint): filing, condition and edition tests in SQL on all four valuation pools, plus a slab-in-raw test; collection card renders null as a dash. Backend + one frontend file → `deploy` AND `purge`. In the working tree, pending the verifier's report and Mike's two commits. Backfills queued under item 16 with counts.**

**⚰️ SUPERSEDED: DEPLOYED AND VERIFIED (Mike, 2026-09-17 evening).** Live cell ASM #1 @ 4.5 `year=1963`: `graded_fmv`
9587.5, `graded_sample_size` 3, `graded_total_sales` 15, `raw_fmv` 4620.0, `raw_sample_size` 4, confidence medium,
basis supported, ROI +$4,583.50 — identical to the local run. Two readings of the live payload: `edition_used`
now says **1963–1963** (with the Annual #1 rows filtered, no 1964–1971 row survives in the cluster; the earlier
"1963–1971" span was the contamination itself), and the pool ratio is **111.1×** (was 45.2×) because the raw
pool lost its Annual and coverless rows. `sources.whatnot` 0, `sources.total` 19 = 15 graded + 4 raw.

**MOST RECENT CHANGE at write time (Rule 5): `routes/sales_valuation.py` (+~50) and `js/collection.js` (one template literal);
`git log -1` = `fdf70a1`, so nothing here is committed, deployed or purged. Verified locally on the read-only
database, twelve cells plus two spot checks. Supersedes the "proposed, not built" line of the Q1 entry.**

**The two corpus-wide counts Mike asked for, and the shape decision.**
1. **Slab word in the title with `graded = false`: 5,150 rows** (5,149 in the window), top titles Absolute Batman
   832, Amazing Spider-Man 435, Batman 173, X-Men 152, Spider-Man 134. **But only 165 carry a grade number after
   the slab word** (9.8 ×30, 9.4 ×21, 9.2 ×12 …) and 130 are negations ("not CGC", "raw"): the rest is "CGC
   candidate" language on raw listings. So a blanket slab-word exclusion would have thrown 5,000 real raw comps
   out of the raw pool; the filter is the 165 shape — slab word FOLLOWED by a grade — on the raw pool only.
   Backfill queued: set `graded = true` and parse the grade on those 165 (item 16).
2. **"Vol N M" with M ≠ issue_number: 996 rows** (995 in the window, 53 graded), top titles Silver Surfer 44,
   Amazing Spider-Man 37, X-Men 37, Daredevil 32. The looser count (any second number) was 8,931 because
   "Vol 1 1963" reads the year as the issue, and "#3 VOL. 1 8.5" reads the grade — the filter takes a 1–3-digit
   second number not followed by a decimal digit. The plain "Vol N = issue" count was 7,502, mostly correct
   #1s ("Ultimate Spider-Man Vol 1 #1"), so it was not the wrong-issue set. **"Annual" under a non-annual title:
   3,056 rows (297 graded)** — the third mechanism from the same book.
**Decision: filters now, backfills queued.** The counts are large enough that the filing errors matter corpus-wide
(996 + 3,056 + 165 rows), but the filters remove all of them from every valuation at query time today; the
backfills — re-parse `issue_number` for the Vol rows, re-file Annuals under "<Title> Annual", flag the 165 slabs
graded — are the collector-parse fix's data half and belong with it (item 16), not in this deploy.

**What changed.** Module constants (Postgres regex, `!~*`): `FILING_TITLE_PATTERN` (#N.N point issues),
`CONDITION_TITLE_PATTERN` (coverless / no cover / missing cover / cover missing / incomplete / not complete /
partial / page N only / NG / restored / qualified), `EDITION_TITLE_PATTERN` (golden record, marvel milestone, true
believers, 2nd/second print, treasury, marvel tales, omnibus), `SLAB_IN_RAW_PATTERN` (slab word + grade, raw pool
only), and `EBAY_FILING_SQL` (the Annual-under-plain-title and Vol-N-M clauses, which reference columns so they
are inlined, ebay queries only). q1/q2 take the three patterns as params (q2 also the slab test) plus the two
inlined clauses; q3/q4 (market_sales, where `raw_title` is the seller's lot label) take condition and edition on
`COALESCE(raw_title, '')`. `js/collection.js`: a null value renders "—" instead of "$0.00" (the multi-edition
saves land there). No fmv-endpoint change.

**Cells (local, RO database):** ASM #1 @ 4.5, year 1963 → **4.5 exact comps 4 → 3, median $9,587.50 unchanged;
graded_total 28 → 15; raw $260 on 35 → $4,620 on 4 rows.** ⚑ Mike's stated target was "$5,990 on 3 rows": that
figure came from my exploratory classification, which also excluded "hole" ("Amazing Spider-Man #1 1963 Marvel
Raw Low Grade Hole Key", $3,250). The built patterns follow the proposal list, which did not include "hole" — a
copy with a hole is a complete low-grade copy, which is a legitimate raw comp — so the fourth row stays and the
trimmed median of {1,871 · 3,250 · 5,990 · 20,000} is $4,620. Mike's call whether "hole" joins the condition
list; one word, no other effect. Standing cells: Spider-Man #1 @ 9.4 unchanged ($62 / 34 exact; raw 878 → 873
rows); New Mutants #98 unchanged; ASM #300 @ 6.5 $347.50 unchanged, raw $380 → $382 on 366 → 359 rows (the
filters took 7 raw and 3 graded rows: annual/Vol/condition words); X-Men #1 cells unchanged in state (1963: 33/34
→ 30/30 rows; 1991: raw $10.50 → $10.00); fmv ASM #300 mid 55 / raw 393 unchanged (fmv untouched). Spot checks:
Silver Surfer #4 (44 Vol-parse rows corpus-wide) prices normally, 59 graded / 90 raw; Moon Knight #2 raw_only.
Guardians of the Galaxy #3 returns fabricated — that is the broken-name filing ("Guardians the Galaxy", six
canonical spellings), pre-existing, not the filter.

**Verification agent (read-only, two-file diff):** every placeholder in the four queries aligned with its params
list, counted in textual order; the inlined Annual/Vol clauses render with the right backslashes, the `(?!…)`
lookahead is valid ARE, `IS DISTINCT FROM` on a text column is fine; the Annual guard keeps a title that is itself
an Annual; `EBAY_FILING_SQL` touches ebay queries only; `??` in collection.js is already the site's floor
(admin.html uses it). **Four pattern findings, all fixed and then PROVED ON THE SERVER with read-only SELECTs
against 39 title shapes (0 mismatches):** (1) bare `restored` matched "Unrestored" → `\yrestored\y`, same for
`qualified`; (2) bare `no cover` matched "1st Rhino cover" / "Domino cover" → `\yno cover\y`; (3) the edition
words had no canonical guard, so "Marvel Tales #1" or "Marvel Treasury Edition #28" would have lost every comp
→ the edition test is now `NOT (raw_title ~* P AND canonical_title !~* P)` on all four pools (pattern passed
twice); (4) the slab-in-raw test excluded "CGC 9.8 candidate" / "CGC 9.8 ready" raws → look-around for
candidate/ready/worthy/potential/contender/material, plus `(?![.0-9])` after the grade so the engine cannot
backtrack to "CGC 9" and pass the word test against ".8" (the first fix alone still matched — caught by the
server proof). Known false negatives, accepted: "CGC-9.8", "CGC SS 9.8", "Volume 1, #98", "Vol 1 No. 98".
Three stale placeholder-order comments rewritten. **Logged, not fixed (other renderers that print a number for a
null figure):** `js/collection.js:552` detail modal ("$0.00"), `:750` alert ("$null"), totals/sorts treat null as 0
(`:133`, `:240–274`); `js/ebay-modal.js:25,157` and `js/marketplace-modal.js:131,205` fall back to 9.99 — a
fabricated suggested price from a withheld figure — ROADMAP item 10.

**Ship block (Mike):** two commits — code: `routes/sales_valuation.py`, `js/collection.js`; records:
`docs/sessions/ROADMAP.txt`, `docs/sessions/WHERE_WE_LEFT_OFF.md`. `git log origin/main..HEAD` first. Push →
`deploy` → wait → **`purge` after the Pages build** (collection.js moved). Post-deploy: ASM #1 @ 4.5 `year=1963`
→ `graded_sample_size` 3, `graded_total_sales` 15, `raw_sample_size` 4, `raw_fmv` ≈ 4,620, `graded_fmv` 9587.5;
ASM #300 @ 6.5 → `graded_fmv` 347.5, `raw_sample_size` ≈ 359; the standing cells as before; after the purge the
served `js/collection.js` contains "withheld figure is saved as null".

## 2026-09-17 — 🔎 **Two open questions on the multi-edition unit answered + the refund count. One small backend change (the multi-edition verdict sentence) in the working tree → needs a `deploy`; the edition-label test is PROPOSED with measured numbers, not built.**

**⚰️ SUPERSEDED: the verdict sentence is DEPLOYED (Mike, 2026-09-17 evening). Q3 CLOSED by Mike: no make-good, since no
refund was owed. Q1 ACCEPTED as the Annual and Vol-parse rows, not the reprint → the label-test unit follows (next entry).**

**MOST RECENT CHANGE at write time (Rule 5): multi-edition unit deployed and verified (`cd22ba2`), purge pending the Pages build at
the flip. This entry adds one line to `routes/sales_valuation.py` (verdict sentence), pending Mike's commit + deploy.
Supersedes nothing.**

**Q1 — what contaminates the 1963–1971 cluster, and it is NOT the Golden Record reprint.** Every graded and raw row
in the cluster was read with its listing title. The cheap graded rows Mike named — 1.5 at $399, 2.5 at $515, 4.5 at
$820, 6.0 at $1,380/$1,399 — are **Amazing Spider-Man ANNUAL #1 (1964)** filed as issue 1; 7.0 at $142.70 is
"Amazing Spider-Man Vol 1 98" and 6.5 at $2,173 is "Vol 1 13" — the collector's issue parse took the "1" of "Vol 1".
Two more graded rows are RESTORED and QUALIFIED slabs. The raw pool is worse: 24 of 35 rows are Annual #1 or
"Vol 1 N", 8 are coverless / incomplete / partial / "page 14 only" / NG copies, and one "$20,000 CGC 6.5" slab sits in
the RAW pool with `graded = false` (a collector flag miss). "Golden Record" appears in 2 listings of this book all
year; "reprint" 12 and "facsimile" 32 are already excluded by the LIKE filters. So the year-gap rule cannot separate
these because they ARE 1963–1971 rows; the separation is by LABEL.
**Proposed — three label tests beside the year test, applied in SQL to BOTH pools (backend, deploy):**
(a) FILING: `\bannual\b`, `\bvol(ume)?\.?\s*\d+\s+\d+`, `#\d+\.\d` (the 2014 "#1.1") — a different issue filed
under this number; the real fix is the collector's issue parse (ROADMAP item 16), this is the belt.
(b) CONDITION: coverless / no cover / missing cover / incomplete / not complete / partial / page N only / NG /
restored / qualified — not comps for a complete unrestored copy; on the graded side restored and qualified are
different-priced labels.
(c) EDITION: reprint, facsimile (kept), golden record, marvel milestone, true believers, 2nd/second print, treasury,
marvel tales, omnibus.
**Measured effect on the 1963 book (365 d, cluster rows):** graded 28 → 15 clean; **4.5 exact comps 4 → 3
($9,587.50, $9,587.50, $10,723.80; median $9,587.50 — unchanged, the $820 Annual was the outlier the trim was
absorbing)**; raw 35 → 3 clean ($1,871, $5,990, $20,000) → **raw median $260 → $5,990, on THREE rows** — honest and
thin; `raw_sample_size` 3 will hedge it. Not built; the parse fix and these patterns belong in one unit with item 16.

**Q2 — which sentence the report renders.** Neither the server `verdict` nor `edition_note` is the tagline: the page
builds the tagline client-side (`app.html` ~2995–3036) from ROI and `verdict_basis`, and the basis sentence
(`js/verdict_basis.js` `basisLong.multi_edition`, "More than one edition shares this name … add or check the
year") sits in the badge expansion; `edition_note` is the separate edition line (now always shown). The server
`verdict` string — "Not enough recent sales to value this reliably" on X-Men #1's 480 graded sales — is API-only:
Mike saw it in the curl output, not on the page. **Built anyway:** `multi_edition` now writes its own sentence,
"More than one edition shares this name — add the publication year to price your copy", ahead of the thin-data
branch. One line, confirmed locally on X-Men #1 (no year) and unchanged on the controls. Pending commit + deploy.

**Q3 — the refund count.** `grade_submissions.credit_refunded = true`: **0 rows, all time.** Multi-edition valuation
lookups since the refund rule (2026-08-27), external: **3, all anonymous** (X-Men #1 ×2, ASM #14 ×1; `user_id`
null), so none was refund-eligible and **the shadowing bug cost no refund** — it would have, on the first
signed-in multi-edition lookup with a grading id. `lookup_demand` does not carry `grading_id`, so eligibility is
user + basis only. Since the 09-17 deploy: 0 multi-edition lookups yet.

## 2026-09-17 — 🔧 **MULTI-EDITION UNIT BUILT (approved shape + amendment): both pools carry the year, two triggers, the pools narrow to the caller's edition BEFORE pricing, figures withheld when nothing narrows them, the edition line prints whenever the detector fired. Backend + two frontend files: needs `deploy` AND `purge`. In the working tree, pending Mike's read of the verifier's report, then his two commits.**

**⚰️ SUPERSEDED the same day: DEPLOYED AND VERIFIED (Mike, 2026-09-17 evening).** Code `cd22ba2`, records `9fa4711`;
Render deploy done and the curl set verified by Mike; **`purge` PENDING the Pages build** at the time of this flip —
until it runs, slabworthy.com may still serve the old `app.html`/`verdict_basis.js` (the dash and the edition line
are frontend), so a report showing `$0` or no edition line before the purge is the cache, not the deploy.

**MOST RECENT CHANGE at write time (Rule 5): `routes/sales_valuation.py` (+~130/−15), `app.html` (two edits), `js/verdict_basis.js`
(one string); `git log -1` = `d900c5a`, so nothing here is committed, deployed or purged. Verified locally on the
read-only database, nine cells below. Supersedes the "shape for approval" entry below it.**

**What changed.**
- **Both pools carry the year:** q2 (ebay raw) selects `title_year`; q4 (market raw) `NULL::int AS title_year`.
- **Two triggers, either fires:** the existing year-gap split on the GRADED pool (gap > 15 y, >= 3 comps a side,
  trimmed-median ratio >= 20), OR the pool-level graded-to-raw trimmed-median ratio >= 20
  (`EDITION_GRADED_RAW_RATIO`). Pool-level rather than at the user's grade because it must be decided before the
  pools are narrowed and priced. The raw pool is NARROWED by the boundary but NEVER triggers on its own: the first
  cut ran the detector on it too, and ASM #300's raw pool split at 1988|2006 at 25.7x on reprints that slip the
  word filters, withholding the most looked-up book's figures for every caller without a year. Caught by the
  item-17 control cells before it left the working tree.
- **Narrowing, BEFORE pricing:** when the detector fired and `year` is on the request, both pools are cut to the
  cluster containing that year (<= the boundary's low year, or >= its high year; a year inside the gap narrows
  nothing; ratio-only trigger -> +/-15 years), year-unknown rows dropped. Everything downstream — exact/
  interpolated/raw FMV, `total_graded`, confidence, verdict tier, price curve, `sources`, the demand record — is
  computed from what is left. **Amendment confirmed by construction, with one precision:** confidence is a
  function of the GRADED counts only (`exact_count` >= 10 -> high; >= 3 exact or >= 10 graded -> medium; >= 3
  graded -> low); the raw pool size never enters it. After narrowing ASM #1 has 4 exact / 28 graded -> `medium`,
  and `high` needs ten same-grade comps of the narrowed edition. A 12-row (here 35-row) raw pool cannot make it
  high because raw is not an input; the raw figure's own hedge is `raw_sample_size`, which the client carries.
- **Fired, not narrowed -> `verdict_basis = 'multi_edition'` on EVERY method** (was `exact` only), ROI withheld
  (existing 08-08 rule), **`graded_fmv` and `raw_fmv` returned null, `confidence` null.** The page prints a dash
  for null figures (was `$0` via `|| 0`).
- **`edition_used` {year, year_low, year_high, graded_comps, raw_comps, trigger}, `edition_trigger`, and a
  server-side `edition_note`** — the page prints the note WHENEVER `edition_span` is true (it used to suppress
  it when the basis was multi_edition), preferring the server text: narrowed -> "Priced as the 1963–1971 edition
  from your publication year, on 28 graded and 35 raw sales…; if the year is wrong, so is this."; not narrowed
  -> "Add the publication year to price it". The `multi_edition` verdict string in `verdict_basis.js` now asks
  for the year instead of describing figures that are no longer shown.

**Cells (local, read-only DB, 365 d):**
| cell | before | after |
|---|---|---|
| ASM #1 @ 4.5, year 1963 | $16 raw / $9,588 slabbed / ROI —, basis multi_edition | **$260 raw (35 rows) / $9,587.50 (4 exact, 28 graded) / ROI +$8,943.50**, basis supported, confidence medium, edition 1963–1971 named, trigger year+ratio (64.8x, pool 45.2x) |
| ASM #1 @ 4.5, no year | same two figures, ROI — | **no figures**, multi_edition verdict, edition line asks for the year |
| X-Men #1 @ 9.0, year 1963 | fired; figures printed | $221 raw (34) / $22,387.50 interpolated (0 exact, 33 graded) -> basis interpolated, ROI withheld by the existing rule, edition 1963 named |
| X-Men #1 @ 9.0, year 1991 | | $10.50 raw (460) / $39 (4 exact, 231 graded), supported, edition 1991–2025 named |
| X-Men #1 @ 9.0, no year | | no figures, multi_edition |
| Spider-Man #1 @ 9.4, with and without 1990 | $18 / $62, 34 exact | **unchanged**, edition_span false |
| New Mutants #98 @ 9.4 | $299.49 / $375, 57 | **unchanged** |
| ASM #300 @ 6.5 | $380 / $347.50, 10 exact | **unchanged** (after the raw-trigger fix) |
| fmv ASM #300 @ 6.5 | mid 55, raw 393 | **unchanged** |

**Logged, NOT scoped (Mike):** (1) the 12 raw rows of 1990 Spider-Man #1 filed under Amazing Spider-Man #1
(`title_year` 1990, median $6.54) — ROADMAP item 16, title filing; after narrowing they sit outside the 1963
cluster, so they no longer touch this book's figures, but they are still wrong rows. (2) **The fmv endpoint is
still edition-blind** — no `year` reaches it from the overlay — **so the operator overlay keeps showing ~$16 on
ASM #1 until it is addressed**; ROADMAP item 19.

**Verification agent (read-only, three-file diff, re-read after the raw-trigger fix):** narrowing precedes
every consumer (grade buckets, exact/CI, interpolation, raw FMV, fallback, confidence, verdict, ROI, price curve,
sources, the demand record); no consumer still reads the pre-narrowing lists; no syntax/TDZ issue in any of the
three files; item-17 gating and the fmv endpoint untouched; the response is additive with three keys newly
nullable. **Its findings and what was done with each:**
- **Year inside the gap** (e.g. X-Men #1 with 1975) was told "add the publication year". FIXED: the note now
  says the year was received and falls between the editions on record (1963 and 1991); `edition_year_received`
  echoed in the response; the verdict string says "add or check the year". Cell added below.
- **Narrowed to an edition with too few priced sales** → the grade/era fallback fires and the note claimed the
  figure came from "N graded and M raw sales". FIXED: the note is built after the fallback with the estimated
  flag and says the figure is an estimate from grade and era, not from sales of that edition; `graded_comps`
  now counts non-variant rows only. (Every Whatnot row is year-unknown by construction, so a narrowed lookup
  prices from eBay rows only — stated, accepted.)
- **Ratio-trigger false positives:** the 1.5–5× premium claim was unmeasured. MEASURED read-only on twelve
  expensive keys: single-edition names top out at 4.5× (Tales of Suspense #39), Showcase #4 4.4×, Batman #181
  3.0×, Hulk #181 2.0×, ASM #129 1.6×, Giant-Size X-Men #1 2.0×, ASM #300 1.5×; the four that fire — ASM #14
  70× (147× on the endpoint's pool), Avengers #1 21×, Fantastic Four #1 193×, Hulk #1 72× — are all names with
  relaunches under them. Threshold 20 stands; Avengers #1 at 21× is the nearest correct fire. ASM #300's own
  pool ratio is 1.5×, so the reprint rows that broke the raw-pool trigger cannot reach it through the ratio.
- **`g` shadowed Flask's request `g`** in the price-curve loop (`for g in sorted(grade_buckets…)`), so the credit
  refund's `getattr(g, 'user_id')` read a grade float and the refund never fired — pre-existing, broadened by
  multi_edition now reaching every method. FIXED (one rename, `curve_grade`); **out of brief, flagged for Mike;**
  `tests/test_credit_refund.py` calls the helper directly and could not see it.
- Ratio-trigger wording: "differing in price by 147×" read as edition-vs-edition when it was graded-vs-raw.
  FIXED: the ratio-only note says "graded sales run N× the raw sales of this name, which points to more than one
  edition under it".
- `ROUGH ESTIMATE` badge beside two dashes → FIXED: `YEAR NEEDED` when the basis is multi_edition. Short basis
  string "these figures may be for the wrong one" → "figures are withheld until the publication year is known".
- Six stale "gated on 'exact'" comments and the page's "suppressed when the basis already says it" comment →
  tombstoned in place.
- **Logged, not fixed:** the collection card renders `raw_value || 0` as $0.00 for a null figure
  (`js/collection.js:457`, pre-existing; every multi_edition save now lands there) — ROADMAP item 10; in the
  withheld state `ci_95_*`, `price_curve`, `graded_sample_size`, `nearby_thin_comps` still carry un-narrowed
  values beside null figures (nothing renders them; noted).

**Two cells added to the standard set:** X-Men #1 @ 9.0 with `year=1975` → figures null, basis multi_edition,
`edition_note` contains "falls between the editions on record (1963 and 1991)"; ASM #14 @ 9.0 without a year →
null, `edition_trigger` "ratio", ratio ≈ 147; with `year=1964` → `graded_fmv` ≈ 7,679 blended, edition
1963–1967 named. Final local run of all twelve cells matched; the item-17 controls unchanged.

**Ship block (Mike), per the 08-16 conventions — TWO commits, then deploy AND purge (frontend files changed):**
1. `git log origin/main..HEAD` first.
2. Code commit, expected list exactly: `routes/sales_valuation.py`, `app.html`, `js/verdict_basis.js`. Stage ->
   `git diff --cached --stat` -> verify -> commit. Records commit: `docs/sessions/ROADMAP.txt`,
   `docs/sessions/WHERE_WE_LEFT_OFF.md`, worded commit-relative.
3. `git push` -> `deploy` (Render) -> wait for it -> **`purge` only after the Pages build has finished**
   (L-SW-2026-022).
4. **Post-deploy curl set (the standing set from item 17 plus the new multi-edition cells; GET; the fmv call
   needs `X-Operator-Key`):** ASM #1 @ 4.5 with `year=1963` -> `graded_fmv` 9587.5, `raw_fmv` ~260,
   `edition_used.year_low` 1963 / `year_high` 1971, basis supported, confidence medium, `edition_note` names
   1963–1971; without `year` -> both figures null, basis multi_edition, confidence null, `edition_note` present.
   X-Men #1 @ 9.0 with `year=1963` -> `edition_used.year_low` 1963, basis interpolated, `graded_fmv` ~22,387;
   with `year=1991` -> `graded_fmv` 39.0, supported; without -> nulls. Spider-Man #1 @ 9.4 -> 34 / 432,
   `edition_span` false. New Mutants #98 @ 9.4 -> 375.0 / 57. ASM #300 @ 6.5 -> 347.5, `edition_span` false.
   fmv ASM #300 @ 6.5 -> `tiers.mid.count` 55, `tiers.raw` present. After the purge: `app.html` served contains
   `edition_note`, `js/verdict_basis.js` served contains "Add the year". Counts drift with live capture; the
   multi-edition cells must show the STATE (nulls vs a named edition).

## 2026-09-17 — 🔎 **ASM #1 (1963) @ 4.5 Slab Report: raw $16 / slabbed $9,588 / ROI dash — REPORT ONLY, with the multi-edition proposal (shape for Mike's approval; no code). Priority over the capture-schedule unit.**

**MOST RECENT CHANGE (Rule 5): nothing built; the four answers below are from the pre-change (`22dcbe0`)
and live (`33a7362`) valuation modules run locally against the current rows, plus read-only SQL.
Supersedes nothing. The capture-schedule unit resumes after this.**

1. **`raw_fmv` did NOT move today.** Pre-change $15.59 (234 raw rows) vs live $15.50 (235 rows): the one-row
   difference is a sale captured since, not the deploy. Slabbed $9,587.50 (5 comps at 4.5) identical on both.
   The Slab Report reads the *valuation* endpoint, whose raw pool the item-17 change only widened by this
   book's two Whatnot rows. (The fmv endpoint's mid tier did move, $800 → $7,025, because its 232 ungraded
   rows left mid — but nothing on the report reads it.)
2. **Neither pool has a year or edition clause; the graded pool merely SELECTs `title_year` for the
   detector, the raw pool does not even select it.** The $16 is the median of 235 ungraded eBay rows of
   everything ever called "Amazing Spider-Man #1": by `title_year`, unknown 82 rows (median $34), 2014
   relaunch 65 ($10), 2025 relaunch 27 ($6), 1964 21 ($230), 2022 14 ($37), 1990 12 ($6.54 — Spider-Man #1
   filed under the wrong title), **1963 12 ($1,935)**, 2018 9 ($10), 2015 8 ($10), 1999 6 ($12). The 1963
   book is 12 of 235 raw rows. The graded pool is the mirror image: 1963 has 17 rows at ~$7,800 and the
   five 4.5 comps average $8,584.
3. **`edition_span` is TRUE for ASM #1** (ratio 64.8, `verdict_basis = multi_edition`, verdict "These
   figures may be for the wrong edition…"). What the detector tests (`_detect_multi_edition`, graded pool
   only, year-known non-variant rows): for every split between consecutive years with a gap > 15 years,
   both sides ≥ 3 comps and trimmed-median price ratio ≥ 20 → fires; the largest ratio is reported.
   **For Spider-Man #1 it is FALSE because the ratio fails, not the gap:** clusters are 1990 (407 rows,
   median $95) and 2009 (23, $521) with 2016/2019/2025 (11 rows) behind it; the only > 15-year gap is
   1990 → 2009 and the price ratio at that split is ~5×, under 20. Its $3 floor and $4,999 ceiling are
   not editions at all (item 18: lot-price slab rows and the unflagged Platinum variant).
4. **The ROI dash is the 2026-08-08 rule "ROI is withheld, not hedged, when `verdict_reliable` is
   false"** (`sales_valuation.py` ~:1277): `_detect_multi_edition` fired → `verdict_basis = multi_edition`
   → `verdict_reliable = false` → `slabbing_roi`/`roi_percentage` stay `None` → `app.html:2864` prints
   the dash. No ratio guard exists; the guard is the edition flag. The page still prints both dollar
   figures (`app.html:2751-2752` take `raw_fmv`/`graded_fmv` unconditionally) and, because the basis is
   multi_edition, HIDES the separate edition note (`:3130`) and relies on the verdict sentence. So the
   report says "may be for the wrong edition" under two numbers that are 600× apart.

**PROPOSAL (shape only; backend, `routes/sales_valuation.py`; deploy; Mike to approve before the file list):**
- **A. Both pools carry the edition.** The raw queries SELECT `title_year` (they do not today) and
  `_detect_multi_edition` runs on the UNION of graded and raw year-known rows, so the raw pool is
  clustered by the same boundary. When the user's `year` param is present (the grading page sends it),
  BOTH pools are restricted to the cluster containing that year (boundary from the detector; year-unknown
  rows dropped, since they cannot be placed) and the response says which edition was priced
  (`edition_used: {year_low, year_high, comps}`); the 1963 ASM #1 then prices from 12 raw and 17 graded
  1963-cluster rows, not from 2014 relaunches. Without a `year`, no restriction — see C.
- **B. Two triggers, either fires.** Keep the year test (gap > 15 years at a split, ≥ 3 comps a side, ratio
  ≥ 20) and add a **graded-to-raw ratio test: `graded_fmv / raw_fmv ≥ 20`** at the user's grade. A slab
  premium on one edition is 1.5–5×; 20× says the raw pool is a different book. ASM #1 is 600×; Spider-Man
  #1 does not trip either (correctly: its problem is item 18).
- **C. When it fires and the year cannot narrow it, the report prints NO dollar figures** — the verdict
  reads "More than one edition shares this name; give the year to price it" (the page already carries the
  input), `raw_fmv`/`graded_fmv` are returned as null with `edition_span` true, and ROI stays withheld.
  When the year DOES narrow it, the figures print with the edition line and the ordinary hedges apply.
  This retires the state where two numbers 600× apart sit under a caution sentence.
- **D. Post-deploy curls gain a multi-edition cell, permanently:** `Amazing Spider-Man #1 @ 4.5` with and
  without `year=1963` (without: no figures, `edition_span` true; with: figures from the 1963 cluster,
  `edition_used` present), and `X-Men #1 @ 9.0` (the originating case) the same way, beside the three
  cells from item 17.
- Not in this shape: the fmv endpoint (extension overlay; no year available there), and item 18's two
  mechanisms.

## 2026-09-17 — 📊 **eBay capture schedule — READ-ONLY measurement for Mike's decision (two tables, delivered in chat; the docx NOT regenerated).**

**MOST RECENT CHANGE (Rule 5): measurement only; no file under `docs/` changed except this record; the
2026-08-17 weekly list stands until Mike cuts a new one. Supersedes nothing.**

**Method.** The list was parsed from `docs/EBAY_CAPTURE_WEEKLY.docx` (2026-08-17): 146 title/issue
cells (the three Absolute ranges expanded, #1–20 / #1–12 / #1–12; Thursday is cut in the doc). "Capture
week" = an ISO week in which ≥ 1,000 `ebay_sales` rows were written; the last four are 08-17 (7,830 rows),
08-24 (22,980), 09-07 (15,130) and 09-14 (3,229 — the current, partial week: the Monday/Tuesday cells show 0
for it because those days' captures had not run by 09-17). Per cell: rows held (lots excluded), graded,
graded 9.4+, new rows per capture week, and the average. **Thresholds stated:** WEEKLY where the average
is ≥ 3.0 new rows per capture week and the pool is not saturated; MONTHLY (saturated) where ≥ 20 graded
9.4+ are already held; MONTHLY (thin) otherwise. Broken-name titles get no cadence until the filing is
fixed. Result: 74 weekly, 37 monthly-saturated,
29 monthly-thin, 2 with no rows at all
(Marvel Two-in-One 1, Saga of the Swamp Thing 1 — the filing has these under another name, or the
searches never ran), 4 on the broken-name list.
**Flagged — on the weekly list AND on the doc's own broken-name list:** Captain Marvel 26, Web of
Spider-Man 18 and 19, Legion of Super-Heroes 1. Web of Spider-Man and Legion now show rows under BOTH
the fixed and the broken filing (the 09-03 normaliser unit repaired part of the "of" family), as do
Conan the Barbarian, Tomb of Dracula, Omega the Unknown, Batman The Killing Joke, The Darkness, The Wicked
+ The Divine and Shade the Changing Man: 12 cells split across two canonical names. Those are
item-16 filing work, and their held counts here are the SUM of both names.
**Demand table.** `lookup_demand`, `endpoint = 'valuation'`, external users only, since 2026-07-21 (Mike's
date; the fmv endpoint's 5,167 rows are the operator's own overlay lookups and were excluded): 223
lookups, 176 distinct title/issue pairs, 141 with fewer than 20 graded comps in 365 days (the threshold
stated). Top 30 delivered in chat after excluding list cells and broken-name titles. Caveat: demand is
thin — the top pair has 4 lookups and most have 1 — and the demand rows carry "The Amazing Spider-Man"
where the corpus files "Amazing Spider-Man", joined here on a leading-"The"-stripped key; other spelling
drift (X-men / The X-Men / Uncanny X-men) is visible in the table and is the same filing family.

## 2026-09-17 — 📋 **Post-deploy follow-ups on the valuation unit (report only) + Spider-Man #1 price-curve anomaly queued (item 18). Nothing built, nothing written to the database.**

**MOST RECENT CHANGE (Rule 5): item 17 live and verified (`33a7362`); this entry adds three answers and one
queue item; the eBay capture-schedule unit follows in its own entry. Supersedes nothing.**

1. **Variant-disclosure count: it DROPS.** `excluded_variant_count` is taken from the graded pool, and a
   vision-graded or null-source variant row no longer enters that pool (the raw pool never held variants).
   Magnitude: **70 such rows in the 365-day window** across all books (read-only count). `variant_excluded*`
   fields and `sources.whatnot` fall by the per-book share; nothing priced changes, since variants were
   never priced. Documented in the module header and q4 comment.
2. **ASM #300's two graded Whatnot rows match neither endpoint's title clause:** their `canonical_title` is
   the DOM lot label ("Bid", "30 Pre-Bids") and the valuation clause matches `canonical_title`/`title`/
   `series` by normalised exact equality — `title` is "Amazing Spider-Man" but the clause did not take it
   here (live `sources.whatnot` 0). Logged on ROADMAP item 16 (title filing) as the field evidence.
3. **`raw_fmv` on the fmv endpoint is BY DESIGN the average of the user's grade tier** (the "raw comic at
   this grade" number; `slabbed_fmv` is the next tier up), not the ungraded pool — `tiers.raw.avg` is the
   ungraded pool. **Nothing renders the fmv endpoint's `raw_fmv`:** the Whatnot overlay reads only
   `tiers.low/mid/high/top`; the grade report page's `raw_fmv` comes from the *valuation* endpoint, a
   different field with the same name. So: pre-existing, by design, misleading name on a field with no
   reader → **copy-audit list** (ROADMAP item 10, strings half).

**Spider-Man #1 price curve (queued as item 18, ranked with item 10):** 9.6 tier minimum $3.00 and 9.8
maximum $4,999.95 in one window, `edition_span` false. Both ends traced read-only: the **$3 floor is
`market_sales` rows 9533 and 9499, `slab_label` 9.6 at $3 under the label "Spiderman Comic"** — lot-price
Whatnot sales carrying a scan-read slab grade (pre-2.47 data; `slab_label` still counts as graded, by
Mike's rule 5) — and **the $4,999.95 ceiling is the 1990 PLATINUM EDITION, not flagged as a variant:
39 Platinum rows, 5 flagged.** The span detector is not the gap: the Platinum shares 1990 with the
newsstand run (519 of 1,090 graded rows are `title_year` 1990; 2009 has 33), so there is no year split
to find. Two mechanisms, two fixes: a "platinum/gold/silver edition" rule in the variant detector
(backend, both tables), and a floor on graded comps from lot-labelled Whatnot rows (or a `slab_label`
that is scan-read vs label-read — the split already logged for 2.48.0).

## 2026-09-17 — 🔧 **SOURCE-AWARE VALUATION BUILT (ROADMAP item 17 + item 10's mid-tier dump): `routes/sales_valuation.py` reads `grade_source`, gates graded pools on it, routes excluded and ungraded rows to the raw pool in both endpoints. In the working tree, pending Mike's commit, push and `deploy` (backend). Branches E and F recorded in the 2.47.0 entry.**

**⚰️ SUPERSEDED the same day: DEPLOYED AND VERIFIED (Mike, 2026-09-17).** Code `33a7362`, records `d900c5a`;
Render deploy done; live cells: Spider-Man #1 `graded_sample_size` 34, `graded_total_sales` 432; New Mutants
#98 `graded_fmv` 375.0, sample 57, unchanged; ASM #300 fmv `tiers.mid.count` 55, `tiers.raw` present with 393
rows, `sources.whatnot` 0. All three match the local AFTER run. Item 17 SHIPPED; item 10's mid-tier half SHIPPED.

**MOST RECENT CHANGE at write time (Rule 5): one backend file changed, `routes/sales_valuation.py` (+51/−16); `git log
-1` = `84524fc` (2.47.0), so NOTHING of this is deployed and prod still serves the old tiers. Verified
locally by running both endpoints from the working tree against the READ-ONLY database (a minimal Flask
app registering only the valuation blueprint; `DATABASE_URL` pointed at `DATABASE_URL_RO`), before and
after, six cells. Supersedes the item-17 "scoped, not built" line.**

**What changed (both endpoints):**
- market_sales queries SELECT `grade_source`; ebay rows carry the constant `'ebay_listing'` (`%s` param in
  q1, a literal in the fmv f-string) — the listing's own statement; no vision exists on the eBay path.
- Graded pool (q3): `grade_source IS NOT NULL AND grade_source <> ALL(%s)` with
  `EXCLUDED_GRADE_SOURCES = ['vision_cover']` (module constant; `dom` and `slab_label` still count).
- Raw pool (q4): `grade IS NULL OR grade_source IS NULL OR grade_source = ANY(%s)` — excluded and
  null-source rows are ungraded sales of the book, not lost.
- `api_sales_fmv`: new `'raw'` bucket; the loop sends ungraded, null-source and excluded rows there
  instead of `'mid'` (queue item 10's dump, fixed for BOTH tables — ungraded eBay rows were in mid too);
  `'raw'` is the last fallback in every `tier_priority` list so a book with only ungraded sales still
  returns a number; response gains `tiers.raw` (additive; the extension reads low/mid/high/top only).
- No discount path; no rename; no change to the title match.

**Before → after, local run on the RO database, 365-day window (valuation endpoint | fmv endpoint):**
| cell | valuation BEFORE graded_fmv (exact n, graded n, raw n; whatnot rows) | valuation AFTER | fmv BEFORE mid (n / avg) | fmv AFTER | fmv raw_fmv |
|---|---|---|---|---|---|
| Amazing Spider-Man #300 @ 6.5 | 347.5 (10 exact, 386 graded, 366 raw; wn 0) | 347.5 (10 exact, 386 graded, 366 raw; wn 0) | mid 448 / $459.71 | mid 55 / $401.83 · raw 393 / $467.81 | 459.71 → 401.83 |
| Amazing Spider-Man #300 @ 9.4 | 699.95 (77 exact, 386 graded, 366 raw; wn 0) | 699.95 (77 exact, 386 graded, 366 raw; wn 0) | mid 448 / $459.71 | mid 55 / $401.83 · raw 393 / $467.81 | 1059.91 → 1059.91 |
| Spider-Man #1 @ 9.4 | 55.0 (43 exact, 446 graded, 864 raw; wn 16) | 62.0 (34 exact, 432 graded, 878 raw; wn 16) | mid 1020 / $82.56 | mid 9 / $171.16 · raw 1025 / $80.7 | 258.35 → 264.83 |
| Invincible #1 @ 9.4 | 3609.0 (5 exact, 34 graded, 44 raw; wn 2) | 3609.0 (5 exact, 34 graded, 44 raw; wn 1) | mid 51 / $1812.22 | mid — · raw 51 / $1812.22 | 3508.78 → 3508.78 |
| Batman #3 @ 8.0 | 50.98 (0 exact, 0 graded, 8 raw; wn 0) | 50.98 (0 exact, 0 graded, 8 raw; wn 0) | mid 7 / $36.72 | mid — · raw 7 / $36.72 | 36.72 → 36.72 |
| New Mutants #98 @ 9.4 | 375.0 (57 exact, 334 graded, 288 raw; wn 0) | 375.0 (57 exact, 334 graded, 288 raw; wn 0) | mid 320 / $311.16 | mid 14 / $261.14 · raw 306 / $313.45 | 611.36 → 611.36 |
Readings: **ASM #300** — the valuation endpoint did not move (its title match finds no Whatnot rows for
this book: their `canonical_title` is the lot label, item 16), the fmv endpoint's mid tier went from 448
rows to 55: it had been 88% ungraded rows, the item-10 dump; mid avg $459.71 → $401.83. **Spider-Man #1
(Whatnot-heavy, all 11 Whatnot grades `vision_cover`)** — 14 graded rows left the graded pool for raw
(432 vs 446; raw 878 vs 864), exact comps at 9.4 fell 43 → 34, graded_fmv $55 → $62; fmv mid 1,020 → 9.
**Invincible #1** — one Whatnot row left; note `sources.whatnot` 2 → 1: a `vision_cover` row that is a
VARIANT drops out of both pools, because the raw query excludes variants (verifier asked to confirm).
**Batman #3 (Whatnot-only in fmv)** — all 7 rows were ungraded/vision: mid 7 → raw 7, and `raw_fmv`
$36.72 unchanged via the new last-fallback. **New Mutants #98 (eBay-only)** — valuation endpoint
UNCHANGED ($375.00, 57 exact), as intended for a listing-stated pool; fmv mid 320 → 14 because 306
ungraded eBay rows had been in mid — item 10, not provenance.

**Verification agent (read-only, on the diff):** every `%s` placeholder in the four modified queries
matched to its params in order (the list → `ARRAY[...]` adaptation and the f-string literal both checked);
`_detect_multi_edition` and every other consumer of the graded pool unaffected beyond the intended
shifts; the fmv endpoint cannot now return a number where it returned none, and `raw` never outranks
a graded tier; empty-pool branch untouched; brief items 1–5 all implemented. **Two findings, both
taken as records, not code:** (1) a `vision_cover` or null-source row that is ALSO a variant now sits in
neither pool — the raw pool has never held variants — so it no longer feeds the variant-disclosure
count or `sources.whatnot` (Invincible #1's 2 → 1 is exactly this); header and q4 comments now say so.
(2) The Whatnot overlay reads only `tiers.low/mid/high/top`, so a book whose sales are all ungraded now
shows four `N/A` slots and no verdict where it used to show the mid average; the number survives in
`raw_fmv`. Rendering the `raw` bucket is a one-line extension change for a later build (2.48.0
candidate), logged, not scoped. Three stale comments it flagged were fixed (placeholder order after the
new first `%s`; the raw-pool wording; the fallback wording).

**Deploy block (Mike), per the 2026-08-16 conventions:**
1. `git log origin/main..HEAD` first (a committed-but-unpushed change is unshipped).
2. Expected file list for the code commit: `routes/sales_valuation.py` ONLY. Stage → `git diff --cached
   --stat` → verify → commit. Records (`CLAUDE.md`? no — `docs/sessions/ROADMAP.txt`,
   `docs/sessions/WHERE_WE_LEFT_OFF.md`) in their own commit, worded commit-relative.
3. `git push` → `deploy` (Render; auto-deploy is OFF) → wait for the deploy → **verify with the endpoint
   that exercises the change, not `/health`:**
   `curl -s "https://collectioncalc-docker.onrender.com/api/sales/valuation?title=Spider-Man&issue=1&grade=9.4&days=365"`
   → `graded_sample_size` **34** (was 43), `graded_total_sales` **432** (was 446);
   `curl -s -H "X-Operator-Key: <key>" "https://collectioncalc-docker.onrender.com/api/sales/fmv?title=Amazing%20Spider-Man&issue=300&grade=6.5&days=365"`
   → `tiers.mid.count` **55** (was 448) and a `tiers.raw` key present;
   `…/api/sales/valuation?title=New%20Mutants&issue=98&grade=9.4&days=365` → `graded_fmv` **375.0** and
   `graded_sample_size` **57**, unchanged (the eBay-only control).
   Live capture moves counts by a few rows per day; a small drift is fine, a return to the BEFORE
   figures means the deploy did not take.
4. No `purge` (backend only).

## 2026-09-16 — 📋 **Four provenance questions answered + the source-aware valuation SCOPED (report only; nothing built, nothing written to the database). 2.47.0 confirmed in the banner (`84524fc`); relabel A–D ran (table in the 2.47.0 entry).**

**MOST RECENT CHANGE (Rule 5): CLAUDE.md flipped to 2.47.0 confirmed. Two more corpus branches proposed
below (E: 91 blanket-9.2 `dom` rows; F: 164 pre-provenance graded rows) — NOT run, Mike's call. Supersedes
nothing else.**

**Q1 — the 94 `dom` rows do not all stay.** 91 are grade 9.2 from ONE seller family ("Single", "Single #391"
… "A"), over six days 01-26 → 03-18, 41 distinct labels on 01-26 alone: a blanket condition text applied to
every lot, not a per-book grade. **Branch E: NULL grade and source where `grade_source = 'dom' AND grade =
9.2` → before dom 94, after dom 3.** The three survivors are real seller-stated decimals in the label
("Strange Tales #179 5.0", "Secret Wars #1 8.5🔑", "Invaders #2 8.5 🔑", all 02-07).
**Q2 — the 164 graded rows with no source: all 01-24 → 01-26, the corpus's first days, written by the
extension build BEFORE `grade_source` existed, by the same loose regex.** 159 are the same seller's blanket
9.2 ("Single #319…"), 2 are 10.0 from "#10" labels ("2-PACK #10", "MISTER MIRACLE #10"), 2 are 4.0, 1 is 7.5;
no image, no slab, `grade_from_title` null on all. Same junk class. **Branch F: NULL grade and source where
`grade IS NOT NULL AND grade_source IS NULL` → before 164, after 0.** Otherwise they count in tiers with no
way to weight them.
**Q3 — 2.47.0 writes `dom` for a seller-stated decimal with no slab** ("$10 start Batman 5 NM 9.4" → 9.4,
`dom`; "graded 8.5" → `dom`). Distinguishable from `slab_label` (grade adjacent to a slab word, from label OR
scan) and `vision_cover` (scan, raw) today. Two naming defects for a later 2.48.0, shape only: rename `dom`
→ `seller_label` (and relabel the survivors), and split `slab_label` into label-read vs scan-read, since one
name currently covers two provenances.
**Q4 — junk-series blocklist (shape only, under ROADMAP item 16):** no such list exists anywhere in the
repo. Shape: `lib/normalizer.js` gains `JUNK_SERIES` (exact, lowercase: box, aaa, aaa awesomeness, single,
singles, comics, comic, bulk, lot, random start, pre-bid, bid, plus any single-letter label); `parse()`
checks the label's leading token before "#" against it and returns `series: null` so `makeKey` yields no
key; `content.js` leaves the record in with the raw label as title and `series` null. The backend
`title_normalizer.py` needs the same list or `canonical_title` still says "Box" (that half is a deploy).
Test: "Box #18" and "AAA awesomeness #19" parse with no series key and record with `series` null.

**Valuation scope — source-aware tiers (shape; NOT built; backend → needs a `deploy`).**
- **Files:** `routes/sales_valuation.py` only, both endpoints: `api_sales_valuation` (`market_graded_query`,
  `market_raw_query`) and `api_sales_fmv` (`market_query`). Neither selects `grade_source` today.
- **Step 1:** add `grade_source` to the market_sales SELECTs; ebay rows get a constant source
  `'ebay_listing'` — the eBay path has NO vision anywhere (the collector has no vision code; the route
  parses `grade_from_title`), so all 42,255 graded ebay rows are listing-stated. **Answer to the open
  question: no `ebay_sales` row carries a vision-derived grade.**
- **Step 2, exclude null-source grades:** `AND grade_source IS NOT NULL` on the graded query. After branch F
  it excludes nothing today; it is the guard for future rows.
- **Step 3, `vision_cover`:** (a) EXCLUDE from graded tiers — in `api_sales_valuation` widen the raw pool to
  `grade IS NULL OR grade_source = 'vision_cover'` so the rows still count as ungraded comps rather than
  vanishing; in `api_sales_fmv` note that ungraded rows are already dumped into the mid tier (`sale_grade
  is None → tiers['mid']`, queue item 10), so "exclude" there means "lands in mid" until that dump is fixed
  in the same unit. (b) DISCOUNT — carry a weight (0.5) per row into the median; `compute_median` /
  `percentile_trim` take plain price lists, so this needs a weighted-percentile helper.
- **ASM #300 mid tier (4.5–7.9), measured read-only:** Whatnot has TWO mid rows — `vision_cover` 7.0 at **$5**
  and `slab_label` 6.0 at $205; eBay has 88 at median $377.50 (IQR $325–$425). Combined, every option lands at
  ~$375 with n 89–90, because the eBay pool dominates. Market-only: as-is and discount keep the $5 "7.0"
  comp (a lot-price sale with a scan grade — a wrong comp at any weight); exclusion leaves the one slab
  comp at $205. The example argues for (a): a discount keeps a comp that should not be in a graded tier.
- Not changed by this scope: the `title`/`series` match (`qualifier_title_clause` over `title`,`series`,
  `canonical_title`) — on these rows `canonical_title` is "Bid" / "30 Pre-Bids" / "Comics", the DOM lot
  label, so the match rides on the extension's `title`, which item 16 owns.

## 2026-09-16 — 🔧 **2.47.0 BUILT (grade provenance): the record's grade comes only from the scan bound to the sold listing or from the sold listing's own label with grade context; `seller_verbal` retired; the `manualGrade` leak closed. In the working tree, pending Mike's commit and a reload showing 2.47.0 in the banner. Relabel SQL handed to Mike (NOT run).**

**MOST RECENT CHANGE (Rule 5): `content.js` + `manifest.json` carry 2.47.0; `git log -1` = `c644764`
(2.46.0, reloaded and confirmed), so 2.47.0 is NOT committed and 2.46.0 runs until the banner shows
2.47.0. CLAUDE.md and ROADMAP item 2 flipped to "pending". Supersedes the grade-provenance entry's
"proposed shape (not built)". The corpus relabel is Mike's to run; branch counts re-read after his
cleanup (they moved by his deletes/nulls).**

**What changed (content script only; POST payload unchanged; `WV/` untouched):**
- `numericGrade` no longer reads `manualGrade`. `manualGrade` remains a DISPLAY value for the overlay
  verdict (its comment now says so); the sale path reads the scan's grade from `vision` — the object
  `visionForSale` bound to the sold listing — or a label grade, nothing else.
- `gradeSource`: the `seller_verbal` branch is gone. Scan grade → `vision_cover` / `slab_label` by the
  scan's slab type; label grade → `slab_label` when the label carries a slab word, else `dom`.
- A label grade (`parsed.grade`, the extension normaliser's regex) is accepted only with grade context:
  a decimal `d.d` in the title/condition text, or a slab word, or "grade"/"graded". The normaliser's
  bare `10|9.x|…` pattern had been reading the dollar figure (67 corpus rows at grade 10 from "$10 starts").
- Manifest and banner 2.46.0 → 2.47.0.

**Harness (real `content.js`, stubbed page, no network, no production write):**
| case | result |
|---|---|
| designed flow, scan 8.0 raw on A, A's sold text after the switch | A recorded, grade 8, `vision_cover`, image |
| LEAK: E unsold → switch to D → manual scan on D (9.6) → E's sold text | E recorded with **grade null, source null**; the scan withheld (`DROP mismatch … kept for the current listing`) — on 2.46.0 this row would have carried 9.6 as `seller_verbal` |
| "$10 starts #14", no scan, own sold text | grade **null**, source null |
| "Comics #37" with condition text "9.2", no scan | grade 9.2, `dom` |
| "ASM 300 CGC 9.8", no scan | grade 9.8, `slab_label`, slab CGC |
Two pre-existing things the harness showed in passing, not scoped: a `$10 starts` title passes
`isValidSale` (the `badTitles` list has no dollar rule though `isGarbageTitle` does), and the
normaliser gives the series "300" for "ASM 300 CGC 9.8" (the issue number becomes the title) — both
item 16.

**Verification agent (read-only, on the first 2.47.0 cut):** `manualGrade` has no remaining path into the
record (its one read is the overlay verdict, short-circuited by `parsed.grade` in both callers);
`seller_verbal` exists only in a comment; payload untouched; no TDZ. **Its real finding: the label-grade
gate was presence-based, not adjacency-based** — "Spawn #1 CGC 9.8" recorded grade **1** as `slab_label`
because the normaliser's `N cgc` pattern captures the issue number and the gate, seeing CGC, accepted it;
"$10 start … NM 9.4" kept the 10 because a decimal existed elsewhere; "ungraded" matched the grade word.
**Fixed in the same build:** the record's label grade now comes from the TEXT with three tied patterns,
in order — the number adjacent to a slab word; the number after a word-bounded "grade/graded"; the
first decimal `d.d` after dollar amounts are stripped — range-checked 0.5–10; the normaliser's own
grade output is no longer read by the sale path at all. Harness on the final file: "Spawn #1 CGC 9.8" →
9.8 `slab_label`; "$10 start Batman 5 NM 9.4" → 9.4 `dom`; "Ungraded raw copy, $10 start" → null;
"Box 44, $9.5 start" → null; "Comics #37" + condition "9.2" → 9.2 `dom`; scan grade 8.0 → `vision_cover`.
Accepted residuals, stated: "NM 10" and "NM 10.0" raw labels record no grade (an integer needs a slab or
"graded" tie); the extension's `series`/`title` still come from the substring aliases ("$10 start
Batman 5 NM 9.4" was titled "New Mutants" via `'nm'`) — ROADMAP item 16, not this unit.

**RELABEL RAN (Mike, 2026-09-16, branches A–D; plus `series = NULL` on 11033/11035/11037/11038).**
`grade_source` on `market_sales` (source = whatnot), rows / rows with a grade:
| grade_source | before | after | moved |
|---|---|---|---|
| (null) | 5,534 / 164 | 6,037 / 164 | +503 = C 436 (seller_verbal, no image → grade+source NULL) + D 67 (dom grade 10 → NULL) |
| seller_verbal | 3,277 / 3,277 | 0 / 0 | −3,277 = A 2,613 + B 228 + C 436 |
| vision_cover | 1,912 / 1,912 | 4,525 / 4,525 | +2,613 (A) |
| slab_label | 231 / 231 | 459 / 459 | +228 (B) |
| dom | 161 / 161 | 94 / 94 | −67 (D) |
The 164 null-source rows WITH a grade were present before and unchanged after (question 2, below).
**Branches E and F approved and RUN by Mike 2026-09-16 (after the four-questions entry):** E — `dom` blanket
9.2 → NULL: **dom 94 → 3**; F — grade with no source → NULL: **164 → 0**. So after E+F: (null) 6,128 rows /
0 with a grade (6,037 + 91), `dom` 3, `vision_cover` 4,525, `slab_label` 459, `seller_verbal` 0. Every
remaining graded Whatnot row now carries a source.
2.47.0 reloaded and confirmed in the banner the same afternoon (`84524fc`); CLAUDE.md flipped.

**Relabel SQL as handed over (counts re-read 2026-09-16 after the cleanup; superseded by the table above):**
A `seller_verbal` + image + slab raw/null → `vision_cover` (2,613); B `seller_verbal` + image + slab set →
`slab_label` (228); C `seller_verbal` + no image → grade and source NULL, Mike's call (436); D `dom` +
grade = 10 → grade and source NULL (67); E `dom` other grades → keep (94). D is the `dom` predicate
Mike asked for; C and D are the two branches that null a grade. Statements in the chat report.

**Ship block (Mike):** `git add CCExtensions/whatnot-valuator/content.js
CCExtensions/whatnot-valuator/manifest.json CLAUDE.md docs/sessions/ROADMAP.txt
docs/sessions/WHERE_WE_LEFT_OFF.md` → commit → push. **No `deploy`, no `purge`.** Reload the unpacked
extension, **refresh or close every open Whatnot tab** (CLAUDE.md reload procedure), verify
`v2.47.0` in the banner. Field tell: no new `seller_verbal` rows after the reload;
`grade_source` on new rows is only `vision_cover`, `slab_label`, `dom` or null.

## 2026-09-16 — ✅ **2.46.0 SHIPPED and confirmed; phantom candidates ruled legitimate; two cleanup queries handed to Mike (NOT run); ROADMAP item 16 ranked second; grade-provenance measurement — REPORT ONLY: `seller_verbal` is a false label on every one of its 3,303 rows, and the grade rides outside the ownership guard.**

**MOST RECENT CHANGE (Rule 5): 2.46.0 committed `c644764` 2026-09-16 14:44 -0700 and reloaded, confirmed
by Mike in the overlay banner. CLAUDE.md flipped and given the reload procedure (refresh or close every
Whatnot tab after an unpacked reload; verify the banner, not only the extensions page). Working tree
after this entry: this file, CLAUDE.md, ROADMAP.txt, plus the two pre-existing modified files. Nothing
deleted in the database; the delete statements below are Mike's to run.**

**Phantom candidates 11048 / 11100 (the strict same-label/opening-price shape since the 2.44.0 reload):
both carry vision and a scan-derived grade → legitimate quick sales. No delete.** Logged on ROADMAP item 2.

**WHAT RAN (Mike, 2026-09-16 afternoon — supersedes the plan wording below):** duplicate delete: 125 before
(two rows had arrived since the count of 123), 92 after, 33 removed. Captain America block: the four
title/issue corrections ran BEFORE the amended report, so Mike nulled `grade` and `grade_source` on
11033/11035/11037/11038 separately; the three deletes (11036/11039/11042) ran. Count 90 at that point with
live capture ongoing (91 at the next read). **Still wrong on the four ids: the `series` column** ('Captain
America' ×3, 'Iron Man' on 11035) — the extension normaliser's alias output, written beside `title`;
`slab_type`, `variant`, `is_key` are null/false (they were label-derived, not vision-derived, because no
vision was attached at record time), so nothing else needs clearing. Statement handed to Mike, not run:
`UPDATE market_sales SET series = NULL WHERE id IN (11033, 11035, 11037, 11038);`

**Cleanup 1 — the 33 same-second duplicate pairs (18:57–20:33 PDT, 2026-09-15).** Two writers on one
stream (the orphaned 2.44.0 content script beside the reloaded one; the reload procedure above is the
fix). Rule: keep the row with the EARLIER `source_id` (the millisecond timestamp), delete the later.
Listing query, delete statement and before/after counts are in the chat report of this date; the delete
targets 33 explicit ids. Not run.

**Cleanup 2 — the "Captain America" rows on stream 2257274543 (16:37–17:00 PDT, 2026-09-15).** Eight
rows, not nine: 11032 is a genuine Captain America #114 (the label says so) and stays. The extension's
normaliser (`lib/normalizer.js`, `combined.includes('ca')`) produced the title; the BACKEND normaliser
wrote `canonical_title` from the label independently and got it right where the label names a book.
Correctable from the label: 11033 → Batman #191, 11035 → Batman #616, 11037 → Critical Hits Comics #1,
11038 → Ghost Rider #15. Delete: 11036 and 11039 (label "$3 - $10 Random Start #4/#5" names no book) and
11042 (label "M"). Statements in the chat report. Not run. The grades on all eight are `seller_verbal`
with no image — see the provenance finding: those grades are not the seller's and not these books'.

**ROADMAP item 16 ranked (Mike): SECOND, beside item 2, above item 3.** Same class (wrong-book records in
`market_sales`, indistinguishable afterward), on the no-vision path, which is the majority path: 6,175
of 11,024 Whatnot rows carry no image. Mitigation already in the corpus: `canonical_title` is written
from the label by the backend and was right where `title` was wrong.

**Grade-provenance measurement (report only; NOT scoped, NOT built). Read of `content.js` + the table.**
- **The code path.** `grade_source` is decided in `checkForSale`: `seller_verbal` when `manualGrade` is
  set ("User typed it (probably from seller)"), else vision (`vision_cover` / `slab_label`), else `dom`.
  **There is no grade input anywhere in the overlay.** `manualGrade` is assigned in exactly one place,
  `applyVisionResult` (`manualGrade = result.grade`), i.e. by a scan; it is reset on a new item and after a
  record. So every `seller_verbal` row is a VISION grade under a label that says a human said it.
- **The numbers.** 3,303 rows are `seller_verbal` — 57.1% of the 5,783 graded Whatnot rows, and the
  largest provenance class. Since the 2.46.0-era reload: 73 of 118 graded rows. Only 23 of 3,303 equal
  `grade_from_title` (the label's own grade), so they are not label grades either.
- **The grade escapes the ownership guard.** 2.44–2.46 bind title/issue/slab/variant/key/image to the
  scanned listing and withhold them on a mismatch — but the GRADE rides on `manualGrade`, which the
  guard never clears. A withheld or dropped vision still leaves its grade on the record, labelled
  `seller_verbal`. Upper bound on such leaks: `seller_verbal` with no image = **442 rows all-time (434
  in January, 8 since the 09-15 reload)**; the eight Captain America rows are in the 8 (grades 4, 9.2,
  10, 9.6, 9.2, 7.5 on books the scan never saw). An image can also be missing because the R2 upload
  failed, so 442 is a ceiling, not a count. `vision_cover` with no image: 226, all January.
- **`dom` (Mike's question 2): 161 rows, 0 with a slab word in the label, 0 equal to the backend's
  `grade_from_title`.** Written by `checkForSale` when the extension normaliser's loose regexes find a
  number in the label or condition text: `/grade[d]?\s*(\d+\.?\d*)/` or a bare `10|9.x|…|0.x`. The
  bare pattern matches the dollar figure — **67 rows carry grade 10, from "$10 starts", "$3 - $10 Random
  Start", "Bulk of 10 comics"** — and 91 rows carry 9.2 from a seller whose condition text said 9.2 on
  every lot. So `dom` = "a number the label-parser found", sometimes a seller's stated grade, often a
  price. Predicate for the relabel: EXCLUDE `dom` from the seller_verbal → vision relabel (they are not
  vision), NULL the grade where `grade_source='dom' AND grade = 10` (67 rows: no seller writes "10" as a
  grade on a $10 lot), keep the remaining 94 as `dom`. Both parsers belong to ROADMAP item 16.
- **Rows 11159 / 11160 (today, 2.46.0, 14:47 PDT, 19 s apart, no vision): plausibly REAL sales, both
  mis-titled.** "Singles #33" → title "Green Lantern" via the `'gl'` alias inside "sin**gl**es"; "AAA
  awesomeness #19" → title "AAA awesomeness" (no alias hit; the label minus its counter). $3 and $5 on a
  singles stream at a fast-auction cadence, recorded once each under the 2.46.0 won-text rule — nothing
  in the shape says phantom. All-time: 32 rows whose label starts "AAA", 18 titled "AAA awesomeness", 33
  titled "Box". **"AAA awesomeness" is a lot-label series exactly like "Box" and belongs on the same
  junk list** — but that list is not in this repo: `title_normalizer.py` has no junk list and the
  extension's `badTitles` has neither "box" nor "aaa"; if the list is Mike's own, add both there.
- **Downstream.** The valuation reads `grade`, not `grade_source` (no reference in
  `routes/sales_valuation.py`), so the mislabel is invisible to FMV today and the LEAKED grades are
  not: a wrong-book grade at a wrong-book price feeds the tiers.
- **Proposed shape (for Mike, not built).** Extension, one unit: take the grade from `vision` only, clear
  `manualGrade` wherever vision is withheld or dropped (mismatch, unsold expiry, late scan), and stop
  writing `seller_verbal` until a real input exists — the label then means what it says. Corpus, one
  statement each, counts above: relabel `seller_verbal` → `vision_cover` where an image exists and
  `slab_type` is raw/null (2,633), → `slab_label` where a slab is set (228); for the 442 with no image,
  either NULL the grade (unowned) or leave and flag — Mike's call. A `grade_source` value the reader can
  trust is CP-1's input (`docs/technical/CP1_STATE_OF_PLAY.md` already lists provenance as one of the
  inconsistent notions of confidence).

## 2026-09-16 — 🔧 **2.46.0 BUILT (Mike's brief): a sold text is consumed by the record it produced; the ring buffer merges on flush; teardown listeners once via `pagehide`. In the working tree, pending Mike's commit and an unpacked reload showing 2.46.0. Repo-only, no deploy, no purge.**

**MOST RECENT CHANGE (Rule 5): `content.js` + `manifest.json` under `CCExtensions/whatnot-valuator/`
carry 2.46.0; `git log -1` = `ba6f42c` 2026-09-15 17:05 -0700 (2.45.0, which Mike reloaded and confirmed),
so 2.46.0 is NOT committed and 2.45.0 is what Chrome runs until the reload shows 2.46.0. Supersedes the
"scoped into 2.46.0" lines of the two-findings entry below. Three side findings from the post-reload
rows are logged in this entry and as ROADMAP items 15–16; none is scoped.**

**What changed (content script only; `WV/` untouched; the POST payload unchanged):**
1. **Won-text consumption.** `checkForSale` computes a signature of the sold text — the auction
   FOOTER's first line carrying "won"/"sold" (`won:<winner>`), and the page-wide "X won!" match only
   when the footer has none, so a pinned chat line cannot become every sale's signature. After a record
   the signature is consumed; the same text is ignored until it changes or disappears for a poll.
   A one-poll blink inside the 30 s debounce re-consumes rather than re-arming (verifier finding).
   **Deliberately NOT scoped to the listing id:** a banner persisting across a real listing change
   would otherwise record the next lot at its opening price on the new id. Known limit, stated in the
   code: the same winner on consecutive lots with no banner gap in between registers once.
2. **Ring buffer read-merge-write.** Each flush reads the stored array, unions it with the tab's own
   (dedupe on the entry's JSON), sorts by `t`, caps at 500, writes; a read that errors skips the write
   rather than clobbering the other tabs' history. **Merged size bound unchanged: 500 entries, ~210 B
   each for ASCII, ~450 B worst case → under 110 KB typical, under 250 KB worst, of 10 MB.** Two tabs
   on the same stream double-count that stream's events (different `t`); an analysis caveat, not a loss.
3. **Teardown once, `pagehide`.** `startWatching` re-runs on every tab-visible resume; the three
   listeners are now registered once, and `unload` (refused by whatnot.com's permissions policy, the
   two violations Mike saw) is `pagehide`, which does fire. Nothing lost: `unload` never ran.
4. Manifest and banner 2.45.0 → 2.46.0.

**Harness (real `content.js` on the stubbed page; no network, no production write; cache-busted script
tags after one run was found to be on a stale copy):**
| case | result |
|---|---|
| won-text: lot 1 hammers $65, banner stays, price reset to $1 on the same id at +3 s, one-poll blink at +12 s, banner still on at +38 s (past the 30 s debounce and the 10 s same-id release) | **1 record at $65, none at $1**; "sold text cleared" logged once at the blink |
| banner clears, lot 2 with the SAME winner hammers $22 | recorded ($22) — the gap re-arms |
| title flap on a fixed id, auto-scan on (pre-refinement 2.46.0 file) | 15 re-render events, 1 scan, 0 drops, sale carries the vision |
| price flap $9/$4 after a real switch (same) | 1 scan, 0 drops, sale carries the vision, "using previous" at $9 |
| sale while current → real switch → next sale 3 s later (same) | recorded for the new listing, 0 drops |
| mismatch, fallback-id, unsold-expiry by switch with vision (same) | all fired with the expected lines |
| unsold-expiry by timeout with vision, late-scan (final file) | fired: `… (timeout 10000 ms); dropped its vision "Thor"`, `DROP lateScan … (result "Venom")` |
The teardown once-guard cannot be exercised in the harness (no visibility change); the verifier traced it.
The refinements between the two harness passes touched only the consumed check and `flushTiming`.

**Verification agent (read-only, final diff):** brief items 1–4 implemented; payload untouched; no TDZ;
merge cap and sort correct, entries pushed mid-flush are kept; `pagehide` fires where `unload` never did.
Its findings, all taken: footer-first signature (a stable "won!" earlier in the page would have starved
later sales), blink re-consume inside the debounce, no write on a failed read. Its remaining caveats:
two tabs flushing at once still last-writer-wins for that write (each re-merges on its next flush; a tab
whose stream ends inside its last 2 s window can lose those entries); display names with spaces share a
signature on the surname; a footer that only ever says "sold" carries no winner and starves same-lot
follow-ups until it clears.

**Phantom query, run read-only on 2026-09-16 (results in the chat report):** 123 Whatnot rows since the
2.44.0 reload; the strict same-label/opening-price shape returns 2 candidates (11048, 11100), both WITH
vision and `seller_verbal`, which argues against the timeout phantom (that path had dropped vision).
The 10 s hold is not in the database, so the DB shape is "same label as the row before, ≤ $5, cheaper
than it, within 5 min"; a true phantom is that plus no vision, and a later row with the same label at a
higher price. The SQL is in the chat report and in `scratchpad` history; it deletes nothing.

**Side finding 1 — same-second duplicate pairs, 18:57–20:33 PDT on 09-15: 33 pairs** (11066/11067 …
11142/11143), identical title, price and second, `source_id` differing by a few ms, both with vision.
Two writers on one stream: two tabs open on it, or the pre-reload 2.44.0 content script surviving
beside the reloaded one (an unpacked reload orphans old content scripts; `fetch` to the API still
works from an orphan while `chrome.*` does not). Mike knows which. `ON CONFLICT (source, source_id)`
cannot catch it because `source_id` is a millisecond timestamp. Backend-side dedup is a separate unit.
**Side finding 2 — "Captain America" under unrelated labels** (nine rows 16:37–16:54 on stream
2257274543, no vision, issue copied from the label; also "Iron Man #616" under a Batman #616 label):
the extension normaliser matches series aliases as substrings, `'ca'` included. Wrong-book by a
different mechanism, on exactly the rows where vision did not attach. ROADMAP item 16.

**Ship block (Mike):** `git add CCExtensions/whatnot-valuator/content.js
CCExtensions/whatnot-valuator/manifest.json CLAUDE.md docs/sessions/ROADMAP.txt
docs/sessions/WHERE_WE_LEFT_OFF.md` → commit → push. **No `deploy`, no `purge`.** Reload the unpacked
extension; **expected version in `chrome://extensions`: 2.46.0**; banner `v2.46.0`; the errors page
should show no more unload violations. Field tells: "sold text cleared" between lots in the console;
the timing buffer keeps every open tab's `sw`/`flap` entries after a multi-tab evening.

## 2026-09-16 — 🔎 **Two findings from the 2.44.0 error page and the stored ring buffer (Mike's three questions, answered 09-15 late; logged here before the 2.46.0 build). Both pre-existing in shape; both scoped into 2.46.0 by Mike.**

**MOST RECENT CHANGE (Rule 5): 2.45.0 committed and reloaded (confirmed by Mike on the extensions page,
2026-09-15 evening); the two DROP entries and two unload violations he saw predate 2.45.0's first write
(every stored buffer entry is 2.44.0-shaped, and the trace's line 707 is 2.44.0's line for the unload
listener; 2.45.0 has it at 777). 2.46.0 is the next unit, scoped by Mike: consume the won-text after a
record; merge the ring buffer on flush; teardown listeners once via pagehide. Supersedes the 2.45.0
entry's "first field check" as the next step.**

**Finding A — the ring buffer loses history across tabs (2.44.0 and 2.45.0 alike).** Each content-script
instance loads the stored array once, then writes its own copy on every flush; with two or three
streams open the last writer wins. Seen in the store: three instance chains, the largest (69 entries,
16:44) overwritten by a 6-entry one at 16:45. Consequence: the Underdog drop Mike saw cannot be tied to
a chain (2.44.0 stored ids only and the title appears nowhere in the store); every surviving chain shows
zero real id changes, so on the evidence it was another flap hold. Fix (2.46.0): read, merge by
timestamp, write at each flush.

**Finding B — persistent won-text becomes a phantom record on a price reset.** Stream id 2257274543
repeats for half an hour: a same-id hold, then a "sale" using the current listing exactly ~10 s later,
`usedPrev=0`. That is the previous lot's won-text still on screen when the seller resets the price for
the next lot: the stale hold dedupes it for 10 s (`saleKey` equals `lastSaleCheck`), the release exposes
the new price reading, and a record goes out at the next lot's OPENING price. 2.45.0 has the same path
through the silent same-id release; 2.43.0 deduped those away (and lost real next-lot sales instead).
Root: the extension never marks a sold text as consumed. Fix (2.46.0): after a record, remember the
winner text and ignore it until it changes. Item 13's family; the DB-side check is the phantom query
in this entry's sibling (2.46.0 entry).

**Unload listener, for the record:** ours, in `startWatching`, pre-existing since 2.43.0 (lines 583–584
there). Chrome refuses `unload` handlers under whatnot.com's permissions policy and logs the violation at
registration; the listener never runs; nothing else is affected. Its job (clear the poll interval at
teardown) is done by the document dying and by the `beforeunload` listener beside it. Two entries because
`startWatching` re-registers all three listeners on every tab-visible resume. 2.46.0 item 3: register
once, `pagehide`.

## 2026-09-15 — 🔧 **2.45.0 BUILT (Mike's go on the proposed fix): hold, expiry and vision drop keyed on the listing ID, never the change key. In the working tree, pending Mike's commit and an unpacked reload showing 2.45.0. Repo-only, no deploy, no purge.**

**MOST RECENT CHANGE (Rule 5): `content.js` + `manifest.json` under `CCExtensions/whatnot-valuator/`
carry 2.45.0; `git log -1` = `4908ed4` 16:48 -0700 (Mike's records commit), so the extension change is
NOT committed and 2.44.0 (`d1d10dd`) is what Chrome has loaded until the reload shows 2.45.0.
Supersedes the "proposed, NOT built" line of the false-fire entry below. Lesson candidate
L-SW-2026-031 added to `docs/LESSONS.md` (index line + entry, awaiting Mike's confirmation).**

**What changed (content script only; `WV/` untouched; the POST payload unchanged):**
- The watcher already computed `listingIdChanged` beside `isNewItem`; the 2.44.0 logic was attached
  to the wrong one. Now a **real switch** (id changed) is the only place the unsold rule fires: a held
  previous whose id is neither the listing ending nor the one arriving is dropped and counted; a
  same-id snapshot of the ending listing is refreshed, not counted. A **flap** (key moved, id did
  not — title reading or price scrape) keeps 2.43.0's snapshot semantics (hold when nothing is held
  or the held one is this id; a held previous with another id is left alone) and touches no counter
  and no vision.
- `expireHeldPrevious`: a same-id snapshot past 10 s is released silently (console line, no counter,
  no vision). `dropHeldPrevious` additionally never drops vision owned by the listing on screen.
- **A listing whose sale is recorded is not re-held at the next real switch** (`lastSoldListingId`)
  — a pre-existing 2.43.0 loss the harness reproduced: a sale detected while current, then the next
  listing's sold text inside the hold window resolved to the already-sold previous and was deduped by
  `lastSaleCheck`; 2.44.0 also counted that stale hold as unsold. **Verifier caught the regression in
  the first cut of this guard** (a same-label relist whose sold text lands after the switch away was
  misattributed to the listing after); fixed: the guard is suspended when a same-id price reset was
  seen since that sale (`relistedSinceSale`), so a second copy is held and its late sold text
  attributes to it.
- Timing ring buffer: `['sw', t, fromId, toId, fromTitle, fromPrice, toTitle, toPrice]`,
  `['flap', t, id, fromTitle, fromPrice, toTitle, toPrice]`, `['sale', t, msSinceRealSwitch,
  usedPrev, soldId]`; `lastSwitchAt` moves only on `sw`, so the bound is measured from real switches
  only. Writes coalesced to one per 2 s; pending queue capped; `getTiming` guarded. Size: ~210 B/entry
  ASCII, ~450 B worst case → under 110 KB typical, under 250 KB worst, of 10 MB. 2.44.0's entries
  (from == to) are flaps mislabelled as switches: ignore them when reading the bound.
- **Bound unchanged: provisional 10 s.** Still unmeasured — no real switch with sold text after it has
  been recorded in the field yet.
- Manifest and banner 2.44.0 → 2.45.0.

**Harness (same stubbed page, real `content.js`; no network, no production write):**
| case | result |
|---|---|
| title flap, fixed id, auto-scan on, 6.5 s | 13 re-render events, 1 scan, **0 drops**; sale recorded with the vision title, image, under the real label |
| price flap $9/$4 scrape, fixed id, after a real switch | 0 price-reset log lines (scan skipped by the 30 s same-id rule), 1 scan, **0 drops**; sale recorded with vision and image |
| same-id snapshot past 10 s | one "released same-id snapshot" console line, counter unchanged |
| sale while current → real switch → next sale 3 s later | recorded under the NEW listing "using current listing" (2.43.0/2.44.0 deduped it away) |
| same-label relist: sold $3 → reset $1 → real switch → sold text 2 s after | recorded under the relisted listing "using previous listing", 0 drops; **price recorded $1** — see queue item 14, pre-existing |
| mismatch | switch to E (unsold) → switch to D → manual scan on D → E's sold text: E recorded without vision, `DROP mismatch … (kept for the current listing)` |
| unsold-expiry (switch) | D, unsold, dropped at the next real switch with its vision "Superman" |
| fallback-id | F1 → F2 (fallback ids) → scan F2 → F1's sold text: `DROP fallbackId … (kept …)` |
| unsold-expiry (timeout) | scan C → switch to G → 11 s: `… (timeout 10000 ms); dropped its vision "Thor"` |
| late-scan | scan held on G → switch to K → resolve: not applied, "Scan outdated", `DROP lateScan` |
One harness note for the record: the second listing's auto-scan is skipped by the pre-existing 10 s
scan cooldown when listings change inside 10 s, so the counter sequences use the Scan button.

**Verification agent (read-only, on the final diff after the relist guard was messaged to it):**
(a) no same-id path fires the unsold rule, the counter or a vision null; (b) no path nulls vision owned
by the current listing; (c) designed flow traced, A's vision attaches and A's record goes out, also
when A flapped before ending; (d) multi-copy reset: no counter, no vision touch; (e) an id-flap
(Apollo alternating two ids) produces no drops and is strictly better than 2.44.0, though it churns
the buffer; (f) cap holds, storage-unavailable is safe — its size-bound and write-frequency notes and
the unbounded pending queue are fixed as above; (g) no TDZ; (h) brief fully implemented. Its one
regression finding (the relist case) is fixed and harness-confirmed.

**Pre-existing, found on the way, NOT scoped (ROADMAP item 14):** the held snapshot's price is the
last "new item" reading, not the final one, and the price scrape can catch the shipping figure.

**Ship block (Mike):** `git add CCExtensions/whatnot-valuator/content.js
CCExtensions/whatnot-valuator/manifest.json CLAUDE.md docs/LESSONS.md docs/sessions/ROADMAP.txt
docs/sessions/WHERE_WE_LEFT_OFF.md` → commit → push. **No `deploy`, no `purge`.** Reload the unpacked
extension; **expected version in `chrome://extensions`: 2.45.0**; banner `v2.45.0`. First field check:
the overlay's `unsold-expiry` should stay at 0 across a flapping listing, and `ValuatorDebug.getTiming()`
should show `flap` entries carrying the two title/price readings, which decides title-flap vs
price-flap. The Hulk stack observation (item 13) still stands as the confirmation for the storm.

## 2026-09-15 — ⚠️ **2.44.0 FIELD FINDING (Mike's first-stream observation): the `unsold-expiry 1` was a FALSE FIRE. Cause: a listing-KEY change on an UNCHANGED listing id ("flap") is treated as a listing switch. Consequence: the live 2.44.0 build can drop vision for the listing that is still running. Fix proposed below, NOT built — awaiting Mike's call.**

**MOST RECENT CHANGE (Rule 5): 2.44.0 is committed (`d1d10dd` 16:22 -0700) and reloaded, confirmed by
Mike; ROADMAP item 2's awaiting clause tombstoned and CLAUDE.md's version line flipped. Then Mike's
observation was checked against the timing ring buffer, pulled read-only from the extension's own
`chrome.storage.local` LevelDB files (profile `Default`, extension `ajlbioldbphabbminilahhenhapnkfkj`,
newest of 11 stored versions, 21 entries, 16:33:43–16:36:12). Supersedes the "expected gap under
~1.5 s" reading of the 10 s bound as MEASURED — it is not yet measured, see below. The bound is unchanged.**

**What the buffer shows.** Every `sw` entry has `from == to`: seventeen "switches" and not one of them
changed the listing id. Two ids appear, `ListingNode:2310331993` (one entry, then a page navigation —
Mike moved streams; a fresh content script records no `sw` for its first listing) and
`ListingNode:2309812493` for everything after 16:33:50. The `sw` at +6.6 s on 2309812493 held that
listing as "previous" of ITSELF; no sold text within 10 s; the timeout fired at ≈+16.6 s. **That is
Mike's `unsold-expiry 1`: not a real unsold lot, not the first listing after page load (that one holds
nothing), but the 10 s timeout on a held copy of the listing still on screen.** Later, at +143.4 s to
+148.4 s, the key flapped EVERY 500 ms poll (eleven `sw` entries), each one a "switch with a held
previous" → `unsold-expiry (switch)` per tick. The overlay in Mike's screenshot was early; the counter
will have run well past 1 by the time he read this.

**Why the key flaps with the id constant.** `isNewItem` (content.js watcher) is `listingKey !==
currentItemId || priceDropped`, where `listingKey = id + '-' + title` and the title is the DOM scrape
(`getAuctionInfoFromDOM`), merged over the Apollo listing. A title that alternates between two DOM
readings, or a price scrape that alternates with a smaller dollar figure in the same footer
("Shipping is $4.85" beside "$9" satisfies the >50 % drop and ≤ $20 rule), flips the key without the
listing changing. 2.43.0 already had this — its own comment resets scan tracking "only when the actual
listing ID changes (not on title fluctuations)" — and it was harmless there because `previousListing`
was merely overwritten. **2.44.0 made it harmful: `dropHeldPrevious` fires on a held previous at a
switch, and drops held vision when `forListingId === held.id` — which is the CURRENT listing's id when
the "switch" is a flap.** Net: on a flapping listing, the auto-scan's vision is dropped before the sale,
and the sale records WITHOUT vision, i.e. under the lot label. That is a data-loss regression against
2.43.0 (which would have attached it correctly on the same-id path), not a wrong-book record. Whether
the +16.6 s expiry took vision with it is in Mike's console (`DROP unsoldExpiry … ; dropped its vision`
suffix), not in the buffer.

**Which entry the buffer cannot tell, and the instrument gap.** The `sw` entry carries ids only, so
title-flap vs price-flap is not decidable from it; both are ruled in. And no REAL id change has been
recorded yet, so the switch→sold-text gap the 10 s bound guesses at is still unmeasured; the +7.5/+8.5 s
`usedPrev=1` gaps are flap→sold-text on one listing and must not be read as switch gaps.
**Bound unchanged per Mike: no measurement, no change.**

**Also in the buffer, pre-existing, logged under item 13's family:** sales detected at +96.9 s and
+126.9 s on the same listing, exactly 30.0 s apart, `usedPrev` 1 then 0 — the persistent sold text
re-firing after the debounce because the flapping key changes `saleKey`. Apollo-mode twin of the Hulk
stack storm; the stable fallback id does not touch it.

**Proposed fix (2.45.0 — behaviour Mike can see changes, so minor, not patch), NOT built:**
1. **Hold and expiry keyed on the listing ID, not the key.** `previousListing` is still captured on
   every `isNewItem` (2.43.0 semantics, keeps the price-reset snapshot for a multi-copy relist), but
   the unsold-on-switch rule, the vision drop and the `unsold-expiry` counter apply ONLY when
   `held.id !== listing.id`. A same-id hold expires by timeout silently (debug line, no counter) and
   never touches vision.
2. **Never drop vision owned by the listing that is current now**, in `dropHeldPrevious` as well —
   the guard already in `visionForSale`, applied symmetrically.
3. **Timing entries distinguish `sw` (id changed) from `flap` (id unchanged) and carry the key
   parts** — title cut to 40 chars and price — so the cause becomes decidable and the bound can be
   measured from real switches only. Entry grows to ≤ ~170 bytes; 500 entries stays under 90 KB.
4. Manifest and banner 2.44.0 → 2.45.0. Content script only. `WV/` untouched.
**Not proposed:** changing `isNewItem` itself (the flap also re-runs `processListing` and the FMV
lookup every poll — pre-existing since 2.43.0 or earlier, out of this unit), or the bound.

**Decision for Mike:** 2.44.0 as loaded trades wrong-book records (the queue-item-2 defect, closed) for
missing-vision records on flapping listings (new). Options: (a) build 2.45.0 now, (b) reload 2.43.0 until
it is built, (c) capture with 2.44.0 and accept label-only records on flapping lots for the evening.
The buffer's `flap` vs `sw` split in (a) is also what makes the bound measurable.

## 2026-09-15 — 🧭 **QUEUE ITEM 2 BUILT: whatnot-valuator 2.44.0 — held vision and held previous listing now have an owner and an expiry. In the working tree, pending Mike's commit and an unpacked reload. Repo-only: no deploy, no purge.**

**MOST RECENT CHANGE (Rule 5): the 2.44.0 build of the Whatnot valuator is in the working tree (four files
under `CCExtensions/whatnot-valuator/`), verified in a stubbed-page harness with zero network and zero
production writes, verification agent run. `git log -1` = `93d0274` 2026-09-14 23:18 -0700, so NOTHING of
this is committed; the next observable step is Mike's commit, then a reload showing 2.44.0 in
`chrome://extensions`. Supersedes the 09-14 close's "next unit: queue item 2 — report first". The report
was delivered in chat (three rounds: mechanism + measurement, then step 1/2 measurements, then the build).**

**The defect, as read.** All state lives in `content.js`. `appliedVisionData` (set :276 in 2.43.0) and
`previousListing` (set :522) were cleared ONLY in the branch that had just recorded a sale (:966, :1007).
There was no end-of-listing detection at all: the reader skips Apollo listings marked ENDED/SOLD
(`apollo-reader.js:146`), so an unsold end was invisible, and the only sale signal is page text "sold"/"won".
Three carry paths, one root: (1) vision across an unsold listing — the next sale gets the previous
book's title/issue/grade/variant/slab and R2 image with its own price; (2) previousListing across an
unsold listing — if the won text is seen while the next listing is current, the record is the previous
book's title AND price, and the real sale is lost; (3) a scan that returns after its listing's sale was
recorded stamps the listing after. `background.js` holds nothing relevant (it mirrors recorded sales into
storage); the POST is built in `lib/collectioncalc.js` `insertSale` and its shape is UNCHANGED.

**Shape shipped (Mike's brief 09-15, two refinements made from the read and stated here):**
- **Stable DOM-fallback id** (`apollo-reader.js` `makeFallbackId`): `dom-<seller>:<lot label>`, replacing
  `'dom-' + Date.now()` at both fallback sites. Decided from the step-1 measurement (below).
- **Vision is stamped with the listing id at scan start** (`handleVisionScan` → `result.forListingId`)
  and attaches at record time only when it equals the sold listing's id (`visionForSale`).
  ⚑ Refinement 1: on a mismatch the vision is WITHHELD from that record, but DISCARDED only if it does not
  belong to the listing that is current now. The common mismatch is "next listing already scanned, then
  the previous listing's sold text lands"; discarding there would strip vision from the next sale. The
  harness showed the kept vision attaching to its own sale afterwards.
- **Unsold expiry**: at a listing switch, a still-held `previousListing` means no sale was detected across
  the whole listing that just ended → dropped, logged. Plus a **provisional 10 s timeout**
  (`HELD_PREVIOUS_EXPIRY_MS`) checked every poll before sale detection.
  ⚑ Refinement 2: held vision is dropped with the expired listing ONLY when it was scanned for that
  listing. Vision scanned for the listing now moving into the held slot survives, because the designed
  flow detects that listing's sale AFTER the switch; dropping it would lose vision on every sale that
  follows an unsold listing.
- **Late scan**: the scan handler re-reads `currentListing.id` when the result arrives and discards a
  result whose listing changed while it ran ("Scan outdated").
- **Four counters** in the overlay line `drops · mismatch n · fallback-id n · unsold-expiry n · late-scan n`,
  each with a `[Valuator] DROP <kind>: …` console line naming both listings. `fallback-id` is the
  mismatch sub-bucket where either id is a fallback id — kept separate so a label-derived id that
  flickers mid-listing shows up as its own signal. `ValuatorDebug.getDropCounts()`.
- **Timing ring buffer** `valuator_timing` in `chrome.storage.local`: `['sw', t, fromId, toId]` per switch,
  `['sale', t, msSinceSwitch, usedPrev]` per detected sale; ids cut to 40 chars; **≤ ~106 bytes per entry
  as JSON, capped at 500 entries → under 60 KB** of the 10 MB quota (harness measured 54 bytes max, 652
  bytes for 19 entries). `ValuatorDebug.getTiming()`. Its purpose is to replace the 10 s guess with data.
- **Manifest 2.43.0 → 2.44.0; console banner 2.41.2 → 2.44.0** (the banner had been stale since 2.42).
- ⚑ **One fix outside the brief, flagged for Mike to keep or strip:** `checkForSale` referenced
  `finalSlabType` before its `const` (a TDZ ReferenceError) on the path "seller's label carries a grade
  AND vision has a grade AND the sale is detected after the switch". Pre-existing (2.43.0 had the same
  reference); the harness reproduced it — `Watch error: Cannot access 'finalSlabType' before
  initialization`, sale detected, NOT recorded, and never re-detected because `lastSaleCheck` was already
  set. Slab sellers' labels ("ASM 300 CGC 9.8") are exactly this path. Replaced with `vision.slabType`,
  which is what the later block computes anyway. Re-run: recorded, grade 9.6, `slab_label`.

**Step 1 measurement — fallback exposure.** The record carries no listing id (`source_id` is a timestamp;
extension storage and the March export carry the same object). Proxy from the code: the Apollo path never
sets `seller`/`viewers` (the normalizer has neither; the DOM merge copies only title/subtitle/price), the
fallback path sets both from the DOM scrape → **seller present ⇒ fallback, certain; seller null ⇏ Apollo**
(lower bound). Since 08-28: **50 of 970 rows (5.2%)**, all one contiguous block 23:00–23:29 on 09-10, one
seller, two labels, Apollo before and after. All-time 89 of 11,024. Corroborated: 48 of the 57
repeat-record rows since 08-28 are inside that block, 47 gaps exactly 30 s (the debounce); fallback rows
carry a bid count 50/50 vs 13/920 on Apollo. Reading: fallback is **per page load**, not per listing —
rare, but an entire session when it happens, and it is also the storm. Hence the stable id.

**Step 2 measurement — the expiry bound.** The "using previous" console lines are retained nowhere.
**Unmeasured; no percentile can be stated.** Mechanics: the "switch" is the reader skipping the listing
once Apollo flips it SOLD, and the won text is Whatnot's render of the same event → expected gap ≈ poll
500 ms + cache 400 ms + bridge 300 ms, under ~1.5 s with the next item queued; ≈ 0 from the switch when
nothing is queued. Harness gaps on the designed flow: 487–3,015 ms (the 2.5–3 s ones are the harness's
own waits). Asymmetry: too tight = the defect itself (A's sale recorded under B). 10 s provisional; the
ring buffer measures the real distribution over one capture evening; set the bound at max + margin then.

**Backfill audit of affected rows: NOT POSSIBLE from the corpus, and why.** Nothing in a row ties the
vision fields to the listing they were scanned from. On Whatnot `raw_title` is the seller's LOT LABEL
("$1 starts #25", "Box #17", "Fight me bro #6"), so vision disagreeing with the label is the normal case:
of 2,611 vision rows with a "#N" label, 2,408 disagree, and the N is the lot counter, not an issue. Both
proxies tried (title mismatch, issue mismatch) return the whole population. Consecutive identical vision
identity (28 pairs since 08-28) is also what a seller running multiple copies produces. Exposed
population: 736 vision rows since 08-28, 4,849 all-time; the number actually wrong is unknowable
retroactively. The counters are the first instrument that can measure the rate, going forward only.

**Known limitation of the stable id (Mike, addition 1) — multi-copy lots, harness-confirmed, NOT scoped:**
a seller running several copies under one label at the same price: the first sale records; the relist's
price reset is detected as a new item (price-drop rule), which re-holds the old copy's snapshot as
"previous" (expires as one `unsold-expiry` count, harmless, logged); the second sale at the **same hammer
price is DROPPED** by the existing sold-text dedup (`saleKey = id-price-label` unchanged since the first
sale); a **different hammer price is recorded**; any second sale inside 30 s is dropped by the debounce
regardless. This is the behaviour Apollo-path listings with a reused product id already had; the stable id
makes fallback sessions match it rather than storm.

**Hulk stack storm — EXPECTED to stop, UNVERIFIED (Mike, addition 2).** Rows 10678–10692 (09-10, seller
`85a650c7…`, label "Hulk stack", $65) were one sale recorded 15 times at 30 s intervals with a fresh scan
each time, because the fallback id changed every poll. With the stable id the harness shows one
new-listing event, one scan and one record for a fallback listing polled 30 s with the sold text left on
for 36 s. **The observation that confirms it in the field: a fallback session (rows with `seller`
present) with NO 30 s repeat clusters (same seller + raw_title + price within 90 s).** Until that is seen
it is not fixed. Logged as its own ROADMAP queue item (13).

**Harness evidence (scratchpad `harness/`, real `content.js` + real normalizer/valuator/sale-tracker/
apollo-reader, stubbed `chrome`/`ComicVision`/`SupabaseClient`, `insertSale` captured in-page — no
network, no production write; served by the gitignored `valuator-harness` launch config):**
| counter | sequence that increments it | observed |
|---|---|---|
| designed flow (control) | scan A → switch to B → A's sold text | A recorded with A's vision + image, drops 0 |
| mismatch | B current → switch to C → scan C → B's sold text within 10 s | B recorded under its own label, no image; `DROP mismatch … (kept for the current listing)`; C's vision then attached to C's own sale |
| fallback-id | fallback F1 → switch F2 → scan F2 → F1's sold text | F1 recorded, no image; `DROP fallbackId … dom-sam:box #2 … dom-sam:box #1 (kept …)` |
| unsold-expiry (switch) | held prev, no sale, next switch | `… ended without a detected sale (switch); dropped its vision "Superman"` |
| unsold-expiry (timeout) | scan F2 → switch to G → 11 s silence | `… (timeout 10000 ms); dropped its vision "Incredible Hulk"` |
| late-scan | scan held on G → switch to K → resolve | not applied, status "Scan outdated", `DROP lateScan: … L-G returned on L-K (result "Thor")` |
No counter needed a production write to observe. Overlay line and `getDropCounts()` agreed throughout.

**Verification agent (read-only; it had no shell, so it read the full current files rather than the diff,
and it read `content.js` BEFORE the TDZ fix landed):** brief items 1–7 all found implemented; payload shape
to `insertSale` unchanged; ring buffer cannot exceed 500 and cannot throw without storage; designed flow
internally consistent. **1 critical: the `finalSlabType` TDZ** — the same defect the harness had already
reproduced, fixed as above (converged independently). **1 low: a first-load race in `recordTiming`** — two
entries in the same tick before the first storage read resolved could each start a load and the later
callback overwrite the earlier entry; fixed by queueing entries until the load drains. One ambiguity it
raised, read as intended: an unsold expiry that also drops vision is one counter increment and one console
line naming both, not two.

**Ship block (Mike):** `git add CCExtensions/whatnot-valuator/content.js
CCExtensions/whatnot-valuator/lib/apollo-reader.js CCExtensions/whatnot-valuator/manifest.json
CCExtensions/whatnot-valuator/styles.css` + records → commit → push. **No `deploy`, no `purge`.** Then
reload the unpacked extension; **expected version in `chrome://extensions`: 2.44.0**; console banner
`Initializing Comic Valuator v2.44.0`; the overlay shows the `drops ·` line. `WV/` untouched (still
2.41.1, queue item 12). CLAUDE.md's version list updated to 2.44.0 with the pending note.

## 2026-09-14 — 🌙 **SESSION CLOSE (Mike, 23:10 PDT). Everything below is committed; the working tree holds only the two pre-existing modified files (`docs/API_SPEND_LEDGER.md`, `docs/EBAY_CAPTURE_WEEKLY.docx`) plus Mike's untracked `docs/LESSONS_INDEX.md`. Next unit: queue item 2.**

**MOST RECENT CHANGE (Rule 5): Mike closed the session after `bb8aeed` (lessons index). Nothing
pending. Supersedes nothing. State checked before writing, per the CLAUDE.md rule: `git log -1` =
`bb8aeed` 2026-09-14 23:02 -0700; live `app.html` at 06:11 UTC has "This grade is already saved" 1,
"Already in your collection" 0, `withInFlight` 7.**

**Shipped and verified this session (all Mike-run):**
- `c23cd7f` — collection save phase 1: grading uuid as the natural key, `ON CONFLICT DO NOTHING`,
  `saved_collection_id` populated, shared in-flight guard on five async buttons. Deployed, purged,
  **confirmed by hand by Mike:** grade → Save → Save again gives the toast and ONE row; two separate
  grades of the same book give TWO rows (correct — one grade, one uuid, one row).
- `d0785d3` — duplicate-save toast names the grade, not the book. Live; old string gone.
- `5df3073` — CLAUDE.md rule "Ship state comes from evidence, not intention" (L-SW-2026-030's
  operational form).
- `bb8aeed` — lessons index, 29 trigger lines at the top of `docs/LESSONS.md`; stale content in
  003/012/017/021/013 reported, not fixed.
- Cleanup **block A** run 22:40 PDT (explicit transaction, three pre-checks): 8 rows deleted,
  `collections` 150 → 142, registry 23 unchanged, eight survivors present, **re-confirmed at 142
  outside the transaction (Mike, in the close message; the file's own 142 read is the verifier's at
  05:41 UTC).** **Block B NOT run, stays unrun.** 32 orphaned R2 objects:
  unscheduled, harmless.

**Findings carried forward:**
- Nothing anywhere groups the collection by title+issue; multi-copy collections display as separate
  rows (Mike holds ~a dozen doubles, a couple of triples). ⚰️ ~~Heroes for Hope #1 ×3 saved tonight as
  rows 191/192/193~~ — **CORRECTED by Mike at close: rows 191/192/193 are TWO physical copies, not three.**
  The two copies graded 7.5 and 8.5; the third row is a RE-GRADE of one of them, run to test the toast,
  and returned 7.5 again — matching its first run. (By id order and grade, 191 and 193 are the same
  copy and 192 the other; that pairing is inferred from the grades, not stated by Mike.) Two things
  follow: (a) the re-grade is the "same copy graded twice" case — a new uuid, a new row, by design, the
  same shape as operator rows 45/47 — so one of 191/193 is a test row Mike may want to delete, his call;
  (b) one copy graded 7.5 twice in a row is a single data point on same-copy consistency, consistent
  with the 0.5 noise floor. Product note (doubles side by side) recorded in ROADMAP regardless.
- **Row 191 carries a legacy client-minted id: saved after the deploy, before the purge.** The
  backend half alone does not close the defect — between `deploy` and `purge` the old client still
  mints random ids. On this unit the purge was half the fix, not cosmetic. (A backend-first ship
  order is still right; the window is the Pages build + purge, and it is real.)
- Lessons gap measure: three lessons would have changed outcomes this week and none fired (024 on
  the nine-row cleanup premise; 024 §3a/027 on the FK guard; 020 on the first toast wording).
  Mike's own account of which four lessons were in use was wrong — 027 was cited zero times.

**Open for the morning (Mike's decisions, nothing pending on Claude):**
1. Stale content inside five lessons — 003 (retention exists since 06-19), 012 (512MB → Standard
   2GB since 07-16), 017 (purge artifact now defined; "UNRELIABLE" superseded), 021 (Web Store claim
   retired 08-26; monitor manifest 1.0.1), 013 (the cited test was a scratchpad file). Reported.
2. Three duplication families — 008/030/the new rule (the git-log check); 015/028/029 (null and
   surface); 016/018/019/020/021 (label is not a mechanism). Consolidation is Mike's.
3. **The index is being placed in Bilbo's project knowledge** (Mike) — the half that closes the gap,
   since the in-repo copy only helps this side. The copy exists as **`docs/LESSONS_INDEX.md`, UNTRACKED,
   created 23:09 PDT by Mike** (40 lines), and its first line already carries the dated header naming
   `LESSONS.md` as authoritative — the drift guard is in place. Whether it is committed is Mike's call;
   if it is, the index in `LESSONS.md` stays the source and this file is the derived copy.

**NEXT UNIT when work resumes — queue item 2 (ROADMAP Pattern-Sweep Queue):** the Whatnot valuator
carries applied vision data across listings when a listing ends without a sale, so the next sale can
be recorded as the wrong book. Present in both the live and the stale copies of the extension. It
corrupts the comp corpus every user's FMV is computed from, and a wrong record is indistinguishable
from a right one afterward. Report first (read-only), then propose; extension change → manifest bump,
repo-only, no deploy.

**Verification agent (close record, read-only):** 7 confirmed / 1 wrong / 0 uncheckable — "distinct
grades" corrected to distinct grading ids; the untracked Bilbo copy and the source of the 142 re-read
added.

**Standing constraints unchanged:** Mike runs all git, deploys, env changes and production writes.
Claude never commits, pushes, deploys or writes to production. Mechanism-vs-outcome convention
applies. Verification agent before presenting. A later record that contradicts a brief → stop and
say so.

## 2026-09-14 — 📇 **LESSONS INDEX added to `docs/LESSONS.md` (records only, no code) + read-only report: stale/duplicative lessons, and which lessons this week's units needed and did not use.**

**MOST RECENT CHANGE (Rule 5): a 29-line trigger-condition index now sits at the top of
`docs/LESSONS.md`, above `## Format`. In the working tree, pending Mike's commit (this file and
LESSONS.md). Nothing merged, nothing deleted; the staleness and duplication findings below are for
Mike to decide.**

**Why (Mike):** the side of the work that writes the briefs does not read LESSONS.md; four lessons
(020, 027, 029, 030) were applied this week because they surfaced in conversation, not because they
fit. Twenty-five have never been read by that side. The pattern sweep's seven shapes came from the
conversation plus one old task description, not from the file.

**Shape decision:** in-file section, not a separate file. A second file is a second record to drift
(the P4 shape this week was spent on); an index directly above the entries it indexes drifts only when a
lesson is added without a line, and the section header says so. Numeric order (stable for lookup); the
entries themselves stay in recency order.

**Stale content INSIDE lessons (mechanism moved; rule still stands unless noted) — REPORTED, NOT FIXED:**
- **003** — WHY/HOW describe a world with no retention ("gated on a privacy/consent decision");
  `grade_submissions` has existed since **2026-06-19** (`e87b8cf` table, `801e79d` writer; Session 107
  "RETENTION shipped & verified"). The rule survives only as "check whether the grade was retained".
- **012** — "512MB Starter ceiling": instance is Standard 2GB since 2026-07-16 (CLAUDE.md). Illustrative.
- **017** — SOURCE says "Cloudflare purge still has no artifact defined": CLAUDE.md's ship sequence now
  defines it (assert the new content is served, `curl -sL`). WHY quotes CLAUDE.md's old "auto-deploy
  UNRELIABLE" wording, corrected to OFF on 2026-08-07.
- **021** — "STILL OPEN: `faq.html:541` Chrome Web Store claim, pending Mike": `faq.html` no longer
  contains the phrase (resolved, unrecorded in the lesson). "`slab-guard-monitor` manifest 1.0.0": now
  1.0.1. The `marketplace_monitoring` false-restriction in `PLANS` is still there (routes/billing.py:63,
  82, 101, 120) — that part is current.
- **013** — cites `test_monitor_flap.py` (S4, "40 alternating polls → exactly 1 email") as the offline
  storm test. **No such file is tracked, and none ever was** (`git ls-files`, `git log --all -- '*flap*'`
  both empty; `find` over the working tree empty). The test the lesson points at does not exist in the
  repo — WWLO Session 118 records it as a *scratchpad* file, never a repo artifact, so nobody should
  hunt for a lost commit; the mechanism (`37d5e97`) is unaffected.
- Current, spot-checked: 005 (`scripts/stripe_preflight.py` exists), 010 (`PYTHONUNBUFFERED=1`
  Dockerfile:7), 014 (says its own figures age), 016 (instances 5–7 "left": `My Reports` still in
  `popup.html:149`, consistent), 021 (`docs/EXTERNAL_COPY_SURFACES.md` exists), 023 (`.dockerignore`
  list matches), 024 (025 still reserved), 029 (`.gitignore:106` still `scripts/cp1_*.py`).

**Duplicative / overlapping (the file already marks 011/027, 015/017 and 026/020 "do not merge", and
018 "DISTINCT FROM 015/024" without the merge wording; those are not re-raised). Mike decides:**
- **008 + 030 + the new CLAUDE.md rule** — one check (git log before writing or presenting ship state)
  in three places. 030 describes itself primarily as **020** "applied to a record instead of user-facing
  text" and secondarily as "the failure 008 guards against", so it sits in both families; the CLAUDE.md
  bullet is the operational form of the 008 half. Candidate: 030 becomes a second instance under 008
  (the check) with a cross-reference from 020 (the shape); the index points at one line.
- **015 → 028 → 029** — 028 calls itself "the general form of 021(a)" and "015 applied to lookups";
  029 calls itself "028 with the surface named". One rule (name the surface; positive-control the
  null), three entries. 029 could be a HOW TO APPLY bullet under 028.
- **016 → 018 → 020 → 021(b)** — 020 says it generalises 016 and 018; 021(b) is "018 inside the fix
  for 016". One root rule (a label, flag, or claim is not a mechanism — find the reader or the
  expression), four entries with different war stories.
- **017 / 022 / 023** — distinct (artifact / timing / location), but all three are now encoded in
  CLAUDE.md's ship sequence; they are diagnosis, CLAUDE.md is the rule — the same promotion 030 got.
- **009 / 019 / 026 — the recall-vs-precision asymmetry** (a miss shrinks a pool, a false merge poisons
  one): 019 and 026 each say "the same asymmetry as [[L-SW-2026-009]]". One principle, three carriers;
  a cross-reference family, not a merge.
- **019 → 016**: 019 calls itself "[[L-SW-2026-016]] at the data layer", so it also belongs in the
  label-is-not-a-mechanism family above (five entries, not four).
- **001** is restated in CLAUDE.md and in memory. Correct; it is the one rule that belongs everywhere.

**Gap measure — lessons this week's units needed and did not apply (the cost of reading a seventh):**
1. **024 (measure THAT population)** — the cleanup's nine-row premise "surplus rows are duplicate
   saves" was a plausible story (same user/title/issue/grade within 3 min); the grade blobs were not
   compared until Mike asked. Rows 45/47 are two grading runs and 47 carries a live serial; the first
   SQL (committed in `c23cd7f`'s record) would have deleted row 47 and its serial. Caught by Mike's
   question. The lesson's first instance (FF #1, "asserted… and never counted") is this shape.
2. **024 §3a (run the whole predicate, verbatim) / 027 ("positive-control every new guard against a
   case it must block")** — the FK guard was checked for row 47 only, not for all nine; registry row
   19 → 54 was found by the verifier before the draft reached a commit. The survivor rule had been
   applied to the wrong row of the Handbook #1 pair.
3. **020 rules 1 and 4 (name for the condition; a mislabel fix is where the next mislabel lands)** —
   the first toast, "Already in your collection", named a representative case (one copy) inside the
   save fix, in the same pass that cited 020 for another string. Caught by Mike.
4. **016 rule 6 + 013 (state that only resets by a button is not a session; per-worker observations
   vs shared state)** — the sweep's P7 shape and its gunicorn per-worker finding were already in the
   file; the sweep derived them from conversation. No outcome cost; the direct evidence for the brief.
5. **030 / 008** — read, cited, and violated twice (recorded; now a CLAUDE.md rule).
Applied without citation, for the record: 017 (Render deploys GET as the
artifact), 022 (wait before purge in every ship block), 028 (CLAUDE.md "no such line" reported rather
than acted on), 018 in mirror form (queue item 1's root cause — a UNIQUE constraint no caller fed —
was found by grepping for the reader). 015 WAS cited (the sweep entry: "positive control required on
every pattern"). ⚠️ The file's own count of this week's citations is 030×5, 020×3, 029×1, 015×1, 026×1,
**027×0** — so of the four Mike named as applied, 027 was applied in a brief, not in a record; 015 and
026 were cited and unlisted. **Verdict: the four in use were not the four that mattered;
three others would have changed outcomes this week and were caught by Mike or the verifier instead of
by the file. The index is worth maintaining.**

**Verification agent (read-only):** 46 confirmed / 5 wrong / 3 uncheckable. The five, folded above:
retention date 06-27 → 06-19; 030's primary self-description is 020, not 008; 018's note is "DISTINCT
FROM 015/024", not "do not merge"; 015 was cited this week; the index header's "recency order" claim.
Four index lines rewritten to state the moment rather than the finding (009, 015, 018, 019). Uncheckable:
the row count, and the conversation-side claims about what the brief-writing side has read.

## 2026-09-14 — 📏 **RULE ADDED to CLAUDE.md (records only, no code): "Ship state comes from evidence, not intention." L-SW-2026-030 stays in LESSONS.md as the diagnosis, with a pointer to the rule.**

**MOST RECENT CHANGE (Rule 5): Mike promoted the ship-state check from lesson to rule, 2026-09-14 late
evening, after the fourth violation in ten days. Supersedes nothing; adds the operational form. Uncommitted
in the working tree: `CLAUDE.md`, `docs/LESSONS.md`, this file. Records only — no deploy, no purge.**

The rule (three sentences, under Session Conventions after "Mechanism vs outcome"): before any record says
a unit is committed, deployed, purged, or not, run `git log -1` and the live assert and write what they show;
if a unit has not shipped, name what is pending rather than describing it as unshipped. Why in CLAUDE.md
rather than LESSONS.md (Mike): the lesson described the failure accurately for a week and did not prevent it —
lessons get read, rules get followed. The four instances: `2e27098` (09-04, the lesson's source), `c23cd7f`
and `d0785d3` (09-14, phase-1 and toast entries each calling themselves uncommitted inside their own
commit), and the block-A record's first draft (09-14 22:52 PDT, calling the toast uncommitted twelve minutes
after it shipped, inside the pass that was tombstoning the previous instance). Queue item 1 is closed
(`7a03470`, Mike): block A run and verified, block B not run and staying unrun.

## 2026-09-14 — ✅ **CLEANUP BLOCK A RUN AND COMMITTED (Mike, DBeaver, 22:40 PDT = 2026-09-15 05:40 UTC). Eight duplicate-save rows deleted. Block B NOT run and STAYS unrun.**

**MOST RECENT CHANGE (Rule 5): production cleanup block A executed by Mike 2026-09-14 22:40 PDT.
Supersedes "prepared, NOT run" in the phase-1 entry's cleanup block (annotated there). Block B — row 47 +
serial SW-2026-000009 — is not run and is not pending: it stays unrun unless Mike decides otherwise.**

**What ran:** `DELETE FROM collections WHERE id IN (24, 53, 92, 94, 95, 96, 129, 132) AND user_id IN
(3, 38, 61)` inside an explicit transaction, after the pre-checks (8 rows listed; 0 registry references;
0 `saved_collection_id` references). **Mike's result:** 8 rows deleted; `collections` 150 → 142;
`comic_registry` unchanged at 23; all eight survivors (23, 45, 47, 54, 91, 93, 128, 131) present.
**Verified read-only 05:41 UTC:** `collections` 142; `comic_registry` 23; none of the eight ids remain;
survivors 23, 45, 47, 54, 91, 93, 128, 131 all present; registry rows 11 → 45 (000007), 13 → 47
(000009), 19 → 54 (000015) untouched.

**Net effect on the duplicate clusters:** Iron Man #109 → one row (23); Handbook #1 → one row (54, the
registered one); Strange Academy #1 → one row (91); Daredevil #196 → one row (93, of four); Tales to
Astonish #93 → one row (128); Tales to Astonish #90 → one row (131). Handbook #2 stays TWO rows (45,
47), two serials — two grading runs, Mike's call, block B unrun.

**R2:** 32 objects orphaned under the eight `submissions/SW-…/` prefixes listed in the cleanup block
(row 54's prefix `SW-1771631680710-qcbei61jr/` is NOT among them and is live). Nothing reads them.
Deleting them is optional, from the Render shell, and NOT scheduled.

**Toast SHIP RECORD (also written after the fact):** `d0785d3` (Mike, 2026-09-14 22:28 -0700, three files:
app.html, ROADMAP.txt, this file) — pushed, Pages built, purged: live `app.html` at 05:42 UTC has
"This grade is already saved" 1, "Already in your collection" 0. Frontend only, no deploy, correct.
⚠️ L-SW-2026-030 shape again, twice tonight: the toast entry below read "uncommitted" inside `d0785d3`,
and this block-A record was first drafted calling the toast uncommitted twelve minutes after it shipped.
Both tombstoned in place. The cause is the same both times — Mike commits faster than the record is
re-read — and the fix is procedural: **before writing any ship state, run `git log -1` and the live
asserts, never trust the last message.** Only these two record files remain uncommitted.

## 2026-09-14 — ✅ **Save toast REWORDED (frontend, ⚰️ ~~uncommitted~~ SHIPPED `d0785d3` — record at top) + read-only answer: nothing groups the collection by title/issue + cleanup premise PARTLY CONTRADICTED (rows 45/47 are two grading runs, not one save twice) + product note recorded.**

**MOST RECENT CHANGE (Rule 5): the prepared cleanup was re-cut 2026-09-14 from nine rows to EIGHT
confirmed duplicate saves plus an OPT-IN block for row 47 / serial 000009, after Mike asked whether the
nine were duplicate saves or distinct grades of distinct copies. Supersedes the nine-row form (tombstoned
in the phase-1 entry below). Toast wording changed in the same pass. **Phase 1 itself SHIPPED while this
pass was running: `c23cd7f` (Mike, 2026-09-14 19:49 -0700), Render deploy `live` on that commit, Pages
built and purged — live asserts pass (ship record in the phase-1 entry below).** The toast rewording is
a NEW frontend-only commit — ⚰️ ~~NOT committed~~ **shipped as `d0785d3` 22:28 PDT, live-asserted 05:42 UTC (entry above).****

**1. String (frontend, `app.html`, a NEW commit after `c23cd7f`):** ⚰️ ~~"Already in your collection — This grade
was saved before — no duplicate was created."~~ → **"This grade is already saved — It went into your
collection on an earlier save. Nothing was added twice."** REASON (Mike): the first wording is a claim
about the comic; for a collector holding three copies of one book it is false. The toast fires only on a
repeat save of the SAME grading uuid; three copies are three grades, three uuids, three rows, and never
see it. Ship: push → Pages build → purge (never on the push); the phase-1 asserts still hold
(`withInFlight` 7, `saveGradeBtn` 3); add `grep -c "This grade is already saved"` → 1 and
`grep -c "Already in your collection"` → 0 (it is 1 on the live page now).
```
git add app.html docs/sessions/WHERE_WE_LEFT_OFF.md docs/sessions/ROADMAP.txt
git commit   # Save toast: claim the grade, not the comic; cleanup re-cut to 8 confirmed + opt-in 47; doubles product note
git push
# frontend only — NO deploy. ⏳ wait for the Pages build to COMPLETE, then:
purge
#   curl -sL https://slabworthy.com/app.html | grep -c "This grade is already saved"   → 1
#   curl -sL https://slabworthy.com/app.html | grep -c "Already in your collection"     → 0
```

**2. Read-only answer — does anything dedupe or group by title+issue rather than by row? NO, nowhere.**
Every surface is per-row: `js/collection.js:131–160` (`totalComics = collection.length`; raw, slabbed and
rated-profit sums are `reduce` over every row; "worth slabbing" is a row filter); `:188–288` filter and
sort — search matches title/issue substrings, sorts tie-break title→issue, nothing collapses; each card
is one row (`createComicCard`). `dashboard.html:413–433` `renderPortfolio` — count = `length`, FMV sum,
average grade over rows; `:438–466` `renderTopComics` — top 5 rows. `routes/collection.py:54–107` GET — one row per `collections` row
(the only aggregate in the query is `COUNT(*)` of sightings per serial, a LEFT JOIN, not a collapse).
`routes/admin_routes.py:104–108` — `COUNT(*) … GROUP BY user_id` (per user, still per row). Account page:
NO collection count is rendered at all (`account.html` only has the plan-feature grid, where "Excel/CSV
Export" is forced SOON at :758). **Excel export of the collection does not exist**: `collection.html:175`
is a disabled SOON button, `js/collection.js:1098` `exportSelected` is a stub; the only `downloadExcel`
(`js/app.js:956–977`) is the bulk-photo VALUATION tool on `app.html#bulkMode` and exports
`extractedItems`, not the collection. The gallery "Export" (`js/collection.js:1043`) is an html2canvas
screenshot of the rendered per-row cards. **Consequence: a three-copy collection displays as three rows,
three counts, three values, everywhere. Not a defect; nothing to fix.** (`routes/feedback.py:111–119`
LATERAL-joins the NEAREST-IN-TIME collection row to a grading rating — a one-row pick for the admin
feedback view, not a collapse; noted because it will pick arbitrarily among a same-minute cluster.) Verifier's
independent sweep added, all per-row: `admin.html:928` renders the per-user count from the admin query;
`routes/admin_routes.py:1130–1138` groups SIGHTINGS per registered serial (displays title+issue with a
count, one row per serial, not per copy); registry→collections joins in `routes/monitor.py`,
`routes/verify.py`, `routes/registry.py` are one row per registry row; `admin.html:1310` shows
`saved_collection_id` per retained grade.

**Live evidence of both halves, 09-15 UTC (verifier, RO):** rows 191/192/193 are ⚰️ ~~Mike's THREE Heroes
for Hope #1~~ **TWO copies of Heroes for Hope #1 plus a re-grade of one of them (Mike, session close —
tombstoned in the close entry)** (02:58–03:00 UTC, grades 7.5 / 8.5 / 7.5, three distinct grading ids) —
three grades, three rows, as designed; the re-grade row is a test artefact, Mike's to keep or delete. Row 191 carries a legacy `SW-` id, 192/193 carry server uuids:
191 was saved 8 min after the deploy finished, before the purge landed (the cached page still minted).
`grade_submissions.saved_collection_id` is now non-NULL on 2 rows — the link column is being written.

**3. Cleanup premise checked (RO, block-level detail in the phase-1 entry's cleanup block):** eight of
the nine are duplicate saves of one grade (identical blob; one retained grade per real-user cluster);
**45/47 are two grading runs** (different defect lists on three of four surfaces — spine identical — 151 s apart, same 7.0).
Cleanup re-cut to block A (eight, confirmed) + block B (47 + serial 000009, opt-in on Mike's memory of
Feb 18). Expected counts as DELTAS — A: collections −8, registry unchanged; A+B: −9 / −1. ⚰️ ~~A → 129 / 22;
A+B → 128 / 21~~ (verifier 09-15: `collections` is 141 now, not 137 — rows 190–193 were saved after the
deploy, so absolute post-run counts are wrong the moment anyone saves; re-census immediately before running).

**4. Product note (recorded, NOT built):** `docs/sessions/ROADMAP.txt` — doubles/triples side by side
(three grades of one title/issue is the comparison a collector with doubles wants, and the product does
not surface it; the rows exist, nothing relates them). Against the collection area, next to CSV import.

## 2026-09-14 — ✅ **Queue item 1, PHASE 1 APPLIED (Save to Collection: natural key + ON CONFLICT + link column + shared in-flight guard; plus CLAUDE.md convention + two P4 fixes). ⚰️ ~~In the working tree, NOT staged, NOT committed. SHIPS IN MIKE'S NEXT COMMIT~~ → **SHIPPED `c23cd7f`, deploy live, purged, asserted (ship record at the end of this entry).** Cleanup is a separate production step (prepared below, NOT run).**

**MOST RECENT CHANGE (Rule 5): Mike approved the agent's shape over the brief's sketch ("wiring up a
constraint that has been sitting unused rather than bolting on a guard"), phase 1 only, with the
in-flight wrapper promoted to a primary item. Applied 2026-09-14; verified before presentation (see
the verification line at the end of this entry).**

**What changed (four files):**
- **`app.html` (FRONTEND):** (1) the Save button gains `id="saveGradeBtn"` (`saveCollectionBtn` was
  already taken by the dead bulk-mode button); (2) `withInFlight(key, btn, fn, {restore})` — one
  shared guard: a re-entrancy key (a second call with the same key while one is in flight is
  dropped), an optional button to disable for the duration, and `restore` to re-enable it in
  `finally`; (3) the five async handlers rewired through it — `saveGradeToCollection` and
  `saveAllToCollection` share key `'save'` on `#saveGradeBtn`; `registerComic` → wrapper +
  `_registerComicImpl` (`restore:false`, it manages its own text/disabled); `window.generateGradeReport`
  → wrapper + `_generateGradeReportImpl` on `#generateReportBtn` (restore true = today's post-failure
  state); `runSignatureCheck` → wrapper + `_runSignatureCheckImpl` (no button is wired to it; re-entrancy
  only); `submitGradingFeedback` → wrapper + `_submitGradingFeedbackImpl` (`restore:false`, no button —
  its own permanent latch is kept, see below); (4) **the natural key**: `gradingId =
  finalGrade.grading_id || SW-mint` — the server-minted `grading_uuid` now goes out as the save's
  `grading_id` AND as the R2 `submission_id`, so a repeat PUT overwrites `submissions/{uuid}/{type}.jpg`
  instead of creating a new object set; the `SW-` mint survives only as a fallback (verifier 09-14: the
  id is never absent on this page, including the `?dev` quick test, which cannot reach the save);
  (5) `result.already_saved` → toast ⚰️ ~~"Already in your collection — This grade was saved before — no
  duplicate was created."~~ → **"This grade is already saved — It went into your collection on an earlier
  save. Nothing was added twice."** (reworded 2026-09-14, entry above: the first wording claimed the comic,
  not the grade) (still a success; Register enables on the returned id as before).
- **`routes/collection.py` (BACKEND):** `INSERT … ON CONFLICT (grading_id) DO NOTHING RETURNING id`;
  on no row → `SELECT id FROM collections WHERE grading_id = %s AND user_id = %s` (mandatory — the old
  `fetchone()['id']` would raise on None); ownership is in the SELECT, so a conflict with another
  account's row is a **409** `{conflict: true}`, never that user's id; NULL `grading_id` never conflicts
  (unchanged). **The never-written link column is written:** `UPDATE grade_submissions SET
  saved_collection_id = %s WHERE grading_uuid = %s AND user_id = %s AND saved_collection_id IS NULL`
  (a legacy `SW-` id matches nothing; the first link stays authoritative). Response gains
  `already_saved: bool`.
- **`CLAUDE.md`:** the mechanism-vs-outcome convention, two sentences, as a bullet under Session
  Conventions (Mike's revised wording: mechanisms are proposals; decisions already made are
  challengeable only on new evidence or an unforeseen consequence — say what changed and let him
  decide). The extension-version list corrected 2.42.1 → **2.43.0**, 1.0.0 → **1.0.1**, dated
  2026-09-14, with the stale list tombstoned inline.
- **`docs/LAUNCH_READINESS.md:79`:** ⚠️ the brief placed "the three unauthenticated uploads line" in
  CLAUDE.md and said it "is now one". Neither held on reading: CLAUDE.md has no such line (it is
  LAUNCH_READINESS.md:79), and the count is **two, not one** — `/upload-for-sale` was deleted in
  `d8a0100`, but `/api/images/upload` (`routes/images.py:75`) and `/submission` (`:164`) still carry no
  `@require_auth` (both now moderate; `/upload` is rate-limited). Corrected to two, in place, with the
  reason. Recorded under the convention: the outcome (no known-wrong content under a new rule) is met;
  the stated mechanism was wrong on both the file and the number.

**Latch inventory — what each of the five had before, so nothing regresses:** `submitGradingFeedback`
had a REAL latch (`feedbackSubmitted` flag + thumbs disabled, intentionally permanent after a vote) —
kept, wrapper adds re-entrancy only; `registerComic` disabled and re-labelled its own button (upgrade
and error branches) — kept, wrapper `restore:false`; `saveAllToCollection` only disabled Register
transitively — now shares the Save key; `generateGradeReport` had NOTHING — now disabled for the run,
re-enabled after; `runSignatureCheck` had NOTHING and no caller — now re-entrancy-guarded;
`saveToCollection` disabled the WRONG button (Register) — now disables Save for the whole
four-upload-plus-POST duration, which is the missing in-progress signal that produced the 23–140 s
re-clicks.

**⚠️ TRAP, recorded loudly for whoever scopes the start-over control:** `js/grading.js:2510`
`resetGrading()` (dead, zero callers) re-shows step 1 by adding `.active` to `gradingContent1` — and it
resets grading.js's own module-scoped `let gradingState` (`js/grading.js:10`), which is a DIFFERENT
object from `window.gradingState` (`app.html:2236`, created precisely because the top-level `let` is
not a window property). Wired as-is as "start over", it would re-open the upload step while
`window.gradingState.finalGrade` (and `extractedData`) survive from the previous book. With phase 1
the stale re-save then collides on the previous book's uuid and returns that row (no wrong row) — but
the identification panel, `extractedData` and every result-card element would still be the previous
book's. **Do not wire `resetGrading`; a start-over control must reset `window.gradingState` (photos,
extractedData, finalGrade, confidence, signatureResult), `lastSavedComicId`, `feedbackSubmitted`, and
the result card, and re-show step 1 — or reload.**

**Stale-grade save: LATENT, not live — reason, for the record.** `generateGradeReport` removes
`.active` from `#gradingContent1` (:2282) on every Generate; nothing in `app.html` re-adds it; there is
no `pageshow` handler; "Grade Next" is `window.location.href='/app'` (a new document); a back-button /
bfcache restore brings back the results screen with the upload step still hidden. No UI route reaches
a second grade in one page session. Phase 1 closes the path structurally anyway (the collision above).

**Phase 2 stays separate — two reasons:** (1) the retained `grade_submissions` row is written on a
daemon thread (`grade_retention.py:66–102` INSERT+commit, photos backfilled :105–119), one to three
seconds after the grade, so a server that reads the grade from that row needs a retry/409 path for a
fast Save; (2) pointing collection photos at the retained keys (`grade_submissions/{id}/{label}.jpg`)
couples them to the 24-month `images_purge_after` purge — the `saved_collection_id` link written in
phase 1 is the column that would let a purge skip linked rows, and it must be populated (it now is,
forward) before that coupling is safe. Phase 2 removes the client cache and the client re-upload;
phase 1 makes the cache unable to create a wrong row.

**CLEANUP — ⚰️ ~~prepared, NOT run~~ → BLOCK A RUN 2026-09-14 22:40 PDT (entry at top: 8 rows, 150 → 142,
registry 23 unchanged, verified RO). BLOCK B NOT RUN, STAYS UNRUN. Prevention was live from `c23cd7f` (deploy finished 2026-09-15 02:50 UTC),
so block A is runnable now, as a separate production step (DBeaver, per the SQL-delivery rule).** Survivor rule: the EARLIEST row of each cluster (first
save, lowest id, the row most likely already looked at) — **EXCEPT where the later row carries the
cluster's only Slab Guard registration, in which case the registered row survives** (one exception:
the Handbook #1 pair, below). Grade, title, issue identical across each cluster; only `created_at` and
the photo paths differ. FK facts (RO 09-14): `comic_registry.comic_id → collections(id)` with NO
cascade, so a collection row with a registry row cannot be deleted first; `sighting_reports.serial_number
→ comic_registry` (0 rows) and `match_reports.registry_id → comic_registry` (0 rows, cascade)
reference nothing here; all three registry rows involved have NULL certificate fields.

⚰️ ~~first draft deleted 54 and kept 53~~ — **DEAD (verifier 09-14, RO): registry row 19
(`SW-2026-000015`, user 3, active) points at collection row 54, and row 53 has NO registry row.** The
FK has no cascade, so step 2 as first drafted would have raised on `comic_registry_comic_id_fkey`
and aborted the transaction; the expected counts could never have been reached. **REPLACED BY:** keep
54 (the registered one), delete 53 — the registry is untouched for that pair and the serial stays
valid. The other two options were (a) delete row 19 as well (loses a live registration; registry →
20) and (b) re-point row 19 to 53 (a registration then references photos it was not fingerprinted
from). Neither is better than keeping the row the registration already describes. **Mike can still
choose (a) or (b) instead; the SQL below encodes the recommendation.**

⚰️ ~~second draft: nine rows in one statement, registry row 13 retired first~~ — **DEAD 2026-09-14 (Mike's
question: are the nine duplicate SAVES, or distinct grades of distinct copies?). RO answer: EIGHT are
duplicate saves — identical grade blob (defects on all four surfaces, confidence, values, verdict) across
every row of the cluster, and for the four real-user clusters exactly ONE retained `grade_submissions` row
for that title/issue in the minutes before the saves (48, 50, 135, 136). Rows 45/47 are NOT: the two
Handbook #2 rows carry DIFFERENT defect lists on three of four surfaces (front, back, interior; spine identical) — two separate `/api/grade` runs, 151 s
apart, that landed on the same 7.0. Whether that was one copy graded twice or two copies is not
decidable from the data; it is Mike's book (user 3) and both rows are registered (000007, 000009).**
**REPLACED BY:** the confirmed eight in one block; row 47 + registry row 13 as a separate OPT-IN block
Mike runs only if he confirms it was one copy. (No `grading_uuid` is shared at the collections level in
any cluster — the old client minted a fresh `SW-` id per click, and the user-38 retained rows predate
the uuid column — so "same uuid" is established by the retained row + identical blob, not by the key.)

```sql
BEGIN;
-- A. ✅ RUN 2026-09-14 22:40 PDT by Mike — 8 rows deleted, 150 → 142. Kept verbatim as the record of what ran.
--    The EIGHT confirmed duplicate saves (identical grade blob; one retained grade per cluster).
--    Survivor = earliest row, except Handbook #1 where 54 stays (registry row 19 → 54; 53 is
--    unregistered and 1.0 s earlier). Guard: no comic_registry row may reference any id here,
--    or the FK (no cascade) aborts the transaction.
--    SELECT id, comic_id FROM comic_registry WHERE comic_id IN (24,53,92,94,95,96,129,132);  -- expect 0 rows
DELETE FROM collections
 WHERE id IN (24, 53, 92, 94, 95, 96, 129, 132)
   AND user_id IN (3, 38, 61);
-- expect: DELETE 8
-- Verify before COMMIT:
--    SELECT count(*) FROM collections;        -- expect (pre-run count) − 8. ⚠️ NOT an absolute: the base moves
--    (137 at the 09-14 census, 141 at 03:00 UTC 09-15 — rows 190–193 arrived after the deploy). Re-census first.
--    SELECT count(*) FROM comic_registry;      -- expect 22  (unchanged by block A)
--    SELECT id FROM collections WHERE id IN (23,45,47,54,91,93,128,131);   -- expect all 8 present
COMMIT;
```
```sql
-- B. ⛔ NOT RUN 2026-09-14 and STAYS UNRUN (Mike). Not pending; do not re-propose without a new decision.
--    OPT-IN, ONLY IF MIKE CONFIRMS rows 45/47 were ONE physical copy graded twice (Feb 18, 14:16 and
--    14:18). If they were two copies, run nothing here: two rows, two serials, is correct.
BEGIN;
DELETE FROM comic_registry
 WHERE id = 13 AND comic_id = 47 AND serial_number = 'SW-2026-000009' AND user_id = 3;
-- expect: DELETE 1   (generate_serial_number() checks uniqueness, so 000009 is never reused)
DELETE FROM collections WHERE id = 47 AND user_id = 3;
-- expect: DELETE 1
--    SELECT count(*) FROM collections;        -- expect (pre-run count) − 9 after A+B
--    SELECT count(*) FROM comic_registry;      -- expect 21  after B
--    SELECT id, comic_id, serial_number FROM comic_registry WHERE id IN (11, 19);  -- expect 11→45, 19→54
COMMIT;
```
Survivors (block A): 23 (Iron Man #109), **54** (Handbook #1, keeps serial 000015 — the exception), 91
(Strange Academy #1), 93 (Daredevil #196 — of four), 128 (Tales to Astonish #93), 131 (Tales to
Astonish #90); 45 AND 47 both stay unless block B runs.
**R2 orphans:** block A leaves 8 × 4 = **32 objects** under `submissions/SW-1771014006939-jz2iv6dpc/`,
`SW-1771631675832-0306rdbak/` (row 53 — ⚰️ ~~`SW-1771631680710-qcbei61jr/`~~, that prefix is row 54's and
SURVIVES), `SW-1785987376943-mrxox0r5g/`, `SW-1785988153694-p473fc7vw/`, `SW-1785988229358-5pkha8z0z/`,
`SW-1785988274708-m7ig7lpon/`, `SW-1787949297009-wbeteig3g/`, `SW-1787950609258-plh212x9t/`; block B adds
4 under `SW-1771424312151-xk42vlgol/` (row 47). Nothing references them after the DELETE (the verify page and Slab Guard read `collections.photos` of the
surviving rows). They are harmless storage; deleting them is a `boto3 delete_object` per key from the
Render shell (32 calls, 36 with block B), optional, and NOT part of this unit. No `grade_submissions.saved_collection_id`
points at any deleted id (the column was NULL everywhere until today).

**SHIP (Mike):**
```
git add app.html routes/collection.py CLAUDE.md docs/LAUNCH_READINESS.md docs/sessions/WHERE_WE_LEFT_OFF.md docs/sessions/ROADMAP.txt
git commit   # Save to Collection: use the server grading_uuid as the natural key; ON CONFLICT + link column; shared in-flight guard on five buttons; CLAUDE.md convention; two P4 fixes
git push
deploy       # BACKEND FIRST — an old server given a uuid simply inserts it; the ON CONFLICT must be live before the client guard is trusted
# ⏳ wait for the Pages build to COMPLETE, then:
purge
# asserts (curl -sL — the .html paths 308 to clean URLs):
#   curl -sL https://slabworthy.com/app.html | grep -c "withInFlight"        → 7
#   curl -sL https://slabworthy.com/app.html | grep -c "saveGradeBtn"        → 3
#   backend: Render Events shows the commit; then a grade + Save, then Save again → toast "This grade is already saved" (⚰️ ~~"Already in your collection"~~), collections gains ONE row, grade_submissions.saved_collection_id set on that grading_uuid
```
**SHIP RECORD (written 2026-09-15 UTC, after the fact):** commit `c23cd7f` (Mike, 2026-09-14 19:49 -0700,
six files: app.html, routes/collection.py, CLAUDE.md, docs/LAUNCH_READINESS.md, ROADMAP.txt, this file);
Render deploy on `c23cd7f` created 02:49:36 UTC, finished 02:50:19 UTC, status `live` (deploys GET);
live page (`curl -sL`): `withInFlight` 7, `saveGradeBtn` 3 — so the Pages build and purge both
happened. Not exercised: the grade → Save → Save-again round trip (Mike's, on the live site). ⚠️
L-SW-2026-030 shape, recorded not blamed: this entry's header read "NOT committed" inside the commit
that shipped it, because the commit ran while the follow-up brief was being worked; tombstoned in place
above. Cleanup: block A runnable now; block B on Mike's decision.

**Verification agent (phase 1 applied, read-only; app.html diff hunks, wrapper simulation in node,
collection.py loop exercised with a scripted fake cursor for the three outcomes, RO schema/row checks,
CLAUDE.md/LAUNCH_READINESS diffs, latch inventory and trap against `git show HEAD:app.html`):**
32 confirmed / 2 wrong / 1 uncheckable. **Wrong 1 (material, corrected above):** the cleanup SQL would
have failed — registry row 19 references collection row 54. **Wrong 2 (a recipe in the verifier's
brief, not in any record):** `git log -S"upload-for-sale"` returns `b36a2e5`, not `d8a0100`; the
removal commit is found with `-G`, and `d8a0100` is correct. Uncheckable: the live-site asserts
(pre-deploy). **One latent note the verifier added, recorded so "nothing regresses" is honest:**
`_registerComicImpl` has two early returns (no token → login redirect in 1.5 s; no
`lastSavedComicId`) that at HEAD left the Register button enabled; with `restore:false` the wrapper now
leaves it disabled on those paths. The first redirects anyway; the second needs the protection section
visible with no saved id, which only an empty `ids` array from a 200 could produce (the server 400s on
no items). Not reachable today; not fixed; named.

## 2026-09-14 — 🟦 **Queue item 1 (Save to Collection) — ⚰️ ~~REPORT STAGE … Mike decides~~ → Mike chose the agent's shape, phase 1 APPLIED the same day (entry above). Findings retained.**

**MOST RECENT CHANGE (Rule 5): read-only characterisation of queue item 1 delivered 2026-09-14 with a
proposal that differs from the brief's sketch — the natural key already exists at every layer and is
ignored by the one call that matters; using it closes both defects without a per-button guard being the
only protection and without clearing cached state. Mike has not decided. HEAD `77ac111` (roadmap
committed by Mike).**

**A. What a second click does.** `saveToCollection` (`app.html:3574`) guards only on
`finalGrade` (:3576); the Save button (:1319, no id) is never disabled — the only `disabled = true`
in the function is the Register button (:3597). Each click **mints its own id** `SW-${Date.now()}-…`
(:3604), uploads the four photos to `submissions/{that id}/{type}.jpg` (`r2_storage.py:141`; plain
`put_object`, no hash check) and POSTs `/api/collection/save` with that id (:3705). The server
(`routes/collection.py:110–178`) is a plain INSERT loop with one commit (:175) and **no `ON CONFLICT`**.
Two clicks = two independent async runs, both 200, nothing idempotent at any layer;
`lastSavedComicId` (:3752) ends on whichever finished last. **The natural key is ignored at exactly one
place:** `/api/grade` mints `grading_uuid` (`routes/grading.py:958–959`), the client holds it as
`finalGrade.grading_id` (:2534–2536, with a client fallback mint) and sends it to valuation (:2706)
and feedback (:3216) — but NOT to the save — and **`collections.grading_id` already carries a UNIQUE
constraint (`collections_grading_id_key`, contype u)** that never fires because every click sends a
fresh random id. Side finding (P1 shape): the comment at `app.html:2530–2532` lists "collection save
:3697" as a consumer of the server id; it is not.

**B. Duplicates already in `collections` (RO, 137 rows, 29 op / 108 real):** 11 near-duplicate pairs
(same user/title/issue/grade within 3 min) = **9 surplus rows: 3 operator (23/24, 45/47, 53/54) and 6
real-user** — user 38: Strange Academy #1 (91, 92), **Daredevil #196 ×4 (93, 94, 95, 96)**; user 61:
Tales to Astonish #93 (128, 129), #90 (131, 132). All 137 `grading_id`s distinct; every pair's photos
sit under different `submissions/SW-…/` prefixes (duplicate R2 object sets). Gaps: the real-user
clusters are 23–140 s apart — not double-clicks but **re-clicks after a save that shows no in-progress
signal** (four uploads then a POST, only a toast); operator pair 53/54 is 1.0 s, a true double-click.
`grade_submissions.saved_collection_id` is NULL on all 215 rows — the retained-grade → collection link
has never been written. **Consequence: prevention PLUS cleanup; cleanup is a production write and is
Mike's** (surplus rows 92; 94, 95, 96; 129; 132, keeping the earliest of each cluster, plus their R2
objects; the three operator pairs likewise).

**C. Register on a duplicate.** `routes/registry.py:576–581` checks `WHERE comic_id = %s` — the
collection ROW id — so a duplicate row is a different comic and mints a new serial (:641–668); no
fingerprint match runs at register. Demonstrated: rows 45 and 47 (operator) carry **SW-2026-000007 and
SW-2026-000009 — two serials, one book** (their hashes differ, so a hash-equality check would not have
caught it either). Three other registrations (68/69/70) share one hash. Users 38/61 have no
registrations → no real-user double serial today. **Recoverable:** `sighting_reports` 0 rows,
`match_reports` 0 rows, both certificate fields NULL — nothing external references either serial.

**D. Route back to the upload step: none via UI.** `generateGradeReport` removes `.active` from
`#gradingContent1` (:2282); nothing in app.html re-adds it; no `pageshow` handler; "Grade Next" is a
reload (:1320); bfcache restores the results screen. **The stale-grade save is latent, not live** —
narrower than the ranking assumed. ⚠️ **Load-bearing for the separate "start-over control" scoping
question:** `js/grading.js:2510` `resetGrading()` (dead, zero callers) DOES re-show step 1 — and it
resets grading.js's own module-scoped `gradingState`, a different object from `window.gradingState`.
Wired as-is as a start-over control, it would re-open the upload step with `window.gradingState.finalGrade`
intact: the stale-grade save exactly.

**E. Mike's structural questions, answered from the code:**
1. **Same root cause?** Same class (page state with no lifecycle) — different mechanisms (request
   identity vs state lifetime). Bundled correctly, but the reason is that ONE change closes both.
2. **Idempotency key vs natural key?** The natural key exists (uuid minted, held, indexed UNIQUE) and is
   unused by the save. A new key would duplicate it. Send `finalGrade.grading_id`; key the R2 uploads on
   it (a second PUT to the same path is idempotent — duplicate objects vanish without content hashing);
   server `INSERT … ON CONFLICT (grading_id) DO NOTHING` then `SELECT id WHERE grading_id = %s` → the
   same collection id, 200, `already_saved: true`. ⚠️ The follow-up SELECT is mandatory: `RETURNING id`
   yields no row on conflict and the current `fetchone()['id']` would raise. Legacy `SW-` ids and 32-hex
   uuids coexist (varchar, no format constraint); `grade_submissions.grading_uuid` has a partial UNIQUE
   index usable by the link UPDATE.
3. **Clear the cache, or not cache?** With the natural key, a stale `finalGrade` carries the FIRST book's
   uuid and collides with its existing row — the wrong-title-under-old-grade row becomes structurally
   impossible **without clearing anything**. The stronger form (server copies grade/subgrades/defects
   from `grade_submissions` by uuid; client stops re-uploading photos) is where the grade actually lives
   and is available, at a cost: the retention row is written on a daemon thread (INSERT+commit
   :66–102, photos backfilled :105–119) so a save within ~1–3 s needs a retry/409, and pointing
   collection photos at retained keys couples them to the 24-month purge (the never-written
   `saved_collection_id` is the column that would let the purge skip linked rows). Recommendation:
   **phase 1 = natural key + ON CONFLICT + write `saved_collection_id`; phase 2, separate unit =
   server-side copy from `grade_submissions`.** Phase 1 removes the defect class for this button; phase 2
   removes the cache.
4. **Structural double-click?** The structural layer is the server's uniqueness — it lives in the data
   and cannot be forgotten on the next button. The client layer today is per-button and inconsistent:
   `submitGradingFeedback` has a real latch (`feedbackSubmitted` + disabled thumbs); `registerComic` and
   `saveAllToCollection` disable Register; `generateGradeReport` and `runSignatureCheck` have nothing;
   `saveToCollection` disables the wrong button. No shared helper exists. A `withInFlight(button, fn)`
   wrapper on the five async buttons makes the client half structural in one place and supplies the
   missing in-progress signal that produced the 23–140 s re-clicks.

**F. Proposed unit (phase 1), NOT applied:** frontend `app.html` — send `finalGrade.grading_id` as
`grading_id` and as the R2 `submission_id` (fallback to the `SW-` mint only if absent — verifier: it is
never absent on the app.html path, incl. the `?dev` quick test, which cannot reach the save); `withInFlight`
on Save (and the other four); treat `already_saved` as success. Backend `routes/collection.py` —
`ON CONFLICT (grading_id) DO NOTHING` + SELECT existing id + `UPDATE grade_submissions SET
saved_collection_id … WHERE grading_uuid = %s` in the same transaction. Not touched: result card,
start-over control, Register flow. **Deploy backend FIRST** (an old server given a uuid simply inserts
it; the ON CONFLICT must be live before the guard is trusted); frontend → push → Pages build → purge.
Cleanup (Mike, production write) as in §B, plus a decision on serial SW-2026-000009.

**Verification agent (read-only):** 35 confirmed / 3 wrong / 1 uncheckable. Wrong: the surplus-row
arithmetic (9 total: 3 op + 6 real — corrected above); "gaps are not double-clicks" (true for real users;
53/54 at 1.0 s is one); "nothing re-adds `.active` to step 1" (dead `resetGrading` does — noted in §D).
Uncheckable: that users 7/27/30 are operator accounts (a scratchpad constant; only user 3 is `is_admin`).

## 2026-09-14 — 🧹 **PATTERN SWEEP (Mike's brief, Todoist item "run the pattern sweep", due 08-28) — READ-ONLY, bounded to seven named shapes. Findings only; no fixes, no proposals, no differentials. Checkpointed per pattern below as each sub-sweep returns.**

**MOST RECENT CHANGE (Rule 5): sweep STARTED 2026-09-14. Seven parallel read-only sub-sweeps, one per
pattern, plain `grep -rn` primary with restricted paths (the nested `.claude/worktrees` tree hangs an
unrestricted grep) and `rg` cross-check on every search, differences reported (rg honours
`.gitignore`; `scripts/cp1_*.py` are ignored — this sweep must not be an instance of Pattern 3).
Positive control required on every pattern (L-SW-2026-015). Checkpoints are appended here in arrival
order, not pattern order; the consolidated report is verified before presentation.**

**The seven patterns and their source instances (from the brief):**
- P1 copy asserting a mechanism that does not exist (L-SW-2026-020) — FAQ→Photo Tips pointer,
  backfill docstring's flat baseline, monitor `--dry-run` text, "we identified the comic" tagline.
- P2 unreachable code that still looks live — Photo Tips modal + opener, both client resize paths,
  the per-step spine prompt, a footer CSS rule matching nothing.
- P3 a null result whose search could not have fired (L-SW-2026-029) — ripgrep honouring .gitignore,
  "zero blur rejections", bare `curl -s` on a 308, dependency-status showing warnings only.
- P4 a record/comment describing state that has since changed (L-SW-2026-030) — unit described as
  unshipped inside its shipping commit, ship records owed, Werewolf by Night listed unsearchable.
- P5 a value measured one way and described another — stylesheet-occurrence coverage, drain report
  blind to case splits, per-table vs whole-corpus 165/367 vs 166/373.
- P6 a threshold/default inherited rather than argued — the 83 pair-rescue floor, `[B-W]`, the 30%
  variant-note gate, rapidfuzz processor default under an unpinned major.
- P7 state that persists when it should reset — `uploaded` class, `finalGrade` never cleared,
  results header before the fix.

**Checkpoints (appended as they arrive):**

**✅ P7 CHECKPOINT — state that persists when it should reset (landed first; full sub-report in scratchpad `sweep_P7_full.md`).** Positive controls found by method (`uploaded` never removed; `finalGrade` never cleared; header reset only since `fb3e0a8`; title `--` on catch). Framing facts: "Grade Next" reloads (`app.html:1320`); there is NO UI path back to the upload step without a reload, so the no-reload second-book path is reachable only via bfcache restore (no `pageshow` handler) or devtools; two `gradingState` objects exist (`js/grading.js:10` script-scope `let` vs `app.html:2236` `window.`), the only full reset (`resetGrading`) targets the dead one; gunicorn is `--workers 2 --threads 8 --max-requests 500 (+jitter 100)` and Render health polls count, so **every backend module-level state is per-worker AND reset every ~30–60 min**.
Ranked findings (severity as the sub-sweep assigned; file:line):
- **HIGH — Save to Collection has no in-flight/double-click guard** (`app.html:1319` button, `saveToCollection` :3574 never disables it): two clicks → two `/api/collection/save` POSTs with fresh `SW-…` ids and a full R2 re-upload each → **two collection rows for one grade**; `window.lastSavedComicId` (:3752) then points at the duplicate, so Register (:3325) registers it. Reachable today.
- **HIGH — valuation strip shown before valuation succeeds** (`:2543`): on any valuation failure (`!response.ok` :2717, `!valData.success` :2743, catch :3166) the strip stays visible with `--`/previous FMV cards, a blank badge (blanked at grade start) and no message. Fresh load: three `--` cards under a real grade. Reachable: any valuation 5xx.
- **HIGH (extension) — whatnot-valuator `appliedVisionData`** — present in BOTH copies: the tracked-but-stale `WV/whatnot-valuator/content.js` (manifest 2.41.1; set :278, cleared :1041 only, not in the listing-change reset :588–604) and the LIVE `CCExtensions/whatnot-valuator/content.js` (manifest 2.43.0; :276 / :966 / reset block :519+, verifier): a listing that ends without a detected sale leaves the previous listing's title/issue/slab/variant/grade applied to the next sale record (:997–1006). Wrong-book sale record.
- **MED — `#resultComicThumb`** (:1194) set only on success (:2565): quality-fail shows the title with an empty thumb (fresh load) or the previous book's cover (no-reload).
- **MED — rate-limit stores are per-worker and never pruned**, and the 1-hour windows (`routes/contact.py:27`, `routes/waitlist.py:36`) are longer than worker life, so those limits reset before the window ends (5 resp. 3 per IP per worker per recycle, not per hour). `_daily_scan_store` (`routes/vision.py:63`): a DAILY cap held on a ~30–60-min worker = unbounded per day (endpoint gated to unsellable tiers; mechanism void).
- **MED — `_resource_streaks`** (`dependency_monitor.py:156`): the sustained-3-samples alert needs 15 min on ONE worker; a recycle mid-streak zeroes it; the admin chip shows the serving worker's memory, not the climbing one.
- **MED — `cc_user` localStorage** set only by login.html, removed by ONE of six logout paths (`js/sidebar.js:614`); other five clear `cc_token` only → next user on the browser sees the previous account's display name/initials and Admin link until login overwrites it; never refreshed, so a revoked admin flag persists until re-login.
- **MED (extension) — WV `lastSaleCheck`** (:900) never cleared; key `id-price-title` → the same item sold again at the same price later is silently dropped (:898) even after the 30 s debounce.
- **MED — same-file re-selection is a silent no-op** (no `.value = ''` on the four file inputs) — already logged as LIVE DEFECT 1; the P7 sweep found it independently.
- LOW/INFO (recorded in the full report): `confidence` and `signatureResult` share `finalGrade`'s shape (`runSignatureCheck` has zero callers, so `signatureResult` is always undefined); `feedbackSubmitted` and the thumbs/Thanks/comment persist across a no-reload second grade; `#gradeReportProtection`/`registrationStatus` never hidden at grade start; the 429 `monthly_limit` branch nukes `#resultsScreen.innerHTML` (:2461) for the page session; `resultVerdictTagline`, `resultEditionNote`, `resultVariantNote`, `resultComicMeta` untouched on one or both failure branches; dependency caches with 24 h TTL longer than worker life (always refetch on recycle); model-fallback index per worker; `sw_sell_platforms` not user-keyed; `sw_ebay_pending_comic` survives an abandoned OAuth; `cc_auth_token` is a dead legacy key; ebay-collector `unsyncedCount` only ever increments from content.js.
- **No Flask `session` usage; `flask.g` request-scoped only. No new pattern shape proposed by this sub-sweep.**
Bounds: root `*.html`, `js/`, `routes/`, root `*.py`, the two `content.js` files; two flagged one-line reads outside bounds (`styles.css:1439`, `Dockerfile:24–36`); `sw.js`, `popup.js`/`background.js` (beyond "who clears") not swept. grep vs rg: five searches, counts identical once rg bounds matched grep's (first rg pass over-counted by recursing into sub-directory html/py and `.claude/` worktrees — the unbounded-rg trap, noted).

**✅ P6 CHECKPOINT — a threshold or default inherited rather than argued (full sub-report in scratchpad `sweep_P6_full.md`).** Positive controls found by both tools: `title_normalizer.py:497` `per_token_floor=83`; `[B-W]` survives ONLY in the comment at :608–609 (the live code is the explicit `_STRAY_LETTERS` list since 09-03); `sales_valuation.py:447–448` 30.0/3/5; `requirements.txt:24` + `RAPIDFUZZ_VERIFIED_MAJOR`. Population: 222 threshold-shaped lines across 61 files in the restricted paths; 62 itemised, tiered by what they decide.
**Tier 1 — decides what a user is told or charged (all bare literals unless noted):**
- `routes/grading.py:885` `{1:65, 2:78, 3:88, 4:94}` — the displayed grade confidence, keyed only on photo count; no comment.
- **Three different "confidence" ladders for the same concept, none argued:** `sales_valuation.py:1077–1084` (`exact_count ≥10` high / `≥3 or total ≥10` medium / `≥3` low), `:1796–1800,1824` (`fmv_sample ≥10/5/2`, `<5` low) on `/api/sales/fmv`, `js/app.js:1243–1245` (`score ≥70/50/30`); plus colour bands `js/utils.js:315–317` (0.8/0.6/0.3).
- `sales_valuation.py:999,1004` `exact_count ≥ 3` → `fmv_method='exact'` (feeds `verdict_reliable`); reused as the anchor for `MIN_EDITION_CLUSTER_COMPS=3` ("CHOSEN, not fitted — matched to the exact_count ≥ 3 evidence bar").
- `:972,979` `1 ± 0.2·grade_diff` — asserted only as "~10% per half grade"; `:996` `× 0.25` floor — bare (the queued max-grade-distance unit is referenced in-comment).
- `:1058,1065,1657,1769,1780` `raw × 1.5` graded-from-raw and the ROI slab premium — asserted ("typically 40–60%", "default 50%"), no corpus figure.
- `:1043–1054` **duplicated at** `:1641–1652`: publisher ×1.3/×1.1, era ×2.0 (<1970)/×1.5 (<1984)/×1.2 (<1992) — the fabricated-FMV multipliers, age labels only, two copies.
- `:1268–1270` `slabbing_roi > 50` → "Worth grading", `> 0` next band — the verdict string; the `> 0` band is already logged (:1271) as producing a false badge.
- `:292–294` EDITION constants — the file says it itself: 15 "carried from the earlier volume work" (inherited, self-declared); 20.0 "FITTED TO 14 OBSERVATIONS … provisional … figures do not reproduce" (argued with recorded doubt); 3 inherited from `exact_count ≥ 3`.
- `:183–197` grading-cost tiers (`year < 1975` vintage; ≥$1000 → max(4%, $135); ≥$400 → $105; else $45/$30) — "tiered by CGC 2026 schedule", no date/URL; the 1975 cut uncited.
- `:206` `percentile_trim(pct=5)` on every median the user sees — "same methodology as premium analysis engine" (inherited by name). `:428–434` bootstrap 1000/95/seed 42 — conventional. `:608` `days=365` — "wider window for more data".
- `:669,746,837,856,1593` price floors `> 5` (eBay graded), `> 2` (eBay raw), `> 2` (market graded), `> 1` (market raw), `> 5` (fmv) — bare AND inconsistent across tables with no comment.
- `content_moderation.py:40` `80` — verbatim rationale "reasonable balance"; no measurement. (Cross-ref: the Rekognition entry — every product-surface block is one label within 12 points of this floor.)
- `routes/fingerprint_utils.py:157–159` `400/250/60` — the 400-vs-250 SPLIT is argued (Batch 7, 394×572); the 400 itself and blur 60 are asserted ("intentionally lenient"); `:217` resizes to 800 before Laplacian — bare; `routes/registry.py:237,246` does the same 800 resize with a blur floor of **100**, so one measurement has two floors (60 vs 100) with no cross-reference.
- `app.html:1878` 75 s abort — argued (30 s × 1 retry); `comic_extraction.py:23–24` timeout/retries — argued.
- Signature thresholds: `js/collection.js:1183,1210` `≥0.40` auto-save / `js/utils.js:445` `<0.25` "No signatures detected" — bare; server side (sampled, outside the listed files) `routes/signature_orchestrator.py:78` `LOW_CONFIDENCE_THRESHOLD=0.50` env-overridable no rationale, `:603–607` 0.85/0.65/0.40, `:376–378` 0.7/0.4, `routes/signatures.py:215–216,578–579` 0.7/0.3 inside prompt text.
- `CCExtensions/ebay-collector/content.js:402` `riskScore ≥ 60` → HIGH — bare. `routes/registry.py:638` registration confidence formula `52 + 8.75·angles + 10 + min(16, 2·extras) − 5` — comment lists outputs, not why.
**Tier 2 — matching / filtering:** `title_normalizer.py:566` pair rescue `≥ 100` — ARGUED (710/0). `:661,692,703` `score_cutoff=75` — inherited ("75% similarity"); :696–701 argue why 75 alone is insufficient, never why 75; `:645–647` reuses it on the "by" guard. `:70,76,80` year window 1930–2029 encoded twice (int check + regex). `:430,433` issue `\d{1,4}` then `0 < n < 1000` — "typically under 1000". `:104–110` condition-grade map — no source. `:271–293` `variant_patterns` incl. `\bdirect\s*(edition)?\b` (→ excluded from the base pool, `sales_valuation.py:749`) — list inherited, Cover-A exception argued (144/974). `:297–308` prefixes (bare-"new" argued, 1,072 rows), `:318–334` publishers, `:369–398` fillers incl. `\bof\b` (the CP-1 "of" source), `:505` stop set, `:140–142,707–708,720` small words/acronyms — inherited. `title_matching.py:48–49` strip leading "the" only — ARGUED (14,033 titles, zero false merges); `:30,37` prefix qualifiers asserted, regex removal argued. `routes/registry.py:134–140` 500/1000/100/500/500/1500 — "calibrated … all test photos scored well above" (an upper bound on good photos, not a floor measurement); `:265` `nfeatures=5000` bare; `:317,356–357` (mirrored `monitor.py:195,221–222`) strip 5% argued, hash 16 asserted, min strip 20 px inherited. `routes/monitor.py:68–71` composite 70/73/77/105 — ARGUED ("Tested thresholds (Feb 2026)"; 105 has a WHY block); `:81–82` edge 124/126 argued; `:85–88` legacy pHash 5/10/15/20 bare; `:442,517` displayed-confidence formulas asserted — the legacy `100 − dist×2.5` over a 64-bit hash reaches 0 at dist 40, not 64, unaddressed; `:461,465,695,697` ±10/15 nudges bare; `:14–16` `edge_iou` 0.025/0.010 argued. `routes/fingerprint_utils.py:97–138` preprocessing constants — pipeline argued as a whole (72→36/256), each constant inherited. `comic_extraction.py:648–676` `_extraction_score` weights (decide a second PAID vision call) — bare.
**Tier 3 — infra:** `GRADING_MAX_LONG_EDGE 2000` argued; `EXTRACT 4096` + `IMAGE_DECODE_CONCURRENCY 2` argued (+310 MB measured); JPEG quality 92 / `max_tokens=1000` bare; `sales_ebay.py:73–76` cap 2 argued (July OOM shape), **`_R2_WORKERS 5` "unchanged" (explicitly inherited)**, 25/250 alert cadence asserted; `s-l1600` argued (byte-identical to s-l2400); rate limits (`monitor.py:59–65`, `sales_valuation.py:1459–1461`) bare; `js/grading.js:1310` `MAX_IMAGE_DIM 2048` vs server 2000 unrelated by any comment (and dead code, per P2); `dependency_monitor.py:68` `CACHE_TTL 86400` bare; `slab-guard-monitor/content.js:17` `MAX_AUTO_SCANS 15` bare.
**`requirements.txt` unbounded majors (18 of 20; only `anthropic` and `stripe` are capped):** rapidfuzz argued+monitored (control); boto3 argued in `dependency_monitor.py:1021–1026` (age-based check instead); **Pillow** no comment — `LANCZOS` ×5, `exif_transpose`, draft-mode thumbnail; `comic_extraction.py:157–163` already documents a draft-mode gotcha that IS Pillow-version behaviour (plausible, partly observed); **imagehash** no comment — persisted 16-bit hashes; `fingerprint_utils.py:8–12` says any preprocessing change invalidates the whole DB, and a library-side hash change would do the same, unmonitored (plausible, unrecorded); **numpy** unbounded across the 1.x→2.x ABI break (plausible); opencv low plausibility; flask/gunicorn/bcrypt/pyjwt/cryptography/requests/psycopg2/scipy/resend/pyzbar/pillow-heif — no comment, not assessed. **The Rekognition 5 MB limit is referenced nowhere in the repo** (zero hits) — the fail-open rows in the Rekognition entry are that limit being hit blind.
Bounds: full reads of `title_normalizer.py`, `title_matching.py`, `routes/fingerprint_utils.py`, `requirements.txt`; grep-plus-context elsewhere; prompt-embedded numbers in `comic_extraction.py` not itemised; signature files sampled. grep vs rg: first rg pass used `-E` (which is `--encoding` in ripgrep) → all zeros for the wrong reason, redone; narrow-pattern lines grep 222 vs rg 203 — the 19 are `__pycache__/*.pyc` binary matches and `scripts/cp1_output/*.txt` (gitignored); rg emits backslash paths on Windows (a first `comm` diff mislabelled files — corrected). **⚠️ New P3 instance found by this sub-sweep, mechanism CORRECTED by the verifier: ripgrep 14.1.1's ignore handling here is NON-DETERMINISTIC whenever two or more path arguments are passed** — ⚰️ ~~argument-set dependent; `scripts/ routes/` → 11 cp1 files~~ → ten identical runs of `rg -l "def " scripts/ routes/` leaked the gitignored `scripts/cp1_*.py` files on 2 of 10, `scripts/ js/` on 5 of 10, `scripts/` alone 0 of 10, and `-j1` (single-threaded) 0 of 10 — a parallel-walker race, and the leak admits 8 of the 9 cp1 files (never `cp1_identity_rate.py`), so "11" was impossible. An rg-only sweep's coverage of those files is a coin flip per run. Plain grep is authoritative for them.

**✅ P3 CHECKPOINT — a null result whose search could not have fired (full sub-report in scratchpad `sweep_P3_full.md`).** Ranked by how likely the null is being read as a pass right now; each with what would prove it capable of failing.
- **HIGH — moderation fail-open counted as a "warning" and fires deterministically on `/api/extract` for any photo > 5 MB.** `content_moderation.py:280–290` (`except → allowed, warnings=['Moderation check failed …']`; ⚰️ first draft cited :293–303, the docstring), logged `was_blocked=False`, folded into `total_warnings` (:419–420). `/api/extract` moderates the RAW base64 before normalisation (`routes/grading.py:341–368`); `/api/grade` normalises first. DB: 71 blocked / **3 genuine warnings / 39 fail-open** rows; every fail-open since August is on `/api/extract` (latest 09-12). Pass ≡ broken (200, nothing in the response). Control: the rows exist and `/api/admin/moderation` returns `total_warnings`, but **no HTML/JS fetches that endpoint** — a fail-open counter or a monitor entry off `labels ILIKE '%check failed%'` would have to be built.
- **HIGH — `check_anthropic` parse-to-empty ≡ "no retirements"** (`dependency_monitor.py:298–306`): non-dict/non-list, missing `items`, or a renamed `provider`/`model_id` field all yield `[]`. Live today: 414 records, 19 Anthropic, 0 matches → `[]` is legitimately correct today, which is the problem. Control: none (the 2026-06 incident closed the *raise* form only); would assert ≥1 Anthropic record parsed or that a known-retired sentinel (`claude-3-opus-20240229`, present in the feed) is seen.
- **HIGH — alert-email channel has no positive control, and a key collision hides real check errors for Rekognition and eBay.** `_error_entry` (:160–178) and `_unmonitorable_entry` (:180–196) both set `item: "monitor check"`, so `_alert_key` collides with the permanent unmonitorable rows in `dependency_alerts` (`AWS Rekognition:monitor check` since 08-25, `eBay:monitor check` since 06-07) → a real `_error_entry` for either is never emailed; on the Rekognition path the gap entry overwrites the error entry before dedup (:1050–1053, :1362). `_send_alert_email` returns silently without `RESEND_API_KEY`/`ADMIN_EMAIL` (:1359); a send failure only prints (:1483). Last evidence of a successful send: 2026-08-25. The 09-04 rapidfuzz fix closed this collision class WITHIN rapidfuzz; the cross-helper collision remains. Control: none — a test-send or a rendered "last email sent" timestamp.
- **HIGH (historically) / MED — dashboard `failed_requests` and `get_recent_errors` key on `error_message IS NOT NULL`, not `status_code ≥ 400`** (`admin.py:134, 212, 230, 252`): all-time ≥400 rows 2,015, **645 (32%) with NULL message** through 08-12 — invisible to every "failed" number. The 08-12 `wsgi.py:412–420` fix (`non-json-NNN`) gives 0 NULLs in the last 30 days; the definition is still the wrong instrument for any new non-JSON path.
- **MED-HIGH — admin dependency banner has no arming line** (`admin.html:818–863`: `catch { // Silent fail }`, banner only when `warnings.length > 0`, `status: error|unmonitorable` rendered like a plain warning; resource chip hidden when both fields absent, so a cgroup-path change silently drops memory monitoring; `/health` swallows a `check_all` failure with a print, `routes/utils.py:44–48`). `resources.sampled_at` exists in the JSON (:1231) but is not rendered. JWT-gated endpoints not fetched.
- **MED — `check_stripe` returns `[]` when `stripe` is not importable** (`dependency_monitor.py:623–627`; contrast `check_rapidfuzz` :684–689 which emits `_error_entry`). No control for this branch.
- **MED — photo-quality gate fail-opens with no trace; blur check silently skipped if `cv2` is absent** (`routes/fingerprint_utils.py:226–227`, :220–221); timing lines carry `quality=Nms` but no outcome; nothing asserts opencv imported on this path.
- **MED — `request_logs` cannot see its own worst case:** `after_request` (`wsgi.py:377–433`) never runs for a request killed by gunicorn `--timeout 300` or OOM; the logger's DB connect is outside its `try` (`admin.py:55`); no row-count heartbeat (30 d rows/day ranged 9 → 5,158). The 07-16 addendum's "ZERO backend trace" is an instance.
- **MED — manifest model universe REPLACES rather than unions local `MODEL_CHAINS`** (`dependency_monitor.py:314`): a model added to `models.py` but not the CSV is unwatched, silently. Not verifiable locally (no `GITHUB_TOKEN`).
- **MED — eBay account-deletion self-probe proves self-consistency only** (`routes/ebay.py:14` and `dependency_monitor.py:85` hard-code the same string, an input to the hash); drift against the portal-registered URL is undetectable. Control: the portal's own validation button (external, manual).
- MED-LOW — Rekognition version-change alarm is off whenever the DB read fails (`:872–903` returns `[]` on table-absent AND on DB error; gap text names it, emits no error entry). MED-LOW — `.claude/skills/health` and `stripe-test` assert on `/health` fields (`barcode`, `moderation`) that no longer exist (live `/health` is 34 bytes), grep source for `STRIPE_WEBHOOK_SECRET` (proves nothing about prod env), and list "sub counts" with no producing step. LOW-MED — timing lines print `-1` for unmeasured spans (every span has both marks today; a future missing `.mark()` prints `-1` identically to "skipped"; `db.py:387` `in_use = -1` renders as `pool -1/N`). LOW — frontend `fair_value || final_value || 0` (`js/grading.js:2344`, `js/app.js:171,241,835–874,967`) turns a NULL FMV into "$0.00" in slab-premium/ROI math. LOW (known) — `/health` 5.6.0 used as deploy proof: 62 backend commits since `1437fdb` with no version change; the record itself cites "prod version 5.6.0" as evidence `f7cd04a` is live (~:2092). LOW — slab-guard-monitor stale/empty hash cache ≡ no-match (`background.js:12–31`, `stolenHashesLastUpdated` stored, never displayed). LOW — pages without the pixel include emit nothing (documented in `js/pixel.js:16`).
- **Positive controls that exist and hold:** `routes/utils.py` drift guard (arming line + BLIND branch; index `indisvalid` live); `sales_ebay.py:_r2_note` (`skipped_no_image` vs `failed`, WARN at 25); ebay-collector kind-specific send failures; `_ExtractTimings` emits `reread=` every request; rapidfuzz distinct alert keys; `api_usage` structural-zero fix (0/1,873 zero-token rows in 30 d); `wsgi.py` non-JSON capture (0/97 NULLs in 30 d). Offline tests with explicit controls exist (`tests/test_moderation_unit.py`, `test_upload_endpoints.py`, `test_credit_refund.py`, `test_check_card_unit.py`; `scripts/jv_photo_backfill.py`, `cp1_confidence_measure.py`, `cp1_identity_rate.py`) — **but nothing runs any test** (no CI workflow, `pytest.ini`, `tox.ini`, `Makefile`, or `conftest.py`); `tests/test_memory_fix.py` has zero asserts. Would have to be built: the first eight findings above (named inline).
Bounds: `*.py routes/ js/ *.html scripts/ tests/*.py docs/ .claude/skills/ CLAUDE.md Dockerfile .gitignore requirements.txt`, targeted `CCExtensions/*/{content,background,popup}.js`; RO DB (`request_logs`, `content_incidents`, `rekognition_model_versions`, `dependency_alerts`, `api_usage`, `grade_submissions`, `pg_index`); live GETs `/health`, deprecations.info. Not covered: `sw.js`; docs beyond grep hits; JWT-gated admin endpoints' live output; the GitHub manifest; Render logs; `EBAY_RSS_URL`. grep vs rg: 12 patterns, identical on 9; three differences all `.gitignore:106` (`scripts/cp1_*.py`) — `positive.control` 45/42, `FILTER (WHERE` 58/56, `except Exception:` 86/85. `.claude/skills/` is gitignored but rg searched it when passed explicitly. One rg pass with `-E` (= `--encoding`) returned 0 everywhere and was discarded — reported so the discarded numbers cannot be re-read as a finding.

**✅ P1 CHECKPOINT — copy asserting a mechanism that does not exist (L-SW-2026-020; full sub-report in scratchpad `sweep_P1_full.md`).** Positive control proven: `git log -S "Photo Tips"` → `0b32bfe`/`4efa047`; the corrected `--dry-run` text at `dependency_monitor.py:723`; `git log -S "we identified the comic"` → `fb3e0a8`; and the same click-pattern grep that would have caught the FAQ line caught finding 1 below.
**USER-visible:**
- **`faq.html:358`** — *"click "Check Another" to start a new one. All your assessments are saved in "My Collection""*. No "Check Another" string exists anywhere in app.html or js/; the button is **"Grade Next"** (`app.html:1320`). Nothing auto-saves to the collection — saving is the manual Save button (:1319); the background `grade_submissions` persistence is an admin retention table, not My Collection. Two false claims in one sentence.
- **`index.html:1044`** — stat tile **"PDF / Export Reports"** inside the visible `<section class="my-collection">` (:1024). Zero `pdf` matches across routes/, js/, app.html, collection.html, account.html; the only export is Excel (`js/app.js:956`); `account.html:758` lists export as coming-soon and `collection.html:175` reads "Export SOON".
- **`verify.html:508`** — *"The owner has been notified."* Shown whenever `data.success` is true (:811–821); `routes/verify.py:619–624` returns `success: True` with that message even when `_send_sighting_email()` returned False (Resend exception path ~:431), and the frontend never reads the `owner_notified` field it is sent. False whenever the email fails.
- **`terms.html:490`** — *"we will retain your Slab Guard registrations … for 90 days … After 90 days, registrations are permanently removed."* No user-facing delete-account route exists (the only `DELETE FROM users` is admin `reject_user`, `auth.py:428`); no registration purge or 90-day logic in `routes/registry.py`, `slabguard_routes.py`, `admin_routes.py`; the deletion runbook never mentions registrations. `privacy.html:354–362` carries a comment asserting the 90 days "is correct" as policy — the automated removal it describes has no mechanism.
- `index.html:1080,1139,1147` / `routes/waitlist.py:87,132,209` — "Get notified when Slab Worthy launches", "Launching Summer 2026", "We'll let you know when we launch" — the mailer mechanism exists (`scripts/cohort_mailer.py`), so this is STALE (P4 shape), not missing; waitlist section still rendered. Noted, out of pattern.
**ADMIN-visible:** `TODO.md:34` — "Grade-retention 90-day PURGE … HARD DEADLINE ~2026-09-17 … our LIVE privacy promise ('retained up to 90 days then deleted')" — `privacy.html` says twenty-four months and explicitly retracts 90 days. `docs/SW_deletion_request_runbook.md:21` — "the ~90-day retained photos/grades" — same.
**DEV (docstring/comment/dead code):** `grade_retention.py:12` docstring *"Retention window is 90 days (disclosed in privacy.html)"* while `RETENTION_DAYS = 90` (:21) stamps `images_purge_after = now + 90 days` (:77) on every row — the disclosure it cites no longer exists and every row carries a purge date the policy contradicts (the P7/L-SW-2026-026 materialised-value shape, already queued). `scripts/cp1_nesting_audit.py:30` usage line lists `[--outside N]`; argparse defines only `--days`, `--examples` (:177–178) — **rg-invisible file**. `js/grading.js:2544–2562` `saveGradeToCollection()` alerts "Save to collection coming soon!" — dead (app.html:3306 redefines it). `js/auth.js:428–447` `showCollection()` alerts "Full collection view coming soon!" — dead (app.html:3173 redefines it). `js/app.js:1046,1067` `refreshItem()` POSTs `/api/cache/update` and reports "(saved to database)" — no such route (only `/cache/check`); zero callers.
**Verified, NOT findings (referent exists):** "Register This Comic", "Save to Collection", "Keep it raw", "Report a Sighting" + `_send_sighting_email`, approval email, reset-link flow, waitlist confirm route, `?invite=` handling, billing portal, refund line ↔ `credit_refunded`, "Download All Photos", "Photos will be uploaded automatically when you publish" ↔ `uploadPhotosToEbay`, all 23 extension endpoints, "Sync Now"/Options/"Check with Slab Guard"/"Report This Match", every dependency_monitor action referent (the backfill's no-flags-is-dry-run is correct via `--execute`), every file path cited in code comments (0 missing), every `scripts/*.py` cited in docs (0 missing).
Bounds: click/tap/button claims; `--flag` mentions vs argparse per file; `/api/` references vs 114 route decorators + 17 url_prefixes (suffix match — a wrong prefix could slip through); behaviour words across 13 non-app HTML pages and app.html/js alerts+toasts; email `<p>`/`<a>` lines in the 7 email sources; file-path claims in comments; dependency_monitor action strings; 3 extension READMEs/popups. Docs: 50 md/txt — only script-path existence, 15 Click/Tap lines and `--flag` lines naming a script were checked; docs prose otherwise unsampled. Not covered: all .docx, tests/, archive/, .claude/, routes/*.md, TODO.md beyond :34, email bodies beyond `<p>`/`<a>`, app.html prose beyond the behaviour-word list. grep vs rg: identical on 5 of 7 searches; **`--flag` mentions grep 225 / rg 167** (rg skipped gitignored `scripts/cp1_confidence_measure.py`, `cp1_fallback_audit.py`, `cp1_nesting_audit.py`, `e3_edge_sequence_test.py`, `scripts/cp1_output/*.txt` — the `--outside` finding is rg-invisible); **file-path claims 172 / 162** (rg skipped `CCExtensions/slab-guard-monitor/README.md` and `whatnot-valuator/lib/collectioncalc.js`, both checked by grep, nothing missing). First rg pass used `-E` (= `--encoding`) → zeros, discarded and re-run.

**✅ P4 CHECKPOINT — a record or comment describing state that has since changed (L-SW-2026-030; full sub-report in scratchpad `sweep_P4_full.md`).** Positive controls: the token-guard tombstone (WWLO :1164) and the ship records (:228) found and not re-reported; **the Werewolf by Night control FIRES** — `docs/EBAY_CAPTURE_WEEKLY.docx` (HEAD and the modified working copy; read by unzipping `word/document.xml` into the scratchpad) still says *"DO NOT SEARCH — searching cannot help these … Werewolf by Night — about 952 sales, filed as 'Werewolf'"*, while the 09-03 normalizer backfill (`22fb8dd`, `a89a10c`) left live `ebay_sales` at `Werewolf By Night` 725 / `Werewolf by Night` 156 / `Werewolf` 14. The doc still instructs the operator not to search a title that now works. **HIGH.** (The other 17 "of"-bug titles in that block remain genuinely unfixed.)
**HIGH (claims about whether something works or shipped):**
- **`docs/LAUNCH_READINESS.md:100`** — "eBay search-results MARKUP RESTRUCTURE broke the sales-capture extension — capture pipeline DOWN until fixed." Fixed `bbe5353` (07-16, live-verified 203 rows); collector now 1.4.0; `ebay_sales` has **243,942 rows created since 2026-07-13**, latest 09-14 16:38 UTC. Never tombstoned.
- **`docs/SECTION_F_CHECKLIST.md:3,17,50,64–66`** — "Not yet run"; "GATE 0 — HEIC … BLOCKED until fixed or consciously waived"; "BUILT IN TREE… awaiting ship"; unchecked "Fix SHIPPED" / "Real-device proof". HEIC shipped `d2e525d` (`requirements.txt:23`); `LAUNCH_READINESS.md:58`: "GATE 0 ✅ CLOSED 2026-07-16 (two real-iPhone HEIC grades end-to-end)". (Memory `project_drift_batch_additions` flagged the header; not previously recorded in the repo.)
- **`TODO.md:34`** — "Grade-retention 90-day PURGE (fast-follow — HARD DEADLINE ~2026-09-17)… don't slip the date." Tombstoned in `LAUNCH_READINESS.md:9` (08-13): the purge obligation is 2028-08-03; the only near date is the 2026-11-02 notification. Three days from today this still reads as a hard deadline.
**MED:**
- `CLAUDE.md:251–252` "Current versions (2026-08-24): … whatnot-valuator 2.42.1, slab-guard-monitor 1.0.0" → `whatnot-valuator/manifest.json:4` **2.43.0** (`eeed129`, 08-28), `slab-guard-monitor` **1.0.1** (`1f023c4`, 08-25); `ebay-collector` 1.4.0 holds. This is the list the version-bump rule tells a reader to verify a reload against.
- `docs/LAUNCH_READINESS.md:79` "3 unauthenticated image uploads … `/upload`, `/upload-for-sale`, `/submission` … the first two also skip moderation" → `d8a0100` (08-25) deleted `/upload-for-sale` and gave `/upload` rate-limit + moderation; `/submission` (`images.py:164`) still has no `@require_auth`. Two remain, one hardened; reads as three open. `:104` "AWS Rekognition NOT in MONITORED_SERVICES … Quick fix" → registered `96a68ef` (08-24), 5th `check_all` entry; CLAUDE.md acknowledges it, this line does not. `:132` "route the extract/upload path through the same 2048px canvas resize the grading flow already has" → that resize has been unreachable since `823820b` 2026-02-06 (WWLO 09-11 entry); the queued unit's premise is dead.
- `docs/technical/CP1_STATE_OF_PLAY.md:292–306` "`lookup_demand`: 1,239 rows … 8 external lookups total … how often a real user hits the thin case is not yet answerable" → live **6,191** rows; external `valuation` **191** (94 since 08-25 from 15 distinct users). The premise no longer holds.
- `docs/SECTION_F_CHECKLIST.md:11–13,120–165` — "Booth reality check: GalaxyCon (Aug 21–23)"; "Ceilings to respect: Starter 512MB"; "Starter→Standard 2GB = Mike's manual dashboard call" → GalaxyCon dropped 07-29; instance Standard 2GB since 07-16.
- `TODO.md:33` "[x] ✅ DRAFTED (Session 107, awaiting Mike's git/deploy)" → shipped `e87b8cf` 06-19. `TODO.md:63` "'Photo too small' error doesn't say WHICH photo" → `fb3e0a8` names the front cover and returns `min_dimension` (queued caveat: hard-coded for blur/undecodable). `TODO.md:3–4,459–460,472` "Target: GalaxyCon … Soft Launch: July 21" — both dead (07-29, 08-03), at the head of the task list.
- `README.md` (last commit `74a7d93`, 2026-03-07; public-facing): `:31,54,76` "19 blueprints, 87 routes" → 25 / 121; `:32,68,75` "16 tables" → **40**; `:11,69` "24,000+ eBay sales" → 315,391; `:17` "23 artists with 97 signature images … 78%" → `creator_signatures` 100, `signature_images` 361 across 92 creators; `:84` "Pre-launch (Session 81) — Targeting GalaxyCon… soft launch July 21, 2026" → dead; **`:19` attaches "Application #63/990,743" to Slab Guard; `CLAUDE.md:131` gives that number to Patent 3 (Signature Identification)** — the one factual error rather than a stale count.
- `docs/technical/ARCHITECTURE.txt:99` "`JWT_SECRET` … INSECURE DEFAULT `'change-me-in-production'` — if unset, tokens become forgeable" → `auth.py:31–49` now defaults to `''` and **raises `RuntimeError` in production** when unset or equal to the old default; the described failure mode no longer exists.
- Code comments: `routes/monitor.py:917–919` "TODO: Send email alert to owner via Resend / when we have the Resend integration ready / For now, log it" (from `c816fff`, 02-14) — Resend wired since `6007dd0` (01-26) and used by four modules; the precondition is long satisfied, the alert still isn't sent. `auth.py:510` "REVISIT before the public soft launch when the beta wall comes down" — wall came down 07-29 (`auth.py:760`); `_is_waitlist_confirmed` still called at :274, :790; no revisit recorded.
**LOW (dated counts / drift, sample only):** `CLAUDE.md:4` "Last Updated 2026-08-24" (modified 09-04); `:197` "six users" (83 live, 23 since 08-25); `:162` "Mobile testing on real devices" partially done 07-16. `LAUNCH_READINESS.md:93,121` `MONTHLY_GRADING_LIMIT` NameError — fixed (`grading.py:927–930` post-mortem comment); `:71` "still open (c) Sentry, (d), (f)" — (d) and (f) closed in the same file at :75/:77, only Sentry remains. `CP1_STATE_OF_PLAY.md` "of"-fragmentation counts (Master Kung Fu 140→432, Savage Sword Conan 552→661, Tomb of Dracula 308/66→608/114, Web Spider-Man 572 vs Web of Spider-Man 3,434 — defect still true, every count stale); `:801` 143,118 → 315,391 ebay rows; `:473` grade_submissions 18 → 214; `:846` 62 → 43 after the 09-03 backfill; `:648` Star Wars #1 580 → 748; **all 8 cited `sales_valuation.py` ranges point at unrelated code** (file grew ~870 lines 08-13→08-16; the claims hold at new positions, e.g. the "only EXPOSES the signal" TODO now :1793); `app.html` refs drifted 45–100 lines. `routes/ROUTE_MAPPING.md:5,9` "March 24 … 88 routes across 19 files" — body sums to 92, edited 08-25 without the header. `ARCHITECTURE.txt` env-var table: 7 of 16 sampled line refs hold, 9 drifted. `Dockerfile:27` "Sized to the Starter instance (512MB)" and `dependency_monitor.py:96` "Render Starter has NO native threshold alerts" — Standard 2GB since 07-16. `wsgi.py:7–8` "11 blueprints … 54 routes" — known (LR :121), unfixed. `js/marketplace-modal.js:176` "Show debug strip (TEMPORARY)" — in place since 03-06. `ebay_listing.py:632–636` "For now … Simplified" — `get_listing_status` has zero callers. `TODO.md:402` "ID Sigs BROKEN" — resolution not recorded anywhere; unverified. WWLO :33–35 (this week's close) "HEAD `56fe022`" — committed as `f5d6b67`, one past what it states (the L-030 shape, trivially).
**Unresolved, NOT a finding (reported as the sub-sweep found it):** `LAUNCH_READINESS.md:7,14,58` "first cold traffic NOT SCHEDULED / mobile pass still ahead" — no repo record contradicts these (no "gate fired" text anywhere in the repo; no WWLO entry 08-17→08-28). **Claude's memory file says the launch gate fired 08-25 with 13 signups/24h; the `users` table shows 2 signups 08-25→26 and a 12-signup week of 08-17.** The repo and the DB agree with each other; the memory note is what does not match. Flagged for Mike; memory not changed by this sweep.
Bounds: `CLAUDE.md docs/ *.py routes/ js/ *.html scripts/ README.md TODO.md`; doc keyword set `currently|not yet|as of|still|TODO|pending|awaiting|N rows|file:N`; code set `TODO|FIXME|temporary|for now|until|will be|not yet|currently|as of 2026`; WWLO top 300 lines; RO live counts. grep vs rg identical on every scoped search (CP1 72/72, ARCHITECTURE 33/33, TODO 22/22, LR 38/38, SECTION_F 7/7, README 1/1, code comments 80/80); one out-of-scope difference `scripts/` code comments grep 16 / rg 11 / rg --no-ignore 13 (`cp1_*.py`). First rg pass with `-E` returned zeros, re-run with `-e`. A `~$AY_CAPTURE_WEEKLY.docx` Word lock file is present in `docs/`.

**✅ P5 CHECKPOINT — a value measured one way and described another (full sub-report in scratchpad `sweep_P5_full.md`).** Positive controls: the backfill drain keyed on exact spelling CONFIRMED (`scripts/backfill_canonical_titles.py:81–95`); SOURCE DRAIN per-table vs whole-corpus CONFIRMED (`scan(cur, table)` per table in `main()` :145–147). **The "stylesheet-occurrence coverage" control did NOT confirm** — `scripts/coverage_assessment.py` is a SQL coverage report with no CSS logic; the nearest in-bounds analogue is `CP1_STATE_OF_PLAY.md:150–151` treating "0 occurrences of 'confidence' in collectioncalc.js" as evidence of non-display. The 09-03 close's "purple-contrast list INVALID (rebuild from live computed styles)" is the likely origin of that control and is not in these bounds.
**USER-facing:**
- **`app.html:2988` "Based on ${sources.total} sales."** — rendered under the ROI tagline on every reliable verdict (:3020–3030). `sources.total` = ebay + whatnot counts (`sales_valuation.py:1326–1327, 1412–1415`) = `len(ebay_graded)+len(ebay_raw)+len(market_graded)+len(market_raw)`: the graded lists still contain `is_variant` rows (partitioned in Python at :889–892, never removed from the lists), rows with grade/price ≤ 0 that never entered a bucket, every raw sale and every other-grade sale. The ROI it sits under is the `exact` bucket (≥3 same-grade non-variant comps) minus the raw median. On a book where the variant note fires, the tagline counts the very sales the note beside it (:3158) says were set aside.
- **`js/verdict_basis.js:101` (`thin`, key at :99) "the ${nearbyThin} nearby sale(s) are one per grade"** — `nearby_thin_comps` = every non-variant graded sale of the book at ANY other grade (`sales_valuation.py:951–952`, no distance bound; a 1.0 sale is "nearby" a 9.8 request). The file corrects exactly this word for `low_support` (:202; comment :189 "at other grades, NOT near") but leaves "nearby" in `thin`.
- **`js/verdict_basis.js:320` (reliable + `roi == null`) "There are no recent ungraded sales"** — the raw window is 365 days (`sales_valuation.py:49`); the file's own comment at :82 (`// NO "recent": lookback is 365 days with NO recency weighting.`) bans "recent" for this reason (L-SW-2026-020 instance 1). Raw variants are dropped in SQL (:762), so "no ungraded sales" can be false with variant raw sales present — the `fabricated` tombstone (:226–231) records that; this arm does not.
- `js/verdict_basis.js:180` (`low_support`) "Only ${nearbyThin} graded sale(s) … at other grades" — post-variant-partition; graded variant sales are not mentioned in this tier though `excludedVariants` is available to it (minor).
- **`routes/sales_valuation.py:1788–1824` (`/api/sales/fmv`, consumer = Whatnot extension)** — `tiers.mid.grades: '4.5-7.9'` also receives EVERY ungraded sale (:1709–1710 `sale_grade is None → mid`), so the "4.5–7.9" count/average and `fmv_sample_size`/`confidence` are graded-4.5–7.9 plus all raw at any grade; `tier_priority` fallback (:1752–1763) prices a 9.0+ request from 'mid' when top/high are empty — i.e. from raw sales of any grade — labelled as the user's grade.
**DOC:**
- `docs/LAUNCH_READINESS.md:114` "89% of keys have 1–2 comps" — `CP1_STATE_OF_PLAY.md:259` corrected to 84.6% (4,661/5,509) and :352 to 85.3%; the denominator is populated `(title, issue, grade)` CELLS in the 365 d graded pool (:244), not keys, and excludes 0-comp cells a user can request; LR carries neither the correction nor the denominator.
- `sales_valuation.py:921–923` (echoed `verdict_basis.js:114–118, 137–139, 150–152`) "Measured on the live corpus, 95.6% of interpolated cells are one-sided" — source `scripts/cp1_floor_and_k2.py` (:81–82, N=900 random sample) over `cp1_identity_lib.py`'s frame: **ebay_sales only**, 365 d, `grade IS NOT NULL` (not `graded=true`), no signature exclusion, no raw_title junk/range guards (production since 08-14/08-16), and a 23-point ladder incl. 0.5/1.5/2.5 that production's `grade_baselines` (:1031–1035) does not price. "Live corpus" = a 900-cell eBay-only sample over a wider ladder.
- `scripts/corpus_snapshot.py:220–260` "DEPTH DISTRIBUTION — populated graded cells", "METHOD MIX … Mirrors shipped tiering", "verdict shown on X% of cells" — `ebay_sales` only while live valuation unions `market_sales`; `NOISE` (:63–69) omits the signature exclusion and the multi-issue-range guard despite ":15 mirrors SHIPPED valuation behaviour"; method-mix denominator = (keys with any graded OR raw sale) × 20, so raw-only keys inflate the hedged share.
- `scripts/coverage_assessment.py:69,83,140` "ALL ebay rows" (filtered to non-empty canonical_title), "VALUATION-ELIGIBLE: graded, fresh ≤365 d, not variant/lot/reprint" (omits the raw_title LIKE chain, signature exclusion, range guard → overstates production eligibility).
- `scripts/cp1_fallback_audit.py:236–248` "corpus-level branch split" — computed over `--pairs` md5-sampled pairs (:201–214), not the corpus (**rg-invisible file**). `scripts/cp1_confidence_measure.py:552` "Variant-filter cost: X of Y comps discarded" — over the `--sample` N pairs (default 200), unstated; `:166` "BASE-TABLE CORPUS TOTAL" = every public table matching a price-like AND date-like column regex.
- `admin.html:391` "API Calls (24h)" / "N failed" ← `count(*) FROM request_logs` 24 h, which logs every request except `/`, `/health`, `/favicon.ico` — CORS preflights, static served by Flask, expired-token 401s and bot 404s all count as "API calls", and since the 08-06 `non-json-<code>` change every ≥400 with a body counts as "failed"; per-user "API Calls" (`routes/admin_routes.py:120–126`) is ALL-TIME, no window — same label, two windows. `admin.html:396` "API Cost (Month)" ← `admin.py:80–90` fixed rate table: Opus $15/$75, **everything else at Sonnet $3/$15** (a Haiku call via `/api/messages` `tier` would be costed at Sonnet; no cache-token pricing); label drops "estimated"; "N calls" = api_usage rows (one per request, multi-run tokens summed), not model calls.
- `dependency_monitor.py:1157–1175` "Container memory X / Y MB (Z%) — sustained ≥85% across 3 samples (~15 min)" — X = cgroup v2 `memory.current` (:1082–1090), which includes page cache, not anon/RSS (the OOM-relevant number; LR's "~70% of 512MB steady" is the same reading); streaks are per gunicorn worker and sampled only when THAT worker receives `/health` ≥300 s after its own last sample, so "~15 min" is a per-worker floor, not a duration. DB-connection scope verified RO today: `used` = rows for `current_database()` = 3 (max_connections 103, usable 100) — matches.
**DEV:** `sales_valuation.py:1377` comment "null when interpolated/estimated or < 5 exact matches" — `bootstrap_ci_median` (:428–435) runs on the TRIMMED list; `percentile_trim` (:206–215) removes 2 for 3 ≤ n < 40, so CI is null for `exact_count ≤ 6`, not < 5 (not displayed; the "Priced from N sales" strings are unaffected — a symmetric trim leaves the median unchanged). `routes/grading.py:885` `confidence = {1:65,…}` — a photo-count lookup labelled confidence, persisted to `collections.confidence` (`routes/collection.py:64,140,156`) and gating `js/grading.js:2154–2157` "quality warning if confidence < 75%" (literally "1 photo"); not rendered as a percentage anywhere in bounds. `sales_valuation.py:1405` `nearby_thin_comps` comment "sales near this grade" — already documented MISNAMED (`verdict_basis.js:166–170`). `:453–454` `variant_excluded_pct` — variant count taken before the `g > 0 and p > 0` filter, `total_graded` after it (asymmetric; only the boolean renders). `lookup_demand.comp_count`/`no_data` — valuation logs `total_graded + raw_count` (:1337, variants excluded), `/fmv` logs `len(all_sales)` (:1809) under a different filter chain; `no_data = not comp_count` (:123); one column, two measures — `CP1_STATE_OF_PLAY.md:300` "577 (47.0%) returned no_data" reads it as one (the doc does disclose 1,220/1,228 are /fmv).
- **"27% excluded" — NOT FOUND in these bounds** (only two unrelated 27.x% figures in `scripts/cp1_identity_*.py`); the P4-era reference lives in WWLO :4734 as a variant+lot+reprint share on a 53,840-row corpus (per the 09-11 newsstand entry), outside this sub-sweep's paths.
Bounds: `*.py routes/ js/ *.html scripts/ docs/technical/ docs/LAUNCH_READINESS.md CLAUDE.md`; not read: `CCExtensions/` (the `/fmv` consumer), `docs/sessions/`. grep vs rg: rg skips `scripts/cp1_*.py` and `scripts/cp1_output/` (`.gitignore:106–107`) — "corpus-level" and "Variant-filter cost" findings are rg-invisible; grep additionally counts `__pycache__/*.pyc` binary matches (`nearby_thin_comps` 6/5, `photos_used` 13/10, `estimated_cost_usd` 13/12); all other terms matched exactly.

**✅ P2 CHECKPOINT — unreachable code that still looks live (landed last; full sub-report in scratchpad `sweep_P2_full.md`).** Positive controls found (Photo Tips only in `58044d5^`; the six known dead grading.js functions; `processImageForExtraction` via the shadowed bulk path; the per-step spine prompt inside dead `analyzeGradingPhoto`). Method: plain grep with restricted paths + throwaway inventory scripts, every zero-caller claim re-confirmed with a bare word-boundary grep (two inventory false positives eliminated). Static analysis only — nothing executed in a browser. Page-load order that decides shadowing: app.html loads `utils.js, verdict_basis.js, auth.js, app.js, grading.js` (:1616–1620), then its inline scripts; a later classic-script declaration replaces the earlier global.
**(a) JS functions:**
- **The grading.js legacy cluster is larger than the known six.** Additional zero-caller: `retakeGradingPhoto` (:1828), `nextGradingStep` (:2000), `skipGradingStep` (:2019). Transitively dead: `analyzeGradingPhoto` (:1603 — holds the per-step spine prompt :1681–1694 and the only frontend fetches of `/api/extract` from grading.js and of **`/api/messages`** :1732), `performRotationAnalysis`, `setComicIdBannersLoading`, `editComicInfo`/`saveComicEdit`/`cancelComicEdit`/`updateComicIdBanners`, `renderAdditionalPhotos`/`removeAdditionalPhoto`, `startDotsAnimation`/`stopDotsAnimation`, `getOrientation`/`applyOrientation` (also shadowed by app.html :1738/:1798).
- **`calculateGradingRecommendation` (grading.js:2263) is shadowed by app.html:2678** — recorded in-file (:2255–2262, "Kept rather than deleted, Mike 2026-08-08") — but its transitive consequences are not: `getSlabPremium`, `getGradingCost`, `showCacheWarning`/`hideCacheWarning`, `startThinkingAnimation`/`stopThinkingAnimation`, `shuffleArray`, and the `thinkingMessages`/`seriousMessages` arrays (:152–~1027, ~880 lines) are referenced only from the shadowed function; **the sole in-repo caller of `POST /api/cache/check` (grading.js:2297) is inside it**. `generateGradeReport` (grading.js:2106) shadowed by app.html:2264 — documented stub.
- **`js/app.js` bulk-valuation path is dormant by shadowing**: `handlePhotoUpload(files)` (:389) is shadowed by app.html:1681's two-arg version; the app.js version is the only shower of `#bulkMode`/`#progressContainer`, so `extractFromPhoto`, `renderItemsList`, `rotateItem`, `deleteItem`, `valuateAll` (onclick at app.html:1406 inside hidden `#bulkMode`), `getValuation`, `showResults`, `sortResults`, `downloadExcel`, `resetApp`, `listItemOnEbay`, `toggleDetails`, `selectPriceTier`, `handleIdentifySignatures`, the thinking/progress helpers (:1079–1178, :507) and `refreshItem` (zero callers even inside) are unreachable on the only page that loads app.js. `js/utils.js` `processImageForExtraction` (known) and `getExifOrientation` (:51) ride on it.
- **`js/app.js` `setMode` (:355) throws before it can show manual mode**: :358 `getElementById('modePhoto').classList…` — `#modePhoto` exists in no HTML (only `#modeManual`/`#modeGrading`, app.html:1027–1028, which call `setMode`). The TypeError means :359–366 never run, so `#manualMode` (app.html:1033) never shows and the `#valuationForm` submit handler (app.js:1180) is unreachable. **A live, clickable control that throws.** (Static; not executed.)
- `js/utils.js` thinking/progress helpers (:216–279) dead on every page — target `#thinkingOverlay`/`#thinkingSteps`/`#progressBar`, which exist in no HTML; shadowed by app.js on app.html, uncalled on collection.html. app.html inline `showEditForm` (:2067), `saveEdit` (:2150), `cancelEdit` (:2074, only from `saveEdit`) — zero callers, reference `#editExtractedBtn`, which exists nowhere. `runSignatureCheck` (:3421) zero callers — deliberately disconnected per :2635–2643 (recorded-intentional). `js/auth.js` `saveToCollection`/`showCollection`/`saveAllToCollection` (:400/:428/:457) all shadowed by app.html inline versions; the auth.js `showCollection` still alerts "Full collection view coming soon!" (dead text — P1 also found it). Smaller: `js/utils.js` `getAuthHeaders` (:39), `js/collection.js` `viewDetails` (:741 TODO stub), `exportSelected`/`deleteSelected` (documented no-op stubs, controls disabled), `login.html` `clearSignupEmailLock` (:932, comment says KEPT).
- **`js/thinking_messages_expanded.js` — the whole file is unreachable**: no `<script>` tag, no sw.js precache entry, no fetch; ends in CommonJS `module.exports` (:1112) and declares top-level `const thinkingMessages` (:7), the same name as grading.js:152, so it could not load alongside grading.js without a SyntaxError.
- **`modal-ebay-listing.html` — orphan page**: nothing loads or links it (the only mention is a comment at `js/pixel.js:16`); its inline functions (:494–787) are near-verbatim duplicates of `js/ebay-modal.js` :34–453, which collection.html actually loads.
- **Shadowed pairs (later wins):** utils.js ↔ app.js (7 thinking/progress helpers — app.js wins); grading.js ↔ app.html (`calculateGradingRecommendation` 2263/2678, `generateGradeReport` 2106/2264, `getOrientation` 1169/1738, `applyOrientation` 1250/1798, `saveGradeToCollection` 2544/3306 — app.html wins); app.js ↔ app.html (`handlePhotoUpload` 389/1681 — app.html wins); auth.js ↔ app.html (3 collection functions — app.html wins). Cross-page duplicates (not shadowing): login.html vs auth.js (6 auth handlers), account vs sightings (`loadSightings`, `respondToSighting`), admin vs dashboard (`loadDashboard`), check/contact/verify (`onTurnstileSuccess`), admin vs signatures (`showToast`), collection.js vs admin (`formatDate`), utils.js vs sightings (`escapeHtml`).
**(b) DOM:** ids referenced by JS that exist in no HTML and are not JS-built: `modePhoto` (app.js:358 — LIVE path, above); `gradingStep1`/`gradingStep2` (app.html:2272–2273 inside the live `generateGradeReport`; null-guarded — a lookup for a step indicator that no longer exists); `gradingStep5`, `gradingNext1`, `gradingSection`, `additionalPhotoInput`/`additionalPhotos` (dead grading.js paths); `editExtractedBtn`; `thinkingOverlay`/`thinkingSteps`/`progressBar`; `listingDescription`/`descriptionValidation` (app.js:265–266 — exist only on collection.html, never where app.js loads). All other 694 id references resolve. `display:none` elements with no reachable show path: `#manualMode` (:1033, only shower is after the throw), `#bulkMode` (:1394) + `#progressContainer`, `#resultsMode` (:1411). The other 55 hidden ids all trace to a show site (not findings).
**(c) Flask routes:** population 121 (120 by decorator regex + `@collection_bp.route('')` at `routes/collection.py:54` by hand); all 25 blueprints registered (`wsgi.py:317–341`); no unregistered blueprint; parameterised routes hand-verified. **No in-repo caller — could not determine (27):** `GET /api/admin/moderation`, `POST /api/admin/backfill-barcodes`, `GET /api/admin/barcode-stats`, `GET /api/admin/slab-guard-stats`, `POST /api/admin/signatures/<id>/image` (legacy alias; signatures.html uses `/images`), `DELETE /api/admin/grade-submissions/by-user/<id>` (erasure), `GET /api/barcode-test`, `POST /api/barcode-scan`, `GET /api/billing/plans`, `POST /api/billing/check-feature`, `POST /api/billing/record-valuation`, `GET /api/images/status`, `POST /api/images/upload-extra`, `POST /api/images/delete-extra`, `GET /api/images/extra-types`, `GET /api/marketplace/platforms` (0 doc mentions), `POST /api/monitor/check-hash`, `POST /api/monitor/compare-copies`, `POST /api/ebay-sales/backfill-titles`, `GET /api/ebay-sales/stats` (only textual match is `CCExtensions/ebay-collector/api_endpoints.py:79`, a "copy into wsgi.py" snippet nothing imports), `GET /api/registry/status/<id>`, `GET /api/signatures/v2/match/stats`, `POST /api/signatures/match` (v1; only `test_signature_matcher.py`), `GET /api/signatures/db-stats`, `GET /api/signatures/signed-sales`, `GET /api/signatures/premium-analysis`, `GET /api/debug/prompt-check`. docs/ mention counts are consistent with curl/DBeaver admin use but are not evidence of a caller. **Caller exists but is itself dead:** `POST /api/cache/check` (grading.py:256; sole caller inside the shadowed function). **Called externally by design, verified:** `/api/ebay/account-deletion`, `/api/ebay/callback`, `/`, `/health`, `/api/waitlist/verify` (email link), `/api/verify/watermark/<serial>` (URL returned by lookup). Extension callers confirmed for the ebay-collector, whatnot-valuator and slab-guard-monitor endpoints.
**(d) CSS:** population 688 class-selector occurrences / 321 distinct (styles.css 554, app.html style block 134), full set checked. **68 distinct classes with no literal match in any HTML or js:** the deleted Photo Tips family `.tips-modal*`/`.tips-section` (styles.css:2273–2335); the step indicator `.grading-progress`/`.grading-step`/`.step-number`/`.step-label`/`.grading-step-line` (:1365–1430, :2346–2361 — the thing app.html:2272 still looks up); the grading.js legacy UI family `.grading-required/-optional/-patent/-instruction/-comic-id/-preview*/-tips`, `.tips-toggle`, `.grading-additional`, `.additional-photos`, `.feedback-icon/-text` (:1466–1664); `.photo-option-btn*`, `.grading-photo-options`, `.mobile-only`/`.desktop-only` (:2425–2531; app.html:227–279); app.html style-block rules with no markup: `.slab-calc-flow`/`.calc-*` (:284–332), `.photo-diagram*` (:338–481), `.upload-box-icon` (:582, :762), `.defect-section`/`.defect-pills`/`.defect-pill` (:774–825); styles.css miscellany `.row-3/-4`, `.checkbox-row`, `.item-value-range`, `.value-fair`, `.value-range-small`, `.item-refresh`, `.confidence.very-low`, `.source-badge`, `.ebay-info`, `.thinking-icon`, `.calc-num1`, `.api-setup*`, `.error-msg`, `.collection-header/-title/-empty*`. **Footer (the known instance), two candidates:** `.tips-modal-footer` (styles.css:2335) matches nothing; the element rules `footer {…}`/`footer a` (styles.css:893–895) render nothing on app.html and collection.html (no `<footer>`, no footer.js) and apply only on sightings.html, which loads root `/footer.js` (a tracked live duplicate of `js/footer.js`, per `pixel.js:13`). Caveat: string-concatenated class names are caught only if the literal appears; `js/collection.css` and other pages' style blocks not swept.
Bounds: `body.html` excluded (untracked Next.js dump, not this project); docs/ consulted only for route mention counts; static analysis only; decorator-regex route detection (all 126 `.route(` occurrences accounted for); dynamic dispatch not tracked beyond literal grep; extensions swept as callers only. grep vs rg: ten probe patterns identical once regex dialects matched (`rg '\.route('` does NOT return 0 — it aborts with `regex parse error: unclosed group`, exit 2, and reads as zero only if stderr is discarded and empty stdout is piped to `wc -l`; the trap is loud unless suppressed — verifier); one genuine difference `api/cache/check` grep 4 / rg 3 (a `.pyc`); files rg silently skips in the swept paths: 50 `__pycache__`/`.pyc`, `scripts/cp1_output/*`, and 11 source files (`reset_test_passwords.py`, nine `scripts/cp1_*.py`, `scripts/e3_edge_sequence_test.py`) — the cp1 scripts are the callers credited to `/api/sales/fmv` and `/api/monitor/check-image`; `rg --files` = 194 vs `find -type f` = 279 over the same paths.

**🏁 ALL SEVEN LANDED 2026-09-14.** Order of arrival: P7, P6, P3, P1, P4, P5, P2. Every sub-sweep ran its positive
control and reported grep-vs-rg; the recurring tooling facts are themselves P3 instances and are recorded once here:
(1) `rg -E` is `--encoding`, not extended-regex — three sub-sweeps' first rg pass returned zeros for that reason and were
re-run; (2) rg silently skips `scripts/cp1_*.py`, `scripts/e3_edge_sequence_test.py`, `reset_test_passwords.py`,
`__pycache__`, `scripts/cp1_output/`, `.claude/skills/` (unless passed explicitly) and, NON-DETERMINISTICALLY with two or more
path arguments, sometimes leaks 8 of the 9 `scripts/cp1_*.py` (a parallel-walker race; `-j1` never leaks — verifier, 10 runs each); (3) grep
counts `.pyc` binary matches that rg does not; (4) `rg '\.route('` aborts with a regex parse error (exit 2) rather than returning 0 — it reads as a null only when stderr is thrown away. Three sub-sweep
findings are rg-invisible (`cp1_nesting_audit.py --outside`, `cp1_fallback_audit.py "corpus-level"`, `cp1_confidence_measure.py
"Variant-filter cost"`). **One positive control did not confirm** (P5: the "stylesheet-occurrence coverage" instance is not in
`scripts/coverage_assessment.py`; it likely refers to the 09-03 purple-contrast list, outside P5's bounds) and is reported as
such rather than forced. **One new shape, named rather than forced into a category (P7):** *backend module-level state is
per-gunicorn-worker AND reset every ~30–60 min by `--max-requests 500` under Render health polling*, which turns "daily"
and "hourly" limits and multi-sample alert streaks into per-worker-per-recycle quantities — it is not P7 (never resets) but
its inverse (resets when it should persist). **Verification agent (whole entry, read-only, spot-check of the highest-impact claim per block):** 31 confirmed / 6 wrong /
0 uncheckable. The six: the rg mechanism (race, not argument-set); four line references (moderation :280–290; CLAUDE.md :131;
verdict_basis :101/:189/:202 and :320/:82); and the `rg '\.route('` framing (it errors loudly). All corrected in place, first
drafts tombstoned where the claim itself changed. Precisions folded: valuation strip :2543; mid-tier :1709–1710; the
whatnot-valuator defect exists in both the stale `WV/` copy and the live `CCExtensions/` copy; `modal-ebay-listing` has one
comment mention. Consolidated ranking is in the 2026-09-14 reply to Mike **and, as the durable queue, in `docs/sessions/ROADMAP.txt` § "🧹 Pattern-Sweep Queue (2026-09-14) — ranked on consequence and reachability, not effort"** (verified 37/1/0; the one wrong was a misattribution of two already-queued items to the close list instead of the 09-11 newsstand entry — corrected) — the agent's consequence-and-reachability order with two amendments from Mike (the terms-page purge promise pulled out of the records batch onto its own line; the Manual-mode toggle left UNRANKED pending a browser check). The roadmap carries the queue and the why, this entry carries the evidence; neither repeats the other. Eleven of the roadmap's own lines were annotated in place as stale or superseded (P4 applied to the roadmap itself); the project-storage docx `SW Roadmap 2026 08 26` is noted there as stale and authoritative-no-longer, not updated (Mike holds project storage).

## 2026-09-13 — 🔒 **SESSION CLOSE (Mike's record; conversation `05e7e4ef-890f-48e9-824f-8749f200ea15`, 09-10 → 09-13). Nothing to act on. Checkable facts re-verified at close; three small precisions noted inline.**

**MOST RECENT CHANGE (Rule 5): session closed 2026-09-13 with every unit of the week shipped and
recorded, one unit parked with its reasoning, and the open list below as the priority order for the
next session. Live backend `fb3e0a8`; HEAD `56fe022` (the Rekognition characterisation, committed by
Mike); `main` == `origin/main`; working tree carries only the two pre-existing docs modifications
and 15 untracked entries.**

**Shipped, deployed, asserted, recorded (all three verified live 09-13, see SHIP RECORDS):**
- `58044d5` — spine capture instruction (45° + consistency note), FAQ straight-on rule scoped, dead
  Photo Tips modal and its seven-month dangling pointer deleted. Frontend only.
- `a19ffec` — newsstand honesty: FMV note and verdict-basis clauses describe labelling, not edition;
  "standard cover" dropped; note contrast 3.58 → 6.65:1.
- `fb3e0a8` — photo-too-small: front cover named, 400 px floor stated from the constant and returned
  in the JSON, results header branched with the reset, tip contrast raised.
- Plus the ship-record reconciliation (`93a43f3`), the rapidfuzz closure (`3fc5777`) and the
  Rekognition characterisation (`56fe022`) — records only.

**Parked with its reasoning:** the upload-box pre-flight. Path A rejected on measurement — 562 grade
requests, twelve too-small rejections, all four of Mike's accounts, none from the other 34 users;
revival condition is the runnable query in the 🅿️ entry (0 rows today); the design read (amber ⚠ not
red X, property-and-number wording, Generate stays enabled, server stays the only gate, the three
conditions for a narrow per-box promise) is preserved for revival.

**OPEN, in Mike's priority order (2026-09-13):**
1. **Save to Collection can write the previous book's grade under the current book's title.**
   Reachable by construction: `saveToCollection` guards on `gradingState.finalGrade`, set only on
   success and never cleared; `extractedData` is overwritten on the next identification. A
   data-corruption path in a collection product — highest-priority open item. (Rekognition entry,
   Part 2.)
2. **`/api/extract` moderates BEFORE it normalizes**, so a raw upload over 5 MB is never screened at
   identification (Rekognition returns a validation error, the fail-open branch allows it, the row
   is logged as a "warning"). 21 logged instances, latest 2026-09-12, on the route most users hit
   first.
3. **"Please try again" on a deterministic moderation rejection** — one line (`app.html:2667`, :2672),
   wrong advice; should not wait for the reason-code unit.
4. **The `Weapon Violence` threshold.** All three grading-product rejections are that one label, all
   within twelve points of the 80 floor, and the label is non-deterministic near the floor (user 68's
   photos scored 84.1 / passing / 90.2 across re-encodes of the same book). A configuration
   decision, Mike's to make; not a code change. Not proposed by Claude.
5. **The reason-code unit**, widened to carry the failing photo label and a `moderation` value, covering
   both failure screens through one renderer and hiding Save on failure (closes item 1's surface as
   well).
6. **The upload box has no reset path** and re-selecting the same file fires no event (LIVE DEFECT 1
   in the 🅿️ entry).
7. **Generate is enabled after a failed extraction** (LIVE DEFECT 2 in the 🅿️ entry).
8. **Dependency-monitor roster gap:** Third-Party rule step 4's letter is unmeetable for any healthy
   check because `/api/admin/dependency-status` emits warnings only.
9. **Repo hygiene (⚠️ the `~$*` gap and the lock file are FIRST recorded here, not carried):** 15 untracked entries — 14 at session start plus `docs/~WRL1970.tmp`, a Word autosave that disappears when the docx closes, which a `~$*` pattern would NOT cover (incl. two Claude report drafts `REPORT_DRAFT.md` /
   `GUARD_REPORT_DRAFT.md`, `body.html`, `headers.txt`, `UniqueProperties/`, the docx pile); `~$*` into
   `.gitignore` (⚠️ precision: `.gitignore:24` already has `~$*.docx` — the gap is the general `~$*`);
   the lock file that broke two history searches (Mike's observation — not reproduced in this
   session; recorded on his word); the nested `.claude/worktrees` copies (18 directories, they
   inflate filesystem audits and hang unrestricted greps — this session hit that once); and
   `docs/API_SPEND_LEDGER.md` still UTF-16 (BOM `FF FE`), last committed `ff67ce2` 2026-08-14,
   modified 2026-08-30, uncommitted since.
10. **Stripe three majors behind (⚠️ FIRST recorded here; no earlier record in this file)** — `requirements.txt:32` pins `stripe>=12,<13` (Mike: 12.5.1
    installed) against PyPI **15.6.1** (checked 09-13), on a live billing integration that has already
    had one API-move incident.

**Verification agent (close record, read-only):** 7 confirmed / 0 wrong / 0 uncheckable; two precisions
folded in above (the autosave temp file; items 9–10 are new). Every open item 1–8 has a matching earlier
record in this file.

**Two method findings worth carrying (Mike):**
- **Cloudflare Pages answers `/app.html` and `/faq.html` with a 308** to the clean URL, so a bare
  `curl -s` gets an empty body and every grep returns zero — indistinguishable from a failed purge.
  Use `curl -sL` or the clean URL; `/js/…` serves directly. Every curl assert written for `.html`
  paths this week was wrong for that reason (SHIP RECORDS entry carries the mechanics; platform
  default, nothing in the repo configures it).
- **A pushed-but-undeployed commit is invisible:** clean `git status`, branch up to date, and `/health`
  reports a hard-coded `5.6.0` (`routes/utils.py:23`, unchanged since March). Making the version
  string reflect the deployed commit would turn a dashboard visit into a one-second check. **Worth
  its own lesson once the fix exists** — not written yet; the Render deploys endpoint (GET) is the
  interim check and is what this week's verifications used.

**Standing constraints unchanged:** Mike runs all git, deploys, env changes and production writes.
Claude never commits, pushes, deploys or writes to production. Verification agent before presenting.
A later record that contradicts this one → stop and say so.

## 2026-09-13 — 🔎 **Rekognition false positive (ASM #361 back cover) — READ-ONLY CHARACTERISATION. No code change, no fix proposed. Verified 52 confirmed / 10 wrong (line refs and two scope words) / 1 uncheckable; corrections folded in. Headline: it was `Weapon Violence` 91.3% on the BACK cover, blocked via its parent `Graphic Violence`; the whole grade aborts; NO credit is lost; Save can write the PREVIOUS book; and every block on the product's own surfaces is that one label.**

**MOST RECENT CHANGE (Rule 5): this characterisation, recorded 2026-09-13. Nothing in the tree
changed. The moderation policy set on 2026-08-25 is unchanged and not proposed to change here.**

**Part 1 — configuration (`content_moderation.py`).** Threshold `MODERATION_CONFIDENCE_THRESHOLD = 80`
(:40) → Rekognition `MinConfidence` (:219). `BLOCKED_CATEGORIES` (:53–65) is exactly `'Explicit'`
(L1), `'Graphic Violence'` (L2 under Violence — catches Weapon Violence, Physical Violence, Self-Harm,
Blood & Gore, Explosions and Blasts via ParentName), `'Hate Symbols'` (L1). `WARNING_CATEGORIES`
(:82–85) is `'Violence'`, `'Visually Disturbing'`. Match rule :241–243 (Name / ParentName /
"Parent: Name"); `reason` = first blocked label (:259, :264). A cover returning only `Violence` +
`Weapons` PASSES with a warning (verifier confirmed from the loop and from rows 71/95/96).

**What fired — recovered.** `content_incidents` id 112, 2026-09-11 20:57:35 UTC, user 3, `/api/grade`,
hash `06de0b57fc…`: **`Weapon Violence` 91.3** (parent `Graphic Violence` 91.3, `Violence` 91.3).
Render `[GRADE-TIMING]` for the request: `images=4 dims=484x720,80x1096,478x714,872x706
moderation_calls=3 outcome=moderation_blocked title='The Amazing Spider-Man' issue='361'`; the loop
increments `_mod_calls` before each call (:747→:748) and the client sends front, spine, back,
centerfold (`app.html:2339`, `:2376–2385`), so **call 3 = the 478×714 back cover**. `[MODERATION]
BLOCKED: Weapon Violence (confidence: 91.3%)` same second.

**How often (RO, `content_incidents` 2026-02-12 → 09-12):** 113 rows; **71 blocked**; blocked by
endpoint `/api/vision/analyze` **68** / `/api/extract` 1 / `/api/images/submission` 1 / `/api/grade`
1; by month Feb 18, Mar 44, Jun 1, Jul 1, Aug 4, Sep 3; users WITH A BLOCK: **2** — user 3 (Mike admin)
69, **user 68 (real, free, joined 09-01) 2**; 71 distinct hashes. By label: Exposed Female Nipple
26, **Weapon Violence 20**, Exposed Buttocks or Anus 18, Exposed Female Genitalia 5, Blood & Gore 1,
bare `Explicit` 1. The 68 vision/analyze blocks are the **Whatnot valuator extension**
(`CCExtensions/whatnot-valuator/lib/vision.js:106`, its only caller) — operator use on listing
images: 49 Explicit-Nudity family (82.9–99.9), 18 Graphic-Violence family (80.5–95.9), 1 bare
Explicit 90.7. **On the grading product's own surfaces every block is `Weapon Violence`** — 84.1
(extract), 90.2 (submission), 91.3 (grade) — all within 12 points of the 80 floor; 2 of those 3 are
a real user. `request_logs` agrees: 71 × `Image rejected: inappropriate content detected.`, same
split.

**User 68, 2026-09-03, mobile (the only real-user blocks):** 00:52:45 `/api/extract` **400 — the
FRONT cover rejected at identification** (84.1); 00:54:56 `/api/extract` 200 with a different image
(the re-shoot the brief says not to propose, performed unprompted); 00:55:39 grade 200 with all
four passing; 00:57:42 **one of the four collection-save uploads rejected at 90.2**
(`/api/images/submission`, hash differs — the save path re-encodes at 1568/0.85) while three stored
and `/api/collection/save` returned 200. Two facts: the label is non-deterministic near the floor
across re-encodes, and **the save path already drops the photo and keeps the record — silently**
(`app.html:3663` catches the per-photo error, the slot stays `null` from :3607, save proceeds :3730).

**⚠️ Side finding (verifier): 39 of the 42 "warn-only" rows are NOT content warnings.** Their `labels`
payload is one string — Rekognition `ValidationException … image.bytes … less than or equal to
5242880` — the fail-open branch (:281–289) logged as a warning (:330). Split: `/api/extract` **21**
(2026-03-15 → **2026-09-12**, still occurring), `/api/grade` 15 (03-15 → 06-16, none since the 07-12
normalize-before-moderate change), `/api/messages` 3. **`/api/extract` moderates at :355 BEFORE
normalizing, so any raw upload over 5 MB is never screened at identification.** Only 3 real
content warnings exist (Weapons/Violence). Logged, not acted.

**Part 2 — the failure path (`routes/grading.py`).** **All four images are moderated**, one Rekognition
round trip each, sequentially, no `break` (:743–759). The front is also moderated at `/api/extract`
(:355–365), so a front rejection normally surfaces at identification. **On any rejection the whole
request aborts** — `return jsonify({'error': 'Image rejected: inappropriate content detected.',
'moderation': True}), 400` (:754–757); no vision call, no result, no retention row; the response
names no image and no label. **Credit: NONE lost, nothing to refund.** The credit is
`users.gradings_this_month`; its only writes are the new-month reset to 0 in the cap check (:569),
the **increment at :866–870 after the vision call and `log_api_usage` (:859)**, and the refund
decrement (`sales_valuation.py:78–82`, keyed on `grade_submissions.grading_uuid` for the
multi-edition refusal, which happens AFTER a counted grade). The moderation return at :754 precedes
the increment, as do the quality (:727) and undecodable (:674) returns — no 400 path increments the
counter. `vision=-1ms post=-1ms` on the 09-11 line confirms the counted stages never ran. **Save to
Collection on a failed grade:** the button is a static `.results-actions` div (`app.html:1318–1321`),
no id, no visibility logic — shown on both failure branches. `saveToCollection` (:3574) guards on
`gradingState.finalGrade` (:3576), set only on success (:2536) and never cleared. Fresh page → "No
grade data to save". **But after one successful grade in the same page session, a rejection on the
next book leaves the FIRST book's `finalGrade` in place while `extractedData` now holds the SECOND
book (:1921): Save writes the previous grade (:3681) under the new title/publisher/year
(:3677–3680).** Not observed in the data; reachable by construction. **The `--` title** is the
default markup (:1198): the moderation 400 has no quality flag, falls to `throw` (:2515) and lands in
the generic catch (:2653–2673), which never sets the title; it shows header "Something went wrong"
(since `fb3e0a8`), body "Error: Image rejected…" + **"Please try again or contact support."** (:2667,
muted token), badge "ERROR", tagline **"Grading failed. Please try again."** (:2672). No client-side
moderation handling exists.

**Part 3 — the expected shape is SUPPORTED by the code; small on the server.** Moderation runs on
the already-assembled `images` list; everything downstream consumes that list AFTER the loop —
`image_content`/`photo_labels` (:764–775), `build_grading_prompt` (:779), `photos_used`/`confidence`
(:884–885), retention (:965). Dropping a rejected non-front image is a list filter at the loop plus
a record of what was dropped; front = `images[0]` (front required, keys 1..4), so "only a rejected
front fails" is an index test. A three-photo retention row is already a normal shape. ⚠️ The model's
`areas_not_visible` field (`grading_engine.py:283, :344`) reaches the response but **the client
never reads it** (0 hits in app.html / js), so the "tell the user which surface was excluded" half
is client work from scratch: an explicit `excluded_photos: [{label, reason}]` in the response and a
result-card line ("Back cover: not assessed — image excluded"). Estimate: server ~20 lines in one
function; client ~30 lines + copy; no new endpoint; no change to the set. Not proposed here.

**Part 4 — the error-state family, scope only (state after `fb3e0a8`):** quality branch (:2478–2513)
= header "Photo check", names "front cover" (hard-coded — wrong for blur/undecodable, queued unit),
title set, server tip; generic catch = header "Something went wrong", names nothing, title `--`,
"Please try again" twice. Both show Save and Grade Next. **One change covers the family:** a single
`renderGradeFailure({header, title, label, badge, body, tip})` fed by a server `reason`
(`resolution | blur | undecodable | moderation`) plus the failing photo label — the already-queued
reason-code unit widened by one value — and hiding `.results-actions` (or Save alone) on every failure
render, which also closes the previous-book save. **The "Please try again" copy is a one-line fix and
should not wait for that unit.**

**Not the answer (per Mike):** re-shoot advice (user 68 did it anyway; for many books every photo of
that surface fails identically); a second vision call. Recorded for the record only: the false-positive
surface in this product's data is ONE label, `Weapon Violence`, entering through the parent
`Graphic Violence`; any policy change is a separate decision.

**Uncheckable:** Render log lines older than ~2 weeks (the logs API rejects a start before 09-01), so
pre-September `moderation_blocked` timing lines cannot be confirmed from the API; `content_incidents`
is the durable record and is complete for the product surfaces.

## 2026-09-13 — ✅ **rapidfuzz post-deploy check (Third-Party rule step 4) CLOSED. Mike ran it in the Render shell on 2026-09-11: `'rapidfuzz' in inspect.getsource(check_all)` → `True`, `check_rapidfuzz(force=True)` → `[]`. Relayed 2026-09-13 (Mike, via Bilbo). Was carried as "still owed" in two places below — tombstoned.**

**Provenance, stated plainly:** this is Mike's terminal fact, not something a Claude session can
observe (no Render shell access). It is recorded on his word. What IS independently verified from
here: the deployed commit (`fb3e0a8`, live 2026-09-13 19:41 UTC, whose ancestry includes `2e27098`)
carries the check as the 7th `check_all` entry with `RAPIDFUZZ_VERIFIED_MAJOR = 3`; the same code run
locally on 09-10 returned `[]` at installed 3.14.3. Together with Mike's shell result the rule's
step 4 is satisfied for rapidfuzz; the pre-existing gap — the dependency-status endpoint has no
roster, so a healthy check is ABSENT from its output and step 4 as written cannot be shown from the
endpoint — stays queued as its own item, unchanged.

## 2026-09-13 — 🚢 **SHIP RECORDS for the three 09-11 units — all three LIVE and asserted. Reconciled against git, the Render deploys endpoint and the live site (read-only, 2026-09-13 ~18:30 PDT). Every line below that still called them pending is tombstoned in place.**

**MOST RECENT CHANGE (Rule 5): Mike reported deploy, purge and asserts complete on `a19ffec` and
`fb3e0a8` (2026-09-13); this entry verifies that, adds `58044d5`, and closes the L-SW-2026-030
step for all three. Supersedes every "SHIPS IN MIKE'S NEXT COMMIT", "NOT staged, NOT committed",
"ship record still owed" and "SHIP (Mike)" block for these units below.**

| unit | commit | committed (PDT) | deploy (Render, UTC) | purge + assert | live now |
|---|---|---|---|---|---|
| Spine capture instruction (caption, FAQ scoping, dead-modal deletion) — frontend only | `58044d5` | 2026-09-11 10:16 | none needed (no backend file) | done — `app`: `photoCaptureNote` 1, `photoTipsModal` 0, "Consistency matters more" 1; `faq`: "inconsistently angled" 1, "Photo tips" 0 | ✅ |
| Newsstand honesty (FMV note + verdict-basis clauses, note contrast) — backend + frontend | `a19ffec` | 2026-09-11 13:33 | `a19ffec` live 2026-09-11 20:33:37→20:34:23 UTC (= 13:33 PDT, Mike's figure); since deactivated by the next deploy, code carried forward | done — `verdict_basis.js`: "direct-edition label" 1, "standard cover" 0; `app`: `resultVariantNote…text-secondary` 1 | ✅ |
| Photo-too-small (front-cover naming, 400 floor from the constant, per-branch header, tip contrast) — backend + frontend | `fb3e0a8` | 2026-09-11 14:51 | `fb3e0a8` deployed twice: 2026-09-11 21:51 UTC (deactivated) and **2026-09-13 19:41:22→19:41:58 UTC = 12:41 PDT, Mike's figure, status live** | done — `app`: `resultDefectsTitle` 4 (Mike's assert also returned 4), "NEEDS A LARGER PHOTO'" 0, "NEEDS A LARGER FRONT COVER PHOTO" 1 | ✅ |

`main` == `origin/main` at `fb3e0a8`; the working tree carries no code change (only this file and the
two pre-existing docs). The live backend is `fb3e0a8`, which contains `a19ffec`'s change.

⚠️ **Assert mechanics, for the next ship block:** Cloudflare Pages answers `/app.html` and `/faq.html`
with **308 → `/app`, `/faq`** (clean URLs — Cloudflare Pages' platform default; nothing in the repo
configures it: `_redirects` holds only the collectioncalc.com rules and `_routes.json` is Functions routing,
so do not hunt for a redirect rule), so a bare `curl -s …/app.html | grep -c` returns 0 for
everything — a false failure. Use `curl -sL` (follow redirects), or the clean URL. `/js/…` paths serve
directly. The ship blocks below were written with bare `curl -s` and would have reported 0/0/0 on a
successful ship; Mike's assert of 4 was taken with the redirect followed. Verified 2026-09-13: 41 confirmed / 0 wrong (git, Render, live site, every tombstone). Recorded so the next
assert is not misread as a failed purge (L-SW-2026-022's failure mode is silent; a wrong probe is
the same silence from the other side).

## 2026-09-13 — 🅿️ **Front-cover pre-flight: PARKED by Mike (analysis kept; two live defects logged as their own items). No code change. The two 09-11 units are COMMITTED by Mike — `a19ffec` (newsstand honesty: FMV note + verdict-basis clauses) and `fb3e0a8` (photo-too-small copy + header + contrast); ⚰️ ~~their push / deploy / Pages build / purge / assert and the one-line ship records here are still Mike's steps~~ — DONE, see the SHIP RECORDS entry above (2026-09-13).**

**🟦 FRONT-COVER PRE-FLIGHT (Mike's brief, 2026-09-13) — ⚰️ ~~REPORT STAGE … Mike decides~~ → PARKED the
same day (block after §7). Verified 27/5/0; corrections folded in below. Analysis retained.**

**§1 What the box ✓ means today — confirmed: "file received", nothing more.** The ✓ is static markup
(`app.html:1103` front; :1114/:1126/:1141), shown by the `uploaded` class (CSS :632–634; green
`rgb(16,185,129)` :648). The ONLY writer is `handlePhotoUpload(photoType, files)` (:1681): after the
FileReader resolves — read own EXIF (:1708), `img.src` (:1711), rotate thumb (:1712), show (:1713),
add `uploaded` (:1714), remove `highlight`, update "N of 4" (:1718), highlight next (:1721), front
only: `await extractComicData` (:1724–1726), enable Generate if `photos[1] && extractedData`
(:1729–1731). **Nothing removes it**: no `classList.remove('uploaded')` anywhere; `window.gradingState`
is created once at script evaluation (:2236–2243; the `DOMContentLoaded` handler :2228–2234 only
highlights the front box); `grading.js`'s `resetGrading` (:2485) targets a different, dead object
and has zero callers; a page reload is the only reset. Extraction failure renders into
`#uploadProgressText` (:1990–1998) and touches no box; the grade-time rejection renders into the
result card only. Re-selecting the SAME file does not fire `onchange` (input value never cleared).

**§2 Can the client read dimensions?** JPEG/PNG/WebP — yes; the thumbnail `<img>` already holds the
data URL (:1711), so `naturalWidth/Height` exist on load; `min(w,h)` is rotation-invariant so EXIF
orientation is moot. **HEIC — not in Chrome/Edge/Firefox** (`<img>` errors, `naturalWidth` 0);
Safari decodes it. Inputs are `accept="image/*"`; iOS transcodes library HEIC to JPEG for such inputs
by default, so HEIC on the wire is mostly desktop-Chrome/Android. The server decodes HEIC everywhere
(`pillow_heif.register_heif_opener()` at `comic_extraction.py:60–61`, process-global, imported by
`wsgi.py:98` before any route). **Rule: a client check must treat "did not decode" as UNKNOWN — no X,
no ✓-as-validation — and fall through to the server.** Client/server divergence for decodable files:
only the long-edge cap, and for JPEG the draft-halving path (`comic_extraction.py:165–166`) can put
the short side under 400 at **aspect > 2.5:1** (measured: 2001×790 JPEG → 1001×395; PNG/WebP/HEIC
only at > 5:1) — not a comic (~1.5:1), but the bound is 2.5, not 5.

**§3 Is the 400 reachable from the client? NO.** After the 09-11 unit it is returned only in the
`/api/grade` FAILURE JSON (`min_dimension`); `/api/auth/me` returns id/email/verified/approved/admin
only; no config route exists; the client holds no 400 (nothing to duplicate yet).
- **Path A (recommended): three keys on the `/api/extract` SUCCESS response** — `image_width`,
  `image_height`, `grade_min_dimension` (from `GRADE_QUALITY_MIN_DIMENSION`). The extract route ALREADY
  runs `check_photo_quality_base64(image_data, purpose='extract')` on the raw upload (`routes/grading.py:341`)
  and discards the dict's `width/height` on success (`return jsonify(result)` :392 — plain dict, extra
  keys safe). The client already awaits that call on every front upload. Same measuring function as
  the grade gate; for a too-small image (short side < 400, long edge ≤ 2000) no shrink occurs on
  either path, so extract-time and grade-time dims are equal. HEIC covered. No client decode. Cost:
  ~3 backend lines in `routes/grading.py`, ~15 client lines + a CSS state in `app.html`. ⚠️ The ok
  dict's dims are post-`auto_orient_pil`, which forces portrait — fine for `min`, must not be shown
  as the file's orientation; the fail-open branch returns `width: None` → treat as unknown.
- **Path B: a config GET + client `naturalWidth`.** Instant on JPEG/PNG, blind on HEIC, new endpoint to
  monitor (Third-Party rule shape), client re-implements a server measurement. Not recommended.
- **Timing, stated plainly:** Path A shows the state when identification returns (5–20 s), not at file
  selection. ⚠️ Corrected coverage: Generate is enabled at THREE sites — :1969 (extract success),
  :1730, and **:2062 (extract FAILURE, after the manual-entry form)** — so on a busy/timeout
  extraction the button is enabled and Path A's dims never arrive; that user reaches today's
  grade-time card with no pre-flight. Also the `/api/extract` 400 for < 250px already surfaces the
  server's dimension message (:1913–1916), so Path A adds coverage for the **250–399 px band** on
  successful identifications — exactly the trigger case.

**§4 Design read.** Any negative state on a box says "this box was evaluated"; no glyph makes an X
mean "one property checked." The promise can be kept narrow on three conditions: (1) ✓ never changes
meaning — "received", every box, never upgraded to "passed"; (2) the negative state is shown only for
a property the SERVER measured with the gate's own function (Path A) — a preview of the server's
verdict, not a new client validation; (3) wording names the property and number, never a verdict:
"Too small to grade — 364×554px", not "Invalid". Glyph: a red X reads as "validated: false" and
implies the other three passed; an amber ⚠ reads as "heads-up about this file" and matches the
result card's amber (`#f59e0b`, :2505). My read: ⚠ over X; Mike's call. Zero-semantics fallback:
keep box ✓ untouched and carry the message in the existing advisory banner `#uploadWarning`
(:1163–1166, shown by `updateUploadProgress` :2192–2197) — less discoverable, implies nothing about
the other boxes. Whichever surface: the state must CLEAR on the next front upload (today's box is
write-once; the new state must not be).

**§5 Generate button — leave ENABLED.** The server is the authority and must stay the only gate; a
client block can be stale (file replaced), blind (HEIC), or wrong (any future divergence) and then
strands the user with no path to the authoritative answer. Enabled costs nothing new: ignoring the ⚠
yields today's failure card with the corrected copy. The identification call is already spent by the
time the state shows, so "save a vision call" does not apply.

**§6 Scope: Path A is modest** — `routes/grading.py` (BACKEND, three keys; `fingerprint_utils`
untouched) + `app.html` (FRONTEND: compare in `extractComicData`'s success branch, toggle a `too-small`
state on `#uploadBoxFront` with a caption, clear it at the top of the next front upload). No change
to the gate, the threshold, the upload path, or the other three boxes. Path B is where "more than
modest" begins. **Ship:** `deploy` for the backend FIRST; client must treat a missing
`grade_min_dimension` as unknown (no state) so a purged frontend against an un-deployed backend
degrades to today's behaviour; then push → ⏳ Pages build COMPLETE → `purge` → assert. Never purge
on the push.

**§7 Context (RO, verified):** `/api/grade` 516 requests through 09-11 (562 by 09-12: +46 on 09-12);
12 too-small 400s, all `desktop`, four accounts (3 admin; 7 "Mike+3"; 27 "MikeTest13"; 30 "Billing
Test 2") — all operator; 38 distinct users have graded, none of the other 34 hit the path. Overall
`/api/grade` traffic is 357 mobile / 205 desktop. Quality-of-experience on a rare path.

**🅿️ PARKED (Mike, 2026-09-13): the front-cover pre-flight is NOT built. Path A is not built. The
analysis below stays because the reasoning is the durable part.**

**Why parked — the measurement decides it.** 562 `/api/grade` requests (through 09-12), 12 too-small
rejections, all four accounts the operator's, none from the other 34 users who have graded. Path A
covers only the 250–399 px band on SUCCESSFUL identifications, so it misses the extraction-timeout
case — the moment a struggling user is most likely to need it. The original appeal was catching the
problem at file selection; Path A shows it 5–20 s later, when identification returns; Path B is
blind on HEIC and duplicates a measurement the server already makes. The design that motivated the
unit is not available at reasonable cost, so it is parked rather than compromised.

**What would revive it:** real-user traffic on this path — too-small rejections from accounts that are
not the operator's (query: `request_logs`, `endpoint LIKE '%/api/grade%'`, `status_code = 400`,
`error_message ILIKE '%too small%'`, `user_id NOT IN (3, 7, 27, 30)`). If it revives, the decisions
below are already made and should not be re-litigated:
- **Amber ⚠ rather than red X** (an X reads "validated: false" and implies the other three boxes
  passed; ⚠ reads "heads-up about this file" and matches the result card's amber `#f59e0b`).
- **Wording names the property and the number, never a verdict** — "Too small to grade — 364×554px",
  not "Invalid" / "Rejected".
- **Generate stays ENABLED; the server stays the ONLY gate.** A client block can be stale (file
  replaced), blind (HEIC), or wrong, and then strands the user with no path to the authoritative
  answer; ignoring the ⚠ yields the existing failure card, so enabled costs nothing new.
- **A negative box state keeps its promise narrow only under three conditions:** (1) ✓ never changes
  meaning — "received", every box, never upgraded to "passed"; (2) the negative state is shown only
  for a property the SERVER measured with the gate's own function (a preview of the server's
  verdict, not a client validation); (3) the state CLEARS on the next front upload.
- **Path of record if built: A** (three keys on the `/api/extract` success response — `image_width`,
  `image_height`, `grade_min_dimension` from `GRADE_QUALITY_MIN_DIMENSION`; the route already
  computes the dict at `routes/grading.py:341` and discards it on success; `return jsonify(result)`
  :392 accepts extra keys; client compares in `extractComicData`'s success branch; deploy backend
  FIRST and treat a missing key as unknown). Path B (config GET + client `naturalWidth`) is
  recorded as rejected: blind on HEIC in Chrome/Edge/Firefox, a new endpoint to monitor, a second
  implementation of a server measurement.
- **Client/server divergence, for the record:** none for decodable too-small files; the long-edge
  cap can only push a short side under 400 at aspect > 2.5:1 (JPEG draft-halving,
  `comic_extraction.py:165–166`) or > 5:1 (PNG/WebP/HEIC) — not a comic. HEIC and undecodable files
  must read as UNKNOWN client-side, never as a pass.

**Verification agent (parked block + two defects, read-only):** 14 confirmed / 4 wrong / 1 uncheckable —
the four were line refs (:392 not :394; :1913–1916 not :1917–1919; :1982–1987 not :1983–1988) and the
"no `.value = ''` anywhere" wording; all corrected in place. Revival query runs and returns 0 rows.

**🐞 LIVE DEFECT 1 (logged 2026-09-13, not fixed) — the upload box has no reset path, and re-selecting
the same file does nothing.** `uploaded` is added exactly once (`app.html:1714`) and never removed; no
reset flow exists in app.html (`window.gradingState` is created once at script evaluation
:2236–2243; `grading.js`'s `resetGrading` :2485 targets a different dead object, zero callers); a
page reload is the only reset. The four per-box `<input type="file">` elements are never cleared (the only `.value = ''` on
file inputs are in `js/grading.js` against ids that do not exist in app.html — dead; a fifth file
input, `#photoInput` :1064, sits in the never-shown bulk mode), so choosing the SAME file again does
not fire `onchange` and the handler does not run (HTML `change` fires only when the selection
changes; Chrome/Edge/Firefox behave so, Safari has historically fired it anyway, and a Chrome
dialog-cancel can clear the value — so the failure is a gallery/desktop-picker scenario; a
`capture="environment"` camera shot is always a fresh file). **Consequence:** a user who lands on a failure card (too-small, blur, moderation, generic
error) and tries to swap the photo — especially re-picking the same file after e.g. cropping or
re-exporting it under the same name — sees the same green ✓ and thumbnail and may believe the photo
was replaced when it was not. Real users reach failure cards (`request_logs`: 21 grade 400s, of
which 8 mobile from non-operator accounts 11/17/38/53 — all `error_message` NULL or the
`non-json-400` sentinel, so which card they saw is not recoverable; five of the eight predate the
current card code). **Scope for a fix:** (a) set
`input.value = ''` after reading the file (or on box click) so re-selection always fires; (b) on a
new front upload, clear `extractedData`, the identification panel and any result-card state; (c)
decide whether a "start over" control belongs on the result card (there is none today — the only
route back is reload). Frontend only (`app.html`) → purge after the Pages build.

**🐞 LIVE DEFECT 2 (logged 2026-09-13, not fixed) — Generate is enabled after a FAILED extraction, so a
timed-out identification can be submitted blind.** `#generateReportBtn` is enabled at three sites:
`app.html:1730` (front stored AND `extractedData` set), `:1969` (extraction success), and **`:2062`
(extraction FAILURE — after the manual-entry form is rendered and `extractedData` is set to the
empty default, :1982–1987)**. The manual form is deliberate (the user can type title/issue and
proceed when identification fails), but it also means: on a busy/timeout/503 extraction the user
can press Generate with a photo the app has never measured, and the first information about the
photo arrives as the grade-time failure card. The extract-time quality message only reaches the
user for the < 250 px case (:1913–1916); the 250–399 band and every non-quality failure carry no
photo information at all. **Scope for a fix:** on the failure branch, (a) distinguish "we could not
identify it" (keep the form, keep the button) from "we could not process the photo" (quality —
keep the button disabled or carry the server's message onto the box), and (b) surface why the
extraction failed next to the form, not only in the transient headline. Frontend (`app.html`) plus,
if the extract response should carry dimensions, the same three backend keys as Path A. Not started.

## 2026-09-11 (evening) — ⚠️ **The client-side image resize is UNREACHABLE on the grade path; the grade request has sent the RAW file since 2026-02-06. The July-16 OOM root-cause record assumed the resize was running. Own entry, on Mike's instruction.**

**MOST RECENT CHANGE (Rule 5): established 2026-09-11 while characterising the "needs a larger
photo" path; recorded separately because it re-frames an instance-size decision.** The Session 118
record (2026-07-16, this file :3965, sentence :3970 — numbering after this entry's insertion) states *"the grading frontend client-resizes to ≤2048px
(`js/grading.js:1313` MAX_IMAGE_DIM) — which is why every grade that COMPLETED today was
harmless"*, and the HEIC finding the same day — *"raw 24MP HEIC has a ~198MB intrinsic decode floor
(libheif double-buffers) — code CANNOT make this input class safe on the 512MB Starter (330 base +
198 ≈ 528). Safe requires either the 2GB tier or an over-size reject policy"* — led to the
Starter → Standard 2GB upgrade (plan_changed 2026-07-16 20:07Z, Mike; CLAUDE.md records it as the
OOM remedy).

**What is actually true (verified 2026-09-11, two independent passes):**
- The live upload handler is the inline `handlePhotoUpload(photoType, files)` in `app.html`
  (:1681, introduced `823820b` 2026-02-06). It stores `FileReader.readAsDataURL` output straight into
  `gradingState.photos` (:1693–1696) — **no canvas pass, no resize** — and `gradeImages`
  (:2376–2385) sends those bytes to `/api/grade`.
- `processImageWithOrientation` (`js/grading.js:1310–1312`, the 2048px cap) is called only from
  `handleGradingPhoto` and `handleAdditionalPhoto`, which have **zero callers** in `app.html` or
  `js/` (the grading.js photo flow left app.html in `e0c5754` 2026-02-06 "Changing to single page
  app", which removed all eight `onchange="handleGradingPhoto(…)"` inputs; `823820b` added the inline
  handler four hours later). `processImageForExtraction` (`js/utils.js:93`, 1200–2400px) is called only from
  `js/app.js:447` inside the bulk flow, whose entry `handlePhotoUpload(files)` is shadowed by the
  inline two-argument declaration (later top-level declaration wins). **Both resize paths are dead
  code.**
- So on 2026-07-16 the grade requests that "completed harmlessly" were harmless because those
  uploads were small at the source or JPEG, not because a client cap protected the server; a raw
  24MP HEIC from the grade flow reaches `/api/grade` at full size. The mitigation that would have
  lowered the memory floor was not running then and is not running now. **The server-side caps
  shipped that day (`GRADING_MAX_LONG_EDGE=2000`, thumbnail-before-transpose, decode concurrency
  gate) are the ONLY protection, and the ~198MB libheif floor sits UNDER them — it is the decode,
  not the output size.** The 2GB decision therefore stands on its own arithmetic (330 + 198 on
  512MB), but the record's "client-resized traffic is the normal case" framing was never true.
- ⚰️ TOMBSTONE (in place, not deleted): Session 118's "the grading frontend client-resizes to
  ≤2048px" is DEAD as a description of the live path from 2026-02-06 onward. The line stays where it
  is with this entry as the correction; do not re-derive load or memory expectations from it.
- Not acted on: restoring a client resize on the grade path is a real unit (it would also cut the
  14.26 MB-of-base64 wire cost the `app.html:3627` comment measured), with its own barcode-parity
  and orientation questions. Logged here, not scoped.

**📐 "NEEDS A LARGER PHOTO" unit — ✅ APPLIED (Mike: all proposals as written, 2026-09-11 evening).
⚰️ ~~In the working tree, NOT staged, NOT committed. SHIPS IN MIKE'S NEXT COMMIT; needs `deploy`
(two backend files) AND, after the Pages build completes, `purge` (one frontend file).~~
**SHIPPED: committed `fb3e0a8` 2026-09-11 14:51 PDT; deployed live 2026-09-13 19:41 UTC; purged and
asserted (`resultDefectsTitle` 4). See SHIP RECORDS, 2026-09-13.**
- **`routes/fingerprint_utils.py` (BACKEND, :193–209):** grade-floor message → *"This photo is too
  small to grade ({w}×{h}px). Grading needs at least {min}px on the shorter side."* with `{min}`
  from `GRADE_QUALITY_MIN_DIMENSION` (f-string, no literal); the failure dict now carries
  `min_dimension`. Tip unchanged. Kept generic on purpose (comment in code). Verified: a 364×554
  JPEG returns the new sentence with `min_dimension: 400`.
- **`routes/grading.py` (BACKEND, :727–734):** the `/api/grade` 400 JSON passes `min_dimension`
  through — one line. (Not in Mike's "backend = fingerprint_utils.py" sentence, but "returned in
  the JSON" needs it; the messages endpoint's own 400 was not touched.)
- **`app.html` (FRONTEND):** `#resultDefectsTitle` id on the header (:1310); quality branch — label
  "Front cover too small", header "Photo check", badge "NEEDS A LARGER FRONT COVER PHOTO", tagline
  "The front cover photo is too small to grade. A phone-camera photo of the front cover will work."
  (drops "We identified the comic", which was asserted even after a failed identification), tip
  colour `var(--text-muted)` → `var(--text-secondary)` (3.58 → 6.65:1, third instance of that token
  carrying read-me text), fallback message text aligned; normal branch — explicit reset to "Defects
  Found" before the grid is written (:2619); generic error branch — "Something went wrong" (:2664).
  No restructuring. All three inline scripts parse (`new Function`); no `var(--text-muted)` remains
  in the quality branch (the error branch's own "Please…" line still uses it — not in this unit).
- **Measurement that bounds future work on this path (RO `request_logs`, 2026-09-11):** 516
  `/api/grade` requests since March; **12 too-small rejections (2.3%), 0 blurry, 0 undecodable**;
  all 12 `device_type = desktop`; shorter sides 302–396 px; **four exactly 394×572 = the eBay listing
  thumbnail** (⚰️ first draft said six); users 3 ×7, 30 ×2, 27 ×2, 7 ×1 — ⚰️ ~~nine of twelve operator,
  three from two real users~~ **ALL TWELVE are the operator's own accounts** (verifier: users 7, 27
  and 30 are Mike's gmail test accounts — `Mike+3`, `MikeTest13`, `Billing Test 2`). **No real user
  has ever hit the too-small path.** Caveat on the zeros: 8 of the 21 grade 400s in the log carry no
  classifiable message (6 `error_message NULL`, 2 non-JSON "Bad Request"), all `device_type = mobile`,
  users 11/17/38/53 — so "0 blurry / 0 undecodable" means "none identified by message text", and
  the unexplained mobile 400s sit outside the desktop, saved-listing-image framing. Not investigated.

**Verification agent (unit applied, read-only):** 27 confirmed / 6 wrong / 0 uncheckable. Wrong = four
stale line refs (fixed above), "six" 394×572 → four, and the user attribution → all twelve operator. Diff
behaviour confirmed: 364×554 → new sentence + `min_dimension: 400`; textured 450×600 → ok; flat 450×600 →
blur rejection (blur check live); all three inline scripts parse; the three header lookups are `const` in
distinct blocks. Note: `min_dimension` rides only on RESOLUTION failures (the blur dict lacks it) — fine
for this unit, but the reason-code unit below should not assume it is always present.

**⏭️ NEXT UNIT (Mike, 2026-09-11) — reason code for the quality branch.** The same client branch
(`app.html:2478`, `quality_fail || quality_issue`) receives the **blur** rejection ("Photo is too
blurry…", `fingerprint_utils.py` Laplacian < 60) and the **undecodable** rejection ("We couldn't read
your {label} photo…", `grading.py:674–679`) and now shows "Front cover too small" / "NEEDS A LARGER
FRONT COVER PHOTO" for all three — advice guaranteed not to work for a blurry upload, the same class
as "please try again" on a deterministic rejection. 0 blur rejections in 516 requests, so nobody has
hit it yet; it is a live wrong-advice path. **Scope:** backend `reason` field (`'resolution' |
'blur' | 'undecodable'`) on every `quality_fail` 400 (`fingerprint_utils.py` return dict + both
`grading.py` returns), and a client switch on `errData.reason` for label / header / badge / tagline,
with the tip already correct per case server-side. Backend → `deploy`; frontend → `purge`. Not
started.

## 2026-09-11 (later) — 🔎 **Newsstand vs direct edition — READ-ONLY CHARACTERISATION (Mike's brief). No code change, no proposed fix. Verdict: SMALL FEATURE on both sides, gated on one measurement (the live extraction prompt already returns an edition, unmeasured and discarded); and the premise "FMV is an average of two markets" is WRONG in a specific, worse way — newsstand-labelled comps are DISCARDED by `is_variant`, so the pool is ⚰️ ~~the direct market~~ **the UNLABELLED market** (direct-labelled comps are discarded by the same pattern — correction below) and a newsstand seller is quoted that pool's price.**

**MOST RECENT CHANGE (Rule 5): the spine-caption unit is COMMITTED by Mike as `58044d5`
(2026-09-11); ⚰️ ~~push / Pages build / purge / assert are Mike's remaining steps and the one-line
ship record here is still owed after the assert~~ — DONE, live and asserted; see SHIP RECORDS,
2026-09-13 (L-SW-2026-030 closed). This entry is a separate, read-only question and changes nothing
in the tree.**

**1. Does anything in the pipeline distinguish newsstand from direct? — NO, on every live
path; and where the word appears it is treated as a VARIANT and thrown out.**
- **Normalizer** (`title_normalizer.py:273–301`, `variant_patterns`): `\bnewsstand\s*(edition)?\b`
  → label `Newsstand` and `\bdirect\s*(edition)?\b` → `Direct Edition` both set **`is_variant =
  True`** (pattern list added with the normalizer itself, `ac9b2be` 2026-02-12). The label is
  written into `title_notes` as text (`Variant: Newsstand`, 708 rows in that exact form) —
  the FACT is recorded, but as a variant. ⚠️ `\bdirect\b` with the optional `edition` also
  fires on "Direct Market" and bare "Direct" (2,673 rows; 1,112 say "direct edition").
- **Valuation** (`routes/sales_valuation.py`): raw pools filter `is_variant` in SQL (:741, :851,
  :1566, :1587); graded pools SELECT it and `continue` past it in Python (:342, :883). The user-facing
  disclosure (:449–462) then says **"Estimate reflects the standard cover; variant sales
  excluded."** — for a newsstand copy that sentence is false twice: it is not a cover variant,
  and the "standard cover" pool is the direct-edition market. Fix F edition-span detection
  (:219–294) is by design a **>15-year span AND ≥20× price-ratio** gate for reprint-era volumes
  (X-Men 1963/1991); same-month editions at 1.5–2× cannot trip it and are not meant to.
- **Dormant model** (`valuation_model.py:65–78`): `edition_multipliers` exist —
  `direct 1.00`, `newsstand_pre_1990 1.10`, `newsstand_1990_1995 1.25`, `newsstand_post_1995
  1.50`, `newsstand_post_2000 2.00` — hand-set, not measured. The only caller is the OLD
  `/api/valuate` path (`ebay_valuation.py:1158`, `:1223`), which passes **`edition='direct'` as a
  constant**; the route (`routes/grading.py:226–256`) never reads an `edition` from the request
  even though the legacy bulk-mode UI sends one (`js/app.js:753`, dropdown :572–576 —
  `#bulkMode` is `display:none` and shown only inside `js/app.js`'s legacy one-argument
  `handlePhotoUpload(files)` (:389–394), which app.html's inline two-argument
  `handlePhotoUpload(photoType, files)` shadows under the current load order — the dropdown is
  unreachable). The grade
  report's FMV (`/api/sales/valuation`) never touches this model. **Net: the multipliers have
  never applied to any live valuation.**
- **Extraction / the user's own copy:** `scan_barcode` (`comic_extraction.py:240`, pyzbar, 4
  rotations) returns `upc_main` / `upc_addon` when it READS one; `extract_from_base64` writes
  `barcode_scanned`, `upc_main`, `barcode_digits` into the extraction result **only on a hit**
  (:826–842). A miss writes nothing — the only trace is the timing note `barcode=hit|miss`
  in the request log (`routes/grading.py:174`). Nothing downstream stores it: `grade_submissions`
  has no barcode/UPC column (schema read 09-11); `collections.comic_data` has 0 of 116 rows
  with a `upc`/`barcode` key; the client never persists it. ⚰️ ~~The vision prompt on this
  path asks for … not edition~~ — **WRONG, verifier 09-11: the live extraction prompt DOES ask
  for `"edition"`** (`comic_extraction.py:385`; instruction :422 *"Check BOTTOM-LEFT CORNER. UPC
  BARCODE = newsstand. ARTWORK/LOGO = direct. Unclear = unknown"*; default `unknown` :564).
  The answer reaches the client (`js/grading.js:1662`, `app.html:1921` keeps `extractedData`)
  and is then **dropped**: the grade request sends only title/issue/publisher/year
  (`app.html:2394–2401`), nothing forwards it to `/api/sales/valuation`, and no table has a
  column for it. A visual edition classifier therefore already runs on every front-cover
  upload, unmeasured, and its output is discarded. **So barcode
  presence/absence is neither a stored fact nor a usable one: a pyzbar miss cannot be read as
  "no UPC printed" — it is also what a blurry, glared, or cropped newsstand barcode returns.
  For 1990s Marvel the signal is the ABSENCE of a UPC (direct) or its PRESENCE (newsstand),
  and the current check can only ever assert presence.**
- **The SECOND place a newsstand detector exists (the first is the extraction prompt above):
  the Whatnot collector's vision prompt**
  (`WV/whatnot-valuator/lib/vision.js:154`: `"variant": "newsstand" or null`) — the model is
  asked, from the cover image, whether the copy is newsstand. It writes `market_sales.variant`
  (315 rows `newsstand`, 78 `direct…`, source = whatnot). ⚠️ That structured field is **NOT
  consulted** by the normalizer or the valuation: only **13** of the 315 are `is_variant`
  (exactly the 13 whose raw_title also says "newsstand"); the other **302 newsstand rows sit
  INSIDE the pools**. So eBay newsstand comps are excluded and Whatnot newsstand comps are
  included — inconsistent by source. Unmeasured: the accuracy of that vision field.

**2. Comp side — what the data can support (RO, 2026-09-11, `ebay_sales` 311,526 rows,
`market_sales` 10,878; `title_year` populated on 187,989 eBay rows, absent on `market_sales`):**

| population | rows | newsstand in raw_title | share | direct in raw_title | share |
|---|--:|--:|--:|--:|--:|
| ebay_sales, all | 311,526 | 12,471 | 4.0% | 2,673 (1,112 "direct edition") | 0.9% |
| ebay_sales, title_year 1980–89 | 37,100 | 5,610 | 15.1% | — | |
| ebay_sales, title_year 1990–99 | 37,609 | 2,538 | 6.7% | 1,265 | 3.4% |
| ebay_sales, 1990–99 AND grade ≥ 9.4 | 4,189 | 387 | 9.2% | — | |
| ebay_sales, title_year ≥ 2000 | 67,427 | 219 | 0.3% | — | |
| market_sales, all | 10,878 | 16 (title) / 315 (`variant` field) | 0.1% / 2.9% | 0 / 78 | |

- **Of the 12,471 eBay newsstand-labelled rows, 12,320 (98.8%) are `is_variant = true`** and
  therefore in no pool; 2,457 of those are graded (2,501 graded across all 12,471). The **151**
  unflagged ones are a pattern-order
  defect, not a data one: the signed / key-claim capture consumes the tail of the title first
  (`Signed: David Michelinie NEWSSTAND`, `Key: 1st Appearance Quasar Newsstand`), so the
  variant regex never sees the word. Log only.
- **`is_variant` overall: 78,034 / 311,526 = 25.0% of ebay_sales** (market 258 / 10,878 =
  2.4%). ⚠️ The "~27%" in the brief is `WHERE_WE_LEFT_OFF.md:4734` — *"~27% of eBay rows
  excluded by variant/lot/reprint filters"* on the 53,840-row corpus of that day: a
  variant+lot+reprint share, not `is_variant` alone, so not comparable with 25.0%. (⚰️ my first
  draft said the figure was not found — verifier found it.) Newsstand-labelled rows are **12,320 / 78,034 = 15.8% of everything
  `is_variant` discards** — the single largest nameable bucket inside it.
- **`upc_main` / `upc_addon` exist on both sales tables and are EMPTY on eBay (0 of 311,526)**;
  nothing in `routes/sales_ebay.py` or the collector writes them. `market_sales` has 1 filled
  (server-side `scan_barcode_from_base64` on the listing image, `routes/sales_market.py:135`).
  Not a usable split key today.
- **The premium is visible in our own corpus** — CGC 9.8, eBay, all-time, newsstand-labelled
  vs the unlabelled non-variant pool (the pool production would price from):

  | key (1990s) | newsstand n / median | pooled-unlabelled n / median | ratio |
  |---|--:|--:|--:|
  | Amazing Spider-Man #361 | 18 / **$477** | 47 / $325 | 1.47× |
  | New Mutants #98 | 11 / **$2,200** | 84 / $1,022 | 2.15× |
  | Spider-Man #1 | 34 / **$180** | 361 / $110 | 1.64× |

  Top 1990s keys by newsstand mentions (all rows): Spider-Man #1 128 of 1,789; ASM #361 94 of
  388; New Mutants #98 86 of 497; Uncanny X-Men #266 84 of 558; X-Men #1 81 of 1,418; Spawn #1
  71 of 830. **So on the books where the money is, the labelled-newsstand comp count at high
  grade is 11–34 — enough for a second pool on those keys, thin everywhere else.**

**3. Direction of the error (sharpens the brief's premise).** Because labelled newsstand comps
are excluded rather than pooled, today's FMV is not an average of two markets; it is the
⚰️ ~~direct/unlabelled market~~ **UNLABELLED market — CORRECTED 2026-09-11 (verifier, brief 1):
`\bdirect\s*(edition)?\b` (`title_normalizer.py:282`) flags direct-labelled listings too, and
2,646 of 2,673 eBay rows saying "direct" are `is_variant` (in the five keys' 365-day graded
pools, 100% of direct-labelled rows are excluded: ASM #361 5, NM #98 11, SM #1 10, UXM #266 13,
X-Men #1 1). So the pool is "sales whose title names no edition or variant": mostly direct
copies by base rate, plus unlabelled newsstand copies.** A **newsstand seller is quoted that
pool's price (too little, by the ratios above)**; a **direct seller is quoted approximately
right**, not too much. The error is one-sided, and it is largest exactly where Mike said: high
grade on 1990s keys. ⚠️ Any copy that says "based on direct-edition sales" is therefore FALSE;
the honest description is about labelling, not edition.

**4. VERDICT (Mike's three options):**
- **Comp side — SMALL FEATURE.** The split key already exists as text (`title_notes`
  `Variant: Newsstand` / `is_variant` reason) and `market_sales.variant`; a "newsstand-labelled"
  pool is a query change plus a label taxonomy that stops treating an edition as a cover
  variant. Ceiling of a text-based approach: 6.7% of 1990s eBay rows / 9.2% of 1990s graded
  ≥ 9.4 / 11–34 comps at 9.8 on the top keys. Enough for a second FMV on the books that
  matter, "insufficient data" honestly elsewhere.
- **User side — ⚰️ ~~RESEARCH PROBLEM~~ → a SMALL FEATURE GATED ON ONE MEASUREMENT** (revised
  after the verifier's finding). The visual classifier the first draft called for **already
  exists and already runs**: the extraction prompt asks the model to read the lower-left
  corner and return `newsstand` / `direct` / `unknown` on every front-cover upload. What is
  missing is (a) its **accuracy**, unmeasured — false rate on glare, bagged, slabbed and
  cropped corners, and the `unknown` rate — and (b) **plumbing**: the answer is discarded
  before the grade request, and nothing stores it. Measuring (a) is a labelled-sample job
  over retained front covers (the extraction call is API spend — estimate from `count_tokens`
  first) or over new uploads by logging the field. Until (a) is measured, treating the field
  as fact would be [[L-SW-2026-018]] (a value nothing verifies). A user-declared edition
  remains the zero-model alternative (the dead bulk-mode dropdown was that) and interacts
  with the CP-1 verdict-withholding design.
- **Not addressable with current data — NO**, except for the long tail: keys with < ~5
  labelled newsstand comps at the requested grade cannot be split and must say so.
- **What changes the answer:** (i) the measured accuracy of the extraction prompt's
  `edition` field (log it on live uploads at no extra spend, or score it on the 185 retained
  front covers — an API-spend item, `count_tokens` estimate first); (ii) whether Mike accepts
  a user-declared edition as an input; (iii) `market_sales.variant` accuracy, which decides
  whether Whatnot rows can join the newsstand pool. **Overall: SMALL FEATURE on both sides,
  gated on (i); not a research problem, and not blocked by data.**

**Verification agent (09-11, read-only, recomputed every DB figure at 17:30 UTC on an unchanged
corpus):** 37 confirmed / 5 wrong / 3 uncheckable. The five are corrected in place above: the
extraction prompt DOES ask for edition (this reversed the user-side verdict); two detectors,
not one; the ~27% exists at :4734 as a variant+lot+reprint share; 2,457 not 2,501 graded among
the flagged; the Fix F span test is strictly > 15. Verifier also noted: `market_sales.variant
ILIKE 'direct%'` includes 2 "Director's Cut" and 2 "Direct Sales" rows (4 of 78 are not
editions); the 9.8 comparison's newsstand side carries no reprint/lot filter (Spider-Man #1
becomes 32 / $177.49 with it — ratios unchanged to two decimals).

**LOGGED, NOT ACTED:** the extraction prompt's `edition` answer is computed and discarded on
every upload (plumbing + measurement candidate); the 151 pattern-order misses; `\bdirect\b` over-firing on "Direct
Market"; the disclosure text calling newsstand copies "variant sales"; the source-inconsistent
treatment of Whatnot newsstand rows (302 inside pools); empty `upc_main` on eBay; the dormant
`edition_multipliers` (hand-set, never applied). **`is_variant` NOT touched, per Mike.**

**📝 BRIEF 1 of 2 (Mike, 2026-09-11 evening) — variant-exclusion note, COPY FIX. ⚰️ ~~REPORT STAGE;
nothing changed yet~~ → APPLIED the same evening, see the block at the end of this entry.**

**Inventory (verified, 0 missed surfaces):**
1. **The sentence is BACKEND-generated:** `routes/sales_valuation.py:462` inside
   `compute_variant_disclosure` (:447–464) — `"Estimate reflects the standard cover; variant
   sales excluded."` — returned as `variant_disclosure` (:1361–1364) and **gated**: fires only
   when the graded pool has ≥ 5 rows, ≥ 3 excluded and **excluded ≥ 30%**.
2. **Frontend pass-through:** `app.html:3138–3146` renders `valData.variant_disclosure` verbatim
   into `#resultVariantNote` (`app.html:1295`, 0.8rem, `color: var(--text-muted)`). No client
   wording of its own.
3. **Second surface, FRONTEND, differently worded, NOT gated:** `js/verdict_basis.js` raw_only
   (:216–218) "No graded sales of the standard cover, {N} graded variant sale(s) excluded.
   Estimated from {R} raw sale(s), marked up 1.5×. A rule of thumb, not a comp." and fabricated
   (:231–233) "No standard-cover sales we can price from, {N} graded variant sale(s) excluded.
   Both figures come from typical prices for this grade, publisher and era." Fire on N > 0.
4. Nowhere else: not FAQ (only :394 "Edition variations and variants", :627 "variant covers or
   obscure issues"), not collection/verify/dashboard, no email, no PDF.

**Three facts that shape the wording:**
- **The 30% gate silences the note on most newsstand-heavy keys** (eBay-only approximation of
  the 365-day graded pool; verifier reproduced to the decimal and checked production's extra
  filters do not flip any): ASM #361 31.4% → fires; New Mutants #98 19.8%, Spider-Man #1 24.9%
  (29.5% under the fuller filter — within 0.5 pt of the gate), Uncanny X-Men #266 16.6%,
  X-Men #1 15.8% → **silent**. A NM #98 newsstand seller sees ~$1,022 at 9.8 with no note.
  Changing the gate is logic, not copy — flagged, not in this unit.
- **One sentence serves two exclusions:** on a modern multi-cover book the excluded rows are
  cover variants; on a 1980s–90s book they are newsstand AND direct-labelled copies. Copy
  cannot tell the eras apart without the year, so the replacement must be true for both and
  must describe LABELLING, not edition.
- **The note element is below the contrast floor:** `#64748b` on `#1a1a2e` = 3.58:1 (floor 4.5;
  guidelines' body-copy token `#94a3b8` = 6.65:1). Style, not copy — Mike decides whether it
  rides along.

**Proposed wording (revised after the verifier killed "based on direct-edition sales"):**
- Server note, **P1:** "Based on sales not labelled as a variant, newsstand or direct edition.
  Newsstand and direct editions of the same issue can differ in value."
- **P2 (shorter):** "Sales labelled variant, newsstand or direct edition are not included.
  Newsstand and direct editions of the same issue can differ in value."
- **P3 (era-hedged second sentence):** "Based on sales not labelled as a variant, newsstand or
  direct edition. Where a newsstand edition exists, it can be worth more or less than the
  direct edition."
- verdict_basis raw_only: "No graded sales without a variant, newsstand or direct-edition label;
  {N} labelled sale(s) set aside. Estimated from {R} raw sale(s), marked up 1.5×. A rule of
  thumb, not a comp." fabricated: "No unlabelled sales we can price from; {N} labelled sale(s)
  set aside. Both figures come from typical prices for this grade, publisher and era."
None claims to know the user's edition. "Standard cover" dropped: it was accurate to the Cover-A
mechanism but reads as a claim about the user's copy.

**File split for the ship (Mike's call which option):**
| change | file | tier | step |
|---|---|---|---|
| note sentence | `routes/sales_valuation.py:462` | **BACKEND** | `deploy` (auto-deploy OFF) |
| verdict-basis clauses | `js/verdict_basis.js` | **FRONTEND** | push → ⏳ Pages build COMPLETES → `purge` |
| (optional) note contrast | `app.html:1295` | **FRONTEND** | same purge |
⚠️ "Frontend copy only" is not available for the sentence itself without a client-side override
of the server string (leaves the API returning the old wording; second copy to drift). Options:
(a) backend string + frontend clauses → `deploy` AND, after the build, `purge`; (b) frontend
override + clauses → `purge` only, stale API string logged. **Purge only after the Pages build
shows complete, never on push** (L-SW-2026-022).

**Verification agent (brief 1, read-only):** 18 confirmed / 3 wrong / 5 unverified / 0 missed
surfaces. The three wrong were one fact — "the pool is the direct market" — and the two
proposals built on it; corrected above and tombstoned in the newsstand entry.

**✅ BRIEF 1 APPLIED (Mike: P1, Option A, contrast fix included; 2026-09-11 evening) — ⚰️ ~~in the
working tree, NOT staged, NOT committed. SHIPS IN MIKE'S NEXT COMMIT; needs BOTH `deploy` (backend
string) AND, after the Pages build completes, `purge` (two frontend files).~~
**SHIPPED: committed `a19ffec` 2026-09-11 13:33 PDT; deployed live 2026-09-11 20:33 UTC (now carried
by `fb3e0a8`); purged and asserted. See SHIP RECORDS, 2026-09-13.**
- **`routes/sales_valuation.py:462–471` (BACKEND):** `variant_disclosure` now
  *"Based on sales not labelled as a variant, newsstand or direct edition. Newsstand and direct
  editions of the same issue can differ in value."* — with a comment stating the pool is the
  UNLABELLED market and that the sentence never claims the user's edition. Gate unchanged
  (≥ 5 / ≥ 3 / ≥ 30%). Verified locally: `compute_variant_disclosure(10, 5)` returns the new
  sentence; `(10, 1)` returns `None`.
- **`js/verdict_basis.js:221–223, :236–238` (FRONTEND; HEAD numbering was 216/231 — the added comment shifted them):** raw_only → *"No graded sales without a
  variant, newsstand or direct-edition label; {N} labelled sale(s) set aside. Estimated from {R}
  raw sale(s), marked up 1.5×. A rule of thumb, not a comp."*; fabricated → *"No unlabelled
  sales we can price from; {N} labelled sale(s) set aside. Both figures come from typical prices
  for this grade, publisher and era."* Comment added above raw_only explaining "labelled".
  `node --check` passes. "standard cover" gone from every user-facing string (the only survivor
  is a dead-badge tombstone comment at `app.html:2871`, plus code comments at
  `sales_valuation.py:449` "base-cover" and `:893` "standard cover" — comments, not copy).
- **`app.html:1295` (FRONTEND):** `#resultVariantNote` colour `var(--text-muted)` →
  `var(--text-secondary)` — 3.58:1 → **6.65:1** on the card (`#94a3b8` on `#1a1a2e`; the
  guidelines' body-copy token). Comment left inline.
- Not touched: `is_variant`, the comp queries, the 30% gate, any detection.

**⏭️ NEXT UNIT (Mike, 2026-09-11) — the 30% gate.** With the wording fixed, the note is still
SILENT on the books where the error is largest: New Mutants #98 (19.8% of the graded pool
excluded), Spider-Man #1 (24.9%; 29.5% under production's fuller filter — within 0.5 pt),
Uncanny X-Men #266 (16.6%), X-Men #1 (15.8%). It fires on ASM #361 (31.4%). Fixing the wording
while the note stays silent on the worst cases is half a fix. Scope for the next unit: the gate
in `compute_variant_disclosure` (`pct_threshold=30.0, min_excluded=3, min_total=5`, `:447–456`)
and/or a second, ungated signal for the newsstand/direct case — e.g. fire whenever the
excluded set contains newsstand- or direct-labelled rows at all (the `title_notes` label text is
already stored per row), independent of the cover-variant share. Logic, not copy; needs its own
measurement of how many lookups would newly show the note (the 594-lookup sample in
`verdict_basis.js` comments is the precedent), and it is BACKEND → `deploy`. Not started.

**Verification agent (brief 1 applied, read-only):** 20 confirmed / 3 wrong / 0 uncheckable — the three
were stale HEAD line numbers in this block (now working-tree numbers); the code diff had no defect.
Template literals evaluated at N=11/R=3 and N=1/R=1 read grammatically.

**SHIP (Mike) — Option A, both tiers — ⚰️ DONE 2026-09-11/13, see SHIP RECORDS; kept for the command shape only (note the `curl -sL` correction there):**
```
git add routes/sales_valuation.py js/verdict_basis.js app.html docs/sessions/WHERE_WE_LEFT_OFF.md
git commit   # variant note: describe labelling not edition; newsstand/direct can differ; drop "standard cover"; note contrast 3.58→6.65
git push
deploy       # Render — the sentence lives in routes/sales_valuation.py; auto-deploy is OFF
# ⏳ wait for the Pages build to COMPLETE (L-SW-2026-022) — then:
purge
# asserts:
#   curl -s https://slabworthy.com/js/verdict_basis.js | grep -c "direct-edition label"     → 1
#   curl -s https://slabworthy.com/js/verdict_basis.js | grep -c "standard cover"            → 0
#   curl -s https://slabworthy.com/app.html | grep -c "resultVariantNote.*text-secondary"    → 1
#   backend: Render Events shows the commit hash; then a grade on ASM #361 (fires) shows the new sentence
```
⚰️ ~~Post-ship: one-line ship record here (L-SW-2026-030).~~ Written — SHIP RECORDS, 2026-09-13.

**📐 "NEEDS A LARGER PHOTO" — copy + one header. ⚰️ ~~REPORT STAGE; NOTHING CHANGED~~ → APPLIED the
same evening, all proposals as written; see the block under the resize entry above.**

**Mechanism (verified, not inherited):** the quality gate on `/api/grade` runs on the **first image
that has base64 and stops** (`routes/grading.py:718–734`, `break  # Only check first image`), and that
image is **always the front cover**: `gradeImages` is built by `Object.entries(gradingState.photos)`
(`app.html:2376–2385`), keys `1..4` from `photoMap` (:1689), integer-like keys iterate ascending
(node-checked), and only the front box is `data-required` (:1095). **Threshold = shorter side ≥ 400 px**
(`routes/fingerprint_utils.py:157` `GRADE_QUALITY_MIN_DIMENSION = 400`, test `min(width, height) <
min_dim` :193, measured after `auto_orient_pil` and after server normalization which only shrinks);
identification uses 250 (:158). That gap is the trigger: 364×554 passes 250, fails 400 — the book
identifies, then the grade refuses. ⚠️ The same client branch (`app.html:2478`, `quality_fail ||
quality_issue`) also receives the **blur** rejection ("Photo is too blurry…", :214–215, Laplacian < 60)
and the **undecodable** rejection ("We couldn't read your {label} photo…", `grading.py:674–677`), and
hard-codes "Photo too small" / "NEEDS A LARGER PHOTO" for all three. The server sends no `reason`.

**Surfaces:**
| what | text | where | tier |
|---|---|---|---|
| message | "This photo's too small for an accurate grade ({w}×{h}px) — upload a larger one for grading." | `fingerprint_utils.py:198` | **BACKEND** |
| tip — KEEP | "Use your phone camera at full resolution. Avoid screenshots or cropped thumbnails." | `:199` | backend |
| grade label / badge / tagline | "Photo too small" / "NEEDS A LARGER PHOTO" / "We identified the comic, but need a larger photo to grade it accurately." | `app.html:2491 / :2500 / :2501` | **FRONTEND** |
| message + tip landing | `#resultDefectsGrid` (:2492–2495); tip in `var(--text-muted)` = 3.58:1 | `app.html` | frontend |
| **the header** | "Defects Found" — static `<div class="defects-title">` at `app.html:1310`, no id, never written by JS | `app.html` | frontend |
The header is a fixed string over a grid that receives THREE content kinds, all inside
`window.generateGradeReport` (:2264): real defects (grid write :2606), this quality failure (:2492),
and the generic catch-all "Error: …" (:2650). (`renderGradeReport` in `js/grading.js:2111` has zero
callers; the :1313 comment "Populated by renderGradeReport" is stale. `runQuickTest` in grading.js
also writes the grid but only under `?dev`.) The same class labels "Grade Breakdown" (:1300), so the
fix must vary by branch, not rename globally, and the normal branch must RESET it — the element
persists across grades in a session.

**Proposals (Mike decides):**
- **Message (backend, `fingerprint_utils.py:198`) — M2 recommended:** "This photo is too small to
  grade ({w}×{h}px). Grading needs at least {min}px on the shorter side." with `{min}` from
  `GRADE_QUALITY_MIN_DIMENSION` (never a literal) and `min_dimension` added to the 400 JSON. The
  client names the photo. (M1 — "This front cover photo…" inside the function — is rejected by the
  verifier: `/api/messages` calls the same function on its first image block and cannot know it is a
  front cover; the endpoint is live even though its only client is dead.) Tip unchanged.
- **Client (app.html):** label "Front cover too small"; badge "NEEDS A LARGER FRONT COVER PHOTO";
  tagline "The front cover photo is too small to grade. A phone-camera photo of the front cover
  will work." (⚠️ the existing tagline's "We identified the comic" is false when identification
  failed and details were typed — the branch reads `extractedData || {}` either way; the proposed
  tagline drops that claim.) Tip colour `var(--text-muted)` → `var(--text-secondary)` (3.58 →
  6.65:1) — style, Mike's call.
- **Header (the one in scope):** id `resultDefectsTitle` on :1310 and three `textContent`
  assignments — quality branch **"Photo check"** (alts: "Upload problem"), generic error branch
  **"Something went wrong"** (alt: "Request failed"), normal branch "Defects Found" (explicit reset).
  No restructuring.
- **Report-only, not in scope:** the blur/undecodable conflation — honest fix is a server `reason`
  field (two lines, backend) and a client switch; until then the badge lies to a blurry upload.

**Worth reporting, not acted:**
- **Resize premise: WRONG on the live path, conclusion right for another reason.** The grade
  payload is the RAW file — `handlePhotoUpload(photoType, files)` (`app.html:1681`) stores
  `readAsDataURL` output straight into `gradingState.photos` (:1693–1696), no canvas. The 2048px
  path (`processImageWithOrientation`, `js/grading.js:1310–1312`, called from `handleGradingPhoto` and
  `handleAdditionalPhoto`) and the 1200–2400px path (`processImageForExtraction`, `js/utils.js:93`,
  called from `js/app.js:447` inside the shadowed bulk flow) are both unreachable. A full-resolution
  capture reaches the server at full size and clears 400 by an order of magnitude; the server then
  caps the long edge at 2000 and measures. So this path fires only on images already small at the
  source.
- **Frequency — MEASURED from `request_logs` (RO, 2026-09-11; ⚰️ my first draft said "no database
  trace" — wrong, `wsgi.py:396–449` `after_request` logs every request with status + error_message;
  correct only that `api_usage` and `grade_submissions` get no row):** `/api/grade` 516 requests
  since 2026-03, **12 too-small rejections (2.3%)**, 0 blurry, 0 undecodable, 475 OK. **All 12 are
  `device_type = desktop`**; shorter sides 302–396 px, six of them exactly 394×572 (the eBay listing
  thumbnail size — the Session 99 origin case). Users: **3 (Mike admin) ×7, 30 (Mike Free test) ×2,
  27 ×2 (June), 7 ×1 (March)** — 9 of 12 operator, 3 from two real users, none since June from a
  real user. `/api/extract` too-small: 4 of 928. Render logs (retained since 09-04): 18 grade timing
  lines, 1 `quality_fail` = the 20:54 UTC trigger; also `outcome=moderation_blocked` on the same
  title at 20:57. Reading: this is a desktop, saved-listing-image path, mostly the operator's own
  testing, not a phone-camera path.
- Session 99 (2026-06-08) is where this copy and the purpose-split floor came from; nothing there
  or in LESSONS forbids naming the photo or stating the threshold.

**Ship split (when Mike picks):** `routes/fingerprint_utils.py` (message) → **BACKEND** → `deploy`
(auto-deploy OFF). `app.html` (label, badge, tagline, header id + 3 assignments, tip colour) →
**FRONTEND** → push → ⏳ Pages build shows COMPLETE → `purge` → assert. Never purge on the push
(L-SW-2026-022). If Mike keeps the backend message untouched, the unit is frontend-only and the
target size must then come from `width`/`height` plus a client-side 400 — a duplicated threshold.

**Verification agent (read-only):** 27 confirmed / 6 wrong / 1 uncheckable. The six: five stale or
misattributed line refs and function names (fixed above: constants :157–159, test :193, message
:198–199, blur :214–215; `data-required` :1095; normal path is `generateGradeReport` not
`renderGradeReport`; extract-fail render is :1992–1993; `handleAdditionalPhoto` not
`rotateGradingPhoto`) and the "no database trace" sentence, replaced by the `request_logs` measurement.
Verifier additions folded in: the undecodable third case; dims are post-normalization; `?dev` reaches
`runQuickTest`.

## 2026-09-11 — ✅ **Spine-photo instruction unit: APPLIED AS REVISED (hold lifted by Mike, shape 1 always-on, trimmed spine line, primary-text colour), frontend only, ⚰️ ~~SHIPS IN MIKE'S NEXT COMMIT~~ SHIPPED as `58044d5` (2026-09-11 10:16 PDT), purged, asserted — SHIP RECORDS 2026-09-13. Plus PART 2: spine-photo validity characterised read-only — 0 real-user duplicate spines in 128; nothing on the grading path validates a spine. Nothing staged, nothing committed.**

**MOST RECENT CHANGE (Rule 5): Mike chose Option 2 — one caption under the four upload
boxes in `app.html`, NOT a restored Photo Tips button — plus scoping the FAQ's blanket
straight-on rule, plus deleting the dead Photo Tips modal (2026-09-11). Supersedes the 09-03
"Spine-angle capture ambiguity … needs a ROADMAP entry" line (no roadmap entry was written;
the unit is built and the residue is queued HERE) and the 08-31 "Spine-angle confound
(recorded, NOT acted on)" line. The 08-31 "no input changes while calibration is mid-flight"
constraint is not breached: the pinned 36-book eval set's photos are already stored; this
changes future submissions only.**

**⏸️ HOLD (Mike, 2026-09-11, after seeing the working tree) — supersedes the "ships in
Mike's next commit" line above until decided.** Concern: the capture screen is clean and easy
to act on; two permanent sentences under the boxes may cost more in friction than they buy in
guidance, and the spine photo is optional — most users never shoot one, yet every user would
read the spine sentence on every submission. **Screenshots delivered** (desktop 1280 and
mobile 375 CSS px, before = HEAD / after = working tree; files `caption_desktop.png`,
`before_desktop.png`, `caption_mobile_after.png`, `caption_mobile_before.png` in the 09-11
scratchpad, sent to Mike in-conversation). Rendered caption: desktop ≈ 2 lines + 2 lines under
the boxes, 13px; mobile 273 × 123 px, 3 + 3 lines. No mobile overflow in the pane's device
emulation (scroll width 375, card 335). ⚠️ Headless desktop Chrome at `--window-size=375`
clips the page on the right — identically on HEAD — because desktop Chrome clamps its minimum
window width and ignores the viewport meta; it is a render artifact, not a layout defect. The
mobile PNGs were produced through a 375px iframe wrapper to avoid it.

**Three shapes on the table, none implemented, Mike decides:**
1. **As applied** — always-on, both sentences under the boxes. Certain to be seen; costs
   screen calm on every submission, for the majority who skip the spine.
2. **Interaction-triggered** — per-photo guidance shown on interacting with the spine box;
   reaches only the person shooting a spine. Keeps the screen clean.
3. **Split** — the consistency line stays permanent (it applies to all four photos); the
   spine-angle line appears on interaction.
Weigh, don't dismiss: guidance behind an interaction is guidance most people never see — the
Photo Tips modal existed, was reachable for two weeks (`4efa047` 01-27 → `0b32bfe` 02-11), and
was apparently never used. Counter: a hint fired by the capture action itself is not a help
button requiring a separate decision to seek help. That is judgment, not evidence.

**Colour — MEASURED, not chosen by eye (pane, 2026-09-11):** the caption's composited
background is `#1a1a2e` (`.card`; body `#0f0f1a` never shows through). The verifier's 09-11 note
that the caption is "lighter than the guidelines' `#94a3b8` body-copy floor" means it EXCEEDS
the floor, not that it violates it — the guidelines say body copy is `#94a3b8` *or lighter*.
Ratios against `#1a1a2e`: current `rgba(255,255,255,.8)` renders `#d1d1d5` → **11.23:1**;
`<strong>` `rgba(255,255,255,.95)` → 15.46:1; `--text-secondary #94a3b8` → **6.65:1**;
`--text-muted #64748b` → 3.58:1 (fails 4.5); `.progress-text`'s `rgba(255,255,255,.7)` →
8.86:1. **Proposed:** `var(--text-secondary)` (`#94a3b8`, 6.65:1) — it is the guidelines' named
body-copy colour and a token rather than a literal, and instruction text should sit on the
body-copy token, not on the warning-text literal. The current value also clears 4.5:1 by a wide
margin; keeping it is defensible. `--brand-gold` excluded per Mike. Not applied — Mike decides.

**Spine-submission frequency among the 139 — what the record holds:** no aggregate. Two
data points only: user 42 (2026-08-06 entry) — 8 of 9 grade submissions `photos_used = 1`,
"single-photo grading is simply how he uses the product"; matbanshee (2026-06-08, L-SW-2026-003
retention lesson) — ~4 images inferred from token count. No count of `photo_labels` containing
`spine` exists anywhere in the record. Not measured here (Mike: do not build an instrument);
a read-only `SELECT count(*) FROM grade_submissions WHERE photo_labels ? 'spine'` would answer
it in one query if he wants it.

**▶️ HOLD LIFTED (Mike, 2026-09-11, later): ship the caption unit AS REVISED — shape 1
(always-on), two changes applied to `app.html` only; everything else in the unit stands.**
1. **Spine line trimmed** (the narrow vertical box already teaches the framing):
   `Spine: hold the comic at about 45° so the spine and cover edge are both visible.`
   Consistency line unchanged.
2. **Colour → `var(--text-primary)` (`#ffffff`), the `strong` override removed.** Measured in
   the pane on the rendered `.card` background `#1a1a2e`: **17.06:1**. For scale, the
   "Click to upload" hints (`rgba(255,255,255,.5)`) render `#8a8a93` against their own
   composited box background (≈`#151527`: `.photo-upload-box` `rgba(0,0,0,.3)` over the
   diagram over the card) at **≈5.25:1** (verifier; my pane read of 5.28 took the box's
   un-composited black), so the caption now
   sits well above hint weight, which was Mike's stated concern (instruction text that
   only works if it is read). `--brand-gold` excluded per Mike. ⚠️ On the premise: the 09-11
   verifier's "lighter than the body-copy floor" meant *exceeds* the floor (the old value
   measured 11.23:1, above `#94a3b8`'s 6.65:1); the change is made on the readability
   argument, not on a contrast failure. Recorded so the next reader does not "fix" a
   violation that never existed.
Re-rendered (headless Chrome, desktop 1280 and mobile 375 via the iframe wrapper):
`caption_desktop_rev.png`, `caption_mobile_rev.png` in the 09-11 scratchpad, sent to Mike.
Working tree after revision: `app.html`, `faq.html`, `js/grading.js`,
`docs/sessions/WHERE_WE_LEFT_OFF.md`. Nothing staged. **The SHIP block below is live again.**

**⚰️ CORRECTION to the "LOG, DO NOT ACT" corpus line below (same day):** "retained spine
photos ≤ 139" is DEAD — 139 was the submission count **through 2026-08-31**; the table has
grown. Live counts (RO, 2026-09-11 ~17:00 UTC, `grade_submissions`):

| | all | excluding operator accounts (users 3 = Mike admin, 30 = Mike Free test) |
|---|--:|--:|
| submissions | **185** (139 before 09-01, 46 since) | **140** |
| with a `spine` R2 key | **173** | **128** |
| distinct users | 28 | 26 |
| `photos_used` = 4 / 3 / 2 / 1 | 143 / 30 / 4 / 8 | — |

So the spine photo is submitted far more often than "most users skip it" assumed: **128 of
140 real-user submissions (91%) carry one.** Top real spine submitters: user 68 (25), 38
(24), 61 (13), 52 (8), 72 (7).

**📐 PART 2 — spine-photo validity, READ-ONLY CHARACTERISATION (Mike's brief, 2026-09-11).
Nothing built, nothing changed.**

**(a) Can the app tell a spine photo is a spine? NO — nothing on the grading path checks
it.** `/api/grade` (`routes/grading.py:503`) runs, per request: the photo-quality gate
(`check_photo_quality_base64`, resolution + blur, **first image only** — `break` at :734);
Rekognition moderation **per photo** (:738+, no break); orientation normalization per photo
type; the vision call; retention. No per-image content check. The extraction path's
`is_comic_cover` (a field the model returns from `extract_from_base64`,
`comic_extraction.py:806–816`, "This doesn't appear to be a comic book cover") exists ONLY on
`/api/extract` (front-cover identification, `routes/grading.py:376`); `/api/grade` never calls
`extract_from_base64`, and nothing analogous exists for the spine. The only spine-specific
check in the codebase ("Is the spine clearly visible and in focus?", `js/grading.js` per-step
prompt) is in the dead `analyzeGradingPhoto` path — never sent. A per-image SHA-256
(`content_moderation.get_image_hash`) IS computed on the grading path, but only to log
moderation incidents; nothing compares the four hashes to each other.

**(b) Cheap duplicate check — what exists and what it would cost.** Slab Guard's perceptual
fingerprinting is `routes/registry.py`: `generate_fingerprint(photo_url)` → imagehash
phash/dhash/ahash/whash (:385–424), `generate_edge_strip_hashes` (:317), and
`assess_photo_quality` (SIFT keypoints, :142). All **server-side** (Python, `imagehash`,
Pillow, `opencv-python-headless` — all in `requirements.txt`); nothing runs client-side
(the client does EXIF orientation only). It is in-process with `/api/grade` — same Flask app —
but takes a **URL**, not base64, so calling it on the grading path needs a small adapter
(decode the already-normalized base64 → PIL → hash), not new machinery. Measured locally on
a retained 1536×2048 pair: SHA-256 of both ≈ **0.1 ms**; JPEG decode **14.5–15.4 ms/image**
(⚰️ my first figure "≈ 10 ms" was understated; verifier re-timed); dhash ≈ 9 ms/image; whole
pipeline over three runs **41–48 ms** — so a spine-vs-front byte-and-perceptual compare is
**< 50 ms CPU per submission on this desktop, with little margin; NOT measured on the Render
Standard instance**, zero API spend, zero network. `/api/grade` already spends 4 Rekognition round
trips and one vision call per request, so the compare would be invisible in the timing.

**(c) What is in the corpus — MEASURED, no API call.** All 173 spine/front pairs fetched
from `img.slabworthy.com` (the retained keys are publicly served; Cloudflare rejects the
default Python UA, accepts a named one) and compared locally: SHA-256, dHash and pHash
Hamming distance, 64×64 normalized correlation, and a multi-scale template match of the
spine image against the front (crop-of-cover probe). Script `spine_dup.py`, results
`spine_dup.json`, images under `subimg/` in the 09-11 scratchpad (delete after use — they are
users' photos).
- **Byte-identical spine == front: 11 of 173.** Every near-identical hit (dHash ≤ 10,
  pHash ≤ 10, NCC ≥ 0.9) is one of the same 11 — there is no "near but not identical" case.
  **All 11 are operator submissions**: user 3 (Mike admin) ×9, user 30 (Mike Free test) ×2,
  ids 2, 3, 9, 12, 14, 15, 17, 18, 53, 55, 137, dated 06-27 → 08-30 — test runs that reused
  one file for every slot (the 442×590 ASM #41 image four times).
  **Among real users: 0 of 128.** The highest-confidence failure case does not occur in the
  corpus.
- **Crop-of-cover probe:** 3 hits ≥ 0.80 (none ≥ 0.90), all user 38, ids 31/35/39 — inspected
  visually: genuine oblique spine shots where the cover artwork is visible at an angle;
  the template match fires on the artwork. **False positives; 0 confirmed cropped covers.**
  The probe as written cannot distinguish "oblique shot showing the cover" from "crop of
  the cover" — that is exactly the research question in (d).
- **Aspect ratio (w/h) of spine images:** < 0.35 strip-like **36**; 0.35–0.6 **36**;
  ≥ 0.6 cover-like **101**. Visual sample (ids 4, 5, 10, 51 strips; 6, 7, 8 cover-like; all
  operator submissions, so the sample says how the operator shoots, not how users do): the
  strips are genuine spine photos cropped tight by the user (0.038 = a bare spine sliver;
  0.13 = spine plus a sliver of cover); the 0.75 ones are the raw 3:4 phone frame holding
  an oblique ~45° shot with the whole cover foreshortened. **Aspect measures cropping
  habit, not validity.** A cropped cover and a cropped spine can share an aspect.
- **Caveat on the population:** the 139 in the earlier record and the "spine optional /
  most skip it" framing are both superseded by the table above; and user 3's 41
  submissions are 22% of the table, so any corpus-wide statement should be made on the
  140-row real-user subset.

**(d) Beyond duplicates — research question, NOT scoped.** Distinguishing a genuine oblique
spine shot from a cropped cover or a useless angle would need one of: (i) geometry — the
spine edge as a near-vertical line with the cover plane receding from it (perspective
foreshortening; a flat crop has none); (ii) a front-vs-spine homography test — a cropped
cover is a *planar* sub-region of the front photo (Slab Guard's `findHomography` machinery,
`routes/slab_guard_cv.py:487`, would find a clean planar map; an oblique spine shot would
not); (iii) a vision-model classification ("is this an edge-on view of a comic?"), which is
an API-spend item (~173 images at a fraction of a cent each; estimate from `count_tokens`
before any run per the spend rule). None is built; (ii) is the cheapest credible signal and
reuses existing code, but its false-positive rate on genuine shots that show most of the
cover (the 0.75-aspect population) is unknown and is the first thing to measure.
**Explicitly out of scope (Mike): the model-facing prompt is unchanged** — telling the
model to expect a 45° view while users submit arbitrary spine images could make it score
spine stress it cannot see; that needs its own argument and measurement. No diagram, info
link or best-practices page (queued separately).

**Why Option 2 (Mike):** restoring the button puts the instruction behind a click that the
collector who reported this never made, and that nobody has made since 2026-02-11.

**WHAT CHANGED — 3 files, ALL FRONTEND → `push` → ⏳ WAIT for the Pages build → `purge`
→ assert. NO `deploy` (no backend file touched).**
- **`app.html`** (+CSS, +markup, −modal):
  - `.photo-capture-note` rules added directly after `.progress-text` in the inline style
    block (13px, `color: var(--text-primary)` — ⚰️ first draft `rgba(255,255,255,0.8)` =
    `.warning-text`'s literal, replaced same day on Mike's readability call, 17.06:1 measured),
    `max-width: 520px`, centred.
  - Caption `<div class="photo-capture-note" id="photoCaptureNote">` inserted between
    `.photo-upload-diagram` and `.upload-progress-indicator`. Two paragraphs, Mike's text
    verbatim: **"Spine:** hold the comic at about 45° so the spine and cover edge are both
    visible." (⚰️ first draft "…the front cover edge are both visible, spine filling the frame
    top to bottom" — trimmed by Mike, same day) / "Shoot every comic the same way each time.
    Consistency matters more than hitting the angle exactly." The second
    paragraph is deliberately unlabelled — it applies to all four photos, not the spine.
  - Photo Tips modal deleted (former lines 1463–1513, 51 lines incl. its own straight-on
    rule and "Turn comic sideways"; the hunk also drops the trailing blank line). It had had no opener since `0b32bfe` (2026-02-11).
- **`js/grading.js`**: `togglePhotoTips()` / `closePhotoTips()` deleted (former 1161–1171;
  zero callers anywhere).
- **`faq.html`**:
  - `Click "Photo tips" during upload for detailed guidance on lighting, angle, and focus.`
    DELETED (former :320). ⚠️ The button and modal date from `4efa047` (2026-01-27, "Add
    Grade My Comic UI"); the FAQ sentence pointing at them was added in `492390d`
    (2026-02-09, faq.html only); the button was removed two days after that in `0b32bfe`
    (2026-02-11). The pointer was true for two days and then live on a public page for **seven months** pointing at a
    mechanism that did not exist — **L-SW-2026-020's exact shape (copy asserting a state the
    mechanism does not have). Name it in the commit message; do not delete it quietly.**
  - :345 `Taken straight-on (camera parallel to comic)` → **`Front, back and centerfold:
    shoot straight on, camera parallel to the comic. Spine: about 45°.`**
  - :349 `Blurry, dark, or angled photos` → **`Blurry, dark, or inconsistently angled photos`**.

**Verified in the static preview (2026-09-11, `python -m http.server` on the working tree,
placeholder `cc_token` in localStorage to pass the client-side auth gate; API calls fail
harmlessly):** `#photoCaptureNote` present, previous sibling `.photo-upload-diagram`, next
sibling `.upload-progress-indicator`, computed 13px / ⚰️ ~~`rgba(255, 255, 255, 0.8)`~~
(first draft; after the revision it computes to `rgb(255, 255, 255)` via `var(--text-primary)`,
re-measured 17.06:1 — see HOLD LIFTED above), not inside any hidden container; `#photoTipsModal` absent; `typeof togglePhotoTips` and
`closePhotoTips` both `undefined`. Screenshot taken: caption reads directly under the four
boxes, above "0 of 4 photos uploaded".

**NOT TOUCHED — residue, log only:** `styles.css` `.tips-toggle` (:1621–1633) and
`.tips-modal-*` / `.tips-section*` (:2255–~2340) are now unreferenced CSS; `js/sidebar.js:586`
still lists `.tips-modal-overlay` in the selector of overlays it re-parents to `<body>`.
Harmless; cleanup candidates, not this unit. **Model-facing prompts unchanged** —
`grading_engine.py` and the per-step prompts say nothing about angle; telling the model what
angle to expect is a separate BACKEND unit (needs `deploy`), if wanted at all.

**Spine box "Click to upload" hint — reported, not fixed:** absent since the box was
introduced in `e0c5754` (the first commit carrying `.upload-box-hint`) — never present, never
removed, no comment records why. The hint is always-visible 11px text (brightened on hover);
the spine box is 40px wide × 170px tall (30px on mobile) and carries its label as a vertical
letter stack, so a horizontal 11px "Click to upload" would not fit. Geometry is the likely
reason; "deliberate" cannot be established from the record.

**LOG, DO NOT ACT (Mike, 2026-09-11):**
- **Corpus constraint:** the spine photo is OPTIONAL (only the front box is
  `data-required="true"`; FAQ says fewer photos are allowed). ⚰️ ~~Retained spine photos are
  therefore ≤ 139 … the true count is unmeasured~~ — **DEAD same day, MEASURED: 173 spine
  photos in 185 submissions (128 of 140 real-user); see the CORRECTION table above.**
- **The confound, stated precisely:** there was **never** a spine-angle instruction on any
  reachable surface. The only live angle guidance since 2026-02-11 was the FAQ's blanket
  "Taken straight-on (camera parallel to comic)" (added `492390d`, 02-09); the Photo Tips
  modal's own straight-on rule was unreachable from 02-11. So the existing spine photos are
  most likely **two populations, not one**: straight-on (users who read the FAQ) and
  improvised-angle (users who read nothing; ~45° in Meisler's case). Which is which is
  unrecorded, and no metadata can recover it — the retained bytes are the server-normalized
  JPEG (EXIF transposed and dropped), and EXIF carries no tilt field anyway. This is a
  stronger claim than "users guessed" and replaces that wording.
- **PARKED — pixel-content classification** of the retained spine photos (an oblique shot
  shows the spine plus a foreshortened cover; a straight-on shot shows the strip alone) to
  label the two populations retroactively. Real, but an **API-spend item** over ≤ 139 photos
  and it **only becomes worth doing if CGC ground truth arrives** (calibration is blocked on
  it — 08-31 entry). Not scoped, not estimated. If it is ever raised: measured
  `count_tokens` estimate and the running daily total BEFORE anything runs (spend rule).

**SHIP (Mike) — ▶️ live again after the revision above — ⚰️ DONE as `58044d5`, see SHIP RECORDS 2026-09-13; command shape kept (use `curl -sL`):**
```
git add app.html faq.html js/grading.js docs/sessions/WHERE_WE_LEFT_OFF.md
git commit   # name the FAQ pointer: L-SW-2026-020-shape copy, live 7 months (2026-02-11 → 09-11)
git push     # → Pages build
# ⏳ wait for the Pages build to finish (L-SW-2026-022) — then:
purge
# assert the new content is served:
#   curl -s https://slabworthy.com/faq.html | grep -c "inconsistently angled"   → 1
#   curl -s https://slabworthy.com/app.html | grep -c "photoCaptureNote"         → 1
#   curl -s https://slabworthy.com/app.html | grep -c "photoTipsModal"           → 0
```
No `deploy`. ⚰️ ~~After the assert passes: one-line ship record here (the L-SW-2026-030 step).~~ Written — SHIP RECORDS, 2026-09-13.

**Verification agents (09-11, read-only):** first pass 28 confirmed / 2 wrong / 1 uncheckable
on the diff + this entry; second pass (revision + Part 2) 20 confirmed / 4 wrong / 0 uncheckable —
the four (quality-gate `break` line :734 not :735; hint grey `#8a8a93` not `#808080`; decode
14.5–15.4 ms not ≈10; stale `rgba(…,0.8)` in the preview paragraph) corrected in place. Both wrong figures corrected in place above (modal 51 lines not 50; the button
predates the FAQ pointer — `4efa047`, not `492390d`). Diff confirmed to contain only the seven
intended hunks; `<div>` balance net zero; `node --check js/grading.js` passes; caption colour
is lighter than the guidelines' `#94a3b8` body-copy floor; no mobile media rule hides or
overlaps the caption at 767px and below. Uncheckable = the preview screenshot (session
activity).

**QUEUED (log only):** delete `subimg/` (users' photos) from the 09-11 scratchpad once Part 2 is verified; a spine-vs-front duplicate compare on `/api/grade` (< 50 ms CPU, no API — see Part 2(b)) if Mike wants the highest-confidence case caught, though it occurs 0 times in real-user data; the homography crop-of-cover probe (Part 2(d)(ii)) as a measurement first; unreferenced tips CSS + sidebar selector cleanup; model-facing angle
expectation (backend unit); spine-box hint (geometry, see above); the pixel classification
above (parked, gated on ground truth). Unchanged from 09-10: plurals/single insertions;
Whatnot `Comics #N`; `House of M` / `Ark-M`; case-split family; dependency-status roster;
⚰️ ~~rapidfuzz Render-shell check still owed~~ (closed 2026-09-13 — run by Mike 09-11).

## 2026-09-10 — ✅ **Token-guard unit (A + B4 + rapidfuzz monitor): COMMITTED + DEPLOYED 2026-09-04 (`2e27098`), BACKFILL RUN + VERIFIED 2026-09-10. The 09-04 heading below ("NOT committed, NOT deployed, backfill NOT run") is DEAD on all three claims.**

**MOST RECENT CHANGE (Rule 5): the canonical-title backfill for the token-guard unit ran in
production on 2026-09-10 (Mike, Render shell, between 20:37 and 21:26 UTC) and is verified from
the RO connection — stored `canonical_title` equals the deployed normalizer's output on EVERY row
of both tables. Supersedes the 09-04 entry's ship-state heading, which was already two-thirds
false at the moment it was committed (see the tombstone and L-SW-2026-030).**

**⚰️ TOMBSTONE — the three ship-state claims in the 09-04 entry, each DEAD, corrected in place:**
- **"NOT committed"** — DEAD. Committed by Mike 2026-09-05 01:25 UTC (09-04 19:25 MDT) as
  `2e27098` (`title_normalizer.py`, `dependency_monitor.py`, `CLAUDE.md`, this file); pushed;
  `main` == `origin/main` on 09-10.
- **"NOT deployed"** — DEAD. Render deploy of `2e27098` triggered via the API four seconds after
  the commit (2026-09-05 01:26:00 UTC), finished 01:26:41, status **live** — read from the Render
  deploys endpoint on 09-10 (GET only). `/health` reports `5.6.0`, a constant unchanged since
  March; it does not identify builds.
- **"backfill NOT run"** — DEAD as of 2026-09-10. Evidence below.
**REPLACED BY:** this entry. **REASON:** the 09-04 entry was written at 21:10 UTC, before the
unit shipped, and was then carried INSIDE `2e27098` — the commit whose contents it described as
unshipped. Nothing updated it afterward; the record was wrong for six days and the 09-10 opening
read reported the unit as undeployed until git and Render were checked. **SUPERSEDES** every
"awaiting Mike's stage/commit/push/deploy" and "deploy BEFORE the dry run" instruction in the
09-04 entry; do not re-present its command blocks. Lesson recorded as **L-SW-2026-030**.

**VERIFICATION — what was ACTUALLY run (Claude, 2026-09-10, RO role `do_readonly`, hard
read-only session).** ⚠️ **`verify_backfill.py` and `preflight.pkl` were NOT used.** Both lived
in the 09-04 session scratchpad and were not available from this session (scratchpads are
session-scoped). Verification was by direct database check instead: every `raw_title` in both
tables re-normalized with the checked-out `title_normalizer.py` (HEAD = `2e27098` = the deployed
commit) and compared with stored `canonical_title` using the backfill script's own comparison
(`after != stored`, raw compare). Scripts: `status_ro.py`, `pools_ro.py`, `ba_ro.py` in the
09-10 scratchpad, 33 / 15 / 13 lines, regenerable from this description.
1. **Flatness — PASS.** `ebay_sales` 303,123 rows with `raw_title`, stored ≠ HEAD **0**, 0 pairs.
   `market_sales` 10,614 rows, **0**, 0 pairs. The same check at 20:37 UTC the same day gave
   **2,981 + 359 = 3,340** rows, **1,298 + 11** distinct pairs, top transitions `EC Comics → Comics`
   321, `’orc → D’orc` 304, `Absolute Batman → Absolute Catwoman` 149, `Batman Adventures →
   Amazing Adventures` 149, `NULL → K.o` 49 — exactly the 09-04 pre-flight differential. So the
   baseline was still flat-to-old-HEAD and unwritten at 20:37, and the write landed between 20:37
   and 21:26 UTC.
2. **The 15 named pools — PASS, once 09-10 captures are subtracted.** ⚠️ **CAPTURE RESUMED
   09-10** (see below), so the RAW counts are NOT the post-write state; the post-write state is
   `count WHERE created_at < '2026-09-10'`. Both tables unioned:

   | known title | expected AFTER (09-04) | now | of which created 09-10 | post-write |
   |---|--:|--:|--:|--:|
   | EC Comics | 4 | 4 | 0 | 4 ✓ |
   | Batman Adventures | 207 | 208 | 1 | 207 ✓ |
   | Absolute Batman | 26,085 | 29,353 | 3,268 | 26,085 ✓ |
   | Edge of Spider-Verse | 183 | 183 | 0 | 183 ✓ |
   | Hero for Hire | 318 | 328 | 10 | 318 ✓ |
   | Wonder Woman | 505 | 505 | 0 | 505 ✓ |
   | Spider-Man | 3,593 | 3,595 | 2 | 3,593 ✓ |
   | Batman | 4,757 | 4,770 | 13 | 4,757 ✓ |
   | Carnage | 96 | 96 | 0 | 96 ✓ |
   | Flash | 344 | 344 | 0 | 344 ✓ |
   | X-Cutioner's Song | 3 | 3 | 0 | 3 ✓ |
   | GI Joe | 84 | 85 | 1 | 84 ✓ |
   | Wildc.a.t.s | 28 | 28 | 0 | 28 ✓ |
   | I Hate Fairyland | 503 | 503 | 0 | 503 ✓ |
   | WildC.A.T.S | 195 | 195 | 0 | 195 ✓ |

   Receiving strings (no 09-04 expectation was tabled for them): **`Comics` 415** (0 captured
   09-10), **`Absolute Catwoman` 371** (27 captured 09-10 → 344 post-write), **`Amazing
   Adventures` 203** (5 captured 09-10 → 198 post-write).
3. **"No known title outside the 42 changed count" — NOT RUN.** It needs the pre-write snapshot
   (`preflight.pkl`), which is unavailable. Check 1 covers the correctness of every stored value
   (each row holds exactly what the deployed code produces); what check 3 would have added —
   that no row moved for a reason other than this unit — cannot be reconstructed after the write
   without the snapshot. Recorded as not done, not as passed.

**CAPTURE RESUMED 2026-09-10 (first ingest since 08-31).** `ebay_sales` 297,559 → **303,123**
(+5,564, all `created_at` 09-10, last ingest 21:24 UTC — i.e. still running during the
verification); `market_sales` 10,593 → **10,614** (+21, last ingest 21:30 UTC). 3,264 of the
5,564 ebay rows are `Absolute Batman` (the pools table's 3,268 is that query's own later
snapshot, at ~5,981 ebay rows captured; each table is internally consistent at its own instant). The 09-04 "no capture since 09-03" statement was true
through 09-09.

**RECONCILED — Batman Adventures "165 moving of 367" (09-10 dry run) vs "−166 of 373" (09-04
table): a SCOPE difference, not an error in either record.** The dry run's `SOURCE DRAIN` block
is printed **per table** — it sits inside the `for table in TABLES` loop in
`scripts/backfill_canonical_titles.py`, so "165 of 367" is the `ebay_sales` line. The 09-04
table is **whole-corpus** (both tables). Post-write, `created_at < 09-10`: `ebay_sales`
`Batman Adventures` **202** = 367 − 165; `market_sales` `Batman Adventures` **5** = 6 − 1; sum 207
= 373 − 166. The arithmetic closes on both sides with no residue. The one `market_sales` leaver
went to `Amazing Adventures` (that table holds exactly 1 `Amazing Adventures` row and 0
`Captain Adventures`, and the 09-04 table's 166 leavers go only to those two strings — one ebay
leaver actually lands on the distinct string `✦ Amazing Adventures`, which the 09-04 table folded
into its 151; verifier, 09-10). Which
`raw_title` it was cannot be listed now — the pre-write stored value is gone — but nothing about
the reconciliation depends on it. ⚠️ Generalise this: EVERY per-source figure a dry run prints is
per-table; compare it to whole-corpus tables only after summing the two tables' lines.

**rapidfuzz monitor — post-deploy check (Third-Party rule step 4) ⚰️ ~~STILL OWED~~ → CLOSED: run by Mike in the Render shell 2026-09-11, `True` / `[]` (recorded 2026-09-13, see the top entry).** Registered in
the deployed code (`check_all` tuple, 7th entry; `RAPIDFUZZ_VERIFIED_MAJOR = 3`;
`requirements.txt` pins `rapidfuzz>=3.0.0`). Run locally against the same code on 09-10,
`check_rapidfuzz(force=True)` returned `[]` (installed 3.14.3, PyPI latest 3.x). ⚰️ ~~**NOT verified in
production** — the Render-shell one-liner in the 09-04 entry has not been run by anyone the record
knows of … it is still open.~~ Mike ran it on 2026-09-11 (`True`, `[]`); the record did not learn of it
until 2026-09-13 — two days carried as open after it was done, the L-SW-2026-030 shape in miniature.

**Also observed, NOT touched (read-only pass; pre-existing dirty files are outside this unit):**
`docs/API_SPEND_LEDGER.md` is modified in the working tree and git now sees it as binary
(4,389 → 13,430 bytes) — it appears to have been re-saved as UTF-16; the content reads correctly
when decoded. Fourteen untracked entries (docx pile, `UniqueProperties/`, `body.html`, `headers.txt`,
two report drafts) and `docs/EBAY_CAPTURE_WEEKLY.docx` modified, all unchanged since the 09-04
snapshot.

**Verification agent (09-10, read-only, independent recomputation incl. the pre-ship differential
from `git show e690e04:title_normalizer.py` against pre-09-10 rows: 2,981 / 1,298 + 359 / 11 =
3,340 reproduced):** 61 confirmed / 3 wrong / 5 uncheckable. The three wrong figures (3,268 →
3,264; twelve → fourteen untracked; "~40 lines") and two imprecisions ("one minute" → four
seconds; the `✦ Amazing Adventures` string) are corrected in place above. Uncheckable = the four
statements about what happened outside this session (Mike ran the backfill in the Render shell;
`verify_backfill.py` unused; the rapidfuzz shell check unrun; the 09-04 file mtime).

**THIS UNIT'S ONLY WRITES (Mike stages):** this entry, and **L-SW-2026-030** in `docs/LESSONS.md`
(header bumped 28 → 29 lessons, dated 2026-09-10). No code change, nothing else applied or staged.
Docs-only → no `deploy`, no `purge`.

**QUEUED (unchanged from 09-04, log only):** plurals/single insertions (known-titles entry);
Whatnot `Comics #N` collector defect (the 321 title-less rows now sit on the string `Comics`,
which is 415 rows in total); `House of M` / `Ark-M` M1 residue; case-split family
characterisation; the dependency-status endpoint's missing service roster (rule step 4 is
unsatisfiable for a healthy check without it).

## 2026-09-04 — ✅ **Token-guard unit (A + B4 + rapidfuzz monitor): the 61 is ACCEPTED by Mike; APPLIED to the working tree; ⚰️ ~~NOT committed, NOT deployed, backfill NOT run~~** — **⚰️ DEAD 2026-09-10: committed + deployed 2026-09-04 in `2e27098` (this very entry rode in that commit), backfill run + verified 2026-09-10. See the 09-10 entry above and L-SW-2026-030.**

**⚰️ 2026-09-10: the ship-state in the paragraph below ("awaiting Mike's stage/commit/push/deploy; the backfill runs after deploy, by Mike, dry run first") is DEAD — all of it happened (commit + deploy 09-04, backfill 09-10). Kept for the 61-acceptance record, which stands.**

**MOST RECENT CHANGE (Rule 5): Mike accepted the 61 correct-rows-newly-rejected figure and
ordered A + B4 + the rapidfuzz monitor check shipped as one unit (2026-09-04, Park City).
Supersedes the 09-03 "NOT verified, NOT applied, 61 not yet accepted" state below. The code
is in the working tree awaiting Mike's stage/commit/push/deploy; the backfill runs after
deploy, by Mike, dry run first.**

**Why 61 is acceptable (Mike's record):** 710 corrupted rows correctly rejected against 61
correct rows newly rejected, roughly 12:1. Of the 61, 29 are correct separations of a
different book the old stripper was falsely merging, so the real cost is closer to 32.
292 rows repaired. Zero known→known swaps. The verification agent's whole-corpus run
(308,152 rows) found zero changes outside the measured 153,171-row subset.

**Verification (agent, 2026-09-04, independent recomputation from the pickles):** every
headline figure reproduced — 3,340 changing, 710 should-reject (all change under A and A+B4,
A+B4 == A on every one), 61 strict (B3: 67), 292 repaired, 2,277 junk→junk, 0 known→known;
proposed file vs measured A+B4 output 0 mismatches on 153,171 rows; proposed file vs stored
on ALL 308,152 rows = exactly 3,340, none outside the subset (B4's strip set is a strict
subset of the old one, so every row it can touch is in the census; A only acts on rows in
the guard probe). Code review: A's `>= 100` is equivalent to `(a + b) in pool`; `fuzz` in
scope; `_STRAY_LETTERS`/`_JOINERS` are function-local (regex cache absorbs the compile).

**⚰️ CORRECTIONS to the 09-03 entry (each also tombstoned in place below):**
- **The 710 is a HAND LABEL, not the formula the 09-03 entry implies.** "HEAD known → A output
  not known, under A alone" yields 1,171 (it includes the 461 correct losses). The 710 is the
  16 hand-labelled REJECT `(candidate, weak token, pair~support)` triples in scratchpad
  `guard_variants.py`, labelled from `guard_samples.txt`, applied to `guard_probe_modes.pkl`,
  spot-checked by the 09-03 verifier, and HARD-CODED (`- 710`) in `fix_run3.py`. The count is
  right and the labels are defensible; the record described a hand count as a computed result
  (L-SW-2026-020 shape). This line is the correct description.
- Line-596 census: **6,848** letter removals, not 5,848 (the four contexts sum to 6,848; typo).
- Census harmful: `I Hate Fairyland` **117**, not 115. One known→known row (`Walking Dead` →
  `The Walking Dead`) sits outside the four buckets (79 + 293 + 764 + 4,026 = 5,162 of 5,163).
- Repaired composition: `WildC.A.T.S` **137** exact (not 138) + 27 `Wildc.a.t.s` case-split
  + `X-Cutioner's Song` 1 (was folded into the 165); the 138th is the typo `WidlC.A.T.S`,
  which B4 alone repairs but the tightened pair rescue blocks (`wildca`~`widlca` 83.3), so it
  lands on its own string `Widlc.a.t.s`.
- Shrink figures are now **net pool deltas** (stored − A+B4 over the whole corpus), not
  should-reject leavers: Absolute Batman **−154** (149 `Absolute Catwoman` + 1 emoji-prefixed
  Catwoman + `Abosulte Batman` 1 + `Absolute BatmanArk M` 1 + `D.C. Comics Absolute Batman` 1
  + `Krs Absolute Catwoman` 1), Wonder Woman **−12**. EC Comics −330 = 321 market_sales rows
  (271 titled `Comics #N`, 50 bare `Comics`) + 9 ebay (5 `Eerie Comics`, 4 misc — all four land on the string `Comics`, so `Comics` receives 325).

**⚠️ T BEHAVIOUR, stated once where it cannot be missed: T STAYS IN THE STRIP LIST.** The
09-03 framing "the range includes I and T" names the defect, not the remedy. Under the joiner
rule only `T.` / `-T` / `T'` forms are kept (`WildC.A.T.S`, `T.M.N.T.`); a whitespace-delimited
T is still stripped — `Mr. T` → `Mr.`. I is the letter rescued; T is not. Deliberate: T's
standalone occurrences in the corpus are initialism residue and stray grade letters
(`T X-MEN`), not words.

**SHRINK RECORD — written before ship, part of this unit (per-title table:
`pool_delta.md` / `pool_delta_full.tsv`, delivered 2026-09-04; regenerable from the pickles
with `pool_delta.py`).** 3,340 rows move across 2,561 strings; 42 known titles change;
rows leaving known pools 771, arriving 292, known→known 0. (Table tallies: 10 named
negatives 729 + 27 small = 771 leaving; 1 + 10 + 27 + 117 + 137 = 292 arriving; 10 + 27 + 5 = 42
titles.)

| known title | before | after | Δ | leaving to |
|---|--:|--:|--:|---|
| EC Comics | 334 | 4 | −330 | `Comics` 325 (321 market_sales title-less Whatnot captures), `Eerie Comics` 5 |
| Batman Adventures | 373 | 207 | −166 | `Amazing Adventures` 151, `Captain Adventures` 15 |
| Absolute Batman | 26,239 | 26,085 | −154 | `Absolute Catwoman` 150, singletons 4 |
| Edge of Spider-Verse | 203 | 183 | −20 | `Spider-Verse` 20 |
| Hero for Hire | 335 | 318 | −17 | `Heroes for Hire` 17 |
| Wonder Woman | 517 | 505 | −12 | `Wonder Man` 11, lot 1 |
| Spider-Man | 3,604 | 3,593 | −11 | `W.e.b. Spider-Man` 11 |
| Batman | 4,765 | 4,757 | −8 | `Batman: R.i.p` 4, `I Am Batman` 4 |
| Carnage | 102 | 96 | −6 | `Carnage U.s.a` 6 |
| Flash | 349 | 344 | −5 | `Flash V.2` 5 |
| 27 titles at −1 to −3 | | | −42 | typos, initialisms, near-title substitutions (4 × −3, 7 × −2, 16 × −1) |
| X-Cutioner's Song | 2 | 3 | +1 | from `X-Cutioner' Song` |
| GI Joe | 74 | 84 | +10 | from `.. Joe` |
| Wildc.a.t.s | 1 | 28 | +27 | from `Wildc.a..` (the accepted case split, 11th instance) |
| I Hate Fairyland | 386 | 503 | +117 | from `Hate Fairyland` variants |
| WildC.A.T.S | 58 | 195 | +137 | from `Wildc.a..` variants |

**This is NOT a regression.** Every leaving row above was a wrong comp inflating a real
pool (a different book, a title-less capture, or a lot). `scripts/coverage_assessment.py`
will move as follows and each move is correct: **DEPTH** (rows per `canonical_title,
issue_number`) falls for EC Comics, Batman Adventures, Absolute Batman, Edge of
Spider-Verse, Hero for Hire, Wonder Woman and the −1..−3 titles, and rises for
I Hate Fairyland, WildC.A.T.S, GI Joe; **BREADTH** (distinct `canonical_title,
issue_number` keys) RISES, because the rejected rows become their own strings
(`Absolute Catwoman`, `Amazing Adventures`, `W.e.b. Spider-Man` …); the **"canonical_title
NULL/empty" count falls by 49** (DC `K.O.` listings that HEAD reduced to nothing now
canonicalise as `K.o`; all 49 are ebay_sales rows, which is the table that metric reads). Whatnot `Comics #N` rows become their own junk string — better,
not fixed; collector defect stays queued.

**Non-known noise in the differential (read, do not fear — none of it moves a real pool):**
`’orc` → `D’orc` 304 (the typographic-apostrophe fix), `Absolute Batman Ark-` → `Ark-M` 204
across three spellings (hyphen guard now two-sided), `.. Joe` → `G.i. Joe` 70 across four
spellings, `World' Finest` → `World's Finest` 15, `, Lusiphur` → `I, Lusiphur` 12, NULL → `K.o`
49. Junk→junk total 2,277.

**Monitor check — `check_rapidfuzz` exercised and fixed (2026-09-04):** eight branches run
in isolation against the tree file (normal with live PyPI, cache hit with no refetch, verified-
major mismatch, newer PyPI major, PyPI failure → `_error_entry` + 300 s backoff exactly as
`check_stripe`, not importable → error entry, both warnings at once, unparseable version).
PyPI latest today 3.14.6, installed 3.14.3, same major → 0 warnings. Two defects found by
the verifier and FIXED before ship: (1) both warnings shared `item` → same `_alert_key` →
`_send_alert_email` kept only the second, so an installed-major mismatch would never be
emailed when a newer major was also published — now `rapidfuzz==X (verified major vN)` vs
`rapidfuzz==X (PyPI major vM)`, distinct keys confirmed; (2) an unparseable installed
version string returned 0 entries (silently healthy) — now warns with item
`rapidfuzz==X (unparseable)`. Also: the module's header table gained the rapidfuzz row AND
the AWS Rekognition row it never received at registration (2026-08-24); CLAUDE.md's
monitored-services list updated. **Post-deploy check (Third-Party rule step 4) — ⚠️ read
before looking:** `/api/admin/dependency-status` returns `check_all()`'s WARNINGS only
(`routes/admin_routes.py:60-84`); a healthy check is ABSENT from it, so "rapidfuzz does not
appear" is the healthy result, not a failed registration. Verify in the Render shell instead:
`python -c "import dependency_monitor as d, inspect; print('rapidfuzz' in inspect.getsource(d.check_all)); print(d.check_rapidfuzz(force=True))"`
→ expect `True` and `[]`. **QUEUED, pre-existing, not this unit:** the endpoint has no roster of
checked services, so rule step 4 as written ("verify the new service appears") is
unsatisfiable for any healthy check; a `services` list in the response would fix it.

**`docs/technical/ARCHITECTURE.txt`: nothing to add** — it has no monitored-services section
(only the env-var table) and this unit adds no env var; the 09-03 line saying it "still needs
the entry" is tombstoned below. **`House of M`:** the tree normalizer maps that string to
`House of` (HEAD: `House of X`, a wrong known-title match); no corpus row carries it (0 pairs
in the pre-flight), so the 09-03 "not this unit" line stands as a corpus fact, not a code one.

**IN THE WORKING TREE (applied 2026-09-04, Mike stages):** `title_normalizer.py` (A + B4 with
comments), `dependency_monitor.py` (check + fixes + header), `CLAUDE.md` (list), this file.
Backend change → `deploy` required; no frontend file touched → **no `purge`**. The backfill
script is already in `scripts/` (in the image); the normalizer it imports is what `deploy`
ships, so **deploy BEFORE the dry run** or the dry run measures HEAD, not the unit.

**BACKFILL (Mike runs, Render shell, after deploy):** `python scripts/backfill_canonical_titles.py`
(dry run) → read → `--execute` → re-run dry run expecting 0. Expected dry-run shape from the
09-03 snapshot: **~3,340 would change** (+ any rows captured since the snapshot),
**1,298 ebay + 11 market distinct (before, after) pairs** — the script's "distinct pairs" is
transitions, NOT the 2,561 distinct strings with a nonzero delta above — **PRE-FLIGHT against the live RO connection (`do_readonly`, 2026-09-04
21:00 UTC, `preflight.py` → `preflight.pkl`): IDENTICAL to the snapshot.** 297,559 + 10,593
rows (no capture since 09-03); stored ≠ HEAD **0** on both tables (baseline flat, verified per
run as the backfill docstring demands); stored ≠ tree **2,981 ebay + 359 market = 3,340**,
1,298 + 11 distinct pairs; all 42 known-title deltas exactly as tabled above; classes
771 / 292 / 2,277 / 0. The dry run should say **3,340 would change** — any other number is
capture growth (account for it) or something else (stop). `verify_backfill.py` (scratchpad,
compiled, reads `preflight.pkl` as the pre-write snapshot) is ready for the post-write check.
`SOURCE DRAIN` will list `SOURCE DRAIN` will list many PARTIAL sources and that is expected —
`Absolute Batman` 154 moving / 26,085 staying, `Batman` 8 / 4,757, `Spider-Man` 11 / 3,593
are the true shape (the leavers are different books), NOT a split; the drain report keys on
exact spelling and cannot tell a correct separation from a split (its known defect, 09-02).
Flatness: stored == HEAD on every row at the 09-03 snapshot; a dry-run total materially above
the differential means capture growth or an unbackfilled change — account for it, do not stop.
Verification afterwards from the RO connection (second principal): (1) stored == tree
normalizer on every row → 0; (2) the 15 named pools at their AFTER counts (± capture growth);
(3) no known title outside the 42 changed count. Instrument to be written as `verify_backfill.py`
in the session scratchpad on Mike's word, as on 09-03.

**QUEUED (unchanged, log only):** plurals/single insertions (known-titles entry, not a
threshold); Whatnot `Comics #N` collector defect; `House of M` / `Ark-M` M1 residue; the
case-split family characterisation (09-03 close).

## 2026-09-03 (later, PAUSED FOR TRAVEL — Mike) — 🧭 **Token-guard unit: measured, shape chosen, NOT verified, NOT applied. Read this before touching `title_normalizer.py`.**

**MOST RECENT CHANGE (Rule 5): Mike decided the guard's pair-rescue fix (A) and the line-596
single-letter stripper ship as ONE unit, and rejected the measured B1/B2 shapes; the redesign
was chosen (joiner rule, below) and measured; work paused before verification. Supersedes the
"case-insensitive canonical-assigning match" queue item below (see tombstone).**

**Standing decisions this arc (Mike, 2026-09-03)**
- ⚰️ **Case fix (M3, `processor=str.lower` on the assigning `extractOne`) is NOT shipping.**
  DEAD as a unit. REASON: measured on the current corpus it relabels 9,146 non-case rows in
  ebay_sales (≈450 substitution merges of a different real title, 4,507 sub-series absorbed
  into parents) — M3 is load-bearing: it is the only thing keeping ALL-CAPS listings away from
  a token guard with a hole in it. The Werewolf `By/by Night` split (156 rows) stands as
  accepted debt. SUPERSEDES the "QUEUED — case-insensitive canonical-ASSIGNING match, 1,461
  rows" item further down; do not re-queue it.
- **Qualifier absorption** (annuals / spin-offs / crossovers into parent pools, 4,507 rows
  under a hypothetical case fix) is a POLICY question, not decided, not this unit.
- **A (guard) + line 596 ship together.** REASON: A alone newly rejects 461 correct rows, 385
  of them the entire `I Hate Fairyland` pool, because the guard's hole is currently the only
  thing repairing what line 596 breaks (L-SW-2026-027 masking shape again).
- ⚰️ **B1 (`[B-HJ-W]`) and B2 (`[B-HJ-SU-W]`) DEAD.** REASON (Mike): a less readable range
  that still mangles `Batman: R.I.P.` → `Batman: .i.`; trades one defect for a smaller one and
  leaves the trap. "The range is the defect."
- **rapidfuzz goes into `dependency_monitor.py` in this unit** (small, separable, same failure
  shape as the Haiku retirement: pin `>=3.0.0`, 3.14.3 installed, the 2.x→3.x processor
  default change is the likely origin of M3, and the monitor version-checks only stripe and
  boto3 today).

**Line 596 — what it is for, and the census (read-only, whole corpus, `census596.py`)**
- Origin: day-one commit `ac9b2be` (2026-02-12). No lesson, no doc mentions it (plain grep 0,
  rg 0). Purpose is only the comment: "Remove any remaining standalone single letters (except
  common ones in titles). Keep X, A, D'". Someone intended an exclusion list and wrote the
  RANGE `[B-W]`, which includes I and T.
- It fires on 5,163 of 308,152 rows (⚰️ ~~5,848~~ **6,848** letter removals — CORRECTED 2026-09-04, typo; the contexts sum to 6,848). Contexts: adjacent to a period
  (initialism) 2,422 · mid-string space-delimited 2,333 · leading 1,060 · trailing 1,033.
  Letters: I 961, M 905, S 868, D 668, T 478 …
- Against known titles: **beneficial (strip makes the match) 79 rows** — and ~23 of those are
  false merges of a DIFFERENT book (`W.E.B. of Spider-Man`→Spider-Man 11, `Carnage U.S.A.` 6,
  `I Am Batman` 4, `I Am Iron Man` 2); the genuine noise it removes is `U PICK` ×8, `B&W` ×3,
  `V.2` ×7, `D.C.` ×3, stray grade letters (`F FANTASTIC FOUR`, `N ABSOLUTE BATMAN`, `T X-MEN`)
  ~10, `Batman: R.I.P.`→Batman 4. **Harmful (strip breaks the match) 293 rows** — all
  initialisms and the word I: `WildC.A.T.S` 165, `I Hate Fairyland` ⚰️ ~~115~~ **117** (CORRECTED 2026-09-04; +1 uncategorised `Walking Dead`→`The Walking Dead` row), `G.I. Joe` 10,
  `X-CUTIONER'S SONG` 1. **No effect 764** (381 are `I Hate Fairyland` rows saved by the
  guard's pair rescue — they become harmful the moment A ships). **Junk either way 4,026**
  (`D’orc`→`’orc` 304: the apostrophe guard is ASCII-only, so the comment's own example fails
  on a typographic apostrophe; `Ark-M`→`Ark-` ~330: the hyphen guard looks only forward;
  `WORLD'S`→`World'`: possessive S in ALL-CAPS).
- **Reading:** the line's purpose is stray whitespace-delimited residue. Every harm is a letter
  JOINED to a neighbour by a period, an apostrophe (either kind) or a hyphen, or the word I.

**Decision — the joiner rule (B4), chosen from purpose, not from score**
- Explicit letter list replaces the range: `BCDEFGHJKLMNOPQRSTUVW` (not stripped: A, I — English
  words that start titles; X; Y — `Y The Last Man`; Z).
- A letter is stripped only when NOT joined to a neighbour by `.` `'` `’` `-`. Ampersand and
  slash SEPARATE words (`B&W`, `W/COA`), so residue around them is still stripped — that is
  the difference from the whitespace-only reading (B3), which loses 6 more rows (`B&W` 3,
  `W/COA` 1, `#v` 2) for no purpose-based reason.
- Proposed line (measured; the patch text is in the scratchpad `make_patch.py`, regenerable):
  `_STRAY_LETTERS = 'BCDEFGHJKLMNOPQRSTUVW'`, `_JOINERS = r'\w.\'’-'`,
  `text = re.sub(r'(?<![' + _JOINERS + r'])\b[' + _STRAY_LETTERS + r']\b(?![' + _JOINERS + r'])', '', text)`
- Proposed A line: `pair_ok = {i for i, (a, b) in enumerate(zip(cand, cand[1:])) if max((fuzz.ratio(a + b, p) for p in pool), default=0) >= 100}`

**Measurement (A + B4, current case-sensitive path only, 153,171-row subset = every row either
change can touch; `fix_run2.py` / `fix_run3.py`; stored == HEAD on all rows)**
| | rows |
|---|---|
| rows changing vs HEAD | 3,340 |
| correctly rejected (the 710 mis-stored rows leave their wrong pools) | 710 |
| **correct rows newly rejected, strict definition** (HEAD known title → not, minus 710 — ⚠️ the 710 is a HAND LABEL from 16 REJECT triples in `guard_variants.py`, hard-coded in `fix_run3.py`, NOT the output of this formula, which gives 1,171 under A alone; see 09-04 entry) | **61** (B3 whitespace-only: 67) — **ACCEPTED by Mike 2026-09-04** |
| repaired (fall-through → known title) | 292: `WildC.A.T.S` ⚰️ ~~165 (138 exact + 27~~ **164 (137 exact + 27** `Wildc.a.t.s` case-split spellings), `I Hate Fairyland` 117, `GI Joe` 10, **`X-Cutioner's Song` 1** (CORRECTED 2026-09-04; the 138th is the `WidlC.A.T.S` typo, blocked by A) |
| junk → junk (neither side a known title; NOISE, no pool moves) | 2,277 |
- **The 61 is NOT at or under B2's 29, and the four `Batman: R.I.P.` rows ARE among them** — as
  the clean string `Batman: R.i.p`, not a mangling; R.I.P. is a Batman storyline, so leaving
  the Batman pool is a judgement call, not a defect. Composition of the 61: 17 A-side (13
  typo/hyphen-glue legit + junk + 1 qualifier, enumerated in the 09-03 guard report); 44
  B-side, of which **28–29 are correct separations of a different book that the old strip
  was falsely merging** (`W.E.B. of Spider-Man` 11, `Carnage U.S.A.` 6, `I Am Batman` 4,
  `U.S.Avengers` 3, `I Am Iron Man` 2, `Punisher: P.O.V.` 1, `Transformers/G.I. Joe` 1,
  `W.I.P. Watchmen` 1), **11 are same-book residue now retained** (`Flash V.2` 5, `What If?
  V.2` 2, `D.C. Comics …` 3, `T.M.N.T. …` 1) and 4 are `Batman: R.I.P.`. B2 scored 29 partly
  by KEEPING the 28 false merges. Reported as-is; not tuned.
- Pool shrink to record before ship (Mike's instruction): EC Comics −330 (321 of them
  market_sales ⚰️ ~~Whatnot captures titled `Comics #N`~~ **271 `Comics #N` + 50 bare `Comics`**), Absolute Batman ⚰️ ~~−151~~ **−154**, Batman Adventures
  −166, Edge of Spider-Verse −20, Hero for Hire −17, Wonder Woman ⚰️ ~~−11~~ **−12** (CORRECTED 2026-09-04: net deltas, not should-reject leavers) … `scripts/coverage_assessment.py`
  BREADTH/DEPTH will drop for those titles; **that is not a regression, those comps were
  wrong**. ⚰️ ~~Per-title before/after table NOT yet computed (see unmeasured).~~ **DONE 2026-09-04 — in the 09-04 entry.**
- Patch check: the proposed `title_normalizer.py` (scratchpad `title_normalizer.py.proposed`)
  reproduces the measured A+B4 output on all 153,171 rows, **0 mismatches**.

**Proposed monitor check ⚰️ ~~(drafted, NOT compiled, NOT run)~~ — COMPILED, EXERCISED (8 branches), FIXED (dedup keys, unparseable version) and APPLIED 2026-09-04:** `check_rapidfuzz` in
`dependency_monitor.py` — `RAPIDFUZZ_VERIFIED_MAJOR = 3`; warn when the installed major
differs from it (behaviour changed with no code change) and when PyPI publishes a newer major
(do not adopt without a corpus differential); `_caches['rapidfuzz']`; registered in the
`check_all` tuple; `PYPI_RAPIDFUZZ_URL`. ⚰️ ~~CLAUDE.md's monitored-services list and
`docs/technical/ARCHITECTURE.txt` still need the entry~~ (CLAUDE.md DONE 09-04; ARCHITECTURE.txt has no such section — nothing to add); `/api/admin/dependency-status` check is
post-deploy.

**UNMEASURED / NOT DONE (in order)** ⚰️ **ALL SIX RESOLVED OR SUPERSEDED 2026-09-04 — see the 09-04 entry; items 1–5 done, item 6 is the live backfill plan there.**
1. Verification agent has NOT run on the B4 measurement, the census, or the patch.
2. Proposed `dependency_monitor.py` NOT compiled or exercised (`py_compile`, `check_rapidfuzz(force=True)`).
3. Per-title before/after pool table for the coverage record NOT computed (inputs exist:
   `corpus.pkl` stored counts vs `fix_run3.pkl` AB4 output).
4. Nothing applied to the working tree. Proposed copies + unified diffs live ONLY in the
   session scratchpad (`…\21ae37af-…\scratchpad\*.proposed`, `*.diff`, `make_patch.py`) — a
   temp dir that may not survive; `make_patch.py` regenerates them from HEAD and the two lines
   above regenerate the code by hand.
5. Record text for the unit (shrink numbers, junk-noise note, queued items) NOT written.
6. Backfill after ship: `scripts/backfill_canonical_titles.py` ⚰️ ~~`--dry-run`~~ (no flags IS the dry run; there is no `--dry-run` flag) then `--execute`
   (Mike), verification from the RO connection as on 09-03.

**QUEUED (log only, Mike's instruction)**
- **Plurals and single insertions are undecidable by score** (`Robins` 28, `Batgirls` 11,
  `Thors` 3, `Outcasts` 4, `Daredevils` 4, `Secret War` 12, `Bartman` 8, `Fantastick` 5):
  the mechanism is a known-titles entry, not a threshold. Open, not solved.
- **Whatnot collector capture defect:** 321 market_sales rows carry the raw title `Comics #N`
  (title-less captures). After this unit they become their own junk string instead of
  corrupting the EC Comics pool — better, not fixed. File against the collector.
- `House of M` (M stripped as trailing residue, `of` stripped by M1) and `Absolute Batman:
  Ark-M` strings: residue of M1 and the qualifier question, not this unit.

**Mystery file resolved:** repo-root `REPORT_DRAFT.md` was Mike's upload copy. Untracked; delete or leave.

## 2026-09-03 (SESSION CLOSE, Mike's record; conversation `46ea11d3-7edc-4e73-abf6-974c15f1165b`) — 🔒 **Everything in this session SHIPPED; open items enumerated below so nothing resolved is re-raised and nothing unresolved is lost.**

**MOST RECENT CHANGE (Rule 5): session closed with all three units shipped and verified —
`fa62550` (contrast + wordmark, deployed + purged), `22fb8dd` (normalizer + docstring +
L-SW-2026-029), `a89a10c` (verified backfill record). Supersedes every "waiting on Mike"
line above. Nothing below is pending on Claude.**

**SHIPPED AND VERIFIED**
- Contrast: `.defect-area-label` + `footer a` → `#a78bfa`. Committed, pushed, deployed, purged.
- Waitlist wordmark `routes/waitlist.py:80` restored (third recurrence). Same commit.
- Normalizer by-phrase change: applied, backfilled by Mike (912 rows updated, 0 skipped),
  verified from the RO connection 03:47 UTC — 724 / 156 / 14, zero rows differ from the
  deployed normalizer, no non-Werewolf title lost rows. The 720 guard-commit drift rows are
  resolved with the 192 from this change.
- Backfill docstring corrected (flatness re-verified per run); drain-detector case-split
  blindness commented at the defect.
- **L-SW-2026-029 follow-up CLOSED (Mike):** the `*secret*` / `*password*` ignore-rule null
  re-checked with plain `Select-String` over the working tree, `.claude` excluded — clean, six
  hits, all prefix-inspection or placeholder code. The eight prior audits no longer carry an
  untested credential conclusion. **Low-priority remainder:** same check against git HISTORY
  (a key committed once and removed is still in the repo).

**NEW, UNQUEUED (found 2026-09-03)**
- `.claude/worktrees/` holds nested full copies of the codebase (worktrees inside worktrees).
  Every filesystem-walking search multiplies hits by the copy count; any prior audit that
  walked the filesystem rather than the git index counted duplicates. Cleanup pass wanted;
  know this before the next audit.
- ⚠️ **The deferred purple-contrast list is INVALID as a list.** `footer a` matched nothing
  rendered; the "nine other occurrences" were selected by grepping `styles.css`, so an unknown
  number are also dead, and a real failure in the footer injector (`js/footer.js`) was never
  in scope. **Rebuild the list from computed styles on live pages before the deferred pass.
  Do not work from the file.**
- `--surface-elevated` is undefined everywhere; the site renders on the `#1a1a2e` fallbacks.
- `WV/whatnot-valuator/content.js:345` renders a key placeholder from `key.slice(-4)` — the
  extension holds an Anthropic key client-side (normal for BYOK). Where it is stored and
  whether page context can reach it is an open DESIGN question, not a repo leak.
- Two dirty tracked files nobody in this session touched: `docs/API_SPEND_LEDGER.md` (still
  UTF-16, BOM `FF FE`, re-encoded at the 08-30 close — see line ~174 of the 08-30 entry) and
  `docs/EBAY_CAPTURE_WEEKLY.docx` ("stopped here 8/28"). **Both predate 09-02.** Identify
  before any commit sweep picks them up.

**QUEUED — CHARACTERIZE BEFORE SCOPING (one unit or two is undecided)**
Four title splits in one family:
1. case-insensitive canonical-ASSIGNING match — 1,461 rows across nine existing splits plus
   tonight's `Werewolf By/by Night`;
2. `Werewolf by Night: Red Band` vs `Werewolf by Night Red Band` — colon split, 6 vs 3;
3. `Giant-Size Werewolf` fragmenting three ways across a 5-row pool;
4. M1 "of" bug → `Dead Night Werewolf by Night` (correct routing for this change, wrong
   output string).
**Question first:** do they share a code path, and would the case fix incidentally resolve
any of the others? Row counts alone do not decide unit boundaries.

**STILL UNSCOPED**
- "free capture re-check" — appeared once in the agreed session order, never defined in any
  record, no scope line from Mike. **Do not guess at it.**
- Spine-angle capture ambiguity — exists only in the Bernard correspondence doc; needs a
  ROADMAP entry. Live UX defect on every submission, retroactively unmeasurable confound
  under all 139 existing ones. Bernard has a protocol; his books are months out.

**Standing constraints unchanged:** Mike runs all git, deploys, env changes, production
writes. Verification agent against anything new before presenting. A later record that
contradicts this one → stop and say so.

## 2026-09-03 (later) — ✅ **BACKFILL EXECUTED BY MIKE AND VERIFIED from a second connection. Normalizer unit is DONE in production.**

**MOST RECENT CHANGE (Rule 5): Mike ran `scripts/backfill_canonical_titles.py --execute` on
Render; verification (read-only `do_readonly`, 03:47 UTC) matched the recorded end state on
all three checks. Supersedes "backfill + verification WAITING ON MIKE" below.**
- Check 1 — stored `canonical_title` vs HEAD normalizer output: **0 rows differ** in
  ebay_sales, **0** in market_sales (was 911 + 1 before the write).
- Check 2 — ebay_sales spellings: `Werewolf By Night` **724**, `Werewolf by Night` **156**,
  `Werewolf` **14** — exactly the pre-recorded expectation.
- Check 3 — no non-Werewolf title lost rows (32 Werewolf-family sources decreased in
  ebay_sales, 1 in market_sales; zero others). No capture growth in the window.
- The accepted case split now exists in production (10th instance). The matcher unit
  owns it. Remaining: Mike's commit/push/deploy of the code side if not already done —
  the backfill ran against the deployed normalizer, so the image already carries it.

## 2026-09-03 — 🚢 **Normalizer SHIP UNIT prepared (superseded above): pre-flight differential re-run (identical), docstring corrected, drain-detector defect annotated.**

**MOST RECENT CHANGE (Rule 5): Mike ordered the normalizer ship unit (2026-09-03). The
case-insensitive-matcher fix is explicitly NOT in it. Supersedes "ship/no-ship is Mike's
call" (09-02 addendum) — the call is SHIP. Sequence: (1) docstring fix ✅ (2) normalizer
change ✅ already in working tree (3) backfill — MIKE RUNS on Render (4) verification from a
second connection — runs on Mike's word, script ready.**

- **Pre-flight (read-only, 2026-09-03 01:05 UTC):** differential re-run against HEAD
  `fa62550` (normalizer at HEAD byte-identical to `4212316`). **IDENTICAL to the 09-02 run:**
  297,559 + 10,593 rows; HEAD≠proposed 192 (190 class A + 2 class C, all Werewolf by
  Night); stored≠HEAD 720; stored≠proposed 912. No new title. Corpus row count unchanged
  since the audit (no capture in between).
- **Expected end state, recorded BEFORE the write** (ebay_sales, from the fresh
  differential + a pre-write per-title snapshot taken 01:08 UTC):
  `Werewolf By Night` 7 → **724** · `Werewolf by Night` 0 → **156** · `Werewolf` 875 → **14**
  (residual: lots/TPBs, 1966 Dell, 2× Blood Moon Rise) · market_sales `Werewolf` 1 → 0,
  `Werewolf By Night` 0 → 1. Backfill dry run should say **911 + 1 = 912 would change**.
- **Backfill drain report will be WRONG in a known way:** it keys on exact spelling, so it
  lists `Werewolf → Werewolf By Night` and `Werewolf → Werewolf by Night` as two pairs and
  cannot flag that they are one split book. `Werewolf` shows PARTIAL (861 moving / 14
  staying) — the 14 are genuine. Not a failure signal. Comment added at the defect
  (`scripts/backfill_canonical_titles.py`, inside `scan()`); fix belongs to the matcher unit.
- **Docstring at `scripts/backfill_canonical_titles.py:11-30` rewritten:** flat baseline is
  a corpus property at a moment, true 2026-08-17 (274,344/274,344), FALSE by 2026-09-02
  (720 rows), must be re-verified per run, never assumed.
- **Verification instrument ready:** scratchpad `verify_backfill.py` (RO, second
  connection): (1) stored==HEAD on every row → 0 diffs, (2) exactly two spellings with the
  counts above, (3) no non-Werewolf title's row count moved vs the snapshot. Stops and
  reports on any disagreement; corrects nothing.
- **⚰️ Known, accepted, NOT fixed:** the case split is the 10th instance of a condition on
  9 titles / 1,461 rows; coverage script already has 59 phantom keys. Real fix =
  case-insensitive canonical-assigning match, own unit, own differential (1,461-row blast
  radius).
- **New lesson L-SW-2026-029:** the `Grep` tool honours `.gitignore` — `scripts/cp1_*.py`
  (ignored since `ad07a22`, 08-26) were invisible to the 09-03 audit; three findings existed
  only because the verification agent read files directly. Eight prior sessions used the
  tool (listed in the lesson). **Mike decides what gets re-checked; nothing re-run.**
- **HEAD moved during the session:** `fa62550` = Mike committed the 09-02 contrast + waitlist
  fixes. Consistent with the record; nothing contradicts the brief.
- API spend today: $0.

# (prior header) Where We Left Off - Sep 2, 2026

## 2026-09-02 — 📐 **Three narrow items done: 2 contrast fixes applied, waitlist wordmark fixed, normalizer DIFFERENTIAL RUN (report only, nothing staged).**

**MOST RECENT CHANGE (Rule 5): the normalizer-pair differential that has gated
`title_normalizer.py` + `scripts/backfill_canonical_titles.py` since 2026-08-26 has now
been RUN (read-only, `do_readonly`, corpus read 2026-09-03 00:24 UTC). Supersedes
"corpus differential NOT run" (08-28 triage). Result: HEAD→proposed changes 192 rows,
ALL Werewolf by Night; zero rows in market_sales. Full report:
`docs/technical/NORMALIZER_DIFFERENTIAL_2026-09-02.md`. Ship/no-ship is Mike's call —
nothing from item 3 is staged or applied beyond the already-dirty working tree.**

- **Contrast (styles.css:894 `footer a`, :2006 `.defect-area-label`) — APPLIED, unstaged.**
  Both `var(--brand-purple)` → literal `#a78bfa` (brand-doc "purple on dark" value; also the
  footer injector's hover fallback). Measured: #7c3aed was 3.0:1 on the defects panel's
  `#1a1a2e` (`--surface-elevated` is undefined everywhere, so the fallback IS the
  background) and 3.3:1 on `#0f0f1a`; #a78bfa is 6.3:1 / 7.0:1. One token serves both.
  ⚠️ **`footer a` in styles.css matches NOTHING rendered:** styles.css loads on app.html
  (`data-no-universal-footer`, no footer), collection.html (no footer) and sightings.html
  (footer injected by /footer.js, whose `.footer-col a` out-specifies `footer a` and
  paints links white on `#1e1b4b`). Confirmed live on index.html; sightings.html itself
  redirects to /login unauthenticated so it was read from source. The fix is correct and
  harmless; it changes no pixel. The nine other #7c3aed uses are untouched (deferred pass).
- **Waitlist email wordmark (routes/waitlist.py:80) — APPLIED, unstaged.** `SLAB` → `$LAB`.
  Root cause of the recurrence: the 03-04 rebrand commit `a6cc7e6` touched HTML/JS only;
  HTML embedded in Python f-strings was invisible to that sweep (L-SW-2026-028 surface
  blindness). Wordmark is retyped per template: `routes/admin_routes.py:942` (correct),
  `routes/waitlist.py:80` (now correct); auth.py/verify.py emails use prose "Slab Worthy"
  in h2s, no wordmark. No shared email module exists; the one shared email-config surface
  is `auth.py:57-59` (`RESEND_FROM_EMAIL`, `FRONTEND_URL`), which admin_routes already
  imports — a `WORDMARK_HTML` constant there is the single home. NOT refactored.
- **Normalizer differential — key findings** (detail in the report): (1) **stored ≠ HEAD on
  720 rows** — the 08-17 guard commit was never backfilled in prod (697 rows still stored
  as 'Werewolf'); the backfill's "baseline is flat" claim is stale. (2) HEAD→proposed:
  190 rows class A (by-phrase preserved, 19 pairs, 156 land on the known title), 2 rows
  class C ('Dead of Night Werewolf by Night' 2009 MAX mini leaves 'Werewolf By Night' —
  arguably correct, but lands on the M1-mangled 'Dead Night Werewolf by Night'). (3) 14 rows
  stay under 'Werewolf' (lots/sets/TPBs, a 1966 Dell 'Werewolf', and 2× 'Blood Moon Rise'
  which is a residual miss). (4) **Case split in the stored column:** proposed yields
  'Werewolf by Night' (156, all-caps inputs via the title-caser) beside 'Werewolf By Night'
  (723, assigned verbatim from known_titles.json) because the canonical-ASSIGNING match is
  still case-sensitive (M3) — deliberately outside this change. `title_matching._norm`
  lowercases both sides so comps unify; the stored strings do not.
- **Verification:** code-reviewer agent over all three artifacts — clean; it reproduced
  all four contrast figures independently.
- **API spend today: $0.** No Anthropic calls. `docs/API_SPEND_LEDGER.md` is still UTF-16
  (flagged 08-30, not touched — out of brief).

# (prior header) Where We Left Off - Aug 31, 2026

## 2026-08-31 (addendum) — 📐 **Spawn #77 RESOLVED (floor stands); ground truth now MONTHS out; spine-angle confound recorded.**

**MOST RECENT CHANGE (Rule 5): the ground-truth timeline moved from days to MONTHS
(Bilbo/Meisler, recorded in project storage). Slabbed-book purchase DEMOTED to optional
partial — a sealed slab yields a cover shot only (no spine/interior/centerfold, plus
glare), so it cannot answer the spine-stress question it was sought for. Real path:
volunteer photographs raw books → app grades → press → CGC submit → compare (~10 books
entering, more recruitable). Variant B blocked for months. Do NOT hold engineering
capacity waiting on calibration. Next-session order UNCHANGED: capture re-check →
two approved contrast fixes → normalizer differential (now clearly the highest-value
unblocked engineering).**

- **Spawn #77 outlier RESOLVED (measured, read-only, 2026-08-31):** the 8.0/7.0/7.0 are
  grade_submissions ids 26/28/33 — three separate PRODUCTION submissions by user 38 on
  2026-08-06, each a fresh 4-photo upload (raw scores 7.77/7.18/7.05; the 8.0-vs-7.0 is
  snap boundaries amplifying a 0.72 raw spread). Cross-PHOTOGRAPHY variance, not
  run-to-run model noise — Bilbo's hypothesis, confirmed stronger. **The 0.5 identical-
  input floor stands; every read rule built on it holds.** Bonus decomposition: id 26
  re-graded 8.0→8.0, id 28 7.0→7.5 in baseline 1 — within-photo-set ≤0.5, across photo
  sets of the SAME book ~1.0. Photography dominates model noise.
- **⚠️ Eval-set wrinkle found in the process:** ids 26 and 28 are the SAME physical
  comic (Spawn #77) under two photo sessions — my near-duplicate screen caught the 1988
  cluster but not this pair (different stored grades hid it). Two of 36 books
  double-weight one comic; accidentally USEFUL as an in-run photo-variance probe. Left
  in place deliberately — the set is pinned; note it when reading aggregates.
- **Spine-angle confound (recorded, NOT acted on):** the spine-photo instruction never
  specifies an angle; Meisler shot ~45° and guessed. Every spine photo in all 139
  submissions is at a submitter-chosen, unrecorded angle — a quiet confound under the
  corpus INCLUDING the pinned eval set, and unmeasurable retroactively. No input
  changes while calibration is mid-flight.
- **Backlog only:** user-declared defect checkboxes for photo-invisible decisive
  defects (cut panel/coupon, interior tears, tidelines, mould, water ripple, staple
  anomalies) — no AI, interacts with CP-1 verdict withholding.

# (prior header) Where We Left Off - Aug 30, 2026

## 2026-08-30 (SESSION CLOSE) — 🔒 **Brand + matcher work committed (`5f30c5c`) and deploying. Operator-key gate: CLOSED AND VERIFIED since Aug 28 (correction below).**

**⚰️ CORRECTED same night (Mike): the paragraph that stood here claimed the Aug-28
operator-key verification was "interrupted and never completed" and that tonight's
deploy closed the gate unverified. FALSE — the check was COMPLETED on 2026-08-28,
end-to-end across five links: X-Operator-Key observed on a live fmv request; deploy;
anonymous curl 401; keyed curl 200; POST /api/sales/record 200 at 17:14:35 GMT; plus
Mike's separate confirmation that the DevTools key matched Render. The gate has been
closed and the endpoints live-verified since Aug 28. The three re-check commands are
being run tonight anyway — a silent 401 costs a week of capture and the check is free
— but as belt-and-braces on a VERIFIED state, not as closing an open gate. Do not
re-raise this as open.**

**Decisions of record (Mike, session close):**
- Provenance blockquote in the brand .md STAYS — byte-parity with the .docx was never
  the goal.
- Contrast: fix ONLY `.defect-area-label` (styles.css:2003) + `footer a`
  (styles.css:894) — the high-traffic surfaces; the other nine deferred to one later
  pass. **Next session's work, not tonight's.**

**Uncommitted / will-not-survive-cold inventory:**
- ⚰️ ~~`scripts/regrade_run_20260830_2006_baseline.json` untracked~~ — **COMMITTED
  same night**, per Mike. Resolved.
- ⚰️ ~~`docs/SlabWorthy_Brand_Guidelines.docx` untracked~~ — **COMMITTED same
  night**, per Mike. Resolved.
- `title_normalizer.py` + `scripts/backfill_canonical_titles.py` — dirty since
  2026-08-26, still awaiting the corpus differential before staging (L-SW-2026-027).
- `docs/EBAY_CAPTURE_WEEKLY.docx` — dirty ("stopped here 8/28" marker).
- ⚠️ `docs/API_SPEND_LEDGER.md` — modified AND **re-encoded to UTF-16** by tonight's
  edit: grep/tooling reading UTF-8 sees byte soup, so spend greps will silently miss
  (L-2026-029 surface blindness). One-line re-encode to UTF-8 next session.
- Untracked BO exports at root/docs/business (Session State, Claims Audit, Roadmap,
  "the 9.0 ceiling and era-blind rubric.docx") — need homes or .gitignore.

**Loops closed tonight:** eval set pinned (36 rows, verified); baseline 1's complete
36/36 run makes the media-type `--preflight` moot for this set; styles.css is frontend
→ tonight's ship wants `purge` after the Pages build (token is inert, no urgency).

**Flagged, unpicked, not in Mike's known-open list:** (1) `/api/messages` is still an
uncapped authed Sonnet proxy (2026-08-29 finding) — dormant (0 calls/30d) but open;
(2) `send_one_email` attachment path is committed but has never sent a real attachment
through Resend — first harness completion exercises it live, loud-fail catches a
payload rejection; (3) ⚰️ run_count=3 medians — **DEFERRED by Mike, same night, on a corrected
measurement**: the run-to-run noise floor is **0.5, not ±1.0** (see the corrected
entry below), and tripling spend to tighten an already half-point floor on a set
with no ground truth buys precision we cannot use yet. **Revisit AFTER CGC books
are in the set, not before.**

**Entry point (calibration blocked on ground truth; not another variant):** after the
capture check above and the two approved contrast fixes, the substantive block is
**the normalizer-pair differential** — the 4-day-old dirty diff needs its corpus
measurement to ship or die, and it is the same file the canonical-"of" fragmentation
fix (CP-1 item 1, 6,815+ unreachable sales, the capture DO-NOT-SEARCH list) lives in.
That is the highest-value engineering NOT blocked on ground truth.

## 2026-08-30 (brand) — 🎨 **BRAND GUIDELINES ARE NOW A DOCUMENT. Decision of record: gold #facc15 IS the brand (Mike). SOURCE OF TRUTH: docs/SlabWorthy_Brand_Guidelines.md.**

- **Canonical-source rule:** the repo .md governs; the .docx is the human copy; the
  project-storage mirror (claude/SW_BRAND_GUIDELINES.md) is DO NOT EDIT. Brand changes
  land in the repo .md FIRST and mirror outward. Never restate the palette elsewhere —
  point at the doc. (The old CLAUDE.md fragment vs styles.css drift is the reason.)
- **Done, uncommitted:** .docx→.md conversion (verified: hex multiset identical 40/40,
  all 60 paragraphs verbatim, 4 tables, chrome-print fence intact; ONE addition
  disclosed — a provenance blockquote under the Status line encoding the mirror rule);
  `--brand-gold: #facc15` added to styles.css :root (TOKEN ONLY, deliberately
  unapplied — where gold appears in the UI awaits Mike's taste call); CLAUDE.md brand
  fragment replaced with a pointer (frontend change → purge on ship, no deploy).
- **Wordmark sweep ("SLAB WORTHY" missing the $), report only:** ONE live user-facing
  hit — **routes/waitlist.py:80**, the waitlist email H1 renders "SLAB WORTHY™"
  (gold, but no $). Rest: internal docs/comments/console banners + archive/. HTML
  surfaces clean — the 2026-07-29 footer fix held.
- **Purple contrast audit (3.3:1 on dark, AA body needs 4.5:1), report only — NOT
  empty, live a11y issue:** worst = `.defect-area-label` styles.css:2003 (0.65rem
  purple labels on the grading report, every grader sees it); site-wide footer links
  styles.css:894 (0.9rem); `.back-link`/`.serial-tag`/`.response-btn.active`
  sightings.html (0.8-0.9rem); `.sell-dropdown-manage` 0.7rem, `.comics-list
  .comic-grade` 0.9rem, `.bulk-count`, `.btn-draft` (collection.css + ebay modal);
  `.details-toggle.active` 0.85rem; `.auth-link:hover` 0.85rem. Mike to decide.
  Exempt-ish: defects-list bullets (markers), the 11px ✏️ icon (non-text, 3:1 ok).
- Not on the critical path; grading calibration work unaffected.

## 2026-08-30 (night) — 🔧 **MATCHER NEGATION BUG FIXED; VARIANT A = NULL RESULT; 2 of 3 run records LOST to a pod recycle; auto-persistence added.**

**MOST RECENT CHANGE (Rule 5): three runs happened tonight (baseline ×2 + variant A);
the pod recycled after an env change and destroyed two records. Baseline 1 was recovered
from email → `scripts/regrade_run_20260830_2006_baseline.json` (normalized from a Yahoo
webmail save: 301 bytes of mail chrome stripped, CRLF→LF; verified 36 books,
cost_usd 1.186404). VARIANT A IS A NULL RESULT (Mike): passing the year moved nothing
beyond the noise floor, ceiling unchanged (two books at 9.0, none above, all three runs).
Next hypothesis: compression comes from the rubric itself — RULE 5 + universal flags +
conservative tiebreak. Supporting shape: book 53 grades 3.5 on raw weighted 3.48 with
structural/interior at 5.5 against spine 2.5.**

- **Matcher bug:** `defect_theme_hits` counted NEGATED mentions ("No visible spine
  stress lines", "rust-free", "No creases, tears, or writing") as defect instances, and
  bare positional nouns ("lower left corner") as corner wear. **Scope verified:
  harness-only** — THEMES/defect_theme_hits exist only in scripts/regrade_harness.py;
  production renders defect strings verbatim (grading.py:890-893 → app.html
  resultDefectsGrid), no theme-matching in any user-facing path. NOT a user-facing bug.
- **Fix (verified 17/17 unit + 8/8 pipeline):** per-item, clause-aware, negation-aware
  matching — cue window 7 tokens, "-free" suffixes, negation DISTRIBUTES across
  comma-enumerations, corner wear requires a wear assertion, gloss ≠ 'glossy'. Theme
  names/count unchanged. `--report <run.json>` re-derives base rates offline from raw
  defect strings, zero API calls; stored-baseline column labelled legacy.
- **Corrected baseline-1 rates (36 books):** crease 35→25, tear →5, staple rust →9,
  tanning →30. ⚠️ **spine stress stays 35/36 and it is GENUINE** — every fire traces to
  an explicit assertion ("2-3 ticks", "8+ visible"). Not tuned down (L-2026-028). That
  near-universal *asserted* flag is itself the rubric-compression evidence.
- **2026-08-30-morning DB base rates RE-DERIVED** (the originals used the naive
  matcher): pre-1970 claims SURVIVE (oils 92%, tanning/soiling/fading/spine-stress
  100%, crease 97%); the bug had inflated mostly modern/current (current crease
  18/22→1/22, current tanning →0/22) — the era contrast is sharper than reported, not
  weaker. Board-reorder decision unaffected.
- **Persistence (Task 3):** run records now EMAIL themselves via the one repo sender
  (send_one_email.send_email, extended with attachments) to ADMIN_EMAIL from
  RESEND_FROM_EMAIL — automatically on completion, on run-level crash, and on SIGTERM
  (pod recycle). Failure prints a loud unmissable block, never silent, never fatal.
  Email chosen over R2: tonight's sole survivor survived BECAUSE it was emailed; an R2
  object still needs the operator to remember to fetch it. Residual gap: SIGKILL is
  uncatchable (incremental local writes still bound the loss to <1 book of progress).
- **page_quality null (Task 4, report only):** neither (a) nor (b) — the field is
  requested ONLY by Variant C's prompt; baseline/A prompts contain no such field, so
  null on all 36 baseline books is correct-by-design, unrelated to CGC ground truth.
  The COLOR_GLOSS and INTERIOR *categories* (the actual 15% weight) scored on all 36
  books and fed every grade. No inert category exists.

## 2026-08-30 (later) — 📏 **MEASURED PROPERTY OF THE GRADER: run-to-run non-determinism at temperature 0. Not a harness defect. Changes how all harness results are read.**

**⚰️ CORRECTED at session close (Mike): the noise FLOOR is 0.5, not ±1.0.** The
measurement of record is the two identical baseline runs: **6 of 36 books moved by
exactly 0.5, none moved a full step, zero aggregate drift.** The ±1.0 figure that
first stood here conflated two different measurements — variant A's min/max against
the STORED grades (a cross-measurement including whatever the stored runs' conditions
were), not run-to-run noise under identical conditions. Original observation kept for
provenance: id 106 graded 6.0 in the smoke test and 7.0 in the baseline run; Spawn
#77's 8.0/7.0/7.0 remains an unexplained outlier against the 0.5 floor.
Consequences unchanged: **per-book deltas are NOT interpretable; the measurement is
the aggregate mean across the 36-book set; the fresh double-baseline is essential,
not precautionary.** A single book moving 0.5 between runs is noise.

**Harness hardening after the first baseline run crashed at book 10/36 (~$0.28 spent,
9 books' results lost):** cause was `media_type` hardcoded to `image/jpeg` while id 9's
retained photo is PNG — pre-2026-07-16 submissions retain ORIGINAL phone bytes; prod
never hits this because /api/grade re-encodes everything to JPEG via
normalize_for_photo_type (grading.py:667). Fixed by MATCHING PROD (normalize-first,
same GRADING_MAX_LONG_EDGE, so harness pixels = prod pixels) with magic-byte sniffing
(PNG/JPEG/GIF/WebP/HEIC) as fallback; HEIC/unidentifiable → per-book skip. Plus:
per-book failures no longer kill the run (skip, log, list in report), and the run
record is rewritten atomically after EVERY book so a crash leaves a usable partial.
Stub-verified offline 13/13. New `--preflight` mode (zero API spend) checks all 36
photo sets' fetchability + real media types — run it in the Render shell before the
next paid run. The 9 crashed books' results are unrecoverable (end-only write);
baseline restarts from scratch, ~$1.13.

## 2026-08-30 — 🧪 **RE-GRADE HARNESS BUILT (measuring instrument, not fix). Rubric untouched. Board reordered: era-blind grading now outranks comp-set purity (Mike).**

**MOST RECENT CHANGE (Rule 5): grading-rubric findings landed 2026-08-30 — page colour
feeds the numeric grade (COLOR_GLOSS 10% + INTERIOR 5%), zero era handling, defect flags
at 92-100% base rate on pre-1970 books, and a hard 9.0 ceiling across all 138 submissions
(no grade above 9.0 ever assigned). Mike's call: DO NOT tune the rubric without ground
truth — undergrading loses an opportunity, overgrading costs a user $105+shipping. First
unit = the measuring instrument. Supersedes any plan that opens CP-1 work on canonical
fragmentation; grading is upstream of valuation and the defects multiply.**

- **Built, verified offline 16/16, NOT committed:** [scripts/regrade_harness.py] +
  [scripts/regrade_eval_set.json]. Fixed 36-book eval set (14 pre-1970 / 10 bronze /
  7 modern / 5 current, all 4-photo, near-duplicate 1988 cluster ids 54-67 excluded).
  Variants are prompt TRANSFORMS in the harness — grading_engine.py untouched; baseline
  = exact prod prompt. Variant A: +publication year (request already carries it,
  grading.py:900; it just never reaches the prompt). B: era-conditional baseline
  language. C: brittleness unbundled from paper colour, page_quality captured
  report-only. C fails loud if the prod prompt's anchor text changes.
- **Cost, measured basis: ≈ $1.22 per 36-book variant run** (7,100 in / 850 out per
  4-photo grade at claude-sonnet-4-6). Dry-run is default; --run required; ledger
  append instructed in-tool. Runs in the Render shell (needs ANTHROPIC_API_KEY + R2).
- **⚠️ Set survival:** images_purge_after on the set spans 2026-10-09→11-26, BUT the
  auto-purge job is DEFERRED/UNBUILT (grade_retention.py:12) and `pinned` has NO
  consumer (admin display only) — pinning is forward protection, not current
  protection. Mike to run: `UPDATE grade_submissions SET pinned = TRUE WHERE id IN
  (manifest ids);` and the future purge job MUST exempt pinned rows.
- **cgc_grade slots** in the manifest for externally-graded ground truth (pursued
  separately); harness reports error-vs-truth when populated.
- **RULE 5 reconciliation (report only, not implemented):** nothing reconciles "every
  defect must reduce its category score" with flags firing on 100% of an era —
  together they guarantee era-normal traits reduce the grade. Assessment: fix belongs
  in the ERA BASELINE (variant B's shape), not in weakening rule 5 (defects must stay
  tied to scores) nor in flag suppression (hides real information).

---

# Where We Left Off - Aug 28, 2026

## 2026-08-28 (SESSION CLOSE) — 🔴 **GATING UNIT COMMITTED + PUSHED, NOT DEPLOYED. DEPLOY IS BLOCKED on one unfinished verification. Plus: a storage-quota incident with an UNVERSIONED console mitigation, and two new units.**

**MOST RECENT CHANGE (Rule 5): both gating commits are IN — `ea6a0c5` (server:
auth.py + the two route files) and `eeed129` (extension: collectioncalc.js +
manifest 2.43.0) — committed and pushed by Mike, 2026-08-28. Supersedes the
"NOT COMMITTED" line in the entry below. `deploy` has NOT been run and MUST NOT
be run until the gate immediately below clears.**

### ⛔ THE DEPLOY GATE — open, and it is the only thing between here and done

**The `X-Operator-Key` header has never been observed on a live fmv request.**
Extension side is otherwise complete: `operatorApiKey` confirmed present in
`chrome.storage.local` (length 20), extension reloaded, chrome://extensions
reads **2.43.0**. The DevTools observation of the header on a real Whatnot fmv
call was interrupted by the quota incident below and **not resumed**. Until
someone sees that header on a real request, the pre-gate server (which ignores
it) is the only safe deployed state. **Resume point: open a Whatnot live page →
DevTools Network → confirm `X-Operator-Key` on an fmv request → then `deploy`
(backend-only, no purge) → post-deploy curls per the entry below.**

### 🟠 INCIDENT — extension storage quota, manually mitigated, mitigation UNVERSIONED

`background.js` threw `Resource::kQuotaBytes quota exceeded`.
`chrome.storage.local` was at **10,475,267 of 10,485,760 bytes**; `salesHistory`
held 10,292,320 across **367 entries**, of which **94 carried a base64
`imageDataUrl` totalling 10,128,598 bytes — 98.4% of the blob.** Capture itself
was NOT failing: `[BG] Sale recorded` logged immediately before each throw —
the failure was the LOCAL write after successful server recording.

**Mitigation applied via the service-worker console, NOT in code:** every
entry's `imageDataUrl` set to null, all 367 entries and their dedup value
preserved. Usage → 347,647 bytes. ⚠️ **This is an unversioned console change.
It does not exist in the repo, will not survive a fresh profile, and will not
reproduce for anyone else.** The durable fix is New Unit 2.

### 🆕 NEW UNIT 1 — box lots recorded as comics (HIGHER PRIORITY of the two)

Observed live and in `salesHistory`: `rawTitle: "Box #18"` parsed to
`title: "Box", issue: 18, platform: "whatnot"`, price 25; console showed
`[BG] Sale recorded: Box - $50`. Also `"AAA) Random Raw Comic as shown"` at $3.
**This creates plausible-looking fake series keys, not obvious junk.** Two
questions to answer BEFORE proposing a fix:
1. Does anything in `/api/sales/record` or downstream reject a payload of this
   shape? (Nothing obvious does — the handler normalizes and INSERTs — but
   answer it by reading the path, not from this parenthetical.)
2. How many rows already in `market_sales` arrived this way? That count decides
   go-forward-only vs also-a-cleanup.
Related to the known Whatnot normalization item, but that item's framing —
"contributes no depth" — **understates this**: it is not just useless rows, it
is fake keys.

### 🆕 NEW UNIT 2 — salesHistory grows without bound

94 images in ~6 months ≈ 108 KB each ≈ **1.7 MB/month → the 10 MB wall returns
in ~6 months.** ⚠️ **Do NOT fix with `unlimitedStorage`.** Likely correct fix is
NOT eviction either: once an image has been sent to the server it has no reason
to persist locally — **null `imageDataUrl` after upload** rather than capping
the list. **Prerequisite: confirm what consumes `imageDataUrl`** before
deciding; do not assume it is write-only.

### 🔒 SECURITY ITEM — reported this session, DO NOT act (no rotation, no removal)

`anthropic_api_key` (110 bytes) sits in the extension's `chrome.storage.local`.
Findings, grep of the whatnot-valuator source with a positive control (the same
probe finds the real `operatorApiKey` and `openai_api_key` storage reads):
- **Nothing in the current extension reads that storage key.** It is residue of
  the pre-Session-61 era — `lib/vision.js:4` records the migration to the
  backend proxy, and its `loadApiKey`/`saveApiKey` are now JWT-based legacy
  shims. **No code path calls Anthropic directly from the client.**
- **BUT the same sweep found a live direct-from-client third-party AI call:**
  `lib/audio.js:123-150` reads `openai_api_key` from the same storage and POSTs
  audio to `https://api.openai.com/v1/audio/transcriptions` with
  `Authorization: Bearer` — a real client-side secret in active use, unlike the
  dead Anthropic one. Also observed: `api.openai.com` is NOT in the manifest's
  `host_permissions`. Reported only; nothing rotated, removed, or changed.

### 📋 FOLLOW-UP GATING UNIT — entry task defined, not started

`/api/sales/count` and `/api/sales/recent` remain ungated; `recent` returns
full `market_sales` rows with a caller-controlled `limit`. **Entry task before
scoping: a complete inventory of every endpoint that reads corpus data, with
its current auth state** — including `/api/sales/valuation`, which is
**anonymous by design** (unauthenticated GET; its own refund docstring says so)
and must appear in the inventory as such, not be assumed covered by the fmv
gate. ⚠️ **The record must not overstate the shipped unit: it NARROWS the
exposure, it does not close it.**

---

## 2026-08-28 (later) — 🟡 **OPERATOR-KEY GATE ON /sales/record + /sales/fmv: BUILT AND OFFLINE-VERIFIED, NOT COMMITTED. Rollout order matters — extension first, then deploy.**
**⚰️ "NOT COMMITTED" is DEAD as of session close — commits `ea6a0c5` + `eeed129` are in and
pushed; deploy blocked on the header-observation gate. See the SESSION CLOSE entry above.**

**MOST RECENT CHANGE (Rule 5): both sales endpoints now require credentials in the working
tree — `/api/sales/record` requires `X-Operator-Key` (env `OPERATOR_API_KEY`, already set on
Render), `/api/sales/fmv` accepts the key OR a logged-in user. Supersedes the roadmap's
"ungated" description once shipped. NOT yet committed/deployed — and unlike F, this defect
WAS verified still live in prod (2026-08-28) before building: anonymous fmv returned 200
with full tiers; an invalid-JSON probe on record reached the handler (Flask 400, no row
written), proving no gate in front of it.**

- **Files:** `auth.py` (`operator_key_status()` — X-Operator-Key header, per-request env
  read like the Stripe webhook secret, `hmac.compare_digest`, 4-state: ok/invalid/absent/
  unconfigured), `routes/sales_market.py` (require key; 60/5min/IP limiter),
  `routes/sales_valuation.py` (key OR `g.user_id`; separate 120/5min service and 30/5min
  user buckets; invalid key rejected loudly, no fall-through),
  `CCExtensions/whatnot-valuator/lib/collectioncalc.js` (sends the header; key from
  `chrome.storage.local.operatorApiKey`, NEVER a repo file) + manifest **2.42.2 → 2.43.0**.
- **Verified offline: 20/20** positive-controlled checks (scratchpad harness) — every gate
  blocks AND passes, 503 self-report on unconfigured env, limiters fire at N+1, buckets
  independent. No DB/network touched.
- **⚠️ ROLLOUT ORDER (zero capture downtime):** commit+push → set key in extension storage
  → reload extension, CONFIRM 2.43.0 in chrome://extensions → confirm header visible in
  DevTools on a Whatnot page (pre-gate server ignores it) → THEN `deploy`. Backend-only:
  no `purge`. Post-deploy: anonymous fmv curl → 401; keyed fmv curl → 200; record proven by
  the next real human-triggered capture returning `success:true`.
- **Flagged, not built:** `/api/sales/count` and `/api/sales/recent` remain unauthenticated
  (recent dumps full `market_sales` rows, caller-controlled limit) — the extension calls
  both, so gating them is the same header wiring, a follow-up unit. `/api/sales/valuation`
  stays public deliberately (website product surface). No API-key pattern existed in the
  codebase to reuse (searched); the limiter reuses the images.py/monitor.py pattern.
- Earlier same day: `2870749` (app.html extension-claim retirement) committed by Mike.

## 2026-08-28 — ✅ **IMPLAUSIBLE-COMP GUARD: ALREADY SHIPPED AND LIVE. Task closed as verification, not build.**

**MOST RECENT CHANGE (Rule 5): the X-Men #1 implausible-comp defect NO LONGER REPRODUCES —
the multi_edition guard is committed (`f7cd04a` at HEAD) and deployed (prod version 5.6.0),
verified live 2026-08-28. Supersedes any task framing that treats the guard as unbuilt,
including the framing this session opened with.**

⚠️ **WHY THIS ENTRY MATTERS MORE THAN ITS CONTENT:** the guard was scoped as new work because
this file's newest entry was 2026-08-12 and `CP1_STATE_OF_PLAY.md` still says "nothing has
been fixed." The guard shipped in sessions after those files were last written
(`499371b` → `9ab7cc3` → `f7cd04a`) and the state record never caught up. A stale state file
re-issued an already-completed unit — the exact failure the STATE-RECORDING PROTOCOL exists
to prevent, arriving via omission rather than a stale plan.

### Verified live, 2026-08-28 (read-only; production `collectioncalc-docker.onrender.com`, v5.6.0)

- **X-Men #1 @ 9.0:** `graded_fmv: 36.0` (unchanged — the guard suppresses the verdict, it
  does not invent a number), `verdict_reliable: false`, `verdict_basis: "multi_edition"`,
  `edition_span: true`, `edition_price_ratio: 86.8`, verdict text = the hedge. `fmv_method`
  = `exact`, so the gate condition matched as designed.
- **Negative controls, all normal:** ASM #300 @ 9.4 → $666 supported/reliable · New Mutants
  #98 @ 9.0 → $300 supported/reliable · Hulk #181 @ 5.0 → $2,625 supported/reliable. All
  three: `edition_span: false`.
- **Observed, not changed:** the refused X-Men response still carries `confidence: "high"`.
  The guard is verdict-affecting only (deliberate per the comment at
  `routes/sales_valuation.py:1144`); whether the confidence label should also be suppressed
  is an open design question for the CP-1 display-consolidation item, not a defect in this unit.
- The shipped design matured past the originally-scoped whole-range rule (15y span AND 20×
  ratio): per-split gap test, cluster floor of 3 per side, best-ratio split reported. The
  3-of-3 precision measurement is superseded by the wider one recorded in the code comments:
  481 production-shaped cells, 6 fire, 0 false positives. Tombstone for the whole-range
  version is in `_detect_multi_edition` itself.

### Second unit, done this session: app.html false extension claim retired

`app.html:1346` "Our Chrome extension flags candidate eBay listings for you to review" —
same never-published-extension claim retired from `faq.html` on 2026-08-26 (`1bc4b58`), on
the higher-traffic surface. Replaced with the live capabilities (photo check + sighting
alert), tombstone comment in place. **Edited in working tree, NOT committed — Mike stages,
commits, purges** (frontend-only: no `deploy`). Positive control run pre-edit: old string
served live (1 hit), new string absent (0), so the post-purge check can assert both
directions.

### Also this session (session-open triage, Mike's 2026-08-26 instruction)

Cold-read classification of the dirty tree — **nothing staged**:
- `title_normalizer.py` — `by <Creator>` strip repair (`processor=str.lower` on the skip-check
  only + " by "-in-matched-title requirement). Finished-looking; **corpus differential for
  this exact diff not evidenced** — L-SW-2026-027 says measure before staging.
- `scripts/backfill_canonical_titles.py` — SOURCE DRAIN report (FULL vs PARTIAL, split
  warning). Finished.
- `docs/EBAY_CAPTURE_WEEKLY.docx` — binary, untriaged, left alone.

---

## 2026-08-12 — 🟠 **JOSEPH VICARIO PHOTO BACKFILL: SCOPED, SCRIPT WRITTEN, NOT RUN.**

**MOST RECENT CHANGE (Rule 5): the Vicario recovery is 20 rows, not 21, and the two rows
that "did not resolve" were never ambiguous. Re-measured 2026-08-12 against live data.
Supersedes the 2026-08-06 diagnosis in every figure below.**

⚠️ **THIS ENTRY EXISTS BECAUSE THE LAST ONE DID NOT.** The 2026-08-06 diagnosis — a real
user, 100% photo loss, a hard 2026-11-04 purge deadline — was **never written to any file**.
`grep -i vicario` across the entire repo returned **zero** on 2026-08-12, six days later. It
survived only in conversation. That is a **Rule 4 violation** (log the decision when it is
made, not when the arc closes) on the single item in the project with an external deadline
and a named human attached. Recorded at Mike's direction: *"the state-recording gap is yours
to close."*

### THE INCIDENT

`user_id 38`, `vicariojoseph.jv@gmail.com`, signed up 2026-08-05 23:23 UTC. Between
**01:22 and 03:51 UTC on 2026-08-06** he saved **21 comics**; every one carries exactly
`{"back": null, "front": null, "spine": null, "centerfold": null}`. 100% of his collection
has no photos and the app reported success on all 21 saves.

**Mechanism (measured, not inferred):** of 90 `/api/images/submission` calls — **69× 400,
11× 500, 10× 200**. The ten 200s took **52–85 seconds**, every one past `app.html`'s 30s
`Promise.race` upload timeout. The browser had already given up and saved all-null while the
server went on to succeed. *The save genuinely succeeded; only the photo URLs were abandoned.*

### CORRECTED FIGURES — re-measured 2026-08-12

⚰️ **DEAD: "19 of 21 resolve, rows 95 and 96 need disambiguation."**
**REPLACED BY: 20 recoverable, 1 permanently lost, 0 needing disambiguation.**
**REASON:** two independent errors in opposite directions.

| | 2026-08-06 | measured 2026-08-12 |
|---|---|---|
| collections rows | 21 | 21 ✓ |
| grade_submissions | 25, 24 with photos | 25, 24 with photos ✓ |
| resolve to one candidate | 19 | 19 ✓ |
| **actually recoverable** | *(not stated)* | **20** |
| objects | "84" | **64 source read · 80 written · 20 rows updated** |

- **Collection 89 (Captain America #6) is UNRECOVERABLE.** It resolves cleanly to submission
  46, whose `photos` column is **NULL** — the persist thread inserted the row and died before
  the photo-backfill `UPDATE`. The row asserts `photos_used = 4` and a populated
  `photo_labels`; **both are true statements about what the GRADER consumed and neither is a
  claim about what was STORED.** Instance of **[[L-SW-2026-016]]** in the retention layer. Any
  matcher keying on those fields writes four broken URLs. **Key on the `photos` jsonb only.**
- **Rows 95/96 were a window artifact, not an ambiguity.** Submission 50 is the *only*
  Daredevil submission in all 25 rows and the last grade of the session. Collections 93/94/95/96
  are four **Save clicks on one grade report**, 45/124/201/252s later, agreeing on title, issue,
  publisher (`Marvel`), year (`1983`), grade (`8.0`) and confidence (`94`). The ±3min window was
  simply too narrow. Same shape resolves 92 → 48 (Strange Academy).
- **The mapping is not a bijection:** sub 48 → 2 rows, sub 50 → 4 rows. **Mike's call
  2026-08-12: reconstruct faithfully — four identical Daredevil covers.** Had the uploads
  worked, each save click would have uploaded its own copy under its own `grading_id`.
  Per-row prefixes, not shared objects. To be explained in the message to Joseph.

### THE ARTIFACT

**`scripts/jv_photo_backfill.py`** — written 2026-08-12, **NOT RUN, NOT COMMITTED.**
Dry-run default; `--execute` required. Runs in the **Render shell** (has `DATABASE_URL` +
`R2_*`; local `.env` has only `DATABASE_URL_RO`). Backend-only → **`deploy`, no `purge`.**

Design: copies to **NEW `submissions/{grading_id}/{label}.jpg` keys**; `collections.photos` is
never pointed at a `grade_submissions/` key — the two key spaces stay disjoint because the
purge job's safety depends on it and nothing enforces it. Label map
`front_cover→front`, `back_cover→back`. Per-row transactions, R2 first, DB commit last.
Guards: `user_id = 38` + explicit 20-id literal + `photos NOT LIKE '%http%'` (which is what
makes a re-run safe). Positive-controlled R2 probe (**[[L-2026-024]]**) and a public-URL base
**derived from a healthy row** then cross-checked against `r2_storage` (**[[L-2026-026]]**).
Rollback printed *before* any write. Verified read-only 2026-08-12: 20/20 pairs pass, and a
deliberately corrupted pair (col 75 → sub 26) is rejected — the verifier can return a hit.

### ✅ EXECUTED 2026-08-12 — 20 updated, 0 failed

Mike ran the dry run, then `--execute`, in the Render shell. **70 objects copied, 10 kept
existing, 20 rows updated, col 89 correctly excluded.** Spot-check on a copied URL: 200.
Verified read-only afterwards: all 20 rows at 4/4, every URL prefix matches that row's own
`grading_id`, and **0 rows point at a `grade_submissions/` key** — the disjointness constraint
held. The only remaining all-null collections row in the entire table is col 89.

**🔍 INCIDENTAL FINDING — the KEEP-EXISTING objects are 3–4× LARGER than the sources.**
1.4MB vs 355KB on the Daredevil front. So **rows 93 and 94 carry Joseph's ACTUAL
full-resolution uploads** (his own late-landing 200s, kept rather than overwritten) while
**rows 95 and 96 carry copies of the grader's normalized versions**. Same book, four rows,
**two image qualities**. Recorded rather than smoothed, at Mike's direction — it is faithful
to what happened, and it is **evidence that his originals were large**, which bears directly
on the upload-failure question below: 1.4MB stored implies a much larger base64 body on the
wire from a phone, pre-`85617c6`.

⚠️ **OPERATOR FRICTION, fixed:** the script needed `PYTHONPATH=/app` and the variable does not
persist between invocations, so it failed identically on the first dry run *and* the first
`--execute`. It failed **safely** — nothing written either time — but a step the operator has
to remember is a step that gets forgotten. Now resolves the repo root from `__file__` via the
`_HERE`/`_ROOT` convention already used by `scripts/cp1_*.py`; verified running from a foreign
cwd with no `PYTHONPATH`. Same principle as deriving a value rather than typing it.

### ✅ 2026-08-13 — USER 42 EXPLAINED. THE ROOT CAUSE APPEARS FIXED. **CLAUDE'S ERROR, CORRECTED.**

⚰️ **DEAD: "user 42, 2026-08-11, collection 101 saved with three of four photos null — still
unexplained; the next user is still exposed."** Stated by Claude repeatedly on 2026-08-12,
including **in the body of commit `3c28da5`**, and used as the reason Joseph could not be told
the bug was fixed.
**REPLACED BY: there was never a failure. `sub 69` has `photos_used = 1` and one key,
`front_cover`. User 42 uploaded ONE photo.**
**REASON:** `app.html` initialises `photoUrls` with all four slots null and fills only the ones
that have a photo, so `{front: URL, back: null, spine: null, centerfold: null}` is the **correct**
result of a one-photo save. His entire request history is **100% HTTP 200 — zero failures of any
kind.** 8 of his 9 grade submissions are `photos_used = 1`; single-photo grading is simply how he
uses the product.
**SUPERSEDES** any statement that the upload bug survived `85617c6`. Do not re-raise it.

⚠️ **THE ERROR IS THE LESSON: absence read as failure, without establishing that the probe could
tell "upload failed" from "no photo was ever taken."** That is **[[L-2026-024]]**, committed by
Claude, three times, in the same week the same rule was being applied correctly elsewhere. The
disproof was one column away — `photos_used` — in a table already being queried.

**THE POST-FIX RECORD** (`85617c6`, 2026-08-06 21:50 UTC):

| `/api/images/submission` | before the fix | after |
|---|---|---|
| 200 | 663 (avg 1,553ms) | **14 (avg ~800ms, max 1,179ms)** |
| 400 | **81 (avg 19,828ms)** | **0** |
| 500 | 11 | **0** |

**Three four-photo saves have completed since the fix — users 3, 39 and 42 — all 4/4, all 200,
every photo under 1.2s.** That is the exact shape that failed for Joseph, whose 400s averaged
**twenty seconds**.

⚠️ **NOT PROOF. n=3, on unknown networks.** The honest position: **no known unexplained photo
loss exists anywhere in the system**, and the failing shape now succeeds. Cols 29 (2026-02-14)
and 65 (2026-06-15) are partial but **predate the earliest `grade_submission` in existence
(2026-06-27)** — no retained source exists, so they are **unmeasurable, not unexplained**; do not
count them either way. The 10 `user IS NULL` rows on that endpoint are **OPTIONS preflight**
(396 overall, 0ms), not a hidden failure population.

**✅ THE NEW INSTRUMENTATION IS CONFIRMED WORKING FROM PRODUCTION DATA, not from the deploy:**
`error_message='non-json-404'` with `response_summary` carrying the Werkzeug HTML — the exact
text that used to be discarded — plus `request_size_bytes` on **2,311 of 2,458** requests since
deploy, including `req=2190265` on the verified 429.

### ⚠️ THE ROOT CAUSE IS NOT FIXED — *superseded 2026-08-13, see above*

`85617c6` (upload resize, 2026-08-06 **21:50 UTC**) landed **7 hours after Joseph's last
visit** — he never saw it. It has **not** been shown to close this: **user 42, 2026-08-11,
five days later, collection 101 saved with three of four photos null.** Do not tell Joseph it
is fixed. The 400-branch hypothesis (truncated request bodies from a mobile uplink) is
**bounded but not closed**: moderation is ruled out by evidence — `content_incidents` has
**zero rows for user 38** and the blocked path logs before returning 400 — but
`request_logs.error_message` and `response_summary` are **NULL on all 80 failures**. The
endpoint records that it failed and not why (**[[L-SW-2026-007]]**).

### 🔬 `/api/images/submission` INSTRUMENTATION — the NULLs were a discarded answer

⚰️ **DEAD: "the endpoint records that it failed and not why."**
**REPLACED BY:** `after_request` *was* capturing the reason and **throwing it away** for any
response whose body was not JSON. **REASON:** `wsgi.py` read `response.get_json()` and took
`data.get('error')` under a bare `except: pass`. Werkzeug's own 400/413/415 pages are **HTML**,
so every framework-level failure logged NULL while route-level failures logged fine.

**The positive control that makes the NULLs evidence (L-2026-024):** the logger demonstrably
works — `/api/grade` 429s on **the same account, the same night** logged
`error_message='monthly_limit'`, and 145 of 267 4xx table-wide carry a message. Since **all
four** reject branches in `api_upload_submission_image` return `jsonify({'error': ...})`,
a NULL on all 69 of Joseph's 400s proves **none of them came from that route**. Combined with
**zero `content_incidents` rows for user 38**, moderation is excluded twice over. The 400s were
raised by `request.get_json()` before the handler.

Shipped:
- **`wsgi.py after_request`** — falls back to the response body (≤1000 chars) into
  `response_summary` with `error_message='non-json-{code}'` when no JSON `error` key exists;
  now also records **`request_size_bytes`** (`request.content_length`) and
  `response_size_bytes`. ⚠️ `response_summary` had been written on **0 of 220,399 rows** — a
  column `log_request()` accepts and nothing has ever passed ([[L-SW-2026-018]]).
- **`routes/images.py`** — `get_json(silent=True)` keeps the failure **inside** the handler so
  it can self-report ([[L-SW-2026-007]]) instead of becoming an anonymous Werkzeug page; logs
  **declared vs received bytes** and a `truncated=` flag, which is the direct test of the
  mobile-uplink hypothesis. Greppable `[IMG-SUBMIT]` prefix. Moderation and R2 legs timed.
- ⚠️ **BEHAVIOUR CHANGE, deliberate:** an R2 upload failure used to return **HTTP 200**
  carrying `{'success': false}`. `request_logs` only sees the status, so **every R2 failure was
  recorded as a success** and was structurally invisible to exactly this investigation. Now
  **502**. `app.html` checks `uploadResult.success`, never `response.ok`, so client behaviour
  is unchanged.

⚠️ **This is observation, not a fix.** It makes the next occurrence self-reporting. The 400
cause remains **inferred**, and user 42 (2026-08-11, col 101, 3 of 4 null) is still unexplained.

### 💸 THE 429 WALL — stale copy that has been refusing money for seven weeks

⚰️ **DEAD: "the 429 has no upgrade CTA."** **REPLACED BY:** it had an **anti-CTA**.
`app.html` rendered *"Want more gradings? Premium plans coming soon!"* with a single
**"← Back to Home"** button — while **Pro has been purchasable since 2026-07-29**
(`COMING_SOON_PLANS = ('dealer', 'guard')`; Pro is the one tier `create_checkout_session()`
will sell). **REASON:** the copy was true when written and nothing re-checked it.
**Joseph saw it seven times across three visits.** Mike, 2026-08-12: *"I have almost no
traffic, so the absolute number is small. The rate is 100%."*

Textbook **[[L-SW-2026-020]]** — correct code, correct mechanism, false label, no test could fail.

**What the refusal already knew and never said:** `routes/grading.py:547` selects
`plan, is_admin, gradings_this_month, gradings_reset_date` and derives the limit from `PLANS`.
Plan, usage, limit and reset date were all in hand; only `limit`/`used`/`resets_at` were emitted.

Shipped (Mike's three answers: **name the number not the tier · keep the reset date but
subordinate it · never show Guard**):
- **`routes/billing.py`** — `next_purchasable_upgrade(plan_key, limit)` returns the **cheapest
  tier the user can ACTUALLY BUY** that raises their cap. Filters on the same
  `COMING_SOON_PLANS` constant that `create_checkout_session()` refuses on, so an unbuyable
  tier **cannot** be advertised at the moment of purchase intent — the failure mode is deleted
  rather than watched ([[L-SW-2026-019]]). Verified with a negative control: temporarily
  removing `guard` from the set makes a Pro user's offer appear and a free user still get Pro
  (cheapest wins); restoring it returns `None`.
- **`TRIAL_PERIOD_DAYS = 14`** — was a bare literal in `create_checkout_session()`. The moment
  a trial length is quoted to a user it becomes a **claim**, and two copies drift silently.
- **`routes/grading.py`** — the 429 body now carries `plan` and a derived `upgrade` object.
  Wrapped so a derivation failure degrades to the previous shape, never a 500 on the cap path.
- **`app.html`** — *"You've used all 25 gradings this month"* → **"75 more gradings this
  month · Free for 14 days, then $4.99/month. Cancel anytime."** → button **"Get 75 more
  gradings"**. Reset date kept, subordinated: *"Or wait — your gradings reset on Sep 01."*
  Exit is now **"Back to my collection"**, not "Back to Home". Every number interpolated from
  the server; **if `upgrade` is null the offer block renders as nothing at all** (omit over
  assert). `startCapCheckout()` goes **straight to Stripe Checkout**, not `/pricing.html` —
  and uses the `checkout_url` response key (**not** `url`; the wrong key fails silently into
  the generic alert, indistinguishable from a decline).

**🐛 FOUND IN PASSING, AND IT IS THE OTHER HALF OF THE WALL:** `routes/grading.py` referenced
**`MONTHLY_GRADING_LIMIT`, deleted by `bfd231c` (2026-06-18)** when the per-tier cap landed —
inside a bare `except Exception: pass`. The `NameError` was swallowed, `result['grading_usage']`
was never set, and `app.html`'s **"N of 25 free gradings remaining this month" counter has not
rendered for ~8 weeks** (it is guarded by `if (counter && text && usageData)`). *The cap arrives
as a surprise because the only forewarning the product has was silently dead.* Fixed to read
per-tier from `PLANS`; the bare `except` now logs.

**"Coming soon" sweep (Mike: "if it is wrong in one place it is likely wrong in others"):**
run across all rendered HTML/JS. **`app.html:2434` was the only false instance.** Every other
hit is accurate — Signature ID, Market Pulse, Price Lookup, unbuilt export/bulk-delete, the old
`collectioncalc.html` landing page. `pricing.html` is **correct**: Pro sells via
`startCheckout('pro')`; Guard and Dealer are roadmap entries routed to `/contact.html`.
**Tombstoned per [[L-SW-2026-014]] so the next sweep does not re-raise it: pricing.html's
tier copy was investigated 2026-08-12 and found correct. Do not "fix" it.**

### 🎭 FIX F — EDITION SPAN (BUILT + VERIFIED 2026-08-13, NOT SHIPPED)

**THE CASE:** X-Men #1 at grade 9.0 returned **$36.00** with `verdict_reliable` TRUE and confidence
HIGH, on a six-figure book. Both the 1963 and 1991 volumes carry `canonical_title = 'X-Men'`, so
branch A pools them and 242 comps at a $71 median outvote 27 at $6,100.

⚠️ **WORSE THAN THE INFLATION CASE.** Wolverine #181 at $6,735 was inflated, and a user holding a
common book might sanity-check it. This is **DEFLATED on a genuine key**: $36 looks plausible, the
verdict is confident, and the user walks away from a six-figure comic.

**Design (settled across two prior sessions, not relitigated):** between-cluster not within-grade;
**both** signals required (year span AND price ratio, each rejecting the other's false positive);
gated on `fmv_method == 'exact'`. The gate is the design — every other tier is already hedged, so F
can only fire where a confident verdict would otherwise escape, and `exact` guarantees ≥3
same-grade comps for the string to name.

### ⚰️ THE FIRST IMPLEMENTATION DID NOT FIRE ON ITS OWN CASE

⚰️ **DEAD: "split at the single widest year gap, after a whole-range span test."**
**REPLACED BY:** evaluate **every** candidate split; fire if any qualifies.
**REASON:** X-Men #1's years are `1963:n=27 · 1990:n=4 · 1991:n=242 · 2021:n=1`. The real boundary
1963→1990 is a **27**-year gap splitting 27/247 at 84.7× — a clean fire. But **1991→2021 is
THIRTY years**, so the split landed there, produced a high cluster of exactly **one comp**, failed
`MIN_EDITION_CLUSTER_COMPS`, and returned False. **The size floor rejected the whole detection
rather than the bad split.** A single $110 eBay row disarmed the hedge on a six-figure book.

⚠️ **AND BATMAN #423 HAS THE IDENTICAL STRUCTURE** — a lone 2022 row wins its gap — **and returned
the DESIRED answer by accident rather than by mechanism.** A verification that only checked
outcomes would have read that as evidence the code worked. This is why the sweep reported
candidate splits and cluster sizes rather than booleans.

**The year test also moved, and it is a correctness change:** from a precondition on the whole
dated range to **the gap at the candidate split**. Whole-range span answers "does this pool cover a
long period", true of nearly any long-running title; the gap at the split answers "are these two
groups separated in time", which is what between-cluster means.

### ✅ VERIFICATION — same-snapshot A/B is the decisive result

The corpus grew measurably mid-verification (ASM #300's pool 405→461 in about an hour), so absolute
counts are snapshot-dependent and old-vs-new could not be compared across runs. The old rule was
reconstructed verbatim and both were run over **one snapshot**, 481 production-shaped
`(canonical_title, issue_number)` cells with ≥6 dated comps:

```
FIRES UNDER NEW ONLY (1):  X-Men #1  84.7×  boundary 1963|1990
FIRES UNDER OLD ONLY (0):  none
FIRES UNDER BOTH   (5):  ASM #1 · Avengers #1 · AF #15 · Invincible #1 · Daredevil #1
                         — identical ratios to the decimal
```

**The entire added risk surface is one cell, and it is the cell the change was written for.**
Six fire, **zero false positives**, every one genuinely multi-volume.

| book | grade | expected | actual |
|---|---|---|---|
| X-Men #1 | 9.0 | withhold | ✅ **84.7× on 1963\|1990** |
| ASM #300 | 9.0 **and** 9.8 | unchanged | ✅ **zero candidate splits** — no gap in 1988–2006 exceeds 15y |
| Absolute Batman #1 | 9.8 | unchanged | ✅ zero candidate splits (2024–2026, largest gap 1y) |
| New Mutants #98 | 9.8 | unchanged | ✅ single year 1991; no gap exists |
| Spider-Man #1 | 9.8 | withhold | ❌ **STILL MISSES** — see below |

⚠️ **ASM #300 is now SAFER, not merely still-safe.** Under the old rule it passed the whole-range
precondition (2006−1988 = 18 > 15) and was saved downstream by a 1.6× ratio. Under the new rule it
is rejected **earlier**, on time-separation itself. Same for Absolute Batman #1 and New Mutants #98.

**F changes the confidence label, not the number.** X-Men #1 @9.0 still returns $36.00 — now marked
unreliable rather than confident, with ROI withheld.

### ❌ OPEN: SPIDER-MAN #1 @9.8 STILL RETURNS $110.00 CONFIDENTLY

One of the six acceptance criteria **fails**. Its pool has exactly one candidate split
(`1990|2009`, gap 19y) at a **4.4×** ratio — the corpus contains no ≥20× discontinuity among its
year-known comps. **This is a data/threshold question, not a split-selection one, and this change
cannot fix it.** Whether the expectation or the mechanism is wrong is undetermined and was not
guessed at. Not a regression: F leaves this cell exactly as it already was.

### ⚠️ OPEN: THE CONSTANT'S JUSTIFICATION DOES NOT REPRODUCE

`EDITION_PRICE_RATIO = 20.0` carried the argument *"AF #15 (26.9×) and Batman #423 (22.3×) sit
close to the line, so a downward move reaches real single-edition books quickly."* Measured with
the shipped matcher: **AF #15 = 185.5×**, **Batman #423 does not fire**, **X-Men #1 = 84.7× not
422×**. May be methodology rather than error — the difference was deliberately **not** reconciled,
and the agent stated its exact pool construction so the two are comparable. **Nothing sits near 20×
in any measurement taken.** The comment now records both sets and marks the argument unverified;
do not move the constant on the strength of it. What IS measured is the constant's *effect*: 6/481
cells, zero false positives.

### 🐛 CAUGHT IN REVIEW, BEFORE SHIP

- **The long string was FALSE.** *"These 12 sales at grade 9.0 span more than one edition"* — the
  span is detected across the **whole pool**, and X-Men #1's grade-9.0 bucket is 4×1991 plus 8
  year-unknown with **no 1963 sale in it at all**; its span is zero. The sentence attributed the
  span to the sales it named. Rewritten to lead with the problem and claim only that the named
  sales *may be any mix*. Short form corrected the same way.
- **`to_float` is a CLOSURE, not a module function** (defined inside `get_valuation()`), so the
  module-level detector calling it was a request-time `NameError` that `py_compile` passes.
  Converted inline; an AST pass now proves every name in the function resolves.
- **The "checked first" comment asserted disjointness**, so it was verified rather than assumed:
  `estimated = True` is set only where `fmv_method` becomes `'estimated'`/`'estimated_from_raw'`,
  so it cannot co-occur with `'exact'`. The branches are disjoint by construction.
- **Return semantics changed** from whole-range years to boundary years. Consumers audited: only
  `edition_price_ratio` crosses to the client; the years appear solely in the `[VALUATION-F]` log.

### 🔭 THE ARGUMENT FOR AN EXTERNAL SERIES ID

X-Men #1's pool contains **27 genuine 1963 comps at a $6,100 median, outvoted 244 to 27.** The
right answer is *in the pool*, and F **refuses rather than finding it**. That is the clearest
available argument that an external series identifier eventually returns real value rather than
only preventing harm.

### 🧱 CP-1 UNIT 2 — the hedge now survives the save boundary (BUILT 2026-08-13, NOT RUN)

**THE PROBLEM:** every CP-1 hedge held on the grade report and evaporated on save. Superman #76
sits in Mike's own collection (**col 99**) at **$1,815.75** with nothing recording that the figure
came off the **0.25 interpolation floor**.

⚰️ **DEAD: the two-column spec (`verdict_basis` + `verdict_reliable`).**
**REPLACED BY: `verdict_basis` alone.** **REASON:** `verdict_reliable` is **identically**
`verdict_basis === 'supported'` — `sales_valuation.py:736` computes it from
`(estimated_flag, fmv_method)`, and the basis ladder **twelve lines below** assigns `'supported'`
in exactly the else-branch where none of those disqualifiers hold. Same two inputs, same block.
**Two columns can disagree where one cannot:** a client bug could persist
`basis='fabricated', reliable=true` — a state the server cannot produce but the table could hold,
rendering a confident chip over a fabricated reason. Claude argued FOR the second column
originally, on an insurance case that assumed the derivation ran from `verdict` (a genuinely
weaker relation, ambiguous when `roi IS NULL` — 2 of 61 rows are in that cell today). Reversed on
2026-08-13; Mike: *"I was leaning the way you argued me out of."*

**Client-sent, not server-derived.** Re-deriving at save time would consult a corpus that MOVES
(`ebay_sales` 71,652 → 163,374 in three days), so the stored reason could contradict the report
the user acted on seconds earlier — the exact class CP-1 exists to close. Guarded by
`_clean_verdict_basis()` against `VERDICT_BASIS_KEYS`; unknown → NULL. **No CHECK constraint:**
two tiers were added in two days, and coupling tier evolution to migrations is a trap.

**⚠️ CLAUDE'S Q3 CATCH — the original spec was self-contradictory.** "Same strings as the grade
report" + "one column" are **mutually exclusive**: the long-form strings interpolate **five
fields** (`sameGradeComps`, `nearbyThin`, `rawComps`, `excludedVariants`, `gradeLabel`) that a
saved row does not carry. Resolved by sharing the **vocabulary**, not the strings.

**`js/verdict_basis.js`** — `BASIS_KEYS` (8: seven live + `multi_edition`, written ahead of the
edition-span unit), `basisLong(ctx)` (moved verbatim out of `app.html`, ~200 lines of tombstones
intact), `basisShort(basis, {roi})` (parameterless — *a string that cannot state a count cannot
state a wrong one*).

**✅ THE EXTRACTION IS PROVEN, NOT ASSERTED.** The pre-move implementation was sliced out of
`git show HEAD:app.html` — never retyped — and compared against `basisLong` over **33,792 input
combinations** spanning all 8 basis values plus an unknown tier, `null` and `undefined`:
**0 differences**, with a positive control confirming the comparison can detect one.

**One comment had to change and is reported rather than decided** (Mike's standing instruction):
`app.html:2920` read *"REPLACED BY: BASIS_REASONS **below**"*. The map is no longer below — it is
in another file. **Location updated, claim untouched**, with the change itself noted inline.

**🐛 FOUND WHILE TESTING:** `basisShort` conflated *"roi is null"* with *"roi was not supplied"*
(`roi == null` is true for `undefined`), so a caller omitting `opts` would have asserted *"there
are no ungraded sales to compare it against"* — a claim about data it never passed. Now
distinguishes `roiKnown`; unknown ROI on a `supported` row offers **no reason at all**. Defensive
(`collection.js` always supplies it), fixed because the failure mode is an **assertion**, not a
crash.

**Render:** the reason sits behind one tap on the verdict chip, on **all three** chip states —
same argument as showing the chip on every comic: a reason that appears only where something is
wrong makes its **absence** an implicit claim. The affordance appears **only** when `basisShort()`
returns a string; all **61** existing rows (not 59) have NULL basis and render exactly as today,
**no icon** — a disabled one would claim a reason exists and is withheld.

**⚠️ SHIP ORDER IS LOAD-BEARING: THE MIGRATION MUST RUN BEFORE THE DEPLOY.** `/api/collection`
now `SELECT`s `c.verdict_basis`; against a table without the column that is a 500 on the
collection page for every user. Migration is metadata-only (nullable, no default) and takes
`ACCESS EXCLUSIVE` — with `lock_timeout = 5s` it now fails fast rather than blocking the table.
**Confirm autocommit:** an uncommitted `ALTER` holds that lock for as long as the window is open,
taking the whole collection page down rather than one row — a sharper version of the 2026-08-12
hang. Verify from `nlq_readonly`, never from the session that ran it.

### 🏷️ THE STRIPE PRODUCT DESCRIPTION — the surface no sweep can reach

**⚠️ NEW STRUCTURAL FINDING, and it is the reusable one: Stripe-hosted copy is OUTSIDE every
sweep this project runs.** `grep` covers the repo. The Stripe product/price description lives in
the Stripe dashboard, is rendered on the **hosted Checkout page** — the last screen before a
user pays — and **no code sweep will ever find it.** It still carries *"Unlimited comic
valuations with price history and collection tracking"*: the same "Unlimited" claim removed
from `pricing.html` in the **June tier-honesty pass**, which survived precisely because it is
not in the repo.

**Third surface in one family** (Mike, 2026-08-12): `pricing.html` fixed June → the cap screen
fixed today → **Stripe still carrying the original claim.** Same defect as [[L-SW-2026-020]],
one layer further out.

**Audit of the three claims, built from READERS not from `PLANS` ([[L-SW-2026-018]]):**

| claim | verdict |
|---|---|
| "Unlimited comic valuations" | **FALSE.** Pro is **100/month**, hard-enforced at `grading.py:580` with a 429. The only claim the code actively contradicts at runtime |
| "price history" | **NO SUCH FEATURE EXISTS.** The nearest thing is **Market Pulse**, which `js/sidebar.js:461` renders with a `SOON` badge. Zero implementation anywhere |
| "collection tracking" | **TRUE — but not a Pro differentiator.** Free users get the full collection |

**ENTITLEMENT TABLE — 12 keys in `PLANS`; Pro differs from Free on 5; only 3 are enforced.**

| capability | free | pro | enforced? | the reader |
|---|---|---|---|---|
| Monthly gradings | 25 | **100** | ✅ | `grading.py:580` → 429 |
| Slab Guard registrations | 3 | **25** | ✅ | `registry.py:530` |
| Extra photos per comic | 0 | **4** | ✅ | `images.py:325`, limit at `:338` |
| Excel/CSV export | ✗ | **✓** | ❌ **advertised only** | no gate anywhere |
| Multi-photo grading | ✗ | **✓** | ❌ **advertised only** | no gate anywhere |
| Signature ID / month | 0 | 0 | ✅ (`signature_orchestrator.py:802`) — identical, not a differentiator |
| Chrome extension | ✗ | ✗ | ✅ (`vision.py:232`) — identical, Guard+ only |
| Marketplace monitoring · API access · Ownership certs · Priority support | ✗ | ✗ | ❌ no gate; identical on both tiers |
| Bulk operations | ✗ | ✗ | ❌ **ZERO references outside `PLANS`** — fully dead key |

⚰️ **CORRECTS the June tier-honesty finding "3 of ~11 enforced (slab-guard regs, multi-photo,
chrome-extension)".** Measured 2026-08-12 the enforced three are **gradings, slab-guard regs,
extra photos**. `multi_photo` has **no `check_feature_access` call anywhere** — the docstring at
`images.py:300` says *"Requires multi_photo feature"* while the code on line 325 checks
`'extra_photos'`. A label naming a different key than the code reads; June most likely counted
the docstring. And `chrome_extension` is `False` on Pro, so it was never a Pro differentiator.

**🐛 FOURTH SURFACE, in-repo and live:** `plan['export'] = True` for Pro flows through
`/my-plan` into `account.html`'s feature grid, so a paying Pro user sees **"✓ Excel/CSV
Export"** — while `collection.html:165` has a live **📥 Export** button whose handler
(`js/collection.js:1034`) is `alert('Export functionality coming soon!')`. Session 106 Commit C
trimmed export from `pricing.html` and **missed `account.html`.** Same for `multi_photo`.

**✅ FIXED 2026-08-12.** Mike set the description to: *"100 comic gradings per month, 25 Slab
Guard registrations, and up to 4 extra photos per comic."* Three claims, all enforced, all
derived from the table above.

**🔴 FIFTH INSTANCE, FOUND IN THE SAME SITTING — AND A NEW CLASS. The Stripe ACCOUNT business
name read "The Masse".** MASSÉ and Slab Worthy **share one Stripe account** and MASSÉ set the
branding first, so **every Slab Worthy customer saw a different company's name on the hosted
Checkout page.** Corrected to Slab Worthy. The account name is a **separate surface** from the
product description, and on a shared account it can be **wrong for one project while correct for
the other** — so no state exists in which MASSÉ would ever notice, neither repo contains it, and
whoever configures it first wins silently and permanently. It is copy about **who you are** at the
payment step. Recorded in `docs/EXTERNAL_COPY_SURFACES.md` under a new *shared-account dimension*
section and proposed for **cross-project promotion** — by construction it cannot be fixed from
inside one project's canon.

**Logged as [[L-SW-2026-021]]** (both halves: third-party copy is outside every sweep, AND an
audit that greps for the claim rather than the reader issues false passes), with the standing
list in **`docs/EXTERNAL_COPY_SURFACES.md`** — Stripe Checkout, Stripe customer-portal product
names, Resend templates, Cloudflare-hosted copy. Inclusion test: *can a user read it, and can
`grep` reach it?* Of those four, only Stripe Checkout has ever been audited.

**account.html + collection.html fixed in the same pass:** `multi_photo` **removed** from the
feature grid (enforced nowhere, and every tier uploads four photos — listing it implied a gate
that has never existed); `export` now renders **SOON** regardless of the plan flag, so a paying
Pro user is no longer shown a ✓ for an unbuilt feature. The live `📥 Export` and `🗑️ Delete`
buttons in the bulk bar — whose handlers were bare `alert('… coming soon!')` — are now
`disabled` with the SOON badge idiom the sidebar already uses. Delete was fixed alongside Export
because it is the identical defect in the identical control bar; fixing one and leaving the
other is the [[L-SW-2026-019]] mistake in miniature.

### THREE THINGS THAT OUTRANK THE BACKFILL (Mike, 2026-08-12) — ordered

1. **`/api/images/submission` instrumentation.** Same treatment as the grade and extract legs.
   Fix the NULL `error_message`/`response_summary` first, *then* we know rather than infer.
2. **The 429 wall — a conversion failure, not a bug.** He burned 25 grades (Free cap) in one
   night, came back **three times over eleven hours**, uploaded photos each time, watched the
   book get identified, and got a **429 with no upgrade CTA** (7 of them). Then loaded his
   empty collection page and left. Not seen since **2026-08-06 14:52 UTC**. Scope required
   before any copy is drafted: what the 429 returns and what the client renders; whether the
   cap check knows plan and reset date at the point of refusal; what Pro would have given him
   **as a number, not a tier name**.
**✅ ALL THREE CLOSED 2026-08-12/13, plus the two follow-ons — verified by Mike:**
- **Cap screen RENDERED end to end.** *"You've used all 25 gradings this month"*, 75 more for
  $4.99, Pro 100/month, reset date subordinated, exit to collection. **The button reached
  `checkout.stripe.com` with a live session**; cancelled at Stripe rather than completed.
- **`gradings_this_month` = 27**, read back from the **`nlq_readonly` connection** — a different
  session than the one that wrote it, closing the decoy-artifact trap that caused the hang.
- **`lock_timeout = 5s`** on `collectioncalc_db_user`, confirmed in `pg_roles`. ⚠️ `SHOW
  lock_timeout` returned **0 until reconnect** — *the same read-it-from-the-writing-session trap
  one layer over.* A role-level setting applies to NEW sessions only; verifying it from the
  session that set it is the identical defect as verifying a DBeaver `UPDATE` from DBeaver.
- **Pin: 25 and 0.**
- **User 42: explained, no bug** — see the 2026-08-13 correction above.

3. **Pin his submissions before 2026-11-04.** ⚠️ `pinned` **has no writer** — declared,
   `DEFAULT FALSE`, indexed, read in exactly two places (`admin_routes.py:1283` →
   `admin.html:1305` badge), set by nothing. **And there is no purge job at all** — the risk is
   not a running timer, it is that whoever builds it builds it against
   `images_purge_after` + `pinned = FALSE` and runs it. **Recommendation: manual `UPDATE` in
   DBeaver, do not wire the column.** Scope is a live decision: `privacy.html:357` discloses
   the exception for **feedback-related** submissions only, which covers **4 rows**
   (26/28/33 Spawn #77 + 50 Daredevil), not 25. Pinning all 25 exceeds the published window
   for a real identifiable user — cleanest fix is to **ask him in the message that is already
   going out**. DECISION PENDING.

### ⚠️ WHAT'S IN THE DATA BEFORE THE MESSAGE GOES OUT

- **`last_login` is a decoy** (**[[L-2026-023]]**): written *only* by the password-login path
  (`auth.py:903`); a returning user on a live JWT never updates it. It reads 2026-08-05 23:31.
  **`request_logs` is the real record** — he returned 03:54, 13:01 and 14:43 on 2026-08-06.
- **He rated two grades** (`user_feedback`, `rating` = thumbs): **thumbs DOWN** on
  "Spawn #77 Grade: 7" (01:28:34) and **thumbs UP** on "Daredevil #196 Grade: 8" (03:47:47).
- **Spawn #77 was graded three times: 8.0, then 7.0, then 7.0.** He downvoted 44 seconds after
  the second. He watched one book come back with different grades — and kept using the product
  for another two and a half hours. **First hard evidence for grading inconsistency, which has
  been anecdotal since June** and which **[[L-SW-2026-003]]** said was unmeasurable before
  retention shipped. Also Gwenom vs Carnage ×3, Ultimate Spider-Man ×3.
- **Blast radius is exactly user 38** — no other user has the total-loss pattern. User 42's
  col 101 (3 of 4 null) is the only other damage.
- After the backfill the **photos** survive 2026-11-04 regardless (they become collection
  images under `submissions/` keys, `privacy.html:356`). What the pin protects is the
  `grade_submissions` **row** — subgrades, `raw_grade`, `limiting_factor`, model, reasoning.

---

## 2026-08-10 — 🟢 **SESSION LIVE. INDEX SHIPPED AND MEASURED. EXTRACT LEG UNCOMMITTED.**

**MOST RECENT CHANGE (Rule 5): the ~30s comic-ID wait is NOT one item. It is TWO legs, two
requests, two user moments — extract (`/api/extract`, photo upload) and grade (`/api/grade`,
the grade button). Split accepted by Mike 2026-08-10. Supersedes the single roadmap item
that has existed since June.**

**PRIOR CHANGE, same day (2 of 3):** `idx_ebay_sales_canonical_title_norm` was built. The
FMV leg went **11,717ms → 463ms** (second run 455ms, so stable rather than warm-cache).
Supersedes "the valuation comp query takes ~11s and we do not know where."

**PRIOR CHANGE, same day (1 of 3):** the drift guard no longer reports per health poll.
Transition-logged, hourly heartbeat while broken, arming line when healthy. Shipped
`62052ca`. Supersedes "the guard prints the full plan on every observation."

---

### 📊 THE MEASUREMENT THAT SETTLED IT

Two runs of The Terminator #1 through the live instrumentation (`557147d`), before the index:

| | total | q1_ebay_graded | q2_ebay_raw | q1+q2 share |
|---|---|---|---|---|
| run 1 | 10,151ms | 3,099ms / 0 rows | 6,703ms / 1 row | **96.6%** |
| run 2 | 11,717ms | 3,391ms / 0 rows | 7,798ms / 1 row | **95.5%** |

Both runs: `before_request_to_handler=0ms`, `handler_to_pool=0ms`, pool ≤160ms. Segments
summed to total with nothing unaccounted.

⚰️ **DEAD: "the 30s wait might be gunicorn queueing."** **REPLACED BY:** it is SQL, in a
segment we measured, twice. **REASON:** queueing would have to appear in
`before_request_to_handler` or `pool`; both were ~0 on both runs, and the segments already
sum to total, so there is no unmeasured remainder for a queue to hide in. **SUPERSEDES** any
plan to tune worker counts for this symptom. Do not re-raise it.

**AFTER the index — same book, same endpoint:**

```
BEFORE  total=11717ms  q1=3391ms/0rows  q2=7798ms/1rows
AFTER   total=  463ms  q1= 104ms/0rows  q2=  52ms/1rows     (2nd run 455ms)
```

**25× on the leg, 150× on q2.** Index built clean, zero invalid residue, DBeaver returned to
Manual commit. Verified **positively** via the `[VALUATION-TIMING]` line, not by the absence
of drift warnings — the absence alone would have been an unproven negative (L-2026-024).

⚠️ **CARRIED FORWARD, NOT SOLVED: q2 scanned 7.8s to return ONE row.** The index makes that
answer arrive fast; it does not make it a better answer. The Terminator #1 has one raw comp
and zero graded. That is the performance problem and the CP-1 problem in the same query, and
only the performance half is fixed. Remember this when the index makes everything feel solved.

---

### 🔀 THE EXTRACT / GRADE SPLIT — the more important finding

⚰️ **DEAD: "the ~30s comic-ID wait" as a single roadmap item (since June).**
**REPLACED BY:**

| leg | request | user moment | vision calls | instrumented |
|---|---|---|---|---|
| **extract** | `/api/extract` | photo upload | 1, **or 2 if the 180° re-read fires** | ⏳ written, UNCOMMITTED |
| **grade** | `/api/grade` | grade button | **exactly 1** (`runs=1`) | ✅ live in `62052ca` |

**REASON:** they are separate HTTP requests at separate moments. The "one vision call or
two" question belongs ONLY to extract — the 180° low-confidence re-read lives in
`comic_extraction.extract_from_base64`, not in the grading path. `/api/grade` at `runs=1`
makes exactly one Sonnet call, which the code settles without measurement.

⚰️ **DEAD: "parallelise identify and grade" as a BACKEND item (written as backend for ~2
months).** **REPLACED BY:** it is a **frontend sequencing** question. **REASON:** the two are
separate requests the browser initiates at different moments; there is no backend sequence to
parallelise. **SUPERSEDES** any backend scoping of it. Mike, 2026-08-10: *"That has been
written as a backend item for two months."*

**Track 1 (staged honest progress messaging) is unaffected and still ships regardless.**

⚠️ **CONSTRAINT, unchanged since June and restated at Mike's direction:** the Sonnet flip was
deliberate and bought honesty of errors over speed. **Nothing may trade accuracy back.**
Haiku's failure mode is confident fabrication. No proposal in this thread touches model
selection.

---

### 🔇 THE DRIFT GUARD'S OWN LOG VOLUME — fixed, `62052ca`

The guard was correct and far too loud: `/health` is polled ~12×/min (and `/` shares the
handler), so persistent drift emitted **~17,280 lines/day at ~700 chars ≈ 12MB/day** — burying
the `[VALUATION-TIMING]` lines shipped in the same commit, and the next incident after that.

Design: **silent when healthy · loud on transition · heartbeat-floored while broken.**

- ok→drift: the **full 700-char plan**, once. That verbatim text is what made the finding legible.
- drift persisting: one line **hourly**, so the freshest evidence is never >1h stale.
- drift→ok: a `✅ INDEX DRIFT RESOLVED` line **derived from the planner's own choice**, not declared.
- healthy: **nothing**, except one **arming line per worker boot**.
- probe throttled separately to 60s (`INDEX_DRIFT_PROBE_SEC`), removing ~16k DB round trips/day.

⚠️ **The arming line is not noise — it is the positive control.** A guard silent when healthy
is indistinguishable from a guard that is dead, unregistered, or throwing. Mike, 2026-08-10:
*"the guard is currently silent and I have no way to distinguish that from a dead guard until
this deploy lands."*

State is **per-worker with no shared store**, deliberately: shared dedup + per-replica
observation is exactly the L-SW-2026-013 storm mechanism (2026-07-16, ~1 email per 5–15s for
hours). Worst case here is one extra line per worker.

---

### 🐛 FOUND WHILE INSTRUMENTING: `/api/extract` has logged 0 tokens for every request

`routes/grading.py` called `log_api_usage(..., result.get('input_tokens', 0),
result.get('output_tokens', 0))` — but `extract_from_base64` **never returned those keys**.
Every `api_usage` row for `/api/extract` recorded **0 in / 0 out**, indefinitely.

The model name beside them was correct, which is what made it invisible: an accurate label
next to a quantity nothing computed — **L-SW-2026-016**, in the cost-attribution layer. The
comment on that very line claims per-extract cost attribution stays accurate after the
2026-06-16 haiku→sonnet flip; the model half was true and the token half was structurally zero.

Fixed in the uncommitted extract work: `_run_vision_pass` now returns its usage tuple, and
`extract_from_base64` returns real counts **summed across every pass**, so a 180° re-read
shows up as the doubled cost it actually is.
⚠️ **This changes what lands in `api_usage`.** Historical `/api/extract` token rows are zeros
and cannot be reconstructed — do not treat pre-2026-08-10 extract cost data as real.

---

### 📊 THE GRADE LEG, MEASURED — 2026-08-10, The Terminator #1

```
total=20686ms  before_request_to_handler=305ms  cap=301ms  body=33ms  normalize=29ms
quality=7ms  moderation=434ms  vision=18734ms  parse=0ms  post=1137ms
images=3  payload_kb=2241  runs=1  vision_calls=1  moderation_calls=3
model=claude-sonnet-4-6  in_tok=2380  out_tok=809
```

**Vision is 18,734ms = 90.6% of the leg. One call. There is no preamble to optimise away.**

⚰️ **DEAD: the moderation loop as a latency suspect.** **REPLACED BY:** 434ms across 3 calls
— noise. **REASON:** measured, not reasoned about. The missing `break` is still a real code
smell (one Rekognition round trip per photo where the quality gate above it breaks after the
first) and is **deliberately LEFT UNFIXED** — Mike, 2026-08-10: *"I am glad we measured
rather than fixed it. Log it, do not touch it."* **SUPERSEDES** any impulse to fix it on
sight. `moderation_calls=3` keeps the count measured rather than read off the loop.

**Two open questions raised by that line, answered by reading the code (2026-08-10):**

1. ⚠️ **`model=claude-sonnet-4-6` is the CONFIGURED HEAD of the chain, not a stale fallback.**
   `MODEL_CHAINS['sonnet'][0]` is `claude-sonnet-4-6`; `_active_index` only advances on a 404,
   and production logged index 0. **But the chain itself is stale** — `models.py` says
   *Last verified: 2026-06-06*, and the Sonnet generation has moved on since. `opus` is in the
   same state (head `claude-opus-4-8`), which is the precedent Mike cited. **The grading path
   is running a generation behind, by configuration, silently.**
   ⚰️ **DEAD: "the dependency monitor watches our models."** **REPLACED BY:** `check_anthropic()`
   watches deprecations.info for **retirements**. It answers *"is what we use dying?"* — never
   *"is what we use current?"* A superseded-but-supported model is **invisible to it by
   design**. **REASON:** that is why both the opus 4.6→4.8 gap and this one passed unnoticed.
   Same shape as everything else this week: a check that cannot see the thing (L-2026-024).
2. ⚰️ **DEAD — RESOLVED 2026-08-10 BY A PROPER RUN. See "IMAGE SIZE IS A CLOSED
   CANDIDATE" below. The hypothesis in this item was WRONG about the mechanism.
   Kept for the record; do not act on it.**

   ~~⚠️ **`in_tok=2380` is honest, but the images are probably arriving small.**~~
   `usage.input_tokens` **does** include image tokens — this is NOT the `/api/extract`
   structural zero (that was a missing dict key defaulting to 0; here the API populates a real
   value). But the arithmetic does not fit 3 full-cap photos: Anthropic bills ≈ (w×h)/750 after
   fitting the long edge to ~1568.

   | photos land at | billed per image | ×3 |
   |---|---|---|
   | 2000px (cap top) | ~2,113 | **~6,340** |
   | 1500px | ~1,936 | ~5,808 |
   | **1000px (cap bottom)** | **~860** | **~2,580** |

   Observed 2,380 **including the prompt** sits on the bottom row. `_decode_normalize_encode`
   draft-decodes at exactly 1/2 and only thumbnails if the result is STILL over cap, so output
   lands anywhere in **(cap/2, cap] = 1000..2000px** — a documented consequence accepted for
   memory reasons on 2026-07-16, whose **accuracy** cost was never priced. A photo at the
   bottom of that band gives the grader **a quarter of the pixel area** of one at the top,
   while the strict grading quality floor exists precisely because defects need detail.
   🚧 **HYPOTHESIS, not a finding.** `dims=` and `norm_kb=` were added to `[GRADE-TIMING]` to
   settle it in one grade. Do not act on it before that line is read.

**`post=1137ms` and `before_request_to_handler=305ms` are both DB round trips.** Every
`db.get_db()` checkout pre-pings with `SELECT 1`, and `/api/grade` opens and closes the pool
**five separate times** (auth decorators, cap check, usage log, counter increment, usage read)
where `/api/sales/valuation` opens it once. At the ~300ms/checkout that `cap=301ms` shows for a
single SELECT, that is ~1.5s of the 20.7s. Not the problem; a real number for later.
⚠️ `before_request_to_handler` was documented as "~0 by construction." That holds only for
`api_sales_valuation`, which carries **no decorators**. `@require_auth` / `@require_approved`
run between `before_request` and the handler body, so their cost lands in that field. The
control field fired and told us something — which is why it was logged.

### ⚰️ IMAGE SIZE IS A CLOSED CANDIDATE — **not a solved problem**

**Run with real CAMERA PHOTOS, 2026-08-10:**

```
[GRADE-TIMING]   total=25459ms body=801ms normalize=598ms imgmeas=7ms quality=47ms
  moderation=932ms vision=21889ms post=891ms images=4 payload_kb=13038 norm_kb=3658
  dims=1506x2000,1506x2000,1506x2000,1506x2000 in_tok=7534 out_tok=908
  cache_create=0 cache_read=0
[EXTRACT-TIMING] total=14214ms body=337ms quality=316ms moderation=482ms normalize=191ms
  barcode=4082ms vision1=8511ms payload_kb=3874 barcode=miss reread=not_needed
  in_tok=4433 out_tok=320
```

**All four photos land at 1506×2000 — the TOP of the (cap/2, cap] band. The cap works.
Real submissions get full detail.** `in_tok=7534` matches the ~6,340 + prompt predicted for
2000px photos, and `cache_create=0 cache_read=0` proves the cache fields are genuinely zero
rather than assumed.

⚰️ **DEAD: "photos may be reaching the grader at a quarter of the intended pixel area."**
**REPLACED BY:** they arrive at the top of the band. **REASON — and this is the part worth
keeping:** the 512×780 sample that produced the hypothesis came from **eBay SCREEN GRABS**,
not camera photos. eBay serves listing thumbnails at a few hundred pixels, so that was a
**small source arriving small** — it never engaged the draft-halving path at all. The
(cap/2, cap] arithmetic was correct and the proposed *mechanism* never fired. **SUPERSEDES**
any plan to trace the normalization step. Mike, 2026-08-10: *"I nearly sent you off tracing a
step that does not exist."*

⚠️ **Image size is now a CLOSED CANDIDATE for the undergrading complaint (L-SW-2026-003) —
which means the undergrading mechanism is back to UNEXPLAINED.** Ruling a cause out is not
finding one. Do not let the closure read as a fix.

✅ **`dims=52x784` was real, not a rendering artifact.** The emit truncates exactly one field
(`title`, `[:60]`); `dims` passes through whole. Verified by positive control against
`1052x784` and a four-photo 4-digit string — both rendered intact, so a narrow value is a
narrow image. It was a sliver screen grab. Closed.

### 🔦 THE BARCODE SEGMENT — 4,082ms of a 14,214ms extract, on a MISS

Measured offline against the real `scan_barcode` control flow, photo-realistic fixtures:

| source | pixels | miss-path total | ms/MP |
|---|---|---|---|
| 3024×4032 (phone, untouched at the 4096 cap) | 12.2 MP | **6,633ms** | 544 |
| 1506×2000 (grading-cap size) | 3.0 MP | 1,612ms | 535 |
| 753×1000 | 0.8 MP | 396ms | 528 |

**Linear in pixels at ~535 ms/MP across a 16× range.** Yes, it scales with image size.

**Where the time actually goes — the four rotations are NOT the cost:**

```
rotates   113ms          <- 1.7%
decodes  6464ms          <- 97%   across EIGHT pyzbar calls
  per rotation:  pass1 (symbol-filtered) ~515ms  +  pass2 (UNFILTERED fallback) ~1090ms
```

Three structural facts, all observed rather than reasoned:
1. **The unfiltered fallback is 2/3 of the total.** It costs ~2× the filtered pass and runs on
   **every** rotation in the miss case, by construction.
2. **`break` fires only on a HIT**, so `barcode=miss` is structurally the maximum-cost path —
   and a comic without a scannable barcode pays the most.
3. **zbar is running PDF417 and DataBar decoders on a comic cover.** Direct evidence: the
   unfiltered pass emits `zbar/decoder/pdf417.c` and `databar.c` assertion warnings. Those
   symbologies do not appear on comics.

🚧 **UNEXERCISED, stated so it is not mistaken for measured:** the HIT path was **not**
successfully benchmarked — the synthetic bar field was not a decodable UPC, so that run was
another miss. Hit-path cost is **unknown**; only the miss path above is measured.

**What the code permits (NOT a proposal — no fix scoped):** the `break` exists but only on
success; the unfiltered fallback is unscoped; extraction scans at up to 12MP where a UPC needs
only enough resolution to resolve bar widths; and `photo_type` is already known to be `front`,
where a comic barcode is always bottom-left — spatial scope exists and is unused.
`dims=`/`mp=` added to `[EXTRACT-TIMING]` so production confirms the scaling directly.

### ⚠️ LOGGED, NOT SCOPED — no warning for too-small source images

Grading from 512px eBay screen grabs passed `quality=8ms` **without comment** and returned a
confident **8.5**. The grading quality gate has a strict resolution floor, and these cleared
it. A collector browsing eBay listings would plausibly do exactly this. Mike, 2026-08-10:
*"I am not scoping it tonight."* Related to L-SW-2026-016 — a confident output whose input
could not support it, with nothing on screen saying so.

### 🔬 STILL UNMEASURED — do not theorise ahead of it

- **Why one Sonnet call takes ~19–22s. NO LEVER IS CURRENTLY INDICATED.**
  ⚰️ **DEAD: "output length is the likely lever."** **REPLACED BY:** nothing — the question is
  open. **REASON:** the proper camera-photo run moved input **3.2×** (2,380 → 7,534) while
  latency rose only **19%** (18,442 → 21,889ms) and output barely moved (806 → 908). Neither
  term dominates cleanly, so the single-run observation that pointed at output length does not
  survive a second data point. Mike, 2026-08-10: *"I am recording that the lever we thought we
  had identified is no longer indicated."* Do not re-raise output length as the suspect
  without new measurement.
- **Whether the 180° re-read fires in practice** is unknown and **the logs cannot answer it**.
  Extraction logs nothing on a clean success path, so absence of the doubled-cost line proves
  nothing in either direction. That is why `reread=` is now emitted on **every** request
  including `not_needed` — the same silence problem as the drift guard, in a different place.

---

### 📌 SHIP STATE, verified from git at time of writing (L-SW-2026-008)

| | |
|---|---|
| `HEAD` | **`62052ca`** — drift guard + `[GRADE-TIMING]`, **committed and DEPLOYED** |
| `04b2bb8` | ROUGH ESTIMATE badge refactor — was pushed but undeployed; **carried live by the `62052ca` deploy** |
| uncommitted | `comic_extraction.py`, `routes/grading.py` — the `[EXTRACT-TIMING]` unit + token fix |

Backend-only throughout: `deploy` yes, `purge` no. No extension touched, no version bump due.

---

## 2026-08-04 — 🔒 **SESSION CLOSED. ALL THREE UNITS SHIPPED, PUSHED AND VERIFIED.**

**MOST RECENT CHANGE (Rule 5): Phase 1 — `all_comic_sales` is now described in `DB_SCHEMA` and granted
to `nlq_readonly`, so NLQ answers sales questions from the full 173,346-row corpus instead of the
5.8% Whatnot slice. Shipped `3a9892f`. Supersedes "`market_sales` is the only sales table NLQ can
see."**

**PRIOR CHANGE, same day (2 of 3):** `all_comic_sales`'s second leg now emits `market_sales.source`
and carries no `WHERE` clause; it previously emitted the literal `'whatnot'::text` **and** filtered
`WHERE market_sales.source = 'whatnot'`. Supersedes the approved scope of "remove the WHERE clause
only," which was incomplete — see the literal-vs-column finding below.

**PRIOR CHANGE, same day (1 of 3):** the admin NLQ handler no longer executes model-generated SQL on
the app's read-write pool; it uses the SELECT-only `nlq_readonly` role via `DATABASE_URL_NLQ`, and the
`admin_nlq_history` INSERT was split onto the read-write pool. Supersedes "the denylist +
SELECT-prefix check are the NLQ safety model" (in place since the endpoint was written).

---

### 🔒 SESSION CLOSE — 2026-08-04

**Ship state, verified from git at close (not from memory — L-SW-2026-008):**
`HEAD` = `origin/main` = **`d3c5a9d`**, confirmed via `git ls-remote`, not the local tracking ref.

| Commit | Contents |
|---|---|
| `d3c5a9d` | NLQ post-mortem + L-SW-2026-019 promotion pointer (2 files) |
| `63d95ad` | July 16 OOM post-mortem, alone (1 file) |
| `3a9892f` | Phase 1 — `admin.py`, `LESSONS.md`, `WHERE_WE_LEFT_OFF.md`, `nlq_readonly_role.sql` |
| `5f2deb5` · `8709518` | the role fix, pushed earlier the same day |

**Live and verified in production:**
- `nlq_readonly` — SELECT-only, unpooled, 15s `statement_timeout`, read-only session, fails closed on
  missing `DATABASE_URL_NLQ`; `users` granted at **column level excluding `password_hash`** and
  deliberately absent from the table-level grant.
- `all_comic_sales` — `WHERE` clause **and** the `'whatnot'::text` literal both removed; ACL
  byte-identical across the replace.
- Phase 1 — view described in `DB_SCHEMA` (3,609 → 4,889 chars) and granted; raw `ebay_sales` still
  denied to the role.
- **Post-deploy artifact: `admin_nlq_history` row 43**, `result_count` 8, `execution_time_ms` 3312.
  The history split works — query on the read-only role, audit row on the read-write pool.

**Lessons written this session:**
- **L-SW-2026-019** written and ✅ **promoted → `L-2026-026`**.
- **L-2026-025** written — the identity of the executing principal is part of a verification's
  meaning. Carries an explicit **do-not-merge** block against L-2026-024.
- **L-2026-024 amended** — role-filtered `information_schema` views as a blinding mechanism, plus the
  rule that an unconstructable positive control means reporting the check **UNPERFORMED**, never
  "clean but unverified."
- `LESSONS_CROSS_PROJECT.md` at **v1.5, 13 lessons active**, footer confirmation string updated in the
  same edit. ⚠️ That file is **outside this repo and under no version control** — see priority 1.

### 🔬 CP-1 CONFIDENCE MEASUREMENT — read-only, nothing shipped, nothing committed

`scripts/cp1_confidence_measure.py` (**UNTRACKED, uncommitted**). Read-only via `do_readonly`.
No writes, no DDL, no production behaviour change, no git operations. Corpus at time of run:
`ebay_sales` 168,405 · `market_sales` 9,972.

**Findings that stand on their own, independent of the pending tables:**

1. ✅ **No user-facing count or range is computed post-trim.** `graded_sample_size` =
   `len(exact_match)` (`sales_valuation.py:388`, untrimmed), `sales_count` = `len(prices)` (:562),
   `min_price`/`max_price` on untrimmed `prices` (:563-564); same in `/api/sales/fmv`'s tier block
   (:856-864). **The Low-confidence evidence display ("3 sales, $40–$95") is already honest — a CP-1
   design concern closed with no code change** (Mike's call, 2026-08-04).
2. ✅ **The median is INVARIANT under `percentile_trim`.** 4,764 synthetic cells incl. adversarial
   shapes → zero differences; also provable (symmetric trim shifts the median index equally on both
   sides). So FMV, `raw_fmv`, price-curve `avg_price` and the interpolation medians are ALL
   unaffected by trimming.
3. ⚠️ **The trim is NOT 5% at low n.** `cut = max(1, int(n*0.05))` removes a FLAT 2 rows from n=3
   through n=39 — 67% at n=3, 40% at n=5, 25% at n=8, 5.1% at n=39 — then 4 rows at n=40. Sawtooth.
4. ⚠️ **The effective CI floor is n=7, not n=5.** `bootstrap_ci_median` needs ≥5 values and
   production trims BEFORE bootstrapping, so **n=5 and n=6 yield an FMV with NO confidence
   interval.** Verified by calling both functions directly. **Leading candidate for the D2 Low
   boundary — defined by what the engine can actually produce rather than a chosen number.**
5. 🚧 **UNPROVEN CLAIM, carried forward (Mike, 2026-08-04):** *"trimming only ever NARROWS the CI."*
   The first half — that the CI is the only output the trim changes — follows from (2). The
   **direction is asserted, not measured.** Trimming both reduces spread (narrows) and reduces n
   (widens); on a tight, evenly-spaced sample with no real outlier the n-reduction may dominate.
   The script now records **per-cell** narrowing with the **sign preserved, never floored**, and
   reports the count of cells where it is negative plus their buckets. If zero across all three
   seeds the claim becomes established; otherwise it is a finding. Same shape as L-SW-2026-015 — a
   claim whose disconfirming case the probe must be able to surface. **It currently prints
   "UNTESTED, not confirmed" when no comparable cells exist, which is correct behaviour.**

⚰️ **The 3B amendment was REVERSED the same day.** DEAD: "lookup_demand is a sanity check; the
grade_submissions/search_cache/collections union is primary." REPLACED BY: **lookup_demand is
PRIMARY (542 distinct books); the union is the sanity check (89 books), reported per-source.**
REASON (Mike): the NULL `user_id` weakness breaks demand **RANKING** by distinct users — it does not
affect the comp-count **distribution**, which ranks nothing and needs only the set of books looked
up. The demotion traded 6.1× the breadth for an attribution property this measurement never uses.

⚠️ **Sampling method, so Step 3A is not over-read:** universe is 44,423 in-window (title, issue)
pairs with a non-empty `canonical_title`; selection is `ORDER BY md5(seed || title || '|' || issue)`.
That is uniform over **BOOKS, not over SALES** — a 600-comp book and a 1-comp book are equally
likely. Books whose in-window rows ALL have an empty canonical (13.6% of `market_sales` rows) cannot
enter the universe at all. Step 1's 5 density-selected control books are now explicitly excluded
from the sample (measured overlap was 0, but nothing enforced it).

**Three N=200 runs launched at session close** (seeds `''`, `s2`, `s3`; repeat seeds `--skip-3b`
since 3B is not sampled). Output persisted to **`scripts/cp1_output/cp1_N200_seed-*.txt`**, each
carrying an in-transaction SNAPSHOT stamp (per-table row counts + max sale date) in its header.
⚠️ Two output-capture failures on 2026-08-04 — Python block-buffering to a file, then a pipe to
`tail` holding until EOF — cost two runs. **Terminal scrollback is not storage.** Confirm the files
exist and are non-empty before treating any run as complete.

⚠️ Three earlier runs died on `NameError: name 'control' is not defined` — a patch to `main()` that
silently did not land, the same write-failure class that mangled five f-strings. **Heredoc patching
of this file is unreliable; use the editor.** Fixed and verified end-to-end before relaunch.

⚠️ **A SECOND crash, caught only because the output was persisted to disk** — which is the argument
for the persistence rule, not a footnote to it. The first N=200 seed-default run reached step 3B
after ~77 minutes and died on
`TypeError: '<' not supported between instances of 'NoneType' and 'str'`: `issue` is NULLABLE in
`lookup_demand`, `grade_submissions`, `search_cache` and `collections`, and a bare `sorted()` on
`(title, issue)` tuples compares `None` against `str`. Fixed with `_sort_pairs()`, which coerces
`None` to `''` **for ordering only** — the `None` is preserved in the tuple because `fetch_comps`
correctly treats a `None` issue as "no issue filter". `--skip-3b` runs never touch that code path,
so s2/s3 were unaffected.

**RUN STATE AT SESSION CLOSE — verify before reading anything:**
- `cp1_N200_seed-default.txt` — first attempt CRASHED in 3B (step 3A output is valid and present;
  steps 4 and 5 never ran). **A corrected full rerun is QUEUED** and starts automatically once
  s2/s3 finish; it overwrites this file. Completion marker: `scripts/cp1_output/_RERUN_DONE`.
- `cp1_N200_seed-s2.txt`, `cp1_N200_seed-s3.txt` — `--skip-3b`, running/queued, unaffected by the
  bug. Chain marker: `scripts/cp1_output/_ALLDONE`.
- ⚠️ **Check for `RUN COMPLETE` in each file before trusting its tables.** Two of the five runs
  attempted tonight produced partial output that looked plausible until the tail was read.

**Verification agent (`feature-dev:code-reviewer`) found 3 real defects, all fixed:** the variant
exclusion was SQL-only so the toggle was a **no-op for every graded cell** (production excludes in
Python at `:369-371`); `percentile_trim` was imported and advertised but never called, so Step 4 ran
untrimmed; and a latent `ZeroDivisionError`. A fourth, found by measurement rather than review:
Step 4 issued **one SQL round trip per comp** to compute age.

### 🔒 2026-08-05 SESSION CLOSE — corrections, ordering, and one uncommitted file

**SHIPPED:** CP-1 Unit 1 (verdict gate → `interpolated` + `exact_thin` + `blended`) · Unit 3 (min-n
K=2 + `low_support` tier) · **L-SW-2026-020** written (20 lessons) · this file updated.

⚠️ **UNCOMMITTED, ON DISK:** `scripts/corpus_snapshot.py` — end-of-day corpus snapshot, `--days` /
`--json`. Same status as `coverage_assessment.py` and `stripe_preflight.py`. **Decide next session
whether it lands; Mike leans yes** (it is the seed of the admin corpus dashboard).

**⚰️ THREE CORRECTIONS — all supersede earlier reasoning in this file. Do not resurrect the dead
versions.**

1. ⚰️ **DEAD: "Whatnot / `market_sales` has been dark since 2026-07-01."**
   REPLACED BY: **10 rows arrived 2026-08-02 → 2026-08-05** (1 · 8 · 1). It is **trickling — neither
   dark nor active.** REASON: measured directly from `created_at` by day.
   **The open question is no longer "is the extension running." It is "why 10 rows against eBay's
   36,961 the same day."**

2. ⚰️ **DEAD: treating a §2A key as done when it clears §1's stopping rule.**
   REPLACED BY: **§1's rule is BOOK-level (≥10 comps / ≥5 graded); the product prices at GRADE
   level.** All nine §2A keys cleared 2026-08-05 — but Batman #227's 54 graded comps spread across a
   20-grade ladder average **under 3 per bucket**, and **67.9% of populated graded cells still hold
   exactly one comp**. **"Cleared" means off the estimate fallback, NOT returning confident
   verdicts.** ⚠️ **This needs FIXING IN `EBAY_CAPTURE_SCHEDULE.docx` §1, not merely noting** —
   the stopping rule as written retires keys that still cannot produce a verdict at most grades.

3. ⚰️ **DEAD: "scarce keys accrue ~3 comps/year."** REPLACED BY: **nothing — the figure was
   invented, never measured.** Batman #227 reached 123 comps in days. **Disregard it wherever it
   influenced reasoning** (it was used to argue starved keys would stay starved; they did not).

**🔜 NEXT SESSION, IN THIS ORDER (Mike, 2026-08-05):**
1. **W2 claims sweep — AUDIT ONLY, no fix proposed until the surfaces are known.** The code contains
   **no recency weighting of any kind** (verified: no decay, no half-life, hard cutoff only), yet it
   is claimed as an edge over CovrPrice and GoCollect. **Discriminate by SURFACE — the exposure is
   completely different per surface:** `COMPETITORS.txt` is internal and nobody outside sees it ·
   user-facing copy and marketing are real exposure · **a patent or whitepaper filing is materially
   worse and would warrant counsel.** Report where it appears before proposing anything.
2. **Unit 2 instrumentation** — `is_internal` (flags 11 of 1,276 rows; ~600 founder lookups read as
   cold traffic) and `fmv_method` pollution (665 rows carry `/api/sales/fmv` tier labels).
   **Degrades daily** and blocks §4's promotion loop from ever running honestly. Cannot retro-fix
   existing rows — §4 must start from a cutoff date.
3. **Field-name hygiene bundle** — rename the `interpolated` tier (95.6% of it is one-sided
   extrapolation), fix `nearby_thin_comps`, **and extract the tiering logic into an importable
   function.** Rationale: `classify()` in `corpus_snapshot.py` now mirrors shipped logic by hand,
   the interpolation arithmetic is inline in the route, and the admin dashboard would be a **third**
   copy. **Cost is lowest right now** — do it before the third copy exists.
4. **Corpus stall alert** — small, and has already cost twice.

**🅿️ PARKED — DO NOT REOPEN WITHOUT NEW DATA: the robustness/bounds check.** Corpus growth is
shrinking its addressable base by itself — buckets that were empty two days ago now return `exact`
(spider man #1 @9.8 went from a 2,627%-error interpolation to `exact` $150 on 522 comps within the
session). **Re-measure in a few weeks and see what is left before designing anything.**

---

### ✅ 2026-08-05 — CP-1 GATE: UNITS 1 AND 3 SHIPPED AND VERIFIED IN PRODUCTION

**All corpus figures below carry a snapshot stamp. The corpus grows ~20k rows/day — a mismatch
against these numbers is growth, not an error.**

**UNIT 1 — the ROI verdict now requires real same-grade comps.** `verdict_reliable` previously gated
only the FABRICATION tier. Measured against the capture schedule's own key lists that hedged **0.0%
of the 9 §2A starved keys and 0.0% of the 15 §2C blue-chip anchors** — none of the 24 books cold
traffic will type. Now also false for `interpolated`, `exact_thin` **and `blended`**.
⚠️ `blended` was nearly missed: B-vs-C measured identical only because `exact_thin` is essentially
EMPTY on the keys that matter — a thin exact bucket becomes `blended` whenever neighbouring grades
exist, which on flagship keys they always do. "The very_low extension is free" was free because it
was **vacuous**. blended is 21.7% of §2A and 15.7% of §2C. New `verdict_basis` field
(`fabricated|low_support|interpolated|blended|thin|supported`) drives tier-specific copy; **FMV
numbers still render in every tier**, only the slab/no-slab recommendation is withheld.

**UNIT 3 — minimum source support (K=2) on interpolation.** A grade bucket must hold ≥2 sales before
it can anchor an interpolation; thinner buckets are skipped and the next populated bucket is used.
Plus the `low_support` tier so ~72% of cells pushed out of `interpolated` are not described by the
`fabricated` string, which would be false for them.

**⚠️ THE ROOT DEFECT (this is the finding to carry forward): interpolation weighted by grade distance
ONLY, never by evidence.** Worked case — **Spider-Man #1 @ 9.8**, true median **$110.00 from 315
same-grade comps** (snapshot 2026-08-05 17:12 UTC, ebay_sales 185,278): the 9.9 bucket held exactly
**one** genuine $4,449.99 sale, and interpolating 9.6 ($99, n=74) → 9.9 at weight 0.667 returned
**$2,999.66 — a 2,627% error. One sale outvoted 315.** With K=2 the 9.9 bucket is skipped and the
result is **$102.95 (6.4% error)**.

**THE INTERPOLATED SURFACE, measured (snapshot 2026-08-05 22:58 UTC, ebay_sales 200,335):**
75,356 interpolated cells, of which **95.6% are one-sided ±20%/grade extrapolation — not
interpolation between two points at all** — and **90.0% anchor on a bucket holding a SINGLE sale**
(96.9% ≤2, only 0.9% ≥5). **69.5% sit on the 2,592 single-graded-comp keys**, which the capture
burst grows with every new title captured at depth 1.

**Tier movement K=1→K=2:** 60,301 cells `interpolated`→`low_support` (72.5%), 1,247
`blended`→`exact_thin`, **0 cells moved from a hedged state to an unhedged one.** `exact` (≥3
same-grade comps) is structurally untouched.

⚠️ **This is a TAIL fix, not a central-tendency fix** — backtest median error moves only 19.3% →
18.1%, coverage lost 7.3%. The backtest modelled **fallthrough-to-next-populated-bucket**, which is
what shipped (verified line-by-line against the shipped selector), so those numbers do describe
production.

**POST-DEPLOY VERIFICATION, live prod (snapshot 2026-08-05 23:27 UTC, ebay_sales 200,335):**
| case | result |
|---|---|
| `spider man #1 @9.8` | `exact` $150.00, 522 same-grade comps — **the pathological case is no longer reproducible**: the 9.8 bucket filled in, so it never reaches interpolation. Fix effect unobservable here. |
| `ASM #41 @9.4` | `interpolated`, hedged, **graded_fmv $3,328 → $2,052.01** — min-n changed which buckets anchor it. **This is the working demonstration case.** |
| `ASM #300 @9.8` | `exact`/`supported`, verdict shows — not silent everywhere |
| `100 Page Super Spectacular #4 @10.0` | `low_support`, `nearby_thin_comps=1` — singular renders correctly |
| nonexistent book | `fabricated`, `nearby_thin_comps=0` — cannot render "0 recent sales" |

**⚠️ THE n≥10 INVERSION — CONTAMINATION FALSIFIED, CURVE STEEPNESS STANDS.** Error falls with source
support (n=1: 27.9% median · n=5-9: 10.2%) then **jumps back at n≥10 to 29.0%**. Excluding suspected
Platinum/UPC Gold/Silver edition rows (260 rows, 1.29%) leaves it at 29.0% / p90 64.8%, and only 3
cells left the band — variants are not concentrated there. **A future confidence bound needs GRADE
POSITION as a term; source-bucket n alone is unsound above 9.** (Caveat: the variant regex catches
1.29% of rows; severe under-detection could still hide an effect.)

**⚠️ CGC COST COUPLING — recorded in code above `get_cgc_grading_cost()`, cross-reference it.**
Above $1,000 the fee is 4% of FMV, so bounding FMV downward also bounds cost downward and **NARROWS**
the ROI gap — a naive pessimistic bound produces a flattered worst case, the opposite of a safety
bound. **Any bound must move both terms together.**

**🅿️ ROBUSTNESS CHECK — PARKED with a re-measure condition.** Recovery measured at 33.1% (all
interpolated) / 51.6% (§2A) / 36.0% (§2C) **on a population that INCLUDES the n=1 anchors Unit 3 has
now removed.** Re-measure post-min-n before deciding: tighter bounds, much smaller addressable base.
Also: 37.7% of interpolated cells have NO raw comps and 17.6% have 1-2, so on **55.2% both sides of
the ROI are weak** — a bound must cover the raw side too.

**BACKLOG, logged not fixed:** `is_variant` misses Platinum/UPC Gold/Silver editions (fold into the
Absolute Batman variant-subtyping work) · the `interpolated` tier is **misnamed** — 95.6% of it is
one-sided extrapolation with a 25% floor · `nearby_thin_comps` sums ALL nearby buckets, so it reads
484 on a 522-comp cell (correct where consumed, misnamed elsewhere — **[[L-SW-2026-020]]** instance 4).

---

### 🔥 2026-08-05 — CP-1 AUDIT: A POPULATION-LEVEL MATCHER DEFECT

⏱️ **EVERY FIGURE BELOW IS A POINT-IN-TIME SNAPSHOT — DIVERGENCE IS GROWTH, NOT CONTRADICTION.**
Since the ingestion-rate fix the corpus grows **~20k rows/day**, and it is bursty: at
2026-08-05 16:58 UTC, `ebay_sales` = **182,674** with **19,300 rows created in 24h and 14,269 of
those in the single preceding hour**. `market_sales` is static at 9,972, so the source split moves
on its own: **94.2%/5.8% (early 2026-08-05) → 94.8%/5.2% (16:58 UTC same day)**. Within this one
session `ebay_sales` read 163,374 → 168,405 → 182,674 and `lookup_demand` 1,266 → 1,268 → 1,271.
**Do not treat a mismatch against these numbers as an error to investigate.** All four audit scripts
now emit a `[SNAPSHOT AT START]` line (row counts, source split, `max(sale_date)`, timestamp);
compare a figure only against the stamp in its own output file. The 180-day window also slides, so
even a re-run at the same instant next week covers a different span.

⚠️ **THIS STARTED AS AN ASM #41 DIAGNOSTIC AND BECAME SOMETHING LARGER.** The question was why one
book valued at ~$47. The answer is that `title_matching.qualifier_title_clause()`'s **fallback
branch** contaminates comp pools across the corpus. ASM #41 itself is NOT explained by it and remains
open — see the bottom of this section. **Nothing shipped, nothing committed, no matcher change, no
production change.** All output persisted in `scripts/cp1_output/`.

**Five read-only runs, all RUN COMPLETE:**

| File | What it did |
|---|---|
| `cp1_N200_seed-{default,s2,s3}.txt` | Step 3A uniform distribution, 3 seeds, N=200 + Step 5 |
| `cp1_STEP4_stratified.txt` | Step 4 stratified, 518 cells, ~75/bucket |
| `cp1_fallback_audit.txt` | 400-pair branch-split cross-check |
| `cp1_nesting_audit.txt` | **complete** audit of the nesting population |

**STEP 4 (stratified) — the estimator-stability curve.** Buckets now hold 51–117 cells, not 2–20.
`CI%med` falls monotonically 113.8 → 80.2 → 65.6 → 38.2. Leave-one-out swing falls 21.8 → 21.6 →
**12.3 → 4.7** → 5.3 → 1.5, breaking hardest between 3-4 and 8-12. `IQR%med` deliberately does NOT
fall (88/98/85/96/94) — dispersion is a property of the book, not the sample size, which is the
check that the strata aren't selecting easy books. `noCI` confirms the **n=7 floor** empirically:
buckets 1/2/3-4 are 100% no-CI; bucket 5-7 is 46 of 64. Median invariance re-confirmed on 518 real
cells, 0 differences.
⚠️ **Reassignment rate 49.8%** (258/518): half of sampled cells had a production comp count
different from their canonical-grouping strata count. Built as a fidelity disclosure; at that
magnitude it is an independent measure of fallback contribution, reached from a different direction.
⚠️ **3 titles timed out at 120s** on unfiltered scans, by name: `Sold Here Retailer Promo Pos`,
`Something is Killing the Chi`, `Spider-Man Characters Lot`. All `issue = None`. Same artifact family
as the junk canonicals below — the pathological-title list and the artifact tier may be one list.

**NESTING AUDIT — complete over the population, not sampled.** Substring-membership IS the fallback's
match predicate, so client-side substring enumeration reproduces branch B exactly. One bulk fetch
(96,921 rows, ~12 MB), matching computed in 6s.
- **2,667 nested targets of 15,957 in-window titles (16.7%)** under production filters.
  (An unfiltered earlier count gave 3,855 / 24,973 / 15.4% — both correct for their scope; the
  filtered one is the right denominator for production impact.)

| target length | cells | added rows | **different canonical** | med Δ | p90 Δ | max Δ |
|---|---|---|---|---|---|---|
| **<6 (artifact)** | 25,458 | 194,762 | **99.8%** | 38.0% | 399.5% | 48,589% |
| 6–11 | 21,278 | 121,004 | **99.6%** | 27.0% | 210.3% | 26,400% |
| 12–19 | 8,631 | 26,487 | **99.2%** | 16.7% | 118.9% | 12,463% |
| 20+ | 3,730 | 11,039 | **99.8%** | 15.4% | 98.0% | 6,367% |

- **The different-book share is ~99% in EVERY tier.** Across ~353,000 added rows the fallback is
  essentially never recovering the same book. It was justified as a rescue for unclean canonicals;
  it is the Batch 8 mechanism intact in branch B.
- **Monotonicity holds and does not rescue the design.** Median delta falls with target length, so a
  minimum-length rule has a measurable shape — but the 20+ tier still moves the median 15.4% (p90
  98%) at a 99.8% different-book rate.
- Median shift over 5,321 comparable cells: only **10.6% unchanged**, **52.4% move >20%**, 14.5%
  move >100%.
- **Artifact tier is live, not a data-quality footnote:** `'an'` (two characters) matches **87,372
  rows**; `'comics'` matches **37,175**. Both exceeded the 20k collection cap; true counts recorded,
  medians computed on the first 20k, cap disclosed in the output.

**⚠️ THE NESTING PROPERTY CORRELATES WITH BEING A FLAGSHIP.** Bare franchise names are substrings of
their own longer titles, so the most valuable and most-queried books are structurally the most
exposed:

```
48589%  'x men'              #181  raw   $2.67 → $1,300.00   n 1→7
26400%  'spider man'         #122  9.2   $3.00 → $  795.00   n 1→3
12463%  'amazing spider man' #22   raw   $9.99 → $1,254.99   n 1→2
 8317%  'silver surfer'      #48   raw   $6.00 → $  505.00   n 5→70
 8296%  'wolverine'          #94   raw   $4.64 → $  390.00   n 4→25
 5321%  'batman'             #400  raw   $2.49 → $  135.00   n 1→18
 4407%  'jsa'                #1    raw   $5.99 → $  269.99   n 1→29
```

**COST SIDE — removing the fallback costs very little where cells had real comps:**

| transition | cells | share |
|---|---|---|
| **cell exists ONLY via fallback** | 53,776 | **91.0%** |
| no threshold change | 2,450 | 4.1% |
| drops below 3 | 2,107 | 3.6% |
| drops below 5 | 483 | 0.8% |
| drops below the n=7 CI floor | 281 | 0.5% |

⚠️ **TWO LIMITATIONS — do not let conclusions outrun them.**
1. **MAGNITUDE ONLY, NOT DIRECTION.** Everything above is `|median shift|`. Every worst-case example
   happens to move UPWARD, which would mean inflated FMV → inflated ROI → users told to grade books
   that are not worth grading (straight into D4). **That direction is NOT measured.** One column,
   same data, no new fetch.
2. **CONTAMINATION, NOT CORRECTNESS.** The audit establishes that added rows carry a different
   canonical 99% of the time. It does NOT establish which median is closer to truth. For bare
   flagship canonicals the EXACT rows may themselves be truncation artifacts, with the fallback
   pulling in the legitimately-titled rows — which would invert the reading. Untested.

**⚰️ ASM #41 IS NOT CLOSED BY THIS.** The fallback on `'amazing spider man'` INFLATES, so it is
probably not the deflation mechanism behind the ~$47 figure. That implies a **separate defect on
thin-data keys**. Do not let it be closed out because a larger finding landed in the same
investigation.

**Scripts (all untracked, uncommitted):** `scripts/cp1_confidence_measure.py`,
`scripts/cp1_fallback_audit.py`, `scripts/cp1_nesting_audit.py`, outputs in `scripts/cp1_output/`.

### 🔜 ON RESUME — priority order (Mike, 2026-08-04)

**0. CP-1 measurement — read the tables first.** In order: Step 3A three-seed spread · Step 4 bucket
table (`CI%med` / `CIraw%` / `narrow` / `noCI`) · Step 5 sensitivity · the narrow<0 count. Then:
**D2 threshold setting** (n=7 CI floor is the leading Low-boundary candidate), and **D4 (ROI verdict
behaviour at Low)**, which is decidable independently and may go first. No production changes have
been made; everything so far is measurement.


1. **Cross-project canon version control.** Scope accepted in shape. ⚠️ **TWO DECISIONS ARE MIKE'S
   AND UNMADE:** (a) whether the canon moves out of the tool-managed `.claude` tree entirely;
   (b) whether to go straight to option C or stage A → B → C. **`.gitignore` with `~$*` goes in the
   INITIAL commit, not after** — once the Office owner file is in history it is permanent.
   ⛔ **DO NOT INITIALIZE ANYTHING UNTIL MIKE DECIDES.**
2. **Phase 2** — scoped and specced below: view extension with the `created_at` **UTC cast recorded
   as chosen rather than inherited**, `grade`'s coverage asymmetry stated **in the `DB_SCHEMA` entry
   itself**, `source_id` → **`listing_id`**, and the `market_sales` revoke, all as ONE unit with the
   ordering **inverted from Phase 1** (deploy the prompt change first, revoke after).
3. **`.claude/worktrees` untrack** — commands prepared below; behind nothing.

**Everything else is in Todoist under Slab Worthy:** `git gc`, the sync-check script, Phase 3, the
polysemy audit, `graded_comics` identification, R2 close-out, `R2_CUTOVER_RUNBOOK.md` date drift.

⚠️ **Five tracked files are dirty and are NOT from this session's work** — `.gitignore`, `TODO.md`,
`docs/EBAY_CAPTURE_SCHEDULE.docx`, `scripts/slabguard_crosscamera_test.py`,
`tests/SlabGuardTests/TP_RESHOOT_PROTOCOL.md`. Pre-existing. Do not sweep them into a future commit
assuming they belong to the NLQ work.

⚠️ **This session-close block is uncommitted at time of writing.** `WHERE_WE_LEFT_OFF.md` went into
`3a9892f`; everything added after it is dirty. Verify with `git status` before assuming it is in
history.

---

### ✅ CLOSURE 1 — `nlq_readonly` role, shipped and verified

⚠️ Supersedes **both** earlier status blocks in this entry: "UNCOMMITTED AND UNDEPLOYED, four files
dirty" and "code PUSHED / infra NOT DONE." Both are DEAD. This table is current.

| Step | State |
|---|---|
| Commits | ✅ `8709518` (feature) + `5f2deb5` (corrections) |
| Push | ✅ `origin/main` = `5f2deb5`. **Both commits are on the remote and are no longer amendable** — the duplicate commit message across the two, and `8709518`'s stale "87.8%" figure, are permanent history. |
| `nlq_readonly` role + grants | ✅ **LIVE.** Corroborated independently from the catalog: `SELECT` on exactly the 9 tables from step 3, and **`users` absent from the table-level list** — the load-bearing condition for the `password_hash` exclusion. |
| `DATABASE_URL_NLQ` on Render | ✅ set |
| Render deploy | ✅ `5f2deb5` deployed |
| Post-deploy artifact | ✅ NLQ run returned **8 rows**; `admin_nlq_history` **row 43** landed with `result_count=8`, `execution_time_ms=3312`. **The history split works** — the query ran on the read-only role and the audit row was written on the read-write pool. |

⚠️ **The first production NLQ returned 8 rows, all `source = 'whatnot'`, from `market_sales` alone.**
That is the corpus hole producing a visibly incomplete answer in production, unprompted — and it is
the argument for Phase 1 following immediately.

### ✅ CLOSURE 2 — `all_comic_sales` filter fixed

Applied on the admin connection as `collectioncalc_db_user` (view owner). Verified from the catalog
after the fact, not by eye:

| Check | Result |
|---|---|
| Second leg emits `market_sales.source` | ✅ present |
| Literal `'whatnot'::text` | ✅ **gone** |
| `WHERE` clause | ✅ **gone** |
| First leg `'ebay'::text` | ✅ retained — correct, `ebay_sales` has no `source` column |
| View row count | **173,346** |
| `ebay_sales` + `market_sales` | 163,374 + 9,972 = **173,346**, delta **0** |
| Split by source | `ebay` 163,374 · `whatnot` 9,972 |
| ACL after vs before | ✅ **identical, 9 rows** — owner `collectioncalc_db_user` (arwdDxtm) + `do_readonly=r`. `CREATE OR REPLACE` kept the relation OID and `relacl`; nothing gained, nothing lost. |

- **Rollback not needed.** The count criterion held exactly, so the filter was provably doing nothing.
- ⚠️ **The row counts are NOT the evidence.** While `market_sales` stays 100% Whatnot, the output is
  byte-identical whether `source` is a literal or a column reference. **The `pg_get_viewdef` text is
  the only thing that proves the change took**; the counts only prove nothing broke.
- **`datadog` needed nothing** — verified it holds **no object grants at all** in schema `public`, so
  it cannot read the view through a grant. Consistent with the Datadog PG integration reading
  `pg_stat_*` via role membership. The "unknown consumer" flag is CLOSED.
- **No monitor was needed after all.** The originally-proposed loud check (non-Whatnot rows in
  `market_sales`) exists to detect a silent drop. Deriving the label instead of asserting it removes
  the failure mode rather than observing it.

### 🔍 THE LITERAL-VS-COLUMN FINDING — caught in implementation, missed in scoping

**The approved scope was "remove the `WHERE` clause only." That scope was incomplete and would have
shipped a new bug while closing an old one.**

The second leg did not read `market_sales.source`. It emitted a **hardcoded literal**:

```sql
SELECT 'whatnot'::text AS source,  -- literal, not the column
   ... FROM market_sales
 WHERE market_sales.source = 'whatnot'::text;
```

The `WHERE` and the literal encoded the *same premise* in two places. Removing only the `WHERE` would
have admitted a future `mercari` row **labelled `source = 'whatnot'`** — converting a silent **drop**
into a silent **mislabel**, which is strictly worse: a dropped row shrinks a comp pool and is
recoverable; a mislabelled row poisons one and compounds (same asymmetry as L-SW-2026-009).

Found only when the full view definition was read to write the replacement statement — the scoping
pass had worked from the `WHERE` clause alone. Recorded as **[[L-SW-2026-019]]**.

⚠️ **`migrations/nlq_readonly_role.sql` step 2 was wrong in `8709518`** — it said `DATABASE collectioncalc`.
The database is **`collectioncalc_db`**. Fixed in `5f2deb5`. Anyone running the version from `8709518`
will error at step 2.

### Why

The two existing guards do not hold. The keyword denylist (`insert|update|delete|drop|truncate|alter|
grant|revoke`) has **no `create` entry**, and psycopg2 executes multi-statement strings — so
`SELECT 1; CREATE TABLE x AS SELECT * FROM users` passed both the `SELECT`-prefix check and the
denylist, and ran on the read-write role. The denylist is retained as the first layer; the role is the
layer that holds when it doesn't.

### 🔑 MANUAL PREREQUISITES — NOT REPRODUCIBLE FROM THIS REPO

Neither exists in version control. A fresh clone + deploy does **not** produce them, and the code
**fails closed** without them (`/api/admin/nlq` returns *"NLQ read-only role not configured"*; the rest
of the app is unaffected).

1. **The `nlq_readonly` Postgres role and its grants** — created by hand in DBeaver. Shape:
   - `CREATE ROLE nlq_readonly WITH LOGIN PASSWORD '<generated by Mike, never in chat or repo>'`
   - `GRANT CONNECT` on the database, `GRANT USAGE` on schema `public`
   - Table-level `GRANT SELECT` on **9** of the 10 `DB_SCHEMA` tables: `beta_codes`, `request_logs`,
     `api_usage`, `market_sales`, `collections`, `search_cache`, `comic_registry`,
     `sighting_reports`, `blocked_reporters`
   - **`users` is column-level only, excluding `password_hash`**, granted via a `DO` block that reads
     `information_schema.columns` — never a typed list. Verified against the live catalog 2026-08-04:
     `users` has **32** columns; `DB_SCHEMA` lists 11 and `DATABASE_PRODUCTION.md` lists 26. Both
     sources lag the database.
   - ⚠️ **`users` must NEVER be added to the table-level `GRANT SELECT` list.** Table and column
     privileges are **additive**: a table-level grant is not diminished by the column-level one, so
     adding `users` back there silently kills the `password_hash` exclusion with no error and no
     visible change. There is no column-level revoke that undoes it.
   - Role-level guards: `statement_timeout = '15s'`,
     `idle_in_transaction_session_timeout = '30s'`, `default_transaction_read_only = on`.
     Timeout lives on the **role**, not in code, so a code edit cannot drop it.
2. **`DATABASE_URL_NLQ` on the `collectioncalc-docker` Render service** — same host/db as
   `DATABASE_URL`, user `nlq_readonly`, `?sslmode=require`. Documented in
   `docs/technical/ARCHITECTURE.txt`. Per L-SW-2026-004 the env change needs the redeploy **and** a
   fresh shell before any check reads it.

✅ **RESOLVED — the grants SQL is committed as `migrations/nlq_readonly_role.sql`** (Mike, 2026-08-04).
Supersedes "the grants SQL exists only in the session transcript / decision pending," written earlier
in this same entry. The file carries a **placeholder** password — generate a real one at run time and
never commit it. Nothing runs the file automatically: it is not wired into any migration runner and
step 1 is not idempotent (it errors if the role already exists). The role itself still does not live
in version control — only the recipe does.

### What changed (5 files — NOT shipped)

| File | Change |
|---|---|
| `db.py` | New `get_db_readonly()`: unpooled (a second pool would add `DB_POOL_MAX x workers` against `max_connections=103` for a few admin queries/day), `RealDictCursor`, `set_session(readonly=True)` as an independent second guard. **Fails closed** — raises if `DATABASE_URL_NLQ` is unset rather than falling back to `DATABASE_URL`. |
| `admin.py` | `get_readonly_connection()` delegating to it; `_log_nlq_history()` (history INSERT moved to the read-write pool, never raises); execute-block now uses the read-only connection, closes it, then logs. |
| `admin.py` | Known-limitation comment above `DB_SCHEMA` — see below. The prompt string itself is **byte-identical** (3,609 chars); the comment sits outside it. |
| `docs/technical/ARCHITECTURE.txt` | `DATABASE_URL_NLQ` row in the Core env-var table. |
| `migrations/nlq_readonly_role.sql` | **NEW.** The role + grants recipe, hand-run in DBeaver. Placeholder password. Carries the `users`-exclusion warning and the verification block inline. |

⚠️ **`natural_language_query`'s prompt construction and response extraction were deliberately not
touched** (Mike's constraint). The model still returns raw SQL text that is string-munged for markdown
fences — that shape is unchanged and was explicitly **not** re-scoped.

### 📋 KNOWN LIMITATION — LOGGED, DELIBERATELY NOT FIXED

`DB_SCHEMA` is not the database, in two ways, both now recorded in a comment at `admin.py`:

1. **The valuation corpus is two tables and only one is described.** Live counts 2026-08-04:
   `ebay_sales` **163,374 rows (94.2%)** is absent; `market_sales` **9,972 (5.8%)** is 100% Whatnot.
   NLQ questions about sales volume, price history or coverage answer from **under 6%** of the corpus
   **and read as complete**. `ebay_sales` is also **not granted** to `nlq_readonly`, so prompt and
   grants stay consistent — the model cannot query what it cannot see.
   ⚠️ **The 71,652-row / 87.8% figures in L-SW-2026-014 are STALE** (measured 2026-08-01); `ebay_sales`
   has more than doubled since. The lesson's *mechanism* is unchanged and still correct — only its
   cited counts are out of date. Not edited here; flagged for Mike.
   ⚠️ **A view `all_comic_sales` already UNIONs both tables** — 15 columns, 173,346 rows, `source`
   discriminator ('ebay' / Whatnot). Described nowhere, granted to nobody. Found 2026-08-04.
2. **Scope and column lists both lag the live database.** Verified read-only against the live catalog
   2026-08-04: `public` holds **34 base tables + 5 views, 472 columns**. `DB_SCHEMA` describes **10
   tables** — so NLQ is blind to 24 of them (19 excluding the five `_bak_*_20260615` backup tables
   left over from the June R2 cutover). Per-table: `users` 32 columns live vs 11 described,
   `market_sales` 34 vs 16, `collections` 26 vs 7. **The five views are described nowhere and are
   not granted** — consistent, but worth knowing before anyone widens the prompt.

Closing either gap is a prompt change and must be paired with a grants change in the same unit.
**Widening one without the other is the failure mode.**

### ⚠️ Known behavioural cost of the column-level grant

**`SELECT *` on `users` now fails for this role** — the expansion includes `password_hash`, which is
denied. The model writes `SELECT *` routinely, so some user-related NLQ questions will return a
permission error instead of rows. Steering the model off `SELECT *` is a prompt change; not done.
**Do not read the first such failure as a broken deploy.**

### Verification order (none of it run yet)

1. Grants in DBeaver, then the positive-control block: `SELECT id, email, plan FROM users LIMIT 3`
   and `SELECT count(*) FROM market_sales` must **succeed** (proving the role can return a hit,
   L-2026-024) before the refusals count as evidence — `SELECT password_hash FROM users`,
   `SELECT * FROM users`, an `INSERT`, a `CREATE TABLE AS`, `SELECT count(*) FROM ebay_sales`, and
   `SELECT count(*) FROM admin_nlq_history` must **all** error.
2. Confirm grants landed: `information_schema.column_privileges` for `nlq_readonly` on `users` must
   list the columns and **must not contain `password_hash`**; `pg_roles.rolconfig` must show all
   three role-level settings.
3. `DATABASE_URL_NLQ` on Render → redeploy → **Render Events shows the pushed commit hash**
   (never `/health` `version` — decoy, L-SW-2026-017). No Cloudflare purge; nothing frontend changed.
4. Post-deploy artifact: run one NLQ from the admin panel, then confirm the audit row landed —
   `SELECT id, admin_id, result_count FROM admin_nlq_history ORDER BY id DESC LIMIT 3`. Query returns
   but no row = the split's write half is broken; check Render logs for `[NLQ] history logging failed`.

### 📐 FOLLOW-UP 1 — DB_SCHEMA drift reconciliation: SCOPED AND DECIDED, NOT STARTED

Decisions (Mike, 2026-08-04). **The prompt has not been touched** — `DB_SCHEMA` is still 3,609 chars.

- **Describe 16 objects:** `all_comic_sales` (view) · `request_logs` · `users` · `collections` ·
  `comic_registry` · `api_usage` · `lookup_demand` · `waitlist` · `grade_submissions` ·
  `user_feedback` · `content_incidents` · `sighting_reports` · `blocked_reporters` · `match_reports`
  · plus views `signature_review_queue`, `signature_confusion_summary`.
- ⚰️ **`beta_codes` RETIRED from the prompt** — beta gating died 2026-07-29; describing a dead
  subsystem is drift by definition. Supersedes its Tier A placement earlier in this scope.
- **Tier B resolved to the two signature VIEWS only.** The three signature base tables stay out.
- **Tier C excluded, with reasons on record:** `password_resets` + `ebay_tokens` (credential
  material) · `search_cache` + `dependency_alerts` (machinery) · `slabguard_*` ×3 (parked
  subsystem) · `graded_comics` (**unidentified** — 12 cols, 1 row, in no doc; flagged not guessed) ·
  raw `market_sales`/`ebay_sales` (superseded by the view) · **`admin_nlq_history` — NLQ must not
  query its own audit log.**
- **Phasing: 1 → 2 → sync-check → 3.** Build the invariant before adding the batch that would
  violate it. The invariant: *objects described in `DB_SCHEMA` == objects granted in
  `nlq_readonly_role.sql`*, minus an explicit `DESCRIBED_BUT_DENIED` list with a reason per entry,
  enforced by a script that exits non-zero on drift (the observable artifact, L-SW-2026-017).

⚠️ **CORRECTION — the selection criterion was stated wrong and Mike caught it.** The first draft
excluded objects on **row count** (naming `match_reports`, `signature_matches`) while keeping
0-row `sighting_reports`/`blocked_reporters` as "semantically load-bearing" — self-contradictory.
**The real rule: an object belongs if a plausible admin question maps onto it and the model needs its
structure to answer.** Row count is evidence about whether a subsystem is *in use*, never a criterion.
An empty table representing a reachable domain event answers "how many sightings?" with a correct `0`.
Consequence: **`match_reports` moved back IN.** Do not re-derive these lists from row counts.

### 📦 PHASE 2 UNIT — view extension + `market_sales` revoke, SHIP TOGETHER

Decided 2026-08-04: **revoking `market_sales` from `nlq_readonly` is the fix, not prompt steering.**
Reason (Mike): steering is probabilistic and the model picked `market_sales` unprompted on the first
production NLQ run. Revoking makes the wrong path fail loudly.

**⚠️ ORDERING — INVERSE OF PHASE 1. Execute in exactly this sequence:**

| # | Step | Where |
|---|---|---|
| 1 | Extend `all_comic_sales` (`CREATE OR REPLACE VIEW`, append columns) | DBeaver, admin |
| 2 | Remove `market_sales`'s entry from `DB_SCHEMA`; add the new view columns | `admin.py` |
| 3 | Remove `market_sales` from step 3 of the grants file | `migrations/nlq_readonly_role.sql` |
| 4 | Commit + push + **deploy the prompt change** | Render |
| 5 | **THEN** `REVOKE SELECT ON market_sales FROM nlq_readonly;` | DBeaver, admin |

**Phase 1 grants BEFORE deploy; Phase 2 revokes AFTER deploy.** Reversed, every sales question errors
during the window between revoke and deploy. The rule generalises: *widen access before the prompt
that uses it; narrow access after the prompt that stopped using it.*

**Verified column findings (live catalog, 2026-08-04) — what can and cannot join the view:**

| Column | eBay side | Verdict |
|---|---|---|
| `is_facsimile` | `is_facsimile` boolean, 163,374/163,374 | ✅ ADD — clean |
| `is_reprint` | `is_reprint` boolean, 163,374/163,374 | ✅ ADD — clean |
| `grade` | `grade` numeric, 22,923/163,374 (14.0%) | ✅ ADD — but Whatnot is 48.9% populated; unioned averages skew Whatnot. `DB_SCHEMA` must say so. |
| `created_at` | `created_at` **`timestamp` WITHOUT tz** vs Whatnot `timestamptz` | ✅ ADD — **DECIDED: cast the eBay leg explicitly to UTC** (`created_at AT TIME ZONE 'UTC'`), written into the view definition, never left to the session `TimeZone`. |
| `source_id` | **`ebay_item_id`** varchar, 163,374/163,374 | ✅ ADD — **DECIDED: the merged column is named `listing_id`**, not `source_id` (which reads as related to `source`). |

**⏱️ `created_at` TIMEZONE DECISION — Mike, 2026-08-04.** The eBay leg is `timestamp` without a zone;
the Whatnot leg is `timestamptz`. A bare union resolves to `timestamptz` by interpreting the eBay
values in whatever the session's `TimeZone` happens to be — **a timezone inherited rather than
chosen.** DECIDED: **UTC, cast explicitly in the view definition**, and **the `DB_SCHEMA` entry must
state that the eBay leg's timezone was chosen, not inherited**, so the next reader does not assume
the value carried a zone all along. This is cross-project **L-2026-023** at the schema layer — *a
timestamp is defined by its writer, not its name* — and the same asserted-vs-derived shape as
[[L-SW-2026-019]].

**📊 `grade` COVERAGE ASYMMETRY — must go in the `DB_SCHEMA` entry itself, not just these notes.**
eBay `grade` is populated in **22,923 / 163,374 (14.0%)**; Whatnot in **4,879 / 9,972 (48.9%)**. An
unqualified `AVG(grade)` over the view silently weights toward Whatnot by a factor of ~3.5 in
population rate. The prompt must say so **in the same steering voice** used to point sales questions
away from `market_sales` — a note in the session log does not reach the model.

**❌ CANNOT BE ADDED — no eBay equivalent, and no honest fill exists:**

- **`grade_source`** (Whatnot: `seller_verbal` 2,775 · `vision_cover` 1,558 · `slab_label` 228 ·
  `dom` 154 · NULL 5,257). Describes how the **capture pipeline** obtained the grade. eBay records no
  such concept. NULL-filling would assert "eBay grades have no source," which is **false** — they have
  one, it simply is not stored.
- **`slab_type`** (Whatnot: `raw` 4,294 · `CGC` 480 · `slabbed` 57 · `CBCS` 25 · NULL 5,094). eBay's
  nearest is `graded` boolean + `grading_company`. Synthesising
  `CASE WHEN graded THEN grading_company ELSE 'raw' END` **manufactures** a value to fill a column —
  the literal-vs-column problem run forwards. **Do not.**

⚠️ **THEREFORE THE REVOKE HAS A REAL, PERMANENT COST — AND IT IS ACCEPTED.**

**DECIDED (Mike, 2026-08-04): `grade_source` and `slab_type` are KNOWINGLY UNREACHABLE to NLQ. Do not
re-litigate this.** Both are ~49% populated and are **Whatnot capture-pipeline metadata, not comp
data** — `grade_source` records *how the grade was obtained* (`seller_verbal`, `vision_cover`,
`slab_label`, `dom`), a concept eBay does not record at all. They cannot join the view because any
fill would be fabricated, and they cannot survive the revoke because the revoke is the point.

The rejected alternative, on the record so it is not re-proposed: a **narrow column-level grant** on
`market_sales` limited to `id`/`source`/`grade_source`/`slab_type` would keep them reachable while
denying `price`/`sold_at`/`canonical_title`, making the table useless for corpus questions. **Rejected
— it costs more in grants-file complexity than it returns** (Mike). If these columns are ever needed
again, the answer is an admin query on the read-write connection, not a widening of `nlq_readonly`.

### 🏷️ LOGGED, NOT CHANGED — the 2026-08-01 copy verdict rests on a figure that has since moved

This entry's line ~728 records: *"12.2% across 1,603 titles is a meaningful share, so the copy stands
unchanged"* — the tombstone from the Slab Guard claims audit for `waitlist-confirmed.html`'s "we track
real sales data across eBay and Whatnot." **The split is now 94.2% / 5.8%, so that verdict now reads
as 5.8%,** and the phrasing question parked alongside it (whether "across eBay and Whatnot" implies
more parity than the real ratio) is sharper at 94/6 than it was at 88/12.

**Mike, 2026-08-04: LOG IT, DO NOT CHANGE IT.** This is a separate decision about public claims and is
not part of the NLQ work. The copy is unchanged and the original tombstone stands as written. Recorded
here only so the next claims sweep knows the underlying figure moved.

### 🚧 PHASE 1 BLOCKER — the `all_comic_sales` filter (Mike's call: blocker, not caveat)

The view's second leg carries `WHERE market_sales.source = 'whatnot'`. Proposing it as the fix for a
silent corpus hole while it installs a second one is not shippable. Measured 2026-08-04:

- `all_comic_sales` **173,346** = `ebay_sales` 163,374 + `market_sales` 9,972. **0 rows dropped.**
- `market_sales.source` is **100% `whatnot`** (9,972); `source IS DISTINCT FROM 'whatnot'` = 0.
- `source` is **NOT NULL with no column default** — the `'whatnot'` default is application-side
  (`sales_market.py:127`), as L-SW-2026-014 says. No NULL-drop edge case exists.
- **Verdict: vestigial today, landmine later.** Its only effect is prospective — the first
  non-Whatnot row ever written vanishes from the corpus with no error.
- **Recommended fix: `CREATE OR REPLACE VIEW` without the filter.** Column names/types/order
  unchanged, so grants survive. Verification is its own positive control: the row count must be
  **173,346 before and after**; any difference falsifies the premise.
- **Blast radius: zero in the repo** — `all_comic_sales` appears in no route, module, script or
  extension. Unknown: ad-hoc DBeaver use and whatever the `datadog` role queries.
- If the filter must instead STAY, Mike requires a **loud check, not a comment** — home would be
  `dependency_monitor.py`, asserting the non-Whatnot count is 0, reusing the dedup/stability-window
  machinery from L-SW-2026-013. Removal is smaller and deletes the need for it.
- **PENDING MIKE'S GO. Nothing executed.**

### 🗄️ `_bak_*_20260615` — RECOMMENDATION: KEEP. NOTHING DROPPED.

Five 2-column snapshots from the June 15 R2 cutover, 60,447 rows total. `R2_CUTOVER_RUNBOOK.md`
**Step 6 (line 284) already plans the exact `DROP TABLE`**, gated on "once confident (separate
session)." Verified read-only 2026-08-04: Step 5's condition holds — **0 residual `pub-*.r2.dev`
references** across all five columns, positive control fired (207 / 4,053 / 138,675 http URLs
present, so the probe can match). Snapshot ids are still **100% aligned** with live rows
(50,555/50,555 and 9,560/9,560), so rollback remains mechanically valid.

**But the drop is half a decision.** Step 6 pairs it with disabling the r2.dev public development
URL, and whether that URL is still enabled is a **Cloudflare fact not visible from the repo or DB**.
Both actions answer the same question. **Recommendation: one deliberate "R2 close-out" item that
disables r2.dev and drops the five tables together.** Holding costs nothing. They stay out of the
NLQ prompt and grants regardless.

⚠️ Drift found while reading that runbook: line 6-7 still states "soft launch is **August 4, 2026**",
which is DEAD per `CLAUDE.md` — the gate is first cold traffic, unscheduled. Not edited.

### 🧹 GIT HYGIENE — `.claude` untrack: SCOPED AND DECIDED, NOT RUN

`git status` was unusable (**8,461 lines**) because `61290bf` — *"Restore dollar sign favicon, remove
MASSE 8-ball from all pages"*, Mike Berry, **2026-03-19**, **8,451 files / 1,486,879 insertions** —
swept the whole agent directory in. 8,428 of its additions were `.claude/` paths; 15 were not. An
`add -A` in everything but name. `CLAUDE.md` itself was added by that same commit and carries the
"NEVER `git add -A` blindly" rule, apparently written the same morning.

- **8,429 files tracked under `.claude`: 8,424 `worktrees/` · 4 `skills/` · 1 `plans/`.**
- `.gitignore` lists `.claude/` **twice** (lines 69, 70). `git check-ignore -v` confirms it is live
  and matching — and irrelevant, because **gitignore does not affect already-tracked files.**
- `git worktree list` shows **18 live registered worktrees**, all present on disk. **`zen-wozniak`,
  the one that flooded the status, is NOT among them** — a genuine orphan, deleted from disk while
  still tracked.
- ⚠️ **Mike had already run `git rm -r --cached .claude` before asking for the scope** (his note,
  2026-08-04), which is why 8,429 deletions were found **staged** in the index. **That staging
  included the 4 `SKILL.md` files** — `deploy-tfo`, `health`, `lesson`, `stripe-test`, all referenced
  by `CLAUDE.md`. A plain `git commit` would have swept them out silently. **This is the finding that
  mattered; the rest is bookkeeping.**
- **DECIDED:** untrack `.claude/worktrees/` and `.claude/plans/purrfect-squishing-lake.md` only;
  **keep `.claude/skills/` tracked.**
- `.gitignore` must be restructured, not patched: `.claude/` with a trailing slash excludes the
  directory outright and git will not descend into it, so a `!.claude/skills/` negation underneath
  silently does nothing. Working form is `.claude/*` + `!.claude/skills/`, duplicate removed.
- `git rm -r --cached` is the right instrument and **removes nothing from disk**; it does not
  deregister or damage the 18 worktrees (registration lives in `.git/worktrees/`, not the index).
- **Repo-size impact: none.** Blobs stay in history; only a rewrite removes them, not recommended.
- **No tooling depends on those paths being tracked** — worktree isolation and skill loading both
  work off disk, not the index.
- **Interim clean status, verified (8,461 → 32 lines, positive control holds):**
  `git status --short -- ':(exclude).claude'`
- Commands prepared and handed to Mike. **BEHIND the role deploy. Nothing run.**

### 🧊 LOGGED, NOT RUN — `git gc`

`git count-objects -vH`: **5,144 loose objects, 119.66 MiB, `in-pack: 0`** — this repo has never been
packed. A `git gc` would likely shrink it substantially. **Mike's instruction 2026-08-04: log it, do
not run it. Separate item.** Unrelated to the `.claude` untrack.

### 📉 CORPUS FIGURES CORRECTED

`ebay_sales` is **163,374** rows, not the 71,652 recorded 2026-08-01. Split is **94.2% / 5.8%**, not
87.8% / 12.2%. ⚠️ **L-SW-2026-014's cited counts are stale** — its mechanism is unchanged and still
correct. `8709518`'s commit message says 87.8% and is now pushed, so that figure is permanent in
history. Not edited in `LESSONS.md`; flagged for Mike.

### 🔜 FOLLOW-UP 2 — polysemy audit: NOT STARTED

Held until the drift work closes (Mike's sequencing). Scope when opened: all **472 columns**, terms
that denote different things in different tables. Seed set: `grade` (NUMERIC in `market_sales`, TEXT
in `collections`), `source`, `value`, `status`, `title`, `confidence`. Value is independent of NLQ —
it documents the data model and locates where wrong joins are most likely today.

---

## 2026-08-03 (EVENING) — ✅ **SIGN-IN ENTRY POINT FIXED, SHIPPED AND VERIFIED LIVE; WHATNOT VISION 401 DIAGNOSED**

**MOST RECENT CHANGE (Rule 5): `/login.html`'s default panel is now `loginPanel`, selected by an explicit
branch; signup is reached via `?mode=signup`. Supersedes "`signupPanel` is now the default panel" (set
2026-07-29 by `b981789`).** Frontend only — **purged, no Render deploy.**

**Shipped:** `8f113c9` (fix) · `3a21ca1` (lessons + state) · `88700f8` (tombstone-quoting fix).
⚰️ **Do NOT re-present any command block from this session — the work is shipped and purged.**

**✅ Verified on live slabworthy.com at 375×812, by clicking the actual link:** Sign In on the landing
page → `/login` → `loginPanel`, "Welcome Back", submit "Log In" at **y=688**, Sign Up tab at **y=254** —
both above the 812 fold, no scrolling. `verifyingPanel` present. Was: `signupPanel`, "Create Account",
toggle at y=1046. Purge sweep green on all four pages (NEW present AND OLD absent, comments stripped).

### 🧯 Two verification findings from the purge check — both false alarms, opposite mechanisms

**1. A purge check run too soon reports a FALSE FAILURE.** The first sweep read `pricing.html` at
**35,642 bytes** with 0 matches; minutes later it was **35,654** with 1 — a 12-byte delta, exactly
`?mode=signup`. The page was mid-propagation. Confirmed it was not a ship failure before re-running:
HEAD contained the change, `main` was in sync with `origin/main`, and a cache-busted fetch matched the
plain one. **The artifact and the check were both correct; only the timing was wrong.** Companion to
L-SW-2026-017 — a decoy artifact reports false success, a premature check reports false failure.
**Wait a minute before re-checking, and diff byte counts before suspecting the deploy.**

**2. A tombstone that quotes the string it retires trips its own audit.** The same sweep reported the
dead beta-code phrase live in `waitlist.html`; it was matching the explanatory comment added in the very
commit that removed it. Rendered copy was correct throughout. Fixed in `88700f8` (comment now describes
rather than quotes) and recorded as a **corollary to L-SW-2026-015**: *a HIT is not a failure until the
match is confirmed to be the live instance* — the mirror of 015's false-negative rule. Sweeps should
strip comment nodes and assert NEW-present alongside OLD-absent.

### ⚰️ TOMBSTONE — the Unit D attribution was WRONG, and the correct framing matters

- **DEAD:** *"Sign In lands on Create Account because Unit D (`b981789`) made signup the default panel."*
- **REPLACED BY:** the defect **predates** `b981789`. Before it the default was `betaCodePanel` — also
  not the login form. **"Sign In" has never reached the login form.**
- **REASON:** `b981789` changed **severity, not cause.** The beta panel was one input and a button, so
  its identical "Already have an account? Log in" link sat on-screen; the six-field signup form pushed
  that same link **234px below the fold at 375×812** (202px at 1440×900 — measured live, both viewports).
  A mildly wrong landing became an unreachable one.
- **SUPERSEDES:** any framing that scopes this to Unit D. ⚠️ **A fix aimed at Unit D alone would have
  left the gap in place** — which is precisely why this is recorded as a tombstone and not a note.

### ⚰️ `?signup=true` was DEAD from `cbd80d7` (2026-02-28) to 2026-08-03 — five months

`index.html`'s Sign Up link carried it; `login.html` **never** contained a reader (`git log -S` finds no
match in its whole history). It "worked" only because signup was the default. It **hid the real defect**
by supplying false evidence that panel selection existed. Now an **alias** for `?mode=signup` and it must
STAY one — the link is live, may be bookmarked, and pages get cached; deleting it would make it dead a
second time, in the direction that breaks signup. New lesson **L-SW-2026-018**; instance of L-SW-2026-016
extended from display surfaces to contracts.

### What changed (4 files — SHIPPED, purged, verified live; see hashes above)

| Part | Change | Files |
|---|---|---|
| A | Explicit `?mode=login\|signup` selector; default = login; `?signup=true` kept as alias; `?invite=` forces signup | `login.html` |
| B | Two-button tab bar at the top of both panels, reusing the **orphaned** `.tabs`/`.tab` CSS (present since forever, no markup ever used it) | `login.html` |
| C | `?mode=signup` on the four acquisition CTAs | `index.html` ×3, `pricing.html` |
| D | `verifyingPanel` shown **synchronously** before the verify fetch; `proceed()` given a terminal else-branch | `login.html` |
| — | Stale "Already have a beta code?" → "Already have an account?" (beta gating died 2026-07-29) | `waitlist.html` |

**Verified locally over HTTP** (`file://` strips query strings — a near-miss false pass, L-SW-2026-015):
`?mode=signup`→signup · `?signup=true`→signup · `?invite=`→signup + URL cleaned · `?token=`→**never
signup**, lands loginPanel + server message · bare→login. Tabs and footer links toggle both ways. At
375×812 **both panels put the toggle at y=254, above the 812 fold**; the login submit is at y=689, so the
whole login flow fits without scrolling.

⚠️ **`sw.js` needs NO `CACHE_NAME` bump** — only HTML changed, and HTML is never precached (policy
rewritten 2026-07-29). No service-worker staleness risk against the purge check.

### 🔎 Whatnot valuator vision scanning — diagnosed, NOT fixed

**Real 401, not a mislabeled 403.** `request_logs` rows 199912/199915/199921: `POST /api/vision/analyze`,
**401**, `user_id NULL`, `"Authentication required"`. NULL `user_id` proves `g.user_id` was never set, so
the 403 plan gate was never reached. The extension's "Session expired" label is **correct**.

- ⚠️ **The premise "it broke yesterday" is false.** Last successful scan **2026-07-01 05:12 UTC — 34 days
  before**. Zero vision traffic in between (the two 2026-08-01 405s were GET blueprint probes). The break
  is **not datable from traffic**; it failed on first use after a month idle.
- **Leading cause: plain JWT expiry.** `JWT_EXPIRY_DAYS = 30`, and the extension's token is minted once at
  Options sign-in and **never refreshed** — no renewal path exists. Website logins don't touch
  `chrome.storage.local`. **Unproven** — needs the stored token's `exp` decoded locally.
- `a0cc9fa` **never touched `routes/vision.py`.** The message change was `88c42aa`, and it was the string
  only — gate logic byte-identical. `88c42aa`'s `billing.py` hunks did not touch `get_user_plan` or
  `check_feature_access`; `COMING_SOON_PLANS` is used only in `create_checkout_session`.
- **Mike = `users.id 3`, plan `free`, `subscription_status canceled`, `is_admin TRUE`.** Plan-wise he
  can't reach vision; the admin bypass grants it. But **`settings.js:158` computes
  `hasVision = ['guard','dealer'].includes(plan)` with no admin term, and `/api/billing/my-plan` doesn't
  return `is_admin`** — so once he signs back in the Options page will tell him he isn't entitled while
  the server grants him access. **Open.**
- ⚠️ **The claims audit's "not site-deployed, leave it" call on `CCExtensions/whatnot-valuator/settings.html:145`
  was WRONG (Mike, 2026-08-03)** — he uses the extension. Three strings still advertise Guard/Dealer, a
  tier `COMING_SOON_PLANS` refuses at checkout: `settings.html:145`, `settings.js:165` (with a live
  Upgrade link), `vision.js:136`. `content.js:95`'s modal is a fourth, different defect — it fires on
  *no token* while asserting a *plan* requirement it never checked. **All open.**

**Open on the extension — the full list, none started:**
1. **Refresh-on-use auth.** The token is minted once and never renewed; a 30-day expiry with no refresh
   path guarantees this recurs.
2. **`validateToken` fails OPEN** (`settings.js:126`) — a network exception returns `true`, so an expired
   token survives an Options visit made while Render is cold-starting. If Options shows signed-in rather
   than the login form, that is this path, not a valid token.
3. **The "Sign In Required" modal** (`content.js:95`) asserts a plan requirement it never checks — it
   fires on *no token*.
4. **Three Guard/Dealer strings** advertising a tier checkout refuses, one with a live Upgrade link.
5. **Options-page entitlement drift** — `settings.js:158` has no admin term and `/api/billing/my-plan`
   returns no `is_admin`, so it *cannot* be correct for an admin without an API change.

⚠️ Any fix here **must bump `CCExtensions/whatnot-valuator/manifest.json`** (currently **2.42.0**, last
bumped `86aff76` 2026-02-23). No code has changed since that commit and the tree is clean for that
directory, so there is no stale-reload blind window today — the bump is what keeps it that way.

### 📄 BO primer — rewritten as a DRAFT, not yet the mirror

`docs/SW_BO_PRIMER_DRAFT_2026-08-03.md` (untracked at time of writing). Full rewrite superseding the
2026-05-26 primer. ⚠️ **Read it before replacing `docs/SW_BO_PRIMER.md`** — the replacement block was
prepared but deliberately not run, and it consumes the draft path. Neither file is authoritative; BO
project storage is Mike's copy.

**Corpus verified live during the rewrite: `ebay_sales` 152,316 + `market_sales` 9,972 = 162,288** — up
from 125,720 at the 03:08 UTC snapshot the same day, and 105,132 the day before. **The draft instructs BO
to re-query rather than quote any numeric figure**, which is the only durable instruction for a number
moving this fast.

⚠️ **On the depth figures — do NOT let the "capture makes it worse" trend harden into a belief.** The
CP-1 doc's two snapshots went 84.6% → 85.3% (≤2 comps); an independent reproduction the same evening on
the larger corpus read **83.9%**, on filters that follow §10's recipe but are **not** a byte-for-byte
match to the doc's query. Three points, two methodologies — the *magnitude* is stable and bad, the trend
line is not established. **The durable finding: roughly five in six comp cells rest on one or two sales,
and of ~4,600 books only ~400–500 have any grade backed by three or more comps.** The structural argument
(scarce Bronze Age keys arrive as fresh 1-comp cells) stands on its own without the trend.

### 🔁 SYSTEMATIC FINDING — backend correct, user-facing surfaces lagging

**Three instances in one night, all the same shape:** the server was right and the surface a user touches
was not.

1. **`login.html`** — the panel logic never selected login; every "Sign In" link on the site landed on a
   signup form, for months.
2. **`waitlist.html`** — the acquisition page asked for a beta code, gone since 2026-07-29.
3. **The Whatnot extension** — still sells Guard/Dealer, pulled from sale 2026-08-01, with a live Upgrade
   link to a checkout that refuses it.

⚠️ **In every case the backend decision had already been made and correctly implemented.** The lag is
entirely in copy and routing, which no server-side test observes.

**Standing recommendation (Mike, 2026-08-03): run a user-facing surface sweep after ANY tier or gate
change — not only before launch.** The trigger is the decision, not the calendar; each tier or gate change
will produce new instances the same way these three did. 🔼 **Proposed as a lesson candidate (L-SW-2026-019)
— not minted, Mike's call.**

---

**Session UUID:** `638118e4-6bdd-4ef4-93b4-e89525e1f1a6`

---

## 2026-08-03 (SESSION CLOSE) — ✅ **FOUR UNITS SHIPPED; CAPTURE WRITE PATH 41.5s → SUB-SECOND, MEASURED**

**MOST RECENT CHANGE (Rule 5): the CP-1 remediation order was REVISED — canonical "of" fragmentation is now item 1, displacing signed-comp contamination. Supersedes the order set 2026-08-02.** Reason: fragmentation's cost **compounds with capture activity** (the work being done most), while signed contamination is stationary at ~7.8%. Tombstone + full order live in `docs/technical/CP1_STATE_OF_PLAY.md` §9.

⚰️ **ALSO DEAD, same session:** *"confidence is computed and stored but displayed nowhere"* — see the tombstone at the CP-1 section below. It was false.

### What shipped

| # | Unit | Files | Commit |
|---|---|---|---|
| 1 | Batch write path: one commit per batch + R2 backup off the request path | `routes/sales_ebay.py`, `docs/technical/ARCHITECTURE.txt` | **`a80b5cd`** |
| 2 | Extension: honest sync-failure reporting + unsynced-buffer warning | `CCExtensions/ebay-collector/content.js`, `popup.js` | **`b4ba1ba`** |
| 3 | CP-1 audit recorded as a durable artifact | `docs/technical/CP1_STATE_OF_PLAY.md` | **`a176d3d`** |
| 4 | Bulk insert via `execute_values`, per-row loop kept as fallback | `routes/sales_ebay.py` | **`680f243`** |

⚠️ Unit 2 is **extension-only — no Render deploy.** It takes effect only when the unpacked extension is reloaded in `chrome://extensions`.

### ✅ Write path — measured, not asserted

| Version | Commit | Measured |
|---|---|---|
| v1 original (commit per row + inline R2) | — | **41,552 ms** avg / 184,417 ms max |
| v2 (one commit per batch, R2 async) | `a80b5cd` | **9,721 ms** avg / 40,055 ms max |
| v3 (bulk `execute_values`) | `680f243` | **547–940 ms** avg / 3,233 ms max |

```
19:52   7 reqs  avg 44,083ms   <- last v2 minute
19:57  12 reqs  avg    848ms  max 2,207ms
19:58  10 reqs  avg    547ms  max 1,706ms
19:59  12 reqs  avg    940ms  max 3,233ms
```

**~50× off the original baseline, sub-second at 10–12 req/min — heavier concurrency than any minute in the v2 data — and the self-congestion ramp is gone.** No 10s+ readings, which is the tell that the bulk path is *succeeding* rather than aborting into the per-row fallback.

⚠️ **The root cause of the original symptom was never an outage.** `request_logs` showed 293 batch POSTs, **all HTTP 200**, while the extension banner read "backend offline" — the server was completing and the client was timing out. The banner asserted a cause it never established (L-SW-2026-007), which Unit 2 fixes.

**Two things load-bearing in `routes/sales_ebay.py`, do not remove:**
1. **The per-row `SAVEPOINT` fallback.** A bare bulk statement aborts entirely on one malformed row — reintroducing the exact regression the savepoint was added to prevent. Bulk is wrapped in `SAVEPOINT sw_bulk`; any failure rolls back and re-runs the batch per-row.
2. **`ON CONFLICT` is UNTARGETED on purpose.** `ebay_sales` has **two** unique indexes — `ebay_item_id` **and** `content_hash`. A targeted clause aborts the bulk statement on a same-title/price/date collision, which is common enough (1,585 recurring `(raw_title, sale_price)` pairs) to make the fast path *slower than the loop it replaces*. Found in review, not by testing — the temp-table check had only one index and would not have caught it.

### 🔎 Three findings nobody was looking for

Full detail in `docs/technical/CP1_STATE_OF_PLAY.md` §5B / §5C / §11.

1. **Canonical "of" fragmentation** (now CP-1 item 1). "of" is dropped inconsistently, splitting comp pools. `Tomb of Dracula` exists both ways (308 rows/83 graded vs 66/23). `Master of Kung Fu` and `Savage Sword of Conan` lost it entirely, so a naturally-titled query reaches **none** of their 140 and 777 rows. Leading-`"The"` fragmentation is **NOT** affected — `title_matching._norm` strips it on both sides — so the 206 `"The"` pairs are harmless and **must not be "fixed"**. The 17-pair / 393-row figure is a **FLOOR**; sizing the universally-dropped population is part of the work. Same family as L-SW-2026-009 / L-SW-2026-011. **Found by a positive control on seven zero-result titles, per L-SW-2026-015 — not by looking for it.**
2. **The grade>10 parser bug is LIVE.** 11 → 13 rows, **5 arrived 2026-08-03**, new value `85.0`. `CGC 94` in a listing title parses as grade 94.0. Changes CP-1 item 3 from a cleanup to a cleanup **plus a parser fix**.
3. **Star Wars #1 variant stripping — the serious direction is the opposite of expected.** All 130 `is_variant` rows are **unpriceable** (excluded from every pool, routed to none). A real 35¢ variant sold at **$6,422** at grade 8.0; the regular pool median is **$272** — the owner is told $272, ~**24× under**. Leaking into the regular pool is negligible for this book (≤1% median effect). The price-variant regex at `title_normalizer.py:274` is **effectively dead code**, firing on **1 of 63** real titles because `[¢c]` consumes the "C" in "Cent".

### 📈 Corpus direction — capture volume alone will not fix confidence

Two dated snapshots in `CP1_STATE_OF_PLAY.md` (§5, §5B), deliberately **not** overwritten. `ebay_sales` 95,169 → **115,756** (+20,587) in one run — and the thin-data ratio got **worse**: cells at ≤2 comps **84.6% → 85.3%**, `medium`-on-≤2-comps **702/1,389 → 870/1,676**. Breadth grew faster than depth (+1,207 cells, only +139 reaching ≥3). Whatnot is dark: **+1 row since 2026-07-01**.

### 🧯 Two process findings recorded at close

**1. ⚠️ THE EXTENSION RAN 4.5 MONTHS OF UNVERIFIABLE RELOADS — and some past debugging may have run against stale code.**

`CCExtensions/ebay-collector/manifest.json` sat at **1.3.5 from 2026-03-19** while `content.js` changed repeatedly: the **July selector fixes** (`bbe5353`), the **hydration/MutationObserver fix**, the **`/sold/i` case-sensitivity fix** (the one that was silently rejecting 267/279 items), the **sync-honesty unit** (`b4ba1ba`), and the **counter unit** (`d3a47ff`). The extensions load **unpacked**, so reloading is a manual step with **no confirmation** — and with the version frozen, **a forgotten or failed reload was indistinguishable from a successful one.**

⚠️ **The implication is not just "we couldn't confirm."** Any debugging session in that window may have been reasoning about behaviour produced by **stale code** — including the July 16 collector diagnosis, which went through several wrong theories (hydration, then visibility filtering) before the case-sensitivity root cause. Nothing is known to be wrong because of this; the point is that **it was not knowable**, and past conclusions from that window carry that caveat.

**Same family as the two Render deploys that silently didn't fire on 2026-08-02** — an action whose completion is not observable is indistinguishable from an action that was skipped. `CLAUDE.md` already carried that warning for Render deploys; it now carries the equivalent rule for extensions.

⚰️ **FIXED FORWARD (`ed4f2a0`):** bumped to **1.4.0** (confirmed by Mike in `chrome://extensions`), and **`CLAUDE.md` now makes the bump MANDATORY** — same commit as the change, expected version stated in the ship block. Scheme documented from the existing history (1.0.4 → 1.1.0 → 1.3.5), not invented.

**2. 📋 REPO HYGIENE — a deliberate pass is owed. Not urgent; logged so it is a decision, not a drift.**

Working tree outside `.claude/worktrees/`: **4 modified, 27 untracked.**

- **Modified:** `.gitignore` · `TODO.md` · `scripts/slabguard_crosscamera_test.py` · `tests/SlabGuardTests/TP_RESHOOT_PROTOCOL.md`
- **Untracked (sets):** `docs/postmortems/` (deliberately untracked per the 2026-08-01 close — commit it deliberately in a later pass) · `tests/SlabGuardTests/` E3/TP/FP photo sets and CSVs · `tests/7_8/`, `tests/Mobile/`, `tests/SectionBTest/`, `tests/SectionDTest/`, `tests/Valuation/` · `CCImages/6_8_26_Tests/` · `DFToBSCOnvos/` · `scripts/e3_edge_sequence_test.py` · loose files: `AdminCheckjs.js`, `ebay_diff.txt`, `ebay_sig_diff.txt`, `extensioncountofsales.png`

⚠️ **Mike's framing (2026-08-03), and the reason this is logged rather than ignored:** *"File-specific staging is protecting me correctly, but it only works as protection if someone eventually looks at what's being excluded."* The per-file staging convention has held all session — nothing unintended has been swept in — but it silently accumulates the excluded set, and an unreviewed exclusion list is a place for something that mattered to hide. **The pass should decide per item: commit, gitignore, or delete.** Large binary photo sets are the main judgement call.

---

### ⏭️ Next session opens on CP-1 item 1 — canonical "of" fragmentation

Order: (1) "of" fragmentation · (2) signed-comp contamination (7.8%, 325 mixed cells, 1.73× median) · (3) grade>10 cleanup **+ parser fix** · (4) `total_graded >= 10` clause · (5) display consolidation + `README.md:11`.

---

## 2026-08-01 (SESSION CLOSE) — ✅ **SIX UNITS SHIPPED AND VERIFIED LIVE**

**MOST RECENT CHANGE (Rule 5): all six units are deployed and verified in production. Backend deploys confirmed by commit hash in Render Events — `88c42aa` (Guard checkout gate) and `a0cc9fa` (email templates), both live. Supersedes every "drafted / awaiting ship" framing below.** ⚰️ **Do NOT re-present any command block from this session; the work is shipped.**

### What shipped

| # | Unit | Files | Deploy |
|---|---|---|---|
| 1 | Guard checkout refusal + stop upselling unbuyable tiers | `routes/billing.py`, `routes/vision.py` | **`88c42aa`** — Render verified |
| 2 | Pricing rebuilt two-column + Guard/Dealer roadmap strip | `pricing.html`, `account.html`, `faq.html` | Pages purged |
| 3 | State record | `docs/sessions/WHERE_WE_LEFT_OFF.md` | — |
| 4a | Slab Guard claims — frontend | `check.html`, `app.html`, `waitlist.html`, `waitlist-confirmed.html` | Pages purged |
| 4b | Slab Guard claims — email templates | `routes/waitlist.py`, `routes/admin_routes.py`, `routes/verify.py` | **`a0cc9fa`** — Render verified |
| 4c | Fingerprinting doc tombstone | `docs/technical/FINGERPRINTING_PROJECT_SUMMARY.md` | — |
| 5 | Privacy disclosure (shipped **ahead of** pixel code, deliberately) | `privacy.html` | Purged |
| 6 | Meta Pixel | `js/pixel.js`, `js/footer.js`, `footer.js`, `js/sidebar.js`, `login.html`, `sw.js` | Purged |

**Post-deploy verification (read-only):** `/health` 200 `{"status":"ok","version":"5.6.0"}`. All four edited backend modules confirmed *imported* by app-handled JSON responses — `/api/waitlist/count` 200, `/api/verify/lookup/...` 404 JSON, `/api/admin/users` 401 JSON, `/api/vision/analyze` 405. That was the check that mattered for 4b: a broken f-string in an email template is a `SyntaxError` at import, the blueprint never registers, and those would have been Flask HTML 404s. ⚠️ **`/health`'s `version` is a hand-maintained string with NO commit SHA** — it can never confirm which commit is live; Render Events is the only source for that.

### Guard tier → coming-soon (three independent gates, all required)
1. **Server:** `COMING_SOON_PLANS = ('dealer','guard')` in `routes/billing.py`, refused ahead of the 409 active-subscription guard (which now only ever sees `'pro'`). Dealer's status/keys/error string unchanged.
2. **Stripe (Mike-side, done BEFORE this brief ran):** Guard monthly + annual removed from the live customer portal's switchable products. ⚠️ **This was the real bypass** — the portal is the only in-place plan-modify path and code cannot reach it. Guard prices were **deliberately NOT archived** (reversibility; Guard is meant to return).
3. **UI:** pricing rebuilt two-column Free/Pro, Guard + Dealer demoted to a roadmap strip with Notify Me → `/contact.html`. "Most Popular" moved Guard → Pro. Compare table trimmed to Free/Pro. Save badge 25% → 17% (25% was *Guard's* discount; Pro saves 16.5% — the badge had been contradicting the Pro card beneath it).

**Re-enabling Guard needs all three reversed.** The one-line `COMING_SOON_PLANS` removal alone is NOT sufficient.

### Meta Pixel — live
Dataset **`4401241006789951`**; domain ID **`924245086634661`** verified via Cloudflare TXT. Confirmed firing on slabworthy.com: `signals/config/4401241006789951` returns a config (Meta recognises the dataset), `facebook.com/tr/` beacon sent, `_fbp` set, fbevents 2.9.368, queue drained. Intercepted wire payload: `id=4401241006789951, ev=CompleteRegistration, cd[content_name]=email_verified`.
- `Lead` = signup accepted **and** verification email dispatched (not on `email_send_failed`). `CompleteRegistration` = first email verification only; four independent guards (token NULLed server-side, `?token` stripped before the fetch resolves, response-shape check, localStorage sentinel).
- **The redirect is deferred until the conversion is actually dispatched** — firing then navigating in the same tick destroys queued events. Bounded 2s; an inert API installs when the pixel is off/blocked so signup is never delayed. *(An earlier draft stalled every verification 10.8s; caught and fixed pre-ship.)*
- **Privacy shipped first, on purpose.** Includes the CCPA revision at **`privacy.html:347`** plus its twin in "How We Use Your Information" — both "we do not sell your personal information" claims now qualified, since sharing ad data with Meta may count as a "sale"/"share" even with no money changing hands.

### ✅ `handle_subscription_deleted` — CONFIRMED IN PRODUCTION
An **accidental live Free→Guard checkout**, then cancelled: the user row reverted to `free` correctly. **This was Section E's last untested path.** ⚰️ Retire "subscription-deleted path untested" wherever it still appears — it is closed by production evidence, not a fixture.

### ✅ `sw.js` install-precache + activate-eviction — CONFIRMED EXECUTING
Previously recorded as "NOT verified by execution" (the in-app browser kept reusing an active worker). Now observed on live slabworthy.com: exactly one cache `slabworthy-v3-20260801`, `/js/pixel.js` precached, **zero HTML cached**, zero stale caches remaining. ⚰️ That open item is closed.

### Slab Guard claims audit — outcome
**Taken:** Tier 1 items 1–6 and Tier 2 items **7** (*"authentication and theft protection"* → *"registration and theft-deterrence"* — **we do not authenticate, CGC does**) and **9** (*"proof of ownership"/"ownership evidence"* → *"evidence of possession at registration"*).

**Deliberately KEPT, with reasoning — do not re-flag:**
- **8** `index.html:1052` "Protect Your Collection" — brand framing, and deterrence *is* genuine protection; with 1–6 landed the section beneath it is accurate.
- **10** `pricing.html` Slab Guard banner — already the most honest copy in the repo ("candidate sightings", "beta", "may be inaccurate").
- **11** `verify.html:531` serial verification — **deterministic, works, and is the claim we want leading.**

⚠️ **FOUR LATE MISSES, found only after I had already reported the audit as complete:** `waitlist-confirmed.html` (never audited at all — it's shown to every waitlist signup), `app.html:2872` (JS-injected success message still read "Monitoring enabled for theft recovery", **contradicting copy rewritten 40 lines above it**), the `check.html` match verdicts, and `routes/verify.py:411` (sighting-alert **email** calling Slab Guard a "theft recovery system"). **One was caused by my own `head -22` truncation hiding line 2872** — see L-SW-2026-015.

⚠️ **LOGGED, NOT CORRECTED (Mike's call):** the two corrected email strings had already been delivered to real users. Not retracted or re-sent at this volume. Recorded so nobody later reads the fixed templates and assumes the old wording never shipped.

### Match verdict rewrite (`check.html`) — the reasoning is the point
`same_copy` → "Strong candidate match — review this listing carefully". `different_copy` → "No strong match… **Photo comparison can't rule a copy in or out**; to know for certain, check the serial number." `uncertain` → also routes to the serial.

**`different_copy` was the HIGHER-RISK string, not `same_copy`** — a false negative tells someone their stolen book isn't theirs and **they stop looking**. Cross-camera FP ran 4/6. Both non-positive verdicts now route to serial verification, the deterministic path and the only one that gives a definitive answer. **Mike: this is the pattern to repeat everywhere Slab Guard surfaces a judgment** — state the epistemic limit plainly, then send people somewhere real.

### ⚰️ TOMBSTONE — the two-table trap (see also L-SW-2026-014)
"The valuation corpus is eBay-only" is **DEAD — it was never true.** I flagged accurate copy at `waitlist-confirmed.html:306` as a false claim; **Mike corrected it and the correction is confirmed by a read-only count.**

| Source | Table | Rows | Share |
|---|---|---|---|
| eBay | `ebay_sales` | 71,652 | 87.8% |
| Whatnot | `market_sales` | 9,963 | 12.2% |

⚠️ **`market_sales` is 100% Whatnot** (`sales_market.py:127` defaults `source` to `'whatnot'`). Querying either table alone yields the **opposite** wrong answer with equal confidence. Whatnot is 9,963 real captures across 1,603 titles / 35 series (2026-01-24 → 2026-07-01) — **not fixtures**. **`waitlist-confirmed.html:306` was investigated and found CORRECT. Do not "fix" it.** Mike's ruling on phrasing: 88/12 is fine — *"across eBay and Whatnot"* describes provenance, not proportions.

---

## 🎯 ~~NEXT SESSION OPENS ON CP-1 — THE VALUATION HONESTY GATE~~ — ⚰️ **AUDITED 2026-08-02/03; THIS FRAMING IS DEAD**

⚰️ **TOMBSTONE (Rule 2) — added 2026-08-03.**
- **DEAD:** *"confidence is **computed and stored but displayed nowhere**"* and *"It remains UNTOUCHED."*
- **REPLACED BY:** CP-1 has been **audited read-only** and the audit lives in **`docs/technical/CP1_STATE_OF_PLAY.md`**. **"Displayed nowhere" was FALSE** — confidence renders in **two** live surfaces in `app.html` (`:1227-1230` + `:2714-2722`, and `js/app.js:1288-1300`). The real defect is **five inconsistent notions of confidence across five threshold sets**, plus a label that is systematically too generous (870 of 1,676 `medium` labels rest on ≤2 same-grade comps).
- **REASON:** the old framing scoped CP-1 as "wire up the display," which would have been the wrong work.
- **SUPERSEDES:** do **not** re-derive a CP-1 plan from this section. `CP1_STATE_OF_PLAY.md` §9 holds the current, tombstoned order.

⚠️ **CP-1 is audited but NOT FIXED** — the gate was characterised, not cleared.

⚰️ **TOMBSTONE (Rule 2) — "AUG 4 IS THE GATE" IS DEAD. Mike, 2026-08-03.**
- **DEAD:** *"Aug 4 soft launch"* as a live date, and my own framing above it that *"whether Aug 4 proceeds against a known-thin corpus is Mike's undecided call."* **Aug 4 was never a live date.** I asserted it from stale docs without checking; Mike corrected it.
- **REPLACED BY:** the real gate is **FIRST COLD TRAFFIC — paid ads or an organic group post. It is NOT SCHEDULED.** There is no calendar date attached to it.
- **WHERE CP-1 SITS:** its remaining fixes are **UPSTREAM of that gate** — they must land before cold traffic arrives, not before a date. So there is no date pressure, but there is ordering pressure.
- **REASON:** a date that nothing is actually planned against produces false urgency and, worse, invites a go/no-go decision nobody asked for.
- **SUPERSEDES:** every "sole declared blocker for Aug 4" / "Aug 4 board" framing, including the ones lower in this file (2026-07-29 blocks) and in the SoT docs listed below. **Do not sequence, count days, or stage a go/no-go against Aug 4.**

⚠️ **STALE-DATE ARTIFACTS — NOT SWEPT, Mike's call (a repo-wide Aug-4 sweep is a decision, not a cleanup):**
`CLAUDE.md:57` and `:95` · `docs/LAUNCH_READINESS.md:5`, `:7`, `:9`, `:15`, `:18` · the 2026-07-29 blocks lower in this file (`:233`, `:238`, `:254`, `:289`, `:318`, `:369`, `:391`–`:398`) · `docs/EBAY_CAPTURE_SCHEDULE.docx` §4, which states *"Soft launch is 2026-08-04, so the trigger fires immediately"* and therefore mis-schedules the `lookup_demand` promotion loop. Every one of these reads **Aug 4** and every one is now **DEAD as a gate**. They are left in place deliberately — sweeping them touches the launch SoT.

**Still accurate from the original note, and not superseded:** multi-run voting exists server-side but the frontend hardcodes `runs: 1` (`app.html:2355`); a live harness exists at `test_grading_consistency.py --live`; **grading consistency has never been measured.** The framing still holds: *honest about confidence, not accurate on everything.*

### 📋 OPEN ITEMS
1. **Test-address problem — Cloudflare Email Routing catch-all on `slabworthy.com`, MID-SETUP.** ⚠️ **DO NOT TOUCH `send.slabworthy.com` MX, SPF or DKIM — those are Resend OUTBOUND and unrelated.** Inbound catch-all only.
2. **DMARC record missing** on the sending domain.
3. **Meta Events Manager cold-signup walkthrough** — never run. I verified the beacon reaches Meta with the correct dataset and payload, **not** that Events Manager attributes it. Walk: landing → signup → verification email → click → verified; assert `Lead` once, `CompleteRegistration` once, neither re-fires on refresh.
4. **Authenticated Guard refusal unproven in prod** — `POST /api/billing/create-checkout {"plan":"guard"}` returns 401 unauthenticated; the 400 `coming_soon` path sits behind `@require_auth`. Passed 13/13 offline against the real view, and the portal gate is closed, so exposure is narrow.
5. **Mobile pass** — still the priority (FB traffic is mobile).
5a. **⏱️ Render instance failure 2026-08-03 ~07:53 — health check timed out after 5s, then recovered.** Seen in Render Events. **Predates all of this session's work** (the write-path units deployed that evening), so it is NOT a regression from them. Not urgent; **not investigated.**
   - **UNTESTED HYPOTHESIS, explicitly flagged as such (L-SW-2026-007 — instrument, do not theorise):** `dependency_monitor.check_all` still runs inside `/health`, so the availability probe Render acts on performs outbound network I/O. A 5s timeout on an endpoint that makes external calls is a plausible shape — **and that is all it is.** L-SW-2026-013 was a prior incident of alert I/O sitting in that same request path, which is why it is the first thing to check, not evidence that it is the cause.
   - **First move:** `request_logs` around 07:53 plus the Render log for that window. Do not act on the hypothesis before the logs say something.
6. 🔻 **SLAB GUARD VIDEO RESEARCH — UNBOUNDED, AND IT IS BLOCKING MORE THAN IT LOOKS. NEEDS A DECISION, NOT A TASK.**

   **What it blocks (Mike, 2026-08-01 — this is the reason it can't just sit):**
   - a **patented** feature (Comic Fingerprinting Theft Recovery, filed 2026-02-12),
   - an **unsellable tier** (Guard — the whole coming-soon unit above exists because of this),
   - the **Slab Guard B2B licensing story**.

   **Its current state: no owner, no date, no decision criterion, no result.** That combination is
   how it drifts into next month unnamed — three high-value things parked on an open question
   nobody has been assigned to close.

   **Required outcome — pick ONE (Mike, not decided today, but do not let it drift):**
   - **(A) TIMEBOX IT.** Fixed calendar bound **plus a pre-committed decision criterion written
     down BEFORE the work starts** — i.e. the accuracy/FP bar that counts as success, decided in
     advance so the result can't be graded against a moving target. On expiry with the bar unmet,
     it auto-parks to (B). No extension without a new explicit decision.
   - **(B) PARK IT EXPLICITLY** and **build CGC cert-number matching as the real recovery path.**
     Cert-number matching is **deterministic and already honest** — the same property that made
     serial verification the claim we chose to lead with in the `check.html` verdict rewrite. This
     is the option that ships something.

   ⚠️ **What must NOT happen: a third state where it stays open, undated and unowned.** That is
   exactly where it is now.

   **Interim honest headline stays: CGC cert-number matching — NOT fingerprint recovery.** Prior
   findings for whoever picks this up: cross-camera was never validated (E3 rep TP 6/6 but **FP 4/6,
   REJECTED** as too permissive), the ceiling was judged **physical** and triangulated three ways,
   and single-image matching is parked as bounded-to-high-wear. The SAM+E3 engine is retained for
   multi-view. Zero production code.
7. `docs/postmortems/` **stays untracked** — deliberate; committing files mid-ship-sequence is how staging accidents happen. Commit it deliberately in a later pass.

---

## 2026-08-01 — 🛡️ **GUARD TIER IS NO LONGER SELLABLE** (coming-soon, same pattern as Dealer)

**MOST RECENT CHANGE (Rule 5): the Guard tier was pulled from sale on 2026-08-01. Supersedes every "Pro + Guard are the two self-service options" statement in this file, including the 2026-07-29 portal-configuration and Unit-D plan-selection entries.** Reason: Slab Guard's **recovery** capability is unproven — cross-camera matching was never properly tested and a video-based approach is under evaluation with no result yet. We will not sell a tier whose headline capability is unproven, least of all on live keys.

⚰️ **TOMBSTONE — three dead statements, all retired today:**
1. **"Live portal plan-switching = Pro + Guard only, Dealer excluded"** (2026-07-29) is **DEAD**. **REPLACED BY:** Pro only — Guard monthly + annual were removed from the live customer portal's switchable products (Mike, verified against the config) **before** this work ran. The portal bypass identified in the code review is therefore **already closed**; do not re-raise it as open.
2. **"Unit D plan-selection page must offer Pro + Guard only, never Dealer"** is **DEAD**. **REPLACED BY: Pro only — never Guard, never Dealer.** ⚠️ The page is still **unbuilt**; this correction exists so it is not built from the stale spec. Free remains until the ~Sept 4 sunset.
3. **"Guard is the Most Popular tier"** (pricing.html) is **DEAD** — the badge moved to Pro, which is now the only purchasable paid tier.

**SCOPE — this is a PURCHASE GATE, NOT a feature removal.** Slab Guard registration, fingerprinting, `verify.html`, `check.html`, sightings and the admin review queue all stay wired and working. Existing Guard subscribers keep **every** entitlement — nothing reads plan state or revokes access. `PLANS['guard']` is untouched.

**✅ `handle_subscription_deleted` IS NOW CONFIRMED WORKING (2026-08-01).** An accidental **live** Free→Guard checkout was run and then cancelled; the user row reverted to `free` correctly. Section E had this path listed as **never tested** — that gap is now closed by real production evidence, not by a fixture. ⚰️ Retire "subscription-deleted path untested" wherever it still appears.

**Item held, deliberately:** archiving the Guard prices in Stripe is **NOT** being done. Guard is intended to become sellable again once recovery is proven, and archiving is a heavier reversal than a portal-config change. The prices stay live but unreachable — server refuses checkout, portal no longer offers the switch.

**Re-enabling Guard later is a one-line code change** (`routes/billing.py`, remove `'guard'` from `COMING_SOON_PLANS`) **plus** re-adding it to the portal config **plus** reverting the pricing-page layout. All three are required; the code change alone is not sufficient.

### 📋 SLAB GUARD CLAIMS AUDIT (2026-08-01) — the rule to apply from now on

**THE LINE:** *registration, fingerprinting, provenance, "on record", registry/serial lookup* = **proven today, state plainly**. *Theft recovery, finding stolen comics, proving ownership of a recovered book, matching a photo back to a registration* = **UNPROVEN, never claim**. Cross-camera matching was never validated (E3: TP 6/6 but **FP 4/6, REJECTED**; ceiling judged physical); a video-based approach is under evaluation with **no result yet**.

**Rewritten (approved by Mike):** `check.html` "identifies the exact same comic across different cameras, lighting, and backgrounds" → candidate matches to review *(this was the single worst instance — it stated the untested capability verbatim, on a public page)*; `app.html` registration blurb *(also falsely claimed Whatnot + "other marketplaces" monitoring — only eBay is monitored)*; `waitlist.html` feature + meta; `faq.html` "authentication and theft protection" → "registration and theft-deterrence" *(**we do not authenticate — CGC does**)*; `faq.html` "proof of ownership"/"ownership evidence" → "evidence of possession at registration"; `routes/waitlist.py` "Prove ownership" → "Put them on record"; `routes/admin_routes.py` invite "Register and protect".

**Deliberately KEPT after review (do not re-flag these):** `index.html:1052` "Protect Your Collection" — brand framing, and deterrence is genuine protection; the section beneath it is now accurate. `verify.html:531` serial-number verification — **deterministic, works, and is the claim we want leading.** `pricing.html` Slab Guard banner — already the most honest copy in the repo (says "candidate sightings", "beta", "may be inaccurate"). Patent titles in `CLAUDE.md` — filed titles, not product claims.

⚠️ **LOGGED, NOT CORRECTED (Mike's call): the two email strings above were already delivered to real users.** Not being retracted or re-sent at this volume. Recorded so nobody later reads the fixed templates and assumes the prior wording never shipped.

⚰️ **`docs/technical/FINGERPRINTING_PROJECT_SUMMARY.md` tombstoned** — it asserted "Technology WORKS for comic theft recovery" from a **same-camera** test. Internal, but it was the most likely thing to be read as ground truth by a future session and re-justify the claims we just removed.

**Also changed in the claims pass — `check.html` match verdicts.** These three strings are the only place the product reports a matching result to a user. `same_copy` → "Strong candidate match — review this listing carefully"; `different_copy` → "No strong match — same title, but the copies look different… check the serial number"; `uncertain` → also points at the serial. **Reasoning worth keeping: `different_copy` was the higher-risk string, not `same_copy`** — a false negative tells someone their stolen book isn't theirs and they stop looking. Both non-positive verdicts now route to serial verification, the deterministic path and the only one that gives a definitive answer.

### ⚰️ TOMBSTONE — "the valuation corpus is eBay-only" is **DEAD. It was never true.**

**RAISED** during the 2026-08-01 claims audit: `waitlist-confirmed.html:306` ("We track real sales data across eBay and Whatnot") was flagged as a false claim on the assumption the corpus was eBay-only. **Mike corrected it; the flag was WRONG and the correction is confirmed by a read-only count.** **DO NOT re-raise it, and do not "fix" that line** — it is accurate as written.

**Measured 2026-08-01 (read-only, `DATABASE_URL_RO`), and the reason the mistake was easy to make: the corpus lives in TWO tables.**

| Source | Table | Rows | Share |
|---|---|---|---|
| eBay | `ebay_sales` | 71,652 | 87.8% |
| Whatnot | `market_sales` | 9,963 | 12.2% |
| **Total** | | **81,615** | |

⚠️ **`market_sales` is 100% Whatnot** — `sales_market.py:127` defaults `source` to `'whatnot'`. Counting only `market_sales` and seeing no eBay rows (or only `ebay_sales` and seeing no Whatnot) gives the opposite wrong answer each way. **Query both tables.** eBay covers 2018-09-10 → 2026-07-16; Whatnot is 9,963 real captures, 1,603 distinct titles / 35 series, captured 2026-01-24 → 2026-07-01 — **not fixtures**.

**VERDICT: 12.2% across 1,603 titles is a meaningful share, so the copy stands unchanged.** The only residual is a phrasing judgement — whether "across eBay and Whatnot" implies more parity than 88/12 — which is Mike's call and blocks nothing. **This item was investigated and found NOT to be a defect. It is a tombstone, not a fix.**

---

> ⚰️ **READ-BEFORE-YOU-USE TOMBSTONE — applies to EVERY 2026-07-29 and earlier block below. Added 2026-08-03.**
>
> Everything from here down is **a record of what was true on its own date and is deliberately left unedited.** One thing in it is now dead and must not be carried forward:
>
> **"Soft launch = August 4, 2026" (and its lineage July 28 ← July 21) is DEAD. Aug 4 was never a live date** (Mike, 2026-08-03). **The gate is an EVENT: first cold traffic — paid ads or an organic group post — and it is NOT SCHEDULED.** Every "Aug 4" / "sole declared blocker for Aug 4" / "the Aug 4 board" phrase below is historical framing, **not a current gate**. Do not sequence, count days, or stage a go/no-go against it. Current statement of the gate: the 2026-08-03 block at the top of this file, and `docs/LAUNCH_READINESS.md`.
>
> Also dead below, same reason as the CP-1 tombstone above: **"confidence is computed and stored but displayed nowhere"** — it renders in two live surfaces. See `docs/technical/CP1_STATE_OF_PLAY.md`.
>
> Everything else in these blocks — gate statuses, incident forensics, commit hashes, decisions and their reasoning — remains accurate as history.

---

## 2026-07-29 (END OF DAY) — 📋 **FULL STATE: what shipped, what's open, what to pick up next**

**MOST RECENT CHANGE (Rule 5): billing went LIVE on real money and the signup gate came down — both on the same day. Soft launch remains AUGUST 4, 2026. Mike is on a break; back later or tomorrow.**

### ✅ SHIPPED + VERIFIED TODAY (in order)
| What | Commit / artefact | Evidence |
|---|---|---|
| Soft-launch date → Aug 4 | `6dd44b4` | docs only |
| GalaxyCon DROPPED, docs swept | `c140231` | 5 files + CLAUDE.md; GALAXYCON_SPRINT deliberately untouched |
| Unit A punch list | `1e1e6b3` | browser-verified 412×915 + desktop, logged in/out |
| Stripe preflight `--live` | `3225572` | all 4 key×flag combos; also fixed a pre-existing Windows crash (L-2026-015) |
| **Unit E — live Stripe cutover** | Render env, Mike | **real card: purchase → webhook → plan active → cancel → teardown → refund** |
| Live customer-portal config | Stripe dashboard, Mike | Pro + Guard switchable; **Dealer excluded** (matches `billing.py:511`) |
| Google Pay dashboard half | Stripe dashboard, Mike | code half still open — see Unit B |
| Test-mode Stripe id cleanup | SQL, Mike | 6 rows nulled, row 33 reset; fixtures 24/25/26 untouched |
| Signup-flow migration | `db_migrate_signup_flow.py` | ran clean, **13 grandfathered / 22 will see the plan page** |
| Gate removal + email canonicalisation + invite rewrite | `auth.py`, `login.html`, `admin_routes.py` | 18/18 signup assertions, 16/16 canonicalisation; **prod-confirmed: `mikeberrysc+test@gmail.com` blocked as duplicate** |
| Pending-user unlock | `db_migrate_approve_pending_users.py` | 1 candidate (`id=6`, Mike's own alias) |
| "Private Beta" badge → **"Early Access"** | `login.html` | badge is on the card, so correct on login/forgot panels too |

**Prod-verified by Mike:** private-window load shows the signup form by default, no beta-code box.

### 🔶 THE ONE REMAINING HARD GATE
**Valuation/identification honesty** — confidence is computed and stored but **displayed nowhere**. This is the old CP-1 from the retired sprint plan and the **sole declared blocker for Aug 4**. Everything else below is punch-list or polish.

### 📋 OPEN WORK (rough priority)
1. **Unit B — billing UX.** Current (free) plan navigates to the dashboard instead of reading as active/non-clickable. Plus **Google Pay: remove `payment_method_types=['card']` at `billing.py:570`** — it actively suppresses Google/Apple Pay/Link; the dashboard half is already enabled, so this one line is all that's left.
2. **Plan-selection page on first login.** Spec settled and **must not be re-litigated: Pro + Guard only, never Dealer** (Dealer is a sales conversation), Free until sunset. Trigger column `has_selected_plan` exists; 22 accounts are already FALSE and will see it.
3. **Coming-soon markers.** SlabGuard = **registration/upgrade copy only, public `verify.html`/`check.html` stay live**. Marketplaces = everything except eBay. ⚠️ **The platform list is duplicated in three places** — `js/collection.js:630`, `js/marketplace-modal.js:11`, `account.html#platforms` — change all three or the dropdown says "Coming soon" while the modal still opens.
4. **`FREE_PLAN_OPEN` switch.** One env var, read at signup/plan-selection. Mike flips it ~Sept 4. Existing free users (29) grandfathered; new signups then see Pro + Guard only. No scheduler needed.
5. **`sw.js` unit — BUILT IN TREE, NOT COMMITTED.** Detail below.
6. **My Collection affordance neutralisation.** `.comic-card` (`js/collection.js:329`) has no click handler while the gallery `.comic-frame` does. **Decision: remove the clickable styling now** so it stops reading as broken; the real detail view ships with the collection redesign. Don't build it twice.
7. ❓ **Market Pulse mobile charts — NEEDS RECHECK ON MOBILE. NOT a confirmed bug.** ⚰️ An earlier line in this file logged it as a defect; **Mike corrected that same day**: he isn't certain the charts failed to render — he may simply not have scrolled to them, or they may have loaded slowly. **Do not open a fix, do not scope work, and do not repeat "charts don't render" as fact.** The only action is: look at Market Pulse on a real phone, scroll all the way to the charts, and note whether they render and how long they take. If they're fine, delete this item.
8. ✅ **Post-subscription banner wording — CONFIRMED, ready to fix, code located.** In-app banner on **My Account** at **`account.html:536`**:
   - **Current:** `<strong>Welcome!</strong> Your subscription is now active. Time to protect your collection.`
   - **Replace with:** `Welcome! Your subscription is now active. Start grading your collection.`
   - **Why:** "protect your collection" is Slab Guard language, and Slab Guard is going "Coming soon" (item 3) — so the banner points a brand-new paying subscriber at a feature they can't use. "Start grading" points at the thing they actually just bought.
   - Logged by Mike in **Todoist as p3**. Just needs the one-line code change — **fold into Unit B** rather than shipping alone.

**DEFERRED by Mike (explicitly not bundled):** My Collection layout redesign — columns wrapping badly, unclear actions, wants a proper PR or two. Collection scroll behaviour at 20+ comics — untested, Mike will report.

### 🧩 `sw.js` UNIT — in tree, diff delivered, awaiting review
Files: **`sw.js` rewritten**, **`offline.html` NEW**, `login.html` (badge, same file as the Early Access change).
- **HTML is never cached now.** Previously every successful page load was stored, so a user on a flaky connection could be served an arbitrarily old page — including the removed private-beta panel — and we had **no way to fix it remotely**. Slab Worthy can't function offline anyway (grading + valuation both need the API), so caching app HTML bought nothing and was the only route to a stale-UI bug.
- **Failed navigations serve `/offline.html`**, self-contained (zero external requests, auto-reloads on `online`). Previously they fell back to cached `/index.html`, so a failed `/account.html` request silently showed the marketing homepage — reads as "the app logged me out".
- **Static assets stay network-first** with cache fallback. Deliberate: HTML is always fresh now, and a cache-first JS bundle could go stale against fresh HTML, which is worse than slightly slower.
- **`CACHE_NAME` → `slabworthy-v2-20260729`.** ⚠️ This makes the eviction code work **for the first time**: it deletes caches whose name ≠ `CACHE_NAME`, but the name was hardcoded `slabworthy-v1` from day one, so **that cleanup had literally never run.** Bump it on any deploy that changes a precached asset.
- **Verified:** after a real navigation the v2 cache holds **zero HTML**; CSS + JS still cached; `offline.html` renders correctly standalone.
- ⚠️ **NOT verified by execution:** the install-precache and activate-eviction paths. The in-app browser reused an already-active worker, so those lifecycle events never re-fired no matter how the registration was cycled. **Confirm in prod:** DevTools → Application → Cache Storage should show **only** `slabworthy-v2-20260729`, and it should contain `offline.html` plus static assets and no `.html` pages.
- 📌 **Correction to an earlier claim in this session:** the stale beta panel seen locally was attributed to the service worker. That isn't supportable — the SW was already network-first, and the unregister and a `?cachebust=` param were applied in the same step, so the two can't be separated. The browser's ordinary HTTP cache is the likelier cause. The `sw.js` defects above are real and worth fixing regardless, but they were **not** the cause of that observation.

### Git truth (2026-07-29 end of day, verified)
HEAD = `3225572`. Dirty in tree, **not committed**: `sw.js`, `offline.html` (new, untracked), `login.html` (Early Access badge), plus today's docs edits to `LAUNCH_READINESS.md` and this file. The `auth.py`/`admin_routes.py`/migration commit block was handed to Mike; confirm with `git log` whether it landed before assuming. Pre-existing `.claude/worktrees/*` dirt untouched as always.

### NEXT SESSION — 🎯 OPENING TOPIC IS FIXED, DO NOT PICK SOMETHING ELSE

**Mike's instruction (2026-07-29, end of day): the FIRST thing next session is the VALUATION-HONESTY GATE. He wants to understand exactly what is BUILT vs what is MISSING before anything else is touched. Open with that — read-only, no code.**

Why it's the right opener: it is the **sole remaining declared hard gate** for Aug 4 (billing closed today). Everything else on the open list is punch-list or polish, individually cheap, and could quietly absorb the whole week without this moving.

What's known going in (verify, don't assume — these are prior findings, not fresh reads):
- Confidence is **computed and stored** but **displayed nowhere** in the UI.
- Multi-run voting exists server-side, but the frontend hardcodes `runs: 1`.
- A live harness exists at root: `test_grading_consistency.py --live`.
- **Grading consistency has never been measured.**
- This is the old **CP-1** from the retired GalaxyCon sprint plan, where the bar was framed as *"honest about confidence, not accurate on everything"* — every FMV carries a confidence signal and thin comp pools say so plainly. That framing is worth re-reading; it's the cheapest version of the gate.
- Related, already logged: valuation Layer 3 (grade-aware raw estimate) was deferred into R1/R2; the media-junk/poster work is paused (Mike, 2026-07-29) with the eyeball list already produced.

Then, only after that discussion:
1. `git log --oneline -5` + `git status --short` — **verify what actually landed** before planning (L-SW-2026-008; state moved twice mid-session on 2026-07-29).
2. **Unit B** — the one-line Google Pay fix (`billing.py:570`) is the cheapest real win; bundle the current-plan UX and the `account.html:536` banner wording with it.
3. Plan-selection page → Coming-soon markers → `FREE_PLAN_OPEN`.
4. **Market Pulse: recheck on a phone. It is NOT a confirmed bug** — see item 7.

### ✅ Everything from 2026-07-29 is committed and deployed
`27144e3` sw.js/PWA + Early Access badge (deployed + **purged**, Mike) · `b981789` gate removal + canonicalisation + invite rewrite · `cbb50a8` signup-flow migration · `156f441` docs. Both migrations ran clean. Mike: *"That closes today completely."*

---

## 2026-07-29 (night) — ✅✅ **BILLING IS LIVE — UNIT E CLOSED, REAL MONEY VERIFIED**

**MOST RECENT CHANGE (2026-07-29 night, Rule 5): the live-mode Stripe cutover is COMPLETE and VERIFIED. Production runs on LIVE Stripe keys as of 2026-07-29. A REAL CARD was taken end-to-end: purchase → webhook → plan active → cancel → teardown → refund.** Mike ran every step.

⚰️ **TOMBSTONE — the two dead framings, both retired tonight:**
1. **"Production is on `sk_test_…0x9c`, no real user can ever pay"** (found this evening) is **RESOLVED**. Do not re-raise it; do not treat the test-key values recorded below as current. They are history.
2. **"Section E closed the billing *state machine*, not the ability to take money"** (written this evening) is also **RESOLVED**. Both halves are now proven: the state machine at `3935ce5` (2026-07-08, teardown + both guard branches observed live) and the money path tonight on a real card. **From here, "billing works" is true without qualification** — the distinction that entry drew no longer needs carrying.

🎯 **ONE OF THE TWO DECLARED HARD GATES IS CLOSED.** Remaining hard gate: **valuation/identification honesty** — confidence is computed and stored but **displayed nowhere**. That is now the **sole declared blocker for Aug 4**, and it's the old CP-1 from the retired sprint plan. Everything else on the board is punch-list or polish.

**Google Pay — dashboard half DONE, code half OPEN.** Enabled in Stripe payment methods (live mode). The remaining piece is `billing.py:570`, which sets `payment_method_types=['card']` and **actively suppresses** Google Pay/Apple Pay/Link regardless of dashboard settings. **That change belongs to Unit B**, not the cutover — recorded so it can't be mistaken for "Google Pay is done."

**Unaffected by the cutover, still true:** the DB cleanup (6 rows nulled, row 33 reset) and the `test-pro`/`test-guard`/`test-dealer` fixtures at rows 24/25/26 — DB-granted tiers, no Stripe objects, **still not revenue**.

---

## 2026-07-29 (evening) — 🔴 **P0: PROD WAS ON STRIPE TEST KEYS** *(RESOLVED same night — see above)* + Pixel punch list + Unit A shipped

**MOST RECENT CHANGE (2026-07-29 evening, Rule 5): production has been running on Stripe TEST keys — `sk_test_…0x9c` / `pk_test_…CiYH`. No real user could ever have paid. Found by Mike's Pixel walkthrough (only `4242…` accepted), confirmed read-only via the Render API. Cutover to a FRESH live key is in progress on Mike's side.** This outranks every other open item for Aug 4.

⚰️ **TOMBSTONE:** any earlier reading of "billing hard gate CLOSED" (Section E, 2026-07-08) as *"we can take money"* is **DEAD**. Section E's teardown/guard logic is genuinely proven — but it was proven **in test mode**, against test-mode objects. The gate was "the billing state machine is correct," never "real cards work." Both are needed for Aug 4; only the first is done.

**Key choice (DF rec, Mike agreed → created a fresh key):** two live keys existed, neither in Render. `sk_live_…id6R` (Feb 15, last used May 17, unnamed) — **don't use**, the Stripe account is shared with MASSÉ products so it may belong to another integration; coupling two projects to one credential means rotating it later breaks the other silently. `sk_live_…9ca0` ("Slab Worthy", created *and* last used 2026-06-19) — that date matches L-SW-2026-005's accidental-LIVE-key-in-Render incident exactly; not compromised, but its handling history includes a mistake. A fresh key costs 30 seconds and buys a clean provenance for the one credential that moves real money.

**Cutover audit (read-only, all from code):**
- **8 env vars change:** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, 6 × `STRIPE_*_PRICE`.
- ⚠️ **`STRIPE_PUBLISHABLE_KEY` is read by ZERO code** — checkout is a server-side redirect to a Stripe-hosted page. Update it for hygiene only; it has no functional effect. (Verified: no hits in any `.py`/`.js`/`.html`/`.json`/`.yaml`.)
- **`PLANS` reads price ids at MODULE IMPORT** (`billing.py:77,78,96,97,115,116`) → saving env vars is not enough, the service must restart. Pairs with L-SW-2026-004 (fresh shell) and CLAUDE.md's warning that auto-deploy is unreliable here.
- **Live webhook endpoint** must be at `/api/billing/webhook` with exactly the 5 events in `billing.py:673-677`. A signing secret is shown **only at creation** — an existing-but-unrecorded live secret must be ROLLED, never guessed.
- **Everything is env-driven** — zero hardcoded keys or price ids anywhere. The cutover is genuinely config-only.
- **Nothing is inferable about a price's mode from its id** (`price_…` in both), which is why the preflight has to retrieve them.

**✅ `scripts/stripe_preflight.py` — `--live` SHIPPED (`3225572`).** Inverts the expected mode (requires `sk_live_`/`rk_live_` + `livemode=true`), and reports a mismatch as a FLAG in **both** directions so a half-swapped config can't read green. Verified across all 4 key×flag combinations. Still strictly read-only — no create/modify/delete calls added. **Also fixed a PRE-EXISTING Windows crash:** it printed `→` and died with `UnicodeEncodeError` at `[1] KEY MODE` before checking anything on a cp1252 console — it had only ever been run in the Render shell. That's cross-project **L-2026-015** verbatim.

**✅ DB cleanup DONE + VERIFIED (Mike ran it, screenshot confirmed).** 6 rows (3, 29, 30, 31, 32, 33) had TEST-mode `cus_`/`sub_` ids nulled; row 33 (`mike@ideabyhuman.com`) additionally reset `pro/trialing → free/canceled` because Stripe had nothing active for it — it would otherwise have sat on a paid tier backed by nothing. **Rows 24/25/26 (`test-pro`/`test-guard`/`test-dealer`) deliberately untouched:** DB-granted tiers, zero Stripe objects, intentional fixtures — **and not revenue; don't count them.** All 9 confirmed by Mike as his own accounts.
- **Live-data lesson worth keeping:** row 29 changed state *between two reads in the same session* (a cancellation cascade landed there, not on 33 as assumed). Re-reading immediately before generating the SQL is what caught it. Never build mutation SQL on a snapshot taken earlier in the conversation.

**📱 PIXEL WALKTHROUGH PUNCH LIST — root causes all confirmed read-only:**
- ✅ **Unit A SHIPPED `1e1e6b3`**, browser-verified at 412×915 and desktop, logged-in and logged-out: (a) **`toggleFAQ()` was called by all 27 FAQ buttons and defined nowhere in the codebase** — ReferenceError per click; the CSS was always correct, only the class toggle was missing. (b) faq/pricing were missing the `sidebar.js` include — `detectPage()` **already had a `faq` case**, so it was designed to be there. (c) mobile topbar was in normal flow → `position:sticky; top:0; z-index:998` (below drawer 1000 / overlay 999). (d) duplicate brand header fixed **generically, not per-page** — because adding the sidebar to faq/pricing would otherwise have *created* the same bug there; hidden not removed, since `account.html:924` binds `#logoutLink` unguarded and app.html's header holds the logged-out auth buttons; matched by brand marker so page-title headers (collection.html) survive. (e) CollectionCalc stripped from **both live footer copies** — `sightings.html` loads root `/footer.js`, all 12 other pages `/js/footer.js`; root copy's brand mark also corrected (`SLAB` → `$LAB`). Legal-entity refs in ToS/privacy/about **deliberately untouched** (Mike: separate business decision, not made yet).
- **P1 (revenue) — HALF CLOSED 2026-07-29.** ✅ **Portal plan-switching CONFIGURED IN LIVE MODE (Mike, during the cutover): eligible switch targets = Pro (monthly + annual) + Guard (monthly + annual). Dealer DELIBERATELY EXCLUDED — requires a manual/sales conversation, not self-service.** That closes the *dashboard* half of the upgrade dead end (`billing.py:547` routes plan changes to the portal; `:617` creates the session with no explicit `configuration`, so it uses the account default — which is now correctly configured). ✅ **Portal now matches the code:** `billing.py:511` already refused Dealer checkout server-side, so the exclusion is enforced on both sides instead of one — a self-serve Dealer path can't open by accident from either direction. ⚠️ **Per-mode:** configured in LIVE only; a test-mode portal check will still read unconfigured — expected, not a regression. **STILL OPEN — the in-app half:** the current (free) plan navigates to the dashboard instead of reading as active/non-clickable.
- **Downstream of the portal config (spec input, don't re-litigate):** at free-plan sunset (~Sept 4) **Pro and Guard are the two options a new user sees** — that is the complete self-service menu by design. Unit D's plan-selection page must offer **Pro + Guard only** (plus Free until sunset) and must **never** surface Dealer as a self-serve choice.
- **OPEN P2:** comic tap dead (`.comic-card` has no handler; gallery `.comic-frame` does) — **decision: neutralize the affordance now, real detail view ships with the My Collection redesign, don't build it twice**. **No Google Pay because `billing.py:570` sets `payment_method_types=['card']`, which actively suppresses it** — needs the code change AND live-mode dashboard enablement.
- **ANSWERED P3:** Turnstile on signup is **not invisible-mode — it was never built.** Present only in `check.html`/`contact.html`; `TURNSTILE_SECRET_KEY` consumed only by `routes/contact.py` and `routes/verify.py`. Working as built.
- **Deferred by Mike:** My Collection layout redesign (own PR, not bundled); collection scroll at 20+ comics (untested, will report).

**🧩 UNIT D — fully specified, not started.** Mike's product calls: remove beta-code gating (**bundled with email normalization, not shipped bare**), plan-selection page on first login, free plan open through ~Sept 4 then manual sunset with existing users **grandfathered**, SlabGuard "Coming soon" = **registration/upgrade copy only, public verify/check stays live**, marketplaces other than eBay "Coming soon", **email canonicalization = NEW SIGNUPS ONLY, no backfill**.
- **Why no backfill matters (measured):** of 34 accounts, **11 are `mikeberrysc+…` aliases** — canonicalizing existing rows would collapse all 11 into one account. Existing rows keep their raw email as canonical; every current login keeps working.
- **The real gate isn't the beta code:** `signup()` only validates a code *if one is supplied*; the block is `auto_approve = bool(beta_code) or waitlist_confirmed` (`auth.py:693`) feeding the login check at `auth.py:812`. Removing "beta gating" means **letting `email_verified` be the gate**. Blast radius today: **exactly 1** verified-but-blocked account.
- **Population (read-only):** 34 accounts (the ~50 is the *waitlist table*, a different thing), 33 approved, 31 verified, 22 never logged in, 29 on free (25 `none` + 4 `canceled`), 5 paid.
- **Design snag logged:** `last_login IS NULL` is a poor first-login signal because `login()` sets it during login — recommend an explicit `has_selected_plan` flag; batches with the `email_canonical` migration.
- **Scope warning:** the marketplace list is duplicated in `js/collection.js:630`, `js/marketplace-modal.js:11`, and `account.html#platforms` — all three must change together or the dropdown says "Coming soon" while the modal still opens.
- **Ship order:** migration (`email_canonical` + `has_selected_plan`) → gate removal + email normalization → plan-selection page → Coming-soon markers → `FREE_PLAN_OPEN` switch.

**Git truth (2026-07-29 evening, verified):** HEAD = `3225572` (preflight `--live`); beneath it `1e1e6b3` (Unit A), `c140231` (GalaxyCon dropped), `6dd44b4` (Aug 4 date move). Working tree clean for all touched files; pre-existing `.claude/worktrees/*` dirt untouched as always.

---

## 2026-07-29 (later) — 🎪 **GALAXYCON IS OFF (DROPPED, not delayed)** + marketing shape + waitlist correction

**MOST RECENT CHANGE (2026-07-29, Rule 5): GALAXYCON SAN JOSE IS DROPPED — not postponed, not re-dated. Personal bandwidth (Mike), NOT technical.** Soft launch **still Aug 4**. After that: **SW is online-marketing-only for the rest of 2026**, reassessed as year-end approaches.

⚰️ **TOMBSTONE — the single most load-bearing dead assumption in this repo:** "GalaxyCon San Jose, Aug 21–23 2026 = the alpha launch event / booth demos / **the calendar anchor that doesn't move**" is **DEAD**. **REPLACED BY:** soft launch Aug 4 → quiet month → FB + email marketing → online-only through year-end. **REASON:** Mike's personal bandwidth. **SUPERSEDES:** `docs/sessions/GALAXYCON_SPRINT.md` **in its entirety** (⚠️ *not touched yet — awaiting Mike's call on archive vs replace, see below*), the "GalaxyCon is the calendar anchor / count weeks, not features" principle in `SW_BO_PRIMER.md:71`, the ROADMAP GalaxyCon launch section, and every booth/con framing in `LAUNCH_READINESS.md`.

**Why this is a re-shaping, not a cancellation line-item — what actually changes:**
1. **The forcing function is gone.** GalaxyCon was the immovable external date that made sequencing honest. Aug 4 is soft and quiet; after it there is **no external deadline at all** except the 90-day purge (~2026-09-17), which is now the *only* hard date left on the project.
2. **F-load drops off the launch-critical path.** Its target (10 concurrent / 3 grading, plus the F-L4 16–18 ceiling burst) was explicitly **booth-shaped** — a room of phones on venue wifi. A gated, wave-admitted online beta will not produce that. **Re-derive an online-shaped target post-launch or defer; do not run the dead booth target and call it a gate.** F-**mobile** is unaffected and still matters for Aug 4.
3. **Physical-venue work is moot:** booth demo design, booth signup mode (gated vs open QR), demo mode to spare Vision API on repeat booth demos, printed booth codes, and the "concentrated savvy-collector crowd" anti-abuse threat model. The anti-abuse holes stay parked — **but they re-activate when open public signup turns on with FB/email marketing**, same shape, different road.
4. **Scope discipline now has to come from the docs.** With no date to be honest against, the "we have time" trap the primer warned about gets materially more dangerous, not less.

**Marketing + sequencing (Mike, 2026-07-29):**
- **Channels: Facebook and email ONLY.** No other channels for now.
- **Sequence:** Aug 4 go-live → **~1 month quiet, NO active marketing push**, waitlist invites continue at current pace → **if nothing serious surfaces, marketing (FB + email) starts after** → online-marketing-only for the rest of 2026, reassess at year-end.

**📋 WAITLIST CORRECTION (Mike, 2026-07-29) — corrects the record:** of the **~50 signups, only ~30 are real users**; the rest are **Mike's own test accounts** created during development. Mike has **already been inviting every real signup** and will continue; signup rate is naturally slow, which suits the quiet month. ⚠️ **Never quote ~50 as real users or as demand.** Any conversion/engagement/COGS math must exclude the test accounts (~30 is the honest denominator).

**❓ OPEN QUESTION BACK TO MIKE (not actioned — do not touch `GALAXYCON_SPRINT.md` until answered):** what happens to that file? Recommendation + options in the session response of 2026-07-29; the file is a sprint plan toward an event that no longer exists, so a re-date is not a valid fix.

**Not changed by any of this:** every A–F gate status; the eBay/valuation corpus work; the 90-day purge deadline ~2026-09-17; Aug 4 itself.

---

## 2026-07-29 (earlier) — 🗓️ SCHEDULE CHANGE ONLY: soft launch moved July 28 → **AUGUST 4, 2026**

**MOST RECENT CHANGE (2026-07-29, Rule 5): SOFT LAUNCH = AUGUST 4, 2026 (Mike). REASON: personal availability — NOT technical, NOT readiness, NOT incident-driven.** ⚰️ **TOMBSTONE: "soft launch July 28" is DEAD** (and the older "July 21" is DEAD twice over). **REPLACED BY:** August 4, 2026. **SUPERSEDES:** the `Launch = July 28.` line at the end of the Session 118 CLOSE block below (corrected in place today), the Session 118 header's "SOFT LAUNCH SLIPPED July 21 → July 28", and `LAUNCH_READINESS.md`'s former "(to July 21)" sequence heading. Do not sequence, count weeks, or plan a go/no-go against July 21 or July 28.

- **What did NOT change:** no gate flipped, no work was re-scoped, no technical status moved. Engineering state is exactly as the Session 118 CLOSE block below records it (capture pipeline LIVE on `bbe5353`; Gate 0 CLOSED; incident closed on Standard 2GB). This entry is a **date-only** amendment.
- **What this does change (schedule shape):** +1 week of runway to soft launch, but **GalaxyCon Aug 21–23 does not move** → the soft-launch→booth buffer shrinks from ~3.5 weeks to ~2.5 weeks. The schedule-sensitive items are therefore **Section F (mobile pass + F-load/F-L4 burst on the 2GB box)** and the eBay/valuation corpus follow-ups (media-junk normalizer filter + 011 audit, ~118 poster candidates, JSON-reader eval) — they now sit closer to the booth with less slack behind them.
- **Unchanged deadlines:** GalaxyCon Aug 21–23 (immovable); ⏰ 90-day image purge hard deadline ~2026-09-17.
- ⚠️ **Stale-date artifacts NOT updated by this change (Mike's call whether to sweep them; they never received the July 28 move either and still read July 21):** `docs/SW_BO_PRIMER.md:44,71`; `docs/sessions/GALAXYCON_SPRINT.md:12,25,28,33,73,96` (incl. the W6 "Jul 15–21" row and the ~250-hours-before-July-21 budget); `docs/sessions/ROADMAP.txt:53,74`; `docs/technical/R2_CUTOVER_RUNBOOK.md:5`; and line ~485 of THIS file (90-day-purge note, "After soft launch (Jul 21)"). Every "July 21" / "July 28" in those files is DEAD — read them against **August 4**.
- **Files updated today:** `docs/LAUNCH_READINESS.md` (target line + Rule-5 header + sequence heading) and this file. No code touched, nothing to deploy.

---

## Session 118 CLOSE (Jul 16, ~20:45 UTC) — ✅ INCIDENT CLOSED: instance upgraded Starter→Standard 2GB (plan_changed 20:07:05Z, Mike) → 🎯 GATE 0 CLOSED: two consecutive real-iPhone HEIC grades fully successful (Heroes for Hope Special #1 + Iron Man #200 — correct title/publisher/year, full breakdowns, honest "Limited/Rough Estimate" on thin comps); memory 322–447MB vs 2048MB (~22% peak), zero failures since 19:43

**MOST RECENT CHANGE (2026-07-16 close, Rule 5): 2GB upgrade LIVE + Gate 0 DONE + both fix units (37d5e97 monitor / 65ffba1 memory) confirmed working under REAL conditions. ⚰️ TOMBSTONE: the addendum below's "testing ON HOLD / idle 441MB one extract from death" state is DEAD — resolved by the plan change. Day's verdict (Mike): the "same input failing differently every time" pattern was resource starvation all along — base drift toward the 512MB ceiling crossing on grade/extract cycles — not a code bug; new headroom removes the failure mode entirely. Five OOMs today, all explained, none remaining.**
- **Stale-spec cleanups for next touches (not urgent):** CLAUDE.md monitored-services line + Dockerfile sizing comment still say "Starter 512MB" → now Standard 2GB (2f thresholds are %-of-cgroup so they scaled automatically); the single-decode extract refactor (normalize + scan_barcode share one decode) downgraded from emergency to nice-to-have efficiency work.
- **NEXT session order:** (1) ~~docs commit~~ DONE (`d747bc9`/`e17c9f3` + `9db1e74` 2f env override, all shipped+verified same evening); (2) **eBay collector fix — SPEC RECEIVED + APPLIED IN TREE (2026-07-16 late), awaiting Mike's live test:** `content.js` +38/−9 — container `[data-listingid]` (li.s-card dead, kept as fallback), `ebay_item_id` from `dataset.listingid` gated by `/^\d{9,15}$/` (DB dedup key verified = `ON CONFLICT (ebay_item_id)`, sales_ebay.py:140 — URL-shape change CANNOT duplicate corpus rows; numeric gate protects the conflict path), title priority REVERSED to `a[class*="item-card__title"]` text with generic-img alt fallback (old primary was img.s-card__image alt — junk-alt risk flagged), price/date innerText regexes untouched, getPageInfo loosened fallbacks (display-only, capture-safety rule intact — zero pagination behavior). node --check clean. **🆕 SECOND collector bug found by Mike's live test (2026-07-16 late): selector fix verified working, but banner captured 12 of 287 DOM items — the ~2026-07 restructure also changed the RENDERING MODEL: items lazy-hydrate as [data-listingid] shells (content fills in as the human scrolls), and the extension's scan was SINGLE-SHOT at T+1.5s (no observer/interval/rescan — confirmed; no visibility filtering anywhere — Mike's hypothesis B ruled out). Old markup was server-rendered, so single-shot used to catch ~240. FIX APPLIED IN TREE (+113/−12 total): debounced (800ms) MutationObserver re-runs the pure-DOM scan as content hydrates, syncs only ids not yet captured this page (session Set + chrome.storage + server ON CONFLICT = triple dedup), silent no-op passes (banner can't self-trigger), cumulative banner "N synced this page — watching as you scroll", observer disconnects on pagehide. CAPTURE-SAFETY INVARIANT documented in-code: zero requests to eBay, zero synthetic scroll/navigation, pagination stays human. Title provenance confirmed for the 'fewer matching words' section: ALL extraction is item-scoped (no search-context defaulting; missing title ⇒ row dropped, never inherited).** **⚰️ CORRECTION (same night, Mike's diagnostic run): the hydration/observer theory was WRONG — all 279 items had title+price at load, observer fired fine (122×). TRUE root cause: `parseListingItem`'s `includes('Sold')` guard is case-SENSITIVE and the new markup uppercases the sold badge via CSS text-transform (innerText is rendering-aware) → 267/279 legitimate items rejected. SAME-BUG COROLLARY: the date parser's month lookup missed uppercase 'JUL' → silently stamped TODAY's date (corpus-freshness poison; dormant pre-restructure). BOTH FIXED in tree (`/sold/i` guard + month-key case normalization). Scrolling was never needed — full capture at load; the auto-scroll question is MOOT (Mike's Network-tab evaluation + DF risk-flag exchange preserved in chat 2026-07-16; never built). Observer kept as cheap insurance (silent no-op). 🆕 EMBEDDED-JSON READER under evaluation as PRIMARY capture (Mike's directive): probe found 40/40 sampled item ids in page script tags with title/price-shaped keys (1.28MB script text) — awaiting a saved sample HTML from Mike to build/verify offline; design = JSON-first with fixed DOM parser as automatic fallback; decisive unknowns = per-item sold date in the blob, section/sponsored flagging, key stability. TEMP [SW-DIAG] instrumentation still in content.js — STRIP BEFORE COMMIT.** **✅ ALL LIVE TESTS PASSED (2026-07-16 night): 203 net-new rows synced 22:39–23:42Z with REAL varied sale_dates (Jul 8–16 — date fix proven in prod data); 'fewer words' provenance spot-check PASSED (item 377346126386, Absolute Batman #1 Dragotta $220 sold 7/15, title = the listing's own); [SW-DIAG] STRIPPED; final collector diff +134/−15, node --check clean. CAPTURE PIPELINE LIVE AGAIN — PUSHED (`bbe5353` collector + `d4cf397` docs, session close). Poster cleanup COMMITTED to prod + verified (4 rows is_lot=true, single marker after a double-run dup was cleaned; AB#1 raw pool = 0 poster rows). JSON-reader sample landed at `tests/ebay_srp_sample.html` (gitignored — 4MB personal-search snapshot). Session-close backlog (Mike, none urgent): ~118 corpus-wide poster candidates (DF sends eyeball list next time); media-junk normalizer filter (next normalizer touch + 011 audit); NL-query-tool schema grounding (wrong table TWICE incl. on pasted literal SQL — fix before a real false alarm); JSON reader build vs the sample; Signature ID accuracy deferred until reference-DB buildout. Post-verification data-quality actions same night: banner now reports SERVER-inserted count (was pre-dedup local: 265 vs 203); 🆕 poster/print junk passes ALL normalizer flags (4 rows in AB#1's raw pool incl. $150/$270 screen prints — manual is_lot=true SQL handed to Mike for those 4; corpus-wide ~122 candidates; real media-junk filter = next normalizer touch WITH the L-SW-2026-011 corpus audit, logged in LAUNCH_READINESS — naive 'poster' regex would nuke legit 'polybagged with poster' comps); 🆕 admin NL-query tool logged as backlog (rewrote even pasted literal SQL to market_sales; confident false zero vs 7,389 real rows). JSON-reader evaluation still open (probe 40/40 — awaiting Mike's saved sample HTML; design = JSON-first, DOM fallback); (3) Section F: Pixel walkthrough + broader mobile pass; (4) F-load + F-L4 burst on the 2GB box. ⚰️ ~~Launch = July 28.~~ **DEAD — Launch = AUGUST 4, 2026** (Mike, 2026-07-29, availability; see the 2026-07-29 block at the top of this file).

## Session 118 addendum (Jul 16, ~20:00 UTC) — 5th OOM, ON THE FIXED BUILD (`eb89454` live 19:31, kill 19:43:40, bftpt): SAME class, new arithmetic — 12MP extract (deliberately uncapped at EXTRACT=4096 for barcode parity) ≈ +150MB, fired from a BASE that had DRIFTED to ~405MB (RSS retention per grade cycle). Post-restart the same flow succeeded from a fresh base (293→441 retained, flat = the current live level, ~71MB headroom). Evidence: caps PROVEN live (submission #15 photos stored at exactly 1500×2000 = GRADING_MAX_LONG_EDGE active; storm dead = monitor unit live; checkout eb89454 logged), api_usage gap 19:41:18→19:44:38 = killed request was the book-3 extract, retried successfully at 19:44:29; all traffic user 3 (Mike). Mike's 19:48 Heroes-for-Hope failure: ZERO backend trace (no log, no api_usage row) = never reached the app (client/edge during churn). CONCLUSION: on 512MB there is no code path that keeps full-res 12MP barcode scanning + 2-worker concurrency + headroom — the remaining calls are (a) instance 2GB (DF strong rec), (b) single-decode extract refactor (normalize+barcode share ONE decode — kills the double-decode waste, would roughly halve extract peak) and/or extract cap ↓2000, (c) 1×12 fallback (anti-booth, not recommended). MALLOC_ARENA_MAX/max-requests runtime confirmation needs Mike's Render shell: `printenv MALLOC_ARENA_MAX; ps aux | grep max-requests`. ⚠️ LIVE STATE: idle 441MB — one 12MP extract from a kill; ALL grading/extract testing on hold (Mike) until the instance decision.

## Session 118 (Jul 16, 2026) — OOM incident FULLY ROOT-CAUSED (3× oomKilled incl. ONE ON THE ROLLBACK BUILD): full-resolution uploads through the image-decode pipelines vs the 512MB instance — NOT the HEIC unit alone, NOT DB connectivity, NOT item 2(d); two fix units BUILT+VERIFIED IN TREE (memory 22/22, monitor-storm 10/10), BOTH ON HOLD per Mike pending his review; 🗓️ SOFT LAUNCH SLIPPED July 21 → July 28 (Mike, 2026-07-16) — ⚰️ **that July 28 date is now DEAD; current target = AUGUST 4, 2026 (Mike, 2026-07-29, availability)**

**MOST RECENT CHANGE (2026-07-16 ~19:15 UTC, Rule 5): ⚠️ ACCIDENTAL REDEPLOY OF `d2e525d` + Unit-1 hardening round + 🆕 HEIC MEMORY FLOOR FOUND.** (1) Mike ran the Unit-2 ship block with its placeholder `git add [monitor storm fix files]` line intact → NOTHING was committed (HEAD still `d2e525d`, dependency_monitor.py still dirty) but the `deploy` step ran → **prod is back on `d2e525d` (live 18:48:26Z) — the rollback is UNDONE, the monitor fix is NOT deployed, email storm re-seeded on the fresh boot** (~11 emails by 18:51). Prod is stable under normal client-resized traffic; raw-HEIC standdown (already agreed) is the operative protection. Exit path = ship the units (any push-deploy carries `d2e525d` anyway since it's on main). (2) Unit 1 hardened twice more by its own suite, now **25/25** incl. Mike's requested **24MP raw-HEIC fixture** (subprocess-isolated — local libheif hard-crashes in-process) and 12MP barcode-parity check: fix #1 = thumbnail-BEFORE-exif-transpose (don't copy the full bitmap to rotate it); fix #2 = the finding: **(3) 🆕 raw 24MP HEIC has a ~198MB intrinsic decode floor (libheif double-buffers: C frame + PIL copy) — code CANNOT make this input class safe on the 512MB Starter (330 base + 198 ≈ 528). Safe requires either the 2GB tier or an over-size reject policy.** Suite records it as a <230MB regression guard + loud NOTE. Ship order (Mike): Unit 2 first (corrected block handed in chat — `git add dependency_monitor.py`), Unit 1 after his diff review (diffs delivered). Client-side 2048px resize for the extract upload path QUEUED (LAUNCH_READINESS post-launch, defense-in-depth). Health Check Path re-enabled by Mike (was briefly off during his investigation). *Prior same evening:*
ROOT CAUSE UNIFIED + 2(d) HYPOTHESIS TESTED AND CLEARED. Render events (authoritative): exactly THREE `server_failed` events in recent history, ALL today, ALL `oomKilled (512Mi)` — 17:28:10 + 17:34:11 (96ngc, `d2e525d`) and 18:00:52 (qtq2g, `1437fdb` ROLLBACK build, 9 min after rollback went live). ⚰️ TOMBSTONE: this entry's earlier framing "regression from the HEIC ship / rollback restores stability" is DEAD — the vulnerability predates `d2e525d` and killed the rollback build too. ⚰️ ALSO DEAD: "DB-connectivity escalation" as a theory — Postgres healthy all day (111MB/256MB flat, CPU ~1%, active connections min 0/max 5 vs 103), exactly ONE SSL-abort blip (17:23:04, monitor + request failed the same second = external transient, never recurred).**

**The unified mechanism (measured, not theorized):** ⚰️ ~~the grading frontend client-resizes to ≤2048px (`js/grading.js:1313` MAX_IMAGE_DIM)~~ **[DEAD 2026-09-11: that resize has been unreachable since `823820b` 2026-02-06; the grade request sends the raw file — see the 2026-09-11 (evening) entry at the top]** — which is why every grade that COMPLETED today was harmless (retained photos = 1204×1600). But any path that ships FULL-RESOLUTION bytes server-side — raw HEIC library picks (Chrome can't canvas-decode HEIC → falls through at camera resolution; 24MP = current iPhone default), or any client that skips the resize — hits decode transients measured at **+187 to +310MB for ONE request** through `/api/extract` (normalize full-res + `scan_barcode` decoding the output AGAIN with up to 4 rotations). From the ~330MB service baseline that exceeds 512MB → `oomKilled`. Mike was actively testing with real iPhone photos (Gate 0 verification = the exact raw-HEIC class) when all three kills happened. `d2e525d` widened the hole (4 server-side decodes per grade); it did not create it.

**Item 2(d)/healthCheckPath hypothesis — CLEARED on all four checks (Mike's ask):** (1) Render polls /health ~every 5s (observed via storm-email cadence) — but polling started 2026-07-12, and `1437fdb` ran under it ~90 hours with ZERO failures before today (events list: no server_failed before 17:28 today); (2) the SELECT 1 conn close is in `finally` with the outer except covering checkout failure (`routes/utils.py:57`) — no leak path, matches the 2(d) suite's close-on-exception test; (3) Postgres active connections FLAT (2–5) all day through all three kills and the heaviest polling — a leak would climb toward 103; zero `POOL EXHAUSTED`/`too many clients` in the full day's logs; (4) the SSL-abort was a single 17:23:04 event under 24/7 polling → unrelated to poll frequency. **healthCheckPath revert NOT recommended — it's real protection and not implicated.**

**📧 EMAIL STORM root-caused + fix unit BUILT (unit 2, offline 10/10, scratchpad `test_monitor_flap.py`):** three compounding monitor defects — (a) `check_ebay_account_deletion._fail` cached FAILURES for the full 24h TTL (other checks back off 5 min): one 502 caught during a deploy-swap/OOM window poisoned a worker's view until process death; (b) per-worker check caches × shared prune-on-every-call dedup = the clean worker prunes the key, the poisoned worker re-inserts + re-EMAILS, alternating at poll cadence (~1 email/5–15s, observed live: `dependency_alerts` row deleted/re-inserted on a ~30s cycle) — self-sustaining, survives rollbacks (state-driven, not code-version-driven); (c) the Resend send ran SYNCHRONOUSLY inside /health. Fixes in tree (`dependency_monitor.py`): failure backoff 5 min; prune only after 15 min continuous absence (last_seen_at refresh + windowed DELETE); `_send_alert_email_async` (daemon thread, skip-if-busy) so /health never carries email latency. ⚠️ Storm is ACTIVE in prod until this ships — Mike's inbox fills at ~4/min during divergence windows.

**Memory-fix unit (unit 1) EXTENDED + re-verified 22/22 (`tests/test_memory_fix.py`, committed copy):** everything from the first build (GRADING_MAX_LONG_EDGE=2000, IMAGE_DECODE_CONCURRENCY=2 gate, MALLOC_ARENA_MAX=2, gunicorn --max-requests 500/jitter 100) PLUS `EXTRACT_MAX_LONG_EDGE=4096` on the extract path (12MP/4032px passes UNTOUCHED = barcode parity for all typical uploads; over-cap sources use a NEW half-decode draft rule — the aspect-box draft silently decoded 24MP at full res, +219MB, caught by the 24MP test) — measured: 24MP extract pipeline +187MB uncapped → **+73MB capped**; JPEG 4-photo grade 95→33MB; 8-way burst 152MB. ⚰️ The "extract deliberately uncapped" decision from unit 1's first draft is DEAD — the 18:00:52 kill WAS the extract path.

**HOLD STATE (Mike, 2026-07-16): both units held pending Mike's review of this evidence — nothing ships. Soft launch slipped one week → July 28 *(⚰️ superseded 2026-07-29 → **August 4, 2026**)*. Prod meanwhile: `1437fdb` live, stable under normal (client-resized) traffic, VULNERABLE to any full-res upload (avoid raw-HEIC/Files-app upload tests until unit 1 ships); email storm active until unit 2 ships. Residual risk noted for review: two simultaneous full-res decodes on DIFFERENT workers can still stack (~2×73MB) — F-L4 will characterize; a Starter→2GB instance upgrade would retire the entire class (Mike's call, cost item).**

**Memory-fix unit (in tree, files: `comic_extraction.py`, `routes/grading.py`, `Dockerfile`, `docs/technical/ARCHITECTURE.txt`):**
- **`GRADING_MAX_LONG_EDGE` (env, default 2000px)** — long-edge cap applied ONLY at the two grading call sites (`/api/grade` 4-photo loop + `/api/messages`); `/api/extract` deliberately uncapped because `scan_barcode` reads the normalizer's output. 2000 > the ~1568px Anthropic downscales to (no model-visible loss) and ≤ half of 4032px, so the aspect-correct libjpeg **draft-mode** decode runs at 1/2 scale — the full 36MB bitmap never exists. ⚠️ First draft had a silent no-op bug (square draft box never triggers on non-square photos) — **caught ONLY by the 12MP peak-RSS test**; that test class is now permanent practice (L-SW-2026-012).
- **`IMAGE_DECODE_CONCURRENCY` (env, default 2)** — semaphore in comic_extraction bounding concurrent decodes per worker (HEIC has no reduced-scale decode; 8 gthread threads × ~40-100MB transients was the F-L4-burst risk). DF ADDITION beyond Mike's approved list — flag in review.
- **`MALLOC_ARENA_MAX=2`** (Dockerfile ENV) — the RSS-ratchet fix (glibc arena fragmentation retained +25–83MB/grade; not testable on Windows, verify via prod memory metrics post-deploy).
- **gunicorn `--max-requests 500 --max-requests-jitter 100`** — staggered graceful worker recycling as residual-creep backstop.
- **Measured (offline suite, photo-realistic 12MP fixtures):** JPEG-only 4-photo peak 95→33MB; realistic mixed grade (3 JPEG+1 HEIC) +83MB transient/+1MB retained; 8-way concurrent burst gated to +149MB (~2-deep). Suite: scratchpad `test_memory_fix.py` (17/17) — correctness (cap/orientation/HEIC/centerfold/garbage/data-URL), uncapped-path-unchanged (barcode compat), 3 peak-RSS classes.
- **Docs in tree with it:** ARCHITECTURE (Dockerfile block trued up — it still showed the pre-Phase-4 CMD — + new memory-tuning env table), LESSONS **L-SW-2026-012** (peak-memory budget check + realistic-fixture rule; cross-project candidate), LAUNCH_READINESS Rule-5 header + **flap-dampening** logged as post-launch item (Mike: small future task, not urgent).

**Incident diagnosis (read-only, evidence-complete — detail in LAUNCH_READINESS Rule-5 header):**

- **🔴 THE REGRESSION — OOM cycling under normal grading load.** `normalize_for_photo_type` now runs on EVERY /api/grade photo at FULL resolution (no downscale anywhere in `normalize_orientation_b64`): 12MP decode + exif_transpose copy + RGB convert + q92 JPEG re-encode + base64, ×4 photos, on top of the request payload copies. Render memory metrics: fresh boot ~320MB → grade #11 (4 img) → 351MB retained → next grade in flight → **466MB → OOM KILL 17:28:10** (no graceful-shutdown lines = SIGKILL) → reboot 319MB → grade #12 (3 img) → 403MB retained → **490MB → OOM KILL 17:34:25**. RSS never returns after a grade (glibc arena fragmentation; 8 gthread threads, no `MALLOC_ARENA_MAX` in Dockerfile). Every kill drops all in-flight requests ("Failed to fetch" for those users). Idle = stable; each grade from the elevated base risks the ceiling. This is the booth-killer shape again — F-load CANNOT run on this build.
- **Mike's two reported failures explained (NEITHER is an exception in the new normalization code — no normalize/HEIC exceptions anywhere in the window):** (1) "Failed to fetch" on Generate Slab Report = in-flight request killed — candidate windows both confirmed as kills: the deploy swap (old container SIGTERM 17:17:20) or the 17:28:10 OOM; (2) "Could not identify comic automatically" = /api/extract 500 at 17:23:04 — **transient DB unreachability** (pool pre-ping correctly discarded a severed parked conn; the retry's FRESH `psycopg2.connect` to Render Postgres failed with the same `SSL SYSCALL ... connection abort`; DependencyMonitor failed simultaneously = external blip, ~1s, self-healed). Pool behaved as designed ("a second failure propagates — that's real").
- **What WORKED live:** grades that completed were correct + retained — submissions #11 (17:23:47, 4 images, 8.5) and #12 (17:30:29, 3 images, 8.0), both user_id 3 (Mike). HEIC decode itself: no errors.
- **📧 EMAIL STORM (side-finding):** ~15 dependency-alert emails 17:28:27–17:31:56 = the eBay account-deletion SELF-CHECK getting 502 from its own dying/rebooting service, amplified by `_send_alert_email`'s prune-then-realert dedup (a flapping warning re-emails on every warn→clear→warn cycle). Symptom of the OOM cycling, but the dedup wants flap-dampening as its own small item. DB `dependency_alerts` row confirms: `GET challenge-response` 502, first_alerted 17:34:37.
- ⚰️ *(superseded same session — decision block resolved as option (A), see MOST RECENT CHANGE above; the fix sketch became the built unit described there.)*
- **NEXT session order:** (1) Mike reviews + ships the memory-fix unit (block in MOST RECENT CHANGE context above / handed in chat) → post-deploy: `/health` ok, `runtime.heif=true`, one JPEG grade, THEN watch Render memory across 2-3 real grades (return-to-baseline is the thing to verify — L-SW-2026-012); (2) real-iPhone HEIC grade = Gate 0; (3) eBay collector fix spec (still owed as its own message — capture pipeline still DOWN); (4) F-mobile/F-load per checklist. Docs commit for SECTION_F_CHECKLIST.md etc. also still pending (block re-handed in chat 2026-07-16).

---

# (prior header) Where We Left Off - Jul 12, 2026

## Session 117 (Jul 12, 2026) — 2(d) SHIPPED `1437fdb` + VERIFIED + healthCheckPath SET (Render native health monitoring live for the first time); Section F opened (checklist + HEIC gate); HEIC/orientation fix BUILT IN TREE = first ship next session; 🆕 eBay collector selector rot diagnosed

**MOST RECENT CHANGE (2026-07-12 close, Rule 5): item 2(d) SHIPPED `1437fdb` + VERIFIED IN PROD (Mike ran commit/deploy; post-deploy checks passed: /health minimal body confirmed, Render Events clean, no crash loop) AND Mike set Render dashboard Health Check Path = /health — Render's native health monitoring (deploy gating + unhealthy detection) is live for the FIRST time. ⚰️ TOMBSTONE: this entry's earlier "2(d) drafted/approved awaiting ship" framings are DEAD — the commit exists at HEAD; do NOT re-present the 2(d) command block. ITEM 2 IS CLOSED except (c) Sentry, which Mike has designated NON-BLOCKING / POST-LAUNCH. NEXT SHIP (first thing next session) = the HEIC/orientation unit, in tree, offline 17/17, NOT committed.**

**🆕 NEW FINDING (Mike, 2026-07-12 night, live DOM inspection — formal fix spec arrives as its own message next session, do NOT draft ahead of it): eBay sales-capture extension is BROKEN by an eBay search-results markup restructure.** `collectSales()` in `CCExtensions/ebay-collector/content.js` selects `li.s-card`, which no longer exists (console-confirmed: `.srp-results`, `li.s-item`, `li.s-card` all return 0). New structure found live: item container = `div.su-item-card` carrying a **`data-listingid` attribute directly** (more robust than the old href-regex approach); title link = `a[class*="item-card__title"]`. Impact: the valuation-corpus capture pipeline is down until the selector fix ships. Capture-safety rules unchanged ([[feedback_ebay_capture_safety]] — human-triggered/paced, no auto-pagination).

**✅ WORKTREE/DIRTY-FILES QUESTION ANSWERED (read-only, 2026-07-12 close): nothing happened tonight — all of it is OLD, pre-existing, and SAFE to leave untouched.** (1) The ~500 `.claude/worktrees/zen-wozniak/*` "deleted" entries: those files were accidentally COMMITTED into the repo on **2026-03-19 (`61290bf`, a git add -A sweep — the exact footgun CLAUDE.md's GIT COMMIT RULE was later written against)**; the zen-wozniak worktree has since been removed from disk and from `git worktree list`, so the tracked copies read as deleted. They've shown in git status since at least Session 116 (recorded there as pre-existing dirt). (2) `TODO.md` modification = legitimate Session-109-era updates (dated Jun 22–23 in the diff: stacking steps 1–3, grading-accuracy item) never committed; `scripts/slabguard_crosscamera_test.py` (+5/−1) and `tests/SlabGuardTests/TP_RESHOOT_PROTOCOL.md` (+59) = S110/111-era SlabGuard-arc edits, also never committed. **Safe as-is:** everything is unstaged; deploys are unaffected (`.dockerignore` excludes `.claude/` since `820b0ae`); the only risk is a blind `git add -A`/`git add .` sweeping them into an unrelated commit — which the standing commit rule already guards. **Cleanup (joint, some future session, Mike runs):** one commit that removes `.claude/worktrees/` from tracking (`git rm -r --cached`) + adds it to `.gitignore` (also fixes the perpetually-modified `elegant-swirles/settings.local.json`), plus decide keep-vs-commit on the TODO/SlabGuard edits. ⚠️ Note: `61290bf` put business files (P&L spreadsheets, roadmap PDF, lock files) into git history — repo is private, history rewrite = optional post-launch hygiene, not urgent.

**Earlier today (PM): Mike's three calls — (1) HEIC = FIX (not waive; "really an orientation-normalization fix with HEIC as a side effect") → BUILT IN TREE same day, offline 17/17; (2) 2(d) approved → since SHIPPED (see header); (3) load target APPROVED + F-L4 ceiling burst added (16–18 concurrent vs the 16 thread slots — find the ceiling, not the floor); checklist canonical in repo, Mike keeps a supplementary personal phone run-sheet (no merge).**

- **🆕 HEIC/orientation fix BUILT (2026-07-12 PM), offline 17/17:** `requirements.txt` +`pillow-heif>=0.16.0`; `comic_extraction.py` registers the HEIF opener beside the PIL import (`HEIF_SUPPORTED` flag; graceful degrade with a loud boot print if the package is missing); `routes/grading.py` api_grade now normalizes EVERY photo via `normalize_for_photo_type` BEFORE the quality gate/moderation/API/retention (label→photo_type: 'Front Cover'→front, 'Spine'→spine, 'Back Cover'→back, 'Centerfold'→centerfold/landscape-allowed; media_type forced to image/jpeg) — undecodable photo fails LOUD with the existing quality-gate error shape naming the photo (deliberate deviation from /api/messages' send-original fallback: forwarding unreadable bytes would just resurface as an opaque Anthropic 400; frontend already renders quality_fail, zero frontend changes); `routes/admin_routes.py` adds `runtime.heif`; ARCHITECTURE.txt documented. **Side benefits verified in suite:** Rekognition moderation + quality gate now operate on HEIC uploads (both previously fail-open/blind on them); retention persists upright JPEG. Suite (scratchpad `test_heic_grade_normalize.py`, real comic_extraction + real route with stubbed auth/models/db/engine/retention): unit HEIC→portrait-JPEG per photo type; route 3×HEIC grade end-to-end (all blocks image/jpeg, front/spine portrait + centerfold landscape); upright JPEG untouched; spoofed heic media_type on JPEG bytes handled; garbage → 400 quality_fail naming Front Cover AND naming Spine when it's photo #2; label-less default portrait. **pillow-heif 1.4.0 verified against local Pillow 12.0.0** (Docker installs its own via requirements; manylinux wheels bundle libheif — no Dockerfile change needed). Post-deploy checks: `runtime.heif=true` on admin dependency-status; one normal JPEG grade (no regression); real-iPhone HEIC grade = checklist Gate 0 boxes.
- **(superseded framing from earlier today, kept for the audit trail):** item 2(d) `/health` DB check DRAFTED IN TREE (offline 17/17), NOT shipped — awaiting Mike's review/commit/deploy + the dashboard half (set Render `healthCheckPath=/health`; dashboard setting, NOT the stale root `render.yaml`). Now APPROVED per the PM header above.

- **1) HEIC/HEIF question ANSWERED (read-only trace): NO — the pipeline cannot decode HEIC anywhere.** No `pillow-heif` in requirements; frontend sends raw bytes (`FileReader.readAsDataURL`, no canvas re-encode) with `image/heic` media type; `/api/extract` dead-ends at the front photo (PIL raises inside `normalize_orientation_b64` → "Image could not be processed" — doesn't mention HEIC, reads as broken app); `/api/grade` forwards `media_type: image/heic` verbatim to the Anthropic API (accepts JPEG/PNG/GIF/WebP only → 400 → generic 500); quality gate fails OPEN on undecodable bytes; moderation = Rekognition (JPEG/PNG only). iPhone users survive today only where iOS silently transcodes (camera-capture inputs = JPEG; library picks usually transcoded; **Files-app picks = raw HEIC = guaranteed dead-end**; the multi-photo input's `accept=".heic"` invites raw HEIC). **🆕 ADJACENT FINDING: `/api/grade` runs NO orientation normalization at all** — the normalizer was wired into `/api/messages` + `/api/extract` only; the structured grading endpoint ships raw client bytes (sideways spine/back photos go to the model sideways). **Recommended one-unit fix (drafted as SECTION_F_CHECKLIST Gate 0, NOT built, decision pending):** add `pillow-heif` (register opener beside the PIL import in `comic_extraction.py`) + route `/api/grade` images through `normalize_for_photo_type` — kills the HEIC hole and the orientation hole together (normalizer always emits upright JPEG).
- **2) Item 2(d) DRAFTED IN TREE (`routes/utils.py`):** `SELECT 1` on the shared pool inside `health()`; DB failure → 503 `{status:'degraded', version}`, body stays minimal (failure detail to logs only, L-SW-2026-007), `check_all()` still can never fail the probe, conn closed in `finally`, root `/` rides the same probe. **Offline suite 17/17** (scratchpad, stubbed db/monitor/auth: happy path exact-body, checkout-fail, execute-fail-with-close-proof, monitor-explodes-still-200, root path both ways) + py_compile clean. **render.yaml deliberately NOT touched** (stale Blueprint — adding healthCheckPath there would be inert now and a trap on future Blueprint attach). Item 2 remaining after (d) ships: **(c) Sentry only.**
- **3) Section F checklist CREATED: `docs/SECTION_F_CHECKLIST.md`** (Gate 0 HEIC; real-device matrix min iPhone/Safari + Android/Chrome; mobile flows F-M1–M5 incl. camera vs library paths, DELETE mis-tap check, billing-on-mobile throwaway-account rule, PWA; load F-L1–L3 with booth-shaped target 10 concurrent / 3 grading / 10 min, memory <85%, 0 POOL EXHAUSTED; exit criteria). Results get recorded IN that file; status rolls up to LAUNCH_READINESS (F row + sequence item 4 + Rule-5 header updated this session).
- **Git truth (2026-07-12 close, verified):** HEAD = **`1437fdb`** (2(d) shipped; `routes/utils.py` clean). Dirty (this arc): **HEIC unit** = `requirements.txt`, `comic_extraction.py`, `routes/grading.py`, `routes/admin_routes.py`, `docs/technical/ARCHITECTURE.txt`; **docs** = `docs/SECTION_F_CHECKLIST.md` (new), `docs/LAUNCH_READINESS.md`, this file. Pre-existing dirt (NOT this arc, do not bundle — mechanism now explained in the worktree block above): `.claude/worktrees/*` (~500 zen-wozniak deletions + elegant-swirles settings mod), `TODO.md`, `scripts/slabguard_crosscamera_test.py`, `tests/SlabGuardTests/TP_RESHOOT_PROTOCOL.md`.
- **Ship block for NEXT session (Mike runs; ⚰️ the 2(d) commit that was here is DEAD — executed as `1437fdb`, do not re-run):**
  ```powershell
  git add requirements.txt comic_extraction.py routes/grading.py routes/admin_routes.py docs/technical/ARCHITECTURE.txt
  git commit -m "fix(grading): normalize every /api/grade photo before gates/API/retention (orientation + HEIC via pillow-heif) — Section F Gate 0; undecodable photo fails loud naming it; runtime.heif flag on admin dependency-status (offline 17/17)"
  git add docs/SECTION_F_CHECKLIST.md docs/LAUNCH_READINESS.md docs/sessions/WHERE_WE_LEFT_OFF.md
  git commit -m "docs(readiness): 2(d) shipped+verified (1437fdb, healthCheckPath set — native monitoring live); Section F canonical checklist (Gate 0 HEIC fix built; 16-18 ceiling burst); eBay collector selector rot diagnosed; worktree dirt explained"
  git push
  deploy
  # AFTER deploy verified:
  #  1. curl https://collectioncalc-docker.onrender.com/health   -> {"status":"ok","version":"5.6.0"}
  #  2. admin dependency-status (admin JWT) -> runtime.heif = true
  #  3. one normal JPEG grade through the live app (no regression)
  ```
- **NEXT session order:** (1) HEIC unit ship block above + post-deploy checks; (2) Mike sends the eBay collector fix spec as its own message (selector migration to `div.su-item-card` / `data-listingid` / `a[class*="item-card__title"]`) → DF drafts against it — capture pipeline is DOWN until this ships; (3) real-iPhone HEIC grade = checklist Gate 0 boxes → F-mobile runs; (4) F-load per approved target + F-L4 ceiling burst; (5) 2(c) Sentry = non-blocking/post-launch (Mike's designation, 2026-07-12). **On Mike's plate (no DF queue impact): Section F checklist review, Pixel 7 walkthrough, borrowing an iPhone for HEIC/Section F testing.**

---

## Session 116 (Jul 11, 2026) — Item 2 CONCURRENCY CLUSTER (Phases 1–4) COMPLETE: Phases 3+4 SHIPPED + VERIFIED IN PROD same day; 2(f) resource self-alert DRAFTED in tree (own ship unit, awaiting review)

**MOST RECENT CHANGE (2026-07-11 PM, Rule 5): Phases 3 AND 4 SHIPPED (Mike ran both commits/deploys: Phase 3 `901a49e`, Phase 4 `820b0ae`) + VERIFIED IN PROD. Item 2's concurrency cluster (a)+(b)+(e) is CLOSED in LAUNCH_READINESS; the single-worker booth-killer is dead. NEXT = 2(f) resource self-alert (gate met, calibration numbers on file). ⚰️ TOMBSTONE: this entry's original framing — "drafted in working tree, NOT committed, awaiting review" — is DEAD; do NOT re-present the Phase 3/4 command blocks, both commits exist at HEAD.**

**Prod verification (2026-07-11, post-deploy, read-only):** Render live deploy = `820b0ae` (matches local HEAD); boot log `Using worker: gthread` + 2 workers (pids 7/8); **Mike's concurrency probe PASSED — 12× `/health` instant while an ASM #41 grade was in flight** (pre-fix: 10–30s queue); memory **357.8–358.0MB steady ≈ 70% of 512MB** (inside the 350–380MB estimate, 1×12 fallback not needed); logs: **0 `POOL EXHAUSTED`, 0 `[DB]` teardown lines** (server-side filtered search, control-validated); pg_stat_activity: **4 connections (1 active) vs max_connections=103**. Build context 4.9GB → ~450MB per the Phase-4 commit. **⚠️ 2(f) calibration note: WARN=80% placeholder (410MB) is only ~52MB above the new steady state — wants sustained-over-N-checks semantics or a higher line; decide at build.**

*(Original drafting record, superseded above but kept for the audit trail:)* Two separate ship units by design (Mike's call): Phase 3 (lower-risk plumbing) → commit/deploy/smoke alone; THEN Phase 4 (the behavior change: real concurrency) → commit/deploy → concurrency probe.

- **Phase 3 (in tree, offline-verified 27/27):** (a) `routes/billing.py` — explicit `try/finally conn.close()` on all 9 direct-connection sites (belt over the wsgi teardown net; behavior contracts preserved: get_user_plan fallback dict, entitlement fails closed, webhook handlers still swallow, check_feature_access still degrades to allow/Unknown). (b) `wsgi.py` — before_request admin check now reads the **signed JWT `is_admin` claim** (verified present, `auth.py:118`) instead of `get_user_by_id()` = one pooled DB checkout saved on EVERY authed request; `get_user_by_id` import dropped. Safety audit done: every ADMIN-AUTHORIZING route (`admin_routes`, `slabguard`, `feedback`) uses `@require_admin_auth`, which does its own fresh DB check + sets g.admin_id itself; before_request's g.admin_id only feeds soft surfaces (vision rate-limit/daily-cap bypass, lookup_demand `is_internal` tag) — staleness bound = 30-day token life (admin promoted/demoted mid-token sees old soft-flag behavior until re-login). Offline suite: stubbed pool, 27/27 — happy + exception paths, close-called-exactly-once each, JWT roundtrip carries is_admin.
- **Phase 4 (in tree):** `Dockerfile` CMD → `--workers 2 --threads 8 --worker-class gthread` (unchanged: `--timeout 300 --bind`), sizing comment in-file (512MB Starter, RSS ~173MB/worker, fallback 1×12); **`.dockerignore` NEW** — excludes .git (134MB), tests/ (783MB), ComicBookImages/ (100MB), .claude (1.9GB local), .env (secret vector), docs/, test-photo dirs, *.csv/*.db exports. Runtime-safety audit done before excluding: signature refs come from R2 at runtime (local `signatures/` KEPT anyway); fonts/json data/prompts/utils/migrations/HTML all KEPT; `comics_pricing.db` = offline scripts only (comic_lookup/scraper/database_setup, not imported by the web path).
- **Known accepted consequences of 2 workers (flagged, not bugs):** in-memory stores go per-worker → vision rate-limit/daily caps effectively ×2 (they were already per-process); gunicorn `--timeout` under gthread is a worker-liveness check, not a per-request killer → long grades safer, not riskier; DB ceiling 2 pools × 8 = 16 + overflow vs ~100 usable.
- **Verification plan (Phase 4, post-deploy):** (1) `/health` baseline; (2) **concurrency probe** — fire a real grade AND hammer `/health` in parallel (pre-fix: health queues 10–30s behind the grade; PASS = health answers <1s throughout the grade); (3) Render Metrics memory watch (~350–380MB expected; sustained >80% of 512MB → drop to 1×12 fallback); (4) logs clean of `POOL EXHAUSTED`/teardown lines; (5) re-run the 12-request connection probe.
- **Rollback levers:** Phase 4 = one-line CMD revert (restore the old CMD line, redeploy) — workers/threads carry NO data/schema coupling; Phase 3 = plumbing-only, teardown net still active underneath; pool kill switch `DB_POOL_DISABLED=1` unchanged.
- **Incidental findings (no action taken):** root `render.yaml` is STALE (`startCommand: gunicorn api_server_v3:app`, a dead entrypoint — Render ignores it for collectioncalc-docker, but a future Blueprint attach would resurrect it); billing's "→" arrows in print() crash cp1252 consoles locally (prod Linux/UTF-8 unaffected).
- **🆕 SAME DAY (2026-07-11 PM): 2(f) resource self-alert DRAFTED IN WORKING TREE (its gate met hours earlier), offline-verified 16/16, awaiting Mike's review as its own ship unit.** `check_resources()` in dependency_monitor.py: cgroup v2/v1 memory + `pg_stat_activity` vs (max_connections−3) + per-worker pool_stats, 5-min TTL, **sustained ×3 (~15 min) before warning**; calibration decided at build: WARN=85% mem / 70% DB (env-overridable) — instant-80% would have paged on GC spikes given the 70% steady state; rides the existing DB-persisted state-change email dedup (first worker to trip emails, others dedup); `resources` snapshot on `/api/admin/dependency-status`; resource lines filtered OFF public `/health`. MONITORING-ONLY (fallback 1×12 / tier upgrade = Mike's manual calls, stated in the alert text). Files: dependency_monitor.py, routes/utils.py, routes/admin_routes.py, CLAUDE.md (monitored-services line), docs/technical/ARCHITECTURE.txt (env vars). Post-deploy test: dependency-status shows the `resources` block.
- **🆕 LATER SAME DAY: 2(f) SHIPPED `bf92fcc` + VERIFIED IN PROD (all three of Mike's checks passed — live `resources` block via admin JWT: 63.4% mem / 2% DB / streaks 0; `/health` zero resource lines; dedup-prune + admin-auth + shared-pool code confirmations quoted from HEAD). ⚰️ The "drafted awaiting review" framing above is DEAD. ITEM 2(f) CLOSED.**
- **✅ FOLLOW-UP UNIT SHIPPED `9641a0a` + VERIFIED same evening (all three checks, Mike): chip live + healthy (358/512MB = 69.9% — back at the expected steady state after the fresh-container dip; DB 4%; pool 2/8), `/health` = exactly `{status, version}`, deploy clean.** ⚰️ The "drafted awaiting review" framing (which shipped inside `9641a0a`'s own docs) is DEAD. (i) admin.html resource status chip (amber ≥warn or streak >0; field names verified against live prod payload); (ii) public `/health` minimized — was exposing installed Stripe version, versions-behind count, internal monitoring notes; `check_all()` STILL runs inside it (no cron — health polling is the monitor's scheduler; state-change email fires inside check_all); detail + runtime flags (barcode/moderation) now admin-only on `/api/admin/dependency-status`. Offline suite was 6/6 incl. exception-never-leaks. ⚠️ Habit note: `curl /health` no longer lists dependency warnings.
- **Git truth (updated 2026-07-11 night):** HEAD = `9641a0a` (health-minimize + chip); beneath it `bf92fcc` (2f) / `3ce6e2d` (docs) / `820b0ae` (Phase 4) / `901a49e` (Phase 3) — the entire day's code is shipped. Dirty (this arc) = docs only (this file + `docs/LAUNCH_READINESS.md`, closure edits). Pre-existing dirt (NOT this arc, do not bundle): `.claude/worktrees/*` deletions/mods, `scripts/slabguard_crosscamera_test.py`, `tests/SlabGuardTests/TP_RESHOOT_PROTOCOL.md`. **Item 2 remaining: (c) Sentry, (d) `/health` DB check — the only open pieces; note (d) now also gates Render's `healthCheckPath` + native-notification value (see 2(f) entry).**

---

## Session 114 (Jul 9, 2026) — Item 2 Phase 1 (shared DB pool) SHIPPED + VERIFIED; pooling/gunicorn plan delivered; 2(f) resource-alert designed; NEW valuation finding: Cover-A variant misclassification (modern mispricing, systemic)

**⚠️ CURRENT STATE (2026-07-10 PM; Rule 5, read this FIRST): MOST RECENT CHANGE = eBay Issue 1 (compliance timeout) INVESTIGATED + CLOSED by Mike's portal check — BOTH eBay endpoint halves are now DONE; NEXT item 2 is fully closed and the eBay endpoint carries zero launch-blocking work.** Issue-1 findings (detail in LAUNCH_READINESS Dependency watch): suspension = 1000 CONSECUTIVE failures (no 200 within 3000ms), counter self-heals on any success → warm ~0.45s endpoint can't plausibly trip it; registered URL + verification token confirmed matching prod/Render; Data-Handling bulletin N/A (CN/RU/etc.-scoped); eBay's field reference independently confirms `username` as the deletion-notice identity field (validates the Issue-2 fix); keep-warm/monitor-timeout = optional nice-to-have now. OPEN MICRO-ITEM (Mike, 2-min): enable the portal "Notify Me" failure-alert email; nice-to-have: one-time confirm the dev account is US-registered. *Earlier same day:* eBay Issue-2 security fix SHIPPED (`060f1dc`, Mike ran commit/deploy) + VERIFIED IN PROD, all three checks passed. Evidence: (1) unsigned curl POST → 412 `{"error":"Signature required"}`; (2) eBay portal "Send Test Notification" ×multiple → every one verified successfully, INCLUDING across a mid-sequence eBay key rotation (`kid=3cf880e7…`→`9936261a…` — the unknown-kid→fresh `getPublicKey` fetch path proven live, not just the cache), each proceeding to identity lookup and correctly matching no user on eBay's synthetic test IDs; (3) GET challenge-response still 200/valid hash. The raw-body byte assumption is proven against genuinely eBay-signed messages, not just self-signed test keys. ⚰️ TOMBSTONE: this checkpoint's prior framing — "fix DRAFTED + OFFLINE-VERIFIED, UNCOMMITTED, awaiting Mike's review" — is DEAD; do NOT re-present the eBay-fix command block, the commit exists at HEAD (`060f1dc`). LAUNCH_READINESS updated same day (Rule-5 header + sequence-item-3 eBay bullet ✅ + Dependency-watch Issue-2 line). REMAINING (re-revised 2026-07-10 PM ×2 — normalizer fix COMMITTED `15cb459` + docs/lessons `2904fa7` [L-SW-2026-008/009/010 finally in history], DEPLOYED [new code confirmed in container: `_fuzzy_tokens_supported` grep=2, "Cover A"→is_variant=False], dry-run VERIFIED [computed variant 15,344 vs stored 18,044 = 2,700 flipping ≈ the audit's ~2,601 + rows captured since]; ⚰️ command blocks #2/#3 below are EXECUTED, do not re-run the commits): (1) ✅ **live re-normalize COMPLETE + VERIFIED (2026-07-10 late PM): 71,449/71,449 updated, 0 errors; stored `is_variant` = exactly 15,344; Defenders→Descender mis-merge = 0 rows; "Absolute Batman Annual" separated into its own canonical; end-to-end live-app check: AB#1 9.0 → raw FMV $169.99 (blended, real comps, verdict_reliable=true) vs pre-fix $150.00. Gap to ~$185–300 market = Layer 3, deferred to R1/R2 by prior decision. NOTE for future queries: `canonical_title` is stored TITLE-CASE ('Absolute Batman', not 'absolute batman'). ⚠️ CORRECTION to an earlier note: the ~1hr runtime was from the RENDER SHELL (likely internal DB URL), so my "external hostname" latency attribution was speculation — expect the re-run below to take ~1hr again;** (1b) **🆕 LEADING-"NEW" BUG FOUND during the market_sales dry-run (2026-07-10 late): `title_normalizer.py:314` has stripped a bare leading "new" as a condition prefix SINCE DAY ONE (`ac9b2be`), eating series names — New Mutants/New Teen Titans/New Warriors/New X-Men etc. Before `15cb459` the permissive fuzzy matcher silently repaired most of it; the per-token guard correctly refuses now, so the ebay re-normalize SURFACED it: 1,072 ebay rows carry New-less canonicals (635 'Mutants' incl. the #98 1st-Deadpool key; 210 New Teen Titans CONTAMINATING the real Teen Titans pool — that class was wrong since day one, not caused by the rewrite). FIX DRAFTED in tree (strip only 'brand new', keep bare 'New'; safe because condition-prefix listings still fuzzy-merge with all tokens supported): `title_normalizer.py` one-liner + comment, PLUS `normalize_batch.py` extended with `--table market` (maps normalized_issue_number, raw_title→title fallback, does NOT write is_facsimile/is_reprint = barcode-derived on market_sales). OFFLINE-VERIFIED: 9/9 targeted cases; full-corpus diff fixed-vs-shipped over all 71,449 ebay rows = exactly 1,063 rows change, 0 variant flips. ✅ **SHIPPED + BOTH TABLES RUN + VERIFIED same night (2026-07-10): Mike committed/deployed, ebay re-run 71,449 + market 9,963, 0 errors; post-run exact ('New Mutants' 963 / 'Mutants' orphans 0 / Teen-Titans contamination 0 / is_variant 15,344 ebay + 221 market / Monstress clean); live app: New Mutants #98 @9.0 → $300 raw, exact, high confidence, 10 comps; AB#1 unchanged $169.99. NORMALIZATION LOOP CLOSED. Residual tail (post-launch, logged in LAUNCH_READINESS item 6): ~28 New-*-series fuzzy-merges into parent series (fix = add New Avengers/Champions/FF/Suicide Squad/Excalibur to known_titles.json), media junk in pools, emoji-led canonicals;** (2) market_sales equivalent pass (8,604 canonical rows, small extension — LAUNCH_READINESS item 6); (3) micro-items: eBay portal "Notify Me" email (2-min); prior docs note = `docs/LAUNCH_READINESS.md` + this file + `docs/LESSONS.md` (⚠️ L-SW-2026-008/009/010 STILL never committed — folded into command block #3 below) + optionally the untracked `docs/technical/VALUATION_FMV_FIXES_SPEC.md` (S111 spec, referenced by session notes but never added — include or defer, Mike's call). Git truth at write (verified): HEAD = `060f1dc`; dirty = `title_normalizer.py`, `docs/LESSONS.md`, this file, `docs/LAUNCH_READINESS.md`.**

**MOST RECENT CHANGE (earlier 2026-07-09): Item 2 Phase 1 VERIFIED IN PROD: `db.py` shared pool + 8 getter rewires (~59 sites) + wsgi teardown leak-net (commit Mike's; deploy verified). Evidence: full smoke passed, zero `[DB]` warnings, 12-request public-lookup probe = ZERO connection growth (app parked-set flat at 5; old code opened 4+ fresh connections per grade). Phase 2 QUEUED = ~75 inline `psycopg2.connect` sites → `db.get_db()`. Detail + phase plan in LAUNCH_READINESS item 2(b) (SoT). Offline verification before deploy: py_compile ×10, 15/15 pool-mechanics checks vs RO string (both cursor flavors, reuse, flavor reset, idempotent close, exhaustion→overflow, kill switch), teardown net proven end-to-end (leaked-on-exception connection force-returned).**

### Also this session
- **Read-only pooling/gunicorn plan** (facts: Render Starter 512MB/0.5CPU, measured RSS ~173MB, max_connections=103, ~59 getter-routed + ~75 inline sites, two cursor_factory flavors; 4-phase rollout, pool-first-workers-last; gunicorn target `--workers 2 --threads 8 gthread`, fallback 1×12 if memory alerts).
- **2(f) resource-ceiling self-alert designed** (Render has NO native threshold alerts — verified against current docs; self-check in dependency_monitor: cgroup memory + pg_stat_activity vs ceiling + pool_stats(); WARN 80%/70% placeholders, calibrate post-Phase-1; monitoring-only, tier upgrade stays Mike's manual call). Queued behind Phase 2/3. Mike separately: enable Render native event notifications (dashboard-only).
- **🔍 NEW VALUATION FINDING (read-only diagnosis, logged in LAUNCH_READINESS item 6): Cover-A variant misclassification — modern multi-cover mispricing, SYSTEMIC.** Absolute Batman #1 (Dragotta A, 1st print) 9.0 → raw FMV $150 vs real Cover-A market ~$185 median/$238–395 clean copies. Mechanism corpus-proven: `title_normalizer.py:268` flags "Cover A" ITSELF as `is_variant` → the standard cover's 156 best-labeled sales are EXCLUDED from their own estimate; included "standard" pool (median exactly $150.00 = shipped FMV) retains word-form printings ("Tenth Print"), Noir editions, artist-name variants, Annual-canonical leakage, a graded=false CGC slab, missed lots. Extraction DOES identify cover/printing (vision + barcode digits 4/5) but the valuation key drops it (title+issue+issue_type only). Fix-B gate correctly green (pool is big) = confidently wrong. Fix tiers logged, NOT applied; placement decision pending (tier-1 = 1-line regex + flag re-normalize — cheap, moderns are the con-booth demo books).
- **Interaction flag:** the Cover-A finding is upstream of R1/R2 — grading-accuracy benchmarks inherit wrong-product FMVs regardless of grade correctness.

### LATER SAME DAY (2026-07-09 PM) — two working-tree deliverables awaiting Mike's return
- **Phase 2 DONE in working tree, approved in principle:** all 57 inline `psycopg2.connect` sites → `db.get_db()` (16 files, +85/−66; expressions only, control flow untouched; `database_url` locals deliberately left; 2 disguised getters converted; helper modules incl. after close-discipline check). All compile; zero residual connects in web path. **Mike: review → commit → deploy → smoke → DF re-runs connection probe.** Parked set may legitimately grow past 5 (more surface pooled); signal = `POOL EXHAUSTED` lines or growth past DB_POOL_MAX=8.
- **Cover-A + cross-title fix DRAFTED (Mike decided: Layers 1+2 pre-launch as one correctness fix; Layer 3 grade-aware raw → R1/R2):** `title_normalizer.py` +58/−3. Corpus audit = SYSTEMIC: 748 rows/23 canonicals mis-merged (DEFENDERS→descender 56 rows the standout beyond the Absolute line); 2,601 Cover-A rows flip to standard; AB#1 median $158.50→$178.20 end-to-end. Full numbers + rollout (normalize_batch re-run; market_sales needs small extension) in LAUNCH_READINESS item 6.

### NEXT (revised 2026-07-09 late — Phase 2 shipped; eBay endpoint promoted to active)
1. ~~Phase 2 review+commit+deploy~~ — **DONE (`e75f0f9`), gate passed** (see CURRENT STATE block).
2. **eBay account-deletion endpoint — ✅ FULLY DONE 2026-07-10, both halves.** Issue 2 (security): SHIPPED `060f1dc` + VERIFIED IN PROD (412 unsigned / portal test notifications verified incl. live key rotation / GET 200). Issue 1 (compliance timeout): CLOSED same day PM — downgraded to low-probability/self-healing (1000-consecutive-failure threshold, self-resetting; config confirmed correct; see CURRENT STATE + LAUNCH_READINESS Dependency watch). Only residue: portal "Notify Me" micro-item (Mike, 2-min). *(Historical detail of the shipped fix:)* new `ebay_signature.py` (ECDSA/SHA1 over RAW body per eBay's scheme; base64-JSON `x-ebay-signature` header {alg,kid,signature,digest}; public key via Notification API `getPublicKey` w/ client-credentials app token, cached 1h; tri-state valid/invalid/unavailable → 200/412/500 — 500 makes eBay REDELIVER, never ack-and-drop a real GDPR notice; kill switch `EBAY_SIGNATURE_VERIFICATION_DISABLED=1`) + `routes/ebay.py` POST branch verify-first + **bonus bug fixed: real eBay payloads nest identity under `notification.data` — old top-level reads meant REAL notifications never deleted anything (only forged flat ones could)** + `cryptography>=42` in requirements + monitor/ARCHITECTURE touches. Offline-verified: py_compile + 12/12 branch tests (self-signed EC key, tampered body, malformed headers, alg drift, key-fetch outage, non-EC key, kill switch, cache path). Raw-body byte assumption subsequently proven in prod against real eBay-signed messages (see CURRENT STATE). ⚰️ The commit/deploy command block that lived here is DEAD — executed as `060f1dc`, do not re-run.
3. **title_normalizer fix commit/deploy + corpus re-normalize (dry-run first)** — verified, sits on disk, command block #2 below; slots whenever Mike runs it.
4. Phase 3 (billing finally + before_request lookup) → Phase 4 (gunicorn CMD + .dockerignore).
5. 2(f) resource alert after Phase 2/3.
6. eBay OAuth pool surface spot-check when extension flakiness clears.

### Morning command blocks (revised 2026-07-10; git truth: HEAD `060f1dc`, block #1 DONE as `e75f0f9`, eBay block DONE as `060f1dc`)
```powershell
# ⚰️ 1) Phase 2 — EXECUTED as e75f0f9, verified; do not re-run.
# ⚰️ (eBay Issue-2 block from NEXT item 2) — EXECUTED as 060f1dc, verified; do not re-run.

# 2) Normalizer correctness fix (still pending; slots whenever Mike runs it)
git add title_normalizer.py
git commit -m "fix(valuation): Cover-A is standard not variant; token guard on fuzzy canonical match (748 cross-title mis-merges, 23 titles)"
git push
deploy
# → then corpus re-normalize in Render shell: python normalize_batch.py --dry-run  (review) → python normalize_batch.py

# 3) Docs + lessons (BOTH eBay issues closed in LAUNCH_READINESS + this file; LESSONS 008/009/010 folded in — still never committed)
git add docs/LAUNCH_READINESS.md docs/sessions/WHERE_WE_LEFT_OFF.md docs/LESSONS.md
git commit -m "docs(readiness): eBay endpoint fully closed — Issue 2 verified in prod (412/portal-tests/key-rotation), Issue 1 downgraded (1000-consecutive-failure threshold, config confirmed); lessons L-SW-2026-008 (S111, unstaged until now) + 009 + 010"
git push
# optional add to the same commit if wanted: docs/technical/VALUATION_FMV_FIXES_SPEC.md (S111 spec, currently untracked)
```

---
# (prior header) Where We Left Off - Jul 8, 2026

## Session 113 (Jul 8, 2026) — BILLING ITEM 1 FULLY CLOSED: one-diff shipped, core teardown + add-on both PASSED, both guard branches observed live; mid-test scare diagnosed read-only (dashboard-created subs — fix NOT implicated); PYTHONUNBUFFERED gap found, fixed, confirmed

**MOST RECENT CHANGE: 2026-07-08 (PM) — LAUNCH_READINESS sequence item 1 CLOSED. One-diff SHIPPED (`3935ce5`, 19:42 UTC, Mike ran all git/deploy); core teardown PASSED all three fields (`plan=free`/`status=canceled`/`stripe_subscription_id=NULL` — the field that never cleared before), doubly confirmed by cross-account comparison (user 32 clean vs 30/31 pre-fix stale); add-on PASSED with BOTH guard branches directly observed in real-time logs after the PYTHONUNBUFFERED deploy — skip branch (non-record dashboard-sub cancel → plan unchanged pro/trialing + `ignoring …, not the sub of record`) and teardown branch (record cancel → full 3-field reset + `→ free (sub … cleared)`). Buffering fix confirmed working (live log lines). ⚰️ Supersedes LAUNCH_READINESS's "targeted direct UPDATE, don't touch the helper" prescription — the shipped fix IS in the helper (`_UNSET` sentinel, `billing.py:183`; omission still skips, explicit `None` writes NULL, all 5 callers audited). NEXT SESSION: sequence item 2 — gunicorn workers/threads + DB pool + finally-closes (+ Sentry, /health DB check, .dockerignore). Detail lives in LAUNCH_READINESS.md (SoT); this entry is the pointer + incident record.**

### What shipped (Mike committed/deployed; Claude drafted + applied to tree only)
- `routes/billing.py` (`3935ce5`): (a) **step-3 multi-sub guard** — `handle_subscription_deleted` selects `id, stripe_subscription_id`, downgrades only when the deleted `sub.id` IS the sub of record; **falls open** (downgrades) when stored sub_id is NULL or event id missing — conservative bias: never trap a user on a paid tier with no live sub, never silently skip a legitimate downgrade. Skip path logs `ignoring <id>, not the sub of record`. (b) **sub_id-NULL** — `_UNSET` sentinel default on `update_user_subscription.stripe_subscription_id`.
- `Dockerfile`: `ENV PYTHONUNBUFFERED=1` — shipped + deployed same session; **confirmed working** (the add-on test's guard log lines appeared in real time, the thing the old buffering made impossible).

### ⚠️ MID-TEST INCIDENT + DIAGNOSIS (read-only, ~20:15–20:30 UTC) — recorded so the pattern is recognizable next time
- **Scare:** after the passing core test, two new subs on the same throwaway customer (Pro $4.99 ~20:04, Guard $9.99 ~20:08) showed real/active in Stripe but the DB stayed frozen at post-cancel state. Looked like webhooks dropping.
- **Diagnosis (evidence, not theory):** Stripe Workbench event stream shows **both subs were DASHBOARD-created** — Source=Dashboard, NO `checkout.session.completed` anywhere in either cascade, immediate charge (our checkout ALWAYS attaches a 14-day trial → $0 first invoice, as the 19:54 core-test cascade shows). Dashboard subs fire `customer.subscription.created` — **not subscribed by the endpoint, no handler in billing.py** — plus `invoice.payment_succeeded` (log-only handler). **DB unchanged = system working as wired.** Endpoint deliveries: ALL 200, 0 failed, error rate 0%. Deploy clean (one deploy, live 19:42:18, zero restarts). `/health` 200. **The billing fix is NOT implicated.**
- **Real finding — the service is LOG-BLIND: `PYTHONUNBUFFERED=1` missing on collectioncalc-docker** (violates cross-project L-2026-020). All `print()` buffers until container death; proof = the dying pre-deploy container flushed 10 stale `[Billing]` lines with identical timestamp 19:43:17 (old log format, days-old events). The new container's core-test logs are still invisible in its buffer. Also: no gunicorn access logs. This is why Render logs could not answer the delivery question and Stripe's dashboard had to.
- **Tooling note (for future read-only prod diagnosis):** `RENDER_API_KEY` in local shell env works for Render API reads (services/deploys/events/logs; logs need `ownerId`); `DATABASE_URL_RO` in `.env` for read-only SELECTs; Stripe delivery status via Chrome → dashboard (Workbench → Webhooks → Event deliveries). Full loop ran without touching prod.

### ✅ NEXT list from earlier in this session — ALL DONE same day (recorded for the arc)
1. ~~Cancel the two stray dashboard subs~~ — done; fall-open path behaved (idempotent free/canceled re-write).
2. ~~PYTHONUNBUFFERED commit + deploy + fresh shell~~ — done; confirmed working (live log lines).
3. ~~Add-on re-run in the correct shape~~ — **PASSED, both guard branches observed** (see MOST RECENT CHANGE).

### NEXT SESSION
**LAUNCH_READINESS sequence item 2** (locked since S112, now the active item): gunicorn workers/threads (`--workers 2 --threads 8 --worker-class gthread`, sized to instance RAM) + DB connection pool + close-in-`finally` sweep, plus Sentry, `/health` DB check, `.dockerignore`. Note: item 2(c)'s first slice (PYTHONUNBUFFERED) already landed this session. **Read-only plan for the pool+gunicorn work DELIVERED 2026-07-09** (4 phases: db.py pool+getter rewire → inline sweep → finally/hot-path → gunicorn CMD; facts: Starter 512MB/0.5CPU, measured RSS ~173MB, max_connections=103, ~59 getter-routed + ~75 inline connect sites, getters have two cursor_factory flavors). **Queued behind Phase 1 verification: item 2(f) resource-ceiling self-alert** (cgroup memory + pg_stat_activity vs ceiling in dependency_monitor; Render Starter has no native threshold alerts — verified; monitoring-only, upgrade decision stays Mike's).

### Post-launch (logged, no action): webhook sub-state sync hardening
Dashboard/API-created subs invisible (no `.created` handling) + `handle_subscription_updated` customer-matched last-writer-wins (`plan or 'free'` metadata footgun) — one-touch fix spec'd in LAUNCH_READINESS Post-launch section (2026-07-08 bullet).

---

## Session 112 (Jul 7, 2026) — DF full technical review (4-track, read-only) + BS competitive requirements reconciled; NEW launch-blocker (gunicorn single worker); grade-retention status corrected (BUILT, not spec-only); moat reframed

**MOST RECENT CHANGE: 2026-07-07 — Full technical review reconciled into `docs/LAUNCH_READINESS.md` (the SoT — read THAT for all detail; this entry is the pointer). NEW LAUNCH-BLOCKER: gunicorn = 1 sync worker, no DB pool (booth-killer; LAUNCH_READINESS sequence item 2). ⚰️ STATUS CORRECTION: grade retention is BUILT+DEPLOYED (`801e79d`/`6fb83f7`) — the long-carried "spec only, gated on privacy" framing is DEAD (privacy disclosure shipped S107, build followed; remaining = purge job + pin-on-feedback + areas_not_visible persistence). Moat REFRAMED per BS competitive doc (mirrored at `docs/SW_COMPETITIVE_REQUIREMENTS_FOR_DF.md`): NOT the only AI raw-grader (ComicMintAI / Comic Locker / Gradr claim the same; none proven) → the race is FIRST DEMONSTRABLY ACCURATE + honest-about-uncertainty; R2 side-by-side competitor benchmark added to grading triage (one motion with the consistency-harness run). eBay deletion endpoint = TWO independent issues — the probe-timeout compliance diagnosis is NOT superseded by the new no-signature-verification security finding (BS doc said "struck"; corrected, Mike agreed). NEXT SESSION LOCKED (Mike, this session): (1) billing one-diff (step-3 multi-sub guard + sub_id-NULL; pass = `--check-db` teardown → sub_id=NULL), THEN (2) gunicorn workers/threads + DB pool + finally-closes (+ Sentry, /health DB check, .dockerignore). Prior (2026-06-29): BILLING hard gate essentially cleared (Model A + teardown verified); anti-abuse logged MEDIUM, coupled to gated signup.**

### Session 112 summary (detail deliberately NOT duplicated here — LAUNCH_READINESS.md is the SoT)
- **What ran:** 4 parallel read-only review tracks (grading-accuracy deep-dive, architecture/code-health, security/perf/scalability, feasibility inventory), then BS's competitive requirements doc reconciled in.
- **Grading-accuracy facts now on file** (LAUNCH_READINESS sequence item 6): grade = ONE temp-0 Sonnet call; multi-run voting built server-side but dead in prod (frontend hardcodes `runs:1`); consistency NEVER measured (live harness exists at root: `test_grading_consistency.py --live`); confidence = photo-count lookup, displayed nowhere; no Fix-B-style grade gate; quality gate checks first image only; PROMPT_VERSION absent. Recommended pre-launch minimum ≈2 contained sessions: PROMPT_VERSION → harness run + R2 competitor benchmark (one motion) → `grade_reliable` + amber partial-view UI.
- **Security:** 3 unauthenticated upload endpoints + eBay deletion no-signature = LAUNCH_READINESS sequence item 3 (before beta admits strangers); OAuth-state CSRF / body-size cap / atomic cap-increment = post-launch tier. SQL injection / IDOR / JWT / Stripe-webhook signatures / secrets all verified clean.
- **Committed this session (Mike):** LAUNCH_READINESS reconciliation + competitive-requirements mirror.
- **Zero production code touched** (review + docs only). Draft-then-authorize rhythm held; Mike ran all git.

---

## Session 111 (Jun 27, 2026) — State-Recording Protocol enshrined; E3 RAN → single-image PARKED; LIVE Slab Guard copy RESCOPED (provenance + candidate-sightings beta); pivot to VALUATION

**[SUPERSEDED as most-recent by Session 112 above] MOST RECENT CHANGE: 2026-06-29 — BILLING hard gate essentially CLEARED (verify-against-Model-A session). Cancel = Model A confirmed (portal cancel-at-period-end); trial cancel = $0 + access-to-period-end; never-tested TEARDOWN entitlement OBSERVED working (immediate-cancel → plan=free/status=canceled, access lost). Two contained cleanups queued as ONE diff in `handle_subscription_deleted`: step-3 multi-sub guard + sub_id-NULL (`billing.py:197` None="skip" footgun); next-session pass condition = re-run `--check-db` teardown → sub_id=NULL. Anti-abuse logged (MEDIUM, not fixed): repeat-trials + email-alias evasion, coupled to "no un-gated public signup before they ship." Full launch status lives in `docs/LAUNCH_READINESS.md` (the SoT). Prior (2026-06-27): created LAUNCH_READINESS.md; VALUATION Fix A/B shipped+verified; grading-accuracy signal; L-SW-2026-008.**

**Built draft-for-review; Mike runs all git/deploy. Zero production code shipped this arc (E3 is a standalone harness). State-Recording Protocol adopted into the operating model after last night's near-miss. Earlier-in-session reversal (re-capture → SAM) tombstoned below.**

### ⚰️ E3 RESULT + DECISION TOMBSTONE — single-image cross-camera recovery PARKED (2026-06-27)
- **E3 RESULT: TP 6/6, FP 4/6 → REJECTED by the both-sets gate.** Read the per-pair reasoning, not the score: E3 didn't get more *discriminative*, it got more *permissive* — it now matches BOTH same and different copies. The 4 FPs (Heros, Marvel_Universe_1, Marvel_Universe_2, Wolverine — all **low-wear**) matched on **shared printed art** (the arbiter's own words: "artwork registration corresponds", "printed art registers at identical positions", "few sharp wear landmarks"). The 2 correct rejections (Iron_Man_200, The_Invaders_41 — both **high-wear**) found **real divergent wear** ("jagged chip/tear absent in REF", "outward bulge and chips near 65-70%"). The discriminator is real but the band can't separate copy-unique wear from copy-shared print on low-wear books. CSV: `tests/SlabGuardTests/e3_bothsets.csv`. Cost $0.28.
- **ENSEMBLE (Mike's old-arbiter-veto idea): DEAD.** Read-only data check (no Opus) against the old corner-crop arbiter (`truepositive_results.csv` / `crosscam_fp_results.csv`): hard AND-gate = **TP 1/6, FP 0/6 = the old method bit-for-bit**. Deeper reason it can't work: on the 4 low-wear books the old arbiter is a constant "different" and E3 is a constant "same" — both **saturated in opposite directions, zero discriminative signal in either**. The disagreement is pure opposite-bias, not complementary competence → **correlated blindness, nothing combinable**. (Only Iron_Man carries independent signal: E3 discriminates, old is reject-biased.)
- **CEILING: physical, not representational — triangulated from 3 directions.** Ensemble → reproduces old. Print-masking (edge-profile-only rep) → ~2/6 TP, 0/6 FP. Route-by-wear → ~2/6 TP, 0/6 FP. All three converge on **"recover the high-wear fraction (~2/6), abstain on low-wear, FP 0."** Because copy identity lives in WEAR and low-wear books don't have it — no representation extracts a signal that isn't on the paper. The grade ceiling, confirmed from a third direction.
- **SINGLE-IMAGE: bounded, NOT zero.** Works on high-wear raw books, must ABSTAIN on low-wear. **Edge-profile-only representation** (reduce each edge to the bare SAM cut-line profile, discard interior print; cross-correlate REF↔TEST 1-D wear signals — could even be no-Opus) = the documented **safe-ification path**: it turns E3's dangerous low-wear FALSE-MATCHES into safe ABSTENTIONS. **NOT built; post-launch.** Upgrades **lane 3 from "provenance/monitoring only" → "provenance + high-wear recovery, abstains otherwise."**
- **ROADMAP (evidence-locked):**
  1. **Slabbed / high-grade → cert-number recovery** — the headline, works, wear-independent.
  2. **Raw high-wear → single-image recovery WITH abstention** (post-launch; edge-profile path).
  3. **Raw low-wear → MULTI-VIEW** — the ONLY path to manufacture copy-signal where one photo has none (more independent views beat the per-view print confound).
  4. **Raw single-image today → provenance / monitoring only, no recovery claim** until the edge-profile abstention ships.
- **PRODUCT-SCOPING NOTE (post-launch, zero build now):** when single-image recovery ships, scope it via **automatic per-book abstention on insufficient wear, NOT a user-facing grade-cutoff disclaimer.** A "only use below grade 9.0" disclaimer is **circular** (the user is using the app to LEARN the grade, so can't self-apply the cutoff) and doesn't engineer out the liability (E3's dangerous form false-matches low-wear books; a disclaimer doesn't stop that — abstention does). The edge-profile path already produces abstention; name the user-facing behavior: **high-wear → "fingerprinted this copy's wear pattern" (recovery works); low-wear → "too clean to fingerprint from photos" (honest abstention, framed as a compliment about condition) → route to the CERT path** (slab it, recover by cert number). The ceiling of single-image recovery becomes the **on-ramp to the cert lane** that actually works for high-value books.
- **TOOLS RETAINED:** SAM masking + the E3 boundary-following engine are **validated and kept** — they feed the multi-view lane later (and the edge-profile rep, if pursued). Nothing wasted.
- **DECISION: park single-image (do NOT pursue ensemble or build edge-profile now), pivot to VALUATION** — launch-critical (ASM #41 first-Rhino ~10× undervaluation; thin-comp key issues). Roughness-routing empirical check deliberately NOT run (wouldn't change the decision; valuation is the priority).

**Docs-only changes this session; Mike commits all (no deploy). State-Recording Protocol adopted into the operating model after last night's near-miss.**

### ⚰️ REVERSAL TOMBSTONE (Rule 2) — the dropped re-capture
- **DEAD:** controlled-background re-capture / re-shoot per `tests/SlabGuardTests/E3_CAPTURE_SPEC.md` (chroma-key matte background, front-only re-shoot to get clean classical-contour edges).
- **REPLACED BY:** **E3 runs on SAM masks of the EXISTING captures** (`TPTests/{Pixel,iPhone}` + `FalsePostiveTest/{PixelPhotos,iPhonePhotos}`) via `scripts/e3_edge_sequence_test.py`. No new photos.
- **REASON:** the SAM run (2026-06-26) produced **24/24 clean masks incl. the white-on-white Marvel cover**; classical contour reliably segmented only **~6/24**. SAM answers the SCIENCE question (does edge-sequence matching recover?) AND the PRODUCTION question (segment arbitrary backgrounds) at once → the clean-input re-shoot is no longer needed to isolate the variable.
- **SUPERSEDES:** `E3_CAPTURE_SPEC.md` is **SUPERSEDED — do NOT execute it.** Header tombstone added to that file 2026-06-27 so a future read can't resurrect the plan. (This is the exact resurrection that bit us the morning of 2026-06-27: an overview reconstructed from the stale spec re-recommended the dead re-capture.)
- **DECISION DATE:** 2026-06-26 (SAM run + "re-shoot dropped, SAM answers both questions"); logged here 2026-06-27 per Rule 4 (should have been logged at the moment of deciding, not at the next session).

### E3 BUILD — CONFIRMED PRESENT (built, not yet run)
- `scripts/e3_edge_sequence_test.py` (untracked, standalone, **zero production-code changes**). Pipeline per pair: SAM quad on REF → SIFT homography maps the quad into the *original un-warped* TEST (void-free correspondence) → perspective-rectify both to a canonical rect + background margin → straddling edge band per side → one Opus 4.8 call with continuous edge-strips + sequence-matching prompt (reject-default + FP strictness preserved).
- **Both of Mike's pre-build confirmations folded in:** (1) **band straddles the paper edge** (`--band-out-mm 2 --band-in-mm 4`, outboard background + inboard cover) with FP-risk reasoning in the docstring; (2) **resolution vs ~8000px API limit** handled as downsample-to-2400-long + thin band (every strip ≪8000px at uniform ~9.3 px/mm), with **`--seg-per-edge` as the tile/along-edge-resolution escape hatch**.
- **Run status: NOT yet run.** Gated only on `ANTHROPIC_API_KEY` (the keyed gate run Mike fires). SAM checkpoint present (375MB, gitignored); `segment_anything` imports OK; all 6 TP + 6 FP pairs verified to form. Yesterday's SAM prototype artifacts in `tests/SlabGuardTests/_e3_sam/` (incl. `sam_marvel_white.png`) prove the engine end-to-end.
- **Both-sets gate (one session):** TP must rise above the 1/6 ceiling **AND** cross-camera FP stay **exactly 0/6** at per-pair confidence. Validity guard: INVALID if any pair has `cost==0` / vision error. Est. cost ~$0.50 (12 Opus calls).
- **OFFLINE PRE-FLIGHT (no key) run 2026-06-27** — exercised the whole pipeline except the Opus call on all 12 real pairs. Engine sound (SAM cracked the white-on-white Marvel covers; homography 430–2674 on real pairs; all build segs=4). **DATA FIX:** the two iPhone FP Marvel files were SWAPPED at capture (`Marvel_Universe_1_Front_iPhone.jpeg` held #2, `_2` held #1) → both Marvel FP pairs were cross-ISSUE (one failed homography at 4 matches, the other slipped through at 68 on shared trade dress and would have falsely "passed" the FP gate). Corrected by swapping the two filenames; re-ran FP pre-flight → 6/6, MU_1 68→1706, MU_2 4→430. Cross-issue audit via match-count separation (mismatch=4/68 vs same-issue=hundreds-to-thousands) confirms NO other mislabel in the 12 front pairs. Backs not audited (deprecated S110, E3 is front-only).
- **FIX B — adaptive boundary-following extraction BUILT (2026-06-27, replaces the minAreaRect rectify-then-slice).** Wide-band eyeball (BO + Mike) found the short edges (TOP/BOTTOM) slant + void SYSTEMATICALLY across all 6 (not Iron-Man-specific) — minAreaRect forces a rectangle but raw comics are bowed/trapezoidal, so a straight band clips the short edges. Wide band "fixed" coverage only by being generous enough to pull in heavy printed trade dress = the FP vector. Fix B traces the TRUE SAM contour (drops minAreaRect), samples a band along the boundary NORMAL per-column (REF direct; TEST via the ref→test homography on the same world points → corresponding, void-free), biased TIGHT to the bare paper margin (≈2mm out / 3mm in → max copy-unique wear, min shared print), with mm-scale contour smoothing (1.6mm) to reject SAM px-jitter. Contained to `build_segments`/`_edge_strip` in `scripts/e3_edge_sequence_test.py` — ZERO production code. Offline-verified: all 6 TP rebuild segs=4, bottom voids gone, bands hug the edge. QA strips (before/after) in `tests/SlabGuardTests/_e3_qa/` (`*_wide` = stopgap, `*_fixb` = Fix B). **Awaiting Mike's eyeball verdict on the Fix B strips → then the paid both-sets gate.**

### ⚰️ VALUATION DIAGNOSIS TOMBSTONE — ASM #41 miss = leading-article title bug, NOT thin data (2026-06-27, read-only)
- **SYMPTOM:** ASM #41 (first Rhino), graded 6.0 → returned FMV ~$47, verdict "probably not worth grading." Real CGC 6.0 sells ~$400–600 (~10× undervaluation), driving a WRONG slab/no-slab verdict — the core product promise.
- **ROOT CAUSE (proven from `lookup_demand` + corpus):** the actual logged lookup used title **`"The Amazing Spider-Man"`** → **comp_count=0, fmv_method=`estimated`, no_data=True**. The corpus stores `canonical_title="Amazing Spider-Man"` (no article). `title_matching.qualifier_title_clause` does a NORMALIZED EXACT match on canonical_title; the leading **"The"** breaks it, and the substring-LIKE fallback also fails (column "amazing spider man" doesn't CONTAIN "the amazing spider man"). → 0 comps → generic `grade_baselines` estimate ($10@6.0 × pub × era ≈ $39–47, KEY-BLIND). Had it matched: **6.0 median ≈ $550 (7 comps/365d)**, raw ≈ $250, ROI ≈ +$255 → "Worth grading" (opposite verdict).
- **NOT a thin-comp problem:** ASM #41 has 49 graded comps/365d, full grade curve (4.0→$325 … 7.0→$750 … 8.5→$1,739). Data is rich; retrieval missed it.
- **WIDE BLAST RADIUS (flagship titles):** `lookup_demand` already shows **16 lookups / 11 distinct "The…" titles** hitting no-data/estimated; de-articling lands on huge pools — **Amazing Spider-Man 3,410 rows, Incredible Hulk 1,033, Uncanny X-Men 1,151, Avengers 254, New Mutants 648, Invincible Iron Man 137, Spectacular Spider-Man 150**. The bug silently zeroes valuation for the highest-traffic Marvel/DC books (the ones that conventionally carry "The").
- **STRUCTURAL GAP it exposed:** the system COMPUTES `confidence`/`estimated`/`no_data`/`exact_count` (and logs them) but the slab/no-slab VERDICT does NOT gate on them — it renders a confident "don't grade" off a no-comp estimate exactly as off 50 real comps. A $550 key and a $5 nobody book yield the same confident verdict when comps=0.
- **FIX PLAN — spec'd, built, verified (spec: `docs/technical/VALUATION_FMV_FIXES_SPEC.md`):**
  - **Fix A — leading-article title normalization (`title_matching.py`): COMMITTED `c688bce` + DEPLOYED.** Strip leading "the " symmetrically in `_norm`/`_norm_sql` (lockstep). Corpus-proven: **0 false merges across 14,033 titles** (every merge = {X,"the X"}); "a"/"an" excluded (no rescue value, nonzero risk). Verifications: flagships rescued (The Amazing Spider-Man→1,230 comps/365d, X-Men 436, Hulk 377…); **ASM #41 end-to-end → 6.0 median $550, ROI positive, "Worth the Slab", `verdict_reliable=True` — confirmed live in the result UI.** Mike commits + Render deploy.
  - **Fix B — data-sufficiency verdict gate: COMMITTED `cecbaa5` (backend+frontend) + DEPLOYED + SMOKE-TEST PASSED live (NFL SuperPro #1 → amber "ROUGH ESTIMATE" caution rendered).** Backend `routes/sales_valuation.py`: confidence computed before the verdict; `verdict_reliable = not (estimated or fmv_method in estimated/estimated_from_raw)` → **FABRICATION TIER ONLY** (zero-real-comp invented FMV); on `!verdict_reliable` the verdict becomes "Not enough recent sales to value this reliably — rough estimate only, treat with caution" (number kept), `verdict_reliable` added to response. Frontend `app.html`: on `verdict_reliable:false` → amber "ROUGH ESTIMATE" badge (not green/red), neutral ROI color, prominent caution tagline — **essential, B is invisible without it.** SCOPE RESOLVED: `exact_thin` (1-2 real comps) stays confident at launch (thin-but-real ≠ fabricated); `confidence=='very_low'` would wrongly sweep it in. **⏰ POST-LAUNCH:** extend gate to `very_low` once we have data on how often exact_thin misleads (in-code ⏰ comment).
  - **REMAINING TITLE-MATCHING TAIL (post-launch, small):** ~14 lookup titles across token-order + colon/subtitle/accent classes; ~25 "absent" are junk (auction noise/foreign, not fixable). Spacing/hyphen + possessive classes have ZERO traffic yet (untriggered, not absent) — **monitor `lookup_demand` post-launch** to catch the tail as traffic surfaces it. Not a pre-launch gap.
  - **SEQUENCE:** ship A now (commit+deploy) → review B diff (backend+frontend together) → commit+deploy B.

### ⚰️ LIVE SLAB GUARD SCOPING TOMBSTONE — copy rescoped to match what's supported (2026-06-27)
- **OVERCLAIM (DEAD):** the live user-facing copy claimed cross-camera photo-**recovery** — "tied to the physical **copy**, not just the title" (index.html), "monitors eBay… alert you if a **match** appears" / "**Match Alerts**" (pricing.html + extension), "advanced fingerprinting technology to **track and recover** stolen comics" (verify.html). These ride the QUANT path (`compare_covers` = composite hash + edge-strip + SIFT edge-IoU) the code's own `monitor.py` docstring calls **"UNRELIABLE for cross-camera."**
- **PRODUCT TRUTH (read-only confirmed):** the live extension photo-matches **quant-only** — `background.js` calls `/api/monitor/check-image` with NO `marketplace_mode`/`use_vision`, so `compare_covers_with_vision` (the whole E1/E2/E3 vision-arbiter surface) **never fires in production**. Reliable layers = **serial-number lookup + reported-stolen DB flags** (exact). Only prod CV changes this whole arc: `647bca2` Opus-arbiter swap + `27946ff`/`99337f4` two safety fixes — **all in the vision path the live extension doesn't invoke**; E1/E2 reverted; E3/SAM grep in product file = NONE (harness-only). **No edge-sequence upgrade is shippable** (E3 FP 4/6 < live).
- **REPLACED BY:** copy rescoped to **provenance + monitoring** across 4 surfaces (index.html, pricing.html, verify.html, extension `popup.html`): fingerprint = "a record of your copy"; auto-scan = "**candidate sightings to review (beta — may be inaccurate; verify by serial)**"; recovery routed to the serial lookup that actually works. **Match-alert rework is a SAFETY fix in copy form** — the bar is "can never send a user to confront the wrong person over a legitimately-owned book," so results read as reviewable candidate leads, never a confident ID. **Beta label kept.**
- **KEPT (honest, supported):** serial verification, reported-stolen lookup, register/fingerprint-as-record.
- **STATUS:** copy diff DRAFTED (4 files), awaiting Mike's commit — NO deploy. Loud surfaces also softened (don't let hero/subtitle/share-preview overclaim what the body walks back): extension tagline "Catch thieves" → "Monitor the market"; homepage subtitle "authentication powered by AI" → "fingerprinting & monitoring powered by AI"; pricing `<meta>` "theft protection" → "theft monitoring." Complete copy rescope = ONE reviewable/committable unit; cert-wiring scoped SEPARATELY after this lands (don't entangle the launch-safety copy commit with a build).
- **DEFERRED — the real recovery upgrade:** wire **cert-number recovery** (slabbed books: cert already OCR'd/stored/indexed → exact, wear-independent lookup) = lane 1, the honest capability gain, next build (scoped AFTER this copy diff lands). Nothing from edge-matching.

### State-Recording Protocol — ENSHRINED
- Full text committed to **`docs/STATE_RECORDING_PROTOCOL.md`** (in-repo, not a loose Downloads file).
- **Surfaced from `CLAUDE.md`:** SESSION OPENING PROTOCOL now has a **step 4** (re-read THIS file + scan for newer decisions before acting — Rule 3), plus a callout block summarizing Rules 2/4/5 with the source incident. So "re-read before acting" has something to re-read, and a future open hits the rules on the way in.

### NEXT
1. **VALUATION (launch-critical, the new active thread)** — ASM #41 first-Rhino ~10× undervaluation; thin-comp key issues. (Mike/BO bringing the framing.)
2. **Mike commits the E3 arc + docs** when ready: `docs/STATE_RECORDING_PROTOCOL.md`, `CLAUDE.md`, `E3_CAPTURE_SPEC.md` tombstone, this `WHERE_WE_LEFT_OFF.md` entry, the harness `scripts/e3_edge_sequence_test.py`, and the `tests/SlabGuardTests/` E3 data/CSVs/QA strips as desired. No deploy (docs/test only; zero production code touched this arc).
3. **Single-image: PARKED** (see E3 RESULT + DECISION TOMBSTONE above). Do NOT pursue ensemble (proven dead) or build edge-profile now (post-launch). SAM + E3 engine retained for the multi-view lane.
4. Unchanged launch track behind valuation: cert-number recovery lookup (lane 1 headline), billing stacking steps 2 & 3, Section F mobile+load, ⏰ 90-day purge ~2026-09-17.

---

## Session 110 (Jun 24-26, 2026) — Cross-camera recovery FULLY CHARACTERIZED: FP=0/12 (liability gate PASSED, 3 runs) but TP=1/6 (recovery sensitivity FAILS); E1 (prompt) + E2 (pixel normalization/glare-mask) BOTH REJECTED → single-image looked CEILINGED **— BUT see E3 section: that conclusion is now SUSPENDED** (the TP was measured on warp-void-crippled input — the arbiter only saw half the perimeter, fragmented); learned-feature swap closed (registration is NOT the bottleneck); two arbiter safety fixes committed; backs deprecated; roadmap = three lanes (slab→cert / raw-multiview→post-launch / raw-single→provenance-only)

**Built draft-for-review; Mike runs all git/deploy. Verification ran before every diff reached Mike (offline parsing/pairing asserts + in-process arbiter-logic asserts + module-import checks). Standing protocol: file-specific staging, commit message matches diff.**

### E3 (Jun 26) — continuous edge-SEQUENCE representation: the "single-image ceilinged" conclusion is SUSPENDED, under test
- **Why suspended — the ceiling was measured on CRIPPLED input.** A read-only crop-coverage dump of the Iron Man TP pair showed the arbiter received **only the top + right edges** — the **bottom + left edges and both bottom corners were dropped as warp voids** (the iPhone shot was rotated ~90°, so the homography warp leaves black non-overlap regions, and `_region_is_black` skips them). The arbiter adjudicated **half the perimeter, fragmented into isolated patches**, never tracing the continuous sequence. Mike's decisive ticks (top-center, top-right, right-edge) WERE in the crops it received and it rejected anyway → confirmed it does **isolated-patch adjudication, not sequence-tracing**. We proved "corner-crop region-comparison fails," NOT "single images lack the signal."
- **⚠️ WARP-VOID DROPPING = LATENT PRODUCT BUG (flag independently).** On differently-framed pairs — i.e. MOST real recovery scenarios, where the recovery photo won't match enrollment framing — the crop builder silently discards edge/corner regions as warp voids, so the arbiter loses evidence. It has been degrading every cross-framing comparison. E3's contour-follow fixes it as a side effect, but it is its own bug.
- **E3 hypothesis (modeled on Mike's demonstrated method):** Mike matched Iron Man by eye **forensically** — continuous full-perimeter edge tracing, matching a SEQUENCE of bends/ticks at positions, no prior. E3 reframes the arbiter's INPUT: one **continuous physical-edge strip** (perimeter "unrolled") + instruction to match the sequence. Keeps reject-default + FP strictness — changes WHAT it sees + the operation, NOT the bar. FP bonus: tracing the bare PAPER edge minimizes shared printed trade dress = starves the false-sequence-match vector (first fix that helps TP and FP TOGETHER).
- **E3 ENGINE VALIDATED (read-only prototype):** contour-follow unroll + **homography correspondence** — detect the book quad in REF, map it via the homography into the ORIGINAL (un-warped) TEST → **void-free, physically-corresponding** traces. On the hard rotated Iron Man pair it produced two directly-comparable, void-free perimeter traces. The representation Mike's method needs is producible, and it fixes the warp-void bug.
- **BLOCKER → SCIENCE/PRODUCT SPLIT (Mike's reframe):** the engine hinges on book-edge detection; classical contour detection (Otsu, border-flood-fill) reliably finds only dark high-contrast covers (~6/24), fails on white/light covers (white cover ≈ white table). Two separate questions:
  - **Q1 — science, answerable NOW:** does edge-sequence matching actually recover? Test on a CONTROLLED-background re-capture (clean edge extraction isolates the variable). Spec: `tests/SlabGuardTests/E3_CAPTURE_SPEC.md` (saturated matte chroma bg, front-only, TP + FP, both phones).
  - **Q2 — product, POST-LAUNCH:** extract the comic edge from ARBITRARY real-world backgrounds (carpet/wood/bedspread/white-on-white) = **learned segmentation (SAM2 / custom comic-seg model), NOT classical contour** (brittle to clutter). Queued, **gated on E3 validating**, same CPU/Render infra reality as the LightGlue call; also lifts grading/valuation image quality (not single-purpose).
  - **Controlled background is deliberate TEST ISOLATION, NOT the production assumption.** Production edge extraction = learned segmentation, queued pending E3.
- **NEXT for E3:** Mike re-captures per `E3_CAPTURE_SPEC.md` → I draft E3 (unroll + sequence-matching prompt) → both-sets gate (TP↑ AND cross-camera FP=0/6 at per-pair confidence). Validates → single-image back on the table for soft launch + learned-seg roadmap item justified; fails → single-image genuinely ceilinged (now tested with the demonstrated-working method on clean input) → multi-view primary. Read-only-later: assess SAM2 vs a custom seg model as the CPU production fit (gated on E3 — do NOT scope yet).

### Headline: the decisive number landed clean. Front-cover cross-camera false-positive rate = **0** — held across **three** runs — and two real arbiter safety bugs (both in the dangerous "different copy surfaces as a match" direction) were caught by the test and fixed in the live product path.

### THE RESULT — cross-camera false positives = 0
- **Front covers: FP = 0/12**, three consecutive runs, confidences **0.6–0.97**. This is the metric that gates the recovery claim (different copy of the same issue, two cameras, must NOT match). It passed.
- Test set: `tests/SlabGuardTests/FalsePostiveTest/{PixelPhotos,iPhonePhotos}` — same 6 issues, **different physical copies** across the two phone folders (visually confirmed same-issue, e.g. Iron Man #200 both sides). 6 same-issue cross-camera pairs per side.

### BACKS DEPRECATED AS A MATCHING SURFACE
- Backs produced **3/6 non-clean** results (1 false positive — since corrected by the fix below — + 2 `uncertain`) vs fronts 6/6 clean across every run.
- **Structural reason (not tunable):** same-issue back covers are frequently the **identical mass-printed full-page ad** (shared trade dress / barcode block), so the SIFT/border matcher agrees on shared **print**, not shared **wear**, and cannot discriminate copies. Evidence: the Wolverine back pair shows `border=39` geometric inliers vs 0–10 on every other pair — a spurious spike from shared printed content. **Recommendation: drop back covers from the recovery matching path.**

### TWO PRODUCT-PATH ARBITER FIXES (`routes/slab_guard_cv.py` — COMMITTED in HEAD; deploy to Render per protocol)
Both surfaced by the back-cover run; both are general live-path hardening (not test-only), both in the "different copy must never read as same_copy" safety direction:
1. **Vision JSON parse hardening.** The arbiter assumed a pure-JSON response; when the model appended trailing prose (more common on dense back covers) `json.loads()` raised "Extra data", the greedy-regex fallback also threw, the exception escaped to the outer handler → `vision=None` → quant fallback defaulted to `same_copy` (a real false positive on Heros_For_Hope back). Fix: new `_extract_first_json_object()` (balanced-brace, string/escape aware) parses only the first `{...}` object and ignores leading/trailing content + code fences; a genuine parse failure now defaults to **`uncertain`, never throws**; safety net so a parse failure can never surface as `same_copy`.
2. **Uncertain vision can no longer be promoted to a match.** In marketplace mode, a successfully-parsed `vision=uncertain` could still be overridden to `same_copy` by the LPQ/quant tiebreaker (Wolverine back: `vision=uncertain` → `final=same_copy/0.6`). Fix: the marketplace vision-uncertain branch may only downgrade toward `different_copy`; floor outcome is `uncertain`, never a match. Generalized the safety net to enforce this invariant (no real vision match ⇒ never `same_copy`). Standard mode unchanged (quant is the trusted primary there by design). Re-run confirmed: Wolverine back flipped to `different_copy` (same `border=39` spike, verdict held correct).

### HARNESS ADAPTED TO THE REAL SHOOT (`scripts/slabguard_crosscamera_test.py`, drafted + verified)
- Rewrote ingestion for the actual shoot: **phone = folder** (`--phone1`/`--phone2`), parses `<Issue_Name>_<Front|Back>_<copyNumber>` (`copynum`, default), dynamic copy enumeration (handles the 2- and 3-copy issues), `--side front|back|both`, FP split into **cross_camera vs same_phone**, `invalid_no_arbiter` CSV column (a keyless quant-only run can't be mistaken for valid), one localhost file server per phone folder.
- Added **`--layout crosscam-fp`** for the FalsePostiveTest set (`<Issue>_<Front|Back>_<Pixel|iPhone>`): copy identity comes from the folder so same-issue Pixel↔iPhone pairs score as different copies (cross-camera FP), `expect=different_copy`.
- Default-model label corrected to Opus 4.8; docstring updated to 6 issues / variable copies / dual FP modes.

### ARCHITECTURE FINDING (read-only) — copy discrimination is WEAR-carried → route recovery by book type
- Traced what each layer keys on in marketplace mode. **Print/image signal (SIFT alignment + dIoU edge-IoU) establishes same-ISSUE only — copy-blind by design** (`_compute_edge_iou` docstring: aligned edges "match across ALL copies of the same issue"). **Copy-level identity is carried by WEAR/DEFECT signal:** the Vision arbiter (primary in marketplace; prompt is explicitly anti-print — "matching ink patterns... are NOT evidence", requires a SPECIFIC uniquely-identifiable defect, defaults DIFFERENT_COPY) and **LPQ-border** (the residual-texture quant signal — Session 55: "the discriminative signal lives in border wear patterns, not interior printed content"). `border_inliers` is wear-keyed in theory but **unreliable cross-camera** (false matches from background/shared-ad print) → demoted to confidence/different-only support, never drives same_copy (the Wolverine back `border=39` is exactly this documented false-inlier mode).
- **Failure direction on low-wear books = FALSE NEGATIVE (missed match), not false positive.** So the **FP=0 liability result holds across ALL grades**; but **recovery SENSITIVITY has a grade ceiling — high-grade/slabbed/mint is exactly where wear-matching is weakest** (little wear = little copy-unique signal; every layer defaults toward different_copy/uncertain).
- **ROUTING IMPLICATION — this finding is the technical evidence for the primer's existing routing call, and the architecture + market align by book type:**
  - **Slabbed / high-grade → cert-number recovery** (wear-independent; cert already OCR'd/stored/indexed, just needs the lookup wired) — the path for the high-value books photo-matching is weakest on.
  - **Raw / mid-grade with genuine wear → wear-based photo matching** (this harness's path), where the wear signal is strong.
  - **Recovery photo-matching claims must be SCOPED to raw books with real wear; slabbed recovery rides the CERT path, not photo-matching.**
- **Consequence for the TP run (interpretation HELD until grades are noted):** a clean TP on worn books does NOT generalize to high-grade. Provisional visual read of the 6 already-shot TP books: none slabbed/mint, spanning Heavy (The_Invaders_41 — strongest wear, easiest case) to Low (Wolverine — weakest wear, hardest case); **no decisive high-grade copy in the set.** Protocol (`TP_RESHOOT_PROTOCOL.md` §7–§9) now REQUIRES grade-stratified reporting + at least one deliberately high-grade/low-wear **raw** copy as the decisive sensitivity test, and captures the per-book grade table (Mike to fill actual grades).

### TP RUN — cross-camera raw-book TP = 1/6 (FAILS); two fixes tried, BOTH REJECTED; single-image CEILINGED
- **Result: 1/6** same-book cross-camera pairs matched (`TPTests/{Pixel,iPhone}`, 6 issues, 1 raw copy each, front-only). A prior 4/6 was an **INVALID run** (all vision calls 401/502'd → quant-only; the harness now logs `align`/`low_evidence` and the operator checks cost>0 / no `vision=None` to catch this).
- **Diagnosis (Mike eyeballed Iron Man 200 — a human matches by defects):** (1) cross-sensor color/tone (iPhone richer, Pixel flatter) + (2) specular GLARE on the Pixel shot manufacturing a phantom corner defect → drives the arbiter's default-to-`different_copy` to a confident WRONG verdict.
- **Experiment 1 — glare/color PROMPT nudge: BUILT, RAN, REJECTED.** Added `marketplace_note` bullets (glare = no-data; cross-sensor color expected) + WHAT-TO-IGNORE lines, marketplace-scoped. Result: TP **unmoved at 1/6**; only turned one confident-wrong into uncertain-wrong (Heros) and pushed FP-side uncertainty 2→5 pairs (more mush, no accuracy). FP held 0. **Words don't fix it — reverted.**
- **Experiment 2 — PIXEL normalization + glare-mask + evidence floor: BUILT, VERIFIED, RAN, REJECTED.** Photometric LAB normalization (color) + specular-glare detection → skip glared crops (no-data, not de-weighted) + `exclude_mask` in dIoU/LPQ + `low_evidence` guardrail (a glare-starved pair is an un-judgeable capture, set aside — NOT a TP miss). Result: TP **1/6 unchanged, every miss `low_evidence=False` (clean evidence)** — these are clean-crop pairs the arbiter rejected. Iron Man **did not flip** (still `different_copy` 0.92) **despite E2 cleaning its pixels** (dIoU dropped 0.61→0.31, confirming normalization worked). FP held **0/6, crisp** (all different_copy 0.6–0.98, no mush) — E2 was SAFE but didn't help recognition. **Reverted to HEAD;** the normalization/glare helpers are filed in `EXPERIMENT2_DESIGN.md` for the multi-view lane.
- **REGISTRATION QUESTION CLOSED (learned-feature swap DEAD).** The `align`-column instrumentation showed every TP pair `align=True` with **1500–2200 SIFT inliers** — alignment is clean across the board. A SuperPoint+LightGlue / LoFTR swap would fix a stage that isn't broken; on CPU-only Render LoFTR is impractical (~5–15s/pair) and LightGlue adds ~200MB torch for no gain here. **Filed closed, not deferred — do not revisit absent new evidence.**
- **CONCLUSION (pre-committed, now triggered): single-image cross-camera raw-book recovery has hit its CEILING.** Two principled interventions (prompt, pixels) both null on clean-evidence pairs. The reject-bias that holds FP=0 and the failure to recognize true matches are the **same mechanism** — the arbiter genuinely cannot match wear across these cameras from single images. Stop single-image tweaking.

### ROADMAP REFRAME — three lanes by book type (this is the decision)
1. **Slabbed / high-grade → cert-number recovery (the marketable HEADLINE).** Wear-independent; the CGC/CBCS cert is already OCR'd/stored/indexed at grading — just needs the lookup endpoint wired (small build, no CV research). This is the recovery path for the high-value books.
2. **Raw + MULTI-VIEW capture → post-launch recovery build (PRIMARY raw-recovery path).** Single image is ceilinged; multiple controlled views (and the E2 normalization/glare helpers) are the path to raw-book recovery. Post-launch.
3. **Raw, single-image → provenance + monitoring framing only. NO recovery claim.** FP=0 makes it safe for "we recorded your copy" / monitoring, but TP=1/6 means it cannot promise "we'll match it back."

### NEXT
1. **Mike: commit the harness** (`git add scripts/slabguard_crosscamera_test.py`) — `align` + `low_evidence` instrumentation, both keepers. `routes/slab_guard_cv.py` is back at HEAD (E1/E2 reverted; the two safety fixes are already committed there — deploy to Render if not yet done).
2. Commit the docs (this log, `TP_RESHOOT_PROTOCOL.md`, `EXPERIMENT2_DESIGN.md`).
3. **Cert-number recovery lookup** = the next build (lane 1, the honest marketable headline).
4. Multi-view capture = the post-launch raw-recovery arc (lane 2).
5. Backs already deprecated (fronts-only); raw single-image stays provenance/monitoring (lane 3, no recovery claim).

---

## Session 109 (cont., Jun 22-23, 2026) — Opus 4.8 Slab Guard arbiter SHIPPED & DEPLOYED (commit 647bca2); cross-camera RECOVERY test fully set up (harness + capture protocol, pending Mike's photo shoot); recovery positioning decided

**Built draft-for-review; Mike ran all git/deploy + the Render-Events verify. Read LESSONS + cross-project at open. (Same session as the stacking step-1 work below — this is the Slab Guard / Opus half.)**

### Headline: the Slab Guard Vision arbiter is now Opus 4.8 (with real fallback), and the decisive cross-camera recovery test is built and waiting on Mike's photos.
A 4-brief read-only thread assessed what Slab Guard recovery can actually PROVE, reconciled the validation history, then shipped the Opus switch + the resilience fix. The recovery CLAIM is now gated on one number: the **cross-camera false-positive rate**, which Mike's photo shoot will produce.

### OPUS 4.8 ARBITER SWITCH — SHIPPED & DEPLOYED (commit `647bca2`, Render Events green)
- **What changed** (`routes/slab_guard_cv.py` + `models.py`, additive/surgical): the Vision arbiter `compare_covers_with_vision` now defaults to **Opus 4.8 via `call_with_fallback('opus')`** instead of a frozen direct `client.messages.create(model=SONNET)`. Two wins in one — **(a)** Opus is the default (forensic visual copy-discrimination is exactly its strength), and **(b)** the resilience fix: the whole cross-camera copy verdict rides on this ONE call, which previously had **NO fallback** (would 404 with no recovery if its head model retired, and the model string was frozen at import).
- `models.py` opus chain head bumped **4-6 → 4-8** (4-7/4-6 as fallbacks). Cost formula made **model-aware** ($5/$25 Opus default, $3/$15 if a Sonnet A/B override served it) so `cost_usd` is correct for BOTH harness arms. New **`arbiter_model`** field on the response for verification.
- An explicit `model=` override (the harness `--model`) still pins that exact model and bypasses the chain → the Sonnet-vs-Opus A/B works unchanged.
- **Cost reality (corrected from the brief's ~5×):** Opus 4.8 is **$5/$25** vs Sonnet **$3/$15** = ~**1.67×**, on a call that **barely fires today** — the shipped extension runs **quant-only** (`background.js` never sets `marketplace_mode`/`use_vision`), so the arbiter only fires on the manual `/api/monitor/compare-copies` path + the harness. Negligible cost. (If `marketplace_mode` is ever wired into the extension auto-scan, the arbiter fans out **once per hash-gate candidate per listing** — bound that fan-out then; flagged, not built.)
- Functional `arbiter_model=claude-opus-4-8` live check **deferred to the harness run** (didn't chase cover URLs for a curl today).

### SLAB GUARD RECOVERY ASSESSMENT (read-only — the thread that led to the switch)
- **Load-bearing answer — copy vs issue:** the hash gate (pHash+dHash+aHash+wHash) is **issue-level only**. Copy-level identity is attempted by SIFT edge-IoU + border inliers + LPQ + the Vision arbiter. Per the code's own docstrings these work **same-camera** but are **UNRELIABLE cross-camera** (the ACTUAL recovery scenario) — quant "CANNOT discriminate copy identity" cross-camera; Vision is primary there but validated on essentially **n≈1 same-copy cross-camera pair**.
- **Validation-history reconciliation (Mike's "lots of testing" vs my "n=1"):** BOTH true. Substantial testing happened but lives only as **prose** (CV docstring, ROADMAP, `SLAB_GUARD_CV_OVERVIEW.md`) — **zero committed structured result files**. It was mostly **cross-IMAGE / same-camera** (Mike re-shooting his own copies on one device — 6/6 there); the recovery-relevant **cross-CAMERA / different-device axis was never run as a controlled matrix** (its one data point was a single eBay photo that produced a false positive). Cross-image vs cross-camera is exactly what reconciles the two views.
- **Cert-number = the buried lede (strongest recovery vector, UNWIRED):** the CGC/CBCS cert is **already OCR'd** at grading (`comic_extraction.py`), **stored + indexed** (`comic_registry`/`collections`, dedicated index) and **displayed** in verify lookup — but it is **never matched on**. `find_matches()` keys only on hashes; no endpoint accepts a cert and returns a registered copy. Wiring it is the **lowest-effort, highest-reliability** slabbed-recovery feature — needs no CV research.

### CROSS-CAMERA HARNESS + CAPTURE PROTOCOL — READY (read-only, not wired to prod)
- `scripts/slabguard_crosscamera_test.py` — imports the live `compare_covers_with_vision` with `marketplace_mode=True`, serves Mike's local photos over a **localhost file server** (no R2 upload, no prod change), **bypasses the issue gate** (it passes for both TP and FP by design, so it isn't the discriminator), and prints a per-pair metric table + **true-positive and false-positive RATES** + total cost. Takes `--model` (the A/B) and `--csv`.
- **Capture protocol:** front cover of each (copy, phone). 5 issues × 2 copies × 2 phones = ~20 photos, named `issue<N>_copy<A|B>_phone<1|2>.jpg`. **Matte, untextured, contrasting background** (texture = the #1 false-positive cause — the one historical cross-camera FP came from background texture). Even light, no glare, square-on, full cover, ≥500px short side, two **genuinely different** phones. Shooting all 4 per issue yields ~10 TP + ~10 FP cross-camera pairs (real rates, not an anecdote).

### POSITIONING DECIDED (recovery-claim honesty)
- **Slabbed → cert-number = the honest, marketable recovery HEADLINE** (cert already captured/stored/indexed; small build to wire the lookup).
- **Raw / photo-matching stays provenance + monitoring framing** until the harness FP-rate proves cross-camera recovery. **Decisive metric = the cross-camera false-positive rate (different copy, same issue, must NOT match); want 0** — this number gates whether "recovery" can go on any GalaxyCon booth copy / pricing tier.

### NEXT — Mike's physical work (unhurried, its own block)
1. Source a clean **matte, untextured, contrasting** background (poster board / plain matte surface).
2. Confirm **ANTHROPIC_API_KEY + opencv** in the venv BEFORE shooting.
3. Shoot ~20 photos (5 issues × 2 copies × 2 phones, naming above).
4. Run the harness **twice** for the A/B: no `--model` (defaults to Opus 4.8 now) and `--model claude-sonnet-4-6`.
5. Read the **false-positive rate** (want 0); confirm `arbiter_model=claude-opus-4-8` in the default run.

## 2026-08-16 (evening) — VALUATION OUTAGE, cause found, three conventions changed

**MOST RECENT CHANGE: `/api/sales/valuation` went down and was rolled back. Cause was three bare
`%` characters in SQL COMMENTS, not the regex.** Supersedes the first two diagnoses recorded in
the working transcript, both of which were wrong and stated confidently.

### Live state at end of day — verified by real call, not inferred

| | state |
|---|---|
| valuation | **healthy** — Absolute Batman #1 @9.8 → `graded_fmv` 422.68, 445 comps |
| traceback logging | **live**, instrumentation only, verified |
| badge (MARGINAL state) | ⚰️ **REVERTED by `3f6148e` and NEEDS RE-APPLYING** — it was working and verified live; it came out while chasing the wrong cause |
| signatures | **held. Fix applied but UNCOMMITTED in `routes/sales_valuation.py`** — comments de-percented, pattern parameterised, verified through a live execute. ⚠️ Lost if the working tree is cleaned. |

### The outage

`/api/sales/valuation` returned `{"error":"list index out of range","success":false}` on every
book. Two log lines, 07:59:22 and 08:00:18 PM.

**Cause:** three bare `%` in SQL comments added by the signature unit — *"catches ~90% of the
shapes"*, *"(3.31%) at a $85.00"*, *"(82%) are a"*. psycopg2 percent-formats the **entire query
text, comments included**, so `% ` is a malformed format directive. Reproduced exactly: one
parameter → `IndexError`, two → `ValueError: unsupported format character ' ' at index 976`.

⚰️ **TWO DEAD DIAGNOSES — do not resurrect:**
- **DEAD:** *"the regex is correct SQL and fatal as a Python format string."* The pattern
  contains **no `%` at all**. **REASON:** a plausible mechanism was reported instead of the
  character being located.
- **DEAD:** *"parameterising the pattern is the fix."* **REPLACED BY:** cutting the `%` from the
  comments. Parameterising is in the new version as hygiene only. **REASON:** the pattern was
  never the fault.

**Why every check passed:** `py_compile` proved syntax, SQL spot-checks proved the predicate, and
neither executed the Python transport. The comments are valid SQL and fatal only at
`cursor.execute()`.

**Compounding error:** `3f6148e` reverted `app.html` (the badge), which cannot produce a
server-side JSON error. The signature change had shipped inside `95228f7` — a commit whose
message describes only documentation — because the ship block staged code and docs across a
numbered list with no per-commit boundary.

### ⚠️ THREE CONVENTION CHANGES — standing, apply to every ship block

1. **Self-contained commits with a stated expected file list.** Stage → `git diff --cached --stat`
   → verify against the list the block names → commit. Never a numbered list with implied
   boundaries: staging is cumulative, numbered steps read as sequential, and that gap put a code
   file inside a docs commit.
2. **Verify with an endpoint that exercises the change.** `/health` returned 5.6.0 throughout the
   outage — it is structurally incapable of detecting a valuation fault, not merely a weak check.
3. **One live call through the real path before a block is written.** Not `py_compile`, not a SQL
   spot-check, not a `cur.execute` — those proved things that were true and irrelevant. Mike makes
   the call.

Also now standing: `git log origin/main..HEAD` before assembling any block (a committed-but-unpushed
change is still unshipped and still needs deploy/purge), and **every block names a verification
cell with a before and after figure**.

### Already answered — item 3 needs a re-read, not a re-run

**Two defects, not one, plus a third:**

| # | defect | rows | family |
|---|---|---|---|
| 1 | `CGC 98` parsed as grade **98.0** — 29 rows, all `graded=true`, all reach the ladder | 29 | grade parsing |
| 2 | **later printings** (`9th Print`, `11th Print` at $15–28) pooled with first prints | unmeasured | printing identity — **new gap**, `is_reprint` does not cover it |
| 3 | `Absolute Batman Annual #1` / `Ark-M #1` collapsing into the base title | unmeasured | `canonical_title` — same family as Wolverine |

The $9.00 sales are **not lots and not misparsed grades** — they are real graded sales of later
printings and adjacent titles. Absolute Batman #1's 9.8 bucket spans **$15.50 to $4,799**.

### Next session, in order — nothing starts until Mike says
1. **Re-apply the badge.** Good change removed for nothing. Needs **`purge`, not `deploy`.**
2. **Signatures** — fix already applied and uncommitted; block written only after Mike's live call.
3. **Price-curve findings** — answered above; confirm rather than re-measure.
4. **Capture-schedule measurement** — daily row counts, per-key depth against §1's stopping rule,
   grade-bucket depth on cleared keys, and what the marginal row buys. ⚠️ The fourth item arrived
   truncated mid-sentence and needs restating.

---

## 2026-08-17 — ✅ BADGE AND SIGNATURE FILTER BOTH LIVE AND VERIFIED

**MOST RECENT CHANGE: the badge is re-applied and the signature filter is deployed. Both
verified in production, 2026-08-17.** Supersedes the 2026-08-16 queue items 1 and 2 below.

⚰️ **DEAD: "1. Re-apply the badge. 2. Signatures — fix already applied and uncommitted."**
**REPLACED BY:** badge live at `9a1d2d3` (purged and asserted); signature filter live via
`8200374` + `8ae4187` (deployed, cell verified).
**REASON:** both executed today. **SUPERSEDES** any instruction to re-apply or re-commit either.

### What shipped, in three un-bundled blocks

| commit | what | ship path |
|---|---|---|
| `8ae4187` | raw-side signature comment corrected | rode along, no separate deploy |
| `c2877cb` | the 2026-08-16 outage record | docs only |
| `9a1d2d3` | badge re-applied (revert of `3f6148e`) | `purge`, not `deploy` |

`8200374` (the filter itself) and `6d7b0d9` (the anthropic pin) had been sitting **local and
unpushed** and went out with the first push. ⚠️ The tree was described at session open as one
local commit ahead of origin; `git log origin/main..HEAD` showed **four**. Check the range, do
not trust the recollection — L-SW-2026-008.

### Verified

- **Badge:** post-`purge` assert on `slabworthy.com/app.html` — `MARGINAL_ROI_CEILING` ×3
  present, `roi > 0 ? 'WORTH THE SLAB'` absent. Both directions, per L-SW-2026-022. The
  precondition was gated on an origin read with a cache-buster (`cf-cache-status: DYNAMIC`)
  rather than on the dashboard, which confirms a build finished but not what the origin serves.
- **Signature filter:** Absolute Batman #1 @ 9.8 → **`graded_fmv` $345.00 exactly as predicted**,
  `fmv_method: exact`, `confidence: high`, `verdict_basis: supported`, 321 comps.

### ✅ SETTLED — the 321-vs-323 gap. It was the pool moving, and the direction is right.

Measured read-only as `do_readonly`, both queries extracted from the live module source at
runtime and differing **only** by the two signature lines, with the variant exclusion added to
both to mimic the Python partition (L-SW-2026-024 rules 3a and 3d):

| | recorded 2026-08-16 | measured 2026-08-17 |
|---|---|---|
| pre-filter (signature clauses removed) | 445 | **446** |
| post-filter (production predicate) | 323 predicted | **322** |
| removed by the filter | 122 predicted | **124** |

**The pre-filter count is NOT still 445.** The pool gained a row and the filter removed two more
than predicted, which is what a live rolling 365-day window over an actively-captured corpus
does. Nothing else took two comps. **Do not re-derive this.**

⚠️ **A SMALLER, DIFFERENT GAP IS OPEN AND IS NOT THE ONE ABOVE.** The SQL reconstruction returns
**322** where the live endpoint returns **321**, and the two were read **near-simultaneously in
the same script**, so drift is excluded as the explanation. The direction is the interesting
part: `graded_sample_size` is `exact_count = len(exact_match)` over grade buckets built from the
**union** of eBay and market rows, so production should be **≥** an eBay-only count, not one
below it. Unexplained. One row against an exact median — recorded, not chased.

### 🆕 NEW — the signature filter does not cover `market_sales`, and that is not a schema limit

| query literal | `is_signed` | pattern param |
|---|---|---|
| `ebay_graded_query` | ✅ | ✅ |
| `ebay_raw_query` | ✅ | ✅ |
| **`market_graded_query`** | ❌ | ❌ |
| **`market_raw_query`** | ❌ | ❌ |

`market_sales` **has both `is_signed` and `raw_title`** (confirmed against
`information_schema.columns`), so this is uncovered scope, not an impossibility.

⚠️ **The shipped comment is a trap for the next reader.** It says *"Applied to BOTH pools
deliberately. Filtering one side would subtract a signature-excluded median from a
signature-included one."* The "both pools" it means is **graded and raw within eBay**. There are
four pools and two are unfiltered — which is the very asymmetry the sentence argues against.
Blast radius is small today (Whatnot contributed 4 rows to the verification cell against 1,695
from eBay) but the sentence will read as full coverage. **[[L-SW-2026-020]]: the label is the
defect.**

### 🆕 NEW — the grade 1.0 at $529.99 is a grade misparse, NOT a signature residual

Pulled under the production predicate, as asked:

```
grade 1.0   $529.99   is_signed=False   sold 2026-07-30
   "Absolute Batman #1 CBCS 1st Print Not CGC"
```

The title carries **no grade at all**. `CBCS 1st Print` was read as **CBCS 1**, so a book that
sold for a high-grade price landed in the 1.0 bucket and sat above the 9.8 median. It is
**not** the seventh vocabulary shape — `SIGNED_TITLE_PATTERN` did not miss it, because there is
nothing to miss. Same family as the already-recorded `CGC 98` defect (29 rows, line ~2668):
**the grade parser reading a token that is not a grade.** Two distinct sub-shapes now:
notation shorthand (`CGC 98`) and ordinal collision (`CBCS 1st`).

### Confirmed, already recorded — not new findings

- **`CGC 98` → grade 98.0.** Live in the price curve on this cell. Already at line ~2668, 29 rows.
  Verified still present, not re-diagnosed.
- **The $9.00 sales at 9.4/9.6.** Already recorded as later printings and adjacent titles. One
  detail to add: they returned **zero rows from `ebay_sales`** — they are in **`market_sales`**,
  and two of them carry `title='Absolute Batman'` against `series='New Mutants'`. The first
  query looked in one table and found nothing, which is [[L-SW-2026-014]] in textbook form.
- **`nearby_thin_comps: 42` on a `supported` cell.** The non-9.8 buckets sum to exactly 42
  (1+1+5+3+5+26+1). This is **[[L-SW-2026-020]] instance 4 sitting in a live payload** — the
  field sums all nearby buckets, so it is correct inside `low_support` and misnamed everywhere
  else, and this response is everywhere else. Mike's framing: better evidence than the
  description of it.

### Process note — two Claude errors in the ship blocks, both caught by the terminal

1. A **bash heredoc** (`<<'MSG'`) handed to PowerShell. Every line errored; nothing committed.
2. Worse, and only exposed because the heredoc failed first: the block used
   `git commit --amend` to target `8200374`, which is **four commits back**. `--amend` rewrites
   `HEAD`. It would have renamed the docs commit into a valuation-fix commit. The amend was
   dropped for an ordinary follow-up commit (`8ae4187`).
3. Blocks 1 and 2 then **silently no-op'd** because the `git add` and `git revert` were written
   in prose beside the block instead of inside it. Mike had asked for self-contained blocks.
   **Standing: a ship block contains every command including staging, or it is not a block.**

### 🔴 TOMORROW OPENS HERE — two of four pools, and the comment is the seventh instance

**Mike's framing, 2026-08-17: "a wrong comment inside the fix for a wrong comment, which is the
seventh instance and the most self-referential one yet."** [[L-SW-2026-020]] rule 4 says the fix
for a mislabel is the likeliest place to commit the next one. This is that, one level deeper:
`8ae4187` was a commit whose *entire purpose* was correcting a false comment on this filter, and
it left standing a sentence that overstates the filter's coverage.

Blast radius today is 4 Whatnot rows against 1,695 eBay on the verification cell. **`market_sales`
is 10,048 rows and growing, and the comment is what a future reader will trust.**

### ✅ SCOPING MEASURED 2026-08-17 — the answer is NO, do not just extend the filter

Both of Mike's questions, measured read-only as `do_readonly` against the full tables. Pattern
read from the live module source, not retyped.

**(a) Does `is_signed` behave the same way on Whatnot data? — Populated, but at 1/6 the rate.**

| | rows | `is_signed` TRUE | rate | NULL |
|---|---|---|---|---|
| `market_sales` | 10,048 | **69** | 0.69% | 0 |
| `ebay_sales` | 271,344 | 11,842 | 4.36% | 0 |

Not a dead column — it is set, never null. But 65 rows match the literal word `signed` in
`raw_title` against 69 TRUE, so on Whatnot `is_signed` is **essentially just the literal word**.
The eBay derivation's other half — the `SS` group in `(CGC|CBCS|PGX) SS <grade>` — has almost
nothing to bite on, because Whatnot titles do not carry slab notation.

**(b) Are the vocabulary shapes the same? — NO. Half of them have ZERO hits.**

| shape | eBay | `market_sales` |
|---|---|---|
| sketch | 172 | **8** |
| sig | 52 | **0** |
| COA | 43 | **16** |
| auto | 30 | **0** |
| autograph | 7 | *(in auto)* |
| remarque | 7 | **0** |
| **pattern total** | — | **28 of 10,048** |

**The mechanical reason: Whatnot titles are 5× shorter.** Median `raw_title` length **14 chars
vs eBay's 71** (mean 18 vs 66). The vocabulary was enumerated against 66-character listing
titles dense with condition and grading tokens. A 14-character title has no room for those
shapes, which is why three of six return zero.

**🔴 AND THE PART THAT ACTUALLY BLOCKS EXTENDING IT — on Whatnot, "sketch" does not mean
signature.** The 12 highest-priced pattern hits, read directly:

```
$715  DJC Adventurous Astronaut Sketch Card            <- a sketch CARD, not a comic
$715  DJC Adventurous Astronaut Sketch Card            <- (duplicate row)
$499  2026 Under Wraps Autographed NFL Jerseys ... x4  <- NFL JERSEYS, not comics
$315  HAUNT #1 (1:100 RATIO) TODD MCFARLANE SKETCH VARIANT   <- a VARIANT COVER
$255  KING SPAWN #50 ... SIGNED BY TODD MCFARLANE ... SKETCH CVR  <- genuinely signed
$250  Live sketch cover #2                             <- a sketch COVER edition
$200  Todd Beats sketch #1                             <- a sketch COVER edition
$100  SIGNED BOOK with COA #72                         <- genuinely signed
$40   SIGNED BOOK with COA                             <- genuinely signed
```

On eBay, `sketch` was enumerated as a signature-adjacent shape. **On Whatnot it predominantly
denotes a SKETCH COVER — a variant edition — or a sketch card, which is not a comic.** Applying
the eBay pattern to `market_sales` would exclude variant editions under a *signature* rationale.
That is a wrong label attached to a correct-looking exclusion, i.e. the exact class CP-1 exists
to close, committed while closing it. **Do not port the regex.**

**Directional signal, for whenever the market unit is scoped:** 76 rows would be excluded
(`is_signed` OR pattern) at a **$25.00 median against $5.00** for the 9,972 that remain — a 5×
premium, matching the eBay raw side's 5.3× ($85.00 vs $16.05). The *premium* transfers even
though the *vocabulary* does not.

**🆕 SEPARATE FINDING, NOT MEASURED — non-comic rows in the corpus.** **6 of those 12** are not
comics (2 sketch cards, 4 NFL jersey boxes). Whatnot streams sell more than comics and the
capture is taking them. Stated with its N and **not** generalised: this is 6 of 12 in a
price-sorted slice of 28 pattern hits, **not** a corpus-wide rate. It needs its own measurement
before anyone quotes a number.

**Recommended shape for tomorrow:** fix the comment (Mike's stated minimum), then treat the
market side as **its own unit** — likely `is_signed` alone plus a Whatnot-specific vocabulary
derived from Whatnot titles, never the eBay pattern.

### ⚰️ THE RESIDUAL LIST HAS ZERO CONFIRMED MEMBERS

`8200374`'s comment predicted: *"Residual after this is the shapes nobody has enumerated yet."*
The first candidate was pulled today and **it is not a signature shape at all.**

**Recorded plainly at Mike's direction: the prediction that residual signature shapes would
surface has NOT been borne out by the first candidate.** One candidate is not a refutation, but
the list stands at **0 confirmed members** and should be described that way rather than as a
known-nonempty backlog.

### 🆕 A PATTERN, NOT A ONE-OFF — the grade parser reads adjacent text as a grade

Two measured instances, same shape:

| title | parsed as | truth |
|---|---|---|
| `Absolute Batman 1 Nick Dragotta Cover ... CGC 98 G2U` | grade **98.0** | seller shorthand for 9.8 · 29 rows |
| `Absolute Batman #1 CBCS 1st Print Not CGC` | grade **1.0** | **no grade in the title at all** · 1 row |

Sub-shapes: **notation shorthand** (`CGC 98`) and **ordinal collision** (`CBCS 1st` → `CBCS 1`).
Mike: *"two instances of the same shape — a grade extracted from adjacent text — and that is now
a pattern rather than a one-off."* Same consumer, likely one fix. The 1.0 row is the more
dangerous of the two: it carried a real high-grade price ($529.99) into the 1.0 bucket, where it
sat **above the 9.8 median** and looked exactly like the signature inversion the day's filter was
built to remove.

### ✅ NEAR MISS RECORDED — [[L-SW-2026-014]] avoided, not committed

The `$9.00` outlier pull returned **zero rows from `ebay_sales`**. The zero was **not reported as
a finding** — `market_sales` was checked next, and that is where the rows were.

Recorded at Mike's direction: *"a near miss recorded is worth as much as an instance."* The
tell that prompted the second query was [[L-SW-2026-014]] itself — the live response carried
`sources: {ebay: 1695, whatnot: 4}`, so a zero from one table could not be an answer about a
two-table corpus. Also an instance of [[L-2026-024]] working as intended: an empty result was
treated as a probe that could not have fired, rather than as evidence.

### Queue, in order

1. **Fix the "BOTH pools" comment** in both eBay query literals — say *graded and raw within
   eBay*, and state that the market pools are unfiltered. Comment-only, no behaviour change.
2. **Market-side signature unit** — scoped fresh per the measurement above. Not a port.
3. **Grade-parser defects** — `CGC 98` (29 rows) and `CBCS 1st` (1 row). One consumer.
4. **Non-comic rows in `market_sales`** — measure the rate before quoting one.
5. The 322-vs-321 reconstruction gap, if it ever matters.

---

## 2026-08-17 (later) — 📊 CAPTURE SCHEDULE MEASURED. Saturated AND the wrong list — same cause.

**MOST RECENT CHANGE: the §2 tracker specified in the capture schedule has been built and run.
ALL 34 measured scheduled keys have CLEARED §1's stopping rule, including all 9 "starved" §2A
keys and all 10 §5 bench keys meant to replace them.** Answers the question truncated from
yesterday's message. Nothing changed in the schedule — this is measurement only.

Measured read-only as `do_readonly` through the **production predicate**, extracted from the live
module source, with the variant exclusion the Python partition applies (L-SW-2026-024 rules 3a
and 3d). These are pool-eligible counts, not table counts.

### The question was: saturated, or walking the wrong list? — **Both, and they are one cause.**

⚰️ **DEAD (as a hypothesis): "duplicates mean eBay's 90-day window stopped producing."**
**REPLACED BY:** the walked keys are *finished*, and the retirement rule was never executed
because §2A says *"retire the moment a key clears"* and the tracker to detect clearing was
specified and never built. **REASON:** every key on the list has cleared, so every additional
walk of it can only return rows already held.

### 1. Daily new rows — smooth decline, not a cliff. Saturation confirmed.

Row counts alone are noisy (they track how long Mike walked that day). The discriminating
measure is **what share of the keys touched each day had never been seen before**:

| day | rows | keys touched | NEW keys | new-key share |
|---|---|---|---|---|
| 08-02 | 24,454 | 7,122 | 4,096 | **57.5%** |
| 08-03 | 20,712 | 8,484 | 5,323 | 62.7% |
| 08-05 | 36,961 | 15,941 | 9,284 | 58.2% |
| 08-08 | 3,741 | 1,564 | 786 | 50.3% |
| 08-12 | 15,777 | 4,361 | 2,036 | 46.7% |
| 08-14 | 12,082 | 1,722 | 512 | 29.7% |
| 08-17 | 4,830 | 1,568 | 472 | **30.1%** |

**Monotonic 58% → 30%. A smooth decline is saturation; a cliff would be something breaking.**
No cliff. ⚠️ Two things the row counts also show: **zero rows 2026-07-18 → 08-01** (a 15-day
gap inside the 30-day window), and **no rows at all on 08-09, 08-10, 08-13, 08-15**. Operating
note 6 says a week with no new rows is a signal.

⚠️ **THE DUPLICATES ARE NOT BEING STORED — the dedup is working.** `ebay_sales` holds 271,344
rows against **271,344 distinct `ebay_item_id`**, zero nulls, under a `UNIQUE` index. The
copies-per-item histogram is a single bar at 1. The extension's dupe counter is reporting
correct rejections. **199,692 rows still landed in 30 days — 73% of the whole table** — so
capture is not dying; it is walking a finished list while the broad result pages keep feeding
adjacent keys.

### 2. Per-key depth vs §1's stopping rule — 34 of 34 CLEARED

| block | rule | cleared | new rows/30d |
|---|---|---|---|
| §2A starved (9) | ≥10 comps, ≥5 graded | **9 of 9** | 424 |
| §2C blue-chip (15) | ≥10 comps, ≥5 graded | **15 of 15** | 3,007 |
| §5 bench (10) — *never walked* | ≥5 comps, ≥2 graded | **10 of 10** | 458 |

The §2A block was built from the 2026-06-08 audit's weak set. Every entry has been transformed:
**Incredible Hulk #180 went 2 comps / 0 graded → 238 comps / 109 graded. Batman #227 went 1/0 →
105/42.** The block did its job and should have been emptied.

**§5 is not a source of new keys either.** All ten bench keys already clear their target without
ever having been walked — they fill from adjacent search results. Promoting one buys nothing at
book level.

**§2B is the only block with genuine holes, and they are precise:** `Absolute Superman` and
`Absolute Wonder Woman` have **zero graded comps at issues 2, 5, 6, 9, 11, 12 and 2, 3, 8, 9, 12**
respectively. Recent books simply have few slabbed sales yet. `Absolute Batman` is deep
throughout (#1 = 1,543 comps / 362 graded).

### 3. 🔴 GRADE-CELL DEPTH — Mike called this right, and it is the real question

**Across the 24 cleared §2A+§2C keys, 72 of 168 slab cells (43%) hold fewer than 5 graded comps**
— below the CI-suppression line §1 was written to clear. The book-level rule is satisfied and the
grade-level product is not.

But the thin cells split into **two populations that must not be treated the same:**

**(a) Thin because the census is thin — capture CANNOT fix these.** Every pre-1980 key is empty
or near-empty at the top: Iron Man #55, Captain America #117, Batman #227, Batman #232, X-Men #94
all hold **zero** comps at 9.8. Incredible Hulk #180 and #181 hold **one**. A 1971 Batman in 9.8
barely exists, so no amount of walking produces the sale. Meanwhile every post-1983 key is deep —
Detective Comics #880 (2011) has 10 at 9.8, ASM #361 (1992) has 44, New Mutants #98 (1991) has 56.
**The split is by publication era, measured across all 24 keys, not by how hard the key was
walked.**

**(b) Thin because the pool is CONTAMINATED — and these read as the deepest cells on the board.**

### 🔴🔴 THE FINDING — the two most famous keys in the schedule are valued from the wrong books

`Action Comics #1` and `Amazing Fantasy #15` both sit in §2C Daily Core. Both looked healthy
(11 and 13 comps at 9.8). Pulled and read directly:

**`Action Comics #1`, 13 graded comps at 9.6+, ZERO of them the 1938 book:**
```
$250.00  Action Comics #1, CBCS 9.8, White Pages
$219.95  Action Comics # 1  1976 DC Comics CGC 9.8 ... Safeguard Promotional   <- 1976 reprint
$196.13  Action Comics Vol 1 484 CGC 9.8 (NM/M) (1978)          <- "Vol 1" parsed as issue 1
$112.00  Action Comics Annual #1 CGC 9.8 1987                   <- ANNUAL, different book
$96.00   Action Comics #1 (2025) Natali Sanders ... Ltd 800     <- 2025 relaunch
$79.99   Action Comics #1 Loot Crate Edition CGC 9.8
$75.00   Action Comics # 1 / DC Comics / The New 52 / CGC 9.8   <- 2011 relaunch
$39.99   Action Comics Special #1 CGC 9.6
```

**`Amazing Fantasy #15`, 24 graded comps at 9.6+, essentially none the 1962 book:**
```
$1700.00 Marvel Milestone Edition Amazing Fantasy #15 CGC 9.6 SS Lee 1992  <- 1992 reprint
$1499.99 Amazing Fantasy #15 Pure Silver (2018) CGC 9.9 Artist Proof       <- METAL REPLICA
$250.00  AMAZING FANTASY #15 CGC 9.8 - 1st Amadeus Cho          <- the 2004 series, x5 total
$199.99  Amazing Fantasy #15 Facsimilie Edition CGC 9.8         <- MISSPELLED, filter misses it
$165.00  Amazing Fantasy #15 | CGC 9.6 NM | 1st Spider-Man      <- a real AF15 9.6 is $3M+
```

**Five distinct defects, all visible in one pull:**

| # | defect | example | family |
|---|---|---|---|
| 1 | **year/edition not in the comp key** | 1938 / 2011 / 2025 Action #1 pooled as one | already logged, ⚠️yr §7.4 |
| 2 | **`Annual` / `Special` collapse into the base title** | `Action Comics Annual #1` → `#1` | `qualifier_title_clause` gap |
| 3 | **`Facsimilie` misspelling defeats `%facsimile%`** | AF15 facsimile at 9.8 | filter is exact-substring |
| 4 | **reprint editions not caught by `%reprint%`** | `Marvel Milestone Edition`, `Safeguard Promotional` | vocabulary gap |
| 5 | **issue parsed from adjacent text** | `Action Comics Vol 1 484` → issue **1** | ⚠️ **same family as today's `CBCS 1st` → grade 1.0 and `CGC 98` → grade 98** |

**Defect 5 is the third instance of a pattern found twice already today.** The grade parser reads
adjacent text as a grade; the issue parser reads adjacent text as an issue. One shape, two fields.
[[L-SW-2026-016]] at the extraction layer.

⚠️ **Why this outranks the capture question entirely:** these are not thin cells, they are
**confidently wrong** cells, on two of the most recognisable comics in existence, sitting in the
Daily Core precisely because they are high-traffic lookups. And the contamination makes the pool
look **deeper**, so every depth metric — including §1's stopping rule and the tracker above —
scores them as healthy. **A key can clear the rule on comps that are not the book.**

### 4. Is §4 inert? — Mike's conclusion is RIGHT; his reason needs one correction

⚰️ **DEAD: "demand promotions cannot fire without cold traffic, so §4 is inert."**
**REPLACED BY:** §4 fires nothing — **the promotion query run verbatim returns 0 promotable
rows** — but **not because the table is empty.** `lookup_demand` holds **1,453 rows, 1,420 of
them `is_internal = false`, 195 in the last 30 days, most recent today.**
**REASON:** `is_internal` is written from whatever the caller passes (`lookup_demand.py:62`,
`bool(f.get('is_internal'))`), so "external" does not mean "cold traffic". The top demand rows
are **Whatnot stream titles**: `Flat Rate Box (Shown LIVE) #86`, `Fernanco-Silver, Bronze 🔥`,
`7 oz #58`, `Flipmode Modern Comic`. Nothing clears the ≥5-lookups/week bar; the highest is 2.

**So the operational conclusion stands — §4 promotes nothing — and the record should not say the
table is empty, because someone will check and find 1,420 rows.** [[L-2026-023]]: a field is
defined by its writer, not its name. **🆕 Side finding: `lookup_demand` is being polluted by
non-comic Whatnot stream titles**, which will corrupt the ranking the moment real traffic arrives.

### What this means for the walk — reported, NOT a new schedule

1. **§2A should be emptied.** All 9 cleared. The rule said retire on clearing; nothing retired
   because nothing measured. **The tracker is the missing mechanism, not the list.**
2. **§5 does not backfill it.** All 10 bench keys already clear. Promoting from the bench is a
   lateral move.
3. **The remaining real capture gaps are narrow:** `Absolute Superman` and `Absolute Wonder
   Woman` interior issues at zero graded, and the §3 Sunday tail (unmeasured here).
4. **The largest available win is not capture at all** — it is the five identity defects above.
   Walking `Action Comics #1` again adds more wrong books to a wrong pool.

### Queue additions

6. **🔴 Comp-pool identity defects** — the five in the table above, ranked over further capture.
   Start with `Annual`/`Special` collapse and the `Facsimilie` misspelling; both are cheap.
7. **Build the §2 depth tracker** as a real artifact so retirement can fire ([[L-SW-2026-017]] —
   a step with no observable output is indistinguishable from one never taken).
8. **Grade-cell targets** to replace the book-level rule, split by era so pre-1980 keys are not
   chased toward 9.8 cells that do not exist.
9. **`lookup_demand` pollution** — Whatnot stream titles are entering the demand table.

---

## 🛑 STOPPING POINT — 2026-08-17. TWO UNITS SCOPED AND APPROVED. NOTHING RUNS.

**MOST RECENT CHANGE: Unit A and Unit B are scoped, approved in shape, and EXPLICITLY NOT
STARTED. Mike, 2026-08-17: "DO NOT START Unit A or Unit B. Nothing runs until I am back."**
This supersedes any reading of the capture work as in-progress. Nothing is half-done; nothing
is waiting on a partial state.

### ⛔ THE INSTRUCTION, ahead of everything else

**Do not begin Unit A or Unit B.** Both are fully scoped below so that a future session can
recognise them — **not so it can start them.** If a session opens and finds this entry, the
correct first action is to ask Mike, not to proceed.

### THE UNITS — carried forward unchanged from Mike's own wording

| unit | contents | risk |
|---|---|---|
| **Unit A** | mangled-title fixes **1 + 3** (stop-word stripping; prefix stripping) **+ backfill** | pure recovery — **no production FMV moves** |
| **Unit B** | fix **2** (publisher stripping) **+ backfill + corpus-wide FMV price audit** | **un-merges live pools** |

⚠️ **BINDING CONSTRAINT — code fix and backfill are ONE unit, always.** Shipping a fix alone
splits every affected book into **two** pools, which is worse than the single wrong pool it has
today: all three code fixes are forward-only, and 271,344 existing rows keep the mangled
canonical. There is no "fix now, backfill later" version of this work.

⚠️ **The backfill script goes in `scripts/`, never `docs/`** (`.dockerignore` excludes `docs/`),
**and needs a `deploy` to exist in the container even though it serves nothing**
([[L-SW-2026-023]]).

### 🎁 THE VERIFICATION INSTRUMENT — use it explicitly, not as background

Re-running the **current, unchanged** normalizer over the retained `raw_title` reproduced the
stored `canonical_title` on **6,000 of 6,000 sampled rows — zero differences, zero errors.**

**The baseline is proven flat, so every row that changes after a fix is attributable to that fix
alone.** That is the differential control [[L-SW-2026-011]] normally requires *constructing*, and
here it exists for free. Mike's direction: **use it as the instrument, not as a footnote.**

- **Both units:** before/after row counts by `canonical_title`.
- **Unit B additionally:** before/after **FMV, corpus-wide** — it changes the value of pools that
  are being priced in production today, so a name diff is not sufficient.

Two further consequences worth keeping: the defect is **entirely in current code** (no
archaeology needed), and the backfill is a **pure, idempotent function of `raw_title`**, so
running it twice — once per unit — is safe.

### ✅ ON RECORD AT MIKE'S DIRECTION — §1a: the right answer was that it cannot be written

Asked to amend a rule, the outcome was to **establish that it cannot be written yet**, with the
counterexample that kills the obvious repair.

- A single consistent year **is not the right year**: ASM #2 and #3 pass the check cleanly at a
  uniform **2014** on a **1963** comic.
- **Modal year is worse than refusing.** X-Men #1 holds **244 rows of the 1991 relaunch against
  27 of the 1963 book**, so modal would **bless the contamination as canonical and then discard
  the 27 real rows.** Mike: *"I would not have caught that before shipping it."*
- Measured at scale: **52 of 108** #1 keys have an unsafe modal year. TMNT returns **1988 on 17%**
  of rows for a **1984** comic.
- **What would work, and why it is actionable rather than a dead end:** the year must come from
  **outside the pool**, because the pool is the thing under suspicion. **Production already has
  such a source** — the grader reads the publication year off the photographed cover and passes it
  to the valuation. **The capture tracker does not**, because the key list has never carried years.
  The weekly list now carries a year for the 24 #1s the data supports, which is the start of one.

### ✅ SAME SHAPE, CAUGHT EARLIER — the years-on-#1s correction

The first version derived every #1's year from the pool's modal `title_year`. Unsafe on 52 of 108.
Now printed **only** where one year holds ≥80% of the pool with spread ≤15 years — **24 of them** —
and blank with a stated reason otherwise. **A wrong year in a search is worse than no year.**

⚠️ **Mike, recorded because he named it: "Second time today you have proposed something, measured
it, and withdrawn it before it reached me. That is the cycle working."** The other instance the
same day: a mangled-title population of **14,861** rows, withdrawn before it reached a commit —
it matched any `raw_title` containing "of" anywhere, so `Amazing Spider-Man` at 1,884 rows was a
false positive. Corrected figure: **6,815 across 20 titles, stated as a floor.**

### QUEUED BEHIND THE TWO UNITS

**Grade and issue parser defects — three instances of one pattern**, both parsers reading
adjacent text as their own field:

| input | read as | truth |
|---|---|---|
| `... CGC 98 G2U` | **grade 98.0** | seller shorthand for 9.8 · 29 rows |
| `Absolute Batman #1 CBCS 1st Print Not CGC` | **grade 1.0** | no grade in the title at all |
| `Action Comics Vol 1 484` | **issue 1** | issue 484 |

Then, unchanged from earlier today: the "BOTH pools" comment fix, the market-side signature unit
(scoped fresh, **not** a port of the eBay regex), non-comic rows in `market_sales`, `lookup_demand`
pollution by Whatnot stream titles, and the 322-vs-321 reconstruction gap.

### WHAT SHIPPED 2026-08-17

Badge re-applied and purged; signature filter deployed and verified live (Absolute Batman #1 @ 9.8
→ **$345.00**, the predicted figure exactly); the capture schedule amended; and
`docs/EBAY_CAPTURE_WEEKLY.docx` created as the operating sheet — **147 searches a week, derived
from measuring all 292 rotating keys** rather than from what sounds scarce.

Mike's closing assessment, recorded: *"The audit overturned the premise the whole capture schedule
rested on, and the schedule that replaced it is derived from measurement rather than from what
sounds scarce."*

---

## 🛑 STOPPING POINT — CP-1 valuation arc, 2026-08-16

**MOST RECENT CHANGE: the CP-1 bug-hunt arc is CLOSED and the roadmap resumes.** Everything
below is queue, not chase. A future session should NOT re-derive this decision or re-open these
items as discoveries — they are measured, recorded, and deliberately deferred.

### Fixed and live
- **Lot-range leakage** (`499371b`) — the multi-issue range filter bounded the second number as
  `\d{2,4}`, so `#1-4` and `#1-8` sailed into single-comic pools. 2,405 rows live, 244 ≥$100.
  Four measured guards. **Verified in production: Wolverine LS #1 raw $150 → $125.**
- **Badge third state** (`9b1a5d8`) — the client collapsed the server's three verdicts to two on
  `roi > 0`, so a $16 gain rendered the same green as $1,200. ~29% of confident recommendations
  are under $50. No new threshold: 50 is the server's own boundary, restored not invented.
- **edition_span / multi_edition split** (`9ab7cc3`).

### Scoped, drafted, HELD — not cancelled
- **Signatures** — `is_signed` + six enumerated shapes, query-time, both pools. 115 cells lose
  rateability, −$28.80 average graded median. **Held deliberately:** it pushes 114 cells below
  the evidence bar and those cells live in the thin population, so it makes the thin-bucket
  problem worse while that work is unbuilt. Ships after.

### Measured, NOT BUILT — no code exists for either
- **True cost of grading.** `grading_cost = 30` is flat and wrong by 2–4× at the low end — a $50
  book costs ~$71 to grade (142% of its value). Moves **24.9% of WORTH verdicts** off WORTH.
  Shape: `tier(V) + shipping(V) + flat + expected_loss(V)`; only tier, insurance and loss scale.
  ⚠️ The expected-loss term is **negligible** ($0.01–$0.50, i.e. 0.01–0.39% of cost) — the tail
  risk is priced as the *insurance premium* inside shipping, not as loss. ⚠️ **CGC's published
  fee pages 404'd; every figure is an estimate and none is sourced.**
- **Uncertainty framework.** Three layers — estimator / uncertainty / decision — because ROI is
  downstream of the estimate, so a single `f(depth, roi)` is circular. 47.4% of graded cells have
  **no CI at all** (`bootstrap_ci_median` returns `(None, None)` below 5 values) and the raw side
  has none at any depth, while **over half of raw pools hold fewer than 5 sales**.
  **Binding design constraints, agreed:** both stochastic terms resampled (graded *and* raw), the
  cost term stated as fixed explicitly rather than by omission, and the widening factor derived
  from the hold-one-out table rather than chosen. Hold-one-out is the working instrument: at k=4
  the median error is 6.7% but **1 in 8 exceeds 25% and p99 is 157%** — the damage is in the tail,
  which is why both ladder-shape proxies (inversion, residual) missed it. That table is a **lower
  bound**: it is sampling error on liquid books, and genuinely thin buckets are thin because the
  book does not trade.

### Known STRUCTURAL gap — named as such, not a bug
- **Grade uncertainty.** *(Mike's observation, 2026-08-16.)* The framework resamples comps and
  treats the assigned grade as **exact**. A half-point grade miss moves more value than the entire
  cost model. This is not calibration and not a defect in existing code — it is a dimension the
  design does not model at all.
  ⚠️ **Second thread pointing at the same measurement:** the grading-consistency work, for which
  **Joseph Vicario's 25 pinned `grade_submissions` were preserved** (pin before 2026-11-04). Those
  two threads should meet.

### Queued, unchanged — measured populations, no new information needed to start
- `canonical_title` splits — Wolverine #1 under **three** keys while the `Wolverine` key merges
  1982 ($150, 156 rows) with 1988 ($59.99, 113 rows). First confirmed instance; the Invincible
  case was retracted.
- Issue-number absorption — 22,623 raw rows with NULL `issue_number` (10.6%), unreachable by any
  issue-filtered lookup. Split between legitimate (trades, omnibuses) and parse failure is
  **unmeasured and is the queue item's first task**.
- PSA + six graders missing from Unit 1a's regex — PSA alone is 410 rows, larger than PGX and
  CBCS combined, both already enumerated.
- Lot **vocabulary** gap — `is_lot` keys on vocabulary, not structure; 6,829 rows carry "lot" and
  6,280 "complete/full" outside the caught phrases.
- Unit 1a / 1b — extension regex + backfill, not started.

### Why these are queue rather than chase
The two defects that were **actually wrong** — X-Men #1 confidently priced off a contaminated
pool, and Wolverine LS #1 priced off four-comic sets — are fixed or scoped. Everything after that
is calibration, with **one exception**: the flat $30 grading cost is a live one-directional error
on every verdict and belongs on the queue as a defect, not as tuning.

⚠️ **Method note for whoever picks this up:** five measurement failures in this arc came from the
same shape — substituting a proxy for the production predicate. `docs/LESSONS.md` L-SW-2026-024,
items 3a–3d. In particular, **a graded-side measurement written in SQL alone is wrong**, because
variants are partitioned out in Python.

---

### STILL OPEN (next sessions)
- **Stacking step 2** (account.html "Change Plan" → `openPortal()` + 409 auto-redirect; verify Stripe portal plan-switching enabled) and **step 3** (`handle_subscription_deleted` sub-id match + immediate-cancel→free test) — hardening on the now-closed blocker (detail in the stacking entry below).
- **Section F checklist** (mobile + load) — draft AFTER stacking 2 & 3; **mobile half is higher-priority** (GalaxyCon booth is phone-first; start real-device testing well before Aug 21, not last-minute).
- **Cert-number recovery lookup** (small build) — the marketable slabbed-recovery headline.
- Lower-priority backlog: ~30s comic-ID progress messaging; email setup (mike@/support@); `lookup_demand` thin-data pull (after weeks of real traffic); **variant reclamation / subtyping (Tier 1 — see below)**; capture-cadence scheduled pull; ⏰ 90-day purge (~Sept 17).

  **Variant subtyping (Tier 1), reconfirmed 2026-08-16 — DELIBERATELY NOT TAKEN as part of the
  CP-1 bug work.** Mike: *"it deserves a session rather than a slot."* It is a **feature to
  design, not a defect to measure**, which is why it does not belong at the tail of a bug hunt.
  - ⚠️ **There is NO variant filter defect.** A claim that the graded query omitted the
    `is_variant` filter was **retracted** — the graded side partitions variants out in Python
    (`sales_valuation.py` ~741) while the raw side filters in SQL, both deliberate since
    `9c9dc7c` (2026-06-11). Do not re-open this as a bug. See `docs/LESSONS.md` L-SW-2026-024,
    fifth instance.
  - **The actual gap:** variants are currently *excluded and disclosed* — "Estimate reflects the
    standard cover; variant sales excluded", firing at ≥30% excluded / ≥3 excluded / ≥5 total.
    The open question is whether covers that sell at **orders-of-magnitude different prices**
    (Absolute Batman is the case that made this Tier 1) deserve to be **their own pool** rather
    than discarded behind a footnote.

---

## Session 109 (Jun 22, 2026) — Multi-sub STACKING investigated (read-only) → fix STEP 1 of 3 SHIPPED & VERIFIED: checkout stacking guard (the launch blocker is CLOSED)

**Built draft-for-review; Mike ran all git/deploy + the prod verification. Read LESSONS + cross-project at open.**

### Headline: the stacking launch-blocker is CLOSED. A real user can no longer stack subscriptions via create-checkout.
Investigated the Session-108 multi-sub stacking bug **read-only**, then shipped the contained fix (step 1 of a planned 3). Steps 2 (UI) and 3 (webhook) are hardening on a now-closed blocker — queued, no rush, before launch.

### READ-ONLY INVESTIGATION — what the code actually did (all in `routes/billing.py` + 2 frontend pages)
1. **Checkout guard: NONE (root cause).** `create_checkout_session()` validated the plan, got/created the Stripe customer, then **unconditionally** called `stripe.checkout.Session.create(mode='subscription')`. It never read the user's current sub state → every call minted a **brand-new** subscription. The 3-sub +22 result is exactly what this code does hit 3×; **not** a pure testing artifact.
2. **No in-code modify/upgrade path.** No `stripe.Subscription.modify` anywhere (only `.retrieve`). Billing routes: `/plans`, `/my-plan`, `/check-feature`, `/create-checkout`, `/customer-portal`, `/webhook`, `/record-valuation` — **no change-plan endpoint**. The only in-place modify is the **Stripe Customer Portal** (if configured), which is how the S108 "Pro→Guard works" almost certainly happened.
3. **Webhook = last-writer-wins.** `users` tracks ONE `stripe_subscription_id`/`plan`/`status`. `handle_subscription_updated` matches **by customer_id only** and overwrites from whichever sub's event fires last (+22 landed on guard incidentally). **Worse latent bug:** `handle_subscription_deleted` (billing.py:778) also matches by customer_id only → canceling **one** of several stacked subs reverts the user to **free while Stripe keeps billing the others.**
4. **UI reality: "Change Plan" routes back into stacking.** account.html shows paid users **"Manage Billing"** (→ portal, safe) AND **"Change Plan"** (→ `/pricing.html`). Every pricing button calls `create-checkout` → so "Change Plan" stacks a second sub.

### STEP 1 SHIPPED & VERIFIED — checkout stacking guard (`routes/billing.py`, additive guard clause)
- Committed + pushed + **deployed** by Mike: `"fix(billing): stacking guard — refuse create-checkout when a live sub exists"`.
- The guard: before creating a session, read `get_user_plan()`; if the user has `stripe_subscription_id` AND `subscription_status` in **active/trialing/past_due**, return **HTTP 409** `{"error": "...", "code": "existing_subscription", "manage_via": "customer_portal"}`. Checkout remains allowed ONLY for free→first-paid.
- **Edge cases (confirmed working as specified):** only active/trialing/past_due with a non-null sub id is blocked; canceled/incomplete/unpaid/none can still (re)subscribe; **fails OPEN** on a DB read error (never blocks a legitimate first-time subscriber).
- **VERIFIED two ways in prod:** (1) create-checkout as +22 (user 30, already has live subs) → **HTTP 409** `{code:"existing_subscription", manage_via:"customer_portal"}` (was 200 + checkout_url, would have stacked a 4th sub). (2) Stripe dashboard shows +22 still has **exactly 3** subs, not 4 → the guard refused **before any Stripe call**.

### STILL TO DO — steps 2 & 3 (next session, separate passes; hardening on a closed blocker)
- **STEP 2 — UI redirect:** point account.html "Change Plan" at `openPortal()` (not `/pricing.html`); have pricing.html/account.html **detect the 409 `code:"existing_subscription"`** and auto-open the portal instead of alerting the error string. Also verify in the Stripe dashboard that the Customer Portal's **plan-switching ("switch plans") is enabled** for Pro/Guard (dashboard config, no code) — flag if not.
- **STEP 3 — webhook hardening (the scary latent bug):** `handle_subscription_deleted` should only revert to free if the deleted `sub.id` matches the user's stored `stripe_subscription_id` (or re-resolve the remaining active sub). Optional follow-on: `handle_subscription_updated` ignores events for a sub that isn't the user's-of-record (kills last-writer-wins flicker).
- **Pairs with:** the still-untested **immediate-cancel → plan=free** Section E leg (same handler) — do it alongside step 3.

### SECTION F (Mike's question) — what it is
There is **no standalone doc** enumerating the readiness sections A–F; the lettering lives only in the session notes (A/B early · C = collection mgmt [S104] · D = tier gates [S106] · E = billing [S107–109] · **F = mobile + load**). **Section F = mobile + load testing** — the last un-run readiness section. It maps to existing TODO items but was never written out as a detailed checklist: **mobile** = full grading→value→verdict→save flow on real Android + iOS devices (P1 "Mobile testing"), plus billing/portal on mobile (P2) and PWA install; **load** = behavior under concurrent/convention-spike usage (the R2 edge-cache work was bought as spike insurance). If we want F run rigorously, first step is drafting an actual F checklist (devices, flows, a load target) — it doesn't exist yet.

### NEXT SESSION — queued
1. **Stacking step 2** (account.html "Change Plan" → portal + 409 detection) — draft-for-review.
2. **Stacking step 3** (`handle_subscription_deleted` sub-id match) + **immediate-cancel → free** test (same handler) — draft + test.
3. **Section F** — draft a real mobile + load checklist, then run.
4. ⏰ (Tracked) **90-day grade-retention PURGE** — hard deadline ~2026-09-17.

---

## Session 108 (Jun 20, 2026) — Section E billing LIVE TEST: core revenue path GREEN; webhook 500 root-caused (env-var typo) & fixed; webhook hardening shipped; multi-sub stacking bug found

**Built draft-for-review; Mike ran all git/deploy + the live Stripe test. Read LESSONS + cross-project at open.**

### Headline: core billing works end-to-end — pay → correct tier. Two bugs found, one fixed.
The webhook 500 that blocked all of Section E is **FIXED**, and **Pro + Guard checkout now flip the tier correctly** (incl. the Pro→Guard tier-CHANGE path). A second billing bug (subscription **stacking**) was found during testing and is queued.

### ALSO SHIPPED (Session 108 follow-on, commit `daf9050`) — sales-data coverage assessment + lookup-demand instrumentation
- **Read-only coverage assessment** of the sales corpus (script left on disk untracked: `scripts/coverage_assessment.py`). Findings: eBay `ebay_sales` = **53,840** rows (README "~24K" was stale), Whatnot `market_sales` = **9,677** (real, ~15% of corpus). **Freshness is fine** (83.5% within 180d; capture active but manual/bursty — a real Apr–May stall, resumed June). **Breadth wide, DEPTH thin** (89% of title/issue keys have 1–2 comps; grade-specific FMV is reliable on only ~268 books, high-confidence on 93). **Processing gap:** ~27% of eBay rows excluded by variant/lot/reprint filters — ~11K variants (1,235 graded+fresh) we're sitting on but not pricing (ties to the queued barcode-variant-subtyping work). **Read:** weak spot is DEPTH + over-filtering (PROCESSING), not coverage/freshness — and we were **blind** to which titles return no/thin data.
- **Fix (shipped):** lookup-demand instrumentation — `migrations/add_lookup_demand.sql` (new `lookup_demand` table + ranking indexes) + `lookup_demand.py` (fire-and-forget daemon-thread logger, never blocks/raises) + 3 hooks in `routes/sales_valuation.py` (valuation success, fmv no-data fallback, fmv success). Captures title/canonical/issue/grade, comp counts, fmv_method, estimated/no_data, **user_id** (for distinct-user ranking) and **is_internal** (admin pre-filter; test accts excluded by user_id at query time). Purely additive, non-blocking. **Verified live:** migration applied in Render shell, deployed, an ASM #300 fmv lookup wrote a correct row (`comp_count=327`, `user_id=None`, `fmv_method='mid'`). Now collecting; the "top thin-data titles" demand query is ready to run read-only once real traffic accumulates. **Don't over-read early sparse beta data.**

### THE WEBHOOK 500 — ROOT CAUSE WAS A RENDER ENV-VAR TYPO (not code)
- **All four theories from the webhook-500 brief were WRONG** — not the `.get()` bug, not Stripe version drift, not stale deployed code, not env propagation. (My read-only investigation had already **disproven** the `.get()` theory — proved `.get()` works on stripe 12.1.0 typed Event/Session objects — and flagged "we're blind without the traceback; instrument it.")
- **ACTUAL cause:** the Render env var was misnamed **`STRIPE_WEBHOOOK_SECRET` (THREE O's)** instead of `STRIPE_WEBHOOK_SECRET`. The code reads the correct (two-O) name via `os.environ.get`, found nothing → hit the "Webhook secret not configured" guard → **returned 500** (correctly refusing to process an unverified webhook). The **VALUE was always right; only the KEY NAME was wrong.**
- **Why it hid:** substring search (`grep -i stripe`) displayed the 3-O name so it "looked right"; the earlier manual "secrets match" check compared the **value** (correct); the pre-flight script structurally **cannot** check the webhook secret (Stripe never exposes `whsec_` via API). It only surfaced via **exact-name resolution in the container:** `printenv STRIPE_WEBHOOK_SECRET` = empty, `env | grep -c STRIPE_WEBHOOK_SECRET` = 0, while `STRIPE_SECRET_KEY` = 1 (the asymmetry was the tell).
- **FIX:** renamed the Render env var to `STRIPE_WEBHOOK_SECRET` (two O's), kept the value, redeployed.

### Webhook hardening — SHIPPED & KEPT (it's what pointed at the bug)
Committed + deployed this session (`routes/billing.py` + the stripe pin):
- **`logger.exception` + the explicit "Webhook secret not configured" message** → THIS is what pointed at the env var instead of sending us deeper into the code. Instrument-don't-guess paid off directly.
- `handle_checkout_completed` writes the **real** status (`trialing`, not hardcoded `active`) — confirmed correct in testing (`subscription_status=trialing` for the 14-day trial).
- `_subscription_period_end()` for the `current_period_end` API move (onto `items[]` in 2025-03-31+).
- 200-on-handler-error + greppable logging (a deterministic handler bug no longer retry-storms; traceback is logged, replay via Stripe dashboard after a fix).
- `requirements.txt` pinned **`stripe>=12,<13`** (separate commit) to stop local/prod drift.

### CONFIRMED WORKING (Stripe TEST mode, throwaway mikeberrysc+22@gmail.com, user_id 30)
- **Pro checkout:** webhook 200; `--check-db` → `plan=pro`, `subscription_status=trialing`, both stripe IDs set.
- **Guard checkout (as an upgrade from Pro):** `plan=guard`, `trialing`, both IDs set → **tier-CHANGE path works.**
- **Cancel-at-period-end:** portal scheduled all subs to cancel **Jul 4** (correct scheduled-cancel behavior).
- **Pre-flight `stripe_preflight.py`:** GREEN (key=TEST, all 4 prices resolve `livemode=false`, webhook endpoint + events good). `--check-db` flag working.

### NEW BUG FOUND — MULTI-SUBSCRIPTION STACKING (next billing task)
The customer portal for +22 showed **THREE concurrent active subscriptions** on the one customer: Guard $9.99 + Pro $4.99 + a **SECOND** Pro $4.99 (all cancelling Jul 4). Each checkout run created a **NEW** subscription instead of **MODIFYING** the existing one — so Pro→Guard "change" stacked a new sub, and a re-run Pro checkout stacked another. A real user who subscribes then upgrades could be billed for multiple overlapping plans (~$20/mo here).
- **Caveat — partly a testing artifact:** Mike ran raw checkout 3× rather than using an upgrade button. First step is to determine whether there's a real upgrade path that was bypassed vs. genuinely create-new-every-time.
- **INVESTIGATE (read-only first):** does `routes/billing.py`'s `create-checkout` path check whether the user already has an active Stripe subscription? Is there a proper change-plan flow that MODIFIES the existing subscription (Stripe supports this directly), or does it always create a new one?
- **FIX (either/both):** change-plan should modify the existing subscription, not create parallel; AND/OR checkout should refuse/guard if the user already has an active subscription. **A stacking guard is needed before launch regardless.**

### Signup "too many requests" — my read-only finding (no action this session)
Confirmed: **NOT our app and NOT Cloudflare** — there is no signup rate-limit anywhere in our code (`flask-limiter` isn't even a dependency; only `contact.py`/`monitor.py`/`grading.py` have limiters, none on `/api/auth/*`), and the signup POST goes **straight to Render** (`API_URL = collectioncalc-docker.onrender.com`), bypassing Cloudflare. Most likely **Resend's free-tier daily email cap (~100/day, doesn't reset in minutes)** — fits "didn't clear in 10 min." Accounts still create (the send failure is swallowed → `email_send_failed`); what breaks under load is verification **emails**. **Launch mitigation:** Resend paid plan + verified sending domain before Aug 21. Also: we have **NO abuse rate-limit on signup at all** — consider a gentle per-IP limit post-launch. (Logged; no action.)

### SECTION E STATUS
- **Core revenue path (pay → correct tier): 🟢 GREEN.** Pro, Guard, and tier-change all confirmed.
- **Cancel scheduling:** works (cancel-at-period-end → Jul 4).
- **STILL TO TEST:** immediate cancel → revert to `plan=free` (the `customer.subscription.deleted` path). The portal only did cancel-at-period-end (Jul 4), so nothing has terminated yet — needs a "cancel immediately" to fire the downgrade webhook.
- **STILL TO FIX:** the multi-sub stacking guard (above).

### LESSONS LOGGED THIS SESSION (docs/LESSONS.md)
- **L-SW-2026-006** — config typos are invisible to the eye (brain autocorrects WEBHOOOK→WEBHOOK) AND to substring/value checks; only exact-name machine resolution (`printenv NAME`, `env | grep -c NAME`) catches them.
- **L-SW-2026-007** — instrument before theorizing: "log the real failure reason" turned an hour of wrong theories into a one-line answer.
- (Reinforced **L-SW-2026-004:** Render auto-deploy is OFF — `git push` does NOT deploy; env-var changes need a redeploy + fresh shell to reach the process.)

### NEXT SESSION — queued
1. **Multi-sub stacking bug** — investigate (read-only) + fix (modify-existing and/or refuse-if-already-subscribed). Launch blocker.
2. **Test immediate cancel → `plan=free`** (the `customer.subscription.deleted` downgrade/teardown webhook path) — the last untested Section E leg.
3. (Earlier queued, still open) **~30s comic-ID progress messaging** — brief drafted, not shipped.
4. ⏰ (Tracked) **90-day grade-retention PURGE** — hard deadline ~2026-09-17; `saved_collection_id` backlink.

---

## Session 107 (Jun 19, 2026) — Grade-submission RETENTION shipped & verified end-to-end; collection must-fixes; privacy reconciliation

**Built draft-for-review; Mike ran all git/deploy/purge/migration/smoke-test. Read LESSONS + cross-project at open.**

### Headline: grade-submission retention is LIVE and verified (the matbanshee gap is closed)
- **Origin:** read-only investigation of matbanshee (user 21) "undergraded my 3 books by up to 2.6 pts" → found we retained **NOTHING** for unsaved grades (no photos/grade/subgrades/comic). Token-count forensics showed he submitted ~4 photos (multi-angle starvation excluded), leaving old-photo/photo-condition as the leading-but-unprovable hypothesis. Lesson **L-SW-2026-003** logged. Spec: `docs/technical/GRADE_RETENTION_SPEC.md`.
- **Privacy disclosure shipped FIRST** (prerequisite — commit `245f99b`): `privacy.html` new "Grading Data & Image Retention" subsection (90-day retention incl. unsaved, deletion-on-request within 30 days, authorized-staff review), reconciled the old "Images" line (removed the "unsaved grades vanish" + "anonymized-only" framing); `login.html` signup Terms/Privacy consent line.
- **Retention BUILT + verified live** (commits `e87b8cf` schema, `801e79d` persist, `6fb83f7` admin):
  - `migrations/add_grade_submissions.sql` — 24-col `grade_submissions` table, applied to prod via **Render-shell Python** (psql not in container — used psycopg2 + `$DATABASE_URL`).
  - `grade_retention.py` — background daemon-thread persist AFTER the grade response (no added latency); cascade delete + per-user erasure (R2 objects then DB rows).
  - `/api/grade` persist hook; admin `GET /api/admin/grade-submissions` (find by email/user_id/submission_id, presigned R2 image URLs) + `DELETE` (cascades DB row **and** R2 objects, single + by-user); `r2_storage.generate_presigned_url`; `admin.html` "🔬 Grade Subs" tab + one-click hook from the Feedback tab.
  - **Smoke-test: persist / view / delete-cascade all PASSED.**

### Collection must-fixes (commits `80d34c7`, `0579326`, `1cbfd06`) — shipped earlier in the session
- **Fix 1:** always-confirm delete — names the comic, "can't be undone" copy, removed the skip-warning bypass (no one-tap-delete). **Fix 2:** de-clickified list rows (pure CSS — no dead handler; gallery click left intact = real expand feature). **Fix 3:** admin Feedback comments expand-on-click (was CSS-truncated; backend already sent full text).

### ✅ Deletion-request runbook — written & committed
- **`docs/SW_deletion_request_runbook.md`** — believed already committed but was **not in the repo** (searched names/content/all branches/uncommitted — only a TODO reference existed), so it was **drafted fresh and committed** this session. Manual erasure procedure pairing with the admin grade-submission delete tool: verify by registered-email ownership (confirm-to-account-email on mismatch), scope incl. unsaved grade submissions, R2-cascade delete (R2 first, then rows), confirm `images_deleted`, confirm back, within 30 days, never auto-delete.

### ✅ Section E (billing) PREP — COMPLETE & GREEN (read-only, committed)
- `docs/technical/STRIPE_TEST_BILLING_RUNBOOK.md` — setup map + safe test runbook. Key findings: checkout is **server-created hosted Checkout** (no client publishable key — that mismatch can't happen here); price IDs are env-driven; webhook = `/api/billing/webhook` (mandatory secret); tier path `checkout.session.completed → handle_checkout_completed → update_user_subscription`; 14-day trial ⇒ status shows **`trialing`** (entitled, not broken).
- `scripts/stripe_preflight.py` — strictly read-only (`Price.retrieve` + `WebhookEndpoint.list` + optional `--check-db` SELECT). The `.get()`-on-Stripe-objects crash was patched to attribute access (`getattr`); `--check-db EMAIL` folded in.
- **Pre-flight passes GREEN in Render shell:** key=**TEST**; all 4 prices resolve `livemode=False` (**Pro $4.99 / $49.99, Guard $9.99 / $89.99**); webhook endpoint **enabled** at `/api/billing/webhook` with all required events.
- **✅ Item #2 (webhook signing secret) MANUALLY VERIFIED** — Render `STRIPE_WEBHOOK_SECRET` == the test endpoint's `whsec_`. **All 3 config items confirmed → Section E config is FULLY verified. Next session is the LIVE TEST ONLY** (run Part B; no more config to check).

### ⏰ / 🔧 Tracked follow-ups (carry forward)
1. **⏰ 90-day PURGE — HARD DEADLINE ~2026-09-17** (day-90 from persist deploy). ⚰️ *(Was framed as "after soft launch (Jul 21) + GalaxyCon (Aug 21-23)" — BOTH dead: soft launch is **Aug 4**, GalaxyCon **dropped** 2026-07-29.)* ⚠️ **This is now the ONLY hard external deadline left on the project** — it used to sit behind the con, so it no longer inherits that urgency; it needs its own reminder. Published-policy obligation; **cannot slip past the date**. Columns/index (`images_purge_after`,`pinned`) + `delete_grade_submission` helper already in place → scheduled job + feedback-pin away.
2. **🔧 `saved_collection_id` backlink-on-save** — always NULL (grade precedes save; save path doesn't backlink). Small.
3. **~30s comic-ID progress messaging** — brief drafted, **not yet shipped** (staged honest "still working" messaging only — NO accuracy-costing speedups). Queued.
4. **Email setup (mike@/support@slabworthy.com)** — Resend is **outbound-only**, no real inbox confirmed; **gates the matbanshee reply**. Deliberately held / not started.

*(Section E item #2 — webhook signing secret — now ✅ manually verified; no longer a follow-up.)*

### 🧠 Lessons logged this session (docs/LESSONS.md)
- **L-SW-2026-004:** a Render env-var change needs a redeploy/restart **AND a fresh shell** — an already-open shell keeps the old value (caused a mid-session "same key" confusion).
- **L-SW-2026-005:** run a strictly read-only pre-flight before any billing/money operation — `stripe_preflight.py` caught an expired key, an accidental LIVE key in Render, and a script bug before any could corrupt a real billing test.

### NEXT SESSION OPENER — Section E LIVE TEST (config fully verified; execution only, "follow Part B")
1. Make a **THROWAWAY** account — **NEVER** the `test-*@slabworthy.test` accounts (`create-checkout` taints an account with `stripe_customer_id` the instant checkout starts).
2. Test card `4242 4242 4242 4242` → checkout for **Pro + Guard** → confirm webhook **200** + tier flips (use `--check-db EMAIL` before/after; `my-plan` shows **`trialing`** not `active` due to the 14-day trial — both entitled).
3. Test customer-portal **cancel** → reverts to free.
*(No more config checks — all 3 items already verified this session.)*

Purge sits on its 2026-09-17 clock until separately scheduled.

---

## Session 106 (Jun 18, 2026) — Tier Honesty Pass SHIPPED (storefront now matches product); extraction resilience; ID Sigs CORS bug diagnosed

**Built draft-for-review; Mike ran all git/deploy/purge/smoke-test. Read LESSONS + cross-project at open.**

### 1. Extraction resilience (Commit 2) — SHIPPED, deployed, purged
- `comic_extraction.py` Anthropic client now `timeout=30.0, max_retries=1`; `app.html` `/api/extract` wrapped in a 75s `AbortController` (try/finally clears the timer); honest **"⏳ Our identifier is busy right now"** copy on backend timeout (`Request timed out` / 503 / 504 / overloaded) AND client `AbortError`, replacing the misleading "Could not identify." Insurance vs future load now the Session-105 signature auto-fire contention source is gone — turns a multi-minute hang into a clean ~30–60s honest failure.

### 2. Tier Honesty Pass (Section D reconciliation → 4 commits A–D) — SHIPPED, deployed, purged
- **Context (read-only Section D):** the four tiers were nearly indistinguishable in use. Only **3 of ~11** advertised differentiators were truly server-enforced (slab-guard regs, multi-photo, chrome-extension). Valuations were a **hardcoded flat 25/mo across ALL tiers** (the PLANS valuations field was dead — `check_feature_access('valuations')` never called); export / API / bulk / ownership-certs / white-label / LE-portal were **unbuilt**; the only upgrade prompt fires at the 4th Slab Guard registration.
- **A — per-tier grading cap wired to PLANS** (`routes/billing.py` + `routes/grading.py`): replaced hardcoded `MONTHLY_GRADING_LIMIT=25` with `PLANS[plan]['valuations_per_month']` — **Free 25 / Pro 100 / Guard 250 / Dealer 1000**, admins exempt. Uses the live `gradings_this_month` counter; the dead `valuations_this_month` path left untouched (NOT bridged — see follow-up). **VERIFIED:** `/api/billing/plans` reads 25/100/250/1000.
- **B — `fetchImageAsBase64` `response.ok` guard** (`js/utils.js`): honest "Couldn't load image (HTTP N / network error)" instead of the misleading "Image decode failed." **VERIFIED** — and it surfaced the REAL ID Sigs CORS bug (#3).
- **C — `pricing.html` honesty:** real caps (no "Unlimited" anywhere), Excel/CSV export trimmed, Dealer relabeled **"Coming Soon"** with a **"Notify Me →"** CTA to `/contact.html` (no checkout), Guard "verified ownership certificates" removed, Signature ID surfaced as a Guard **coming-soon** feature + compare-table row.
- **D — refuse Dealer checkout server-side** (`routes/billing.py`): `create-checkout` rejects `plan='dealer'` with an honest coming-soon message + `coming_soon:true` — enforces the label, not just displays it.
- **Net headline:** the storefront now matches the product — no advertised unlimited valuations we cap, exports we haven't built, or a Dealer tier that's mostly unbuilt.

### 3. ID Sigs CORS image-fetch bug — DIAGNOSED (read-only), queued to Signatures v2
- After Commit B's honest errors, testing showed ID Sigs fails at the **image fetch** even though the cover `<img>` thumbnail loads fine (admin: `HTTP 503` on Amethyst #1; test-guard: `network error` on Micronauts #11). The thumbnail and the base64 fetch use the **same** `photoUrl` (mismatch ruled out). **Root cause = cross-origin CORS:** `<img>` display is CORS-exempt; `fetch()→blob()` is enforced, and `img.slabworthy.com` doesn't reliably return `Access-Control-Allow-Origin` for the page origin (+ the uncached fetch hits the R2 origin → 503). Two errors, one root (cache/CORS state). **Preferred fix = server-side image fetch** in `/api/signatures/v2/match` (accept `comic_id`/URL; R2 SDK or `slab_guard_cv._download_image`). Captured in `docs/technical/SIGNATURES_V2_DESIGN.md` (build-checklist item 7 + new "Image-fetch (CORS)" section). **NOT a launch blocker** (ID Sigs is coming-soon / unreachable from upload).
- Corrects the Session 104/105 "response.ok decode" framing: the `response.ok` gap was real and is now **fixed** (Commit B); the *remaining* failure is **CORS**, a separate layer.

### QUEUED FOLLOW-UPS (captured in TODO; none July-21 blockers)
- **"0 used" usage meter:** `account.html` reads the dead `valuations_this_month` (always 0); reconcile to the live `gradings_this_month` — freemium pass.
- **Stale PLANS booleans:** `export` / `api_access` / `ownership_certificates` still read `true` for some tiers but are read by nothing — trimmed from the PAGE; tidy the dead config later.
- **Freemium upgrade-prompt mechanic:** only paywall that fires in normal use is the 4th Slab Guard registration; the grading-cap over-limit returns **429 with no upgrade CTA**. Decide the conversion moment(s) and wire prompts.
- **Dealer webhook hardening (optional):** `handle_checkout_completed` still accepts any plan string; harmless post-Commit-D (no route starts a Dealer checkout), tidy later.

### NEXT SESSION — queued
1. **Section E — billing end-to-end (the HARD launch gate)** — likely the opener. ⚠️ Stripe Checkout footgun: **never** run real Checkout/portal as a `test-*` account (writes `stripe_customer_id`, lets webhooks clobber the tier). Deserves a fresh, focused block.
2. **Section F — mobile + load.**
3. Still open from earlier: ~30s comic-ID wait (staged-progress messaging is the committed fix; speedup parked, conditional on not costing accuracy); **DELETE-confirm** must-fix; **comic-detail-view** decision (build or de-clickify); admin Feedback ~100-char truncation; CGC cost-sourcing investigation; year/edition comp-key gap (post-launch).
4. **Signatures v2** build when authorized (design doc — now includes the CORS server-fetch fix).
- **Cleanup when confident:** drop `_bak_*_20260615` snapshot tables; optionally disable r2.dev.

---

## Session 105 (Jun 16, 2026) — Identification fix SHIPPED; signature auto-fire removed (re-grade hang gone); Commit 2 resilience queued

**Built draft-for-review; Mike ran all git/deploy/purge/smoke-test. Read LESSONS + cross-project at open.**

### 1. Identification trustworthiness — SHIPPED & VERIFIED LIVE (the #1 launch gate)
- **Extraction flip (Haiku→Sonnet):** `comic_extraction.py` `_run_vision_pass` tier `'haiku'`→`'sonnet'`; the `/api/extract` cost-log model label moved with it (`routes/grading.py` → `get_model('sonnet')`) so per-extract cost attribution stays accurate. **VERIFIED:** Sonnet reads **Absolute Batman #19** (title no longer truncated, issue correct) and **Atari Force #4** (was #2 under Haiku) where Haiku failed.
- **Honesty gate:** always-visible, pre-filled, editable ID field (Title/Issue/Publisher/Year) replaces the "✓ Identified" checkmark; new `syncIdentityFields()` flows edits into both the grade request and valuation with NO Save click; removed the `|| '1'` issue default; client maps `'?'`/null/undefined → empty. **Server belt:** `/api/sales/valuation` returns `{issue_required:true}` (HTTP 200, no FMV) on empty/sentinel issue instead of omitting the issue filter and blending all issues into one confident FMV. Grade still shows; FMV/ROI render "—", verdict "ISSUE # NEEDED". Happy path verified on **mobile** (Atari Force #4 → editable field pre-filled → real valuation).

### 2. Signature auto-fire REMOVED — re-grade hang ROOT-CAUSED & FIXED
- **Read-only investigation (multi-round; the test beat the first trace):** the "re-submit identical photos → spins ~5 min → 'Could not identify'" bug was **NOT** image-identity/dedup. The extract path is stateless on content; moderation (Rekognition, no cache) and image-hash logging ruled out. **Root cause:** every successful grade auto-fired `runSignatureCheck` fire-and-forget → the v2 **Opus** orchestration (3 sequential passes, already serialized for a rate-limit constraint). Resubmitting identical photos = the *fastest possible next grade* → its extract fired while the prior grade's Opus job was still consuming the Anthropic rate budget → backoff (extract client had no timeout/retries, fetch had no AbortController) → ~5 min → `APITimeoutError`, mislabeled "Could not identify." A *different* second comic is slower to set up, so its job had finished — which is why A→B worked but B→B-resubmit hung. **Wait-test confirmed:** grade B, wait ~10 min, resubmit identical → WORKS.
- **Fix (Commit 1, `app.html` only): disconnected the post-grade auto-fire call.** Surgical — `runSignatureCheck`, the `gradeReportSignature`/`signatureInfo` panel, `signature_orchestrator.py`, the entitlement gate, and `routes/signatures.py` are ALL preserved (ready for a user-initiated control later). **VERIFIED LIVE:** quick re-grade no longer hangs.
- **Blast radius confirmed:** the Opus job runs only for **Guard/Dealer/admin** (Free/Pro get an instant entitlement 403 — zero Opus work). Mike's account triggered it as **admin**. Normal Free/Pro users would never hit the hang.

### 3. Docs + read-only findings
- **`docs/technical/SIGNATURES_V2_DESIGN.md` — committed.** Deferred signature design: decoupled (collection-based) user-initiated delivery; **detection gate** (mirror `routes/signatures.py` Step-1 "no signatures detected" → abstain at 0 — the REAL false-positive fix + a cost saver, NOT abstain-on-zero-prefilter); confidence-verify UX; tier-gated visibility; threshold alignment (frontend 0.40 → server floor 0.50); multi-sig later.
- **Signature false positive** (Alex Ross on unsigned Absolute Batman #19) root-caused: the v2 orchestrator has no "is a signature visually present?" step (pre-filter is era/publisher *creator* narrowing, not detection), and the frontend show-threshold (0.40) sits below the server's honest match floor (0.50) → 0.40–0.50 "tentative named artist" band renders as "Signature Detected." Both captured in the v2 doc.
- **Year/edition is NOT in the valuation comp-query key** — `/api/sales/valuation` filters on title+issue+issue_type only; `year` affects only the CGC fee tier + the no-data fallback estimate, never comp selection. Same root as X-Men #1 edition blending. Architecture item, post-launch.

### PENDING — Commit 2 (extraction resilience), QUEUED next session
- Currently **OUT of the working tree** (Mike took Commit 1 alone first). Re-apply next session for review: `comic_extraction.py` client `timeout=30.0, max_retries=1`; `app.html` `/api/extract` AbortController (75s) + honest "Our identifier is busy right now" copy on backend-timeout/abort (not "Could not identify"). Insurance against future contention/load now the auto-fire source is gone — **not urgent.** Mike reviews → commit → deploy → purge → verify a forced timeout fails cleanly in ~30-60s with the honest message.

### NEXT SESSION — queued
1. **Re-apply Commit 2** (resilience) draft-for-review.
2. Launch-readiness still open: readiness D (tier gates) / E (billing — ⚠️ Checkout footgun) / F (mobile+load) UN-RUN; DELETE-confirm must-fix; comic-detail-view decision; admin Feedback comment truncation; CGC cost-sourcing investigation; ID Sigs image fetch/decode bug (separate from the hang — still open); year/edition comp-key gap (post-launch).
3. Signatures v2 build when authorized (see design doc).
- **Cleanup when confident:** drop `_bak_*_20260615` snapshot tables; optionally disable r2.dev.

---

## Session 104 (Jun 15, 2026) — R2 migration shipped; model audit; identification plan of record; Section C readiness

**Back from Napa. Big day — multiple read-only briefs + one live migration (run by Mike). All work below is captured in `TODO.md` (🚦 launch-readiness section) and the `project_slabworthy_state.md` memory; this is the narrative.**

### 1. R2 custom-domain migration — DONE & VERIFIED (Mike executed the runbook)
- `img.slabworthy.com` attached to the bucket (Active, SSL auto-provisioned); bucket CORS policy added; `R2_PUBLIC_URL` flipped on Render to `https://img.slabworthy.com` (no trailing slash). Data rewrite ran on all 5 tables holding absolute `pub-c8c9…r2.dev` URLs (single prefix → clean REPLACE); straggler check = 0. Final counts: creator_signatures 1, collections 26 (jsonb), signature_images 207, market_sales 3,818, ebay_sales 50,493 (col = `r2_image_url`).
- **VERIFIED LIVE:** covers load with `Cf-Cache-Status: HIT` (edge cache = the spike insurance is real). Old **ID Sigs CORS+503 image-fetch blocker is FIXED.**
- **Ground-truth divergences:** Postgres is **PG 18.3** (not 16) → DBeaver's pg_dump 17 refused it, so the file-level dump was **skipped**; backup = in-DB snapshot tables only. **`_bak_*_20260615` tables STILL EXIST** (rollback source; drop after a few days clean). **No `.dump` file. r2.dev left ENABLED** as a safety net. Runbook committed: `docs/technical/R2_CUTOVER_RUNBOOK.md`.

### 2. Model-string audit (Sonnet 4 retired June 15) — NO LIVE BREAK
- All production call sites route through `models.py`. Grading + extraction's tier resolution use `call_with_fallback`; grading is on **`claude-sonnet-4-6`** (safe — NOT the retired `claude-sonnet-4-20250514`, which only survives in archived `.patch` files + comments). SW already migrated 2026-06-06; the dependency monitor caught it (it genuinely polls `deprecations.info` + emails on state-change).
- **Resilience gap logged (not urgent):** 8 of 12 model call sites pass static constants (`model=SONNET`/`OPUS`/etc.) with NO fallback (Chrome vision, signature v1/v2, Slab Guard CV, eBay gen, admin) — they'd break with no auto-recovery if a head string retires. Harden later via `call_with_fallback`.

### 3. Identification-honesty review → PLAN OF RECORD (build next session)
- Full analysis: `docs/technical/IDENTIFICATION_HONESTY_REVIEW.md`. Plan: `docs/technical/IDENTIFICATION_FIX_PLAN_OF_RECORD.md` (both committed).
- **Decision 1 — GLOBAL Sonnet extraction:** flip `comic_extraction.py:483` `'haiku'`→`'sonnet'` tier (use the TIER in the existing `call_with_fallback`, not a hardcoded string). Chosen over conditional re-read because the bench showed Haiku **fabricates confidently** (fake barcode 2/3; Sonnet empty 3/3) — a confidence-gated re-read can't catch errors Haiku never admits. Cost ~+1¢/call (~2.9× Haiku), accepted. Caveat: hard-case accuracy gain **inferred, not measured** (`haiku_vs_sonnet_results.json` had only easy books, both 100%).
- **Decision 2 — Honesty gate (#1 launch fix, built regardless of model):** grade still shows (condition observable); **valuation + slab verdict HALT** on absent/low-confidence issue. Objective issue-confidence (`issue=='' ⇒ could_not_determine`; later barcode↔vision agreement — NOT model self-report). Frontend: drop "✓ Identified", show the already-built edit form by default, require issue, gate `/api/sales/valuation`; remove `|| '1'` default (`app.html` ~2554). Server belt: `/api/sales/valuation` must not blend-all-issues on empty issue (`sales_valuation.py` ~228). Ships as ONE change.
- Key mechanism found: barcode-decoded issue is computed (`decode_barcode`) but the merge never writes it to `extracted['issue']` (`comic_extraction.py:663-681`) — parked writeback. Identification runs on Haiku while grading runs on Sonnet (the inversion that motivated Decision 1).

### 4. TODO consolidation + launch posture
- **Launch posture (recorded):** public beta = **GATED/BATCHED** (keep `require_approved` + waitlist + beta codes, admit in waves). HARD gates = billing E2E + valuation/identification honesty; core-flow/mobile buffered by gated intake.
- TODO.md now has a single 🚦 launch-readiness section: identification build, CGC cost-sourcing investigation (read-only, not started), readiness D–F, ID Sigs, resilience gap, polish items.

### 5. Section C readiness (collection mgmt) — run tonight
- **ID SIGS SCOPE GREW (priority BUMPED):** earlier "cosmetic messageToast" framing was wrong. ID Sigs now throws **"Image decode failed" INSTANTLY on multiple comics** — dies UPSTREAM at the image fetch/decode. **Leading hypothesis:** `fetchImageAsBase64` (`js/utils.js:359` area) never checks `response.ok` → base64-encodes a non-image (error/403/redirect/empty) response → instant decode failure regardless of CORS. **Read-only investigation queued** (confirm response.ok gap + what the fetch returns now + whether it builds the right `img.slabworthy.com` URL). Guard/Dealer PAID feature → must work before those tiers launch.
- **MUST-FIX before public:** DELETE (trash icon) has no confirmation/undo — data-loss trust-breaker (mobile mis-tap).
- **DECISION:** comic detail view not built — row looks clickable but does nothing → reads "broken." Build it OR neutralize the affordance (min fix = stop implying it exists).
- **Verified working:** covers, sort/filter/search, Slab Guard reg, eBay (saved-item) + Whatnot gen, Edit MY VAL. Readiness D (tier gates), E (billing — Checkout footgun), F (mobile+load) still UN-RUN.

### NEXT SESSION — queued (Mike says go; Claude drafts, Mike runs all git/deploy)
1. **Read-only ID Sigs fetch/decode investigation** — confirm the `response.ok` gap / URL construction; report before any fix.
2. **Identification build** — draft extraction-flip (`comic_extraction.py:483`) + honesty gate as ONE file-specific diff for review.
3. Other launch-readiness: CGC cost-sourcing investigation; DELETE-confirm; detail-view affordance; readiness D/E/F (careful with E — Checkout footgun); polish (Slab-Worthy-twice/blank-image/early-thumbs, "which photo", duplicate link); resilience hardening.
- **Cleanup when confident:** drop `_bak_*_20260615` snapshot tables; optionally disable r2.dev.

---

## Session 101 (Jun 10, 2026) — Batch 8 shipped + vision-gate fix; capture resumed

**Shipped + verified live:** (1) Vision-gate entitlement fix (`routes/billing.py`) — admin-default-bypass
with `X-View-As-Tier`/`?view_as=` override + plan-string normalization/WARNING-log (root cause:
`check_feature_access` ignored `is_admin`). Test accounts now exist: `test-pro/guard/dealer@slabworthy.test`
(active tiers, non-admin). (2) **Batch 8** (Session 100 work) FINALLY committed + deployed — prod had been
running pre-Batch-8 matching under the Batch 7 deploy. Verified live via the `issue_type` discriminator:
plain "X-Men #1" ≈ $28 / 111 sales vs Giant-Size "X-Men #1" ≈ $5,345 / 128 sales (contamination gone).
(3) Repo hygiene: `.gitignore` now ignores `.env`; dirty-tree docs committed.

**CAPTURE STATE (corpus-growth assumption — keep current):** eBay capture has **resumed** (was stalled
~Apr–May). Now running at **240 results/page** (was ~60 while signed out) ≈ **4× depth per pull**. Cumulative
synced **~45K+**; net-new ~**70–75%** vs dupes per deep pull. So the corpus is growing again and denser per
title — re-measure distribution fresh rather than reusing the ~6,357 queryable-graded-comps figure.

**Confirmed (read-only):** core valuation flow (grade→value→verdict→save→collection) is corpus-powered via
`/api/sales/valuation`; live `/api/valuate` only backs hidden `display:none` surfaces. Read-only DB access:
`DATABASE_URL_RO` in `.env` (`do_readonly` role).

**Queued next:** confidence-field inventory (`/api/sales/valuation` + `/api/sales/fmv` already return
`confidence`/sample-size/`low_confidence`) → design the count-plus-dispersion High/Medium/Low label against
the re-measured (denser) corpus. Parked: 240-capture confirmation, CP-2 billing E2E, mobile testing.

---

## Session 100 (Jun 8, 2026) — Batch 8: series-type qualifier plumbing + qualifier-precise valuation matching

**STATUS: code complete, WIRED + verified end-to-end, NOT committed (checkpoint hold for Mike's review).**
Files: NEW `title_matching.py`; `routes/sales_valuation.py` (6 query sites + `issue_type` param, both
endpoints); `app.html` (display composition + send `issue_type`); NEW `docs/technical/EXTRACTION_ROBUSTNESS_NOTES.md`.
Mike runs all git/deploy/purge (L-SW-2026-001).

**Problem:** qualifiers (Giant-Size/Annual/Special) read into `issue_type` but orphaned; display +
`/api/sales/valuation` used bare `title`; and the `parsed_title LIKE` fallback BLENDED books (X-Men #1
query mixed 1991 + 1963 + Giant-Size → one median). Corpus stores qualifiers cleanly in `canonical_title`
('Giant-Size X-Men' = 112 rows) → app-side plumbing + matching precision, no backfill.

**Solution — `title_matching.py` (single source of truth, no Flask dep):**
- `compose_qualified_title(title, issue_type)` — **per-qualifier position**: Giant-Size/King-Size =
  PREFIX, Annual/Special = SUFFIX. ("X-Men"+"Giant-Size"→"Giant-Size X-Men"; "Star Wars"+"Annual"→
  "Star Wars Annual"; Regular/""→bare.)
- `qualifier_title_clause(exact_col, like_cols, title, issue_type)` — exact normalized canonical match
  OR a qualifier-GATED LIKE fallback. Qualified query requires its qualifier token; plain query excludes
  ANY qualifier. Hyphen/space normalized on both sides (`coalesce→lower→hyphens→collapse`), so
  'Giant-Size'≡'Giant Size'. **COALESCE null-safety** (caught at checkpoint — NULL canonical was silently
  dropping legit plain rows; control fell 203→179, fixed → 203).

**Wired:** server-side composition/matching in both endpoints (4 valuation queries + 2 fmv queries),
`issue_type` request param on both. Frontend composes for DISPLAY only (`composeQualifiedTitle` JS mirror)
and SENDS `issue_type` to valuation (title stays bare; server composes). `js/grading.js` legacy
`calculateGradingRecommendation` is OVERRIDDEN by app.html inline (line 2212) — not plumbed (dead path).

**Security fix (folded in per Mike, pre-public-signup):** the AI-read title/issue/publisher/year went into
`innerHTML` UNescaped in the extraction-display flow (pre-existing; the line was touched here). Added an
`escAttr()` helper (quote-safe for text AND `value="..."` attribute contexts — the bundled `escapeHtml`
doesn't encode quotes) and applied it to all 10 sinks across both display templates (extract success +
saveEdit/showExtractEditAgain). A crafted cover title (or user-typed title) can no longer inject HTML.

**Verification (read-only RO replica + WIRED endpoints via Flask-stub):**

| key | OLD n / median | NEW n / median | wired valuation graded_fmv | wired fmv raw |
|---|---|---|---|---|
| Giant-Size X-Men #1 | 629 / **$40** | 141 / **$1,500** | **$2,150** | **$1,633** |
| X-Men #1 (plain) | 629 / $40 | 481 / $25 | $750 | $52 |
| Spider-Gwen Annual #1 | 91 / $14.99 | 10 / $54.75 | — | — |
| ASM #300 (CONTROL) | 203 / $360 | **203 / $360 ✅** | 205 (unchanged) | 208 (unchanged) |

(OLD shows the bug: Giant-Size and plain X-Men were identical 629/$40 because both sent bare "X-Men".)

**⚠️ KNOWN LIMITATION (logged per Mike):** the qualifier detector is a COARSE regex
(`giant size|king size|annual|special`). A real series literally named with one of those words (e.g.
"Giant Days", a standalone "Special") could be over-excluded from an unrelated plain query. Control
unchanged → not biting in practice; first place to look if a weird title misfires later.

**Captured for the record (NOT this batch):** plain "X-Men #1" is STILL a year/edition blend (1963 key +
1991 Jim Lee + editions share the exact title). Batch 8 fixed the QUALIFIER collision, not YEAR/EDITION.
$25/$750 is not the final answer — next-layer disambiguation by year/era. Logged in
[EXTRACTION_ROBUSTNESS_NOTES.md](../technical/EXTRACTION_ROBUSTNESS_NOTES.md).

### Open / watch (Batch 8)
- **Checkpoint hold:** verification agent + this writeup are the pre-commit review. Nothing committed.
- **Purge IS load-bearing** — `app.html` changed. Deploy (backend: sales_valuation, title_matching) + purge.
- Post-deploy: value Giant-Size X-Men #1 live → Bronze-key FMV with its own comps; plain X-Men #1 → no
  Giant-Size; control ASM #300 → usual number.

## Session 99 (Jun 8, 2026) — Batch 7: decouple quality gates + surface real errors

**STATUS: code complete, verified, NOT committed.** Files: `routes/fingerprint_utils.py`,
`routes/grading.py`, `app.html`. Mike runs all git/deploy/purge (L-SW-2026-001).

**Root cause recap (DO's prior trace):** Giant-Size X-Men #1 = a 394×572 eBay cover hit the
pre-vision quality gate (`GRADE_QUALITY_MIN_DIMENSION=400`) and was rejected by 6px — vision model
never called — and the frontend showed a generic "Could not identify comic automatically." Confirmed
from `request_logs`: most recent `/api/extract` = HTTP 400 "Photo is too small (394×572px)".

**Task 1 — decouple the gate by purpose (🔴).** `check_photo_quality_base64(base64_data, purpose='grade')`
now takes a purpose: `extract` uses a lenient floor (`EXTRACT_QUALITY_MIN_DIMENSION=250`), `grade`
keeps the strict `400`. Also returns measured `width`/`height`. `/api/extract` passes `purpose='extract'`;
`/api/messages` + `/api/grade` pass `purpose='grade'`. Verified with a real 394×572 JPEG: **extract
ok=True, grade ok=False** with message "This photo's too small for an accurate grade (394×572px)…"; a
140×200 image still fails extract. So a legible eBay cover now identifies the book but is correctly
held back from grading.

**Task 2 — honest grade-time UX (🟡).** When `/api/grade` returns 400 `quality_fail`, app.html now shows
an amber "we identified the comic, but need a larger photo to grade it accurately" state (with the book
title from `extractedData` + the backend's tip), instead of a red "Error/Failed". Does NOT grade at
unreliable quality. Check lives at grade-time using the gate's dimension data (grade endpoints now also
return `width`/`height`).

**Task 3 — stop swallowing the real error (🟡).** `extractComicData` previously threw on `!response.ok`
before reading the body, so quality rejections showed the generic line. Now it reads the body first and,
when `quality_issue`/`quality_fail` is set, surfaces the backend's real `quality_message` + `tip`.
(Same swallowed-error pattern fixed in signup/Batch 6.)

**Bonus fix (from review):** the grade flow read the Response body twice on a non-`monthly_limit` 429
(body can only be consumed once → real error lost). Restructured to read the body ONCE and reuse it
across the limit/quality/error/success branches.

**Verification:** real-image gate test (above); `node` syntax check of app.html inline scripts (0
errors); `py_compile` clean. code-reviewer agent: the double-read was the one critical item — **fixed**;
scopes/field-names/floors confirmed correct. Noted latent (accepted, not active): backend quality
strings are interpolated into innerHTML — currently server-static (dimensions + fixed tips), no
user-input path; revisit if message text ever includes user content.

### Open / watch after deploy (Batch 7)
- **Purge IS load-bearing** — `app.html` changed (Tasks 2 & 3). Deploy (backend: fingerprint_utils,
  grading) + purge (frontend).
- Headline live check: re-run the 394px Giant-Size X-Men #1 cover → should now **identify** (reach the
  vision model, return a title); a genuinely small cover → identifies, then at grade shows the honest
  "too small to grade — upload larger" message; a true quality reject → shows the precise backend
  message + tip, not the generic line.

## Session 98 (Jun 8, 2026) — Batch 5: valuation date-filter fix + confidence-labeling audit

**STATUS: code complete, verified read-only against prod corpus, NOT committed.** One file:
`routes/sales_valuation.py`. Mike runs all git/deploy (L-SW-2026-001).

**RECONCILIATION (corrects an earlier overstatement of mine).** The stall was REAL — the audit was
right. Capture is MANUAL (Mike gathers by hand): created_at histogram shows 24,629 rows (Feb) + 13,681
(Mar), then **ZERO in Apr and May**, then a **42-row revival on Jun 6** (Mike resumed this weekend). My
first-pass claim that "capture is current" was wrong — I over-read `max(created_at)=2026-06-06` as
healthy capture when it's a tiny revival after a real ~2-month gap. The audit's OTHER findings ALSO hold
against current data: shallow distribution = **79.1% single-sale, 95.5% <5 comps** (audit said 75% /
94.5% — confirmed, slightly worse); **Whatnot-dark** = market_sales is **19.7%** of the 47,750 corpus.
So the audit is trustworthy; the only "discrepancy" was timing (audit = pre-revival, my read = post-).

**Task 1 — date filter `created_at` → sale date (6 queries) + fmv window 90→180.** All six window
filters now use `COALESCE(sale_date, created_at)` (ebay) / `COALESCE(sold_at, created_at)` (market) —
4 in `/api/sales/valuation`, **2 in `/api/sales/fmv`** (brief said "4"; there were 6). COALESCE =
documented explicit NULL fallback. Plus the fmv default lookback widened **90→180 days** (Mike's call):
sale-date-filtered 90d is too sparse; 180d restores healthy samples without reaching stale pricing.
Before/after comp counts (read-only prod RO replica):

| key | 90d OLD | 90d NEW | **180d NEW** | 365d NEW |
|---|---|---|---|---|
| X-Men #1 | 172 | 106 | **592** | 670 |
| Batman #1 | 159 | 102 | **627** | 737 |
| Amazing Spider-Man #300 | 51 | 42 | **187** | 210 |
| Incredible Hulk #181 | 42 | 23 | **134** | 145 |

(Why the fix matters: the Feb–Mar bulk has created_at within ~90d but sale_dates spread over time, so the
old created_at-90d window counts stale sales as "recent"; sale-date-90d is honest but sparse → 180d is
the sweet spot. And once the Feb–Mar captures age past 90d created_at with capture stalled, the OLD
filter would serve fallback for the WHOLE corpus — the sale-date filter is what keeps real comps flowing.)

**Task 2 — confidence-labeling audit (investigate + low-risk wiring).** Findings: **in-app is fine** —
`/api/sales/valuation` returns `confidence` (exact_count/total_graded → high/medium/low/very_low),
app.html maps `very_low→"Limited"`, and a single-sale key resolves to very_low and always shows the
label alongside any point estimate (+ `estimated` note on the fallback). **Gap = the Whatnot extension
via `/api/sales/fmv`**, which returned **no confidence field at all** — just tier point-estimates (a tier
`avg` can be one sale, rounded to the cent) with a bare count → false precision. **Low-risk wiring fix
(done):** `/api/sales/fmv` now returns `confidence` / `fmv_sample_size` / `low_confidence`, computed from
the count of sales in the tier the FMV was actually priced from (thresholds 10/5/2), on both the main and
no-sales-fallback returns. Verified on real tier counts: X-Men#1@9.4 (16)→high, Batman#1@9.4 (6)→medium,
Hulk#181@9.4 (4)→low, a real 1-sale key→very_low. **FLAGGED for Mike (NOT built — bigger):** the Whatnot
overlay still has to *render* this new signal (a "Limited data" badge); that's an extension UI change +
republish, his call.

**Verification:** read-only harness against prod RO replica (`DATABASE_URL_RO` from `.env`, no writes);
code-reviewer agent — **no critical/important blocking issues** (COALESCE columns match SELECTs, vars
initialized, `used_tier=None` safe, valuation confidence untouched). Reviewer flag (out of scope, NOT
touched per brief): future-dated `sale_date` rows now pass the window — best fixed with a `sale_date <=
NOW()` guard in the eBay scraper at ingest, not here.

**Out of scope / untouched:** capture pipeline, valuation math, sales-table writes.

### Open / watch after deploy (Batch 5)
- **Purge: NOT load-bearing** — backend-only (`routes/sales_valuation.py`); no `js/`/frontend change.
  Render deploy only.
- Headline live check post-deploy: value a well-covered key (X-Men #1 / Batman #1) — real FMV +
  confidence band; fmv now uses a 180-day window.
- **Batch 5B (approved by Mike, separate — extension code + republish):** (1) Whatnot overlay renders the
  new `low_confidence`/`confidence` signal as a "Limited data" badge; (2) ingest-time `sale_date <= NOW()`
  guard in the eBay scraper (future-dated rows now pass the sale-date window).
- Bigger picture: capture is manual and currently only barely revived (42 rows Jun 6); the date-filter
  fix uses correct semantics but does NOT substitute for resuming real capture.

## Session 97 (Jun 8, 2026) — Batch 6: collapse new-user double email-confirm + dead-code cleanup

**STATUS: code complete, verified, NOT committed.** Mike runs commit/push/deploy. Files: `auth.py`,
`login.html` (Batch 6); plus `slab_premium_analysis.py` **deleted** (separate cleanup, staged).

**Cleanup (pre-Batch-6).** Deleted orphaned `slab_premium_analysis.py` — standalone research script
built entirely on eBay's decommissioned Finding API (`findCompletedItems`, dead since 2026-02-05).
Nothing imports it (the live `search_ebay_sold` in `ebay_valuation.py` is a different function). See
`docs/sessions/EBAY_API_SOLD_DATA_INVESTIGATION_2026-06-08.md`. Stale doc ref left at
`docs/technical/ARCHITECTURE.txt:122` (env-var table) — flagged, not yet fixed.

**Investigation (prior turns).** Mapped the full new-user flow: a beta-code stranger hits TWO gates —
beta code → email verification — then auto-login (beta code auto-approves, so the admin-approval gate
is dormant). The "verify twice" friction is **cross-funnel**: a waitlist person confirms their email to
join the list (`waitlist.verified`), then verifies the SAME email again at signup. Verification-email
non-delivery (mikeberry+5) traced to the send path being code-identical to working emails → Resend-side,
not our code; and the send result was being silently discarded.

**Task 1 — pre-verify confirmed-waitlist emails (🔴).** `signup()` now calls `_is_waitlist_confirmed(email)`
(SELECT `verified` FROM waitlist by normalized email, **fails closed**). If confirmed: user created
`email_verified=TRUE`, no verification token stored, **no second email**, JWT returned → frontend
auto-logs-in. ⚠️ **SECURITY CAVEAT (documented in code, [auth.py](../../auth.py) `_is_waitlist_confirmed`):**
email-match trusts a PAST click ("someone controlled this inbox once"), not "this signer controls it now"
— residual email-squatting risk, bounded in beta by the beta-code wall + password-reset recovery.
**REVISIT before public launch** when the beta wall comes down (consider a signed continuity token minted
by the waitlist-confirm click). I surfaced this fork to Mike; proceeded with the brief's primary
email-match approach per his stated risk tolerance.

**Task 2 — auto-approve waitlist signups (🟡).** `auto_approve = bool(beta_code) or waitlist_confirmed`.
Beta-code wall and admin-approval machinery left intact (out of scope). Confirmed-waitlist signup lands
`is_approved=TRUE`, skips the pending panel.

**Task 3 — fix swallowed send result (🔴).** `signup()` now checks `send_verification_email()`'s return.
On failure: returns `email_send_failed=True` + honest message (account still created); frontend shows a
"Couldn't send your email" state with a **Resend** button (hits existing `/api/auth/resend-verification`,
which now also surfaces failures). Failures persisted to a new `email_send_failures` table (lazy-created
once/process) + `logger.error` instead of bare `print`.

**Task 4 — pre-fill + lock email for waitlist invites (🟡, Mike add-on).** The Create Account form asked
invited users to retype the email they'd already confirmed (felt like "they forgot me"; let them type a
DIFFERENT address than the one verified). **Plumbing required** — the verified email wasn't available to
the form (beta codes aren't email-bound; `/api/beta/validate` returned no email). Fix: waitlist-invite
codes already store `note = "Waitlist invite: <email>"` (`/api/admin/waitlist/invite`), so
`validate_beta_code` now parses that and returns `invite_email` + a **server-computed** `email_verified`
(= `_is_waitlist_confirmed`, can't be spoofed client-side). `login.html` pre-fills + locks (`readOnly`)
`#signupEmail`, shows a "✓ Verified" badge (only when server says so), with a **"change it" escape hatch**
(opting out drops pre-verify — correct, it's no longer the confirmed address). Field kept (it's account
identity), not removed. ⚠️ Privacy fix from review: `validate_beta_code` **no longer returns the raw
`note`** (unauthenticated endpoint; note holds the invited email / internal admin remarks). Note wording
gated on `email_verified` so an invited-but-unconfirmed email doesn't falsely read "you confirmed."
Optional follow-up (NOT done): add `?code=...` to the invite link ([admin_routes.py:925](../../routes/admin_routes.py)) so users don't hand-type the code.

**Verification.** Throwaway harness exercised all four signup paths (confirmed-waitlist → no email +
auto-login + approved; unconfirmed-waitlist → normal verify; never-waitlisted+beta → normal verify +
approved; send-fail → honest flag, no token) — all assertions passed. code-reviewer agent: **no critical
bugs**; INSERT placeholders aligned, fails-closed correct, no auto-verify-without-waitlist path, XSS-safe
(textContent). Addressed its one actionable item (moved per-call `CREATE TABLE` behind a once/process
guard).

### Open / watch after deploy (Batch 6)
- **Purge IS load-bearing** — `login.html` (frontend signup flow) changed → Cloudflare cache purge required.
- Post-deploy check: sign up a **fresh, copy-pasted** confirmed-waitlist test email → should NOT re-verify,
  lands in app approved. Then a never-waitlisted email → SHOULD still get a verification email.
- New `email_send_failures` table is lazy-created on first failure; no migration wired. If you want it
  pre-created, add to a startup migration later.
- Still pending (separate batches, NOT this one): Resend monitoring/webhook in `dependency_monitor.py`;
  public-launch gating decision (beta wall + admin gate); ARCHITECTURE.txt:122 stale ref.

## Session 96 (Jun 7, 2026) — Batch 4C: signature 413 chain + grade CGC snap + calibration tooling

Five tasks. Protocol: reproduce → fix → verify → verification agent. **SHIPPED** — Mike committed +
pushed + deployed (Render + Cloudflare purge) + field-verified live 2026-06-07: 413 gone (/v2/match
returns 200), eBay 401 gone on load, grade displays on-scale. HEAD has moved past `8a9e3ae`. Files:
`js/utils.js`, `app.html`, `js/grading.js`, `routes/grading.py`, `routes/signature_orchestrator.py`,
`wsgi.py`, `js/app.js`, `test_haiku_vs_sonnet.py`, `test_grading_consistency.py`.

### ⚠️ Open for tomorrow (from Mike's live testing 2026-06-07 — do NOT act tonight)
1. **Spinner orphan on `matched:false`.** `/v2/match` returns 200 with a correct no-match (Part A
   floor working), but the client only handles error + confident-match — the successful-no-match case
   orphans the "Checking for signatures…" spinner. Fix: on `matched:false`, render the `message`
   field and clear the checking state. (app.html `runSignatureCheck` + js/utils.js `identifySignaturesV2`
   / collection.js consumer.)
2. **`raw_grade` not observed in the live `/api/grade` response** (Mike saw only `grade:7.5`). I added
   `result['raw_grade']` in `routes/grading.py` before `jsonify(result)` — VERIFY tomorrow where it
   actually lands (response field name / serialization / whether the inspected payload was the grade
   object). Calibration (task 4) needs raw QUERYABLE → if it's not a DB column, **adding one is the
   prerequisite** (this is the gap, not the response field).
3. **Signature MATCHING never actually tested this weekend.** All of Mike's test comics have PRINTED
   credits, not hand-signed autographs, so only the REJECTION/no-match path was validated. The
   confident-match path is unverified. Mike has a reframe coming tomorrow.

**Task 1 — signature match 413 (🔴 root cause found).** Client posted the cover base64 as a multipart
TEXT field (`formData.append('image', base64)`); Werkzeug 3.1.3 caps non-file form fields at
`max_form_memory_size` = **500 KB** and raises 413 during form parsing — AFTER the entitlement gate
(matches "gate passed, died on body size"). Server already reads `request.files["image"]` (a file), so
the field upload was also contract-wrong. Verified: 2 MB field @500 KB → 413; file part @500 KB → 200.
Fix: (a) `resizeBase64ToJpegBlob()` in `utils.js` resizes to 1568 px long-edge (Anthropic's vision cap
— no model-visible loss) and returns a JPEG **Blob**; `identifySignaturesV2` + app.html
`runSignatureCheck` append it as a FILE part. (b) `match_signature` accepts a `request.form["image"]`
base64 fallback too. (c) `wsgi.py` sets `MAX_FORM_MEMORY_SIZE=25 MB` as a transitional safety net
(does NOT touch `MAX_CONTENT_LENGTH`, so the JSON multi-image `/api/grade` path is uncapped). Prefer-
shrink honored: full-res cover base64 (~MBs) → ~200–400 KB file.

**Task 2 — orphan spinner (🔴, pairs with 1).** `runSignatureCheck` now wraps the fetch in an
AbortController **120 s timeout** and resolves the "Checking for signatures…" state on EVERY outcome:
403 → hide silently; other non-OK (413/5xx) → "Signature check unavailable"; catch (network/timeout)
→ same. `collection.js` already cleared via `finally` (unchanged). Closes the Friday "flicker" item too.

**Task 3 — grade CGC snap (🟡, "Defensive + store raw" per Mike).** KEY FINDING: the LIVE app.html
path (`/api/grade` → `grading_engine.compute_grade` → `snap_to_cgc_grade`) ALREADY snaps and retains
`raw_score`; the override's catch shows Error (no fallback), and grading.js's `/api/messages`
comprehensive grade is overridden/unused by app.html. So no current live path can show 7.6 (the
5-book grades 7.5/6.0/8.0/5.0 confirm). RESOLVED: the 7.6 was Mike's typo — a re-run displayed 7.5;
production snapping confirmed working, drift hypothesis dead, repo read was correct. Final shape
per Mike: (a) `api_grade` re-snaps `final_grade` via the canonical `snap_to_cgc_grade` (defensive
belt-and-suspenders guard — kept), sets `raw_grade` = unsnapped weighted avg, logs both — the
raw retention has real value for task-4 calibration. (b) the dead grading.js `/api/messages`
comprehensive-grade path was DELETED (replaced with a no-op stub that points to /api/grade), NOT
snapped client-side — confirmed app.html overrides `generateGradeReport` and nothing executes the
stub's body (the step-skip caller at the old line 2050 resolves to the override). No duplicated
grade list anywhere; valuation consumes the snapped `final_grade` (app.html + grading.js paths).
(c) app.html `saveToCollection` sends `raw_grade`. Verified snap: 7.6→7.5, 7.74→7.5, 8.1→8.0,
7.75→8.0 (ties round UP), 0.7→0.5; Python↔JS parity confirmed. NOTE: raw is currently retained via
server LOG + response + save payload; DB persistence of `raw_grade` needs a column (follow-up — not
done, to avoid an unscoped migration).

**Task 4 — calibration tooling + protocol proposal (🟡, measure-don't-fix).** `test_haiku_vs_sonnet.py`
and `test_grading_consistency.py` moved off the retired `claude-sonnet-4-20250514` onto `models.py`
`get_model()` tiers (single source of truth — no future retired-string drift). No prompt changes.
**Proposed measurement protocol for the Sonnet-4.6 grade-lean hypothesis (Mike's call to run):**
  1. Priors = grades already stored in the collection DB (NOT memory). Pull N≥20 books with a stored
     grade + their 4 photos (R2 URLs).
  2. Re-grade each on the current `sonnet` tier (4.6) via `/api/grade` (or the pinned script), 3 runs
     each, recording BOTH snapped `final_grade` and `raw_grade` (raw avoids snap-quantization masking
     the lean).
  3. Report delta distribution: `raw_grade − stored_prior` per book — mean, median, stdev, histogram.
     A consistent +0.3..+0.7 mean across the upright control set ⇒ confirms the ~half-step lean.
  4. THEN (separate decision) calibrate via a prompt nudge or a post-hoc offset; re-measure.

**Task 5 — eBay 401 on load (🟢).** `checkEbayConnection` (`js/app.js`) called `/api/ebay/status`
(which is `@require_auth`) with no token → 401 on every load. Now skips when no `cc_token` and sends
`Authorization: Bearer` when present.

### Verification
- Task 1: Flask/Werkzeug 3.1.3 test — field @500 KB → 413 (repro), field @25 MB → 200 (safety net),
  file part @500 KB → 200 (primary fix bypasses the limit). py_compile + `node --check` all green.
- Task 3: `snap_to_cgc_grade` unit cases + JS parity (above).
- Tasks 2/5: client-side, reviewed (no browser/API here); 4: scripts compile, retired string gone.
- Verification agent (code-reviewer): no critical/important regressions. Latent note (resize assumes
  JPEG bare-base64 — true for all callers; clarified in docstring). Pre-existing (NOT this batch):
  `parse_multi_run_responses` bare `json.loads` → one bad pass 500s the whole multi-run (no partial
  fallback); worth a separate fix.

### Deploy / watch list for Mike
- **Cloudflare Pages purge is LOAD-BEARING:** `js/utils.js`, `js/grading.js`, `js/app.js`, `app.html`
  all changed — frontend must redeploy + cache purge or the 413/spinner/snap/eBay fixes won't ship.
- Render backend: `wsgi.py` (form limit), `routes/grading.py`, `routes/signature_orchestrator.py`.
- Correction to Part B note: app.html DOES use `/api/grade` (its inline override) — `/api/grade` is
  NOT dead. (Part B's "dead" note was from grepping only `js/`, missing app.html's inline script.)
- Post-deploy watch: real sig-check on the failing covers (Amethyst/Micronauts/Invaders) → 200, not
  413; grade displays an on-scale number; no `/api/ebay/status` 401 in console on load.
- Follow-ups surfaced (NOT this batch): persist `raw_grade` to DB (column); `parse_multi_run_responses`
  partial-failure handling; `/api/grade` dead-code cleanup is moot (it's live).

---

## Session 95 (Jun 7, 2026) — Batch 4 Part B: grading-input orientation pipeline

Items 1+2 of Batch 4. Protocol: reproduce → fix → verify → verification agent → STOP (NOT
committed — awaiting Mike). Files: `comic_extraction.py`, `routes/grading.py`, `js/grading.js`
(+ this notes file and the Part A `(c)` doc note still staged, all ride one commit).

**Item 1 — per-photo grading-input normalization (server-side, authoritative).** Grading uses 4
photos: front/spine/back (portrait when correct) + centerfold (legitimately LANDSCAPE — two-page
spread). Repro confirmed: `extract_from_base64` hardcoded `assume_portrait=True` (would force-rotate
a landscape centerfold to portrait), and `/api/messages` (spine/back/centerfold, one image per call)
did ZERO server-side normalization. Fix: new `assume_portrait_for(photo_type)` +
`normalize_for_photo_type()` in `comic_extraction.py` — policy in ONE place: centerfold/center/interior
→ EXIF-only, everything else (incl. unknown) → assume portrait. `photo_type` threaded from the
frontend through `/api/extract` (default `'front'`) and `/api/messages` (popped before forwarding to
Anthropic; absent → skip, preserving the follow-up-chat caller). Backend-first deploy is safe: old JS
sends no `photo_type` → messages-path normalization simply no-ops (never force-rotates an unlabeled
centerfold). Frontend (`js/grading.js`) now sends `photo_type` for all 4 steps — needs a Cloudflare
Pages deploy for full effect.

**Item 2 — 180° low-confidence extraction fallback (server-side).** Repro: a 180° flip is
dimensionally identical, so the dimension-based heuristic can NEVER catch it. Fix: `extract_from_base64`
runs one pass (`_run_vision_pass`); if low-confidence (`_extraction_low_confidence`: unparseable /
model-flagged is_upside_down / not-a-cover / no-title) it re-reads ONCE on a 180°-rotated copy and
keeps the higher-scoring pass (`_extraction_score`; ties keep pass 1). At most 2 vision calls. Every
retry logged `[VISION CALL #2 — doubled cost]` so the doubled cost is visible. Server is now
authoritative on orientation: the chosen result ALWAYS returns `is_upside_down=False` (pass-2 win sets
`orientation_corrected='180'`), so the grading.js client never re-rotates on top of the server.

### Verification
- Repro harness (real `normalize_orientation_b64`): centerfold force-rotated under old behavior;
  preserved under EXIF-only; 180° flip dimensionally invisible.
- Verify harness drove the REAL `extract_from_base64` with `_run_vision_pass` monkeypatched to scripted
  passes: no-retry on good pass1 (1 call); retry on each low-confidence reason (2 calls, never more);
  better pass wins; not-a-cover pass1 gets a 180° rescue before giving up; flags set correctly. Item-1
  policy + case/space tolerance + landscape→portrait vs centerfold-preserved all pass.
- Verification agent (code-reviewer): 2 real findings FIXED + re-verified — (1) `json.JSONDecodeError`
  from a regex-matched-but-invalid fragment escaped the orchestration and skipped the retry → now
  caught in `_run_vision_pass` (returns None = unparseable → retry); (2) pass-1-kept after an
  `is_upside_down` flag left `is_upside_down=True` → client would redundantly re-rotate → now suppressed
  (server authoritative). Issue 3 (quality gate pre-normalization) assessed NON-issue: the gate uses
  `min(w,h)` + Laplacian blur, both rotation-invariant. Issue 4 informational.
- Live-API JSON (real extraction + grading) is Mike's post-deploy check — no local ANTHROPIC_API_KEY.

### Revenue-path / deploy notes for Mike
- `/api/messages` IS the live grading path (Batch 3 flagged grading-input normalization as needing a
  re-spot-check; this is that change, now authorized). Spot-check a few real grades post-deploy.
- `/api/grade` (the labeled comprehensive endpoint) is DEAD in the live flow — no JS calls it; left
  untouched. Possible separate cleanup.
- Known cosmetic trade-off: for an upside-down FRONT, the server now corrects the READ but does not
  return the rotated image, and returns `is_upside_down=False`, so the client preview may show the
  original orientation (data is correct). Ties into the deferred item 3 (preview). Easy follow-up:
  return the corrected image from `/api/extract`.

---

## Session 94 (Jun 6, 2026) — Batch 4 Part A: Sig-ID gating, barcode, dep-monitor email

Batch 4 split into Part A (correctness/billing/monitoring) + Part B (image pipeline). Part A
COMMITTED + DEPLOYED as `d254309` (pushed to origin/main; Free-tier 403 + seed-email field tests
confirmed live, per Mike 2026-06-07). Part B = items 1+2 (Session 95 above); item 3 preview deferred.

**Item 4 — server-side signature-ID tier gating** (`routes/billing.py`, `routes/signature_orchestrator.py`).
Added `signature_id_per_month` to PLANS (free=0, pro=0, guard=10, dealer=-1) and
`get_signature_id_entitlement(user_id)` (fails CLOSED on DB error/unknown user; admin=unlimited;
paid plans need active subscription). `match_signature` now gates BEFORE the expensive match:
error→503, no_access→403, capped plan over limit→429 (fail CLOSED on usage-read error too),
unlimited→proceed. Replaced the old flat `MONTHLY_SIG_LIMIT=10`-for-all + fail-OPEN logic. Usage
Tier policy per Mike 2026-06-06. NOTE: Mike's log confirmed the earlier "flicker" was UI-only (no
/match fired) → that's on the UI-polish list; this gating stands on code grounds.
  - **Amendment (Mike, pre-commit):** (a) CAP SEMANTICS — the Guard cap counts CONFIDENT matches
    only (top confidence >= LOW_CONFIDENCE_THRESHOLD 0.50). Increment happens AFTER the result is
    known and ONLY for capped plans; no-match/below-floor/error never count; blocked calls (403/429)
    never process/bill. Dealer/admin are NOT counted in the cap column (it never resets for them) —
    their usage is monitored via the per-call `[SigID] match served ... cap_counted=...` log instead.
    (b) NO-MATCH HONESTY — `/v2/match` previously force-matched (returned nearest-neighbour top5 + a
    `low_confidence_match` flag). Now returns `matched: false` + "Signature not in our reference set"
    when top confidence < floor, rather than attributing the nearest neighbour. `matched` is the
    authoritative signal; top5 retained as transparency/candidates. Same no-confident-hallucination
    rule as Batch 3 extraction. Verification agent flagged dealer counter-increment (resolved as
    above — log-based visibility, counter is Guard-only).
    (c) THRESHOLD CONFIG — `LOW_CONFIDENCE_THRESHOLD` now reads `SIG_LOW_CONFIDENCE_THRESHOLD`
    (default 0.50), so floor + cap boundary retune via env, no code change. Marked PROVISIONAL —
    calibrate at the signature-v2 accuracy re-measurement (87% target). Single-definition property
    preserved (one constant feeds both the no-match floor and the cap boundary). Cap semantics
    verified locally: Guard no-match → counter unchanged; confident → +1 (true RETURNING count);
    9/10 + no-match + confident → ends at 10, not 11.

**Item 5 — barcode decoder addon-None** (`comic_extraction.py`). `decode_barcode` now runs ONLY when
`barcode_source == 'pyzbar'` (a scanner-confirmed addon), never on the vision model's guessed
`barcode_digits`. Without a confirmed addon: keep main UPC (series ID) only, mark
`barcode_source='vision_unverified'`, don't derive issue/printing/variant. Fixes false decodes like
Amethyst Annual #1 (no post-2008 add-on) → "issue 251".

**Item 6 — dep-monitor emails on state change, not every boot** (`dependency_monitor.py`).
`_send_alert_email` dedups against a self-creating DB table `dependency_alerts` (CREATE TABLE IF NOT
EXISTS — no migration needed) so a permanent state (eBay `unmonitorable`) emails once, not on every
Render restart. Prunes resolved keys so recurrence re-alerts. Falls back to in-memory `_emailed_keys`
(now also pruned) if DB unavailable.

### Verification
All three verified locally: entitlement across all tiers incl. fail-closed; barcode gate (pyzbar
decodes, model-guess doesn't); dep-monitor new→email, reboot→silent, resolved→prune, recurs→re-alert
(DB + in-memory paths). Verification agent: 1 false positive (claimed tz-naive/aware datetime crash —
code compares .year/.month ints, no datetime comparison; matches existing valuations/grading caps),
2 real findings FIXED (Dealer usage log always said used=1 → now RETURNING true count; in-memory
fallback didn't prune → now does).

### Files Modified (Batch 4 Part A)
- `routes/billing.py`, `routes/signature_orchestrator.py`, `comic_extraction.py`, `dependency_monitor.py`

### Still to do
- Part B: item 1 (grading-input normalization, per-photo) + item 2 (CCW 180° low-confidence fallback).
- Deferred: item 3 (preview — only if on-device still sideways). UI-polish: sig-section flicker.

---

## Session 93 (Jun 6, 2026) — Batch 3: Extraction & Orientation Regression

Four items (reproduce → fix → verify → agent → STOP). NOT committed/deployed — awaiting Mike.
Batches 1 (`cf9c3a2`) and 2 (`7d8aad7`) already deployed.

1. **Orientation pipeline (extraction) — root cause + fix.** `app.html`'s `extractComicData`
   (line 1789) sends the RAW front photo to `/api/extract` with no normalization, bypassing the
   client EXIF/canvas code (utils.js `processImageForExtraction`, grading.js
   `processImageWithOrientation`). Server-side did zero normalization. The Anthropic vision API
   ignores EXIF and reads raw pixels → 90deg-rotated covers read as garbled/hallucinated titles
   (Hercules→"Power of The Force", Invaders→"Marvel Comics #60", Atari Force→"Sgt. Rock #5").
   - **Fix (authoritative, server-side):** new `comic_extraction.normalize_orientation_b64()` —
     (a) `ImageOps.exif_transpose` (handles rotated-WITH-EXIF, the real phone→app.html upload, with
     correct direction + strips tag); (b) `assume_portrait` heuristic: if still landscape after EXIF,
     rotate 90deg CCW to portrait (handles hard-rotated NO-EXIF images, e.g. Google Photos
     re-exports, which the test fixtures turned out to be). Runs before BOTH barcode scan and the
     vision call; fails loud on undecodable input; tolerates data-URL prefix. Extraction calls it
     with `assume_portrait=True` (front cover is always portrait).
   - **Key discovery:** the supplied test fixtures (FromGooglePhotos) are landscape `4080x3072` with
     EXIF orientation=1 (tag stripped, rotation NOT baked) — so `exif_transpose` alone was a no-op on
     them; that's why the portrait heuristic was needed. Real phone uploads carry EXIF and are fixed
     by part (a). Direction empirically CCW (verified by rendering all 3 covers).
2. **Extraction model routing.** Extraction still correctly uses the `haiku` tier
   (`call_with_fallback(_client, 'haiku', ...)`); Batch 2 did NOT sweep it to Sonnet. Only the
   `/api/extract` usage LOG mislabeled it `SONNET` → fixed to `get_model('haiku')`.
3. **Re-test failing set (acceptance for 1+2).** Could not run a live extraction (no local
   ANTHROPIC_API_KEY; prod still pre-fix). VISUAL acceptance instead: ran the actual
   `normalize_orientation_b64(assume_portrait=True)` on all 5 covers and rendered outputs — all three
   failing covers now upright + fully legible (Atari Force, Hercules: Prince of Power #1, The Invaders
   #41 with 60c price clearly separate from issue 41); controls (Amethyst, Micronauts) untouched.
   Live-API JSON confirmation is Mike's post-deploy check. PROPOSED (not built): add these 5 covers
   as a permanent extraction regression fixture once the pinned-model test scripts are updated.
4. **Mobile 3-photo slab report.** Reproduction in code found NO 4-photo gate: the grading-report
   path requires only the FRONT cover (app.html:2195-2196); "of 4" is a label and "<4" a non-blocking
   warning; FAQ confirms "front required at minimum, proceed with fewer"; git history shows no 3->4
   change. So NOT a code regression in the visible path — likely stale cached JS, a mobile rendering
   issue, or a different flow. Needs a device repro/screenshot from Mike. No code change.

### Verification agent
Ran twice (after core fix, then after the portrait heuristic). No critical/correctness issues.
First-pass finding (data-URL prefix robustness) addressed. Confirmed: no double-rotation, gate
correct, CCW direction matches intent, only the front-cover path uses assume_portrait.

### Items needing Mike's call (NOT changed)
- **Symptom #3 (preview shows un-corrected):** display is separate from the API payload (uses the
  client raw image). Modern browsers auto-orient `<img>` by EXIF, so the raw-with-EXIF preview likely
  shows upright already; if not, return the normalized image from `/api/extract` for the preview.
- **Grading inputs:** brief says "before any API call," but grading is out-of-scope + passed.
  `/api/grade` and `/api/messages` still send un-normalized images. Applying the same normalization
  there would fix grading orientation but changes the revenue-path inputs (re-spot-check needed).

### Files Modified (Batch 3)
- `comic_extraction.py`, `routes/grading.py`

---

## Session 92 (Jun 6, 2026) — Batch 2: Model Migration + Hardening

Three tightly-scoped items (reproduce/establish → fix → verify → verification agent). NOT yet
committed/deployed — awaiting Mike's authorization. Batch 1 (`cf9c3a2`) is already deployed live.

1. **Migrated off `claude-sonnet-4-20250514`** (retires 2026-06-15 — deadline-driven). `models.py`
   sonnet chain → `claude-sonnet-4-6` (the deprecations.info-listed replacement), removed the
   retiring string from both `sonnet` and `sonnet-new` plus the aged `claude-3-5-sonnet-latest`.
   Centralized both grading paths through `models.py` + `call_with_fallback`: `/api/messages`
   (`routes/grading.py`) now ignores any client-supplied `model` and uses tier (default 'sonnet');
   `/api/grade` `run_grading` switched from `create(model=SONNET)` to `call_with_fallback`. Frontend
   `js/grading.js` (2 spots) now sends `tier: 'sonnet'` instead of the hardcoded retiring model.
   Added a thread-safety lock to `_active_index` (the threaded multi-run grading path now mutates it).
   - **Deprecation sweep:** on the Anthropic API, ONLY `claude-sonnet-4-20250514` was on a near
     clock. Other feed hits (3-5-sonnet/Vertex, sonnet-4/Bedrock, haiku-4-5 & sonnet-4-5/Azure,
     opus-4-6/Azure) are OTHER platforms (Vertex/Bedrock/Azure), not our direct Anthropic API.
   - ⚠️ **Revenue path:** grading model changed Sonnet 4 → Sonnet 4.6. Mike should spot-check a few
     real grades after deploy (a live grading call needs ANTHROPIC_API_KEY, only set in prod).
2. **JWT_SECRET fail-loud** (`auth.py`): if unset or == 'change-me-in-production', refuse to start in
   production (detected via Render's `RENDER` env var); in dev, warn loudly and use the dev default.
   ASCII-only messages (L-2026-015 — emoji crashed Windows cp1252 stdout in the dev path).
3. **eBay RSS 403** (`dependency_monitor.py`): diagnosed as site-wide Akamai bot-wall on
   developer.ebay.com (all paths, any User-Agent, incl. from Render). No automatable eBay
   deprecation source exists. Reclassified the eBay check from `error` to `status: unmonitorable`
   (honest degradation, cached 24h, retries daily in case the wall lifts) with manual-tracking
   guidance. `check_all()` still runs all four checks isolated.

### Verification
- Reproduced/established each item first (sonnet call-site grep + deprecation sweep; JWT default;
  eBay 403 with default + browser UA across multiple paths).
- All verified locally: models chains clean + fallback (incl. 8-thread concurrency, no index
  overrun); `/api/messages` overrides old model → 4-6; JWT refuse/warn across prod/dev contexts;
  eBay → unmonitorable; monitor no longer warns about a model we use.
- Verification agent: 3 findings. #2 (thread-unsafe `_active_index`) FIXED (lock + over-advance
  guard). #1 (`SONNET` static constant / dead `_ModelProxy`) — pre-existing, logging-only,
  left as-is (converting risks passing non-str to DB logging). #3 (auth import-raise on Render
  shell) — latent only; scripts don't import auth and Render shell inherits JWT_SECRET.

### Files Modified (Batch 2)
- `models.py`, `routes/grading.py`, `js/grading.js`, `auth.py`, `dependency_monitor.py`

### Still open / follow-ups
- `_ModelProxy` dead code + `SONNET`/`HAIKU` static constants (logging accuracy in
  `/api/valuate`, `/api/extract`) — separate cleanup.
- Frontend `js/grading.js` deploys via Cloudflare Pages (separate from Render). Backend ignores the
  client `model` regardless, so deploy order doesn't matter — but the JS cleanup needs a Pages deploy.
- CLAUDE.md deploy-note fix (auto-deploy unreliable) — spawned as a separate task.

---

## Session 91 (Jun 6, 2026) — Reconciliation + Fixes Batch 1

### What Was Done

Ran a read-only reconciliation pass (`docs/sessions/RECONCILIATION_2026-06-06.md`), then
implemented Fixes Batch 1 (reproduce-before-fix; verified; NOT yet committed/deployed — awaiting
Mike's authorization).

1. **Fixed the dead dependency monitor** (`dependency_monitor.py`). Root cause: `deprecations.info`
   changed its JSON from `{"items":[...]}` to a top-level array, so `check_anthropic()` crashed on
   `data.get("items")` — and because it ran first in `check_all()`, it killed every check (eBay RSS,
   Stripe, and the new eBay account-deletion self-check never ran). Fix: shape-tolerant parsing
   (handles both dict+array, `model_id`/`model_name`), all parsing inside try/except, each check
   isolated in `check_all()` so one failure can't block others, failed checks now surface a loud
   `status: error` entry (with a ~5 min backoff so an outage doesn't hammer upstream).
2. **Hardened the Stripe webhook** (`routes/billing.py`). Was processing events UNVERIFIED when
   `STRIPE_WEBHOOK_SECRET` was unset (forgeable → self-upgrade to paid tier). Now: unset secret →
   500 + refuse; bad signature → 400 + refuse; valid → process. Secret read per-request.
3. **Repointed `/api/signatures/db-stats`** (`routes/signatures.py`) from the stale bundled
   `signatures_db.json` snapshot to the live `creator_signatures` + `signature_images` tables (the
   stale endpoint reported 80/97 vs the live 99/203). Graceful 503 if no DB; backward-compatible
   response keys. The v1 matcher still reads the JSON snapshot — left untouched (separate cleanup).
4. **Documented all env vars** in `docs/technical/ARCHITECTURE.txt` (was 1 of ~32) — name, purpose,
   reading module, unset behavior. Flagged `JWT_SECRET`'s insecure `'change-me-in-production'`
   default (auth.py NOT changed this batch).

### Verification
- Reproduced bugs #1 and #2 first (tracebacks / code-path quotes captured in session).
- All fixes verified locally (monitor: all checks run + isolation + backoff; webhook: 500/400/200
  with no handler calls when rejected; db-stats: 503 + correct aggregation). Ran a code-review
  verification agent; its 3 findings (retry backoff, `none` quality bucket, per-request secret read)
  were all addressed and re-verified.

### Follow-ups surfaced (NOT in this batch — own briefs)
- 🔴 **`claude-sonnet-4-20250514` retires 2026-06-15** (the now-working monitor caught it) — Sonnet
  migration gets its own brief.
- 🟡 **eBay RSS feed returns 403** (`developer.ebay.com/rss/api-status`) — check can't fetch; needs
  a new URL or a User-Agent header.
- 🟡 **v1 signature matcher** still on the stale JSON snapshot.
- 🟡 **`JWT_SECRET` insecure default** in `auth.py` — harden separately.

### Files Modified (Batch 1)
- `dependency_monitor.py`, `routes/billing.py`, `routes/signatures.py`, `docs/technical/ARCHITECTURE.txt`
- `docs/sessions/RECONCILIATION_2026-06-06.md` (new, from the reconciliation pass)

---

## Session 90 (Mar 24, 2026) — Mobile Extraction Fix + Dependency Monitor

### What Was Done

1. **Fixed mobile image extraction** — Three bugs causing extraction failures on mobile:
   - Images now always go through canvas (max 2048px, JPEG normalized) — fixes oversized payloads
   - Rewrote EXIF orientation parser — was bailing early on valid JPEG segments, sending rotated photos uncorrected
   - Added `is_comic_cover` validation to extraction prompt — non-comic photos get a clear error

2. **Fixed Haiku model retirement** — `claude-3-5-haiku-latest` returned 404, broke all extraction. Updated to `claude-haiku-4-5-20251001`. Migrated `comic_extraction.py` from raw `requests.post()` to Anthropic SDK with `call_with_fallback()`.

3. **Built automated dependency monitoring** — `dependency_monitor.py` checks three services:
   - Anthropic model retirements (via deprecations.info)
   - eBay API deprecations (via developer.ebay.com RSS)
   - Stripe SDK version drift (via PyPI)
   - Email alerts + admin dashboard warning banner
   - Runs on every Render health check, cached 24h

4. **Added enforcement rules** — CLAUDE.md now mandates all new third-party services be registered in dependency monitor. Saved as persistent memory.

5. **Consolidated report loading UI** — Replaced 3 simultaneous loading indicators with single animated gradient spinner + cycling status messages. Works above the fold on mobile.

6. **Fixed health endpoint crash** — `dependency_monitor.py` was taking down the `/health` endpoint. Wrapped in try/except, made resend import optional.

7. **Fixed grading report error** — Loading spinner refactor accidentally removed `defectsGrid` variable declaration, causing ReferenceError that showed "Error/FAILED" even though grading succeeded. One-line fix.

8. **Updated MASSE + TheFormOf CLAUDE.md** — Added mandatory dependency monitoring rules to both projects. TFO version includes Layer 2 (client app dependencies) and billable "Managed Updates" service concept.

### Files Created
- `dependency_monitor.py`

### Files Modified
- `js/grading.js`, `comic_extraction.py`, `models.py`, `routes/utils.py`, `routes/admin_routes.py`, `admin.html`, `app.html`, `CLAUDE.md`

### Next Up
- Continue mobile testing (extraction + grading confirmed working)

---

## Session 89 (Mar 11-12, 2026) — Admin Insights + Unified AdminHub Dashboard

### What Was Done

1. **Enhanced Admin Users Tab** — Rewrote `/api/admin/users` to JOIN with collections, comic_registry, request_logs, api_usage, user_feedback tables. Each user row now shows: collections count, slab guard registrations, API calls, AI cost, last activity, top actions breakdown, feedback count/avg. Expandable rows show full detail. Committed and pushed.

2. **Enhanced Feedback Endpoint** — Updated `/api/admin/feedback` to JOIN with collections table via `grading_id`, returning comic title, issue number, grade, and photo URLs alongside each feedback entry. Feedback now shows what comic was being graded when the user left feedback.

3. **AdminHub — Unified Cross-Domain Dashboard** — Built a single-page admin dashboard that aggregates data from both SlabWorthy and MASSE into one view. Located at `C:/Users/mberr/theformof/`.
   - **Dual auth engine**: JWT for SlabWorthy, Supabase SDK for MASSE
   - **Connection dots**: Green/red per-app status in header
   - **Overview tab**: Aggregated stats across all apps
   - **Per-app tabs**: Users, Beta Codes, Errors, Usage, Waitlist, Feedback, NLQ Query
   - **Modular config**: Adding a 3rd app = one config object in the APPS array
   - **Runs locally**: `node serve.js` → `http://localhost:8080`
   - **Future-ready**: TheFormOf placeholder tab (greyed out) already in place

4. **MASSE CORS Update** — Added `localhost:8080` and `127.0.0.1:8080` to MASSE backend CORS whitelist so AdminHub can call MASSE APIs cross-origin. Committed and pushed.

5. **Bug Fixes**
   - Fixed SlabWorthy login URL in AdminHub (`/api/login` → `/api/auth/login`)
   - Fixed race condition where `closeLoginModal()` nulled `loginTargetApp` before the post-login code could use it
   - Fixed `substring()` error on numeric SlabWorthy user IDs (MASSE uses UUID strings)

### Files Created
- `C:/Users/mberr/theformof/index.html` — AdminHub dashboard (~1200 lines, single-file)
- `C:/Users/mberr/theformof/serve.js` — Express static file server
- `C:/Users/mberr/theformof/package.json` — Express dependency

### Files Modified
- `routes/admin_routes.py` — Enhanced `/api/admin/users` with 6 additional SQL joins; enhanced `/api/admin/feedback` with collection/comic context
- `admin.html` — Enhanced Users tab (10 columns, expandable rows, timeAgo, activity chips)
- MASSE `backend/server.js` — Added localhost:8080 to CORS origins
- MASSE `backend/routes/admin.js` — Enhanced `/api/admin/users` with companies, invite_codes, token_usage joins

### Planning Docs
- `docs/UNIFIED_ADMIN_PLAN.md` — Updated to reflect AdminHub is built (Phases 1-3 complete)
- Same doc mirrored in MASSE repo

### What's Next
- **Deploy to Render** — Run `deploy` CLI command to push enhanced admin API endpoints live. The AdminHub dashboard calls the production APIs, so the enriched user data (activity, costs, feedback context) will only show once the backend is redeployed.
- **TheFormOf** — When the 3rd app is built, add one config object to AdminHub's APPS array and it auto-integrates.
- **Phase 4** — Cross-app user matching (same email across apps), unified cost dashboard, cross-app NLQ queries.

### Previous Session
- Session 88 (Mar 8) — Beta User Management: Grading Cap (25/month) + Feedback System + Waitlist Admin + Invite Flow
