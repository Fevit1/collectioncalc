# Stripe TEST-mode Setup Map + Safe Billing-Test Runbook (Section E prep)

> Read-only map of the billing stack + the safe procedure to test checkout/portal end-to-end in
> Stripe **test mode** (fake money). Drafted Session 107 from the code; **values that live in Render
> env / the Stripe dashboard are NOT in the repo and must be confirmed there** (flagged below).
> Mike runs the actual test as its own focused session.

---

## PART A — Setup map

### 1. Keys
- **Secret key:** `STRIPE_SECRET_KEY` (Render env) → `stripe.api_key` (`routes/billing.py:38`). Mike confirmed `sk_test_…` → **test mode**. ✅
- **Publishable key: NOT USED — and that's fine.** Checkout is **server-created Stripe-hosted Checkout**: `create-checkout` calls `stripe.checkout.Session.create(...)` and returns `session.url`; `pricing.html:967` just does `window.location.href = data.checkout_url`. There is **no Stripe.js and no `pk_` anywhere in the frontend** (grep-confirmed). So the classic *"test secret + live publishable"* mismatch **can't happen here** — one less failure mode.
- **Where configured:** all Stripe config is **Render env vars**. The local `.env` has **no** Stripe vars (grep-confirmed) — so nothing to reconcile locally.

### 2. Price / product IDs — ⚠️ THE #1 THING TO VERIFY
- Price IDs are **not hardcoded**; `create-checkout` reads them from env via PLANS:
  - Pro: `STRIPE_PRO_MONTHLY_PRICE`, `STRIPE_PRO_ANNUAL_PRICE`
  - Guard: `STRIPE_GUARD_MONTHLY_PRICE`, `STRIPE_GUARD_ANNUAL_PRICE`
  - Dealer: `STRIPE_DEALER_*` — **irrelevant**: `create-checkout` refuses `plan='dealer'` server-side (`billing.py:490`).
- Selection: `price_id = PLANS[plan]['stripe_{billing_period}_price_id']` (`billing.py:500-501`). If unset → **500 "Price not configured"**.
- **FLAG — verify in Render → Environment:** the `STRIPE_*_PRICE` values must be **TEST-mode** price IDs (created under the Stripe **test** dashboard). Test and live price IDs are *different objects*; a live price ID used with the `sk_test` key fails checkout with **"No such price"**. This is the single most common silent break of test-mode checkout. I **cannot see the env values from the repo** — confirm them on Render. (Sanity check: with the test key, `stripe.Price.retrieve("<id>")` succeeds only for test prices.)

