---
name: health
description: Full infrastructure health check for TheFormOf
disable-model-invocation: true
---

Run a full infrastructure health check:

1. **API Health** — Hit the health endpoint:
   - `curl -s https://collectioncalc-docker.onrender.com/health | python -m json.tool`
   - Check `status` is "ok"
   - Report `version`, `barcode`, and `moderation` status

2. **Database** — Verify Supabase/Postgres connectivity (project ID: `kgqnwfpklodyyiqariid`):
   - Use the Supabase MCP to run: `SELECT NOW(), current_database(), pg_size_pretty(pg_database_size(current_database()))`
   - Report connection status and DB size
   - List tables with `list_tables` and report row counts

3. **Stripe** — Verify Stripe webhook is configured:
   - Check that `STRIPE_WEBHOOK_SECRET` is referenced in billing routes
   - Note: Stripe/subscription data lives in the Render Postgres DB, not Supabase

4. **Summary** — Present a status table:
   | Service    | Status | Details |
   |------------|--------|---------|
   | API        | ✅/❌  | version |
   | Database   | ✅/❌  | size    |
   | Stripe     | ✅/❌  | sub counts |
