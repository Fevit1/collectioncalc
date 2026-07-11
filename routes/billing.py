"""
Billing Blueprint - Stripe subscription management
Routes: /api/billing/*

Handles:
- Subscription checkout (creates Stripe Checkout Session)
- Customer portal (manage/cancel subscription)
- Webhook processing (Stripe events)
- Plan status check (what plan is user on?)
- Usage enforcement (registration limits, etc.)

Plans (valuations_per_month = monthly grading cap, enforced in grading.py):
- free: $0 (25 valuations/mo, 3 Slab Guard registrations)
- pro: $4.99/mo or $49.99/yr (100 valuations/mo, 25 registrations)
- guard: $9.99/mo or $89.99/yr (250 valuations/mo, unlimited registrations + monitoring)
- dealer: $24.99/mo or $239.99/yr (1000 valuations/mo; API/bulk/white-label in development)
"""

import os
import logging
import psycopg2
from datetime import datetime
from flask import Blueprint, jsonify, request, g
from auth import require_auth, require_approved, verify_jwt, get_user_by_id

logger = logging.getLogger(__name__)

# Create blueprint
billing_bp = Blueprint('billing', __name__, url_prefix='/api/billing')

# Stripe will be imported with fallback
stripe = None
STRIPE_AVAILABLE = False

def init_modules():
    """Initialize Stripe from environment"""
    global stripe, STRIPE_AVAILABLE
    try:
        import stripe as stripe_lib
        stripe = stripe_lib
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
        if stripe.api_key:
            STRIPE_AVAILABLE = True
            print("✅ Stripe initialized")
        else:
            print("⚠️ STRIPE_SECRET_KEY not set - billing disabled")
    except ImportError:
        print("⚠️ stripe package not installed - billing disabled")


# ============================================
# PLAN CONFIGURATION
# ============================================

PLANS = {
    'free': {
        'name': 'Free',
        'monthly_price': 0,
        'annual_price': 0,
        'valuations_per_month': 25,    # monthly grading cap, enforced in grading.py via gradings_this_month
        'slab_guard_registrations': 3,
        'signature_id_per_month': 0,      # No signature ID on free (Beta: Guard/Dealer only)
        'marketplace_monitoring': False,
        'chrome_extension': False,
        'api_access': False,
        'bulk_operations': False,
        'export': False,
        'multi_photo': False,
        'extra_photos_limit': 0,          # No extra photos on free plan
        'ownership_certificates': False,
        'priority_support': False,
    },
    'pro': {
        'name': 'Pro',
        'monthly_price': 499,   # cents
        'annual_price': 4999,   # cents
        'stripe_monthly_price_id': os.environ.get('STRIPE_PRO_MONTHLY_PRICE'),
        'stripe_annual_price_id': os.environ.get('STRIPE_PRO_ANNUAL_PRICE'),
        'valuations_per_month': 100,   # monthly grading cap (was 'unlimited' — now a real per-tier limit)
        'slab_guard_registrations': 25,
        'signature_id_per_month': 0,      # No signature ID on Pro (Beta: Guard/Dealer only)
        'marketplace_monitoring': False,
        'chrome_extension': False,
        'api_access': False,
        'bulk_operations': False,
        'export': True,
        'multi_photo': True,
        'extra_photos_limit': 4,          # 4 extra photos per comic
        'ownership_certificates': False,
        'priority_support': False,
    },
    'guard': {
        'name': 'Collector + Guard',
        'monthly_price': 999,
        'annual_price': 8999,
        'stripe_monthly_price_id': os.environ.get('STRIPE_GUARD_MONTHLY_PRICE'),
        'stripe_annual_price_id': os.environ.get('STRIPE_GUARD_ANNUAL_PRICE'),
        'valuations_per_month': 250,   # monthly grading cap (was 'unlimited' — now a real per-tier limit)
        'slab_guard_registrations': -1,  # unlimited
        'signature_id_per_month': 10,     # Beta: 10/month (revisit at 87% promotion)
        'marketplace_monitoring': True,
        'chrome_extension': True,
        'api_access': False,
        'bulk_operations': False,
        'export': True,
        'multi_photo': True,
        'extra_photos_limit': 8,          # 8 extra photos per comic
        'ownership_certificates': True,
        'priority_support': True,
    },
    'dealer': {
        'name': 'Dealer',
        'monthly_price': 2499,
        'annual_price': 23999,
        'stripe_monthly_price_id': os.environ.get('STRIPE_DEALER_MONTHLY_PRICE'),
        'stripe_annual_price_id': os.environ.get('STRIPE_DEALER_ANNUAL_PRICE'),
        'valuations_per_month': 1000,  # monthly grading cap (was 'unlimited' — now a real per-tier limit)
        'slab_guard_registrations': -1,
        'signature_id_per_month': -1,     # Beta: uncapped (usage logged for visibility)
        'marketplace_monitoring': True,
        'chrome_extension': True,
        'api_access': True,
        'bulk_operations': True,
        'export': True,
        'multi_photo': True,
        'extra_photos_limit': 12,         # 12 extra photos per comic
        'ownership_certificates': True,
        'priority_support': True,
    }
}

