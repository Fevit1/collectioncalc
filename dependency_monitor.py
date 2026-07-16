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
 Resources (self)  │ check_resources()             │ container cgroup + Postgres │ Memory + DB-connection ceilings (item 2f)

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
import io
import csv
import time
import hashlib
import threading
import xml.etree.ElementTree as ET
import requests
from models import MODEL_CHAINS

try:
    import psycopg2
    import db as _dbpool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

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

# Cross-portfolio dependency manifest (github.com/Fevit1/ideabyhuman-ops).
# Lets this monitor watch EVERY IdeaByHuman venture's models, not just Slab
# Worthy's. Fetched via the GitHub Contents API (private repo) using a
# read-only, Contents-scoped GITHUB_TOKEN. If unavailable, check_anthropic()
# falls back to Slab Worthy's local MODEL_CHAINS — it degrades, never goes blind.
MANIFEST_API_URL = "https://api.github.com/repos/Fevit1/ideabyhuman-ops/contents/dependency_manifest.csv"
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

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

# ── Resource-ceiling self-alert (LAUNCH_READINESS item 2f) ──
# Render Starter has NO native threshold alerts (event emails only), so the
# container watches its own ceilings. MONITORING-ONLY: warns via the admin
# dashboard + the state-change email; the tier-upgrade decision stays a human
# call — nothing here scales, restarts, or changes anything.
RESOURCE_CHECK_TTL = 300  # resource state moves fast; don't ride the 24h cache
# Sustained-over-N semantics, not instant: post-Phase-4 steady state measured
# ~70% of 512MB (358MB under 2 workers x 8 gthread threads, 2026-07-11), so the
# original 80% placeholder sat only ~52MB above normal — a single GC spike or
# deploy overlap would page. 85% sustained across 3 consecutive samples
# (~15 min at the 5-min TTL) alerts on real pressure, not noise.
RESOURCE_SUSTAIN_SAMPLES = 3
WARN_MEMORY_PCT = int(os.environ.get('RESOURCE_WARN_MEMORY_PCT', '85'))
WARN_DB_CONN_PCT = int(os.environ.get('RESOURCE_WARN_DB_CONN_PCT', '70'))
# Memory ceiling normally comes from the container's cgroup (memory.max), so a
# Render plan change is picked up automatically on the next boot — verified
# live across the 2026-07-16 Starter→Standard upgrade. This override exists for
# the day a platform misreports or hides the cgroup limit: set it to the
# instance's real MB and it takes precedence. 0 (default) = use the cgroup.
RESOURCE_MEM_LIMIT_MB = int(os.environ.get('RESOURCE_MEM_LIMIT_MB', '0'))
DB_RESERVED_CONNECTIONS = 3  # measured on Render Postgres: superuser-reserved slots

if RESEND_API_KEY and RESEND_AVAILABLE:
    resend.api_key = RESEND_API_KEY

# eBay APIs we depend on (from ebay_listing.py, ebay_oauth.py, ebay_signature.py)
EBAY_APIS_WE_USE = [
    'sell/inventory/v1',
    'sell/account/v1',
    'sell/fulfillment',
    'sell/marketing',
    'identity/v1/oauth2',
    'commerce/media/v1',
    'commerce/identity',
    'commerce/notification/v1',  # public-key fetch for deletion-notification signature verification
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
    'manifest':             {"data": None, "fetched_at": 0},
    'resources':            {"data": [], "fetched_at": 0},
}
_emailed_keys = set()  # Track what we've emailed about (service:identifier)

# Per-process (per-worker) resource sampling state. Streaks implement the
# sustained-over-N warning semantics; _resource_last feeds the always-visible
# status line on /api/admin/dependency-status. Multiple gunicorn workers each
# sample independently, but the DB-persisted alert dedup means only the first
# worker to cross the sustain threshold sends the email.
_resource_streaks = {'memory': 0, 'db_connections': 0}
_resource_last = {}


