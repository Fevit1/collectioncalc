# Grade-Submission Retention — Spec (DESIGN / SCOPING ONLY)

> **Status:** Draft for review — **build nothing yet.** No migration, no schema change, no code.
> **Author:** DO (Claude) · **Date:** 2026-06-19 · **Owner decision:** Mike
> **Origin:** The matbanshee undergrading investigation (2026-06-08, user_id 21). We could not
> diagnose his complaint because **nothing about an unsaved grade is retained** — no photos, no
> assigned grade, no subgrades, not even which comics. This spec defines what to retain so that any
> future grading-accuracy complaint is diagnosable.

---

## 0. The problem, precisely

Today a grade only leaves a trace if the user **saves the comic to their collection**. For a grade
that is run and not saved:

- `collections` / `graded_comics` → **0 rows** (confirmed for user 21).
- `api_usage` → stores only endpoint, model, token counts, cost. **No grade, no photos.**
- `request_logs` → `request_data`, `response_summary`, `request_size_bytes` all **NULL**.
- R2 → **nothing uploaded** (see §2 lifecycle; confirmed: user 21 made *zero* `/api/images/*`
  calls across all 3 grades).

Net: the core promise of the product (grade accuracy) has **no audit trail** for the exact event a
user disputes. This spec closes that.

---

## 1. WHAT TO RETAIN (per grade, even unsaved)

Enough to reconstruct *"what did the grader see, and what did it conclude."* All of this already
exists in memory at grade time — it's computed in `grading.py` / `grading_engine.py` and then
discarded. Retain:

| Field | Source today | Notes |
|---|---|---|
| `user_id` | `g.user_id` | who |
| `created_at` | now | when |
| `grading_id` | client-supplied (optional) | links to the client's grade session if present |
| **Submitted photos** | the in-request base64 (`images[]`) | persist to R2 — see §2 |
| `photo_labels` | `photo_labels` (`front`/`spine`/`back`/`centerfold`) | which angle each image is |
| `photos_used` (count) | `result['photos_used']` = `len(images)` | the forensic signal we used for matbanshee |
| Identified `title` / `issue` / `year` / `publisher` | extract result passed into grade | the "which comic" that was missing |
| **Overall grade** + `grade_label` | `compute_grade()` → snapped CGC grade | the headline number |
| **8 subgrades** (`category_scores`) | `grading_engine.CATEGORY_WEIGHTS` keys | `cover_front, spine, corners, edges, cover_back, color_gloss, structural, interior` (0–10 each) |
| `raw_score` / `limiting_factor` | `compute_grade()` output | why the grade landed where it did |
| Internal `confidence` | `result['confidence']` = `{1:65, 2:78, 3:88, 4:94}[len(images)]` | derived from photo count |
| `model` | `get_model('sonnet')` (incl. fallback) | which model graded |
| `run_count` | `result['run_count']` | single-run vs multi-run consensus |
| `grade_reasoning` / `observations` | `result['grade_reasoning']` | the model's notes if captured |
| `defects` (per area) | `result['defects']` | front/spine/back/interior/other |
| `areas_not_visible` | grade response | flags single-photo / occluded grades |
| `saved_collection_id` | NULL until/unless saved | back-link if the user later saves this grade |

### ⚠️ Honesty flag — the "180° re-read"
The brief asks to retain *"whether the 180° re-read fired."* **There is no 180° low-confidence
re-read in the grading path.** The only 180° logic in the codebase is **barcode scanning rotation**
(`routes/barcodes.py`) and **fingerprint orientation** for the registry
(`routes/fingerprint_utils.py`) — neither touches grading. So this field would be **always NULL /
N/A today.** Two honest options: (a) omit the field until such a feature exists; (b) include a
nullable `reread_fired boolean` now so it's ready *if* a low-confidence re-read is ever added. I'd
include the nullable column (cheap, future-proof) but **not** imply the mechanism exists. Worth a
separate decision on whether to *build* a low-confidence re-read at all — it's a plausible accuracy
lever, but out of scope here.

---

## 2. WHERE / HOW

### Current image lifecycle (confirmed)
- **During grade:** the frontend holds the photos as base64, sends them to `/api/extract` then
  `/api/grade`. `grading.py` builds Anthropic image blocks, calls the model, returns the result, and
  **discards the images.** It does **not** call R2 and does **not** write the DB.
- **Only on save:** the client uploads the images to R2 via `/api/images/submission`
  (`r2_storage.upload_submission_image` → key `submissions/{submission_id}/{type}.jpg`), gets back
  public URLs, and `POST /api/collection` stores those URLs in `collections.photos` (jsonb).