# NOTE: STRIPE_WEBHOOK_SECRET is read at request time inside stripe_webhook()
# (like DATABASE_URL in get_db), not cached at import — so a secret injected
# after process start is picked up without a restart.


# ============================================
# HELPERS
# ============================================

def get_db():
    """Get database connection (shared pool; tuple rows)."""
    import db as _dbpool
    return _dbpool.get_db()


def get_user_plan(user_id):
    """Get the user's current plan from the database"""
    try:
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT plan, stripe_customer_id, stripe_subscription_id,
                       subscription_status, billing_period, current_period_end,
                       valuations_this_month, valuations_reset_date,
                       COALESCE(is_admin, FALSE)
                FROM users
                WHERE id = %s
            """, (user_id,))
            row = cur.fetchone()
            cur.close()
        finally:
            conn.close()

        if not row:
            return None

        return {
            'plan': row[0] or 'free',
            'stripe_customer_id': row[1],
            'stripe_subscription_id': row[2],
            'subscription_status': row[3] or 'none',
            'billing_period': row[4] or 'monthly',
            'current_period_end': row[5].isoformat() if row[5] else None,
            'valuations_this_month': row[6] or 0,
            'valuations_reset_date': row[7].isoformat() if row[7] else None,
            'is_admin': bool(row[8]),
        }
    except Exception as e:
        print(f"[Billing] Error getting user plan: {e}")
        return {'plan': 'free', 'subscription_status': 'none', 'is_admin': False}


_UNSET = object()  # distinguishes "argument omitted" from an explicit None (= write SQL NULL)


def update_user_subscription(user_id, plan, stripe_customer_id=None,
                              stripe_subscription_id=_UNSET, status=None,
                              billing_period=None, current_period_end=None):
    """Update user's subscription info in the database.

    stripe_subscription_id: omit it to leave the column untouched; pass None
    explicitly to clear it to NULL (subscription teardown). The other optional
    fields keep None-means-skip semantics.
    """
    try:
        fields = ['plan = %s']
        values = [plan]

        if stripe_customer_id is not None:
            fields.append('stripe_customer_id = %s')
            values.append(stripe_customer_id)
        if stripe_subscription_id is not _UNSET:
            fields.append('stripe_subscription_id = %s')
            values.append(stripe_subscription_id)
        if status is not None:
            fields.append('subscription_status = %s')
            values.append(status)
        if billing_period is not None:
            fields.append('billing_period = %s')
            values.append(billing_period)
        if current_period_end is not None:
            fields.append('current_period_end = %s')
            values.append(current_period_end)

        values.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)} WHERE id = %s"

        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute(query, values)
            conn.commit()
            cur.close()
        finally:
            conn.close()
        return True
    except Exception as e:
        print(f"[Billing] Error updating subscription: {e}")
        return False


def _resolve_admin_view_as_tier():
    """Admin-only 'view as tier' override for testing gated UX.

    Reads the X-View-As-Tier request header (or ?view_as= query param) and
    returns a normalized, KNOWN tier string (a PLANS key), else None. The
    caller MUST confirm the account is_admin before honoring this — a non-admin
    can never set their own effective tier, so this can only ever REDUCE an
    admin's access, never escalate anyone's.
    """
    try:
        raw = request.headers.get('X-View-As-Tier') or request.args.get('view_as')
    except RuntimeError:
        return None  # no request context (not expected for current callers)
    if not raw:
        return None
    tier = raw.strip().lower()
    return tier if tier in PLANS else None


def check_feature_access(user_id, feature):
    """Check if user's plan allows a specific feature.

    Admin policy: admins get full access by DEFAULT ("Admin"). An admin may set
    an X-View-As-Tier header (or ?view_as=) to EXPERIENCE a tier's gates instead
    of bypassing — view_as=free shows the upgrade wall, view_as=dealer shows the
    granted experience. Honored only for admins; simulates an *active*
    subscription on the named tier so paid-tier gates are actually exercised.

    NOTE: keep this admin-bypass in sync with get_signature_id_entitlement()
    below, which uses the same is_admin short-circuit. The two drifting apart
    (this one lacking the bypass) is exactly what caused the vision-gate bug.
    """
    user_plan = get_user_plan(user_id)
    if not user_plan:
        return False, "User not found"

    is_admin = bool(user_plan.get('is_admin'))
    view_as = _resolve_admin_view_as_tier() if is_admin else None

    # Admin, no override -> full access (the default).
    if is_admin and not view_as:
        return True, "Admin"

    if view_as:
        # Evaluate AS the chosen tier with a simulated active subscription.
        plan_key = view_as
        status = 'active'
    else:
        # Item 2: normalize, and surface (don't silence) unknown plan values.
        plan_key = (user_plan['plan'] or 'free').strip().lower()
        status = user_plan.get('subscription_status', 'none')
        if plan_key not in PLANS:
            print(f"[Billing] WARNING: unknown plan value "
                  f"{user_plan['plan']!r} for user_id={user_id}; "
                  f"falling back to 'free'")

    plan = PLANS.get(plan_key, PLANS['free'])

    # Check subscription is active (or free)
    if plan_key != 'free':
        if status not in ('active', 'trialing'):
            return False, "Subscription not active"

    # Check specific feature
    if feature == 'valuations':
        limit = plan['valuations_per_month']
        if limit == -1:
            return True, "Unlimited"
        used = user_plan.get('valuations_this_month', 0)
        if used >= limit:
            return False, f"Monthly limit reached ({limit} valuations)"
        return True, f"{limit - used} remaining"

    elif feature == 'slab_guard_registrations':
        limit = plan['slab_guard_registrations']
        if limit == -1:
            return True, "Unlimited"
        # Count current registrations
        try:
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM comic_registry WHERE user_id = %s AND status = 'active'",
                    (user_id,)
                )
                count = cur.fetchone()[0]
                cur.close()
            finally:
                conn.close()
            if count >= limit:
                return False, f"Registration limit reached ({limit})"
            return True, f"{limit - count} remaining"
        except:
            return True, "Unknown"

    elif feature == 'extra_photos':
        limit = plan.get('extra_photos_limit', 0)
        if limit == 0:
            return False, "Extra photos require a paid plan"
        return True, f"Up to {limit} extra photos per comic"

    elif feature in plan:
        return plan[feature], "Included" if plan[feature] else "Upgrade required"

    return False, "Unknown feature"


def get_signature_id_entitlement(user_id):
    """Per-plan signature-ID (v2 match) entitlement — PURE entitlement, no usage counting.

    Returns a dict:
      {'reason': 'ok'|'no_access'|'error',
       'limit': int,        # -1 = unlimited, 0 = none, N = N/month
       'plan': str|None,
       'is_admin': bool,
       'message': str}

    Policy (Beta): free/pro = no access (403), guard = 10/mo, dealer = unlimited
    (usage still logged for visibility), admins = unlimited. FAILS CLOSED: any DB
    error or unknown user returns reason='error' so the caller refuses the request
    rather than processing/billing it. The per-month usage check itself lives in
    the signature endpoint (it owns the sig_checks counter).
    """
    try:
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT plan, subscription_status, COALESCE(is_admin, FALSE) FROM users WHERE id = %s",
                (user_id,)
            )
            row = cur.fetchone()
            cur.close()
        finally:
            conn.close()
    except Exception as e:
        print(f"[Billing] signature entitlement check failed (failing closed): {e}")
        return {'reason': 'error', 'limit': 0, 'plan': None, 'is_admin': False,
                'message': 'Could not verify access'}

    if not row:
        return {'reason': 'error', 'limit': 0, 'plan': None, 'is_admin': False,
                'message': 'User not found'}

    plan_key = row[0] or 'free'
    status = row[1] or 'none'
    is_admin = bool(row[2])

    # Mirrors the admin short-circuit in check_feature_access() above — keep the
    # two in sync (their drift is what caused the vision-gate bug).
    if is_admin:
        return {'reason': 'ok', 'limit': -1, 'plan': plan_key, 'is_admin': True, 'message': 'Admin'}

    # Paid plans must have an active subscription
    if plan_key != 'free' and status not in ('active', 'trialing'):
        return {'reason': 'no_access', 'limit': 0, 'plan': plan_key, 'is_admin': False,
                'message': 'Subscription not active'}

    limit = PLANS.get(plan_key, PLANS['free']).get('signature_id_per_month', 0)
    if limit == 0:
        return {'reason': 'no_access', 'limit': 0, 'plan': plan_key, 'is_admin': False,
                'message': 'Signature ID is available on Guard and Dealer plans'}
    return {'reason': 'ok', 'limit': limit, 'plan': plan_key, 'is_admin': False, 'message': 'Included'}


# ============================================
# ROUTES
# ============================================

@billing_bp.route('/plans', methods=['GET'])
def get_plans():
    """Return available plans and pricing (public endpoint)"""
    public_plans = {}
    for key, plan in PLANS.items():
        public_plans[key] = {
            'name': plan['name'],
            'monthly_price': plan['monthly_price'],
            'annual_price': plan['annual_price'],
            'valuations_per_month': plan['valuations_per_month'],
            'slab_guard_registrations': plan['slab_guard_registrations'],
            'marketplace_monitoring': plan['marketplace_monitoring'],
            'chrome_extension': plan['chrome_extension'],
            'api_access': plan['api_access'],
            'export': plan['export'],
            'multi_photo': plan['multi_photo'],
            'extra_photos_limit': plan.get('extra_photos_limit', 0),
            'ownership_certificates': plan['ownership_certificates'],
        }
    return jsonify({'plans': public_plans})


@billing_bp.route('/my-plan', methods=['GET'])
@require_auth
def get_my_plan():
    """Get the current user's plan and usage"""
    user_id = g.user_id
    user_plan = get_user_plan(user_id)

    if not user_plan:
        return jsonify({'error': 'User not found'}), 404

    plan_key = user_plan['plan']
    plan_config = PLANS.get(plan_key, PLANS['free'])

    # Check registration count
    try:
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM comic_registry WHERE user_id = %s AND status = 'active'",
                (user_id,)
            )
            reg_count = cur.fetchone()[0]
            cur.close()
        finally:
            conn.close()
    except:
        reg_count = 0

    return jsonify({
        'plan': plan_key,
        'plan_name': plan_config['name'],
        'subscription_status': user_plan['subscription_status'],
        'billing_period': user_plan.get('billing_period', 'monthly'),
        'current_period_end': user_plan.get('current_period_end'),
        'usage': {
            'valuations_used': user_plan.get('valuations_this_month', 0),
            'valuations_limit': plan_config['valuations_per_month'],
            'registrations_used': reg_count,
            'registrations_limit': plan_config['slab_guard_registrations'],
        },
        'features': {
            'marketplace_monitoring': plan_config['marketplace_monitoring'],
            'chrome_extension': plan_config['chrome_extension'],
            'api_access': plan_config['api_access'],
            'export': plan_config['export'],
            'multi_photo': plan_config['multi_photo'],
            'ownership_certificates': plan_config['ownership_certificates'],
            'priority_support': plan_config['priority_support'],
        }
    })


