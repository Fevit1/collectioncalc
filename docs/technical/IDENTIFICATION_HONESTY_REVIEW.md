# Identification-Honesty Review — extraction pipeline (private-beta readiness)

> **Status:** Read-only diagnostic + architectural map + fix-direction recommendation.
> Nothing built or committed at authoring time. Drafted 2026-06-15 (Session ~104).
> **Companion data:** `haiku_vs_sonnet_results.json` (Haiku-vs-Sonnet extraction/grading bench).
> **Theme parent:** `docs/technical/EXTRACTION_ROBUSTNESS_NOTES.md` — "the book the model
> *reads* and the identity we *price* can diverge." This is that theme one layer up: honest
> handling of identification uncertainty, before valuation.

## The problem (observed hands-on, grade flow)

Extraction mis-identifies or fails to identify the book, and the pipeline produces a confident
grade + FMV + slab verdict anyway. Three failure modes:
1. **Wrong-but-confident** — Atari Force #4 read as #2; valuation returns an FMV for the wrong issue.
2. **Identified-nothing-but-proceeded** — Absolute Batman #19 (1:25 variant, mylar) read as only
   "Batman" (no issue, no variant), yet returned a 9.0 + FMV + verdict. Most dangerous case.
3. **Partial** — Watchmen: title read, issue missed.

The launch gate is **not** extraction accuracy (an infinite chase). It is that the pipeline does
not honestly handle its own uncertainty: when it doesn't know the issue, it must not fabricate a
valuation as if it does. Same principle as the valuation-confidence work, one layer up.

---

## Section 0 — How identification works today, and what signal it leaves on the table

It's a **combination, sequenced correctly** in `extract_from_base64` (`comic_extraction.py:547`):
1. Server-side orientation normalize.
2. **Barcode scan first** via pyzbar (`comic_extraction.py:135`) — 4 rotations; reads the main
   UPC-A/EAN-13 (series ID) and the 5-digit EAN-5 IIICP supplement.
3. **Claude Haiku vision pass** (`comic_extraction.py:477`, `_run_vision_pass`) with
   `EXTRACTION_PROMPT` → title / issue / variant / publisher / year.
4. **Merge** (`comic_extraction.py:635-687`) — `decode_barcode` (`comic_extraction.py:235`) turns a
   pyzbar-confirmed addon into issue/cover/printing.

So: **not** pure vision; **yes** barcode; **no** cover-match/reference-catalog lookup exists (no
GCD/ComicVine/Marvel API — identity is vision + barcode only). Order is right: precise signal
first, vision fallback.

**Does it use the barcode when present? Only partially — the key findings:**
- **The decoded-barcode *issue* is computed and then never used.** `decode_barcode` returns
  `issue = digits[0:3]` (`comic_extraction.py:257`), but the merge block
  (`comic_extraction.py:663-681`) writes back only `printing`, `cover`, `is_variant`, `is_reprint`
  — it **never sets `extracted['issue']`**. The displayed issue *always* comes from vision, even
  when a barcode was read perfectly. This is the easy signal left on the floor.
- The addon is trusted only from pyzbar, never from vision's own `barcode_digits`
  (`comic_extraction.py:663,682`) — a deliberate, correct guard (it prevented false decodes like
  Amethyst→"issue 251"). But pyzbar reading a tiny, often-vertical EAN-5 through mylar/glare is
  unreliable, so the barcode-issue signal is frequently unavailable in practice.
- `decode_barcode` assumes the post-2008 Diamond IIICP format — **vintage books have no addon by
  design.**

**Failure-mode → method mapping:**
| Observed | Why |
|---|---|
| Atari Force #4 → #2 (wrong-but-confident) | 1984 book, **no IIICP addon exists** → vision-only issue → misread. No barcode signal possible. |
| Absolute Batman #19 1:25 in mylar → only "Batman" | Modern book *has* a barcode, but mylar+glare defeated pyzbar's EAN-5 **and** vision couldn't read the cover number. **And** the legible white "#19" top-left was missed by the Haiku pass, and "ABSOLUTE BATMAN" was truncated to "Batman" — a vision/model-tier miss, not just bad capture (see Delta below). |
| Watchmen → title, no issue (partial) | Vision got title, missed issue; no readable addon to rescue it. |

