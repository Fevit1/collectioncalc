# Slab Worthy — Project Lessons

> **Operator:** Mike Berry · **Last updated:** 2026-08-03 (18 lessons)
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

### L-SW-2026-011 — Cleanup strippers that delete tokens before matching can truncate entity names; adding a precision guard downstream requires auditing what the permissive path was silently repairing

- **RULE:** Any cleanup/stripper step that deletes tokens BEFORE a matching step can silently
  truncate entity names (a "condition prefix" list containing a word that legitimately starts
  entity names — "New" — eats "New Mutants"). And when you ADD a precision guard downstream of a
  permissive matcher, **audit what the permissive path had been silently repairing** — the guard
  will stop those repairs and surface the upstream bug as new-looking damage. Diff the full
  corpus (fixed vs shipped code) before trusting either the old or the new output.
- **WHY:** `title_normalizer.py` stripped a bare leading "new" as listing-condition wording since
  day one (`ac9b2be`). The permissive fuzzy matcher glued "Mutants" back to 'New Mutants', hiding
  the bug — while "New Teen Titans" exact-matched into the *different, real* 'Teen Titans' pool,
  corrupting it invisibly for the product's whole life. The moment the per-token guard
  (L-SW-2026-009) shipped and the corpus was re-normalized, the hidden repairs stopped: 1,072
  rows surfaced with truncated canonicals, including 635 'Mutants' orphans (New Mutants #98,
  the 1st-Deadpool key, valued from an orphan pool). The guard was correct; the stripper was the
  defect; the permissive matcher had been the camouflage.