@billing_bp.route('/check-feature', methods=['POST'])
@require_auth
def check_feature():
    """Check if the current user can use a specific feature"""
    data = request.get_json()
    feature = data.get('feature')

    if not feature:
        return jsonify({'error': 'Feature name required'}), 400

    allowed, message = check_feature_access(g.user_id, feature)
    return jsonify({
        'allowed': allowed,
        'message': message,
        'feature': feature
    })


@billing_bp.route('/create-checkout', methods=['POST'])
@require_auth
def create_checkout_session():
    """Create a Stripe Checkout Session for subscribing"""
    if not STRIPE_AVAILABLE:
        return jsonify({'error': 'Billing not configured'}), 503

    data = request.get_json()
    plan = data.get('plan')
    billing_period = data.get('billing_period', 'monthly')

    # Dealer is "coming soon" — its features are unbuilt, so refuse checkout
    # server-side (enforce the pricing-page label, don't just display it). The
    # page routes Dealer to /contact.html; this is the belt for a direct API call.
    if plan == 'dealer':
        return jsonify({
            'error': 'The Dealer plan is coming soon — contact us for early access.',
            'coming_soon': True
        }), 400

    if plan not in ('pro', 'guard'):
        return jsonify({'error': 'Invalid plan'}), 400

    plan_config = PLANS[plan]
    price_key = f'stripe_{billing_period}_price_id'
    price_id = plan_config.get(price_key)

    if not price_id:
        return jsonify({'error': f'Price not configured for {plan} {billing_period}'}), 500

    user_id = g.user_id
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Stacking guard (additive): every create-checkout mints a BRAND-NEW
    # subscription, so a user who already has a live sub and clicks "Change Plan"
    # (→ pricing → checkout) would stack a second paid subscription on the same
    # customer. Refuse here and route plan CHANGES to the customer portal, which
    # modifies the existing sub in place. Only block genuinely-live subs
    # (active/trialing/past_due) that have a real Stripe sub id — canceled /
    # incomplete / unpaid users (sub id nulled, or never live) may check out
    # again to (re)subscribe. On a DB read error get_user_plan() returns a dict
    # with no sub id, so this fails OPEN (allows checkout) rather than blocking a
    # legitimate first-time subscriber.
    user_plan = get_user_plan(user_id)
    if (user_plan and user_plan.get('stripe_subscription_id')
            and user_plan.get('subscription_status') in ('active', 'trialing', 'past_due')):
        return jsonify({
            'error': 'You already have an active subscription. '
                     'Change your plan from the billing portal.',
            'code': 'existing_subscription',
            'manage_via': 'customer_portal',
        }), 409

    # Get or create Stripe customer
    customer_id = user_plan.get('stripe_customer_id') if user_plan else None

    try:
        if not customer_id:
            customer = stripe.Customer.create(
                email=user.get('email'),
                metadata={'user_id': str(user_id)}
            )
            customer_id = customer.id
            update_user_subscription(user_id, user_plan.get('plan', 'free'),
                                      stripe_customer_id=customer_id)

        # Build success/cancel URLs
        base_url = os.environ.get('FRONTEND_URL', 'https://slabworthy.com')

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            subscription_data={
                'trial_period_days': 14,
                'metadata': {
                    'user_id': str(user_id),
                    'plan': plan,
                }
            },
            success_url=f'{base_url}/account.html?session_id={{CHECKOUT_SESSION_ID}}&status=success',
            cancel_url=f'{base_url}/pricing.html?status=cancelled',
            metadata={
                'user_id': str(user_id),
                'plan': plan,
                'billing_period': billing_period,
            }
        )

        return jsonify({
            'checkout_url': session.url,
            'session_id': session.id
        })

    except stripe.error.StripeError as e:
        print(f"[Billing] Stripe error: {e}")
        return jsonify({'error': 'Payment service error'}), 500


