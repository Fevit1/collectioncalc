# Slab Worthy — Claude Code Project Context

**Founder:** Mike Berry (Don Michael Berry II)
**Last Updated:** 2026-03-19

> SESSION OPENING PROTOCOL — read in this order before any substantive work:
> 1. This CLAUDE.md
> 2. docs/LESSONS.md if it exists (confirm: 'Read LESSONS.md — N lessons, updated YYYY-MM-DD')
> 3. C:\Users\mberr\.claude\projects\shared\LESSONS_CROSS_PROJECT.md
>    (confirm: 'Read LESSONS_CROSS_PROJECT.md — N lessons active')
> 4. docs/sessions/WHERE_WE_LEFT_OFF.md — the canonical live decision record. RE-READ it AND scan
>    recent conversation for any decision made AFTER the file's last write. If the conversation holds a
>    newer decision, the file is STALE — update it (tombstone-style) BEFORE acting. Never reconstruct
>    state from a spec doc alone; spec docs lag decisions.
>
> Then emit the 6-line context summary before proceeding with any substantive work.

> ⚠️ STATE-RECORDING PROTOCOL is part of this operating model — full text: docs/STATE_RECORDING_PROTOCOL.md
> (read it when recording state, reversing a plan, or resuming after a gap). The rules that bite most:
> - **Rule 2 (tombstone reversals):** when a plan changes, log DEAD / REPLACED BY / REASON / SUPERSEDES —
>   name the dead artifact so a future read can't resurrect it. The new plan alone is NOT enough.
> - **Rule 4 (don't defer):** log the decision the moment it's made, even mid-arc. Never "hold the log
>   until X resolves."
> - **Rule 5 (what-just-changed checkpoint):** the FIRST line of any "where are we" overview states the
>   single most recent decision/reversal — "MOST RECENT CHANGE: [what], [date]. Supersedes [what]." —
>   before any milestone summary.
> SOURCE: a milestone-only shutdown record let a superseded plan (a dead re-capture) get re-recommended
> next morning. State lives in files, not memory; reversals are logged louder than decisions.

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
- **Target:** ⚰️ ~~GalaxyCon San Jose alpha launch (Aug 21-23, 2026)~~ — **DROPPED 2026-07-29.** ⚰️ ~~soft launch Aug 4, 2026~~ — **DEAD 2026-08-03: Aug 4 was never a live date** (Mike). **The gate is an EVENT, not a date: FIRST COLD TRAFFIC — paid ads or an organic group post — and it is NOT SCHEDULED.** Posture is unchanged (online, gated beta) → ~1 quiet month, no marketing → then Facebook + email only → online-marketing-only through year-end. ⚠️ **Do not sequence, count days, or stage a go/no-go against any calendar date.** SoT: `docs/LAUNCH_READINESS.md`
- **Revenue:** Pre-revenue, 4-tier Stripe billing live (Free/Pro/Guard/Dealer)

---

## Key Architecture

- **Entry:** `wsgi.py` → gunicorn
- **Routes:** 19 blueprints in `routes/` (~87 endpoints)
- **Critical routes:** `/health`, `/api/grade`, `/api/billing/webhook`, `/api/signatures/v2/match`
- **Ship sequence:** `git add <specific files>` → `git commit` → `git push` → `deploy` →
  **⏳ WAIT FOR THE PAGES BUILD** → `purge` → **assert the new content is served**

  ⚠️ **The wait is a STEP, not a pause.** `purge` acts on Cloudflare; `push` triggers a Pages
  build that takes ~a minute. Purging inside that window does not clear the old file — it
  **re-caches it**, because the edge refetches from an origin still serving the previous build,
  and the 4-hour TTL restarts. Purging too early is strictly worse than not purging at all, and
  it fails **silently**. Bit the 2026-08-13 privacy-policy publish (`f69a207`): the post-purge
  check found the retired clause still live on a legal page. Full rule: `docs/LESSONS.md`
  **L-SW-2026-022**.

  | step | what it is | when it is needed |
  |---|---|---|
  | `deploy` | custom CLI, triggers a full **Render** deploy | any **backend** change. Render auto-deploy is **OFF**, so a push alone never reaches prod |
  | `purge` | custom CLI, purges the **entire Cloudflare zone** | any **frontend** change (slabworthy.com is Cloudflare Pages) |

  Backend-only change → skip `purge`. Frontend-only change → skip `deploy`. A change
  touching both needs both. `purge` is zone-wide, so **do not bother listing changed
  file URLs** — there is nothing to enumerate.

  Why `purge` matters: frontend assets ship with `Cache-Control: public, max-age=14400`
  and no cache-busting query string, so a stale edge copy looks exactly like a failed
  fix for up to four hours. (`sw.js` never caches HTML, so the service worker is not
  the risk — the Cloudflare edge is.)

  ⚠️ Auto-deploy was previously described here as "UNRELIABLE — sometimes it fires,
  often it does not." Corrected 2026-08-07: it is **OFF**. Nothing fires on push.
  Verifying in the Render dashboard (Events tab) after `deploy` is still worthwhile.
- **Health check:** `curl https://collectioncalc-docker.onrender.com/health`

### Three Patents (All Filed)
1. Multi-Angle Grading System (Jan 27, 2026)
2. Comic Fingerprinting Theft Recovery (Feb 12, 2026)
3. Signature Identification (Feb 25, 2026 — App #63/990,743)

---

## Session Conventions

- **Skills:** `/health`, `/stripe-test` (in `.claude/skills/`)
- **Session notes:** docs/sessions/CLAUDE_NOTES.txt (full history), docs/sessions/WHERE_WE_LEFT_OFF.md (last session detail)
- **Roadmap:** docs/sessions/ROADMAP.txt (mixed planning + session log; treat session log portions as historical)
- **Task list:** TODO.md
- **🚦 Launch readiness (SINGLE SOURCE OF TRUTH):** docs/LAUNCH_READINESS.md — honest A–F status + the launch-critical sequence to July 21. Status lives HERE, not in browser windows or session-note labels. Read it before any "what's left before launch" question.
- **BO primer (Slab Worthy specific):** docs/SW_BO_PRIMER.md (mirror of the file uploaded to BO project storage)
- **No Supabase.** Slab Worthy's only database is Render PostgreSQL
  (`collectioncalc_db`). Audited read-only 2026-08-08: no live code path in this
  repo touches Supabase, the backend has zero Supabase references, and
  `requirements.txt` has no Supabase package. ⚰️ A "Supabase project ID
  `kgqnwfpklodyyiqariid` (TheFormOf, shared DB)" line lived here until
  2026-08-08. **DEAD. REPLACED BY** this line. **REASON:** that ref is
  TheFormOf's own project (it appears 13 times across the TFO repo, so it is
  not a typo), it is not resolvable from this account, and a Supabase project ID
  does not belong in Slab Worthy's context regardless of which ref it is.
  **SUPERSEDES** any instruction to query Supabase for Slab Worthy. Do not add
  one back; do not "correct" it to the historic SW ref `kvtfywxvawdolgxyiari`
  either, whose project (`Source DB For CC`) is paused and superseded by
  `market_sales` on Render.

---

## Current Priorities

1. eBay listing end-to-end test (draft + auction)
2. Marketplace prep testing (Whatnot, Mercari, etc.)
3. Signature v2 — upload refs for 57 new creators, target 87%+ accuracy
4. Mobile testing on real devices
5. ⚰️ ~~GalaxyCon sprint plan (25 weeks to Aug 21)~~ — **DEAD 2026-07-29, GalaxyCon dropped.** `docs/sessions/GALAXYCON_SPRINT.md` is superseded in its entirety; do not execute or re-date it (retirement decision pending Mike). Replacement sequence: ⚰️ ~~Aug 4 soft launch~~ **first cold traffic (unscheduled)** → quiet month → FB + email marketing.
6. 🚦 **CP-1 valuation honesty — audited, NOT fixed.** Findings + the current fix order: `docs/technical/CP1_STATE_OF_PLAY.md`. Opens on canonical "of" fragmentation. ⚠️ *"confidence is displayed nowhere"* is **FALSE** — it renders in two live surfaces; do not re-scope CP-1 as "wire up the display."

---

## Mandatory: Chrome Extension Version Bumps

Any unit that changes an extension under `CCExtensions/` **MUST bump `manifest.json` `version` in the
SAME commit**, and the ship block **MUST state the expected version**.

**Why:** the extensions are loaded **unpacked**, so reloading is a manual step with no confirmation.
Without a bump, **a forgotten or failed reload is indistinguishable from a successful one** — the same
class of silent no-op as a Render deploy that doesn't fire. The version in `chrome://extensions` is the
only observable proof the reload took. This was already biting: `ebay-collector` sat at **1.3.5 from
2026-03-19** while `content.js` changed repeatedly through July–August — ~4.5 months of unverifiable
reloads.

**Scheme (semver; existing history 1.0.4 → 1.1.0 → 1.3.5):**
- **patch** — fixes/comments with no observable behaviour change
- **minor** — behaviour or UI a user would notice (figures added/renamed/removed, banner or popup changes)
- **major** — rewrite, or a breaking change to capture semantics

⚠️ Extension changes are **repo-only — NO Render deploy.** Always pair the bump with the reload callout.

---

## Mandatory: Third-Party Dependency Rules

When adding ANY new third-party service, API, or SDK to Slab Worthy:

1. **Add monitoring** in `dependency_monitor.py` — register the service in `MONITORED_SERVICES` with its check URL/feed and the APIs or packages we depend on. This is NOT optional.
2. **Add error handling** — every external call must have a try/except and a graceful degradation path (feature flag like `SERVICE_AVAILABLE`).
3. **Document env vars** — add any new API keys or config to `docs/technical/ARCHITECTURE.txt`.
4. **Test the monitor** — after adding, hit `/api/admin/dependency-status` to verify the new service appears.

Current monitored services: Anthropic (models), eBay (API deprecations), Stripe (SDK version), eBay account-deletion endpoint (self-check), Resources (self — memory + DB-connection ceilings vs Standard 2GB (upgraded from Starter 512MB, 2026-07-16 OOM incident) / max_connections, item 2f).

---

## Related Project

**TheFormOf (TFO)** — AI-native app dev platform. Separate repo at `C:\Users\mberr\TheFormOf`.
See that project's `CLAUDE.md` and `TFO_EXECUTIVE_SUMMARY.md` for TFO context.