So **retaining unsaved-grade images means persisting images that today never touch R2.** This is a
*new* persistence step, not "stop discarding an existing R2 object."

### Proposed shape (design only)
1. **New table `grade_submissions`** — one row per `/api/grade` call, holding all §1 metadata.
   Mirrors the existing `graded_comics` / `collections` column style (jsonb for `category_scores`,
   `defects`, `photos`). Sketch:

   ```
   grade_submissions(
     id              serial pk,
     user_id         int,
     created_at      timestamptz default now(),
     grading_id      varchar null,
     title           varchar, issue varchar, year int, publisher varchar,
     grade           numeric, grade_label varchar,
     category_scores jsonb,        -- the 8 subgrades
     raw_score       numeric, limiting_factor varchar null,
     confidence      int,
     photos_used     int,
     photo_labels    jsonb,        -- ["front","back","spine","centerfold"]
     photos          jsonb,        -- { "front": "<r2 key/url>", ... }
     defects         jsonb,
     areas_not_visible jsonb null,
     model           varchar, run_count int,
     reread_fired    boolean null, -- N/A today (see §1 flag)
     grade_reasoning text null,
     saved_collection_id int null, -- back-link if later saved
     pinned          boolean default false,   -- retention override (see §3)
     images_purge_after timestamptz null       -- image-purge schedule (see §3)
   )
   ```

2. **R2 path:** `grade_submissions/{id}/{label}.jpg`, reusing `r2_storage.upload_image()` (same
   helper the submission path uses). No new storage primitive needed.

3. **Persistence point:** in `/api/grade`, after a successful grade, upload the in-request images to
   R2 and INSERT the row. **Build consideration:** this adds ~4 small R2 PUTs + 1 INSERT to every
   grade. Do it *after* the response is sent (background thread / fire-and-forget) so it never adds
   latency to the user-visible grade. Reuse the existing `log_api_usage` post-response pattern.

4. **Reuse, don't reinvent:** `category_scores`/`defects` jsonb mirrors `collections`; R2 helper and
   path convention mirror `submissions/`; admin read mirrors the `/api/admin/feedback` pattern (§5).

---

## 3. RETENTION WINDOW / VOLUME

### Current volume (measured, read-only)
- **76 grades all-time** (2026-03-01 → 2026-06-18), **11 distinct grading users.**
- **51 grades in the last 30 days.** 31 saved collections, 28 total users.

### Rough storage math
~4 images/grade. Stored resized JPEGs ≈ **0.3–1.0 MB each** (call it ~0.5 MB → ~2 MB/grade).

| Scenario | Images/mo | New storage/mo | 1 yr retained |
|---|---|---|---|
| Today (~51 grades/mo) | ~200 | ~100 MB | ~1.2 GB |
| 10× beta growth (~510/mo) | ~2,000 | ~1 GB | ~12 GB |

R2 storage is **$0.015/GB-month, no egress fees.** So **"retain everything for a year" costs cents**
(~$0.02–0.20/month). **Storage is not the constraint — privacy is (§4).** The DB rows are trivially
small.

### Options
- **(a) Retain ALL for a fixed window (e.g. 30/90 days), then purge.** Simplest. Cheap at this scale.
- **(b) Retain a SAMPLE.** Saves storage we don't need to save — and risks purging the *one* grade a
  user later complains about. **Not recommended at this volume.**
