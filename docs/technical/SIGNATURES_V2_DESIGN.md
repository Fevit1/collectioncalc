# Signatures v2 — Design Record (deferred)

> **Status:** DESIGN ONLY — nothing here is built. Captured 2026-06-16 (Session ~105) so the
> deferred signature design isn't lost. The v2 matching pipeline exists and works
> (`routes/signature_orchestrator.py`, `/api/signatures/v2/match`), but the user-facing control is
> grayed-out / "coming soon" and the post-grade **auto-fire was removed** this session (it was the
> re-grade-hang contention source + a hidden-feature Opus cost + the false-positive source).
> This doc is the plan for shipping signatures *properly*, later, as a deliberate feature.
>
> **What shipped this session (for context):** the fire-and-forget `runSignatureCheck` call after
> every grade was disconnected in `app.html` (the function, the `gradeReportSignature`/`signatureInfo`
> panel, the orchestrator, the entitlement gate, and `routes/signatures.py` are all preserved). See
> `IDENTIFICATION_FIX_PLAN_OF_RECORD.md` for the related identification honesty work.

## Intent

Signature identification is a **major differentiator** — users have said they would pay for it on its
own. It is NOT being removed. It is being held back until it can ship as a **deliberate,
user-initiated, properly-gated** feature rather than a hidden automatic side-effect of grading.

## Delivery path (decoupled from grade/upload)

Signature verification should **not** be an automatic side-effect of the grade/upload flow. The
contention hang, the surprise per-grade Opus cost, and the false positives all trace back to the
auto-fire. The intended path:

- A **deliberate user action**, most likely on a **saved** book — e.g. "save to collection for
  grading refinement, including signature identification" — with its own considered context, not
  bolted onto every grade.
- Re-enable by calling `runSignatureCheck(window.gradingState.photos[1])` from a real
  "Check for signatures" control (the function and results panel already exist in `app.html`).

## Detection gate (correctness — the false-positive fix)

The v2 orchestrator currently has **no "is a signature visually present?" step**. It pre-filters
candidate creators by era/publisher metadata (`prefilter_candidates` — this never looks at the
uploaded cover; "0 candidates → top 15" is a *reference-pool* coverage fallback, **not** signature
detection), fetches reference images, then runs 3 Opus passes that ask "which of these creators
matches?" — and always returns a best guess. On an unsigned cover, primed with publisher/era/title
context, it produces a plausible named artist (the **Alex-Ross-on-an-unsigned-Absolute-Batman-#19**
false positive, ~0.42 confidence).

