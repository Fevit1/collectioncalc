"""
Dependency Monitor
Checks third-party service deprecations and alerts via email + admin dashboard.
Piggybacks on Render's health-check polling (no cron needed).
Each check is cached 24 hours independently.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 MONITORED SERVICES — update this when adding new third-party integrations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Service     │ Check Method      │ Source                         │ What We Watch
 ────────────┼───────────────────┼────────────────────────────────┼─────────────────────
 Anthropic   │ check_anthropic() │ deprecations.info JSON API     │ Model retirements
 eBay        │ check_ebay()      │ developer.ebay.com RSS feed    │ API deprecations
 Stripe      │ check_stripe()    │ PyPI version check             │ SDK version drift

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
import xml.etree.ElementTree as ET
import requests
import resend
from models import MODEL_CHAINS

# ── Config ──
DEPRECATIONS_API = "https://deprecations.info/v1/deprecations.json"
EBAY_RSS_URL = "https://developer.ebay.com/rss/api-status"
PYPI_STRIPE_URL = "https://pypi.org/pypi/stripe/json"
CACHE_TTL = 86400  # 24 hours

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'noreply@slabworthy.com')

if RESEND_API_KEY:
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
    'anthropic': {"data": [], "fetched_at": 0},
    'ebay':      {"data": [], "fetched_at": 0},
    'stripe':    {"data": [], "fetched_at": 0},
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
    warnings.extend(check_stripe(force))

    if warnings:
        _send_alert_email(warnings)

    return warnings


# Keep backward compat for existing callers
check_deprecations = check_all


def _send_alert_email(warnings):
    """Send email alert for new dependency warnings. Only once per item."""
    if not RESEND_API_KEY or not ADMIN_EMAIL:
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
