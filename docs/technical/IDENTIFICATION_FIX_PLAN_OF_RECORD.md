# Identification Fix — Plan of Record

> **Status:** DECIDED 2026-06-15 (Session ~104). **Build is NEXT SESSION** — drafted for Mike's
> review first, then file-specific commit/deploy/smoke-test by Mike (he runs all git/deploy).
> **Nothing is built yet.** Companion analysis: `docs/technical/IDENTIFICATION_HONESTY_REVIEW.md`.
> Problem recap: extraction mis-identifies (or fails to identify) the book, and the pipeline
> produces a confident grade + FMV + slab verdict anyway. Launch gate for private beta.

## Decision 1 — Extraction model: GLOBAL Sonnet

- Flip `comic_extraction.py:483` from the **`'haiku'` tier to the `'sonnet'` tier** in its existing
  `call_with_fallback` call. Use the **tier, not a hardcoded string** (targets `claude-sonnet-4-6`
  today, fallback-protected, same tier grading uses).
- **Why GLOBAL over conditional re-read:** the bench showed Haiku's failure mode is confident
  **fabrication**, not honest abstention (invented fake `barcode_digits` 2/3; Sonnet empty 3/3). A
  confidence-gated re-read can't catch errors Haiku never admits, so the conditional approach would
  leak the exact wrong-but-confident cases (Absolute Batman / Atari Force) being fixed.
- **Cost:** ~+1¢/call, ~$10/1,000 extractions (~2.9× Haiku). Trivial at soft-launch volume —
  **accepted.**
- **Caveat on record:** the bench held only easy clean books (both models 100%), so the hard-case
  accuracy gain is **inferred, not measured**. Decision is robust regardless because the honesty
  gate (Decision 2) catches whatever Sonnet still misses.

## Decision 2 — The honesty gate (#1 launch fix; built REGARDLESS of the model choice)

**Principle:** when the pipeline doesn't actually know the issue, it must NOT fabricate a valuation
as if it does. **Grade can still show** (condition is observable); **valuation + slab verdict HALT**
until the issue is confirmed. All components are wiring of pieces that already exist:

- **Objective issue-confidence** — `issue=='' ⇒ could_not_determine`; later, barcode↔vision
  agreement. **NOT** model self-reported confidence — the data proved a weak model reports
  confident-wrong, so self-report is untrustworthy.
- **Frontend** — on absent/low-confidence issue: drop the "✓ Identified" framing; show the existing
  edit form **by default** (already built — shown on extract-failure today, hidden behind the pencil
  on success); require the issue; gate the `/api/sales/valuation` call on a confirmed issue. **Remove
  the `|| '1'` issue default** (`app.html` ~2554).
- **Server belt** — `/api/sales/valuation` must NOT blend-all-issues when issue is empty
  (`sales_valuation.py` ~228): require issue or return `issue_required` (no FMV).
- **Surface the extracted value prominently** — "We read this as X #N — confirm or fix" — so
  wrong-but-confident reads get caught by the human, not buried behind a green checkmark.

## Sequencing

Extraction-flip + honesty gate **ship together as one coherent "make identification trustworthy"
change.** Build next session, drafted for review first, then file-specific commit/deploy/smoke-test
by Mike.

## Parked / NOT NOW (on record, don't act)

- **Barcode-issue writeback** — `decode_barcode` computes issue but the merge never writes it back
  (`comic_extraction.py:663-681`). Real; helps clean modern books; demoted below the model fix;
  pairs with the barcode variant-subtyping roadmap item.
- **Mylar/sleeve grade-inflation** — grader has no obstruction penalty (a sleeved Absolute Batman
  graded 9.0). Separate grading-accuracy item.
- **Resilience gap** — 8 of 12 model call sites pass static constants with NO fallback (Chrome
  vision, signature v1/v2, Slab Guard CV, eBay gen, admin). Harden via `call_with_fallback` later.
- **Reference-catalog / cover-match lookup (GCD/ComicVine)** — the real long-term identity fix, but
  a multi-session third-party integration (with its own dependency-monitoring burden). Post-launch.
- **Pricing-tier review** — global Sonnet raises per-grade cost on every tier incl. Free (flat
  25/mo cap). Unit-economics input for the pricing conversation, later.
