# Slab Worthy — Project Lessons

> **Operator:** Mike Berry · **Last updated:** 2026-06-19
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
