# Section F Checklist — Mobile + Load (LAUNCH-CRITICAL, booth-gating)

> **Status:** DRAFTED 2026-07-12 (DF). Not yet run. This file is the working checklist for
> LAUNCH_READINESS sequence item 4 / A–F table row F. **Record results IN THIS FILE** (date +
> device + pass/fail + notes on each line) — status rolls up to `docs/LAUNCH_READINESS.md`.
> Mobile is the priority half (per standing decision, [[project_section_f_mobile_priority]]);
> load runs second, now unblocked by item 2's concurrency cluster (2×8 gthread + pool, verified
> 2026-07-11). **This file is CANONICAL (Mike, 2026-07-12)** — Mike keeps a supplementary
> personal run-sheet for the live phone pass; no merge needed, but results still land HERE.

**Booth reality check:** GalaxyCon (Aug 21–23) is phone-first — a stranger's phone, con-hall
lighting, con wifi/cell congestion, and Mike away from a desk. Every mobile test below should be
run at least once in "booth conditions" (cell data, not home wifi).

---

## 🚧 GATE 0 — HEIC/HEIF (iPhone default format) — **BLOCKED until fixed or consciously waived**

**Finding (2026-07-12, read-only code trace):** the pipeline **cannot decode HEIC anywhere**;
iPhone-default photos survive only when Apple's OS silently converts them to JPEG before we see
them. Evidence:

- Frontend sends **raw file bytes** — `FileReader.readAsDataURL`, no canvas re-encode
  (`app.html:1658–1711`); the multi-photo input explicitly accepts `.heic` (`app.html:1044`);
  the data-URL media type (`image/heic`) is forwarded as-is.
- Server decode = Pillow only — **no `pillow-heif`/`pyheif` in `requirements.txt`**, so
  `normalize_orientation_b64` (`comic_extraction.py:86`) raises on HEIC → `/api/extract`
  returns `"Image could not be processed"` → **the front-photo step fails and the flow dead-ends
  at step 1** (generate button never enables). The error doesn't say "HEIC" — to the user it
  reads as "the app is broken."
- Even bypassing extraction, `/api/grade` passes the client `media_type` straight to the
  Anthropic API (`routes/grading.py:446`), which accepts **JPEG/PNG/GIF/WebP only** →
  `image/heic` = API 400 → generic 500 to the user.
- The two byte-touching gates don't save it: photo-quality gate **fails open** on decode error
  (`routes/fingerprint_utils.py:185`); moderation is AWS **Rekognition (JPEG/PNG only)**.

