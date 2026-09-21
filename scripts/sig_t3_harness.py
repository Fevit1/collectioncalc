"""Signature matcher EXTERNAL TEST — measurement unit part (3). REPORT ONLY.

Sample: scripts/sig_t3_sample_2026-09-21.json — signed CGC/CBCS eBay rows from the HELD-OUT fold
(ebay_sales.id % 5 == 0; the priors never saw them), R2 image present, exactly one in-set creator
named beside a signing cue in the title ("SS Frank Miller", "signed by ..."), capped at six rows a
signer, plus the few rows whose title says "signed by <Name>" for a name NOT in the set.
Images come from OUR R2 copy only — no request to eBay of any kind.

The request is the DEPLOYED ROUTE's request: production prefilter_candidates (Design A pool from the
row's publisher / era / title), production fetch_reference_images, production
build_identification_messages and system prompt (version 2), same model, same max_tokens. The
response is parsed by production run_single_pass (fed through a stub client) and decided by
production aggregate_passes + passes_floor_rule. ONE pass per row.

TWO THINGS DIFFER FROM A USER'S CLICK, both stated in the report:
  * The listing photo is a whole slab, and a CGC Signature Series label PRINTS the signer's name.
    The top 15% of every image is cropped off so the matcher reads the signature, not the label.
    Rows where the model still mentions a label are flagged.
  * It is sent through the Message Batches API (same request, asynchronous, half price). Design A
    pools depend on the title, so 87 rows make 56 distinct pools and prompt caching saves little;
    synchronous would be ~$19. Any cache_control the working tree adds is stripped — the deployed
    route has none.
READ-ONLY database.
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
os.environ['DATABASE_URL'] = os.environ['DATABASE_URL_RO']   # this process only
os.environ['SIG_PROMPT_VERSION'] = '2'

import logging
logging.basicConfig(level=logging.WARNING)
import anthropic
import requests
from PIL import Image

import routes.signature_orchestrator as so

SAMPLE = os.path.join(ROOT, 'scripts', 'sig_t3_sample_2026-09-21.json')
STATE = os.path.join(ROOT, 'scripts', 'sig_t3_state_2026-09-21.json')
OUT = os.path.join(ROOT, 'scripts', 'sig_t3_results_2026-09-21.jsonl')
CROP_TOP = 0.15
BATCH_PRICE = {'in': 2.50, 'out': 12.50}          # $/MTok — Opus 4.8 at the 50% batch rate
MAX_BATCH_BYTES = 200 * 1024 * 1024                # the API's cap is 256 MB a batch

_img_cache = {}
_orig_fetch = so._fetch_and_encode_image


def _cached_fetch(url):
    if url not in _img_cache:
        _img_cache[url] = _orig_fetch(url)
    return _img_cache[url]


so._fetch_and_encode_image = _cached_fetch          # same function, remembered per URL


def era(y):
    if not y:
        return 'unknown'
    y = int(y)
    return 'pre-1970' if y < 1970 else f"{y // 10 * 10}s"


def target_b64(url):
    raw = requests.get(url, timeout=30).content
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    w, h = im.size
    im = im.crop((0, int(h * CROP_TOP), w, h))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=92)
    return base64.b64encode(buf.getvalue()).decode(), im.size


def build(row, system_prompt, with_images=True):
    ctx = {'publisher': row['publisher'] or 'unknown', 'era_decade': era(row['year']),
           'title': row['canonical_title'] or 'unknown', 'signature_location': 'cover', 'slab_label': 'unknown'}
    cands = so.prefilter_candidates(era_decade=ctx['era_decade'], publisher=ctx['publisher'],
                                    signature_location='cover', title=row['canonical_title'])
    if with_images:
        cands = so.fetch_reference_images(cands)
    return ctx, cands


def strip_cache(messages):
    for blk in messages[0]['content']:
        blk.pop('cache_control', None)
    return messages


def cmd_submit(args):
    rows = json.load(open(SAMPLE, encoding='utf-8'))[:args.n]
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'], max_retries=3, timeout=1800.0)
    system_prompt = so.load_system_prompt()
    state = json.load(open(STATE, encoding='utf-8')) if os.path.exists(STATE) else {'batches': [], 'rows': {}}
    pending, size = [], 0

    def flush():
        nonlocal pending, size
        if not pending:
            return
        b = client.messages.batches.create(requests=pending)
        state['batches'].append(b.id)
        json.dump(state, open(STATE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"submitted batch {b.id}: {len(pending)} requests, {size / 1e6:.0f} MB")
        pending, size = [], 0

    counted = []
    for i, row in enumerate(rows):
        cid = f"row{row['id']}"
        if cid in state['rows']:
            continue
        ctx, cands = build(row, system_prompt)
        tb64, tsize = target_b64(row['url'])
        _, messages = so.build_identification_messages(tb64, cands, ctx, system_prompt)
        strip_cache(messages)
        params = {'model': so.OPUS_MODEL, 'max_tokens': 1500, 'system': system_prompt, 'messages': messages}
        if args.dry:
            if i < args.dry:
                n = client.messages.count_tokens(model=so.OPUS_MODEL, system=system_prompt, messages=messages).input_tokens
                counted.append(n)
                print(f"[{i}] {row['truth']!r} pool {len(cands)} target {tsize} -> {n} input tokens, "
                      f"{len(json.dumps(params)) / 1e6:.1f} MB")
                continue
            break
        nbytes = len(json.dumps(params))
        if pending and size + nbytes > MAX_BATCH_BYTES:
            flush()
        pending.append({'custom_id': cid, 'params': params})
        size += nbytes
        state['rows'][cid] = {'ctx': ctx, 'pool': [c.name for c in cands], 'target_size': tsize}
        print(f"[{i + 1}/{len(rows)}] queued {cid} {row['truth']!r} ({nbytes / 1e6:.1f} MB)")
    if args.dry and counted:
        avg = sum(counted) / len(counted)
        for n in (60, 70, 75, 80, 87):
            est = n * (avg * BATCH_PRICE['in'] + 1067 * BATCH_PRICE['out']) / 1e6
            worst = n * (max(counted) * BATCH_PRICE['in'] + 1500 * BATCH_PRICE['out']) / 1e6
            print(f"  N={n}: est ${est:.2f}  worst case ${worst:.2f}   (avg input {avg:.0f}, max {max(counted)})")
        return
    flush()
    print('all submitted:', state['batches'])


class _Stub:
    """Hands run_single_pass the batch's Message, so production parsing is what reads it."""
    def __init__(self, message):
        self._m = message
        self.messages = self

    def create(self, **kw):
        return self._m


