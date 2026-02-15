"""
Billing Blueprint - Stripe subscription management
Routes: /api/billing/*

Handles:
- Subscription checkout (creates Stripe Checkout Session)
- Customer portal (manage/cancel subscription)
- Webhook processing (Stripe events)
- Plan status check (what plan is user on?)
- Usage enforcement (registration limits, etc.)

Plans:
- free: $0 (10 valuations/mo, 3 Slab Guard registrations)
- pro: $4.99/mo or $49.99/yr (unlimited valuations, 25 registrations)
- guard: $9.99/mo or $89.99/yr (unlimited everything + monitoring)
- dealer: $24.99/mo or $239.99/yr (API access, bulk ops, white-label)
"""

import os
import json
import psycopg2
from datetime import datetime
from flask import Blueprint, jsonify, request, g
from auth import require_auth, require_approved, verify_jwt, get_user_by_id

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
        'valuations_per_month': 10,
        'slab_guard_registrations': 3,
        'marketplace_monitoring': False,
        'chrome_extension': False,
        'api_access': False,
        'bulk_operations': False,
        'export': False,
        'multi_photo': False,
        'ownership_certificates': False,
        'priority_support': False,
    },
    'pro': {
        'name': 'Pro',
        'monthly_price': 499,   # cents
        'annual_price': 4999,   # cents
        'stripe_monthly_price_id': os.environ.get('STRIPE_PRO_MONTHLY_PRICE'),
        'stripe_annual_price_id': os.environ.get('STRIPE_PRO_ANNUAL_PRICE'),
        'valuations_per_month': -1,  # unlimited
        'slab_guard_registrations': 25,
        'marketplace_monitoring': False,
        'chrome_extension': False,
        'api_access': False,
        'bulk_operations': False,
        'export': True,
        'multi_photo': True,
        'ownership_certificates': False,
        'priority_support': False,
    },
    'guard': {
        'name': 'Collector + Guard',
        'monthly_price': 999,
        'annual_price': 8999,
        'stripe_monthly_price_id': os.environ.get('STRIPE_GUARD_MONTHLY_PRICE'),
        'stripe_annual_price_id': os.environ.get('STRIPE_GUARD_ANNUAL_PRICE'),
        'valuations_per_month': -1,
        'slab_guard_registrations': -1,  # unlimited
        'marketplace_monitoring': True,
        'chrome_extension': True,
        'api_access': False,
        'bulk_operations': False,
        'export': True,
        'multi_photo': True,
        'ownership_certificates': True,
        'priority_support': True,
    },
    'dealer': {
        'name': 'Dealer',
        'monthly_price': 2499,
        'annual_price': 23999,
        'stripe_monthly_price_id': os.environ.get('STRIPE_DEALER_MONTHLY_PRICE'),
        'stripe_annual_price_id': os.environ.get('STRIPE_DEALER_ANNUAL_PRICE'),
        'valuations_per_month': -1,
        'slab_guard_registrations': -1,
        'marketplace_monitoring': True,
        'chrome_extension': True,
        'api_access': True,
        'bulk_operations': True,
        'export': True,
        'multi_photo': True,
        'ownership_certificates': True,
        'priority_support': True,
    }
}

WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')


# ============================================
# HELPERS
# ============================================

def get_db():
    """Get database connection"""
    database_url = os.environ.get('DATABASE_URL')
    return psycopg2.connect(database_url)


def get_user_plan(user_id):
    """Get the user's current plan from the database"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT plan, stripe_customer_id, stripe_subscription_id,
                   subscription_status, billing_period, current_period_end,
                   valuations_this_month, valuations_reset_date
            FROM users
            WHERE id = %s
        """, (user_id,))
        row = cur.fetchone()
        cur.close()
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
        }
    except Exception as e:
        print(f"[Billing] Error getting user plan: {e}")
        return {'plan': 'free', 'subscription_status': 'none'}


def update_user_subscription(user_id, plan, stripe_customer_id=None,
                              stripe_subscription_id=None, status=None,
                              billing_period=None, current_period_end=None):
    """Update user's subscription info in the database"""
    try:
        conn = get_db()
        cur = conn.cursor()

        fields = ['plan = %s']
        values = [plan]

        if stripe_customer_id is not None:
            fields.append('stripe_customer_id = %s')
            values.append(stripe_customer_id)
        if stripe_subscription_id is not None:
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
        cur.execute(query, values)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[Billing] Error updating subscription: {e}")
        return False


