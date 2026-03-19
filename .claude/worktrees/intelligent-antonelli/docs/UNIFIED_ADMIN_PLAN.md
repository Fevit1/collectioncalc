# Unified Admin Dashboard — Cross-Domain Plan

**Status:** Planning (not started)
**Domains:** SlabWorthy, MASSE, TheFormOf (future)
**Last Updated:** 2026-03-11

---

## Goal

A single admin dashboard at a neutral URL that aggregates user insights, AI costs, and activity data across all Mike Berry products. One login, one view.

---

## Recommended Architecture: Option 1 — Standalone Frontend + Existing APIs

### Why This Approach
- Both apps already have rich `/api/admin/*` endpoints returning JSON
- No new backend service needed — just a static HTML page
- Each app keeps its own auth and data ownership
- Adding a new domain (TheFormOf) = adding one more API config

### How It Works

```
┌──────────────────────────────────────────────┐
│           unified-admin.html                 │
│  (hosted on any domain or GitHub Pages)      │
│                                              │
│  ┌─────────┐  ┌─────────┐  ┌──────────────┐ │
│  │ MASSE   │  │ SLAB    │  │ THE FORM OF  │ │
│  │ Panel   │  │ WORTHY  │  │ Panel        │ │
│  │         │  │ Panel   │  │ (future)     │ │
│  └────┬────┘  └────┬────┘  └──────┬───────┘ │
│       │            │              │          │
│  Combined Overview: Total Users, AI Spend,   │
│  Active Today, Revenue (future)              │
└───────┼────────────┼──────────────┼──────────┘
        │            │              │
        ▼            ▼              ▼
   MASSE API    SlabWorthy API   TheFormOf API
   (Render)     (Render)         (TBD)
   Supabase     PostgreSQL       TBD
```

---

## Implementation Steps

### Phase 1: Foundation (2-3 hours)

