# Signature measurement unit — prep findings, 2026-09-18

**Status: PREP ONLY. $0.0002 spent (the temperature probe). No matcher call has run. Parts (2) and (3) wait on Mike's go on the
estimate below, and the whole unit is queued behind the privacy ship.** Read-only DB (RO role),
`count_tokens` (free), and GETs to our own R2 only. No eBay request of any kind.

Pointed to from `WHERE_WE_LEFT_OFF.md` (2026-09-18 entry) and committed with that records pass.

## Part 1 — reference set (DONE, read-only)

- `creator_signatures`: 100 rows, 100 active. `signature_images`: **389 images across 99 creators**
  (README-era figure was 361 / 92). Last upload 2026-09-18 04:22Z. `reference_image_count` matches
  the real count for all 100.
- Distribution: 94 creators × 4 images, 1 × 5, 2 × 3, 2 × 1, 1 × 0.
- The matcher's floor is **2** (`cs.reference_image_count >= 2` and `HAVING COUNT(si.id) >= 2`,
  `routes/signature_orchestrator.py:156,201`). Below it, so never a candidate:
  **Whilce Portacio (0), Ryan Stegman (1), Warren Ellis (1).** 97 creators are matchable.
- It sends at most 4 references per creator (`REFERENCE_IMAGES_PER_CREATOR`).

## Blockers found while reading the matcher (none fixed — report only)

1. **`temperature` on Opus 4.8 — a hard failure in prod, PROVEN (see the end of this item).** `run_single_pass` sends
   `temperature=0.2/0.5/0.7` to `OPUS` = `claude-opus-4-8` (head of the chain since `647bca2`,
   2026-06-23). The API reference lists sampling params as removed (400) on Opus 4.7/4.8. The call is
   not routed through `call_with_fallback`; a 400 is caught as a generic exception, so all three passes
   fail and the route raises "All Opus passes failed". `signature_identification_log` has 15 rows and
   the **last is 2026-06-16** — a week before the switch — which is consistent with it never having
   succeeded since. **PROVEN 2026-09-18 (probe approved by Mike, $0.0002):** `claude-opus-4-8` with
   `temperature=0.2` → 400 "`temperature` is deprecated for this model."; the same call without it → 200.
   So `/api/signatures/v2/match` has failed on every request since the `647bca2` deploy (2026-06-23), and the
   three-temperature ensemble cannot exist on this model: three passes would be three default-sampling runs.
2. **Every reference is sent as `image/jpeg`; 40 of 60 sampled references are PNG.** The API validates
   media type against the bytes. The June runs predate most PNG uploads.
3. **The pre-filter's pool is arbitrary.** `ORDER BY reference_image_count DESC LIMIT 15` with 94
   creators tied at 4: whenever more than 15 pass the era/publisher filter, which 15 are compared is
   undefined tie order. The true signer can be absent from the pool before any vision call — the June
   log shows the shape (rows 11 and 13: the notes name José Luis García-López, the ranking says
   George Pérez, because the answer must come from the pool).
4. Request size: 60 references = 19.1 MB raw, ~25.5 MB base64, against a 32 MB request cap.

## Measured cost basis

`count_tokens`, `claude-opus-4-8`, the real system prompt, 15 creators × 4 real references + 1 target:
**38,903 input tokens per pass** (system + scaffold 2,196; ~602 per image; long edge 58 / 875 / 1,834
px min/median/max). Opus 4.8 = $5 / $25 per MTok. Output is NOT measured (no call has run): 1,000
tokens per pass assumed, 1,500 is the hard cap (`max_tokens`).

- One pass, as the code runs it (no caching): **$0.22**. One identification (3 passes): **$0.66**.

| design | calls | est. | worst case (output at cap) |
|---|---|---|---|
| (2) as literally specified: leave-one-out, all 386 images, 3 passes, no cache | 1,158 | **$255** | $270 |
| (2) one held-out image per creator, 3 passes, no cache | 291 | **$64** | $68 |
| (2) same, fixed pools + prompt cache, 3 passes | 291 | **$14.60** | $18.60 |
| (2) same, fixed pools + prompt cache, **1 pass** | 97 | **$5.70** | $7.00 |
| (3) 100 eBay rows, prod pipeline, 3 passes, no cache | 300 | **$66** | $70 |
| (3) 100 rows, grouped by (era, publisher) pool + cache, 3 passes | 300 | **$17.60** | $21.40 |
| (3) same, **1 pass** | 100 | **$8.10** | $9.40 |

Today's API total before any of this: **$0.00**. Every 3-pass design crosses $10 alone; (2) and (3)
at 1 pass are $13.80 together, so they fit under the ceiling only on separate days.

Split proposed for (2): hold out each creator's LAST image by `sort_order` (95 creators with >= 4 keep
3 references; the two 3-image creators keep 2; 97 queries), seven fixed pools of ~14 grouped by career
era so the reference prefix is byte-identical within a pool and caches. This measures discrimination
with the signer guaranteed in the pool; pre-filter recall is a separate, free SQL number.

## Part 3 population (read-only)

`ebay_sales` rows whose title has CGC/CBCS and a signed marker: 6,302, of which **5,002 already have an
R2 copy of the listing image (`r2_image_url`, img.slabworthy.com)** — so the sample needs **zero eBay
CDN requests** and the capture-safety exception is not in play. Of those: 2,171 name exactly one
in-set creator by full name (73 distinct signers; Scott Snyder 399, Todd McFarlane 379, Stan Lee 240),
145 name several, 2,686 name no in-set creator by full name. Two cautions: a named creator is not
always the signer ("McFarlane cover, signed by Stan Lee"), so labels need a "signed by / SS <name>"
pattern, and the R2 copies are whole-slab listing photos, so "signature too small to read" (the
June log's commonest note) will be a large bucket.
