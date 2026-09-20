"""Signature matcher cross-validation — measurement unit part (2). REPORT ONLY.

Calls the PRODUCTION functions in routes/signature_orchestrator.py —
build_identification_messages (via run_single_pass), run_single_pass,
aggregate_passes, _fetch_and_encode_image, load_system_prompt — never a copy.
The harness supplies only what the route cannot: a candidate list with the
held-out image removed, and a client wrapper that (a) marks the end of the
reference block as a prompt-cache breakpoint and (b) keeps response.usage, which
the route throws away.

THE SPLIT
    Eligible creators: active, >= 3 reference images (so >= 2 remain after the
    hold-out — the matcher's own floor).
    HELD OUT  = each creator's LAST image by (sort_order NULLS LAST, created_at DESC)
                — the same order the route uses to pick references.
    REFERENCE = the creator's remaining images, first four at most.
    One query per creator. ONE pass per query (the three-temperature ensemble no
    longer exists on Opus 4.8; three passes are three identical samples).
POOLS
    Creators sorted by career_start, cut into fixed pools of ~14. Every query in a
    pool sees the SAME candidates in the SAME order, so the reference prefix is
    byte-identical and caches; the true signer is always in the pool.
WHAT THIS MEASURES — and does not
    Discrimination among ~14 candidates with the signer guaranteed present, on a
    clean reference-style crop with no comic context. It is an UPPER bound on the
    route: no pool miss, no cover photo, no second signature. Pool recall is
    measured separately (free, SQL).

READ-ONLY database. Spend: Anthropic API, Opus 4.8. Re-bases its estimate after
REBASE_AFTER calls and stops if the projection passes --ceiling.
"""
import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, '.env'))
os.environ['DATABASE_URL'] = os.environ['DATABASE_URL_RO']   # this process only

import logging
logging.basicConfig(level=logging.WARNING)
import anthropic
import psycopg2
import psycopg2.extras

import routes.signature_orchestrator as so

PRICE = {'in': 5.00, 'cache_write': 6.25, 'cache_read': 0.50, 'out': 25.00}   # $/MTok, Opus 4.8
POOL_SIZE = 14
REBASE_AFTER = 5
TARGET_MARKER = "--- TARGET SIGNATURE (unknown) ---"


def cost(u):
    return (u['in'] * PRICE['in'] + u['cache_write'] * PRICE['cache_write']
            + u['cache_read'] * PRICE['cache_read'] + u['out'] * PRICE['out']) / 1e6


class _Messages:
    def __init__(self, inner, sink):
        self._inner, self._sink = inner, sink

    def create(self, **kw):
        # Breakpoint on the last block BEFORE the target marker: system + every
        # reference is the shared prefix; the target image is the only thing that varies.
        content = kw['messages'][0]['content']
        idx = next(i for i, b in enumerate(content)
                   if b.get('type') == 'text' and TARGET_MARKER in b.get('text', ''))
        content[idx - 1] = dict(content[idx - 1], cache_control={'type': 'ephemeral'})
        resp = self._inner.create(**kw)
        u = resp.usage
        self._sink.append({'in': u.input_tokens,
                           'cache_write': getattr(u, 'cache_creation_input_tokens', 0) or 0,
                           'cache_read': getattr(u, 'cache_read_input_tokens', 0) or 0,
                           'out': u.output_tokens, 'stop': resp.stop_reason})
        return resp


class UsageClient:
    """Looks like anthropic.Anthropic to run_single_pass; records usage per call."""
    def __init__(self, inner):
        self.usage = []
        self.messages = _Messages(inner.messages, self.usage)


