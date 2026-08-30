#!/usr/bin/env python3
"""Re-grade comparison harness — the measuring instrument for rubric changes.

Re-grades the FIXED evaluation set (scripts/regrade_eval_set.json, 36 retained
submissions, pre-1970-over-weighted) against a named rubric variant and diffs
the result against baseline: per-book grade deltas, defect-flag base-rate
changes, and grade-distribution shift. This is what makes a rubric change
auditable instead of vibes.

PRODUCTION IS NEVER TOUCHED. Variants are prompt TRANSFORMS applied here, on
top of grading_engine.build_grading_prompt's output — grading_engine.py itself
is not modified, and nothing here writes to the database.

VARIANTS (one variable each, so effects isolate):
  baseline  the exact production prompt, re-run fresh. Run this FIRST in any
            session — it separates model drift from variant effect. Stored
            grades in the manifest are a second, free comparison column.
  A         publication year appended to the comic-identification block.
            Nothing else changes.
  B         era-conditional baseline language: expected condition differs by
            era; tanning on a pre-1975 book reads as normal, not a defect.
  C         brittleness unbundled from paper colour in COLOR_GLOSS; paper
            colour moves to a separate reported page_quality designation
            (report-only here — no schema change, the field is captured into
            the run output).

DRY RUN IS THE DEFAULT: prints set composition + cost estimate and exits.
Nothing calls the API without --run.

SPEND (measured basis, 2026-08-30): ~7,100 input + ~850 output tokens per
4-photo grade at claude-sonnet-4-6 ($3/$15 per MTok) ≈ $0.034/book →
≈ $1.22 per 36-book run. Append the estimate to docs/API_SPEND_LEDGER.md
BEFORE running and correct it after (CLAUDE.md → API Spend Ceiling).

WHERE TO RUN: the Render shell (has ANTHROPIC_API_KEY, R2 creds, DATABASE_URL).
scripts/ ships in the container (docs/ does not — L-SW-2026-023), which is why
the manifest lives in scripts/. The container FS is ephemeral: the JSON run
record is also printed to stdout so a copy survives the shell.

USAGE
    python scripts/regrade_harness.py                       # dry run, baseline
    python scripts/regrade_harness.py --variant A           # dry run, variant A
    python scripts/regrade_harness.py --variant A --run     # spends money
    python scripts/regrade_harness.py --variant A --run --limit 3   # smoke test
    python scripts/regrade_harness.py --report r1.json r2.json      # diff two runs
"""
import argparse
import base64
import collections
import json
import os
import re
import statistics
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')  # L-2026-015

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

MANIFEST = os.path.join(_HERE, 'regrade_eval_set.json')

# Cost basis — measured 2026-08-30 from api_usage (median, 4-photo grades).
COST_IN_PER_MTOK, COST_OUT_PER_MTOK = 3.00, 15.00
EST_IN_TOKENS, EST_OUT_TOKENS = 7100, 850

# Defect themes for base-rate diffing. Word-boundary on 'oils' is load-bearing:
# a bare /oil/ matches 'soiling' (caught 2026-08-30, before it shipped a wrong
# base rate). Keep in sync with any future report using these names.
THEMES = [
    ('oils',            r'\boils?\b'),
    ('tanning/yellow',  r'tann|brown|yellow'),
    ('soiling/dirt',    r'soil|dirt|smudg|grime'),
    ('spine stress',    r'spine (stress|tick)|stress line'),
    ('corner wear',     r'corner'),
    ('crease',          r'creas'),
    ('edge wear',       r'edge'),
    ('fading',          r'fad'),
    ('foxing',          r'foxing'),
    ('staple rust',     r'rust'),
    ('tear',            r'\btear|torn'),
    ('gloss loss',      r'gloss'),
    ('brittle',         r'brittle'),
]

# ── Variant prompt transforms ────────────────────────────────────────────────
# Each takes (prompt_text, year) and returns the transformed prompt. They edit
# the STRING built by production's build_grading_prompt, so baseline is exactly
# what prod sends and each variant differs from it by one variable.

def _variant_baseline(prompt, year):
    return prompt


def _variant_a(prompt, year):
    """A: pass the publication year. Smallest possible change."""
    if year is None:
        return prompt
    return prompt.replace(
        'Publisher: ',
        f'Publication year: {year}\nPublisher: ', 1)


