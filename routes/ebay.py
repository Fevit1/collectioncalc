"""
eBay Blueprint - eBay OAuth, listing, and image upload endpoints
Routes: /api/ebay/*
"""
import os
import hashlib
from flask import Blueprint, jsonify, request, g

# Canonical, registered eBay Marketplace Account Deletion endpoint URL.
# This MUST exactly match the URL registered in the eBay developer portal
# (no trailing slash, -docker host). It is part of the challenge hash input,
# so do NOT reconstruct it from request headers — a header-derived host could
# differ from the registered string and produce a wrong (failing) hash.
EBAY_ACCOUNT_DELETION_ENDPOINT = "https://collectioncalc-docker.onrender.com/api/ebay/account-deletion"

# Create blueprint
ebay_bp = Blueprint('ebay', __name__, url_prefix='/api/ebay')

# Import auth decorators
from auth import require_auth, require_approved
from admin import log_api_usage
from models import SONNET

# Module imports (will be set by wsgi.py)
get_auth_url = None
exchange_code_for_token = None
get_user_token = None
is_user_connected = None
create_listing = None
upload_image_to_ebay = None
generate_description = None


def init_modules(auth_url_func, exchange_func, get_token_func, is_connected_func,
                 create_listing_func, upload_image_func, gen_desc_func):
    """Initialize modules from wsgi.py"""
    global get_auth_url, exchange_code_for_token, get_user_token, is_user_connected
    global create_listing, upload_image_to_ebay, generate_description
    
    get_auth_url = auth_url_func
    exchange_code_for_token = exchange_func
    get_user_token = get_token_func
    is_user_connected = is_connected_func
    create_listing = create_listing_func
    upload_image_to_ebay = upload_image_func
    generate_description = gen_desc_func


@ebay_bp.route('/account-deletion', methods=['GET', 'POST'])
def api_ebay_account_deletion():
    """
    eBay Marketplace Account Deletion Notification endpoint.

    GET  - eBay's endpoint-validation challenge. eBay sends ?challenge_code=...
           and expects {"challengeResponse": sha256(challengeCode + verificationToken + endpoint)}.
    POST - Runtime account-deletion notification (GDPR compliance).
           Signature-verified (ECDSA/SHA1 over the raw body, x-ebay-signature
           header — see ebay_signature.py). Responses follow eBay's contract:
           200 = verified + acknowledged, 412 = signature rejected (no data
           touched), 500 = verification temporarily impossible (eBay retries).
    """
    # --- GET: eBay challenge-response validation ---
    if request.method == 'GET':
        verification_token = os.environ.get('EBAY_VERIFICATION_TOKEN')
        if not verification_token:
            # Fail loud: a missing token would silently produce a wrong hash.
            print("ERROR: EBAY_VERIFICATION_TOKEN is not set; cannot answer eBay challenge")
            return jsonify({'error': 'Verification token not configured'}), 500

        challenge_code = request.args.get('challenge_code')
        if not challenge_code:
            return jsonify({'error': 'Missing challenge_code'}), 400

        # Order is exactly: challengeCode + verificationToken + endpoint
        m = hashlib.sha256()
        m.update((challenge_code + verification_token + EBAY_ACCOUNT_DELETION_ENDPOINT).encode('utf-8'))
        challenge_response = m.hexdigest()

        resp = jsonify({'challengeResponse': challenge_response})
        resp.headers['Content-Type'] = 'application/json'
        return resp, 200

    # --- POST: runtime deletion notification ---
    # Signature gate FIRST — nothing below runs on an unverified request.
    # raw body must be captured before get_json(): the signature is over
    # these exact bytes.
    raw_body = request.get_data(cache=True)
    signature_header = request.headers.get('x-ebay-signature')
    if not signature_header:
        print(f"[eBay] deletion notification REJECTED: no x-ebay-signature header "
              f"(remote={request.remote_addr})")
        return jsonify({'success': False, 'error': 'Signature required'}), 412

    from ebay_signature import verify_notification
    status, reason = verify_notification(raw_body, signature_header)
    if status == 'invalid':
        print(f"[eBay] deletion notification REJECTED: {reason} (remote={request.remote_addr})")
        return jsonify({'success': False, 'error': 'Signature verification failed'}), 412
    if status == 'unavailable':
        # Fail closed but retryable: never delete unverified, and never ack —
        # a 200 here would silently drop a real GDPR notice. 500 makes eBay
        # redeliver once verification infrastructure recovers.
        print(f"[eBay] deletion notification NOT PROCESSED (verification unavailable): {reason}")
        return jsonify({'success': False, 'error': 'Verification temporarily unavailable'}), 500
    print(f"[eBay] deletion notification signature OK: {reason}")

    try:
        from ebay_oauth import delete_user_by_ebay_id

        data = request.get_json(silent=True) or {}

        # Real eBay payloads nest identity under notification.data — the
        # username field is what OAuth stores in ebay_tokens.ebay_username.
        # (The old top-level reads meant real notifications never matched;
        # kept only as a fallback.)
        notif_data = ((data.get('notification') or {}).get('data') or {})
        candidates = [v for v in (
            notif_data.get('username'),
            notif_data.get('userId'),
            data.get('userId'), data.get('user_id'), data.get('username'),
        ) if v]

        if not candidates:
            # Verified notification with no identity — acknowledge.
            return jsonify({'success': True, 'message': 'Notification received'}), 200

        deleted = False
        for ebay_user_id in candidates:
            if delete_user_by_ebay_id(ebay_user_id):
                deleted = True
                print(f"Successfully deleted data for eBay user: {ebay_user_id}")

        if not deleted:
            print(f"No data found for eBay user identifiers: {candidates}")

        # Always return 200 to acknowledge a VERIFIED notification
        return jsonify({'success': True, 'deleted': deleted}), 200

    except Exception as e:
        print(f"Error processing eBay deletion notification: {e}")
        # Verified but failed to process: still 200 to prevent eBay retry loops
        return jsonify({'success': False, 'error': str(e)}), 200