**Sequencing verdict:** order is fine; the *merge* is the defect — the most reliable signal
(barcode-decoded issue) is dropped, and **barcode↔vision agreement is never used as a confidence
check** (agreement = free high-confidence signal; disagreement = free force-confirm trigger).
Method improvement helps modern books but **cannot** help the vintage no-addon cases (Atari/
Watchmen) — necessary but not sufficient; the honesty layer is still required.

---

## Section A — Is there a confidence signal? (the crux: essentially no)

- **App extraction path: no per-field confidence.** `EXTRACTION_PROMPT` returns best-guess strings
  only. The *sole* uncertainty signal is `issue == ""`. A wrong-but-present issue (Atari #2) is
  **indistinguishable** from a correct one — zero signal for "confidently wrong."
- There is internal coarse scoring (`_extraction_score` `comic_extraction.py:516`,
  `_extraction_low_confidence` `comic_extraction.py:533`) but it's title/cover/upside-down only,
  used *solely* to trigger the 180° re-read, and **never returned to the caller**. Issue-level
  confidence isn't considered.
- The pattern exists elsewhere: the Chrome-extension path emits `confidence` + `gradeConfidence` +
  an explicit `{"error":"Cannot identify comic","confidence":0}` (`routes/vision.py:197`). The
  grader emits `areas_not_visible` (`grading_engine.py:283`). So honesty primitives exist — just
  not in the app's *identification* path.
- **How hard to get a coarse one? Easy.** (1) derive `issue_confidence = could_not_determine` when
  `issue==''` — zero model cost; (2) add `issue_confidence: high|low|unsure` to the prompt JSON +
  defaults — one prompt edit; (3) barcode↔vision agreement — a model-free high-confidence signal
  for modern books. "Confidently wrong" is the hard residue — best mitigated by the barcode
  cross-check + user confirm, not by a self-reported number (a weak Haiku pass that misses legible
  text will self-report confident — see Delta).

---

## Section B — Halt-on-failure: where it could live, what should happen

**Path:** `/api/extract` → display (`app.html:1864`) → `/api/grade` (grades condition; identity is
passthrough metadata, defaults `title='Unknown'`/`issue='?'`, `routes/grading.py:385-386`) →
`calculateGradingRecommendation` → `/api/sales/valuation` (`app.html:2546,2564`).

**Today there is no halt — and two places actively manufacture an answer:**
- `app.html:2554`: valuation issue defaults to **`'1'`** when missing.
- `routes/sales_valuation.py:228,260`: the issue filter is applied only when issue is truthy and
  not in `['null','undefined','None']`. An **empty issue → no issue filter → the endpoint blends
  *all* issues of the title** into one median and returns a confident-looking FMV (the "Batman" →
  whole-series blend). It still sets `estimated`/`confidence`, which the frontend discards.

Also note `/api/grade`'s `confidence` is purely a function of **photo count** (1→65% … 4→94%,
`routes/grading.py:517`) — blind to whether identification succeeded.

**Where halt should live:** one client-side gate between extraction and valuation — if issue is
absent/low-confidence, **don't call `/api/sales/valuation`**; render "couldn't identify the issue —
confirm it." Server belt: `/api/sales/valuation` should refuse to price (or return a hard
`issue_required`) instead of blending all issues when issue is empty (`routes/sales_valuation.py:228`).

**Batman case, what *should* happen:** show the grade (condition is observable — 9.0 stands), but
**halt valuation + slab verdict** until the issue is confirmed.

**Grade separable from identification? Yes, cleanly.** `/api/grade` scores condition from photos and
only echoes title/issue as metadata (`routes/grading.py:513-516`); it never uses them to grade. So
"grade proceeds; valuation gates on identity" needs **no backend re-architecture**.

---

## Section C — User-confirm: the cheapest fix, and it's already ~90% built

- **The editable confirm UI already exists.** On extract success, app.html builds an inline
  Title/Issue/Publisher/Year edit form (`app.html:1884`) — but it's `display:none`, revealed only by
  clicking ✏️ (`app.html:1876`). On extract *failure*, the same form shows **by default**
  (`display:block`, Title required, `app.html:1976`). `saveEdit` (`app.html:2138`) already writes
  back to `extractedData`. The wiring is done — the only question is *when* it shows and whether
  issue is required.
