# Slab Worthy — Claude Code Project Context

**Founder:** Mike Berry (Don Michael Berry II)
**Last Updated:** 2026-03-19

> SESSION OPENING PROTOCOL — read in this order before any substantive work:
> 1. This CLAUDE.md
> 2. docs/LESSONS.md if it exists (confirm: 'Read LESSONS.md — N lessons, updated YYYY-MM-DD')
> 3. C:\Users\mberr\.claude\projects\shared\LESSONS_CROSS_PROJECT.md
>    (confirm: 'Read LESSONS_CROSS_PROJECT.md — N lessons active')
>
> Then emit the 6-line context summary before proceeding with any substantive work.

---

# ⚠️ THIS IS SLAB WORTHY (collectioncalc repo)
# Brand: $LAB WORTHY — purple/gold, comic grading, CGC authentication
# Favicon: /favicon.svg (gold dollar sign on black background, 8° tilt)
# Logo font: Bangers, gold (#facc15), purple accent (#7c3aed)
# DO NOT apply MASSÉ branding (8-ball, red #C0392B, billiards, IBM Plex)
# DO NOT apply TFO branding (theformof.com, agentic app platform)
# GitHub repo: Fevit1/collectioncalc
# Deploy: Cloudflare Pages (slabworthy.com) + Render backend
#
# ⚠️ GIT COMMIT RULE — ALWAYS run this before git add:
#   git status
# Review every file listed. Ask yourself:
#   - Does this file belong to THIS project?
#   - Is this a .claude/ worktree file? (never commit these)
#   - Is this a ~$ Excel temp file? (never commit these)
# Only then run: git add [specific files] — NEVER git add -A blindly


## What This Is
AI-powered comic book grading tool. Upload 4 photos, get CGC-equivalent grade + FMV.

- **Live:** slabworthy.com
- **API:** collectioncalc-docker.onrender.com
- **Stack:** Flask/Python, PostgreSQL (Render), Cloudflare R2, Claude API
- **Frontend:** Vanilla HTML/CSS/JS (no framework)
- **Target:** GalaxyCon San Jose alpha launch (Aug 21-23, 2026)
- **Revenue:** Pre-revenue, 4-tier Stripe billing live (Free/Pro/Guard/Dealer)

---

## Key Architecture

- **Entry:** `wsgi.py` → gunicorn
- **Routes:** 19 blueprints in `routes/` (~87 endpoints)
- **Critical routes:** `/health`, `/api/grade`, `/api/billing/webhook`, `/api/signatures/v2/match`
- **Deploy:** push to `main`, then deploy on Render. Auto-deploy-on-push is UNRELIABLE for collectioncalc-docker — sometimes it fires, often it does not. After pushing, verify the deploy actually started in the Render dashboard (Events tab); if not, trigger it manually: Manual Deploy → Deploy latest commit, and confirm the commit hash matches what you pushed. Do not assume a push deployed.
- **Health check:** `curl https://collectioncalc-docker.onrender.com/health`

### Three Patents (All Filed)
1. Multi-Angle Grading System (Jan 27, 2026)
2. Comic Fingerprinting Theft Recovery (Feb 12, 2026)
3. Signature Identification (Feb 25, 2026 — App #63/990,743)

---

## Session Conventions

- **Skills:** `/deploy-tfo`, `/health`, `/lesson`, `/stripe-test` (in `.claude/skills/`)
- **Session notes:** docs/sessions/CLAUDE_NOTES.txt (full history), docs/sessions/WHERE_WE_LEFT_OFF.md (last session detail)
- **Roadmap:** docs/sessions/ROADMAP.txt (mixed planning + session log; treat session log portions as historical)
- **Task list:** TODO.md
- **BO primer (Slab Worthy specific):** docs/SW_BO_PRIMER.md (mirror of the file uploaded to BO project storage)
- **Supabase project ID:** `kgqnwfpklodyyiqariid` (TheFormOf — shared DB)

---

## Current Priorities

1. eBay listing end-to-end test (draft + auction)
2. Marketplace prep testing (Whatnot, Mercari, etc.)
3. Signature v2 — upload refs for 57 new creators, target 87%+ accuracy
4. Mobile testing on real devices
5. GalaxyCon sprint plan (25 weeks to Aug 21)

---

## Mandatory: Third-Party Dependency Rules

When adding ANY new third-party service, API, or SDK to Slab Worthy:

1. **Add monitoring** in `dependency_monitor.py` — register the service in `MONITORED_SERVICES` with its check URL/feed and the APIs or packages we depend on. This is NOT optional.
2. **Add error handling** — every external call must have a try/except and a graceful degradation path (feature flag like `SERVICE_AVAILABLE`).
3. **Document env vars** — add any new API keys or config to `docs/technical/ARCHITECTURE.txt`.
4. **Test the monitor** — after adding, hit `/api/admin/dependency-status` to verify the new service appears.

Current monitored services: Anthropic (models), eBay (API deprecations), Stripe (SDK version).

---

## Related Project

**TheFormOf (TFO)** — AI-native app dev platform. Separate repo at `C:\Users\mberr\TheFormOf`.
See that project's `CLAUDE.md` and `TFO_EXECUTIVE_SUMMARY.md` for TFO context.
