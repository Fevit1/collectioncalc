# Overnight report, 2026-09-18 → 09-19 — report only

No matcher call, no commit, push, deploy, purge or database write. Read-only DB (RO role) and repo reads. $0.

## 0. Unanswered on my side — first thing

- **Decision 3 arrived as a placeholder:** "Accounts 25 and 26: [mine / not mine]". Still open. It decides whether
  the 06-23 → 09-18 outage gets a harm post-mortem or a detection one.
- **"The homepage and sitemap unit from my earlier message": that message is not in this conversation** and nothing in
  `WHERE_WE_LEFT_OFF.md`, `ROADMAP.txt` or `TODO.md` describes it. Section 4 is the state of the ground, not the
  unit's shape. Paste the brief and I will shape it.
- **Found while pulling The Terminator 1:** the tracked `docs/EBAY_CAPTURE_WEEKLY.docx` is still the **2026-08-17**
  list. The 2026-09-17 list is `EBAY_CAPTURE_WEEKLY_2026-09-17.docx`, **untracked at the repo root**. `aa84391` did
  change the tracked file (40,652 → 33,147 bytes) but its first line still reads "2026-08-17", so the record "the
  2026-09-17 docx replaces the August one (committed with the records, `aa84391`)" is not what git holds. I edited
  the root 09-17 file (Terminator 1 out; intro "Fifteen" → "Fourteen … pulled 09-18"; X-Men 1 (1963)'s "the most
  looked-up book since launch" → "One user has looked it up; kept for the 1963/1991 split"). Which path is the
  list's home is Mike's call; until then the corrected list is not in git.

## 1. Logging-level unit

**File list: `wsgi.py`.** Backend → `deploy`. No purge, no DB write.

**Cause, confirmed:** nothing in the repo calls `logging.basicConfig`, `setLevel` or passes gunicorn a log config, so
the root logger sits at WARNING with Python's last-resort handler. `logger.error` reaches Render; `logger.info` is
dropped. The app otherwise logs with `print()`, which is why this went unseen: **only
`routes/signature_orchestrator.py` uses `logger.info` — 8 lines**, including `[SigID] match served` (the stated usage
signal for unlimited plans), the pre-filter's candidate count and each pass's top result.

**The change** — after the stdlib imports at the top of `wsgi.py` (it must run before the blueprints import, and
gunicorn imports `wsgi:app` in every worker, so once here covers both):

```python
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
```

**What else starts printing at INFO (checked, so the deploy holds no surprise):** no other first-party `logger.info`
exists. Third-party: `httpx` logs one `HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"`
line per Anthropic call (URL and status only — no key, no body), and `botocore` logs "Found credentials in
environment variables." once per client (the fact, not the values). If the httpx line is unwanted on the grading
path, two more lines quiet it: `logging.getLogger('httpx').setLevel(logging.WARNING)` and the same for `botocore`.
I would leave httpx ON for a week — it is a free per-call record of model traffic, which is what was missing
tonight.

**Post-deploy assert:** one ID Sigs click on ASM #252 (the click already planned after the pool fix — do not spend a
separate one) → Render shows `INFO routes.signature_orchestrator: Pre-filter selected N candidates` and
`[SigID] match served: user=… matched=…`. Before the pool fix, a free assert: any grade request shows the httpx line.

## 2. Candidate pool proposal

### What the pool does today
`prefilter_candidates` keeps creators whose career overlaps the book's era window and whose publisher list has the
book's publisher, then `ORDER BY reference_image_count DESC LIMIT 15`. 94 of 97 eligible creators have exactly four
images, so the order is an arbitrary tie. `signature_location` is accepted and never used. Creators passing the
filter, against a cap of 15:

| era | MARVEL | DC | IMAGE | no publisher |
|---|---|---|---|---|
| pre-1970 | 11 | 10 | 0 | 14 |
| 1970s | 21 | 20 | 2 | 25 |
| 1980s | **43** | 37 | 12 | 47 |
| 1990s | 63 | 54 | 21 | 69 |
| 2000s | 70 | 62 | 32 | 83 |
| 2010s+ | 75 | 67 | 35 | 90 |

