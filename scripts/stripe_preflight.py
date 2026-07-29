#!/usr/bin/env python
"""
Stripe pre-flight check — TEST mode by default, LIVE mode with --live.

╔══════════════════════════════════════════════════════════════════════════╗
║  READ-ONLY — NO SIDE EFFECTS.                                             ║
║  This script ONLY performs list/retrieve (GET) calls against the Stripe  ║
║  API, and (optionally, with --check-db) a single SELECT against the DB.   ║
║  It does NOT create, modify, or delete anything: no customers, no         ║
║  checkout sessions, no subscriptions, no webhook changes, no DB writes.   ║
║  The only external calls used are:                                        ║
║      stripe.Price.retrieve(...)         (read)                            ║
║      stripe.WebhookEndpoint.list(...)   (read)                            ║
║      SELECT ... FROM users WHERE email  (read, only with --check-db)      ║
║  Safe to run against production test-mode keys.                           ║
╚══════════════════════════════════════════════════════════════════════════╝

Confirms (from the Stripe runbook) the items you couldn't see from the repo:
  #1 STRIPE_*_PRICE env values resolve in the EXPECTED mode      → CHECKED here
  #3 a webhook endpoint in that mode points at /api/billing/webhook → CHECKED here
  #2 STRIPE_WEBHOOK_SECRET matches that endpoint's secret        → NOT checkable
     (Stripe shows a webhook signing secret only once, at creation; it is not
      retrievable via API. This stays a manual dashboard check — see summary.)

Uses STRIPE_SECRET_KEY from the environment. Never hardcodes a key.

Modes:
  default   expect TEST — sk_test_/rk_test_ key, livemode=false prices (Section E)
  --live    expect LIVE — sk_live_/rk_live_ key, livemode=true prices (cutover check)
Both are equally read-only; --live only changes what counts as PASS. Running the
default against a live key (or --live against a test key) is reported as a flag
rather than silently passing, so a half-swapped config can't look green.

Run:
    python scripts/stripe_preflight.py                       # test mode
    python scripts/stripe_preflight.py --live                # after the live cutover
    python scripts/stripe_preflight.py --check-db a@b.com    # optional, SELECT-only
(Run it where STRIPE_SECRET_KEY is set — e.g. the Render shell, where the env is
 already present — or set $env:STRIPE_SECRET_KEY for the session locally.
 Per L-SW-2026-004: after changing env vars, redeploy AND open a FRESH shell —
 an already-open shell keeps the old values and will verify the wrong config.)
"""

import os
import sys
import argparse

# Cross-project L-2026-015: Windows stdout must be explicitly UTF-8. This script prints
# arrows/check marks, which crash a cp1252 console with UnicodeEncodeError mid-run — so a
# local run died at [1] KEY MODE before checking anything. Harmless on Linux (Render shell).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import stripe
except ImportError:
    print("ERROR: the 'stripe' package isn't installed in this environment.")
    sys.exit(1)

# The price env vars create-checkout reads (Pro + Guard; Dealer is refused server-side, skipped).
PRICE_ENV_VARS = [
    ("Pro / monthly",   "STRIPE_PRO_MONTHLY_PRICE"),
    ("Pro / annual",    "STRIPE_PRO_ANNUAL_PRICE"),
    ("Guard / monthly", "STRIPE_GUARD_MONTHLY_PRICE"),
    ("Guard / annual",  "STRIPE_GUARD_ANNUAL_PRICE"),
]

# Events the webhook handler processes (routes/billing.py).
NEEDED_EVENTS = [
    "checkout.session.completed",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
]

WEBHOOK_PATH = "/api/billing/webhook"

flags = []   # collected problems → printed in the summary


