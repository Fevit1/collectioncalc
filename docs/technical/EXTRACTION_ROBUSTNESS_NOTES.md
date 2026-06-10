# Extraction Robustness Notes

Running log of identity/extraction robustness issues — the recurring theme that
the book the model *reads* and the identity we *price* can diverge. Capture
here; fixes happen in scoped batches.

> Note: created in-repo 2026-06-08 (Batch 8). If an external copy exists, merge.

---

## Theme: series-type qualifiers (Giant-Size / Annual / Special / Limited Series)

The extractor reads the qualifier into `issue_type`, but for a long time
`issue_type` was orphaned — display and valuation used bare `title`, so a
qualified book was priced as its base series.

Instances seen:
- **Hercules "Limited Series"** — qualifier dropped from identity.
- **Amethyst "Annual"** — qualifier dropped; plus a separate barcode addon
  false-decode (→ "issue 251"), fixed in Batch 4A.
- **Giant-Size X-Men #1** — read correctly (year 1975) but displayed/priced as
  "X-Men #1". Worse, the valuation `parsed_title LIKE` fallback BLENDED books
  (X-Men #1 query mixed 1991 Jim Lee + 1963 key + Giant-Size into one median).

**Status: ADDRESSED in Batch 8** (2026-06-08) — `issue_type` is now plumbed into
display + valuation; matching is qualifier-precise via `title_matching.py`
(prefix/suffix composition + gated LIKE). Proof: Giant-Size X-Men #1 median
$40 (blended) → ~$1,500 (Bronze key); plain X-Men #1 no longer pulls Giant-Size.

### Known residual limitation (Batch 8)
The qualifier detector is a **coarse regex** (`giant size|king size|annual|special`).
Note it requires `giant size`/`king size` (with the word "size"), so a series
named "Giant Days" is SAFE. The real exposure is a series whose own name contains
**"Annual"/"Special"** as a word (e.g. a standalone "Special", "Special Forces"):
a plain query for it has its LIKE-FALLBACK rows excluded by the gate (the
exact-`canonical_title` arm still matches, so only rows with a dirty/NULL
canonical are dropped). ASM #300 control unchanged → not biting in practice.
Cheap future fix if it ever bites: exclude only qualifier tokens NOT already
present in the base title. Deferred per Mike (don't chase now).

---

## OPEN — next layer: year/edition collision *within* a plain title

**Not yet fixed (captured 2026-06-08, Batch 8).** Batch 8 fixed the QUALIFIER
collision, not the YEAR/EDITION collision. A plain `canonical_title='X-Men'`
#1 still blends **different books that legitimately share that exact title**:
- X-Men #1 **1963** (Silver Age key, $$$$)
- X-Men #1 **1991** Jim Lee (modern, cheap — dominates the corpus)
- X-Men #1 other vol/editions

So plain "X-Men #1" returning ~$25–$750 (depending on grade) is **still a blend**,
not a single book's value. The corpus has `title_year` / year signals and the
extractor reads `year`; the next-layer fix is to disambiguate by year/era
(and possibly volume) so "X-Men #1 (1963)" prices separately from "(1991)".
Same theme as the qualifier work — identity precision — one level deeper.
**$25 is NOT the final answer for "X-Men #1."**