@ebay_bp.route('/auth', methods=['GET'])
@require_auth
@require_approved
def api_ebay_auth():
    """Get eBay OAuth authorization URL"""
    if not get_auth_url:
        return jsonify({'success': False, 'error': 'eBay module not available'}), 503
    # Encode return page into state so callback redirects back to the right place
    return_to = request.args.get('return_to', 'account.html')
    state = f"{g.user_id}|{return_to}"
    url = get_auth_url(state)
    return jsonify({'success': True, 'url': url})


@ebay_bp.route('/callback', methods=['GET'])
def api_ebay_callback():
    """eBay OAuth callback endpoint"""
    if not exchange_code_for_token:
        return jsonify({'success': False, 'error': 'eBay module not available'}), 503
    
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code:
        return jsonify({'success': False, 'error': 'No code provided'}), 400
    
    try:
        from ebay_oauth import save_user_token, save_ebay_user_id
        token_data = exchange_code_for_token(code)

        # Parse state: "user_id|return_page" or just "user_id"
        user_id = state
        return_page = 'account.html'
        if state and '|' in state:
            parts = state.split('|', 1)
            user_id = parts[0]
            return_page = parts[1] if parts[1] else 'account.html'

        if user_id:
            save_user_token(user_id, token_data)

            # Fetch and save eBay username
            try:
                import requests as req
                ebay_access_token = token_data.get('access_token')
                if ebay_access_token:
                    identity_resp = req.get(
                        'https://apiz.ebay.com/commerce/identity/v1/user/',
                        headers={'Authorization': f'Bearer {ebay_access_token}'}
                    )
                    if identity_resp.status_code == 200:
                        identity_data = identity_resp.json()
                        ebay_username = identity_data.get('username', '')
                        if ebay_username:
                            save_ebay_user_id(user_id, ebay_username)
                            print(f"Saved eBay username: {ebay_username}")
                    else:
                        print(f"eBay identity API returned {identity_resp.status_code}")
            except Exception as identity_err:
                print(f"Could not fetch eBay username (non-fatal): {identity_err}")

        # Redirect back to the page the user started from
        frontend_url = os.environ.get('FRONTEND_URL', 'https://slabworthy.com')
        # Sanitize return_page to prevent open redirect — only allow known pages
        allowed_pages = ['account.html', 'collection.html', 'dashboard.html', 'app.html']
        if return_page not in allowed_pages:
            return_page = 'account.html'
        return f'<script>window.location.href = "{frontend_url}/{return_page}?ebay=connected";</script>'
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@ebay_bp.route('/status', methods=['GET'])
@require_auth
@require_approved
def api_ebay_status():
    """Check if user has connected eBay account"""
    if not get_user_token:
        return jsonify({'success': False, 'error': 'eBay module not available'}), 503
    token_data = get_user_token(str(g.user_id))
    if token_data and token_data.get('access_token'):
        # Return the eBay username — fetch from DB, backfill from API if missing
        from ebay_oauth import get_db_connection, save_ebay_user_id
        ebay_username = None
        try:
            conn = get_db_connection()
            if conn:
                cur = conn.cursor()
                cur.execute("SELECT ebay_username FROM ebay_tokens WHERE user_id = %s", (str(g.user_id),))
                row = cur.fetchone()
                if row:
                    ebay_username = row[0]
                cur.close()
                conn.close()
        except Exception:
            pass

        # Backfill: if username missing, fetch from eBay Identity API and save
        if not ebay_username:
            try:
                import requests as req
                identity_resp = req.get(
                    'https://apiz.ebay.com/commerce/identity/v1/user/',
                    headers={'Authorization': f'Bearer {token_data["access_token"]}'}
                )
                if identity_resp.status_code == 200:
                    ebay_username = identity_resp.json().get('username', '')
                    if ebay_username:
                        save_ebay_user_id(str(g.user_id), ebay_username)
            except Exception:
                pass

        return jsonify({'success': True, 'connected': True, 'ebay_username': ebay_username})
    return jsonify({'success': True, 'connected': False})


