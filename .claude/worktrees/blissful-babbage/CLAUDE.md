# Slab Worthy + TheFormOf — Claude Code Project Context

**Founder:** Mike Berry (Don Michael Berry II)
**Last Updated:** 2026-03-14

---

## Two Projects, One Repo

### Slab Worthy (SW) — The Product
AI-powered comic book grading tool. Upload 4 photos, get CGC-equivalent grade + FMV.

- **Live:** slabworthy.com
- **API:** collectioncalc-docker.onrender.com
- **Stack:** Flask/Python, PostgreSQL (Render), Cloudflare R2, Claude API
- **Frontend:** Vanilla HTML/CSS/JS (no framework)
- **Target:** GalaxyCon San Jose alpha launch (Aug 21-23, 2026)
- **Revenue:** Pre-revenue, 4-tier Stripe billing live (Free/Pro/Guard/Dealer)

### TheFormOf (TFO) — The Platform
AI-native app development service. Orchestrates specialized AI agents to build client apps.

- **Site:** theformof.com (frontend only, no backend yet)
- **Database:** Supabase (project ID: `kgqnwfpklodyyiqariid`)
- **Tables:** tfo_agents (17), tfo_cabinet (6), tfo_builds (1), tfo_lessons (1), tfo_milestones (0), tfo_capabilities (0), tfo_clients (0)
- **Stage:** Foundation — schema designed, first payment received, agent roster defined

---

## Key Architecture

### SW Backend (this repo)
- **Entry:** `wsgi.py` → gunicorn
- **Routes:** 19 blueprints in `routes/` (~87 endpoints)
- **Critical routes:** `/health`, `/api/grade`, `/api/billing/webhook`, `/api/signatures/v2/match`
- **Deploy:** `git push` → Render auto-deploys

### TFO Agent System (Supabase)
- **7 Lead agents:** ORCHESTRATOR, ARCHITECT, SENTINEL, PULSE, BROKER, HERALD, ANALYST
- **10 Specialist agents:** SCHEMA, ENDPOINTS, INTERFACE, GATEKEEPER, LAUNCH, PROBE, TEMPO, METRICS, ACCESS, VOICE
- **6 Cabinet advisors:** COACH, HORIZON, ATLAS, LEDGER, FUTURIST, PHILOSOPHER
- **Knowledge system:** tfo_lessons (what went wrong) → tfo_capabilities (what we can do) → agent promotion

### Three Patents (All Filed)
1. Multi-Angle Grading System (Jan 27, 2026)
2. Comic Fingerprinting Theft Recovery (Feb 12, 2026)
3. Signature Identification (Feb 25, 2026 — App #63/990,743)

---

## Session Conventions

- **Skills:** `/deploy-tfo`, `/health`, `/lesson`, `/stripe-test` (in `.claude/skills/`)
- **Docs to update together:** CLAUDE.md + TFO_EXECUTIVE_SUMMARY.md (always update both)
- **Session notes:** CLAUDE_NOTES.txt (SW history), WHERE_WE_LEFT_OFF.md (last session detail)
- **Supabase project ID:** `kgqnwfpklodyyiqariid` (TheFormOf)
- **Health endpoint:** `curl https://collectioncalc-docker.onrender.com/health`

---

## Current Priorities

### Slab Worthy
1. eBay listing end-to-end test (draft + auction)
2. Marketplace prep testing (Whatnot, Mercari, etc.)
3. Signature v2 — upload refs for 57 new creators, target 87%+ accuracy
4. Mobile testing on real devices
5. GalaxyCon sprint plan (25 weeks to Aug 21)

### TheFormOf
1. First build execution (Blueprint stage, payment received)
2. CEO orchestration engine (agent routing + lesson injection)
3. Capability auto-detection from lessons (Month 3-4)
4. Client onboarding flow

See `TFO_EXECUTIVE_SUMMARY.md` for detailed TFO status.
See `TODO.md` for detailed SW task list.
