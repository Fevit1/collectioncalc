---
name: stripe-test
description: Verify Stripe payment pipeline end-to-end
disable-model-invocation: true
---

Verify the Stripe payment pipeline is working:

1. **Config Check** — Verify Stripe environment variables are referenced:
   - Check `routes/billing.py` for `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
   - Check that price IDs are configured for all plans (pro, guard, dealer)

2. **Database State** — Note: subscription data lives in the Render Postgres DB, not Supabase.
   Check billing route code for the database queries used to manage subscriptions.

3. **Recent Activity** — Review billing route logs or check the Render DB for recent webhook activity.

4. **Webhook Endpoint** — Verify the webhook route is registered:
   - Confirm `POST /api/billing/webhook` exists in billing blueprint
   - List handled event types: checkout.session.completed, customer.subscription.updated, customer.subscription.deleted, invoice.payment_succeeded, invoice.payment_failed

5. **Summary** — Report:
   | Check          | Status | Details |
   |----------------|--------|---------|
   | Config         | ✅/❌  | env vars |
   | DB Connection  | ✅/❌  | sub counts |
   | Webhook Route  | ✅/❌  | events handled |
   | Recent Activity| ✅/❌  | last payment date |
