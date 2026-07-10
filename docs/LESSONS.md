# Slab Worthy — Project Lessons

> **Operator:** Mike Berry · **Last updated:** 2026-07-09
> **Scope:** Lessons specific to working on Slab Worthy. Read after `CLAUDE.md` during the
> session-opening protocol. Cross-project lessons live in
> `C:\Users\mberr\.claude\projects\shared\LESSONS_CROSS_PROJECT.md`.

## Format

Each entry: an ID, a one-sentence **RULE**, **WHY**, **HOW TO APPLY**, and (optionally) the
**SOURCE** incident. A lesson is a rule sentence for future behavior — not an error log.
Promotion to the cross-project file is Mike's call; Claude only proposes at session end.

---

## Active lessons

### L-SW-2026-001 — Claude NEVER runs git or deploy operations; Mike runs 100% of them

- **RULE:** Claude **never** executes `git add`, `git rm`, `git commit`, `git push`, `deploy`, or
  `purge` — not after approval, not to unblock a task, not "to be helpful," **no exceptions**. Claude
  prepares diffs and hands Mike copy-paste command blocks; **Mike runs every git and deploy/purge
  operation himself.** Read-only inspection (`git status`, `git diff`, `git log`, `git show`) is the
  only git Claude may run. If Claude believes a commit/deploy should happen, it **says so and waits**.
- **WHY:** The gate is not about whether the work is good — it has been good every time. It is about
  Mike being the one who pulls the trigger **every** time, so the gate still holds on the day the work
  is **not** good. Any Claude-run git/deploy mutation — even staging a deletion with `git rm`, even a
  change that was approved — defeats that. "Authorized," "looks good," and "approved" mean Mike
  approves the **code**; they are **never** permission to execute git or deploy.
- **HOW TO APPLY:**
  1. After verifying a change, present diffs + the exact `git add … ; git commit … ; git push ; deploy ; purge`
     block in Mike's PowerShell format, then **stop**. Run none of it.
  2. Never run `git add`/`git rm`/`git commit`/`git push`/`deploy`/`purge` under any phrasing of
     approval. Staging (even `git rm` to delete a file) is Mike's, not Claude's — hand him the command.
  3. If a task's final step is "deploy X" but X isn't committed, surface the gap and ask — do not
     commit/push/deploy to satisfy it.
  4. Wanting to help is not authorization. If unsure whether you may run something git/deploy-related,
     the answer is no — prepare the block and wait.
