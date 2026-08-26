"""
Images Blueprint - R2 storage and image upload endpoints
Routes: /api/images/*

Includes extra photo uploads for Slab Guard enhanced fingerprinting.
Extra photos (close-ups, defects, alternate angles) are stored in the
collections.photos JSONB under an 'extra' array.
"""
import os
import json
import time
from flask import Blueprint, jsonify, request, g
import psycopg2
import db as _dbpool
from auth import require_auth, require_approved

# Create blueprint
images_bp = Blueprint('images', __name__, url_prefix='/api/images')

# Module imports (will be set by wsgi.py)
R2_AVAILABLE = False
upload_sale_image = None
upload_temp_image = None
upload_submission_image = None
check_r2_connection = None
scan_barcode_from_base64 = None
moderate_image = None
log_moderation_incident = None
get_image_hash = None


def init_modules(r2_available, upload_sale_func, upload_temp_func, upload_sub_func, 
                 check_r2_func, scan_barcode_func, mod_image_func, log_mod_func, hash_func):
    """Initialize modules from wsgi.py"""
    global R2_AVAILABLE, upload_sale_image, upload_temp_image, upload_submission_image
    global check_r2_connection, scan_barcode_from_base64, moderate_image
    global log_moderation_incident, get_image_hash
    
    R2_AVAILABLE = r2_available
    upload_sale_image = upload_sale_func
    upload_temp_image = upload_temp_func
    upload_submission_image = upload_sub_func
    check_r2_connection = check_r2_func
    scan_barcode_from_base64 = scan_barcode_func
    moderate_image = mod_image_func
    log_moderation_incident = log_mod_func
    get_image_hash = hash_func


# ── Rate limit for the anonymous upload path ──
# Same budget as /api/monitor/check-image's limiter (10 per 5 min per IP,
# routes/monitor.py) because check.html's flow is one upload followed by one
# check — matching budgets keep the two gates coherent. Deliberately a
# SEPARATE store from monitor.py's: sharing _check_rate_store would make
# upload+check draw from one bucket and halve the effective check budget.
# Per-worker in-memory, same as the monitor.py precedent (2 workers → worst
# case 2× the nominal ceiling; acceptable for an abuse gate).
_upload_rate_store = {}  # ip -> (count, window_start)
UPLOAD_RATE_LIMIT_MAX = 10
UPLOAD_RATE_LIMIT_WINDOW = 300  # seconds


def _upload_rate_limited(ip):
    """True if this IP is over the anonymous-upload budget. Counts the call."""
    now = time.time()
    count, window_start = _upload_rate_store.get(ip, (0, now))
    if now - window_start > UPLOAD_RATE_LIMIT_WINDOW:
        count, window_start = 0, now
    if count >= UPLOAD_RATE_LIMIT_MAX:
        return True
    _upload_rate_store[ip] = (count + 1, window_start)
    return False