def load_creators():
    conn = psycopg2.connect(os.environ['DATABASE_URL_RO'], connect_timeout=15)
    try:
        conn.set_session(readonly=True)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT cs.id AS creator_id, cs.creator_name, cs.career_start, cs.career_end,
                   cs.publisher_affiliations, cs.signature_style,
                   COALESCE(cs.style_confidence, 0.5) AS style_confidence,
                   COALESCE(cs.style_source, 'ai_assigned') AS style_source,
                   array_agg(si.image_url ORDER BY si.sort_order NULLS LAST, si.created_at DESC) AS urls
            FROM creator_signatures cs JOIN signature_images si ON si.creator_id = cs.id
            WHERE cs.active = true
            GROUP BY cs.id HAVING COUNT(si.id) >= 3
            ORDER BY cs.career_start NULLS LAST, cs.id
        """)
        return cur.fetchall()
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--ceiling', type=float, default=7.00, help='stop if the projected total passes this')
    ap.add_argument('--limit', type=int, default=0, help='run only the first N queries (smoke test)')
    args = ap.parse_args()

    rows = load_creators()
    pools = [rows[i:i + POOL_SIZE] for i in range(0, len(rows), POOL_SIZE)]
    if len(pools) > 1 and len(pools[-1]) < 8:            # no runt pool: fold it into the one before
        pools[-2].extend(pools.pop())
    n_queries = sum(len(p) for p in pools)
    print(f"{len(rows)} creators, {len(pools)} pools {[len(p) for p in pools]}, {n_queries} queries, 1 pass each")

    client = UsageClient(anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'], max_retries=4))
    system_prompt = so.load_system_prompt()
    ctx = {'publisher': 'unknown', 'era_decade': 'unknown', 'title': 'unknown',
           'signature_location': 'unknown', 'slab_label': 'unknown'}

    # RESUME: a truth already in the out file (without an error) is never re-run or re-paid.
    already = set()
    if os.path.exists(args.out):
        for line in open(args.out, encoding='utf-8'):
            try:
                r = json.loads(line)
                if 'error' not in r:
                    already.add(r['truth'])
            except ValueError:
                pass
    if already:
        print(f"resuming: {len(already)} queries already recorded, skipped")
    spent = 0.0
    done = 0
    with open(args.out, 'a', encoding='utf-8') as out:
        for pi, pool in enumerate(pools):
            cands, held = [], {}
            for r in pool:
                urls = [u for u in r['urls'] if u]
                held[r['creator_name']] = urls[-1]
                c = so.CreatorCandidate(
                    creator_id=r['creator_id'], name=r['creator_name'], era_start=r['career_start'],
                    era_end=r['career_end'], publisher_affiliations=r['publisher_affiliations'] or [],
                    signature_style=r['signature_style'], style_confidence=r['style_confidence'],
                    style_source=r['style_source'],
                    image_urls=urls[:-1][:so.REFERENCE_IMAGES_PER_CREATOR])
                cands.append(c)
            cands = so.fetch_reference_images(cands)          # production fetch + drop-if-empty
            names = [c.name for c in cands]
            if all(n in already for n in [r['creator_name'] for r in pool]):
                continue
            for truth in names:
                if args.limit and done >= args.limit:
                    break
                if truth in already:
                    continue
                target = so._fetch_and_encode_image(held[truth])
                rec = {'pool': pi, 'truth': truth, 'pool_names': names}
                if not target:
                    rec['error'] = 'held-out image fetch failed'
                else:
                    t0 = time.time()
                    before = len(client.usage)
                    p = so.run_single_pass(0.2, target, cands, ctx, system_prompt, client)
                    rec['seconds'] = round(time.time() - t0, 1)
                    rec['usage'] = client.usage[before:] or None
                    if p.rankings:
                        agg = so.aggregate_passes([p], passes_attempted=1)
                        top = agg.top5[0] if agg.top5 else None
                        rec.update({
                            'top1': top and top['creator'], 'top1_conf': top and top['confidence'],
                            'top5': [(x['creator'], x['confidence']) for x in agg.top5],
                            'correct': bool(top and top['creator'] == truth),
                            'matched': bool(top and top['confidence'] >= so.LOW_CONFIDENCE_THRESHOLD),
                            'truth_rank': next((i + 1 for i, x in enumerate(agg.top5)
                                                if x['creator'] == truth), None),
                        })
                    else:
                        rec['error'] = f'pass failed: {p.flags}'
                    spent = sum(cost(u) for u in client.usage)
                done += 1
                out.write(json.dumps(rec, ensure_ascii=False) + '\n')
                out.flush()
                print(f"[{done}/{n_queries}] pool {pi} {truth!r} -> {rec.get('top1')!r} "
                      f"{rec.get('top1_conf')} {'OK' if rec.get('correct') else 'x'}  ${spent:.3f}")
                if done == REBASE_AFTER:
                    u = client.usage
                    # The first call in a pool pays the cache write; project with writes per pool.
                    reads = [x for x in u if x['cache_read'] > 0] or u
                    per_read = sum(cost(x) for x in reads) / len(reads)
                    write_extra = max((cost(x) for x in u), default=0) - per_read
                    proj = per_read * n_queries + max(write_extra, 0) * len(pools)
                    avg_out = sum(x['out'] for x in u) / len(u)
                    print(f"RE-BASE after {done}: avg output {avg_out:.0f} tok (assumed 1,000); "
                          f"per cached call ${per_read:.4f}; projected total ${proj:.2f} "
                          f"(estimate $5.70, ceiling ${args.ceiling:.2f}); cache_read seen: "
                          f"{sum(1 for x in u if x['cache_read'] > 0)}/{len(u)}")
                    if proj > args.ceiling:
                        print("STOP: projection passes the ceiling. Nothing further runs.")
                        return
            if args.limit and done >= args.limit:
                break
    print(f"DONE {done} queries, ${spent:.3f}, calls {len(client.usage)}")
    tot = {k: sum(u[k] for u in client.usage) for k in ('in', 'cache_write', 'cache_read', 'out')}
    print('usage totals:', tot)


if __name__ == '__main__':
    main()