@billing_bp.route('/customer-portal', methods=['POST'])
@require_auth
def create_customer_portal():
    """Create a Stripe Customer Portal session for managing subscription"""
    if not STRIPE_AVAILABLE:
        return jsonify({'error': 'Billing not configured'}), 503

    user_id = g.user_id
    user_plan = get_user_plan(user_id)

    if not user_plan or not user_plan.get('stripe_customer_id'):
        return jsonify({'error': 'No billing account found'}), 404

    try:
        base_url = os.environ.get('FRONTEND_URL', 'https://slabworthy.com')
        session = stripe.billing_portal.Session.create(
            customer=user_plan['stripe_customer_id'],
            return_url=f'{base_url}/account.html'
        )
        return jsonify({'portal_url': session.url})

    except stripe.error.StripeError as e:
        print(f"[Billing] Portal error: {e}")
        return jsonify({'error': 'Payment service error'}), 500


@billing_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    if not STRIPE_AVAILABLE:
        return jsonify({'error': 'Billing not configured'}), 503

    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    # Read the secret per-request (not at import) so late env injection is picked
    # up without a restart. A webhook secret is MANDATORY: without it we cannot
    # prove the event came from Stripe, and processing an unverified event would
    # let anyone forge subscription state (e.g. POST a checkout.session.completed
    # to self-upgrade to a paid tier). Fail loud — never degrade to unverified.
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    if not webhook_secret:
        print("[Billing] ERROR: STRIPE_WEBHOOK_SECRET is not set — refusing to "
              "process webhook (would be unverified). Set the secret in Render.")
        return jsonify({'error': 'Webhook secret not configured'}), 500

    # Verify webhook signature. Any failure → reject, do not process.
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        print(f"[Billing] Webhook verification failed: {e}")
        return jsonify({'error': 'Invalid signature'}), 400

    event_type = event.get('type', '')
    event_id = event.get('id', '?')
    data = event.get('data', {}).get('object', {})

    print(f"[Billing] Webhook: {event_type} (id={event_id})")

    # ---- Handle events ----
    # Each handler is isolated in a try/except so that an exception in one
    # NEVER bubbles up as a bare 500 with no context. Before this, a handler
    # crash returned an opaque 500 and Stripe retried it — but a deterministic
    # code bug crashes identically on every retry, so the tier stayed un-flipped
    # AND no traceback was easy to find. Now we log the FULL traceback with the
    # event type + id, then ACK with 200 so Stripe stops retry-storming a bug it
    # can't fix by retrying. After deploying a fix, replay the event from the
    # Stripe dashboard (Developers → Webhooks → the event → Resend).
    handlers = {
        'checkout.session.completed': handle_checkout_completed,
        'customer.subscription.updated': handle_subscription_updated,
        'customer.subscription.deleted': handle_subscription_deleted,
        'invoice.payment_succeeded': handle_payment_succeeded,
        'invoice.payment_failed': handle_payment_failed,
    }
    handler = handlers.get(event_type)
    if handler:
        try:
            handler(data)
        except Exception:
            logger.exception(
                "[Billing] Webhook handler FAILED: type=%s id=%s", event_type, event_id
            )
            return jsonify({'received': True, 'handler_error': True}), 200

    return jsonify({'received': True})