def _error_entry(service, reason):
    """Build a loud 'this check failed' warning entry.

    A check that errors (network, shape change, parse failure) must surface as a
    visible error in the monitor output — never silently return empty/cached and
    look healthy. Uses a stable `item` so _send_alert_email dedups repeats.
    """
    return {
        "service": service,
        "item": "monitor check",
        "detail": f"Dependency check failed: {reason}",
        "date": "",
        "url": "",
        "action": (f"The {service} dependency check raised an error and could not "
                   f"run. Other checks still executed. Investigate dependency_monitor.py "
                   f"(e.g. upstream response-shape change) so this service is monitored again."),
        "status": "error",
    }


def _unmonitorable_entry(service, reason, action):
    """Build an honest 'we can't automatically watch this' entry.

    Distinct from _error_entry: not a bug to fix, but a known coverage gap where
    no automatable source exists. Surfaced visibly (so we never believe we have
    coverage we don't) with manual-tracking guidance.
    """
    return {
        "service": service,
        "item": "monitor check",
        "detail": f"Not automatically monitorable: {reason}",
        "date": "",
        "url": "",
        "action": action,
        "status": "unmonitorable",
    }


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


def _load_manifest(force=False):
    """Fetch + parse the cross-portfolio dependency manifest from ideabyhuman-ops.

    Returns a dict:
      {"ok": bool,
       "anthropic_models": set(model_id),
       "usage": {model_id: ["project [config_ref]", ...]},
       "error": str|None}

    On ANY failure (no token, network, non-200, parse error) returns ok=False
    with an error string — never raises. check_anthropic() then falls back to
    Slab Worthy's local MODEL_CHAINS and emits a loud error entry, so a manifest
    outage shrinks coverage visibly instead of silently. Cached 24h; failures
    are short-backed-off (retry in ~5 min) like the other checks.
    """
    cache = _caches['manifest']
    now = time.time()
    if not force and cache["data"] is not None and (now - cache["fetched_at"]) < CACHE_TTL:
        return cache["data"]

    try:
        if not GITHUB_TOKEN:
            raise RuntimeError("GITHUB_TOKEN not set — cannot read the private manifest")
        resp = requests.get(
            MANIFEST_API_URL,
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.raw",
                "User-Agent": "ideabyhuman-dependency-monitor",
            },
            timeout=10,
        )
        resp.raise_for_status()
        models = set()
        usage = {}
        for row in csv.DictReader(io.StringIO(resp.text)):
            provider = (row.get("provider") or "").strip().lower()
            model_id = (row.get("model_id") or "").strip()
            if not model_id or model_id == "TODO":
                continue
            if provider == "anthropic":
                project = (row.get("project") or "").strip()
                config_ref = (row.get("config_ref") or "").strip()
                models.add(model_id)
                usage.setdefault(model_id, []).append(
                    f"{project} [{config_ref}]" if config_ref else project
                )
        result = {"ok": True, "anthropic_models": models, "usage": usage, "error": None}
    except Exception as e:
        print(f"[DependencyMonitor] manifest load failed: {e}")
        result = {"ok": False, "anthropic_models": set(), "usage": {}, "error": str(e)}

    cache["data"] = result
    # Cache success the full TTL; back off failures so a manifest outage doesn't
    # hammer GitHub on every health-check poll (mirrors check_anthropic).
    cache["fetched_at"] = now if result["ok"] else (now - CACHE_TTL + 300)
    return result


