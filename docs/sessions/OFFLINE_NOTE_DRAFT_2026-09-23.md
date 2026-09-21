# DRAFT — the offline note. Goes at the TOP of `WHERE_WE_LEFT_OFF.md` at Tuesday's close-out (2026-09-22).
# Drafted 2026-09-21 from Mike's specification. The close-out fills the three ⟦…⟧ fields and deletes this file.

## 🛑 MIKE IS OFFLINE from Wednesday 2026-09-23 for about five days. NO COMMITS in that window. Read this first.

**If production breaks during the window: NOBODY ACTS.** Mike runs every deploy and every rollback, and he will not
be reachable. A production problem that starts in the window STAYS BROKEN until he is back. That is the decision,
not an oversight — do not look for a way around it, and do not read an alert as a reason to try.

**State at close:** `git log -1` = ⟦hash⟧ · 0 ahead of origin · working tree ⟦clean / list⟧ · last deploy `d21fdc9`
(2026-09-21 16:02Z, the cache breakpoint) · last purge `2f40607` (2026-09-20) · nothing deployed 09-22 or 09-23.
Render env that differs from defaults: `SLAB_GUARD_REGISTRATION_ALLOW_USER_IDS=3,25,26`. Extensions as loaded:
`ebay-collector` 1.5.0 · `whatnot-valuator` 2.47.0 · `slab-guard-monitor` 1.0.1. Claude-initiated API spend ⟦total⟧.

### What Claude (Frodo) will and will not do during the window
- **Will, if Mike messages:** REPORT-ONLY work — reading the repo, read-only queries through the `DATABASE_URL_RO`
  role, reading the live site with `curl`, writing up findings in chat.
- **Will NOT, under any phrasing:** write to the repo (no file edits — so no records either; anything worth recording
  is held in the chat and written on Mike's return), write to the database, touch production (no `deploy`, no
  `purge`, no Render or Stripe or Cloudflare change, no env var), run git, or spend on the Anthropic API. The
  $10-a-day ceiling is moot: the window's Claude-initiated spend is $0.

### Return checklist — Mike's FIRST HOUR back, in this order
1. **The dependency monitor's email alerts, in date order.** Oldest first: the first alert dates the start of any
   problem; later ones are usually its echoes. (The monitor runs inside `/health` — it is only as alive as the
   service is; a gap in alerts can mean "healthy" or "down".)
2. **`/health` and the dependency-status page.**
   `curl.exe -s https://collectioncalc-docker.onrender.com/health` → `{"status":…,"version":…}`; then the admin page's
   dependency chip (`/api/admin/dependency-status`, admin login) — Anthropic models, eBay, the eBay deletion endpoint,
   Stripe, Rekognition, resources (memory / DB connections), rapidfuzz.
3. **The Render events feed** — anything that restarted, failed a health check, was OOM-killed or redeployed. No
   deploy should appear after `d21fdc9`; one that does was not Mike's.
4. **The extensions errors page in Chrome** (`chrome://extensions` → Errors on each of the three). The extensions
   only run while Mike browses, so errors here are from before the window or from the first minutes back.
5. **The API spend ledger against the Anthropic console** — `docs/API_SPEND_LEDGER.md` says the window's
   Claude-initiated spend is $0. Any console spend in the window is the app's own user-driven grading, or something
   nobody initiated. Signature ID cannot add to it: only accounts 3, 25 and 26 are entitled.
6. **The `[R2Backup] shed` count over the window** — search the Render logs for `[R2Backup] shed`. The "shed total"
   in each line is a per-worker counter that resets on restart, so count the LINES. A shed batch loses nothing
   permanently (`image_url` is retained) — but the recovery it names is a CDN backfill, which is NOT authorized
   outside the capture path (CLAUDE.md, eBay Capture Safety). Count it; do not fix it from the log line.
7. **`git status` and `git log -1`** — the tree and HEAD must match "State at close" above. Anything else is drift.

### Rollback levers — the exact action for each (Mike only)
| lever | when | exact action | verify |
|---|---|---|---|
| **Render rollback to the prior deploy** | the service is unhealthy after a deploy, or a backend change misbehaves | Render dashboard → `collectioncalc-docker` → **Deploys** → the last good deploy → **Rollback to this deploy**. (The `deploy` CLI only deploys HEAD; rolling back in git means `git revert <hash>` → push → `deploy`.) Prior deploys, newest first: `d21fdc9` cache breakpoint · `2f40607` registration gate · `8413efb` prompt v2 | `/health` 200; Events shows the rollback |
| **`SIG_PROMPT_VERSION=1`** | the signature prompt v2 or its floor rule misbehaves | Render → Environment → add `SIG_PROMPT_VERSION` = `1` → save → **restart** (an env change needs a restart — L-SW-2026-004). Reverts to the March prompt and its 0.50 share floor; the labels and the no-percentage copy stay. Remove the var to return to v2 | one ID Sigs click → the log row's `flags_json.prompt_version` = "1" |
| **The floor, without touching the prompt** | names are wrong (raise) or too few (lower) | Render env: `SIG_MATCH_FLOOR` (0.75), `SIG_MATCH_MARGIN` (0.40), `SIG_NONE_OF_THESE_CEILING` (0.50) → restart | `[SigID] match served … matched=` on the next click |
| **`SLAB_GUARD_REGISTRATION_OPEN` and the allow-list** | registration must reopen for everyone, or close for the allow-listed accounts too | reopen: set `SLAB_GUARD_REGISTRATION_OPEN=true` → restart. Close completely: delete `SLAB_GUARD_REGISTRATION_ALLOW_USER_IDS` (now `3,25,26`) → restart. No code deploy either way | collection page → DevTools → `my-plan` → `usage.registration_open` |
| **`ebay-collector` — reload 1.5.0** | the collector misbehaves (wrong grades, no capture) | `chrome://extensions` → `ebay-collector` → reload → confirm **1.5.0** → refresh or close every open eBay tab. To go back a version: `git checkout b80a284~1 -- CCExtensions/ebay-collector` is a REPO WRITE — Mike only, and the manifest would read 1.4.0 | the version on the extensions page |
| **`whatnot-valuator` — reload 2.47.0** | the valuator misbehaves (duplicate records, wrong-book vision) | `chrome://extensions` → reload → refresh or close EVERY open Whatnot tab (an unpacked reload orphans the old content scripts, which keep recording) → confirm **2.47.0 in the overlay banner**, not only on the extensions page | the banner: `Initializing Comic Valuator v2.47.0` |
| **Cloudflare** | a frontend change is wrong | there is no rollback button in the workflow: `git revert <hash>` → push → WAIT for the Pages build → `purge` → assert the served file | the served file |

### What is queued for after the window (nothing here is started)
⟦filled at close-out from Tuesday's results: the pricing decision, the label-reading leak, Design B, the `title_year`
backfill, item 20's marketplace halves, item 21's follow-on, item 23, the detection post-mortem, the canary lesson⟧
