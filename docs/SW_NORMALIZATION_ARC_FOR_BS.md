# Slab Worthy — Valuation Title-Normalization Arc (briefing for BS)

> **Prepared:** 2026-07-10 (Session 115) · **Audience:** BS (no session context assumed)
> **Status:** Fixes shipped + corpus re-normalized + verified. Deferred items noted at bottom.
> **Detail SoT:** `docs/LAUNCH_READINESS.md` (sequence item 6) · Spec: `docs/technical/VALUATION_FMV_FIXES_SPEC.md`

## The problem class

Slab Worthy's FMV engine prices comics from a corpus of ~71K captured eBay sales
(`ebay_sales`). Each sale's raw listing title is normalized into structured fields
(canonical title, issue number, variant/lot/signed/reprint/facsimile flags), and
valuations draw comp pools from those fields. Three separate defects in that
normalization layer were silently corrupting comp pools — meaning the product could
return a **confident, wrong FMV even when the grade was right**. All three are now
fixed and proven with corpus-wide before/after audits.

## Fix 1 — leading-article mismatch (shipped 2026-06-27, `c688bce` + gate `cecbaa5`)

- **Symptom:** ASM #41 (first Rhino), graded 6.0 → FMV ~$47 and "not worth grading."
  Real CGC 6.0 market ~$550 — a ~10× miss on the core product promise.
- **Mechanism:** lookups for "The Amazing Spider-Man" found ZERO comps because the
  corpus stores "Amazing Spider-Man" — the leading "The" broke the normalized exact
  match AND the substring fallback → generic key-blind estimate. Blast radius: the
  highest-traffic Marvel/DC flagships (the titles that conventionally carry "The").
- **Fix:** strip a leading article on BOTH sides of the match (`title_matching.py`),
  corpus-proven **0 false merges across 14,033 titles**.
- **Paired honesty fix (`cecbaa5`):** data-sufficiency verdict gate — a zero-real-comp
  fabricated estimate now renders an amber "ROUGH ESTIMATE" caution instead of a
  confident slab/no-slab verdict (`verdict_reliable` in the API response).
- **Verified live:** ASM #41 → 6.0 median $550, "Worth the Slab."

## Fix 2 — Cover-A misclassification + cross-title fuzzy leakage (shipped 2026-07-10, `15cb459`)

Found while diagnosing Absolute Batman #1 (Dragotta Cover A, 1st print) pricing at
$150 vs. a real Cover-A market of ~$185 median. Two independent mechanisms in
`title_normalizer.py`:

1. **Cover-A bug:** the normalizer flagged "Cover A" — the STANDARD cover — as a
   variant, so the standard cover's own best-labeled sales were **excluded from their
   own comp pool**, leaving a pool polluted with word-form later printings ("Tenth
   Print"), Noir editions, and artist-name variants. **2,601 corpus rows affected.**
   Fix: cover-letter handler — "Cover B"+ still flags variant; "Cover A" is standard.
2. **Cross-title fuzzy leakage (systemic):** the fuzzy canonical-title matcher merged
   similar-but-different titles on aggregate similarity score alone —
   `token_sort_ratio("Absolute Catwoman", "Absolute Batman") = 88`, and no threshold
   separates that from legitimate rescues. Corpus audit: **748 sales rows mis-merged
   across 23 canonical titles**, headlined by **Defenders sales (incl. CGC keys)
   merged into Descender's pool**, plus Power Girl→Fire Power, X-Force→X-Men,
   Crossover→Crossed, etc. Fix: `_fuzzy_tokens_supported` per-token guard — every
   content token of a matched candidate must be supported by the listing text
   (order/hyphen/typo tolerant in both directions, so Spiderman↔Spider-Man survives;
   a substituted word fails, because one substituted word = a different comic).

**Why the pool being "big" didn't save us:** the data-sufficiency gate (Fix 1's
pair) correctly saw a large pool and stayed green — the pool was large and WRONG.
Data-integrity corruption is invisible to sufficiency checks.

## Rollout + verification (2026-07-10)

- Deploy verified (new code confirmed in container before trusting any run output).
- Dry-run reviewed first: computed variant count 15,344 vs stored 18,044 = 2,700 rows
  flipping ≈ the audit's predicted 2,601 + rows captured since. Then live:
  **71,449/71,449 rows re-normalized, 0 errors** (~1 hr, batched commits, idempotent).
- Post-run checks — predictions hit exactly:
  - stored `is_variant` = **15,344 exactly**
  - Defenders→Descender contamination = **0 rows remaining**
  - "Absolute Batman Annual" separated into its own canonical (42 rows) instead of
    leaking into the main book's pool
  - **End-to-end through the live app: Absolute Batman #1 @ 9.0 → raw FMV $169.99**
    (`fmv_method=blended`, real comps, `verdict_reliable=true`) vs the pre-fix $150.00.

## Deliberately deferred (decided, not forgotten)

- **Layer 3 — grade-aware raw estimate:** the remaining gap from $169.99 to the
  ~$185–300 clean-copy market is a *display/methodology* change, not a data fix, so
  it's folded into the grading-accuracy benchmark work (R1/R2), not shipped ad hoc.
- **`market_sales` equivalent pass:** the fix ran on `ebay_sales`; the smaller
  `market_sales` table (~8,604 canonical rows) needs the same re-normalization —
  small extension of `normalize_batch.py`, queued.
- **Tier-2 tail:** word-form printings, enumerated-run lot-shield gaps, graded=false
  CGC slabs in raw pools — logged in LAUNCH_READINESS item 6, negligible for the
  headline books.

## Competitive relevance

Direct progress on the **"first demonstrably accurate + honest-about-uncertainty"**
positioning: every fix was proven with a corpus-wide before/after audit rather than
spot checks, and the honesty gate means fabricated estimates visibly downgrade
themselves. Generalizable lesson extracted (L-SW-2026-009): any fuzzy/similarity
match that WRITES into a shared pool needs a per-token support guard — an unmatched
item is recoverable, a false merge silently poisons an existing pool.
