# Slab Worthy — Claude Code Project Context

**Founder:** Mike Berry (Don Michael Berry II)
**Last Updated:** 2026-03-14

---

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
- **Deploy:** `git push` → Render auto-deploys
- **Health check:** `curl https://collectioncalc-docker.onrender.com/health`

### Three Patents (All Filed)
1. Multi-Angle Grading System (Jan 27, 2026)
2. Comic Fingerprinting Theft Recovery (Feb 12, 2026)
3. Signature Identification (Feb 25, 2026 — App #63/990,743)

---

## Session Conventions

- **Skills:** `/deploy-tfo`, `/health`, `/lesson`, `/stripe-test` (in `.claude/skills/`)
- **Session notes:** CLAUDE_NOTES.txt (full history), WHERE_WE_LEFT_OFF.md (last session detail)
- **Task list:** TODO.md
- **Supabase project ID:** `kgqnwfpklodyyiqariid` (TheFormOf — shared DB)

---

## Current Priorities

1. eBay listing end-to-end test (draft + auction)
2. Marketplace prep testing (Whatnot, Mercari, etc.)
3. Signature v2 — upload refs for 57 new creators, target 87%+ accuracy
4. Mobile testing on real devices
5. GalaxyCon sprint plan (25 weeks to Aug 21)

---

## Related Project

**TheFormOf (TFO)** — AI-native app dev platform. Separate repo at `C:\Users\mberr\TheFormOf`.
See that project's `CLAUDE.md` and `TFO_EXECUTIVE_SUMMARY.md` for TFO context.