def check_feature_access(user_id, feature):
    """Check if user's plan allows a specific feature"""
    user_plan = get_user_plan(user_id)
    if not user_plan:
        return False, "User not found"

    plan_key = user_plan['plan']
    plan = PLANS.get(plan_key, PLANS['free'])

    # Check subscription is active (or free)
    if plan_key != 'free':
        status = user_plan.get('subscription_status', 'none')
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
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM comic_registry WHERE user_id = %s AND status = 'active'",
                (user_id,)
            )
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            if count >= limit:
                return False, f"Registration limit reached ({limit})"
            return True, f"{limit - count} remaining"
        except:
            return True, "Unknown"

    elif feature in plan:
        return plan[feature], "Included" if plan[feature] else "Upgrade required"

    return False, "Unknown feature"


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
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM comic_registry WHERE user_id = %s AND status = 'active'",
            (user_id,)
        )
        reg_count = cur.fetchone()[0]
        cur.close()
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

    if plan not in ('pro', 'guard', 'dealer'):
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

    # Get or create Stripe customer
    user_plan = get_user_plan(user_id)
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

    # Verify webhook signature
    try:
        if WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload, sig_header, WEBHOOK_SECRET
            )
        else:
            # Dev mode: parse without verification
            event = json.loads(payload)
            print("⚠️ Webhook signature not verified (no secret configured)")
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        print(f"[Billing] Webhook verification failed: {e}")
        return jsonify({'error': 'Invalid signature'}), 400

    event_type = event.get('type', '')
    data = event.get('data', {}).get('object', {})

    print(f"[Billing] Webhook: {event_type}")

    # ---- Handle events ----

    if event_type == 'checkout.session.completed':
        handle_checkout_completed(data)

    elif event_type == 'customer.subscription.updated':
        handle_subscription_updated(data)

    elif event_type == 'customer.subscription.deleted':
        handle_subscription_deleted(data)

    elif event_type == 'invoice.payment_succeeded':
        handle_payment_succeeded(data)

    elif event_type == 'invoice.payment_failed':
        handle_payment_failed(data)

    return jsonify({'received': True})


# ============================================
# WEBHOOK EVENT HANDLERS
# ============================================

def handle_checkout_completed(session):
    """User completed checkout - activate their plan"""
    metadata = session.get('metadata', {})
    user_id = metadata.get('user_id')
    plan = metadata.get('plan')
    billing_period = metadata.get('billing_period', 'monthly')
    subscription_id = session.get('subscription')
    customer_id = session.get('customer')

    if not user_id or not plan:
        print(f"[Billing] Checkout missing metadata: {metadata}")
        return

    print(f"[Billing] Checkout completed: user={user_id}, plan={plan}")

    update_user_subscription(
        int(user_id), plan,
        stripe_customer_id=customer_id,
        stripe_subscription_id=subscription_id,
        status='active',
        billing_period=billing_period
    )


def handle_subscription_updated(subscription):
    """Subscription changed (upgrade, downgrade, trial end, etc.)"""
    customer_id = subscription.get('customer')
    status = subscription.get('status')  # active, trialing, past_due, canceled, unpaid
    sub_id = subscription.get('id')

    # Get plan from subscription metadata or price lookup
    metadata = subscription.get('metadata', {})
    plan = metadata.get('plan')

    # Get period end
    period_end = subscription.get('current_period_end')
    period_end_dt = datetime.fromtimestamp(period_end) if period_end else None

    if not customer_id:
        return

    # Find user by stripe_customer_id
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE stripe_customer_id = %s", (customer_id,))
        row = cur.fetchone()
        cur.close()
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
    """Subscription canceled - revert to free"""
    customer_id = subscription.get('customer')

    if not customer_id:
        return

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE stripe_customer_id = %s", (customer_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            user_id = row[0]
            update_user_subscription(
                user_id, 'free',
                stripe_subscription_id=None,
                status='canceled'
            )
            print(f"[Billing] Subscription deleted: user={user_id} → free")
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
        cur = conn.cursor()
        cur.execute("SELECT id, plan FROM users WHERE stripe_customer_id = %s", (customer_id,))
        row = cur.fetchone()
        cur.close()
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
        conn.close()

        return jsonify({'recorded': True})
    except Exception as e:
        print(f"[Billing] Error recording valuation: {e}")
        return jsonify({'error': 'Failed to record usage'}), 500