@images_bp.route('/upload', methods=['POST'])
def api_r2_upload_image():
    """
    Upload an image to R2 temp storage (whatnot/{timestamp}_{id}.jpg).

    Live caller: check.html — the PUBLIC Slab Guard "Check a Comic" page.
    That flow is tokenless BY DESIGN (public users get the SIFT-only check),
    so this endpoint stays unauthenticated; the gates are rate limit +
    moderation, hardened 2026-08-25 when cold traffic arrived.

    ⚰️ REMOVED 2026-08-25: the `sale_id` branch (stored straight to
    sales/{id}/front.jpg via upload_sale_image). DEAD. REASON: no caller ever
    sent sale_id — check.html doesn't, and the whatnot extension records
    sales through /api/sales/record, which does its own inline R2 upload
    server-side (routes/sales_market.py) — while the branch let an
    unauthenticated POST overwrite any sale's stored image. sale_id is now
    explicitly rejected rather than silently ignored so a confused caller
    hears about it (L-SW-2026-020: reinterpreting input is worse than
    refusing it).

    Body: {
        "image": "base64 encoded image data",
        "type": "front"  // accepted but unused; temp path ignores it
    }
    """
    if not R2_AVAILABLE:
        return jsonify({'success': False, 'error': 'Image storage not configured'}), 503

    if _upload_rate_limited(request.remote_addr or 'unknown'):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded. Try again in a few minutes.'
        }), 429

    # silent=True: a malformed/non-JSON body (routine from bot scanners on a
    # public endpoint) must land in OUR 400 below, not Flask's default
    # error page — same lesson /submission carries (L-SW-2026-007).
    data = request.get_json(silent=True) or {}
    image_data = data.get('image')

    if not image_data:
        return jsonify({'success': False, 'error': 'Image data required'}), 400

    if data.get('sale_id'):
        return jsonify({
            'success': False,
            'error': 'sale_id is no longer accepted here; sale images are '
                     'uploaded via /api/sales/record.'
        }), 400

    # Content moderation BEFORE storing — mirrors every other upload surface.
    # user_id is normally None here (public page); incidents still log.
    if moderate_image:
        mod_result = moderate_image(image_data)
        if mod_result.get('blocked'):
            if log_moderation_incident and get_image_hash:
                log_moderation_incident(
                    getattr(g, 'user_id', None), '/api/images/upload',
                    mod_result, get_image_hash(image_data)
                )
            return jsonify({
                'success': False,
                'error': 'Image rejected: inappropriate content detected.',
                'moderation': True
            }), 400
        if mod_result.get('warnings'):
            if log_moderation_incident and get_image_hash:
                log_moderation_incident(
                    getattr(g, 'user_id', None), '/api/images/upload',
                    mod_result, get_image_hash(image_data)
                )

    result = upload_temp_image(image_data, 'whatnot')
    return jsonify(result)


# ⚰️ REMOVED 2026-08-25: POST /api/images/upload-for-sale. DEAD.
# REASON: zero live callers — its only nominal caller was uploadImage() in
# CCExtensions/whatnot-valuator/lib/collectioncalc.js, which was exported but
# never invoked (removed in the same unit, manifest 2.42.2). The whatnot
# extension actually ships images inline with /api/sales/record, which does
# its own server-side R2 upload (routes/sales_market.py) — all 4,113
# market_sales rows with R2 sales/ URLs came from there, verified read-only
# 2026-08-25. Meanwhile the endpoint let an UNAUTHENTICATED post overwrite
# image_url, upc_main, upc_addon and is_reprint on ANY market_sales row — a
# corpus-tamper surface with no legitimate user. Deleting beat hardening.
# Do not re-add without an authenticated caller that actually needs it.


