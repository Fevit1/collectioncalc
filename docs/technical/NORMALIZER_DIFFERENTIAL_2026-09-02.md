# Normalizer differential — HEAD vs proposed, 2026-09-02

**Status: REPORT ONLY. Nothing applied, nothing staged.** Ship/no-ship is Mike's call.

| | |
|---|---|
| Current (HEAD) | `title_normalizer.py` at `4212316` |
| Proposed | working-tree `title_normalizer.py` (dirty since 2026-08-26) |
| Corpus | `ebay_sales` 297,559 rows + `market_sales` 10,593 rows, every non-null `raw_title` |
| Read | 2026-09-03 00:24 UTC, `DATABASE_URL_RO` (`do_readonly`), read-only session, SELECT only |
| Runtime | 368 s |
| Method | both versions run over each `raw_title`; rows compared on `canonical_title`; grouped by change class; source-drain and stored-vs-HEAD reported alongside |
| Verification | code-reviewer agent, static review of the script — clean |

## What the proposed change is

Two edits to the "by"-strip guard in `_build_canonical_title`:

1. `processor=str.lower` on the known-title check that decides whether to **skip** the destructive `by <Name>` strip. ALL-CAPS eBay titles (`WEREWOLF BY NIGHT`) failed the case-sensitive check, the strip ran, and the book split (`Werewolf By Night` vs `Werewolf`).
2. Skip the strip **only** when the matched known title itself contains " by " — so `Avengers by Jonathan Hickman` matching `Avengers` still gets its credit stripped.

Plus, in `scripts/backfill_canonical_titles.py`, a source-drain report (moving / staying / total per source canonical, PARTIAL flagged).

## Headline numbers

| table | rows | stored ≠ HEAD | **HEAD ≠ proposed** | stored ≠ proposed |
|---|---|---|---|---|
| ebay_sales | 297,559 | 719 | **192** | 911 |
| market_sales | 10,593 | 1 | **0** | 1 |

- **The differential is 192 rows, every one of them Werewolf by Night.** No other title moves. No zero-row title is created or erased by this change.
- **stored ≠ HEAD on 720 rows.** The stored canonical is *not* what HEAD's code produces: 697 rows are stored as `Werewolf` that HEAD would now write as `Werewolf By Night`. That is the 2026-08-17 guard commit, measured then at "719 rows change", **never backfilled in production.** The backfill script's docstring ("baseline is flat, verified 2026-08-17: 274,344 of 274,344") described the pre-change code and is stale. Whichever way item 3 goes, that 720-row backfill debt exists independently.

## HEAD → proposed, by change class (ebay_sales)

### A. by-phrase PRESERVED — 190 rows, 19 pairs

The proposed guard now recognises the ALL-CAPS/odd-cased listing as a known "by" title and keeps the tokens.

| rows | HEAD canonical | proposed canonical | note |
|---|---|---|---|
| 156 | `Werewolf` | `Werewolf by Night` | lands on the known title (see case note below) |
| 6 | `Werewolf: Red Band` | `Werewolf by Night: Red Band` | 2024 series |
| 3 | `Werewolf` | `Werewolf by Night Red Band` | |
| 2 | `Werewolf #'s` | `Werewolf by Night #'s` | |
| 2 | `Werewolf ( -77` | `Werewolf by Night ( -77` | pre-existing paren mangling, unchanged |
| 2 | `Werewolf. 32` | `Werewolf by Night No. 32` | |
| 2 | `Werewolf` | `Werewolf by Night Vol` | pre-existing "Vol" residue |
| 2 | `Giant-Size Werewolf` | `Giant-Size Werewolf by Night` | |
| 2 | `Werewolf` | `Werewolf by Night Blood Hunt` | 2024 series |
| 2 ×3 | `9.2) Werewolf` etc. | `9.2) Werewolf by Night` etc. | pre-existing grade-prefix residue |
| 1 ×7 | assorted prefix junk + `Werewolf` | same junk + `Werewolf by Night` | emoji / lot-number prefixes, pre-existing |

Every pair in this class is the same book gaining its real name. The junk prefixes and `Vol`/`( -77` residues are **pre-existing defects that this change neither causes nor fixes**; they were wrong under `Werewolf` and remain wrong under `Werewolf by Night`.

### B. by-phrase NOW STRIPPED — 0 rows

The second edit (require " by " in the matched title) changes nothing in the corpus today. There is no `Avengers by Hickman`-shaped row currently being protected by the old guard. The edit is defensive, not corrective.

### C. OTHER — 2 rows, 1 pair

