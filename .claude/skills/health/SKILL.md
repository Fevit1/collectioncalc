---
name: health
description: Full infrastructure health check for Slab Worthy
disable-model-invocation: true
---

Run a full infrastructure health check.

⚠️ Slab Worthy has **no Supabase dependency**. Its only database is Render
PostgreSQL (`collectioncalc_db`). Do not add a Supabase step to this skill.
A step here queried Supabase project `kgqnwfpklodyyiqariid` via the Supabase
MCP until 2026-08-08; that is TheFormOf's project, it is not resolvable from
this account, and the step failed silently for an unknown period. **DEAD,
removed, not repointed.** See `CLAUDE.md` § Session Conventions.

1. **API Health** — Hit the health endpoint:
   - `curl -s https://collectioncalc-docker.onrender.com/health | python -m json.tool`
   - Check `status` is "ok"
   - Report `version`, `barcode`, and `moderation` status

2. **Stripe** — Verify Stripe webhook is configured:
   - Check that `STRIPE_WEBHOOK_SECRET` is referenced in billing routes
   - ⚠️ Resolve the **exact** env var name, not a substring match (L-2026-021:
     `STRIPE_WEBHOOOK_SECRET`, three O's, read identically to a correct key)

3. **Summary** — Present a status table:
   | Service    | Status | Details |
   |------------|--------|---------|
   | API        | ✅/❌  | version |
   | Stripe     | ✅/❌  | sub counts |

   ⚠️ **Known coverage gap:** this skill no longer checks the database. The
   removed step checked the wrong platform, so removing it lost nothing that
   worked, but Render PostgreSQL is now unverified by `/health`. A replacement
   step is drafted and awaiting Mike's decision as of 2026-08-08; if he declines
   it, this gap is accepted deliberately and this note stays.