# ============================================
# WEBHOOK EVENT HANDLERS
# ============================================

def _subscription_period_end(subscription):
    """current_period_end as a datetime, tolerant of Stripe's API change.

    Stripe moved `current_period_end` off the Subscription object and onto its
    items (API versions 2025-03-31+). Read the top-level field first, then fall
    back to the first item's value. Returns None if neither is present (e.g. a
    brand-new trialing sub before the first period is computed)."""
    ts = subscription.get('current_period_end')
    if not ts:
        try:
            items = (subscription.get('items') or {}).get('data') or []
            if items:
                ts = items[0].get('current_period_end')
        except Exception:
            ts = None
    return datetime.fromtimestamp(ts) if ts else None


def handle_checkout_completed(session):
    """User completed checkout - activate their plan.

    Writes the REAL subscription status (trialing vs active) by retrieving the
    subscription, instead of hardcoding 'active'. Our create-checkout always
    attaches a 14-day trial, so a successful checkout lands the sub in
    `trialing` — check_feature_access treats trialing as full access, so the
    tier is live immediately and flips to active when Stripe bills the trial.
    If the retrieve fails we still flip the tier (default 'trialing') so a
    transient Stripe read never leaves a paying user stuck on free."""
    metadata = session.get('metadata') or {}
    user_id = metadata.get('user_id')
    plan = metadata.get('plan')
    billing_period = metadata.get('billing_period', 'monthly')
    subscription_id = session.get('subscription')
    customer_id = session.get('customer')

    if not user_id or not plan:
        print(f"[Billing] Checkout missing metadata: {dict(metadata)}")
        return

    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        print(f"[Billing] Checkout has non-numeric user_id: {user_id!r}")
        return

    # Default to 'trialing' (correct for our trial checkout) and resolve the real
    # status + period end from the subscription when we can.
    status = 'trialing'
    period_end_dt = None
    if subscription_id and STRIPE_AVAILABLE:
        try:
            sub = stripe.Subscription.retrieve(subscription_id)
            status = sub.get('status') or status
            period_end_dt = _subscription_period_end(sub)
        except Exception:
            logger.exception(
                "[Billing] Could not retrieve subscription %s for checkout "
                "(user=%s) — flipping tier with default status=%s",
                subscription_id, uid, status,
            )

    print(f"[Billing] Checkout completed: user={uid}, plan={plan}, status={status}")

    ok = update_user_subscription(
        uid, plan,
        stripe_customer_id=customer_id,
        stripe_subscription_id=subscription_id,
        status=status,
        billing_period=billing_period,
        current_period_end=period_end_dt,
    )
    if not ok:
        # update_user_subscription swallows DB errors and returns False; surface
        # it loudly so a silent DB failure here is greppable in the logs.
        logger.error(
            "[Billing] update_user_subscription returned False for checkout "
            "(user=%s, plan=%s) — tier did NOT flip.", uid, plan,
        )


