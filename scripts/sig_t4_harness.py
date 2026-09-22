"""Signature matcher — the IMAGE LEVER and ONE-PASS vs THREE-PASS. REPORT ONLY (2026-09-22).

Same split as (2) (scripts/sig_cv_harness.py): creators with >= 3 reference images, each creator's LAST
image held out, the rest (<= 4) as references, creators sorted by career_start into fixed pools of 14.
Pools 0, 1 and 2 are used here (42 creators) so there are three cache writes, not seven. Production
functions throughout: fetch_reference_images, run_single_pass (build_identification_messages inside it),
aggregate_passes, passes_floor_rule, load_system_prompt. Prompt v2.

ARM 1 — the image lever. Every held-out signature is sent twice, one pass each:
    full   = the reference image as stored (long edge 58-1834 px, median ~875);
    thumb  = the same image downscaled so its long edge is THUMB_PX (80) — the size a signature has on a
             375 x 500 eBay listing thumbnail, which is what (3) was scored on.
ARM 2 — one pass vs three. Two MORE full-resolution passes per creator (labels 0.5 and 0.7); with arm 1's
    full pass (label 0.2) that is three, aggregated by production aggregate_passes exactly as the route
    does. Reported: top-1 agreement between the single pass and the three-pass aggregate, and the
    floor-rule outcome under each.

Resumable per (creator, arm, label). Cost from response.usage. Stops at --ceiling on projection.
"""
import argparse
import base64
import io
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
os.environ['DATABASE_URL'] = os.environ['DATABASE_URL_RO']
os.environ['SIG_PROMPT_VERSION'] = '2'

import logging
logging.basicConfig(level=logging.WARNING)
import anthropic
import psycopg2
import psycopg2.extras
from PIL import Image

import routes.signature_orchestrator as so

PRICE = {'in': 5.00, 'cache_write': 6.25, 'cache_read': 0.50, 'out': 25.00}
POOL_SIZE = 14
THUMB_PX = 80
TARGET_MARKER = "--- TARGET SIGNATURE (unknown) ---"


def cost(u):
    return (u['in'] * PRICE['in'] + u['cache_write'] * PRICE['cache_write']
            + u['cache_read'] * PRICE['cache_read'] + u['out'] * PRICE['out']) / 1e6


class _Messages:
    def __init__(self, inner, sink):
        self._inner, self._sink = inner, sink

    def create(self, **kw):
        content = kw['messages'][0]['content']
        idx = next(i for i, b in enumerate(content) if b.get('type') == 'text' and TARGET_MARKER in b.get('text', ''))
        content[idx - 1] = dict(content[idx - 1], cache_control={'type': 'ephemeral'})
        resp = self._inner.create(**kw)
        u = resp.usage
        self._sink.append({'in': u.input_tokens, 'cache_write': getattr(u, 'cache_creation_input_tokens', 0) or 0,
                           'cache_read': getattr(u, 'cache_read_input_tokens', 0) or 0, 'out': u.output_tokens})
        return resp


class UsageClient:
    def __init__(self, inner):
        self.usage = []
        self.messages = _Messages(inner.messages, self.usage)


