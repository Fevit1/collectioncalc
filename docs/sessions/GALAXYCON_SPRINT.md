# Slab Worthy — GalaxyCon Sprint Plan

**Created:** 2026-06-10 · **Author:** Mike (with BO)
**Status:** Active working plan. Revise weekly. Relay week-blocks to DO as needed.

---

## Fixed dates (these do not move)

| Gate | Date | Distance from 2026-06-10 |
|------|------|--------------------------|
| **Soft launch** (public beta, open online sign-ups) | **July 21, 2026** | 41 days (~5.9 weeks) |
| **GalaxyCon San Jose** (alpha launch event, booth demos) | **Aug 21–23, 2026** | 72 days (~10.3 weeks) |

## The one decision that shapes everything

**Soft launch = CORE FLOW ONLY.** Grade → value → slab verdict → save, with billing live.
Slab Guard waits for after the core flow proves credible. Reason: Slab Guard's buyers
(dealers, high-value collectors) are downstream of trust the grade-and-value flow has to
earn first. Nobody licenses fingerprinting or trusts it with a $10K book if the flow that
brought them in was sloppy.

## Capacity assumptions

- Mike: ~250 hours of builder/design time available before July 21.
- DO (Claude Code): completes engineering at ~10X a normal time estimate.
- **The risk is NOT too little time. It is too much scope.** With abundant time + fast DO,
  the temptation is to build everything — including items that should NOT ship by July 21.
  Surplus time goes to HARDENING the three critical-path items, not widening scope.

---

## PHASE 1 — Nail the core flow (now → July 21)

Only three things gate the soft launch. Everything else is fenced out (see below).

### CP-1: Valuation confidence labeling (V2/V3) — THE GATE
- **Why it's first:** Public sign-ups funnel strangers onto popular titles where the corpus
  is thin. The launch-killer is being *confidently* wrong in public on day one (the Tabi
  "wildly off" failure mode). Bar is NOT full-catalog accuracy — it's that every FMV carries
  an honest confidence signal and thin keys say so plainly.
- **Principle:** "Respectable = honest about confidence, not accurate on everything."
- **Work split:** Label/threshold *design* = Mike + BO (the real work). DO build is small —
  comp-count infrastructure already exists from the Batch 5 lookback work.
- **Done when:** Every valuation response carries a confidence tier; thin keys are visibly
  flagged; no FMV is presented with false precision.

### CP-2: Billing end-to-end across all four tiers
- **Why:** Open sign-ups + live Stripe means someone WILL try to pay July 21.
- **Test matrix:** Free / Pro / Guard / Dealer — happy path AND failure cases:
  declined card, webhook delivery + retry, tier-gating enforced SERVER-SIDE (not UI-only).
- **Surplus-time target:** The failure cases are what bite in public. Spend the extra hours here.
- **Done when:** All four tiers subscribe, upgrade, downgrade, and cancel correctly; gating
  is enforced at the API layer; webhooks confirmed in Stripe dashboard.

### CP-3: Mobile testing on real devices
- **Why:** Acquisition is Facebook comic groups → overwhelmingly mobile traffic. If the
  four-photo upload → grade → value flow breaks on a phone, the launch breaks for most users.
- **Scope:** Real iOS + Android devices. Full flow, not desktop devtools emulation.
- **Done when:** Full core flow completes cleanly on at least one real iOS and one real
  Android device, including photo capture/upload.

### Fenced OUT of Phase 1 (do not let these creep in)
- Signature accuracy push (ships at 78% with honest labeling — same philosophy as valuation)
- Sell Now Alerts (retention/differentiation, not first-impression)
- Slab Guard registration (Phase 2 / GalaxyCon reveal)
- Consumer vs. B2B positioning (doesn't block consumer launch)
- Repo cleanup / reorg pass
- Marketplace-prep coverage beyond what already works

---

## PHASE 2 — Earn the booth (July 21 → Aug 21)

Only after the core flow is proven in public for ~4 weeks.

- **Sell Now Alerts v1** — "killer feature nobody else has." Safe to build now because it's
  not in the first-impression path. Alert when an incoming eBay sale on an owned title
  exceeds FMV by >25%. Email + in-app badge.
- **Signature accuracy 78 → 87%** — upload 57 new creator refs via admin UI, re-run
  cross-validation. Booth-demo upgrade, not a launch gate.
- **Consumer vs. B2B Slab Guard positioning** — the booth forces it. Resolve before standing there.
- **GalaxyCon booth demo design** — the live-demo script that cannot faceplant.

---

## Week-by-week (Phase 1)

| Week | Dates | Focus |
|------|-------|-------|
| W1 | Jun 10–16 | CP-1 design: confidence tiers + thresholds (Mike+BO). DO scaffolds label plumbing. |
| W2 | Jun 17–23 | CP-1 build + integrate. Begin CP-2 billing happy-path tests. |
| W3 | Jun 24–30 | CP-2 failure-case testing (declines, webhooks, server-side gating). CP-1 verification pass. |
| W4 | Jul 1–7 | CP-3 mobile on real devices. Fix what breaks. |
| W5 | Jul 8–14 | Full-flow regression across all three CPs. Soft-launch dry run (waitlist invite cohort). |
| W6 | Jul 15–21 | Buffer + polish. Final go/no-go. **Soft launch July 21.** |

Note: W5's dry-run cohort (invite a slice of the confirmed waitlist before fully opening) is
the cheapest insurance against a public faceplant. Use it.

---

## Standing disciplines (from CLAUDE.md / lessons)

- Git: `git status` → review every file → `git add [specific files]` → commit → push → deploy → purge.
  Never `git add -A`. Staged, file-specific commits only.
- DO does not commit/push without Mike's explicit command (L-SW-2026-001/002).
- Any new third-party service → register in `dependency_monitor.py`. Not optional.
- Run verification agent against new code before it's presented to Mike.