- **(c) Retain only when triggered** (e.g. on grading feedback, keep that user's recent grades).
  Minimizes data held, but you must capture *before* you know a complaint is coming — so it only
  works as an *extend/pin*, not as the sole mechanism.

### ✅ Recommended: hybrid — **"retain all for 90 days" + "pin on feedback"**
1. Retain **all** grade submissions (metadata + images) for **90 days**, then **purge the images**
   (the heavy, privacy-sensitive part) while optionally keeping the lightweight metadata row longer
   for trend analysis.
2. When a user **files grading feedback**, **pin** (`pinned=true`) their recent submissions so a
   complaint's evidence is never purged before it's diagnosed — exactly the matbanshee gap.

Rationale: at beta volume "retain all" is effectively free and guarantees the disputed grade is
always there; 90 days covers the feedback loop; image-purge bounds both cost and privacy exposure;
pin-on-feedback closes the one hole where a window could drop evidence mid-complaint. Revisit the
window + sampling **only if** volume grows ~100×.

**→ DECISION 1 for Mike:** retention approach + window (recommend all / 90d / pin-on-feedback).

---

## 4. PRIVACY / CONSENT — *surface honestly, not an afterthought*

This is the **bigger** of the two decisions. We would be retaining **user-submitted photographs**
and their **grading activity**, including for **unsaved grades the user likely assumed were
ephemeral.** matbanshee is the archetype: he *"took old photographs… as a test"* and ran them — a
user who would reasonably be surprised we kept them.

Considerations to address before building:
- **Disclosure:** the privacy policy must state that **submitted images and grade results are
  retained** (including grades not saved to a collection) for a defined period, and for what purpose
  (quality, diagnostics, model improvement). Silence here is the real risk, not the storage.
- **ToS:** confirm the terms grant retention + internal use for diagnostics/calibration. If we ever
  use retained images to *train/evaluate* grading, that's a stronger consent ask than mere
  diagnostics — call it out explicitly.
- **Erasure:** account deletion (and any GDPR/CCPA "delete my data" request) must cascade to
  `grade_submissions` rows **and** their R2 objects. Design the purge job to be reusable for
  on-demand erasure.
- **Minimization:** the 90-day image purge (§3) is itself a privacy control — hold the sensitive
  part only as long as it's useful.
- **Access control:** admin-only (§5), never user-to-user, signed/expiring URLs for retained images.
- **Optional opt-out:** consider whether free/beta users can opt out of retention (vs. it being a
  condition of the free grade). Defaults and copy matter.

**→ DECISION 2 for Mike:** privacy/consent posture — privacy-policy + ToS update, erasure cascade,
and whether retention is mandatory or opt-out for beta. **Building retention before the policy says
so is the thing to avoid.**

---

## 5. ACCESS — admin diagnostic view (sketch, don't build)

The thing that was missing for matbanshee: given a user (or a specific grade), **see the photos +
the assigned overall grade + 8 subgrades + confidence + reasoning.**

- **New admin endpoint** `GET /api/admin/grade-submissions?user_id=&since=&grade_id=` (admin-auth),
  reading `grade_submissions` and returning rows + **signed, expiring R2 URLs** for the images.
  Mirrors the existing `/api/admin/feedback` handler.
- **Admin UI:** either a new **"Grade Submissions"** tab in `admin.html`, or — higher-value — a
  **drill-down from the Feedback tab**: a grading-feedback row links to *that user's grade
  submissions within ±a window of the feedback timestamp.* That's precisely the manual join we did
  by hand for matbanshee (feedback at 17:58 → grades at 17:43/17:48/17:51), made one click.
- **Per-submission card:** the 4 photos (front/back/spine/centerfold), overall grade + label, the 8
  subgrades with the limiting factor highlighted, confidence, photos_used, model, timestamp, and the
  identified comic — plus a "was this later saved?" link.

---

## 6. THE PAYOFF — why this is the prerequisite for calibration

Retention is **the gate** for the grading-calibration thread. Without per-grade ground truth (the
photos + the assigned subgrades, ideally paired later with the **professional** grade), we can
**never** distinguish:

- **(b) a systematic conservative bias** — a correctable, roughly-constant offset across many books
  → fixable by recalibrating `CATEGORY_WEIGHTS` / the score→grade snap; **vs.**
- **(a) case-by-case photo-condition issues** — old photos, glare, sleeve/slab artifacts (the
  matbanshee leading hypothesis), which are input problems, not grader-accuracy problems.

With retention you can accumulate `(SW subgrades, photos) → eventual pro grade` pairs and **measure
the offset distribution**: tight + consistently negative ⇒ systematic bias (fix the calibration);
scattered ⇒ photo-condition (fix guidance/UX, add an obstruction penalty). It also makes every
"you undergraded me" report **answerable instead of un-disprovable.** This is what makes the grader
improvable over time — and the honest answer to a knowledgeable user's bug report.

This pairs with the **grade-presentation honesty/confidence** work (showing the user the confidence
and which angles were/weren't visible, so a single-photo grade is labeled as such) — see TODO.

---

## Decisions required (summary)
1. **Retention approach + window** — recommend **retain all / 90 days / pin-on-feedback** (§3).
2. **Privacy/consent posture** — privacy policy + ToS disclosure, erasure cascade, mandatory-vs-
   opt-out for beta (§4). *Settle this before any build.*

*Out of scope (flagged, not specified here): building a low-confidence 180° re-read; using retained
images for model training (stronger consent ask than diagnostics).*
