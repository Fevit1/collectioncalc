/**
 * VERDICT BASIS — one vocabulary, two forms, one place.
 *
 * WHY THIS FILE EXISTS. The grade report (app.html) and the collection card
 * (js/collection.js) both have to explain WHY a figure is hedged, and they are
 * different surfaces with different data:
 *
 *   LONG form  — app.html, live valuation response in hand. Interpolates five
 *                fields (sameGradeComps, nearbyThin, rawComps, excludedVariants,
 *                gradeLabel) plus fmvMethod and editionPriceRatio.
 *   SHORT form — js/collection.js, a saved row. NONE of those five fields are
 *                persisted on `collections`; only `verdict_basis`, `verdict` and
 *                `roi` are. So the short strings are PARAMETERLESS by necessity,
 *                and that is also their safety: a string that cannot interpolate
 *                a count cannot assert one.
 *
 * The two forms are NOT copies of each other and must never be made into copies.
 * What is shared, and the only thing that needs to be, is BASIS_KEYS — the
 * vocabulary. Two independent lists of these values in two files is
 * L-SW-2026-019 / L-2026-026 waiting to happen: one decision, two edits, and the
 * second one eventually gets missed.
 *
 * ⚠️ EVERY COMMENT IN `basisLong` BELOW MOVED VERBATIM FROM app.html. They are
 * tombstones: each records a wording that was tried, shipped or considered and
 * found FALSE, and why. Re-deriving a disproved wording is exactly what they
 * prevent, so they are load-bearing and they travel with the code. Do not
 * summarise, reflow or "tidy" them.
 *
 * Loaded as a plain global script, same as js/utils.js (API_URL). No module
 * system on these pages.
 */

/**
 * The vocabulary. EIGHT values: seven the server emits today, plus
 * `multi_edition`, which is written ahead of the edition-span unit (see its
 * tombstone in basisLong).
 *
 * Frozen so a caller cannot mutate the shared list. Anything not in here is
 * treated as unknown by both forms, which fails to silence rather than to a
 * wrong explanation.
 */
const BASIS_KEYS = Object.freeze([
    'supported',
    'thin',
    'blended',
    'interpolated',
    'low_support',
    'raw_only',
    'fabricated',
    'multi_edition',
]);

/**
 * LONG form — the grade report's basis expansion.
 *
 * @param {object} ctx
 *   verdictBasis, verdictReliable, roi, sameGradeComps, nearbyThin, rawComps,
 *   excludedVariants, gradeLabel, fmvMethod, editionPriceRatio
 * @returns {string} the reason sentence(s)
 *
 * Behaviourally identical to the inline version it replaces. The ONLY code
 * changes in the move are mechanical rebinding of free variables onto `ctx`
 * (`valData.edition_price_ratio` → `ctx.editionPriceRatio`, and the eight
 * locals that were in scope in app.html). No string, no branch, no order.
 */