- **HOW TO APPLY:** (1) Never put words that can legitimately start entity names into a
  strip-by-position cleanup list; prefer unambiguous phrases ("brand new" yes, bare "new" never).
  (2) When tightening any matcher, run a corpus-wide differential of new-vs-old outputs and read
  the changes — regressions that look caused by the new precision are often day-one bugs losing
  their camouflage; fix the upstream defect, don't loosen the guard. (3) Verify heals
  end-to-end after the fix (the stranded key valued correctly: NM #98 → $300 exact/high).
- **SOURCE:** Session 115 (2026-07-10), market_sales dry-run surfaced the leading-"New" bug hours
  after the ebay re-normalize. Pairs with L-SW-2026-009 (the guard that exposed it). Candidate
  for cross-project promotion (Mike's call — applies to any pipeline with cleanup-then-match).

### L-SW-2026-012 — Any change adding image decoding to a hot request path needs a peak-memory budget check on the actual instance size before ship

- **RULE:** Before shipping a change that adds (or multiplies) full-resolution image decoding on a
  request path, budget its **peak transient memory at real-world input sizes** (12MP+ phone photos,
  × photos-per-request, × concurrent requests) against the actual instance ceiling — and the offline
  suite must include a **peak-RSS test with real-world-sized fixtures**, not just small ones. "Tests
  pass" on 400px fixtures says nothing about memory.
- **WHY:** The HEIC/orientation unit (`d2e525d`, 2026-07-16) was offline-verified 17/17 — every test
  correct, every test small. In prod, normalizing four 12MP photos per `/api/grade` spiked RSS into
  the 512MB Starter ceiling and retained +25–83MB per grade (glibc arena fragmentation under
  gthread): two OOM kills within 18 minutes of going live, each dropping every in-flight request
  ("Failed to fetch"), plus a dependency-alert email storm as the monitor's self-check watched the
  instance die. A single user grading normally was enough. The fix (long-edge cap + draft-mode
  decode + decode-concurrency gate + MALLOC_ARENA_MAX=2 + worker recycling) cut the JPEG peak
  95→33MB — and its own first draft had a silent no-op bug (aspect-incorrect draft box) that ONLY
  the 12MP peak-memory test caught. Small fixtures validate correctness; only realistic fixtures
  validate survival.
- **HOW TO APPLY:** (1) When a diff touches image decode on a request path, compute the worst case:
  bitmap bytes (W×H×3) × simultaneous copies (decode + transpose/rotate) × photos-per-request ×
  worker threads, vs instance RAM minus steady-state RSS. (2) Add/extend a peak-RSS test (psutil
  sampler thread) using generated 12MP+ photo-realistic fixtures (gradient+mild-noise — pure noise
  inflates encoded sizes and masks decode-buffer wins). (3) On a memory-ceiling instance, bound
  decode concurrency explicitly (semaphore), don't rely on thread-count luck. (4) Post-deploy
  verification for such changes includes watching instance memory across 2-3 real grades — a
  metric, not a feeling.
- **SOURCE:** Session 118 (2026-07-16) OOM incident — post-deploy verification by Mike caught it
  same-hour; rollback to `1437fdb`, fix re-shipped as its own unit. Candidate for cross-project
  promotion (Mike's call — applies to any project decoding user media on small instances).

### L-SW-2026-013 — Replicated observers sharing a state-change alert dedup need stability windows; prune-on-absence is a race that turns one flap into an alert storm

- **RULE:** When alert state ("email once per state change") is SHARED (a DB table) but the
  observations feeding it are computed PER REPLICA (per-worker/per-instance caches, streaks, or
  probe results), never prune/clear an alert key the moment one observer reports it resolved.
  Require a **stability window** on both edges: alert only after the warning persists, and prune
  only after it has been continuously absent for a window that outlasts any per-replica cache
  divergence. Also: never cache a FAILURE observation longer than a success (a long-lived failure
  snapshot IS the divergence), and never do alert I/O (email/webhook) synchronously inside the
  request path that triggers the check.
- **WHY:** The 2026-07-16 email storm ran for hours across three deploys and survived a rollback,
  at ~1 email per 5–15s: worker A's self-check cached a single 502 (caught during a deploy-swap
  window) for the FULL 24h TTL while worker B saw healthy; every health poll handled by B pruned
  the shared dedup key ("resolved"), every poll handled by A re-inserted and RE-EMAILED it
  ("new"). Three small defects compounded: (1) failure cached 24h vs the other checks' 5-min
  backoff; (2) prune-on-every-call with no absence window; (3) the Resend send ran inside
  /health — the availability probe Render acts on. The storm was state-driven, not
  code-version-driven, which made it look like a recurring platform problem during an unrelated
  OOM incident and cost real diagnosis time. Fix (`37d5e97`) verified live: one dedup'd email per
  real event, including across an OOM restart.
- **HOW TO APPLY:** (1) In any state-change alerting with >1 worker/instance, add a prune
  stability window (SW uses: refresh `last_seen_at` for present keys; DELETE only keys absent AND
  `last_seen_at` older than 15 min — longer than any check cache divergence). (2) Audit failure
  caching: a failed probe backs off minutes, never rides a long success TTL. (3) Move alert I/O
  off the request thread (daemon thread + skip-if-busy lock). (4) Offline-test the storm shape
  directly: simulate N alternating divergent observers against the shared store and assert total
  emails == 1 (SW: `test_monitor_flap.py` S4, 40 alternating polls → exactly 1 email, was ~20).
- **SOURCE:** Session 118 (2026-07-16) email storm, diagnosed live via `dependency_alerts` row
  churn (~30s insert/delete cycle). Pairs with L-SW-2026-012 (same incident's memory half).
  Candidate for cross-project promotion (Mike's call — applies to any project with multi-worker
  alerting: MASSE agent alerting, TFO pipeline monitors).

### L-SW-2026-014 — When a domain spans multiple tables, count EVERY table before characterising the whole; a `source` column with a DEFAULT value is the tell that a sibling table holds the rest

- **RULE:** Before asserting what a dataset does or does not contain, enumerate **every** table that
  holds that domain and count them all. A single-table count that looks conclusive is the failure
  mode, not the evidence. **The reusable heuristic: a `source`/`type`/`origin` column that carries a
  DEFAULT value is a strong signal that the other sources live somewhere else** — a genuinely
  multi-source table rarely needs a default.
- **WHY:** The valuation corpus lives in **two** tables: `ebay_sales` (71,652 rows, 87.8%) and
  `market_sales` (9,963 rows, 12.2%, **100% Whatnot** — `sales_market.py:127` defaults `source` to
  `'whatnot'`). Querying either one alone produces the **opposite** wrong answer with equal
  confidence. Reasoning from the eBay-shaped tooling (the eBay collector extension, `sales_ebay.py`,
  the eBay corpus work in session notes), I asserted "the corpus is eBay-only" and flagged **accurate**
  marketing copy (`waitlist-confirmed.html:306`, "we track real sales data across eBay and Whatnot")
  as a false claim — and got a green light to "fix" correct copy. Caught only because Mike knew the
  data. The Whatnot rows are real: 1,603 distinct titles across 35 series, captured 2026-01-24 →
  2026-07-01.
- **HOW TO APPLY:** (1) For any "does the data support this claim" question, list the tables FIRST
  (`\dt`, or grep every `INSERT INTO`) and count them all before concluding. (2) Treat a defaulted
  discriminator column as an explicit prompt to go looking for the sibling. (3) When a claim is about
  a *union* ("across X and Y"), the query must be a union too. (4) Copy that turns out to be correct
  gets a **tombstone recording that it was investigated and found correct** — otherwise the next
  sweep re-raises it and someone eventually "fixes" accurate text.
- **SOURCE:** 2026-08-01 Slab Guard claims audit. Mike's correction; verified read-only via
  `DATABASE_URL_RO`. Candidate for cross-project promotion (Mike's call — the defaulted-discriminator
  heuristic applies to any multi-source pipeline: MASSE lead sources, TFO run origins).
- **STATUS:** ⛔ **STAYS SLAB WORTHY-LOCAL** (Mike, 2026-08-01) — the two-table trap is specific to
  this corpus. Not promoted; do not re-propose it.

### L-SW-2026-015 — A null, empty, or zero result is not a pass until you have proven the probe could have returned a hit

- **RULE:** Any check whose "good" outcome is **absence** (no matches, zero rows, empty diff, clean
  scan) must be paired with a **positive control** proving the probe was capable of finding something
  before its silence is treated as evidence. Never report "clean" from a command you have not shown
  can return a hit.
- **WHY:** Three independent instances in a single session (2026-08-01), all the same shape, all
  self-caught only on re-check: (1) `grep ... | head -22` silently truncated the `app.html` claims
  sweep and hid line 2872 — I reported that audit **complete** while a "theft recovery" string sat in
  the JS-injected success message, contradicting copy I had rewritten 40 lines above it; (2) a
  post-deploy `curl` without `-L` hit an **HTTP 308** and measured **0 bytes**, so "0 banned phrases
  across 6 live pages" was scanning empty responses — a total false pass on production verification;
  (3) three blueprint probes used **guessed** route URLs (`/api/admin/stats`, `/api/vision/scan`) that
  do not exist, so their 404s read as "module failed to import" when the modules were fine. Each one
  produced a confident, clean-looking, **wrong** answer.
- **HOW TO APPLY:** (1) Never let a truncating pipe (`head`, `-m`, `| head -N`) terminate a
  completeness sweep — count first (`grep -c`), then page deliberately. (2) On any HTTP check, print
  `%{http_code}` and `%{size_download}` and follow redirects (`curl -sL`); a 0-byte body is never a
  pass. (3) Derive endpoint paths by **reading the route decorators**, never by guessing; distinguish
  a route-level 404 (JSON body, app handled it) from an unregistered blueprint (framework HTML), and
  remember **405 proves the path exists**. (4) Before trusting an absence, invert the probe once
  against known-present content to confirm it can fire. (5) When reporting verification, state what
  the check would have missed — "absence of the old string" is not "presence of the new one"; assert
  both.
- **⚠️ COROLLARY, added 2026-08-03 — THE MIRROR CASE: a HIT is not a failure until you have confirmed
  the match is the live instance.** The rule above guards false *negatives* (absence read as a pass).
  The same sweep produces false *positives* when the pattern matches something that is not the rendered
  thing: a **comment**, a test fixture, a changelog entry, or — the case that bit — a **tombstone that
  quotes the exact string it retired**. The 2026-08-03 `waitlist.html` purge check reported the dead
  beta-code phrase as still live; it was matching the explanatory comment added in the very commit that
  removed it. Two guards: **(1)** scope completeness sweeps to rendered content (exclude comment nodes,
  or assert on the specific element) and assert the NEW string's presence alongside the OLD string's
  absence, since the pair disambiguates; **(2)** when writing a tombstone, **describe the retired
  wording, don't reproduce it** — a comment containing the string is indistinguishable from an unfixed
  instance to every future grep, and the cost lands on whoever sweeps next.
- **SOURCE:** 2026-08-01, Guard coming-soon + claims-audit session; recorded at Mike's request after
  he noted all three in one sitting. Corollary from 2026-08-03, `login.html` sign-in fix — the purge
  artifact designed under L-SW-2026-017 fired a false alarm on its own tombstone. Pairs with
  L-SW-2026-008 (verify state from the source of truth, don't reconstruct it).
- **STATUS:** ✅ **PROMOTED CROSS-PROJECT 2026-08-01 (Mike) → `LESSONS_CROSS_PROJECT.md` L-2026-024**
  (file bumped to v1.4, 11 lessons active). Mike's reasoning: it is the **same failure shape as
  L-2026-021**, the `STRIPE_WEBHOOOK_SECRET` hunt — there `grep -i stripe` displayed the misnamed key
  and the value comparison matched, so **both checks returned clean because neither could see the
  defect**. The positive-control rule transfers to MASSÉ and TFO without modification.

### L-SW-2026-016 — A displayed figure's LABEL is a claim about what was measured; trace it to the expression or don't ship it

- **RULE:** Before shipping or trusting any user-facing number, trace it to the expression that produces
  it and confirm the **label matches that expression's semantics** — its scope, its units, and its
  behaviour on the failure path. A number that *looks* plausible is not evidence that it measures what
  its label says. When you cannot make a figure true, **omit it rather than assert it**.
- **WHY:** **Seven instances in one extension, found in a single day**, all the identical shape — a
  real-sounding label over a quantity the code never measured:
  1. **"backend offline"** — asserted an unverified *cause*. `request_logs` showed 293 batch POSTs, all
     HTTP 200; the server was completing and the client was timing out. (Also L-SW-2026-007.)
  2. **"session total"** — wrong twice: it never reset per session (only a popup button nobody presses;
     observed live at **235,216**, ~2× the entire `ebay_sales` table) and it counted locally-novel items
     rather than server-inserted rows.
  3. **"Pending Sync"** — showed `collectedSales.length`, the rolling 1000-item **local dedup buffer**,
     permanently at its cap and unrelated to anything pending.
  4. **"Total Collected"** — read like corpus size; was a lifetime count of locally-novel items, and the
     *same* unreconciled increment as "session total" under a second label.
  5. **"N new"** on the failure path — attempted, not saved; nothing had reached the server.
  6. **"N dupes"** — absorbed items dropped for a missing `ebay_item_id`, which are not duplicates.
  7. **"My Reports"** — permanently `0`; the only write in the file sets it to `'0'` on logout and
     nothing ever populates it.
  Every one was individually plausible on screen. The class is invisible to testing because the code
  *works* — it computes something, renders it, and never lies about the arithmetic, only about the
  meaning. Two of them (2, 3) had survived months of daily use being read as fact.
- **HOW TO APPLY:**
  1. When touching any display surface, **enumerate every figure on it** and name the expression behind
     each one before changing anything. The audit is cheap; discovering it later is not.
  2. **Never let a fallback substitute a different quantity under the same label.**
     `result.saved ?? newSales.length` silently turns a server count into a local count. If the
     authoritative value is missing, contribute **0** or render `—`.
  3. **`||` on a numeric that can legitimately be 0 is a falsy-zero bug.** `result.saved || sales.length`
     printed "✓ Synced 1000 sales" for the all-duplicates case, contradicting the tile beside it that
     had correctly added 0. Use `??`.
  4. **Omit over assert.** `0` under "Saved this run" claims a run exists that saved nothing — a
     different statement from "no run is in progress". Render `—`, or drop the element.
  5. **If an authoritative source exists, do not keep a local approximation of it.** Postgres knows the
     cumulative capture total exactly; a browser-local mirror drifts, dies with a profile, and cannot
     distinguish inserted from later-deleted.
  6. **Prefer a scope with a real boundary** over one whose reset depends on a human pressing something.
     "Session" that only clears via a button is not a session. When a boundary is automatic, **surface
     its anchor, not its rule** — "saved this run · since 3:42 PM" makes an idle-gap reset self-evident
     where no tooltip fits.
  7. **A control whose target you retired is the same defect.** After removing `sessionCollected`, the
     "Reset Session" button would have looked like it worked and done nothing.
- **EXTENDED 2026-08-03 to a non-display surface — see [[L-SW-2026-018]]** (`?signup=true`, a URL
  parameter asserting an intent nothing read). Same mechanism, different medium: the claim was in a
  *contract* rather than on a screen, and it was right by coincidence rather than by computation.
- **SOURCE:** 2026-08-03, eBay collector honesty pass. Instances 1–4 fixed; 5–7 recorded and deliberately
  left (reported, not swept). Pairs with **L-SW-2026-007** (instrument, don't theorise — #1 is the same
  incident) and **L-SW-2026-015** (a clean result is not a pass until the probe is shown able to fail —
  same epistemics applied to checks rather than to displays). **Candidate for cross-project promotion
  (Mike's call)** — the mechanism is not eBay-specific and applies to any MASSÉ or TFO dashboard,
  admin panel, or status surface.

### L-SW-2026-017 — Every manual ship step must leave an OBSERVABLE ARTIFACT; a step whose completion isn't observable is indistinguishable from one that was skipped

- **RULE:** Any manual step in a ship sequence — reload, deploy, purge, env edit, restart — **must leave
  an artifact that distinguishes "done" from "skipped," and the ship block must name that artifact and
  its expected value.** Not *"then deploy"* but *"then deploy; Render Events should show `680f243`."*
  If no artifact exists, **create one as part of the change**. Absence of an error is not evidence of
  completion.
- **WHY:** Four instances across three surfaces, three of them inside a single fast-moving day
  (2026-08-03):
  1. **Unpacked extension reload — ~4.5 months blind.** `ebay-collector/manifest.json` sat at **1.3.5
     from 2026-03-19** while `content.js` changed repeatedly: the July selector fixes (`bbe5353`), the
     hydration/MutationObserver fix, the `/sold/i` case-sensitivity fix, the sync-honesty unit
     (`b4ba1ba`), the counter unit (`d3a47ff`). Reloading unpacked is manual with **no confirmation**,
     so a forgotten or failed reload looked exactly like a successful one.
  2 & 3. **Render auto-deploy silently didn't fire — twice in one day.** Already a known hazard
     (`CLAUDE.md`: auto-deploy-on-push is UNRELIABLE for `collectioncalc-docker`) — the warning existed
     and it *still* happened twice, because a warning is not an artifact.
  4. **Cloudflare `purge`** — same shape, and at the time of writing **no warning attached at all**.
- **⚠️ THE REAL COST IS EPISTEMIC, NOT OPERATIONAL.** The damage is not "we had to reload again." It is
  that **every conclusion drawn in the blind window carries an unremovable caveat.** Debugging during the
  extension's 4.5 months may have been reasoning about behaviour produced by **stale code** — including
  the 2026-07-16 collector diagnosis, which passed through two wrong theories (hydration, then visibility
  filtering) before reaching the case-sensitivity root cause. Nothing is *known* to be wrong. The point
  is that it was **not knowable**, and it cannot be established retroactively.
- **⚠️ A DECOY ARTIFACT IS WORSE THAN NONE.** `/health` returns `{"status":"ok","version":"5.6.0"}` and
  reads like deploy confirmation. The `version` is a **hand-maintained string with no commit SHA** — it
  cannot confirm which commit is live and will happily report the new version from the old container.
  An artifact must be **derived from the thing it claims to confirm**, or it manufactures false
  confidence. Render Events (commit hash) is the real artifact; `/health` `version` is not.
- **HOW TO APPLY:**
  1. **Name the artifact and its expected value in the ship block**, per manual step:
     · extension → *"after reload, `chrome://extensions` should read 1.4.0"*
     · Render deploy → *"Events should show commit `<sha>`"* (never `/health` `version`)
     · Cloudflare purge → *assert the NEW content is actually served* — `curl -sL <url>` and grep for a
       string that only exists post-change. There is no dashboard artifact, so it must be constructed.
  2. **Prefer artifacts the platform already emits** (version strings, commit hashes, Events rows) over
     ones a human must remember to look at.
  3. **If a change has no natural artifact, add one in the same commit** — a version constant, a build
     stamp. A follow-up bump does not help the reload that already happened.
  4. **Verify it is derived, not declared.** Ask: *could this artifact show the expected value while the
     step did not happen?* If yes, it is a decoy.
  5. **This matters most exactly when you are moving fast** — that is when steps get batched, assumed,
     and skipped, and when nobody stops to check. Speed is the condition that produces the failure, not
     an excuse for skipping the check.
- **DISTINCT FROM L-SW-2026-015 — different failure, different fix. Do not merge them.**
  · **015 is about CHECKS:** a null/empty/zero result treated as a pass without proving the probe could
    have returned a hit. Fix = **positive control**.
  · **017 is about ACTIONS:** a step whose completion produces no observable difference. Fix =
    **observable artifact**.
  A positive control cannot help you here — there is nothing to probe. An artifact cannot help there —
  the check ran, it just couldn't see. They compose: *the action leaves an artifact, and the check for
  that artifact is positive-controlled.*
- **SOURCE:** 2026-08-03, recorded at Mike's direction after the manifest-gap finding. Mike's framing:
  *"Three instances across two surfaces in one session is a mechanism, not a coincidence — and it bit
  specifically because we were moving fast, which is when it matters most."* Behavioural fixes already
  landed for two surfaces (`CLAUDE.md` Render-deploy warning; mandatory extension version bumps,
  `ed4f2a0`); **Cloudflare purge still has no artifact defined.** Pairs with L-SW-2026-004 (an env change
  needs a redeploy *and* a fresh shell — the same "the step you think you took didn't take" family) and
  L-SW-2026-008 (verify ship state from git, never from memory).
- **STATUS:** 🔼 **CANDIDATE FOR CROSS-PROJECT PROMOTION (Mike's call).** The mechanism is
  platform-agnostic and already has instances outside this repo's tooling: TFO's Vercel deploys, MASSÉ's
  agent restarts, and any manual env/config edit on any platform. Nothing in the rule is Slab
  Worthy-specific.

### L-SW-2026-018 — A parameter, flag or option that nothing reads is a claim, not a mechanism; verify the READER exists, because a default can make it look like it works for months

- **RULE:** Before trusting — or writing — any URL parameter, feature flag, config key or option that is
  supposed to *select* a behaviour, **find the code that reads it.** `git log -S` on the parameter name
  against the consuming file, not a glance at the caller. A parameter whose desired outcome happens to
  match the default is **indistinguishable from a working one** until the default changes, at which point
  it fails silently and in the opposite direction.
- **WHY:** `index.html`'s "Sign Up" link carried **`?signup=true` from `cbd80d7` (2026-02-28) to
  2026-08-03 — five months — and `login.html` never contained a reader for it.** `git log -S 'signup=true'`
  against `login.html` returns nothing across its entire history. It appeared to work the whole time
  purely because signup was the default panel. Two consequences, both real:
  1. **It hid the actual defect.** Because Sign *Up* visibly "worked", nobody asked why Sign *In* — the
     bare `/login.html` on the same nav line — landed on the same Create Account form. The dead parameter
     supplied false evidence that panel selection existed at all.
  2. **It is a live trap on any default change.** The moment the default flips to login (which is exactly
     the fix), the parameter's silence stops being harmless and starts breaking signup. It had to be kept
     as a deliberate **alias** — the link is in production, may be bookmarked, and pages get cached —
     rather than deleted as "unused."
- **HOW TO APPLY:**
  1. **Grep for the reader, not the writer.** `?x=`, `--x`, `FEATURE_X` in a caller proves only that
     someone *intended* it. Confirm `params.get('x')` / `os.environ.get('X')` / equivalent exists.
  2. **When a param's effect equals the default, you have not tested it.** Test selection by asserting
     BOTH directions against a non-default — and assert the param was actually received (`location.search`
     non-empty). A local `file://` load silently strips query strings; that near-missed here.
  3. **Never delete a shipped parameter as "unused" — alias it.** Deletion and never-implemented look
     identical in the code but differ in the wild, where the URL is already out there.
  4. **Make selection an explicit total branch**, never "whatever carries `active` in the markup." The
     implicit default is what let the beta-panel removal silently redefine the page's landing.
- **DISTINCT FROM L-SW-2026-015/024:** that is about a *check* whose null result wasn't proven capable of
  firing. Here the outcome was *correct*, so no check would have flagged it — the mechanism behind the
  correct outcome was simply absent. Fix = **verify the reader**, not a positive control.
- **SOURCE:** 2026-08-03, `login.html` sign-in landing fix. Found while tracing why "Sign In" reached the
  signup form; the dead parameter was incidental to that hunt and is the more transferable finding.
  Instance of **[[L-SW-2026-016]]** (a label asserting something nothing measures) extended from display
  surfaces to contracts. **Candidate for cross-project promotion (Mike's call)** — applies to TFO feature
  flags, MASSÉ agent config keys, and any CLI option or env var anywhere.