def check_anthropic(force=False):
    """Check deprecations.info for Anthropic model retirements.

    Tolerates both response shapes:
      - legacy: {"items": [{"_deprecation": {"provider","model_name",...}}, ...]}
      - current (2026-06): top-level JSON array of flat records
        [{"provider","model_id","shutdown_date","url",...}, ...]

    All fetching AND parsing happen inside the try/except. If the upstream shape
    changes again, this one check degrades to a loud error entry instead of
    raising and killing check_all() (see _error_entry / check_all isolation).
    """
    cache = _caches['anthropic']
    now = time.time()
    if not force and (now - cache["fetched_at"]) < CACHE_TTL:
        return cache["data"]

    try:
        resp = requests.get(DEPRECATIONS_API, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Normalize both shapes to a flat list of deprecation records.
        if isinstance(data, dict):
            records = data.get("items", [])
        elif isinstance(data, list):
            records = data
        else:
            records = []

        # Source the model universe from the cross-portfolio manifest so this
        # check watches EVERY venture's models, not just Slab Worthy's. If the
        # manifest is unreachable, fall back to Slab Worthy's local chains (SW
        # stays covered) and emit a loud entry so the shrunk coverage is visible,
        # never silent.
        manifest = _load_manifest(force=force)
        manifest_warnings = []
        if manifest["ok"]:
            our_models = manifest["anthropic_models"] or _all_model_ids()
        else:
            our_models = _all_model_ids()
            manifest_warnings.append(_error_entry(
                "Dependency Manifest",
                f"could not load the cross-portfolio manifest ({manifest['error']}). "
                f"The Anthropic check fell back to Slab Worthy's local models ONLY — "
                f"other IdeaByHuman ventures are NOT being watched until the manifest "
                f"is reachable again (verify GITHUB_TOKEN on this service).",
            ))

        warnings = []
        seen = set()  # dedup our_model — same model can appear in multiple records
        for item in records:
            if not isinstance(item, dict):
                continue
            # Current records are flat; legacy nested fields under "_deprecation".
            dep = item.get("_deprecation", item)
            provider = (dep.get("provider") or "").lower()
            if provider not in ("anthropic", "ant"):
                continue
            # Key differs across shapes: "model_id" (current) vs "model_name" (legacy).
            model_name = dep.get("model_id") or dep.get("model_name") or ""
            if not model_name:
                continue
            for our_model in our_models:
                if our_model in seen:
                    continue
                if our_model == model_name or our_model in model_name or model_name in our_model:
                    seen.add(our_model)
                    if manifest["ok"]:
                        users = ", ".join(manifest["usage"].get(our_model, ["unknown project"]))
                        action = (f"Model retiring — used by: {users}. "
                                  f"Update each listed project's model config before the date.")
                    else:
                        action = f"Update models.py — replace in {', '.join(_tier_for_model(our_model))} tier"
                    warnings.append({
                        "service": "Anthropic",
                        "item": our_model,
                        "detail": "Model retiring",
                        "date": dep.get("shutdown_date", "unknown"),
                        "url": dep.get("url", ""),
                        "action": action,
                    })

        warnings.extend(manifest_warnings)
    except Exception as e:
        print(f"[DependencyMonitor] Anthropic check failed: {e}")
        err = [_error_entry("Anthropic", e)]
        # Surface the error loudly but back off: retry in ~5 min instead of on
        # every health-check poll, so a prolonged upstream outage doesn't hammer
        # the source (or re-enter the alert path) every 30 seconds.
        cache["data"] = err
        cache["fetched_at"] = now - CACHE_TTL + 300
        return err

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
        resp = requests.get(
            EBAY_RSS_URL, timeout=10,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; SlabWorthyDependencyMonitor/1.0)'},
        )

        # developer.ebay.com sits behind Akamai bot protection that 403s all
        # server-side requests (any User-Agent, all paths) with a JS-challenge
        # error page. This is a permanent block, not a transient error — report
        # it honestly as unmonitorable (cached the normal 24h, so we retry daily
        # in case the wall is ever lifted) rather than a recurring error entry.
        if resp.status_code == 403:
            result = [_unmonitorable_entry(
                "eBay",
                "developer.ebay.com RSS is Akamai bot-protected (HTTP 403) — not "
                "pollable from a server. No automatable eBay API-deprecation feed "
                "is currently available.",
                "Track eBay API deprecations manually (subscribe to eBay developer "
                "announcements / release notes by email), or revisit if eBay "
                "publishes a machine-readable feed. The eBay account-deletion "
                "self-check (separate) still covers our own compliance endpoint.",
            )]
            cache["data"] = result
            cache["fetched_at"] = now
            return result

        resp.raise_for_status()
        root = ET.fromstring(resp.text)

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
    except Exception as e:
        print(f"[DependencyMonitor] eBay RSS check failed: {e}")
        err = [_error_entry("eBay", e)]
        cache["data"] = err
        cache["fetched_at"] = now - CACHE_TTL + 300  # loud, but back off (see check_anthropic)
        return err

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
        # Back off, don't camp: caching a FAILURE for the full 24h TTL poisons
        # this worker's view for a day — one 502 caught during a deploy-swap
        # window kept a worker warning until process death, seeding the
        # 2026-07-16 email storm (per-worker divergence × shared dedup prune).
        # Match the other checks' failure handling: retry in ~5 min.
        cache["fetched_at"] = now - CACHE_TTL + 300
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
        latest = (data.get("info") or {}).get("version", "")

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
    except Exception as e:
        print(f"[DependencyMonitor] Stripe PyPI check failed: {e}")
        err = [_error_entry("Stripe", e)]
        cache["data"] = err
        cache["fetched_at"] = now - CACHE_TTL + 300  # loud, but back off (see check_anthropic)
        return err

    cache["data"] = warnings
    cache["fetched_at"] = now
    return warnings