**Fix:** add a **detection gate before attribution** — mirror the pattern that already exists in
`routes/signatures.py` (Step 1: "how many signatures are present?" → abstain / "No signatures
detected on this cover" when the count is 0, see its early-return). Only run the expensive attribution
passes if a signature is actually detected.

- **Correctness:** abstains honestly instead of naming an artist from context.
- **Cost bonus:** abstaining on unsigned covers **skips the 3-pass Opus job entirely** — a direct
  unit-economics win on the app's most expensive call.

> Note: "abstain on zero pre-filter candidates" is the **wrong** lever — that would suppress
> legitimate matches for thinly-covered eras/publishers (a reference-DB coverage gap) while doing
> nothing about unsigned covers. The gate must be a *visual signature-present* check, not a
> metadata-match count.

## Confidence-verify UX (honest confidence)

Instead of asserting "**Signature Detected: David Finch**", present uncertainty and let the human
adjudicate — e.g. "**We're 55% confident this is a David Finch autograph — can you confirm?**" Same
honest-confidence principle as the valuation confidence labeling and the identification gate. The
person physically holding the book is the ideal verifier. Pairs with the detection gate (only ask to
verify when a signature is actually present).

## Tier-gated visibility

Don't **show** the signature control to users who can't use it. Today Free/Pro get a server-side
`403` (entitlement: `signature_id_per_month = 0`), but the control shouldn't be visible-then-rejected.
Gate **visibility** to entitled tiers (Guard/Dealer; admin unlimited) — `get_signature_id_entitlement`
in `routes/billing.py` already provides the entitlement signal to drive this.

## Threshold alignment (honesty pass)

The frontend show-threshold (`confidence < 0.40` hides, `app.html` ~`runSignatureCheck`) sits **below**
the server's honest match floor (`LOW_CONFIDENCE_THRESHOLD = 0.50` in `signature_orchestrator.py`). So
the **0.40–0.50 "tentative named artist" band** can render as a confident "Signature Detected." Align
them: hide unless `confidence >= 0.50`, or have the server send an explicit `is_confident_match` flag
and gate the UI on that. Cheap; part of the v2 honesty pass.

## Later problem (noted, not designed)

Handling **multiple signatures on one cover** (multi-sig books). Not designed yet — flagged so it
isn't forgotten when v2 ships.

## Cost note (unit economics)

The v2 job is the **most expensive call in the app**: Opus × 3 sequential passes (already serialized
due to a rate-limit constraint — see the `MAX_WORKERS removed` note in `signature_orchestrator.py`).
Both **user-initiated invocation** and **detection-gate abstain-on-unsigned** reduce how often it
runs — relevant input to the pricing-tier review and overall unit economics.

## Build checklist (when authorized — not now)

1. Re-wire `runSignatureCheck` to a user-initiated "Check for signatures" control (likely on a saved
   book), removing the disconnected auto-fire reference.
2. Add the visual detection gate before attribution (mirror `routes/signatures.py` Step 1); abstain +
   skip Opus when zero signatures detected.
3. Tier-gate the control's visibility to entitled tiers.
4. Align the frontend show-threshold to the server floor (or gate on `is_confident_match`).
5. Convert the result UX to confidence-verify framing ("We're N% confident — can you confirm?").
6. (Later) design multi-signature handling.
7. Fix the image-fetch path: move R2 image retrieval **server-side** in
   `/api/signatures/v2/match` (accept `comic_id`/URL; fetch via the R2 SDK or
   `slab_guard_cv._download_image`) — see "Image-fetch (CORS)" below.

## Image-fetch (CORS) — browser base64 fetch of R2 image fails

> Captured 2026-06-18 (Session ~106) from testing after the `fetchImageAsBase64`
> `response.ok` fix (Commit B) landed — the honest errors it now reports exposed
> this underlying bug. **Not a launch blocker** (ID Sigs is coming-soon /
> unreachable from upload); queued for v2.

**Symptom (reproduced, two accounts):** In My Collection, clicking ID Sigs fails
at the image fetch — admin saw `Couldn't load image (HTTP 503)` on "Amethyst
Princess of Gemworld #1"; test-guard saw `Couldn't load image (network error)` on
"The Micronauts #11" — **even though the cover `<img>` thumbnail loads fine** on
the same comic.

**Not a URL mismatch:** the thumbnail and the base64 fetch use the **same**
`photoUrl` (`comic.photos.front || .spine || .back`, `js/collection.js`
~297/331/407 vs ~1003/1032). Ruled out.

**Root cause — cross-origin CORS.** The page (`slabworthy.com` / `www`) and the
image host (`img.slabworthy.com`, or a `pub-*.r2.dev` fallback per
`r2_storage.py:32`) are **different origins**. `<img src>` display is CORS-exempt
(always loads); `fetchImageAsBase64` does `fetch()`→`.blob()`, which **is**
CORS-enforced. When the host doesn't return `Access-Control-Allow-Origin` for the
page origin, the browser blocks the fetch.

**Two errors, one root (cache/CORS state):**
- *network error* = response carried **no ACAO** (or a preflight failed) → browser
  blocks → `fetch` rejects.
- *HTTP 503* = CORS passed, but the **R2 origin was throttled**. The `<img>` rode
  the Cloudflare edge cache (HIT); the CORS-mode `fetch` (different headers /
  preflight / cache MISS) hit origin and 503'd.
- Both fail in the **browser, before** the request reaches the backend — so it is
  NOT the tier/entitlement gate (that runs server-side after upload).

**Fix direction:**
- **Preferred (strategic):** fetch the image **server-side** — `/api/signatures/v2/match`
  takes `comic_id`/URL and pulls the cover from R2 directly (R2 SDK by key, or the
  existing `slab_guard_cv._download_image`). Eliminates browser CORS *and* the
  multi-MB base64 upload. Best fit for v2.
- **Tactical (only if keeping the client path):** fix R2/Cloudflare CORS on
  `img.slabworthy.com` to return ACAO for the real page origin(s) — **apex AND
  `www`** — on GET + OPTIONS, and make the fetch path cache-eligible so it stops
  hitting origin → 503. When implementing, verify (a) page origin apex vs `www`
  and (b) the actual stored host (`img.slabworthy.com` vs leftover `pub-*.r2.dev`);
  a www/apex mismatch alone reproduces this.
