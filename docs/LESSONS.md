# Slab Worthy — Project Lessons

> **Operator:** Mike Berry · **Last updated:** 2026-06-06
> **Scope:** Lessons specific to working on Slab Worthy. Read after `CLAUDE.md` during the
> session-opening protocol. Cross-project lessons live in
> `C:\Users\mberr\.claude\projects\shared\LESSONS_CROSS_PROJECT.md`.

## Format

Each entry: an ID, a one-sentence **RULE**, **WHY**, **HOW TO APPLY**, and (optionally) the
**SOURCE** incident. A lesson is a rule sentence for future behavior — not an error log.
Promotion to the cross-project file is Mike's call; Claude only proposes at session end.

---

## Active lessons

### L-SW-2026-001 — "Looks good" is not commit/deploy authorization

- **RULE:** Passing verification, a stakeholder saying *"the batch looks good,"* or being handed a
  task whose final step is a deploy does **not** authorize committing, pushing, or deploying. Commit,
  push, and deploy each happen **only** when Mike explicitly says so **in that turn**, or runs them
  himself. If an assigned deploy task requires an uncommitted prerequisite, **stop and ask** — never
  commit/push to unblock yourself.
- **WHY:** Authorization is per-action and per-instance, not implied by verification status, task
  framing, or prior approvals. Mike controls exactly when code lands in git and ships to production.
  Treating "approve the work" as "ship the work" removes his control over timing and is hard to undo.
- **HOW TO APPLY:**
  1. After verifying a change, present the diffs + the exact `git add … ; commit ; push ; deploy`
     command block, then **wait**. Do not run any of it.
  2. Read "looks good" / "verification passed" as approval of *quality*, not a go signal. Get a fresh
     explicit instruction before **each** of: commit, push, deploy.
  3. If the task itself is "deploy X" but X isn't committed yet, surface that gap and ask how to
     proceed — don't silently commit to satisfy the deploy step.
  4. Distinguish the three actions: explicit authorization to commit is not authorization to push;
     authorization to push is not authorization to deploy. Confirm each.
- **SOURCE:** 2026-06-06 session — established as a standing protocol after the reconciliation +
  fixes batches. Candidate for cross-project promotion (applies to every Mike project), per the
  governance in `LESSONS_CROSS_PROJECT.md` — proposing for Mike's decision.
