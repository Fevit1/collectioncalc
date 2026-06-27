# Launch Readiness — Slab Worthy (SINGLE SOURCE OF TRUTH)

> ⚠️ **This file is the durable source of truth for what's left before launch. Status lives HERE — not in a browser window, not as retroactive labels in session notes.** The prior A–F "checklist" existed only in a BO browser tab (never downloaded) and survived as labels in `docs/sessions/WHERE_WE_LEFT_OFF.md`. This doc replaces it. Update this file when readiness status changes.

**Soft launch target:** July 21, 2026 · **GalaxyCon (booth):** Aug 21–23, 2026 · **Launch posture:** gated/batched public beta (`require_approved` + waitlist + beta codes; admit in waves). **Declared HARD gates:** billing end-to-end + valuation/identification honesty.

**MOST RECENT CHANGE (Rule 5):** Doc created 2026-06-27 (Session 111) as the durable replacement for the lost A–F checklist. Reconciled the A–F session-note labels with the older ~March P0/P1/P2 "47-test" QA plan (Session 59). Verdict: **F (mobile+load) is the largest un-started gap; billing's cancel/downgrade lifecycle is the untested hard-gate item.** No fixes performed — assembly only.

---

## Lineage (so we don't rebuild blind)
Two overlapping checklists existed; neither was a maintained artifact:
- **~March (Session 59) "47-test QA plan"** — lives in `TODO.md` (Testing sections), `ROADMAP.txt:119`, `CLAUDE_NOTES.txt:62`. Covers Auth, billing, grading, collection, fingerprinting; **~40 of 47 still formally untested.** It ALREADY listed today's "gaps" as untested: **"Mobile testing — full grading flow on real phones"** (`TODO.md:209`) and **"End-to-end grading accuracy test — grade 10+ known-CGC comics, compare — this IS the calibration test suite"** (`TODO.md:294`). **These are long-standing known-untested items, not new.**
- **Spring (Sessions 104–109) "A–F readiness"** — a re-cut that lives only as labels in `WHERE_WE_LEFT_OFF.md` (`A/B early · C=collection mgmt · D=tier gates · E=billing · F=mobile+load`). Most of A–E maps to spring work that was actually done; F was never reached.

This doc supersedes both as the current view. March predates most of spring's work, so status below is CURRENT, not March's.

---

## A–F honest status (no optimism)

| Sec | Area | Status | Detail |
|----|------|--------|--------|
| **A** | (undefined) | ❓ **UNKNOWN — not "done"** | No recorded definition of what A tested ("early" in notes). No artifact, no evidence. Must define what it was meant to cover before claiming complete. |
| **B** | (undefined) | ❓ **UNKNOWN — not "done"** | Same as A — undefined, unverified. |
| **C** | Collection mgmt | 🟡 **RUN — 2 must-fixes OPEN** | Run S104, mostly working (covers load, sort/filter/search, Slab Guard reg, eBay+Whatnot gen, Edit MY VAL all verified). **OPEN:** (1) DELETE (trash icon) has **no confirm/undo** — immediate delete; mobile mis-tap = data loss = trust-breaker. (2) comic-detail row **looks clickable but does nothing** → reads as "broken"; build it or neutralize the affordance. |
| **D** | Tier gates | ✅ **DONE** | Tier Honesty Pass shipped S106 — per-tier grading caps wired to PLANS (Free 25/Pro 100/Guard 250/Dealer 1000), Dealer checkout refused server-side, pricing copy matches product. Server-enforced gates real (extra_photos, slab_guard_regs, vision/extension, signature_id). |
| **E** | Billing | 🟡 **Happy path verified; cancel lifecycle UNTESTED; bugs open** | Pay→correct tier (incl. Pro→Guard change) verified live S108 (Stripe TEST). Stacking guard SHIPPED (`billing.py:525–532`, 409 on existing live sub). **OPEN:** (a) **immediate-cancel→free UNTESTED** — the `customer.subscription.deleted` teardown webhook has never fired (live test only did cancel-at-period-end, scheduled Jul 4); (b) **step-3 latent bug** (`billing.py:797–818`): `handle_subscription_deleted` matches `stripe_customer_id` ONLY and reverts to free on ANY sub deletion → cancel-one-of-stacked drops user to free while Stripe keeps billing the rest (low-risk for net-new now that the guard prevents stacking, but a real correctness bug); (c) **step-2 UX**: account "Change Plan" → `/pricing.html`→checkout (now hits the 409 raw error) instead of opening the portal. |
| **F** | Mobile + load | 🔴 **NOT STARTED — no checklist exists** | The largest un-started gap, and GalaxyCon-critical (booth is phone-first). **Mobile** = full grade→value→verdict→save on real Android+iOS + billing/portal on mobile + PWA install. **Load** = concurrent/convention-spike (R2 edge-cache already bought as spike insurance). **No detailed checklist drafted** — first step of F is writing one (devices, flows, a load target). |

