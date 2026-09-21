"""Signed-versus-unsigned premium from ebay_sales. REPORT ONLY — read-only DB, no model calls, $0.

For every title-issue pair with >= 10 signed AND >= 10 unsigned GRADED sales in the last 365 days:
median sale price by grade band for raw unsigned / raw signed / slabbed unsigned / slabbed signed,
the last split into WITNESSED and unwitnessed. Top 20 pairs by total sample, counts in every cell.

  slabbed   = ebay_sales.graded (a grading company was parsed from the title); band from `grade`.
  raw       = not graded; band from `grade_from_title` — the SELLER-STATED grade, labelled as such.
  signed    = SIGNED_RE on raw_title (below) — deliberately NOT the stored is_signed flag, so the
              report states its own rule; the two are compared at the end.
  witnessed = a slabbed signed row whose title says Signature Series / SS / Verified Signature /
              yellow label (CGC SS, CBCS VSP). Everything else slabbed-and-signed is unwitnessed
              (green "qualified" label, JSA / Beckett / COA, or simply unstated).
Lots, reprints, facsimiles and variants are excluded, as the valuation pools exclude them.
The valuation code EXCLUDES signed rows on purpose (a signature is a second price driver it cannot
attribute, so signed sales would contaminate the unsigned comps a user is priced against). This
report reads them on purpose: the premium is the thing being measured.
"""
import os
import re
import statistics
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, '.env'))

SIGNED_RE = re.compile(r"\b(signature\s+series|ss|signed|autograph(?:ed)?|auto|verified\s+signature|vsp|sig(?:nature)?)\b", re.I)
NOT_SIGNED_RE = re.compile(r"\b(unsigned|not\s+signed|facsimile\s+sig|printed\s+sig|signature\s+(?:page|stamp))", re.I)
WITNESS_RE = re.compile(r"\b(signature\s+series|ss|verified\s+signature|vsp|yellow\s+label)\b", re.I)
SIGNED_BY_RE = re.compile(r"(?:signed|auto(?:graph(?:ed)?)?|ss|signature\s+series)\s+(?:by\s+)?([A-Z][a-zA-Z\.']+(?:\s+[A-Z][a-zA-Z\.']+){1,2})")
BANDS = [('4.5-7.9', 4.5, 7.9), ('8.0-8.9', 8.0, 8.9), ('9.0-9.6', 9.0, 9.6), ('9.8+', 9.8, 10.0)]
GROUPS = ['raw unsigned', 'raw signed', 'slab unsigned', 'slab signed WITNESSED', 'slab signed unwitnessed']


def band(g):
    if g is None:
        return None
    g = float(g)
    for name, lo, hi in BANDS:
        if lo <= g <= hi:
            return name
    return None


def main():
    conn = psycopg2.connect(os.environ['DATABASE_URL_RO'], connect_timeout=15)
    try:
        conn.set_session(readonly=True)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SET statement_timeout = 180000")
        cur.execute("SELECT creator_name FROM creator_signatures WHERE active")
        creators = [r['creator_name'] for r in cur.fetchall()]
        cur.execute("""
            SELECT raw_title, canonical_title, issue_number, sale_price, graded, grade, grade_from_title, is_signed
            FROM ebay_sales
            WHERE sale_date >= now() - interval '365 days'
              AND canonical_title IS NOT NULL AND canonical_title <> '' AND issue_number IS NOT NULL
              AND sale_price > 0
              AND COALESCE(is_lot, false) = false AND COALESCE(is_reprint, false) = false
              AND COALESCE(is_facsimile, false) = false AND COALESCE(is_variant, false) = false
              AND (grade IS NOT NULL OR grade_from_title IS NOT NULL)
        """)
        rows = cur.fetchall()
    finally:
        conn.close()

    cells = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))   # pair -> group -> band -> prices
    signers = defaultdict(Counter)
    tot = defaultdict(lambda: [0, 0])                                     # pair -> [signed, unsigned]
    agree = Counter()
    for r in rows:
        t = r['raw_title'] or ''
        signed = bool(SIGNED_RE.search(t)) and not NOT_SIGNED_RE.search(t)
        agree[(signed, bool(r['is_signed']))] += 1
        slab = bool(r['graded'])
        b = band(r['grade'] if slab else r['grade_from_title'])
        if not b:
            continue
        pair = (r['canonical_title'], str(r['issue_number']))
        if slab:
            grp = ('slab signed WITNESSED' if WITNESS_RE.search(t) else 'slab signed unwitnessed') if signed else 'slab unsigned'
        else:
            grp = 'raw signed' if signed else 'raw unsigned'
        cells[pair][grp][b].append(float(r['sale_price']))
        tot[pair][0 if signed else 1] += 1
        if signed:
            named = [c for c in creators if c.lower() in t.lower()]
            if named:
                for c in named:
                    signers[pair][c] += 1
            else:
                m = SIGNED_BY_RE.search(t)
                if m:
                    signers[pair][m.group(1).strip() + ' (as written)'] += 1

    eligible = [(p, s + u, s, u) for p, (s, u) in tot.items() if s >= 10 and u >= 10]
    eligible.sort(key=lambda x: -x[1])
    out = []
    w = out.append
    w(f"rows read (365 days, graded or listing-stated grade, no lots/reprints/facsimiles/variants): {len(rows):,}")
    w(f"title-issue pairs with >= 10 signed AND >= 10 unsigned graded sales: {len(eligible)}")
    w(f"signed rule vs stored is_signed flag (rule, flag): {dict(agree)}")
    w('')
    for pair, n, s, u in eligible[:20]:
        top = ', '.join(f"{k} {v}" for k, v in signers[pair].most_common(3)) or 'no signer named'
        w(f"### {pair[0]} #{pair[1]} — {n} sales ({s} signed, {u} unsigned) — signer(s): {top}")
        w('| band | ' + ' | '.join(GROUPS) + ' |')
        w('|---|' + '---|' * len(GROUPS))
        for bname, _, _ in BANDS:
            line = [bname]
            for g in GROUPS:
                v = cells[pair][g][bname]
                line.append(f"${statistics.median(v):,.0f} (n={len(v)})" if v else '—')
            w('| ' + ' | '.join(line) + ' |')
        w('')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