1. **Create `admin.html`** — single-file dashboard (like SlabWorthy's current admin.html pattern)
   - Dark theme matching existing apps
   - Tab bar: Overview | MASSE | Slab Worthy | The Form Of
   - Store auth tokens in localStorage per domain

2. **Add CORS headers** to both backends for the admin domain:
   - MASSE (`backend/server.js`): Add admin domain to allowed origins
   - SlabWorthy (`wsgi.py`): Add admin domain to Flask-CORS config
   - Only allow GET requests from the admin domain (read-only)

3. **Auth flow** — on first visit, prompt for credentials per app:
   - MASSE: Email/password → Supabase JWT token
   - SlabWorthy: Email/password → JWT token
   - Store tokens in localStorage, auto-refresh on expiry
   - Show connection status per app (green dot / red dot)

### Phase 2: Combined Overview Tab

4. **Overview cards** — aggregated across all connected apps:

   | Card | Source |
   |------|--------|
   | Total Users | SUM of all app user counts |
   | Active Today | Users with activity in last 24h |
   | AI Spend (Month) | SUM of Anthropic API costs |
   | AI Spend (Today) | SUM of today's costs |
   | Total Feedback | Combined feedback count |
   | Apps Connected | Count of successfully authed apps |

5. **Combined user timeline** — recent activity across all apps:
   - "Mike@email.com graded a comic on SlabWorthy (2m ago)"
   - "Jane@email.com ran Scout scan on MASSE (15m ago)"
   - Pulls from each app's activity data and merges by timestamp

### Phase 3: Per-App Panels

6. **MASSE panel** — mirrors current Admin tab:
   - Calls: `/api/admin/dashboard`, `/api/admin/users`, `/api/admin/usage`
   - Shows: Users table (same enhanced view), Usage trends, Scout runs, Invite codes

7. **SlabWorthy panel** — mirrors current admin.html:
   - Calls: `/api/admin/dashboard`, `/api/admin/users`, `/api/admin/usage`
   - Shows: Users table (same enhanced view), Slab Guard stats, Beta codes, Errors

8. **TheFormOf panel** — placeholder until app is built:
   - Shows: "Coming soon" or connects once API exists
   - Same pattern: `/api/admin/dashboard`, `/api/admin/users`

### Phase 4: Cross-App Insights (Future)

9. **Cross-domain user matching** — if same email across apps:
   - Show unified profile: "mike@email.com uses MASSE + SlabWorthy"
   - Combined activity timeline per user

10. **Cost dashboard** — Anthropic spend breakdown:
    - By app, by feature, by day
    - Budget alerts (e.g., "SlabWorthy exceeded $5 today")

11. **NLQ across apps** — "How many users signed up this week across all apps?"
    - Route query to appropriate app or aggregate results

---

## Hosting Options

| Option | Pros | Cons |
|--------|------|------|
| **GitHub Pages** (free) | Zero cost, auto-deploy from repo | Public URL (but auth-gated) |
| **Render Static Site** (free) | Same platform as apps | Another Render service |
| **Subfolder on existing app** | No new deploy needed | Couples to one app |
| **theformof.com/admin** | Already own domain | Ties to future app |

**Recommendation:** Host on one of the existing domains as `/admin-hub.html` for now. Move to its own domain later if needed.

---

## API Endpoints Already Available

### MASSE (Express + Supabase)
```
GET /api/admin/dashboard     → stats (users, API costs, companies, codes, feedback)
GET /api/admin/users         → users with activity data (companies, API calls, last active, actions breakdown)
GET /api/admin/usage         → token usage (recent, by_user, by_action)
GET /api/admin/usage/trends  → daily cost trends + by_feature breakdown
GET /api/admin/invite-codes  → all invite codes with status
GET /api/admin/feedback      → feedback entries + stats
GET /api/admin/scout/runs    → recent scan logs
GET /api/admin/scout/schedule → user scan settings
GET /api/admin/funnel        → onboarding funnel data
POST /api/admin/nlq          → natural language query
```
Auth: `Authorization: Bearer <supabase_jwt>` where user ID is in ADMIN_USER_IDS env var.

### SlabWorthy (Flask + PostgreSQL)
```
GET /api/admin/dashboard     → stats (users, requests, API costs, sales, codes)
GET /api/admin/users         → users with activity data (collections, slab guard, API calls, AI cost, feedback, actions breakdown)
GET /api/admin/beta-codes    → all beta codes
GET /api/admin/errors        → recent failed requests
GET /api/admin/usage         → Anthropic API usage (30-day summary)
GET /api/admin/feedback      → user feedback entries
GET /api/admin/waitlist      → waitlist signups
GET /api/admin/slab-guard-stats → registrations, sightings, theft reports
GET /api/admin/barcode-stats → barcode scan coverage
POST /api/admin/nlq          → natural language query
```
Auth: `Authorization: Bearer <jwt>` where user is_admin = true.

### TheFormOf (TBD)
- Will follow same pattern: `/api/admin/*` endpoints
- Same auth pattern as whichever stack is chosen

---

## Adding a New App Checklist

When TheFormOf (or any new app) is ready:

1. Build `/api/admin/dashboard` and `/api/admin/users` endpoints (minimum)
2. Add CORS header for the unified admin domain
3. Add app config to the unified dashboard:
   ```js
   const APPS = [
     { id: 'masse', name: 'MASSE', apiBase: 'https://masse-api.onrender.com', color: '#e94560' },
     { id: 'slabworthy', name: 'Slab Worthy', apiBase: 'https://slabworthy.com', color: '#6366f1' },
     { id: 'theformof', name: 'The Form Of', apiBase: 'https://theformof.com', color: '#10b981' }
   ];
   ```
4. Add auth flow for the new app
5. Add per-app panel tab
6. Done — overview cards auto-aggregate

---

## Estimated Effort

| Phase | Time | Priority |
|-------|------|----------|
| Phase 1: Foundation | 2-3 hours | When 3rd app exists or beta testers scale |
| Phase 2: Overview | 1-2 hours | Same time as Phase 1 |
| Phase 3: Per-app panels | 2-3 hours | Copy existing admin UIs |
| Phase 4: Cross-app insights | 3-4 hours | Nice-to-have, do later |

**Total: ~8-12 hours of work when ready.**

---

## Notes

- Both apps currently use the same Anthropic API key — cost tracking already captures which app made the call via the `action` field
- SlabWorthy uses traditional JWT auth; MASSE uses Supabase auth — the unified dashboard needs to handle both
- For TheFormOf, decide early whether to use Supabase (like MASSE) or PostgreSQL (like SlabWorthy) — this affects the admin API pattern
- The NLQ feature in both apps could be extended to query across databases, but that's Phase 4 territory
