From Mike - This was generated from LESSONS.md by Frodo on 2026-09-14 and the repo is authoritative.

## Index — trigger conditions (added 2026-09-14)

> One line per lesson: the **situation** that should send you to the full entry, not its story.
> Test for a line: would someone who has never read the lesson recognise, from the line alone, that
> they are in it now? **Add a line here whenever a lesson is added; a lesson with no index line is
> one nobody finds.** Numeric order here; the entries below are not in numeric order.

- **001** — About to run `git add`/`commit`/`push`/`deploy`/`purge` yourself, under any phrasing of approval.
- **002** — Writing a commit message before the staged file list is final.
- **003** — Diagnosing a grading-accuracy complaint; was the grade retained? Check before theorising.
- **004** — An env var you just changed on Render still reads the old value in the service or shell.
- **005** — About to touch a billing/Stripe flow, key, or ID without a read-only pre-flight first.
- **006** — A config value is "right there" in the dashboard but the code behaves as if it is missing.
- **007** — Generating theories about an opaque error instead of making it log its own reason.
- **008** — About to say what is pending or hand over a commit/deploy plan from memory, not `git log`.
- **009** — A fuzzy match is about to write a shared key on an aggregate score alone; no per-token guard.
- **010** — Many log lines carry the same timestamp.
- **011** — A cleanup step deletes tokens before a matcher; tightening the matcher surfaced "new" damage.
- **012** — Adding or multiplying image decoding on a request path, on an instance with a memory ceiling.
- **013** — Alerts flap or storm; a shared dedup store is fed by per-worker or per-replica observations.
- **014** — Characterising a dataset from one table; a `source`/`type` column carries a DEFAULT.
- **015** — Reporting clean/zero/no-match without proving the probe could hit — or a hit not proven live.
- **016** — A displayed number whose label you cannot trace to the expression that computes it.
- **017** — A manual ship step (reload, deploy, purge, env edit) with no artifact that proves it happened.
- **018** — About to trust or add a URL param, flag, or config key without finding the code that reads it.
- **019** — Removing a filter/guard/condition scoped from the named clause, not the whole definition.
- **020** — Code and copy disagree; or you are naming a new string/field inside the fix for a mislabel.
- **021** — Copy lives outside the repo (Stripe, Resend); an audit matched a claim, not its reader.
- **022** — About to `purge` before the Pages build has finished; a post-purge check shows old content.
- **023** — A script or file must EXIST in the container (Render shell), not merely be committed or served.
- **024** — Stating what a set of rows "is" from a story, a proxy predicate, or a smaller sample.
- **026** — Replacing a rule with one that "does more"; the honest outcome may be "cannot be written yet".
- **027** — A fix regressed rows that were correct before; check whether it removed a mask.
- **028** — Asserting something exists or does not, without naming a surface that could return a hit.
- **029** — A `Grep`-tool null over paths `.gitignore` hides (`scripts/cp1_*`, `.env`, `*secret*`).
- **030** — A record saying "not committed / not deployed" is about to ride in the commit that ships it.

(025 is reserved — see the ID note under Active lessons.)
