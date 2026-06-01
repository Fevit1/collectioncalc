"""
Dependency Monitor
Checks third-party service deprecations and alerts via email + admin dashboard.
Piggybacks on Render's health-check polling (no cron needed).
Each check is cached 24 hours independently.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 MONITORED SERVICES — update this when adding new third-party integrations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Service           │ Check Method                  │ Source                      │ What We Watch
 ──────────────────┼───────────────────────────────┼─────────────────────────────┼─────────────────────
 Anthropic         │ check_anthropic()             │ deprecations.info JSON API  │ Model retirements
 eBay              │ check_ebay()                  │ developer.ebay.com RSS feed │ API deprecations
 eBay acct-del self│ check_ebay_account_deletion() │ our own live endpoint (GET) │ Notification endpoint up + valid challenge
 Stripe            │ check_stripe()                │ PyPI version check          │ SDK version drift

 TO ADD A NEW SERVICE:
 1. Write a check_<service>() function that returns a list of warning dicts:
    [{"service": "Name", "item": "what", "detail": "why", "date": "when",
      "url": "link", "action": "what to do"}]
 2. Add a cache entry in _caches below
 3. Call your function from check_all()
 4. Update the table above
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import re
import time
import hashlib
import xml.etree.ElementTree as ET
import requests
from models import MODEL_CHAINS

try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False

# ── Config ──
DEPRECATIONS_API = "https://deprecations.info/v1/deprecations.json"
EBAY_RSS_URL = "https://developer.ebay.com/rss/api-status"
PYPI_STRIPE_URL = "https://pypi.org/pypi/stripe/json"
CACHE_TTL = 86400  # 24 hours

# Self-health check: our OWN eBay marketplace account-deletion endpoint.
# This URL MUST mirror EBAY_ACCOUNT_DELETION_ENDPOINT in routes/ebay.py and the
# URL registered in the eBay developer portal. It is intentionally kept as an
# independent literal (not imported from routes/ebay.py): if the route's
# constant ever drifts from this one, the recomputed challenge hash won't match
# and this self-check will trip — which is exactly the endpoint-string drift we
# want to catch.
EBAY_ACCOUNT_DELETION_ENDPOINT = "https://collectioncalc-docker.onrender.com/api/ebay/account-deletion"
# Fixed, obviously-synthetic probe. Challenge codes are never persisted or
# matched against any state (the handler only hashes them), so this cannot
# collide with real eBay traffic, and a GET never reaches the POST deletion path.
EBAY_DELETION_PROBE_CODE = "slabworthy-monitor-probe-DO-NOT-DELETE"

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'noreply@slabworthy.com')

if RESEND_API_KEY and RESEND_AVAILABLE:
    resend.api_key = RESEND_API_KEY

# eBay APIs we depend on (from ebay_listing.py and ebay_oauth.py)
EBAY_APIS_WE_USE = [
    'sell/inventory/v1',
    'sell/account/v1',
    'sell/fulfillment',
    'sell/marketing',
    'identity/v1/oauth2',
    'commerce/media/v1',
    'commerce/identity',
]

# Keywords that signal a deprecation notice
DEPRECATION_KEYWORDS = re.compile(
    r'deprecat|decommission|end.of.life|sunset|shutdown|retire|breaking.change',
    re.IGNORECASE
)

# ── Per-service caches ──
_caches = {
    'anthropic':            {"data": [], "fetched_at": 0},
    'ebay':                 {"data": [], "fetched_at": 0},
    'stripe':               {"data": [], "fetched_at": 0},
    'ebay_account_deletion': {"data": [], "fetched_at": 0},
}
_emailed_keys = set()  # Track what we've emailed about (service:identifier)


# =============================================
# ANTHROPIC — via deprecations.info
# =============================================

def _all_model_ids():
    ids = set()
    for chain in MODEL_CHAINS.values():
        ids.update(chain)
    return ids


def _tier_for_model(model_id):
    tiers = []
    for tier, chain in MODEL_CHAINS.items():
        if model_id in chain:
            tiers.append(tier)
    return tiers


def check_anthropic(force=False):
    """Check deprecations.info for Anthropic model retirements."""
    cache = _caches['anthropic']
    now = time.time()
    if not force and (now - cache["fetched_at"]) < CACHE_TTL:
        return cache["data"]

    try:
        resp = requests.get(DEPRECATIONS_API, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[DependencyMonitor] Anthropic check failed: {e}")
        return cache["data"] or []

    our_models = _all_model_ids()
    warnings = []

    for item in data.get("items", []):
        dep = item.get("_deprecation", {})
        provider = dep.get("provider", "")
        if provider.lower() not in ("anthropic", "ant"):
            continue
        model_name = dep.get("model_name", "")
        for our_model in our_models:
            if our_model == model_name or our_model in model_name or model_name in our_model:
                warnings.append({
                    "service": "Anthropic",
                    "item": our_model,
                    "detail": f"Model retiring",
                    "date": dep.get("shutdown_date", "unknown"),
                    "url": dep.get("url", ""),
                    "action": f"Update models.py — replace in {', '.join(_tier_for_model(our_model))} tier",
                })

    cache["data"] = warnings
    cache["fetched_at"] = now
    return warnings


# =============================================
# EBAY — via RSS feed
# =============================================

def check_ebay(force=False):
    """Check eBay developer RSS for deprecation notices affecting our APIs."""
    cache = _caches['ebay']
    now = time.time()
    if not force and (now - cache["fetched_at"]) < CACHE_TTL:
        return cache["data"]

    try:
        resp = requests.get(EBAY_RSS_URL, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception as e:
        print(f"[DependencyMonitor] eBay RSS check failed: {e}")
        return cache["data"] or []

    warnings = []
    # RSS items are under channel/item
    for item in root.findall('.//item'):
        title = (item.findtext('title') or '').strip()
        desc = (item.findtext('description') or '').strip()
        pub_date = (item.findtext('pubDate') or '').strip()
        link = (item.findtext('link') or '').strip()
        combined = f"{title} {desc}"

        # Only care about deprecation-related notices
        if not DEPRECATION_KEYWORDS.search(combined):
            continue

        # Check if any of our eBay APIs are mentioned
        for api in EBAY_APIS_WE_USE:
            # Match on the API path or a simplified version
            api_short = api.split('/')[0]  # e.g. "sell", "identity", "commerce"
            if api.lower() in combined.lower() or api_short.lower() in combined.lower():
                warnings.append({
                    "service": "eBay",
                    "item": api,
                    "detail": title[:120],
                    "date": pub_date,
                    "url": link,
                    "action": f"Review eBay notice and update {api} integration",
                })
                break  # One warning per RSS item is enough

    cache["data"] = warnings
    cache["fetched_at"] = now
    return warnings


# =============================================
# EBAY ACCOUNT-DELETION ENDPOINT — self-health check
# =============================================
# NOTE: distinct from check_ebay() above. That watches eBay's RSS for API
# deprecations (their changes break us). THIS watches our OWN registered
# marketplace account-deletion notification endpoint (our outage breaks
# compliance). eBay deactivates app keys if this endpoint fails their
# validation — and they notified us before our own monitoring did once. This
# closes that gap. Two different failure modes → two separate checks/alerts.

def check_ebay_account_deletion(force=False):
    """Probe our own eBay account-deletion endpoint's GET challenge-response.

    Exercises exactly the path eBay's validator uses:
      GET <endpoint>?challenge_code=<probe>  ->  200 {"challengeResponse": "<sha256>"}

    Failure states (any of these emit a warning): non-200 (405 = GET handler
    gone, 503 = service suspended, 5xx = token unset/error), timeout/connection
    error, non-JSON body, missing/empty challengeResponse, or a challengeResponse
    that doesn't match the independently recomputed canonical hash.
    """
    cache = _caches['ebay_account_deletion']
    now = time.time()
    if not force and (now - cache["fetched_at"]) < CACHE_TTL:
        return cache["data"]

    url = EBAY_ACCOUNT_DELETION_ENDPOINT
    probe = EBAY_DELETION_PROBE_CODE

    def _fail(detail):
        result = [{
            "service": "eBay Account-Deletion Endpoint (self)",
            "item": "GET challenge-response",
            "detail": detail,
            "date": "",
            "url": url,
            "action": ("Our endpoint that eBay uses to validate marketplace "
                       "account-deletion notifications is failing. Verify the route is "
                       "deployed, EBAY_VERIFICATION_TOKEN is set on collectioncalc-docker, "
                       "and the registered URL in the eBay developer portal matches this "
                       "endpoint. If left unresolved, eBay will deactivate our application "
                       "keys (kills eBay listing)."),
        }]
        cache["data"] = result
        cache["fetched_at"] = now
        return result

    # Read-only GET probe. A GET never reaches the POST deletion logic, and the
    # probe challenge_code is never persisted, so this mutates no state.
    try:
        resp = requests.get(url, params={"challenge_code": probe}, timeout=10)
    except Exception as e:
        return _fail(f"Probe request failed (timeout/connection error): {e}")

    if resp.status_code != 200:
        return _fail(
            f"Expected HTTP 200, got HTTP {resp.status_code} "
            f"(405 = GET challenge handler missing, 503 = service suspended, "
            f"5xx = verification token unset or handler error)"
        )

    try:
        body = resp.json()
    except ValueError:
        return _fail(f"Response was not valid JSON (Content-Type: "
                     f"{resp.headers.get('Content-Type', 'unknown')})")

    returned = (body or {}).get("challengeResponse")
    if not returned:
        return _fail("Response JSON missing or empty 'challengeResponse' field")

    # Strongest check: independently recompute the expected hash and compare.
    # Same formula as the live handler: sha256(challenge_code + token + endpoint).
    # Catches handler regressions (wrong concat order, double-encoding) and
    # endpoint-string drift between routes/ebay.py and this monitor.
    token = os.environ.get('EBAY_VERIFICATION_TOKEN')
    if token:
        expected = hashlib.sha256(
            (probe + token + url).encode('utf-8')
        ).hexdigest()
        if returned != expected:
            return _fail(
                "challengeResponse hash mismatch — the handler's challenge formula "
                "or endpoint string has drifted from the canonical "
                "sha256(challenge_code + EBAY_VERIFICATION_TOKEN + endpoint). eBay's "
                "own validation would also fail."
            )
    # If the token isn't visible to this process we can't recompute; the 200 +
    # non-empty challengeResponse checks above still stand (and a missing token
    # would have produced a 500 from the handler, caught as a non-200 above).

    # Healthy.
    cache["data"] = []
    cache["fetched_at"] = now
    return []


# =============================================
# STRIPE — SDK version check via PyPI
# =============================================

def _get_installed_stripe_version():
    """Get the currently installed stripe package version."""
    try:
        import stripe
        return stripe.VERSION
    except (ImportError, AttributeError):
        return None


def _parse_major(version_str):
    """Extract major version number from a version string like '7.12.0'."""
    try:
        return int(version_str.split('.')[0])
    except (ValueError, IndexError):
        return None


def check_stripe(force=False):
    """Check if our Stripe SDK is significantly behind the latest."""
    cache = _caches['stripe']
    now = time.time()
    if not force and (now - cache["fetched_at"]) < CACHE_TTL:
        return cache["data"]

    installed = _get_installed_stripe_version()
    if not installed:
        cache["data"] = []
        cache["fetched_at"] = now
        return []

    try:
        resp = requests.get(PYPI_STRIPE_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        latest = data.get("info", {}).get("version", "")
    except Exception as e:
        print(f"[DependencyMonitor] Stripe PyPI check failed: {e}")
        return cache["data"] or []

    warnings = []
    installed_major = _parse_major(installed)
    latest_major = _parse_major(latest)

    if installed_major is not None and latest_major is not None:
        gap = latest_major - installed_major
        if gap >= 2:
            warnings.append({
                "service": "Stripe",
                "item": f"stripe=={installed}",
                "detail": f"Installed v{installed}, latest is v{latest} ({gap} major versions behind)",
                "date": "",
                "url": "https://github.com/stripe/stripe-python/blob/master/CHANGELOG.md",
                "action": f"Update stripe package: pip install stripe>={latest_major}.0.0",
            })

    cache["data"] = warnings
    cache["fetched_at"] = now
    return warnings


# =============================================
# UNIFIED CHECK + EMAIL
# =============================================

def check_all(force=False):
    """Run all dependency checks. Returns unified list of warnings."""
    warnings = []
    warnings.extend(check_anthropic(force))
    warnings.extend(check_ebay(force))
    warnings.extend(check_ebay_account_deletion(force))
    warnings.extend(check_stripe(force))

    if warnings:
        _send_alert_email(warnings)

    return warnings


# Keep backward compat for existing callers
check_deprecations = check_all


def _send_alert_email(warnings):
    """Send email alert for new dependency warnings. Only once per item."""
    if not RESEND_AVAILABLE or not RESEND_API_KEY or not ADMIN_EMAIL:
        return

    new_warnings = [w for w in warnings if f"{w['service']}:{w['item']}" not in _emailed_keys]
    if not new_warnings:
        return

    # Group by service
    by_service = {}
    for w in new_warnings:
        by_service.setdefault(w['service'], []).append(w)

    sections_html = ""
    for service, items in by_service.items():
        rows = ""
        for w in items:
            rows += f"""
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #2a2a4a;">{w['item']}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #2a2a4a;">{w['detail']}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #2a2a4a;color:#f59e0b;font-weight:600;">{w['date'] or 'N/A'}</td>
            </tr>"""

        sections_html += f"""
        <h3 style="color:#60a5fa;margin-top:24px;">{service}</h3>
        <table style="width:100%;border-collapse:collapse;margin:8px 0;">
            <thead>
                <tr style="border-bottom:2px solid #f59e0b;">
                    <th style="padding:8px 12px;text-align:left;color:#94a3b8;">Item</th>
                    <th style="padding:8px 12px;text-align:left;color:#94a3b8;">Detail</th>
                    <th style="padding:8px 12px;text-align:left;color:#94a3b8;">Date</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>"""

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto;background:#0f0f23;color:#e2e8f0;padding:32px;border-radius:12px;">
        <h2 style="color:#f59e0b;margin-top:0;">Slab Worthy — Dependency Alert</h2>
        <p>The following third-party dependencies have deprecation or version warnings:</p>
        {sections_html}
        <p style="margin-top:24px;">Review each item and take action before the deadline.</p>
        <p style="font-size:0.85em;color:#64748b;margin-top:16px;">
            Sources: <a href="https://deprecations.info" style="color:#60a5fa;">deprecations.info</a> ·
            <a href="https://developer.ebay.com/rss/api-status" style="color:#60a5fa;">eBay API Status</a> ·
            <a href="https://pypi.org/project/stripe/" style="color:#60a5fa;">PyPI</a>
        </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": RESEND_FROM_EMAIL,
            "to": [ADMIN_EMAIL],
            "subject": f"[Slab Worthy] Dependency alert: {len(new_warnings)} item(s) need attention",
            "html": html,
        })
        for w in new_warnings:
            _emailed_keys.add(f"{w['service']}:{w['item']}")
        print(f"[DependencyMonitor] Email sent for {len(new_warnings)} warning(s)")
    except Exception as e:
        print(f"[DependencyMonitor] Email failed: {e}")