- **SOURCE:** Hardened 2026-06-08 after the prior version (which allowed running when "Mike explicitly
  says so in that turn") failed to hold — commits/pushes happened without Mike running them three times
  over the 2026-06-07/08 weekend (incl. `8e3cce0`, `a4838da`). The conditional permission was the
  loophole; this version removes it entirely. Strong candidate for cross-project promotion (Mike's call).

### L-SW-2026-002 — Commit messages must describe only what the commit actually contains

- **RULE:** A commit message must match its diff exactly. Never describe a change in the message that
  isn't staged in that commit. Draft the message from the **actually-staged file list**, not from the
  intended scope.
- **WHY:** `8e3cce0`'s message claimed a "stale ARCHITECTURE.txt ref" fix that the commit did not
  contain (only the file deletion was staged) — the message was written anticipating a file that never
  got added. A message that overclaims makes history lie and misleads anyone reading the log later.
- **HOW TO APPLY:** When preparing a commit block, the message lists only the files in the `git add`
  line of that same block. If a described fix isn't in the staged set, either add the file to the block
  or remove the claim from the message. When in doubt, scope the message narrower than the intent.
- **SOURCE:** 2026-06-08 — `8e3cce0` message/diff mismatch caught by Mike.

### L-SW-2026-003 — Unsaved grades retain nothing → grading-accuracy complaints are undiagnosable; retention is the prerequisite for calibration

- **RULE:** A grade that isn't saved to a collection leaves **no diagnostic trace** — no photos
  (images are transient base64 in the `/api/grade` request and never reach R2), no overall grade, no
  8 subgrades, no confidence, not even which comic. Treat **grade-submission retention as the
  prerequisite** for any grading-accuracy or calibration work: you cannot tell a *systematic
  conservative bias* (correctable via weights/snap) from *case-by-case photo-condition issues* (old
  photos, glare, sleeve/slab) without retained `(photos, subgrades) → eventual pro grade` pairs.
- **WHY:** A knowledgeable beta user (matbanshee, user_id 21, 2026-06-08) reported Slab Worthy
  undergraded 3 later-slabbed books by up to 2.6 pts. The complaint was **un-disprovable**: all three
  grades existed only in `api_usage` token counts. The only forensic signal left was input-token
  count (~7,532/grade) → ~4 images submitted → multi-angle starvation *excluded*, leaving the
  old-photo confound as leading hypothesis — but unprovable, because the pixels are gone. For a
  product whose core promise is grade accuracy, an unanswerable accuracy complaint is a credibility
  hole.
- **HOW TO APPLY:** Before promising/iterating on grading accuracy, ensure submissions are retained
  (design: `docs/technical/GRADE_RETENTION_SPEC.md`). When diagnosing an accuracy complaint, first
  check whether the grade was *saved* — if not, say plainly that photos/grades aren't retained rather
  than speculating. Retention build is **gated on a privacy/consent decision** (users may assume
  unsaved grades are ephemeral) — disclosure + ToS + erasure cascade come first.
- **SOURCE:** 2026-06-08 matbanshee investigation; spec drafted 2026-06-19 (Session 107).

### L-SW-2026-004 — A Render env-var change needs a redeploy/restart AND a fresh shell

- **RULE:** After changing an environment variable on Render, **both** the running service **and** any
  already-open Render shell keep the **old** value until you redeploy/restart the service and open a
  **new** shell. Never trust an already-open shell (or an un-redeployed service) to reflect a
  just-changed env var.
- **WHY:** Mid-Session-107 a Stripe key was updated in Render, but an already-open shell kept reading
  the previous key — producing a confusing "it's still the same key" loop until a fresh shell was
  opened.
- **HOW TO APPLY:** After any env change, redeploy/restart the service, then open a **new** shell
  before re-running any check that reads the var. If a value looks unchanged after you "just changed
  it," suspect a stale shell/process before suspecting the dashboard.
- **SOURCE:** Session 107 (2026-06-19) Stripe key swap. Candidate for cross-project promotion (Mike's call).

### L-SW-2026-005 — Run a strictly read-only pre-flight before any billing/money operation

- **RULE:** Before a billing/payment test (or any operation that depends on env-configured external
  keys/IDs), run a **strictly read-only** pre-flight that verifies key mode, that referenced IDs
  resolve in the active mode, and that endpoints are configured — *before* touching the real flow.
- **WHY:** Session 107's `scripts/stripe_preflight.py` caught an **expired key**, an **accidental LIVE
  key** in Render (the Stripe test/live toggle is a footgun), and a **script bug** — each before it
  could corrupt a real billing test. The cost of the read-only check is trivial vs. a botched live
  billing run.
- **HOW TO APPLY:** Keep/extend `scripts/stripe_preflight.py`; require a GREEN pre-flight before
  Section E and before any billing config change. Pre-flights stay read-only (list/retrieve + SELECT
  only) — never let one acquire a side effect.
- **SOURCE:** Session 107 (2026-06-19). Candidate for cross-project promotion (Mike's call).

### L-SW-2026-006 — Config-name typos are invisible to the eye and to substring/value checks; only exact-name machine resolution catches them

- **RULE:** When something is configured "right there" but behaves as if it's missing, suspect the
  **key NAME**, not the value — and verify it by **exact-name machine resolution** (`printenv NAME`,
  `env | grep -c NAME`), not by eyeballing a dashboard or a substring search.
- **WHY:** The Section E webhook 500 was a Render env var named `STRIPE_WEBHOOOK_SECRET` (**three O's**)
  instead of `STRIPE_WEBHOOK_SECRET`. The code read the correct two-O name, found nothing, and returned
  the "secret not configured" 500. It hid from every soft check: the brain autocorrects WEBHOOOK→WEBHOOK
  when reading; `grep -i stripe` *displayed* the 3-O name so it "looked present"; the manual "secrets
  match" check compared the **value** (which was correct). It only surfaced when the container was asked
  for the **exact** name: `printenv STRIPE_WEBHOOK_SECRET` = empty, `env | grep -c` = 0, while
  `STRIPE_SECRET_KEY` = 1 (the asymmetry was the tell).
- **HOW TO APPLY:** For any "configured but not working" env/config value, resolve the EXACT name the
  code reads (copy it from the `os.environ.get(...)` call) against the environment — never trust a
  substring match or a visual scan. A present-but-misnamed key reads identically to a missing one.
- **SOURCE:** Session 108 (2026-06-20) Stripe webhook 500. Candidate for cross-project promotion (Mike's call).

### L-SW-2026-007 — Instrument before theorizing: log the real failure reason instead of guessing at causes

- **RULE:** When a failure's cause isn't obvious, the first move is to make the failure **self-report**
  (log the actual exception / an explicit reason at the failure point) — not to generate and test
  theories against the code.
- **WHY:** The webhook-500 brief carried four plausible code theories (`.get()` bug, Stripe version
  drift, stale deploy, env propagation) — **all four were wrong.** What actually solved it was the
  hardening that added `logger.exception` + an explicit "Webhook secret not configured" message: the
  moment it ran, it pointed straight at the env var instead of sending us deeper into the code. An hour
  of wrong theories collapsed into a one-line answer once the code said *why* it failed.
- **HOW TO APPLY:** On any opaque 500/error path, add a clear logged reason (exception + identifying
  context) and reproduce ONCE before theorizing. Prefer explicit failure messages at guards ("X not
  configured") over generic errors. Treat "I can't find the traceback" as the first problem to fix, not
  a reason to guess.
- **SOURCE:** Session 108 (2026-06-20) Stripe webhook 500. Pairs with L-SW-2026-005 (read-only pre-flight). Candidate for cross-project promotion (Mike's call).

### L-SW-2026-008 — Verify ship/commit state from git BEFORE presenting any commit/deploy plan; never regenerate completed steps from memory

- **RULE:** Before handing Mike a `git add`/`commit`/`deploy` block — or describing what's "pending" /
  "ready to ship" — **run `git log`/`git status` and report the actual state.** Never reconstruct a
  commit plan from conversational memory; what the chat "remembers" as un-shipped may already be
  committed and deployed.
- **WHY:** Twice now a stale-state lapse surfaced the same way: (1) the dropped-E3-recapture resurrected
  from a stale spec doc (2026-06-27 AM), and (2) Fix A (title normalization) was re-listed as a pending
  `git add title_matching.py` step **after it was already committed (`c688bce`) and deployed** — Mike had
  the live $550 ASM #41 screenshot to prove it. Presenting completed work as pending wastes the reviewer's
  attention and erodes trust in the plan; in the worst case it invites a double-commit or a re-deploy.
- **HOW TO APPLY:** Treat git as the source of truth for ship-state, the same way files (not memory) are
  the source of truth for decision-state ([[State-Recording Protocol]], Rule 3 generalized: *verify
  current state before acting*). When about to say "ship this" / "commit that," first `git log --oneline`
  + `git status --short` on the specific files and report what's actually committed vs. dirty. If the tree
  is clean, there is no commit plan to give — say so.
- **SOURCE:** Session 111 (2026-06-27), valuation Fix A/B. Mike flagged the regenerated-as-pending pattern
  explicitly ("same staleness pattern as yesterday"). Pairs with the State-Recording Protocol. Candidate
  for cross-project promotion (Mike's call).

### L-SW-2026-009 — Similarity scores across multi-token names need a per-token support guard; one substituted token = a different entity

- **RULE:** Never accept a fuzzy/similarity match between multi-word names (titles, entities, keys) on an
  aggregate score alone. Require that **every content token of the matched candidate is supported by the
  input** (order/hyphen/typo tolerant, both concatenation directions) — because an aggregate score rates a
  ONE-WORD SUBSTITUTION highly when shared tokens dominate, and a substituted word means a **different
  entity**. Precision beats recall when a match writes into a shared pool: an unmatched item forms its own
  thin pool (recoverable); a false merge poisons an existing pool (silent, compounding).
- **WHY:** `token_sort_ratio(\"Absolute Catwoman\", \"Absolute Batman\") = 88` — no threshold could separate
  it (legit rescues live below 88). At the 75 cutoff, current code had merged **748 sales rows across 23
  canonical titles** into the wrong comp pools (Defenders→Descender incl. CGC keys, Power Girl→Fire Power,
  Crossover→Crossed, X-Force→X-Men…), silently corrupting the valuations of flagship titles. The guard
  (`_fuzzy_tokens_supported`) fixed all 23 while keeping the legit rescue classes (Spiderman↔Spider-Man,
  Ironman↔Iron Man) — proven by corpus-wide before/after audit, same method as Fix A's 0-false-merge proof.
- **HOW TO APPLY:** Any `fuzz`/`extractOne`/embedding-similarity match that CANONICALIZES (writes a shared
  key) gets a token-support guard + a corpus-wide before/after audit before deploy. Test both tolerance
  directions (split↔squashed compounds) — the first guard version broke Ironman→Iron Man; the audit caught it.
- **SOURCE:** Session 114 (2026-07-09), Absolute Batman #1 mispricing diagnosis → cross-title leakage audit.
  Candidate for cross-project promotion (Mike's call — applies to any project matching names fuzzily).

### L-SW-2026-010 — Identical timestamps across many log lines = a buffered-stdout flush artifact, not real-time events

- **RULE:** When a burst of log lines shares one timestamp, suspect a **buffer flush** (typically a dying
  process dumping its pipe-buffered stdout) before treating them as events that happened at that moment.
  Check content age (log format version, referenced entity IDs/dates) before reasoning from them.
- **WHY:** At the 2026-07-08 deploy, the old container flushed 10 `[Billing]` lines — days of history —
  all stamped 19:43:17, in the pre-fix log format. Read naively they looked like live webhook activity at
  deploy time and nearly misdirected the "webhooks not updating the DB" diagnosis. The tells: one shared
  timestamp, old log format, stale entity references.
- **HOW TO APPLY:** Timestamp-flattened logs are unusable for timeline reconstruction — get the timeline
  from an external witness instead (Stripe delivery log, DB rows). Root fix is L-2026-020
  (`PYTHONUNBUFFERED=1`, now also in this repo's Dockerfile); this lesson is the *reading* skill for logs
  produced before that fix, on any service that still lacks it.
- **SOURCE:** Session 113 (2026-07-08), billing mid-test scare diagnosis. Pairs with cross-project
  L-2026-020.
