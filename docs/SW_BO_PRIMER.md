# Slab Worthy — BO Primer (DRAFT)

*Version 2026-05-26. Draft, not yet stored. Becomes authoritative when Mike saves it to BO project storage; until then this file is just a paste candidate.*

*Purpose: starting point for a fresh BO opened on the Slab Worthy project. Pairs with the cross-project BO primer (Mike's identity, operating model, principles, health/family/financial context) — does not duplicate that material. Read both.*

---

## What Slab Worthy is

AI-powered comic book grading + valuation + collection management tool. The product answers the one question every collector asks before spending $25-100 on professional grading: "is this worth getting slabbed?" Upload four photos, get a CGC-equivalent grade (0.5-10.0 scale, 8-category structured scoring), grade-specific FMV from real eBay/Whatnot sales data, and an ROI verdict on whether slabbing makes economic sense.

Sits in IdeaByHuman's portfolio alongside MASSÉ (job-discovery for execs) and TheFormOf (agentic app builder). Slab Worthy is the most consumer-facing of the three and the closest to a real launch event.

## Where things live

- **Live site:** slabworthy.com (frontend on Cloudflare Pages)
- **API:** collectioncalc-docker.onrender.com (Flask backend on Render, deploys on `git push`)
- **GitHub:** Fevit1/collectioncalc (repo name is the pre-rebrand "CollectionCalc" — repo never got renamed; the deploy hooks would all need rewiring)
- **DO (Claude Code for engineering work):** `C:\Users\mberr\CC\SW`
- **DB:** PostgreSQL on Render (16 tables), Cloudflare R2 for image storage
- **Stack:** Flask/Python backend, vanilla HTML/CSS/JS frontend (no framework), Anthropic Claude API for grading/extraction/signature matching, Stripe for billing, eBay Inventory API for listings.

## Two distinct surfaces (this matters for strategy)

Slab Worthy is really two products under one brand. Treat them as separable when reasoning about pricing, customers, moat, and competition.

1. **Consumer app — "Should I slab this?"** Free + three paid tiers (Pro / Guard / Dealer). Self-serve, individual collectors. Competes with CovrPrice, GoCollect, Key Collector, CLZ, ComicMint AI, Tabi. The differentiated wedge is multi-photo AI grading + the slabbing-ROI calculation, both of which competitors don't have.

2. **Slab Guard — B2B licensing of the fingerprinting/theft-recovery system.** Patent-backed perceptual-fingerprint registration with stolen/recovered state machine and verify-page lookup. Different buyer (LCS owners, conventions, CGC itself, insurance), different conversation, different sales motion. White paper + licensing proposal already drafted (`docs/business/SlabGuard_WhitePaper_DRAFT.docx`, `Slab_Guard_Licensing_Proposal.docx`).

A common BO failure mode would be collapsing these into one product. They share infrastructure but have separate customers, separate moats, and separate go-to-market.

## Defensibility (three patents pending)

1. **Multi-angle comic grading system** — filed Jan 27, 2026. Covers the structured 8-category grading scored against multi-photo input.
2. **Comic fingerprinting theft recovery** — filed Feb 12, 2026. The Slab Guard substrate.
3. **Signature identification** — filed Feb 25, 2026 (Application #63/990,743). Forensic-match-style signature attribution against a reference DB.

The patents are real moat for the Slab Guard B2B story; for the consumer app they're more of a "we got here first" credibility marker than a competitive wall (competitors can copy the consumer UX without infringing the underlying methods).

## Launch shape

- **Soft launch:** July 21, 2026 (public beta, open sign-ups online)
- **Alpha launch event:** **GalaxyCon San Jose, Aug 21-23, 2026** at the San Jose McEnery Convention Center. CGC is on-site via One Stop Comic Shop, so the audience is grading-aware — the right room. Booth demos planned.

GalaxyCon is the forcing function. The original target was San Diego Comic-Con; pivoted to GalaxyCon because it's local, smaller, and grading-audience-rich. As of 2026-05-26 that's roughly 12 weeks out from soft launch and 17 weeks from the event.

## Financial model

Year 1 projection (15K users — 5K comics + 10K baseball cards, since the card vertical is planned for Q4 2026): **$739K revenue, $379K net profit, 51% net margin**, including a first hire (Marketing + Front-End Design at ~$97.5K all-in) and $54K marketing budget. Penetration assumption is <0.1% of TAM (comics ~2-5M collectors, cards ~15-20M households) which is achievable but not given.

Source: `docs/business/SlabWorthy_Year1_PnL.xlsx`. The model is Mike's, defensible enough to discuss, not externally validated.

Pre-revenue today. Four-tier Stripe billing is wired (Free/Pro/Guard/Dealer) but the user base is pre-launch — there is no real conversion data yet.

## Operating model (specific to Slab Worthy)

Same DO/BO/Mike triangle as MASSÉ. DO at `C:\Users\mberr\CC\SW`. DO does engineering, BO does strategy/synthesis/pushback. Mike has final taste and authorization.

Same brief-writing discipline: BO drafts paste-ready messages to DO as standalone fresh messages, not as continuations of BO's drafting history. Same drafted-≠-sent watchword. Same domain boundary: strategy docs are BO/Mike-side, not handed to DO.

Same "schema-exceeds-wiring" standing assumption — applies here too. The repo has multiple instances of capability described in docs that may not match production reality (older docs still say "CollectionCalc," some marketplaces listed in marketplace prep but not all tested end-to-end, signature DB schema upgraded but accuracy still climbing toward target). Before recommending a fix is "wire in the existing X," verify X is actually consumed in the live path.

## Working principles specific to Slab Worthy

**Pricing-tier integrity matters more than feature shipping.** Mike has chosen four tiers (Free / Pro / Guard / Dealer). Each must do something distinct enough that the upgrade story is honest. New features should land in a tier deliberately, not "across all tiers because that's easier" — that erodes the tier value differential.

**Patents are a strategic asset, not a moat by themselves.** Don't reason as if "patent-pending" prevents competition; reason as if the patents are a Slab-Guard-licensing enabler and a credibility/PR asset for the consumer app. The actual consumer moat is the data flywheel (eBay + Whatnot sales coverage), the signature reference DB, and the multi-photo grading consistency.

**GalaxyCon is the calendar anchor.** Aug 21-23 doesn't move. Soft launch July 21 doesn't move. Work that doesn't land on the critical path to those two dates should be parked or named as off-critical-path explicitly. The "we have time" trap is real — count weeks, not features.

**Mandatory third-party dependency monitoring.** Every new external service added to Slab Worthy must be registered in `dependency_monitor.py` (Anthropic, eBay, Stripe currently monitored). This was learned the hard way when a Haiku model retirement broke production extraction. Codified in CLAUDE.md.

## Current state (as of 2026-05-26)

⚠️ The last entries in `WHERE_WE_LEFT_OFF.md`, `ROADMAP.txt`, and `TODO.md` are Mar 24, 2026 (Session 90). That's ~9 weeks ago. During that window Mike was on the cancer diagnosis + treatment-decision path, the CZI/OpenAI job search, the MASSÉ Sprint 2 layer-3 work, the IDH homepage replacement, and the BAR voice-macro side project. Slab Worthy likely hasn't moved meaningfully since Session 90; if it has, this primer is stale and needs reconciliation against the repo state before relying on specifics.

**Last known Session 90 work (Mar 24):**
- Mobile image extraction fixes (canvas resize to 2048px, EXIF parser rewrite, non-comic-cover validation).
- Anthropic model migration: `claude-3-5-haiku-latest` retired → moved to `claude-haiku-4-5-20251001` via the Anthropic SDK with `call_with_fallback()`.
- Built `dependency_monitor.py` for Anthropic / eBay / Stripe deprecation tracking, with email alerts and admin dashboard banner.
- Loading-UI consolidation, health-endpoint crash fix, grading-report ReferenceError fix.

**Known open threads from Session 90 / earlier (verify before relying):**
- **Signature v2 accuracy** — currently 78.3% cross-validation. Target 87%+. Session 86 expanded the creator DB from 43 → 100 (57 new creators selected with weighted criteria + confusion-risk screening); migration prepared, reference images still to be uploaded via admin UI.
- **eBay listing end-to-end test** — fixed-price working, auction format needs full validation.
- **Marketplace prep testing** — Whatnot/Mercari/Facebook/Heritage/ComicConnect/MyComicShop/COMC/Hip Comics generation written; coverage of which platforms are actually tested end-to-end is unclear and worth a verification pass.
- **Mobile testing on real devices** — extraction and grading confirmed working in Session 90, broader regression coverage still needed.
- **GalaxyCon sprint plan** — 25 weeks out as of Mar 24, now ~12 weeks out. A real sprint plan from today's date is overdue.
- **Sell Now Alerts (v1)** — flagged as "killer feature nobody else has" in roadmap. Not built. When an incoming eBay sale on a title a user owns exceeds FMV by >25%, alert them. Email + in-app badge.
- **Data collection ramp** — more eBay/Whatnot sales coverage needed before launch. Coverage gaps are quiet, not loud — easy to miss until a user gets an embarrassing "no data" result on a popular title.

**Repo-hygiene state:** the local repo is noisy and overdue for a cleanup pass — ~170 files at root mixing four eras (pre-rebrand CollectionCalc, early Slab Worthy, recent sessions, current). Older business docs still header "CollectionCalc." Multiple stale patch files, mockup HTML, and duplicate `.docx`/`.md` versions of the same content sit alongside live code. A separate reorg pass is queued.

## What current BO should know about Slab Worthy work

This is Mike's most product-tangible project in the IDH portfolio. MASSÉ has been the priority during the cancer + job-search window, but Slab Worthy has a hard external deadline (GalaxyCon Aug 21-23) and a market window (the grading-audience-rich room, the patents-pending narrative, the four-tier billing already wired). The risk shape is different from MASSÉ: MASSÉ's risk is finding traction; Slab Worthy's risk is shipping a polished product into a known audience by a fixed date with limited attention.

Mike has been the user-interaction designer, product-taste arbiter, and patent strategist across this project. He has *not* been the marketing arm yet — that's the planned first hire. A new BO should expect to be useful on: launch sequencing, pricing-tier critique, Slab Guard B2B narrative, competitive positioning vs CovrPrice / GoCollect / Key Collector, GalaxyCon booth demo design, soft-launch sequencing (waitlist → invites → public), and pre-launch trust-grade verification (because public launches make new-user-flow failures very visible).

The same adversarial posture applies — push back on assumptions, name what doesn't quite work, bring the contrary case. Mike's biggest risk on Slab Worthy is not the product, it's attention scarcity and a calendar that doesn't move. BO that softens that reality isn't helping.

---

*End of primer.*
