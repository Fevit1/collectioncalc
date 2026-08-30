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


def fetch_photos_b64(photos_map):
    """photos_map: label_key -> R2 key. Returns [(label, b64)] in prod's order."""
    from r2_storage import get_r2_client, R2_BUCKET_NAME
    client = get_r2_client()
    order = ['front_cover', 'spine', 'back_cover', 'centerfold']
    label_for = {'front_cover': 'Front Cover', 'spine': 'Spine',
                 'back_cover': 'Back Cover', 'centerfold': 'Centerfold'}
    out = []
    for key in order:
        r2_key = photos_map.get(key)
        if not r2_key:
            continue
        obj = client.get_object(Bucket=R2_BUCKET_NAME, Key=r2_key)
        out.append((label_for[key], base64.standard_b64encode(obj['Body'].read()).decode()))
    return out


# ── Grading call (mirrors /api/grade's request shape) ────────────────────────

def regrade_one(client, model, sub, variant_fn):
    from grading_engine import build_grading_prompt, parse_grading_response
    labels = [l for l, _ in sub['_photos']]
    prompt = build_grading_prompt(sub['title'], sub['issue'], sub['publisher'], labels)
    prompt = variant_fn(prompt, sub['year'])

    content = []
    for label, b64 in sub['_photos']:
        content.append({'type': 'text', 'text': f'Photo: {label}'})
        content.append({'type': 'image',
                        'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': b64}})
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


def summarize(run):
    """run: manifest-shaped dict with per-book results. Prints the diff report."""
    books = run['books']
    n = len(books)
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
    args = ap.parse_args()

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

    results, t_in, t_out = [], 0, 0
    for i, e in enumerate(entries, 1):
        sub = subs[e['id']]
        try:
            sub['_photos'] = fetch_photos_b64(sub['photos'] or {})
        except Exception as ex:
            sys.exit(f'photo fetch failed for id {e["id"]}: {ex} — if purged, the '
                     f'fixed set is broken; stop and re-scope rather than skip.')
        if len(sub['_photos']) < 3:
            sys.exit(f'id {e["id"]}: only {len(sub["_photos"])} photos retrievable — '
                     f'refusing (set fixed at >=3).')
        r = regrade_one(client, model, sub, VARIANTS[args.variant])
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
        time.sleep(1)  # gentle pacing; this is 36 sequential vision calls

    cost = (t_in * COST_IN_PER_MTOK + t_out * COST_OUT_PER_MTOK) / 1e6
    run = {'variant': args.variant, 'model': model, 'ran_at': time.strftime('%Y-%m-%d %H:%M'),
           'tokens_in': t_in, 'tokens_out': t_out, 'cost_usd': cost, 'books': results}
    out_path = args.out or os.path.join(
        _HERE, f"regrade_run_{time.strftime('%Y%m%d_%H%M')}_{args.variant}.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(run, f, indent=1)
    print(f'\nrun record written: {out_path}')
    print('(container FS is ephemeral — copy the JSON out of the shell, or rely on stdout below)')
    print(json.dumps(run)[:200] + ' ...')
    summarize(run)
    return 0


if __name__ == '__main__':
    sys.exit(main())
