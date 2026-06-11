r"""
Fixture for the conditional variant-exclusion disclosure (Bucket 1, folded into
the variant/lot filter commit).

`compute_variant_disclosure` below mirrors the helper added to
routes/sales_valuation.py byte-for-byte — this file is the single source of truth
for the threshold so the diff and the test can't drift.

The disclosure fires ONLY when excluded variants are a MATERIAL share of a book's
available graded comps, so it stays quiet where the base number is representative
(newsstand ≈ direct) and only speaks up on variant-heavy books (Absolute Batman).

Calibrated against live read-only counts (graded, title+issue):
  Absolute Batman #1 : base  8, variant  4  -> 33.3%  FIRES
  Amazing SM   #300  : base123, variant 33  -> 21.2%  quiet
  X-Men        #1    : base 48, variant 13  -> 21.3%  quiet
  Incredible Hulk#181: base149, variant 11  ->  6.9%  quiet

Run:  python tests/test_variant_disclosure.py    (table + exit 1 on any fail)
"""
import sys


def compute_variant_disclosure(base_count, excluded_variant_count,
                               pct_threshold=30.0, min_excluded=3, min_total=5):
    """Disclosure ABOUT the base-cover number — never changes the FMV itself.
    Fires only when excluded variants are a material share AND the sample is big
    enough that the percentage isn't thin-data noise (thin samples already read
    low-confidence via the sample-size confidence score)."""
    total = base_count + excluded_variant_count
    pct = round(100.0 * excluded_variant_count / total, 1) if total else 0.0
    fires = (total >= min_total
             and excluded_variant_count >= min_excluded
             and pct >= pct_threshold)
    return {
        'variant_excluded': fires,
        'variant_excluded_pct': pct,
        'variant_excluded_count': excluded_variant_count,
        'variant_disclosure': (
            "Estimate reflects the standard cover; variant sales excluded."
            if fires else None),
    }


# (label, base, excluded, expected_fires)
CASES = [
    ("Absolute Batman #1 (real)",       8,   4,  True),   # 33.3% -> fire
    ("Amazing Spider-Man #300 (real)",  123, 33, False),  # 21.2% -> quiet
    ("X-Men #1 (real)",                 48,  13, False),  # 21.3% -> quiet
    ("Incredible Hulk #181 (real)",     149, 11, False),  # 6.9%  -> quiet
    ("boundary exactly 30%",            7,   3,  True),    # 30.0%, 3 excl, 10 tot
    ("thin: 50% but total<5",           2,   2,  False),   # noise guard
    ("thin: 33% but <3 excluded",       4,   2,  False),   # noise guard
    ("no variants",                     10,  0,  False),   # 0%
    ("variant-dominant 60%",            4,   6,  True),    # outnumber base
]


def _run():
    ok = True
    print("=" * 92)
    print(f"{'CASE':<34}{'base':>5}{'excl':>5}{'pct':>7}  {'FIRES':<6} RESULT")
    print("-" * 92)
    for label, base, excl, expected in CASES:
        d = compute_variant_disclosure(base, excl)
        passed = (d['variant_excluded'] == expected)
        ok = ok and passed
        print(f"{label:<34}{base:>5}{excl:>5}{d['variant_excluded_pct']:>6}%  "
              f"{str(d['variant_excluded']):<6} {'PASS' if passed else 'FAIL'}")
    print("=" * 92)
    print("ALL PASS" if ok else "FAILURES PRESENT")
    return ok


def test_real_keys_classified_correctly():
    for label, base, excl, expected in CASES:
        d = compute_variant_disclosure(base, excl)
        assert d['variant_excluded'] == expected, label


def test_disclosure_message_only_when_fires():
    on = compute_variant_disclosure(8, 4)
    off = compute_variant_disclosure(149, 11)
    assert on['variant_disclosure'] and "standard cover" in on['variant_disclosure']
    assert off['variant_disclosure'] is None


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(0 if _run() else 1)