# =============================================
# RESOURCES — memory + DB-connection ceiling self-alert (item 2f)
# =============================================

def _read_cgroup_memory():
    """(current_bytes, limit_bytes) from the container's cgroup, else None.

    cgroup v2 first (memory.current / memory.max), v1 fallback. A limit of
    'max' (v2) or the v1 unlimited sentinel returns limit=None (can't compute
    a percentage). Returns None entirely when no cgroup files exist — expected
    on dev machines (Windows/macOS), not an outage, so the caller skips the
    memory half silently rather than alerting."""
    try:
        base = '/sys/fs/cgroup'
        v2_current = os.path.join(base, 'memory.current')
        if os.path.exists(v2_current):
            with open(v2_current) as f:
                current = int(f.read().strip())
            with open(os.path.join(base, 'memory.max')) as f:
                raw = f.read().strip()
            limit = None if raw == 'max' else int(raw)
            return current, limit
        v1_current = os.path.join(base, 'memory', 'memory.usage_in_bytes')
        if os.path.exists(v1_current):
            with open(v1_current) as f:
                current = int(f.read().strip())
            with open(os.path.join(base, 'memory', 'memory.limit_in_bytes')) as f:
                limit = int(f.read().strip())
            if limit >= (1 << 60):  # v1 reports "unlimited" as a huge sentinel
                limit = None
            return current, limit
    except Exception as e:
        print(f"[DependencyMonitor] cgroup memory read failed: {e}")
    return None


def _db_connection_usage():
    """(used, usable) connection counts, else None when DB is unavailable.

    used = pg_stat_activity rows for our database (all workers + shells + any
    other client — the true global number the ceiling applies to);
    usable = max_connections - DB_RESERVED_CONNECTIONS."""
    if not PSYCOPG2_AVAILABLE or not os.environ.get('DATABASE_URL'):
        return None
    conn = _dbpool.get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
        )
        used = cur.fetchone()[0]
        cur.execute("SHOW max_connections")
        max_conn = int(cur.fetchone()[0])
        cur.close()
    finally:
        conn.close()
    return used, max(1, max_conn - DB_RESERVED_CONNECTIONS)


