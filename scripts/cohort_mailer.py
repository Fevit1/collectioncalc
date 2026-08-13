#!/usr/bin/env python3
"""Cohort mailer — one templated message to every real user who has graded.

Built for the 2026-08-13 retention-change notice: privacy.html now says 24
months, the cohort was told 90 days, and publishing the policy does not by
itself discharge telling them.

DESIGN, and why each part is the way it is:

  ONE SENDER. Imports send_email() from send_one_email.py rather than talking to
  Resend directly. Two senders means two From addresses and two payload shapes,
  and the second one is the one nobody tests.

  RECIPIENTS COME FROM THE DATABASE, never a hardcoded list. Anyone who grades
  tomorrow is in the cohort tomorrow. A pasted list is correct exactly once and
  silently wrong forever after.

  DRY RUN IS THE DEFAULT and prints every rendered message IN FULL. Six real
  people are receiving a legal notice; "Hi Sean" reaching Joseph is a terrible
  way to find a templating bug, and it is unrecallable.

  PER-RECIPIENT LOG, append-only JSONL. Each success is written the moment it
  happens, so a failure at message four leaves one, two and three recorded. A
  re-run reads the log and SKIPS them — recoverable without re-sending, which is
  the same idempotency shape as scripts/jv_photo_backfill.py.

USAGE (Render shell — it has RESEND_API_KEY and DATABASE_URL):

    python scripts/cohort_mailer.py --template docs/cohort_notice.txt \\
        --subject "A change to how long we keep your grading data"

    ... read all six rendered messages ...

    python scripts/cohort_mailer.py --template docs/cohort_notice.txt \\
        --subject "..." --send

⚠️ THE LOG LIVES ON THE CONTAINER FILESYSTEM and does not survive a redeploy.
   The script prints how many it found already-sent at startup; if that number
   is 0 on what you believe is a resume, STOP — the log is gone, not the sends.
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')  # L-2026-015
sys.stderr.reconfigure(encoding='utf-8')  # sys.exit() messages go here, and an
                                          # abort reason is the one line the operator
                                          # must be able to read.

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import psycopg2
from psycopg2.extras import RealDictCursor

from send_one_email import send_email, DEFAULT_FROM

# Mike's own accounts. Four of the ten grading users are his; a legal notice to
# himself is noise, and worse, it inflates the "cohort notified" count.
EXCLUDED_EMAILS = (
    'mberry133@yahoo.com',
    'mikeberrysc+22@gmail.com',
    'mike@ideabyhuman.com',
    'mike@slabworthy.com',
)

DEFAULT_LOG = os.path.join(_ROOT, 'scripts', 'cohort_mailer_sent.jsonl')

# The template must contain this, or the salutation silently does not happen and
# six people get a message that opens mid-sentence.
REQUIRED_PLACEHOLDER = '{first_name}'


def load_recipients(conn):
    """Every non-Mike user who has ever submitted a grade. Derived, not listed."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT u.id, u.email, u.display_name, COUNT(gs.id) AS submissions
        FROM users u
        JOIN grade_submissions gs ON gs.user_id = u.id
        WHERE lower(u.email) NOT IN %s
        GROUP BY u.id, u.email, u.display_name
        ORDER BY u.id
    """, (tuple(e.lower() for e in EXCLUDED_EMAILS),))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    return rows


def first_name(display_name):
    """First word of display_name. Returns None rather than guessing.

    An empty or missing display_name must ABORT the run, not fall back to
    "there" or "" — a legal notice opening "Hi ," is worse than a delayed send,
    and a fallback would hide the data problem instead of surfacing it.
    """
    if not display_name or not str(display_name).strip():
        return None
    return str(display_name).strip().split()[0]


def load_sent(path):
    """user_id -> log entry, for every message already confirmed sent."""
    sent = {}
    if not os.path.exists(path):
        return sent
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                if e.get('user_id') is not None and e.get('resend_id'):
                    sent[e['user_id']] = e
            except json.JSONDecodeError:
                print(f'  [warn] unparseable log line skipped: {line[:80]}')
    return sent


def append_sent(path, entry):
    """Append-and-flush per message, so a crash cannot lose a send that happened."""
    with open(path, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(entry) + '\n')
        fh.flush()
        os.fsync(fh.fileno())


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--template', required=True,
                    help=f'UTF-8 body file containing {REQUIRED_PLACEHOLDER}')
    ap.add_argument('--subject', required=True)
    ap.add_argument('--from', dest='sender', default=DEFAULT_FROM)
    ap.add_argument('--reply-to', default=None)
    ap.add_argument('--log', default=DEFAULT_LOG)
    ap.add_argument('--send', action='store_true',
                    help='actually send. Omit to preview every message (the default).')
    args = ap.parse_args()
    dry = not args.send

    print('=' * 78)
    print('  COHORT MAILER')
    print(f'  MODE:     {"DRY RUN (nothing will be sent)" if dry else "SEND (WILL SEND)"}')
    print(f'  from:     {args.sender}')
    print(f'  subject:  {args.subject}')
    print(f'  template: {args.template}')
    print(f'  log:      {args.log}')
    print('=' * 78)

    template = open(args.template, encoding='utf-8').read()
    if REQUIRED_PLACEHOLDER not in template:
        sys.exit(f'template does not contain {REQUIRED_PLACEHOLDER} — refusing to send '
                 f'six identical messages with no salutation')
    if not template.strip():
        sys.exit('template is empty')

    db_url = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_URL_RO')
    if not db_url:
        sys.exit('DATABASE_URL not set. Run this in the Render shell.')
    conn = psycopg2.connect(db_url)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT current_user, current_database()')
    ident = cur.fetchone()
    print(f'  db:       {ident["current_database"]} as {ident["current_user"]}')  # L-2026-025
    cur.close()

    recipients = load_recipients(conn)
    conn.close()

    sent = load_sent(args.log)
    print(f'\n  recipients found: {len(recipients)}')
    print(f'  already sent (from log): {len(sent)}'
          f'{"  <-- if you expected a resume, the log is missing, not the sends" if not sent else ""}')

    # Validate EVERY salutation before sending ANY message. A run that sends
    # three and then aborts on a missing display_name has already done the
    # unrecallable part.
    problems = [r for r in recipients if first_name(r['display_name']) is None]
    if problems:
        for r in problems:
            print(f"  ! user {r['id']} {r['email']}: display_name is "
                  f"{r['display_name']!r} — no first name")
        sys.exit(f'{len(problems)} recipient(s) have no usable first name. '
                 f'Nothing sent. Fix the data or exclude them explicitly.')

    todo = [r for r in recipients if r['id'] not in sent]
    print(f'  to send now: {len(todo)}\n')

    for r in recipients:
        if r['id'] in sent:
            e = sent[r['id']]
            print(f"  SKIP  user {r['id']:<4} {r['email']:<32} already sent "
                  f"(resend id {e.get('resend_id')})")

    print('\n' + '=' * 78)
    print('  RENDERED MESSAGES — read all of them before sending')
    print('=' * 78)
    for r in todo:
        fn = first_name(r['display_name'])
        body = template.replace(REQUIRED_PLACEHOLDER, fn)
        print(f"\n{'-' * 78}")
        print(f"  TO:      {r['email']}  (user {r['id']}, {r['submissions']} submission(s))")
        print(f"  NAME:    display_name={r['display_name']!r}  ->  first_name={fn!r}")
        print(f"  SUBJECT: {args.subject}")
        print(f"{'-' * 78}")
        print(body)
        # Prove the substitution actually happened in THIS message rather than
        # trusting that it happened in general.
        if REQUIRED_PLACEHOLDER in body:
            sys.exit(f'placeholder survived substitution for user {r["id"]} — aborting')
        if fn not in body:
            print(f"  [warn] {fn!r} does not appear in the rendered body — check the template")

    print('\n' + '=' * 78)
    if dry:
        print(f'  DRY RUN COMPLETE — {len(todo)} message(s) rendered, NONE sent.')
        print('  Re-run with --send to deliver.')
        return 0

    print('  SENDING')
    print('=' * 78)
    ok, failed = [], []
    for r in todo:
        fn = first_name(r['display_name'])
        body = template.replace(REQUIRED_PLACEHOLDER, fn)
        try:
            msg_id = send_email(args.sender, r['email'], args.subject, body,
                                reply_to=args.reply_to)
            entry = {'user_id': r['id'], 'email': r['email'], 'first_name': fn,
                     'subject': args.subject, 'resend_id': msg_id}
            append_sent(args.log, entry)   # written BEFORE we print success
            ok.append(r['id'])
            print(f"  SENT  user {r['id']:<4} {r['email']:<32} resend id {msg_id}")
        except Exception as e:
            failed.append((r['id'], r['email'], str(e)))
            print(f"  FAIL  user {r['id']:<4} {r['email']:<32} {e}")

    print('\n' + '=' * 78)
    print(f'  sent:   {len(ok)}  {ok}')
    print(f'  failed: {len(failed)}')
    for uid, email, err in failed:
        print(f'    ! {uid} {email}: {err}')
    if failed:
        print('\n  Re-run to retry ONLY the failures — successes are in the log and are skipped.')
    print(f'\n  Log: {args.log}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