@images_bp.route('/submission', methods=['POST'])
def api_upload_submission_image():
    """
    Upload an image for a B4Cert submission (future).
    Supports front, back, spine, centerfold.
    
    Body: {
        "image": "base64 encoded image data",
        "submission_id": "uuid-string",
        "type": "front" | "back" | "spine" | "centerfold"
    }
    """
    if not R2_AVAILABLE:
        print('[IMG-SUBMIT] reject: R2 not configured')
        return jsonify({'success': False, 'error': 'Image storage not configured'}), 503

    # ── Body arrival, measured before parsing ───────────────────────────────
    # This endpoint lost user 38's entire collection on 2026-08-06: 69× 400,
    # 11× 500, 10× 200 — and the ten successes took 52–85s, past app.html's 30s
    # client timeout, so the browser saved all-null while the server succeeded.
    #
    # Every one of the 69 400s logged error_message NULL. Since all four reject
    # branches below return jsonify({'error': ...}) and after_request reads that
    # key (proven: /api/grade 429s on the same account logged 'monthly_limit'),
    # NONE of them came from this route — they were raised by request.get_json()
    # before the handler and rendered as HTML. That is what made the cause
    # inferable but not knowable.
    #
    # get_json(silent=True) keeps the failure inside this handler so it can
    # self-report (L-SW-2026-007) instead of becoming an anonymous Werkzeug
    # page. Same 400 status; a JSON body the client can actually read.
    declared = request.content_length
    try:
        received = len(request.get_data(cache=True))
    except Exception:
        received = None

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        print(f'[IMG-SUBMIT] reject=unparseable-body user={getattr(g, "user_id", None)} '
              f'declared={declared} received={received} '
              f'truncated={received is not None and declared is not None and received < declared} '
              f'ctype={request.content_type!r} device={getattr(g, "device_type", "?")}')
        return jsonify({
            'success': False,
            'error': 'Request body was not readable as JSON',
            'declared_bytes': declared,
            'received_bytes': received,
        }), 400

    image_data = data.get('image')
    submission_id = data.get('submission_id')
    image_type = data.get('type', 'front')

    if not image_data:
        print(f'[IMG-SUBMIT] reject=no-image user={getattr(g, "user_id", None)} '
              f'declared={declared} received={received} keys={sorted(data.keys())}')
        return jsonify({'success': False, 'error': 'Image data required'}), 400
    if not submission_id:
        print(f'[IMG-SUBMIT] reject=no-submission-id user={getattr(g, "user_id", None)}')
        return jsonify({'success': False, 'error': 'submission_id required'}), 400
    if image_type not in ['front', 'back', 'spine', 'centerfold']:
        print(f'[IMG-SUBMIT] reject=bad-type type={image_type!r}')
        return jsonify({'success': False, 'error': 'type must be front, back, spine, or centerfold'}), 400

    print(f'[IMG-SUBMIT] accept user={getattr(g, "user_id", None)} type={image_type} '
          f'sub={submission_id} declared={declared} received={received} '
          f'b64_len={len(image_data)} device={getattr(g, "device_type", "?")}')

    # Content moderation check BEFORE storing
    if moderate_image:
        user_id = getattr(g, 'user_id', None)
        t_mod = time.time()
        mod_result = moderate_image(image_data)
        mod_ms = int((time.time() - t_mod) * 1000)
        if mod_result.get('blocked'):
            log_moderation_incident(user_id, '/api/images/submission', mod_result, get_image_hash(image_data))
            print(f'[IMG-SUBMIT] reject=moderation user={user_id} type={image_type} '
                  f'mod_ms={mod_ms} reason={mod_result.get("reason")!r}')
            return jsonify({
                'success': False,
                'error': 'Image rejected: inappropriate content detected.',
                'moderation': True
            }), 400
        if mod_result.get('warnings'):
            log_moderation_incident(user_id, '/api/images/submission', mod_result, get_image_hash(image_data))
    else:
        mod_ms = None

    t_up = time.time()
    result = upload_submission_image(submission_id, image_data, image_type)
    up_ms = int((time.time() - t_up) * 1000)

    if not result.get('success'):
        # This used to return HTTP 200 carrying {'success': False}. The client
        # reads the body and behaves correctly either way, but request_logs only
        # sees the STATUS — so every R2 failure was recorded as a success and was
        # structurally invisible to exactly the kind of investigation this
        # endpoint just cost us. 502 makes it visible without changing what the
        # client does (app.html checks uploadResult.success, never response.ok).
        print(f'[IMG-SUBMIT] fail=r2 user={getattr(g, "user_id", None)} type={image_type} '
              f'sub={submission_id} up_ms={up_ms} error={result.get("error")!r}')
        return jsonify(result), 502

    print(f'[IMG-SUBMIT] ok user={getattr(g, "user_id", None)} type={image_type} '
          f'sub={submission_id} bytes={result.get("size")} mod_ms={mod_ms} up_ms={up_ms}')
    return jsonify(result)


@images_bp.route('/status', methods=['GET'])
def api_images_status():
    """Check R2 storage connection status"""
    if not R2_AVAILABLE:
        return jsonify({'connected': False, 'error': 'R2 module not loaded'})

    result = check_r2_connection() if check_r2_connection else {'connected': False}
    return jsonify(result)


# ============================================================
# EXTRA PHOTOS — Enhanced Slab Guard fingerprinting
# ============================================================

EXTRA_PHOTO_TYPES = [
    'defect',           # Close-up of a specific defect (spine tick, corner ding, crease)
    'closeup_front',    # Zoomed-in front cover detail
    'closeup_back',     # Zoomed-in back cover detail
    'closeup_spine',    # Zoomed-in spine detail
    'edge_top',         # High-res crop of top edge
    'edge_bottom',      # High-res crop of bottom edge
    'edge_left',        # High-res crop of left edge
    'edge_right',       # High-res crop of right edge
    'alternate_front',  # Different photo of front cover (different angle/lighting)
    'alternate_back',   # Different photo of back cover
    'other',            # Anything else the user wants to document
]


