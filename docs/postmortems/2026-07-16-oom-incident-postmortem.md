# Post-Mortem: OOM Incident — July 16, 2026

## 1. Summary

Shipping the HEIC/orientation fix on `/api/grade` triggered a latent, weeks-old memory bug: raw full-resolution photos (specifically HEIC files that Chrome can't client-side resize) bypass the browser's existing 2048px protection and hit the server at full size, 12-24MP. Combined with a genuine, deliberate memory cost from running 2 workers instead of 1, and a slow per-request memory drift, this produced 5 separate OOM kills across 3 different builds over about 3 hours. Root cause was fully diagnosed with real data (not guesswork) and fixed at three levels: code (decode caps, concurrency gate, allocator tuning), infrastructure (Starter 512MB → Standard 2GB), and process (a new test class using realistic photo sizes, now permanent). Soft launch moved from July 21 to July 28. Total resolution time: roughly 3 hours from first OOM to fully verified fix, including two real-iPhone HEIC grades confirming Gate 0 closed.

## 2. Timeline

*(All times Pacific, as shown in Render's dashboard.)*

- **10:14-10:16 AM** — HEIC/orientation fix deployed (`d2e525d`).
- **10:28 AM** — Instance `96ngc` OOM-killed (over 512MB). Auto-recovered.
- **10:34 AM** — Same instance OOM-killed again. Auto-recovered.
- **~10:40 AM** — Decision made to roll back rather than keep debugging live; real-iPhone test (Heroes for Hope) had also just failed with "Failed to fetch."
- **10:51 AM** — Rollback deployed to `1437fdb` (last known-good build, containing only the earlier item 2(d) health-check work).
- **11:00 AM** — New instance `qtq2g` OOM-killed — on the supposedly-safe rollback build. This contradicted the working theory and forced a re-investigation.
- **~11:05-11:30 AM** — Wrong hypothesis pursued: suspected item 2(d)'s new `/health` DB check, combined with Render's healthCheckPath polling (enabled that same day), as the cause. Mike disabled healthCheckPath as a precaution. DF disproved this with real data: ~90 hours and ~65,000 prior health-check polls with flat DB connection counts and zero failures — the polling wasn't new behavior and wasn't implicated. healthCheckPath re-enabled once cleared.
- **~11:30 AM** — Real root cause identified: full-resolution HEIC photos (iPhone default 24MP) bypass the client-side 2048px resize because Chrome cannot canvas-decode HEIC. Server-side decode (once for orientation, again for barcode scanning) spikes memory by 150-300MB. This path has existed for weeks; today was the first time a real raw-HEIC input ever hit it.
- **11:48 AM** — Process error, not a technical one: a ship-block message contained a bracketed placeholder (`[monitor storm fix files]`) instead of real filenames. Running it staged nothing and committed nothing, but the `deploy` step still fired and deployed whatever was on `main` — which was still `d2e525d`, the original broken build. This silently undid the rollback for about 40 minutes without anyone intending it.
- **~11:50 AM - 12:28 PM** — Real, complete diffs obtained for both fix units and reviewed properly (not just descriptions): Unit 1 (memory: decode-size caps, concurrency gate, `MALLOC_ARENA_MAX`, gunicorn worker recycling, 25/25 test suite including realistic 12MP/24MP fixtures) and Unit 2 (a separate, pre-existing bug: an eBay-alert-email dedup race that had been flooding the inbox all morning).
- **12:31 PM** — Both units + docs deployed together (`eb89454`).
- **12:43 PM** — Instance `bftpt` OOM-killed — on the new, fixed build. Recovered 12:44 PM.
- **12:48 PM** — Heroes for Hope attempt failed again (identification + "Failed to fetch"). Later confirmed to have zero backend trace — it never reached the app; pure edge-routing churn during the restart window.
- **~12:50-1:00 PM** — Root cause fully closed with data: the fix worked exactly as designed (proof: stored photo dimensions came back at exactly 1500×2000, confirming the grading cap was active; the email storm had already stopped, confirming the monitor fix was active). What the fix deliberately left uncapped fired instead: the extract path's 4096px cap intentionally passes 12MP photos through untouched to protect barcode-scan quality, at a real cost of ~150MB per extract. Baseline memory drifts upward with use (392MB → 405MB across successive grades), so by the third comic in a row, drifted baseline + extract cost crossed 512MB. Post-restart, the instance idled at a flat 441MB — one normal 12MP extract from the next kill.
- **~1:00 PM** — Decision: upgrade Render instance, Starter (512MB, $7/mo) → Standard (2GB, $25/mo). This was the only option that didn't cost something already decided to matter (full-res barcode scanning, 2-worker concurrency, HEIC support).
- **1:07 PM** — Upgrade live.
- **1:07-1:15 PM** — Verification: one normal JPEG grade succeeded; two consecutive real-iPhone HEIC grades succeeded end-to-end (Heroes for Hope Starring the X-Men Special #1, Iron Man #200), both correctly identified and graded, valuation confidence honestly labeled "Limited." Memory confirmed at ~447MB of 2048MB (~22%). Gate 0 closed.
- **~1:35 PM** — A memory-ceiling alert email arrived showing "446.7MB / 512.0MB (87.2%)," 25+ minutes after everything above was confirmed passing. Investigated: not a bug. The monitor correctly auto-detects the container's real memory limit via cgroup; this specific alert had actually been sent 8 minutes before the upgrade and was accurate at the time it was sent. An optional env-override and stale alert-text wording were fixed anyway as minor robustness improvements, verified live (`limit_mb: 2048`, `limit_source: cgroup`).
- **Separately, throughout the OOM window**, the eBay account-deletion compliance endpoint sent ~15 alert emails. Root cause: a pre-existing dedup race in the monitor (one worker caches a failure for a 24-hour window while another worker prunes and re-alerts on its own poll cycle, causing an alternating storm). This bug predated today and was exposed/amplified by the deploy churn, not caused by it. Fixed in Unit 2.

## 3. What worked

- Checking Render's own Events log instead of trusting an email's timestamp caught that a suspicious OOM notification was real, and separately caught that another alert (the 87.2% one) was stale-but-accurate rather than a live bug — same verification habit, two different correct conclusions.
- Insisting on realistic-sized test fixtures (12MP/24MP) rather than small ones is what caught two real bugs in the first draft of the memory fix: a resize logic bug that silently failed to engage on certain aspect ratios, and a memory-ordering bug (transposing before downscaling instead of after) that cost an extra ~70MB on HEIC specifically. Neither would have been caught by the original small-fixture test suite.
- File-specific git staging (never `git add -A`) meant the placeholder-command mistake failed safely — it staged and committed nothing, rather than committing a broken mix of files.
- Requiring the actual code diff before shipping, not just a description of it, allowed a real review that confirmed the fix logic rather than taking a summary on faith.
- Pausing live testing once a pattern looked serious (rather than continuing to poke at prod while the fix was investigated) kept the diagnostic signal clean.
- Distinguishing measured fact from working theory throughout, and explicitly disproving an earlier finding with new data when it stopped fitting (e.g., reopening the "rollback fixed it" conclusion the moment a new OOM appeared on the rollback build) — treating an earlier conclusion as provisional rather than defended.

## 4. What didn't work

- A bracketed placeholder in a drafted command block (`[monitor storm fix files]`) got run literally. This was a mistake in how the command was written — a placeholder meant to be filled with real filenames instead of run as-is. It caused an accidental ~40-minute redeploy of the known-broken build. No harm resulted only because no OOM happened to occur in that specific window; it was still a real, unnecessary risk.
- The first hypothesis on the second OOM (item 2(d)/healthCheckPath) was wrong, based on reasonable but incomplete reasoning. It cost some time and one unnecessary precautionary setting change (disabling healthCheckPath) before being cleared with real data. The theory was reasonable to raise but shouldn't have been treated as more than a hypothesis until checked.
- The original memory fix shipped and passed 17/17 offline, then still caused a new OOM on the very next deploy. The fix wasn't wrong in what it capped — it was incomplete, because the extract path's cap was deliberately wide (for barcode quality) and nobody had modeled what happens when that deliberate gap combines with memory drift under three-books-in-a-row real usage. The test suite that would have caught this (realistic multi-request drift under the actual instance ceiling) didn't exist until after this exact incident.
- The whole incident took about 3 hours and 5 OOM kills to fully resolve, partly because each fix addressed the most recent symptom correctly without yet having the full multi-factor picture (input class + 2-worker baseline + drift + deliberate barcode-quality tradeoff all had to be identified before the real fix was obvious).

## 5. Root cause

Four factors, only dangerous in combination:

1. A months-old, until-today-silent gap: full-resolution HEIC photos bypass the browser's client-side resize because Chrome cannot canvas-decode HEIC to shrink it before upload. This has existed since server-side photo decoding was added; nothing had ever exercised it in production until today's first real-device test.
2. A deliberate, correct tradeoff made weeks ago: moving from 1 worker to 2 workers (to support concurrent grading, needed for the booth) roughly doubled baseline memory, since each worker is a fully separate process with its own copy of the app loaded.
3. A real allocator quirk: memory doesn't fully return to baseline between requests under heavy multi-threaded use, so the resting baseline crept upward with use rather than resetting.
4. A deliberate, correct design choice that had a real cost: the extract path's decode cap was set high (4096px) specifically to preserve barcode-scan accuracy, at the cost of ~150MB per full-res extract.

None of these alone would likely have caused today's incident. Stacked together, on a 512MB instance, they did — five times, across three different builds, because each build still had at least the "full-res HEIC + 2 workers + drift" combination present even after early fixes addressed only part of it.

## 6. Action items

**Shipped already:**
- Per-photo decode-size caps on both grading (2000px) and extract (4096px, barcode-preserving) paths.
- Concurrency gate limiting simultaneous image decodes per worker.
- `MALLOC_ARENA_MAX=2` and gunicorn worker recycling (`--max-requests`) to bound drift.
- eBay alert-storm dedup race fixed (5-min backoff, 15-min prune-after-absence, emails off the request thread).
- Instance upgraded Starter → Standard (2GB), removing the ceiling as a fragile edge entirely.
- Optional env-override for the memory-monitor's ceiling detection, plus removal of stale hardcoded tier-name text in alert messages.
- New permanent test class (`tests/test_memory_fix.py`) measuring real peak memory with realistic 12MP/24MP fixtures, including a subprocess-isolated raw-HEIC test that documents the known physical floor (~200MB transient, unavoidable by any code fix) as an explicit regression guard.

**Queued, not urgent:**
- Share a single image decode between orientation-normalization and barcode-scanning (currently decodes twice on the extract path) — pure efficiency gain, no quality tradeoff.
- Extend the client-side 2048px browser resize to the identification/extraction flow (currently only grading has it) — defense in depth, doesn't help the HEIC-on-Chrome case specifically but reduces exposure for everything else.
- Signature ID path: currently hardcodes `image/jpeg` without inspecting bytes, so a raw HEIC upload there would fail (different failure mode than the OOM — an honest rejection, not a crash, and the path is currently UI-gated/unreachable). Queued for whenever Signatures v2 resumes. Also noted: any future signature-accuracy work should use client-side cropping, not raised server caps, since the model downscales everything to ~1568px regardless of what's sent.

**Process/lesson changes:**
- L-SW-2026-012 (logged): any change adding image decoding to a hot request path needs a peak-memory budget check using realistic full-size inputs on the actual instance's memory limit, before shipping — not just correctness tests on small fixtures.
- L-SW-2026-013 (drafted, pending): alerting/monitoring systems with multiple independent workers sharing dedup state need a stability window (a minimum time before re-alerting), not just immediate re-alert-on-next-failure — the eBay email storm is a specific case of a generalizable pattern.
- New standing rule (this session): after any major incident like this one, run this exact post-mortem process rather than just moving on once the immediate fire is out.
- Command-block hygiene: no bracketed placeholders in ship-block commands going forward — real filenames only, confirmed before the block is written, not filled in by whoever runs it.