_ERA_BASELINE_BLOCK = """
ERA CONTEXT — read before scoring:
This comic was published in {year}. Judge each category against a WELL-PRESERVED
copy OF ITS ERA, not against a modern printing:
- Pre-1975 newsprint naturally tones to cream or tan with age. Cream-to-tan
  pages on a pre-1975 book are NORMAL, not a defect; score paper colour as a
  defect only when it is markedly worse than typical for the era (heavy
  browning, staining) or the paper is brittle.
- 1975-1990 paper stock tones more slowly; light tanning is common and minor.
- Post-2000 books are printed on coated stock: tanning, foxing, or yellowing
  on these IS a genuine defect at full weight.
Structural damage, creases, tears, spine stress and staple problems are
defects in EVERY era — era context never excuses handling damage.
"""


def _variant_b(prompt, year):
    """B: era-conditional baseline expectations."""
    if year is None:
        return prompt
    block = _ERA_BASELINE_BLOCK.format(year=year)
    return prompt.replace('SCORING INSTRUCTIONS:', block + '\nSCORING INSTRUCTIONS:', 1)


_C_OLD_BLOCK = """6. COLOR_GLOSS (10% of grade): Paper and printing quality
   - Paper quality (white, cream, tan, brown)
   - Gloss/sheen remaining on cover
   - Ink coverage intact
   - Yellowing/tanning/brittleness
   Score: ___"""

_C_NEW_BLOCK = """6. COLOR_GLOSS (10% of grade): Printing and structural paper quality
   - Gloss/sheen remaining on cover
   - Ink coverage intact
   - Brittleness or flaking of the paper (structural aging)
   - Do NOT deduct for paper COLOUR (white/cream/tan) — report that separately
     as page_quality below
   Score: ___"""


def _variant_c(prompt, year):
    """C: unbundle brittleness (grade-relevant) from paper colour
    (designation-only). Adds a page_quality field to the response."""
    if _C_OLD_BLOCK not in prompt:
        raise RuntimeError('Variant C anchor text not found — grading_engine prompt '
                           'has changed; re-derive _C_OLD_BLOCK before trusting this run.')
    out = prompt.replace(_C_OLD_BLOCK, _C_NEW_BLOCK, 1)
    out = out.replace(
        '"signature_detected": false,',
        '"page_quality": "one of: White | Off-white | Off-white to white | Cream | '
        'Tan | Brittle",\n  "signature_detected": false,', 1)
    return out


VARIANTS = {'baseline': _variant_baseline, 'A': _variant_a,
            'B': _variant_b, 'C': _variant_c}


# ── Data access ──────────────────────────────────────────────────────────────

def load_manifest():
    with open(MANIFEST, encoding='utf-8') as f:
        return json.load(f)