**Why it sometimes works anyway (and why that's not enough):** the 4 grading inputs use
`accept="image/*" capture="environment"` — iOS **camera capture delivers JPEG**; iOS photo-library
picks are *usually* OS-transcoded to JPEG. But **Files-app picks deliver raw HEIC**, library-pick
behavior varies by iOS version and the `accept` attribute (the multi-photo input names `.heic`,
which invites the raw file), and Android/HEIF exists too. The failure mode is silent and
device-dependent — exactly what a booth can't absorb.

**Adjacent finding (same trace):** `/api/grade` runs **no orientation normalization at all** —
the EXIF/portrait normalizer was wired into `/api/messages` (`routes/grading.py:251–266`) and
`/api/extract`, but the structured grading endpoint sends raw client bytes. A sideways spine/back
photo goes to the model sideways.

**✅ DECIDED 2026-07-12 (Mike): FIX, not waive — framed as an orientation-normalization fix with
HEIC as a side effect. BUILT IN TREE same day (offline 17/17), awaiting ship.** The unit:
`pillow-heif>=0.16.0` in requirements + opener registered beside the PIL import
(`comic_extraction.py`, `HEIF_SUPPORTED` flag) + `/api/grade` now normalizes EVERY photo through
`normalize_for_photo_type` BEFORE the quality gate/moderation/API/retention (label→photo_type:
Front Cover/Spine/Back→portrait, Centerfold→landscape-allowed; always emits upright JPEG).
Undecodable photo → fail-LOUD 400 in the quality-gate error shape naming the photo (frontend
already renders it; no frontend change needed). Bonus: Rekognition moderation + the quality gate
now actually operate on HEIC uploads, and retention persists upright JPEG. Runtime flag `heif` on
`/api/admin/dependency-status`; documented in `ARCHITECTURE.txt`; monitor check n/a (pure
package, no service endpoint).

- [x] HEIC fix decided: **FIX** (2026-07-12) — built in tree, offline 17/17 (unit decode + route
      end-to-end: 3×HEIC grade, portrait/landscape per type, gate/retention see JPEG, garbage →
      400 naming the photo)
- [ ] Fix SHIPPED + post-deploy check: admin dependency-status `runtime.heif = true` + one normal
      JPEG grade (no regression)
- [ ] Real-device proof: iPhone shot-in-HEIC → library pick → full grade succeeds
- [ ] Real-device proof: iPhone → Files-app pick of a raw `.heic` → full grade succeeds (raw HEIC
      now decodes server-side; anything else fails loud naming the photo, never a dead-end)

---

## Part 1 — MOBILE (priority half)

### Device matrix (real devices only — DevTools emulation proves nothing about camera/HEIC/PWA)
| # | Device | Browser | Who has it |
|---|--------|---------|------------|
| M1 | iPhone (recent iOS) | Safari | ☐ source device |
| M2 | Same iPhone | Chrome-on-iOS (WebKit) | ☐ |
| M3 | Android (Pixel-class) | Chrome | ☐ source device |
| M4 | Android (Samsung, if available) | Samsung Internet | ☐ optional |

Minimum bar = M1 + M3. Record iOS/Android + browser versions with each result.

### F-M1. Core loop: grade → value → verdict → save (per device, camera path)
- [ ] Signup/login on the device (beta code entry usable on a phone keyboard)
- [ ] 4-photo grading flow using **live camera capture** (front/spine/back/centerfold)
- [ ] Same flow using **photo-library picks** (pre-shot photos — the HEIC path on iPhone)
- [ ] Extraction correct (title/issue), grade renders, FMV + slab/no-slab verdict renders
- [ ] Save to collection; comic appears in collection view
- [ ] Repeat once in booth conditions (cell data, hall-type lighting)

### F-M2. Collection management on mobile
- [ ] Load/scroll a 20+ item collection; sort/filter/search usable with thumbs
- [ ] ⚠️ **DELETE mis-tap check** — C's open must-fix (no confirm/undo) is WORST here; verify
      severity on a real phone, feed the fix (sequence item 5)
- [ ] Edit MY VAL; eBay/Whatnot listing generation renders usably

### F-M3. Billing on mobile
- [ ] Pricing page → checkout (Stripe) on the phone — **throwaway account ONLY, never a `test-*`
      or the Free test account** ([[reference_slabworthy_test_accounts]])
- [ ] Customer portal (manage/cancel) usable on mobile
- [ ] Tier gate messaging (cap reached) renders on small viewport

### F-M4. PWA / install surface
- [ ] "Add to Home Screen" on iOS Safari — icon, name, launch (favicon/manifest correct)
- [ ] Install prompt on Android Chrome; launched-app flow works (camera permissions inside PWA!)
- [ ] Android TWA (parked asset, `android-twa/`) — explicitly OUT of F scope; note only

### F-M5. Layout/UX sweep (per device, screenshot anything broken)
- [ ] Landing, app, pricing, account, verify pages — no horizontal scroll, tap targets sane
- [ ] Photo upload boxes + thumbnails; progress states during the 10–30s grade wait
- [ ] Result card (grade circle, subgrades, FMV, verdict) fits the viewport
- Note: `app.html` = 3,261 lines with ~1,669 lines inline JS across 10 blocks **plus** `js/`
  modules — every mobile fix must be hunted in two places; budget extra time.

---

## Part 2 — LOAD (second half; run AFTER mobile sweep or in parallel late)

**Context:** the old booth-killer (1 sync worker) is dead — 2 workers × 8 gthread threads +
shared DB pool verified 2026-07-11 (12× `/health` instant during a live grade; 358MB/512MB
steady; 0 pool exhaustion). F-load now measures REAL capacity instead of rediscovering that
defect. Ceilings to respect: Starter **512MB** RAM (WARN 85% sustained via 2(f) self-alert),
pool 8/worker ×2 + overflow, max_connections=103.

**Booth-shaped load target (✅ APPROVED by Mike 2026-07-12):** 10 concurrent active users,
of which 3 grading simultaneously (each grade = 1 Sonnet call, 10–30s) + 7 browsing
(collection/valuation/health), sustained 10 minutes. **Plus one ceiling burst above the floor
(Mike's addition): 16–18 concurrent** — deliberately at/over the 16 request slots (2 workers ×
8 gthread threads), to find where the service actually degrades, not just confirm the floor.
See F-L4.

### F-L1. Concurrent-grade test
- [ ] 3 simultaneous real grades from 3 accounts/devices — all complete, none error/time out
- [ ] `/health` stays <1s throughout (the item-2 probe, now at booth scale)
- [ ] Non-grading routes (login, collection load, valuation lookup) stay responsive (<2s)

### F-L2. Sustained-mix test (scripted, read-heavy)
- [ ] 10-min mix at target above; record p50/p95 per route class
- [ ] Memory watch: stays under WARN 85% (435MB) sustained; note peak (admin resource chip /
      `/api/admin/dependency-status`)
- [ ] Logs: **0 `POOL EXHAUSTED`**, 0 `[DB]` teardown lines, 0 5xx
- [ ] pg_stat_activity comfortably under ceiling

### F-L3. Spike/recovery
- [ ] Cold-start behavior: first request after idle (Render spin state) — measure, note UX
- [ ] Burst 20 rapid `/health` + 5 valuations mid-grade — no queueing regression
- [ ] After load stops: memory returns to ~steady (no ratchet), pool parked-set sane

### F-L4. Ceiling burst — 16–18 concurrent (find the ceiling, not the floor)
2 workers × 8 gthread threads = **16 request slots**; 16–18 concurrent deliberately saturates
them so excess requests queue. The goal is to CHARACTERIZE degradation, not to pass:
- [ ] 16 concurrent mixed (4 grading + 12 browsing), 3 min — record p95 per route class and
      queue-wait signature (does `/health` latency step up when slots fill?)
- [ ] Push to 18 — note the failure MODE: graceful queueing (latency grows, everything completes)
      vs errors/timeouts/worker kills. Graceful = acceptable ceiling; errors = record the number
      as the hard cap
- [ ] Memory at saturation vs the 85% WARN line (435MB) — does the ceiling bind on slots or RAM?
- [ ] Logs after: `POOL EXHAUSTED` count (expected 0 — pool 8/worker matches thread count),
      teardown lines, any 5xx
- [ ] **Record the observed ceiling + failure mode here** — this number decides whether Starter
      survives GalaxyCon foot traffic or the tier upgrade conversation happens BEFORE the con

**Fallback lever if load fails on memory:** documented 1×12 gthread CMD revert (LAUNCH_READINESS
item 2(a)); tier upgrade (Starter→Standard 2GB) = Mike's manual dashboard call, never automatic.

---

## Exit criteria (F flips 🔴→✅ in LAUNCH_READINESS when ALL true)
1. Gate 0 (HEIC) closed — fixed+verified or explicitly waived with real-device evidence.
2. F-M1 core loop passes on M1 (iPhone/Safari) AND M3 (Android/Chrome), camera + library paths.
3. F-M3 billing checkout + portal verified on at least one real phone.
4. F-L1 + F-L2 pass at the booth-shaped target with clean logs and memory under WARN.
5. Every failure found is either fixed+re-run or logged in LAUNCH_READINESS with a severity call.