- **Minimal fix:** when identification is low-confidence/absent, show the form **by default** (reuse
  the failure-path behavior) and require the issue before enabling valuation — instead of
  "✓ Identified: Batman #?" with the form hidden behind a pencil.
- **Does confirm subsume the confidence signal?** Partially. Always-confirm catches everything but
  adds friction to the ~80% correct cases. Best: use a coarse confidence (Section A) to decide
  *when* to force confirm — flow silently when confident, force-confirm when unsure. They compose.
  Either way, **the "✓ Identified" checkmark should never appear when issue is empty.**

---

## Secondary — mylar grade inflation (flag only)

The grader has a *partial* honesty primitive — `areas_not_visible` (`grading_engine.py:283`) and
"note which areas you could NOT directly observe" (`grading_engine.py:259`) — but **no
mylar/sleeve/glare detection**, obstruction doesn't penalize the grade or its confidence, and
extraction is even told to "Ignore bag/sleeve artifacts." A sleeved book grades 9.0 on a
glare-obscured cover with no penalty. **Separate grading-accuracy item.** Cheap future hook: have
the grader set an `obstructed` flag (it already reasons about visibility) and treat it like low
photo-count confidence. Not part of this gate.

---

## Delta — the Absolute Batman photo + the model-tier finding (2026-06-15)

Mike supplied the actual cover photo with annotations. This sharpened the findings:

1. **Reclassified the Batman case.** The `#19` was plainly legible (white, top-left) and vision
   still missed it; the title came back "Batman" when the cover reads "**ABSOLUTE** BATMAN." So it's
   **two vision misses in one book** (dropped issue + truncated series), not bad input.
2. **Identification runs on the *weakest* model.** Extraction = **Haiku**
   (`comic_extraction.py:483`); grading = **Sonnet** (`routes/grading.py:449`). The step that must
   be right for an honest valuation uses the cheaper/weaker OCR model. A legible white "#19" on a
   dark, busy, full-bleed painted cover is exactly where Haiku's small-text/low-contrast OCR fails
   and Sonnet usually doesn't. **Decision made: move extraction to Sonnet.**
3. **Barcode confirmed not a silver bullet.** The Absolute Batman barcode was small/dark/shadowed/
   through mylar — marginal to decode; barcode writeback would help clean modern books, not this one.
4. **Self-reported model confidence is the weakest signal option** — a pass that misses legible text
   will self-report confident. Lean on objective signals (`issue==''`, barcode↔vision agreement) +
   user confirm.

---

## Recommended fix direction (combination; all small)

1. **Honesty gate (A→C→B) — the launch gate. ≈ 1–1.5 sessions.** Built regardless of the model
   approach (even Sonnet won't be perfect on vintage no-barcode books).
   - Derive coarse `issue_confidence` (`could_not_determine` when empty).
   - Frontend: on low-confidence/absent issue → drop the "✓ Identified" framing, show the existing
     edit form by default, require issue, gate the `/api/sales/valuation` call on a confirmed issue.
     **Remove the `|| '1'` default** (`app.html:2554`).
   - Server belt: don't blend-all-issues on empty issue (`routes/sales_valuation.py:228`) — require
     issue or return `issue_required` (no FMV).
   - Let grade proceed; gate only valuation + verdict.
2. **Extraction model: Haiku → Sonnet** (decided). Global vs conditional re-read is being settled
   with the `haiku_vs_sonnet_results.json` numbers (see the separate numbers analysis). Target the
   `sonnet` tier in the existing `call_with_fallback` (currently on `claude-sonnet-4-6`), not a
   hardcoded string.
3. **Barcode-issue writeback** (complementary; same capability as the parked barcode
   variant-subtyping roadmap item): when pyzbar confirms an addon, write the decoded issue into
   `extracted['issue']`, and use barcode↔vision agreement as a confidence signal. Helps modern
   books; doesn't replace the gate.
4. **Not now (per Mike's framing):** chasing vision accuracy; a reference-catalog/cover-match lookup
   (GCD/ComicVine) — the real long-term identity fix, but a multi-session third-party integration
   with its own dependency-monitoring burden. Post-launch.

The launch-shaped fix is C+B seeded by a coarse confidence from A, with the model-tier change and
barcode writeback as accuracy complements. It's small because the confirm UI, the grade/identity
separation, and the valuation `estimated`/`confidence` outputs already exist — wiring and gating,
not new architecture.