@ebay_bp.route('/disconnect', methods=['POST'])
@require_auth
@require_approved
def api_ebay_disconnect():
    """Disconnect user's eBay account"""
    try:
        from ebay_oauth import disconnect_user
        success = disconnect_user(str(g.user_id))
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@ebay_bp.route('/generate-description', methods=['POST'])
@require_auth
@require_approved
def api_generate_description():
    """Generate eBay listing description using AI"""
    if not generate_description:
        return jsonify({'success': False, 'error': 'Description module not available'}), 503
    data = request.get_json() or {}
    result = generate_description(
        data.get('title', ''),
        data.get('issue', ''),
        data.get('grade', 'VF'),
        data.get('price', 0)
    )
    if result.get('success'):
        log_api_usage(g.user_id, '/api/ebay/generate-description', SONNET,
                      result.get('input_tokens', 0), result.get('output_tokens', 0))
    return jsonify(result)


@ebay_bp.route('/upload-image', methods=['POST'])
@require_auth
@require_approved
def api_ebay_upload_image():
    """Upload image to eBay for listing.

    Accepts:
      - { image_url: "https://..." } — passes public URL to eBay's createImageFromUrl
    eBay fetches the image directly from the public R2 URL.
    """
    if not upload_image_to_ebay or not get_user_token:
        return jsonify({'success': False, 'error': 'eBay module not available'}), 503
    data = request.get_json() or {}
    image_url = data.get('image_url')
    filename = data.get('filename', 'comic.jpg')

    if not image_url:
        return jsonify({'success': False, 'error': 'image_url required'}), 400

    token_data = get_user_token(str(g.user_id))
    if not token_data or not token_data.get('access_token'):
        return jsonify({'success': False, 'error': 'eBay not connected'}), 401

    # Pass URL string directly — eBay's createImageFromUrl fetches it
    print(f"Passing R2 URL to eBay createImageFromUrl: {image_url[:80]}...")
    result = upload_image_to_ebay(token_data['access_token'], image_url, filename)
    return jsonify(result)


@ebay_bp.route('/list', methods=['POST'])
@require_auth
@require_approved
def api_ebay_list():
    """Create eBay listing"""
    if not create_listing or not get_user_token:
        return jsonify({'success': False, 'error': 'eBay module not available'}), 503
    data = request.get_json() or {}
    
    token_data = get_user_token(str(g.user_id))
    if not token_data or not token_data.get('access_token'):
        return jsonify({'success': False, 'error': 'eBay not connected'}), 401
    
    result = create_listing(
        str(g.user_id),
        data.get('title', ''),
        data.get('issue', ''),
        data.get('price', 0),
        data.get('grade', 'VF'),
        data.get('description'),
        data.get('publish', False),
        data.get('image_urls'),
        listing_format=data.get('listing_format', 'FIXED_PRICE'),
        auction_duration=data.get('auction_duration', 'DAYS_7'),
        start_price=data.get('start_price'),
        reserve_price=data.get('reserve_price'),
        buy_it_now_price=data.get('buy_it_now_price'),
        listing_title=data.get('listing_title')
    )
    return jsonify(result)
