#!/usr/bin/env python3
"""
One-shot photo backfill for user 38 (vicariojoseph.jv@gmail.com).

WHAT HAPPENED
-------------
2026-08-06 01:22 -> 03:51 UTC, user 38 saved 21 comics to his collection. Every
`/api/images/submission` upload either failed or returned AFTER app.html's 30s
client-side `Promise.race` timeout, so `photoUrls` stayed all-null while
`/api/collection/save` returned 200. All 21 rows hold exactly:

    {"back": null, "front": null, "spine": null, "centerfold": null}

His photos survive only in `grade_submissions` (the retention path, which
uploads server-side and did not go through the failing endpoint). Those rows
carry `images_purge_after = 2026-11-04`, so this is the only recovery window.

WHAT THIS DOES
--------------
For each recoverable collection row: copies the four grade_submissions R2
objects to NEW `submissions/{grading_id}/{label}.jpg` keys and writes the
public URLs into `collections.photos`.

DESIGN CONSTRAINT (agreed, not up for revision): the two key spaces stay
disjoint. `collections.photos` is NEVER pointed at a `grade_submissions/` key.
The 90-day purge's safety depends on that separation and nothing enforces it,
so recovery must preserve it rather than consume it.

WHY 20 ROWS AND NOT 21
----------------------
Collection 89 (Captain America #6) resolves cleanly to submission 46, whose
`photos` column is NULL -- the persist thread inserted the row and died before
the photo-backfill UPDATE ran. There are no objects to copy.

That row asserts `photos_used = 4` and a populated `photo_labels`. Both are
true statements about what the GRADER consumed; neither is a claim about what
was STORED. This script keys on the `photos` jsonb and nothing else.

WHY SOME SUBMISSIONS MAP TO SEVERAL ROWS
----------------------------------------
Submission 48 -> collections 91, 92 (Strange Academy #1)
Submission 50 -> collections 93, 94, 95, 96 (Daredevil #196)

Those are repeated Save clicks on one grade report, each minting its own
`grading_id`. Copying per-row is the faithful reconstruction: had the uploads
worked, every save click would have uploaded its own copy under its own prefix.
Deliberate. Do not "optimise" this into shared objects -- per-row prefixes keep
each row self-contained.

USAGE (Render shell -- it already has DATABASE_URL and the R2_* credentials)
---------------------------------------------------------------------------
    python scripts/jv_photo_backfill.py             # DRY RUN, writes nothing
    python scripts/jv_photo_backfill.py --execute   # writes

The dry run prints the full plan and the pre-filled rollback statement. Read it
before running with --execute.

Re-running is safe. Rows that already carry an http URL are skipped, and the R2
copy is idempotent by key, so a crash at row 12 is fixed by re-running.
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')  # L-2026-015

# Resolve the repo root from THIS file, never from the invocation. Requiring the
# operator to remember `PYTHONPATH=/app` makes correctness depend on how the
# script was called -- and a step you have to remember is a step that gets
# forgotten. Same convention as scripts/cp1_*.py.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import psycopg2
from psycopg2.extras import RealDictCursor

# ── The plan ────────────────────────────────────────────────────────────────
# (collection_id, grade_submission_id). Derived 2026-08-12 from user + exact
# title + attribute agreement; every pair is re-verified against live data
# below before anything is written.
MAPPING = [
    (75, 27), (76, 30), (77, 31), (78, 33), (80, 34), (81, 35), (82, 36),
    (83, 37), (84, 40), (85, 41), (86, 42), (87, 44), (88, 45), (90, 47),
    (91, 48), (92, 48), (93, 50), (94, 50), (95, 50), (96, 50),
]

# Recorded so the exclusion is visible in the output rather than silent.
EXCLUDED = {
    89: (46, 'submission 46 has photos IS NULL -- no R2 objects exist; '
             'photos_used=4 and photo_labels are claims about the grader, not about storage'),
}

USER_ID = 38
USER_EMAIL = 'vicariojoseph.jv@gmail.com'

# grade_submissions label -> collections label
LABEL_MAP = {
    'front_cover': 'front',
    'back_cover': 'back',
    'spine': 'spine',
    'centerfold': 'centerfold',
}

# The exact literal every one of the 21 rows currently holds. Verified by
# SELECT DISTINCT: one value across all 21.
BEFORE_LITERAL = {"back": None, "front": None, "spine": None, "centerfold": None}

# A save always follows its grade, and the widest real gap is 252s (collection
# 96). Anything outside this bound means the mapping no longer matches the data.
MAX_DELTA_SEC = 300

# Positive control (L-2026-024): a key that must exist and one that must not.
# The present one is derived from a healthy row rather than hardcoded, so it
# cannot drift; the absent one is synthetic.
CONTROL_ABSENT_KEY = 'positive_control/this_object_must_never_exist_jv_backfill.jpg'

MIN_PLAUSIBLE_BYTES = 1024  # below this an object is a stub, not a photo


class Abort(Exception):
    pass


def rule(title=''):
    print('\n' + '=' * 78)
    if title:
        print(title)
        print('=' * 78)


# ── R2 ──────────────────────────────────────────────────────────────────────

def get_r2():
    """Build the R2 client from the same env the app uses."""
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        raise Abort('boto3 is not installed here. This script must run in the Render '
                    'shell, which has boto3 and the R2 credentials.')

    key_id = os.environ.get('R2_ACCESS_KEY_ID')
    secret = os.environ.get('R2_SECRET_ACCESS_KEY')
    account = os.environ.get('R2_ACCOUNT_ID')
    bucket = os.environ.get('R2_BUCKET_NAME', 'collectioncalc-images')
    endpoint = os.environ.get('R2_ENDPOINT') or f'https://{account}.r2.cloudflarestorage.com'

    if not all([key_id, secret, account]):
        raise Abort('R2 credentials not configured (R2_ACCESS_KEY_ID / '
                    'R2_SECRET_ACCESS_KEY / R2_ACCOUNT_ID). Run this in the Render shell.')

    client = boto3.client(
        's3', endpoint_url=endpoint,
        aws_access_key_id=key_id, aws_secret_access_key=secret,
        config=Config(signature_version='s3v4', retries={'max_attempts': 3}),
    )
    return client, bucket


def head(client, bucket, key):
    """Return object size, or None if absent. Raises on anything else --
    a permissions error must never read as 'missing'."""
    from botocore.exceptions import ClientError
    try:
        return client.head_object(Bucket=bucket, Key=key)['ContentLength']
    except ClientError as e:
        code = e.response.get('Error', {}).get('Code', '')
        if code in ('404', 'NoSuchKey', 'NotFound'):
            return None
        raise


def positive_control(client, bucket, present_key):
    """Prove the probe can return BOTH answers before trusting any of them."""
    rule('POSITIVE CONTROL -- proving the existence probe can fire both ways')
    print(f'  bucket: {bucket}')

    present = head(client, bucket, present_key)
    print(f'  MUST EXIST   {present_key}')
    print(f'               -> {"EXISTS, " + str(present) + " bytes" if present else "MISSING"}')

    absent = head(client, bucket, CONTROL_ABSENT_KEY)
    print(f'  MUST BE GONE {CONTROL_ABSENT_KEY}')
    print(f'               -> {"EXISTS (" + str(absent) + " bytes)" if absent is not None else "MISSING"}')

    if present is None:
        raise Abort('positive control failed: a known-present object read as MISSING. '
                    'Every "source missing" result below would be untrustworthy.')
    if absent is not None:
        raise Abort('positive control failed: a synthetic key read as EXISTS.')
    print('\n  PASS -- the probe distinguishes present from absent.')


# ── Verification ────────────────────────────────────────────────────────────

def load_and_verify(cur):
    """Re-verify every mapped pair against live data. Returns the work list."""
    rule('VERIFYING THE MAPPING AGAINST LIVE DATA')

    cur.execute('SELECT id, email FROM users WHERE id = %s', (USER_ID,))
    user = cur.fetchone()
    if not user or user['email'] != USER_EMAIL:
        raise Abort(f'user {USER_ID} is not {USER_EMAIL} (got {user}). Refusing to touch anything.')
    print(f'  user {USER_ID} = {user["email"]}')

    col_ids = sorted({c for c, _ in MAPPING})
    sub_ids = sorted({s for _, s in MAPPING})

    cur.execute("""SELECT id, user_id, title, issue, publisher, year, grade,
                          grading_id, created_at, photos
                   FROM collections WHERE id = ANY(%s)""", (col_ids,))
    cols = {r['id']: r for r in cur.fetchall()}

    cur.execute("""SELECT id, user_id, title, issue, publisher, year, grade,
                          created_at, photos
                   FROM grade_submissions WHERE id = ANY(%s)""", (sub_ids,))
    subs = {r['id']: r for r in cur.fetchall()}

    work, problems, already_done = [], [], []

    for col_id, sub_id in MAPPING:
        c, s = cols.get(col_id), subs.get(sub_id)
        tag = f'col {col_id} <- sub {sub_id}'

        if c is None:
            problems.append(f'{tag}: collection row is gone')
            continue
        if s is None:
            problems.append(f'{tag}: submission row is gone')
            continue

        # Ownership. Both sides, every time.
        if c['user_id'] != USER_ID or s['user_id'] != USER_ID:
            problems.append(f'{tag}: ownership mismatch '
                            f'(col.user={c["user_id"]}, sub.user={s["user_id"]})')
            continue

        # Already repaired? Skip -- this is what makes a re-run safe.
        if c['photos'] and 'http' in json.dumps(c['photos']):
            already_done.append(col_id)
            continue

        # Untouched rows must still hold the exact literal we recorded.
        if c['photos'] != BEFORE_LITERAL:
            problems.append(f'{tag}: photos is not the expected all-null literal '
                            f'-- got {json.dumps(c["photos"])}')
            continue

        # Identity agreement. These are what make 95/96 certain without a
        # time window: title, issue, grade, publisher and year all agree and
        # sub 50 is the only Daredevil submission in the retained set.
        for field in ('title', 'issue', 'grade'):
            if c[field] != s[field]:
                problems.append(f'{tag}: {field} disagrees '
                                f'(col={c[field]!r} sub={s[field]!r})')
                break
        else:
            for field in ('publisher', 'year'):
                if c[field] is not None and s[field] is not None and c[field] != s[field]:
                    problems.append(f'{tag}: {field} disagrees '
                                    f'(col={c[field]!r} sub={s[field]!r})')
                    break
            else:
                # The grade must precede the save.
                delta = (c['created_at'] - s['created_at']).total_seconds()
                if not (0 < delta <= MAX_DELTA_SEC):
                    problems.append(f'{tag}: delta {delta:.1f}s outside '
                                    f'(0, {MAX_DELTA_SEC}]')
                    continue

                # Source keys come from the photos jsonb ONLY.
                photos = s['photos'] if isinstance(s['photos'], dict) else {}
                missing = [k for k in LABEL_MAP if not photos.get(k)]
                if missing:
                    problems.append(f'{tag}: submission photos jsonb lacks {missing} '
                                    f'-- nothing to copy')
                    continue

                work.append({
                    'col_id': col_id, 'sub_id': sub_id,
                    'grading_id': c['grading_id'], 'delta': delta,
                    'title': c['title'], 'issue': c['issue'], 'grade': c['grade'],
                    'existing_photos': c['photos'],
                    'pairs': [(photos[gs], f'submissions/{c["grading_id"]}/{cl}.jpg', cl)
                              for gs, cl in LABEL_MAP.items()],
                })

    print(f'  mapped pairs:      {len(MAPPING)}')
    print(f'  verified to do:    {len(work)}')
    print(f'  already repaired:  {len(already_done)} {already_done or ""}')
    print(f'  problems:          {len(problems)}')
    for p in problems:
        print(f'    ! {p}')

    rule('DELIBERATELY EXCLUDED -- not a silent cap')
    for col_id, (sub_id, why) in EXCLUDED.items():
        print(f'  col {col_id} (<- sub {sub_id}): {why}')
    print(f'\n  {len(MAPPING)} recoverable + {len(EXCLUDED)} unrecoverable = '
          f'{len(MAPPING) + len(EXCLUDED)} of his 21 saved comics.')

    if problems:
        raise Abort(f'{len(problems)} pair(s) failed verification. The mapping no longer '
                    f'matches the data. Nothing has been written. Re-derive before running.')

    return work


def resolve_public_base(cur):
    """Derive the public URL base from a healthy row, then cross-check it
    against what the app would compute. Derived beats asserted -- a wrong
    domain written into 20 rows would look exactly like a working fix."""
    rule('PUBLIC URL BASE -- derived, then cross-checked')

    cur.execute("""SELECT id, photos FROM collections
                   WHERE photos::text LIKE %s AND user_id <> %s
                   ORDER BY id DESC LIMIT 1""", ('%https://%submissions/%', USER_ID))
    row = cur.fetchone()
    if not row:
        raise Abort('no healthy collections row to derive the public URL base from')

    sample = next(v for k, v in row['photos'].items()
                  if k != 'extra' and isinstance(v, str) and '/submissions/' in v)
    base = sample.split('/submissions/')[0]
    control_key = 'submissions/' + sample.split('/submissions/', 1)[1]
    print(f'  derived from collection {row["id"]}: {sample}')
    print(f'  base -> {base}')

    from r2_storage import get_image_url
    computed = get_image_url('submissions/x.jpg').rsplit('/submissions/', 1)[0]
    print(f'  r2_storage.get_image_url() would produce base -> {computed}')
    if computed != base:
        raise Abort(f'public base disagreement: live rows use {base!r} but this '
                    f'container computes {computed!r}. Refusing to write URLs.')
    print('  AGREE')
    return base, control_key


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--execute', action='store_true',
                    help='actually write. Omit for a dry run (the default).')
    args = ap.parse_args()
    dry = not args.execute

    print('=' * 78)
    print(f'  JV PHOTO BACKFILL -- user {USER_ID} ({USER_EMAIL})')
    print(f'  MODE: {"DRY RUN (nothing will be written)" if dry else "EXECUTE (WILL WRITE)"}')
    print('=' * 78)

    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise Abort('DATABASE_URL not set. Run this in the Render shell.')

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute('SELECT current_user, current_database()')
    ident = cur.fetchone()
    print(f'  db: {ident["current_database"]} as {ident["current_user"]}')  # L-2026-025

    base, control_key = resolve_public_base(cur)
    work = load_and_verify(cur)

    client, bucket = get_r2()
    positive_control(client, bucket, control_key)

    # ── Probe every source and destination BEFORE writing anything ──────────
    rule('R2 PROBE -- sources and destinations, before any write')
    blocked = []
    for w in work:
        print(f'\n  col {w["col_id"]} <- sub {w["sub_id"]}  '
              f'{w["title"]} #{w["issue"]} g={w["grade"]}  (delta {w["delta"]:.0f}s)')
        print(f'    dest prefix: submissions/{w["grading_id"]}/')
        w['actions'] = []
        for src, dst, label in w['pairs']:
            s_size = head(client, bucket, src)
            d_size = head(client, bucket, dst)

            if d_size is not None and d_size >= MIN_PLAUSIBLE_BYTES:
                # His own upload landed late (server 200 after the client's 30s
                # timeout). Keep the genuine original rather than copying over it.
                action = 'KEEP-EXISTING'
            elif s_size is None:
                action = 'BLOCKED-SOURCE-MISSING'
                blocked.append(f'col {w["col_id"]} {label}: source {src} MISSING')
            elif s_size < MIN_PLAUSIBLE_BYTES:
                action = 'BLOCKED-SOURCE-TOO-SMALL'
                blocked.append(f'col {w["col_id"]} {label}: source {src} only {s_size} bytes')
            else:
                action = 'COPY'

            w['actions'].append((src, dst, label, action))
            print(f'    {label:11} src {"MISSING" if s_size is None else str(s_size) + "B":>10}'
                  f'   dst {"absent" if d_size is None else str(d_size) + "B":>10}   -> {action}')

    # ── The rollback, printed BEFORE anything is written ────────────────────
    touched = sorted(w['col_id'] for w in work)
    rule('ROLLBACK -- printed before any write. Save this.')
    print('  Run in DBeaver to restore every row this script would touch:\n')
    print('    UPDATE collections')
    print(f"    SET photos = '{json.dumps(BEFORE_LITERAL)}'::jsonb")
    print(f'    WHERE user_id = {USER_ID} AND id IN ({", ".join(str(i) for i in touched)});')
    print('\n  R2 objects can be left in place -- nothing references them once the')
    print('  rows are restored, and the collection delete path already orphans objects.')

    n_copy = sum(1 for w in work for *_, a in w['actions'] if a == 'COPY')
    n_keep = sum(1 for w in work for *_, a in w['actions'] if a == 'KEEP-EXISTING')
    rule('SUMMARY')
    print(f'  collection rows to update:   {len(work)}')
    print(f'  R2 objects to copy:          {n_copy}')
    print(f'  R2 objects already present:  {n_keep}  (his own late-landing uploads)')
    print(f'  blocked:                     {len(blocked)}')
    for b in blocked:
        print(f'    ! {b}')

    if blocked:
        raise Abort('one or more source objects are missing or implausibly small. '
                    'Nothing has been written. Investigate before proceeding.')

    if dry:
        rule('DRY RUN COMPLETE -- nothing was written')
        print('  Re-run with --execute to apply.')
        conn.rollback()
        conn.close()
        return 0

    # ── Execute: per-row, R2 first, DB commit last ─────────────────────────
    rule('EXECUTING')
    ok, failed = [], []
    for w in work:
        try:
            for src, dst, label, action in w['actions']:
                if action == 'COPY':
                    client.copy_object(Bucket=bucket, Key=dst,
                                       CopySource={'Bucket': bucket, 'Key': src})
                    size = head(client, bucket, dst)
                    if size is None or size < MIN_PLAUSIBLE_BYTES:
                        raise RuntimeError(f'{dst} did not land (size={size})')

            photos = dict(w['existing_photos'] or {})
            for _, dst, label, _a in w['actions']:
                photos[label] = f'{base}/{dst}'

            cur.execute("""UPDATE collections SET photos = %s, updated_at = NOW()
                           WHERE id = %s AND user_id = %s
                             AND photos::text NOT LIKE %s
                           RETURNING id""",
                        (json.dumps(photos), w['col_id'], USER_ID, '%http%'))
            hit = cur.fetchone()
            if not hit:
                raise RuntimeError('UPDATE matched no row (guard rejected it)')
            conn.commit()
            ok.append(w['col_id'])
            print(f'  OK   col {w["col_id"]}  {w["title"]} #{w["issue"]}  '
                  f'-> submissions/{w["grading_id"]}/')
        except Exception as e:
            conn.rollback()
            failed.append((w['col_id'], str(e)))
            print(f'  FAIL col {w["col_id"]}: {e}')

    rule('DONE')
    print(f'  updated: {len(ok)}  {ok}')
    print(f'  failed:  {len(failed)}')
    for col_id, err in failed:
        print(f'    ! col {col_id}: {err}')
    if failed:
        print('\n  Re-run to retry -- completed rows are skipped by the http guard.')
    print(f'\n  Verify: his collection page should now show covers on {len(ok)} of 21 rows.')
    print(f'  Collection 89 (Captain America #6) stays blank -- see EXCLUDED above.')

    cur.close()
    conn.close()
    return 1 if failed else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Abort as e:
        print(f'\nABORTED: {e}')
        sys.exit(2)