def check_db(email):
    """READ-ONLY: print a user's current billing fields (a single SELECT — no writes)."""
    print("\n[DB] ACCOUNT BILLING STATE (read-only SELECT)")
    dburl = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL_RO")
    if not dburl:
        print("    Neither DATABASE_URL nor DATABASE_URL_RO is set — skipping db check.")
        return
    try:
        import psycopg2
        conn = psycopg2.connect(dburl)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, plan, subscription_status, billing_period, "
            "       (stripe_customer_id IS NOT NULL) AS has_customer, "
            "       (stripe_subscription_id IS NOT NULL) AS has_subscription "
            "FROM users WHERE email = %s",
            (email,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            print(f"    no user found with email {email}")
            return
        uid, em, plan, status, period, has_cust, has_sub = row
        print(f"    id={uid}  email={em}")
        print(f"    plan={plan} · subscription_status={status} · billing_period={period}")
        print(f"    stripe_customer_id set={has_cust} · stripe_subscription_id set={has_sub}")
    except Exception as e:
        print(f"    db check failed: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="READ-ONLY Stripe pre-flight for Section E (billing end-to-end)."
    )
    parser.add_argument(
        "--check-db", metavar="EMAIL", default=None,
        help="Optional read-only SELECT: print this account's plan + subscription_status.",
    )
    parser.add_argument(
        "--live", action="store_true",
        help="Expect LIVE mode instead of TEST: require an sk_live_/rk_live_ key and "
             "livemode=true prices. Use this to verify the live-mode cutover. Still READ-ONLY.",
    )
    args = parser.parse_args()

    expect_live = args.live
    expected_mode = "LIVE" if expect_live else "TEST"

    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        print("ERROR: STRIPE_SECRET_KEY is not set in this environment. Nothing to check.")
        sys.exit(1)
    stripe.api_key = key

    print("=" * 70)
    print(f"Stripe pre-flight (READ-ONLY) — expecting {expected_mode} mode")
    print("=" * 70)

    # ── 1. KEY MODE ────────────────────────────────────────────────────────
    print("\n[1] KEY MODE")
    if key.startswith(("sk_test_", "rk_test_")):
        mode = "TEST"
    elif key.startswith(("sk_live_", "rk_live_")):
        mode = "LIVE"
    else:
        mode = "UNKNOWN"
    print(f"    Secret key: ...{key[-4:]}  → mode: {mode}   (expected: {expected_mode})")
    if mode != expected_mode:
        if expect_live:
            flags.append(f"Key is {mode}, not LIVE — the live cutover needs an sk_live_ key. "
                         f"If you meant to check test mode, drop --live.")
        else:
            flags.append(f"Key is {mode}, not TEST — Section E must run on a sk_test_ key. "
                         f"If you meant to check the live cutover, pass --live.")
    if expect_live and mode == "LIVE":
        print("    ⚠️  LIVE key: this script still only performs GET/list/retrieve calls, but any")
        print("        OTHER command you run against this key can move real money. Be deliberate.")

    # ── 2. PRICE IDS (item #1) ─────────────────────────────────────────────
    want_livemode = bool(expect_live)   # True when --live, else False
    print(f"\n[2] PRICE IDS (item #1 — must resolve in {expected_mode} mode, "
          f"livemode={str(want_livemode).lower()})")
    for label, env_var in PRICE_ENV_VARS:
        pid = os.environ.get(env_var)
        if not pid:
            print(f"    [{label}]  {env_var} is NOT SET")
            flags.append(f"{env_var} not set → '{label}' checkout returns 'Price not configured'.")
            continue
        try:
            price = stripe.Price.retrieve(pid, expand=["product"])
        except stripe.error.InvalidRequestError as e:
            print(f"    [{label}]  {pid}  → ✗ DOES NOT RESOLVE: {getattr(e, 'user_message', None) or e}")
            other = "TEST" if expect_live else "LIVE"
            flags.append(f"{env_var} ({pid}) doesn't resolve on this key → 'No such price' at checkout "
                         f"(likely a {other}-mode price id set while running {expected_mode}).")
            continue
        except stripe.error.StripeError as e:
            print(f"    [{label}]  {pid}  → ✗ error: {e}")
            flags.append(f"{env_var} ({pid}) errored: {e}")
            continue

        # Stripe objects use attribute access, not dict .get() — read fields safely.
        product = getattr(price, "product", None)
        if product is None or isinstance(product, str):
            # unexpanded → product is the id string (or absent)
            product_name = product or "—"
        else:
            product_name = getattr(product, "name", None) or getattr(product, "id", "—")
        amount = getattr(price, "unit_amount", None)
        currency = (getattr(price, "currency", "") or "").upper()
        amount_str = f"{amount / 100:.2f} {currency}" if amount is not None else "—"
        recurring = getattr(price, "recurring", None)
        interval = getattr(recurring, "interval", "—") if recurring else "—"  # guard one-time prices
        livemode = getattr(price, "livemode", None)

        ok = "✓" if livemode is want_livemode else "✗"
        print(f"    [{label}]  {pid}  → {ok} {product_name} · {amount_str} / {interval} · livemode={livemode}")
        if livemode is not want_livemode:
            is_live_price = "a LIVE" if livemode else "a TEST"
            flags.append(f"{env_var} ({pid}) has livemode={livemode} — that's {is_live_price}-mode price; "
                         f"{expected_mode} checkout needs a {expected_mode.lower()}-mode price.")

    # ── 3. WEBHOOK ENDPOINT (item #3) ──────────────────────────────────────
    print(f"\n[3] WEBHOOK ENDPOINTS (item #3 — a {expected_mode.lower()} endpoint must point at our URL)")
    try:
        endpoints = stripe.WebhookEndpoint.list(limit=100)
        matches = [ep for ep in endpoints.auto_paging_iter()
                   if (getattr(ep, "url", "") or "").rstrip("/").endswith(WEBHOOK_PATH)]
    except stripe.error.StripeError as e:
        print(f"    ✗ could not list webhook endpoints: {e}")
        flags.append(f"Could not list webhook endpoints: {e}")
        matches = []

    if not matches:
        print(f"    ✗ no webhook endpoint found whose URL ends with {WEBHOOK_PATH}")
        flags.append(f"No {expected_mode} webhook endpoint points at {WEBHOOK_PATH} → checkout completes "
                     f"but the tier never updates. Create one in the Stripe {expected_mode} dashboard.")
    for ep in matches:
        status = getattr(ep, "status", None)
        events = getattr(ep, "enabled_events", None) or []
        wildcard = "*" in events
        missing = [] if wildcard else [e for e in NEEDED_EVENTS if e not in events]
        print(f"    URL:    {getattr(ep, 'url', '—')}")
        print(f"    status: {status}   events: {'ALL (*)' if wildcard else ', '.join(events) or '(none)'}")
        if status != "enabled":
            flags.append(f"Webhook endpoint {getattr(ep, 'url', '?')} status is '{status}', not 'enabled'.")
        if missing:
            print(f"    ✗ missing required events: {', '.join(missing)}")
            flags.append(f"Webhook endpoint missing events: {', '.join(missing)}")
        elif status == "enabled":
            print("    ✓ enabled and subscribed to all required events")

    # ── item #2 note ───────────────────────────────────────────────────────
    print("\n[#2] WEBHOOK SIGNING SECRET — NOT checkable via API")
    print("     Stripe reveals a webhook signing secret (whsec_...) only once, at creation; it is")
    print("     not retrievable by API. Confirm MANUALLY that the Render STRIPE_WEBHOOK_SECRET equals")
    print(f"     the {expected_mode} endpoint's signing secret (Stripe {expected_mode.lower()} dashboard →")
    print("     Developers → Webhooks → the endpoint → Signing secret).")
    print("     A 400 in the webhook delivery log = this is wrong.")
    if expect_live:
        print("     NOTE: the live and test endpoints have DIFFERENT secrets. If a live endpoint already")
        print("     existed and its secret was never recorded, roll it and use the new value — do not guess.")

    # ── optional DB check ──────────────────────────────────────────────────
    if args.check_db:
        check_db(args.check_db)

    # ── SUMMARY ────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    if not flags:
        print(f"RESULT: ✅ GREEN — all API-checkable items pass "
              f"(key={expected_mode}, prices resolve, webhook OK).")
        print("        Remaining manual check: item #2 (webhook signing secret) — see above.")
    else:
        target = "the live cutover" if expect_live else "Section E"
        print(f"RESULT: ⚠️  {len(flags)} FLAG(S) — resolve before {target}:")
        for i, f in enumerate(flags, 1):
            print(f"   {i}. {f}")
        print("        Plus the manual item #2 (webhook signing secret) — see above.")
    print("=" * 70)


if __name__ == "__main__":
    main()