def handle_subscription_updated(subscription):
    """Subscription changed (upgrade, downgrade, trial end, etc.)"""
    customer_id = subscription.get('customer')
    status = subscription.get('status')  # active, trialing, past_due, canceled, unpaid
    sub_id = subscription.get('id')

    # Get plan from subscription metadata or price lookup
    metadata = subscription.get('metadata', {})
    plan = metadata.get('plan')

    # Get period end (tolerant of Stripe moving the field onto items)
    period_end_dt = _subscription_period_end(subscription)

    if not customer_id:
        return

    # Find user by stripe_customer_id
    try:
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE stripe_customer_id = %s", (customer_id,))
            row = cur.fetchone()
            cur.close()
        finally:
            conn.close()

        if row:
            user_id = row[0]
            update_user_subscription(
                user_id,
                plan or 'free',
                stripe_subscription_id=sub_id,
                status=status,
                current_period_end=period_end_dt
            )
            print(f"[Billing] Subscription updated: user={user_id}, status={status}")
    except Exception as e:
        print(f"[Billing] Error handling subscription update: {e}")


def handle_subscription_deleted(subscription):
    """Subscription canceled - revert to free.

    Only downgrades when the deleted subscription IS the user's sub of record
    (users.stripe_subscription_id). With stacked subs, canceling a stray one
    must not revert a user who is still paying on another.
    """
    customer_id = subscription.get('customer')
    deleted_sub_id = subscription.get('id')

    if not customer_id:
        return

    try:
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, stripe_subscription_id FROM users "
                "WHERE stripe_customer_id = %s",
                (customer_id,),
            )
            row = cur.fetchone()
            cur.close()
        finally:
            conn.close()

        if row:
            user_id, sub_of_record = row
            if sub_of_record and deleted_sub_id and sub_of_record != deleted_sub_id:
                print(f"[Billing] Subscription deleted: user={user_id} — ignoring "
                      f"{deleted_sub_id}, not the sub of record ({sub_of_record}); "
                      f"plan unchanged")
                return
            update_user_subscription(
                user_id, 'free',
                stripe_subscription_id=None,  # explicit None → clears to NULL
                status='canceled'
            )
            print(f"[Billing] Subscription deleted: user={user_id} → free "
                  f"(sub {deleted_sub_id} cleared)")
    except Exception as e:
        print(f"[Billing] Error handling subscription deletion: {e}")


