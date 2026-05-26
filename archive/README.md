# Archive — Stale-but-Keep

Files moved here in the 2026-05-26 cleanup pass. Not load-bearing (no live code or active doc references them), but worth keeping for history or future reference.

## What's in each folder

- **patches/** — `*.patch` diffs from past sessions. Already applied to the codebase; kept as historical record of how specific fixes were composed.
- **mockups/** — design exploration HTMLs and one build-log Markdown. Includes dashboard mockups (A/B/C), waitlist variants, hero imagery, favicon options, FB assets preview, logo mockup, Slab Guard icon. Reference-only.
- **fb-assets-old/** — Facebook profile + cover variants from the brand-asset iteration (Session 77). The picked final lives somewhere in active marketing; these are the alternates.
- **sdcc/** — `SDCC_Launch_Roadmap.{docx,js,pdf}`. The original launch was targeted at San Diego Comic-Con; pivoted to GalaxyCon San Jose (Aug 21-23, 2026). Plan is superseded but the structure may inform the GalaxyCon plan.
- **old-pnls/** — drafts `SlabWorthy_Year1_PnL.xlsx`, `_v2.xlsx`, `_v3.xlsx` from the P&L iteration. Canonical lives at `docs/business/SlabWorthy_Year1_PnL.xlsx` (matches v3).
- **old-brand/** — `BRAND_GUIDELINES.txt` v2.2 (Feb 2026). Documents the pre-pivot brand where CollectionCalc was the parent and "Slab Worthy?" was a sub-feature, with indigo/dark color palette. The current brand is Slab Worthy / purple-gold / Bangers font. **A new brand guide is overdue.**
- **docx-duplicates/** — `TODO.md.docx`. Word version of `TODO.md`; the `.md` is the source of truth.
- **test-plans-old/** — `Session59_Test_Plan_From_Mike_Footer_Issues.docx`, `Valuation_Endpoint_Test_Plan.docx`. One-off test plans from completed sessions.

## What's NOT here

Anything load-bearing for the live site (`slabworthy.com`), the backend (`collectioncalc-docker.onrender.com`), or the Render/Cloudflare deploys stayed at root. Active business docs (P&L, competitors, budget, patents, white papers) stayed in `docs/business/`.

If you find yourself reaching into `archive/` repeatedly for the same file, that's a signal it shouldn't be archived — promote it back to root or `docs/`.
