# Where We Left Off - Jul 9, 2026

## Session 114 (Jul 9, 2026) — Item 2 Phase 1 (shared DB pool) SHIPPED + VERIFIED; pooling/gunicorn plan delivered; 2(f) resource-alert designed; NEW valuation finding: Cover-A variant misclassification (modern mispricing, systemic)

**⚠️ CURRENT STATE (2026-07-10 PM; Rule 5, read this FIRST): MOST RECENT CHANGE = eBay Issue 1 (compliance timeout) INVESTIGATED + CLOSED by Mike's portal check — BOTH eBay endpoint halves are now DONE; NEXT item 2 is fully closed and the eBay endpoint carries zero launch-blocking work.** Issue-1 findings (detail in LAUNCH_READINESS Dependency watch): suspension = 1000 CONSECUTIVE failures (no 200 within 3000ms), counter self-heals on any success → warm ~0.45s endpoint can't plausibly trip it; registered URL + verification token confirmed matching prod/Render; Data-Handling bulletin N/A (CN/RU/etc.-scoped); eBay's field reference independently confirms `username` as the deletion-notice identity field (validates the Issue-2 fix); keep-warm/monitor-timeout = optional nice-to-have now. OPEN MICRO-ITEM (Mike, 2-min): enable the portal "Notify Me" failure-alert email; nice-to-have: one-time confirm the dev account is US-registered. *Earlier same day:* eBay Issue-2 security fix SHIPPED (`060f1dc`, Mike ran commit/deploy) + VERIFIED IN PROD, all three checks passed. Evidence: (1) unsigned curl POST → 412 `{"error":"Signature required"}`; (2) eBay portal "Send Test Notification" ×multiple → every one verified successfully, INCLUDING across a mid-sequence eBay key rotation (`kid=3cf880e7…`→`9936261a…` — the unknown-kid→fresh `getPublicKey` fetch path proven live, not just the cache), each proceeding to identity lookup and correctly matching no user on eBay's synthetic test IDs; (3) GET challenge-response still 200/valid hash. The raw-body byte assumption is proven against genuinely eBay-signed messages, not just self-signed test keys. ⚰️ TOMBSTONE: this checkpoint's prior framing — "fix DRAFTED + OFFLINE-VERIFIED, UNCOMMITTED, awaiting Mike's review" — is DEAD; do NOT re-present the eBay-fix command block, the commit exists at HEAD (`060f1dc`). LAUNCH_READINESS updated same day (Rule-5 header + sequence-item-3 eBay bullet ✅ + Dependency-watch Issue-2 line). REMAINING (re-revised 2026-07-10 PM ×2 — normalizer fix COMMITTED `15cb459` + docs/lessons `2904fa7` [L-SW-2026-008/009/010 finally in history], DEPLOYED [new code confirmed in container: `_fuzzy_tokens_supported` grep=2, "Cover A"→is_variant=False], dry-run VERIFIED [computed variant 15,344 vs stored 18,044 = 2,700 flipping ≈ the audit's ~2,601 + rows captured since]; ⚰️ command blocks #2/#3 below are EXECUTED, do not re-run the commits): (1) ✅ **live re-normalize COMPLETE + VERIFIED (2026-07-10 late PM): 71,449/71,449 updated, 0 errors; stored `is_variant` = exactly 15,344; Defenders→Descender mis-merge = 0 rows; "Absolute Batman Annual" separated into its own canonical; end-to-end live-app check: AB#1 9.0 → raw FMV $169.99 (blended, real comps, verdict_reliable=true) vs pre-fix $150.00. Gap to ~$185–300 market = Layer 3, deferred to R1/R2 by prior decision. NOTE for future queries: `canonical_title` is stored TITLE-CASE ('Absolute Batman', not 'absolute batman');** (2) market_sales equivalent pass (8,604 canonical rows, small extension — LAUNCH_READINESS item 6); (3) micro-items: eBay portal "Notify Me" email (2-min); prior docs note = `docs/LAUNCH_READINESS.md` + this file + `docs/LESSONS.md` (⚠️ L-SW-2026-008/009/010 STILL never committed — folded into command block #3 below) + optionally the untracked `docs/technical/VALUATION_FMV_FIXES_SPEC.md` (S111 spec, referenced by session notes but never added — include or defer, Mike's call). Git truth at write (verified): HEAD = `060f1dc`; dirty = `title_normalizer.py`, `docs/LESSONS.md`, this file, `docs/LAUNCH_READINESS.md`.**

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

### STILL OPEN (next sessions)
- **Stacking step 2** (account.html "Change Plan" → `openPortal()` + 409 auto-redirect; verify Stripe portal plan-switching enabled) and **step 3** (`handle_subscription_deleted` sub-id match + immediate-cancel→free test) — hardening on the now-closed blocker (detail in the stacking entry below).
- **Section F checklist** (mobile + load) — draft AFTER stacking 2 & 3; **mobile half is higher-priority** (GalaxyCon booth is phone-first; start real-device testing well before Aug 21, not last-minute).
- **Cert-number recovery lookup** (small build) — the marketable slabbed-recovery headline.
- Lower-priority backlog: ~30s comic-ID progress messaging; email setup (mike@/support@); `lookup_demand` thin-data pull (after weeks of real traffic); variant reclamation (Tier 1); capture-cadence scheduled pull; ⏰ 90-day purge (~Sept 17).

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
1. **⏰ 90-day PURGE — HARD DEADLINE ~2026-09-17** (day-90 from persist deploy). After soft launch (Jul 21) + GalaxyCon (Aug 21-23) — not urgent, but a published-policy obligation; **cannot slip past the date**. Columns/index (`images_purge_after`,`pinned`) + `delete_grade_submission` helper already in place → scheduled job + feedback-pin away.
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