def cmd_collect(args):
    state = json.load(open(STATE, encoding='utf-8'))
    rows = {f"row{r['id']}": r for r in json.load(open(SAMPLE, encoding='utf-8'))}
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
    system_prompt = so.load_system_prompt()
    done = set()
    if os.path.exists(OUT):
        done = {json.loads(l)['custom_id'] for l in open(OUT, encoding='utf-8')}
    while True:
        status = {b: client.messages.batches.retrieve(b).processing_status for b in state['batches']}
        print(time.strftime('%H:%M:%S'), status)
        if all(s == 'ended' for s in status.values()) or args.once:
            break
        time.sleep(60)
    with open(OUT, 'a', encoding='utf-8') as out:
        for b, s in status.items():
            if s != 'ended':
                continue
            for res in client.messages.batches.results(b):
                cid = res.custom_id
                if cid in done:
                    continue
                row, meta = rows[cid], state['rows'][cid]
                rec = {'custom_id': cid, 'id': row['id'], 'truth': row['truth'], 'kind': row['kind'],
                       'raw_title': row['raw_title'], 'pool': meta['pool'], 'truth_in_pool': row['truth'] in meta['pool'],
                       'result_type': res.result.type}
                if res.result.type == 'succeeded':
                    msg = res.result.message
                    u = msg.usage
                    rec['usage'] = {'in': u.input_tokens, 'out': u.output_tokens}
                    cands = [so.CreatorCandidate(creator_id=i, name=n, era_start=None, era_end=None,
                                                 publisher_affiliations=[], signature_style=None,
                                                 reference_images_b64=[]) for i, n in enumerate(meta['pool'])]
                    p = so.run_single_pass(0.2, '', cands, meta['ctx'], system_prompt, _Stub(msg))
                    if p.rankings:
                        agg = so.aggregate_passes([p], passes_attempted=1)
                        top = agg.top5[0]
                        rec.update({'top1': top['creator'], 'score': top['confidence'], 'margin': agg.margin,
                                    'none_of_these': agg.none_of_these, 'suggested': agg.suggested_outside_pool,
                                    'top5': [(x['creator'], x['confidence']) for x in agg.top5],
                                    'named': so.passes_floor_rule(top['confidence'], agg.margin, agg.none_of_these),
                                    'flags': {k: v for k, v in agg.flags.items() if k != 'usage'}})
                    else:
                        rec['error'] = f'unparsed: {p.flags}'
                else:
                    rec['error'] = str(getattr(res.result, 'error', res.result.type))
                out.write(json.dumps(rec, ensure_ascii=False) + '\n')
                done.add(cid)
    print('collected', len(done))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('submit'); s.add_argument('--n', type=int, default=87); s.add_argument('--dry', type=int, default=0)
    c = sub.add_parser('collect'); c.add_argument('--once', action='store_true')
    a = ap.parse_args()
    (cmd_submit if a.cmd == 'submit' else cmd_collect)(a)
