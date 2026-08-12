#!/usr/bin/env python3
"""Send ONE email through Resend, from a named sender.

Built for the reply to Joseph Vicario (user 38) and reusable as-is for the
2026-09-17 cohort notification, which needs exactly the same thing.

Yahoo cannot send as slabworthy.com, and a personal reply should not arrive from
`noreply@`. So the sender defaults to mike@slabworthy.com and is overridable.

  --from must be on a domain VERIFIED in Resend, or the send is rejected. That is
  a Resend/DNS fact, not a flag this script can satisfy; Cloudflare Email Routing
  handles inbound (so replies reach you) and is a SEPARATE thing from outbound
  authorisation. Verify the domain in Resend before relying on this.

DRY RUN IS THE DEFAULT. Nothing sends without --send, because the failure mode
here is a real message to a real person that cannot be recalled.

USAGE
    python scripts/send_one_email.py --to a@b.com --subject "..." --body-file msg.txt
    python scripts/send_one_email.py --to a@b.com --subject "..." --body-file msg.txt --send

--body-file is preferred over --body: shell quoting mangles apostrophes and
newlines, and this text is going to a customer.
"""
import argparse
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')  # L-2026-015

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

DEFAULT_FROM = 'Mike Berry <mike@slabworthy.com>'


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--to', required=True)
    ap.add_argument('--subject', required=True)
    ap.add_argument('--body', help='body text (prefer --body-file)')
    ap.add_argument('--body-file', help='path to a UTF-8 file holding the body')
    ap.add_argument('--from', dest='sender', default=DEFAULT_FROM)
    ap.add_argument('--reply-to', default=None)
    ap.add_argument('--html', action='store_true',
                    help='send the body as HTML instead of plain text')
    ap.add_argument('--send', action='store_true',
                    help='actually send. Omit to preview (the default).')
    args = ap.parse_args()

    if bool(args.body) == bool(args.body_file):
        sys.exit('give exactly one of --body or --body-file')

    body = (open(args.body_file, encoding='utf-8').read() if args.body_file
            else args.body)
    if not body.strip():
        sys.exit('refusing to send an empty body')

    print('=' * 72)
    print(f'  from     {args.sender}')
    print(f'  to       {args.to}')
    if args.reply_to:
        print(f'  reply-to {args.reply_to}')
    print(f'  subject  {args.subject}')
    print(f'  format   {"html" if args.html else "plain text"}  ({len(body)} chars)')
    print('=' * 72)
    print(body)
    print('=' * 72)

    if not args.send:
        print('  DRY RUN — nothing sent. Re-run with --send.')
        return 0

    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        sys.exit('RESEND_API_KEY not set. Run this in the Render shell, or export it locally.')

    import resend
    resend.api_key = api_key

    payload = {
        'from': args.sender,
        'to': [args.to],
        'subject': args.subject,
        ('html' if args.html else 'text'): body,
    }
    if args.reply_to:
        payload['reply_to'] = args.reply_to

    result = resend.Emails.send(payload)
    # Print the provider's own id. "No exception" is not proof of delivery, and
    # an id is the only handle you have if you later need to check what happened
    # to this specific message (L-SW-2026-017: name the artifact).
    print(f'  SENT — Resend id: {result.get("id") if isinstance(result, dict) else result}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