function basisLong(ctx) {
    const {
        verdictBasis, verdictReliable, roi,
        sameGradeComps, nearbyThin, rawComps, excludedVariants,
        gradeLabel, fmvMethod, editionPriceRatio,
    } = ctx;

    const gradeAt = gradeLabel != null ? ` at grade ${gradeLabel}` : '';
    const s = (n) => (n === 1 ? '' : 's');

    // ONE reason string per verdict_basis. Each has been checked TRUE for
    // every cell that can reach its branch, against the branch order in
    // sales_valuation.py (2026-08-08). Four wordings people reach for first
    // are deliberately NOT here; each was false, and why is recorded inline.
    const BASIS_REASONS = {
        // exact_count >= 3 always, so N is never 1 or 2.
        // NO "recent": lookback is 365 days with NO recency weighting.
        // L-SW-2026-020 instance 1 was exactly that false claim.
        supported:
            `Priced from ${sameGradeComps} sale${s(sameGradeComps)}${gradeAt}.`,
        // exact_thin implies no neighbouring bucket reached
        // MIN_SOURCE_COMPS, so "too few at nearby grades" is true. This
        // DEPENDS on the zero-factor boundary fix in this same unit;
        // without it, cells with a real n>=2 neighbour landed here and
        // the clause was false.
        // ⚠️ States the nearby COUNT rather than asserting nearby absence.
        // "too few at nearby grades to cross-check" was the second
        // instance of the assumption sales_valuation.py already warns
        // about for low_support ("the copy must state the real number
        // rather than assume one"): reaching exact_thin only means no
        // nearby bucket holds >=2, so a book can arrive with single sales
        // at six distinct nearby grades, which that wording declared
        // absent. nearbyThin is in the payload; use it.
        thin: nearbyThin > 0
            ? `Only ${sameGradeComps} sale${s(sameGradeComps)}${gradeAt}, and the `
              + `${nearbyThin} nearby sale${s(nearbyThin)} are one per grade, too scattered `
              + `to check it against.`
            : `Only ${sameGradeComps} sale${s(sameGradeComps)}${gradeAt}, and none at any `
              + `other grade to check it against.`,
        // NO COUNT of other-grade sales, deliberately. The interpolation
        // anchors on AT MOST TWO buckets, the nearest qualifying one
        // below and above (one in the one-sided branches). "estimated
        // from 30 sales at other grades" would be false: a pool of
        // 9.0(n=2)/9.4(n=1)/9.8(n=50)/10.0(n=30) anchors on 9.0 and 9.8
        // only, but a count would read 83. No anchor count exists in the
        // payload; adding one is its own decision.
        // ⚠️ NOT "the nearest grades above AND below", and NOT "filled in
        // from" — both were false. `blended` needs only exact_avg plus
        // ANY interpolated_avg, and interpolated_avg has three producers:
        // one two-sided, and two ONE-SIDED branches that are not a fill-in
        // from bracketing data at all but a flat +/-20%-per-grade step off
        // a single anchor. The server records the rate: 95.6% of
        // interpolated cells are one-sided. So the plural and the
        // bracketing were wrong for the large majority of cells here.
        blended:
            `Only ${sameGradeComps} sale${s(sameGradeComps)}${gradeAt}. The rest is `
            + `estimated from the nearest grade that has enough sales, stepped about `
            + `20% per grade.`,
        // Same no-count reasoning, plus one that cuts harder: a large
        // count reads as reassurance, and here that inference is
        // measurably FALSE. Interpolation error falls with support then
        // JUMPS BACK UP: 27.9% at n=1, 10.2% at n=5-9, 29.0% at n>=10.
        // "9.6 and 9.8", not "and up" — that is the band the backtest
        // measured; extending it to 9.9/10.0 asserts beyond the evidence.
        // This tier can carry ABUNDANT comps (30 graded sales, none at
        // this grade), so NO scarcity language.
        // ⚠️ SINGULAR "grade", and no "gap" language. 95.6% of cells here
        // are ONE-SIDED extrapolation off a single anchor bucket, so
        // "grades that have data" and "that gap" both described a
        // bracketing that usually does not happen.
        // ⚠️ The "9.6 and 9.8" emphasis alone MISDIRECTS. The zero-factor
        // boundary fix in this same unit newly routes grade_diff >= 5.0
        // cells into this tier, where the figure is the flat 0.25x floor
        // (a 5.0 gap and an 8.8 gap both get 0.25x). Telling that user the
        // risk is worst at 9.6-9.8 points away from what they are looking
        // at, so the wide-gap clause is stated too.
        interpolated:
            `No sales${gradeAt}. The slabbed figure is estimated from the nearest grade `
            + `that has enough sales, which is often well off — most of all at 9.6 and 9.8, `
            + `and it is barely more than a guess when the nearest sales are several `
            + `grades away.`,
        // nearby_thin_comps counts SALES, and in THIS branch every
        // qualifying bucket holds exactly 1 (all below MIN_SOURCE_COMPS
        // = 2), so sales count == bucket count and "one per grade" is
        // true. The field is documented as MISNAMED and is safe ONLY
        // inside this branch; elsewhere it sums buckets that DID anchor
        // the price. Do not reuse it in another tier's string.
        // ⚠️ "at other grades", NOT "near". `_all_below`/`_all_above` have
        // NO distance bound, so a 1.0 sale counts as "near" a 9.8 request.
        // In this branch nearby_thin_comps == total_graded (the exact
        // bucket is empty), i.e. every graded sale of the book at any
        // grade. "Near" was the mechanism's word, not a true one.
        // ⚠️ MUST disclose the mechanism, because this branch is checked
        // BEFORE estimated_from_raw and therefore STEALS those cells. A
        // cell with real raw sales and thin graded neighbours lands here
        // with a Slabbed FMV that is literally raw x 1.5, and the raw_only
        // string that exists to disclose that never runs. Without the
        // clause below this tier shows a price while saying nothing solid
        // enough to price from exists, and never says where the price
        // came from — the exact defect raw_only was added to fix.
        low_support: `Only ${nearbyThin} graded sale${s(nearbyThin)} of this book at other `
            + `grades, one per grade, so there is nothing solid to price the slab from. `
            + (fmvMethod === 'estimated_from_raw'
                ? `The slabbed figure is ${rawComps} raw sale${s(rawComps)} marked up 1.5×.`
                : `The figures come from typical prices for this grade, publisher and era.`),
        // The variant clause is NOT optional and must survive any rework.
        // Graded variants are excluded in PYTHON, not SQL, so a book
        // whose only graded sales are variants arrives with an empty
        // pool; "No graded sales for this book" is false there, and 7 of
        // 594 real lookups hit exactly that state.
        // The 1.5x is literal (graded_fmv = round(raw_fmv * 1.5, 2)), so
        // stating it numerically is accurate. It will NOT reproduce from
        // the two displayed figures, which are Math.round'ed.
        raw_only: excludedVariants > 0
            ? `No graded sales of the standard cover, ${excludedVariants} graded variant `
              + `sale${s(excludedVariants)} excluded. Estimated from ${rawComps} raw `
              + `sale${s(rawComps)}, marked up 1.5×. A rule of thumb, not a comp.`
            : `No graded sales for this book. Estimated from ${rawComps} raw `
              + `sale${s(rawComps)}, marked up 1.5×. A rule of thumb, not a comp.`,
        // "No USABLE sales", never "no sales at all". Two reachable
        // classes have real sales here: variant-only graded sales, which
        // are dropped in Python and land in this tier; and variant RAW
        // sales, dropped in SQL and counted in NO response field, so no
        // clause can even disclose them. The previous copy said "No
        // recent sales found for this book" and "not from sales" — both
        // absolute, both false for those cells.
        // The dollars here carry ZERO information about the book: raw_fmv
        // is itself the synthetic baseline, graded_fmv = raw_fmv * 1.5.
        fabricated: excludedVariants > 0
            ? `No standard-cover sales we can price from, ${excludedVariants} graded variant `
              + `sale${s(excludedVariants)} excluded. Both figures come from typical prices for `
              + `this grade, publisher and era.`
            : `No usable sales for this book. Both figures come from typical prices for this `
              + `grade, publisher and era, nothing about this specific comic.`,
        // ⏰ NOT EMITTED BY THE SERVER YET. Written now so the
        // edition-span unit inherits a short string rather than a long
        // one to shorten. The tier gates a comp pool holding MORE THAN
        // ONE EDITION of the same issue: the X-Men #1 case, twelve 9.0
        // comps, four from the 1991 volume, eight undated, zero from
        // 1963, returning $36 confidently on a six-figure book. Signal is
        // year span > 15y AND price ratio >= 20x, BOTH required.
        // If a ratio is printed it must be the TRIMMED one (422x on
        // X-Men #1, not 1429x). `edition_price_ratio` is not in the
        // payload yet, so the clause is omitted until it is and the
        // string is correct either way.
        // Abundant comps by definition, so NO scarcity language.
        // ⚠️ LEADS WITH THE PROBLEM, not with "Priced from N sales".
        // Under the collapsed ROUGH ESTIMATE badge, opening with a
        // confident-sounding count asserts exactly what the badge just
        // denied, and the reader reaches the "but" too late. Every other
        // hedged string already opens on an absence or a small count;
        // this was the only one that opened on confidence.
        multi_edition: (() => {
            const ratio = editionPriceRatio;
            const ratioClause = ratio ? `, differing in price by ${ratio}×,` : '';
            return `These ${sameGradeComps} sale${s(sameGradeComps)}${gradeAt} span more than `
                 + `one edition of this issue${ratioClause} so we can't tell which one `
                 + `you have.`;
        })()
    };
    // ⚠️ The fallback asserts NOTHING about counts or provenance, on
    // purpose. It must not be BASIS_REASONS.fabricated: that string says
    // "No usable sales for this book", which about an UNRECOGNISED basis
    // is an assertion we have not verified. The realistic way to get
    // here is a server that emits a new tier before this map knows it —
    // e.g. the edition-span tier landing server-side first, where
    // "no usable sales" would be flatly false on a 12-comp pool.
    // These two sentences are true for any cell by definition of
    // verdict_reliable, which is the only thing we know in that case.
    // ⚠️ NEITHER arm may state a count or a provenance. The reliable arm
    // previously reused the `supported` wording ("Priced from N sales at
    // grade X"), which verdict_reliable does NOT imply: it is defined
    // NEGATIVELY (not estimated, not interpolated, not thin), so a future
    // reliable tier carries no guarantee that graded_sample_size is what
    // priced the book. Worst case it rendered "Priced from 0 sales".
    // ⚠️ KEYED ON `roi == null`, NOT ON verdict_basis, and it must be
    // checked FIRST. This is the graded-present / raw-absent cell: the
    // server has no branch for it, so it arrives with verdict_basis
    // 'supported' and verdict_reliable true but no ROI. Collapsing the
    // badge is what exposed it — it now shows ROUGH ESTIMATE, and
    // BASIS_REASONS.supported would have answered "Priced from 12 sales
    // at grade 9.4", contradicting the badge in the same breath.
    // It is the ONLY tier where the missing thing is the RAW side, which
    // is worth the reader knowing: the slab price is well supported, the
    // comparison is what cannot be made. sameGradeComps is >= 3 here —
    // verdict_reliable with graded_fmv present implies fmv_method 'exact',
    // which requires exact_count >= 3.
    // ⚠️ LEADS WITH THE MISSING THING, same fix as multi_edition and for
    // the same reason. The first wording opened "Priced from 12 sales at
    // grade 9.4, but there are no recent ungraded sales…", which under a
    // ROUGH ESTIMATE badge asserts a confident price in its first four
    // words. Both clauses are TRUE here — unlike multi_edition, the count
    // is not undermined — but the reader still meets a contradiction
    // before they meet the resolution. The slab price being well
    // supported is still stated; it is just no longer the opening claim.
    // ⚠️ OPEN TENSION, worth Mike's decision: 'ROUGH ESTIMATE' arguably
    // MISDESCRIBES this cell. The slabbed figure is not a rough estimate;
    // it is a well-supported price with no raw comparison available. That
    // is the same objection the 2026-08-07 per-tier badges existed to
    // answer, resurfacing in a state that was not a category back then.
    // A fourth badge value would fix it and would break the three-value
    // rule. Left at three by default.
    return (verdictReliable && roi == null)
        ? `There are no recent ungraded sales to compare against, so we can't say `
          + `whether grading pays off. The slabbed figure itself is priced from `
          + `${sameGradeComps} sale${s(sameGradeComps)}${gradeAt}.`
        : (BASIS_REASONS[verdictBasis] || (verdictReliable
            ? `Priced from the sales we have${gradeAt}.`
            : `We can't price this reliably from the sales we have, so we're not `
              + `making a call on whether grading pays off.`));
}