**"A–E complete" is optimistic:** only **D** is cleanly done. C is run-with-open-must-fixes; E is happy-path-verified-but-lifecycle-untested; **A/B are unrecorded.** F is untouched.

---

## Launch-critical sequence (to July 21)

1. **Billing cancel-path test + step-3 fix** — declared hard gate, real money, contained. Fire an immediate cancel → confirm `plan=free` via `customer.subscription.deleted`; fix `handle_subscription_deleted` to revert only when the deleted `sub.id` matches the stored one (do alongside — same handler). ⚠️ Checkout footgun: never run real checkout/portal from a `test-*` account (writes `stripe_customer_id`).
2. **Section F — mobile (then load).** FIRST **draft the F checklist** (devices, flows, load target — doesn't exist), THEN run on real iOS/Android: full grade→value→verdict→save + billing-on-mobile + PWA install. **Load** second (edge cache already insures the spike). This is the biggest gap and the booth depends on it.
3. **C's DELETE-confirm fix** — cheap, data-loss/trust, worst on mobile mis-tap.
4. **Grading-accuracy triage** — decide blocker vs. ship-and-monitor. A burned-user complaint exists (3 comics graded off, images not retained so un-diagnosable); grade accuracy is the **unaudited half of the slab/no-slab verdict** (comps half fixed S111; grade half never calibrated — the March "End-to-end grading accuracy test / 10+ known-CGC" is still untested). Same confidence-gating question as valuation Fix B: does the grade render confidently when image quality/angle doesn't support it?
5. **New-user flow end-to-end** — overlaps with F-mobile (mobile grade→value→verdict→save IS the new-user flow on a phone). Run together.
6. **Then:** billing step-2 UX redirect; define/verify what A & B were meant to cover (close the unknowns).

---

## Post-launch / parked (recorded so they're not lost)
- **Cert-number recovery wiring** — the honest marketable slabbed-recovery headline (cert already OCR'd/stored/indexed, just unwired); lane-1, the real recovery upgrade.
- **Valuation normalization tail** — colon/subtitle/accent/token-order title classes (~14 lookups); monitor `lookup_demand` as traffic surfaces them. Plus the **⏰ Fix B gate extension to `very_low`** (exact_thin tier) once we see how often it misleads.
- **Multi-view cross-camera recovery** — the only path to recover LOW-wear raw books (single-image parked, bounded-to-high-wear; SAM + E3 engine retained). See `[[project_slabguard_crosscamera]]`.
- **eBay capture tooling / cadence** — capture is manual/bursty; demand-driven depth backfill + variant reclamation (~11K filtered comps).
- **⏰ 90-day grade-retention PURGE** — HARD DEADLINE ~2026-09-17 (published-policy obligation; after launch + GalaxyCon but cannot slip).
- **Product-wide confidence-gating audit** — the Fix-B/Slab-Guard lesson generalized: anywhere a low-confidence inference drives a confident product verdict (grade, signature, slab-guard match), gate it.
- **Grades-user re-contact** — gated on (a) improving the grading path AND (b) image retention to diagnose AND (c) a real support inbox. Not now.
- Lower-priority: ~30s comic-ID progress messaging; email setup (mike@/support@); Signatures v2 (detection gate, CORS server-fetch); resilience gap (7/12 model call sites lack `call_with_fallback`); CGC cost-sourcing audit; admin Feedback comment truncation; "0 used" usage-meter dead-counter; Dealer webhook hardening.

---

## Provenance
Assembled read-only 2026-06-27 (Session 111) from: `WHERE_WE_LEFT_OFF.md` (A–F labels + session detail), `TODO.md` (P0–P5 + Testing sections, the 47-test plan), `ROADMAP.txt`/`CLAUDE_NOTES.txt` (Session 59 lineage), and direct code verification of `routes/billing.py` (stacking guard `:525–532`, deletion handler `:797–818`). No fixes performed. Keep this file current; it is the source of truth.
