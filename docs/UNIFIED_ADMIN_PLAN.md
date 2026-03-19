# Unified Admin Dashboard — Cross-Domain Plan

**Status:** Phases 1-3 COMPLETE — running locally at `http://localhost:8080`
**Location:** `C:/Users/mberr/theformof/index.html`
**Domains:** SlabWorthy, MASSE, TheFormOf (future placeholder)
**Last Updated:** 2026-03-12

---

## Goal

A single admin dashboard at a neutral URL that aggregates user insights, AI costs, and activity data across all Mike Berry products. One login, one view.

---

## Architecture: Standalone Frontend + Existing APIs

### How It Works

```
┌──────────────────────────────────────────────┐
│         AdminHub (index.html)                │
│  Location: C:/Users/mberr/theformof/         │
│  Server: node serve.js → localhost:8080      │
│                                              │
│  ┌─────────┐  ┌─────────┐  ┌──────────────┐ │
│  │ MASSE   │  │ SLAB    │  │ THE FORM OF  │ │
│  │ Panel   │  │ WORTHY  │  │ (greyed out) │ │
│  │         │  │ Panel   │  │              │ │
│  └────┬────┘  └────┬────┘  └──────┬───────┘ │
│       │            │              │          │
│  Combined Overview: Total Users, AI Spend,   │
│  Active Today, Feedback                      │
└───────┼────────────┼──────────────┼──────────┘
        │            │              │
        ▼            ▼              ▼
   MASSE API    SlabWorthy API   TheFormOf API
   (Render)     (Render)         (TBD)
   Supabase     PostgreSQL       TBD
```

### Auth Engine
- **SlabWorthy**: Email/password → `POST /api/auth/login` → JWT stored in localStorage
- **MASSE**: Email/password → Supabase `signInWithPassword()` → JWT → verified via `/api/admin/check`
- Connection status shown as green/red dots in header per app
- Auto-validates stored tokens on page load

---

## Implementation Status

### Phase 1: Foundation ✅ COMPLETE
- Single-file dashboard with dark theme, Tailwind CSS
- Tab bar: Overview | Slab Worthy | MASSE | The Form Of (greyed)
- Dual auth engine (JWT + Supabase SDK) with localStorage tokens
- Connection dots in header
- CORS configured on both backends for localhost:8080

### Phase 2: Combined Overview Tab ✅ COMPLETE
- Aggregated stat cards (Total Users, New This Week, AI Spend, API Calls, Codes Available, Feedback)
- Per-app breakdown within each card
- Clickable app summary cards linking to per-app tabs

### Phase 3: Per-App Panels ✅ COMPLETE
- **SlabWorthy**: Users, Beta Codes, Errors, Usage, Waitlist, Feedback, NLQ Query
- **MASSE**: Users, Invite Codes, Usage, Feedback, Scout, NLQ Query
- **TheFormOf**: Placeholder tab (greyed out, ready for config)
- Expandable user rows with activity breakdown chips
- Feedback tab with thumbs up/down, context linking, comic details

### Phase 4: Cross-App Insights — NOT STARTED
- [ ] Cross-domain user matching (same email across apps)
- [ ] Unified cost dashboard (by app, by feature, by day)
- [ ] Budget alerts
- [ ] Cross-app NLQ queries

---

## API Endpoints Used

### MASSE (Express + Supabase)
```
GET /api/admin/check          → verify admin status
GET /api/admin/dashboard      → stats (users, API costs, companies, codes, feedback)
GET /api/admin/users          → users with activity data (companies, API calls, last active, actions)
GET /api/admin/usage          → token usage (recent, by_user, by_action)
GET /api/admin/usage/trends   → daily cost trends + by_feature breakdown
GET /api/admin/invite-codes   → all invite codes with status
GET /api/admin/feedback       → feedback entries + stats
GET /api/admin/scout/runs     → recent scan logs
GET /api/admin/scout/schedule → user scan settings
GET /api/admin/funnel         → onboarding funnel data
POST /api/admin/nlq           → natural language query
```
Auth: `Authorization: Bearer <supabase_jwt>` where user ID is in ADMIN_USER_IDS env var.

### SlabWorthy (Flask + PostgreSQL)
```
GET /api/auth/me              → verify admin status (is_admin flag)
POST /api/auth/login          → email/password → JWT token
GET /api/admin/dashboard      → stats (users, requests, API costs, sales, codes)
GET /api/admin/users          → users with activity data (collections, slab guard, API calls, AI cost, feedback, actions)
GET /api/admin/beta-codes     → all beta codes
GET /api/admin/errors         → recent failed requests
GET /api/admin/usage          → Anthropic API usage (30-day summary)
GET /api/admin/feedback       → user feedback with comic context (title, issue, grade, photos)
GET /api/admin/waitlist       → waitlist signups
POST /api/admin/nlq           → natural language query
```
Auth: `Authorization: Bearer <jwt>` where user is_admin = true.

---

## Adding a New App Checklist

When TheFormOf (or any new app) is ready:

1. Build `/api/admin/dashboard` and `/api/admin/users` endpoints (minimum)
2. Add CORS header for `http://localhost:8080` (and production URL when deployed)
3. Add app config to `index.html` APPS array:
   ```js
   {
     id: 'theformof',
     name: 'The Form Of',
     icon: '✦',
     color: '#f59e0b',
     apiBase: 'https://theformof.com',
     authType: 'supabase', // or 'jwt'
     tokenKey: 'adminhub_token_theformof',
     endpoints: { dashboard: '/api/admin/dashboard', users: '/api/admin/users', ... },
     parseStats: (data) => ({ totalUsers: data?.stats?.users?.total || 0, ... }),
     subTabs: ['users', 'codes', ...],
     subTabLabels: { users: 'Users', ... }
   }
   ```
4. Remove from FUTURE_APPS array, add to APPS array
5. Done — overview cards, tabs, and dots auto-generate

---

## Running Locally

```bash
cd C:/Users/mberr/theformof
npm install    # first time only
node serve.js  # starts on http://localhost:8080
```

## Future Hosting Options

| Option | Pros | Cons |
|--------|------|------|
| **theformof.com/admin** | Already own domain | Ties to future app |
| **GitHub Pages** (free) | Zero cost, auto-deploy | Public URL (but auth-gated) |
| **Render Static Site** (free) | Same platform as apps | Another Render service |
| **Subfolder on existing app** | No new deploy needed | Couples to one app |

---

## Notes

- Both apps use the same Anthropic API key — cost tracking captures which app via the `action` field
- SlabWorthy uses traditional JWT auth; MASSE uses Supabase auth — AdminHub handles both
- For TheFormOf, decide early whether to use Supabase or PostgreSQL — affects admin API pattern
- AdminHub is ~1200 lines of vanilla HTML/JS + Tailwind CDN — no build step needed