/**
 * SHORT form — the collection card's one-tap reason.
 *
 * PARAMETERLESS BY NECESSITY AND BY DESIGN. A saved row carries none of the
 * five interpolated fields, and a string that cannot state a count cannot state
 * a wrong one. Every clause below is therefore true for EVERY cell that can
 * reach its branch, with no dependence on how many sales there were.
 *
 * Each string was checked against its long-form twin's branch conditions:
 *
 *   supported     exact_count >= 3 at the requested grade.
 *   thin          exact_thin: 1-2 same-grade sales AND no nearby bucket >= 2.
 *                 Covers BOTH long-form arms (scattered singles, or nothing).
 *   blended       exact_avg + interpolated_avg. SINGULAR "grade" and no
 *                 bracketing language — 95.6% of interpolated cells are
 *                 one-sided, the same correction the long form carries.
 *   interpolated  zero same-grade sales. NO scarcity language: this tier can
 *                 hold 30 graded sales, none at the requested grade.
 *   low_support   estimated_flag + low_support_only. Says nothing solid exists
 *                 to price the SLAB from, which is the true claim; the figures
 *                 still exist.
 *   raw_only      real raw sales, zero graded. Must NOT say "no sales".
 *   fabricated    "no USABLE sales", never "no sales at all" — variant-only
 *                 graded and variant raw sales are both reachable here.
 *   multi_edition abundant comps by definition, so NO scarcity language.
 *
 * @param {string} basis  a verdict_basis value, or null/unknown
 * @param {object} [opts] { roi } — roi is persisted on collections and is what
 *                        distinguishes the graded-present / raw-absent cell.
 * @returns {string|null} the short reason, or NULL when nothing true can be
 *                        said. NULL is the signal to render no affordance at
 *                        all (see js/collection.js): a row saved before this
 *                        column existed has no reason, and a disabled or
 *                        greyed control would claim one exists and is withheld.
 */