def handle_payment_succeeded(invoice):
    """Payment went through - log it"""
    customer_id = invoice.get('customer')
    amount = invoice.get('amount_paid', 0)
    print(f"[Billing] Payment succeeded: customer={customer_id}, amount=${amount/100:.2f}")


def handle_payment_failed(invoice):
    """Payment failed - mark subscription as past_due"""
    customer_id = invoice.get('customer')

    if not customer_id:
        return

    try:
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, plan FROM users WHERE stripe_customer_id = %s", (customer_id,))
            row = cur.fetchone()
            cur.close()
        finally:
            conn.close()

        if row:
            user_id = row[0]
            current_plan = row[1]
            update_user_subscription(user_id, current_plan, status='past_due')
            print(f"[Billing] Payment failed: user={user_id}, status→past_due")
    except Exception as e:
        print(f"[Billing] Error handling payment failure: {e}")


# ============================================
# USAGE TRACKING
# ============================================

@billing_bp.route('/record-valuation', methods=['POST'])
@require_auth
def record_valuation():
    """Increment the user's valuation count for the month"""
    user_id = g.user_id

    try:
        conn = get_db()
        try:
            cur = conn.cursor()

            # Check if reset date has passed
            cur.execute(
                "SELECT valuations_this_month, valuations_reset_date FROM users WHERE id = %s",
                (user_id,)
            )
            row = cur.fetchone()

            if row:
                count = row[0] or 0
                reset_date = row[1]
                now = datetime.now()

                # Reset counter if we've entered a new month
                if not reset_date or now >= reset_date:
                    # Set reset to first of next month
                    if now.month == 12:
                        next_reset = datetime(now.year + 1, 1, 1)
                    else:
                        next_reset = datetime(now.year, now.month + 1, 1)

                    cur.execute("""
                        UPDATE users
                        SET valuations_this_month = 1, valuations_reset_date = %s
                        WHERE id = %s
                    """, (next_reset, user_id))
                else:
                    cur.execute("""
                        UPDATE users
                        SET valuations_this_month = valuations_this_month + 1
                        WHERE id = %s
                    """, (user_id,))

            conn.commit()
            cur.close()
        finally:
            conn.close()

        return jsonify({'recorded': True})
    except Exception as e:
        print(f"[Billing] Error recording valuation: {e}")
        return jsonify({'error': 'Failed to record usage'}), 500