### 3. Webhook — ⚠️ test mode has its OWN endpoint + secret
- **Endpoint:** `POST /api/billing/webhook` → `https://collectioncalc-docker.onrender.com/api/billing/webhook` (`billing.py:588`).
- **Secret is MANDATORY:** reads `STRIPE_WEBHOOK_SECRET` per-request; if unset → **500, refuses to process** (won't accept unverified events). Verifies signature via `stripe.Webhook.construct_event`; bad signature → **400**.
- **Events handled:** `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`.
- **FLAG — verify in Render + Stripe test dashboard:** Stripe **test mode has a separate webhook endpoint with its own `whsec_…` signing secret** from live. The Render `STRIPE_WEBHOOK_SECRET` must be the **TEST** endpoint's secret. If Render holds the *live* secret while Stripe sends *test* events, every webhook fails signature verification (**400**) → **checkout completes but the tier never updates** → looks broken when it isn't. Confirm: Stripe (test toggle ON) → Developers → Webhooks → an endpoint pointing at the URL above, subscribed to at least `checkout.session.completed` + `customer.subscription.*` + `invoice.payment_*`, and its signing secret == Render's `STRIPE_WEBHOOK_SECRET`.

### 4. Tier-update path (what to verify changed)
On `checkout.session.completed` → `handle_checkout_completed` (`billing.py:646`):
- reads `session.metadata.user_id` + `.plan` + `.billing_period`, plus `session.subscription` + `session.customer`
- → `update_user_subscription(user_id, plan, stripe_customer_id, stripe_subscription_id, status='active', billing_period)`
- which writes the **`users`** row: `plan`, `stripe_customer_id`, `stripe_subscription_id`, `subscription_status`, `billing_period`, `current_period_end` (`billing.py:180-216`).

Then `customer.subscription.updated` finds the user by `stripe_customer_id` and updates `subscription_status` + `current_period_end`.

- **⚠️ Trial note:** checkout creates the sub with `trial_period_days: 14` (`billing.py:537`). During the trial the Stripe subscription status is **`trialing`**, so after `customer.subscription.updated` lands, `my-plan` will likely show **`subscription_status: "trialing"`**, not `"active"`. **Both count as entitled** (paid gates accept `active`/`trialing`) — don't mistake `trialing` for broken. No card charge happens until the trial ends, so `invoice.payment_succeeded` won't fire on day 0.
- **Verification endpoint:** `GET /api/billing/my-plan` (`billing.py:407`) returns `plan`, `subscription_status`, `billing_period`, `current_period_end`, and usage limits. (`account.html:646` already calls it.)

---

## PART B — Safe billing-test runbook

### Account — use a THROWAWAY, never the protected test-tier accounts
- **Do NOT** run checkout/portal on `test-pro@ / test-guard@ / test-dealer@slabworthy.test`. Test mode removes the **money** risk but **not** the **tier-clobber** risk: `create-checkout` creates a Stripe customer and writes `stripe_customer_id` to the user row **immediately, before checkout completes** (`billing.py:516-523`). Once a customer_id is on a row, webhooks match on it and rewrite that account's manually-set tier.
- **Recommended:** a dedicated **`billing-test@…`** inbox you control (real email, so the portal/receipts work). Sign it up normally at `/login.html`, then **approve it in admin** (new signups are gated by `require_approved` + waitlist; `create-checkout` itself only needs auth, but you'll want a usable approved account). **Leave its tier untouched** (don't manually set plan) so the only thing that can flip it is billing — that's the whole point of the test.

### Test cards (test mode only)
- **Success:** `4242 4242 4242 4242`, any future expiry, any CVC, any ZIP.
- **Decline (generic):** `4000 0000 0000 0002`. **Insufficient funds:** `4000 0000 0000 9995`.
- **3-D Secure (auth required):** `4000 0025 0000 3155`.

### Pre-flight (read-only — before clicking anything)
1. Render env: `STRIPE_SECRET_KEY` starts `sk_test`; `STRIPE_PRO_*`/`STRIPE_GUARD_*_PRICE` are **test** price IDs (Part A.2); `STRIPE_WEBHOOK_SECRET` is the **test** endpoint's secret (Part A.3).
2. Stripe dashboard **test toggle ON** → Developers → Webhooks → endpoint = the `/api/billing/webhook` URL, subscribed to the events in Part A.3.

### Steps — checkout
1. Log in as the approved throwaway. `GET /api/billing/my-plan` → confirm `plan: "free"`.
2. From `pricing.html`, start **Pro / monthly** (or `POST /api/billing/create-checkout` `{ "plan": "pro", "billing_period": "monthly" }`). You'll be redirected to Stripe-hosted Checkout — confirm the **"TEST MODE"** banner is visible.
3. Pay with `4242 4242 4242 4242` → complete. You land on `account.html?status=success`.
4. **Confirm the webhook fired (check BOTH):**
   - Stripe test dashboard → Developers → Webhooks → the endpoint → **Recent deliveries**: `checkout.session.completed` = **200** (also `customer.subscription.created/updated`).
   - Render logs: `[Billing] Webhook: checkout.session.completed` then `[Billing] Checkout completed: user=<id>, plan=pro`.
   - **If you see 400 here → wrong-mode `STRIPE_WEBHOOK_SECRET`. If 500 → secret unset.** (Part A.3)
5. **Verify the tier flipped:** `GET /api/billing/my-plan` → `plan: "pro"`, `subscription_status: "trialing"` (or `"active"`), `usage.valuations_limit: 100`. In the DB `users` row: `plan='pro'`, `subscription_status` set, `stripe_customer_id` + `stripe_subscription_id` populated. Grading cap now reflects Pro (100).
6. **Guard:** repeat with `{ "plan": "guard" }` → expect `valuations_limit: 250`. **Use a fresh throwaway (or reset first)** — switching plans on the *same* customer is a proration/upgrade path, not a clean first-subscribe; for clean per-plan verification, one throwaway per plan is simplest.

### Steps — customer portal (manage / cancel)
7. `POST /api/billing/customer-portal` (the throwaway must have a `stripe_customer_id`) → returns a portal session URL → open it → test **update card** and **cancel subscription**.
8. On cancel, Stripe sends `customer.subscription.deleted` → `handle_subscription_deleted` reverts the user to **free** → verify `my-plan` shows `plan: "free"`. (Confirm the delivery is 200 in the webhook log.)

### Steps — decline path (optional)
9. Fresh throwaway → checkout with `4000 0000 0000 0002` → expect the payment to fail on the Stripe page, **no** `checkout.session.completed`, tier stays `free`.

### Reset a throwaway between runs
- Cancel its subscription first (portal, or Stripe test dashboard → Customers → cancel).
- Then reset the `users` row (read-write DB — Render-shell Python or psql):
  ```sql
  UPDATE users
     SET plan='free', subscription_status='none',
         stripe_subscription_id=NULL, stripe_customer_id=NULL,
         billing_period=NULL, current_period_end=NULL
   WHERE email='billing-test@...';
  ```
  Clearing `stripe_customer_id` makes the next run create a clean new customer (avoids stacking subs on one customer). **Simplest of all: just make a brand-new throwaway each run.**

### What NOT to do (footguns, plainly)
- ❌ No checkout/portal on `test-pro/guard/dealer@slabworthy.test` (tier-clobber via the immediate `stripe_customer_id` write-back).
- ❌ No live keys, no pointing at the live webhook endpoint, no live price IDs.
- ❌ Don't manually set the throwaway's `plan` — let billing drive it, or you can't tell what actually flipped the tier.

### How to confirm the webhook fired (always check both)
- **Stripe test dashboard** → Developers → Webhooks → endpoint → **Recent deliveries** (per-event response code: 200 good · 400 = signature/secret-mode mismatch · 500 = secret unset).
- **Render logs** → `[Billing] Webhook: <event>` lines.

---

## Open items for Mike to confirm in the dashboards (not visible in repo)
1. **`STRIPE_*_PRICE` env values are test-mode price IDs** (Part A.2) — the #1 silent break.
2. **`STRIPE_WEBHOOK_SECRET` on Render == the Stripe TEST webhook endpoint's secret** (Part A.3).
3. A **test-mode webhook endpoint** exists pointing at `/api/billing/webhook` with the right events.

If all three hold, Section E is "follow Part B."
