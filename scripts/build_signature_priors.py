"""Build signature_priors.json — who actually signs books, from our own corpus.

READ-ONLY against the database (uses DATABASE_URL_RO when set). Writes ONE file:
<repo>/signature_priors.json, which routes/signature_orchestrator.py reads at
import to order the candidate pool (Design A, 2026-09-19). Re-run by hand when the
corpus or the creator list has moved; commit the JSON; `deploy`.

A LABELLED ROW is an ebay_sales row whose raw_title has CGC/CBCS, a signed marker,
and names EXACTLY ONE creator from creator_signatures by full name. The label is a
proxy: a named creator is not always the signer ("McFarlane cover, signed by Stan
Lee" names two and is dropped; a lone cover-artist credit on a signed book is kept
and is wrong). Good enough for a base rate, not for ground truth.

THE SPLIT — so the external test (3) never scores the prior on its own data:
    TEST FOLD  = labelled rows with ebay_sales.id % 5 == 0   (held out; ~20%)
    PRIOR FOLD = every other labelled row                     (~80%)
Priors are counted from the PRIOR FOLD only. The (3) sample is drawn from the TEST
FOLD only. The rule is on the row id, so it is stable across rebuilds and a row
never changes sides. Known leak, accepted: a relisted copy of the same book can
land on both sides under two ids.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

TEST_MOD = 5          # id % TEST_MOD == 0  -> test fold
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'signature_priors.json')


def title_key(title):
    """Same normalisation as routes/signature_orchestrator._prior_title_key."""
    t = (title or '').lower().strip()
    t = re.sub(r'^the\s+', '', t)
    t = re.sub(r'[^a-z0-9]+', ' ', t)
    return t.strip()


def main():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    url = os.environ.get('DATABASE_URL_RO') or os.environ.get('DATABASE_URL')
    if not url:
        sys.exit('DATABASE_URL_RO / DATABASE_URL not set')

    conn = psycopg2.connect(url, connect_timeout=15)
    try:
        conn.set_session(readonly=True)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SET statement_timeout = 120000")
        cur.execute("SELECT creator_name FROM creator_signatures WHERE active")
        names = [r['creator_name'] for r in cur.fetchall()]
        cur.execute(r"""
            SELECT id, raw_title, canonical_title
            FROM ebay_sales
            WHERE raw_title ~* '\y(cgc|cbcs)\y'
              AND raw_title ~* '(signature series|\yss\y|signed|autograph)'
        """)
        rows = cur.fetchall()
    finally:
        conn.close()

    lowered = [(n, n.lower()) for n in names]
    global_prior = Counter()
    by_title = defaultdict(Counter)
    n_labelled = n_test = n_prior = 0
    for r in rows:
        t = (r['raw_title'] or '').lower()
        hits = [n for n, low in lowered if low in t]
        if len(hits) != 1:
            continue
        n_labelled += 1
        if r['id'] % TEST_MOD == 0:
            n_test += 1
            continue
        n_prior += 1
        global_prior[hits[0]] += 1
        k = title_key(r['canonical_title'])
        if k:
            by_title[k][hits[0]] += 1

    out = {
        'meta': {
            'built_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'source': "ebay_sales: CGC/CBCS + signed marker + exactly one in-set creator named",
            'split': f'test fold = id % {TEST_MOD} == 0 (held out of these counts); prior fold = the rest',
            'signed_slab_rows': len(rows),
            'labelled_rows': n_labelled,
            'prior_fold_rows': n_prior,
            'test_fold_rows': n_test,
            'creators_with_prior': len(global_prior),
            'titles_with_prior': len(by_title),
        },
        'global': dict(global_prior.most_common()),
        'by_title': {k: dict(v.most_common()) for k, v in sorted(by_title.items())},
    }
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write('\n')
    print(json.dumps(out['meta'], indent=1))
    print('top 10:', global_prior.most_common(10))
    print('wrote', OUT)


if __name__ == '__main__':
    main()