def fetch_submissions(ids):
    import psycopg2
    from psycopg2.extras import RealDictCursor
    url = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_URL_RO')
    if not url:
        sys.exit('DATABASE_URL not set — run in the Render shell.')
    conn = psycopg2.connect(url)
    conn.set_session(readonly=True)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""SELECT id, title, issue, year, publisher, grade, category_scores,
                          defects, photo_labels, photos, model
                   FROM grade_submissions WHERE id = ANY(%s)""", (list(ids),))
    rows = {r['id']: r for r in cur.fetchall()}
    conn.close()
    return rows


_PHOTO_ORDER = ['front_cover', 'spine', 'back_cover', 'centerfold']
_LABEL_FOR = {'front_cover': 'Front Cover', 'spine': 'Spine',
              'back_cover': 'Back Cover', 'centerfold': 'Centerfold'}
# Same env read as routes/grading.py:22 (not imported — that module drags the
# whole Flask app in; the duplication is of an env read, not a value).
GRADING_MAX_LONG_EDGE = int(os.environ.get('GRADING_MAX_LONG_EDGE', '2000'))


def _sniff_media_type(raw: bytes):
    """Magic-byte detection for the FALLBACK path only. Prod never needs this —
    /api/grade re-encodes every image to JPEG via normalize_for_photo_type
    (grading.py:667). Retained photos from before that unit shipped (2026-07-16)
    are original phone bytes and can be PNG/WebP/HEIC — the 2026-08-30 baseline
    run died at id 9 on exactly this (PNG sent as image/jpeg)."""
    if raw[:3] == b'\xff\xd8\xff':
        return 'image/jpeg'
    if raw[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    if raw[:6] in (b'GIF87a', b'GIF89a'):
        return 'image/gif'
    if raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':
        return 'image/webp'
    if raw[4:8] == b'ftyp':
        return 'image/heic'  # Anthropic API does NOT accept this — caller must skip
    return None


def fetch_photos_b64(photos_map):
    """photos_map: label_key -> R2 key. Returns [(label, b64, media_type)] in
    prod's order.

    PRIMARY PATH MATCHES PROD: normalize_for_photo_type re-encodes to upright
    JPEG at GRADING_MAX_LONG_EDGE — the same pixels /api/grade hands the model
    (EXIF fix, HEIC decode, downscale). FALLBACK: if normalization fails, sniff
    the magic bytes and send the original with its true media type; HEIC or
    unidentifiable bytes raise (per-book skip upstream — prod would have 400'd
    the same request, so there is no prod-faithful way to grade that photo)."""
    from r2_storage import get_r2_client, R2_BUCKET_NAME
    from comic_extraction import normalize_for_photo_type
    client = get_r2_client()
    out = []
    for key in _PHOTO_ORDER:
        r2_key = photos_map.get(key)
        if not r2_key:
            continue
        raw = client.get_object(Bucket=R2_BUCKET_NAME, Key=r2_key)['Body'].read()
        b64 = base64.standard_b64encode(raw).decode()
        photo_type = key.split('_')[0] if key != 'centerfold' else 'centerfold'
        try:
            b64 = normalize_for_photo_type(b64, photo_type,
                                           max_long_edge=GRADING_MAX_LONG_EDGE)
            media = 'image/jpeg'  # normalizer always emits JPEG
        except Exception as e:
            media = _sniff_media_type(raw)
            if media in (None, 'image/heic'):
                raise RuntimeError(
                    f'{key} ({r2_key}): normalize failed ({e}) and bytes are '
                    f'{media or "unidentifiable"} — unusable') from e
            print(f'    [warn] {key}: normalize failed ({e}); sending original as {media}')
        out.append((_LABEL_FOR[key], b64, media))
    return out


# ── Grading call (mirrors /api/grade's request shape) ────────────────────────

def regrade_one(client, model, sub, variant_fn):
    from grading_engine import build_grading_prompt, parse_grading_response
    labels = [l for l, _, _ in sub['_photos']]
    prompt = build_grading_prompt(sub['title'], sub['issue'], sub['publisher'], labels)
    prompt = variant_fn(prompt, sub['year'])

    content = []
    for label, b64, media in sub['_photos']:
        content.append({'type': 'text', 'text': f'Photo: {label}'})
        content.append({'type': 'image',
                        'source': {'type': 'base64', 'media_type': media, 'data': b64}})
    content.append({'type': 'text', 'text': prompt})

    resp = client.messages.create(model=model, max_tokens=2000, temperature=0,
                                  messages=[{'role': 'user', 'content': content}])
    text = ''.join(b.text for b in resp.content if b.type == 'text')

    # parse_grading_response runs the FULL production pipeline: parse ->
    # compute_grade (weights, snap, min-category ceiling). Using it whole keeps
    # this harness's math identical to prod's by construction.
    parsed = parse_grading_response(text)
    # Variant C's page_quality is outside the schema grading_engine parses.
    pq = None
    m = re.search(r'"page_quality"\s*:\s*"([^"]+)"', text)
    if m:
        pq = m.group(1)
    return {
        'grade': parsed['final_grade'], 'raw_score': parsed.get('raw_score'),
        'category_scores': parsed['category_scores'],
        'defects': parsed.get('defects', {}),
        'page_quality': pq,
        'usage': {'in': resp.usage.input_tokens, 'out': resp.usage.output_tokens},
    }


# ── Reporting ────────────────────────────────────────────────────────────────

def defect_theme_hits(defects):
    s = ' || '.join(x.lower() for v in (defects or {}).values()
                    if isinstance(v, list) for x in v)
    return {name for name, pat in THEMES if re.search(pat, s)}


def preflight(entries):
    """No API spend: verify every photo of the eval set is fetchable and report
    its actual media type from magic bytes (16-byte Range reads). Run BEFORE a
    paid run so a PNG at book 22 is discovered here, not mid-spend."""
    from r2_storage import get_r2_client, R2_BUCKET_NAME
    client = get_r2_client()
    subs = fetch_submissions([e['id'] for e in entries])
    by_type, problems = collections.Counter(), []
    print(f"{'id':>4}  types")
    for e in entries:
        sub = subs.get(e['id'])
        if not sub:
            problems.append((e['id'], 'row missing from DB'))
            continue
        types = []
        for key in _PHOTO_ORDER:
            r2_key = (sub['photos'] or {}).get(key)
            if not r2_key:
                types.append(f'{key}:ABSENT')
                continue
            try:
                head = client.get_object(Bucket=R2_BUCKET_NAME, Key=r2_key,
                                         Range='bytes=0-15')['Body'].read()
                t = _sniff_media_type(head) or 'UNKNOWN'
            except Exception as ex:
                t = f'FETCH-FAIL({type(ex).__name__})'
                problems.append((e['id'], f'{key}: {t}'))
            by_type[t] += 1
            types.append(f"{key.split('_')[0]}:{t.replace('image/', '')}")
        print(f"{e['id']:>4}  {'  '.join(types)}")
    print(f"\ntotals by type: {dict(by_type)}")
    print('note: with the normalize-first fix, PNG/WebP/GIF here are fine (re-encoded '
          'to JPEG before sending); only UNKNOWN, heic, FETCH-FAIL or ABSENT are risks.')
    if problems:
        print(f'⚠ problems: {problems}')
    else:
        print('all photos present and typed — no book should fail on media type.')
    return 1 if problems else 0


def summarize(run):
    """run: manifest-shaped dict with per-book results. Prints the diff report."""
    books = run['books']
    n = len(books)
    if run.get('skipped'):
        print(f"\n⚠ SKIPPED ids (excluded from every aggregate): "
              f"{[s['id'] for s in run['skipped']]}")
    if not books:
        print('no completed books in this record — nothing to summarize.')
        return
    deltas = [b['new_grade'] - b['baseline_grade'] for b in books]
    print(f"\n===== RUN REPORT — variant {run['variant']} · {n} books · model {run['model']} =====")
    print(f"grade delta vs stored baseline: mean {statistics.mean(deltas):+.2f}  "
          f"median {statistics.median(deltas):+.2f}  min {min(deltas):+.1f}  max {max(deltas):+.1f}")
    moved = sum(1 for d in deltas if abs(d) >= 0.5)
    print(f"books moving >= 0.5: {moved}/{n}")
    by_era = collections.defaultdict(list)
    for b, d in zip(books, deltas):
        by_era[b['era']].append(d)
    for e, ds in sorted(by_era.items()):
        print(f"  {e:<9} mean {statistics.mean(ds):+.2f}  (n={len(ds)})")

    print(f"\n{'id':>4} {'era':<8} {'stored':>6} {'new':>5} {'delta':>6}  page_quality")
    for b, d in zip(books, deltas):
        print(f"{b['id']:>4} {b['era']:<8} {b['baseline_grade']:>6} {b['new_grade']:>5} "
          f"{d:+6.1f}  {b.get('page_quality') or ''}")

    print('\ndefect base rates (this run vs stored):')
    stored_hits, new_hits = collections.Counter(), collections.Counter()
    for b in books:
        for t in b['stored_themes']:
            stored_hits[t] += 1
        for t in b['new_themes']:
            new_hits[t] += 1
    print(f"  {'theme':<18}{'stored':>8}{'new':>6}")
    for name, _ in THEMES:
        print(f"  {name:<18}{stored_hits[name]:>5}/{n}{new_hits[name]:>4}/{n}")

    truth = [(b['new_grade'] - b['cgc_grade'], b['baseline_grade'] - b['cgc_grade'])
             for b in books if b.get('cgc_grade') is not None]
    if truth:
        nd = [t[0] for t in truth]
        bd = [t[1] for t in truth]
        print(f"\nvs CGC ground truth (n={len(truth)}): "
              f"new mean error {statistics.mean(nd):+.2f}, "
              f"stored mean error {statistics.mean(bd):+.2f}")
    else:
        print('\nno CGC ground truth in the set yet (all cgc_grade null).')

    dist = collections.Counter(b['new_grade'] for b in books)
    print('\nnew-grade distribution:')
    for g in sorted(dist, reverse=True):
        print(f"  {g:>4}  {'#' * dist[g]} {dist[g]}")
    print(f"\nspend: in={run['tokens_in']} out={run['tokens_out']} "
          f"→ ${run['cost_usd']:.3f} (correct the ledger row with this)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--variant', choices=sorted(VARIANTS), default='baseline')
    ap.add_argument('--run', action='store_true',
                    help='actually call the API. Omit to preview (default).')
    ap.add_argument('--limit', type=int, default=None,
                    help='smoke test: only the first N books of the set')
    ap.add_argument('--out', default=None, help='write the JSON run record here')
    ap.add_argument('--report', nargs='+', default=None,
                    help='no API calls: re-print report(s) from saved run JSON')
    ap.add_argument('--preflight', action='store_true',
                    help='no API calls: check every eval-set photo is fetchable '
                         'and report actual media types (run before any paid run)')
    args = ap.parse_args()

    if args.preflight:
        manifest = load_manifest()
        entries = manifest['books'][:args.limit] if args.limit else manifest['books']
        return preflight(entries)

    if args.report:
        for path in args.report:
            with open(path, encoding='utf-8') as f:
                summarize(json.load(f))
        return 0

    manifest = load_manifest()
    entries = manifest['books'][:args.limit] if args.limit else manifest['books']
    n = len(entries)
    est = n * (EST_IN_TOKENS * COST_IN_PER_MTOK + EST_OUT_TOKENS * COST_OUT_PER_MTOK) / 1e6
    strata = collections.Counter(e['era'] for e in entries)
    print(f"variant {args.variant} · {n} books · {dict(strata)}")
    print(f"estimated cost: ${est:.2f} at {manifest['model']} "
          f"(~{EST_IN_TOKENS} in / ~{EST_OUT_TOKENS} out per book)")
    print("ledger: append this estimate to docs/API_SPEND_LEDGER.md BEFORE --run.")
    if not args.run:
        print('DRY RUN — no API calls made. Re-run with --run.')
        return 0

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        sys.exit('ANTHROPIC_API_KEY not set — run in the Render shell.')
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    model = manifest['model']

    subs = fetch_submissions([e['id'] for e in entries])
    missing = [e['id'] for e in entries if e['id'] not in subs]
    if missing:
        sys.exit(f'submissions missing from DB: {missing} — refusing to run on a '
                 f'silently smaller set (the set is fixed; fix the manifest or the data).')

    out_path = args.out or os.path.join(
        _HERE, f"regrade_run_{time.strftime('%Y%m%d_%H%M')}_{args.variant}.json")
    results, skipped, t_in, t_out = [], [], 0, 0

    def _write_record(complete):
        # Incremental: rewritten after EVERY book, so a crash leaves a usable
        # partial record instead of forfeiting the money already spent
        # (2026-08-30 baseline run: 9 books / ~$0.28 lost to an end-only write).
        cost = (t_in * COST_IN_PER_MTOK + t_out * COST_OUT_PER_MTOK) / 1e6
        run = {'variant': args.variant, 'model': model,
               'ran_at': time.strftime('%Y-%m-%d %H:%M'), 'complete': complete,
               'tokens_in': t_in, 'tokens_out': t_out, 'cost_usd': cost,
               'skipped': skipped, 'books': results}
        tmp = out_path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(run, f, indent=1)
        os.replace(tmp, out_path)
        return run

    for i, e in enumerate(entries, 1):
        sub = subs[e['id']]
        # ── One bad book must not destroy the run: a $1.13 run forfeited every
        # book after a single malformed image on 2026-08-30. Catch, log,
        # continue; skipped ids surface in the report.
        try:
            sub['_photos'] = fetch_photos_b64(sub['photos'] or {})
            if len(sub['_photos']) < 3:
                raise RuntimeError(f'only {len(sub["_photos"])} photos retrievable '
                                   f'(set requires >=3)')
            r = regrade_one(client, model, sub, VARIANTS[args.variant])
        except Exception as ex:
            print(f"  [{i}/{n}] id {e['id']}: SKIPPED — {type(ex).__name__}: {ex}")
            skipped.append({'id': e['id'], 'error': f'{type(ex).__name__}: {ex}'})
            _write_record(complete=False)
            continue
        t_in += r['usage']['in']
        t_out += r['usage']['out']
        results.append({
            **e,
            'new_grade': r['grade'],
            'new_scores': r['category_scores'],
            'page_quality': r['page_quality'],
            'stored_themes': sorted(defect_theme_hits(sub['defects'])),
            'new_themes': sorted(defect_theme_hits(r['defects'])),
            'new_defects': r['defects'],
        })
        print(f"  [{i}/{n}] id {e['id']}: stored {e['baseline_grade']} → new {r['grade']}")
        _write_record(complete=False)
        time.sleep(1)  # gentle pacing; this is 36 sequential vision calls

    run = _write_record(complete=True)
    print(f'\nrun record written: {out_path}')
    print('(container FS is ephemeral — copy the JSON out of the shell)')
    if skipped:
        print(f'⚠ {len(skipped)} book(s) SKIPPED: {[s["id"] for s in skipped]} — '
              f'aggregates below cover {len(results)} books, not {n}.')
    summarize(run)
    return 0


if __name__ == '__main__':
    sys.exit(main())
