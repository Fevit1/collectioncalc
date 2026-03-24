"""
Model Deprecation Monitor
Checks deprecations.info for upcoming Anthropic model retirements
and alerts via email + admin dashboard.

Designed to piggyback on Render's health-check polling — no cron needed.
"""

import os
import time
import requests
import resend
from models import MODEL_CHAINS

# ── Config ──
DEPRECATIONS_API = "https://deprecations.info/v1/deprecations.json"
CACHE_TTL_SECONDS = 86400  # 24 hours
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'noreply@slabworthy.com')

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# ── In-memory state ──
_cache = {"data": [], "fetched_at": 0}
_emailed_models = set()  # Track which models we've already emailed about


def _all_model_ids():
    """Collect every model ID referenced in MODEL_CHAINS."""
    ids = set()
    for chain in MODEL_CHAINS.values():
        ids.update(chain)
    return ids


def _tier_for_model(model_id):
    """Return which tier(s) a model belongs to."""
    tiers = []
    for tier, chain in MODEL_CHAINS.items():
        if model_id in chain:
            tiers.append(tier)
    return tiers


def check_deprecations(force=False):
    """
    Check deprecations.info for any Anthropic models we use.
    Returns list of dicts: [{model, shutdown_date, tiers, announcement_date, url}]
    Results are cached for 24 hours.
    """
    now = time.time()

    # Return cached result if fresh
    if not force and _cache["data"] is not None and (now - _cache["fetched_at"]) < CACHE_TTL_SECONDS:
        return _cache["data"]

    try:
        resp = requests.get(DEPRECATIONS_API, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[DeprecationCheck] Failed to fetch deprecations.info: {e}")
        # Return stale cache on error, don't clear it
        return _cache["data"] or []

    our_models = _all_model_ids()
    warnings = []

    # The JSON feed has an 'items' array with _deprecation extension
    items = data.get("items", [])
    for item in items:
        dep = item.get("_deprecation", {})
        provider = dep.get("provider", "")
        if provider.lower() not in ("anthropic", "ant"):
            continue

        model_name = dep.get("model_name", "")
        # Check if any of our models match (exact or prefix match)
        for our_model in our_models:
            if our_model == model_name or our_model in model_name or model_name in our_model:
                warnings.append({
                    "model": model_name,
                    "our_model": our_model,
                    "shutdown_date": dep.get("shutdown_date", "unknown"),
                    "announcement_date": dep.get("announcement_date", ""),
                    "url": dep.get("url", ""),
                    "tiers": _tier_for_model(our_model),
                })

    _cache["data"] = warnings
    _cache["fetched_at"] = now

    # Send email for new warnings
    if warnings:
        _send_deprecation_email(warnings)

    return warnings


def _send_deprecation_email(warnings):
    """Send email alert for deprecated models. Only sends once per model."""
    if not RESEND_API_KEY or not ADMIN_EMAIL:
        return

    # Filter to only new warnings we haven't emailed about
    new_warnings = [w for w in warnings if w["our_model"] not in _emailed_models]
    if not new_warnings:
        return

    model_rows = ""
    for w in new_warnings:
        tiers_str = ", ".join(w["tiers"])
        model_rows += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #2a2a4a;">{w['our_model']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #2a2a4a;">{tiers_str}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #2a2a4a;color:#f59e0b;font-weight:600;">{w['shutdown_date']}</td>
        </tr>"""

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:600px;margin:0 auto;background:#0f0f23;color:#e2e8f0;padding:32px;border-radius:12px;">
        <h2 style="color:#f59e0b;margin-top:0;">Slab Worthy — Model Deprecation Alert</h2>
        <p>One or more Anthropic models used by Slab Worthy have been marked for retirement:</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
            <thead>
                <tr style="border-bottom:2px solid #f59e0b;">
                    <th style="padding:8px 12px;text-align:left;color:#94a3b8;">Model</th>
                    <th style="padding:8px 12px;text-align:left;color:#94a3b8;">Tier</th>
                    <th style="padding:8px 12px;text-align:left;color:#94a3b8;">Shutdown Date</th>
                </tr>
            </thead>
            <tbody>{model_rows}</tbody>
        </table>
        <p style="margin-top:20px;">Update <code style="background:#1e1e3a;padding:2px 6px;border-radius:4px;">models.py</code> with replacement models before the shutdown date.</p>
        <p style="font-size:0.85em;color:#64748b;margin-top:24px;">Source: <a href="https://deprecations.info" style="color:#60a5fa;">deprecations.info</a></p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": RESEND_FROM_EMAIL,
            "to": [ADMIN_EMAIL],
            "subject": f"[Slab Worthy] Model retirement alert: {len(new_warnings)} model(s) affected",
            "html": html,
        })
        # Mark as emailed
        for w in new_warnings:
            _emailed_models.add(w["our_model"])
        print(f"[DeprecationCheck] Email sent for {len(new_warnings)} model(s)")
    except Exception as e:
        print(f"[DeprecationCheck] Email failed: {e}")
