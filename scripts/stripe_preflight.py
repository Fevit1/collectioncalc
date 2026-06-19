#!/usr/bin/env python
"""
Stripe TEST-mode pre-flight check for Section E (billing end-to-end).

╔══════════════════════════════════════════════════════════════════════════╗
║  READ-ONLY — NO SIDE EFFECTS.                                             ║
║  This script ONLY performs list/retrieve (GET) calls against the Stripe  ║
║  API. It does NOT create, modify, or delete anything: no customers, no    ║
║  checkout sessions, no subscriptions, no webhook changes, no DB writes.   ║
║  The only Stripe calls used are:                                          ║
║      stripe.Price.retrieve(...)        (read)                             ║
║      stripe.WebhookEndpoint.list(...)  (read)                             ║
║  Safe to run against production test-mode keys.                           ║
╚══════════════════════════════════════════════════════════════════════════╝

Confirms (from the Stripe runbook) the items you couldn't see from the repo:
  #1 STRIPE_*_PRICE env values resolve as TEST-mode price IDs   → CHECKED here
  #3 a test-mode webhook endpoint points at /api/billing/webhook → CHECKED here
  #2 STRIPE_WEBHOOK_SECRET matches the test endpoint's secret    → NOT checkable
     (Stripe shows a webhook signing secret only once, at creation; it is not
      retrievable via API. This stays a manual dashboard check — see summary.)

Uses STRIPE_SECRET_KEY from the environment (the sk_test_ one). Never hardcodes a key.

Run:
    python scripts/stripe_preflight.py
(Run it where STRIPE_SECRET_KEY is set — e.g. the Render shell, where the env is
 already present — or set $env:STRIPE_SECRET_KEY for the session locally.)
"""

import os
import sys

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


def main():
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        print("ERROR: STRIPE_SECRET_KEY is not set in this environment. Nothing to check.")
        sys.exit(1)
    stripe.api_key = key

    print("=" * 70)
    print("Stripe pre-flight (READ-ONLY)")
    print("=" * 70)

    # ── 1. KEY MODE ────────────────────────────────────────────────────────
    print("\n[1] KEY MODE")
    if key.startswith(("sk_test_", "rk_test_")):
        mode = "TEST"
    elif key.startswith(("sk_live_", "rk_live_")):
        mode = "LIVE"
    else:
        mode = "UNKNOWN"
    print(f"    Secret key: ...{key[-4:]}  → mode: {mode}")
    if mode != "TEST":
        flags.append(f"Key is {mode}, not TEST — Section E must run on a sk_test_ key.")

    # ── 2. PRICE IDS (item #1) ─────────────────────────────────────────────
    print("\n[2] PRICE IDS (item #1 — must resolve in TEST mode, livemode=false)")
    for label, env_var in PRICE_ENV_VARS:
        pid = os.environ.get(env_var)
        if not pid:
            print(f"    [{label}]  {env_var} is NOT SET")
            flags.append(f"{env_var} not set → '{label}' checkout returns 'Price not configured'.")
            continue
        try:
            price = stripe.Price.retrieve(pid, expand=["product"])
        except stripe.error.InvalidRequestError as e:
            print(f"    [{label}]  {pid}  → ✗ DOES NOT RESOLVE: {e.user_message or e}")
            flags.append(f"{env_var} ({pid}) doesn't resolve on this key → 'No such price' at checkout "
                         f"(likely a LIVE price id set while running TEST).")
            continue
        except stripe.error.StripeError as e:
            print(f"    [{label}]  {pid}  → ✗ error: {e}")
            flags.append(f"{env_var} ({pid}) errored: {e}")
            continue

        product = price.get("product")
        product_name = product.get("name") if isinstance(product, dict) else str(product)
        amount = price.get("unit_amount")
        amount_str = f"{amount / 100:.2f} {price.get('currency', '').upper()}" if amount is not None else "—"
        recurring = price.get("recurring") or {}
        interval = recurring.get("interval", "—")
        livemode = price.get("livemode")
        ok = "✓" if livemode is False else "✗"
        print(f"    [{label}]  {pid}  → {ok} {product_name} · {amount_str} / {interval} · livemode={livemode}")
        if livemode is not False:
            flags.append(f"{env_var} ({pid}) has livemode={livemode} — that's a LIVE price; "
                         f"TEST checkout needs a test-mode price.")

    # ── 3. WEBHOOK ENDPOINT (item #3) ──────────────────────────────────────
    print("\n[3] WEBHOOK ENDPOINTS (item #3 — a test endpoint must point at our URL)")
    try:
        endpoints = stripe.WebhookEndpoint.list(limit=100)
        matches = [ep for ep in endpoints.auto_paging_iter()
                   if (ep.get("url") or "").rstrip("/").endswith(WEBHOOK_PATH)]
    except stripe.error.StripeError as e:
        print(f"    ✗ could not list webhook endpoints: {e}")
        flags.append(f"Could not list webhook endpoints: {e}")
        matches = []

    if not matches:
        print(f"    ✗ no webhook endpoint found whose URL ends with {WEBHOOK_PATH}")
        flags.append(f"No TEST webhook endpoint points at {WEBHOOK_PATH} → checkout completes but the "
                     f"tier never updates. Create one in the Stripe TEST dashboard.")
    for ep in matches:
        status = ep.get("status")
        events = ep.get("enabled_events") or []
        wildcard = "*" in events
        missing = [] if wildcard else [e for e in NEEDED_EVENTS if e not in events]
        print(f"    URL:    {ep.get('url')}")
        print(f"    status: {status}   events: {'ALL (*)' if wildcard else ', '.join(events) or '(none)'}")
        if status != "enabled":
            flags.append(f"Webhook endpoint {ep.get('url')} status is '{status}', not 'enabled'.")
        if missing:
            print(f"    ✗ missing required events: {', '.join(missing)}")
            flags.append(f"Webhook endpoint missing events: {', '.join(missing)}")
        elif status == "enabled":
            print("    ✓ enabled and subscribed to all required events")

    # ── item #2 note ───────────────────────────────────────────────────────
    print("\n[#2] WEBHOOK SIGNING SECRET — NOT checkable via API")
    print("     Stripe reveals a webhook signing secret (whsec_...) only once, at creation; it is")
    print("     not retrievable by API. Confirm MANUALLY that the Render STRIPE_WEBHOOK_SECRET equals")
    print("     the TEST endpoint's signing secret (Stripe test dashboard → Developers → Webhooks →")
    print("     the endpoint → Signing secret). A 400 in the webhook delivery log = this is wrong.")

    # ── SUMMARY ────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    if not flags:
        print("RESULT: ✅ GREEN — all API-checkable items pass (key=TEST, prices resolve, webhook OK).")
        print("        Remaining manual check: item #2 (webhook signing secret) — see above.")
    else:
        print(f"RESULT: ⚠️  {len(flags)} FLAG(S) — resolve before running Section E:")
        for i, f in enumerate(flags, 1):
            print(f"   {i}. {f}")
        print("        Plus the manual item #2 (webhook signing secret) — see above.")
    print("=" * 70)


if __name__ == "__main__":
    main()