def load_creators():
    conn = psycopg2.connect(os.environ['DATABASE_URL_RO'], connect_timeout=15)
    try:
        conn.set_session(readonly=True)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT cs.id AS creator_id, cs.creator_name, cs.career_start, cs.career_end, cs.publisher_affiliations,
                   cs.signature_style, COALESCE(cs.style_confidence, 0.5) AS style_confidence,
                   COALESCE(cs.style_source, 'ai_assigned') AS style_source,
                   array_agg(si.image_url ORDER BY si.sort_order NULLS LAST, si.created_at DESC) AS urls
            FROM creator_signatures cs JOIN signature_images si ON si.creator_id = cs.id
            WHERE cs.active = true GROUP BY cs.id HAVING COUNT(si.id) >= 3
            ORDER BY cs.career_start NULLS LAST, cs.id""")
        return cur.fetchall()
    finally:
        conn.close()


def downscale(b64, long_edge):
    im = Image.open(io.BytesIO(base64.b64decode(b64))).convert('RGB')
    w, h = im.size
    s = long_edge / max(w, h)
    im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=85)
    return base64.b64encode(buf.getvalue()).decode(), im.size


def score(p, truth):
    agg = so.aggregate_passes([p] if not isinstance(p, list) else p, passes_attempted=1 if not isinstance(p, list) else len(p))
    top = agg.top5[0] if agg.top5 else None
    return {'top1': top and top['creator'], 'score': top and top['confidence'], 'margin': agg.margin,
            'none_of_these': agg.none_of_these, 'suggested': agg.suggested_outside_pool,
            'correct': bool(top and top['creator'] == truth),
            'named': bool(top and so.passes_floor_rule(top['confidence'], agg.margin, agg.none_of_these)),
            'top5': [(x['creator'], x['confidence']) for x in agg.top5]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', choices=['image', 'passes'], required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--pools', default='0,1,2')
    ap.add_argument('--ceiling', type=float, required=True)
    args = ap.parse_args()
    want = {int(x) for x in args.pools.split(',')}

    rows = load_creators()
    pools = [rows[i:i + POOL_SIZE] for i in range(0, len(rows), POOL_SIZE)]
    pools = [p for i, p in enumerate(pools) if i in want]
    n_creators = sum(len(p) for p in pools)
    per = 2 if args.arm == 'image' else 2
    n_calls = n_creators * per
    print(f"arm {args.arm}: {len(pools)} pools, {n_creators} creators, {n_calls} calls")

    done = {}
    if os.path.exists(args.out):
        for l in open(args.out, encoding='utf-8'):
            r = json.loads(l)
            done[(r['truth'], r['arm'], r['label'])] = r
    client = UsageClient(anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'], max_retries=4))
    system_prompt = so.load_system_prompt()
    ctx = {'publisher': 'unknown', 'era_decade': 'unknown', 'title': 'unknown', 'signature_location': 'unknown', 'slab_label': 'unknown'}
    spent = 0.0
    n = 0
    with open(args.out, 'a', encoding='utf-8') as out:
        for pi, pool in enumerate(pools):
            cands, held = [], {}
            for r in pool:
                urls = [u for u in r['urls'] if u]
                held[r['creator_name']] = urls[-1]
                cands.append(so.CreatorCandidate(
                    creator_id=r['creator_id'], name=r['creator_name'], era_start=r['career_start'], era_end=r['career_end'],
                    publisher_affiliations=r['publisher_affiliations'] or [], signature_style=r['signature_style'],
                    style_confidence=r['style_confidence'], style_source=r['style_source'],
                    image_urls=urls[:-1][:so.REFERENCE_IMAGES_PER_CREATOR]))
            cands = so.fetch_reference_images(cands)
            names = [c.name for c in cands]
            for truth in names:
                full = so._fetch_and_encode_image(held[truth])
                if not full:
                    continue
                jobs = ([('full', 0.2, full, None), ('thumb', 0.2, None, THUMB_PX)] if args.arm == 'image'
                        else [('full', 0.5, full, None), ('full', 0.7, full, None)])
                for arm, label, img, px in jobs:
                    if (truth, arm, label) in done:
                        continue
                    size = None
                    if px:
                        img, size = downscale(full, px)
                    before = len(client.usage)
                    t0 = time.time()
                    p = so.run_single_pass(label, img, cands, ctx, system_prompt, client)
                    rec = {'pool': pi, 'truth': truth, 'arm': arm, 'label': label, 'thumb_size': size,
                           'seconds': round(time.time() - t0, 1), 'usage': client.usage[before:] or None,
                           'rankings': p.rankings, 'none_of_these': p.none_of_these, 'suggested': p.suggested_outside_pool,
                           'flags': p.flags}
                    if p.rankings:
                        rec.update(score(p, truth))
                    else:
                        rec['error'] = str(p.flags)
                    out.write(json.dumps(rec, ensure_ascii=False) + '\n')
                    out.flush()
                    n += 1
                    spent = sum(cost(u) for u in client.usage)
                    print(f"[{n}] pool {pi} {truth!r} {arm} {label} -> {rec.get('top1')!r} {rec.get('score')} "
                          f"{'OK' if rec.get('correct') else 'x'} {'NAMED' if rec.get('named') else ''} ${spent:.3f}")
                    if n == 6:
                        reads = [u for u in client.usage if u['cache_read'] > 0] or client.usage
                        per_read = sum(cost(u) for u in reads) / len(reads)
                        proj = per_read * n_calls + 0.09 * len(pools)
                        print(f"RE-BASE after {n}: per cached call ${per_read:.4f}; projected ${proj:.2f}; ceiling ${args.ceiling:.2f}")
                        if proj > args.ceiling:
                            print('STOP: projection over the ceiling')
                            return
    print(f"DONE {n} calls ${spent:.3f}")


if __name__ == '__main__':
    main()