def check_resources(force=False):
    """Resource-ceiling self-alert (LAUNCH_READINESS item 2f).

    Samples container memory (cgroup) and global DB connections every
    RESOURCE_CHECK_TTL seconds, riding the health-check polling like every
    other check. A warning fires only after RESOURCE_SUSTAIN_SAMPLES
    consecutive over-threshold samples (~15 min) — see the threshold config
    comment for the calibration rationale. MONITORING-ONLY: the fallback
    (1 worker x 12 threads) and the tier upgrade are HUMAN decisions; this
    code only surfaces the numbers."""
    cache = _caches['resources']
    now = time.time()
    if not force and (now - cache["fetched_at"]) < RESOURCE_CHECK_TTL:
        return cache["data"]

    warnings = []
    try:
        pool_snapshot = None
        if PSYCOPG2_AVAILABLE:
            try:
                pool_snapshot = _dbpool.pool_stats()  # per-worker; labeled by pid
            except Exception:
                pass

        # ---- memory (skipped silently off-container) ----
        mem = _read_cgroup_memory()
        if mem and RESOURCE_MEM_LIMIT_MB:
            mem = (mem[0], RESOURCE_MEM_LIMIT_MB * 1048576)  # explicit override wins
        if mem and mem[1]:
            current, limit = mem
            pct = 100.0 * current / limit
            _resource_last['memory'] = {
                'used_mb': round(current / 1048576, 1),
                'limit_mb': round(limit / 1048576, 1),
                'pct': round(pct, 1),
                'warn_pct': WARN_MEMORY_PCT,
                'limit_source': 'env:RESOURCE_MEM_LIMIT_MB' if RESOURCE_MEM_LIMIT_MB else 'cgroup',
            }
            if pct >= WARN_MEMORY_PCT:
                _resource_streaks['memory'] += 1
            else:
                _resource_streaks['memory'] = 0
            if _resource_streaks['memory'] >= RESOURCE_SUSTAIN_SAMPLES:
                m = _resource_last['memory']
                warnings.append({
                    "service": "Resources (self)",
                    "item": "memory ceiling",
                    "detail": (f"Container memory {m['used_mb']}MB / {m['limit_mb']}MB "
                               f"({m['pct']}%) — sustained ≥{WARN_MEMORY_PCT}% across "
                               f"{RESOURCE_SUSTAIN_SAMPLES} samples "
                               f"(~{RESOURCE_SUSTAIN_SAMPLES * RESOURCE_CHECK_TTL // 60} min). "
                               f"Worker pool stats (pid-local): {pool_snapshot}"),
                    "date": "",
                    "url": "https://dashboard.render.com",
                    "action": ("Sustained memory pressure. Options (HUMAN decision, nothing "
                               "automatic): drop gunicorn to 1 worker x 12 threads (the "
                               "documented Dockerfile fallback), or upgrade the instance tier "
                               "in the Render dashboard. The ceiling above is auto-detected "
                               "from the container cgroup, so a tier change is reflected on "
                               "the next boot (RESOURCE_MEM_LIMIT_MB env overrides it if a "
                               "platform ever misreports)."),
                })

        # ---- DB connections (skipped silently without DATABASE_URL) ----
        db_usage = _db_connection_usage()
        if db_usage:
            used, usable = db_usage
            pct = 100.0 * used / usable
            _resource_last['db_connections'] = {
                'used': used,
                'usable': usable,
                'pct': round(pct, 1),
                'warn_pct': WARN_DB_CONN_PCT,
            }
            if pct >= WARN_DB_CONN_PCT:
                _resource_streaks['db_connections'] += 1
            else:
                _resource_streaks['db_connections'] = 0
            if _resource_streaks['db_connections'] >= RESOURCE_SUSTAIN_SAMPLES:
                d = _resource_last['db_connections']
                warnings.append({
                    "service": "Resources (self)",
                    "item": "DB connection ceiling",
                    "detail": (f"{d['used']} / {d['usable']} usable Postgres connections "
                               f"({d['pct']}%) — sustained ≥{WARN_DB_CONN_PCT}% across "
                               f"{RESOURCE_SUSTAIN_SAMPLES} samples. "
                               f"Worker pool stats (pid-local): {pool_snapshot}"),
                    "date": "",
                    "url": "https://dashboard.render.com",
                    "action": ("Connection count approaching the Postgres ceiling. First check "
                               "Render logs for 'POOL EXHAUSTED' (a leak upstream of the pool) "
                               "and non-app clients (shells, scripts) in pg_stat_activity; "
                               "DB_POOL_MAX × workers should sit far below usable. Upgrading "
                               "the Postgres plan is the last resort, not the first."),
                })

        _resource_last['sampled_at'] = int(now)
    except Exception as e:
        print(f"[DependencyMonitor] resource check failed: {e}")
        err = [_error_entry("Resources (self)", e)]
        cache["data"] = err
        cache["fetched_at"] = now - RESOURCE_CHECK_TTL + 60  # loud, retry in ~1 min
        return err

    cache["data"] = warnings
    cache["fetched_at"] = now
    return warnings


