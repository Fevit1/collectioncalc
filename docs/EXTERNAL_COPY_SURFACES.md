# External Copy Surfaces — everything a user reads that `grep` cannot reach

> **Operator:** Mike Berry · **Created:** 2026-08-12 · **Companion to:** `docs/LESSONS.md`
> **L-SW-2026-021**
>
> **Read this during any claims sweep, honesty pass, or feature retirement.** A completeness
> sweep over the repo is complete only with respect to the repo. Every surface below is
> user-visible, carries product claims, and is **invisible to `grep`, to tests, and to code
> review** — nothing moves it when the product moves.

## Why this file exists

The Stripe product description carried *"Unlimited comic valuations with price history and
collection tracking"* until **2026-08-12**. The same "Unlimited" claim was removed from
`pricing.html` in the **June tier-honesty pass**. It survived that pass and every sweep since
for exactly one reason: **it is not in the repo.**

By then it was false three ways — Pro is 100 gradings/month and hard-enforced with a 429;
"price history" describes no feature that exists in any state; and "collection tracking" is
something free users get. It sat on the **hosted Stripe Checkout page — the last screen a user
reads before paying.**

The general shape: **third-party copy cannot fail a test, cannot be grepped, and does not
change when the code changes.** That is how a retired claim outlives its own retirement.

## The test for inclusion

> **Can a user read it, and can `grep` reach it?**

If the answer is *yes / no*, it belongs in this file.

## The surfaces

| # | surface | where it is edited | what it can claim | last audited |
|---|---|---|---|---|
| 1 | **Stripe product & price descriptions** — rendered on hosted Checkout | Stripe dashboard → Products | tier capabilities, limits, feature names | **2026-08-12 — corrected** |
| 2 | **Stripe customer-portal product names** | Stripe dashboard → Billing → Customer portal | tier names shown to existing subscribers on upgrade/downgrade | ⚠️ **never audited** |
| 3 | **Resend email templates / any copy not built from `auth.py`** | Resend dashboard | verification + notification wording, sender identity | ⚠️ **never audited** |
| 4 | **Cloudflare-hosted copy** — redirect pages, error pages, Access/WAF block pages, Email Routing bounce text | Cloudflare dashboard | whatever a user hits when something fails | ⚠️ **never audited** |
| 5 | *(future)* app-store / marketplace listings, Chrome Web Store listing if the extensions are ever published | respective consoles | everything | n/a |

⚠️ **Stripe's customer portal is a live one, not a hypothetical.** `routes/billing.py` already
carries a warning that the portal is a separate path `COMING_SOON_PLANS` cannot reach — a tier
listed there must **also** be removed from the portal's switchable products in the dashboard, or
an existing subscriber can switch into a tier the server refuses to sell. Copy and capability
have the same hole in the same place.

## Rules

1. **When a claim is retired anywhere, enumerate its surfaces before closing the item** — this
   file plus the repo, not the repo alone. One decision, more than one edit
   (`L-SW-2026-019` / cross-project `L-2026-026`).
2. **Write the claim from the enforcement, never from memory or from the previous copy.** The
   corrected Stripe description was written from an entitlement table built by resolving the
   *reader* for every `PLANS` key — which is also what surfaced a false positive that had been
   sitting inside the June audit for ten weeks.
3. **Record the audit date in the table above even when nothing changed.** A surface found
   correct gets a tombstone, or the next sweep re-raises it and someone eventually "fixes"
   accurate copy (`L-SW-2026-014`).
4. **Never delete a row from this table.** A surface that stops being used is marked retired,
   with the date. Deletion and never-known-about look identical to the next reader.

## Current entitlement ground truth (measured 2026-08-12)

What Pro actually buys over Free, **server-enforced only**:

| capability | free | pro | enforced at |
|---|---|---|---|
| Monthly gradings | 25 | **100** | `routes/grading.py:580` → 429 |
| Slab Guard registrations | 3 | **25** | `routes/registry.py:530` |
| Extra photos per comic | 0 | **4** | `routes/images.py:325`, limit `:338` |

Everything else in `PLANS` is either identical across the two tiers or **advertised and not
enforced** (`export`, `multi_photo`). `bulk_operations` has **zero readers anywhere** — it is
dead, not disabled. Full table and the reasoning: `docs/LESSONS.md` L-SW-2026-021 and
`docs/sessions/WHERE_WE_LEFT_OFF.md` (2026-08-12).

⚠️ **Do not quote this table into user-facing copy without re-measuring.** It is a snapshot of
readers on one day, and the whole point of this file is that snapshots go stale silently.
