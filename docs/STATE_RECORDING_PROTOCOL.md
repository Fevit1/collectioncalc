# State-Recording Protocol (DO + BO)

*Written 2026-06-27 after a concrete failure: Mike told DO at shutdown to "record where we were"
so the next session could resume clean. DO recorded the milestone state but NOT the most recent
decision reversal (SAM segmentation had just superseded the controlled-background re-capture plan).
Next morning DO reconstructed an overview from the stale spec doc and recommended the dead re-capture.
BO caught it only because BO's thread happened to still hold the SAM arc in context — a luck-shaped
save, not a system-shaped one. This protocol makes it system-shaped.*

> **This file is part of the operating model.** It is referenced from `CLAUDE.md`'s SESSION OPENING
> PROTOCOL and must be re-read (Rule 3) before producing any "where are we" overview or resuming after
> a gap. The canonical decision record it governs is `docs/sessions/WHERE_WE_LEFT_OFF.md`.

---

## The core problem this solves
Agents (and humans relaying between agents) lose the *most recent decision* most easily, because:
- A superseded plan has more "dwell time" in the record than the thing that just replaced it.
- "Record where we are" captures the current *position*, not the recent *reversals* — and reversals
  are exactly what reassert themselves when context is lost.
- The danger zone is the **pivot**: right after an approach/infrastructure change, the OLD approach is
  the most-rehearsed thing in context and the NEW one is a single fresh event. Lose context there and
  the agent reverts to the well-worn dead plan.

**Principle: state lives in files, not memory. Reversals are logged louder than decisions. The record
is written at the moment of deciding, not at shutdown.**

---

## Rule 1 — Log decisions WHEN they happen, not at milestones or shutdown
Do not batch state-recording to the end of a session ("record where we are before I go"). By then the
freshest, most fragile decisions are the ones most likely to be compressed away. Append to the decision
log at the moment a decision is made. Shutdown recording is a *final sweep*, not the primary mechanism.

## Rule 2 — Log REVERSALS as reversals, with a tombstone
This is the rule that would have prevented the failure. When a plan changes, do not just record the new
plan. Record:
- **DEAD:** what the plan WAS (the specific, named thing — e.g. "controlled-background re-capture per
  E3_CAPTURE_SPEC.md").
- **REPLACED BY:** what it is now ("E3 runs on SAM masks of existing photos").
- **REASON:** why it flipped ("SAM 24/24 incl. white-on-white; classical ~6/24").
- **SUPERSEDES:** name the now-stale artifact explicitly so a future read doesn't resurrect it
  ("E3_CAPTURE_SPEC.md is SUPERSEDED — do not execute it").

A future instance re-reading "Y is the plan" may still pattern-match to X if X has more dwell time.
A future instance re-reading "X is DEAD, do not do X, Y replaces it because Z" will not. Mark the
tombstone, not just the new direction.

## Rule 3 — Keep a single durable, decision-oriented state file, re-read before acting
One canonical file (WHERE_WE_LEFT_OFF.md) is the shared memory both instances read. It is NOT a
milestone trophy case — it is the live decision record. Before producing any "where are we" overview
or starting work after a gap, RE-READ it AND scan recent conversation for decisions made after the
file's last write. If the conversation contains a decision newer than the file, the file is stale —
update it before acting on it. Never reconstruct state from a spec doc alone; spec docs lag decisions.

## Rule 4 — Don't defer logging "until X resolves"
Deferring the log to avoid churn (e.g. "hold the log until E3 resolves") optimizes against the wrong
cost. The churn of an extra log line is trivial; the cost of a lost reversal is a wasted re-shoot or a
rebuilt dead plan. If a decision is made, log it now — even if the larger arc is unresolved. A log can
hold both "resolved" and "in-flight, current decision = Y, X is dead" at once.

## Rule 5 — The "what just changed" checkpoint
When asked for an overview, or when resuming after a gap, the FIRST line of the response states the
single most recent decision or reversal, before any milestone summary. This forces the fragile fresh
fact to the top instead of letting it get buried under well-rehearsed older state. Format:
  "MOST RECENT CHANGE: [what changed], [date]. This supersedes [what it replaced]."

## Rule 6 — On relays between instances, relay reversals AS reversals
(For Mike, who relays BO↔DO.) When relaying a changed plan to the other instance, frame it as the
reversal, not just the new order. "Build E3 on SAM masks" executes fine but doesn't overwrite the old
plan in the receiving instance's model. "The re-capture is DEAD — SAM replaced it — here's the new
build" updates the model. The framing of the relay determines whether the instance learns the new fact
or just follows the new order while still believing the old plan.

---

## Why this matters beyond today: autonomy implications
The BO/DO/Mike triangle has a built-in error-correction layer a single autonomous agent lacks: DO can
drift, BO catches it, Mike corrects. Three checkpoints. An autonomous agent collapses all three into
one instance — it will confidently execute a stale plan with no second instance to notice.

Therefore:
- **Autonomy is safest on stable, well-specified, non-pivoting work** (e.g. wiring a lookup against a
  fixed spec — the plan doesn't change, so there's nothing to forget).
- **Autonomy is most dangerous on research/approach-changing work** (e.g. the E1/E2/E3 recovery arc),
  where every result can pivot the plan and every pivot is a forgettable event.
- **The defense is externalized, reversal-aware, re-read-before-acting state — not better agent memory.**
  Agents forget; files don't. Match autonomy to plan stability.

---
*Adopt into CLAUDE.md operating model. The one-line version: write decisions to the durable file the
moment they're made, log reversals with a tombstone naming the dead plan, and re-read the file (plus
scan for newer decisions) before acting after any gap.*