def resource_status(force=False):
    """Always-visible resource snapshot for /api/admin/dependency-status —
    the healthy numbers, not just warnings. Rides check_resources()'s TTL
    cache, so a dashboard load costs nothing between samples."""
    check_resources(force)
    out = dict(_resource_last)
    out['streaks'] = dict(_resource_streaks)
    out['sustain_required'] = RESOURCE_SUSTAIN_SAMPLES
    if PSYCOPG2_AVAILABLE:
        try:
            out['pool'] = _dbpool.pool_stats()
        except Exception:
            pass
    return out


# =============================================
# UNIFIED CHECK + EMAIL
# =============================================

def check_all(force=False):
    """Run all dependency checks. Returns unified list of warnings.

    Each check is isolated: if one raises (despite its own try/except), it is
    converted to a loud error entry and the remaining checks still run. One
    broken check must never blind us to the others — that regression is exactly
    what took the whole monitor down (deprecations.info shape change, 2026-06).
    """
    checks = (
        ("Anthropic", check_anthropic),
        ("eBay", check_ebay),
        ("eBay Account-Deletion Endpoint (self)", check_ebay_account_deletion),
        ("Stripe", check_stripe),
        ("Resources (self)", check_resources),
    )

    warnings = []
    for name, fn in checks:
        try:
            warnings.extend(fn(force))
        except Exception as e:
            print(f"[DependencyMonitor] {name} check crashed in check_all: {e}")
            warnings.append(_error_entry(name, e))

    if warnings:
        _send_alert_email_async(warnings)

    return warnings


# Keep backward compat for existing callers
check_deprecations = check_all


# ── Persistent alert dedup (email on STATE CHANGE, not every boot) ──
# Render restarts/deploys frequently and the in-memory _emailed_keys resets each
# time, which re-emailed permanent states (e.g. eBay 'unmonitorable') on every
# boot. Persist alerted keys in a tiny self-creating DB table so an alert fires
# once per state change. Falls back to in-memory dedup if the DB is unavailable.
_alerts_table_ready = False
_email_send_lock = threading.Lock()


def _send_alert_email_async(warnings):
    """Run _send_alert_email on a daemon thread — never in the request path.

    check_all() rides the health-check polling, so before this, every alert
    email was a synchronous Resend API call INSIDE a /health request (~0.5-1s
    added to the availability probe Render acts on — observed during the
    2026-07-16 storm). Skip-if-busy: if a send is already in flight, drop this
    round; the same warning state comes back on the next poll, and dedup makes
    the retry a no-op once persisted."""
    def run():
        if not _email_send_lock.acquire(blocking=False):
            return
        try:
            _send_alert_email(warnings)
        finally:
            _email_send_lock.release()
    threading.Thread(target=run, daemon=True, name="dep-alert-email").start()


def _alerts_conn():
    if not PSYCOPG2_AVAILABLE:
        return None
    url = os.environ.get('DATABASE_URL')
    if not url:
        return None
    return _dbpool.get_db()


