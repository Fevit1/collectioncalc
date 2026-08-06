#!/usr/bin/env python
"""END-OF-DAY CORPUS SNAPSHOT — READ-ONLY. Re-runnable, output comparable day to day.

Run at the end of each capture day. Every section is a point-in-time reading
against the UTC timestamp printed at the top; the corpus grows ~20k rows/day, so
two runs WILL disagree and that is growth, not error. Compare a figure only
against the timestamp in its own output.

Connects with DATABASE_URL_RO (the do_readonly role), opens a hard READ-ONLY
session, runs ONLY SELECTs. No writes, no DDL. Same pattern as
scripts/coverage_assessment.py.

Also the seed of the admin corpus dashboard: `--json` emits the same numbers as
a machine-readable object so a route can serve them without re-deriving anything.

METHOD MIX mirrors SHIPPED valuation behaviour as of 2026-08-05, including
Unit 1 (the verdict gate) and Unit 3 (MIN_SOURCE_COMPS=2 on interpolation
sources, and the `low_support` tier). If sales_valuation.py changes its tiering,
change CLASSIFY here or the two will silently drift apart.

Usage:
    python -u scripts/corpus_snapshot.py [--days 365] [--json]
"""
import argparse
import io
import json
import os
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')  # cross-project L-2026-015

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def load_env(path=None):
    """Load .env without printing any value."""
    path = path or os.path.join(_ROOT, '.env')
    if not os.path.exists(path):
        return
    for line in io.open(path, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()

import psycopg2                                     # noqa: E402
from psycopg2.extras import RealDictCursor          # noqa: E402
from title_matching import _norm_sql, _norm         # noqa: E402

BAR = '=' * 74

# The valuation engine's grade ladder (grade_baselines keys, sales_valuation.py).
LADDER = [10.0, 9.8, 9.6, 9.4, 9.2, 9.0, 8.5, 8.0, 7.5, 7.0,
          6.5, 6.0, 5.5, 5.0, 4.5, 4.0, 3.5, 3.0, 2.0, 1.0]
MIN_SOURCE_COMPS = 2          # Unit 3, must track sales_valuation.py

# Capture schedule §2A — starved keys. §1 target: >=10 comps AND >=5 graded.
STARVED = [('Incredible Hulk', '180'), ('Incredible Hulk', '271'),
           ('Iron Man', '55'), ('Captain America', '117'),
           ('Batman', '227'), ('Batman', '232'), ('Batman', '423'),
           ('Detective Comics', '880'), ('X-Men', '94')]
TARGET_COMPS, TARGET_GRADED = 10, 5

# Production noise filters, mirrored from the comp queries.
NOISE = """
   AND LOWER(raw_title) NOT LIKE '%%facsimile%%' AND LOWER(raw_title) NOT LIKE '%%reprint%%'
   AND LOWER(raw_title) NOT LIKE '%%lot of%%'    AND LOWER(raw_title) NOT LIKE '%%bundle%%'
   AND LOWER(raw_title) NOT LIKE '%%complete set%%' AND LOWER(raw_title) NOT LIKE '%%complete run%%'
   AND LOWER(raw_title) NOT LIKE '%%full run%%'  AND LOWER(raw_title) NOT LIKE '%%all covers%%'
"""


def say(*a):
    print(*a, flush=True)


def pct(n, d, default='--'):
    return f'{100.0 * n / d:.1f}%' if d else default


def connect():
    url = os.environ.get('DATABASE_URL_RO')
    if not url:
        say('FATAL: DATABASE_URL_RO not set. This script refuses to run on a '
            'read-write DSN.')
        sys.exit(1)
    conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '300s'")
    return conn, cur


def classify(buckets, grade, has_raw):
    """Mirror of the shipped tiering. `buckets` is {grade: comp_count} for one
    (title, issue). Returns one of the six verdict tiers."""
    n = buckets.get(grade, 0)
    nearby = [g for g in buckets if g != grade]
    qualifying = [g for g in nearby if buckets[g] >= MIN_SOURCE_COMPS]
    if n >= 3:
        return 'exact'
    if n >= 1:
        return 'blended' if qualifying else 'exact_thin'
    if qualifying:
        return 'interpolated'
    if nearby:
        return 'low_support'          # Unit 3: nearby sales exist, all too thin
    return 'estimated_from_raw' if has_raw else 'fabricated'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=365,
                    help='Lookback window. Default 365 = /api/sales/valuation.')
    ap.add_argument('--json', action='store_true',
                    help='Emit machine-readable JSON instead of the report.')
    args = ap.parse_args()
    out = {}
    conn, cur = connect()
    try:
        # ---------- header ------------------------------------------------
        cur.execute("SELECT NOW() AT TIME ZONE 'UTC' AS utc, current_user AS u")
        h = cur.fetchone()
        out['snapshot_utc'] = str(h['utc'])
        out['window_days'] = args.days
        if not args.json:
            say(BAR)
            say(f'CORPUS SNAPSHOT — {h["utc"]} UTC')
            say(f'role={h["u"]} (READ ONLY)   window={args.days}d')
            say(BAR)
            say('Point-in-time. The corpus grows ~20k rows/day; disagreement '
                'with an\nearlier run is growth, not error.')

        # ---------- 1. counts, today, freshness ---------------------------
        cur.execute("""
            SELECT (SELECT count(*) FROM ebay_sales)                          AS e_rows,
                   (SELECT count(*) FROM market_sales)                        AS m_rows,
                   (SELECT count(*) FROM ebay_sales
                     WHERE created_at >= date_trunc('day', NOW()))            AS e_today,
                   (SELECT count(*) FROM market_sales
                     WHERE created_at >= date_trunc('day', NOW()))            AS m_today,
                   (SELECT max(sale_date) FROM ebay_sales)                    AS e_maxsale,
                   (SELECT max(sold_at)::date FROM market_sales)              AS m_maxsale,
                   (SELECT max(created_at) FROM ebay_sales)                   AS e_ingest,
                   (SELECT max(created_at) FROM market_sales)                 AS m_ingest,
                   (SELECT count(*) FROM ebay_sales WHERE graded)             AS e_graded
        """)
        r = cur.fetchone()
        total = r['e_rows'] + r['m_rows']
        cur.execute("""SELECT EXTRACT(day FROM NOW() - %s)::int AS e_d,
                              EXTRACT(day FROM NOW() - %s)::int AS m_d""",
                    [r['e_ingest'], r['m_ingest']])
        d = cur.fetchone()
        out['rows'] = {'ebay_sales': r['e_rows'], 'market_sales': r['m_rows'],
                       'total': total}
        out['added_today'] = {'ebay_sales': r['e_today'],
                              'market_sales': r['m_today']}
        out['max_sale_date'] = {'ebay_sales': str(r['e_maxsale']),
                                'market_sales': str(r['m_maxsale'])}
        out['days_since_ingest'] = {'ebay_sales': d['e_d'],
                                    'market_sales': d['m_d']}
        out['graded_share_ebay'] = round(100.0 * r['e_graded'] / r['e_rows'], 2) \
            if r['e_rows'] else None
        if not args.json:
            say(f'\n1. ROW COUNTS')
            say(f'   {"feed":<16s} {"rows":>10s} {"added today":>12s} '
                f'{"max sale_date":>14s} {"days since ingest":>18s}')
            say(f'   {"ebay_sales":<16s} {r["e_rows"]:>10,} {r["e_today"]:>12,} '
                f'{str(r["e_maxsale"]):>14s} {d["e_d"]:>18,}')
            say(f'   {"market_sales":<16s} {r["m_rows"]:>10,} {r["m_today"]:>12,} '
                f'{str(r["m_maxsale"]):>14s} {d["m_d"]:>18,}')
            say(f'   {"TOTAL":<16s} {total:>10,}')
            say(f'   source split: ebay {pct(r["e_rows"], total)} / '
                f'market {pct(r["m_rows"], total)}')
            say(f'\n2. FEED FRESHNESS')
            for nm, dd, mx in (('ebay_sales', d['e_d'], r['e_maxsale']),
                               ('market_sales', d['m_d'], r['m_maxsale'])):
                state = 'ACTIVE' if dd is not None and dd <= 1 else \
                        f'DARK for {dd} days' if dd is not None else 'UNKNOWN'
                say(f'   {nm:<16s} last ingest {dd:>4} day(s) ago   '
                    f'latest sale {mx}   → {state}')
            say(f'\n3. GRADED SHARE (ebay_sales)')
            say(f'   {r["e_graded"]:,} of {r["e_rows"]:,} = '
                f'{pct(r["e_graded"], r["e_rows"])}')

        # ---------- 2. cells: depth + method mix --------------------------
        cur.execute(f"""
            SELECT {_norm_sql('canonical_title')} AS nc, issue_number AS iss,
                   grade AS g, count(*) AS n
              FROM ebay_sales
             WHERE graded = true AND grade IS NOT NULL AND sale_price > 5
               AND (is_reprint IS NULL OR is_reprint = false)
               AND (is_lot IS NULL OR is_lot = false)
               AND (is_variant IS NULL OR is_variant = false)
               AND coalesce(canonical_title,'') <> ''
               AND COALESCE(sale_date, created_at) > NOW() - INTERVAL '%s days'
               {NOISE}
             GROUP BY 1, 2, 3
        """, [args.days])
        buckets = defaultdict(dict)
        for x in cur.fetchall():
            buckets[(x['nc'], x['iss'])][float(x['g'])] = x['n']
        cur.execute(f"""
            SELECT DISTINCT {_norm_sql('canonical_title')} AS nc,
                   issue_number AS iss
              FROM ebay_sales
             WHERE (graded = false OR graded IS NULL) AND sale_price > 2
               AND (is_reprint IS NULL OR is_reprint = false)
               AND (is_lot IS NULL OR is_lot = false)
               AND coalesce(canonical_title,'') <> ''
               AND COALESCE(sale_date, created_at) > NOW() - INTERVAL '%s days'
               {NOISE}
        """, [args.days])
        raw_keys = {(x['nc'], x['iss']) for x in cur.fetchall()}

        depth = Counter()
        for k, b in buckets.items():
            for g, n in b.items():
                lab = '1' if n == 1 else '2-4' if n <= 4 else '5-9' if n <= 9 else '10+'
                depth[lab] += 1
        dtot = sum(depth.values())
        out['depth_graded_cells'] = {k: depth[k] for k in ('1', '2-4', '5-9', '10+')}
        out['depth_total_cells'] = dtot

        mix = Counter()
        for k in set(list(buckets.keys()) + list(raw_keys)):
            b = buckets.get(k, {})
            has_raw = k in raw_keys
            for g in LADDER:
                mix[classify(b, g, has_raw)] += 1
        mtot = sum(mix.values())
        out['method_mix'] = dict(mix)
        out['method_mix_total'] = mtot

        if not args.json:
            say(f'\n4. DEPTH DISTRIBUTION — populated graded cells '
                f'(canonical_title, issue, grade), {args.days}d')
            say(f'   {"comps":<8s} {"cells":>9s} {"share":>8s}')
            for lab in ('1', '2-4', '5-9', '10+'):
                say(f'   {lab:<8s} {depth[lab]:>9,} {pct(depth[lab], dtot):>8s}')
            say(f'   {"TOTAL":<8s} {dtot:>9,}')
            say(f'\n5. METHOD MIX — every (title, issue) x the 20-grade ladder')
            say('   Mirrors shipped tiering incl. Unit 3 MIN_SOURCE_COMPS=2.')
            say(f'   {"tier":<20s} {"cells":>10s} {"share":>8s}  {"verdict":<8s}')
            for t in ('exact', 'blended', 'exact_thin', 'interpolated',
                      'low_support', 'estimated_from_raw', 'fabricated'):
                v = 'SHOWN' if t == 'exact' else 'hedged'
                say(f'   {t:<20s} {mix[t]:>10,} {pct(mix[t], mtot):>8s}  {v:<8s}')
            say(f'   {"TOTAL":<20s} {mtot:>10,}')
            say(f'   verdict shown on {pct(mix["exact"], mtot)} of cells; '
                f'the rest are hedged by design.')

        # ---------- 3. §2A starved keys -----------------------------------
        rows = []
        for title, issue in STARVED:
            cur.execute(f"""
                SELECT count(*) AS comps,
                       count(*) FILTER (WHERE graded) AS graded
                  FROM ebay_sales
                 WHERE {_norm_sql('canonical_title')} = %s AND issue_number = %s
                   AND sale_price > 2
                   AND (is_reprint IS NULL OR is_reprint = false)
                   AND (is_lot IS NULL OR is_lot = false)
                   AND COALESCE(sale_date, created_at) > NOW() - INTERVAL '%s days'
                   {NOISE}
            """, [_norm(title), issue, args.days])
            x = cur.fetchone()
            cleared = x['comps'] >= TARGET_COMPS and x['graded'] >= TARGET_GRADED
            rows.append({'title': title, 'issue': issue, 'comps': x['comps'],
                         'graded': x['graded'], 'cleared': cleared})
        out['starved_keys'] = rows
        out['starved_cleared'] = sum(1 for x in rows if x['cleared'])
        if not args.json:
            say(f'\n6. §2A STARVED KEYS — target >={TARGET_COMPS} comps AND '
                f'>={TARGET_GRADED} graded ({args.days}d)')
            say(f'   {"key":<30s} {"comps":>7s} {"graded":>7s}  status')
            for x in rows:
                need = []
                if x['comps'] < TARGET_COMPS:
                    need.append(f'+{TARGET_COMPS - x["comps"]} comps')
                if x['graded'] < TARGET_GRADED:
                    need.append(f'+{TARGET_GRADED - x["graded"]} graded')
                status = '✅ CLEARED — retire from block' if x['cleared'] \
                    else 'needs ' + ', '.join(need)
                say(f'   {x["title"] + " #" + x["issue"]:<30s} '
                    f'{x["comps"]:>7,} {x["graded"]:>7,}  {status}')
            say(f'\n   {out["starved_cleared"]} of {len(rows)} cleared.')
            say(f'\n{BAR}')
            say('Read-only. No rows written, no schema touched.')
            say(BAR)
    finally:
        cur.close()
        conn.close()
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
