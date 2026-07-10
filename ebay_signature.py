"""eBay event-notification signature verification (Marketplace Account Deletion).

eBay signs every notification POST with ECDSA/SHA1 over the RAW request body.
The x-ebay-signature header is base64-encoded JSON:

    {"alg": "ecdsa", "kid": "<public-key-id>", "signature": "<base64 sig>", "digest": "SHA1"}

The public key comes from the Notification API using an application
(client-credentials) OAuth token — the same EBAY_CLIENT_ID/SECRET the OAuth
flow already uses:

    GET /commerce/notification/v1/public_key/{kid}

Keys are cached ~1h per eBay's guidance (don't refetch per notification).

verify_notification() is deliberately TRI-STATE so the route can answer per
eBay's endpoint contract (200 ack / 412 reject / 500 retry-later):

    'valid'       signature verified over the raw body — process the delete
    'invalid'     definitive mismatch or malformed header — 412, never delete
    'unavailable' we could not verify (token/key fetch/library failure) —
                  500 so eBay REDELIVERS later; unverifiable is never treated
                  as valid (fail closed) and never acked (a 200 would silently
                  drop a real GDPR deletion notice)

Kill switch: EBAY_SIGNATURE_VERIFICATION_DISABLED=1 restores the pre-check
accept-all behavior without a code revert (same rollback pattern as
DB_POOL_DISABLED). Env flips need a service restart + fresh shell (L-SW-2026-004).
"""

import os
import json
import base64
import threading
import time

import requests

from ebay_oauth import EBAY_TOKEN_URL, EBAY_SANDBOX_TOKEN_URL, is_sandbox_mode

# cryptography is the one new dependency (stdlib cannot verify ECDSA). Guarded
# import so a missing wheel degrades to 'unavailable' (500/retry), not an
# import-time crash of the whole app.
try:
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import hashes
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

EBAY_PUBLIC_KEY_URL = "https://api.ebay.com/commerce/notification/v1/public_key/"
EBAY_SANDBOX_PUBLIC_KEY_URL = "https://api.sandbox.ebay.com/commerce/notification/v1/public_key/"

# eBay currently signs with ECDSA over a SHA1 digest (their SDKs' 'ssl3-sha1').
# Strict by design: an unexpected alg/digest is rejected, not guessed at — if
# eBay ever migrates, the dependency monitor + REJECTED log lines surface it.
_EXPECTED_ALG = 'ecdsa'
_EXPECTED_DIGEST = 'sha1'

_KEY_CACHE_TTL = 3600  # seconds; eBay recommends ~1h

_lock = threading.Lock()
_app_token = {'token': None, 'expires_at': 0}
_key_cache = {}  # kid -> {'pem': str, 'fetched_at': float}


def _get_app_token():
    """Client-credentials application token for the Notification API.
    Cached until 60s before expiry. Raises on failure (caller maps to
    'unavailable')."""
    now = time.time()
    with _lock:
        if _app_token['token'] and now < _app_token['expires_at'] - 60:
            return _app_token['token']

    client_id = os.environ.get('EBAY_CLIENT_ID')
    client_secret = os.environ.get('EBAY_CLIENT_SECRET')
    if not (client_id and client_secret):
        raise ValueError("EBAY_CLIENT_ID/EBAY_CLIENT_SECRET not configured")

    token_url = EBAY_SANDBOX_TOKEN_URL if is_sandbox_mode() else EBAY_TOKEN_URL
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        token_url,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {credentials}',
        },
        data={
            'grant_type': 'client_credentials',
            'scope': 'https://api.ebay.com/oauth/api_scope',
        },
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"app token request failed: {resp.status_code} {resp.text[:200]}")
    payload = resp.json()
    with _lock:
        _app_token['token'] = payload['access_token']
        _app_token['expires_at'] = now + int(payload.get('expires_in', 7200))
    return _app_token['token']


def _format_pem(key: str) -> str:
    """eBay returns the PEM as one line ('-----BEGIN PUBLIC KEY-----MFkw…');
    the parser needs newlines around the delimiters."""
    return (key
            .replace('-----BEGIN PUBLIC KEY-----', '-----BEGIN PUBLIC KEY-----\n')
            .replace('-----END PUBLIC KEY-----', '\n-----END PUBLIC KEY-----\n'))


def _get_public_key_pem(kid: str) -> str:
    """Fetch (or serve cached) public key PEM for a key id. Raises on failure
    (caller maps to 'unavailable')."""
    now = time.time()
    with _lock:
        cached = _key_cache.get(kid)
        if cached and now - cached['fetched_at'] < _KEY_CACHE_TTL:
            return cached['pem']

    token = _get_app_token()
    base = EBAY_SANDBOX_PUBLIC_KEY_URL if is_sandbox_mode() else EBAY_PUBLIC_KEY_URL
    resp = requests.get(
        base + kid,
        headers={'Authorization': f'Bearer {token}'},
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"getPublicKey failed for kid={kid}: {resp.status_code} {resp.text[:200]}")
    key = resp.json().get('key')
    if not key:
        raise RuntimeError(f"getPublicKey response for kid={kid} has no 'key' field")
    pem = _format_pem(key)
    with _lock:
        _key_cache[kid] = {'pem': pem, 'fetched_at': now}
    return pem


def verify_notification(raw_body: bytes, signature_header: str):
    """Verify an eBay notification signature over the raw request body.

    Returns (status, reason): status in {'valid', 'invalid', 'unavailable'}.
    Never raises.
    """
    if os.environ.get('EBAY_SIGNATURE_VERIFICATION_DISABLED') == '1':
        return 'valid', 'verification DISABLED via env kill switch'

    # --- Parse the header. Anything malformed is 'invalid' (attacker/garbage),
    # not 'unavailable' — eBay's real header always parses. ---
    try:
        decoded = json.loads(base64.b64decode(signature_header, validate=True))
        kid = decoded['kid']
        signature = base64.b64decode(decoded['signature'])
        alg = str(decoded.get('alg', '')).lower()
        digest = str(decoded.get('digest', '')).lower()
    except Exception as e:
        return 'invalid', f'malformed x-ebay-signature header ({type(e).__name__}: {e})'

    if alg != _EXPECTED_ALG or digest != _EXPECTED_DIGEST:
        return 'invalid', f'unexpected alg/digest ({alg}/{digest}); expected {_EXPECTED_ALG}/{_EXPECTED_DIGEST}'

    if not CRYPTO_AVAILABLE:
        return 'unavailable', "the 'cryptography' package is not installed"

    # --- Fetch the public key (infra failures are retryable). ---
    try:
        pem = _get_public_key_pem(kid)
        public_key = load_pem_public_key(pem.encode())
    except Exception as e:
        return 'unavailable', f'could not obtain/parse public key for kid={kid} ({e})'

    # --- Verify. ---
    try:
        public_key.verify(signature, raw_body, ec.ECDSA(hashes.SHA1()))
        return 'valid', f'signature verified (kid={kid})'
    except InvalidSignature:
        return 'invalid', f'signature does not match payload (kid={kid})'
    except Exception as e:
        # e.g. the fetched key is not an EC key — misconfiguration, retryable
        return 'unavailable', f'verification error ({type(e).__name__}: {e})'
