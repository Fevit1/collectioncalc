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
> 5. **§ Mandatory: API Spend Ceiling** below — $10/day aggregate on Claude-initiated
>    Anthropic API spend, with the running total in `docs/API_SPEND_LEDGER.md`.
>    Read it before quoting any cost or starting any run that calls the API.
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

  ⚠️ **THERE IS A THIRD CASE the backend/frontend split misses: files that must EXIST
  in the container.** `deploy` is not only how code starts *serving* — it is how files
  *get there at all*. A one-shot script run from the Render shell, and anything it
  reads, needs a deploy even when nothing in the change is ever served. Committing and
  pushing is not enough, and `git show --stat` will happily confirm a file that is not
  in the image.
  **`.dockerignore` excludes `docs/`, `tests/`, `CCExtensions/`, `archive/`, `*.csv`,
  `*.db` and `*.docx`** (deliberately — it is what took the build context 4.9GB → 450MB).
  So **anything a script must read at runtime belongs in `scripts/`, never `docs/`.**
  Bit the 2026-08-13 cohort mailer: the notice text was committed to `docs/`, verified
  in the commit, and absent at `/app/docs/`. Full rule: `docs/LESSONS.md`
  **L-SW-2026-023**.

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

## Mandatory: API Spend Ceiling — $10/day aggregate

**Effective 2026-08-14. An operating constraint, not a preference.**

**$10 A DAY, AGGREGATE.** When the day's cumulative Anthropic API spend would cross
$10, **the run that crosses it needs Mike's written permission BEFORE it starts** —
not after, not at the next natural break. Anything over $10 on its own trips this by
definition.

**Scope:** Anthropic API spend *Claude initiates* — vision samples, backfills, sweeps,
any batch job. **NOT** the app's normal per-request grading cost, which is user-driven
and not something Claude chooses to run.

Two rules make this enforceable rather than aspirational:

1. **Track the running daily total durably and report it with every estimate.**
   Format: *"This run is $1.39, today's total is $2.75."* An estimate with no running
   total makes the rule unfollowable. Ledger: `docs/API_SPEND_LEDGER.md` — append
   BEFORE the run (estimate) and correct AFTER (actual, from `response.usage`).
2. **State the estimate BEFORE the run in every case, even when it is well under.**
   A rule that only surfaces near the threshold means the first time Mike hears a
   number is the first time it matters — the wrong moment to be calibrating whether
   the estimates are any good.

**Why:** the CP-1 vision sample is $1.39 and the corresponding sweep is $103–650. The
gap between those is exactly where an unremarkable-sounding decision becomes real
money, against a few-hundred-a-month infrastructure budget on a pre-revenue product
with six users.

⚠️ Estimates must be built from **measured** token counts, not modelled ones. The
first CP-1 image estimate was wrong by 4.5× (modelled ~1,100 image tokens/row; actual
245) and it inverted a recommendation. Use `count_tokens` (free) or real dimensions
before quoting a figure.

---

## Mandatory: eBay Capture Safety — and the one CDN exception

**THE INVARIANT:** eBay capture stays **human-triggered and human-paced**. The operator
clicks native Next; there is no programmatic auto-pagination, no auto-walk, no
scripted traversal of listing or search pages. **Never draft one.** A bot pattern here
is a ban risk, and a ban kills the valuation corpus — the asset the whole CP-1
programme is built on. Close data gaps with loud honest prompts and capture-assist,
never with auto-fetch.

⚠️ **The image CDN is inside this constraint, not outside it.** `_backup_one_image()`
in `routes/sales_ebay.py` fetches covers from `i.ebayimg.com` — that traffic is
legitimate because it is *downstream of the operator browsing*: one GET per image, in
the capture path, at the operator's pace.

### The one deliberate exception — 2026-08-14

**200 paced GETs to `i.ebayimg.com` outside the browsing path**, to fetch s-l800 and
s-l1600 variants for the CP-1 condition-estimation sample. Approved by Mike in advance,
after the exposure was named rather than discovered. Paced as Poisson arrivals
(exponential inter-arrival, mean 17s, clamped [4s, 70s]) over ~57 minutes —
memoryless, so there is no periodic signature; a fixed tick is its own tell.

**This is a ONE-OFF, not a precedent.** It was justified by being a go/no-go on whether
condition estimation is viable at all — a decision that could not be made any other
way, for $1.39. It was the **first time image traffic ever left the browsing path.**

⚠️ **A future unit wanting CDN fetches outside capture starts from
"Mike approved 200 paced GETs once, for a decision that could not be made any other
way" — NOT from "we do this."** Each such request is argued fresh, on its own merits,
in advance. The 143,118-row cover backfill is the obvious candidate and is
**explicitly NOT authorized** (see the comment block in `_backup_one_image`); if it
ever happens it is the 23,131 rows at $100+, paced, and separately approved.

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