ASM #252 is 1980s / MARVEL: 43 pass, 15 are compared, 28 are dropped by tie order. **Stan Lee (id 21, writer,
1939–2018, MARVEL, 4 images) passes the filter and lost the tie.** Nothing about him is misfiled.

### Measured, free: how often the true signer reaches the pool
Population: the 852 signed CGC/CBCS eBay rows with an R2 image, a `title_year`, and exactly one in-set creator named
in the title (the external test's own population). Labels are a proxy — a named creator is not always the signer.

| ordering of the creators that pass the era filter | signer in the 15 |
|---|---|
| **today** (arbitrary 15 of those passing; expected value, publisher ignored) | **34.2%** |
| by how often the creator signs books in our own corpus (leave-one-out) | **85.1%** |
| by who signs THIS title in the corpus, then the global count (leave-one-out) | **93.0%** |
| signer fails the era filter outright | 1.5% |

**Today's pool caps accuracy near one in three before any image is compared.** An 87% bar cannot be met by any
matcher behind a 34% pool; this is the first-order answer to part 4 of the measurement unit.

### Proposed selection signal — Design A (SQL only, no extra model call)
Order the creators that pass the filter by, in turn:
1. **Title prior** — creators named on signed slabs of this `canonical_title` in `ebay_sales` / `market_sales`.
2. **Global signing prior** — how often the creator is the named signer across the corpus (Scott Snyder 399, Todd
   McFarlane 379, Stan Lee 240 …). This is a base rate: who actually signs books.
3. **Publisher exactness** — an explicit affiliation above a NULL (NULL currently matches everything).
4. **Era closeness** — career midpoint distance to the book's year, as a tie-break.
5. `creator_signatures.id` — a deterministic final tie-break, so the same book always gets the same pool.
Image count is gone as a signal; it stays only as the eligibility floor (≥ 2). `signature_location` still has
nothing to filter on (no creator-level column describes where someone signs) — drop the parameter or leave it
documented as unused; do not pretend it narrows.
Where the prior lives: a small table or a `signing_prior` column refreshed by a script (a DB write, Mike's DBeaver),
or a JSON in the repo read at import. The title prior is a live indexed query at request time, or the same JSON.
⚠️ The prior is built from eBay signed slabs, which is the population test (3) samples — so (3) will flatter it. It
is a rich-get-richer ordering: a rarely-signing creator is found only if stage 2 below adds them.

### Design B — two-stage, additive (Mike's idea, reshaped)
Rows 16 and 17 both said "resembles Stan Lee, not in the candidate pool". Re-running after a full 3-pass miss costs a
second identification. Cheaper shape: **ask first.** Stage 1 is one call with the target image and the 97 eligible
NAMES as text — no reference images: "which of these could this be; read any legible letters" → up to 5 names, as a
structured field. Stage 2 is today's 3-pass comparison on a pool = stage-1 names + Design A's order, filled to the
cap. **Stage 1 only ever ADDS candidates**, so it cannot push recall below Design A. (That is the difference from
the two-stage Haiku pre-filter tried in Session 84 and reverted at 52.2%: that one REMOVED candidates.) A
`suggested_outside_pool` field in the pass schema replaces parsing free-text notes; it is a prompt change, so it is
versioned (L-2026-006).

### Cost per identification (Opus 4.8, $5 / $25; 38.9k measured input per 15 × 4 pass; output ASSUMED 1,000/pass)
| design | calls | cost | note |
|---|---|---|---|
| today | 3 | **$0.66** | pool recall ~34% |
| A — signal-ordered 15 | 3 | **$0.66** | pool recall 85–93% on the proxy; no new spend |
| B — ask-first + A | 1 + 3 | **$0.69** | stage 1 ≈ 2.2k system + 0.6k image + ~1k names in, ~300 out ≈ $0.03 |
| Mike's variant — full run, then re-run with X added on a miss | 3 (+3) | **$0.66 / $1.32** | the miss pays twice; on today's pool most runs miss |
| rerun variant, one scouting pass first | 1 + 3 | **$0.88** | strictly worse than B: $0.22 to learn what $0.03 learns |
| no cap, 1980s/MARVEL (43 × 4 = 172 images) | 3 | **$1.68** | ⚠️ over the API's per-request image limit as I recall it (100) and near the 32 MB cap — verify before considering |
| no cap, 2010s+ (90 creators) | 3 | **$3.40** | not viable |
| any design + a cache breakpoint after the references | 3 | **−$0.21** | passes 2–3 read the prefix at 0.1×: $0.66 → ~$0.45. Separate production change, argued on its own |

### Does the 15 cap move?
**Not yet.** With Design A the cap stops being the binding constraint (85–93% in 15), and every extra creator costs
~2,430 input tokens × 3 passes ≈ $0.036 per identification. Two measured reasons could move it later: if (2) shows
discrimination holds up with more distractors, 20 × 3 references is the same 60 images and the same cost as 15 × 4,
and buys five more candidates; if (2) shows confusion rising with pool size, the cap should fall, not rise. Decide
on (2)'s numbers, not before.

### Recommendation
Build **A now** (it is the pool fix), run ASM #252 on it — expected: Stan Lee in the pool by both priors. Hold **B**
until (3) shows how many misses are "signer passed the filter but ranked below 15": on the proxy that residue is
7–15%, which is what B is for.

## 3. The "$0.00" tile between Keep Raw and Register
**Neither: it is not a null renderer and item 21 did not miss it.** It is the **"My Val" input**
(`js/collection.js:492`, `:584`, class `my-valuation-input`) — an empty editable field whose **placeholder** is
"$0.00" in muted grey. No value is being rendered; the row simply has no `my_valuation`. It still reads as a price
on a row whose real figure sits two cells to the left, so it belongs on the follow-on: placeholder "$0.00" →
"Add yours" (or "—"), both templates.
**Item 21 DID miss one thing, found on the same read:** the "My Val" column sort (`js/collection.js:264`) still does
`(parseFloat(a.my_valuation) || 0)`, so rows with no valuation sort FIRST ascending as if worth $0 — the defect
`cmpFigure` fixed for the raw and slabbed sorts. Same one-line fix. Both added to ROADMAP item 21's follow-on beside
the dashboard sums.

## 4. Homepage and sitemap — the ground, not the shape (brief not in hand)
- **`robots.txt` is `User-agent: * / Disallow: /`**, live and in the repo, unchanged since `3039344` (2026-02-02),
  plus named blocks for AI crawlers. The whole site is closed to search. With that in place a sitemap does nothing,
  so the unit's first decision is whether the public pages open — a launch-posture decision, not a build detail.
- **No `sitemap.xml` exists in the repo.** `https://slabworthy.com/sitemap.xml` answers 200; that is most likely
  Pages serving a fallback page, not a sitemap — unverified, and if so it is a soft-404 worth fixing either way.
- `index.html` has a `<title>` ("Slab Worthy™ - AI for Collectors"); no robots meta or canonical link turned up.
- 23 root `.html` files. Public candidates: `index`, `about`, `pricing`, `faq`, `contact`, `privacy`, `terms`,
  `verify`, `check`, `waitlist`. Not for a sitemap: `app`, `collection`, `dashboard`, `account`, `admin`,
  `signatures`, `sightings`, `login`, `offline`, `waitlist-confirmed`, and three that look like strays —
  `body.html` (untracked), `collectioncalc.html`, `modal-ebay-listing.html` (ROADMAP item 9's orphan).
- Pages 308s `.html` to clean URLs, so a sitemap lists the clean form.
