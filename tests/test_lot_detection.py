r"""
Fixture gate for the FIX-2 query-time "lot shield" (launch-critical, Bucket 1).

These are the EXACT patterns added to the eBay graded/raw comp-pool queries in
routes/sales_valuation.py (the launch shield that protects the existing ~48K
corpus without a backfill). This file is the single source of truth for the
pattern strings — the SQL WHERE additions must mirror them byte-for-byte.

Why a fixture and not a DB test: the shield must flag every multi-book/combo/run
listing (so a lot can never price a single issue) while NOT flagging legit
singles. The combo pattern is the risky one; this proves ZERO false positives on
the negative set before the diff is authorized.

POSIX note: Postgres regex has NO lookahead, so the range pattern guards against
"#1 - 1st" by requiring the SECOND number to be >=2 digits (\d{2,4}) rather than
a negative lookahead. The patterns below are written to be valid in BOTH Python
`re` (this test) and Postgres `~*` (the shipped SQL).

Run:  python tests/test_lot_detection.py      (prints pass/fail table, exit 1 on any fail)
      pytest tests/test_lot_detection.py
"""
import re
import sys

# ── Shield patterns (mirror the SQL exactly) ─────────────────────────────────
# 1) substring LIKE checks  ->  LOWER(raw_title) LIKE '%...%'
LIKE_SIGNALS = [
    "lot of",        # existing
    "bundle",        # existing
    "complete set",
    "complete run",
    "full run",
    "all covers",
]
# 2) "+N extra/more books" -> raw_title ~* '\d+\s+(extra|more)\s+(book|comic|issue)s?'
RE_EXTRA = re.compile(r"\d+\s+(extra|more)\s+(book|comic|issue)s?", re.IGNORECASE)
# 3) issue RANGE "#1-113"/"#94-100" -> raw_title ~* '#\s*\d{1,4}\s*[-–]\s*\d{2,4}'
#    2nd token >=2 digits is the lookahead-free guard against "#1 - 1st".
RE_RANGE = re.compile(r"#\s*\d{1,4}\s*[-–]\s*\d{2,4}")
# 4) COMBO "Hulk 181 + Giant-Size X-Men 1": letter→number, +/&, then a NAMED
#    second book that ALSO ends in a number. Requiring a number on BOTH sides
#    (and a letter starting the 2nd operand) is what keeps "Hulk 181 + Sketch
#    variant", "CGC 9.8 + Signed", and "9.8 NM+/M" from tripping it.
#    -> raw_title ~* "[a-z]\s*#?\d{1,4}\s*[+&]\s*[a-z][a-z0-9 .'\-]*?\d{1,4}"
RE_COMBO = re.compile(r"[a-z]\s*#?\d{1,4}\s*[+&]\s*[a-z][a-z0-9 .'\-]*?\d{1,4}", re.IGNORECASE)


def lot_shield_signal(raw_title):
    """Return (signal_name, matched_text) if the shield would EXCLUDE this row,
    else None. Mirrors the SQL `AND NOT (... OR ...)` exclusion."""
    if not raw_title:
        return None
    low = raw_title.lower()
    for s in LIKE_SIGNALS:
        if s in low:
            return ("like:" + s, s)
    m = RE_EXTRA.search(raw_title)
    if m:
        return ("extra_books", m.group(0))
    m = RE_RANGE.search(raw_title)
    if m:
        return ("range", m.group(0))
    m = RE_COMBO.search(raw_title)
    if m:
        return ("combo", m.group(0))
    return None


# ── Fixtures: real titles from the investigation ─────────────────────────────
POSITIVES = [
    # the $174,999.99 wrong-item that priced a single Hulk #181 9.8
    "Incredible Hulk 181 + Giant-size X-men 1 Cgc 9.8 WP Perfect Centering",
    "X-Men #1-113 Complete W/Keys + Annuals And More (Marvel 1991) Jim Lee *VF-NM*",
    "X-MEN #1 A B C D & E (1991) CGC 9.8 COMPLETE SET of JIM LEE! 2 Sets",
    "Uncanny X-Men #94-143 Complete Run Bronze Age Marvel",
    "X-MEN 1-12 (1991) JIM LEE & CHRIS CLAREMONT!!! ALL COVERS INCLUDED!!!",
    "INCREDIBLE HULK #181 CGC 5.5 - 1ST APPEARANCE OF WOLVERINE -plus 9 Extra Books",
    "X-Men #1-35 (Complete) Marvel 1991 Series Lot, 1 2 3 4 5 6 7 8 9 10 11",
    "X-Men (1991) #1-100 Set Lot Full Run All 5 #1 Covers, 95, 96, 97, 98",
]

NEGATIVES = [
    # legit singles that MUST NOT be flagged as lot/multi
    "Giant-Size X-Men #1 - 1st App Storm Colossus Nightcrawler - Higher Grade Plus",
    "Giant-Size X-Men #1 CGC 8.5 WHITE Marvel 1975 - 1st New Team - Bright Reds",
    "Hulk 181 + Sketch variant",
    "CGC 9.8 + Signed",
    "Giant-Size X-Men #1 - 2nd print",                    # "#1 - 2nd" form
    "Amazing Spider-Man #129 (1974) CGC 8.5 - 1st app Punisher (Frank Castle)",
    "X-Men #1 (2024) Alex Ross Storm Variant CGC 9.8 NM+/M SDCC",   # NM+ must not trip combo
    "Incredible Hulk #181 - 1st Full App Wolverine / Wendigo App (CGC 4.5) 1974",
]


def _run():
    rows = []
    ok = True
    for t in POSITIVES:
        sig = lot_shield_signal(t)
        passed = sig is not None
        ok = ok and passed
        rows.append(("POS", passed, sig[0] if sig else "—", t))
    for t in NEGATIVES:
        sig = lot_shield_signal(t)
        passed = sig is None          # negatives pass when NOT flagged
        ok = ok and passed
        rows.append(("NEG", passed, sig[0] if sig else "—", t))

    print("=" * 100)
    print(f"{'KIND':<4} {'RESULT':<6} {'SIGNAL':<14} TITLE")
    print("-" * 100)
    for kind, passed, sig, t in rows:
        print(f"{kind:<4} {('PASS' if passed else 'FAIL'):<6} {sig:<14} {t[:62]}")
    print("=" * 100)
    n_pos = sum(1 for k, *_ in rows if k == "POS")
    n_neg = len(rows) - n_pos
    print(f"positives: {sum(1 for k,p,*_ in rows if k=='POS' and p)}/{n_pos} flagged   "
          f"negatives: {sum(1 for k,p,*_ in rows if k=='NEG' and p)}/{n_neg} clean   "
          f"=> {'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return ok


# pytest entry points
def test_positives_flagged():
    for t in POSITIVES:
        assert lot_shield_signal(t) is not None, f"should be flagged: {t}"


def test_negatives_not_flagged():
    for t in NEGATIVES:
        assert lot_shield_signal(t) is None, f"false positive: {t}"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(0 if _run() else 1)