function basisShort(basis, opts) {
    // ⚠️ "roi was not supplied" and "roi is null" are DIFFERENT FACTS and must
    // not collapse. `roi == null` is true for undefined, so a caller that omits
    // opts would otherwise take the raw-absent branch below and assert "there
    // are no ungraded sales to compare it against" — a claim about data it
    // never passed. js/collection.js always supplies roi (the column is always
    // selected, null or a number), so this is defensive; it is here because the
    // failure mode is an assertion, not a crash, and assertions are the class
    // this whole file exists to police.
    const roiKnown = !!opts && 'roi' in opts;
    const roi = roiKnown ? opts.roi : undefined;

    // The graded-present / raw-absent cell, keyed exactly as the long form
    // keys it: reliable AND no ROI. `verdict_reliable` is not persisted and
    // does not need to be — it is IDENTICALLY `basis === 'supported'`
    // (sales_valuation.py:736 vs the basis ladder twelve lines below it,
    // same two inputs, same block). Checked FIRST for the same reason the
    // long form checks it first: the `supported` string alone would read as
    // confident under a "Can't say" chip.
    if (basis === 'supported' && roiKnown && roi == null) {
        return 'The slab price is well supported, but there are no ungraded sales '
             + 'to compare it against.';
    }
    // Basis is 'supported' but we were not told the ROI, so we can say neither
    // "priced from sales at this grade" (which would read confident under a
    // hedged chip if this is in fact the raw-absent cell) nor the raw-absent
    // sentence (which asserts an absence we have not been shown). Offer nothing.
    if (basis === 'supported' && !roiKnown) {
        return null;
    }

    const BASIS_SHORT = {
        supported: 'Priced from sales at this grade.',
        thin: 'Priced from very few sales at this grade, with too little nearby to '
            + 'check it against.',
        blended: 'Partly priced from sales at this grade, partly estimated from the '
            + 'nearest grade that has enough.',
        interpolated: 'No sales at this grade. The slabbed figure is estimated from '
            + 'the nearest grade that has them.',
        low_support: 'Too few graded sales of this book to price the slab from.',
        raw_only: 'No graded sales of this book. Estimated from raw sales, marked up.',
        fabricated: 'No usable sales for this book. The figures come from typical '
            + 'prices for this grade, publisher and era.',
        multi_edition: 'These sales span more than one edition of this issue, so we '
            + "can't tell which one you have.",
    };

    // Unknown or missing basis returns NULL rather than a generic sentence.
    // The long form has a fallback because it MUST render something under an
    // already-visible badge; the short form has no such obligation — it can
    // simply not offer the affordance, which asserts nothing.
    return BASIS_SHORT[basis] || null;
}