def _ensure_alerts_table(conn):
    global _alerts_table_ready
    if _alerts_table_ready:
        return
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dependency_alerts (
                alert_key TEXT PRIMARY KEY,
                detail TEXT,
                first_alerted_at TIMESTAMPTZ DEFAULT NOW(),
                last_seen_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    conn.commit()
    _alerts_table_ready = True


def _alert_key(w):
    return f"{w['service']}:{w['item']}"


def _send_alert_email(warnings):
    """Email NEW dependency warnings only (state-change), once per item.

    Dedup is DB-persisted (dependency_alerts table) so a permanent state like
    eBay 'unmonitorable' is emailed once, not on every Render restart. Falls back
    to the in-memory _emailed_keys (per-process) if the DB is unavailable.
    """
    if not RESEND_AVAILABLE or not RESEND_API_KEY or not ADMIN_EMAIL:
        return

    current = {_alert_key(w): w for w in warnings}

    conn = None
    persisted = None
    try:
        conn = _alerts_conn()
        if conn is not None:
            _ensure_alerts_table(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT alert_key FROM dependency_alerts")
                persisted = {r[0] for r in cur.fetchall()}
    except Exception as e:
        print(f"[DependencyMonitor] alert-state DB unavailable, using in-memory dedup: {e}")
        persisted = None

    known = persisted if persisted is not None else _emailed_keys
    new_warnings = [w for k, w in current.items() if k not in known]

    # Refresh last_seen_at for still-present keys, then prune only keys that
    # have been absent for a full stability window. Pruning IMMEDIATELY on
    # absence is a race: check results are cached PER WORKER, so a warning one
    # worker sees and the other doesn't gets pruned by the clean worker and
    # re-inserted (re-EMAILED) by the poisoned worker on every alternating
    # health poll — the 2026-07-16 storm (~1 email/15s, self-sustaining).
    # 15 min of continuous absence before pruning outlasts any per-worker
    # cache divergence; a genuinely cleared warning still re-alerts if it
    # recurs after the window.
    if persisted is not None and conn is not None:
        try:
            present = list(set(current.keys()) & persisted)
            with conn.cursor() as cur:
                if present:
                    cur.execute(
                        "UPDATE dependency_alerts SET last_seen_at = NOW() "
                        "WHERE alert_key = ANY(%s)", (present,))
                cur.execute(
                    "DELETE FROM dependency_alerts "
                    "WHERE NOT (alert_key = ANY(%s)) "
                    "AND last_seen_at < NOW() - INTERVAL '15 minutes'",
                    (list(current.keys()),))
            conn.commit()
        except Exception as e:
            print(f"[DependencyMonitor] failed refreshing/pruning alert state: {e}")
    else:
        # In-memory fallback: prune resolved keys too so recurrence re-alerts.
        for k in (set(_emailed_keys) - set(current.keys())):
            _emailed_keys.discard(k)

    if not new_warnings:
        if conn is not None:
            conn.close()
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
        # Persist newly-alerted keys so we don't re-email them on the next boot.
        if persisted is not None and conn is not None:
            try:
                with conn.cursor() as cur:
                    for w in new_warnings:
                        cur.execute(
                            """INSERT INTO dependency_alerts (alert_key, detail)
                               VALUES (%s, %s)
                               ON CONFLICT (alert_key) DO UPDATE SET last_seen_at = NOW()""",
                            (_alert_key(w), w.get('detail', '')),
                        )
                conn.commit()
            except Exception as e:
                print(f"[DependencyMonitor] failed persisting alert state: {e}")
        else:
            for w in new_warnings:
                _emailed_keys.add(_alert_key(w))
        print(f"[DependencyMonitor] Email sent for {len(new_warnings)} warning(s)")
    except Exception as e:
        print(f"[DependencyMonitor] Email failed: {e}")
    finally:
        if conn is not None:
            conn.close()