@images_bp.route('/upload-extra', methods=['POST'])
@require_auth
@require_approved
def api_upload_extra_photo():
    """
    Upload an extra photo for enhanced Slab Guard fingerprinting.
    Extra photos are stored in the collections.photos JSONB under an 'extra' array.

    Body: {
        "image": "base64 encoded image data",
        "comic_id": 123,
        "photo_type": "defect" | "closeup_front" | "edge_top" | ... (see EXTRA_PHOTO_TYPES),
        "label": "Spine tick at 2 o'clock position"  // optional user description
    }

    Requires multi_photo feature (paid plans only).
    Limits: pro=4, guard=8, dealer=12 extra photos per comic.
    """
    if not R2_AVAILABLE:
        return jsonify({'success': False, 'error': 'Image storage not configured'}), 503

    data = request.get_json() or {}
    image_data = data.get('image')
    comic_id = data.get('comic_id')
    photo_type = data.get('photo_type', 'other')
    label = data.get('label', '')

    if not image_data:
        return jsonify({'success': False, 'error': 'image is required'}), 400
    if not comic_id:
        return jsonify({'success': False, 'error': 'comic_id is required'}), 400
    if photo_type not in EXTRA_PHOTO_TYPES:
        return jsonify({
            'success': False,
            'error': f'photo_type must be one of: {", ".join(EXTRA_PHOTO_TYPES)}'
        }), 400

    # Check billing: extra photos require paid plan
    try:
        from routes.billing import check_feature_access, PLANS, get_user_plan
        allowed, message = check_feature_access(g.user_id, 'extra_photos')
        if not allowed:
            return jsonify({
                'success': False,
                'error': message,
                'upgrade_required': True,
                'upgrade_url': '/pricing.html'
            }), 403

        # Get the per-comic limit for this plan
        user_plan = get_user_plan(g.user_id)
        plan_key = user_plan['plan'] if user_plan else 'free'
        plan = PLANS.get(plan_key, PLANS['free'])
        extra_limit = plan.get('extra_photos_limit', 0)
    except ImportError:
        extra_limit = 4  # Default if billing module unavailable

    database_url = os.environ.get('DATABASE_URL')
    conn = None

    try:
        conn = _dbpool.get_db()
        cur = conn.cursor()

        # Verify comic belongs to user and get current photos
        cur.execute(
            "SELECT photos FROM collections WHERE id = %s AND user_id = %s",
            (comic_id, g.user_id)
        )
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Comic not found or access denied'}), 404

        photos = row[0]
        if photos and isinstance(photos, str):
            photos = json.loads(photos)
        if not photos or not isinstance(photos, dict):
            photos = {}

        # Check extra photo count against plan limit
        extras = photos.get('extra', [])
        if len(extras) >= extra_limit:
            return jsonify({
                'success': False,
                'error': f'Extra photo limit reached ({extra_limit} per comic on your plan)',
                'current_count': len(extras),
                'limit': extra_limit,
                'upgrade_required': True,
            }), 403

        # Content moderation check
        if moderate_image:
            mod_result = moderate_image(image_data)
            if mod_result.get('blocked'):
                if log_moderation_incident and get_image_hash:
                    log_moderation_incident(
                        g.user_id, '/api/images/upload-extra',
                        mod_result, get_image_hash(image_data)
                    )
                return jsonify({
                    'success': False,
                    'error': 'Image rejected: inappropriate content detected.',
                    'moderation': True
                }), 400
            # Log warnings (allowed through) — this also captures fail-open
            # markers ('Moderation check failed' / 'not configured'), which
            # every sibling call site persists; without this branch a
            # fail-open here was stdout-only.
            if mod_result.get('warnings'):
                if log_moderation_incident and get_image_hash:
                    log_moderation_incident(
                        g.user_id, '/api/images/upload-extra',
                        mod_result, get_image_hash(image_data)
                    )

        # Upload to R2: collections/{comic_id}/extra_{index}.jpg
        extra_index = len(extras)
        r2_path = f"collections/{comic_id}/extra_{extra_index}.jpg"

        try:
            from r2_storage import upload_image
            upload_result = upload_image(image_data, r2_path)
        except ImportError:
            return jsonify({'success': False, 'error': 'R2 storage module not available'}), 503

        if not upload_result.get('success'):
            return jsonify(upload_result), 500

        photo_url = upload_result['url']

        # Append to extras array
        extras.append({
            'type': photo_type,
            'label': label,
            'url': photo_url,
        })
        photos['extra'] = extras

        # Update DB
        cur.execute(
            "UPDATE collections SET photos = %s, updated_at = NOW() WHERE id = %s AND user_id = %s",
            (json.dumps(photos), comic_id, g.user_id)
        )
        conn.commit()

        return jsonify({
            'success': True,
            'url': photo_url,
            'photo_type': photo_type,
            'label': label,
            'index': extra_index,
            'extra_count': len(extras),
            'limit': extra_limit,
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Upload extra photo error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if conn:
            cur.close()
            conn.close()


@images_bp.route('/delete-extra', methods=['POST'])
@require_auth
@require_approved
def api_delete_extra_photo():
    """
    Delete an extra photo from a comic's enhanced fingerprint set.

    Body: {
        "comic_id": 123,
        "index": 2       // index in the extras array to remove
    }
    """
    data = request.get_json() or {}
    comic_id = data.get('comic_id')
    index = data.get('index')

    if not comic_id or index is None:
        return jsonify({'success': False, 'error': 'comic_id and index are required'}), 400

    database_url = os.environ.get('DATABASE_URL')
    conn = None

    try:
        conn = _dbpool.get_db()
        cur = conn.cursor()

        # Get current photos
        cur.execute(
            "SELECT photos FROM collections WHERE id = %s AND user_id = %s",
            (comic_id, g.user_id)
        )
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'error': 'Comic not found or access denied'}), 404

        photos = row[0]
        if photos and isinstance(photos, str):
            photos = json.loads(photos)
        if not photos or not isinstance(photos, dict):
            return jsonify({'success': False, 'error': 'No photos found'}), 404

        extras = photos.get('extra', [])
        if index < 0 or index >= len(extras):
            return jsonify({'success': False, 'error': f'Invalid index {index} (have {len(extras)} extras)'}), 400

        # Remove the photo (R2 object remains — could add cleanup later)
        removed = extras.pop(index)
        photos['extra'] = extras

        cur.execute(
            "UPDATE collections SET photos = %s, updated_at = NOW() WHERE id = %s AND user_id = %s",
            (json.dumps(photos), comic_id, g.user_id)
        )
        conn.commit()

        return jsonify({
            'success': True,
            'removed': removed,
            'extra_count': len(extras),
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Delete extra photo error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if conn:
            cur.close()
            conn.close()


@images_bp.route('/extra-types', methods=['GET'])
def api_extra_photo_types():
    """Return the list of valid extra photo types with descriptions."""
    types = [
        {'type': 'defect', 'description': 'Close-up of a specific defect (spine tick, corner ding, crease)'},
        {'type': 'closeup_front', 'description': 'Zoomed-in front cover detail'},
        {'type': 'closeup_back', 'description': 'Zoomed-in back cover detail'},
        {'type': 'closeup_spine', 'description': 'Zoomed-in spine detail'},
        {'type': 'edge_top', 'description': 'High-resolution crop of top edge'},
        {'type': 'edge_bottom', 'description': 'High-resolution crop of bottom edge'},
        {'type': 'edge_left', 'description': 'High-resolution crop of left edge'},
        {'type': 'edge_right', 'description': 'High-resolution crop of right edge'},
        {'type': 'alternate_front', 'description': 'Different photo of front cover (different angle/lighting)'},
        {'type': 'alternate_back', 'description': 'Different photo of back cover'},
        {'type': 'other', 'description': 'Any other identifying detail'},
    ]
    return jsonify({'success': True, 'types': types})