| rows | HEAD | proposed | raw |
|---|---|---|---|
| 2 | `Werewolf By Night` | `Dead Night Werewolf by Night` | `Dead of Night Werewolf by Night #1 Marvel Comics 2009` |

Under HEAD the strip ran (`Dead of Night Werewolf`) and the fuzzy assign still landed on the known title. Under proposed the strip is skipped, the longer text fails the token guard, and the row falls through to the title-caser — where the M1 filler bug (`of` stripped from every title) produces `Dead Night Werewolf by Night`. The 2009 MAX miniseries *is* a different book from the 1972 series, so **leaving the known title is arguably the correct direction**, but the destination string is mangled by a separate, known defect (L-SW-2026-027, M1). Two rows.

## Source drain (HEAD canonical → anything else)

| source | moving | staying | total | |
|---|---|---|---|---|
| `Werewolf` | 164 | 14 | 178 | PARTIAL |
| `Werewolf By Night` | 2 | 724 | 726 | PARTIAL (the class-C pair) |
| `Giant-Size Werewolf` | 2 | 2 | 4 | PARTIAL |
| 13 junk-prefixed sources | 1–6 each | 0 | | FULL |

**The 14 rows left under `Werewolf`** (read individually): 9 are lots, complete sets, or TPB/Complete Collection listings that the comp queries' noise filter already excludes or that carry no single-issue number; `Werewolf #1 VG 4.0 1966` is the Dell book and genuinely different; `Werewolf #25 VF- 1975 Kane` is Werewolf by Night listed without the name and cannot be recovered from the title alone; **2 × `WEREWOLF BY NIGHT BLOOD MOON RISE #1`** (2025 series) are a residual miss — the extra tokens fail the token guard. Not a regression; a gap the change does not close.

**The 2 rows left under `Giant-Size Werewolf`** are listed exactly that way on eBay (`GIANT-SIZE WEREWOLF # 5`); the other 2 say "by Night" and move. Whether `Giant-Size Werewolf` / `Giant-Size Werewolf by Night` should be one pool is a known-titles question, not a normalizer one.

## ⚠️ The case split — read this before deciding

After the change, `ebay_sales.canonical_title` for this book would hold **two spellings**:

| spelling | rows | how it gets there |
|---|---|---|
| `Werewolf By Night` | 723 | assigned verbatim from `known_titles.json` (entry is spelled with capital "By") — mixed-case listings that pass the still-case-sensitive assigning match |
| `Werewolf by Night` | 156 | ALL-CAPS listings: the guard now preserves the tokens, but the canonical-**assigning** fuzzy match below the guard is still case-sensitive (defect M3), so the row falls through to the title-caser, whose small-word set lowercases "by" |

The proposed change's own comment says it deliberately does **not** lowercase the assigning match ("this decides only whether to SKIP a destructive strip, so it can preserve tokens but can never merge two books"). That is a sound scoping decision, and the consequence is this split.

**For comp lookup the split is invisible:** `title_matching._norm()` and `_norm_sql()` lowercase both sides before comparing, so 723 + 156 = 879 rows match one query. **For anything that groups or displays on the raw `canonical_title` string** (admin views, `GROUP BY canonical_title` reports, the corpus snapshot's per-title counts) they are two rows. This was already true in a smaller way — the 14 stayers and junk-prefixed rows are also outside the pool — but 156 rows is the largest instance and it is created by this change.

Options, for Mike, not decided here:
- Ship as-is and accept the stored-string split (comps unaffected).
- Ship with a one-line follow-on: lowercase the title-caser's output comparison so that a title-cased result equal (case-insensitively) to a known title is replaced by the known title's spelling. That would need its own differential.
- Fix M3 (case-insensitive assigning match) — explicitly out of scope per L-SW-2026-027, since it interacts with M1 and must be measured in combination.

## What a backfill would actually rewrite

`stored ≠ proposed` = 912 rows (911 eBay + 1 Whatnot). Of those, 720 are the un-backfilled 08-17 change and 192 are this one. The backfill script handles both in one pass because it compares stored to the current code's output. **Code change and backfill remain one unit** (script docstring, unchanged rule).

## Not done, deliberately

- Nothing staged. `title_normalizer.py` and `scripts/backfill_canonical_titles.py` are exactly as they were this morning.
- The differential script is `normalizer_differential.py` in this session's scratchpad (temp dir, not the repo). If the differential is to be the standing control for every future normalizer change — L-SW-2026-027 says it is — it belongs in `scripts/`. Mike's call; not copied in this pass.
- No Anthropic API calls were made. Spend today: $0.
