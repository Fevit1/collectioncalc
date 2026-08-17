# Where We Left Off - Aug 12, 2026

## 2026-08-12 — 🟠 **JOSEPH VICARIO PHOTO BACKFILL: SCOPED, SCRIPT WRITTEN, NOT RUN.**

**MOST RECENT CHANGE (Rule 5): the Vicario recovery is 20 rows, not 21, and the two rows
that "did not resolve" were never ambiguous. Re-measured 2026-08-12 against live data.
Supersedes the 2026-08-06 diagnosis in every figure below.**

⚠️ **THIS ENTRY EXISTS BECAUSE THE LAST ONE DID NOT.** The 2026-08-06 diagnosis — a real
user, 100% photo loss, a hard 2026-11-04 purge deadline — was **never written to any file**.
`grep -i vicario` across the entire repo returned **zero** on 2026-08-12, six days later. It
survived only in conversation. That is a **Rule 4 violation** (log the decision when it is
made, not when the arc closes) on the single item in the project with an external deadline
and a named human attached. Recorded at Mike's direction: *"the state-recording gap is yours
to close."*

### THE INCIDENT

`user_id 38`, `vicariojoseph.jv@gmail.com`, signed up 2026-08-05 23:23 UTC. Between
**01:22 and 03:51 UTC on 2026-08-06** he saved **21 comics**; every one carries exactly
`{"back": null, "front": null, "spine": null, "centerfold": null}`. 100% of his collection
has no photos and the app reported success on all 21 saves.

**Mechanism (measured, not inferred):** of 90 `/api/images/submission` calls — **69× 400,
11× 500, 10× 200**. The ten 200s took **52–85 seconds**, every one past `app.html`'s 30s
`Promise.race` upload timeout. The browser had already given up and saved all-null while the
server went on to succeed. *The save genuinely succeeded; only the photo URLs were abandoned.*

### CORRECTED FIGURES — re-measured 2026-08-12

⚰️ **DEAD: "19 of 21 resolve, rows 95 and 96 need disambiguation."**
**REPLACED BY: 20 recoverable, 1 permanently lost, 0 needing disambiguation.**
**REASON:** two independent errors in opposite directions.

| | 2026-08-06 | measured 2026-08-12 |
|---|---|---|
| collections rows | 21 | 21 ✓ |
| grade_submissions | 25, 24 with photos | 25, 24 with photos ✓ |
| resolve to one candidate | 19 | 19 ✓ |
| **actually recoverable** | *(not stated)* | **20** |
| objects | "84" | **64 source read · 80 written · 20 rows updated** |

- **Collection 89 (Captain America #6) is UNRECOVERABLE.** It resolves cleanly to submission
  46, whose `photos` column is **NULL** — the persist thread inserted the row and died before
  the photo-backfill `UPDATE`. The row asserts `photos_used = 4` and a populated
  `photo_labels`; **both are true statements about what the GRADER consumed and neither is a
  claim about what was STORED.** Instance of **[[L-SW-2026-016]]** in the retention layer. Any
  matcher keying on those fields writes four broken URLs. **Key on the `photos` jsonb only.**
- **Rows 95/96 were a window artifact, not an ambiguity.** Submission 50 is the *only*
  Daredevil submission in all 25 rows and the last grade of the session. Collections 93/94/95/96
  are four **Save clicks on one grade report**, 45/124/201/252s later, agreeing on title, issue,
  publisher (`Marvel`), year (`1983`), grade (`8.0`) and confidence (`94`). The ±3min window was
  simply too narrow. Same shape resolves 92 → 48 (Strange Academy).
- **The mapping is not a bijection:** sub 48 → 2 rows, sub 50 → 4 rows. **Mike's call
  2026-08-12: reconstruct faithfully — four identical Daredevil covers.** Had the uploads
  worked, each save click would have uploaded its own copy under its own `grading_id`.
  Per-row prefixes, not shared objects. To be explained in the message to Joseph.

### THE ARTIFACT

**`scripts/jv_photo_backfill.py`** — written 2026-08-12, **NOT RUN, NOT COMMITTED.**
Dry-run default; `--execute` required. Runs in the **Render shell** (has `DATABASE_URL` +
`R2_*`; local `.env` has only `DATABASE_URL_RO`). Backend-only → **`deploy`, no `purge`.**

Design: copies to **NEW `submissions/{grading_id}/{label}.jpg` keys**; `collections.photos` is
never pointed at a `grade_submissions/` key — the two key spaces stay disjoint because the
purge job's safety depends on it and nothing enforces it. Label map
`front_cover→front`, `back_cover→back`. Per-row transactions, R2 first, DB commit last.
Guards: `user_id = 38` + explicit 20-id literal + `photos NOT LIKE '%http%'` (which is what
makes a re-run safe). Positive-controlled R2 probe (**[[L-2026-024]]**) and a public-URL base
**derived from a healthy row** then cross-checked against `r2_storage` (**[[L-2026-026]]**).
Rollback printed *before* any write. Verified read-only 2026-08-12: 20/20 pairs pass, and a
deliberately corrupted pair (col 75 → sub 26) is rejected — the verifier can return a hit.

### ✅ EXECUTED 2026-08-12 — 20 updated, 0 failed

Mike ran the dry run, then `--execute`, in the Render shell. **70 objects copied, 10 kept
existing, 20 rows updated, col 89 correctly excluded.** Spot-check on a copied URL: 200.
Verified read-only afterwards: all 20 rows at 4/4, every URL prefix matches that row's own
`grading_id`, and **0 rows point at a `grade_submissions/` key** — the disjointness constraint
held. The only remaining all-null collections row in the entire table is col 89.

**🔍 INCIDENTAL FINDING — the KEEP-EXISTING objects are 3–4× LARGER than the sources.**
1.4MB vs 355KB on the Daredevil front. So **rows 93 and 94 carry Joseph's ACTUAL
full-resolution uploads** (his own late-landing 200s, kept rather than overwritten) while
**rows 95 and 96 carry copies of the grader's normalized versions**. Same book, four rows,
**two image qualities**. Recorded rather than smoothed, at Mike's direction — it is faithful
to what happened, and it is **evidence that his originals were large**, which bears directly
on the upload-failure question below: 1.4MB stored implies a much larger base64 body on the
wire from a phone, pre-`85617c6`.

⚠️ **OPERATOR FRICTION, fixed:** the script needed `PYTHONPATH=/app` and the variable does not
persist between invocations, so it failed identically on the first dry run *and* the first
`--execute`. It failed **safely** — nothing written either time — but a step the operator has
to remember is a step that gets forgotten. Now resolves the repo root from `__file__` via the
`_HERE`/`_ROOT` convention already used by `scripts/cp1_*.py`; verified running from a foreign
cwd with no `PYTHONPATH`. Same principle as deriving a value rather than typing it.

### ✅ 2026-08-13 — USER 42 EXPLAINED. THE ROOT CAUSE APPEARS FIXED. **CLAUDE'S ERROR, CORRECTED.**

⚰️ **DEAD: "user 42, 2026-08-11, collection 101 saved with three of four photos null — still
unexplained; the next user is still exposed."** Stated by Claude repeatedly on 2026-08-12,
including **in the body of commit `3c28da5`**, and used as the reason Joseph could not be told
the bug was fixed.
**REPLACED BY: there was never a failure. `sub 69` has `photos_used = 1` and one key,
`front_cover`. User 42 uploaded ONE photo.**
**REASON:** `app.html` initialises `photoUrls` with all four slots null and fills only the ones
that have a photo, so `{front: URL, back: null, spine: null, centerfold: null}` is the **correct**
result of a one-photo save. His entire request history is **100% HTTP 200 — zero failures of any
kind.** 8 of his 9 grade submissions are `photos_used = 1`; single-photo grading is simply how he
uses the product.
**SUPERSEDES** any statement that the upload bug survived `85617c6`. Do not re-raise it.

⚠️ **THE ERROR IS THE LESSON: absence read as failure, without establishing that the probe could
tell "upload failed" from "no photo was ever taken."** That is **[[L-2026-024]]**, committed by
Claude, three times, in the same week the same rule was being applied correctly elsewhere. The
disproof was one column away — `photos_used` — in a table already being queried.

**THE POST-FIX RECORD** (`85617c6`, 2026-08-06 21:50 UTC):

| `/api/images/submission` | before the fix | after |
|---|---|---|
| 200 | 663 (avg 1,553ms) | **14 (avg ~800ms, max 1,179ms)** |
| 400 | **81 (avg 19,828ms)** | **0** |
| 500 | 11 | **0** |

**Three four-photo saves have completed since the fix — users 3, 39 and 42 — all 4/4, all 200,
every photo under 1.2s.** That is the exact shape that failed for Joseph, whose 400s averaged
**twenty seconds**.

⚠️ **NOT PROOF. n=3, on unknown networks.** The honest position: **no known unexplained photo
loss exists anywhere in the system**, and the failing shape now succeeds. Cols 29 (2026-02-14)
and 65 (2026-06-15) are partial but **predate the earliest `grade_submission` in existence
(2026-06-27)** — no retained source exists, so they are **unmeasurable, not unexplained**; do not
count them either way. The 10 `user IS NULL` rows on that endpoint are **OPTIONS preflight**
(396 overall, 0ms), not a hidden failure population.

**✅ THE NEW INSTRUMENTATION IS CONFIRMED WORKING FROM PRODUCTION DATA, not from the deploy:**
`error_message='non-json-404'` with `response_summary` carrying the Werkzeug HTML — the exact
text that used to be discarded — plus `request_size_bytes` on **2,311 of 2,458** requests since
deploy, including `req=2190265` on the verified 429.

### ⚠️ THE ROOT CAUSE IS NOT FIXED — *superseded 2026-08-13, see above*

`85617c6` (upload resize, 2026-08-06 **21:50 UTC**) landed **7 hours after Joseph's last
visit** — he never saw it. It has **not** been shown to close this: **user 42, 2026-08-11,
five days later, collection 101 saved with three of four photos null.** Do not tell Joseph it
is fixed. The 400-branch hypothesis (truncated request bodies from a mobile uplink) is
**bounded but not closed**: moderation is ruled out by evidence — `content_incidents` has
**zero rows for user 38** and the blocked path logs before returning 400 — but
`request_logs.error_message` and `response_summary` are **NULL on all 80 failures**. The
endpoint records that it failed and not why (**[[L-SW-2026-007]]**).

### 🔬 `/api/images/submission` INSTRUMENTATION — the NULLs were a discarded answer

⚰️ **DEAD: "the endpoint records that it failed and not why."**
**REPLACED BY:** `after_request` *was* capturing the reason and **throwing it away** for any
response whose body was not JSON. **REASON:** `wsgi.py` read `response.get_json()` and took
`data.get('error')` under a bare `except: pass`. Werkzeug's own 400/413/415 pages are **HTML**,
so every framework-level failure logged NULL while route-level failures logged fine.

**The positive control that makes the NULLs evidence (L-2026-024):** the logger demonstrably
works — `/api/grade` 429s on **the same account, the same night** logged
`error_message='monthly_limit'`, and 145 of 267 4xx table-wide carry a message. Since **all
four** reject branches in `api_upload_submission_image` return `jsonify({'error': ...})`,
a NULL on all 69 of Joseph's 400s proves **none of them came from that route**. Combined with
**zero `content_incidents` rows for user 38**, moderation is excluded twice over. The 400s were
raised by `request.get_json()` before the handler.

Shipped:
- **`wsgi.py after_request`** — falls back to the response body (≤1000 chars) into
  `response_summary` with `error_message='non-json-{code}'` when no JSON `error` key exists;
  now also records **`request_size_bytes`** (`request.content_length`) and
  `response_size_bytes`. ⚠️ `response_summary` had been written on **0 of 220,399 rows** — a
  column `log_request()` accepts and nothing has ever passed ([[L-SW-2026-018]]).
- **`routes/images.py`** — `get_json(silent=True)` keeps the failure **inside** the handler so
  it can self-report ([[L-SW-2026-007]]) instead of becoming an anonymous Werkzeug page; logs
  **declared vs received bytes** and a `truncated=` flag, which is the direct test of the
  mobile-uplink hypothesis. Greppable `[IMG-SUBMIT]` prefix. Moderation and R2 legs timed.
- ⚠️ **BEHAVIOUR CHANGE, deliberate:** an R2 upload failure used to return **HTTP 200**
  carrying `{'success': false}`. `request_logs` only sees the status, so **every R2 failure was
  recorded as a success** and was structurally invisible to exactly this investigation. Now
  **502**. `app.html` checks `uploadResult.success`, never `response.ok`, so client behaviour
  is unchanged.

⚠️ **This is observation, not a fix.** It makes the next occurrence self-reporting. The 400
cause remains **inferred**, and user 42 (2026-08-11, col 101, 3 of 4 null) is still unexplained.

### 💸 THE 429 WALL — stale copy that has been refusing money for seven weeks

⚰️ **DEAD: "the 429 has no upgrade CTA."** **REPLACED BY:** it had an **anti-CTA**.
`app.html` rendered *"Want more gradings? Premium plans coming soon!"* with a single
**"← Back to Home"** button — while **Pro has been purchasable since 2026-07-29**
(`COMING_SOON_PLANS = ('dealer', 'guard')`; Pro is the one tier `create_checkout_session()`
will sell). **REASON:** the copy was true when written and nothing re-checked it.
**Joseph saw it seven times across three visits.** Mike, 2026-08-12: *"I have almost no
traffic, so the absolute number is small. The rate is 100%."*

Textbook **[[L-SW-2026-020]]** — correct code, correct mechanism, false label, no test could fail.

**What the refusal already knew and never said:** `routes/grading.py:547` selects
`plan, is_admin, gradings_this_month, gradings_reset_date` and derives the limit from `PLANS`.
Plan, usage, limit and reset date were all in hand; only `limit`/`used`/`resets_at` were emitted.

Shipped (Mike's three answers: **name the number not the tier · keep the reset date but
subordinate it · never show Guard**):
- **`routes/billing.py`** — `next_purchasable_upgrade(plan_key, limit)` returns the **cheapest
  tier the user can ACTUALLY BUY** that raises their cap. Filters on the same
  `COMING_SOON_PLANS` constant that `create_checkout_session()` refuses on, so an unbuyable
  tier **cannot** be advertised at the moment of purchase intent — the failure mode is deleted
  rather than watched ([[L-SW-2026-019]]). Verified with a negative control: temporarily
  removing `guard` from the set makes a Pro user's offer appear and a free user still get Pro
  (cheapest wins); restoring it returns `None`.
- **`TRIAL_PERIOD_DAYS = 14`** — was a bare literal in `create_checkout_session()`. The moment
  a trial length is quoted to a user it becomes a **claim**, and two copies drift silently.
- **`routes/grading.py`** — the 429 body now carries `plan` and a derived `upgrade` object.
  Wrapped so a derivation failure degrades to the previous shape, never a 500 on the cap path.
- **`app.html`** — *"You've used all 25 gradings this month"* → **"75 more gradings this
  month · Free for 14 days, then $4.99/month. Cancel anytime."** → button **"Get 75 more
  gradings"**. Reset date kept, subordinated: *"Or wait — your gradings reset on Sep 01."*
  Exit is now **"Back to my collection"**, not "Back to Home". Every number interpolated from
  the server; **if `upgrade` is null the offer block renders as nothing at all** (omit over
  assert). `startCapCheckout()` goes **straight to Stripe Checkout**, not `/pricing.html` —
  and uses the `checkout_url` response key (**not** `url`; the wrong key fails silently into
  the generic alert, indistinguishable from a decline).

**🐛 FOUND IN PASSING, AND IT IS THE OTHER HALF OF THE WALL:** `routes/grading.py` referenced
**`MONTHLY_GRADING_LIMIT`, deleted by `bfd231c` (2026-06-18)** when the per-tier cap landed —
inside a bare `except Exception: pass`. The `NameError` was swallowed, `result['grading_usage']`
was never set, and `app.html`'s **"N of 25 free gradings remaining this month" counter has not
rendered for ~8 weeks** (it is guarded by `if (counter && text && usageData)`). *The cap arrives
as a surprise because the only forewarning the product has was silently dead.* Fixed to read
per-tier from `PLANS`; the bare `except` now logs.

**"Coming soon" sweep (Mike: "if it is wrong in one place it is likely wrong in others"):**
run across all rendered HTML/JS. **`app.html:2434` was the only false instance.** Every other
hit is accurate — Signature ID, Market Pulse, Price Lookup, unbuilt export/bulk-delete, the old
`collectioncalc.html` landing page. `pricing.html` is **correct**: Pro sells via
`startCheckout('pro')`; Guard and Dealer are roadmap entries routed to `/contact.html`.
**Tombstoned per [[L-SW-2026-014]] so the next sweep does not re-raise it: pricing.html's
tier copy was investigated 2026-08-12 and found correct. Do not "fix" it.**

### 🎭 FIX F — EDITION SPAN (BUILT + VERIFIED 2026-08-13, NOT SHIPPED)

**THE CASE:** X-Men #1 at grade 9.0 returned **$36.00** with `verdict_reliable` TRUE and confidence
HIGH, on a six-figure book. Both the 1963 and 1991 volumes carry `canonical_title = 'X-Men'`, so
branch A pools them and 242 comps at a $71 median outvote 27 at $6,100.

⚠️ **WORSE THAN THE INFLATION CASE.** Wolverine #181 at $6,735 was inflated, and a user holding a
common book might sanity-check it. This is **DEFLATED on a genuine key**: $36 looks plausible, the
verdict is confident, and the user walks away from a six-figure comic.

**Design (settled across two prior sessions, not relitigated):** between-cluster not within-grade;
**both** signals required (year span AND price ratio, each rejecting the other's false positive);
gated on `fmv_method == 'exact'`. The gate is the design — every other tier is already hedged, so F
can only fire where a confident verdict would otherwise escape, and `exact` guarantees ≥3
same-grade comps for the string to name.

### ⚰️ THE FIRST IMPLEMENTATION DID NOT FIRE ON ITS OWN CASE

⚰️ **DEAD: "split at the single widest year gap, after a whole-range span test."**
**REPLACED BY:** evaluate **every** candidate split; fire if any qualifies.
**REASON:** X-Men #1's years are `1963:n=27 · 1990:n=4 · 1991:n=242 · 2021:n=1`. The real boundary
1963→1990 is a **27**-year gap splitting 27/247 at 84.7× — a clean fire. But **1991→2021 is
THIRTY years**, so the split landed there, produced a high cluster of exactly **one comp**, failed
`MIN_EDITION_CLUSTER_COMPS`, and returned False. **The size floor rejected the whole detection
rather than the bad split.** A single $110 eBay row disarmed the hedge on a six-figure book.

⚠️ **AND BATMAN #423 HAS THE IDENTICAL STRUCTURE** — a lone 2022 row wins its gap — **and returned
the DESIRED answer by accident rather than by mechanism.** A verification that only checked
outcomes would have read that as evidence the code worked. This is why the sweep reported
candidate splits and cluster sizes rather than booleans.

**The year test also moved, and it is a correctness change:** from a precondition on the whole
dated range to **the gap at the candidate split**. Whole-range span answers "does this pool cover a
long period", true of nearly any long-running title; the gap at the split answers "are these two
groups separated in time", which is what between-cluster means.

### ✅ VERIFICATION — same-snapshot A/B is the decisive result

The corpus grew measurably mid-verification (ASM #300's pool 405→461 in about an hour), so absolute
counts are snapshot-dependent and old-vs-new could not be compared across runs. The old rule was
reconstructed verbatim and both were run over **one snapshot**, 481 production-shaped
`(canonical_title, issue_number)` cells with ≥6 dated comps:

```
FIRES UNDER NEW ONLY (1):  X-Men #1  84.7×  boundary 1963|1990
FIRES UNDER OLD ONLY (0):  none
FIRES UNDER BOTH   (5):  ASM #1 · Avengers #1 · AF #15 · Invincible #1 · Daredevil #1
                         — identical ratios to the decimal
```

**The entire added risk surface is one cell, and it is the cell the change was written for.**
Six fire, **zero false positives**, every one genuinely multi-volume.

| book | grade | expected | actual |
|---|---|---|---|
| X-Men #1 | 9.0 | withhold | ✅ **84.7× on 1963\|1990** |
| ASM #300 | 9.0 **and** 9.8 | unchanged | ✅ **zero candidate splits** — no gap in 1988–2006 exceeds 15y |
| Absolute Batman #1 | 9.8 | unchanged | ✅ zero candidate splits (2024–2026, largest gap 1y) |
| New Mutants #98 | 9.8 | unchanged | ✅ single year 1991; no gap exists |
| Spider-Man #1 | 9.8 | withhold | ❌ **STILL MISSES** — see below |

⚠️ **ASM #300 is now SAFER, not merely still-safe.** Under the old rule it passed the whole-range
precondition (2006−1988 = 18 > 15) and was saved downstream by a 1.6× ratio. Under the new rule it
is rejected **earlier**, on time-separation itself. Same for Absolute Batman #1 and New Mutants #98.

**F changes the confidence label, not the number.** X-Men #1 @9.0 still returns $36.00 — now marked
unreliable rather than confident, with ROI withheld.

### ❌ OPEN: SPIDER-MAN #1 @9.8 STILL RETURNS $110.00 CONFIDENTLY

One of the six acceptance criteria **fails**. Its pool has exactly one candidate split
(`1990|2009`, gap 19y) at a **4.4×** ratio — the corpus contains no ≥20× discontinuity among its
year-known comps. **This is a data/threshold question, not a split-selection one, and this change
cannot fix it.** Whether the expectation or the mechanism is wrong is undetermined and was not
guessed at. Not a regression: F leaves this cell exactly as it already was.

### ⚠️ OPEN: THE CONSTANT'S JUSTIFICATION DOES NOT REPRODUCE

`EDITION_PRICE_RATIO = 20.0` carried the argument *"AF #15 (26.9×) and Batman #423 (22.3×) sit
close to the line, so a downward move reaches real single-edition books quickly."* Measured with
the shipped matcher: **AF #15 = 185.5×**, **Batman #423 does not fire**, **X-Men #1 = 84.7× not
422×**. May be methodology rather than error — the difference was deliberately **not** reconciled,
and the agent stated its exact pool construction so the two are comparable. **Nothing sits near 20×
in any measurement taken.** The comment now records both sets and marks the argument unverified;
do not move the constant on the strength of it. What IS measured is the constant's *effect*: 6/481
cells, zero false positives.

### 🐛 CAUGHT IN REVIEW, BEFORE SHIP

- **The long string was FALSE.** *"These 12 sales at grade 9.0 span more than one edition"* — the
  span is detected across the **whole pool**, and X-Men #1's grade-9.0 bucket is 4×1991 plus 8
  year-unknown with **no 1963 sale in it at all**; its span is zero. The sentence attributed the
  span to the sales it named. Rewritten to lead with the problem and claim only that the named
  sales *may be any mix*. Short form corrected the same way.
- **`to_float` is a CLOSURE, not a module function** (defined inside `get_valuation()`), so the
  module-level detector calling it was a request-time `NameError` that `py_compile` passes.
  Converted inline; an AST pass now proves every name in the function resolves.
- **The "checked first" comment asserted disjointness**, so it was verified rather than assumed:
  `estimated = True` is set only where `fmv_method` becomes `'estimated'`/`'estimated_from_raw'`,
  so it cannot co-occur with `'exact'`. The branches are disjoint by construction.
- **Return semantics changed** from whole-range years to boundary years. Consumers audited: only
  `edition_price_ratio` crosses to the client; the years appear solely in the `[VALUATION-F]` log.

### 🔭 THE ARGUMENT FOR AN EXTERNAL SERIES ID

X-Men #1's pool contains **27 genuine 1963 comps at a $6,100 median, outvoted 244 to 27.** The
right answer is *in the pool*, and F **refuses rather than finding it**. That is the clearest
available argument that an external series identifier eventually returns real value rather than
only preventing harm.

### 🧱 CP-1 UNIT 2 — the hedge now survives the save boundary (BUILT 2026-08-13, NOT RUN)

**THE PROBLEM:** every CP-1 hedge held on the grade report and evaporated on save. Superman #76
sits in Mike's own collection (**col 99**) at **$1,815.75** with nothing recording that the figure
came off the **0.25 interpolation floor**.

⚰️ **DEAD: the two-column spec (`verdict_basis` + `verdict_reliable`).**
**REPLACED BY: `verdict_basis` alone.** **REASON:** `verdict_reliable` is **identically**
`verdict_basis === 'supported'` — `sales_valuation.py:736` computes it from
`(estimated_flag, fmv_method)`, and the basis ladder **twelve lines below** assigns `'supported'`
in exactly the else-branch where none of those disqualifiers hold. Same two inputs, same block.
**Two columns can disagree where one cannot:** a client bug could persist
`basis='fabricated', reliable=true` — a state the server cannot produce but the table could hold,
rendering a confident chip over a fabricated reason. Claude argued FOR the second column
originally, on an insurance case that assumed the derivation ran from `verdict` (a genuinely
weaker relation, ambiguous when `roi IS NULL` — 2 of 61 rows are in that cell today). Reversed on
2026-08-13; Mike: *"I was leaning the way you argued me out of."*

**Client-sent, not server-derived.** Re-deriving at save time would consult a corpus that MOVES
(`ebay_sales` 71,652 → 163,374 in three days), so the stored reason could contradict the report
the user acted on seconds earlier — the exact class CP-1 exists to close. Guarded by
`_clean_verdict_basis()` against `VERDICT_BASIS_KEYS`; unknown → NULL. **No CHECK constraint:**
two tiers were added in two days, and coupling tier evolution to migrations is a trap.

**⚠️ CLAUDE'S Q3 CATCH — the original spec was self-contradictory.** "Same strings as the grade
report" + "one column" are **mutually exclusive**: the long-form strings interpolate **five
fields** (`sameGradeComps`, `nearbyThin`, `rawComps`, `excludedVariants`, `gradeLabel`) that a
saved row does not carry. Resolved by sharing the **vocabulary**, not the strings.

**`js/verdict_basis.js`** — `BASIS_KEYS` (8: seven live + `multi_edition`, written ahead of the
edition-span unit), `basisLong(ctx)` (moved verbatim out of `app.html`, ~200 lines of tombstones
intact), `basisShort(basis, {roi})` (parameterless — *a string that cannot state a count cannot
state a wrong one*).

**✅ THE EXTRACTION IS PROVEN, NOT ASSERTED.** The pre-move implementation was sliced out of
`git show HEAD:app.html` — never retyped — and compared against `basisLong` over **33,792 input
combinations** spanning all 8 basis values plus an unknown tier, `null` and `undefined`:
**0 differences**, with a positive control confirming the comparison can detect one.

**One comment had to change and is reported rather than decided** (Mike's standing instruction):
`app.html:2920` read *"REPLACED BY: BASIS_REASONS **below**"*. The map is no longer below — it is
in another file. **Location updated, claim untouched**, with the change itself noted inline.

**🐛 FOUND WHILE TESTING:** `basisShort` conflated *"roi is null"* with *"roi was not supplied"*
(`roi == null` is true for `undefined`), so a caller omitting `opts` would have asserted *"there
are no ungraded sales to compare it against"* — a claim about data it never passed. Now
distinguishes `roiKnown`; unknown ROI on a `supported` row offers **no reason at all**. Defensive
(`collection.js` always supplies it), fixed because the failure mode is an **assertion**, not a
crash.

**Render:** the reason sits behind one tap on the verdict chip, on **all three** chip states —
same argument as showing the chip on every comic: a reason that appears only where something is
wrong makes its **absence** an implicit claim. The affordance appears **only** when `basisShort()`
returns a string; all **61** existing rows (not 59) have NULL basis and render exactly as today,
**no icon** — a disabled one would claim a reason exists and is withheld.

**⚠️ SHIP ORDER IS LOAD-BEARING: THE MIGRATION MUST RUN BEFORE THE DEPLOY.** `/api/collection`
now `SELECT`s `c.verdict_basis`; against a table without the column that is a 500 on the
collection page for every user. Migration is metadata-only (nullable, no default) and takes
`ACCESS EXCLUSIVE` — with `lock_timeout = 5s` it now fails fast rather than blocking the table.
**Confirm autocommit:** an uncommitted `ALTER` holds that lock for as long as the window is open,
taking the whole collection page down rather than one row — a sharper version of the 2026-08-12
hang. Verify from `nlq_readonly`, never from the session that ran it.

### 🏷️ THE STRIPE PRODUCT DESCRIPTION — the surface no sweep can reach

**⚠️ NEW STRUCTURAL FINDING, and it is the reusable one: Stripe-hosted copy is OUTSIDE every
sweep this project runs.** `grep` covers the repo. The Stripe product/price description lives in
the Stripe dashboard, is rendered on the **hosted Checkout page** — the last screen before a
user pays — and **no code sweep will ever find it.** It still carries *"Unlimited comic
valuations with price history and collection tracking"*: the same "Unlimited" claim removed
from `pricing.html` in the **June tier-honesty pass**, which survived precisely because it is
not in the repo.

**Third surface in one family** (Mike, 2026-08-12): `pricing.html` fixed June → the cap screen
fixed today → **Stripe still carrying the original claim.** Same defect as [[L-SW-2026-020]],
one layer further out.

**Audit of the three claims, built from READERS not from `PLANS` ([[L-SW-2026-018]]):**

| claim | verdict |
|---|---|
| "Unlimited comic valuations" | **FALSE.** Pro is **100/month**, hard-enforced at `grading.py:580` with a 429. The only claim the code actively contradicts at runtime |
| "price history" | **NO SUCH FEATURE EXISTS.** The nearest thing is **Market Pulse**, which `js/sidebar.js:461` renders with a `SOON` badge. Zero implementation anywhere |
| "collection tracking" | **TRUE — but not a Pro differentiator.** Free users get the full collection |

**ENTITLEMENT TABLE — 12 keys in `PLANS`; Pro differs from Free on 5; only 3 are enforced.**

| capability | free | pro | enforced? | the reader |
|---|---|---|---|---|
| Monthly gradings | 25 | **100** | ✅ | `grading.py:580` → 429 |
| Slab Guard registrations | 3 | **25** | ✅ | `registry.py:530` |
| Extra photos per comic | 0 | **4** | ✅ | `images.py:325`, limit at `:338` |
| Excel/CSV export | ✗ | **✓** | ❌ **advertised only** | no gate anywhere |
| Multi-photo grading | ✗ | **✓** | ❌ **advertised only** | no gate anywhere |
| Signature ID / month | 0 | 0 | ✅ (`signature_orchestrator.py:802`) — identical, not a differentiator |
| Chrome extension | ✗ | ✗ | ✅ (`vision.py:232`) — identical, Guard+ only |
| Marketplace monitoring · API access · Ownership certs · Priority support | ✗ | ✗ | ❌ no gate; identical on both tiers |
| Bulk operations | ✗ | ✗ | ❌ **ZERO references outside `PLANS`** — fully dead key |

⚰️ **CORRECTS the June tier-honesty finding "3 of ~11 enforced (slab-guard regs, multi-photo,
chrome-extension)".** Measured 2026-08-12 the enforced three are **gradings, slab-guard regs,
extra photos**. `multi_photo` has **no `check_feature_access` call anywhere** — the docstring at
`images.py:300` says *"Requires multi_photo feature"* while the code on line 325 checks
`'extra_photos'`. A label naming a different key than the code reads; June most likely counted
the docstring. And `chrome_extension` is `False` on Pro, so it was never a Pro differentiator.

**🐛 FOURTH SURFACE, in-repo and live:** `plan['export'] = True` for Pro flows through
`/my-plan` into `account.html`'s feature grid, so a paying Pro user sees **"✓ Excel/CSV
Export"** — while `collection.html:165` has a live **📥 Export** button whose handler
(`js/collection.js:1034`) is `alert('Export functionality coming soon!')`. Session 106 Commit C
trimmed export from `pricing.html` and **missed `account.html`.** Same for `multi_photo`.

**✅ FIXED 2026-08-12.** Mike set the description to: *"100 comic gradings per month, 25 Slab
Guard registrations, and up to 4 extra photos per comic."* Three claims, all enforced, all
derived from the table above.

**🔴 FIFTH INSTANCE, FOUND IN THE SAME SITTING — AND A NEW CLASS. The Stripe ACCOUNT business
name read "The Masse".** MASSÉ and Slab Worthy **share one Stripe account** and MASSÉ set the
branding first, so **every Slab Worthy customer saw a different company's name on the hosted
Checkout page.** Corrected to Slab Worthy. The account name is a **separate surface** from the
product description, and on a shared account it can be **wrong for one project while correct for
the other** — so no state exists in which MASSÉ would ever notice, neither repo contains it, and
whoever configures it first wins silently and permanently. It is copy about **who you are** at the
payment step. Recorded in `docs/EXTERNAL_COPY_SURFACES.md` under a new *shared-account dimension*
section and proposed for **cross-project promotion** — by construction it cannot be fixed from
inside one project's canon.

**Logged as [[L-SW-2026-021]]** (both halves: third-party copy is outside every sweep, AND an
audit that greps for the claim rather than the reader issues false passes), with the standing
list in **`docs/EXTERNAL_COPY_SURFACES.md`** — Stripe Checkout, Stripe customer-portal product
names, Resend templates, Cloudflare-hosted copy. Inclusion test: *can a user read it, and can
`grep` reach it?* Of those four, only Stripe Checkout has ever been audited.

**account.html + collection.html fixed in the same pass:** `multi_photo` **removed** from the
feature grid (enforced nowhere, and every tier uploads four photos — listing it implied a gate
that has never existed); `export` now renders **SOON** regardless of the plan flag, so a paying
Pro user is no longer shown a ✓ for an unbuilt feature. The live `📥 Export` and `🗑️ Delete`
buttons in the bulk bar — whose handlers were bare `alert('… coming soon!')` — are now
`disabled` with the SOON badge idiom the sidebar already uses. Delete was fixed alongside Export
because it is the identical defect in the identical control bar; fixing one and leaving the
other is the [[L-SW-2026-019]] mistake in miniature.

### THREE THINGS THAT OUTRANK THE BACKFILL (Mike, 2026-08-12) — ordered

1. **`/api/images/submission` instrumentation.** Same treatment as the grade and extract legs.
   Fix the NULL `error_message`/`response_summary` first, *then* we know rather than infer.
2. **The 429 wall — a conversion failure, not a bug.** He burned 25 grades (Free cap) in one
   night, came back **three times over eleven hours**, uploaded photos each time, watched the
   book get identified, and got a **429 with no upgrade CTA** (7 of them). Then loaded his
   empty collection page and left. Not seen since **2026-08-06 14:52 UTC**. Scope required
   before any copy is drafted: what the 429 returns and what the client renders; whether the
   cap check knows plan and reset date at the point of refusal; what Pro would have given him
   **as a number, not a tier name**.
**✅ ALL THREE CLOSED 2026-08-12/13, plus the two follow-ons — verified by Mike:**
- **Cap screen RENDERED end to end.** *"You've used all 25 gradings this month"*, 75 more for
  $4.99, Pro 100/month, reset date subordinated, exit to collection. **The button reached
  `checkout.stripe.com` with a live session**; cancelled at Stripe rather than completed.
- **`gradings_this_month` = 27**, read back from the **`nlq_readonly` connection** — a different
  session than the one that wrote it, closing the decoy-artifact trap that caused the hang.
- **`lock_timeout = 5s`** on `collectioncalc_db_user`, confirmed in `pg_roles`. ⚠️ `SHOW
  lock_timeout` returned **0 until reconnect** — *the same read-it-from-the-writing-session trap
  one layer over.* A role-level setting applies to NEW sessions only; verifying it from the
  session that set it is the identical defect as verifying a DBeaver `UPDATE` from DBeaver.
- **Pin: 25 and 0.**
- **User 42: explained, no bug** — see the 2026-08-13 correction above.

3. **Pin his submissions before 2026-11-04.** ⚠️ `pinned` **has no writer** — declared,
   `DEFAULT FALSE`, indexed, read in exactly two places (`admin_routes.py:1283` →
   `admin.html:1305` badge), set by nothing. **And there is no purge job at all** — the risk is
   not a running timer, it is that whoever builds it builds it against
   `images_purge_after` + `pinned = FALSE` and runs it. **Recommendation: manual `UPDATE` in
   DBeaver, do not wire the column.** Scope is a live decision: `privacy.html:357` discloses
   the exception for **feedback-related** submissions only, which covers **4 rows**
   (26/28/33 Spawn #77 + 50 Daredevil), not 25. Pinning all 25 exceeds the published window
   for a real identifiable user — cleanest fix is to **ask him in the message that is already
   going out**. DECISION PENDING.

### ⚠️ WHAT'S IN THE DATA BEFORE THE MESSAGE GOES OUT

- **`last_login` is a decoy** (**[[L-2026-023]]**): written *only* by the password-login path
  (`auth.py:903`); a returning user on a live JWT never updates it. It reads 2026-08-05 23:31.
  **`request_logs` is the real record** — he returned 03:54, 13:01 and 14:43 on 2026-08-06.
- **He rated two grades** (`user_feedback`, `rating` = thumbs): **thumbs DOWN** on
  "Spawn #77 Grade: 7" (01:28:34) and **thumbs UP** on "Daredevil #196 Grade: 8" (03:47:47).
- **Spawn #77 was graded three times: 8.0, then 7.0, then 7.0.** He downvoted 44 seconds after
  the second. He watched one book come back with different grades — and kept using the product
  for another two and a half hours. **First hard evidence for grading inconsistency, which has
  been anecdotal since June** and which **[[L-SW-2026-003]]** said was unmeasurable before
  retention shipped. Also Gwenom vs Carnage ×3, Ultimate Spider-Man ×3.
- **Blast radius is exactly user 38** — no other user has the total-loss pattern. User 42's
  col 101 (3 of 4 null) is the only other damage.
- After the backfill the **photos** survive 2026-11-04 regardless (they become collection
  images under `submissions/` keys, `privacy.html:356`). What the pin protects is the
  `grade_submissions` **row** — subgrades, `raw_grade`, `limiting_factor`, model, reasoning.

---

## 2026-08-10 — 🟢 **SESSION LIVE. INDEX SHIPPED AND MEASURED. EXTRACT LEG UNCOMMITTED.**

**MOST RECENT CHANGE (Rule 5): the ~30s comic-ID wait is NOT one item. It is TWO legs, two
requests, two user moments — extract (`/api/extract`, photo upload) and grade (`/api/grade`,
the grade button). Split accepted by Mike 2026-08-10. Supersedes the single roadmap item
that has existed since June.**

**PRIOR CHANGE, same day (2 of 3):** `idx_ebay_sales_canonical_title_norm` was built. The
FMV leg went **11,717ms → 463ms** (second run 455ms, so stable rather than warm-cache).
Supersedes "the valuation comp query takes ~11s and we do not know where."

**PRIOR CHANGE, same day (1 of 3):** the drift guard no longer reports per health poll.
Transition-logged, hourly heartbeat while broken, arming line when healthy. Shipped
`62052ca`. Supersedes "the guard prints the full plan on every observation."

---

### 📊 THE MEASUREMENT THAT SETTLED IT

Two runs of The Terminator #1 through the live instrumentation (`557147d`), before the index:

| | total | q1_ebay_graded | q2_ebay_raw | q1+q2 share |
|---|---|---|---|---|
| run 1 | 10,151ms | 3,099ms / 0 rows | 6,703ms / 1 row | **96.6%** |
| run 2 | 11,717ms | 3,391ms / 0 rows | 7,798ms / 1 row | **95.5%** |

Both runs: `before_request_to_handler=0ms`, `handler_to_pool=0ms`, pool ≤160ms. Segments
summed to total with nothing unaccounted.

⚰️ **DEAD: "the 30s wait might be gunicorn queueing."** **REPLACED BY:** it is SQL, in a
segment we measured, twice. **REASON:** queueing would have to appear in
`before_request_to_handler` or `pool`; both were ~0 on both runs, and the segments already
sum to total, so there is no unmeasured remainder for a queue to hide in. **SUPERSEDES** any
plan to tune worker counts for this symptom. Do not re-raise it.

**AFTER the index — same book, same endpoint:**

```
BEFORE  total=11717ms  q1=3391ms/0rows  q2=7798ms/1rows
AFTER   total=  463ms  q1= 104ms/0rows  q2=  52ms/1rows     (2nd run 455ms)
```

**25× on the leg, 150× on q2.** Index built clean, zero invalid residue, DBeaver returned to
Manual commit. Verified **positively** via the `[VALUATION-TIMING]` line, not by the absence
of drift warnings — the absence alone would have been an unproven negative (L-2026-024).

⚠️ **CARRIED FORWARD, NOT SOLVED: q2 scanned 7.8s to return ONE row.** The index makes that
answer arrive fast; it does not make it a better answer. The Terminator #1 has one raw comp
and zero graded. That is the performance problem and the CP-1 problem in the same query, and
only the performance half is fixed. Remember this when the index makes everything feel solved.

---

### 🔀 THE EXTRACT / GRADE SPLIT — the more important finding

⚰️ **DEAD: "the ~30s comic-ID wait" as a single roadmap item (since June).**
**REPLACED BY:**

| leg | request | user moment | vision calls | instrumented |
|---|---|---|---|---|
| **extract** | `/api/extract` | photo upload | 1, **or 2 if the 180° re-read fires** | ⏳ written, UNCOMMITTED |
| **grade** | `/api/grade` | grade button | **exactly 1** (`runs=1`) | ✅ live in `62052ca` |

**REASON:** they are separate HTTP requests at separate moments. The "one vision call or
two" question belongs ONLY to extract — the 180° low-confidence re-read lives in
`comic_extraction.extract_from_base64`, not in the grading path. `/api/grade` at `runs=1`
makes exactly one Sonnet call, which the code settles without measurement.

⚰️ **DEAD: "parallelise identify and grade" as a BACKEND item (written as backend for ~2
months).** **REPLACED BY:** it is a **frontend sequencing** question. **REASON:** the two are
separate requests the browser initiates at different moments; there is no backend sequence to
parallelise. **SUPERSEDES** any backend scoping of it. Mike, 2026-08-10: *"That has been
written as a backend item for two months."*

**Track 1 (staged honest progress messaging) is unaffected and still ships regardless.**

⚠️ **CONSTRAINT, unchanged since June and restated at Mike's direction:** the Sonnet flip was
deliberate and bought honesty of errors over speed. **Nothing may trade accuracy back.**
Haiku's failure mode is confident fabrication. No proposal in this thread touches model
selection.

---

### 🔇 THE DRIFT GUARD'S OWN LOG VOLUME — fixed, `62052ca`

The guard was correct and far too loud: `/health` is polled ~12×/min (and `/` shares the
handler), so persistent drift emitted **~17,280 lines/day at ~700 chars ≈ 12MB/day** — burying
the `[VALUATION-TIMING]` lines shipped in the same commit, and the next incident after that.

Design: **silent when healthy · loud on transition · heartbeat-floored while broken.**

- ok→drift: the **full 700-char plan**, once. That verbatim text is what made the finding legible.
- drift persisting: one line **hourly**, so the freshest evidence is never >1h stale.
- drift→ok: a `✅ INDEX DRIFT RESOLVED` line **derived from the planner's own choice**, not declared.
- healthy: **nothing**, except one **arming line per worker boot**.
- probe throttled separately to 60s (`INDEX_DRIFT_PROBE_SEC`), removing ~16k DB round trips/day.

⚠️ **The arming line is not noise — it is the positive control.** A guard silent when healthy
is indistinguishable from a guard that is dead, unregistered, or throwing. Mike, 2026-08-10:
*"the guard is currently silent and I have no way to distinguish that from a dead guard until
this deploy lands."*

State is **per-worker with no shared store**, deliberately: shared dedup + per-replica
observation is exactly the L-SW-2026-013 storm mechanism (2026-07-16, ~1 email per 5–15s for
hours). Worst case here is one extra line per worker.

---

### 🐛 FOUND WHILE INSTRUMENTING: `/api/extract` has logged 0 tokens for every request

`routes/grading.py` called `log_api_usage(..., result.get('input_tokens', 0),
result.get('output_tokens', 0))` — but `extract_from_base64` **never returned those keys**.
Every `api_usage` row for `/api/extract` recorded **0 in / 0 out**, indefinitely.

The model name beside them was correct, which is what made it invisible: an accurate label
next to a quantity nothing computed — **L-SW-2026-016**, in the cost-attribution layer. The
comment on that very line claims per-extract cost attribution stays accurate after the
2026-06-16 haiku→sonnet flip; the model half was true and the token half was structurally zero.

Fixed in the uncommitted extract work: `_run_vision_pass` now returns its usage tuple, and
`extract_from_base64` returns real counts **summed across every pass**, so a 180° re-read
shows up as the doubled cost it actually is.
⚠️ **This changes what lands in `api_usage`.** Historical `/api/extract` token rows are zeros
and cannot be reconstructed — do not treat pre-2026-08-10 extract cost data as real.

---

### 📊 THE GRADE LEG, MEASURED — 2026-08-10, The Terminator #1

```
total=20686ms  before_request_to_handler=305ms  cap=301ms  body=33ms  normalize=29ms
quality=7ms  moderation=434ms  vision=18734ms  parse=0ms  post=1137ms
images=3  payload_kb=2241  runs=1  vision_calls=1  moderation_calls=3
model=claude-sonnet-4-6  in_tok=2380  out_tok=809
```

**Vision is 18,734ms = 90.6% of the leg. One call. There is no preamble to optimise away.**

⚰️ **DEAD: the moderation loop as a latency suspect.** **REPLACED BY:** 434ms across 3 calls
— noise. **REASON:** measured, not reasoned about. The missing `break` is still a real code
smell (one Rekognition round trip per photo where the quality gate above it breaks after the
first) and is **deliberately LEFT UNFIXED** — Mike, 2026-08-10: *"I am glad we measured
rather than fixed it. Log it, do not touch it."* **SUPERSEDES** any impulse to fix it on
sight. `moderation_calls=3` keeps the count measured rather than read off the loop.

**Two open questions raised by that line, answered by reading the code (2026-08-10):**

1. ⚠️ **`model=claude-sonnet-4-6` is the CONFIGURED HEAD of the chain, not a stale fallback.**
   `MODEL_CHAINS['sonnet'][0]` is `claude-sonnet-4-6`; `_active_index` only advances on a 404,
   and production logged index 0. **But the chain itself is stale** — `models.py` says
   *Last verified: 2026-06-06*, and the Sonnet generation has moved on since. `opus` is in the
   same state (head `claude-opus-4-8`), which is the precedent Mike cited. **The grading path
   is running a generation behind, by configuration, silently.**
   ⚰️ **DEAD: "the dependency monitor watches our models."** **REPLACED BY:** `check_anthropic()`
   watches deprecations.info for **retirements**. It answers *"is what we use dying?"* — never
   *"is what we use current?"* A superseded-but-supported model is **invisible to it by
   design**. **REASON:** that is why both the opus 4.6→4.8 gap and this one passed unnoticed.
   Same shape as everything else this week: a check that cannot see the thing (L-2026-024).
2. ⚰️ **DEAD — RESOLVED 2026-08-10 BY A PROPER RUN. See "IMAGE SIZE IS A CLOSED
   CANDIDATE" below. The hypothesis in this item was WRONG about the mechanism.
   Kept for the record; do not act on it.**

   ~~⚠️ **`in_tok=2380` is honest, but the images are probably arriving small.**~~
   `usage.input_tokens` **does** include image tokens — this is NOT the `/api/extract`
   structural zero (that was a missing dict key defaulting to 0; here the API populates a real
   value). But the arithmetic does not fit 3 full-cap photos: Anthropic bills ≈ (w×h)/750 after
   fitting the long edge to ~1568.

   | photos land at | billed per image | ×3 |
   |---|---|---|
   | 2000px (cap top) | ~2,113 | **~6,340** |
   | 1500px | ~1,936 | ~5,808 |
   | **1000px (cap bottom)** | **~860** | **~2,580** |

   Observed 2,380 **including the prompt** sits on the bottom row. `_decode_normalize_encode`
   draft-decodes at exactly 1/2 and only thumbnails if the result is STILL over cap, so output
   lands anywhere in **(cap/2, cap] = 1000..2000px** — a documented consequence accepted for
   memory reasons on 2026-07-16, whose **accuracy** cost was never priced. A photo at the
   bottom of that band gives the grader **a quarter of the pixel area** of one at the top,
   while the strict grading quality floor exists precisely because defects need detail.
   🚧 **HYPOTHESIS, not a finding.** `dims=` and `norm_kb=` were added to `[GRADE-TIMING]` to
   settle it in one grade. Do not act on it before that line is read.

**`post=1137ms` and `before_request_to_handler=305ms` are both DB round trips.** Every
`db.get_db()` checkout pre-pings with `SELECT 1`, and `/api/grade` opens and closes the pool
**five separate times** (auth decorators, cap check, usage log, counter increment, usage read)
where `/api/sales/valuation` opens it once. At the ~300ms/checkout that `cap=301ms` shows for a
single SELECT, that is ~1.5s of the 20.7s. Not the problem; a real number for later.
⚠️ `before_request_to_handler` was documented as "~0 by construction." That holds only for
`api_sales_valuation`, which carries **no decorators**. `@require_auth` / `@require_approved`
run between `before_request` and the handler body, so their cost lands in that field. The
control field fired and told us something — which is why it was logged.

### ⚰️ IMAGE SIZE IS A CLOSED CANDIDATE — **not a solved problem**

**Run with real CAMERA PHOTOS, 2026-08-10:**

```
[GRADE-TIMING]   total=25459ms body=801ms normalize=598ms imgmeas=7ms quality=47ms
  moderation=932ms vision=21889ms post=891ms images=4 payload_kb=13038 norm_kb=3658
  dims=1506x2000,1506x2000,1506x2000,1506x2000 in_tok=7534 out_tok=908
  cache_create=0 cache_read=0
[EXTRACT-TIMING] total=14214ms body=337ms quality=316ms moderation=482ms normalize=191ms
  barcode=4082ms vision1=8511ms payload_kb=3874 barcode=miss reread=not_needed
  in_tok=4433 out_tok=320
```

**All four photos land at 1506×2000 — the TOP of the (cap/2, cap] band. The cap works.
Real submissions get full detail.** `in_tok=7534` matches the ~6,340 + prompt predicted for
2000px photos, and `cache_create=0 cache_read=0` proves the cache fields are genuinely zero
rather than assumed.

⚰️ **DEAD: "photos may be reaching the grader at a quarter of the intended pixel area."**
**REPLACED BY:** they arrive at the top of the band. **REASON — and this is the part worth
keeping:** the 512×780 sample that produced the hypothesis came from **eBay SCREEN GRABS**,
not camera photos. eBay serves listing thumbnails at a few hundred pixels, so that was a
**small source arriving small** — it never engaged the draft-halving path at all. The
(cap/2, cap] arithmetic was correct and the proposed *mechanism* never fired. **SUPERSEDES**
any plan to trace the normalization step. Mike, 2026-08-10: *"I nearly sent you off tracing a
step that does not exist."*

⚠️ **Image size is now a CLOSED CANDIDATE for the undergrading complaint (L-SW-2026-003) —
which means the undergrading mechanism is back to UNEXPLAINED.** Ruling a cause out is not
finding one. Do not let the closure read as a fix.

✅ **`dims=52x784` was real, not a rendering artifact.** The emit truncates exactly one field
(`title`, `[:60]`); `dims` passes through whole. Verified by positive control against
`1052x784` and a four-photo 4-digit string — both rendered intact, so a narrow value is a
narrow image. It was a sliver screen grab. Closed.

### 🔦 THE BARCODE SEGMENT — 4,082ms of a 14,214ms extract, on a MISS

Measured offline against the real `scan_barcode` control flow, photo-realistic fixtures:

| source | pixels | miss-path total | ms/MP |
|---|---|---|---|
| 3024×4032 (phone, untouched at the 4096 cap) | 12.2 MP | **6,633ms** | 544 |
| 1506×2000 (grading-cap size) | 3.0 MP | 1,612ms | 535 |
| 753×1000 | 0.8 MP | 396ms | 528 |

**Linear in pixels at ~535 ms/MP across a 16× range.** Yes, it scales with image size.

**Where the time actually goes — the four rotations are NOT the cost:**

```
rotates   113ms          <- 1.7%
decodes  6464ms          <- 97%   across EIGHT pyzbar calls
  per rotation:  pass1 (symbol-filtered) ~515ms  +  pass2 (UNFILTERED fallback) ~1090ms
```

Three structural facts, all observed rather than reasoned:
1. **The unfiltered fallback is 2/3 of the total.** It costs ~2× the filtered pass and runs on
   **every** rotation in the miss case, by construction.
2. **`break` fires only on a HIT**, so `barcode=miss` is structurally the maximum-cost path —
   and a comic without a scannable barcode pays the most.
3. **zbar is running PDF417 and DataBar decoders on a comic cover.** Direct evidence: the
   unfiltered pass emits `zbar/decoder/pdf417.c` and `databar.c` assertion warnings. Those
   symbologies do not appear on comics.

🚧 **UNEXERCISED, stated so it is not mistaken for measured:** the HIT path was **not**
successfully benchmarked — the synthetic bar field was not a decodable UPC, so that run was
another miss. Hit-path cost is **unknown**; only the miss path above is measured.

**What the code permits (NOT a proposal — no fix scoped):** the `break` exists but only on
success; the unfiltered fallback is unscoped; extraction scans at up to 12MP where a UPC needs
only enough resolution to resolve bar widths; and `photo_type` is already known to be `front`,
where a comic barcode is always bottom-left — spatial scope exists and is unused.
`dims=`/`mp=` added to `[EXTRACT-TIMING]` so production confirms the scaling directly.

### ⚠️ LOGGED, NOT SCOPED — no warning for too-small source images

Grading from 512px eBay screen grabs passed `quality=8ms` **without comment** and returned a
confident **8.5**. The grading quality gate has a strict resolution floor, and these cleared
it. A collector browsing eBay listings would plausibly do exactly this. Mike, 2026-08-10:
*"I am not scoping it tonight."* Related to L-SW-2026-016 — a confident output whose input
could not support it, with nothing on screen saying so.

### 🔬 STILL UNMEASURED — do not theorise ahead of it

- **Why one Sonnet call takes ~19–22s. NO LEVER IS CURRENTLY INDICATED.**
  ⚰️ **DEAD: "output length is the likely lever."** **REPLACED BY:** nothing — the question is
  open. **REASON:** the proper camera-photo run moved input **3.2×** (2,380 → 7,534) while
  latency rose only **19%** (18,442 → 21,889ms) and output barely moved (806 → 908). Neither
  term dominates cleanly, so the single-run observation that pointed at output length does not
  survive a second data point. Mike, 2026-08-10: *"I am recording that the lever we thought we
  had identified is no longer indicated."* Do not re-raise output length as the suspect
  without new measurement.
- **Whether the 180° re-read fires in practice** is unknown and **the logs cannot answer it**.
  Extraction logs nothing on a clean success path, so absence of the doubled-cost line proves
  nothing in either direction. That is why `reread=` is now emitted on **every** request
  including `not_needed` — the same silence problem as the drift guard, in a different place.

---

### 📌 SHIP STATE, verified from git at time of writing (L-SW-2026-008)

| | |
|---|---|
| `HEAD` | **`62052ca`** — drift guard + `[GRADE-TIMING]`, **committed and DEPLOYED** |
| `04b2bb8` | ROUGH ESTIMATE badge refactor — was pushed but undeployed; **carried live by the `62052ca` deploy** |
| uncommitted | `comic_extraction.py`, `routes/grading.py` — the `[EXTRACT-TIMING]` unit + token fix |

Backend-only throughout: `deploy` yes, `purge` no. No extension touched, no version bump due.

---

## 2026-08-04 — 🔒 **SESSION CLOSED. ALL THREE UNITS SHIPPED, PUSHED AND VERIFIED.**

**MOST RECENT CHANGE (Rule 5): Phase 1 — `all_comic_sales` is now described in `DB_SCHEMA` and granted
to `nlq_readonly`, so NLQ answers sales questions from the full 173,346-row corpus instead of the
5.8% Whatnot slice. Shipped `3a9892f`. Supersedes "`market_sales` is the only sales table NLQ can
see."**

**PRIOR CHANGE, same day (2 of 3):** `all_comic_sales`'s second leg now emits `market_sales.source`
and carries no `WHERE` clause; it previously emitted the literal `'whatnot'::text` **and** filtered
`WHERE market_sales.source = 'whatnot'`. Supersedes the approved scope of "remove the WHERE clause
only," which was incomplete — see the literal-vs-column finding below.

**PRIOR CHANGE, same day (1 of 3):** the admin NLQ handler no longer executes model-generated SQL on
the app's read-write pool; it uses the SELECT-only `nlq_readonly` role via `DATABASE_URL_NLQ`, and the
`admin_nlq_history` INSERT was split onto the read-write pool. Supersedes "the denylist +
SELECT-prefix check are the NLQ safety model" (in place since the endpoint was written).

---

### 🔒 SESSION CLOSE — 2026-08-04

**Ship state, verified from git at close (not from memory — L-SW-2026-008):**
`HEAD` = `origin/main` = **`d3c5a9d`**, confirmed via `git ls-remote`, not the local tracking ref.

| Commit | Contents |
|---|---|
| `d3c5a9d` | NLQ post-mortem + L-SW-2026-019 promotion pointer (2 files) |
| `63d95ad` | July 16 OOM post-mortem, alone (1 file) |
| `3a9892f` | Phase 1 — `admin.py`, `LESSONS.md`, `WHERE_WE_LEFT_OFF.md`, `nlq_readonly_role.sql` |
| `5f2deb5` · `8709518` | the role fix, pushed earlier the same day |

**Live and verified in production:**
- `nlq_readonly` — SELECT-only, unpooled, 15s `statement_timeout`, read-only session, fails closed on
  missing `DATABASE_URL_NLQ`; `users` granted at **column level excluding `password_hash`** and
  deliberately absent from the table-level grant.
- `all_comic_sales` — `WHERE` clause **and** the `'whatnot'::text` literal both removed; ACL
  byte-identical across the replace.
- Phase 1 — view described in `DB_SCHEMA` (3,609 → 4,889 chars) and granted; raw `ebay_sales` still
  denied to the role.
- **Post-deploy artifact: `admin_nlq_history` row 43**, `result_count` 8, `execution_time_ms` 3312.
  The history split works — query on the read-only role, audit row on the read-write pool.

**Lessons written this session:**
- **L-SW-2026-019** written and ✅ **promoted → `L-2026-026`**.
- **L-2026-025** written — the identity of the executing principal is part of a verification's
  meaning. Carries an explicit **do-not-merge** block against L-2026-024.
- **L-2026-024 amended** — role-filtered `information_schema` views as a blinding mechanism, plus the
  rule that an unconstructable positive control means reporting the check **UNPERFORMED**, never
  "clean but unverified."
- `LESSONS_CROSS_PROJECT.md` at **v1.5, 13 lessons active**, footer confirmation string updated in the
  same edit. ⚠️ That file is **outside this repo and under no version control** — see priority 1.

### 🔬 CP-1 CONFIDENCE MEASUREMENT — read-only, nothing shipped, nothing committed

`scripts/cp1_confidence_measure.py` (**UNTRACKED, uncommitted**). Read-only via `do_readonly`.
No writes, no DDL, no production behaviour change, no git operations. Corpus at time of run:
`ebay_sales` 168,405 · `market_sales` 9,972.

**Findings that stand on their own, independent of the pending tables:**

1. ✅ **No user-facing count or range is computed post-trim.** `graded_sample_size` =
   `len(exact_match)` (`sales_valuation.py:388`, untrimmed), `sales_count` = `len(prices)` (:562),
   `min_price`/`max_price` on untrimmed `prices` (:563-564); same in `/api/sales/fmv`'s tier block
   (:856-864). **The Low-confidence evidence display ("3 sales, $40–$95") is already honest — a CP-1
   design concern closed with no code change** (Mike's call, 2026-08-04).
2. ✅ **The median is INVARIANT under `percentile_trim`.** 4,764 synthetic cells incl. adversarial
   shapes → zero differences; also provable (symmetric trim shifts the median index equally on both
   sides). So FMV, `raw_fmv`, price-curve `avg_price` and the interpolation medians are ALL
   unaffected by trimming.
3. ⚠️ **The trim is NOT 5% at low n.** `cut = max(1, int(n*0.05))` removes a FLAT 2 rows from n=3
   through n=39 — 67% at n=3, 40% at n=5, 25% at n=8, 5.1% at n=39 — then 4 rows at n=40. Sawtooth.
4. ⚠️ **The effective CI floor is n=7, not n=5.** `bootstrap_ci_median` needs ≥5 values and
   production trims BEFORE bootstrapping, so **n=5 and n=6 yield an FMV with NO confidence
   interval.** Verified by calling both functions directly. **Leading candidate for the D2 Low
   boundary — defined by what the engine can actually produce rather than a chosen number.**
5. 🚧 **UNPROVEN CLAIM, carried forward (Mike, 2026-08-04):** *"trimming only ever NARROWS the CI."*
   The first half — that the CI is the only output the trim changes — follows from (2). The
   **direction is asserted, not measured.** Trimming both reduces spread (narrows) and reduces n
   (widens); on a tight, evenly-spaced sample with no real outlier the n-reduction may dominate.
   The script now records **per-cell** narrowing with the **sign preserved, never floored**, and
   reports the count of cells where it is negative plus their buckets. If zero across all three
   seeds the claim becomes established; otherwise it is a finding. Same shape as L-SW-2026-015 — a
   claim whose disconfirming case the probe must be able to surface. **It currently prints
   "UNTESTED, not confirmed" when no comparable cells exist, which is correct behaviour.**

⚰️ **The 3B amendment was REVERSED the same day.** DEAD: "lookup_demand is a sanity check; the
grade_submissions/search_cache/collections union is primary." REPLACED BY: **lookup_demand is
PRIMARY (542 distinct books); the union is the sanity check (89 books), reported per-source.**
REASON (Mike): the NULL `user_id` weakness breaks demand **RANKING** by distinct users — it does not
affect the comp-count **distribution**, which ranks nothing and needs only the set of books looked
up. The demotion traded 6.1× the breadth for an attribution property this measurement never uses.

⚠️ **Sampling method, so Step 3A is not over-read:** universe is 44,423 in-window (title, issue)
pairs with a non-empty `canonical_title`; selection is `ORDER BY md5(seed || title || '|' || issue)`.
That is uniform over **BOOKS, not over SALES** — a 600-comp book and a 1-comp book are equally
likely. Books whose in-window rows ALL have an empty canonical (13.6% of `market_sales` rows) cannot
enter the universe at all. Step 1's 5 density-selected control books are now explicitly excluded
from the sample (measured overlap was 0, but nothing enforced it).

**Three N=200 runs launched at session close** (seeds `''`, `s2`, `s3`; repeat seeds `--skip-3b`
since 3B is not sampled). Output persisted to **`scripts/cp1_output/cp1_N200_seed-*.txt`**, each
carrying an in-transaction SNAPSHOT stamp (per-table row counts + max sale date) in its header.
⚠️ Two output-capture failures on 2026-08-04 — Python block-buffering to a file, then a pipe to
`tail` holding until EOF — cost two runs. **Terminal scrollback is not storage.** Confirm the files
exist and are non-empty before treating any run as complete.

⚠️ Three earlier runs died on `NameError: name 'control' is not defined` — a patch to `main()` that
silently did not land, the same write-failure class that mangled five f-strings. **Heredoc patching
of this file is unreliable; use the editor.** Fixed and verified end-to-end before relaunch.

⚠️ **A SECOND crash, caught only because the output was persisted to disk** — which is the argument
for the persistence rule, not a footnote to it. The first N=200 seed-default run reached step 3B
after ~77 minutes and died on
`TypeError: '<' not supported between instances of 'NoneType' and 'str'`: `issue` is NULLABLE in
`lookup_demand`, `grade_submissions`, `search_cache` and `collections`, and a bare `sorted()` on
`(title, issue)` tuples compares `None` against `str`. Fixed with `_sort_pairs()`, which coerces
`None` to `''` **for ordering only** — the `None` is preserved in the tuple because `fetch_comps`
correctly treats a `None` issue as "no issue filter". `--skip-3b` runs never touch that code path,
so s2/s3 were unaffected.

**RUN STATE AT SESSION CLOSE — verify before reading anything:**
- `cp1_N200_seed-default.txt` — first attempt CRASHED in 3B (step 3A output is valid and present;
  steps 4 and 5 never ran). **A corrected full rerun is QUEUED** and starts automatically once
  s2/s3 finish; it overwrites this file. Completion marker: `scripts/cp1_output/_RERUN_DONE`.
- `cp1_N200_seed-s2.txt`, `cp1_N200_seed-s3.txt` — `--skip-3b`, running/queued, unaffected by the
  bug. Chain marker: `scripts/cp1_output/_ALLDONE`.
- ⚠️ **Check for `RUN COMPLETE` in each file before trusting its tables.** Two of the five runs
  attempted tonight produced partial output that looked plausible until the tail was read.

**Verification agent (`feature-dev:code-reviewer`) found 3 real defects, all fixed:** the variant
exclusion was SQL-only so the toggle was a **no-op for every graded cell** (production excludes in
Python at `:369-371`); `percentile_trim` was imported and advertised but never called, so Step 4 ran
untrimmed; and a latent `ZeroDivisionError`. A fourth, found by measurement rather than review:
Step 4 issued **one SQL round trip per comp** to compute age.

### 🔒 2026-08-05 SESSION CLOSE — corrections, ordering, and one uncommitted file

**SHIPPED:** CP-1 Unit 1 (verdict gate → `interpolated` + `exact_thin` + `blended`) · Unit 3 (min-n
K=2 + `low_support` tier) · **L-SW-2026-020** written (20 lessons) · this file updated.

⚠️ **UNCOMMITTED, ON DISK:** `scripts/corpus_snapshot.py` — end-of-day corpus snapshot, `--days` /
`--json`. Same status as `coverage_assessment.py` and `stripe_preflight.py`. **Decide next session
whether it lands; Mike leans yes** (it is the seed of the admin corpus dashboard).

**⚰️ THREE CORRECTIONS — all supersede earlier reasoning in this file. Do not resurrect the dead
versions.**

1. ⚰️ **DEAD: "Whatnot / `market_sales` has been dark since 2026-07-01."**
   REPLACED BY: **10 rows arrived 2026-08-02 → 2026-08-05** (1 · 8 · 1). It is **trickling — neither
   dark nor active.** REASON: measured directly from `created_at` by day.
   **The open question is no longer "is the extension running." It is "why 10 rows against eBay's
   36,961 the same day."**

2. ⚰️ **DEAD: treating a §2A key as done when it clears §1's stopping rule.**
   REPLACED BY: **§1's rule is BOOK-level (≥10 comps / ≥5 graded); the product prices at GRADE
   level.** All nine §2A keys cleared 2026-08-05 — but Batman #227's 54 graded comps spread across a
   20-grade ladder average **under 3 per bucket**, and **67.9% of populated graded cells still hold
   exactly one comp**. **"Cleared" means off the estimate fallback, NOT returning confident
   verdicts.** ⚠️ **This needs FIXING IN `EBAY_CAPTURE_SCHEDULE.docx` §1, not merely noting** —
   the stopping rule as written retires keys that still cannot produce a verdict at most grades.

3. ⚰️ **DEAD: "scarce keys accrue ~3 comps/year."** REPLACED BY: **nothing — the figure was
   invented, never measured.** Batman #227 reached 123 comps in days. **Disregard it wherever it
   influenced reasoning** (it was used to argue starved keys would stay starved; they did not).

**🔜 NEXT SESSION, IN THIS ORDER (Mike, 2026-08-05):**
1. **W2 claims sweep — AUDIT ONLY, no fix proposed until the surfaces are known.** The code contains
   **no recency weighting of any kind** (verified: no decay, no half-life, hard cutoff only), yet it
   is claimed as an edge over CovrPrice and GoCollect. **Discriminate by SURFACE — the exposure is
   completely different per surface:** `COMPETITORS.txt` is internal and nobody outside sees it ·
   user-facing copy and marketing are real exposure · **a patent or whitepaper filing is materially
   worse and would warrant counsel.** Report where it appears before proposing anything.
2. **Unit 2 instrumentation** — `is_internal` (flags 11 of 1,276 rows; ~600 founder lookups read as
   cold traffic) and `fmv_method` pollution (665 rows carry `/api/sales/fmv` tier labels).
   **Degrades daily** and blocks §4's promotion loop from ever running honestly. Cannot retro-fix
   existing rows — §4 must start from a cutoff date.
3. **Field-name hygiene bundle** — rename the `interpolated` tier (95.6% of it is one-sided
   extrapolation), fix `nearby_thin_comps`, **and extract the tiering logic into an importable
   function.** Rationale: `classify()` in `corpus_snapshot.py` now mirrors shipped logic by hand,
   the interpolation arithmetic is inline in the route, and the admin dashboard would be a **third**
   copy. **Cost is lowest right now** — do it before the third copy exists.
4. **Corpus stall alert** — small, and has already cost twice.

**🅿️ PARKED — DO NOT REOPEN WITHOUT NEW DATA: the robustness/bounds check.** Corpus growth is
shrinking its addressable base by itself — buckets that were empty two days ago now return `exact`
(spider man #1 @9.8 went from a 2,627%-error interpolation to `exact` $150 on 522 comps within the
session). **Re-measure in a few weeks and see what is left before designing anything.**

---

### ✅ 2026-08-05 — CP-1 GATE: UNITS 1 AND 3 SHIPPED AND VERIFIED IN PRODUCTION

**All corpus figures below carry a snapshot stamp. The corpus grows ~20k rows/day — a mismatch
against these numbers is growth, not an error.**

**UNIT 1 — the ROI verdict now requires real same-grade comps.** `verdict_reliable` previously gated
only the FABRICATION tier. Measured against the capture schedule's own key lists that hedged **0.0%
of the 9 §2A starved keys and 0.0% of the 15 §2C blue-chip anchors** — none of the 24 books cold
traffic will type. Now also false for `interpolated`, `exact_thin` **and `blended`**.
⚠️ `blended` was nearly missed: B-vs-C measured identical only because `exact_thin` is essentially
EMPTY on the keys that matter — a thin exact bucket becomes `blended` whenever neighbouring grades
exist, which on flagship keys they always do. "The very_low extension is free" was free because it
was **vacuous**. blended is 21.7% of §2A and 15.7% of §2C. New `verdict_basis` field
(`fabricated|low_support|interpolated|blended|thin|supported`) drives tier-specific copy; **FMV
numbers still render in every tier**, only the slab/no-slab recommendation is withheld.

**UNIT 3 — minimum source support (K=2) on interpolation.** A grade bucket must hold ≥2 sales before
it can anchor an interpolation; thinner buckets are skipped and the next populated bucket is used.
Plus the `low_support` tier so ~72% of cells pushed out of `interpolated` are not described by the
`fabricated` string, which would be false for them.

**⚠️ THE ROOT DEFECT (this is the finding to carry forward): interpolation weighted by grade distance
ONLY, never by evidence.** Worked case — **Spider-Man #1 @ 9.8**, true median **$110.00 from 315
same-grade comps** (snapshot 2026-08-05 17:12 UTC, ebay_sales 185,278): the 9.9 bucket held exactly
**one** genuine $4,449.99 sale, and interpolating 9.6 ($99, n=74) → 9.9 at weight 0.667 returned
**$2,999.66 — a 2,627% error. One sale outvoted 315.** With K=2 the 9.9 bucket is skipped and the
result is **$102.95 (6.4% error)**.

**THE INTERPOLATED SURFACE, measured (snapshot 2026-08-05 22:58 UTC, ebay_sales 200,335):**
75,356 interpolated cells, of which **95.6% are one-sided ±20%/grade extrapolation — not
interpolation between two points at all** — and **90.0% anchor on a bucket holding a SINGLE sale**
(96.9% ≤2, only 0.9% ≥5). **69.5% sit on the 2,592 single-graded-comp keys**, which the capture
burst grows with every new title captured at depth 1.

**Tier movement K=1→K=2:** 60,301 cells `interpolated`→`low_support` (72.5%), 1,247
`blended`→`exact_thin`, **0 cells moved from a hedged state to an unhedged one.** `exact` (≥3
same-grade comps) is structurally untouched.

⚠️ **This is a TAIL fix, not a central-tendency fix** — backtest median error moves only 19.3% →
18.1%, coverage lost 7.3%. The backtest modelled **fallthrough-to-next-populated-bucket**, which is
what shipped (verified line-by-line against the shipped selector), so those numbers do describe
production.

**POST-DEPLOY VERIFICATION, live prod (snapshot 2026-08-05 23:27 UTC, ebay_sales 200,335):**
| case | result |
|---|---|
| `spider man #1 @9.8` | `exact` $150.00, 522 same-grade comps — **the pathological case is no longer reproducible**: the 9.8 bucket filled in, so it never reaches interpolation. Fix effect unobservable here. |
| `ASM #41 @9.4` | `interpolated`, hedged, **graded_fmv $3,328 → $2,052.01** — min-n changed which buckets anchor it. **This is the working demonstration case.** |
| `ASM #300 @9.8` | `exact`/`supported`, verdict shows — not silent everywhere |
| `100 Page Super Spectacular #4 @10.0` | `low_support`, `nearby_thin_comps=1` — singular renders correctly |
| nonexistent book | `fabricated`, `nearby_thin_comps=0` — cannot render "0 recent sales" |

**⚠️ THE n≥10 INVERSION — CONTAMINATION FALSIFIED, CURVE STEEPNESS STANDS.** Error falls with source
support (n=1: 27.9% median · n=5-9: 10.2%) then **jumps back at n≥10 to 29.0%**. Excluding suspected
Platinum/UPC Gold/Silver edition rows (260 rows, 1.29%) leaves it at 29.0% / p90 64.8%, and only 3
cells left the band — variants are not concentrated there. **A future confidence bound needs GRADE
POSITION as a term; source-bucket n alone is unsound above 9.** (Caveat: the variant regex catches
1.29% of rows; severe under-detection could still hide an effect.)

**⚠️ CGC COST COUPLING — recorded in code above `get_cgc_grading_cost()`, cross-reference it.**
Above $1,000 the fee is 4% of FMV, so bounding FMV downward also bounds cost downward and **NARROWS**
the ROI gap — a naive pessimistic bound produces a flattered worst case, the opposite of a safety
bound. **Any bound must move both terms together.**

**🅿️ ROBUSTNESS CHECK — PARKED with a re-measure condition.** Recovery measured at 33.1% (all
interpolated) / 51.6% (§2A) / 36.0% (§2C) **on a population that INCLUDES the n=1 anchors Unit 3 has
now removed.** Re-measure post-min-n before deciding: tighter bounds, much smaller addressable base.
Also: 37.7% of interpolated cells have NO raw comps and 17.6% have 1-2, so on **55.2% both sides of
the ROI are weak** — a bound must cover the raw side too.

**BACKLOG, logged not fixed:** `is_variant` misses Platinum/UPC Gold/Silver editions (fold into the
Absolute Batman variant-subtyping work) · the `interpolated` tier is **misnamed** — 95.6% of it is
one-sided extrapolation with a 25% floor · `nearby_thin_comps` sums ALL nearby buckets, so it reads
484 on a 522-comp cell (correct where consumed, misnamed elsewhere — **[[L-SW-2026-020]]** instance 4).

---

### 🔥 2026-08-05 — CP-1 AUDIT: A POPULATION-LEVEL MATCHER DEFECT

⏱️ **EVERY FIGURE BELOW IS A POINT-IN-TIME SNAPSHOT — DIVERGENCE IS GROWTH, NOT CONTRADICTION.**
Since the ingestion-rate fix the corpus grows **~20k rows/day**, and it is bursty: at
2026-08-05 16:58 UTC, `ebay_sales` = **182,674** with **19,300 rows created in 24h and 14,269 of
those in the single preceding hour**. `market_sales` is static at 9,972, so the source split moves
on its own: **94.2%/5.8% (early 2026-08-05) → 94.8%/5.2% (16:58 UTC same day)**. Within this one
session `ebay_sales` read 163,374 → 168,405 → 182,674 and `lookup_demand` 1,266 → 1,268 → 1,271.
**Do not treat a mismatch against these numbers as an error to investigate.** All four audit scripts
now emit a `[SNAPSHOT AT START]` line (row counts, source split, `max(sale_date)`, timestamp);
compare a figure only against the stamp in its own output file. The 180-day window also slides, so
even a re-run at the same instant next week covers a different span.

⚠️ **THIS STARTED AS AN ASM #41 DIAGNOSTIC AND BECAME SOMETHING LARGER.** The question was why one
book valued at ~$47. The answer is that `title_matching.qualifier_title_clause()`'s **fallback
branch** contaminates comp pools across the corpus. ASM #41 itself is NOT explained by it and remains
open — see the bottom of this section. **Nothing shipped, nothing committed, no matcher change, no
production change.** All output persisted in `scripts/cp1_output/`.

**Five read-only runs, all RUN COMPLETE:**

| File | What it did |
|---|---|
| `cp1_N200_seed-{default,s2,s3}.txt` | Step 3A uniform distribution, 3 seeds, N=200 + Step 5 |
| `cp1_STEP4_stratified.txt` | Step 4 stratified, 518 cells, ~75/bucket |
| `cp1_fallback_audit.txt` | 400-pair branch-split cross-check |
| `cp1_nesting_audit.txt` | **complete** audit of the nesting population |

**STEP 4 (stratified) — the estimator-stability curve.** Buckets now hold 51–117 cells, not 2–20.
`CI%med` falls monotonically 113.8 → 80.2 → 65.6 → 38.2. Leave-one-out swing falls 21.8 → 21.6 →
**12.3 → 4.7** → 5.3 → 1.5, breaking hardest between 3-4 and 8-12. `IQR%med` deliberately does NOT
fall (88/98/85/96/94) — dispersion is a property of the book, not the sample size, which is the
check that the strata aren't selecting easy books. `noCI` confirms the **n=7 floor** empirically:
buckets 1/2/3-4 are 100% no-CI; bucket 5-7 is 46 of 64. Median invariance re-confirmed on 518 real
cells, 0 differences.
⚠️ **Reassignment rate 49.8%** (258/518): half of sampled cells had a production comp count
different from their canonical-grouping strata count. Built as a fidelity disclosure; at that
magnitude it is an independent measure of fallback contribution, reached from a different direction.
⚠️ **3 titles timed out at 120s** on unfiltered scans, by name: `Sold Here Retailer Promo Pos`,
`Something is Killing the Chi`, `Spider-Man Characters Lot`. All `issue = None`. Same artifact family
as the junk canonicals below — the pathological-title list and the artifact tier may be one list.

**NESTING AUDIT — complete over the population, not sampled.** Substring-membership IS the fallback's
match predicate, so client-side substring enumeration reproduces branch B exactly. One bulk fetch
(96,921 rows, ~12 MB), matching computed in 6s.
- **2,667 nested targets of 15,957 in-window titles (16.7%)** under production filters.
  (An unfiltered earlier count gave 3,855 / 24,973 / 15.4% — both correct for their scope; the
  filtered one is the right denominator for production impact.)

| target length | cells | added rows | **different canonical** | med Δ | p90 Δ | max Δ |
|---|---|---|---|---|---|---|
| **<6 (artifact)** | 25,458 | 194,762 | **99.8%** | 38.0% | 399.5% | 48,589% |
| 6–11 | 21,278 | 121,004 | **99.6%** | 27.0% | 210.3% | 26,400% |
| 12–19 | 8,631 | 26,487 | **99.2%** | 16.7% | 118.9% | 12,463% |
| 20+ | 3,730 | 11,039 | **99.8%** | 15.4% | 98.0% | 6,367% |

- **The different-book share is ~99% in EVERY tier.** Across ~353,000 added rows the fallback is
  essentially never recovering the same book. It was justified as a rescue for unclean canonicals;
  it is the Batch 8 mechanism intact in branch B.
- **Monotonicity holds and does not rescue the design.** Median delta falls with target length, so a
  minimum-length rule has a measurable shape — but the 20+ tier still moves the median 15.4% (p90
  98%) at a 99.8% different-book rate.
- Median shift over 5,321 comparable cells: only **10.6% unchanged**, **52.4% move >20%**, 14.5%
  move >100%.
- **Artifact tier is live, not a data-quality footnote:** `'an'` (two characters) matches **87,372
  rows**; `'comics'` matches **37,175**. Both exceeded the 20k collection cap; true counts recorded,
  medians computed on the first 20k, cap disclosed in the output.

**⚠️ THE NESTING PROPERTY CORRELATES WITH BEING A FLAGSHIP.** Bare franchise names are substrings of
their own longer titles, so the most valuable and most-queried books are structurally the most
exposed:

```
48589%  'x men'              #181  raw   $2.67 → $1,300.00   n 1→7
26400%  'spider man'         #122  9.2   $3.00 → $  795.00   n 1→3
12463%  'amazing spider man' #22   raw   $9.99 → $1,254.99   n 1→2
 8317%  'silver surfer'      #48   raw   $6.00 → $  505.00   n 5→70
 8296%  'wolverine'          #94   raw   $4.64 → $  390.00   n 4→25
 5321%  'batman'             #400  raw   $2.49 → $  135.00   n 1→18
 4407%  'jsa'                #1    raw   $5.99 → $  269.99   n 1→29
```

**COST SIDE — removing the fallback costs very little where cells had real comps:**

| transition | cells | share |
|---|---|---|
| **cell exists ONLY via fallback** | 53,776 | **91.0%** |
| no threshold change | 2,450 | 4.1% |
| drops below 3 | 2,107 | 3.6% |
| drops below 5 | 483 | 0.8% |
| drops below the n=7 CI floor | 281 | 0.5% |

⚠️ **TWO LIMITATIONS — do not let conclusions outrun them.**
1. **MAGNITUDE ONLY, NOT DIRECTION.** Everything above is `|median shift|`. Every worst-case example
   happens to move UPWARD, which would mean inflated FMV → inflated ROI → users told to grade books
   that are not worth grading (straight into D4). **That direction is NOT measured.** One column,
   same data, no new fetch.
2. **CONTAMINATION, NOT CORRECTNESS.** The audit establishes that added rows carry a different
   canonical 99% of the time. It does NOT establish which median is closer to truth. For bare
   flagship canonicals the EXACT rows may themselves be truncation artifacts, with the fallback
   pulling in the legitimately-titled rows — which would invert the reading. Untested.

**⚰️ ASM #41 IS NOT CLOSED BY THIS.** The fallback on `'amazing spider man'` INFLATES, so it is
probably not the deflation mechanism behind the ~$47 figure. That implies a **separate defect on
thin-data keys**. Do not let it be closed out because a larger finding landed in the same
investigation.

**Scripts (all untracked, uncommitted):** `scripts/cp1_confidence_measure.py`,
`scripts/cp1_fallback_audit.py`, `scripts/cp1_nesting_audit.py`, outputs in `scripts/cp1_output/`.

### 🔜 ON RESUME — priority order (Mike, 2026-08-04)

**0. CP-1 measurement — read the tables first.** In order: Step 3A three-seed spread · Step 4 bucket
table (`CI%med` / `CIraw%` / `narrow` / `noCI`) · Step 5 sensitivity · the narrow<0 count. Then:
**D2 threshold setting** (n=7 CI floor is the leading Low-boundary candidate), and **D4 (ROI verdict
behaviour at Low)**, which is decidable independently and may go first. No production changes have
been made; everything so far is measurement.


1. **Cross-project canon version control.** Scope accepted in shape. ⚠️ **TWO DECISIONS ARE MIKE'S
   AND UNMADE:** (a) whether the canon moves out of the tool-managed `.claude` tree entirely;
   (b) whether to go straight to option C or stage A → B → C. **`.gitignore` with `~$*` goes in the
   INITIAL commit, not after** — once the Office owner file is in history it is permanent.
   ⛔ **DO NOT INITIALIZE ANYTHING UNTIL MIKE DECIDES.**
2. **Phase 2** — scoped and specced below: view extension with the `created_at` **UTC cast recorded
   as chosen rather than inherited**, `grade`'s coverage asymmetry stated **in the `DB_SCHEMA` entry
   itself**, `source_id` → **`listing_id`**, and the `market_sales` revoke, all as ONE unit with the
   ordering **inverted from Phase 1** (deploy the prompt change first, revoke after).
3. **`.claude/worktrees` untrack** — commands prepared below; behind nothing.

**Everything else is in Todoist under Slab Worthy:** `git gc`, the sync-check script, Phase 3, the
polysemy audit, `graded_comics` identification, R2 close-out, `R2_CUTOVER_RUNBOOK.md` date drift.

⚠️ **Five tracked files are dirty and are NOT from this session's work** — `.gitignore`, `TODO.md`,
`docs/EBAY_CAPTURE_SCHEDULE.docx`, `scripts/slabguard_crosscamera_test.py`,
`tests/SlabGuardTests/TP_RESHOOT_PROTOCOL.md`. Pre-existing. Do not sweep them into a future commit
assuming they belong to the NLQ work.

⚠️ **This session-close block is uncommitted at time of writing.** `WHERE_WE_LEFT_OFF.md` went into
`3a9892f`; everything added after it is dirty. Verify with `git status` before assuming it is in
history.

---

### ✅ CLOSURE 1 — `nlq_readonly` role, shipped and verified

⚠️ Supersedes **both** earlier status blocks in this entry: "UNCOMMITTED AND UNDEPLOYED, four files
dirty" and "code PUSHED / infra NOT DONE." Both are DEAD. This table is current.

| Step | State |
|---|---|
| Commits | ✅ `8709518` (feature) + `5f2deb5` (corrections) |
| Push | ✅ `origin/main` = `5f2deb5`. **Both commits are on the remote and are no longer amendable** — the duplicate commit message across the two, and `8709518`'s stale "87.8%" figure, are permanent history. |
| `nlq_readonly` role + grants | ✅ **LIVE.** Corroborated independently from the catalog: `SELECT` on exactly the 9 tables from step 3, and **`users` absent from the table-level list** — the load-bearing condition for the `password_hash` exclusion. |
| `DATABASE_URL_NLQ` on Render | ✅ set |
| Render deploy | ✅ `5f2deb5` deployed |
| Post-deploy artifact | ✅ NLQ run returned **8 rows**; `admin_nlq_history` **row 43** landed with `result_count=8`, `execution_time_ms=3312`. **The history split works** — the query ran on the read-only role and the audit row was written on the read-write pool. |

⚠️ **The first production NLQ returned 8 rows, all `source = 'whatnot'`, from `market_sales` alone.**
That is the corpus hole producing a visibly incomplete answer in production, unprompted — and it is
the argument for Phase 1 following immediately.

### ✅ CLOSURE 2 — `all_comic_sales` filter fixed

Applied on the admin connection as `collectioncalc_db_user` (view owner). Verified from the catalog
after the fact, not by eye:

| Check | Result |
|---|---|
| Second leg emits `market_sales.source` | ✅ present |
| Literal `'whatnot'::text` | ✅ **gone** |
| `WHERE` clause | ✅ **gone** |
| First leg `'ebay'::text` | ✅ retained — correct, `ebay_sales` has no `source` column |
| View row count | **173,346** |
| `ebay_sales` + `market_sales` | 163,374 + 9,972 = **173,346**, delta **0** |
| Split by source | `ebay` 163,374 · `whatnot` 9,972 |
| ACL after vs before | ✅ **identical, 9 rows** — owner `collectioncalc_db_user` (arwdDxtm) + `do_readonly=r`. `CREATE OR REPLACE` kept the relation OID and `relacl`; nothing gained, nothing lost. |

- **Rollback not needed.** The count criterion held exactly, so the filter was provably doing nothing.
- ⚠️ **The row counts are NOT the evidence.** While `market_sales` stays 100% Whatnot, the output is
  byte-identical whether `source` is a literal or a column reference. **The `pg_get_viewdef` text is
  the only thing that proves the change took**; the counts only prove nothing broke.
- **`datadog` needed nothing** — verified it holds **no object grants at all** in schema `public`, so
  it cannot read the view through a grant. Consistent with the Datadog PG integration reading
  `pg_stat_*` via role membership. The "unknown consumer" flag is CLOSED.
- **No monitor was needed after all.** The originally-proposed loud check (non-Whatnot rows in
  `market_sales`) exists to detect a silent drop. Deriving the label instead of asserting it removes
  the failure mode rather than observing it.

### 🔍 THE LITERAL-VS-COLUMN FINDING — caught in implementation, missed in scoping

**The approved scope was "remove the `WHERE` clause only." That scope was incomplete and would have
shipped a new bug while closing an old one.**

The second leg did not read `market_sales.source`. It emitted a **hardcoded literal**:

```sql
SELECT 'whatnot'::text AS source,  -- literal, not the column
   ... FROM market_sales
 WHERE market_sales.source = 'whatnot'::text;
```

The `WHERE` and the literal encoded the *same premise* in two places. Removing only the `WHERE` would
have admitted a future `mercari` row **labelled `source = 'whatnot'`** — converting a silent **drop**
into a silent **mislabel**, which is strictly worse: a dropped row shrinks a comp pool and is
recoverable; a mislabelled row poisons one and compounds (same asymmetry as L-SW-2026-009).

Found only when the full view definition was read to write the replacement statement — the scoping
pass had worked from the `WHERE` clause alone. Recorded as **[[L-SW-2026-019]]**.

⚠️ **`migrations/nlq_readonly_role.sql` step 2 was wrong in `8709518`** — it said `DATABASE collectioncalc`.
The database is **`collectioncalc_db`**. Fixed in `5f2deb5`. Anyone running the version from `8709518`
will error at step 2.

### Why

The two existing guards do not hold. The keyword denylist (`insert|update|delete|drop|truncate|alter|
grant|revoke`) has **no `create` entry**, and psycopg2 executes multi-statement strings — so
`SELECT 1; CREATE TABLE x AS SELECT * FROM users` passed both the `SELECT`-prefix check and the
denylist, and ran on the read-write role. The denylist is retained as the first layer; the role is the
layer that holds when it doesn't.

### 🔑 MANUAL PREREQUISITES — NOT REPRODUCIBLE FROM THIS REPO

Neither exists in version control. A fresh clone + deploy does **not** produce them, and the code
**fails closed** without them (`/api/admin/nlq` returns *"NLQ read-only role not configured"*; the rest
of the app is unaffected).

1. **The `nlq_readonly` Postgres role and its grants** — created by hand in DBeaver. Shape:
   - `CREATE ROLE nlq_readonly WITH LOGIN PASSWORD '<generated by Mike, never in chat or repo>'`
   - `GRANT CONNECT` on the database, `GRANT USAGE` on schema `public`
   - Table-level `GRANT SELECT` on **9** of the 10 `DB_SCHEMA` tables: `beta_codes`, `request_logs`,
     `api_usage`, `market_sales`, `collections`, `search_cache`, `comic_registry`,
     `sighting_reports`, `blocked_reporters`
   - **`users` is column-level only, excluding `password_hash`**, granted via a `DO` block that reads
     `information_schema.columns` — never a typed list. Verified against the live catalog 2026-08-04:
     `users` has **32** columns; `DB_SCHEMA` lists 11 and `DATABASE_PRODUCTION.md` lists 26. Both
     sources lag the database.
   - ⚠️ **`users` must NEVER be added to the table-level `GRANT SELECT` list.** Table and column
     privileges are **additive**: a table-level grant is not diminished by the column-level one, so
     adding `users` back there silently kills the `password_hash` exclusion with no error and no
     visible change. There is no column-level revoke that undoes it.
   - Role-level guards: `statement_timeout = '15s'`,
     `idle_in_transaction_session_timeout = '30s'`, `default_transaction_read_only = on`.
     Timeout lives on the **role**, not in code, so a code edit cannot drop it.
2. **`DATABASE_URL_NLQ` on the `collectioncalc-docker` Render service** — same host/db as
   `DATABASE_URL`, user `nlq_readonly`, `?sslmode=require`. Documented in
   `docs/technical/ARCHITECTURE.txt`. Per L-SW-2026-004 the env change needs the redeploy **and** a
   fresh shell before any check reads it.

✅ **RESOLVED — the grants SQL is committed as `migrations/nlq_readonly_role.sql`** (Mike, 2026-08-04).
Supersedes "the grants SQL exists only in the session transcript / decision pending," written earlier
in this same entry. The file carries a **placeholder** password — generate a real one at run time and
never commit it. Nothing runs the file automatically: it is not wired into any migration runner and
step 1 is not idempotent (it errors if the role already exists). The role itself still does not live
in version control — only the recipe does.

### What changed (5 files — NOT shipped)

| File | Change |
|---|---|
| `db.py` | New `get_db_readonly()`: unpooled (a second pool would add `DB_POOL_MAX x workers` against `max_connections=103` for a few admin queries/day), `RealDictCursor`, `set_session(readonly=True)` as an independent second guard. **Fails closed** — raises if `DATABASE_URL_NLQ` is unset rather than falling back to `DATABASE_URL`. |
| `admin.py` | `get_readonly_connection()` delegating to it; `_log_nlq_history()` (history INSERT moved to the read-write pool, never raises); execute-block now uses the read-only connection, closes it, then logs. |
| `admin.py` | Known-limitation comment above `DB_SCHEMA` — see below. The prompt string itself is **byte-identical** (3,609 chars); the comment sits outside it. |
| `docs/technical/ARCHITECTURE.txt` | `DATABASE_URL_NLQ` row in the Core env-var table. |
| `migrations/nlq_readonly_role.sql` | **NEW.** The role + grants recipe, hand-run in DBeaver. Placeholder password. Carries the `users`-exclusion warning and the verification block inline. |

⚠️ **`natural_language_query`'s prompt construction and response extraction were deliberately not
touched** (Mike's constraint). The model still returns raw SQL text that is string-munged for markdown
fences — that shape is unchanged and was explicitly **not** re-scoped.

### 📋 KNOWN LIMITATION — LOGGED, DELIBERATELY NOT FIXED

`DB_SCHEMA` is not the database, in two ways, both now recorded in a comment at `admin.py`:

1. **The valuation corpus is two tables and only one is described.** Live counts 2026-08-04:
   `ebay_sales` **163,374 rows (94.2%)** is absent; `market_sales` **9,972 (5.8%)** is 100% Whatnot.
   NLQ questions about sales volume, price history or coverage answer from **under 6%** of the corpus
   **and read as complete**. `ebay_sales` is also **not granted** to `nlq_readonly`, so prompt and
   grants stay consistent — the model cannot query what it cannot see.
   ⚠️ **The 71,652-row / 87.8% figures in L-SW-2026-014 are STALE** (measured 2026-08-01); `ebay_sales`
   has more than doubled since. The lesson's *mechanism* is unchanged and still correct — only its
   cited counts are out of date. Not edited here; flagged for Mike.
   ⚠️ **A view `all_comic_sales` already UNIONs both tables** — 15 columns, 173,346 rows, `source`
   discriminator ('ebay' / Whatnot). Described nowhere, granted to nobody. Found 2026-08-04.
2. **Scope and column lists both lag the live database.** Verified read-only against the live catalog
   2026-08-04: `public` holds **34 base tables + 5 views, 472 columns**. `DB_SCHEMA` describes **10
   tables** — so NLQ is blind to 24 of them (19 excluding the five `_bak_*_20260615` backup tables
   left over from the June R2 cutover). Per-table: `users` 32 columns live vs 11 described,
   `market_sales` 34 vs 16, `collections` 26 vs 7. **The five views are described nowhere and are
   not granted** — consistent, but worth knowing before anyone widens the prompt.

Closing either gap is a prompt change and must be paired with a grants change in the same unit.
**Widening one without the other is the failure mode.**

### ⚠️ Known behavioural cost of the column-level grant

**`SELECT *` on `users` now fails for this role** — the expansion includes `password_hash`, which is
denied. The model writes `SELECT *` routinely, so some user-related NLQ questions will return a
permission error instead of rows. Steering the model off `SELECT *` is a prompt change; not done.
**Do not read the first such failure as a broken deploy.**

### Verification order (none of it run yet)

1. Grants in DBeaver, then the positive-control block: `SELECT id, email, plan FROM users LIMIT 3`
   and `SELECT count(*) FROM market_sales` must **succeed** (proving the role can return a hit,
   L-2026-024) before the refusals count as evidence — `SELECT password_hash FROM users`,
   `SELECT * FROM users`, an `INSERT`, a `CREATE TABLE AS`, `SELECT count(*) FROM ebay_sales`, and
   `SELECT count(*) FROM admin_nlq_history` must **all** error.
2. Confirm grants landed: `information_schema.column_privileges` for `nlq_readonly` on `users` must
   list the columns and **must not contain `password_hash`**; `pg_roles.rolconfig` must show all
   three role-level settings.
3. `DATABASE_URL_NLQ` on Render → redeploy → **Render Events shows the pushed commit hash**
   (never `/health` `version` — decoy, L-SW-2026-017). No Cloudflare purge; nothing frontend changed.
4. Post-deploy artifact: run one NLQ from the admin panel, then confirm the audit row landed —
   `SELECT id, admin_id, result_count FROM admin_nlq_history ORDER BY id DESC LIMIT 3`. Query returns
   but no row = the split's write half is broken; check Render logs for `[NLQ] history logging failed`.

### 📐 FOLLOW-UP 1 — DB_SCHEMA drift reconciliation: SCOPED AND DECIDED, NOT STARTED

Decisions (Mike, 2026-08-04). **The prompt has not been touched** — `DB_SCHEMA` is still 3,609 chars.

- **Describe 16 objects:** `all_comic_sales` (view) · `request_logs` · `users` · `collections` ·
  `comic_registry` · `api_usage` · `lookup_demand` · `waitlist` · `grade_submissions` ·
  `user_feedback` · `content_incidents` · `sighting_reports` · `blocked_reporters` · `match_reports`
  · plus views `signature_review_queue`, `signature_confusion_summary`.
- ⚰️ **`beta_codes` RETIRED from the prompt** — beta gating died 2026-07-29; describing a dead
  subsystem is drift by definition. Supersedes its Tier A placement earlier in this scope.
- **Tier B resolved to the two signature VIEWS only.** The three signature base tables stay out.
- **Tier C excluded, with reasons on record:** `password_resets` + `ebay_tokens` (credential
  material) · `search_cache` + `dependency_alerts` (machinery) · `slabguard_*` ×3 (parked
  subsystem) · `graded_comics` (**unidentified** — 12 cols, 1 row, in no doc; flagged not guessed) ·
  raw `market_sales`/`ebay_sales` (superseded by the view) · **`admin_nlq_history` — NLQ must not
  query its own audit log.**
- **Phasing: 1 → 2 → sync-check → 3.** Build the invariant before adding the batch that would
  violate it. The invariant: *objects described in `DB_SCHEMA` == objects granted in
  `nlq_readonly_role.sql`*, minus an explicit `DESCRIBED_BUT_DENIED` list with a reason per entry,
  enforced by a script that exits non-zero on drift (the observable artifact, L-SW-2026-017).

⚠️ **CORRECTION — the selection criterion was stated wrong and Mike caught it.** The first draft
excluded objects on **row count** (naming `match_reports`, `signature_matches`) while keeping
0-row `sighting_reports`/`blocked_reporters` as "semantically load-bearing" — self-contradictory.
**The real rule: an object belongs if a plausible admin question maps onto it and the model needs its
structure to answer.** Row count is evidence about whether a subsystem is *in use*, never a criterion.
An empty table representing a reachable domain event answers "how many sightings?" with a correct `0`.
Consequence: **`match_reports` moved back IN.** Do not re-derive these lists from row counts.

### 📦 PHASE 2 UNIT — view extension + `market_sales` revoke, SHIP TOGETHER

Decided 2026-08-04: **revoking `market_sales` from `nlq_readonly` is the fix, not prompt steering.**
Reason (Mike): steering is probabilistic and the model picked `market_sales` unprompted on the first
production NLQ run. Revoking makes the wrong path fail loudly.

**⚠️ ORDERING — INVERSE OF PHASE 1. Execute in exactly this sequence:**

| # | Step | Where |
|---|---|---|
| 1 | Extend `all_comic_sales` (`CREATE OR REPLACE VIEW`, append columns) | DBeaver, admin |
| 2 | Remove `market_sales`'s entry from `DB_SCHEMA`; add the new view columns | `admin.py` |
| 3 | Remove `market_sales` from step 3 of the grants file | `migrations/nlq_readonly_role.sql` |
| 4 | Commit + push + **deploy the prompt change** | Render |
| 5 | **THEN** `REVOKE SELECT ON market_sales FROM nlq_readonly;` | DBeaver, admin |

**Phase 1 grants BEFORE deploy; Phase 2 revokes AFTER deploy.** Reversed, every sales question errors
during the window between revoke and deploy. The rule generalises: *widen access before the prompt
that uses it; narrow access after the prompt that stopped using it.*

**Verified column findings (live catalog, 2026-08-04) — what can and cannot join the view:**

| Column | eBay side | Verdict |
|---|---|---|
| `is_facsimile` | `is_facsimile` boolean, 163,374/163,374 | ✅ ADD — clean |
| `is_reprint` | `is_reprint` boolean, 163,374/163,374 | ✅ ADD — clean |
| `grade` | `grade` numeric, 22,923/163,374 (14.0%) | ✅ ADD — but Whatnot is 48.9% populated; unioned averages skew Whatnot. `DB_SCHEMA` must say so. |
| `created_at` | `created_at` **`timestamp` WITHOUT tz** vs Whatnot `timestamptz` | ✅ ADD — **DECIDED: cast the eBay leg explicitly to UTC** (`created_at AT TIME ZONE 'UTC'`), written into the view definition, never left to the session `TimeZone`. |
| `source_id` | **`ebay_item_id`** varchar, 163,374/163,374 | ✅ ADD — **DECIDED: the merged column is named `listing_id`**, not `source_id` (which reads as related to `source`). |

**⏱️ `created_at` TIMEZONE DECISION — Mike, 2026-08-04.** The eBay leg is `timestamp` without a zone;
the Whatnot leg is `timestamptz`. A bare union resolves to `timestamptz` by interpreting the eBay
values in whatever the session's `TimeZone` happens to be — **a timezone inherited rather than
chosen.** DECIDED: **UTC, cast explicitly in the view definition**, and **the `DB_SCHEMA` entry must
state that the eBay leg's timezone was chosen, not inherited**, so the next reader does not assume
the value carried a zone all along. This is cross-project **L-2026-023** at the schema layer — *a
timestamp is defined by its writer, not its name* — and the same asserted-vs-derived shape as
[[L-SW-2026-019]].

**📊 `grade` COVERAGE ASYMMETRY — must go in the `DB_SCHEMA` entry itself, not just these notes.**
eBay `grade` is populated in **22,923 / 163,374 (14.0%)**; Whatnot in **4,879 / 9,972 (48.9%)**. An
unqualified `AVG(grade)` over the view silently weights toward Whatnot by a factor of ~3.5 in
population rate. The prompt must say so **in the same steering voice** used to point sales questions
away from `market_sales` — a note in the session log does not reach the model.

**❌ CANNOT BE ADDED — no eBay equivalent, and no honest fill exists:**

- **`grade_source`** (Whatnot: `seller_verbal` 2,775 · `vision_cover` 1,558 · `slab_label` 228 ·
  `dom` 154 · NULL 5,257). Describes how the **capture pipeline** obtained the grade. eBay records no
  such concept. NULL-filling would assert "eBay grades have no source," which is **false** — they have
  one, it simply is not stored.
- **`slab_type`** (Whatnot: `raw` 4,294 · `CGC` 480 · `slabbed` 57 · `CBCS` 25 · NULL 5,094). eBay's
  nearest is `graded` boolean + `grading_company`. Synthesising
  `CASE WHEN graded THEN grading_company ELSE 'raw' END` **manufactures** a value to fill a column —
  the literal-vs-column problem run forwards. **Do not.**

⚠️ **THEREFORE THE REVOKE HAS A REAL, PERMANENT COST — AND IT IS ACCEPTED.**

**DECIDED (Mike, 2026-08-04): `grade_source` and `slab_type` are KNOWINGLY UNREACHABLE to NLQ. Do not
re-litigate this.** Both are ~49% populated and are **Whatnot capture-pipeline metadata, not comp
data** — `grade_source` records *how the grade was obtained* (`seller_verbal`, `vision_cover`,
`slab_label`, `dom`), a concept eBay does not record at all. They cannot join the view because any
fill would be fabricated, and they cannot survive the revoke because the revoke is the point.

The rejected alternative, on the record so it is not re-proposed: a **narrow column-level grant** on
`market_sales` limited to `id`/`source`/`grade_source`/`slab_type` would keep them reachable while
denying `price`/`sold_at`/`canonical_title`, making the table useless for corpus questions. **Rejected
— it costs more in grants-file complexity than it returns** (Mike). If these columns are ever needed
again, the answer is an admin query on the read-write connection, not a widening of `nlq_readonly`.

### 🏷️ LOGGED, NOT CHANGED — the 2026-08-01 copy verdict rests on a figure that has since moved

This entry's line ~728 records: *"12.2% across 1,603 titles is a meaningful share, so the copy stands
unchanged"* — the tombstone from the Slab Guard claims audit for `waitlist-confirmed.html`'s "we track
real sales data across eBay and Whatnot." **The split is now 94.2% / 5.8%, so that verdict now reads
as 5.8%,** and the phrasing question parked alongside it (whether "across eBay and Whatnot" implies
more parity than the real ratio) is sharper at 94/6 than it was at 88/12.

**Mike, 2026-08-04: LOG IT, DO NOT CHANGE IT.** This is a separate decision about public claims and is
not part of the NLQ work. The copy is unchanged and the original tombstone stands as written. Recorded
here only so the next claims sweep knows the underlying figure moved.

### 🚧 PHASE 1 BLOCKER — the `all_comic_sales` filter (Mike's call: blocker, not caveat)

The view's second leg carries `WHERE market_sales.source = 'whatnot'`. Proposing it as the fix for a
silent corpus hole while it installs a second one is not shippable. Measured 2026-08-04:

- `all_comic_sales` **173,346** = `ebay_sales` 163,374 + `market_sales` 9,972. **0 rows dropped.**
- `market_sales.source` is **100% `whatnot`** (9,972); `source IS DISTINCT FROM 'whatnot'` = 0.
- `source` is **NOT NULL with no column default** — the `'whatnot'` default is application-side
  (`sales_market.py:127`), as L-SW-2026-014 says. No NULL-drop edge case exists.
- **Verdict: vestigial today, landmine later.** Its only effect is prospective — the first
  non-Whatnot row ever written vanishes from the corpus with no error.
- **Recommended fix: `CREATE OR REPLACE VIEW` without the filter.** Column names/types/order
  unchanged, so grants survive. Verification is its own positive control: the row count must be
  **173,346 before and after**; any difference falsifies the premise.
- **Blast radius: zero in the repo** — `all_comic_sales` appears in no route, module, script or
  extension. Unknown: ad-hoc DBeaver use and whatever the `datadog` role queries.
- If the filter must instead STAY, Mike requires a **loud check, not a comment** — home would be
  `dependency_monitor.py`, asserting the non-Whatnot count is 0, reusing the dedup/stability-window
  machinery from L-SW-2026-013. Removal is smaller and deletes the need for it.
- **PENDING MIKE'S GO. Nothing executed.**

### 🗄️ `_bak_*_20260615` — RECOMMENDATION: KEEP. NOTHING DROPPED.

Five 2-column snapshots from the June 15 R2 cutover, 60,447 rows total. `R2_CUTOVER_RUNBOOK.md`
**Step 6 (line 284) already plans the exact `DROP TABLE`**, gated on "once confident (separate
session)." Verified read-only 2026-08-04: Step 5's condition holds — **0 residual `pub-*.r2.dev`
references** across all five columns, positive control fired (207 / 4,053 / 138,675 http URLs
present, so the probe can match). Snapshot ids are still **100% aligned** with live rows
(50,555/50,555 and 9,560/9,560), so rollback remains mechanically valid.

**But the drop is half a decision.** Step 6 pairs it with disabling the r2.dev public development
URL, and whether that URL is still enabled is a **Cloudflare fact not visible from the repo or DB**.
Both actions answer the same question. **Recommendation: one deliberate "R2 close-out" item that
disables r2.dev and drops the five tables together.** Holding costs nothing. They stay out of the
NLQ prompt and grants regardless.

⚠️ Drift found while reading that runbook: line 6-7 still states "soft launch is **August 4, 2026**",
which is DEAD per `CLAUDE.md` — the gate is first cold traffic, unscheduled. Not edited.

### 🧹 GIT HYGIENE — `.claude` untrack: SCOPED AND DECIDED, NOT RUN

`git status` was unusable (**8,461 lines**) because `61290bf` — *"Restore dollar sign favicon, remove
MASSE 8-ball from all pages"*, Mike Berry, **2026-03-19**, **8,451 files / 1,486,879 insertions** —
swept the whole agent directory in. 8,428 of its additions were `.claude/` paths; 15 were not. An
`add -A` in everything but name. `CLAUDE.md` itself was added by that same commit and carries the
"NEVER `git add -A` blindly" rule, apparently written the same morning.

- **8,429 files tracked under `.claude`: 8,424 `worktrees/` · 4 `skills/` · 1 `plans/`.**
- `.gitignore` lists `.claude/` **twice** (lines 69, 70). `git check-ignore -v` confirms it is live
  and matching — and irrelevant, because **gitignore does not affect already-tracked files.**
- `git worktree list` shows **18 live registered worktrees**, all present on disk. **`zen-wozniak`,
  the one that flooded the status, is NOT among them** — a genuine orphan, deleted from disk while
  still tracked.
- ⚠️ **Mike had already run `git rm -r --cached .claude` before asking for the scope** (his note,
  2026-08-04), which is why 8,429 deletions were found **staged** in the index. **That staging
  included the 4 `SKILL.md` files** — `deploy-tfo`, `health`, `lesson`, `stripe-test`, all referenced
  by `CLAUDE.md`. A plain `git commit` would have swept them out silently. **This is the finding that
  mattered; the rest is bookkeeping.**
- **DECIDED:** untrack `.claude/worktrees/` and `.claude/plans/purrfect-squishing-lake.md` only;
  **keep `.claude/skills/` tracked.**
- `.gitignore` must be restructured, not patched: `.claude/` with a trailing slash excludes the
  directory outright and git will not descend into it, so a `!.claude/skills/` negation underneath
  silently does nothing. Working form is `.claude/*` + `!.claude/skills/`, duplicate removed.
- `git rm -r --cached` is the right instrument and **removes nothing from disk**; it does not
  deregister or damage the 18 worktrees (registration lives in `.git/worktrees/`, not the index).
- **Repo-size impact: none.** Blobs stay in history; only a rewrite removes them, not recommended.
- **No tooling depends on those paths being tracked** — worktree isolation and skill loading both
  work off disk, not the index.
- **Interim clean status, verified (8,461 → 32 lines, positive control holds):**
  `git status --short -- ':(exclude).claude'`
- Commands prepared and handed to Mike. **BEHIND the role deploy. Nothing run.**

### 🧊 LOGGED, NOT RUN — `git gc`

`git count-objects -vH`: **5,144 loose objects, 119.66 MiB, `in-pack: 0`** — this repo has never been
packed. A `git gc` would likely shrink it substantially. **Mike's instruction 2026-08-04: log it, do
not run it. Separate item.** Unrelated to the `.claude` untrack.

### 📉 CORPUS FIGURES CORRECTED

`ebay_sales` is **163,374** rows, not the 71,652 recorded 2026-08-01. Split is **94.2% / 5.8%**, not
87.8% / 12.2%. ⚠️ **L-SW-2026-014's cited counts are stale** — its mechanism is unchanged and still
correct. `8709518`'s commit message says 87.8% and is now pushed, so that figure is permanent in
history. Not edited in `LESSONS.md`; flagged for Mike.

### 🔜 FOLLOW-UP 2 — polysemy audit: NOT STARTED

Held until the drift work closes (Mike's sequencing). Scope when opened: all **472 columns**, terms
that denote different things in different tables. Seed set: `grade` (NUMERIC in `market_sales`, TEXT
in `collections`), `source`, `value`, `status`, `title`, `confidence`. Value is independent of NLQ —
it documents the data model and locates where wrong joins are most likely today.

---

## 2026-08-03 (EVENING) — ✅ **SIGN-IN ENTRY POINT FIXED, SHIPPED AND VERIFIED LIVE; WHATNOT VISION 401 DIAGNOSED**

**MOST RECENT CHANGE (Rule 5): `/login.html`'s default panel is now `loginPanel`, selected by an explicit
branch; signup is reached via `?mode=signup`. Supersedes "`signupPanel` is now the default panel" (set
2026-07-29 by `b981789`).** Frontend only — **purged, no Render deploy.**

**Shipped:** `8f113c9` (fix) · `3a21ca1` (lessons + state) · `88700f8` (tombstone-quoting fix).
⚰️ **Do NOT re-present any command block from this session — the work is shipped and purged.**

**✅ Verified on live slabworthy.com at 375×812, by clicking the actual link:** Sign In on the landing
page → `/login` → `loginPanel`, "Welcome Back", submit "Log In" at **y=688**, Sign Up tab at **y=254** —
both above the 812 fold, no scrolling. `verifyingPanel` present. Was: `signupPanel`, "Create Account",
toggle at y=1046. Purge sweep green on all four pages (NEW present AND OLD absent, comments stripped).

### 🧯 Two verification findings from the purge check — both false alarms, opposite mechanisms

**1. A purge check run too soon reports a FALSE FAILURE.** The first sweep read `pricing.html` at
**35,642 bytes** with 0 matches; minutes later it was **35,654** with 1 — a 12-byte delta, exactly
`?mode=signup`. The page was mid-propagation. Confirmed it was not a ship failure before re-running:
HEAD contained the change, `main` was in sync with `origin/main`, and a cache-busted fetch matched the
plain one. **The artifact and the check were both correct; only the timing was wrong.** Companion to
L-SW-2026-017 — a decoy artifact reports false success, a premature check reports false failure.
**Wait a minute before re-checking, and diff byte counts before suspecting the deploy.**

**2. A tombstone that quotes the string it retires trips its own audit.** The same sweep reported the
dead beta-code phrase live in `waitlist.html`; it was matching the explanatory comment added in the very
commit that removed it. Rendered copy was correct throughout. Fixed in `88700f8` (comment now describes
rather than quotes) and recorded as a **corollary to L-SW-2026-015**: *a HIT is not a failure until the
match is confirmed to be the live instance* — the mirror of 015's false-negative rule. Sweeps should
strip comment nodes and assert NEW-present alongside OLD-absent.

### ⚰️ TOMBSTONE — the Unit D attribution was WRONG, and the correct framing matters

- **DEAD:** *"Sign In lands on Create Account because Unit D (`b981789`) made signup the default panel."*
- **REPLACED BY:** the defect **predates** `b981789`. Before it the default was `betaCodePanel` — also
  not the login form. **"Sign In" has never reached the login form.**
- **REASON:** `b981789` changed **severity, not cause.** The beta panel was one input and a button, so
  its identical "Already have an account? Log in" link sat on-screen; the six-field signup form pushed
  that same link **234px below the fold at 375×812** (202px at 1440×900 — measured live, both viewports).
  A mildly wrong landing became an unreachable one.
- **SUPERSEDES:** any framing that scopes this to Unit D. ⚠️ **A fix aimed at Unit D alone would have
  left the gap in place** — which is precisely why this is recorded as a tombstone and not a note.

### ⚰️ `?signup=true` was DEAD from `cbd80d7` (2026-02-28) to 2026-08-03 — five months

`index.html`'s Sign Up link carried it; `login.html` **never** contained a reader (`git log -S` finds no
match in its whole history). It "worked" only because signup was the default. It **hid the real defect**
by supplying false evidence that panel selection existed. Now an **alias** for `?mode=signup` and it must
STAY one — the link is live, may be bookmarked, and pages get cached; deleting it would make it dead a
second time, in the direction that breaks signup. New lesson **L-SW-2026-018**; instance of L-SW-2026-016
extended from display surfaces to contracts.

### What changed (4 files — SHIPPED, purged, verified live; see hashes above)

| Part | Change | Files |
|---|---|---|
| A | Explicit `?mode=login\|signup` selector; default = login; `?signup=true` kept as alias; `?invite=` forces signup | `login.html` |
| B | Two-button tab bar at the top of both panels, reusing the **orphaned** `.tabs`/`.tab` CSS (present since forever, no markup ever used it) | `login.html` |
| C | `?mode=signup` on the four acquisition CTAs | `index.html` ×3, `pricing.html` |
| D | `verifyingPanel` shown **synchronously** before the verify fetch; `proceed()` given a terminal else-branch | `login.html` |
| — | Stale "Already have a beta code?" → "Already have an account?" (beta gating died 2026-07-29) | `waitlist.html` |

**Verified locally over HTTP** (`file://` strips query strings — a near-miss false pass, L-SW-2026-015):
`?mode=signup`→signup · `?signup=true`→signup · `?invite=`→signup + URL cleaned · `?token=`→**never
signup**, lands loginPanel + server message · bare→login. Tabs and footer links toggle both ways. At
375×812 **both panels put the toggle at y=254, above the 812 fold**; the login submit is at y=689, so the
whole login flow fits without scrolling.

⚠️ **`sw.js` needs NO `CACHE_NAME` bump** — only HTML changed, and HTML is never precached (policy
rewritten 2026-07-29). No service-worker staleness risk against the purge check.

### 🔎 Whatnot valuator vision scanning — diagnosed, NOT fixed

**Real 401, not a mislabeled 403.** `request_logs` rows 199912/199915/199921: `POST /api/vision/analyze`,
**401**, `user_id NULL`, `"Authentication required"`. NULL `user_id` proves `g.user_id` was never set, so
the 403 plan gate was never reached. The extension's "Session expired" label is **correct**.

- ⚠️ **The premise "it broke yesterday" is false.** Last successful scan **2026-07-01 05:12 UTC — 34 days
  before**. Zero vision traffic in between (the two 2026-08-01 405s were GET blueprint probes). The break
  is **not datable from traffic**; it failed on first use after a month idle.
- **Leading cause: plain JWT expiry.** `JWT_EXPIRY_DAYS = 30`, and the extension's token is minted once at
  Options sign-in and **never refreshed** — no renewal path exists. Website logins don't touch
  `chrome.storage.local`. **Unproven** — needs the stored token's `exp` decoded locally.
- `a0cc9fa` **never touched `routes/vision.py`.** The message change was `88c42aa`, and it was the string
  only — gate logic byte-identical. `88c42aa`'s `billing.py` hunks did not touch `get_user_plan` or
  `check_feature_access`; `COMING_SOON_PLANS` is used only in `create_checkout_session`.
- **Mike = `users.id 3`, plan `free`, `subscription_status canceled`, `is_admin TRUE`.** Plan-wise he
  can't reach vision; the admin bypass grants it. But **`settings.js:158` computes
  `hasVision = ['guard','dealer'].includes(plan)` with no admin term, and `/api/billing/my-plan` doesn't
  return `is_admin`** — so once he signs back in the Options page will tell him he isn't entitled while
  the server grants him access. **Open.**
- ⚠️ **The claims audit's "not site-deployed, leave it" call on `CCExtensions/whatnot-valuator/settings.html:145`
  was WRONG (Mike, 2026-08-03)** — he uses the extension. Three strings still advertise Guard/Dealer, a
  tier `COMING_SOON_PLANS` refuses at checkout: `settings.html:145`, `settings.js:165` (with a live
  Upgrade link), `vision.js:136`. `content.js:95`'s modal is a fourth, different defect — it fires on
  *no token* while asserting a *plan* requirement it never checked. **All open.**

**Open on the extension — the full list, none started:**
1. **Refresh-on-use auth.** The token is minted once and never renewed; a 30-day expiry with no refresh
   path guarantees this recurs.
2. **`validateToken` fails OPEN** (`settings.js:126`) — a network exception returns `true`, so an expired
   token survives an Options visit made while Render is cold-starting. If Options shows signed-in rather
   than the login form, that is this path, not a valid token.
3. **The "Sign In Required" modal** (`content.js:95`) asserts a plan requirement it never checks — it
   fires on *no token*.
4. **Three Guard/Dealer strings** advertising a tier checkout refuses, one with a live Upgrade link.
5. **Options-page entitlement drift** — `settings.js:158` has no admin term and `/api/billing/my-plan`
   returns no `is_admin`, so it *cannot* be correct for an admin without an API change.

⚠️ Any fix here **must bump `CCExtensions/whatnot-valuator/manifest.json`** (currently **2.42.0**, last
bumped `86aff76` 2026-02-23). No code has changed since that commit and the tree is clean for that
directory, so there is no stale-reload blind window today — the bump is what keeps it that way.

### 📄 BO primer — rewritten as a DRAFT, not yet the mirror

`docs/SW_BO_PRIMER_DRAFT_2026-08-03.md` (untracked at time of writing). Full rewrite superseding the
2026-05-26 primer. ⚠️ **Read it before replacing `docs/SW_BO_PRIMER.md`** — the replacement block was
prepared but deliberately not run, and it consumes the draft path. Neither file is authoritative; BO
project storage is Mike's copy.

**Corpus verified live during the rewrite: `ebay_sales` 152,316 + `market_sales` 9,972 = 162,288** — up
from 125,720 at the 03:08 UTC snapshot the same day, and 105,132 the day before. **The draft instructs BO
to re-query rather than quote any numeric figure**, which is the only durable instruction for a number
moving this fast.

⚠️ **On the depth figures — do NOT let the "capture makes it worse" trend harden into a belief.** The
CP-1 doc's two snapshots went 84.6% → 85.3% (≤2 comps); an independent reproduction the same evening on
the larger corpus read **83.9%**, on filters that follow §10's recipe but are **not** a byte-for-byte
match to the doc's query. Three points, two methodologies — the *magnitude* is stable and bad, the trend
line is not established. **The durable finding: roughly five in six comp cells rest on one or two sales,
and of ~4,600 books only ~400–500 have any grade backed by three or more comps.** The structural argument
(scarce Bronze Age keys arrive as fresh 1-comp cells) stands on its own without the trend.

### 🔁 SYSTEMATIC FINDING — backend correct, user-facing surfaces lagging

**Three instances in one night, all the same shape:** the server was right and the surface a user touches
was not.

1. **`login.html`** — the panel logic never selected login; every "Sign In" link on the site landed on a
   signup form, for months.
2. **`waitlist.html`** — the acquisition page asked for a beta code, gone since 2026-07-29.
3. **The Whatnot extension** — still sells Guard/Dealer, pulled from sale 2026-08-01, with a live Upgrade
   link to a checkout that refuses it.

⚠️ **In every case the backend decision had already been made and correctly implemented.** The lag is
entirely in copy and routing, which no server-side test observes.

**Standing recommendation (Mike, 2026-08-03): run a user-facing surface sweep after ANY tier or gate
change — not only before launch.** The trigger is the decision, not the calendar; each tier or gate change
will produce new instances the same way these three did. 🔼 **Proposed as a lesson candidate (L-SW-2026-019)
— not minted, Mike's call.**

---

**Session UUID:** `638118e4-6bdd-4ef4-93b4-e89525e1f1a6`

---

## 2026-08-03 (SESSION CLOSE) — ✅ **FOUR UNITS SHIPPED; CAPTURE WRITE PATH 41.5s → SUB-SECOND, MEASURED**

**MOST RECENT CHANGE (Rule 5): the CP-1 remediation order was REVISED — canonical "of" fragmentation is now item 1, displacing signed-comp contamination. Supersedes the order set 2026-08-02.** Reason: fragmentation's cost **compounds with capture activity** (the work being done most), while signed contamination is stationary at ~7.8%. Tombstone + full order live in `docs/technical/CP1_STATE_OF_PLAY.md` §9.

⚰️ **ALSO DEAD, same session:** *"confidence is computed and stored but displayed nowhere"* — see the tombstone at the CP-1 section below. It was false.

### What shipped

| # | Unit | Files | Commit |
|---|---|---|---|
| 1 | Batch write path: one commit per batch + R2 backup off the request path | `routes/sales_ebay.py`, `docs/technical/ARCHITECTURE.txt` | **`a80b5cd`** |
| 2 | Extension: honest sync-failure reporting + unsynced-buffer warning | `CCExtensions/ebay-collector/content.js`, `popup.js` | **`b4ba1ba`** |
| 3 | CP-1 audit recorded as a durable artifact | `docs/technical/CP1_STATE_OF_PLAY.md` | **`a176d3d`** |
| 4 | Bulk insert via `execute_values`, per-row loop kept as fallback | `routes/sales_ebay.py` | **`680f243`** |

⚠️ Unit 2 is **extension-only — no Render deploy.** It takes effect only when the unpacked extension is reloaded in `chrome://extensions`.

### ✅ Write path — measured, not asserted

| Version | Commit | Measured |
|---|---|---|
| v1 original (commit per row + inline R2) | — | **41,552 ms** avg / 184,417 ms max |
| v2 (one commit per batch, R2 async) | `a80b5cd` | **9,721 ms** avg / 40,055 ms max |
| v3 (bulk `execute_values`) | `680f243` | **547–940 ms** avg / 3,233 ms max |

```
19:52   7 reqs  avg 44,083ms   <- last v2 minute
19:57  12 reqs  avg    848ms  max 2,207ms
19:58  10 reqs  avg    547ms  max 1,706ms
19:59  12 reqs  avg    940ms  max 3,233ms
```

**~50× off the original baseline, sub-second at 10–12 req/min — heavier concurrency than any minute in the v2 data — and the self-congestion ramp is gone.** No 10s+ readings, which is the tell that the bulk path is *succeeding* rather than aborting into the per-row fallback.

⚠️ **The root cause of the original symptom was never an outage.** `request_logs` showed 293 batch POSTs, **all HTTP 200**, while the extension banner read "backend offline" — the server was completing and the client was timing out. The banner asserted a cause it never established (L-SW-2026-007), which Unit 2 fixes.

**Two things load-bearing in `routes/sales_ebay.py`, do not remove:**
1. **The per-row `SAVEPOINT` fallback.** A bare bulk statement aborts entirely on one malformed row — reintroducing the exact regression the savepoint was added to prevent. Bulk is wrapped in `SAVEPOINT sw_bulk`; any failure rolls back and re-runs the batch per-row.
2. **`ON CONFLICT` is UNTARGETED on purpose.** `ebay_sales` has **two** unique indexes — `ebay_item_id` **and** `content_hash`. A targeted clause aborts the bulk statement on a same-title/price/date collision, which is common enough (1,585 recurring `(raw_title, sale_price)` pairs) to make the fast path *slower than the loop it replaces*. Found in review, not by testing — the temp-table check had only one index and would not have caught it.

### 🔎 Three findings nobody was looking for

Full detail in `docs/technical/CP1_STATE_OF_PLAY.md` §5B / §5C / §11.

1. **Canonical "of" fragmentation** (now CP-1 item 1). "of" is dropped inconsistently, splitting comp pools. `Tomb of Dracula` exists both ways (308 rows/83 graded vs 66/23). `Master of Kung Fu` and `Savage Sword of Conan` lost it entirely, so a naturally-titled query reaches **none** of their 140 and 777 rows. Leading-`"The"` fragmentation is **NOT** affected — `title_matching._norm` strips it on both sides — so the 206 `"The"` pairs are harmless and **must not be "fixed"**. The 17-pair / 393-row figure is a **FLOOR**; sizing the universally-dropped population is part of the work. Same family as L-SW-2026-009 / L-SW-2026-011. **Found by a positive control on seven zero-result titles, per L-SW-2026-015 — not by looking for it.**
2. **The grade>10 parser bug is LIVE.** 11 → 13 rows, **5 arrived 2026-08-03**, new value `85.0`. `CGC 94` in a listing title parses as grade 94.0. Changes CP-1 item 3 from a cleanup to a cleanup **plus a parser fix**.
3. **Star Wars #1 variant stripping — the serious direction is the opposite of expected.** All 130 `is_variant` rows are **unpriceable** (excluded from every pool, routed to none). A real 35¢ variant sold at **$6,422** at grade 8.0; the regular pool median is **$272** — the owner is told $272, ~**24× under**. Leaking into the regular pool is negligible for this book (≤1% median effect). The price-variant regex at `title_normalizer.py:274` is **effectively dead code**, firing on **1 of 63** real titles because `[¢c]` consumes the "C" in "Cent".

### 📈 Corpus direction — capture volume alone will not fix confidence

Two dated snapshots in `CP1_STATE_OF_PLAY.md` (§5, §5B), deliberately **not** overwritten. `ebay_sales` 95,169 → **115,756** (+20,587) in one run — and the thin-data ratio got **worse**: cells at ≤2 comps **84.6% → 85.3%**, `medium`-on-≤2-comps **702/1,389 → 870/1,676**. Breadth grew faster than depth (+1,207 cells, only +139 reaching ≥3). Whatnot is dark: **+1 row since 2026-07-01**.

### 🧯 Two process findings recorded at close

**1. ⚠️ THE EXTENSION RAN 4.5 MONTHS OF UNVERIFIABLE RELOADS — and some past debugging may have run against stale code.**

`CCExtensions/ebay-collector/manifest.json` sat at **1.3.5 from 2026-03-19** while `content.js` changed repeatedly: the **July selector fixes** (`bbe5353`), the **hydration/MutationObserver fix**, the **`/sold/i` case-sensitivity fix** (the one that was silently rejecting 267/279 items), the **sync-honesty unit** (`b4ba1ba`), and the **counter unit** (`d3a47ff`). The extensions load **unpacked**, so reloading is a manual step with **no confirmation** — and with the version frozen, **a forgotten or failed reload was indistinguishable from a successful one.**

⚠️ **The implication is not just "we couldn't confirm."** Any debugging session in that window may have been reasoning about behaviour produced by **stale code** — including the July 16 collector diagnosis, which went through several wrong theories (hydration, then visibility filtering) before the case-sensitivity root cause. Nothing is known to be wrong because of this; the point is that **it was not knowable**, and past conclusions from that window carry that caveat.

**Same family as the two Render deploys that silently didn't fire on 2026-08-02** — an action whose completion is not observable is indistinguishable from an action that was skipped. `CLAUDE.md` already carried that warning for Render deploys; it now carries the equivalent rule for extensions.

⚰️ **FIXED FORWARD (`ed4f2a0`):** bumped to **1.4.0** (confirmed by Mike in `chrome://extensions`), and **`CLAUDE.md` now makes the bump MANDATORY** — same commit as the change, expected version stated in the ship block. Scheme documented from the existing history (1.0.4 → 1.1.0 → 1.3.5), not invented.

**2. 📋 REPO HYGIENE — a deliberate pass is owed. Not urgent; logged so it is a decision, not a drift.**

Working tree outside `.claude/worktrees/`: **4 modified, 27 untracked.**

- **Modified:** `.gitignore` · `TODO.md` · `scripts/slabguard_crosscamera_test.py` · `tests/SlabGuardTests/TP_RESHOOT_PROTOCOL.md`
- **Untracked (sets):** `docs/postmortems/` (deliberately untracked per the 2026-08-01 close — commit it deliberately in a later pass) · `tests/SlabGuardTests/` E3/TP/FP photo sets and CSVs · `tests/7_8/`, `tests/Mobile/`, `tests/SectionBTest/`, `tests/SectionDTest/`, `tests/Valuation/` · `CCImages/6_8_26_Tests/` · `DFToBSCOnvos/` · `scripts/e3_edge_sequence_test.py` · loose files: `AdminCheckjs.js`, `ebay_diff.txt`, `ebay_sig_diff.txt`, `extensioncountofsales.png`

⚠️ **Mike's framing (2026-08-03), and the reason this is logged rather than ignored:** *"File-specific staging is protecting me correctly, but it only works as protection if someone eventually looks at what's being excluded."* The per-file staging convention has held all session — nothing unintended has been swept in — but it silently accumulates the excluded set, and an unreviewed exclusion list is a place for something that mattered to hide. **The pass should decide per item: commit, gitignore, or delete.** Large binary photo sets are the main judgement call.

---

### ⏭️ Next session opens on CP-1 item 1 — canonical "of" fragmentation

Order: (1) "of" fragmentation · (2) signed-comp contamination (7.8%, 325 mixed cells, 1.73× median) · (3) grade>10 cleanup **+ parser fix** · (4) `total_graded >= 10` clause · (5) display consolidation + `README.md:11`.

---

## 2026-08-01 (SESSION CLOSE) — ✅ **SIX UNITS SHIPPED AND VERIFIED LIVE**

**MOST RECENT CHANGE (Rule 5): all six units are deployed and verified in production. Backend deploys confirmed by commit hash in Render Events — `88c42aa` (Guard checkout gate) and `a0cc9fa` (email templates), both live. Supersedes every "drafted / awaiting ship" framing below.** ⚰️ **Do NOT re-present any command block from this session; the work is shipped.**

### What shipped

| # | Unit | Files | Deploy |
|---|---|---|---|
| 1 | Guard checkout refusal + stop upselling unbuyable tiers | `routes/billing.py`, `routes/vision.py` | **`88c42aa`** — Render verified |
| 2 | Pricing rebuilt two-column + Guard/Dealer roadmap strip | `pricing.html`, `account.html`, `faq.html` | Pages purged |
| 3 | State record | `docs/sessions/WHERE_WE_LEFT_OFF.md` | — |
| 4a | Slab Guard claims — frontend | `check.html`, `app.html`, `waitlist.html`, `waitlist-confirmed.html` | Pages purged |
| 4b | Slab Guard claims — email templates | `routes/waitlist.py`, `routes/admin_routes.py`, `routes/verify.py` | **`a0cc9fa`** — Render verified |
| 4c | Fingerprinting doc tombstone | `docs/technical/FINGERPRINTING_PROJECT_SUMMARY.md` | — |
| 5 | Privacy disclosure (shipped **ahead of** pixel code, deliberately) | `privacy.html` | Purged |
| 6 | Meta Pixel | `js/pixel.js`, `js/footer.js`, `footer.js`, `js/sidebar.js`, `login.html`, `sw.js` | Purged |

**Post-deploy verification (read-only):** `/health` 200 `{"status":"ok","version":"5.6.0"}`. All four edited backend modules confirmed *imported* by app-handled JSON responses — `/api/waitlist/count` 200, `/api/verify/lookup/...` 404 JSON, `/api/admin/users` 401 JSON, `/api/vision/analyze` 405. That was the check that mattered for 4b: a broken f-string in an email template is a `SyntaxError` at import, the blueprint never registers, and those would have been Flask HTML 404s. ⚠️ **`/health`'s `version` is a hand-maintained string with NO commit SHA** — it can never confirm which commit is live; Render Events is the only source for that.

### Guard tier → coming-soon (three independent gates, all required)
1. **Server:** `COMING_SOON_PLANS = ('dealer','guard')` in `routes/billing.py`, refused ahead of the 409 active-subscription guard (which now only ever sees `'pro'`). Dealer's status/keys/error string unchanged.
2. **Stripe (Mike-side, done BEFORE this brief ran):** Guard monthly + annual removed from the live customer portal's switchable products. ⚠️ **This was the real bypass** — the portal is the only in-place plan-modify path and code cannot reach it. Guard prices were **deliberately NOT archived** (reversibility; Guard is meant to return).
3. **UI:** pricing rebuilt two-column Free/Pro, Guard + Dealer demoted to a roadmap strip with Notify Me → `/contact.html`. "Most Popular" moved Guard → Pro. Compare table trimmed to Free/Pro. Save badge 25% → 17% (25% was *Guard's* discount; Pro saves 16.5% — the badge had been contradicting the Pro card beneath it).

**Re-enabling Guard needs all three reversed.** The one-line `COMING_SOON_PLANS` removal alone is NOT sufficient.

### Meta Pixel — live
Dataset **`4401241006789951`**; domain ID **`924245086634661`** verified via Cloudflare TXT. Confirmed firing on slabworthy.com: `signals/config/4401241006789951` returns a config (Meta recognises the dataset), `facebook.com/tr/` beacon sent, `_fbp` set, fbevents 2.9.368, queue drained. Intercepted wire payload: `id=4401241006789951, ev=CompleteRegistration, cd[content_name]=email_verified`.
- `Lead` = signup accepted **and** verification email dispatched (not on `email_send_failed`). `CompleteRegistration` = first email verification only; four independent guards (token NULLed server-side, `?token` stripped before the fetch resolves, response-shape check, localStorage sentinel).
- **The redirect is deferred until the conversion is actually dispatched** — firing then navigating in the same tick destroys queued events. Bounded 2s; an inert API installs when the pixel is off/blocked so signup is never delayed. *(An earlier draft stalled every verification 10.8s; caught and fixed pre-ship.)*
- **Privacy shipped first, on purpose.** Includes the CCPA revision at **`privacy.html:347`** plus its twin in "How We Use Your Information" — both "we do not sell your personal information" claims now qualified, since sharing ad data with Meta may count as a "sale"/"share" even with no money changing hands.

### ✅ `handle_subscription_deleted` — CONFIRMED IN PRODUCTION
An **accidental live Free→Guard checkout**, then cancelled: the user row reverted to `free` correctly. **This was Section E's last untested path.** ⚰️ Retire "subscription-deleted path untested" wherever it still appears — it is closed by production evidence, not a fixture.

### ✅ `sw.js` install-precache + activate-eviction — CONFIRMED EXECUTING
Previously recorded as "NOT verified by execution" (the in-app browser kept reusing an active worker). Now observed on live slabworthy.com: exactly one cache `slabworthy-v3-20260801`, `/js/pixel.js` precached, **zero HTML cached**, zero stale caches remaining. ⚰️ That open item is closed.

### Slab Guard claims audit — outcome
**Taken:** Tier 1 items 1–6 and Tier 2 items **7** (*"authentication and theft protection"* → *"registration and theft-deterrence"* — **we do not authenticate, CGC does**) and **9** (*"proof of ownership"/"ownership evidence"* → *"evidence of possession at registration"*).

**Deliberately KEPT, with reasoning — do not re-flag:**
- **8** `index.html:1052` "Protect Your Collection" — brand framing, and deterrence *is* genuine protection; with 1–6 landed the section beneath it is accurate.
- **10** `pricing.html` Slab Guard banner — already the most honest copy in the repo ("candidate sightings", "beta", "may be inaccurate").
- **11** `verify.html:531` serial verification — **deterministic, works, and is the claim we want leading.**

⚠️ **FOUR LATE MISSES, found only after I had already reported the audit as complete:** `waitlist-confirmed.html` (never audited at all — it's shown to every waitlist signup), `app.html:2872` (JS-injected success message still read "Monitoring enabled for theft recovery", **contradicting copy rewritten 40 lines above it**), the `check.html` match verdicts, and `routes/verify.py:411` (sighting-alert **email** calling Slab Guard a "theft recovery system"). **One was caused by my own `head -22` truncation hiding line 2872** — see L-SW-2026-015.

⚠️ **LOGGED, NOT CORRECTED (Mike's call):** the two corrected email strings had already been delivered to real users. Not retracted or re-sent at this volume. Recorded so nobody later reads the fixed templates and assumes the old wording never shipped.

### Match verdict rewrite (`check.html`) — the reasoning is the point
`same_copy` → "Strong candidate match — review this listing carefully". `different_copy` → "No strong match… **Photo comparison can't rule a copy in or out**; to know for certain, check the serial number." `uncertain` → also routes to the serial.

**`different_copy` was the HIGHER-RISK string, not `same_copy`** — a false negative tells someone their stolen book isn't theirs and **they stop looking**. Cross-camera FP ran 4/6. Both non-positive verdicts now route to serial verification, the deterministic path and the only one that gives a definitive answer. **Mike: this is the pattern to repeat everywhere Slab Guard surfaces a judgment** — state the epistemic limit plainly, then send people somewhere real.

### ⚰️ TOMBSTONE — the two-table trap (see also L-SW-2026-014)
"The valuation corpus is eBay-only" is **DEAD — it was never true.** I flagged accurate copy at `waitlist-confirmed.html:306` as a false claim; **Mike corrected it and the correction is confirmed by a read-only count.**

| Source | Table | Rows | Share |
|---|---|---|---|
| eBay | `ebay_sales` | 71,652 | 87.8% |
| Whatnot | `market_sales` | 9,963 | 12.2% |

⚠️ **`market_sales` is 100% Whatnot** (`sales_market.py:127` defaults `source` to `'whatnot'`). Querying either table alone yields the **opposite** wrong answer with equal confidence. Whatnot is 9,963 real captures across 1,603 titles / 35 series (2026-01-24 → 2026-07-01) — **not fixtures**. **`waitlist-confirmed.html:306` was investigated and found CORRECT. Do not "fix" it.** Mike's ruling on phrasing: 88/12 is fine — *"across eBay and Whatnot"* describes provenance, not proportions.

---

## 🎯 ~~NEXT SESSION OPENS ON CP-1 — THE VALUATION HONESTY GATE~~ — ⚰️ **AUDITED 2026-08-02/03; THIS FRAMING IS DEAD**

⚰️ **TOMBSTONE (Rule 2) — added 2026-08-03.**
- **DEAD:** *"confidence is **computed and stored but displayed nowhere**"* and *"It remains UNTOUCHED."*
- **REPLACED BY:** CP-1 has been **audited read-only** and the audit lives in **`docs/technical/CP1_STATE_OF_PLAY.md`**. **"Displayed nowhere" was FALSE** — confidence renders in **two** live surfaces in `app.html` (`:1227-1230` + `:2714-2722`, and `js/app.js:1288-1300`). The real defect is **five inconsistent notions of confidence across five threshold sets**, plus a label that is systematically too generous (870 of 1,676 `medium` labels rest on ≤2 same-grade comps).
- **REASON:** the old framing scoped CP-1 as "wire up the display," which would have been the wrong work.
- **SUPERSEDES:** do **not** re-derive a CP-1 plan from this section. `CP1_STATE_OF_PLAY.md` §9 holds the current, tombstoned order.

⚠️ **CP-1 is audited but NOT FIXED** — the gate was characterised, not cleared.

⚰️ **TOMBSTONE (Rule 2) — "AUG 4 IS THE GATE" IS DEAD. Mike, 2026-08-03.**
- **DEAD:** *"Aug 4 soft launch"* as a live date, and my own framing above it that *"whether Aug 4 proceeds against a known-thin corpus is Mike's undecided call."* **Aug 4 was never a live date.** I asserted it from stale docs without checking; Mike corrected it.
- **REPLACED BY:** the real gate is **FIRST COLD TRAFFIC — paid ads or an organic group post. It is NOT SCHEDULED.** There is no calendar date attached to it.
- **WHERE CP-1 SITS:** its remaining fixes are **UPSTREAM of that gate** — they must land before cold traffic arrives, not before a date. So there is no date pressure, but there is ordering pressure.
- **REASON:** a date that nothing is actually planned against produces false urgency and, worse, invites a go/no-go decision nobody asked for.
- **SUPERSEDES:** every "sole declared blocker for Aug 4" / "Aug 4 board" framing, including the ones lower in this file (2026-07-29 blocks) and in the SoT docs listed below. **Do not sequence, count days, or stage a go/no-go against Aug 4.**

⚠️ **STALE-DATE ARTIFACTS — NOT SWEPT, Mike's call (a repo-wide Aug-4 sweep is a decision, not a cleanup):**
`CLAUDE.md:57` and `:95` · `docs/LAUNCH_READINESS.md:5`, `:7`, `:9`, `:15`, `:18` · the 2026-07-29 blocks lower in this file (`:233`, `:238`, `:254`, `:289`, `:318`, `:369`, `:391`–`:398`) · `docs/EBAY_CAPTURE_SCHEDULE.docx` §4, which states *"Soft launch is 2026-08-04, so the trigger fires immediately"* and therefore mis-schedules the `lookup_demand` promotion loop. Every one of these reads **Aug 4** and every one is now **DEAD as a gate**. They are left in place deliberately — sweeping them touches the launch SoT.

**Still accurate from the original note, and not superseded:** multi-run voting exists server-side but the frontend hardcodes `runs: 1` (`app.html:2355`); a live harness exists at `test_grading_consistency.py --live`; **grading consistency has never been measured.** The framing still holds: *honest about confidence, not accurate on everything.*

### 📋 OPEN ITEMS
1. **Test-address problem — Cloudflare Email Routing catch-all on `slabworthy.com`, MID-SETUP.** ⚠️ **DO NOT TOUCH `send.slabworthy.com` MX, SPF or DKIM — those are Resend OUTBOUND and unrelated.** Inbound catch-all only.
2. **DMARC record missing** on the sending domain.
3. **Meta Events Manager cold-signup walkthrough** — never run. I verified the beacon reaches Meta with the correct dataset and payload, **not** that Events Manager attributes it. Walk: landing → signup → verification email → click → verified; assert `Lead` once, `CompleteRegistration` once, neither re-fires on refresh.
4. **Authenticated Guard refusal unproven in prod** — `POST /api/billing/create-checkout {"plan":"guard"}` returns 401 unauthenticated; the 400 `coming_soon` path sits behind `@require_auth`. Passed 13/13 offline against the real view, and the portal gate is closed, so exposure is narrow.
5. **Mobile pass** — still the priority (FB traffic is mobile).
5a. **⏱️ Render instance failure 2026-08-03 ~07:53 — health check timed out after 5s, then recovered.** Seen in Render Events. **Predates all of this session's work** (the write-path units deployed that evening), so it is NOT a regression from them. Not urgent; **not investigated.**
   - **UNTESTED HYPOTHESIS, explicitly flagged as such (L-SW-2026-007 — instrument, do not theorise):** `dependency_monitor.check_all` still runs inside `/health`, so the availability probe Render acts on performs outbound network I/O. A 5s timeout on an endpoint that makes external calls is a plausible shape — **and that is all it is.** L-SW-2026-013 was a prior incident of alert I/O sitting in that same request path, which is why it is the first thing to check, not evidence that it is the cause.
   - **First move:** `request_logs` around 07:53 plus the Render log for that window. Do not act on the hypothesis before the logs say something.
6. 🔻 **SLAB GUARD VIDEO RESEARCH — UNBOUNDED, AND IT IS BLOCKING MORE THAN IT LOOKS. NEEDS A DECISION, NOT A TASK.**

   **What it blocks (Mike, 2026-08-01 — this is the reason it can't just sit):**
   - a **patented** feature (Comic Fingerprinting Theft Recovery, filed 2026-02-12),
   - an **unsellable tier** (Guard — the whole coming-soon unit above exists because of this),
   - the **Slab Guard B2B licensing story**.

   **Its current state: no owner, no date, no decision criterion, no result.** That combination is
   how it drifts into next month unnamed — three high-value things parked on an open question
   nobody has been assigned to close.

   **Required outcome — pick ONE (Mike, not decided today, but do not let it drift):**
   - **(A) TIMEBOX IT.** Fixed calendar bound **plus a pre-committed decision criterion written
     down BEFORE the work starts** — i.e. the accuracy/FP bar that counts as success, decided in
     advance so the result can't be graded against a moving target. On expiry with the bar unmet,
     it auto-parks to (B). No extension without a new explicit decision.
   - **(B) PARK IT EXPLICITLY** and **build CGC cert-number matching as the real recovery path.**
     Cert-number matching is **deterministic and already honest** — the same property that made
     serial verification the claim we chose to lead with in the `check.html` verdict rewrite. This
     is the option that ships something.

   ⚠️ **What must NOT happen: a third state where it stays open, undated and unowned.** That is
   exactly where it is now.

   **Interim honest headline stays: CGC cert-number matching — NOT fingerprint recovery.** Prior
   findings for whoever picks this up: cross-camera was never validated (E3 rep TP 6/6 but **FP 4/6,
   REJECTED** as too permissive), the ceiling was judged **physical** and triangulated three ways,
   and single-image matching is parked as bounded-to-high-wear. The SAM+E3 engine is retained for
   multi-view. Zero production code.
7. `docs/postmortems/` **stays untracked** — deliberate; committing files mid-ship-sequence is how staging accidents happen. Commit it deliberately in a later pass.

---

## 2026-08-01 — 🛡️ **GUARD TIER IS NO LONGER SELLABLE** (coming-soon, same pattern as Dealer)

**MOST RECENT CHANGE (Rule 5): the Guard tier was pulled from sale on 2026-08-01. Supersedes every "Pro + Guard are the two self-service options" statement in this file, including the 2026-07-29 portal-configuration and Unit-D plan-selection entries.** Reason: Slab Guard's **recovery** capability is unproven — cross-camera matching was never properly tested and a video-based approach is under evaluation with no result yet. We will not sell a tier whose headline capability is unproven, least of all on live keys.

⚰️ **TOMBSTONE — three dead statements, all retired today:**
1. **"Live portal plan-switching = Pro + Guard only, Dealer excluded"** (2026-07-29) is **DEAD**. **REPLACED BY:** Pro only — Guard monthly + annual were removed from the live customer portal's switchable products (Mike, verified against the config) **before** this work ran. The portal bypass identified in the code review is therefore **already closed**; do not re-raise it as open.
2. **"Unit D plan-selection page must offer Pro + Guard only, never Dealer"** is **DEAD**. **REPLACED BY: Pro only — never Guard, never Dealer.** ⚠️ The page is still **unbuilt**; this correction exists so it is not built from the stale spec. Free remains until the ~Sept 4 sunset.
3. **"Guard is the Most Popular tier"** (pricing.html) is **DEAD** — the badge moved to Pro, which is now the only purchasable paid tier.

**SCOPE — this is a PURCHASE GATE, NOT a feature removal.** Slab Guard registration, fingerprinting, `verify.html`, `check.html`, sightings and the admin review queue all stay wired and working. Existing Guard subscribers keep **every** entitlement — nothing reads plan state or revokes access. `PLANS['guard']` is untouched.

**✅ `handle_subscription_deleted` IS NOW CONFIRMED WORKING (2026-08-01).** An accidental **live** Free→Guard checkout was run and then cancelled; the user row reverted to `free` correctly. Section E had this path listed as **never tested** — that gap is now closed by real production evidence, not by a fixture. ⚰️ Retire "subscription-deleted path untested" wherever it still appears.

**Item held, deliberately:** archiving the Guard prices in Stripe is **NOT** being done. Guard is intended to become sellable again once recovery is proven, and archiving is a heavier reversal than a portal-config change. The prices stay live but unreachable — server refuses checkout, portal no longer offers the switch.

**Re-enabling Guard later is a one-line code change** (`routes/billing.py`, remove `'guard'` from `COMING_SOON_PLANS`) **plus** re-adding it to the portal config **plus** reverting the pricing-page layout. All three are required; the code change alone is not sufficient.

### 📋 SLAB GUARD CLAIMS AUDIT (2026-08-01) — the rule to apply from now on

**THE LINE:** *registration, fingerprinting, provenance, "on record", registry/serial lookup* = **proven today, state plainly**. *Theft recovery, finding stolen comics, proving ownership of a recovered book, matching a photo back to a registration* = **UNPROVEN, never claim**. Cross-camera matching was never validated (E3: TP 6/6 but **FP 4/6, REJECTED**; ceiling judged physical); a video-based approach is under evaluation with **no result yet**.

**Rewritten (approved by Mike):** `check.html` "identifies the exact same comic across different cameras, lighting, and backgrounds" → candidate matches to review *(this was the single worst instance — it stated the untested capability verbatim, on a public page)*; `app.html` registration blurb *(also falsely claimed Whatnot + "other marketplaces" monitoring — only eBay is monitored)*; `waitlist.html` feature + meta; `faq.html` "authentication and theft protection" → "registration and theft-deterrence" *(**we do not authenticate — CGC does**)*; `faq.html` "proof of ownership"/"ownership evidence" → "evidence of possession at registration"; `routes/waitlist.py` "Prove ownership" → "Put them on record"; `routes/admin_routes.py` invite "Register and protect".

**Deliberately KEPT after review (do not re-flag these):** `index.html:1052` "Protect Your Collection" — brand framing, and deterrence is genuine protection; the section beneath it is now accurate. `verify.html:531` serial-number verification — **deterministic, works, and is the claim we want leading.** `pricing.html` Slab Guard banner — already the most honest copy in the repo (says "candidate sightings", "beta", "may be inaccurate"). Patent titles in `CLAUDE.md` — filed titles, not product claims.

⚠️ **LOGGED, NOT CORRECTED (Mike's call): the two email strings above were already delivered to real users.** Not being retracted or re-sent at this volume. Recorded so nobody later reads the fixed templates and assumes the prior wording never shipped.

⚰️ **`docs/technical/FINGERPRINTING_PROJECT_SUMMARY.md` tombstoned** — it asserted "Technology WORKS for comic theft recovery" from a **same-camera** test. Internal, but it was the most likely thing to be read as ground truth by a future session and re-justify the claims we just removed.

**Also changed in the claims pass — `check.html` match verdicts.** These three strings are the only place the product reports a matching result to a user. `same_copy` → "Strong candidate match — review this listing carefully"; `different_copy` → "No strong match — same title, but the copies look different… check the serial number"; `uncertain` → also points at the serial. **Reasoning worth keeping: `different_copy` was the higher-risk string, not `same_copy`** — a false negative tells someone their stolen book isn't theirs and they stop looking. Both non-positive verdicts now route to serial verification, the deterministic path and the only one that gives a definitive answer.

### ⚰️ TOMBSTONE — "the valuation corpus is eBay-only" is **DEAD. It was never true.**

**RAISED** during the 2026-08-01 claims audit: `waitlist-confirmed.html:306` ("We track real sales data across eBay and Whatnot") was flagged as a false claim on the assumption the corpus was eBay-only. **Mike corrected it; the flag was WRONG and the correction is confirmed by a read-only count.** **DO NOT re-raise it, and do not "fix" that line** — it is accurate as written.

**Measured 2026-08-01 (read-only, `DATABASE_URL_RO`), and the reason the mistake was easy to make: the corpus lives in TWO tables.**

| Source | Table | Rows | Share |
|---|---|---|---|
| eBay | `ebay_sales` | 71,652 | 87.8% |
| Whatnot | `market_sales` | 9,963 | 12.2% |
| **Total** | | **81,615** | |

⚠️ **`market_sales` is 100% Whatnot** — `sales_market.py:127` defaults `source` to `'whatnot'`. Counting only `market_sales` and seeing no eBay rows (or only `ebay_sales` and seeing no Whatnot) gives the opposite wrong answer each way. **Query both tables.** eBay covers 2018-09-10 → 2026-07-16; Whatnot is 9,963 real captures, 1,603 distinct titles / 35 series, captured 2026-01-24 → 2026-07-01 — **not fixtures**.

**VERDICT: 12.2% across 1,603 titles is a meaningful share, so the copy stands unchanged.** The only residual is a phrasing judgement — whether "across eBay and Whatnot" implies more parity than 88/12 — which is Mike's call and blocks nothing. **This item was investigated and found NOT to be a defect. It is a tombstone, not a fix.**

---

> ⚰️ **READ-BEFORE-YOU-USE TOMBSTONE — applies to EVERY 2026-07-29 and earlier block below. Added 2026-08-03.**
>
> Everything from here down is **a record of what was true on its own date and is deliberately left unedited.** One thing in it is now dead and must not be carried forward:
>
> **"Soft launch = August 4, 2026" (and its lineage July 28 ← July 21) is DEAD. Aug 4 was never a live date** (Mike, 2026-08-03). **The gate is an EVENT: first cold traffic — paid ads or an organic group post — and it is NOT SCHEDULED.** Every "Aug 4" / "sole declared blocker for Aug 4" / "the Aug 4 board" phrase below is historical framing, **not a current gate**. Do not sequence, count days, or stage a go/no-go against it. Current statement of the gate: the 2026-08-03 block at the top of this file, and `docs/LAUNCH_READINESS.md`.
>
> Also dead below, same reason as the CP-1 tombstone above: **"confidence is computed and stored but displayed nowhere"** — it renders in two live surfaces. See `docs/technical/CP1_STATE_OF_PLAY.md`.
>
> Everything else in these blocks — gate statuses, incident forensics, commit hashes, decisions and their reasoning — remains accurate as history.

---

## 2026-07-29 (END OF DAY) — 📋 **FULL STATE: what shipped, what's open, what to pick up next**

**MOST RECENT CHANGE (Rule 5): billing went LIVE on real money and the signup gate came down — both on the same day. Soft launch remains AUGUST 4, 2026. Mike is on a break; back later or tomorrow.**

### ✅ SHIPPED + VERIFIED TODAY (in order)
| What | Commit / artefact | Evidence |
|---|---|---|
| Soft-launch date → Aug 4 | `6dd44b4` | docs only |
| GalaxyCon DROPPED, docs swept | `c140231` | 5 files + CLAUDE.md; GALAXYCON_SPRINT deliberately untouched |
| Unit A punch list | `1e1e6b3` | browser-verified 412×915 + desktop, logged in/out |
| Stripe preflight `--live` | `3225572` | all 4 key×flag combos; also fixed a pre-existing Windows crash (L-2026-015) |
| **Unit E — live Stripe cutover** | Render env, Mike | **real card: purchase → webhook → plan active → cancel → teardown → refund** |
| Live customer-portal config | Stripe dashboard, Mike | Pro + Guard switchable; **Dealer excluded** (matches `billing.py:511`) |
| Google Pay dashboard half | Stripe dashboard, Mike | code half still open — see Unit B |
| Test-mode Stripe id cleanup | SQL, Mike | 6 rows nulled, row 33 reset; fixtures 24/25/26 untouched |
| Signup-flow migration | `db_migrate_signup_flow.py` | ran clean, **13 grandfathered / 22 will see the plan page** |
| Gate removal + email canonicalisation + invite rewrite | `auth.py`, `login.html`, `admin_routes.py` | 18/18 signup assertions, 16/16 canonicalisation; **prod-confirmed: `mikeberrysc+test@gmail.com` blocked as duplicate** |
| Pending-user unlock | `db_migrate_approve_pending_users.py` | 1 candidate (`id=6`, Mike's own alias) |
| "Private Beta" badge → **"Early Access"** | `login.html` | badge is on the card, so correct on login/forgot panels too |

**Prod-verified by Mike:** private-window load shows the signup form by default, no beta-code box.

### 🔶 THE ONE REMAINING HARD GATE
**Valuation/identification honesty** — confidence is computed and stored but **displayed nowhere**. This is the old CP-1 from the retired sprint plan and the **sole declared blocker for Aug 4**. Everything else below is punch-list or polish.

### 📋 OPEN WORK (rough priority)
1. **Unit B — billing UX.** Current (free) plan navigates to the dashboard instead of reading as active/non-clickable. Plus **Google Pay: remove `payment_method_types=['card']` at `billing.py:570`** — it actively suppresses Google/Apple Pay/Link; the dashboard half is already enabled, so this one line is all that's left.
2. **Plan-selection page on first login.** Spec settled and **must not be re-litigated: Pro + Guard only, never Dealer** (Dealer is a sales conversation), Free until sunset. Trigger column `has_selected_plan` exists; 22 accounts are already FALSE and will see it.
3. **Coming-soon markers.** SlabGuard = **registration/upgrade copy only, public `verify.html`/`check.html` stay live**. Marketplaces = everything except eBay. ⚠️ **The platform list is duplicated in three places** — `js/collection.js:630`, `js/marketplace-modal.js:11`, `account.html#platforms` — change all three or the dropdown says "Coming soon" while the modal still opens.
4. **`FREE_PLAN_OPEN` switch.** One env var, read at signup/plan-selection. Mike flips it ~Sept 4. Existing free users (29) grandfathered; new signups then see Pro + Guard only. No scheduler needed.
5. **`sw.js` unit — BUILT IN TREE, NOT COMMITTED.** Detail below.
6. **My Collection affordance neutralisation.** `.comic-card` (`js/collection.js:329`) has no click handler while the gallery `.comic-frame` does. **Decision: remove the clickable styling now** so it stops reading as broken; the real detail view ships with the collection redesign. Don't build it twice.
7. ❓ **Market Pulse mobile charts — NEEDS RECHECK ON MOBILE. NOT a confirmed bug.** ⚰️ An earlier line in this file logged it as a defect; **Mike corrected that same day**: he isn't certain the charts failed to render — he may simply not have scrolled to them, or they may have loaded slowly. **Do not open a fix, do not scope work, and do not repeat "charts don't render" as fact.** The only action is: look at Market Pulse on a real phone, scroll all the way to the charts, and note whether they render and how long they take. If they're fine, delete this item.
8. ✅ **Post-subscription banner wording — CONFIRMED, ready to fix, code located.** In-app banner on **My Account** at **`account.html:536`**:
   - **Current:** `<strong>Welcome!</strong> Your subscription is now active. Time to protect your collection.`
   - **Replace with:** `Welcome! Your subscription is now active. Start grading your collection.`
   - **Why:** "protect your collection" is Slab Guard language, and Slab Guard is going "Coming soon" (item 3) — so the banner points a brand-new paying subscriber at a feature they can't use. "Start grading" points at the thing they actually just bought.
   - Logged by Mike in **Todoist as p3**. Just needs the one-line code change — **fold into Unit B** rather than shipping alone.

**DEFERRED by Mike (explicitly not bundled):** My Collection layout redesign — columns wrapping badly, unclear actions, wants a proper PR or two. Collection scroll behaviour at 20+ comics — untested, Mike will report.

### 🧩 `sw.js` UNIT — in tree, diff delivered, awaiting review
Files: **`sw.js` rewritten**, **`offline.html` NEW**, `login.html` (badge, same file as the Early Access change).
- **HTML is never cached now.** Previously every successful page load was stored, so a user on a flaky connection could be served an arbitrarily old page — including the removed private-beta panel — and we had **no way to fix it remotely**. Slab Worthy can't function offline anyway (grading + valuation both need the API), so caching app HTML bought nothing and was the only route to a stale-UI bug.
- **Failed navigations serve `/offline.html`**, self-contained (zero external requests, auto-reloads on `online`). Previously they fell back to cached `/index.html`, so a failed `/account.html` request silently showed the marketing homepage — reads as "the app logged me out".
- **Static assets stay network-first** with cache fallback. Deliberate: HTML is always fresh now, and a cache-first JS bundle could go stale against fresh HTML, which is worse than slightly slower.
- **`CACHE_NAME` → `slabworthy-v2-20260729`.** ⚠️ This makes the eviction code work **for the first time**: it deletes caches whose name ≠ `CACHE_NAME`, but the name was hardcoded `slabworthy-v1` from day one, so **that cleanup had literally never run.** Bump it on any deploy that changes a precached asset.
- **Verified:** after a real navigation the v2 cache holds **zero HTML**; CSS + JS still cached; `offline.html` renders correctly standalone.
- ⚠️ **NOT verified by execution:** the install-precache and activate-eviction paths. The in-app browser reused an already-active worker, so those lifecycle events never re-fired no matter how the registration was cycled. **Confirm in prod:** DevTools → Application → Cache Storage should show **only** `slabworthy-v2-20260729`, and it should contain `offline.html` plus static assets and no `.html` pages.
- 📌 **Correction to an earlier claim in this session:** the stale beta panel seen locally was attributed to the service worker. That isn't supportable — the SW was already network-first, and the unregister and a `?cachebust=` param were applied in the same step, so the two can't be separated. The browser's ordinary HTTP cache is the likelier cause. The `sw.js` defects above are real and worth fixing regardless, but they were **not** the cause of that observation.

### Git truth (2026-07-29 end of day, verified)
HEAD = `3225572`. Dirty in tree, **not committed**: `sw.js`, `offline.html` (new, untracked), `login.html` (Early Access badge), plus today's docs edits to `LAUNCH_READINESS.md` and this file. The `auth.py`/`admin_routes.py`/migration commit block was handed to Mike; confirm with `git log` whether it landed before assuming. Pre-existing `.claude/worktrees/*` dirt untouched as always.

### NEXT SESSION — 🎯 OPENING TOPIC IS FIXED, DO NOT PICK SOMETHING ELSE

**Mike's instruction (2026-07-29, end of day): the FIRST thing next session is the VALUATION-HONESTY GATE. He wants to understand exactly what is BUILT vs what is MISSING before anything else is touched. Open with that — read-only, no code.**

Why it's the right opener: it is the **sole remaining declared hard gate** for Aug 4 (billing closed today). Everything else on the open list is punch-list or polish, individually cheap, and could quietly absorb the whole week without this moving.

What's known going in (verify, don't assume — these are prior findings, not fresh reads):
- Confidence is **computed and stored** but **displayed nowhere** in the UI.
- Multi-run voting exists server-side, but the frontend hardcodes `runs: 1`.
- A live harness exists at root: `test_grading_consistency.py --live`.
- **Grading consistency has never been measured.**
- This is the old **CP-1** from the retired GalaxyCon sprint plan, where the bar was framed as *"honest about confidence, not accurate on everything"* — every FMV carries a confidence signal and thin comp pools say so plainly. That framing is worth re-reading; it's the cheapest version of the gate.
- Related, already logged: valuation Layer 3 (grade-aware raw estimate) was deferred into R1/R2; the media-junk/poster work is paused (Mike, 2026-07-29) with the eyeball list already produced.

Then, only after that discussion:
1. `git log --oneline -5` + `git status --short` — **verify what actually landed** before planning (L-SW-2026-008; state moved twice mid-session on 2026-07-29).
2. **Unit B** — the one-line Google Pay fix (`billing.py:570`) is the cheapest real win; bundle the current-plan UX and the `account.html:536` banner wording with it.
3. Plan-selection page → Coming-soon markers → `FREE_PLAN_OPEN`.
4. **Market Pulse: recheck on a phone. It is NOT a confirmed bug** — see item 7.

### ✅ Everything from 2026-07-29 is committed and deployed
`27144e3` sw.js/PWA + Early Access badge (deployed + **purged**, Mike) · `b981789` gate removal + canonicalisation + invite rewrite · `cbb50a8` signup-flow migration · `156f441` docs. Both migrations ran clean. Mike: *"That closes today completely."*

---

## 2026-07-29 (night) — ✅✅ **BILLING IS LIVE — UNIT E CLOSED, REAL MONEY VERIFIED**

**MOST RECENT CHANGE (2026-07-29 night, Rule 5): the live-mode Stripe cutover is COMPLETE and VERIFIED. Production runs on LIVE Stripe keys as of 2026-07-29. A REAL CARD was taken end-to-end: purchase → webhook → plan active → cancel → teardown → refund.** Mike ran every step.

⚰️ **TOMBSTONE — the two dead framings, both retired tonight:**
1. **"Production is on `sk_test_…0x9c`, no real user can ever pay"** (found this evening) is **RESOLVED**. Do not re-raise it; do not treat the test-key values recorded below as current. They are history.
2. **"Section E closed the billing *state machine*, not the ability to take money"** (written this evening) is also **RESOLVED**. Both halves are now proven: the state machine at `3935ce5` (2026-07-08, teardown + both guard branches observed live) and the money path tonight on a real card. **From here, "billing works" is true without qualification** — the distinction that entry drew no longer needs carrying.

🎯 **ONE OF THE TWO DECLARED HARD GATES IS CLOSED.** Remaining hard gate: **valuation/identification honesty** — confidence is computed and stored but **displayed nowhere**. That is now the **sole declared blocker for Aug 4**, and it's the old CP-1 from the retired sprint plan. Everything else on the board is punch-list or polish.

**Google Pay — dashboard half DONE, code half OPEN.** Enabled in Stripe payment methods (live mode). The remaining piece is `billing.py:570`, which sets `payment_method_types=['card']` and **actively suppresses** Google Pay/Apple Pay/Link regardless of dashboard settings. **That change belongs to Unit B**, not the cutover — recorded so it can't be mistaken for "Google Pay is done."

**Unaffected by the cutover, still true:** the DB cleanup (6 rows nulled, row 33 reset) and the `test-pro`/`test-guard`/`test-dealer` fixtures at rows 24/25/26 — DB-granted tiers, no Stripe objects, **still not revenue**.

---

## 2026-07-29 (evening) — 🔴 **P0: PROD WAS ON STRIPE TEST KEYS** *(RESOLVED same night — see above)* + Pixel punch list + Unit A shipped

**MOST RECENT CHANGE (2026-07-29 evening, Rule 5): production has been running on Stripe TEST keys — `sk_test_…0x9c` / `pk_test_…CiYH`. No real user could ever have paid. Found by Mike's Pixel walkthrough (only `4242…` accepted), confirmed read-only via the Render API. Cutover to a FRESH live key is in progress on Mike's side.** This outranks every other open item for Aug 4.

⚰️ **TOMBSTONE:** any earlier reading of "billing hard gate CLOSED" (Section E, 2026-07-08) as *"we can take money"* is **DEAD**. Section E's teardown/guard logic is genuinely proven — but it was proven **in test mode**, against test-mode objects. The gate was "the billing state machine is correct," never "real cards work." Both are needed for Aug 4; only the first is done.

**Key choice (DF rec, Mike agreed → created a fresh key):** two live keys existed, neither in Render. `sk_live_…id6R` (Feb 15, last used May 17, unnamed) — **don't use**, the Stripe account is shared with MASSÉ products so it may belong to another integration; coupling two projects to one credential means rotating it later breaks the other silently. `sk_live_…9ca0` ("Slab Worthy", created *and* last used 2026-06-19) — that date matches L-SW-2026-005's accidental-LIVE-key-in-Render incident exactly; not compromised, but its handling history includes a mistake. A fresh key costs 30 seconds and buys a clean provenance for the one credential that moves real money.

**Cutover audit (read-only, all from code):**
- **8 env vars change:** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, 6 × `STRIPE_*_PRICE`.
- ⚠️ **`STRIPE_PUBLISHABLE_KEY` is read by ZERO code** — checkout is a server-side redirect to a Stripe-hosted page. Update it for hygiene only; it has no functional effect. (Verified: no hits in any `.py`/`.js`/`.html`/`.json`/`.yaml`.)
- **`PLANS` reads price ids at MODULE IMPORT** (`billing.py:77,78,96,97,115,116`) → saving env vars is not enough, the service must restart. Pairs with L-SW-2026-004 (fresh shell) and CLAUDE.md's warning that auto-deploy is unreliable here.
- **Live webhook endpoint** must be at `/api/billing/webhook` with exactly the 5 events in `billing.py:673-677`. A signing secret is shown **only at creation** — an existing-but-unrecorded live secret must be ROLLED, never guessed.
- **Everything is env-driven** — zero hardcoded keys or price ids anywhere. The cutover is genuinely config-only.
- **Nothing is inferable about a price's mode from its id** (`price_…` in both), which is why the preflight has to retrieve them.

**✅ `scripts/stripe_preflight.py` — `--live` SHIPPED (`3225572`).** Inverts the expected mode (requires `sk_live_`/`rk_live_` + `livemode=true`), and reports a mismatch as a FLAG in **both** directions so a half-swapped config can't read green. Verified across all 4 key×flag combinations. Still strictly read-only — no create/modify/delete calls added. **Also fixed a PRE-EXISTING Windows crash:** it printed `→` and died with `UnicodeEncodeError` at `[1] KEY MODE` before checking anything on a cp1252 console — it had only ever been run in the Render shell. That's cross-project **L-2026-015** verbatim.

**✅ DB cleanup DONE + VERIFIED (Mike ran it, screenshot confirmed).** 6 rows (3, 29, 30, 31, 32, 33) had TEST-mode `cus_`/`sub_` ids nulled; row 33 (`mike@ideabyhuman.com`) additionally reset `pro/trialing → free/canceled` because Stripe had nothing active for it — it would otherwise have sat on a paid tier backed by nothing. **Rows 24/25/26 (`test-pro`/`test-guard`/`test-dealer`) deliberately untouched:** DB-granted tiers, zero Stripe objects, intentional fixtures — **and not revenue; don't count them.** All 9 confirmed by Mike as his own accounts.
- **Live-data lesson worth keeping:** row 29 changed state *between two reads in the same session* (a cancellation cascade landed there, not on 33 as assumed). Re-reading immediately before generating the SQL is what caught it. Never build mutation SQL on a snapshot taken earlier in the conversation.

**📱 PIXEL WALKTHROUGH PUNCH LIST — root causes all confirmed read-only:**
- ✅ **Unit A SHIPPED `1e1e6b3`**, browser-verified at 412×915 and desktop, logged-in and logged-out: (a) **`toggleFAQ()` was called by all 27 FAQ buttons and defined nowhere in the codebase** — ReferenceError per click; the CSS was always correct, only the class toggle was missing. (b) faq/pricing were missing the `sidebar.js` include — `detectPage()` **already had a `faq` case**, so it was designed to be there. (c) mobile topbar was in normal flow → `position:sticky; top:0; z-index:998` (below drawer 1000 / overlay 999). (d) duplicate brand header fixed **generically, not per-page** — because adding the sidebar to faq/pricing would otherwise have *created* the same bug there; hidden not removed, since `account.html:924` binds `#logoutLink` unguarded and app.html's header holds the logged-out auth buttons; matched by brand marker so page-title headers (collection.html) survive. (e) CollectionCalc stripped from **both live footer copies** — `sightings.html` loads root `/footer.js`, all 12 other pages `/js/footer.js`; root copy's brand mark also corrected (`SLAB` → `$LAB`). Legal-entity refs in ToS/privacy/about **deliberately untouched** (Mike: separate business decision, not made yet).
- **P1 (revenue) — HALF CLOSED 2026-07-29.** ✅ **Portal plan-switching CONFIGURED IN LIVE MODE (Mike, during the cutover): eligible switch targets = Pro (monthly + annual) + Guard (monthly + annual). Dealer DELIBERATELY EXCLUDED — requires a manual/sales conversation, not self-service.** That closes the *dashboard* half of the upgrade dead end (`billing.py:547` routes plan changes to the portal; `:617` creates the session with no explicit `configuration`, so it uses the account default — which is now correctly configured). ✅ **Portal now matches the code:** `billing.py:511` already refused Dealer checkout server-side, so the exclusion is enforced on both sides instead of one — a self-serve Dealer path can't open by accident from either direction. ⚠️ **Per-mode:** configured in LIVE only; a test-mode portal check will still read unconfigured — expected, not a regression. **STILL OPEN — the in-app half:** the current (free) plan navigates to the dashboard instead of reading as active/non-clickable.
- **Downstream of the portal config (spec input, don't re-litigate):** at free-plan sunset (~Sept 4) **Pro and Guard are the two options a new user sees** — that is the complete self-service menu by design. Unit D's plan-selection page must offer **Pro + Guard only** (plus Free until sunset) and must **never** surface Dealer as a self-serve choice.
- **OPEN P2:** comic tap dead (`.comic-card` has no handler; gallery `.comic-frame` does) — **decision: neutralize the affordance now, real detail view ships with the My Collection redesign, don't build it twice**. **No Google Pay because `billing.py:570` sets `payment_method_types=['card']`, which actively suppresses it** — needs the code change AND live-mode dashboard enablement.
- **ANSWERED P3:** Turnstile on signup is **not invisible-mode — it was never built.** Present only in `check.html`/`contact.html`; `TURNSTILE_SECRET_KEY` consumed only by `routes/contact.py` and `routes/verify.py`. Working as built.
- **Deferred by Mike:** My Collection layout redesign (own PR, not bundled); collection scroll at 20+ comics (untested, will report).

**🧩 UNIT D — fully specified, not started.** Mike's product calls: remove beta-code gating (**bundled with email normalization, not shipped bare**), plan-selection page on first login, free plan open through ~Sept 4 then manual sunset with existing users **grandfathered**, SlabGuard "Coming soon" = **registration/upgrade copy only, public verify/check stays live**, marketplaces other than eBay "Coming soon", **email canonicalization = NEW SIGNUPS ONLY, no backfill**.
- **Why no backfill matters (measured):** of 34 accounts, **11 are `mikeberrysc+…` aliases** — canonicalizing existing rows would collapse all 11 into one account. Existing rows keep their raw email as canonical; every current login keeps working.
- **The real gate isn't the beta code:** `signup()` only validates a code *if one is supplied*; the block is `auto_approve = bool(beta_code) or waitlist_confirmed` (`auth.py:693`) feeding the login check at `auth.py:812`. Removing "beta gating" means **letting `email_verified` be the gate**. Blast radius today: **exactly 1** verified-but-blocked account.
- **Population (read-only):** 34 accounts (the ~50 is the *waitlist table*, a different thing), 33 approved, 31 verified, 22 never logged in, 29 on free (25 `none` + 4 `canceled`), 5 paid.
- **Design snag logged:** `last_login IS NULL` is a poor first-login signal because `login()` sets it during login — recommend an explicit `has_selected_plan` flag; batches with the `email_canonical` migration.
- **Scope warning:** the marketplace list is duplicated in `js/collection.js:630`, `js/marketplace-modal.js:11`, and `account.html#platforms` — all three must change together or the dropdown says "Coming soon" while the modal still opens.
- **Ship order:** migration (`email_canonical` + `has_selected_plan`) → gate removal + email normalization → plan-selection page → Coming-soon markers → `FREE_PLAN_OPEN` switch.

**Git truth (2026-07-29 evening, verified):** HEAD = `3225572` (preflight `--live`); beneath it `1e1e6b3` (Unit A), `c140231` (GalaxyCon dropped), `6dd44b4` (Aug 4 date move). Working tree clean for all touched files; pre-existing `.claude/worktrees/*` dirt untouched as always.

---

## 2026-07-29 (later) — 🎪 **GALAXYCON IS OFF (DROPPED, not delayed)** + marketing shape + waitlist correction

**MOST RECENT CHANGE (2026-07-29, Rule 5): GALAXYCON SAN JOSE IS DROPPED — not postponed, not re-dated. Personal bandwidth (Mike), NOT technical.** Soft launch **still Aug 4**. After that: **SW is online-marketing-only for the rest of 2026**, reassessed as year-end approaches.

⚰️ **TOMBSTONE — the single most load-bearing dead assumption in this repo:** "GalaxyCon San Jose, Aug 21–23 2026 = the alpha launch event / booth demos / **the calendar anchor that doesn't move**" is **DEAD**. **REPLACED BY:** soft launch Aug 4 → quiet month → FB + email marketing → online-only through year-end. **REASON:** Mike's personal bandwidth. **SUPERSEDES:** `docs/sessions/GALAXYCON_SPRINT.md` **in its entirety** (⚠️ *not touched yet — awaiting Mike's call on archive vs replace, see below*), the "GalaxyCon is the calendar anchor / count weeks, not features" principle in `SW_BO_PRIMER.md:71`, the ROADMAP GalaxyCon launch section, and every booth/con framing in `LAUNCH_READINESS.md`.

**Why this is a re-shaping, not a cancellation line-item — what actually changes:**
1. **The forcing function is gone.** GalaxyCon was the immovable external date that made sequencing honest. Aug 4 is soft and quiet; after it there is **no external deadline at all** except the 90-day purge (~2026-09-17), which is now the *only* hard date left on the project.
2. **F-load drops off the launch-critical path.** Its target (10 concurrent / 3 grading, plus the F-L4 16–18 ceiling burst) was explicitly **booth-shaped** — a room of phones on venue wifi. A gated, wave-admitted online beta will not produce that. **Re-derive an online-shaped target post-launch or defer; do not run the dead booth target and call it a gate.** F-**mobile** is unaffected and still matters for Aug 4.
3. **Physical-venue work is moot:** booth demo design, booth signup mode (gated vs open QR), demo mode to spare Vision API on repeat booth demos, printed booth codes, and the "concentrated savvy-collector crowd" anti-abuse threat model. The anti-abuse holes stay parked — **but they re-activate when open public signup turns on with FB/email marketing**, same shape, different road.
4. **Scope discipline now has to come from the docs.** With no date to be honest against, the "we have time" trap the primer warned about gets materially more dangerous, not less.

**Marketing + sequencing (Mike, 2026-07-29):**
- **Channels: Facebook and email ONLY.** No other channels for now.
- **Sequence:** Aug 4 go-live → **~1 month quiet, NO active marketing push**, waitlist invites continue at current pace → **if nothing serious surfaces, marketing (FB + email) starts after** → online-marketing-only for the rest of 2026, reassess at year-end.

**📋 WAITLIST CORRECTION (Mike, 2026-07-29) — corrects the record:** of the **~50 signups, only ~30 are real users**; the rest are **Mike's own test accounts** created during development. Mike has **already been inviting every real signup** and will continue; signup rate is naturally slow, which suits the quiet month. ⚠️ **Never quote ~50 as real users or as demand.** Any conversion/engagement/COGS math must exclude the test accounts (~30 is the honest denominator).

**❓ OPEN QUESTION BACK TO MIKE (not actioned — do not touch `GALAXYCON_SPRINT.md` until answered):** what happens to that file? Recommendation + options in the session response of 2026-07-29; the file is a sprint plan toward an event that no longer exists, so a re-date is not a valid fix.

**Not changed by any of this:** every A–F gate status; the eBay/valuation corpus work; the 90-day purge deadline ~2026-09-17; Aug 4 itself.

---

## 2026-07-29 (earlier) — 🗓️ SCHEDULE CHANGE ONLY: soft launch moved July 28 → **AUGUST 4, 2026**

**MOST RECENT CHANGE (2026-07-29, Rule 5): SOFT LAUNCH = AUGUST 4, 2026 (Mike). REASON: personal availability — NOT technical, NOT readiness, NOT incident-driven.** ⚰️ **TOMBSTONE: "soft launch July 28" is DEAD** (and the older "July 21" is DEAD twice over). **REPLACED BY:** August 4, 2026. **SUPERSEDES:** the `Launch = July 28.` line at the end of the Session 118 CLOSE block below (corrected in place today), the Session 118 header's "SOFT LAUNCH SLIPPED July 21 → July 28", and `LAUNCH_READINESS.md`'s former "(to July 21)" sequence heading. Do not sequence, count weeks, or plan a go/no-go against July 21 or July 28.

- **What did NOT change:** no gate flipped, no work was re-scoped, no technical status moved. Engineering state is exactly as the Session 118 CLOSE block below records it (capture pipeline LIVE on `bbe5353`; Gate 0 CLOSED; incident closed on Standard 2GB). This entry is a **date-only** amendment.
- **What this does change (schedule shape):** +1 week of runway to soft launch, but **GalaxyCon Aug 21–23 does not move** → the soft-launch→booth buffer shrinks from ~3.5 weeks to ~2.5 weeks. The schedule-sensitive items are therefore **Section F (mobile pass + F-load/F-L4 burst on the 2GB box)** and the eBay/valuation corpus follow-ups (media-junk normalizer filter + 011 audit, ~118 poster candidates, JSON-reader eval) — they now sit closer to the booth with less slack behind them.
- **Unchanged deadlines:** GalaxyCon Aug 21–23 (immovable); ⏰ 90-day image purge hard deadline ~2026-09-17.
- ⚠️ **Stale-date artifacts NOT updated by this change (Mike's call whether to sweep them; they never received the July 28 move either and still read July 21):** `docs/SW_BO_PRIMER.md:44,71`; `docs/sessions/GALAXYCON_SPRINT.md:12,25,28,33,73,96` (incl. the W6 "Jul 15–21" row and the ~250-hours-before-July-21 budget); `docs/sessions/ROADMAP.txt:53,74`; `docs/technical/R2_CUTOVER_RUNBOOK.md:5`; and line ~485 of THIS file (90-day-purge note, "After soft launch (Jul 21)"). Every "July 21" / "July 28" in those files is DEAD — read them against **August 4**.
- **Files updated today:** `docs/LAUNCH_READINESS.md` (target line + Rule-5 header + sequence heading) and this file. No code touched, nothing to deploy.

---

## Session 118 CLOSE (Jul 16, ~20:45 UTC) — ✅ INCIDENT CLOSED: instance upgraded Starter→Standard 2GB (plan_changed 20:07:05Z, Mike) → 🎯 GATE 0 CLOSED: two consecutive real-iPhone HEIC grades fully successful (Heroes for Hope Special #1 + Iron Man #200 — correct title/publisher/year, full breakdowns, honest "Limited/Rough Estimate" on thin comps); memory 322–447MB vs 2048MB (~22% peak), zero failures since 19:43

**MOST RECENT CHANGE (2026-07-16 close, Rule 5): 2GB upgrade LIVE + Gate 0 DONE + both fix units (37d5e97 monitor / 65ffba1 memory) confirmed working under REAL conditions. ⚰️ TOMBSTONE: the addendum below's "testing ON HOLD / idle 441MB one extract from death" state is DEAD — resolved by the plan change. Day's verdict (Mike): the "same input failing differently every time" pattern was resource starvation all along — base drift toward the 512MB ceiling crossing on grade/extract cycles — not a code bug; new headroom removes the failure mode entirely. Five OOMs today, all explained, none remaining.**
- **Stale-spec cleanups for next touches (not urgent):** CLAUDE.md monitored-services line + Dockerfile sizing comment still say "Starter 512MB" → now Standard 2GB (2f thresholds are %-of-cgroup so they scaled automatically); the single-decode extract refactor (normalize + scan_barcode share one decode) downgraded from emergency to nice-to-have efficiency work.
- **NEXT session order:** (1) ~~docs commit~~ DONE (`d747bc9`/`e17c9f3` + `9db1e74` 2f env override, all shipped+verified same evening); (2) **eBay collector fix — SPEC RECEIVED + APPLIED IN TREE (2026-07-16 late), awaiting Mike's live test:** `content.js` +38/−9 — container `[data-listingid]` (li.s-card dead, kept as fallback), `ebay_item_id` from `dataset.listingid` gated by `/^\d{9,15}$/` (DB dedup key verified = `ON CONFLICT (ebay_item_id)`, sales_ebay.py:140 — URL-shape change CANNOT duplicate corpus rows; numeric gate protects the conflict path), title priority REVERSED to `a[class*="item-card__title"]` text with generic-img alt fallback (old primary was img.s-card__image alt — junk-alt risk flagged), price/date innerText regexes untouched, getPageInfo loosened fallbacks (display-only, capture-safety rule intact — zero pagination behavior). node --check clean. **🆕 SECOND collector bug found by Mike's live test (2026-07-16 late): selector fix verified working, but banner captured 12 of 287 DOM items — the ~2026-07 restructure also changed the RENDERING MODEL: items lazy-hydrate as [data-listingid] shells (content fills in as the human scrolls), and the extension's scan was SINGLE-SHOT at T+1.5s (no observer/interval/rescan — confirmed; no visibility filtering anywhere — Mike's hypothesis B ruled out). Old markup was server-rendered, so single-shot used to catch ~240. FIX APPLIED IN TREE (+113/−12 total): debounced (800ms) MutationObserver re-runs the pure-DOM scan as content hydrates, syncs only ids not yet captured this page (session Set + chrome.storage + server ON CONFLICT = triple dedup), silent no-op passes (banner can't self-trigger), cumulative banner "N synced this page — watching as you scroll", observer disconnects on pagehide. CAPTURE-SAFETY INVARIANT documented in-code: zero requests to eBay, zero synthetic scroll/navigation, pagination stays human. Title provenance confirmed for the 'fewer matching words' section: ALL extraction is item-scoped (no search-context defaulting; missing title ⇒ row dropped, never inherited).** **⚰️ CORRECTION (same night, Mike's diagnostic run): the hydration/observer theory was WRONG — all 279 items had title+price at load, observer fired fine (122×). TRUE root cause: `parseListingItem`'s `includes('Sold')` guard is case-SENSITIVE and the new markup uppercases the sold badge via CSS text-transform (innerText is rendering-aware) → 267/279 legitimate items rejected. SAME-BUG COROLLARY: the date parser's month lookup missed uppercase 'JUL' → silently stamped TODAY's date (corpus-freshness poison; dormant pre-restructure). BOTH FIXED in tree (`/sold/i` guard + month-key case normalization). Scrolling was never needed — full capture at load; the auto-scroll question is MOOT (Mike's Network-tab evaluation + DF risk-flag exchange preserved in chat 2026-07-16; never built). Observer kept as cheap insurance (silent no-op). 🆕 EMBEDDED-JSON READER under evaluation as PRIMARY capture (Mike's directive): probe found 40/40 sampled item ids in page script tags with title/price-shaped keys (1.28MB script text) — awaiting a saved sample HTML from Mike to build/verify offline; design = JSON-first with fixed DOM parser as automatic fallback; decisive unknowns = per-item sold date in the blob, section/sponsored flagging, key stability. TEMP [SW-DIAG] instrumentation still in content.js — STRIP BEFORE COMMIT.** **✅ ALL LIVE TESTS PASSED (2026-07-16 night): 203 net-new rows synced 22:39–23:42Z with REAL varied sale_dates (Jul 8–16 — date fix proven in prod data); 'fewer words' provenance spot-check PASSED (item 377346126386, Absolute Batman #1 Dragotta $220 sold 7/15, title = the listing's own); [SW-DIAG] STRIPPED; final collector diff +134/−15, node --check clean. CAPTURE PIPELINE LIVE AGAIN — PUSHED (`bbe5353` collector + `d4cf397` docs, session close). Poster cleanup COMMITTED to prod + verified (4 rows is_lot=true, single marker after a double-run dup was cleaned; AB#1 raw pool = 0 poster rows). JSON-reader sample landed at `tests/ebay_srp_sample.html` (gitignored — 4MB personal-search snapshot). Session-close backlog (Mike, none urgent): ~118 corpus-wide poster candidates (DF sends eyeball list next time); media-junk normalizer filter (next normalizer touch + 011 audit); NL-query-tool schema grounding (wrong table TWICE incl. on pasted literal SQL — fix before a real false alarm); JSON reader build vs the sample; Signature ID accuracy deferred until reference-DB buildout. Post-verification data-quality actions same night: banner now reports SERVER-inserted count (was pre-dedup local: 265 vs 203); 🆕 poster/print junk passes ALL normalizer flags (4 rows in AB#1's raw pool incl. $150/$270 screen prints — manual is_lot=true SQL handed to Mike for those 4; corpus-wide ~122 candidates; real media-junk filter = next normalizer touch WITH the L-SW-2026-011 corpus audit, logged in LAUNCH_READINESS — naive 'poster' regex would nuke legit 'polybagged with poster' comps); 🆕 admin NL-query tool logged as backlog (rewrote even pasted literal SQL to market_sales; confident false zero vs 7,389 real rows). JSON-reader evaluation still open (probe 40/40 — awaiting Mike's saved sample HTML; design = JSON-first, DOM fallback); (3) Section F: Pixel walkthrough + broader mobile pass; (4) F-load + F-L4 burst on the 2GB box. ⚰️ ~~Launch = July 28.~~ **DEAD — Launch = AUGUST 4, 2026** (Mike, 2026-07-29, availability; see the 2026-07-29 block at the top of this file).

## Session 118 addendum (Jul 16, ~20:00 UTC) — 5th OOM, ON THE FIXED BUILD (`eb89454` live 19:31, kill 19:43:40, bftpt): SAME class, new arithmetic — 12MP extract (deliberately uncapped at EXTRACT=4096 for barcode parity) ≈ +150MB, fired from a BASE that had DRIFTED to ~405MB (RSS retention per grade cycle). Post-restart the same flow succeeded from a fresh base (293→441 retained, flat = the current live level, ~71MB headroom). Evidence: caps PROVEN live (submission #15 photos stored at exactly 1500×2000 = GRADING_MAX_LONG_EDGE active; storm dead = monitor unit live; checkout eb89454 logged), api_usage gap 19:41:18→19:44:38 = killed request was the book-3 extract, retried successfully at 19:44:29; all traffic user 3 (Mike). Mike's 19:48 Heroes-for-Hope failure: ZERO backend trace (no log, no api_usage row) = never reached the app (client/edge during churn). CONCLUSION: on 512MB there is no code path that keeps full-res 12MP barcode scanning + 2-worker concurrency + headroom — the remaining calls are (a) instance 2GB (DF strong rec), (b) single-decode extract refactor (normalize+barcode share ONE decode — kills the double-decode waste, would roughly halve extract peak) and/or extract cap ↓2000, (c) 1×12 fallback (anti-booth, not recommended). MALLOC_ARENA_MAX/max-requests runtime confirmation needs Mike's Render shell: `printenv MALLOC_ARENA_MAX; ps aux | grep max-requests`. ⚠️ LIVE STATE: idle 441MB — one 12MP extract from a kill; ALL grading/extract testing on hold (Mike) until the instance decision.

## Session 118 (Jul 16, 2026) — OOM incident FULLY ROOT-CAUSED (3× oomKilled incl. ONE ON THE ROLLBACK BUILD): full-resolution uploads through the image-decode pipelines vs the 512MB instance — NOT the HEIC unit alone, NOT DB connectivity, NOT item 2(d); two fix units BUILT+VERIFIED IN TREE (memory 22/22, monitor-storm 10/10), BOTH ON HOLD per Mike pending his review; 🗓️ SOFT LAUNCH SLIPPED July 21 → July 28 (Mike, 2026-07-16) — ⚰️ **that July 28 date is now DEAD; current target = AUGUST 4, 2026 (Mike, 2026-07-29, availability)**

**MOST RECENT CHANGE (2026-07-16 ~19:15 UTC, Rule 5): ⚠️ ACCIDENTAL REDEPLOY OF `d2e525d` + Unit-1 hardening round + 🆕 HEIC MEMORY FLOOR FOUND.** (1) Mike ran the Unit-2 ship block with its placeholder `git add [monitor storm fix files]` line intact → NOTHING was committed (HEAD still `d2e525d`, dependency_monitor.py still dirty) but the `deploy` step ran → **prod is back on `d2e525d` (live 18:48:26Z) — the rollback is UNDONE, the monitor fix is NOT deployed, email storm re-seeded on the fresh boot** (~11 emails by 18:51). Prod is stable under normal client-resized traffic; raw-HEIC standdown (already agreed) is the operative protection. Exit path = ship the units (any push-deploy carries `d2e525d` anyway since it's on main). (2) Unit 1 hardened twice more by its own suite, now **25/25** incl. Mike's requested **24MP raw-HEIC fixture** (subprocess-isolated — local libheif hard-crashes in-process) and 12MP barcode-parity check: fix #1 = thumbnail-BEFORE-exif-transpose (don't copy the full bitmap to rotate it); fix #2 = the finding: **(3) 🆕 raw 24MP HEIC has a ~198MB intrinsic decode floor (libheif double-buffers: C frame + PIL copy) — code CANNOT make this input class safe on the 512MB Starter (330 base + 198 ≈ 528). Safe requires either the 2GB tier or an over-size reject policy.** Suite records it as a <230MB regression guard + loud NOTE. Ship order (Mike): Unit 2 first (corrected block handed in chat — `git add dependency_monitor.py`), Unit 1 after his diff review (diffs delivered). Client-side 2048px resize for the extract upload path QUEUED (LAUNCH_READINESS post-launch, defense-in-depth). Health Check Path re-enabled by Mike (was briefly off during his investigation). *Prior same evening:*
ROOT CAUSE UNIFIED + 2(d) HYPOTHESIS TESTED AND CLEARED. Render events (authoritative): exactly THREE `server_failed` events in recent history, ALL today, ALL `oomKilled (512Mi)` — 17:28:10 + 17:34:11 (96ngc, `d2e525d`) and 18:00:52 (qtq2g, `1437fdb` ROLLBACK build, 9 min after rollback went live). ⚰️ TOMBSTONE: this entry's earlier framing "regression from the HEIC ship / rollback restores stability" is DEAD — the vulnerability predates `d2e525d` and killed the rollback build too. ⚰️ ALSO DEAD: "DB-connectivity escalation" as a theory — Postgres healthy all day (111MB/256MB flat, CPU ~1%, active connections min 0/max 5 vs 103), exactly ONE SSL-abort blip (17:23:04, monitor + request failed the same second = external transient, never recurred).**

**The unified mechanism (measured, not theorized):** the grading frontend client-resizes to ≤2048px (`js/grading.js:1313` MAX_IMAGE_DIM) — which is why every grade that COMPLETED today was harmless (retained photos = 1204×1600). But any path that ships FULL-RESOLUTION bytes server-side — raw HEIC library picks (Chrome can't canvas-decode HEIC → falls through at camera resolution; 24MP = current iPhone default), or any client that skips the resize — hits decode transients measured at **+187 to +310MB for ONE request** through `/api/extract` (normalize full-res + `scan_barcode` decoding the output AGAIN with up to 4 rotations). From the ~330MB service baseline that exceeds 512MB → `oomKilled`. Mike was actively testing with real iPhone photos (Gate 0 verification = the exact raw-HEIC class) when all three kills happened. `d2e525d` widened the hole (4 server-side decodes per grade); it did not create it.

**Item 2(d)/healthCheckPath hypothesis — CLEARED on all four checks (Mike's ask):** (1) Render polls /health ~every 5s (observed via storm-email cadence) — but polling started 2026-07-12, and `1437fdb` ran under it ~90 hours with ZERO failures before today (events list: no server_failed before 17:28 today); (2) the SELECT 1 conn close is in `finally` with the outer except covering checkout failure (`routes/utils.py:57`) — no leak path, matches the 2(d) suite's close-on-exception test; (3) Postgres active connections FLAT (2–5) all day through all three kills and the heaviest polling — a leak would climb toward 103; zero `POOL EXHAUSTED`/`too many clients` in the full day's logs; (4) the SSL-abort was a single 17:23:04 event under 24/7 polling → unrelated to poll frequency. **healthCheckPath revert NOT recommended — it's real protection and not implicated.**

**📧 EMAIL STORM root-caused + fix unit BUILT (unit 2, offline 10/10, scratchpad `test_monitor_flap.py`):** three compounding monitor defects — (a) `check_ebay_account_deletion._fail` cached FAILURES for the full 24h TTL (other checks back off 5 min): one 502 caught during a deploy-swap/OOM window poisoned a worker's view until process death; (b) per-worker check caches × shared prune-on-every-call dedup = the clean worker prunes the key, the poisoned worker re-inserts + re-EMAILS, alternating at poll cadence (~1 email/5–15s, observed live: `dependency_alerts` row deleted/re-inserted on a ~30s cycle) — self-sustaining, survives rollbacks (state-driven, not code-version-driven); (c) the Resend send ran SYNCHRONOUSLY inside /health. Fixes in tree (`dependency_monitor.py`): failure backoff 5 min; prune only after 15 min continuous absence (last_seen_at refresh + windowed DELETE); `_send_alert_email_async` (daemon thread, skip-if-busy) so /health never carries email latency. ⚠️ Storm is ACTIVE in prod until this ships — Mike's inbox fills at ~4/min during divergence windows.

**Memory-fix unit (unit 1) EXTENDED + re-verified 22/22 (`tests/test_memory_fix.py`, committed copy):** everything from the first build (GRADING_MAX_LONG_EDGE=2000, IMAGE_DECODE_CONCURRENCY=2 gate, MALLOC_ARENA_MAX=2, gunicorn --max-requests 500/jitter 100) PLUS `EXTRACT_MAX_LONG_EDGE=4096` on the extract path (12MP/4032px passes UNTOUCHED = barcode parity for all typical uploads; over-cap sources use a NEW half-decode draft rule — the aspect-box draft silently decoded 24MP at full res, +219MB, caught by the 24MP test) — measured: 24MP extract pipeline +187MB uncapped → **+73MB capped**; JPEG 4-photo grade 95→33MB; 8-way burst 152MB. ⚰️ The "extract deliberately uncapped" decision from unit 1's first draft is DEAD — the 18:00:52 kill WAS the extract path.

**HOLD STATE (Mike, 2026-07-16): both units held pending Mike's review of this evidence — nothing ships. Soft launch slipped one week → July 28 *(⚰️ superseded 2026-07-29 → **August 4, 2026**)*. Prod meanwhile: `1437fdb` live, stable under normal (client-resized) traffic, VULNERABLE to any full-res upload (avoid raw-HEIC/Files-app upload tests until unit 1 ships); email storm active until unit 2 ships. Residual risk noted for review: two simultaneous full-res decodes on DIFFERENT workers can still stack (~2×73MB) — F-L4 will characterize; a Starter→2GB instance upgrade would retire the entire class (Mike's call, cost item).**

**Memory-fix unit (in tree, files: `comic_extraction.py`, `routes/grading.py`, `Dockerfile`, `docs/technical/ARCHITECTURE.txt`):**
- **`GRADING_MAX_LONG_EDGE` (env, default 2000px)** — long-edge cap applied ONLY at the two grading call sites (`/api/grade` 4-photo loop + `/api/messages`); `/api/extract` deliberately uncapped because `scan_barcode` reads the normalizer's output. 2000 > the ~1568px Anthropic downscales to (no model-visible loss) and ≤ half of 4032px, so the aspect-correct libjpeg **draft-mode** decode runs at 1/2 scale — the full 36MB bitmap never exists. ⚠️ First draft had a silent no-op bug (square draft box never triggers on non-square photos) — **caught ONLY by the 12MP peak-RSS test**; that test class is now permanent practice (L-SW-2026-012).
- **`IMAGE_DECODE_CONCURRENCY` (env, default 2)** — semaphore in comic_extraction bounding concurrent decodes per worker (HEIC has no reduced-scale decode; 8 gthread threads × ~40-100MB transients was the F-L4-burst risk). DF ADDITION beyond Mike's approved list — flag in review.
- **`MALLOC_ARENA_MAX=2`** (Dockerfile ENV) — the RSS-ratchet fix (glibc arena fragmentation retained +25–83MB/grade; not testable on Windows, verify via prod memory metrics post-deploy).
- **gunicorn `--max-requests 500 --max-requests-jitter 100`** — staggered graceful worker recycling as residual-creep backstop.
- **Measured (offline suite, photo-realistic 12MP fixtures):** JPEG-only 4-photo peak 95→33MB; realistic mixed grade (3 JPEG+1 HEIC) +83MB transient/+1MB retained; 8-way concurrent burst gated to +149MB (~2-deep). Suite: scratchpad `test_memory_fix.py` (17/17) — correctness (cap/orientation/HEIC/centerfold/garbage/data-URL), uncapped-path-unchanged (barcode compat), 3 peak-RSS classes.
- **Docs in tree with it:** ARCHITECTURE (Dockerfile block trued up — it still showed the pre-Phase-4 CMD — + new memory-tuning env table), LESSONS **L-SW-2026-012** (peak-memory budget check + realistic-fixture rule; cross-project candidate), LAUNCH_READINESS Rule-5 header + **flap-dampening** logged as post-launch item (Mike: small future task, not urgent).

**Incident diagnosis (read-only, evidence-complete — detail in LAUNCH_READINESS Rule-5 header):**

- **🔴 THE REGRESSION — OOM cycling under normal grading load.** `normalize_for_photo_type` now runs on EVERY /api/grade photo at FULL resolution (no downscale anywhere in `normalize_orientation_b64`): 12MP decode + exif_transpose copy + RGB convert + q92 JPEG re-encode + base64, ×4 photos, on top of the request payload copies. Render memory metrics: fresh boot ~320MB → grade #11 (4 img) → 351MB retained → next grade in flight → **466MB → OOM KILL 17:28:10** (no graceful-shutdown lines = SIGKILL) → reboot 319MB → grade #12 (3 img) → 403MB retained → **490MB → OOM KILL 17:34:25**. RSS never returns after a grade (glibc arena fragmentation; 8 gthread threads, no `MALLOC_ARENA_MAX` in Dockerfile). Every kill drops all in-flight requests ("Failed to fetch" for those users). Idle = stable; each grade from the elevated base risks the ceiling. This is the booth-killer shape again — F-load CANNOT run on this build.
- **Mike's two reported failures explained (NEITHER is an exception in the new normalization code — no normalize/HEIC exceptions anywhere in the window):** (1) "Failed to fetch" on Generate Slab Report = in-flight request killed — candidate windows both confirmed as kills: the deploy swap (old container SIGTERM 17:17:20) or the 17:28:10 OOM; (2) "Could not identify comic automatically" = /api/extract 500 at 17:23:04 — **transient DB unreachability** (pool pre-ping correctly discarded a severed parked conn; the retry's FRESH `psycopg2.connect` to Render Postgres failed with the same `SSL SYSCALL ... connection abort`; DependencyMonitor failed simultaneously = external blip, ~1s, self-healed). Pool behaved as designed ("a second failure propagates — that's real").
- **What WORKED live:** grades that completed were correct + retained — submissions #11 (17:23:47, 4 images, 8.5) and #12 (17:30:29, 3 images, 8.0), both user_id 3 (Mike). HEIC decode itself: no errors.
- **📧 EMAIL STORM (side-finding):** ~15 dependency-alert emails 17:28:27–17:31:56 = the eBay account-deletion SELF-CHECK getting 502 from its own dying/rebooting service, amplified by `_send_alert_email`'s prune-then-realert dedup (a flapping warning re-emails on every warn→clear→warn cycle). Symptom of the OOM cycling, but the dedup wants flap-dampening as its own small item. DB `dependency_alerts` row confirms: `GET challenge-response` 502, first_alerted 17:34:37.
- ⚰️ *(superseded same session — decision block resolved as option (A), see MOST RECENT CHANGE above; the fix sketch became the built unit described there.)*
- **NEXT session order:** (1) Mike reviews + ships the memory-fix unit (block in MOST RECENT CHANGE context above / handed in chat) → post-deploy: `/health` ok, `runtime.heif=true`, one JPEG grade, THEN watch Render memory across 2-3 real grades (return-to-baseline is the thing to verify — L-SW-2026-012); (2) real-iPhone HEIC grade = Gate 0; (3) eBay collector fix spec (still owed as its own message — capture pipeline still DOWN); (4) F-mobile/F-load per checklist. Docs commit for SECTION_F_CHECKLIST.md etc. also still pending (block re-handed in chat 2026-07-16).

---

# (prior header) Where We Left Off - Jul 12, 2026

## Session 117 (Jul 12, 2026) — 2(d) SHIPPED `1437fdb` + VERIFIED + healthCheckPath SET (Render native health monitoring live for the first time); Section F opened (checklist + HEIC gate); HEIC/orientation fix BUILT IN TREE = first ship next session; 🆕 eBay collector selector rot diagnosed

**MOST RECENT CHANGE (2026-07-12 close, Rule 5): item 2(d) SHIPPED `1437fdb` + VERIFIED IN PROD (Mike ran commit/deploy; post-deploy checks passed: /health minimal body confirmed, Render Events clean, no crash loop) AND Mike set Render dashboard Health Check Path = /health — Render's native health monitoring (deploy gating + unhealthy detection) is live for the FIRST time. ⚰️ TOMBSTONE: this entry's earlier "2(d) drafted/approved awaiting ship" framings are DEAD — the commit exists at HEAD; do NOT re-present the 2(d) command block. ITEM 2 IS CLOSED except (c) Sentry, which Mike has designated NON-BLOCKING / POST-LAUNCH. NEXT SHIP (first thing next session) = the HEIC/orientation unit, in tree, offline 17/17, NOT committed.**

**🆕 NEW FINDING (Mike, 2026-07-12 night, live DOM inspection — formal fix spec arrives as its own message next session, do NOT draft ahead of it): eBay sales-capture extension is BROKEN by an eBay search-results markup restructure.** `collectSales()` in `CCExtensions/ebay-collector/content.js` selects `li.s-card`, which no longer exists (console-confirmed: `.srp-results`, `li.s-item`, `li.s-card` all return 0). New structure found live: item container = `div.su-item-card` carrying a **`data-listingid` attribute directly** (more robust than the old href-regex approach); title link = `a[class*="item-card__title"]`. Impact: the valuation-corpus capture pipeline is down until the selector fix ships. Capture-safety rules unchanged ([[feedback_ebay_capture_safety]] — human-triggered/paced, no auto-pagination).

**✅ WORKTREE/DIRTY-FILES QUESTION ANSWERED (read-only, 2026-07-12 close): nothing happened tonight — all of it is OLD, pre-existing, and SAFE to leave untouched.** (1) The ~500 `.claude/worktrees/zen-wozniak/*` "deleted" entries: those files were accidentally COMMITTED into the repo on **2026-03-19 (`61290bf`, a git add -A sweep — the exact footgun CLAUDE.md's GIT COMMIT RULE was later written against)**; the zen-wozniak worktree has since been removed from disk and from `git worktree list`, so the tracked copies read as deleted. They've shown in git status since at least Session 116 (recorded there as pre-existing dirt). (2) `TODO.md` modification = legitimate Session-109-era updates (dated Jun 22–23 in the diff: stacking steps 1–3, grading-accuracy item) never committed; `scripts/slabguard_crosscamera_test.py` (+5/−1) and `tests/SlabGuardTests/TP_RESHOOT_PROTOCOL.md` (+59) = S110/111-era SlabGuard-arc edits, also never committed. **Safe as-is:** everything is unstaged; deploys are unaffected (`.dockerignore` excludes `.claude/` since `820b0ae`); the only risk is a blind `git add -A`/`git add .` sweeping them into an unrelated commit — which the standing commit rule already guards. **Cleanup (joint, some future session, Mike runs):** one commit that removes `.claude/worktrees/` from tracking (`git rm -r --cached`) + adds it to `.gitignore` (also fixes the perpetually-modified `elegant-swirles/settings.local.json`), plus decide keep-vs-commit on the TODO/SlabGuard edits. ⚠️ Note: `61290bf` put business files (P&L spreadsheets, roadmap PDF, lock files) into git history — repo is private, history rewrite = optional post-launch hygiene, not urgent.

**Earlier today (PM): Mike's three calls — (1) HEIC = FIX (not waive; "really an orientation-normalization fix with HEIC as a side effect") → BUILT IN TREE same day, offline 17/17; (2) 2(d) approved → since SHIPPED (see header); (3) load target APPROVED + F-L4 ceiling burst added (16–18 concurrent vs the 16 thread slots — find the ceiling, not the floor); checklist canonical in repo, Mike keeps a supplementary personal phone run-sheet (no merge).**

- **🆕 HEIC/orientation fix BUILT (2026-07-12 PM), offline 17/17:** `requirements.txt` +`pillow-heif>=0.16.0`; `comic_extraction.py` registers the HEIF opener beside the PIL import (`HEIF_SUPPORTED` flag; graceful degrade with a loud boot print if the package is missing); `routes/grading.py` api_grade now normalizes EVERY photo via `normalize_for_photo_type` BEFORE the quality gate/moderation/API/retention (label→photo_type: 'Front Cover'→front, 'Spine'→spine, 'Back Cover'→back, 'Centerfold'→centerfold/landscape-allowed; media_type forced to image/jpeg) — undecodable photo fails LOUD with the existing quality-gate error shape naming the photo (deliberate deviation from /api/messages' send-original fallback: forwarding unreadable bytes would just resurface as an opaque Anthropic 400; frontend already renders quality_fail, zero frontend changes); `routes/admin_routes.py` adds `runtime.heif`; ARCHITECTURE.txt documented. **Side benefits verified in suite:** Rekognition moderation + quality gate now operate on HEIC uploads (both previously fail-open/blind on them); retention persists upright JPEG. Suite (scratchpad `test_heic_grade_normalize.py`, real comic_extraction + real route with stubbed auth/models/db/engine/retention): unit HEIC→portrait-JPEG per photo type; route 3×HEIC grade end-to-end (all blocks image/jpeg, front/spine portrait + centerfold landscape); upright JPEG untouched; spoofed heic media_type on JPEG bytes handled; garbage → 400 quality_fail naming Front Cover AND naming Spine when it's photo #2; label-less default portrait. **pillow-heif 1.4.0 verified against local Pillow 12.0.0** (Docker installs its own via requirements; manylinux wheels bundle libheif — no Dockerfile change needed). Post-deploy checks: `runtime.heif=true` on admin dependency-status; one normal JPEG grade (no regression); real-iPhone HEIC grade = checklist Gate 0 boxes.
- **(superseded framing from earlier today, kept for the audit trail):** item 2(d) `/health` DB check DRAFTED IN TREE (offline 17/17), NOT shipped — awaiting Mike's review/commit/deploy + the dashboard half (set Render `healthCheckPath=/health`; dashboard setting, NOT the stale root `render.yaml`). Now APPROVED per the PM header above.

- **1) HEIC/HEIF question ANSWERED (read-only trace): NO — the pipeline cannot decode HEIC anywhere.** No `pillow-heif` in requirements; frontend sends raw bytes (`FileReader.readAsDataURL`, no canvas re-encode) with `image/heic` media type; `/api/extract` dead-ends at the front photo (PIL raises inside `normalize_orientation_b64` → "Image could not be processed" — doesn't mention HEIC, reads as broken app); `/api/grade` forwards `media_type: image/heic` verbatim to the Anthropic API (accepts JPEG/PNG/GIF/WebP only → 400 → generic 500); quality gate fails OPEN on undecodable bytes; moderation = Rekognition (JPEG/PNG only). iPhone users survive today only where iOS silently transcodes (camera-capture inputs = JPEG; library picks usually transcoded; **Files-app picks = raw HEIC = guaranteed dead-end**; the multi-photo input's `accept=".heic"` invites raw HEIC). **🆕 ADJACENT FINDING: `/api/grade` runs NO orientation normalization at all** — the normalizer was wired into `/api/messages` + `/api/extract` only; the structured grading endpoint ships raw client bytes (sideways spine/back photos go to the model sideways). **Recommended one-unit fix (drafted as SECTION_F_CHECKLIST Gate 0, NOT built, decision pending):** add `pillow-heif` (register opener beside the PIL import in `comic_extraction.py`) + route `/api/grade` images through `normalize_for_photo_type` — kills the HEIC hole and the orientation hole together (normalizer always emits upright JPEG).
- **2) Item 2(d) DRAFTED IN TREE (`routes/utils.py`):** `SELECT 1` on the shared pool inside `health()`; DB failure → 503 `{status:'degraded', version}`, body stays minimal (failure detail to logs only, L-SW-2026-007), `check_all()` still can never fail the probe, conn closed in `finally`, root `/` rides the same probe. **Offline suite 17/17** (scratchpad, stubbed db/monitor/auth: happy path exact-body, checkout-fail, execute-fail-with-close-proof, monitor-explodes-still-200, root path both ways) + py_compile clean. **render.yaml deliberately NOT touched** (stale Blueprint — adding healthCheckPath there would be inert now and a trap on future Blueprint attach). Item 2 remaining after (d) ships: **(c) Sentry only.**
- **3) Section F checklist CREATED: `docs/SECTION_F_CHECKLIST.md`** (Gate 0 HEIC; real-device matrix min iPhone/Safari + Android/Chrome; mobile flows F-M1–M5 incl. camera vs library paths, DELETE mis-tap check, billing-on-mobile throwaway-account rule, PWA; load F-L1–L3 with booth-shaped target 10 concurrent / 3 grading / 10 min, memory <85%, 0 POOL EXHAUSTED; exit criteria). Results get recorded IN that file; status rolls up to LAUNCH_READINESS (F row + sequence item 4 + Rule-5 header updated this session).
- **Git truth (2026-07-12 close, verified):** HEAD = **`1437fdb`** (2(d) shipped; `routes/utils.py` clean). Dirty (this arc): **HEIC unit** = `requirements.txt`, `comic_extraction.py`, `routes/grading.py`, `routes/admin_routes.py`, `docs/technical/ARCHITECTURE.txt`; **docs** = `docs/SECTION_F_CHECKLIST.md` (new), `docs/LAUNCH_READINESS.md`, this file. Pre-existing dirt (NOT this arc, do not bundle — mechanism now explained in the worktree block above): `.claude/worktrees/*` (~500 zen-wozniak deletions + elegant-swirles settings mod), `TODO.md`, `scripts/slabguard_crosscamera_test.py`, `tests/SlabGuardTests/TP_RESHOOT_PROTOCOL.md`.
- **Ship block for NEXT session (Mike runs; ⚰️ the 2(d) commit that was here is DEAD — executed as `1437fdb`, do not re-run):**
  ```powershell
  git add requirements.txt comic_extraction.py routes/grading.py routes/admin_routes.py docs/technical/ARCHITECTURE.txt
  git commit -m "fix(grading): normalize every /api/grade photo before gates/API/retention (orientation + HEIC via pillow-heif) — Section F Gate 0; undecodable photo fails loud naming it; runtime.heif flag on admin dependency-status (offline 17/17)"
  git add docs/SECTION_F_CHECKLIST.md docs/LAUNCH_READINESS.md docs/sessions/WHERE_WE_LEFT_OFF.md
  git commit -m "docs(readiness): 2(d) shipped+verified (1437fdb, healthCheckPath set — native monitoring live); Section F canonical checklist (Gate 0 HEIC fix built; 16-18 ceiling burst); eBay collector selector rot diagnosed; worktree dirt explained"
  git push
  deploy
  # AFTER deploy verified:
  #  1. curl https://collectioncalc-docker.onrender.com/health   -> {"status":"ok","version":"5.6.0"}
  #  2. admin dependency-status (admin JWT) -> runtime.heif = true
  #  3. one normal JPEG grade through the live app (no regression)
  ```
- **NEXT session order:** (1) HEIC unit ship block above + post-deploy checks; (2) Mike sends the eBay collector fix spec as its own message (selector migration to `div.su-item-card` / `data-listingid` / `a[class*="item-card__title"]`) → DF drafts against it — capture pipeline is DOWN until this ships; (3) real-iPhone HEIC grade = checklist Gate 0 boxes → F-mobile runs; (4) F-load per approved target + F-L4 ceiling burst; (5) 2(c) Sentry = non-blocking/post-launch (Mike's designation, 2026-07-12). **On Mike's plate (no DF queue impact): Section F checklist review, Pixel 7 walkthrough, borrowing an iPhone for HEIC/Section F testing.**

---

## Session 116 (Jul 11, 2026) — Item 2 CONCURRENCY CLUSTER (Phases 1–4) COMPLETE: Phases 3+4 SHIPPED + VERIFIED IN PROD same day; 2(f) resource self-alert DRAFTED in tree (own ship unit, awaiting review)

**MOST RECENT CHANGE (2026-07-11 PM, Rule 5): Phases 3 AND 4 SHIPPED (Mike ran both commits/deploys: Phase 3 `901a49e`, Phase 4 `820b0ae`) + VERIFIED IN PROD. Item 2's concurrency cluster (a)+(b)+(e) is CLOSED in LAUNCH_READINESS; the single-worker booth-killer is dead. NEXT = 2(f) resource self-alert (gate met, calibration numbers on file). ⚰️ TOMBSTONE: this entry's original framing — "drafted in working tree, NOT committed, awaiting review" — is DEAD; do NOT re-present the Phase 3/4 command blocks, both commits exist at HEAD.**

**Prod verification (2026-07-11, post-deploy, read-only):** Render live deploy = `820b0ae` (matches local HEAD); boot log `Using worker: gthread` + 2 workers (pids 7/8); **Mike's concurrency probe PASSED — 12× `/health` instant while an ASM #41 grade was in flight** (pre-fix: 10–30s queue); memory **357.8–358.0MB steady ≈ 70% of 512MB** (inside the 350–380MB estimate, 1×12 fallback not needed); logs: **0 `POOL EXHAUSTED`, 0 `[DB]` teardown lines** (server-side filtered search, control-validated); pg_stat_activity: **4 connections (1 active) vs max_connections=103**. Build context 4.9GB → ~450MB per the Phase-4 commit. **⚠️ 2(f) calibration note: WARN=80% placeholder (410MB) is only ~52MB above the new steady state — wants sustained-over-N-checks semantics or a higher line; decide at build.**

*(Original drafting record, superseded above but kept for the audit trail:)* Two separate ship units by design (Mike's call): Phase 3 (lower-risk plumbing) → commit/deploy/smoke alone; THEN Phase 4 (the behavior change: real concurrency) → commit/deploy → concurrency probe.

- **Phase 3 (in tree, offline-verified 27/27):** (a) `routes/billing.py` — explicit `try/finally conn.close()` on all 9 direct-connection sites (belt over the wsgi teardown net; behavior contracts preserved: get_user_plan fallback dict, entitlement fails closed, webhook handlers still swallow, check_feature_access still degrades to allow/Unknown). (b) `wsgi.py` — before_request admin check now reads the **signed JWT `is_admin` claim** (verified present, `auth.py:118`) instead of `get_user_by_id()` = one pooled DB checkout saved on EVERY authed request; `get_user_by_id` import dropped. Safety audit done: every ADMIN-AUTHORIZING route (`admin_routes`, `slabguard`, `feedback`) uses `@require_admin_auth`, which does its own fresh DB check + sets g.admin_id itself; before_request's g.admin_id only feeds soft surfaces (vision rate-limit/daily-cap bypass, lookup_demand `is_internal` tag) — staleness bound = 30-day token life (admin promoted/demoted mid-token sees old soft-flag behavior until re-login). Offline suite: stubbed pool, 27/27 — happy + exception paths, close-called-exactly-once each, JWT roundtrip carries is_admin.
- **Phase 4 (in tree):** `Dockerfile` CMD → `--workers 2 --threads 8 --worker-class gthread` (unchanged: `--timeout 300 --bind`), sizing comment in-file (512MB Starter, RSS ~173MB/worker, fallback 1×12); **`.dockerignore` NEW** — excludes .git (134MB), tests/ (783MB), ComicBookImages/ (100MB), .claude (1.9GB local), .env (secret vector), docs/, test-photo dirs, *.csv/*.db exports. Runtime-safety audit done before excluding: signature refs come from R2 at runtime (local `signatures/` KEPT anyway); fonts/json data/prompts/utils/migrations/HTML all KEPT; `comics_pricing.db` = offline scripts only (comic_lookup/scraper/database_setup, not imported by the web path).
- **Known accepted consequences of 2 workers (flagged, not bugs):** in-memory stores go per-worker → vision rate-limit/daily caps effectively ×2 (they were already per-process); gunicorn `--timeout` under gthread is a worker-liveness check, not a per-request killer → long grades safer, not riskier; DB ceiling 2 pools × 8 = 16 + overflow vs ~100 usable.
- **Verification plan (Phase 4, post-deploy):** (1) `/health` baseline; (2) **concurrency probe** — fire a real grade AND hammer `/health` in parallel (pre-fix: health queues 10–30s behind the grade; PASS = health answers <1s throughout the grade); (3) Render Metrics memory watch (~350–380MB expected; sustained >80% of 512MB → drop to 1×12 fallback); (4) logs clean of `POOL EXHAUSTED`/teardown lines; (5) re-run the 12-request connection probe.
- **Rollback levers:** Phase 4 = one-line CMD revert (restore the old CMD line, redeploy) — workers/threads carry NO data/schema coupling; Phase 3 = plumbing-only, teardown net still active underneath; pool kill switch `DB_POOL_DISABLED=1` unchanged.
- **Incidental findings (no action taken):** root `render.yaml` is STALE (`startCommand: gunicorn api_server_v3:app`, a dead entrypoint — Render ignores it for collectioncalc-docker, but a future Blueprint attach would resurrect it); billing's "→" arrows in print() crash cp1252 consoles locally (prod Linux/UTF-8 unaffected).
- **🆕 SAME DAY (2026-07-11 PM): 2(f) resource self-alert DRAFTED IN WORKING TREE (its gate met hours earlier), offline-verified 16/16, awaiting Mike's review as its own ship unit.** `check_resources()` in dependency_monitor.py: cgroup v2/v1 memory + `pg_stat_activity` vs (max_connections−3) + per-worker pool_stats, 5-min TTL, **sustained ×3 (~15 min) before warning**; calibration decided at build: WARN=85% mem / 70% DB (env-overridable) — instant-80% would have paged on GC spikes given the 70% steady state; rides the existing DB-persisted state-change email dedup (first worker to trip emails, others dedup); `resources` snapshot on `/api/admin/dependency-status`; resource lines filtered OFF public `/health`. MONITORING-ONLY (fallback 1×12 / tier upgrade = Mike's manual calls, stated in the alert text). Files: dependency_monitor.py, routes/utils.py, routes/admin_routes.py, CLAUDE.md (monitored-services line), docs/technical/ARCHITECTURE.txt (env vars). Post-deploy test: dependency-status shows the `resources` block.
- **🆕 LATER SAME DAY: 2(f) SHIPPED `bf92fcc` + VERIFIED IN PROD (all three of Mike's checks passed — live `resources` block via admin JWT: 63.4% mem / 2% DB / streaks 0; `/health` zero resource lines; dedup-prune + admin-auth + shared-pool code confirmations quoted from HEAD). ⚰️ The "drafted awaiting review" framing above is DEAD. ITEM 2(f) CLOSED.**
- **✅ FOLLOW-UP UNIT SHIPPED `9641a0a` + VERIFIED same evening (all three checks, Mike): chip live + healthy (358/512MB = 69.9% — back at the expected steady state after the fresh-container dip; DB 4%; pool 2/8), `/health` = exactly `{status, version}`, deploy clean.** ⚰️ The "drafted awaiting review" framing (which shipped inside `9641a0a`'s own docs) is DEAD. (i) admin.html resource status chip (amber ≥warn or streak >0; field names verified against live prod payload); (ii) public `/health` minimized — was exposing installed Stripe version, versions-behind count, internal monitoring notes; `check_all()` STILL runs inside it (no cron — health polling is the monitor's scheduler; state-change email fires inside check_all); detail + runtime flags (barcode/moderation) now admin-only on `/api/admin/dependency-status`. Offline suite was 6/6 incl. exception-never-leaks. ⚠️ Habit note: `curl /health` no longer lists dependency warnings.
- **Git truth (updated 2026-07-11 night):** HEAD = `9641a0a` (health-minimize + chip); beneath it `bf92fcc` (2f) / `3ce6e2d` (docs) / `820b0ae` (Phase 4) / `901a49e` (Phase 3) — the entire day's code is shipped. Dirty (this arc) = docs only (this file + `docs/LAUNCH_READINESS.md`, closure edits). Pre-existing dirt (NOT this arc, do not bundle): `.claude/worktrees/*` deletions/mods, `scripts/slabguard_crosscamera_test.py`, `tests/SlabGuardTests/TP_RESHOOT_PROTOCOL.md`. **Item 2 remaining: (c) Sentry, (d) `/health` DB check — the only open pieces; note (d) now also gates Render's `healthCheckPath` + native-notification value (see 2(f) entry).**

---

## Session 114 (Jul 9, 2026) — Item 2 Phase 1 (shared DB pool) SHIPPED + VERIFIED; pooling/gunicorn plan delivered; 2(f) resource-alert designed; NEW valuation finding: Cover-A variant misclassification (modern mispricing, systemic)

**⚠️ CURRENT STATE (2026-07-10 PM; Rule 5, read this FIRST): MOST RECENT CHANGE = eBay Issue 1 (compliance timeout) INVESTIGATED + CLOSED by Mike's portal check — BOTH eBay endpoint halves are now DONE; NEXT item 2 is fully closed and the eBay endpoint carries zero launch-blocking work.** Issue-1 findings (detail in LAUNCH_READINESS Dependency watch): suspension = 1000 CONSECUTIVE failures (no 200 within 3000ms), counter self-heals on any success → warm ~0.45s endpoint can't plausibly trip it; registered URL + verification token confirmed matching prod/Render; Data-Handling bulletin N/A (CN/RU/etc.-scoped); eBay's field reference independently confirms `username` as the deletion-notice identity field (validates the Issue-2 fix); keep-warm/monitor-timeout = optional nice-to-have now. OPEN MICRO-ITEM (Mike, 2-min): enable the portal "Notify Me" failure-alert email; nice-to-have: one-time confirm the dev account is US-registered. *Earlier same day:* eBay Issue-2 security fix SHIPPED (`060f1dc`, Mike ran commit/deploy) + VERIFIED IN PROD, all three checks passed. Evidence: (1) unsigned curl POST → 412 `{"error":"Signature required"}`; (2) eBay portal "Send Test Notification" ×multiple → every one verified successfully, INCLUDING across a mid-sequence eBay key rotation (`kid=3cf880e7…`→`9936261a…` — the unknown-kid→fresh `getPublicKey` fetch path proven live, not just the cache), each proceeding to identity lookup and correctly matching no user on eBay's synthetic test IDs; (3) GET challenge-response still 200/valid hash. The raw-body byte assumption is proven against genuinely eBay-signed messages, not just self-signed test keys. ⚰️ TOMBSTONE: this checkpoint's prior framing — "fix DRAFTED + OFFLINE-VERIFIED, UNCOMMITTED, awaiting Mike's review" — is DEAD; do NOT re-present the eBay-fix command block, the commit exists at HEAD (`060f1dc`). LAUNCH_READINESS updated same day (Rule-5 header + sequence-item-3 eBay bullet ✅ + Dependency-watch Issue-2 line). REMAINING (re-revised 2026-07-10 PM ×2 — normalizer fix COMMITTED `15cb459` + docs/lessons `2904fa7` [L-SW-2026-008/009/010 finally in history], DEPLOYED [new code confirmed in container: `_fuzzy_tokens_supported` grep=2, "Cover A"→is_variant=False], dry-run VERIFIED [computed variant 15,344 vs stored 18,044 = 2,700 flipping ≈ the audit's ~2,601 + rows captured since]; ⚰️ command blocks #2/#3 below are EXECUTED, do not re-run the commits): (1) ✅ **live re-normalize COMPLETE + VERIFIED (2026-07-10 late PM): 71,449/71,449 updated, 0 errors; stored `is_variant` = exactly 15,344; Defenders→Descender mis-merge = 0 rows; "Absolute Batman Annual" separated into its own canonical; end-to-end live-app check: AB#1 9.0 → raw FMV $169.99 (blended, real comps, verdict_reliable=true) vs pre-fix $150.00. Gap to ~$185–300 market = Layer 3, deferred to R1/R2 by prior decision. NOTE for future queries: `canonical_title` is stored TITLE-CASE ('Absolute Batman', not 'absolute batman'). ⚠️ CORRECTION to an earlier note: the ~1hr runtime was from the RENDER SHELL (likely internal DB URL), so my "external hostname" latency attribution was speculation — expect the re-run below to take ~1hr again;** (1b) **🆕 LEADING-"NEW" BUG FOUND during the market_sales dry-run (2026-07-10 late): `title_normalizer.py:314` has stripped a bare leading "new" as a condition prefix SINCE DAY ONE (`ac9b2be`), eating series names — New Mutants/New Teen Titans/New Warriors/New X-Men etc. Before `15cb459` the permissive fuzzy matcher silently repaired most of it; the per-token guard correctly refuses now, so the ebay re-normalize SURFACED it: 1,072 ebay rows carry New-less canonicals (635 'Mutants' incl. the #98 1st-Deadpool key; 210 New Teen Titans CONTAMINATING the real Teen Titans pool — that class was wrong since day one, not caused by the rewrite). FIX DRAFTED in tree (strip only 'brand new', keep bare 'New'; safe because condition-prefix listings still fuzzy-merge with all tokens supported): `title_normalizer.py` one-liner + comment, PLUS `normalize_batch.py` extended with `--table market` (maps normalized_issue_number, raw_title→title fallback, does NOT write is_facsimile/is_reprint = barcode-derived on market_sales). OFFLINE-VERIFIED: 9/9 targeted cases; full-corpus diff fixed-vs-shipped over all 71,449 ebay rows = exactly 1,063 rows change, 0 variant flips. ✅ **SHIPPED + BOTH TABLES RUN + VERIFIED same night (2026-07-10): Mike committed/deployed, ebay re-run 71,449 + market 9,963, 0 errors; post-run exact ('New Mutants' 963 / 'Mutants' orphans 0 / Teen-Titans contamination 0 / is_variant 15,344 ebay + 221 market / Monstress clean); live app: New Mutants #98 @9.0 → $300 raw, exact, high confidence, 10 comps; AB#1 unchanged $169.99. NORMALIZATION LOOP CLOSED. Residual tail (post-launch, logged in LAUNCH_READINESS item 6): ~28 New-*-series fuzzy-merges into parent series (fix = add New Avengers/Champions/FF/Suicide Squad/Excalibur to known_titles.json), media junk in pools, emoji-led canonicals;** (2) market_sales equivalent pass (8,604 canonical rows, small extension — LAUNCH_READINESS item 6); (3) micro-items: eBay portal "Notify Me" email (2-min); prior docs note = `docs/LAUNCH_READINESS.md` + this file + `docs/LESSONS.md` (⚠️ L-SW-2026-008/009/010 STILL never committed — folded into command block #3 below) + optionally the untracked `docs/technical/VALUATION_FMV_FIXES_SPEC.md` (S111 spec, referenced by session notes but never added — include or defer, Mike's call). Git truth at write (verified): HEAD = `060f1dc`; dirty = `title_normalizer.py`, `docs/LESSONS.md`, this file, `docs/LAUNCH_READINESS.md`.**

**MOST RECENT CHANGE (earlier 2026-07-09): Item 2 Phase 1 VERIFIED IN PROD: `db.py` shared pool + 8 getter rewires (~59 sites) + wsgi teardown leak-net (commit Mike's; deploy verified). Evidence: full smoke passed, zero `[DB]` warnings, 12-request public-lookup probe = ZERO connection growth (app parked-set flat at 5; old code opened 4+ fresh connections per grade). Phase 2 QUEUED = ~75 inline `psycopg2.connect` sites → `db.get_db()`. Detail + phase plan in LAUNCH_READINESS item 2(b) (SoT). Offline verification before deploy: py_compile ×10, 15/15 pool-mechanics checks vs RO string (both cursor flavors, reuse, flavor reset, idempotent close, exhaustion→overflow, kill switch), teardown net proven end-to-end (leaked-on-exception connection force-returned).**

### Also this session
- **Read-only pooling/gunicorn plan** (facts: Render Starter 512MB/0.5CPU, measured RSS ~173MB, max_connections=103, ~59 getter-routed + ~75 inline sites, two cursor_factory flavors; 4-phase rollout, pool-first-workers-last; gunicorn target `--workers 2 --threads 8 gthread`, fallback 1×12 if memory alerts).
- **2(f) resource-ceiling self-alert designed** (Render has NO native threshold alerts — verified against current docs; self-check in dependency_monitor: cgroup memory + pg_stat_activity vs ceiling + pool_stats(); WARN 80%/70% placeholders, calibrate post-Phase-1; monitoring-only, tier upgrade stays Mike's manual call). Queued behind Phase 2/3. Mike separately: enable Render native event notifications (dashboard-only).
- **🔍 NEW VALUATION FINDING (read-only diagnosis, logged in LAUNCH_READINESS item 6): Cover-A variant misclassification — modern multi-cover mispricing, SYSTEMIC.** Absolute Batman #1 (Dragotta A, 1st print) 9.0 → raw FMV $150 vs real Cover-A market ~$185 median/$238–395 clean copies. Mechanism corpus-proven: `title_normalizer.py:268` flags "Cover A" ITSELF as `is_variant` → the standard cover's 156 best-labeled sales are EXCLUDED from their own estimate; included "standard" pool (median exactly $150.00 = shipped FMV) retains word-form printings ("Tenth Print"), Noir editions, artist-name variants, Annual-canonical leakage, a graded=false CGC slab, missed lots. Extraction DOES identify cover/printing (vision + barcode digits 4/5) but the valuation key drops it (title+issue+issue_type only). Fix-B gate correctly green (pool is big) = confidently wrong. Fix tiers logged, NOT applied; placement decision pending (tier-1 = 1-line regex + flag re-normalize — cheap, moderns are the con-booth demo books).
- **Interaction flag:** the Cover-A finding is upstream of R1/R2 — grading-accuracy benchmarks inherit wrong-product FMVs regardless of grade correctness.

### LATER SAME DAY (2026-07-09 PM) — two working-tree deliverables awaiting Mike's return
- **Phase 2 DONE in working tree, approved in principle:** all 57 inline `psycopg2.connect` sites → `db.get_db()` (16 files, +85/−66; expressions only, control flow untouched; `database_url` locals deliberately left; 2 disguised getters converted; helper modules incl. after close-discipline check). All compile; zero residual connects in web path. **Mike: review → commit → deploy → smoke → DF re-runs connection probe.** Parked set may legitimately grow past 5 (more surface pooled); signal = `POOL EXHAUSTED` lines or growth past DB_POOL_MAX=8.
- **Cover-A + cross-title fix DRAFTED (Mike decided: Layers 1+2 pre-launch as one correctness fix; Layer 3 grade-aware raw → R1/R2):** `title_normalizer.py` +58/−3. Corpus audit = SYSTEMIC: 748 rows/23 canonicals mis-merged (DEFENDERS→descender 56 rows the standout beyond the Absolute line); 2,601 Cover-A rows flip to standard; AB#1 median $158.50→$178.20 end-to-end. Full numbers + rollout (normalize_batch re-run; market_sales needs small extension) in LAUNCH_READINESS item 6.

### NEXT (revised 2026-07-09 late — Phase 2 shipped; eBay endpoint promoted to active)
1. ~~Phase 2 review+commit+deploy~~ — **DONE (`e75f0f9`), gate passed** (see CURRENT STATE block).
2. **eBay account-deletion endpoint — ✅ FULLY DONE 2026-07-10, both halves.** Issue 2 (security): SHIPPED `060f1dc` + VERIFIED IN PROD (412 unsigned / portal test notifications verified incl. live key rotation / GET 200). Issue 1 (compliance timeout): CLOSED same day PM — downgraded to low-probability/self-healing (1000-consecutive-failure threshold, self-resetting; config confirmed correct; see CURRENT STATE + LAUNCH_READINESS Dependency watch). Only residue: portal "Notify Me" micro-item (Mike, 2-min). *(Historical detail of the shipped fix:)* new `ebay_signature.py` (ECDSA/SHA1 over RAW body per eBay's scheme; base64-JSON `x-ebay-signature` header {alg,kid,signature,digest}; public key via Notification API `getPublicKey` w/ client-credentials app token, cached 1h; tri-state valid/invalid/unavailable → 200/412/500 — 500 makes eBay REDELIVER, never ack-and-drop a real GDPR notice; kill switch `EBAY_SIGNATURE_VERIFICATION_DISABLED=1`) + `routes/ebay.py` POST branch verify-first + **bonus bug fixed: real eBay payloads nest identity under `notification.data` — old top-level reads meant REAL notifications never deleted anything (only forged flat ones could)** + `cryptography>=42` in requirements + monitor/ARCHITECTURE touches. Offline-verified: py_compile + 12/12 branch tests (self-signed EC key, tampered body, malformed headers, alg drift, key-fetch outage, non-EC key, kill switch, cache path). Raw-body byte assumption subsequently proven in prod against real eBay-signed messages (see CURRENT STATE). ⚰️ The commit/deploy command block that lived here is DEAD — executed as `060f1dc`, do not re-run.
3. **title_normalizer fix commit/deploy + corpus re-normalize (dry-run first)** — verified, sits on disk, command block #2 below; slots whenever Mike runs it.
4. Phase 3 (billing finally + before_request lookup) → Phase 4 (gunicorn CMD + .dockerignore).
5. 2(f) resource alert after Phase 2/3.
6. eBay OAuth pool surface spot-check when extension flakiness clears.

### Morning command blocks (revised 2026-07-10; git truth: HEAD `060f1dc`, block #1 DONE as `e75f0f9`, eBay block DONE as `060f1dc`)
```powershell
# ⚰️ 1) Phase 2 — EXECUTED as e75f0f9, verified; do not re-run.
# ⚰️ (eBay Issue-2 block from NEXT item 2) — EXECUTED as 060f1dc, verified; do not re-run.

# 2) Normalizer correctness fix (still pending; slots whenever Mike runs it)
git add title_normalizer.py
git commit -m "fix(valuation): Cover-A is standard not variant; token guard on fuzzy canonical match (748 cross-title mis-merges, 23 titles)"
git push
deploy
# → then corpus re-normalize in Render shell: python normalize_batch.py --dry-run  (review) → python normalize_batch.py

# 3) Docs + lessons (BOTH eBay issues closed in LAUNCH_READINESS + this file; LESSONS 008/009/010 folded in — still never committed)
git add docs/LAUNCH_READINESS.md docs/sessions/WHERE_WE_LEFT_OFF.md docs/LESSONS.md
git commit -m "docs(readiness): eBay endpoint fully closed — Issue 2 verified in prod (412/portal-tests/key-rotation), Issue 1 downgraded (1000-consecutive-failure threshold, config confirmed); lessons L-SW-2026-008 (S111, unstaged until now) + 009 + 010"
git push
# optional add to the same commit if wanted: docs/technical/VALUATION_FMV_FIXES_SPEC.md (S111 spec, currently untracked)
```

---
# (prior header) Where We Left Off - Jul 8, 2026

## Session 113 (Jul 8, 2026) — BILLING ITEM 1 FULLY CLOSED: one-diff shipped, core teardown + add-on both PASSED, both guard branches observed live; mid-test scare diagnosed read-only (dashboard-created subs — fix NOT implicated); PYTHONUNBUFFERED gap found, fixed, confirmed

**MOST RECENT CHANGE: 2026-07-08 (PM) — LAUNCH_READINESS sequence item 1 CLOSED. One-diff SHIPPED (`3935ce5`, 19:42 UTC, Mike ran all git/deploy); core teardown PASSED all three fields (`plan=free`/`status=canceled`/`stripe_subscription_id=NULL` — the field that never cleared before), doubly confirmed by cross-account comparison (user 32 clean vs 30/31 pre-fix stale); add-on PASSED with BOTH guard branches directly observed in real-time logs after the PYTHONUNBUFFERED deploy — skip branch (non-record dashboard-sub cancel → plan unchanged pro/trialing + `ignoring …, not the sub of record`) and teardown branch (record cancel → full 3-field reset + `→ free (sub … cleared)`). Buffering fix confirmed working (live log lines). ⚰️ Supersedes LAUNCH_READINESS's "targeted direct UPDATE, don't touch the helper" prescription — the shipped fix IS in the helper (`_UNSET` sentinel, `billing.py:183`; omission still skips, explicit `None` writes NULL, all 5 callers audited). NEXT SESSION: sequence item 2 — gunicorn workers/threads + DB pool + finally-closes (+ Sentry, /health DB check, .dockerignore). Detail lives in LAUNCH_READINESS.md (SoT); this entry is the pointer + incident record.**

### What shipped (Mike committed/deployed; Claude drafted + applied to tree only)
- `routes/billing.py` (`3935ce5`): (a) **step-3 multi-sub guard** — `handle_subscription_deleted` selects `id, stripe_subscription_id`, downgrades only when the deleted `sub.id` IS the sub of record; **falls open** (downgrades) when stored sub_id is NULL or event id missing — conservative bias: never trap a user on a paid tier with no live sub, never silently skip a legitimate downgrade. Skip path logs `ignoring <id>, not the sub of record`. (b) **sub_id-NULL** — `_UNSET` sentinel default on `update_user_subscription.stripe_subscription_id`.
- `Dockerfile`: `ENV PYTHONUNBUFFERED=1` — shipped + deployed same session; **confirmed working** (the add-on test's guard log lines appeared in real time, the thing the old buffering made impossible).

### ⚠️ MID-TEST INCIDENT + DIAGNOSIS (read-only, ~20:15–20:30 UTC) — recorded so the pattern is recognizable next time
- **Scare:** after the passing core test, two new subs on the same throwaway customer (Pro $4.99 ~20:04, Guard $9.99 ~20:08) showed real/active in Stripe but the DB stayed frozen at post-cancel state. Looked like webhooks dropping.
- **Diagnosis (evidence, not theory):** Stripe Workbench event stream shows **both subs were DASHBOARD-created** — Source=Dashboard, NO `checkout.session.completed` anywhere in either cascade, immediate charge (our checkout ALWAYS attaches a 14-day trial → $0 first invoice, as the 19:54 core-test cascade shows). Dashboard subs fire `customer.subscription.created` — **not subscribed by the endpoint, no handler in billing.py** — plus `invoice.payment_succeeded` (log-only handler). **DB unchanged = system working as wired.** Endpoint deliveries: ALL 200, 0 failed, error rate 0%. Deploy clean (one deploy, live 19:42:18, zero restarts). `/health` 200. **The billing fix is NOT implicated.**
- **Real finding — the service is LOG-BLIND: `PYTHONUNBUFFERED=1` missing on collectioncalc-docker** (violates cross-project L-2026-020). All `print()` buffers until container death; proof = the dying pre-deploy container flushed 10 stale `[Billing]` lines with identical timestamp 19:43:17 (old log format, days-old events). The new container's core-test logs are still invisible in its buffer. Also: no gunicorn access logs. This is why Render logs could not answer the delivery question and Stripe's dashboard had to.
- **Tooling note (for future read-only prod diagnosis):** `RENDER_API_KEY` in local shell env works for Render API reads (services/deploys/events/logs; logs need `ownerId`); `DATABASE_URL_RO` in `.env` for read-only SELECTs; Stripe delivery status via Chrome → dashboard (Workbench → Webhooks → Event deliveries). Full loop ran without touching prod.

### ✅ NEXT list from earlier in this session — ALL DONE same day (recorded for the arc)
1. ~~Cancel the two stray dashboard subs~~ — done; fall-open path behaved (idempotent free/canceled re-write).
2. ~~PYTHONUNBUFFERED commit + deploy + fresh shell~~ — done; confirmed working (live log lines).
3. ~~Add-on re-run in the correct shape~~ — **PASSED, both guard branches observed** (see MOST RECENT CHANGE).

### NEXT SESSION
**LAUNCH_READINESS sequence item 2** (locked since S112, now the active item): gunicorn workers/threads (`--workers 2 --threads 8 --worker-class gthread`, sized to instance RAM) + DB connection pool + close-in-`finally` sweep, plus Sentry, `/health` DB check, `.dockerignore`. Note: item 2(c)'s first slice (PYTHONUNBUFFERED) already landed this session. **Read-only plan for the pool+gunicorn work DELIVERED 2026-07-09** (4 phases: db.py pool+getter rewire → inline sweep → finally/hot-path → gunicorn CMD; facts: Starter 512MB/0.5CPU, measured RSS ~173MB, max_connections=103, ~59 getter-routed + ~75 inline connect sites, getters have two cursor_factory flavors). **Queued behind Phase 1 verification: item 2(f) resource-ceiling self-alert** (cgroup memory + pg_stat_activity vs ceiling in dependency_monitor; Render Starter has no native threshold alerts — verified; monitoring-only, upgrade decision stays Mike's).

### Post-launch (logged, no action): webhook sub-state sync hardening
Dashboard/API-created subs invisible (no `.created` handling) + `handle_subscription_updated` customer-matched last-writer-wins (`plan or 'free'` metadata footgun) — one-touch fix spec'd in LAUNCH_READINESS Post-launch section (2026-07-08 bullet).

---

## Session 112 (Jul 7, 2026) — DF full technical review (4-track, read-only) + BS competitive requirements reconciled; NEW launch-blocker (gunicorn single worker); grade-retention status corrected (BUILT, not spec-only); moat reframed

**MOST RECENT CHANGE: 2026-07-07 — Full technical review reconciled into `docs/LAUNCH_READINESS.md` (the SoT — read THAT for all detail; this entry is the pointer). NEW LAUNCH-BLOCKER: gunicorn = 1 sync worker, no DB pool (booth-killer; LAUNCH_READINESS sequence item 2). ⚰️ STATUS CORRECTION: grade retention is BUILT+DEPLOYED (`801e79d`/`6fb83f7`) — the long-carried "spec only, gated on privacy" framing is DEAD (privacy disclosure shipped S107, build followed; remaining = purge job + pin-on-feedback + areas_not_visible persistence). Moat REFRAMED per BS competitive doc (mirrored at `docs/SW_COMPETITIVE_REQUIREMENTS_FOR_DF.md`): NOT the only AI raw-grader (ComicMintAI / Comic Locker / Gradr claim the same; none proven) → the race is FIRST DEMONSTRABLY ACCURATE + honest-about-uncertainty; R2 side-by-side competitor benchmark added to grading triage (one motion with the consistency-harness run). eBay deletion endpoint = TWO independent issues — the probe-timeout compliance diagnosis is NOT superseded by the new no-signature-verification security finding (BS doc said "struck"; corrected, Mike agreed). NEXT SESSION LOCKED (Mike, this session): (1) billing one-diff (step-3 multi-sub guard + sub_id-NULL; pass = `--check-db` teardown → sub_id=NULL), THEN (2) gunicorn workers/threads + DB pool + finally-closes (+ Sentry, /health DB check, .dockerignore). Prior (2026-06-29): BILLING hard gate essentially cleared (Model A + teardown verified); anti-abuse logged MEDIUM, coupled to gated signup.**

### Session 112 summary (detail deliberately NOT duplicated here — LAUNCH_READINESS.md is the SoT)
- **What ran:** 4 parallel read-only review tracks (grading-accuracy deep-dive, architecture/code-health, security/perf/scalability, feasibility inventory), then BS's competitive requirements doc reconciled in.
- **Grading-accuracy facts now on file** (LAUNCH_READINESS sequence item 6): grade = ONE temp-0 Sonnet call; multi-run voting built server-side but dead in prod (frontend hardcodes `runs:1`); consistency NEVER measured (live harness exists at root: `test_grading_consistency.py --live`); confidence = photo-count lookup, displayed nowhere; no Fix-B-style grade gate; quality gate checks first image only; PROMPT_VERSION absent. Recommended pre-launch minimum ≈2 contained sessions: PROMPT_VERSION → harness run + R2 competitor benchmark (one motion) → `grade_reliable` + amber partial-view UI.
- **Security:** 3 unauthenticated upload endpoints + eBay deletion no-signature = LAUNCH_READINESS sequence item 3 (before beta admits strangers); OAuth-state CSRF / body-size cap / atomic cap-increment = post-launch tier. SQL injection / IDOR / JWT / Stripe-webhook signatures / secrets all verified clean.
- **Committed this session (Mike):** LAUNCH_READINESS reconciliation + competitive-requirements mirror.
- **Zero production code touched** (review + docs only). Draft-then-authorize rhythm held; Mike ran all git.

---

## Session 111 (Jun 27, 2026) — State-Recording Protocol enshrined; E3 RAN → single-image PARKED; LIVE Slab Guard copy RESCOPED (provenance + candidate-sightings beta); pivot to VALUATION

**[SUPERSEDED as most-recent by Session 112 above] MOST RECENT CHANGE: 2026-06-29 — BILLING hard gate essentially CLEARED (verify-against-Model-A session). Cancel = Model A confirmed (portal cancel-at-period-end); trial cancel = $0 + access-to-period-end; never-tested TEARDOWN entitlement OBSERVED working (immediate-cancel → plan=free/status=canceled, access lost). Two contained cleanups queued as ONE diff in `handle_subscription_deleted`: step-3 multi-sub guard + sub_id-NULL (`billing.py:197` None="skip" footgun); next-session pass condition = re-run `--check-db` teardown → sub_id=NULL. Anti-abuse logged (MEDIUM, not fixed): repeat-trials + email-alias evasion, coupled to "no un-gated public signup before they ship." Full launch status lives in `docs/LAUNCH_READINESS.md` (the SoT). Prior (2026-06-27): created LAUNCH_READINESS.md; VALUATION Fix A/B shipped+verified; grading-accuracy signal; L-SW-2026-008.**

**Built draft-for-review; Mike runs all git/deploy. Zero production code shipped this arc (E3 is a standalone harness). State-Recording Protocol adopted into the operating model after last night's near-miss. Earlier-in-session reversal (re-capture → SAM) tombstoned below.**

### ⚰️ E3 RESULT + DECISION TOMBSTONE — single-image cross-camera recovery PARKED (2026-06-27)
- **E3 RESULT: TP 6/6, FP 4/6 → REJECTED by the both-sets gate.** Read the per-pair reasoning, not the score: E3 didn't get more *discriminative*, it got more *permissive* — it now matches BOTH same and different copies. The 4 FPs (Heros, Marvel_Universe_1, Marvel_Universe_2, Wolverine — all **low-wear**) matched on **shared printed art** (the arbiter's own words: "artwork registration corresponds", "printed art registers at identical positions", "few sharp wear landmarks"). The 2 correct rejections (Iron_Man_200, The_Invaders_41 — both **high-wear**) found **real divergent wear** ("jagged chip/tear absent in REF", "outward bulge and chips near 65-70%"). The discriminator is real but the band can't separate copy-unique wear from copy-shared print on low-wear books. CSV: `tests/SlabGuardTests/e3_bothsets.csv`. Cost $0.28.
- **ENSEMBLE (Mike's old-arbiter-veto idea): DEAD.** Read-only data check (no Opus) against the old corner-crop arbiter (`truepositive_results.csv` / `crosscam_fp_results.csv`): hard AND-gate = **TP 1/6, FP 0/6 = the old method bit-for-bit**. Deeper reason it can't work: on the 4 low-wear books the old arbiter is a constant "different" and E3 is a constant "same" — both **saturated in opposite directions, zero discriminative signal in either**. The disagreement is pure opposite-bias, not complementary competence → **correlated blindness, nothing combinable**. (Only Iron_Man carries independent signal: E3 discriminates, old is reject-biased.)
- **CEILING: physical, not representational — triangulated from 3 directions.** Ensemble → reproduces old. Print-masking (edge-profile-only rep) → ~2/6 TP, 0/6 FP. Route-by-wear → ~2/6 TP, 0/6 FP. All three converge on **"recover the high-wear fraction (~2/6), abstain on low-wear, FP 0."** Because copy identity lives in WEAR and low-wear books don't have it — no representation extracts a signal that isn't on the paper. The grade ceiling, confirmed from a third direction.
- **SINGLE-IMAGE: bounded, NOT zero.** Works on high-wear raw books, must ABSTAIN on low-wear. **Edge-profile-only representation** (reduce each edge to the bare SAM cut-line profile, discard interior print; cross-correlate REF↔TEST 1-D wear signals — could even be no-Opus) = the documented **safe-ification path**: it turns E3's dangerous low-wear FALSE-MATCHES into safe ABSTENTIONS. **NOT built; post-launch.** Upgrades **lane 3 from "provenance/monitoring only" → "provenance + high-wear recovery, abstains otherwise."**
- **ROADMAP (evidence-locked):**
  1. **Slabbed / high-grade → cert-number recovery** — the headline, works, wear-independent.
  2. **Raw high-wear → single-image recovery WITH abstention** (post-launch; edge-profile path).
  3. **Raw low-wear → MULTI-VIEW** — the ONLY path to manufacture copy-signal where one photo has none (more independent views beat the per-view print confound).
  4. **Raw single-image today → provenance / monitoring only, no recovery claim** until the edge-profile abstention ships.
- **PRODUCT-SCOPING NOTE (post-launch, zero build now):** when single-image recovery ships, scope it via **automatic per-book abstention on insufficient wear, NOT a user-facing grade-cutoff disclaimer.** A "only use below grade 9.0" disclaimer is **circular** (the user is using the app to LEARN the grade, so can't self-apply the cutoff) and doesn't engineer out the liability (E3's dangerous form false-matches low-wear books; a disclaimer doesn't stop that — abstention does). The edge-profile path already produces abstention; name the user-facing behavior: **high-wear → "fingerprinted this copy's wear pattern" (recovery works); low-wear → "too clean to fingerprint from photos" (honest abstention, framed as a compliment about condition) → route to the CERT path** (slab it, recover by cert number). The ceiling of single-image recovery becomes the **on-ramp to the cert lane** that actually works for high-value books.
- **TOOLS RETAINED:** SAM masking + the E3 boundary-following engine are **validated and kept** — they feed the multi-view lane later (and the edge-profile rep, if pursued). Nothing wasted.
- **DECISION: park single-image (do NOT pursue ensemble or build edge-profile now), pivot to VALUATION** — launch-critical (ASM #41 first-Rhino ~10× undervaluation; thin-comp key issues). Roughness-routing empirical check deliberately NOT run (wouldn't change the decision; valuation is the priority).

**Docs-only changes this session; Mike commits all (no deploy). State-Recording Protocol adopted into the operating model after last night's near-miss.**

### ⚰️ REVERSAL TOMBSTONE (Rule 2) — the dropped re-capture
- **DEAD:** controlled-background re-capture / re-shoot per `tests/SlabGuardTests/E3_CAPTURE_SPEC.md` (chroma-key matte background, front-only re-shoot to get clean classical-contour edges).
- **REPLACED BY:** **E3 runs on SAM masks of the EXISTING captures** (`TPTests/{Pixel,iPhone}` + `FalsePostiveTest/{PixelPhotos,iPhonePhotos}`) via `scripts/e3_edge_sequence_test.py`. No new photos.
- **REASON:** the SAM run (2026-06-26) produced **24/24 clean masks incl. the white-on-white Marvel cover**; classical contour reliably segmented only **~6/24**. SAM answers the SCIENCE question (does edge-sequence matching recover?) AND the PRODUCTION question (segment arbitrary backgrounds) at once → the clean-input re-shoot is no longer needed to isolate the variable.
- **SUPERSEDES:** `E3_CAPTURE_SPEC.md` is **SUPERSEDED — do NOT execute it.** Header tombstone added to that file 2026-06-27 so a future read can't resurrect the plan. (This is the exact resurrection that bit us the morning of 2026-06-27: an overview reconstructed from the stale spec re-recommended the dead re-capture.)
- **DECISION DATE:** 2026-06-26 (SAM run + "re-shoot dropped, SAM answers both questions"); logged here 2026-06-27 per Rule 4 (should have been logged at the moment of deciding, not at the next session).

### E3 BUILD — CONFIRMED PRESENT (built, not yet run)
- `scripts/e3_edge_sequence_test.py` (untracked, standalone, **zero production-code changes**). Pipeline per pair: SAM quad on REF → SIFT homography maps the quad into the *original un-warped* TEST (void-free correspondence) → perspective-rectify both to a canonical rect + background margin → straddling edge band per side → one Opus 4.8 call with continuous edge-strips + sequence-matching prompt (reject-default + FP strictness preserved).
- **Both of Mike's pre-build confirmations folded in:** (1) **band straddles the paper edge** (`--band-out-mm 2 --band-in-mm 4`, outboard background + inboard cover) with FP-risk reasoning in the docstring; (2) **resolution vs ~8000px API limit** handled as downsample-to-2400-long + thin band (every strip ≪8000px at uniform ~9.3 px/mm), with **`--seg-per-edge` as the tile/along-edge-resolution escape hatch**.
- **Run status: NOT yet run.** Gated only on `ANTHROPIC_API_KEY` (the keyed gate run Mike fires). SAM checkpoint present (375MB, gitignored); `segment_anything` imports OK; all 6 TP + 6 FP pairs verified to form. Yesterday's SAM prototype artifacts in `tests/SlabGuardTests/_e3_sam/` (incl. `sam_marvel_white.png`) prove the engine end-to-end.
- **Both-sets gate (one session):** TP must rise above the 1/6 ceiling **AND** cross-camera FP stay **exactly 0/6** at per-pair confidence. Validity guard: INVALID if any pair has `cost==0` / vision error. Est. cost ~$0.50 (12 Opus calls).
- **OFFLINE PRE-FLIGHT (no key) run 2026-06-27** — exercised the whole pipeline except the Opus call on all 12 real pairs. Engine sound (SAM cracked the white-on-white Marvel covers; homography 430–2674 on real pairs; all build segs=4). **DATA FIX:** the two iPhone FP Marvel files were SWAPPED at capture (`Marvel_Universe_1_Front_iPhone.jpeg` held #2, `_2` held #1) → both Marvel FP pairs were cross-ISSUE (one failed homography at 4 matches, the other slipped through at 68 on shared trade dress and would have falsely "passed" the FP gate). Corrected by swapping the two filenames; re-ran FP pre-flight → 6/6, MU_1 68→1706, MU_2 4→430. Cross-issue audit via match-count separation (mismatch=4/68 vs same-issue=hundreds-to-thousands) confirms NO other mislabel in the 12 front pairs. Backs not audited (deprecated S110, E3 is front-only).
- **FIX B — adaptive boundary-following extraction BUILT (2026-06-27, replaces the minAreaRect rectify-then-slice).** Wide-band eyeball (BO + Mike) found the short edges (TOP/BOTTOM) slant + void SYSTEMATICALLY across all 6 (not Iron-Man-specific) — minAreaRect forces a rectangle but raw comics are bowed/trapezoidal, so a straight band clips the short edges. Wide band "fixed" coverage only by being generous enough to pull in heavy printed trade dress = the FP vector. Fix B traces the TRUE SAM contour (drops minAreaRect), samples a band along the boundary NORMAL per-column (REF direct; TEST via the ref→test homography on the same world points → corresponding, void-free), biased TIGHT to the bare paper margin (≈2mm out / 3mm in → max copy-unique wear, min shared print), with mm-scale contour smoothing (1.6mm) to reject SAM px-jitter. Contained to `build_segments`/`_edge_strip` in `scripts/e3_edge_sequence_test.py` — ZERO production code. Offline-verified: all 6 TP rebuild segs=4, bottom voids gone, bands hug the edge. QA strips (before/after) in `tests/SlabGuardTests/_e3_qa/` (`*_wide` = stopgap, `*_fixb` = Fix B). **Awaiting Mike's eyeball verdict on the Fix B strips → then the paid both-sets gate.**

### ⚰️ VALUATION DIAGNOSIS TOMBSTONE — ASM #41 miss = leading-article title bug, NOT thin data (2026-06-27, read-only)
- **SYMPTOM:** ASM #41 (first Rhino), graded 6.0 → returned FMV ~$47, verdict "probably not worth grading." Real CGC 6.0 sells ~$400–600 (~10× undervaluation), driving a WRONG slab/no-slab verdict — the core product promise.
- **ROOT CAUSE (proven from `lookup_demand` + corpus):** the actual logged lookup used title **`"The Amazing Spider-Man"`** → **comp_count=0, fmv_method=`estimated`, no_data=True**. The corpus stores `canonical_title="Amazing Spider-Man"` (no article). `title_matching.qualifier_title_clause` does a NORMALIZED EXACT match on canonical_title; the leading **"The"** breaks it, and the substring-LIKE fallback also fails (column "amazing spider man" doesn't CONTAIN "the amazing spider man"). → 0 comps → generic `grade_baselines` estimate ($10@6.0 × pub × era ≈ $39–47, KEY-BLIND). Had it matched: **6.0 median ≈ $550 (7 comps/365d)**, raw ≈ $250, ROI ≈ +$255 → "Worth grading" (opposite verdict).
- **NOT a thin-comp problem:** ASM #41 has 49 graded comps/365d, full grade curve (4.0→$325 … 7.0→$750 … 8.5→$1,739). Data is rich; retrieval missed it.
- **WIDE BLAST RADIUS (flagship titles):** `lookup_demand` already shows **16 lookups / 11 distinct "The…" titles** hitting no-data/estimated; de-articling lands on huge pools — **Amazing Spider-Man 3,410 rows, Incredible Hulk 1,033, Uncanny X-Men 1,151, Avengers 254, New Mutants 648, Invincible Iron Man 137, Spectacular Spider-Man 150**. The bug silently zeroes valuation for the highest-traffic Marvel/DC books (the ones that conventionally carry "The").
- **STRUCTURAL GAP it exposed:** the system COMPUTES `confidence`/`estimated`/`no_data`/`exact_count` (and logs them) but the slab/no-slab VERDICT does NOT gate on them — it renders a confident "don't grade" off a no-comp estimate exactly as off 50 real comps. A $550 key and a $5 nobody book yield the same confident verdict when comps=0.
- **FIX PLAN — spec'd, built, verified (spec: `docs/technical/VALUATION_FMV_FIXES_SPEC.md`):**
  - **Fix A — leading-article title normalization (`title_matching.py`): COMMITTED `c688bce` + DEPLOYED.** Strip leading "the " symmetrically in `_norm`/`_norm_sql` (lockstep). Corpus-proven: **0 false merges across 14,033 titles** (every merge = {X,"the X"}); "a"/"an" excluded (no rescue value, nonzero risk). Verifications: flagships rescued (The Amazing Spider-Man→1,230 comps/365d, X-Men 436, Hulk 377…); **ASM #41 end-to-end → 6.0 median $550, ROI positive, "Worth the Slab", `verdict_reliable=True` — confirmed live in the result UI.** Mike commits + Render deploy.
  - **Fix B — data-sufficiency verdict gate: COMMITTED `cecbaa5` (backend+frontend) + DEPLOYED + SMOKE-TEST PASSED live (NFL SuperPro #1 → amber "ROUGH ESTIMATE" caution rendered).** Backend `routes/sales_valuation.py`: confidence computed before the verdict; `verdict_reliable = not (estimated or fmv_method in estimated/estimated_from_raw)` → **FABRICATION TIER ONLY** (zero-real-comp invented FMV); on `!verdict_reliable` the verdict becomes "Not enough recent sales to value this reliably — rough estimate only, treat with caution" (number kept), `verdict_reliable` added to response. Frontend `app.html`: on `verdict_reliable:false` → amber "ROUGH ESTIMATE" badge (not green/red), neutral ROI color, prominent caution tagline — **essential, B is invisible without it.** SCOPE RESOLVED: `exact_thin` (1-2 real comps) stays confident at launch (thin-but-real ≠ fabricated); `confidence=='very_low'` would wrongly sweep it in. **⏰ POST-LAUNCH:** extend gate to `very_low` once we have data on how often exact_thin misleads (in-code ⏰ comment).
  - **REMAINING TITLE-MATCHING TAIL (post-launch, small):** ~14 lookup titles across token-order + colon/subtitle/accent classes; ~25 "absent" are junk (auction noise/foreign, not fixable). Spacing/hyphen + possessive classes have ZERO traffic yet (untriggered, not absent) — **monitor `lookup_demand` post-launch** to catch the tail as traffic surfaces it. Not a pre-launch gap.
  - **SEQUENCE:** ship A now (commit+deploy) → review B diff (backend+frontend together) → commit+deploy B.

### ⚰️ LIVE SLAB GUARD SCOPING TOMBSTONE — copy rescoped to match what's supported (2026-06-27)
- **OVERCLAIM (DEAD):** the live user-facing copy claimed cross-camera photo-**recovery** — "tied to the physical **copy**, not just the title" (index.html), "monitors eBay… alert you if a **match** appears" / "**Match Alerts**" (pricing.html + extension), "advanced fingerprinting technology to **track and recover** stolen comics" (verify.html). These ride the QUANT path (`compare_covers` = composite hash + edge-strip + SIFT edge-IoU) the code's own `monitor.py` docstring calls **"UNRELIABLE for cross-camera."**
- **PRODUCT TRUTH (read-only confirmed):** the live extension photo-matches **quant-only** — `background.js` calls `/api/monitor/check-image` with NO `marketplace_mode`/`use_vision`, so `compare_covers_with_vision` (the whole E1/E2/E3 vision-arbiter surface) **never fires in production**. Reliable layers = **serial-number lookup + reported-stolen DB flags** (exact). Only prod CV changes this whole arc: `647bca2` Opus-arbiter swap + `27946ff`/`99337f4` two safety fixes — **all in the vision path the live extension doesn't invoke**; E1/E2 reverted; E3/SAM grep in product file = NONE (harness-only). **No edge-sequence upgrade is shippable** (E3 FP 4/6 < live).
- **REPLACED BY:** copy rescoped to **provenance + monitoring** across 4 surfaces (index.html, pricing.html, verify.html, extension `popup.html`): fingerprint = "a record of your copy"; auto-scan = "**candidate sightings to review (beta — may be inaccurate; verify by serial)**"; recovery routed to the serial lookup that actually works. **Match-alert rework is a SAFETY fix in copy form** — the bar is "can never send a user to confront the wrong person over a legitimately-owned book," so results read as reviewable candidate leads, never a confident ID. **Beta label kept.**
- **KEPT (honest, supported):** serial verification, reported-stolen lookup, register/fingerprint-as-record.
- **STATUS:** copy diff DRAFTED (4 files), awaiting Mike's commit — NO deploy. Loud surfaces also softened (don't let hero/subtitle/share-preview overclaim what the body walks back): extension tagline "Catch thieves" → "Monitor the market"; homepage subtitle "authentication powered by AI" → "fingerprinting & monitoring powered by AI"; pricing `<meta>` "theft protection" → "theft monitoring." Complete copy rescope = ONE reviewable/committable unit; cert-wiring scoped SEPARATELY after this lands (don't entangle the launch-safety copy commit with a build).
- **DEFERRED — the real recovery upgrade:** wire **cert-number recovery** (slabbed books: cert already OCR'd/stored/indexed → exact, wear-independent lookup) = lane 1, the honest capability gain, next build (scoped AFTER this copy diff lands). Nothing from edge-matching.

### State-Recording Protocol — ENSHRINED
- Full text committed to **`docs/STATE_RECORDING_PROTOCOL.md`** (in-repo, not a loose Downloads file).
- **Surfaced from `CLAUDE.md`:** SESSION OPENING PROTOCOL now has a **step 4** (re-read THIS file + scan for newer decisions before acting — Rule 3), plus a callout block summarizing Rules 2/4/5 with the source incident. So "re-read before acting" has something to re-read, and a future open hits the rules on the way in.

### NEXT
1. **VALUATION (launch-critical, the new active thread)** — ASM #41 first-Rhino ~10× undervaluation; thin-comp key issues. (Mike/BO bringing the framing.)
2. **Mike commits the E3 arc + docs** when ready: `docs/STATE_RECORDING_PROTOCOL.md`, `CLAUDE.md`, `E3_CAPTURE_SPEC.md` tombstone, this `WHERE_WE_LEFT_OFF.md` entry, the harness `scripts/e3_edge_sequence_test.py`, and the `tests/SlabGuardTests/` E3 data/CSVs/QA strips as desired. No deploy (docs/test only; zero production code touched this arc).
3. **Single-image: PARKED** (see E3 RESULT + DECISION TOMBSTONE above). Do NOT pursue ensemble (proven dead) or build edge-profile now (post-launch). SAM + E3 engine retained for the multi-view lane.
4. Unchanged launch track behind valuation: cert-number recovery lookup (lane 1 headline), billing stacking steps 2 & 3, Section F mobile+load, ⏰ 90-day purge ~2026-09-17.

---

## Session 110 (Jun 24-26, 2026) — Cross-camera recovery FULLY CHARACTERIZED: FP=0/12 (liability gate PASSED, 3 runs) but TP=1/6 (recovery sensitivity FAILS); E1 (prompt) + E2 (pixel normalization/glare-mask) BOTH REJECTED → single-image looked CEILINGED **— BUT see E3 section: that conclusion is now SUSPENDED** (the TP was measured on warp-void-crippled input — the arbiter only saw half the perimeter, fragmented); learned-feature swap closed (registration is NOT the bottleneck); two arbiter safety fixes committed; backs deprecated; roadmap = three lanes (slab→cert / raw-multiview→post-launch / raw-single→provenance-only)

**Built draft-for-review; Mike runs all git/deploy. Verification ran before every diff reached Mike (offline parsing/pairing asserts + in-process arbiter-logic asserts + module-import checks). Standing protocol: file-specific staging, commit message matches diff.**

### E3 (Jun 26) — continuous edge-SEQUENCE representation: the "single-image ceilinged" conclusion is SUSPENDED, under test
- **Why suspended — the ceiling was measured on CRIPPLED input.** A read-only crop-coverage dump of the Iron Man TP pair showed the arbiter received **only the top + right edges** — the **bottom + left edges and both bottom corners were dropped as warp voids** (the iPhone shot was rotated ~90°, so the homography warp leaves black non-overlap regions, and `_region_is_black` skips them). The arbiter adjudicated **half the perimeter, fragmented into isolated patches**, never tracing the continuous sequence. Mike's decisive ticks (top-center, top-right, right-edge) WERE in the crops it received and it rejected anyway → confirmed it does **isolated-patch adjudication, not sequence-tracing**. We proved "corner-crop region-comparison fails," NOT "single images lack the signal."
- **⚠️ WARP-VOID DROPPING = LATENT PRODUCT BUG (flag independently).** On differently-framed pairs — i.e. MOST real recovery scenarios, where the recovery photo won't match enrollment framing — the crop builder silently discards edge/corner regions as warp voids, so the arbiter loses evidence. It has been degrading every cross-framing comparison. E3's contour-follow fixes it as a side effect, but it is its own bug.
- **E3 hypothesis (modeled on Mike's demonstrated method):** Mike matched Iron Man by eye **forensically** — continuous full-perimeter edge tracing, matching a SEQUENCE of bends/ticks at positions, no prior. E3 reframes the arbiter's INPUT: one **continuous physical-edge strip** (perimeter "unrolled") + instruction to match the sequence. Keeps reject-default + FP strictness — changes WHAT it sees + the operation, NOT the bar. FP bonus: tracing the bare PAPER edge minimizes shared printed trade dress = starves the false-sequence-match vector (first fix that helps TP and FP TOGETHER).
- **E3 ENGINE VALIDATED (read-only prototype):** contour-follow unroll + **homography correspondence** — detect the book quad in REF, map it via the homography into the ORIGINAL (un-warped) TEST → **void-free, physically-corresponding** traces. On the hard rotated Iron Man pair it produced two directly-comparable, void-free perimeter traces. The representation Mike's method needs is producible, and it fixes the warp-void bug.
- **BLOCKER → SCIENCE/PRODUCT SPLIT (Mike's reframe):** the engine hinges on book-edge detection; classical contour detection (Otsu, border-flood-fill) reliably finds only dark high-contrast covers (~6/24), fails on white/light covers (white cover ≈ white table). Two separate questions:
  - **Q1 — science, answerable NOW:** does edge-sequence matching actually recover? Test on a CONTROLLED-background re-capture (clean edge extraction isolates the variable). Spec: `tests/SlabGuardTests/E3_CAPTURE_SPEC.md` (saturated matte chroma bg, front-only, TP + FP, both phones).
  - **Q2 — product, POST-LAUNCH:** extract the comic edge from ARBITRARY real-world backgrounds (carpet/wood/bedspread/white-on-white) = **learned segmentation (SAM2 / custom comic-seg model), NOT classical contour** (brittle to clutter). Queued, **gated on E3 validating**, same CPU/Render infra reality as the LightGlue call; also lifts grading/valuation image quality (not single-purpose).
  - **Controlled background is deliberate TEST ISOLATION, NOT the production assumption.** Production edge extraction = learned segmentation, queued pending E3.
- **NEXT for E3:** Mike re-captures per `E3_CAPTURE_SPEC.md` → I draft E3 (unroll + sequence-matching prompt) → both-sets gate (TP↑ AND cross-camera FP=0/6 at per-pair confidence). Validates → single-image back on the table for soft launch + learned-seg roadmap item justified; fails → single-image genuinely ceilinged (now tested with the demonstrated-working method on clean input) → multi-view primary. Read-only-later: assess SAM2 vs a custom seg model as the CPU production fit (gated on E3 — do NOT scope yet).

### Headline: the decisive number landed clean. Front-cover cross-camera false-positive rate = **0** — held across **three** runs — and two real arbiter safety bugs (both in the dangerous "different copy surfaces as a match" direction) were caught by the test and fixed in the live product path.

### THE RESULT — cross-camera false positives = 0
- **Front covers: FP = 0/12**, three consecutive runs, confidences **0.6–0.97**. This is the metric that gates the recovery claim (different copy of the same issue, two cameras, must NOT match). It passed.
- Test set: `tests/SlabGuardTests/FalsePostiveTest/{PixelPhotos,iPhonePhotos}` — same 6 issues, **different physical copies** across the two phone folders (visually confirmed same-issue, e.g. Iron Man #200 both sides). 6 same-issue cross-camera pairs per side.

### BACKS DEPRECATED AS A MATCHING SURFACE
- Backs produced **3/6 non-clean** results (1 false positive — since corrected by the fix below — + 2 `uncertain`) vs fronts 6/6 clean across every run.
- **Structural reason (not tunable):** same-issue back covers are frequently the **identical mass-printed full-page ad** (shared trade dress / barcode block), so the SIFT/border matcher agrees on shared **print**, not shared **wear**, and cannot discriminate copies. Evidence: the Wolverine back pair shows `border=39` geometric inliers vs 0–10 on every other pair — a spurious spike from shared printed content. **Recommendation: drop back covers from the recovery matching path.**

### TWO PRODUCT-PATH ARBITER FIXES (`routes/slab_guard_cv.py` — COMMITTED in HEAD; deploy to Render per protocol)
Both surfaced by the back-cover run; both are general live-path hardening (not test-only), both in the "different copy must never read as same_copy" safety direction:
1. **Vision JSON parse hardening.** The arbiter assumed a pure-JSON response; when the model appended trailing prose (more common on dense back covers) `json.loads()` raised "Extra data", the greedy-regex fallback also threw, the exception escaped to the outer handler → `vision=None` → quant fallback defaulted to `same_copy` (a real false positive on Heros_For_Hope back). Fix: new `_extract_first_json_object()` (balanced-brace, string/escape aware) parses only the first `{...}` object and ignores leading/trailing content + code fences; a genuine parse failure now defaults to **`uncertain`, never throws**; safety net so a parse failure can never surface as `same_copy`.
2. **Uncertain vision can no longer be promoted to a match.** In marketplace mode, a successfully-parsed `vision=uncertain` could still be overridden to `same_copy` by the LPQ/quant tiebreaker (Wolverine back: `vision=uncertain` → `final=same_copy/0.6`). Fix: the marketplace vision-uncertain branch may only downgrade toward `different_copy`; floor outcome is `uncertain`, never a match. Generalized the safety net to enforce this invariant (no real vision match ⇒ never `same_copy`). Standard mode unchanged (quant is the trusted primary there by design). Re-run confirmed: Wolverine back flipped to `different_copy` (same `border=39` spike, verdict held correct).

### HARNESS ADAPTED TO THE REAL SHOOT (`scripts/slabguard_crosscamera_test.py`, drafted + verified)
- Rewrote ingestion for the actual shoot: **phone = folder** (`--phone1`/`--phone2`), parses `<Issue_Name>_<Front|Back>_<copyNumber>` (`copynum`, default), dynamic copy enumeration (handles the 2- and 3-copy issues), `--side front|back|both`, FP split into **cross_camera vs same_phone**, `invalid_no_arbiter` CSV column (a keyless quant-only run can't be mistaken for valid), one localhost file server per phone folder.
- Added **`--layout crosscam-fp`** for the FalsePostiveTest set (`<Issue>_<Front|Back>_<Pixel|iPhone>`): copy identity comes from the folder so same-issue Pixel↔iPhone pairs score as different copies (cross-camera FP), `expect=different_copy`.
- Default-model label corrected to Opus 4.8; docstring updated to 6 issues / variable copies / dual FP modes.

### ARCHITECTURE FINDING (read-only) — copy discrimination is WEAR-carried → route recovery by book type
- Traced what each layer keys on in marketplace mode. **Print/image signal (SIFT alignment + dIoU edge-IoU) establishes same-ISSUE only — copy-blind by design** (`_compute_edge_iou` docstring: aligned edges "match across ALL copies of the same issue"). **Copy-level identity is carried by WEAR/DEFECT signal:** the Vision arbiter (primary in marketplace; prompt is explicitly anti-print — "matching ink patterns... are NOT evidence", requires a SPECIFIC uniquely-identifiable defect, defaults DIFFERENT_COPY) and **LPQ-border** (the residual-texture quant signal — Session 55: "the discriminative signal lives in border wear patterns, not interior printed content"). `border_inliers` is wear-keyed in theory but **unreliable cross-camera** (false matches from background/shared-ad print) → demoted to confidence/different-only support, never drives same_copy (the Wolverine back `border=39` is exactly this documented false-inlier mode).
- **Failure direction on low-wear books = FALSE NEGATIVE (missed match), not false positive.** So the **FP=0 liability result holds across ALL grades**; but **recovery SENSITIVITY has a grade ceiling — high-grade/slabbed/mint is exactly where wear-matching is weakest** (little wear = little copy-unique signal; every layer defaults toward different_copy/uncertain).
- **ROUTING IMPLICATION — this finding is the technical evidence for the primer's existing routing call, and the architecture + market align by book type:**
  - **Slabbed / high-grade → cert-number recovery** (wear-independent; cert already OCR'd/stored/indexed, just needs the lookup wired) — the path for the high-value books photo-matching is weakest on.
  - **Raw / mid-grade with genuine wear → wear-based photo matching** (this harness's path), where the wear signal is strong.
  - **Recovery photo-matching claims must be SCOPED to raw books with real wear; slabbed recovery rides the CERT path, not photo-matching.**
- **Consequence for the TP run (interpretation HELD until grades are noted):** a clean TP on worn books does NOT generalize to high-grade. Provisional visual read of the 6 already-shot TP books: none slabbed/mint, spanning Heavy (The_Invaders_41 — strongest wear, easiest case) to Low (Wolverine — weakest wear, hardest case); **no decisive high-grade copy in the set.** Protocol (`TP_RESHOOT_PROTOCOL.md` §7–§9) now REQUIRES grade-stratified reporting + at least one deliberately high-grade/low-wear **raw** copy as the decisive sensitivity test, and captures the per-book grade table (Mike to fill actual grades).

### TP RUN — cross-camera raw-book TP = 1/6 (FAILS); two fixes tried, BOTH REJECTED; single-image CEILINGED
- **Result: 1/6** same-book cross-camera pairs matched (`TPTests/{Pixel,iPhone}`, 6 issues, 1 raw copy each, front-only). A prior 4/6 was an **INVALID run** (all vision calls 401/502'd → quant-only; the harness now logs `align`/`low_evidence` and the operator checks cost>0 / no `vision=None` to catch this).
- **Diagnosis (Mike eyeballed Iron Man 200 — a human matches by defects):** (1) cross-sensor color/tone (iPhone richer, Pixel flatter) + (2) specular GLARE on the Pixel shot manufacturing a phantom corner defect → drives the arbiter's default-to-`different_copy` to a confident WRONG verdict.
- **Experiment 1 — glare/color PROMPT nudge: BUILT, RAN, REJECTED.** Added `marketplace_note` bullets (glare = no-data; cross-sensor color expected) + WHAT-TO-IGNORE lines, marketplace-scoped. Result: TP **unmoved at 1/6**; only turned one confident-wrong into uncertain-wrong (Heros) and pushed FP-side uncertainty 2→5 pairs (more mush, no accuracy). FP held 0. **Words don't fix it — reverted.**
- **Experiment 2 — PIXEL normalization + glare-mask + evidence floor: BUILT, VERIFIED, RAN, REJECTED.** Photometric LAB normalization (color) + specular-glare detection → skip glared crops (no-data, not de-weighted) + `exclude_mask` in dIoU/LPQ + `low_evidence` guardrail (a glare-starved pair is an un-judgeable capture, set aside — NOT a TP miss). Result: TP **1/6 unchanged, every miss `low_evidence=False` (clean evidence)** — these are clean-crop pairs the arbiter rejected. Iron Man **did not flip** (still `different_copy` 0.92) **despite E2 cleaning its pixels** (dIoU dropped 0.61→0.31, confirming normalization worked). FP held **0/6, crisp** (all different_copy 0.6–0.98, no mush) — E2 was SAFE but didn't help recognition. **Reverted to HEAD;** the normalization/glare helpers are filed in `EXPERIMENT2_DESIGN.md` for the multi-view lane.
- **REGISTRATION QUESTION CLOSED (learned-feature swap DEAD).** The `align`-column instrumentation showed every TP pair `align=True` with **1500–2200 SIFT inliers** — alignment is clean across the board. A SuperPoint+LightGlue / LoFTR swap would fix a stage that isn't broken; on CPU-only Render LoFTR is impractical (~5–15s/pair) and LightGlue adds ~200MB torch for no gain here. **Filed closed, not deferred — do not revisit absent new evidence.**
- **CONCLUSION (pre-committed, now triggered): single-image cross-camera raw-book recovery has hit its CEILING.** Two principled interventions (prompt, pixels) both null on clean-evidence pairs. The reject-bias that holds FP=0 and the failure to recognize true matches are the **same mechanism** — the arbiter genuinely cannot match wear across these cameras from single images. Stop single-image tweaking.

### ROADMAP REFRAME — three lanes by book type (this is the decision)
1. **Slabbed / high-grade → cert-number recovery (the marketable HEADLINE).** Wear-independent; the CGC/CBCS cert is already OCR'd/stored/indexed at grading — just needs the lookup endpoint wired (small build, no CV research). This is the recovery path for the high-value books.
2. **Raw + MULTI-VIEW capture → post-launch recovery build (PRIMARY raw-recovery path).** Single image is ceilinged; multiple controlled views (and the E2 normalization/glare helpers) are the path to raw-book recovery. Post-launch.
3. **Raw, single-image → provenance + monitoring framing only. NO recovery claim.** FP=0 makes it safe for "we recorded your copy" / monitoring, but TP=1/6 means it cannot promise "we'll match it back."

### NEXT
1. **Mike: commit the harness** (`git add scripts/slabguard_crosscamera_test.py`) — `align` + `low_evidence` instrumentation, both keepers. `routes/slab_guard_cv.py` is back at HEAD (E1/E2 reverted; the two safety fixes are already committed there — deploy to Render if not yet done).
2. Commit the docs (this log, `TP_RESHOOT_PROTOCOL.md`, `EXPERIMENT2_DESIGN.md`).
3. **Cert-number recovery lookup** = the next build (lane 1, the honest marketable headline).
4. Multi-view capture = the post-launch raw-recovery arc (lane 2).
5. Backs already deprecated (fronts-only); raw single-image stays provenance/monitoring (lane 3, no recovery claim).

---

## Session 109 (cont., Jun 22-23, 2026) — Opus 4.8 Slab Guard arbiter SHIPPED & DEPLOYED (commit 647bca2); cross-camera RECOVERY test fully set up (harness + capture protocol, pending Mike's photo shoot); recovery positioning decided

**Built draft-for-review; Mike ran all git/deploy + the Render-Events verify. Read LESSONS + cross-project at open. (Same session as the stacking step-1 work below — this is the Slab Guard / Opus half.)**

### Headline: the Slab Guard Vision arbiter is now Opus 4.8 (with real fallback), and the decisive cross-camera recovery test is built and waiting on Mike's photos.
A 4-brief read-only thread assessed what Slab Guard recovery can actually PROVE, reconciled the validation history, then shipped the Opus switch + the resilience fix. The recovery CLAIM is now gated on one number: the **cross-camera false-positive rate**, which Mike's photo shoot will produce.

### OPUS 4.8 ARBITER SWITCH — SHIPPED & DEPLOYED (commit `647bca2`, Render Events green)
- **What changed** (`routes/slab_guard_cv.py` + `models.py`, additive/surgical): the Vision arbiter `compare_covers_with_vision` now defaults to **Opus 4.8 via `call_with_fallback('opus')`** instead of a frozen direct `client.messages.create(model=SONNET)`. Two wins in one — **(a)** Opus is the default (forensic visual copy-discrimination is exactly its strength), and **(b)** the resilience fix: the whole cross-camera copy verdict rides on this ONE call, which previously had **NO fallback** (would 404 with no recovery if its head model retired, and the model string was frozen at import).
- `models.py` opus chain head bumped **4-6 → 4-8** (4-7/4-6 as fallbacks). Cost formula made **model-aware** ($5/$25 Opus default, $3/$15 if a Sonnet A/B override served it) so `cost_usd` is correct for BOTH harness arms. New **`arbiter_model`** field on the response for verification.
- An explicit `model=` override (the harness `--model`) still pins that exact model and bypasses the chain → the Sonnet-vs-Opus A/B works unchanged.
- **Cost reality (corrected from the brief's ~5×):** Opus 4.8 is **$5/$25** vs Sonnet **$3/$15** = ~**1.67×**, on a call that **barely fires today** — the shipped extension runs **quant-only** (`background.js` never sets `marketplace_mode`/`use_vision`), so the arbiter only fires on the manual `/api/monitor/compare-copies` path + the harness. Negligible cost. (If `marketplace_mode` is ever wired into the extension auto-scan, the arbiter fans out **once per hash-gate candidate per listing** — bound that fan-out then; flagged, not built.)
- Functional `arbiter_model=claude-opus-4-8` live check **deferred to the harness run** (didn't chase cover URLs for a curl today).

### SLAB GUARD RECOVERY ASSESSMENT (read-only — the thread that led to the switch)
- **Load-bearing answer — copy vs issue:** the hash gate (pHash+dHash+aHash+wHash) is **issue-level only**. Copy-level identity is attempted by SIFT edge-IoU + border inliers + LPQ + the Vision arbiter. Per the code's own docstrings these work **same-camera** but are **UNRELIABLE cross-camera** (the ACTUAL recovery scenario) — quant "CANNOT discriminate copy identity" cross-camera; Vision is primary there but validated on essentially **n≈1 same-copy cross-camera pair**.
- **Validation-history reconciliation (Mike's "lots of testing" vs my "n=1"):** BOTH true. Substantial testing happened but lives only as **prose** (CV docstring, ROADMAP, `SLAB_GUARD_CV_OVERVIEW.md`) — **zero committed structured result files**. It was mostly **cross-IMAGE / same-camera** (Mike re-shooting his own copies on one device — 6/6 there); the recovery-relevant **cross-CAMERA / different-device axis was never run as a controlled matrix** (its one data point was a single eBay photo that produced a false positive). Cross-image vs cross-camera is exactly what reconciles the two views.
- **Cert-number = the buried lede (strongest recovery vector, UNWIRED):** the CGC/CBCS cert is **already OCR'd** at grading (`comic_extraction.py`), **stored + indexed** (`comic_registry`/`collections`, dedicated index) and **displayed** in verify lookup — but it is **never matched on**. `find_matches()` keys only on hashes; no endpoint accepts a cert and returns a registered copy. Wiring it is the **lowest-effort, highest-reliability** slabbed-recovery feature — needs no CV research.

### CROSS-CAMERA HARNESS + CAPTURE PROTOCOL — READY (read-only, not wired to prod)
- `scripts/slabguard_crosscamera_test.py` — imports the live `compare_covers_with_vision` with `marketplace_mode=True`, serves Mike's local photos over a **localhost file server** (no R2 upload, no prod change), **bypasses the issue gate** (it passes for both TP and FP by design, so it isn't the discriminator), and prints a per-pair metric table + **true-positive and false-positive RATES** + total cost. Takes `--model` (the A/B) and `--csv`.
- **Capture protocol:** front cover of each (copy, phone). 5 issues × 2 copies × 2 phones = ~20 photos, named `issue<N>_copy<A|B>_phone<1|2>.jpg`. **Matte, untextured, contrasting background** (texture = the #1 false-positive cause — the one historical cross-camera FP came from background texture). Even light, no glare, square-on, full cover, ≥500px short side, two **genuinely different** phones. Shooting all 4 per issue yields ~10 TP + ~10 FP cross-camera pairs (real rates, not an anecdote).

### POSITIONING DECIDED (recovery-claim honesty)
- **Slabbed → cert-number = the honest, marketable recovery HEADLINE** (cert already captured/stored/indexed; small build to wire the lookup).
- **Raw / photo-matching stays provenance + monitoring framing** until the harness FP-rate proves cross-camera recovery. **Decisive metric = the cross-camera false-positive rate (different copy, same issue, must NOT match); want 0** — this number gates whether "recovery" can go on any GalaxyCon booth copy / pricing tier.

### NEXT — Mike's physical work (unhurried, its own block)
1. Source a clean **matte, untextured, contrasting** background (poster board / plain matte surface).
2. Confirm **ANTHROPIC_API_KEY + opencv** in the venv BEFORE shooting.
3. Shoot ~20 photos (5 issues × 2 copies × 2 phones, naming above).
4. Run the harness **twice** for the A/B: no `--model` (defaults to Opus 4.8 now) and `--model claude-sonnet-4-6`.
5. Read the **false-positive rate** (want 0); confirm `arbiter_model=claude-opus-4-8` in the default run.

## 2026-08-16 (evening) — VALUATION OUTAGE, cause found, three conventions changed

**MOST RECENT CHANGE: `/api/sales/valuation` went down and was rolled back. Cause was three bare
`%` characters in SQL COMMENTS, not the regex.** Supersedes the first two diagnoses recorded in
the working transcript, both of which were wrong and stated confidently.

### Live state at end of day — verified by real call, not inferred

| | state |
|---|---|
| valuation | **healthy** — Absolute Batman #1 @9.8 → `graded_fmv` 422.68, 445 comps |
| traceback logging | **live**, instrumentation only, verified |
| badge (MARGINAL state) | ⚰️ **REVERTED by `3f6148e` and NEEDS RE-APPLYING** — it was working and verified live; it came out while chasing the wrong cause |
| signatures | **held. Fix applied but UNCOMMITTED in `routes/sales_valuation.py`** — comments de-percented, pattern parameterised, verified through a live execute. ⚠️ Lost if the working tree is cleaned. |

### The outage

`/api/sales/valuation` returned `{"error":"list index out of range","success":false}` on every
book. Two log lines, 07:59:22 and 08:00:18 PM.

**Cause:** three bare `%` in SQL comments added by the signature unit — *"catches ~90% of the
shapes"*, *"(3.31%) at a $85.00"*, *"(82%) are a"*. psycopg2 percent-formats the **entire query
text, comments included**, so `% ` is a malformed format directive. Reproduced exactly: one
parameter → `IndexError`, two → `ValueError: unsupported format character ' ' at index 976`.

⚰️ **TWO DEAD DIAGNOSES — do not resurrect:**
- **DEAD:** *"the regex is correct SQL and fatal as a Python format string."* The pattern
  contains **no `%` at all**. **REASON:** a plausible mechanism was reported instead of the
  character being located.
- **DEAD:** *"parameterising the pattern is the fix."* **REPLACED BY:** cutting the `%` from the
  comments. Parameterising is in the new version as hygiene only. **REASON:** the pattern was
  never the fault.

**Why every check passed:** `py_compile` proved syntax, SQL spot-checks proved the predicate, and
neither executed the Python transport. The comments are valid SQL and fatal only at
`cursor.execute()`.

**Compounding error:** `3f6148e` reverted `app.html` (the badge), which cannot produce a
server-side JSON error. The signature change had shipped inside `95228f7` — a commit whose
message describes only documentation — because the ship block staged code and docs across a
numbered list with no per-commit boundary.

### ⚠️ THREE CONVENTION CHANGES — standing, apply to every ship block

1. **Self-contained commits with a stated expected file list.** Stage → `git diff --cached --stat`
   → verify against the list the block names → commit. Never a numbered list with implied
   boundaries: staging is cumulative, numbered steps read as sequential, and that gap put a code
   file inside a docs commit.
2. **Verify with an endpoint that exercises the change.** `/health` returned 5.6.0 throughout the
   outage — it is structurally incapable of detecting a valuation fault, not merely a weak check.
3. **One live call through the real path before a block is written.** Not `py_compile`, not a SQL
   spot-check, not a `cur.execute` — those proved things that were true and irrelevant. Mike makes
   the call.

Also now standing: `git log origin/main..HEAD` before assembling any block (a committed-but-unpushed
change is still unshipped and still needs deploy/purge), and **every block names a verification
cell with a before and after figure**.

### Already answered — item 3 needs a re-read, not a re-run

**Two defects, not one, plus a third:**

| # | defect | rows | family |
|---|---|---|---|
| 1 | `CGC 98` parsed as grade **98.0** — 29 rows, all `graded=true`, all reach the ladder | 29 | grade parsing |
| 2 | **later printings** (`9th Print`, `11th Print` at $15–28) pooled with first prints | unmeasured | printing identity — **new gap**, `is_reprint` does not cover it |
| 3 | `Absolute Batman Annual #1` / `Ark-M #1` collapsing into the base title | unmeasured | `canonical_title` — same family as Wolverine |

The $9.00 sales are **not lots and not misparsed grades** — they are real graded sales of later
printings and adjacent titles. Absolute Batman #1's 9.8 bucket spans **$15.50 to $4,799**.

### Next session, in order — nothing starts until Mike says
1. **Re-apply the badge.** Good change removed for nothing. Needs **`purge`, not `deploy`.**
2. **Signatures** — fix already applied and uncommitted; block written only after Mike's live call.
3. **Price-curve findings** — answered above; confirm rather than re-measure.
4. **Capture-schedule measurement** — daily row counts, per-key depth against §1's stopping rule,
   grade-bucket depth on cleared keys, and what the marginal row buys. ⚠️ The fourth item arrived
   truncated mid-sentence and needs restating.

---

## 2026-08-17 — ✅ BADGE AND SIGNATURE FILTER BOTH LIVE AND VERIFIED

**MOST RECENT CHANGE: the badge is re-applied and the signature filter is deployed. Both
verified in production, 2026-08-17.** Supersedes the 2026-08-16 queue items 1 and 2 below.

⚰️ **DEAD: "1. Re-apply the badge. 2. Signatures — fix already applied and uncommitted."**
**REPLACED BY:** badge live at `9a1d2d3` (purged and asserted); signature filter live via
`8200374` + `8ae4187` (deployed, cell verified).
**REASON:** both executed today. **SUPERSEDES** any instruction to re-apply or re-commit either.

### What shipped, in three un-bundled blocks

| commit | what | ship path |
|---|---|---|
| `8ae4187` | raw-side signature comment corrected | rode along, no separate deploy |
| `c2877cb` | the 2026-08-16 outage record | docs only |
| `9a1d2d3` | badge re-applied (revert of `3f6148e`) | `purge`, not `deploy` |

`8200374` (the filter itself) and `6d7b0d9` (the anthropic pin) had been sitting **local and
unpushed** and went out with the first push. ⚠️ The tree was described at session open as one
local commit ahead of origin; `git log origin/main..HEAD` showed **four**. Check the range, do
not trust the recollection — L-SW-2026-008.

### Verified

- **Badge:** post-`purge` assert on `slabworthy.com/app.html` — `MARGINAL_ROI_CEILING` ×3
  present, `roi > 0 ? 'WORTH THE SLAB'` absent. Both directions, per L-SW-2026-022. The
  precondition was gated on an origin read with a cache-buster (`cf-cache-status: DYNAMIC`)
  rather than on the dashboard, which confirms a build finished but not what the origin serves.
- **Signature filter:** Absolute Batman #1 @ 9.8 → **`graded_fmv` $345.00 exactly as predicted**,
  `fmv_method: exact`, `confidence: high`, `verdict_basis: supported`, 321 comps.

### ✅ SETTLED — the 321-vs-323 gap. It was the pool moving, and the direction is right.

Measured read-only as `do_readonly`, both queries extracted from the live module source at
runtime and differing **only** by the two signature lines, with the variant exclusion added to
both to mimic the Python partition (L-SW-2026-024 rules 3a and 3d):

| | recorded 2026-08-16 | measured 2026-08-17 |
|---|---|---|
| pre-filter (signature clauses removed) | 445 | **446** |
| post-filter (production predicate) | 323 predicted | **322** |
| removed by the filter | 122 predicted | **124** |

**The pre-filter count is NOT still 445.** The pool gained a row and the filter removed two more
than predicted, which is what a live rolling 365-day window over an actively-captured corpus
does. Nothing else took two comps. **Do not re-derive this.**

⚠️ **A SMALLER, DIFFERENT GAP IS OPEN AND IS NOT THE ONE ABOVE.** The SQL reconstruction returns
**322** where the live endpoint returns **321**, and the two were read **near-simultaneously in
the same script**, so drift is excluded as the explanation. The direction is the interesting
part: `graded_sample_size` is `exact_count = len(exact_match)` over grade buckets built from the
**union** of eBay and market rows, so production should be **≥** an eBay-only count, not one
below it. Unexplained. One row against an exact median — recorded, not chased.

### 🆕 NEW — the signature filter does not cover `market_sales`, and that is not a schema limit

| query literal | `is_signed` | pattern param |
|---|---|---|
| `ebay_graded_query` | ✅ | ✅ |
| `ebay_raw_query` | ✅ | ✅ |
| **`market_graded_query`** | ❌ | ❌ |
| **`market_raw_query`** | ❌ | ❌ |

`market_sales` **has both `is_signed` and `raw_title`** (confirmed against
`information_schema.columns`), so this is uncovered scope, not an impossibility.

⚠️ **The shipped comment is a trap for the next reader.** It says *"Applied to BOTH pools
deliberately. Filtering one side would subtract a signature-excluded median from a
signature-included one."* The "both pools" it means is **graded and raw within eBay**. There are
four pools and two are unfiltered — which is the very asymmetry the sentence argues against.
Blast radius is small today (Whatnot contributed 4 rows to the verification cell against 1,695
from eBay) but the sentence will read as full coverage. **[[L-SW-2026-020]]: the label is the
defect.**

### 🆕 NEW — the grade 1.0 at $529.99 is a grade misparse, NOT a signature residual

Pulled under the production predicate, as asked:

```
grade 1.0   $529.99   is_signed=False   sold 2026-07-30
   "Absolute Batman #1 CBCS 1st Print Not CGC"
```

The title carries **no grade at all**. `CBCS 1st Print` was read as **CBCS 1**, so a book that
sold for a high-grade price landed in the 1.0 bucket and sat above the 9.8 median. It is
**not** the seventh vocabulary shape — `SIGNED_TITLE_PATTERN` did not miss it, because there is
nothing to miss. Same family as the already-recorded `CGC 98` defect (29 rows, line ~2668):
**the grade parser reading a token that is not a grade.** Two distinct sub-shapes now:
notation shorthand (`CGC 98`) and ordinal collision (`CBCS 1st`).

### Confirmed, already recorded — not new findings

- **`CGC 98` → grade 98.0.** Live in the price curve on this cell. Already at line ~2668, 29 rows.
  Verified still present, not re-diagnosed.
- **The $9.00 sales at 9.4/9.6.** Already recorded as later printings and adjacent titles. One
  detail to add: they returned **zero rows from `ebay_sales`** — they are in **`market_sales`**,
  and two of them carry `title='Absolute Batman'` against `series='New Mutants'`. The first
  query looked in one table and found nothing, which is [[L-SW-2026-014]] in textbook form.
- **`nearby_thin_comps: 42` on a `supported` cell.** The non-9.8 buckets sum to exactly 42
  (1+1+5+3+5+26+1). This is **[[L-SW-2026-020]] instance 4 sitting in a live payload** — the
  field sums all nearby buckets, so it is correct inside `low_support` and misnamed everywhere
  else, and this response is everywhere else. Mike's framing: better evidence than the
  description of it.

### Process note — two Claude errors in the ship blocks, both caught by the terminal

1. A **bash heredoc** (`<<'MSG'`) handed to PowerShell. Every line errored; nothing committed.
2. Worse, and only exposed because the heredoc failed first: the block used
   `git commit --amend` to target `8200374`, which is **four commits back**. `--amend` rewrites
   `HEAD`. It would have renamed the docs commit into a valuation-fix commit. The amend was
   dropped for an ordinary follow-up commit (`8ae4187`).
3. Blocks 1 and 2 then **silently no-op'd** because the `git add` and `git revert` were written
   in prose beside the block instead of inside it. Mike had asked for self-contained blocks.
   **Standing: a ship block contains every command including staging, or it is not a block.**

### 🔴 TOMORROW OPENS HERE — two of four pools, and the comment is the seventh instance

**Mike's framing, 2026-08-17: "a wrong comment inside the fix for a wrong comment, which is the
seventh instance and the most self-referential one yet."** [[L-SW-2026-020]] rule 4 says the fix
for a mislabel is the likeliest place to commit the next one. This is that, one level deeper:
`8ae4187` was a commit whose *entire purpose* was correcting a false comment on this filter, and
it left standing a sentence that overstates the filter's coverage.

Blast radius today is 4 Whatnot rows against 1,695 eBay on the verification cell. **`market_sales`
is 10,048 rows and growing, and the comment is what a future reader will trust.**

### ✅ SCOPING MEASURED 2026-08-17 — the answer is NO, do not just extend the filter

Both of Mike's questions, measured read-only as `do_readonly` against the full tables. Pattern
read from the live module source, not retyped.

**(a) Does `is_signed` behave the same way on Whatnot data? — Populated, but at 1/6 the rate.**

| | rows | `is_signed` TRUE | rate | NULL |
|---|---|---|---|---|
| `market_sales` | 10,048 | **69** | 0.69% | 0 |
| `ebay_sales` | 271,344 | 11,842 | 4.36% | 0 |

Not a dead column — it is set, never null. But 65 rows match the literal word `signed` in
`raw_title` against 69 TRUE, so on Whatnot `is_signed` is **essentially just the literal word**.
The eBay derivation's other half — the `SS` group in `(CGC|CBCS|PGX) SS <grade>` — has almost
nothing to bite on, because Whatnot titles do not carry slab notation.

**(b) Are the vocabulary shapes the same? — NO. Half of them have ZERO hits.**

| shape | eBay | `market_sales` |
|---|---|---|
| sketch | 172 | **8** |
| sig | 52 | **0** |
| COA | 43 | **16** |
| auto | 30 | **0** |
| autograph | 7 | *(in auto)* |
| remarque | 7 | **0** |
| **pattern total** | — | **28 of 10,048** |

**The mechanical reason: Whatnot titles are 5× shorter.** Median `raw_title` length **14 chars
vs eBay's 71** (mean 18 vs 66). The vocabulary was enumerated against 66-character listing
titles dense with condition and grading tokens. A 14-character title has no room for those
shapes, which is why three of six return zero.

**🔴 AND THE PART THAT ACTUALLY BLOCKS EXTENDING IT — on Whatnot, "sketch" does not mean
signature.** The 12 highest-priced pattern hits, read directly:

```
$715  DJC Adventurous Astronaut Sketch Card            <- a sketch CARD, not a comic
$715  DJC Adventurous Astronaut Sketch Card            <- (duplicate row)
$499  2026 Under Wraps Autographed NFL Jerseys ... x4  <- NFL JERSEYS, not comics
$315  HAUNT #1 (1:100 RATIO) TODD MCFARLANE SKETCH VARIANT   <- a VARIANT COVER
$255  KING SPAWN #50 ... SIGNED BY TODD MCFARLANE ... SKETCH CVR  <- genuinely signed
$250  Live sketch cover #2                             <- a sketch COVER edition
$200  Todd Beats sketch #1                             <- a sketch COVER edition
$100  SIGNED BOOK with COA #72                         <- genuinely signed
$40   SIGNED BOOK with COA                             <- genuinely signed
```

On eBay, `sketch` was enumerated as a signature-adjacent shape. **On Whatnot it predominantly
denotes a SKETCH COVER — a variant edition — or a sketch card, which is not a comic.** Applying
the eBay pattern to `market_sales` would exclude variant editions under a *signature* rationale.
That is a wrong label attached to a correct-looking exclusion, i.e. the exact class CP-1 exists
to close, committed while closing it. **Do not port the regex.**

**Directional signal, for whenever the market unit is scoped:** 76 rows would be excluded
(`is_signed` OR pattern) at a **$25.00 median against $5.00** for the 9,972 that remain — a 5×
premium, matching the eBay raw side's 5.3× ($85.00 vs $16.05). The *premium* transfers even
though the *vocabulary* does not.

**🆕 SEPARATE FINDING, NOT MEASURED — non-comic rows in the corpus.** **6 of those 12** are not
comics (2 sketch cards, 4 NFL jersey boxes). Whatnot streams sell more than comics and the
capture is taking them. Stated with its N and **not** generalised: this is 6 of 12 in a
price-sorted slice of 28 pattern hits, **not** a corpus-wide rate. It needs its own measurement
before anyone quotes a number.

**Recommended shape for tomorrow:** fix the comment (Mike's stated minimum), then treat the
market side as **its own unit** — likely `is_signed` alone plus a Whatnot-specific vocabulary
derived from Whatnot titles, never the eBay pattern.

### ⚰️ THE RESIDUAL LIST HAS ZERO CONFIRMED MEMBERS

`8200374`'s comment predicted: *"Residual after this is the shapes nobody has enumerated yet."*
The first candidate was pulled today and **it is not a signature shape at all.**

**Recorded plainly at Mike's direction: the prediction that residual signature shapes would
surface has NOT been borne out by the first candidate.** One candidate is not a refutation, but
the list stands at **0 confirmed members** and should be described that way rather than as a
known-nonempty backlog.

### 🆕 A PATTERN, NOT A ONE-OFF — the grade parser reads adjacent text as a grade

Two measured instances, same shape:

| title | parsed as | truth |
|---|---|---|
| `Absolute Batman 1 Nick Dragotta Cover ... CGC 98 G2U` | grade **98.0** | seller shorthand for 9.8 · 29 rows |
| `Absolute Batman #1 CBCS 1st Print Not CGC` | grade **1.0** | **no grade in the title at all** · 1 row |

Sub-shapes: **notation shorthand** (`CGC 98`) and **ordinal collision** (`CBCS 1st` → `CBCS 1`).
Mike: *"two instances of the same shape — a grade extracted from adjacent text — and that is now
a pattern rather than a one-off."* Same consumer, likely one fix. The 1.0 row is the more
dangerous of the two: it carried a real high-grade price ($529.99) into the 1.0 bucket, where it
sat **above the 9.8 median** and looked exactly like the signature inversion the day's filter was
built to remove.

### ✅ NEAR MISS RECORDED — [[L-SW-2026-014]] avoided, not committed

The `$9.00` outlier pull returned **zero rows from `ebay_sales`**. The zero was **not reported as
a finding** — `market_sales` was checked next, and that is where the rows were.

Recorded at Mike's direction: *"a near miss recorded is worth as much as an instance."* The
tell that prompted the second query was [[L-SW-2026-014]] itself — the live response carried
`sources: {ebay: 1695, whatnot: 4}`, so a zero from one table could not be an answer about a
two-table corpus. Also an instance of [[L-2026-024]] working as intended: an empty result was
treated as a probe that could not have fired, rather than as evidence.

### Queue, in order

1. **Fix the "BOTH pools" comment** in both eBay query literals — say *graded and raw within
   eBay*, and state that the market pools are unfiltered. Comment-only, no behaviour change.
2. **Market-side signature unit** — scoped fresh per the measurement above. Not a port.
3. **Grade-parser defects** — `CGC 98` (29 rows) and `CBCS 1st` (1 row). One consumer.
4. **Non-comic rows in `market_sales`** — measure the rate before quoting one.
5. The 322-vs-321 reconstruction gap, if it ever matters.

---

## 2026-08-17 (later) — 📊 CAPTURE SCHEDULE MEASURED. Saturated AND the wrong list — same cause.

**MOST RECENT CHANGE: the §2 tracker specified in the capture schedule has been built and run.
ALL 34 measured scheduled keys have CLEARED §1's stopping rule, including all 9 "starved" §2A
keys and all 10 §5 bench keys meant to replace them.** Answers the question truncated from
yesterday's message. Nothing changed in the schedule — this is measurement only.

Measured read-only as `do_readonly` through the **production predicate**, extracted from the live
module source, with the variant exclusion the Python partition applies (L-SW-2026-024 rules 3a
and 3d). These are pool-eligible counts, not table counts.

### The question was: saturated, or walking the wrong list? — **Both, and they are one cause.**

⚰️ **DEAD (as a hypothesis): "duplicates mean eBay's 90-day window stopped producing."**
**REPLACED BY:** the walked keys are *finished*, and the retirement rule was never executed
because §2A says *"retire the moment a key clears"* and the tracker to detect clearing was
specified and never built. **REASON:** every key on the list has cleared, so every additional
walk of it can only return rows already held.

### 1. Daily new rows — smooth decline, not a cliff. Saturation confirmed.

Row counts alone are noisy (they track how long Mike walked that day). The discriminating
measure is **what share of the keys touched each day had never been seen before**:

| day | rows | keys touched | NEW keys | new-key share |
|---|---|---|---|---|
| 08-02 | 24,454 | 7,122 | 4,096 | **57.5%** |
| 08-03 | 20,712 | 8,484 | 5,323 | 62.7% |
| 08-05 | 36,961 | 15,941 | 9,284 | 58.2% |
| 08-08 | 3,741 | 1,564 | 786 | 50.3% |
| 08-12 | 15,777 | 4,361 | 2,036 | 46.7% |
| 08-14 | 12,082 | 1,722 | 512 | 29.7% |
| 08-17 | 4,830 | 1,568 | 472 | **30.1%** |

**Monotonic 58% → 30%. A smooth decline is saturation; a cliff would be something breaking.**
No cliff. ⚠️ Two things the row counts also show: **zero rows 2026-07-18 → 08-01** (a 15-day
gap inside the 30-day window), and **no rows at all on 08-09, 08-10, 08-13, 08-15**. Operating
note 6 says a week with no new rows is a signal.

⚠️ **THE DUPLICATES ARE NOT BEING STORED — the dedup is working.** `ebay_sales` holds 271,344
rows against **271,344 distinct `ebay_item_id`**, zero nulls, under a `UNIQUE` index. The
copies-per-item histogram is a single bar at 1. The extension's dupe counter is reporting
correct rejections. **199,692 rows still landed in 30 days — 73% of the whole table** — so
capture is not dying; it is walking a finished list while the broad result pages keep feeding
adjacent keys.

### 2. Per-key depth vs §1's stopping rule — 34 of 34 CLEARED

| block | rule | cleared | new rows/30d |
|---|---|---|---|
| §2A starved (9) | ≥10 comps, ≥5 graded | **9 of 9** | 424 |
| §2C blue-chip (15) | ≥10 comps, ≥5 graded | **15 of 15** | 3,007 |
| §5 bench (10) — *never walked* | ≥5 comps, ≥2 graded | **10 of 10** | 458 |

The §2A block was built from the 2026-06-08 audit's weak set. Every entry has been transformed:
**Incredible Hulk #180 went 2 comps / 0 graded → 238 comps / 109 graded. Batman #227 went 1/0 →
105/42.** The block did its job and should have been emptied.

**§5 is not a source of new keys either.** All ten bench keys already clear their target without
ever having been walked — they fill from adjacent search results. Promoting one buys nothing at
book level.

**§2B is the only block with genuine holes, and they are precise:** `Absolute Superman` and
`Absolute Wonder Woman` have **zero graded comps at issues 2, 5, 6, 9, 11, 12 and 2, 3, 8, 9, 12**
respectively. Recent books simply have few slabbed sales yet. `Absolute Batman` is deep
throughout (#1 = 1,543 comps / 362 graded).

### 3. 🔴 GRADE-CELL DEPTH — Mike called this right, and it is the real question

**Across the 24 cleared §2A+§2C keys, 72 of 168 slab cells (43%) hold fewer than 5 graded comps**
— below the CI-suppression line §1 was written to clear. The book-level rule is satisfied and the
grade-level product is not.

But the thin cells split into **two populations that must not be treated the same:**

**(a) Thin because the census is thin — capture CANNOT fix these.** Every pre-1980 key is empty
or near-empty at the top: Iron Man #55, Captain America #117, Batman #227, Batman #232, X-Men #94
all hold **zero** comps at 9.8. Incredible Hulk #180 and #181 hold **one**. A 1971 Batman in 9.8
barely exists, so no amount of walking produces the sale. Meanwhile every post-1983 key is deep —
Detective Comics #880 (2011) has 10 at 9.8, ASM #361 (1992) has 44, New Mutants #98 (1991) has 56.
**The split is by publication era, measured across all 24 keys, not by how hard the key was
walked.**

**(b) Thin because the pool is CONTAMINATED — and these read as the deepest cells on the board.**

### 🔴🔴 THE FINDING — the two most famous keys in the schedule are valued from the wrong books

`Action Comics #1` and `Amazing Fantasy #15` both sit in §2C Daily Core. Both looked healthy
(11 and 13 comps at 9.8). Pulled and read directly:

**`Action Comics #1`, 13 graded comps at 9.6+, ZERO of them the 1938 book:**
```
$250.00  Action Comics #1, CBCS 9.8, White Pages
$219.95  Action Comics # 1  1976 DC Comics CGC 9.8 ... Safeguard Promotional   <- 1976 reprint
$196.13  Action Comics Vol 1 484 CGC 9.8 (NM/M) (1978)          <- "Vol 1" parsed as issue 1
$112.00  Action Comics Annual #1 CGC 9.8 1987                   <- ANNUAL, different book
$96.00   Action Comics #1 (2025) Natali Sanders ... Ltd 800     <- 2025 relaunch
$79.99   Action Comics #1 Loot Crate Edition CGC 9.8
$75.00   Action Comics # 1 / DC Comics / The New 52 / CGC 9.8   <- 2011 relaunch
$39.99   Action Comics Special #1 CGC 9.6
```

**`Amazing Fantasy #15`, 24 graded comps at 9.6+, essentially none the 1962 book:**
```
$1700.00 Marvel Milestone Edition Amazing Fantasy #15 CGC 9.6 SS Lee 1992  <- 1992 reprint
$1499.99 Amazing Fantasy #15 Pure Silver (2018) CGC 9.9 Artist Proof       <- METAL REPLICA
$250.00  AMAZING FANTASY #15 CGC 9.8 - 1st Amadeus Cho          <- the 2004 series, x5 total
$199.99  Amazing Fantasy #15 Facsimilie Edition CGC 9.8         <- MISSPELLED, filter misses it
$165.00  Amazing Fantasy #15 | CGC 9.6 NM | 1st Spider-Man      <- a real AF15 9.6 is $3M+
```

**Five distinct defects, all visible in one pull:**

| # | defect | example | family |
|---|---|---|---|
| 1 | **year/edition not in the comp key** | 1938 / 2011 / 2025 Action #1 pooled as one | already logged, ⚠️yr §7.4 |
| 2 | **`Annual` / `Special` collapse into the base title** | `Action Comics Annual #1` → `#1` | `qualifier_title_clause` gap |
| 3 | **`Facsimilie` misspelling defeats `%facsimile%`** | AF15 facsimile at 9.8 | filter is exact-substring |
| 4 | **reprint editions not caught by `%reprint%`** | `Marvel Milestone Edition`, `Safeguard Promotional` | vocabulary gap |
| 5 | **issue parsed from adjacent text** | `Action Comics Vol 1 484` → issue **1** | ⚠️ **same family as today's `CBCS 1st` → grade 1.0 and `CGC 98` → grade 98** |

**Defect 5 is the third instance of a pattern found twice already today.** The grade parser reads
adjacent text as a grade; the issue parser reads adjacent text as an issue. One shape, two fields.
[[L-SW-2026-016]] at the extraction layer.

⚠️ **Why this outranks the capture question entirely:** these are not thin cells, they are
**confidently wrong** cells, on two of the most recognisable comics in existence, sitting in the
Daily Core precisely because they are high-traffic lookups. And the contamination makes the pool
look **deeper**, so every depth metric — including §1's stopping rule and the tracker above —
scores them as healthy. **A key can clear the rule on comps that are not the book.**

### 4. Is §4 inert? — Mike's conclusion is RIGHT; his reason needs one correction

⚰️ **DEAD: "demand promotions cannot fire without cold traffic, so §4 is inert."**
**REPLACED BY:** §4 fires nothing — **the promotion query run verbatim returns 0 promotable
rows** — but **not because the table is empty.** `lookup_demand` holds **1,453 rows, 1,420 of
them `is_internal = false`, 195 in the last 30 days, most recent today.**
**REASON:** `is_internal` is written from whatever the caller passes (`lookup_demand.py:62`,
`bool(f.get('is_internal'))`), so "external" does not mean "cold traffic". The top demand rows
are **Whatnot stream titles**: `Flat Rate Box (Shown LIVE) #86`, `Fernanco-Silver, Bronze 🔥`,
`7 oz #58`, `Flipmode Modern Comic`. Nothing clears the ≥5-lookups/week bar; the highest is 2.

**So the operational conclusion stands — §4 promotes nothing — and the record should not say the
table is empty, because someone will check and find 1,420 rows.** [[L-2026-023]]: a field is
defined by its writer, not its name. **🆕 Side finding: `lookup_demand` is being polluted by
non-comic Whatnot stream titles**, which will corrupt the ranking the moment real traffic arrives.

### What this means for the walk — reported, NOT a new schedule

1. **§2A should be emptied.** All 9 cleared. The rule said retire on clearing; nothing retired
   because nothing measured. **The tracker is the missing mechanism, not the list.**
2. **§5 does not backfill it.** All 10 bench keys already clear. Promoting from the bench is a
   lateral move.
3. **The remaining real capture gaps are narrow:** `Absolute Superman` and `Absolute Wonder
   Woman` interior issues at zero graded, and the §3 Sunday tail (unmeasured here).
4. **The largest available win is not capture at all** — it is the five identity defects above.
   Walking `Action Comics #1` again adds more wrong books to a wrong pool.

### Queue additions

6. **🔴 Comp-pool identity defects** — the five in the table above, ranked over further capture.
   Start with `Annual`/`Special` collapse and the `Facsimilie` misspelling; both are cheap.
7. **Build the §2 depth tracker** as a real artifact so retirement can fire ([[L-SW-2026-017]] —
   a step with no observable output is indistinguishable from one never taken).
8. **Grade-cell targets** to replace the book-level rule, split by era so pre-1980 keys are not
   chased toward 9.8 cells that do not exist.
9. **`lookup_demand` pollution** — Whatnot stream titles are entering the demand table.

---

## 🛑 STOPPING POINT — 2026-08-17. TWO UNITS SCOPED AND APPROVED. NOTHING RUNS.

**MOST RECENT CHANGE: Unit A and Unit B are scoped, approved in shape, and EXPLICITLY NOT
STARTED. Mike, 2026-08-17: "DO NOT START Unit A or Unit B. Nothing runs until I am back."**
This supersedes any reading of the capture work as in-progress. Nothing is half-done; nothing
is waiting on a partial state.

### ⛔ THE INSTRUCTION, ahead of everything else

**Do not begin Unit A or Unit B.** Both are fully scoped below so that a future session can
recognise them — **not so it can start them.** If a session opens and finds this entry, the
correct first action is to ask Mike, not to proceed.

### THE UNITS — carried forward unchanged from Mike's own wording

| unit | contents | risk |
|---|---|---|
| **Unit A** | mangled-title fixes **1 + 3** (stop-word stripping; prefix stripping) **+ backfill** | pure recovery — **no production FMV moves** |
| **Unit B** | fix **2** (publisher stripping) **+ backfill + corpus-wide FMV price audit** | **un-merges live pools** |

⚠️ **BINDING CONSTRAINT — code fix and backfill are ONE unit, always.** Shipping a fix alone
splits every affected book into **two** pools, which is worse than the single wrong pool it has
today: all three code fixes are forward-only, and 271,344 existing rows keep the mangled
canonical. There is no "fix now, backfill later" version of this work.

⚠️ **The backfill script goes in `scripts/`, never `docs/`** (`.dockerignore` excludes `docs/`),
**and needs a `deploy` to exist in the container even though it serves nothing**
([[L-SW-2026-023]]).

### 🎁 THE VERIFICATION INSTRUMENT — use it explicitly, not as background

Re-running the **current, unchanged** normalizer over the retained `raw_title` reproduced the
stored `canonical_title` on **6,000 of 6,000 sampled rows — zero differences, zero errors.**

**The baseline is proven flat, so every row that changes after a fix is attributable to that fix
alone.** That is the differential control [[L-SW-2026-011]] normally requires *constructing*, and
here it exists for free. Mike's direction: **use it as the instrument, not as a footnote.**

- **Both units:** before/after row counts by `canonical_title`.
- **Unit B additionally:** before/after **FMV, corpus-wide** — it changes the value of pools that
  are being priced in production today, so a name diff is not sufficient.

Two further consequences worth keeping: the defect is **entirely in current code** (no
archaeology needed), and the backfill is a **pure, idempotent function of `raw_title`**, so
running it twice — once per unit — is safe.

### ✅ ON RECORD AT MIKE'S DIRECTION — §1a: the right answer was that it cannot be written

Asked to amend a rule, the outcome was to **establish that it cannot be written yet**, with the
counterexample that kills the obvious repair.

- A single consistent year **is not the right year**: ASM #2 and #3 pass the check cleanly at a
  uniform **2014** on a **1963** comic.
- **Modal year is worse than refusing.** X-Men #1 holds **244 rows of the 1991 relaunch against
  27 of the 1963 book**, so modal would **bless the contamination as canonical and then discard
  the 27 real rows.** Mike: *"I would not have caught that before shipping it."*
- Measured at scale: **52 of 108** #1 keys have an unsafe modal year. TMNT returns **1988 on 17%**
  of rows for a **1984** comic.
- **What would work, and why it is actionable rather than a dead end:** the year must come from
  **outside the pool**, because the pool is the thing under suspicion. **Production already has
  such a source** — the grader reads the publication year off the photographed cover and passes it
  to the valuation. **The capture tracker does not**, because the key list has never carried years.
  The weekly list now carries a year for the 24 #1s the data supports, which is the start of one.

### ✅ SAME SHAPE, CAUGHT EARLIER — the years-on-#1s correction

The first version derived every #1's year from the pool's modal `title_year`. Unsafe on 52 of 108.
Now printed **only** where one year holds ≥80% of the pool with spread ≤15 years — **24 of them** —
and blank with a stated reason otherwise. **A wrong year in a search is worse than no year.**

⚠️ **Mike, recorded because he named it: "Second time today you have proposed something, measured
it, and withdrawn it before it reached me. That is the cycle working."** The other instance the
same day: a mangled-title population of **14,861** rows, withdrawn before it reached a commit —
it matched any `raw_title` containing "of" anywhere, so `Amazing Spider-Man` at 1,884 rows was a
false positive. Corrected figure: **6,815 across 20 titles, stated as a floor.**

### QUEUED BEHIND THE TWO UNITS

**Grade and issue parser defects — three instances of one pattern**, both parsers reading
adjacent text as their own field:

| input | read as | truth |
|---|---|---|
| `... CGC 98 G2U` | **grade 98.0** | seller shorthand for 9.8 · 29 rows |
| `Absolute Batman #1 CBCS 1st Print Not CGC` | **grade 1.0** | no grade in the title at all |
| `Action Comics Vol 1 484` | **issue 1** | issue 484 |

Then, unchanged from earlier today: the "BOTH pools" comment fix, the market-side signature unit
(scoped fresh, **not** a port of the eBay regex), non-comic rows in `market_sales`, `lookup_demand`
pollution by Whatnot stream titles, and the 322-vs-321 reconstruction gap.

### WHAT SHIPPED 2026-08-17

Badge re-applied and purged; signature filter deployed and verified live (Absolute Batman #1 @ 9.8
→ **$345.00**, the predicted figure exactly); the capture schedule amended; and
`docs/EBAY_CAPTURE_WEEKLY.docx` created as the operating sheet — **147 searches a week, derived
from measuring all 292 rotating keys** rather than from what sounds scarce.

Mike's closing assessment, recorded: *"The audit overturned the premise the whole capture schedule
rested on, and the schedule that replaced it is derived from measurement rather than from what
sounds scarce."*

---

## 🛑 STOPPING POINT — CP-1 valuation arc, 2026-08-16

**MOST RECENT CHANGE: the CP-1 bug-hunt arc is CLOSED and the roadmap resumes.** Everything
below is queue, not chase. A future session should NOT re-derive this decision or re-open these
items as discoveries — they are measured, recorded, and deliberately deferred.

### Fixed and live
- **Lot-range leakage** (`499371b`) — the multi-issue range filter bounded the second number as
  `\d{2,4}`, so `#1-4` and `#1-8` sailed into single-comic pools. 2,405 rows live, 244 ≥$100.
  Four measured guards. **Verified in production: Wolverine LS #1 raw $150 → $125.**
- **Badge third state** (`9b1a5d8`) — the client collapsed the server's three verdicts to two on
  `roi > 0`, so a $16 gain rendered the same green as $1,200. ~29% of confident recommendations
  are under $50. No new threshold: 50 is the server's own boundary, restored not invented.
- **edition_span / multi_edition split** (`9ab7cc3`).

### Scoped, drafted, HELD — not cancelled
- **Signatures** — `is_signed` + six enumerated shapes, query-time, both pools. 115 cells lose
  rateability, −$28.80 average graded median. **Held deliberately:** it pushes 114 cells below
  the evidence bar and those cells live in the thin population, so it makes the thin-bucket
  problem worse while that work is unbuilt. Ships after.

### Measured, NOT BUILT — no code exists for either
- **True cost of grading.** `grading_cost = 30` is flat and wrong by 2–4× at the low end — a $50
  book costs ~$71 to grade (142% of its value). Moves **24.9% of WORTH verdicts** off WORTH.
  Shape: `tier(V) + shipping(V) + flat + expected_loss(V)`; only tier, insurance and loss scale.
  ⚠️ The expected-loss term is **negligible** ($0.01–$0.50, i.e. 0.01–0.39% of cost) — the tail
  risk is priced as the *insurance premium* inside shipping, not as loss. ⚠️ **CGC's published
  fee pages 404'd; every figure is an estimate and none is sourced.**
- **Uncertainty framework.** Three layers — estimator / uncertainty / decision — because ROI is
  downstream of the estimate, so a single `f(depth, roi)` is circular. 47.4% of graded cells have
  **no CI at all** (`bootstrap_ci_median` returns `(None, None)` below 5 values) and the raw side
  has none at any depth, while **over half of raw pools hold fewer than 5 sales**.
  **Binding design constraints, agreed:** both stochastic terms resampled (graded *and* raw), the
  cost term stated as fixed explicitly rather than by omission, and the widening factor derived
  from the hold-one-out table rather than chosen. Hold-one-out is the working instrument: at k=4
  the median error is 6.7% but **1 in 8 exceeds 25% and p99 is 157%** — the damage is in the tail,
  which is why both ladder-shape proxies (inversion, residual) missed it. That table is a **lower
  bound**: it is sampling error on liquid books, and genuinely thin buckets are thin because the
  book does not trade.

### Known STRUCTURAL gap — named as such, not a bug
- **Grade uncertainty.** *(Mike's observation, 2026-08-16.)* The framework resamples comps and
  treats the assigned grade as **exact**. A half-point grade miss moves more value than the entire
  cost model. This is not calibration and not a defect in existing code — it is a dimension the
  design does not model at all.
  ⚠️ **Second thread pointing at the same measurement:** the grading-consistency work, for which
  **Joseph Vicario's 25 pinned `grade_submissions` were preserved** (pin before 2026-11-04). Those
  two threads should meet.

### Queued, unchanged — measured populations, no new information needed to start
- `canonical_title` splits — Wolverine #1 under **three** keys while the `Wolverine` key merges
  1982 ($150, 156 rows) with 1988 ($59.99, 113 rows). First confirmed instance; the Invincible
  case was retracted.
- Issue-number absorption — 22,623 raw rows with NULL `issue_number` (10.6%), unreachable by any
  issue-filtered lookup. Split between legitimate (trades, omnibuses) and parse failure is
  **unmeasured and is the queue item's first task**.
- PSA + six graders missing from Unit 1a's regex — PSA alone is 410 rows, larger than PGX and
  CBCS combined, both already enumerated.
- Lot **vocabulary** gap — `is_lot` keys on vocabulary, not structure; 6,829 rows carry "lot" and
  6,280 "complete/full" outside the caught phrases.
- Unit 1a / 1b — extension regex + backfill, not started.

### Why these are queue rather than chase
The two defects that were **actually wrong** — X-Men #1 confidently priced off a contaminated
pool, and Wolverine LS #1 priced off four-comic sets — are fixed or scoped. Everything after that
is calibration, with **one exception**: the flat $30 grading cost is a live one-directional error
on every verdict and belongs on the queue as a defect, not as tuning.

⚠️ **Method note for whoever picks this up:** five measurement failures in this arc came from the
same shape — substituting a proxy for the production predicate. `docs/LESSONS.md` L-SW-2026-024,
items 3a–3d. In particular, **a graded-side measurement written in SQL alone is wrong**, because
variants are partitioned out in Python.

---

### STILL OPEN (next sessions)
- **Stacking step 2** (account.html "Change Plan" → `openPortal()` + 409 auto-redirect; verify Stripe portal plan-switching enabled) and **step 3** (`handle_subscription_deleted` sub-id match + immediate-cancel→free test) — hardening on the now-closed blocker (detail in the stacking entry below).
- **Section F checklist** (mobile + load) — draft AFTER stacking 2 & 3; **mobile half is higher-priority** (GalaxyCon booth is phone-first; start real-device testing well before Aug 21, not last-minute).
- **Cert-number recovery lookup** (small build) — the marketable slabbed-recovery headline.
- Lower-priority backlog: ~30s comic-ID progress messaging; email setup (mike@/support@); `lookup_demand` thin-data pull (after weeks of real traffic); **variant reclamation / subtyping (Tier 1 — see below)**; capture-cadence scheduled pull; ⏰ 90-day purge (~Sept 17).

  **Variant subtyping (Tier 1), reconfirmed 2026-08-16 — DELIBERATELY NOT TAKEN as part of the
  CP-1 bug work.** Mike: *"it deserves a session rather than a slot."* It is a **feature to
  design, not a defect to measure**, which is why it does not belong at the tail of a bug hunt.
  - ⚠️ **There is NO variant filter defect.** A claim that the graded query omitted the
    `is_variant` filter was **retracted** — the graded side partitions variants out in Python
    (`sales_valuation.py` ~741) while the raw side filters in SQL, both deliberate since
    `9c9dc7c` (2026-06-11). Do not re-open this as a bug. See `docs/LESSONS.md` L-SW-2026-024,
    fifth instance.
  - **The actual gap:** variants are currently *excluded and disclosed* — "Estimate reflects the
    standard cover; variant sales excluded", firing at ≥30% excluded / ≥3 excluded / ≥5 total.
    The open question is whether covers that sell at **orders-of-magnitude different prices**
    (Absolute Batman is the case that made this Tier 1) deserve to be **their own pool** rather
    than discarded behind a footnote.

---

## Session 109 (Jun 22, 2026) — Multi-sub STACKING investigated (read-only) → fix STEP 1 of 3 SHIPPED & VERIFIED: checkout stacking guard (the launch blocker is CLOSED)

**Built draft-for-review; Mike ran all git/deploy + the prod verification. Read LESSONS + cross-project at open.**

### Headline: the stacking launch-blocker is CLOSED. A real user can no longer stack subscriptions via create-checkout.
Investigated the Session-108 multi-sub stacking bug **read-only**, then shipped the contained fix (step 1 of a planned 3). Steps 2 (UI) and 3 (webhook) are hardening on a now-closed blocker — queued, no rush, before launch.

### READ-ONLY INVESTIGATION — what the code actually did (all in `routes/billing.py` + 2 frontend pages)
1. **Checkout guard: NONE (root cause).** `create_checkout_session()` validated the plan, got/created the Stripe customer, then **unconditionally** called `stripe.checkout.Session.create(mode='subscription')`. It never read the user's current sub state → every call minted a **brand-new** subscription. The 3-sub +22 result is exactly what this code does hit 3×; **not** a pure testing artifact.
2. **No in-code modify/upgrade path.** No `stripe.Subscription.modify` anywhere (only `.retrieve`). Billing routes: `/plans`, `/my-plan`, `/check-feature`, `/create-checkout`, `/customer-portal`, `/webhook`, `/record-valuation` — **no change-plan endpoint**. The only in-place modify is the **Stripe Customer Portal** (if configured), which is how the S108 "Pro→Guard works" almost certainly happened.
3. **Webhook = last-writer-wins.** `users` tracks ONE `stripe_subscription_id`/`plan`/`status`. `handle_subscription_updated` matches **by customer_id only** and overwrites from whichever sub's event fires last (+22 landed on guard incidentally). **Worse latent bug:** `handle_subscription_deleted` (billing.py:778) also matches by customer_id only → canceling **one** of several stacked subs reverts the user to **free while Stripe keeps billing the others.**
4. **UI reality: "Change Plan" routes back into stacking.** account.html shows paid users **"Manage Billing"** (→ portal, safe) AND **"Change Plan"** (→ `/pricing.html`). Every pricing button calls `create-checkout` → so "Change Plan" stacks a second sub.

### STEP 1 SHIPPED & VERIFIED — checkout stacking guard (`routes/billing.py`, additive guard clause)
- Committed + pushed + **deployed** by Mike: `"fix(billing): stacking guard — refuse create-checkout when a live sub exists"`.
- The guard: before creating a session, read `get_user_plan()`; if the user has `stripe_subscription_id` AND `subscription_status` in **active/trialing/past_due**, return **HTTP 409** `{"error": "...", "code": "existing_subscription", "manage_via": "customer_portal"}`. Checkout remains allowed ONLY for free→first-paid.
- **Edge cases (confirmed working as specified):** only active/trialing/past_due with a non-null sub id is blocked; canceled/incomplete/unpaid/none can still (re)subscribe; **fails OPEN** on a DB read error (never blocks a legitimate first-time subscriber).
- **VERIFIED two ways in prod:** (1) create-checkout as +22 (user 30, already has live subs) → **HTTP 409** `{code:"existing_subscription", manage_via:"customer_portal"}` (was 200 + checkout_url, would have stacked a 4th sub). (2) Stripe dashboard shows +22 still has **exactly 3** subs, not 4 → the guard refused **before any Stripe call**.

### STILL TO DO — steps 2 & 3 (next session, separate passes; hardening on a closed blocker)
- **STEP 2 — UI redirect:** point account.html "Change Plan" at `openPortal()` (not `/pricing.html`); have pricing.html/account.html **detect the 409 `code:"existing_subscription"`** and auto-open the portal instead of alerting the error string. Also verify in the Stripe dashboard that the Customer Portal's **plan-switching ("switch plans") is enabled** for Pro/Guard (dashboard config, no code) — flag if not.
- **STEP 3 — webhook hardening (the scary latent bug):** `handle_subscription_deleted` should only revert to free if the deleted `sub.id` matches the user's stored `stripe_subscription_id` (or re-resolve the remaining active sub). Optional follow-on: `handle_subscription_updated` ignores events for a sub that isn't the user's-of-record (kills last-writer-wins flicker).
- **Pairs with:** the still-untested **immediate-cancel → plan=free** Section E leg (same handler) — do it alongside step 3.

### SECTION F (Mike's question) — what it is
There is **no standalone doc** enumerating the readiness sections A–F; the lettering lives only in the session notes (A/B early · C = collection mgmt [S104] · D = tier gates [S106] · E = billing [S107–109] · **F = mobile + load**). **Section F = mobile + load testing** — the last un-run readiness section. It maps to existing TODO items but was never written out as a detailed checklist: **mobile** = full grading→value→verdict→save flow on real Android + iOS devices (P1 "Mobile testing"), plus billing/portal on mobile (P2) and PWA install; **load** = behavior under concurrent/convention-spike usage (the R2 edge-cache work was bought as spike insurance). If we want F run rigorously, first step is drafting an actual F checklist (devices, flows, a load target) — it doesn't exist yet.

### NEXT SESSION — queued
1. **Stacking step 2** (account.html "Change Plan" → portal + 409 detection) — draft-for-review.
2. **Stacking step 3** (`handle_subscription_deleted` sub-id match) + **immediate-cancel → free** test (same handler) — draft + test.
3. **Section F** — draft a real mobile + load checklist, then run.
4. ⏰ (Tracked) **90-day grade-retention PURGE** — hard deadline ~2026-09-17.

---

## Session 108 (Jun 20, 2026) — Section E billing LIVE TEST: core revenue path GREEN; webhook 500 root-caused (env-var typo) & fixed; webhook hardening shipped; multi-sub stacking bug found

**Built draft-for-review; Mike ran all git/deploy + the live Stripe test. Read LESSONS + cross-project at open.**

### Headline: core billing works end-to-end — pay → correct tier. Two bugs found, one fixed.
The webhook 500 that blocked all of Section E is **FIXED**, and **Pro + Guard checkout now flip the tier correctly** (incl. the Pro→Guard tier-CHANGE path). A second billing bug (subscription **stacking**) was found during testing and is queued.

### ALSO SHIPPED (Session 108 follow-on, commit `daf9050`) — sales-data coverage assessment + lookup-demand instrumentation
- **Read-only coverage assessment** of the sales corpus (script left on disk untracked: `scripts/coverage_assessment.py`). Findings: eBay `ebay_sales` = **53,840** rows (README "~24K" was stale), Whatnot `market_sales` = **9,677** (real, ~15% of corpus). **Freshness is fine** (83.5% within 180d; capture active but manual/bursty — a real Apr–May stall, resumed June). **Breadth wide, DEPTH thin** (89% of title/issue keys have 1–2 comps; grade-specific FMV is reliable on only ~268 books, high-confidence on 93). **Processing gap:** ~27% of eBay rows excluded by variant/lot/reprint filters — ~11K variants (1,235 graded+fresh) we're sitting on but not pricing (ties to the queued barcode-variant-subtyping work). **Read:** weak spot is DEPTH + over-filtering (PROCESSING), not coverage/freshness — and we were **blind** to which titles return no/thin data.
- **Fix (shipped):** lookup-demand instrumentation — `migrations/add_lookup_demand.sql` (new `lookup_demand` table + ranking indexes) + `lookup_demand.py` (fire-and-forget daemon-thread logger, never blocks/raises) + 3 hooks in `routes/sales_valuation.py` (valuation success, fmv no-data fallback, fmv success). Captures title/canonical/issue/grade, comp counts, fmv_method, estimated/no_data, **user_id** (for distinct-user ranking) and **is_internal** (admin pre-filter; test accts excluded by user_id at query time). Purely additive, non-blocking. **Verified live:** migration applied in Render shell, deployed, an ASM #300 fmv lookup wrote a correct row (`comp_count=327`, `user_id=None`, `fmv_method='mid'`). Now collecting; the "top thin-data titles" demand query is ready to run read-only once real traffic accumulates. **Don't over-read early sparse beta data.**

### THE WEBHOOK 500 — ROOT CAUSE WAS A RENDER ENV-VAR TYPO (not code)
- **All four theories from the webhook-500 brief were WRONG** — not the `.get()` bug, not Stripe version drift, not stale deployed code, not env propagation. (My read-only investigation had already **disproven** the `.get()` theory — proved `.get()` works on stripe 12.1.0 typed Event/Session objects — and flagged "we're blind without the traceback; instrument it.")
- **ACTUAL cause:** the Render env var was misnamed **`STRIPE_WEBHOOOK_SECRET` (THREE O's)** instead of `STRIPE_WEBHOOK_SECRET`. The code reads the correct (two-O) name via `os.environ.get`, found nothing → hit the "Webhook secret not configured" guard → **returned 500** (correctly refusing to process an unverified webhook). The **VALUE was always right; only the KEY NAME was wrong.**
- **Why it hid:** substring search (`grep -i stripe`) displayed the 3-O name so it "looked right"; the earlier manual "secrets match" check compared the **value** (correct); the pre-flight script structurally **cannot** check the webhook secret (Stripe never exposes `whsec_` via API). It only surfaced via **exact-name resolution in the container:** `printenv STRIPE_WEBHOOK_SECRET` = empty, `env | grep -c STRIPE_WEBHOOK_SECRET` = 0, while `STRIPE_SECRET_KEY` = 1 (the asymmetry was the tell).
- **FIX:** renamed the Render env var to `STRIPE_WEBHOOK_SECRET` (two O's), kept the value, redeployed.

### Webhook hardening — SHIPPED & KEPT (it's what pointed at the bug)
Committed + deployed this session (`routes/billing.py` + the stripe pin):
- **`logger.exception` + the explicit "Webhook secret not configured" message** → THIS is what pointed at the env var instead of sending us deeper into the code. Instrument-don't-guess paid off directly.
- `handle_checkout_completed` writes the **real** status (`trialing`, not hardcoded `active`) — confirmed correct in testing (`subscription_status=trialing` for the 14-day trial).
- `_subscription_period_end()` for the `current_period_end` API move (onto `items[]` in 2025-03-31+).
- 200-on-handler-error + greppable logging (a deterministic handler bug no longer retry-storms; traceback is logged, replay via Stripe dashboard after a fix).
- `requirements.txt` pinned **`stripe>=12,<13`** (separate commit) to stop local/prod drift.

### CONFIRMED WORKING (Stripe TEST mode, throwaway mikeberrysc+22@gmail.com, user_id 30)
- **Pro checkout:** webhook 200; `--check-db` → `plan=pro`, `subscription_status=trialing`, both stripe IDs set.
- **Guard checkout (as an upgrade from Pro):** `plan=guard`, `trialing`, both IDs set → **tier-CHANGE path works.**
- **Cancel-at-period-end:** portal scheduled all subs to cancel **Jul 4** (correct scheduled-cancel behavior).
- **Pre-flight `stripe_preflight.py`:** GREEN (key=TEST, all 4 prices resolve `livemode=false`, webhook endpoint + events good). `--check-db` flag working.

### NEW BUG FOUND — MULTI-SUBSCRIPTION STACKING (next billing task)
The customer portal for +22 showed **THREE concurrent active subscriptions** on the one customer: Guard $9.99 + Pro $4.99 + a **SECOND** Pro $4.99 (all cancelling Jul 4). Each checkout run created a **NEW** subscription instead of **MODIFYING** the existing one — so Pro→Guard "change" stacked a new sub, and a re-run Pro checkout stacked another. A real user who subscribes then upgrades could be billed for multiple overlapping plans (~$20/mo here).
- **Caveat — partly a testing artifact:** Mike ran raw checkout 3× rather than using an upgrade button. First step is to determine whether there's a real upgrade path that was bypassed vs. genuinely create-new-every-time.
- **INVESTIGATE (read-only first):** does `routes/billing.py`'s `create-checkout` path check whether the user already has an active Stripe subscription? Is there a proper change-plan flow that MODIFIES the existing subscription (Stripe supports this directly), or does it always create a new one?
- **FIX (either/both):** change-plan should modify the existing subscription, not create parallel; AND/OR checkout should refuse/guard if the user already has an active subscription. **A stacking guard is needed before launch regardless.**

### Signup "too many requests" — my read-only finding (no action this session)
Confirmed: **NOT our app and NOT Cloudflare** — there is no signup rate-limit anywhere in our code (`flask-limiter` isn't even a dependency; only `contact.py`/`monitor.py`/`grading.py` have limiters, none on `/api/auth/*`), and the signup POST goes **straight to Render** (`API_URL = collectioncalc-docker.onrender.com`), bypassing Cloudflare. Most likely **Resend's free-tier daily email cap (~100/day, doesn't reset in minutes)** — fits "didn't clear in 10 min." Accounts still create (the send failure is swallowed → `email_send_failed`); what breaks under load is verification **emails**. **Launch mitigation:** Resend paid plan + verified sending domain before Aug 21. Also: we have **NO abuse rate-limit on signup at all** — consider a gentle per-IP limit post-launch. (Logged; no action.)

### SECTION E STATUS
- **Core revenue path (pay → correct tier): 🟢 GREEN.** Pro, Guard, and tier-change all confirmed.
- **Cancel scheduling:** works (cancel-at-period-end → Jul 4).
- **STILL TO TEST:** immediate cancel → revert to `plan=free` (the `customer.subscription.deleted` path). The portal only did cancel-at-period-end (Jul 4), so nothing has terminated yet — needs a "cancel immediately" to fire the downgrade webhook.
- **STILL TO FIX:** the multi-sub stacking guard (above).

### LESSONS LOGGED THIS SESSION (docs/LESSONS.md)
- **L-SW-2026-006** — config typos are invisible to the eye (brain autocorrects WEBHOOOK→WEBHOOK) AND to substring/value checks; only exact-name machine resolution (`printenv NAME`, `env | grep -c NAME`) catches them.
- **L-SW-2026-007** — instrument before theorizing: "log the real failure reason" turned an hour of wrong theories into a one-line answer.
- (Reinforced **L-SW-2026-004:** Render auto-deploy is OFF — `git push` does NOT deploy; env-var changes need a redeploy + fresh shell to reach the process.)

### NEXT SESSION — queued
1. **Multi-sub stacking bug** — investigate (read-only) + fix (modify-existing and/or refuse-if-already-subscribed). Launch blocker.
2. **Test immediate cancel → `plan=free`** (the `customer.subscription.deleted` downgrade/teardown webhook path) — the last untested Section E leg.
3. (Earlier queued, still open) **~30s comic-ID progress messaging** — brief drafted, not shipped.
4. ⏰ (Tracked) **90-day grade-retention PURGE** — hard deadline ~2026-09-17; `saved_collection_id` backlink.

---

## Session 107 (Jun 19, 2026) — Grade-submission RETENTION shipped & verified end-to-end; collection must-fixes; privacy reconciliation

**Built draft-for-review; Mike ran all git/deploy/purge/migration/smoke-test. Read LESSONS + cross-project at open.**

### Headline: grade-submission retention is LIVE and verified (the matbanshee gap is closed)
- **Origin:** read-only investigation of matbanshee (user 21) "undergraded my 3 books by up to 2.6 pts" → found we retained **NOTHING** for unsaved grades (no photos/grade/subgrades/comic). Token-count forensics showed he submitted ~4 photos (multi-angle starvation excluded), leaving old-photo/photo-condition as the leading-but-unprovable hypothesis. Lesson **L-SW-2026-003** logged. Spec: `docs/technical/GRADE_RETENTION_SPEC.md`.
- **Privacy disclosure shipped FIRST** (prerequisite — commit `245f99b`): `privacy.html` new "Grading Data & Image Retention" subsection (90-day retention incl. unsaved, deletion-on-request within 30 days, authorized-staff review), reconciled the old "Images" line (removed the "unsaved grades vanish" + "anonymized-only" framing); `login.html` signup Terms/Privacy consent line.
- **Retention BUILT + verified live** (commits `e87b8cf` schema, `801e79d` persist, `6fb83f7` admin):
  - `migrations/add_grade_submissions.sql` — 24-col `grade_submissions` table, applied to prod via **Render-shell Python** (psql not in container — used psycopg2 + `$DATABASE_URL`).
  - `grade_retention.py` — background daemon-thread persist AFTER the grade response (no added latency); cascade delete + per-user erasure (R2 objects then DB rows).
  - `/api/grade` persist hook; admin `GET /api/admin/grade-submissions` (find by email/user_id/submission_id, presigned R2 image URLs) + `DELETE` (cascades DB row **and** R2 objects, single + by-user); `r2_storage.generate_presigned_url`; `admin.html` "🔬 Grade Subs" tab + one-click hook from the Feedback tab.
  - **Smoke-test: persist / view / delete-cascade all PASSED.**

### Collection must-fixes (commits `80d34c7`, `0579326`, `1cbfd06`) — shipped earlier in the session
- **Fix 1:** always-confirm delete — names the comic, "can't be undone" copy, removed the skip-warning bypass (no one-tap-delete). **Fix 2:** de-clickified list rows (pure CSS — no dead handler; gallery click left intact = real expand feature). **Fix 3:** admin Feedback comments expand-on-click (was CSS-truncated; backend already sent full text).

### ✅ Deletion-request runbook — written & committed
- **`docs/SW_deletion_request_runbook.md`** — believed already committed but was **not in the repo** (searched names/content/all branches/uncommitted — only a TODO reference existed), so it was **drafted fresh and committed** this session. Manual erasure procedure pairing with the admin grade-submission delete tool: verify by registered-email ownership (confirm-to-account-email on mismatch), scope incl. unsaved grade submissions, R2-cascade delete (R2 first, then rows), confirm `images_deleted`, confirm back, within 30 days, never auto-delete.

### ✅ Section E (billing) PREP — COMPLETE & GREEN (read-only, committed)
- `docs/technical/STRIPE_TEST_BILLING_RUNBOOK.md` — setup map + safe test runbook. Key findings: checkout is **server-created hosted Checkout** (no client publishable key — that mismatch can't happen here); price IDs are env-driven; webhook = `/api/billing/webhook` (mandatory secret); tier path `checkout.session.completed → handle_checkout_completed → update_user_subscription`; 14-day trial ⇒ status shows **`trialing`** (entitled, not broken).
- `scripts/stripe_preflight.py` — strictly read-only (`Price.retrieve` + `WebhookEndpoint.list` + optional `--check-db` SELECT). The `.get()`-on-Stripe-objects crash was patched to attribute access (`getattr`); `--check-db EMAIL` folded in.
- **Pre-flight passes GREEN in Render shell:** key=**TEST**; all 4 prices resolve `livemode=False` (**Pro $4.99 / $49.99, Guard $9.99 / $89.99**); webhook endpoint **enabled** at `/api/billing/webhook` with all required events.
- **✅ Item #2 (webhook signing secret) MANUALLY VERIFIED** — Render `STRIPE_WEBHOOK_SECRET` == the test endpoint's `whsec_`. **All 3 config items confirmed → Section E config is FULLY verified. Next session is the LIVE TEST ONLY** (run Part B; no more config to check).

### ⏰ / 🔧 Tracked follow-ups (carry forward)
1. **⏰ 90-day PURGE — HARD DEADLINE ~2026-09-17** (day-90 from persist deploy). ⚰️ *(Was framed as "after soft launch (Jul 21) + GalaxyCon (Aug 21-23)" — BOTH dead: soft launch is **Aug 4**, GalaxyCon **dropped** 2026-07-29.)* ⚠️ **This is now the ONLY hard external deadline left on the project** — it used to sit behind the con, so it no longer inherits that urgency; it needs its own reminder. Published-policy obligation; **cannot slip past the date**. Columns/index (`images_purge_after`,`pinned`) + `delete_grade_submission` helper already in place → scheduled job + feedback-pin away.
2. **🔧 `saved_collection_id` backlink-on-save** — always NULL (grade precedes save; save path doesn't backlink). Small.
3. **~30s comic-ID progress messaging** — brief drafted, **not yet shipped** (staged honest "still working" messaging only — NO accuracy-costing speedups). Queued.
4. **Email setup (mike@/support@slabworthy.com)** — Resend is **outbound-only**, no real inbox confirmed; **gates the matbanshee reply**. Deliberately held / not started.

*(Section E item #2 — webhook signing secret — now ✅ manually verified; no longer a follow-up.)*

### 🧠 Lessons logged this session (docs/LESSONS.md)
- **L-SW-2026-004:** a Render env-var change needs a redeploy/restart **AND a fresh shell** — an already-open shell keeps the old value (caused a mid-session "same key" confusion).
- **L-SW-2026-005:** run a strictly read-only pre-flight before any billing/money operation — `stripe_preflight.py` caught an expired key, an accidental LIVE key in Render, and a script bug before any could corrupt a real billing test.

### NEXT SESSION OPENER — Section E LIVE TEST (config fully verified; execution only, "follow Part B")
1. Make a **THROWAWAY** account — **NEVER** the `test-*@slabworthy.test` accounts (`create-checkout` taints an account with `stripe_customer_id` the instant checkout starts).
2. Test card `4242 4242 4242 4242` → checkout for **Pro + Guard** → confirm webhook **200** + tier flips (use `--check-db EMAIL` before/after; `my-plan` shows **`trialing`** not `active` due to the 14-day trial — both entitled).
3. Test customer-portal **cancel** → reverts to free.
*(No more config checks — all 3 items already verified this session.)*

Purge sits on its 2026-09-17 clock until separately scheduled.

---

## Session 106 (Jun 18, 2026) — Tier Honesty Pass SHIPPED (storefront now matches product); extraction resilience; ID Sigs CORS bug diagnosed

**Built draft-for-review; Mike ran all git/deploy/purge/smoke-test. Read LESSONS + cross-project at open.**

### 1. Extraction resilience (Commit 2) — SHIPPED, deployed, purged
- `comic_extraction.py` Anthropic client now `timeout=30.0, max_retries=1`; `app.html` `/api/extract` wrapped in a 75s `AbortController` (try/finally clears the timer); honest **"⏳ Our identifier is busy right now"** copy on backend timeout (`Request timed out` / 503 / 504 / overloaded) AND client `AbortError`, replacing the misleading "Could not identify." Insurance vs future load now the Session-105 signature auto-fire contention source is gone — turns a multi-minute hang into a clean ~30–60s honest failure.

### 2. Tier Honesty Pass (Section D reconciliation → 4 commits A–D) — SHIPPED, deployed, purged
- **Context (read-only Section D):** the four tiers were nearly indistinguishable in use. Only **3 of ~11** advertised differentiators were truly server-enforced (slab-guard regs, multi-photo, chrome-extension). Valuations were a **hardcoded flat 25/mo across ALL tiers** (the PLANS valuations field was dead — `check_feature_access('valuations')` never called); export / API / bulk / ownership-certs / white-label / LE-portal were **unbuilt**; the only upgrade prompt fires at the 4th Slab Guard registration.
- **A — per-tier grading cap wired to PLANS** (`routes/billing.py` + `routes/grading.py`): replaced hardcoded `MONTHLY_GRADING_LIMIT=25` with `PLANS[plan]['valuations_per_month']` — **Free 25 / Pro 100 / Guard 250 / Dealer 1000**, admins exempt. Uses the live `gradings_this_month` counter; the dead `valuations_this_month` path left untouched (NOT bridged — see follow-up). **VERIFIED:** `/api/billing/plans` reads 25/100/250/1000.
- **B — `fetchImageAsBase64` `response.ok` guard** (`js/utils.js`): honest "Couldn't load image (HTTP N / network error)" instead of the misleading "Image decode failed." **VERIFIED** — and it surfaced the REAL ID Sigs CORS bug (#3).
- **C — `pricing.html` honesty:** real caps (no "Unlimited" anywhere), Excel/CSV export trimmed, Dealer relabeled **"Coming Soon"** with a **"Notify Me →"** CTA to `/contact.html` (no checkout), Guard "verified ownership certificates" removed, Signature ID surfaced as a Guard **coming-soon** feature + compare-table row.
- **D — refuse Dealer checkout server-side** (`routes/billing.py`): `create-checkout` rejects `plan='dealer'` with an honest coming-soon message + `coming_soon:true` — enforces the label, not just displays it.
- **Net headline:** the storefront now matches the product — no advertised unlimited valuations we cap, exports we haven't built, or a Dealer tier that's mostly unbuilt.

### 3. ID Sigs CORS image-fetch bug — DIAGNOSED (read-only), queued to Signatures v2
- After Commit B's honest errors, testing showed ID Sigs fails at the **image fetch** even though the cover `<img>` thumbnail loads fine (admin: `HTTP 503` on Amethyst #1; test-guard: `network error` on Micronauts #11). The thumbnail and the base64 fetch use the **same** `photoUrl` (mismatch ruled out). **Root cause = cross-origin CORS:** `<img>` display is CORS-exempt; `fetch()→blob()` is enforced, and `img.slabworthy.com` doesn't reliably return `Access-Control-Allow-Origin` for the page origin (+ the uncached fetch hits the R2 origin → 503). Two errors, one root (cache/CORS state). **Preferred fix = server-side image fetch** in `/api/signatures/v2/match` (accept `comic_id`/URL; R2 SDK or `slab_guard_cv._download_image`). Captured in `docs/technical/SIGNATURES_V2_DESIGN.md` (build-checklist item 7 + new "Image-fetch (CORS)" section). **NOT a launch blocker** (ID Sigs is coming-soon / unreachable from upload).
- Corrects the Session 104/105 "response.ok decode" framing: the `response.ok` gap was real and is now **fixed** (Commit B); the *remaining* failure is **CORS**, a separate layer.

### QUEUED FOLLOW-UPS (captured in TODO; none July-21 blockers)
- **"0 used" usage meter:** `account.html` reads the dead `valuations_this_month` (always 0); reconcile to the live `gradings_this_month` — freemium pass.
- **Stale PLANS booleans:** `export` / `api_access` / `ownership_certificates` still read `true` for some tiers but are read by nothing — trimmed from the PAGE; tidy the dead config later.
- **Freemium upgrade-prompt mechanic:** only paywall that fires in normal use is the 4th Slab Guard registration; the grading-cap over-limit returns **429 with no upgrade CTA**. Decide the conversion moment(s) and wire prompts.
- **Dealer webhook hardening (optional):** `handle_checkout_completed` still accepts any plan string; harmless post-Commit-D (no route starts a Dealer checkout), tidy later.

### NEXT SESSION — queued
1. **Section E — billing end-to-end (the HARD launch gate)** — likely the opener. ⚠️ Stripe Checkout footgun: **never** run real Checkout/portal as a `test-*` account (writes `stripe_customer_id`, lets webhooks clobber the tier). Deserves a fresh, focused block.
2. **Section F — mobile + load.**
3. Still open from earlier: ~30s comic-ID wait (staged-progress messaging is the committed fix; speedup parked, conditional on not costing accuracy); **DELETE-confirm** must-fix; **comic-detail-view** decision (build or de-clickify); admin Feedback ~100-char truncation; CGC cost-sourcing investigation; year/edition comp-key gap (post-launch).
4. **Signatures v2** build when authorized (design doc — now includes the CORS server-fetch fix).
- **Cleanup when confident:** drop `_bak_*_20260615` snapshot tables; optionally disable r2.dev.

---

## Session 105 (Jun 16, 2026) — Identification fix SHIPPED; signature auto-fire removed (re-grade hang gone); Commit 2 resilience queued

**Built draft-for-review; Mike ran all git/deploy/purge/smoke-test. Read LESSONS + cross-project at open.**

### 1. Identification trustworthiness — SHIPPED & VERIFIED LIVE (the #1 launch gate)
- **Extraction flip (Haiku→Sonnet):** `comic_extraction.py` `_run_vision_pass` tier `'haiku'`→`'sonnet'`; the `/api/extract` cost-log model label moved with it (`routes/grading.py` → `get_model('sonnet')`) so per-extract cost attribution stays accurate. **VERIFIED:** Sonnet reads **Absolute Batman #19** (title no longer truncated, issue correct) and **Atari Force #4** (was #2 under Haiku) where Haiku failed.
- **Honesty gate:** always-visible, pre-filled, editable ID field (Title/Issue/Publisher/Year) replaces the "✓ Identified" checkmark; new `syncIdentityFields()` flows edits into both the grade request and valuation with NO Save click; removed the `|| '1'` issue default; client maps `'?'`/null/undefined → empty. **Server belt:** `/api/sales/valuation` returns `{issue_required:true}` (HTTP 200, no FMV) on empty/sentinel issue instead of omitting the issue filter and blending all issues into one confident FMV. Grade still shows; FMV/ROI render "—", verdict "ISSUE # NEEDED". Happy path verified on **mobile** (Atari Force #4 → editable field pre-filled → real valuation).

### 2. Signature auto-fire REMOVED — re-grade hang ROOT-CAUSED & FIXED
- **Read-only investigation (multi-round; the test beat the first trace):** the "re-submit identical photos → spins ~5 min → 'Could not identify'" bug was **NOT** image-identity/dedup. The extract path is stateless on content; moderation (Rekognition, no cache) and image-hash logging ruled out. **Root cause:** every successful grade auto-fired `runSignatureCheck` fire-and-forget → the v2 **Opus** orchestration (3 sequential passes, already serialized for a rate-limit constraint). Resubmitting identical photos = the *fastest possible next grade* → its extract fired while the prior grade's Opus job was still consuming the Anthropic rate budget → backoff (extract client had no timeout/retries, fetch had no AbortController) → ~5 min → `APITimeoutError`, mislabeled "Could not identify." A *different* second comic is slower to set up, so its job had finished — which is why A→B worked but B→B-resubmit hung. **Wait-test confirmed:** grade B, wait ~10 min, resubmit identical → WORKS.
- **Fix (Commit 1, `app.html` only): disconnected the post-grade auto-fire call.** Surgical — `runSignatureCheck`, the `gradeReportSignature`/`signatureInfo` panel, `signature_orchestrator.py`, the entitlement gate, and `routes/signatures.py` are ALL preserved (ready for a user-initiated control later). **VERIFIED LIVE:** quick re-grade no longer hangs.
- **Blast radius confirmed:** the Opus job runs only for **Guard/Dealer/admin** (Free/Pro get an instant entitlement 403 — zero Opus work). Mike's account triggered it as **admin**. Normal Free/Pro users would never hit the hang.

### 3. Docs + read-only findings
- **`docs/technical/SIGNATURES_V2_DESIGN.md` — committed.** Deferred signature design: decoupled (collection-based) user-initiated delivery; **detection gate** (mirror `routes/signatures.py` Step-1 "no signatures detected" → abstain at 0 — the REAL false-positive fix + a cost saver, NOT abstain-on-zero-prefilter); confidence-verify UX; tier-gated visibility; threshold alignment (frontend 0.40 → server floor 0.50); multi-sig later.
- **Signature false positive** (Alex Ross on unsigned Absolute Batman #19) root-caused: the v2 orchestrator has no "is a signature visually present?" step (pre-filter is era/publisher *creator* narrowing, not detection), and the frontend show-threshold (0.40) sits below the server's honest match floor (0.50) → 0.40–0.50 "tentative named artist" band renders as "Signature Detected." Both captured in the v2 doc.
- **Year/edition is NOT in the valuation comp-query key** — `/api/sales/valuation` filters on title+issue+issue_type only; `year` affects only the CGC fee tier + the no-data fallback estimate, never comp selection. Same root as X-Men #1 edition blending. Architecture item, post-launch.

### PENDING — Commit 2 (extraction resilience), QUEUED next session
- Currently **OUT of the working tree** (Mike took Commit 1 alone first). Re-apply next session for review: `comic_extraction.py` client `timeout=30.0, max_retries=1`; `app.html` `/api/extract` AbortController (75s) + honest "Our identifier is busy right now" copy on backend-timeout/abort (not "Could not identify"). Insurance against future contention/load now the auto-fire source is gone — **not urgent.** Mike reviews → commit → deploy → purge → verify a forced timeout fails cleanly in ~30-60s with the honest message.

### NEXT SESSION — queued
1. **Re-apply Commit 2** (resilience) draft-for-review.
2. Launch-readiness still open: readiness D (tier gates) / E (billing — ⚠️ Checkout footgun) / F (mobile+load) UN-RUN; DELETE-confirm must-fix; comic-detail-view decision; admin Feedback comment truncation; CGC cost-sourcing investigation; ID Sigs image fetch/decode bug (separate from the hang — still open); year/edition comp-key gap (post-launch).
3. Signatures v2 build when authorized (see design doc).
- **Cleanup when confident:** drop `_bak_*_20260615` snapshot tables; optionally disable r2.dev.

---

## Session 104 (Jun 15, 2026) — R2 migration shipped; model audit; identification plan of record; Section C readiness

**Back from Napa. Big day — multiple read-only briefs + one live migration (run by Mike). All work below is captured in `TODO.md` (🚦 launch-readiness section) and the `project_slabworthy_state.md` memory; this is the narrative.**

### 1. R2 custom-domain migration — DONE & VERIFIED (Mike executed the runbook)
- `img.slabworthy.com` attached to the bucket (Active, SSL auto-provisioned); bucket CORS policy added; `R2_PUBLIC_URL` flipped on Render to `https://img.slabworthy.com` (no trailing slash). Data rewrite ran on all 5 tables holding absolute `pub-c8c9…r2.dev` URLs (single prefix → clean REPLACE); straggler check = 0. Final counts: creator_signatures 1, collections 26 (jsonb), signature_images 207, market_sales 3,818, ebay_sales 50,493 (col = `r2_image_url`).
- **VERIFIED LIVE:** covers load with `Cf-Cache-Status: HIT` (edge cache = the spike insurance is real). Old **ID Sigs CORS+503 image-fetch blocker is FIXED.**
- **Ground-truth divergences:** Postgres is **PG 18.3** (not 16) → DBeaver's pg_dump 17 refused it, so the file-level dump was **skipped**; backup = in-DB snapshot tables only. **`_bak_*_20260615` tables STILL EXIST** (rollback source; drop after a few days clean). **No `.dump` file. r2.dev left ENABLED** as a safety net. Runbook committed: `docs/technical/R2_CUTOVER_RUNBOOK.md`.

### 2. Model-string audit (Sonnet 4 retired June 15) — NO LIVE BREAK
- All production call sites route through `models.py`. Grading + extraction's tier resolution use `call_with_fallback`; grading is on **`claude-sonnet-4-6`** (safe — NOT the retired `claude-sonnet-4-20250514`, which only survives in archived `.patch` files + comments). SW already migrated 2026-06-06; the dependency monitor caught it (it genuinely polls `deprecations.info` + emails on state-change).
- **Resilience gap logged (not urgent):** 8 of 12 model call sites pass static constants (`model=SONNET`/`OPUS`/etc.) with NO fallback (Chrome vision, signature v1/v2, Slab Guard CV, eBay gen, admin) — they'd break with no auto-recovery if a head string retires. Harden later via `call_with_fallback`.

### 3. Identification-honesty review → PLAN OF RECORD (build next session)
- Full analysis: `docs/technical/IDENTIFICATION_HONESTY_REVIEW.md`. Plan: `docs/technical/IDENTIFICATION_FIX_PLAN_OF_RECORD.md` (both committed).
- **Decision 1 — GLOBAL Sonnet extraction:** flip `comic_extraction.py:483` `'haiku'`→`'sonnet'` tier (use the TIER in the existing `call_with_fallback`, not a hardcoded string). Chosen over conditional re-read because the bench showed Haiku **fabricates confidently** (fake barcode 2/3; Sonnet empty 3/3) — a confidence-gated re-read can't catch errors Haiku never admits. Cost ~+1¢/call (~2.9× Haiku), accepted. Caveat: hard-case accuracy gain **inferred, not measured** (`haiku_vs_sonnet_results.json` had only easy books, both 100%).
- **Decision 2 — Honesty gate (#1 launch fix, built regardless of model):** grade still shows (condition observable); **valuation + slab verdict HALT** on absent/low-confidence issue. Objective issue-confidence (`issue=='' ⇒ could_not_determine`; later barcode↔vision agreement — NOT model self-report). Frontend: drop "✓ Identified", show the already-built edit form by default, require issue, gate `/api/sales/valuation`; remove `|| '1'` default (`app.html` ~2554). Server belt: `/api/sales/valuation` must not blend-all-issues on empty issue (`sales_valuation.py` ~228). Ships as ONE change.
- Key mechanism found: barcode-decoded issue is computed (`decode_barcode`) but the merge never writes it to `extracted['issue']` (`comic_extraction.py:663-681`) — parked writeback. Identification runs on Haiku while grading runs on Sonnet (the inversion that motivated Decision 1).

### 4. TODO consolidation + launch posture
- **Launch posture (recorded):** public beta = **GATED/BATCHED** (keep `require_approved` + waitlist + beta codes, admit in waves). HARD gates = billing E2E + valuation/identification honesty; core-flow/mobile buffered by gated intake.
- TODO.md now has a single 🚦 launch-readiness section: identification build, CGC cost-sourcing investigation (read-only, not started), readiness D–F, ID Sigs, resilience gap, polish items.

### 5. Section C readiness (collection mgmt) — run tonight
- **ID SIGS SCOPE GREW (priority BUMPED):** earlier "cosmetic messageToast" framing was wrong. ID Sigs now throws **"Image decode failed" INSTANTLY on multiple comics** — dies UPSTREAM at the image fetch/decode. **Leading hypothesis:** `fetchImageAsBase64` (`js/utils.js:359` area) never checks `response.ok` → base64-encodes a non-image (error/403/redirect/empty) response → instant decode failure regardless of CORS. **Read-only investigation queued** (confirm response.ok gap + what the fetch returns now + whether it builds the right `img.slabworthy.com` URL). Guard/Dealer PAID feature → must work before those tiers launch.
- **MUST-FIX before public:** DELETE (trash icon) has no confirmation/undo — data-loss trust-breaker (mobile mis-tap).
- **DECISION:** comic detail view not built — row looks clickable but does nothing → reads "broken." Build it OR neutralize the affordance (min fix = stop implying it exists).
- **Verified working:** covers, sort/filter/search, Slab Guard reg, eBay (saved-item) + Whatnot gen, Edit MY VAL. Readiness D (tier gates), E (billing — Checkout footgun), F (mobile+load) still UN-RUN.

### NEXT SESSION — queued (Mike says go; Claude drafts, Mike runs all git/deploy)
1. **Read-only ID Sigs fetch/decode investigation** — confirm the `response.ok` gap / URL construction; report before any fix.
2. **Identification build** — draft extraction-flip (`comic_extraction.py:483`) + honesty gate as ONE file-specific diff for review.
3. Other launch-readiness: CGC cost-sourcing investigation; DELETE-confirm; detail-view affordance; readiness D/E/F (careful with E — Checkout footgun); polish (Slab-Worthy-twice/blank-image/early-thumbs, "which photo", duplicate link); resilience hardening.
- **Cleanup when confident:** drop `_bak_*_20260615` snapshot tables; optionally disable r2.dev.

---

## Session 101 (Jun 10, 2026) — Batch 8 shipped + vision-gate fix; capture resumed

**Shipped + verified live:** (1) Vision-gate entitlement fix (`routes/billing.py`) — admin-default-bypass
with `X-View-As-Tier`/`?view_as=` override + plan-string normalization/WARNING-log (root cause:
`check_feature_access` ignored `is_admin`). Test accounts now exist: `test-pro/guard/dealer@slabworthy.test`
(active tiers, non-admin). (2) **Batch 8** (Session 100 work) FINALLY committed + deployed — prod had been
running pre-Batch-8 matching under the Batch 7 deploy. Verified live via the `issue_type` discriminator:
plain "X-Men #1" ≈ $28 / 111 sales vs Giant-Size "X-Men #1" ≈ $5,345 / 128 sales (contamination gone).
(3) Repo hygiene: `.gitignore` now ignores `.env`; dirty-tree docs committed.

**CAPTURE STATE (corpus-growth assumption — keep current):** eBay capture has **resumed** (was stalled
~Apr–May). Now running at **240 results/page** (was ~60 while signed out) ≈ **4× depth per pull**. Cumulative
synced **~45K+**; net-new ~**70–75%** vs dupes per deep pull. So the corpus is growing again and denser per
title — re-measure distribution fresh rather than reusing the ~6,357 queryable-graded-comps figure.

**Confirmed (read-only):** core valuation flow (grade→value→verdict→save→collection) is corpus-powered via
`/api/sales/valuation`; live `/api/valuate` only backs hidden `display:none` surfaces. Read-only DB access:
`DATABASE_URL_RO` in `.env` (`do_readonly` role).

**Queued next:** confidence-field inventory (`/api/sales/valuation` + `/api/sales/fmv` already return
`confidence`/sample-size/`low_confidence`) → design the count-plus-dispersion High/Medium/Low label against
the re-measured (denser) corpus. Parked: 240-capture confirmation, CP-2 billing E2E, mobile testing.

---

## Session 100 (Jun 8, 2026) — Batch 8: series-type qualifier plumbing + qualifier-precise valuation matching

**STATUS: code complete, WIRED + verified end-to-end, NOT committed (checkpoint hold for Mike's review).**
Files: NEW `title_matching.py`; `routes/sales_valuation.py` (6 query sites + `issue_type` param, both
endpoints); `app.html` (display composition + send `issue_type`); NEW `docs/technical/EXTRACTION_ROBUSTNESS_NOTES.md`.
Mike runs all git/deploy/purge (L-SW-2026-001).

**Problem:** qualifiers (Giant-Size/Annual/Special) read into `issue_type` but orphaned; display +
`/api/sales/valuation` used bare `title`; and the `parsed_title LIKE` fallback BLENDED books (X-Men #1
query mixed 1991 + 1963 + Giant-Size → one median). Corpus stores qualifiers cleanly in `canonical_title`
('Giant-Size X-Men' = 112 rows) → app-side plumbing + matching precision, no backfill.

**Solution — `title_matching.py` (single source of truth, no Flask dep):**
- `compose_qualified_title(title, issue_type)` — **per-qualifier position**: Giant-Size/King-Size =
  PREFIX, Annual/Special = SUFFIX. ("X-Men"+"Giant-Size"→"Giant-Size X-Men"; "Star Wars"+"Annual"→
  "Star Wars Annual"; Regular/""→bare.)
- `qualifier_title_clause(exact_col, like_cols, title, issue_type)` — exact normalized canonical match
  OR a qualifier-GATED LIKE fallback. Qualified query requires its qualifier token; plain query excludes
  ANY qualifier. Hyphen/space normalized on both sides (`coalesce→lower→hyphens→collapse`), so
  'Giant-Size'≡'Giant Size'. **COALESCE null-safety** (caught at checkpoint — NULL canonical was silently
  dropping legit plain rows; control fell 203→179, fixed → 203).

**Wired:** server-side composition/matching in both endpoints (4 valuation queries + 2 fmv queries),
`issue_type` request param on both. Frontend composes for DISPLAY only (`composeQualifiedTitle` JS mirror)
and SENDS `issue_type` to valuation (title stays bare; server composes). `js/grading.js` legacy
`calculateGradingRecommendation` is OVERRIDDEN by app.html inline (line 2212) — not plumbed (dead path).

**Security fix (folded in per Mike, pre-public-signup):** the AI-read title/issue/publisher/year went into
`innerHTML` UNescaped in the extraction-display flow (pre-existing; the line was touched here). Added an
`escAttr()` helper (quote-safe for text AND `value="..."` attribute contexts — the bundled `escapeHtml`
doesn't encode quotes) and applied it to all 10 sinks across both display templates (extract success +
saveEdit/showExtractEditAgain). A crafted cover title (or user-typed title) can no longer inject HTML.

**Verification (read-only RO replica + WIRED endpoints via Flask-stub):**

| key | OLD n / median | NEW n / median | wired valuation graded_fmv | wired fmv raw |
|---|---|---|---|---|
| Giant-Size X-Men #1 | 629 / **$40** | 141 / **$1,500** | **$2,150** | **$1,633** |
| X-Men #1 (plain) | 629 / $40 | 481 / $25 | $750 | $52 |
| Spider-Gwen Annual #1 | 91 / $14.99 | 10 / $54.75 | — | — |
| ASM #300 (CONTROL) | 203 / $360 | **203 / $360 ✅** | 205 (unchanged) | 208 (unchanged) |

(OLD shows the bug: Giant-Size and plain X-Men were identical 629/$40 because both sent bare "X-Men".)

**⚠️ KNOWN LIMITATION (logged per Mike):** the qualifier detector is a COARSE regex
(`giant size|king size|annual|special`). A real series literally named with one of those words (e.g.
"Giant Days", a standalone "Special") could be over-excluded from an unrelated plain query. Control
unchanged → not biting in practice; first place to look if a weird title misfires later.

**Captured for the record (NOT this batch):** plain "X-Men #1" is STILL a year/edition blend (1963 key +
1991 Jim Lee + editions share the exact title). Batch 8 fixed the QUALIFIER collision, not YEAR/EDITION.
$25/$750 is not the final answer — next-layer disambiguation by year/era. Logged in
[EXTRACTION_ROBUSTNESS_NOTES.md](../technical/EXTRACTION_ROBUSTNESS_NOTES.md).

### Open / watch (Batch 8)
- **Checkpoint hold:** verification agent + this writeup are the pre-commit review. Nothing committed.
- **Purge IS load-bearing** — `app.html` changed. Deploy (backend: sales_valuation, title_matching) + purge.
- Post-deploy: value Giant-Size X-Men #1 live → Bronze-key FMV with its own comps; plain X-Men #1 → no
  Giant-Size; control ASM #300 → usual number.

## Session 99 (Jun 8, 2026) — Batch 7: decouple quality gates + surface real errors

**STATUS: code complete, verified, NOT committed.** Files: `routes/fingerprint_utils.py`,
`routes/grading.py`, `app.html`. Mike runs all git/deploy/purge (L-SW-2026-001).

**Root cause recap (DO's prior trace):** Giant-Size X-Men #1 = a 394×572 eBay cover hit the
pre-vision quality gate (`GRADE_QUALITY_MIN_DIMENSION=400`) and was rejected by 6px — vision model
never called — and the frontend showed a generic "Could not identify comic automatically." Confirmed
from `request_logs`: most recent `/api/extract` = HTTP 400 "Photo is too small (394×572px)".

**Task 1 — decouple the gate by purpose (🔴).** `check_photo_quality_base64(base64_data, purpose='grade')`
now takes a purpose: `extract` uses a lenient floor (`EXTRACT_QUALITY_MIN_DIMENSION=250`), `grade`
keeps the strict `400`. Also returns measured `width`/`height`. `/api/extract` passes `purpose='extract'`;
`/api/messages` + `/api/grade` pass `purpose='grade'`. Verified with a real 394×572 JPEG: **extract
ok=True, grade ok=False** with message "This photo's too small for an accurate grade (394×572px)…"; a
140×200 image still fails extract. So a legible eBay cover now identifies the book but is correctly
held back from grading.

**Task 2 — honest grade-time UX (🟡).** When `/api/grade` returns 400 `quality_fail`, app.html now shows
an amber "we identified the comic, but need a larger photo to grade it accurately" state (with the book
title from `extractedData` + the backend's tip), instead of a red "Error/Failed". Does NOT grade at
unreliable quality. Check lives at grade-time using the gate's dimension data (grade endpoints now also
return `width`/`height`).

**Task 3 — stop swallowing the real error (🟡).** `extractComicData` previously threw on `!response.ok`
before reading the body, so quality rejections showed the generic line. Now it reads the body first and,
when `quality_issue`/`quality_fail` is set, surfaces the backend's real `quality_message` + `tip`.
(Same swallowed-error pattern fixed in signup/Batch 6.)

**Bonus fix (from review):** the grade flow read the Response body twice on a non-`monthly_limit` 429
(body can only be consumed once → real error lost). Restructured to read the body ONCE and reuse it
across the limit/quality/error/success branches.

**Verification:** real-image gate test (above); `node` syntax check of app.html inline scripts (0
errors); `py_compile` clean. code-reviewer agent: the double-read was the one critical item — **fixed**;
scopes/field-names/floors confirmed correct. Noted latent (accepted, not active): backend quality
strings are interpolated into innerHTML — currently server-static (dimensions + fixed tips), no
user-input path; revisit if message text ever includes user content.

### Open / watch after deploy (Batch 7)
- **Purge IS load-bearing** — `app.html` changed (Tasks 2 & 3). Deploy (backend: fingerprint_utils,
  grading) + purge (frontend).
- Headline live check: re-run the 394px Giant-Size X-Men #1 cover → should now **identify** (reach the
  vision model, return a title); a genuinely small cover → identifies, then at grade shows the honest
  "too small to grade — upload larger" message; a true quality reject → shows the precise backend
  message + tip, not the generic line.

## Session 98 (Jun 8, 2026) — Batch 5: valuation date-filter fix + confidence-labeling audit

**STATUS: code complete, verified read-only against prod corpus, NOT committed.** One file:
`routes/sales_valuation.py`. Mike runs all git/deploy (L-SW-2026-001).

**RECONCILIATION (corrects an earlier overstatement of mine).** The stall was REAL — the audit was
right. Capture is MANUAL (Mike gathers by hand): created_at histogram shows 24,629 rows (Feb) + 13,681
(Mar), then **ZERO in Apr and May**, then a **42-row revival on Jun 6** (Mike resumed this weekend). My
first-pass claim that "capture is current" was wrong — I over-read `max(created_at)=2026-06-06` as
healthy capture when it's a tiny revival after a real ~2-month gap. The audit's OTHER findings ALSO hold
against current data: shallow distribution = **79.1% single-sale, 95.5% <5 comps** (audit said 75% /
94.5% — confirmed, slightly worse); **Whatnot-dark** = market_sales is **19.7%** of the 47,750 corpus.
So the audit is trustworthy; the only "discrepancy" was timing (audit = pre-revival, my read = post-).

**Task 1 — date filter `created_at` → sale date (6 queries) + fmv window 90→180.** All six window
filters now use `COALESCE(sale_date, created_at)` (ebay) / `COALESCE(sold_at, created_at)` (market) —
4 in `/api/sales/valuation`, **2 in `/api/sales/fmv`** (brief said "4"; there were 6). COALESCE =
documented explicit NULL fallback. Plus the fmv default lookback widened **90→180 days** (Mike's call):
sale-date-filtered 90d is too sparse; 180d restores healthy samples without reaching stale pricing.
Before/after comp counts (read-only prod RO replica):

| key | 90d OLD | 90d NEW | **180d NEW** | 365d NEW |
|---|---|---|---|---|
| X-Men #1 | 172 | 106 | **592** | 670 |
| Batman #1 | 159 | 102 | **627** | 737 |
| Amazing Spider-Man #300 | 51 | 42 | **187** | 210 |
| Incredible Hulk #181 | 42 | 23 | **134** | 145 |

(Why the fix matters: the Feb–Mar bulk has created_at within ~90d but sale_dates spread over time, so the
old created_at-90d window counts stale sales as "recent"; sale-date-90d is honest but sparse → 180d is
the sweet spot. And once the Feb–Mar captures age past 90d created_at with capture stalled, the OLD
filter would serve fallback for the WHOLE corpus — the sale-date filter is what keeps real comps flowing.)

**Task 2 — confidence-labeling audit (investigate + low-risk wiring).** Findings: **in-app is fine** —
`/api/sales/valuation` returns `confidence` (exact_count/total_graded → high/medium/low/very_low),
app.html maps `very_low→"Limited"`, and a single-sale key resolves to very_low and always shows the
label alongside any point estimate (+ `estimated` note on the fallback). **Gap = the Whatnot extension
via `/api/sales/fmv`**, which returned **no confidence field at all** — just tier point-estimates (a tier
`avg` can be one sale, rounded to the cent) with a bare count → false precision. **Low-risk wiring fix
(done):** `/api/sales/fmv` now returns `confidence` / `fmv_sample_size` / `low_confidence`, computed from
the count of sales in the tier the FMV was actually priced from (thresholds 10/5/2), on both the main and
no-sales-fallback returns. Verified on real tier counts: X-Men#1@9.4 (16)→high, Batman#1@9.4 (6)→medium,
Hulk#181@9.4 (4)→low, a real 1-sale key→very_low. **FLAGGED for Mike (NOT built — bigger):** the Whatnot
overlay still has to *render* this new signal (a "Limited data" badge); that's an extension UI change +
republish, his call.

**Verification:** read-only harness against prod RO replica (`DATABASE_URL_RO` from `.env`, no writes);
code-reviewer agent — **no critical/important blocking issues** (COALESCE columns match SELECTs, vars
initialized, `used_tier=None` safe, valuation confidence untouched). Reviewer flag (out of scope, NOT
touched per brief): future-dated `sale_date` rows now pass the window — best fixed with a `sale_date <=
NOW()` guard in the eBay scraper at ingest, not here.

**Out of scope / untouched:** capture pipeline, valuation math, sales-table writes.

### Open / watch after deploy (Batch 5)
- **Purge: NOT load-bearing** — backend-only (`routes/sales_valuation.py`); no `js/`/frontend change.
  Render deploy only.
- Headline live check post-deploy: value a well-covered key (X-Men #1 / Batman #1) — real FMV +
  confidence band; fmv now uses a 180-day window.
- **Batch 5B (approved by Mike, separate — extension code + republish):** (1) Whatnot overlay renders the
  new `low_confidence`/`confidence` signal as a "Limited data" badge; (2) ingest-time `sale_date <= NOW()`
  guard in the eBay scraper (future-dated rows now pass the sale-date window).
- Bigger picture: capture is manual and currently only barely revived (42 rows Jun 6); the date-filter
  fix uses correct semantics but does NOT substitute for resuming real capture.

## Session 97 (Jun 8, 2026) — Batch 6: collapse new-user double email-confirm + dead-code cleanup

**STATUS: code complete, verified, NOT committed.** Mike runs commit/push/deploy. Files: `auth.py`,
`login.html` (Batch 6); plus `slab_premium_analysis.py` **deleted** (separate cleanup, staged).

**Cleanup (pre-Batch-6).** Deleted orphaned `slab_premium_analysis.py` — standalone research script
built entirely on eBay's decommissioned Finding API (`findCompletedItems`, dead since 2026-02-05).
Nothing imports it (the live `search_ebay_sold` in `ebay_valuation.py` is a different function). See
`docs/sessions/EBAY_API_SOLD_DATA_INVESTIGATION_2026-06-08.md`. Stale doc ref left at
`docs/technical/ARCHITECTURE.txt:122` (env-var table) — flagged, not yet fixed.

**Investigation (prior turns).** Mapped the full new-user flow: a beta-code stranger hits TWO gates —
beta code → email verification — then auto-login (beta code auto-approves, so the admin-approval gate
is dormant). The "verify twice" friction is **cross-funnel**: a waitlist person confirms their email to
join the list (`waitlist.verified`), then verifies the SAME email again at signup. Verification-email
non-delivery (mikeberry+5) traced to the send path being code-identical to working emails → Resend-side,
not our code; and the send result was being silently discarded.

**Task 1 — pre-verify confirmed-waitlist emails (🔴).** `signup()` now calls `_is_waitlist_confirmed(email)`
(SELECT `verified` FROM waitlist by normalized email, **fails closed**). If confirmed: user created
`email_verified=TRUE`, no verification token stored, **no second email**, JWT returned → frontend
auto-logs-in. ⚠️ **SECURITY CAVEAT (documented in code, [auth.py](../../auth.py) `_is_waitlist_confirmed`):**
email-match trusts a PAST click ("someone controlled this inbox once"), not "this signer controls it now"
— residual email-squatting risk, bounded in beta by the beta-code wall + password-reset recovery.
**REVISIT before public launch** when the beta wall comes down (consider a signed continuity token minted
by the waitlist-confirm click). I surfaced this fork to Mike; proceeded with the brief's primary
email-match approach per his stated risk tolerance.

**Task 2 — auto-approve waitlist signups (🟡).** `auto_approve = bool(beta_code) or waitlist_confirmed`.
Beta-code wall and admin-approval machinery left intact (out of scope). Confirmed-waitlist signup lands
`is_approved=TRUE`, skips the pending panel.

**Task 3 — fix swallowed send result (🔴).** `signup()` now checks `send_verification_email()`'s return.
On failure: returns `email_send_failed=True` + honest message (account still created); frontend shows a
"Couldn't send your email" state with a **Resend** button (hits existing `/api/auth/resend-verification`,
which now also surfaces failures). Failures persisted to a new `email_send_failures` table (lazy-created
once/process) + `logger.error` instead of bare `print`.

**Task 4 — pre-fill + lock email for waitlist invites (🟡, Mike add-on).** The Create Account form asked
invited users to retype the email they'd already confirmed (felt like "they forgot me"; let them type a
DIFFERENT address than the one verified). **Plumbing required** — the verified email wasn't available to
the form (beta codes aren't email-bound; `/api/beta/validate` returned no email). Fix: waitlist-invite
codes already store `note = "Waitlist invite: <email>"` (`/api/admin/waitlist/invite`), so
`validate_beta_code` now parses that and returns `invite_email` + a **server-computed** `email_verified`
(= `_is_waitlist_confirmed`, can't be spoofed client-side). `login.html` pre-fills + locks (`readOnly`)
`#signupEmail`, shows a "✓ Verified" badge (only when server says so), with a **"change it" escape hatch**
(opting out drops pre-verify — correct, it's no longer the confirmed address). Field kept (it's account
identity), not removed. ⚠️ Privacy fix from review: `validate_beta_code` **no longer returns the raw
`note`** (unauthenticated endpoint; note holds the invited email / internal admin remarks). Note wording
gated on `email_verified` so an invited-but-unconfirmed email doesn't falsely read "you confirmed."
Optional follow-up (NOT done): add `?code=...` to the invite link ([admin_routes.py:925](../../routes/admin_routes.py)) so users don't hand-type the code.

**Verification.** Throwaway harness exercised all four signup paths (confirmed-waitlist → no email +
auto-login + approved; unconfirmed-waitlist → normal verify; never-waitlisted+beta → normal verify +
approved; send-fail → honest flag, no token) — all assertions passed. code-reviewer agent: **no critical
bugs**; INSERT placeholders aligned, fails-closed correct, no auto-verify-without-waitlist path, XSS-safe
(textContent). Addressed its one actionable item (moved per-call `CREATE TABLE` behind a once/process
guard).

### Open / watch after deploy (Batch 6)
- **Purge IS load-bearing** — `login.html` (frontend signup flow) changed → Cloudflare cache purge required.
- Post-deploy check: sign up a **fresh, copy-pasted** confirmed-waitlist test email → should NOT re-verify,
  lands in app approved. Then a never-waitlisted email → SHOULD still get a verification email.
- New `email_send_failures` table is lazy-created on first failure; no migration wired. If you want it
  pre-created, add to a startup migration later.
- Still pending (separate batches, NOT this one): Resend monitoring/webhook in `dependency_monitor.py`;
  public-launch gating decision (beta wall + admin gate); ARCHITECTURE.txt:122 stale ref.

## Session 96 (Jun 7, 2026) — Batch 4C: signature 413 chain + grade CGC snap + calibration tooling

Five tasks. Protocol: reproduce → fix → verify → verification agent. **SHIPPED** — Mike committed +
pushed + deployed (Render + Cloudflare purge) + field-verified live 2026-06-07: 413 gone (/v2/match
returns 200), eBay 401 gone on load, grade displays on-scale. HEAD has moved past `8a9e3ae`. Files:
`js/utils.js`, `app.html`, `js/grading.js`, `routes/grading.py`, `routes/signature_orchestrator.py`,
`wsgi.py`, `js/app.js`, `test_haiku_vs_sonnet.py`, `test_grading_consistency.py`.

### ⚠️ Open for tomorrow (from Mike's live testing 2026-06-07 — do NOT act tonight)
1. **Spinner orphan on `matched:false`.** `/v2/match` returns 200 with a correct no-match (Part A
   floor working), but the client only handles error + confident-match — the successful-no-match case
   orphans the "Checking for signatures…" spinner. Fix: on `matched:false`, render the `message`
   field and clear the checking state. (app.html `runSignatureCheck` + js/utils.js `identifySignaturesV2`
   / collection.js consumer.)
2. **`raw_grade` not observed in the live `/api/grade` response** (Mike saw only `grade:7.5`). I added
   `result['raw_grade']` in `routes/grading.py` before `jsonify(result)` — VERIFY tomorrow where it
   actually lands (response field name / serialization / whether the inspected payload was the grade
   object). Calibration (task 4) needs raw QUERYABLE → if it's not a DB column, **adding one is the
   prerequisite** (this is the gap, not the response field).
3. **Signature MATCHING never actually tested this weekend.** All of Mike's test comics have PRINTED
   credits, not hand-signed autographs, so only the REJECTION/no-match path was validated. The
   confident-match path is unverified. Mike has a reframe coming tomorrow.

**Task 1 — signature match 413 (🔴 root cause found).** Client posted the cover base64 as a multipart
TEXT field (`formData.append('image', base64)`); Werkzeug 3.1.3 caps non-file form fields at
`max_form_memory_size` = **500 KB** and raises 413 during form parsing — AFTER the entitlement gate
(matches "gate passed, died on body size"). Server already reads `request.files["image"]` (a file), so
the field upload was also contract-wrong. Verified: 2 MB field @500 KB → 413; file part @500 KB → 200.
Fix: (a) `resizeBase64ToJpegBlob()` in `utils.js` resizes to 1568 px long-edge (Anthropic's vision cap
— no model-visible loss) and returns a JPEG **Blob**; `identifySignaturesV2` + app.html
`runSignatureCheck` append it as a FILE part. (b) `match_signature` accepts a `request.form["image"]`
base64 fallback too. (c) `wsgi.py` sets `MAX_FORM_MEMORY_SIZE=25 MB` as a transitional safety net
(does NOT touch `MAX_CONTENT_LENGTH`, so the JSON multi-image `/api/grade` path is uncapped). Prefer-
shrink honored: full-res cover base64 (~MBs) → ~200–400 KB file.

**Task 2 — orphan spinner (🔴, pairs with 1).** `runSignatureCheck` now wraps the fetch in an
AbortController **120 s timeout** and resolves the "Checking for signatures…" state on EVERY outcome:
403 → hide silently; other non-OK (413/5xx) → "Signature check unavailable"; catch (network/timeout)
→ same. `collection.js` already cleared via `finally` (unchanged). Closes the Friday "flicker" item too.

**Task 3 — grade CGC snap (🟡, "Defensive + store raw" per Mike).** KEY FINDING: the LIVE app.html
path (`/api/grade` → `grading_engine.compute_grade` → `snap_to_cgc_grade`) ALREADY snaps and retains
`raw_score`; the override's catch shows Error (no fallback), and grading.js's `/api/messages`
comprehensive grade is overridden/unused by app.html. So no current live path can show 7.6 (the
5-book grades 7.5/6.0/8.0/5.0 confirm). RESOLVED: the 7.6 was Mike's typo — a re-run displayed 7.5;
production snapping confirmed working, drift hypothesis dead, repo read was correct. Final shape
per Mike: (a) `api_grade` re-snaps `final_grade` via the canonical `snap_to_cgc_grade` (defensive
belt-and-suspenders guard — kept), sets `raw_grade` = unsnapped weighted avg, logs both — the
raw retention has real value for task-4 calibration. (b) the dead grading.js `/api/messages`
comprehensive-grade path was DELETED (replaced with a no-op stub that points to /api/grade), NOT
snapped client-side — confirmed app.html overrides `generateGradeReport` and nothing executes the
stub's body (the step-skip caller at the old line 2050 resolves to the override). No duplicated
grade list anywhere; valuation consumes the snapped `final_grade` (app.html + grading.js paths).
(c) app.html `saveToCollection` sends `raw_grade`. Verified snap: 7.6→7.5, 7.74→7.5, 8.1→8.0,
7.75→8.0 (ties round UP), 0.7→0.5; Python↔JS parity confirmed. NOTE: raw is currently retained via
server LOG + response + save payload; DB persistence of `raw_grade` needs a column (follow-up — not
done, to avoid an unscoped migration).

**Task 4 — calibration tooling + protocol proposal (🟡, measure-don't-fix).** `test_haiku_vs_sonnet.py`
and `test_grading_consistency.py` moved off the retired `claude-sonnet-4-20250514` onto `models.py`
`get_model()` tiers (single source of truth — no future retired-string drift). No prompt changes.
**Proposed measurement protocol for the Sonnet-4.6 grade-lean hypothesis (Mike's call to run):**
  1. Priors = grades already stored in the collection DB (NOT memory). Pull N≥20 books with a stored
     grade + their 4 photos (R2 URLs).
  2. Re-grade each on the current `sonnet` tier (4.6) via `/api/grade` (or the pinned script), 3 runs
     each, recording BOTH snapped `final_grade` and `raw_grade` (raw avoids snap-quantization masking
     the lean).
  3. Report delta distribution: `raw_grade − stored_prior` per book — mean, median, stdev, histogram.
     A consistent +0.3..+0.7 mean across the upright control set ⇒ confirms the ~half-step lean.
  4. THEN (separate decision) calibrate via a prompt nudge or a post-hoc offset; re-measure.

**Task 5 — eBay 401 on load (🟢).** `checkEbayConnection` (`js/app.js`) called `/api/ebay/status`
(which is `@require_auth`) with no token → 401 on every load. Now skips when no `cc_token` and sends
`Authorization: Bearer` when present.

### Verification
- Task 1: Flask/Werkzeug 3.1.3 test — field @500 KB → 413 (repro), field @25 MB → 200 (safety net),
  file part @500 KB → 200 (primary fix bypasses the limit). py_compile + `node --check` all green.
- Task 3: `snap_to_cgc_grade` unit cases + JS parity (above).
- Tasks 2/5: client-side, reviewed (no browser/API here); 4: scripts compile, retired string gone.
- Verification agent (code-reviewer): no critical/important regressions. Latent note (resize assumes
  JPEG bare-base64 — true for all callers; clarified in docstring). Pre-existing (NOT this batch):
  `parse_multi_run_responses` bare `json.loads` → one bad pass 500s the whole multi-run (no partial
  fallback); worth a separate fix.

### Deploy / watch list for Mike
- **Cloudflare Pages purge is LOAD-BEARING:** `js/utils.js`, `js/grading.js`, `js/app.js`, `app.html`
  all changed — frontend must redeploy + cache purge or the 413/spinner/snap/eBay fixes won't ship.
- Render backend: `wsgi.py` (form limit), `routes/grading.py`, `routes/signature_orchestrator.py`.
- Correction to Part B note: app.html DOES use `/api/grade` (its inline override) — `/api/grade` is
  NOT dead. (Part B's "dead" note was from grepping only `js/`, missing app.html's inline script.)
- Post-deploy watch: real sig-check on the failing covers (Amethyst/Micronauts/Invaders) → 200, not
  413; grade displays an on-scale number; no `/api/ebay/status` 401 in console on load.
- Follow-ups surfaced (NOT this batch): persist `raw_grade` to DB (column); `parse_multi_run_responses`
  partial-failure handling; `/api/grade` dead-code cleanup is moot (it's live).

---

## Session 95 (Jun 7, 2026) — Batch 4 Part B: grading-input orientation pipeline

Items 1+2 of Batch 4. Protocol: reproduce → fix → verify → verification agent → STOP (NOT
committed — awaiting Mike). Files: `comic_extraction.py`, `routes/grading.py`, `js/grading.js`
(+ this notes file and the Part A `(c)` doc note still staged, all ride one commit).

**Item 1 — per-photo grading-input normalization (server-side, authoritative).** Grading uses 4
photos: front/spine/back (portrait when correct) + centerfold (legitimately LANDSCAPE — two-page
spread). Repro confirmed: `extract_from_base64` hardcoded `assume_portrait=True` (would force-rotate
a landscape centerfold to portrait), and `/api/messages` (spine/back/centerfold, one image per call)
did ZERO server-side normalization. Fix: new `assume_portrait_for(photo_type)` +
`normalize_for_photo_type()` in `comic_extraction.py` — policy in ONE place: centerfold/center/interior
→ EXIF-only, everything else (incl. unknown) → assume portrait. `photo_type` threaded from the
frontend through `/api/extract` (default `'front'`) and `/api/messages` (popped before forwarding to
Anthropic; absent → skip, preserving the follow-up-chat caller). Backend-first deploy is safe: old JS
sends no `photo_type` → messages-path normalization simply no-ops (never force-rotates an unlabeled
centerfold). Frontend (`js/grading.js`) now sends `photo_type` for all 4 steps — needs a Cloudflare
Pages deploy for full effect.

**Item 2 — 180° low-confidence extraction fallback (server-side).** Repro: a 180° flip is
dimensionally identical, so the dimension-based heuristic can NEVER catch it. Fix: `extract_from_base64`
runs one pass (`_run_vision_pass`); if low-confidence (`_extraction_low_confidence`: unparseable /
model-flagged is_upside_down / not-a-cover / no-title) it re-reads ONCE on a 180°-rotated copy and
keeps the higher-scoring pass (`_extraction_score`; ties keep pass 1). At most 2 vision calls. Every
retry logged `[VISION CALL #2 — doubled cost]` so the doubled cost is visible. Server is now
authoritative on orientation: the chosen result ALWAYS returns `is_upside_down=False` (pass-2 win sets
`orientation_corrected='180'`), so the grading.js client never re-rotates on top of the server.

### Verification
- Repro harness (real `normalize_orientation_b64`): centerfold force-rotated under old behavior;
  preserved under EXIF-only; 180° flip dimensionally invisible.
- Verify harness drove the REAL `extract_from_base64` with `_run_vision_pass` monkeypatched to scripted
  passes: no-retry on good pass1 (1 call); retry on each low-confidence reason (2 calls, never more);
  better pass wins; not-a-cover pass1 gets a 180° rescue before giving up; flags set correctly. Item-1
  policy + case/space tolerance + landscape→portrait vs centerfold-preserved all pass.
- Verification agent (code-reviewer): 2 real findings FIXED + re-verified — (1) `json.JSONDecodeError`
  from a regex-matched-but-invalid fragment escaped the orchestration and skipped the retry → now
  caught in `_run_vision_pass` (returns None = unparseable → retry); (2) pass-1-kept after an
  `is_upside_down` flag left `is_upside_down=True` → client would redundantly re-rotate → now suppressed
  (server authoritative). Issue 3 (quality gate pre-normalization) assessed NON-issue: the gate uses
  `min(w,h)` + Laplacian blur, both rotation-invariant. Issue 4 informational.
- Live-API JSON (real extraction + grading) is Mike's post-deploy check — no local ANTHROPIC_API_KEY.

### Revenue-path / deploy notes for Mike
- `/api/messages` IS the live grading path (Batch 3 flagged grading-input normalization as needing a
  re-spot-check; this is that change, now authorized). Spot-check a few real grades post-deploy.
- `/api/grade` (the labeled comprehensive endpoint) is DEAD in the live flow — no JS calls it; left
  untouched. Possible separate cleanup.
- Known cosmetic trade-off: for an upside-down FRONT, the server now corrects the READ but does not
  return the rotated image, and returns `is_upside_down=False`, so the client preview may show the
  original orientation (data is correct). Ties into the deferred item 3 (preview). Easy follow-up:
  return the corrected image from `/api/extract`.

---

## Session 94 (Jun 6, 2026) — Batch 4 Part A: Sig-ID gating, barcode, dep-monitor email

Batch 4 split into Part A (correctness/billing/monitoring) + Part B (image pipeline). Part A
COMMITTED + DEPLOYED as `d254309` (pushed to origin/main; Free-tier 403 + seed-email field tests
confirmed live, per Mike 2026-06-07). Part B = items 1+2 (Session 95 above); item 3 preview deferred.

**Item 4 — server-side signature-ID tier gating** (`routes/billing.py`, `routes/signature_orchestrator.py`).
Added `signature_id_per_month` to PLANS (free=0, pro=0, guard=10, dealer=-1) and
`get_signature_id_entitlement(user_id)` (fails CLOSED on DB error/unknown user; admin=unlimited;
paid plans need active subscription). `match_signature` now gates BEFORE the expensive match:
error→503, no_access→403, capped plan over limit→429 (fail CLOSED on usage-read error too),
unlimited→proceed. Replaced the old flat `MONTHLY_SIG_LIMIT=10`-for-all + fail-OPEN logic. Usage
Tier policy per Mike 2026-06-06. NOTE: Mike's log confirmed the earlier "flicker" was UI-only (no
/match fired) → that's on the UI-polish list; this gating stands on code grounds.
  - **Amendment (Mike, pre-commit):** (a) CAP SEMANTICS — the Guard cap counts CONFIDENT matches
    only (top confidence >= LOW_CONFIDENCE_THRESHOLD 0.50). Increment happens AFTER the result is
    known and ONLY for capped plans; no-match/below-floor/error never count; blocked calls (403/429)
    never process/bill. Dealer/admin are NOT counted in the cap column (it never resets for them) —
    their usage is monitored via the per-call `[SigID] match served ... cap_counted=...` log instead.
    (b) NO-MATCH HONESTY — `/v2/match` previously force-matched (returned nearest-neighbour top5 + a
    `low_confidence_match` flag). Now returns `matched: false` + "Signature not in our reference set"
    when top confidence < floor, rather than attributing the nearest neighbour. `matched` is the
    authoritative signal; top5 retained as transparency/candidates. Same no-confident-hallucination
    rule as Batch 3 extraction. Verification agent flagged dealer counter-increment (resolved as
    above — log-based visibility, counter is Guard-only).
    (c) THRESHOLD CONFIG — `LOW_CONFIDENCE_THRESHOLD` now reads `SIG_LOW_CONFIDENCE_THRESHOLD`
    (default 0.50), so floor + cap boundary retune via env, no code change. Marked PROVISIONAL —
    calibrate at the signature-v2 accuracy re-measurement (87% target). Single-definition property
    preserved (one constant feeds both the no-match floor and the cap boundary). Cap semantics
    verified locally: Guard no-match → counter unchanged; confident → +1 (true RETURNING count);
    9/10 + no-match + confident → ends at 10, not 11.

**Item 5 — barcode decoder addon-None** (`comic_extraction.py`). `decode_barcode` now runs ONLY when
`barcode_source == 'pyzbar'` (a scanner-confirmed addon), never on the vision model's guessed
`barcode_digits`. Without a confirmed addon: keep main UPC (series ID) only, mark
`barcode_source='vision_unverified'`, don't derive issue/printing/variant. Fixes false decodes like
Amethyst Annual #1 (no post-2008 add-on) → "issue 251".

**Item 6 — dep-monitor emails on state change, not every boot** (`dependency_monitor.py`).
`_send_alert_email` dedups against a self-creating DB table `dependency_alerts` (CREATE TABLE IF NOT
EXISTS — no migration needed) so a permanent state (eBay `unmonitorable`) emails once, not on every
Render restart. Prunes resolved keys so recurrence re-alerts. Falls back to in-memory `_emailed_keys`
(now also pruned) if DB unavailable.

### Verification
All three verified locally: entitlement across all tiers incl. fail-closed; barcode gate (pyzbar
decodes, model-guess doesn't); dep-monitor new→email, reboot→silent, resolved→prune, recurs→re-alert
(DB + in-memory paths). Verification agent: 1 false positive (claimed tz-naive/aware datetime crash —
code compares .year/.month ints, no datetime comparison; matches existing valuations/grading caps),
2 real findings FIXED (Dealer usage log always said used=1 → now RETURNING true count; in-memory
fallback didn't prune → now does).

### Files Modified (Batch 4 Part A)
- `routes/billing.py`, `routes/signature_orchestrator.py`, `comic_extraction.py`, `dependency_monitor.py`

### Still to do
- Part B: item 1 (grading-input normalization, per-photo) + item 2 (CCW 180° low-confidence fallback).
- Deferred: item 3 (preview — only if on-device still sideways). UI-polish: sig-section flicker.

---

## Session 93 (Jun 6, 2026) — Batch 3: Extraction & Orientation Regression

Four items (reproduce → fix → verify → agent → STOP). NOT committed/deployed — awaiting Mike.
Batches 1 (`cf9c3a2`) and 2 (`7d8aad7`) already deployed.

1. **Orientation pipeline (extraction) — root cause + fix.** `app.html`'s `extractComicData`
   (line 1789) sends the RAW front photo to `/api/extract` with no normalization, bypassing the
   client EXIF/canvas code (utils.js `processImageForExtraction`, grading.js
   `processImageWithOrientation`). Server-side did zero normalization. The Anthropic vision API
   ignores EXIF and reads raw pixels → 90deg-rotated covers read as garbled/hallucinated titles
   (Hercules→"Power of The Force", Invaders→"Marvel Comics #60", Atari Force→"Sgt. Rock #5").
   - **Fix (authoritative, server-side):** new `comic_extraction.normalize_orientation_b64()` —
     (a) `ImageOps.exif_transpose` (handles rotated-WITH-EXIF, the real phone→app.html upload, with
     correct direction + strips tag); (b) `assume_portrait` heuristic: if still landscape after EXIF,
     rotate 90deg CCW to portrait (handles hard-rotated NO-EXIF images, e.g. Google Photos
     re-exports, which the test fixtures turned out to be). Runs before BOTH barcode scan and the
     vision call; fails loud on undecodable input; tolerates data-URL prefix. Extraction calls it
     with `assume_portrait=True` (front cover is always portrait).
   - **Key discovery:** the supplied test fixtures (FromGooglePhotos) are landscape `4080x3072` with
     EXIF orientation=1 (tag stripped, rotation NOT baked) — so `exif_transpose` alone was a no-op on
     them; that's why the portrait heuristic was needed. Real phone uploads carry EXIF and are fixed
     by part (a). Direction empirically CCW (verified by rendering all 3 covers).
2. **Extraction model routing.** Extraction still correctly uses the `haiku` tier
   (`call_with_fallback(_client, 'haiku', ...)`); Batch 2 did NOT sweep it to Sonnet. Only the
   `/api/extract` usage LOG mislabeled it `SONNET` → fixed to `get_model('haiku')`.
3. **Re-test failing set (acceptance for 1+2).** Could not run a live extraction (no local
   ANTHROPIC_API_KEY; prod still pre-fix). VISUAL acceptance instead: ran the actual
   `normalize_orientation_b64(assume_portrait=True)` on all 5 covers and rendered outputs — all three
   failing covers now upright + fully legible (Atari Force, Hercules: Prince of Power #1, The Invaders
   #41 with 60c price clearly separate from issue 41); controls (Amethyst, Micronauts) untouched.
   Live-API JSON confirmation is Mike's post-deploy check. PROPOSED (not built): add these 5 covers
   as a permanent extraction regression fixture once the pinned-model test scripts are updated.
4. **Mobile 3-photo slab report.** Reproduction in code found NO 4-photo gate: the grading-report
   path requires only the FRONT cover (app.html:2195-2196); "of 4" is a label and "<4" a non-blocking
   warning; FAQ confirms "front required at minimum, proceed with fewer"; git history shows no 3->4
   change. So NOT a code regression in the visible path — likely stale cached JS, a mobile rendering
   issue, or a different flow. Needs a device repro/screenshot from Mike. No code change.

### Verification agent
Ran twice (after core fix, then after the portrait heuristic). No critical/correctness issues.
First-pass finding (data-URL prefix robustness) addressed. Confirmed: no double-rotation, gate
correct, CCW direction matches intent, only the front-cover path uses assume_portrait.

### Items needing Mike's call (NOT changed)
- **Symptom #3 (preview shows un-corrected):** display is separate from the API payload (uses the
  client raw image). Modern browsers auto-orient `<img>` by EXIF, so the raw-with-EXIF preview likely
  shows upright already; if not, return the normalized image from `/api/extract` for the preview.
- **Grading inputs:** brief says "before any API call," but grading is out-of-scope + passed.
  `/api/grade` and `/api/messages` still send un-normalized images. Applying the same normalization
  there would fix grading orientation but changes the revenue-path inputs (re-spot-check needed).

### Files Modified (Batch 3)
- `comic_extraction.py`, `routes/grading.py`

---

## Session 92 (Jun 6, 2026) — Batch 2: Model Migration + Hardening

Three tightly-scoped items (reproduce/establish → fix → verify → verification agent). NOT yet
committed/deployed — awaiting Mike's authorization. Batch 1 (`cf9c3a2`) is already deployed live.

1. **Migrated off `claude-sonnet-4-20250514`** (retires 2026-06-15 — deadline-driven). `models.py`
   sonnet chain → `claude-sonnet-4-6` (the deprecations.info-listed replacement), removed the
   retiring string from both `sonnet` and `sonnet-new` plus the aged `claude-3-5-sonnet-latest`.
   Centralized both grading paths through `models.py` + `call_with_fallback`: `/api/messages`
   (`routes/grading.py`) now ignores any client-supplied `model` and uses tier (default 'sonnet');
   `/api/grade` `run_grading` switched from `create(model=SONNET)` to `call_with_fallback`. Frontend
   `js/grading.js` (2 spots) now sends `tier: 'sonnet'` instead of the hardcoded retiring model.
   Added a thread-safety lock to `_active_index` (the threaded multi-run grading path now mutates it).
   - **Deprecation sweep:** on the Anthropic API, ONLY `claude-sonnet-4-20250514` was on a near
     clock. Other feed hits (3-5-sonnet/Vertex, sonnet-4/Bedrock, haiku-4-5 & sonnet-4-5/Azure,
     opus-4-6/Azure) are OTHER platforms (Vertex/Bedrock/Azure), not our direct Anthropic API.
   - ⚠️ **Revenue path:** grading model changed Sonnet 4 → Sonnet 4.6. Mike should spot-check a few
     real grades after deploy (a live grading call needs ANTHROPIC_API_KEY, only set in prod).
2. **JWT_SECRET fail-loud** (`auth.py`): if unset or == 'change-me-in-production', refuse to start in
   production (detected via Render's `RENDER` env var); in dev, warn loudly and use the dev default.
   ASCII-only messages (L-2026-015 — emoji crashed Windows cp1252 stdout in the dev path).
3. **eBay RSS 403** (`dependency_monitor.py`): diagnosed as site-wide Akamai bot-wall on
   developer.ebay.com (all paths, any User-Agent, incl. from Render). No automatable eBay
   deprecation source exists. Reclassified the eBay check from `error` to `status: unmonitorable`
   (honest degradation, cached 24h, retries daily in case the wall lifts) with manual-tracking
   guidance. `check_all()` still runs all four checks isolated.

### Verification
- Reproduced/established each item first (sonnet call-site grep + deprecation sweep; JWT default;
  eBay 403 with default + browser UA across multiple paths).
- All verified locally: models chains clean + fallback (incl. 8-thread concurrency, no index
  overrun); `/api/messages` overrides old model → 4-6; JWT refuse/warn across prod/dev contexts;
  eBay → unmonitorable; monitor no longer warns about a model we use.
- Verification agent: 3 findings. #2 (thread-unsafe `_active_index`) FIXED (lock + over-advance
  guard). #1 (`SONNET` static constant / dead `_ModelProxy`) — pre-existing, logging-only,
  left as-is (converting risks passing non-str to DB logging). #3 (auth import-raise on Render
  shell) — latent only; scripts don't import auth and Render shell inherits JWT_SECRET.

### Files Modified (Batch 2)
- `models.py`, `routes/grading.py`, `js/grading.js`, `auth.py`, `dependency_monitor.py`

### Still open / follow-ups
- `_ModelProxy` dead code + `SONNET`/`HAIKU` static constants (logging accuracy in
  `/api/valuate`, `/api/extract`) — separate cleanup.
- Frontend `js/grading.js` deploys via Cloudflare Pages (separate from Render). Backend ignores the
  client `model` regardless, so deploy order doesn't matter — but the JS cleanup needs a Pages deploy.
- CLAUDE.md deploy-note fix (auto-deploy unreliable) — spawned as a separate task.

---

## Session 91 (Jun 6, 2026) — Reconciliation + Fixes Batch 1

### What Was Done

Ran a read-only reconciliation pass (`docs/sessions/RECONCILIATION_2026-06-06.md`), then
implemented Fixes Batch 1 (reproduce-before-fix; verified; NOT yet committed/deployed — awaiting
Mike's authorization).

1. **Fixed the dead dependency monitor** (`dependency_monitor.py`). Root cause: `deprecations.info`
   changed its JSON from `{"items":[...]}` to a top-level array, so `check_anthropic()` crashed on
   `data.get("items")` — and because it ran first in `check_all()`, it killed every check (eBay RSS,
   Stripe, and the new eBay account-deletion self-check never ran). Fix: shape-tolerant parsing
   (handles both dict+array, `model_id`/`model_name`), all parsing inside try/except, each check
   isolated in `check_all()` so one failure can't block others, failed checks now surface a loud
   `status: error` entry (with a ~5 min backoff so an outage doesn't hammer upstream).
2. **Hardened the Stripe webhook** (`routes/billing.py`). Was processing events UNVERIFIED when
   `STRIPE_WEBHOOK_SECRET` was unset (forgeable → self-upgrade to paid tier). Now: unset secret →
   500 + refuse; bad signature → 400 + refuse; valid → process. Secret read per-request.
3. **Repointed `/api/signatures/db-stats`** (`routes/signatures.py`) from the stale bundled
   `signatures_db.json` snapshot to the live `creator_signatures` + `signature_images` tables (the
   stale endpoint reported 80/97 vs the live 99/203). Graceful 503 if no DB; backward-compatible
   response keys. The v1 matcher still reads the JSON snapshot — left untouched (separate cleanup).
4. **Documented all env vars** in `docs/technical/ARCHITECTURE.txt` (was 1 of ~32) — name, purpose,
   reading module, unset behavior. Flagged `JWT_SECRET`'s insecure `'change-me-in-production'`
   default (auth.py NOT changed this batch).

### Verification
- Reproduced bugs #1 and #2 first (tracebacks / code-path quotes captured in session).
- All fixes verified locally (monitor: all checks run + isolation + backoff; webhook: 500/400/200
  with no handler calls when rejected; db-stats: 503 + correct aggregation). Ran a code-review
  verification agent; its 3 findings (retry backoff, `none` quality bucket, per-request secret read)
  were all addressed and re-verified.

### Follow-ups surfaced (NOT in this batch — own briefs)
- 🔴 **`claude-sonnet-4-20250514` retires 2026-06-15** (the now-working monitor caught it) — Sonnet
  migration gets its own brief.
- 🟡 **eBay RSS feed returns 403** (`developer.ebay.com/rss/api-status`) — check can't fetch; needs
  a new URL or a User-Agent header.
- 🟡 **v1 signature matcher** still on the stale JSON snapshot.
- 🟡 **`JWT_SECRET` insecure default** in `auth.py` — harden separately.

### Files Modified (Batch 1)
- `dependency_monitor.py`, `routes/billing.py`, `routes/signatures.py`, `docs/technical/ARCHITECTURE.txt`
- `docs/sessions/RECONCILIATION_2026-06-06.md` (new, from the reconciliation pass)

---

## Session 90 (Mar 24, 2026) — Mobile Extraction Fix + Dependency Monitor

### What Was Done

1. **Fixed mobile image extraction** — Three bugs causing extraction failures on mobile:
   - Images now always go through canvas (max 2048px, JPEG normalized) — fixes oversized payloads
   - Rewrote EXIF orientation parser — was bailing early on valid JPEG segments, sending rotated photos uncorrected
   - Added `is_comic_cover` validation to extraction prompt — non-comic photos get a clear error

2. **Fixed Haiku model retirement** — `claude-3-5-haiku-latest` returned 404, broke all extraction. Updated to `claude-haiku-4-5-20251001`. Migrated `comic_extraction.py` from raw `requests.post()` to Anthropic SDK with `call_with_fallback()`.

3. **Built automated dependency monitoring** — `dependency_monitor.py` checks three services:
   - Anthropic model retirements (via deprecations.info)
   - eBay API deprecations (via developer.ebay.com RSS)
   - Stripe SDK version drift (via PyPI)
   - Email alerts + admin dashboard warning banner
   - Runs on every Render health check, cached 24h

4. **Added enforcement rules** — CLAUDE.md now mandates all new third-party services be registered in dependency monitor. Saved as persistent memory.

5. **Consolidated report loading UI** — Replaced 3 simultaneous loading indicators with single animated gradient spinner + cycling status messages. Works above the fold on mobile.

6. **Fixed health endpoint crash** — `dependency_monitor.py` was taking down the `/health` endpoint. Wrapped in try/except, made resend import optional.

7. **Fixed grading report error** — Loading spinner refactor accidentally removed `defectsGrid` variable declaration, causing ReferenceError that showed "Error/FAILED" even though grading succeeded. One-line fix.

8. **Updated MASSE + TheFormOf CLAUDE.md** — Added mandatory dependency monitoring rules to both projects. TFO version includes Layer 2 (client app dependencies) and billable "Managed Updates" service concept.

### Files Created
- `dependency_monitor.py`

### Files Modified
- `js/grading.js`, `comic_extraction.py`, `models.py`, `routes/utils.py`, `routes/admin_routes.py`, `admin.html`, `app.html`, `CLAUDE.md`

### Next Up
- Continue mobile testing (extraction + grading confirmed working)

---

## Session 89 (Mar 11-12, 2026) — Admin Insights + Unified AdminHub Dashboard

### What Was Done

1. **Enhanced Admin Users Tab** — Rewrote `/api/admin/users` to JOIN with collections, comic_registry, request_logs, api_usage, user_feedback tables. Each user row now shows: collections count, slab guard registrations, API calls, AI cost, last activity, top actions breakdown, feedback count/avg. Expandable rows show full detail. Committed and pushed.

2. **Enhanced Feedback Endpoint** — Updated `/api/admin/feedback` to JOIN with collections table via `grading_id`, returning comic title, issue number, grade, and photo URLs alongside each feedback entry. Feedback now shows what comic was being graded when the user left feedback.

3. **AdminHub — Unified Cross-Domain Dashboard** — Built a single-page admin dashboard that aggregates data from both SlabWorthy and MASSE into one view. Located at `C:/Users/mberr/theformof/`.
   - **Dual auth engine**: JWT for SlabWorthy, Supabase SDK for MASSE
   - **Connection dots**: Green/red per-app status in header
   - **Overview tab**: Aggregated stats across all apps
   - **Per-app tabs**: Users, Beta Codes, Errors, Usage, Waitlist, Feedback, NLQ Query
   - **Modular config**: Adding a 3rd app = one config object in the APPS array
   - **Runs locally**: `node serve.js` → `http://localhost:8080`
   - **Future-ready**: TheFormOf placeholder tab (greyed out) already in place

4. **MASSE CORS Update** — Added `localhost:8080` and `127.0.0.1:8080` to MASSE backend CORS whitelist so AdminHub can call MASSE APIs cross-origin. Committed and pushed.

5. **Bug Fixes**
   - Fixed SlabWorthy login URL in AdminHub (`/api/login` → `/api/auth/login`)
   - Fixed race condition where `closeLoginModal()` nulled `loginTargetApp` before the post-login code could use it
   - Fixed `substring()` error on numeric SlabWorthy user IDs (MASSE uses UUID strings)

### Files Created
- `C:/Users/mberr/theformof/index.html` — AdminHub dashboard (~1200 lines, single-file)
- `C:/Users/mberr/theformof/serve.js` — Express static file server
- `C:/Users/mberr/theformof/package.json` — Express dependency

### Files Modified
- `routes/admin_routes.py` — Enhanced `/api/admin/users` with 6 additional SQL joins; enhanced `/api/admin/feedback` with collection/comic context
- `admin.html` — Enhanced Users tab (10 columns, expandable rows, timeAgo, activity chips)
- MASSE `backend/server.js` — Added localhost:8080 to CORS origins
- MASSE `backend/routes/admin.js` — Enhanced `/api/admin/users` with companies, invite_codes, token_usage joins

### Planning Docs
- `docs/UNIFIED_ADMIN_PLAN.md` — Updated to reflect AdminHub is built (Phases 1-3 complete)
- Same doc mirrored in MASSE repo

### What's Next
- **Deploy to Render** — Run `deploy` CLI command to push enhanced admin API endpoints live. The AdminHub dashboard calls the production APIs, so the enriched user data (activity, costs, feedback context) will only show once the backend is redeployed.
- **TheFormOf** — When the 3rd app is built, add one config object to AdminHub's APPS array and it auto-integrates.
- **Phase 4** — Cross-app user matching (same email across apps), unified cost dashboard, cross-app NLQ queries.

### Previous Session
- Session 88 (Mar 8) — Beta User Management: Grading Cap (25/month) + Feedback System + Waitlist Admin + Invite Flow
