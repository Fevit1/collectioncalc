"""
Grading Blueprint - Comic valuation and extraction endpoints
Routes: /api/valuate, /api/extract, /api/cache/check, /api/messages, /api/grade
"""
import os
import json
import time
import concurrent.futures
from flask import Blueprint, jsonify, request, g

# Create blueprint
grading_bp = Blueprint('grading', __name__, url_prefix='/api')

# Long-edge cap for grading-input normalization (/api/grade, /api/messages).
# These endpoints normalize up to 4 photos per request; uncapped 12MP decodes
# spiked RSS into the 512MB Starter ceiling and OOM-killed the service twice
# on 2026-07-16. 2000px: above the ~1568px the Anthropic API downscales to
# (no model-visible loss), and ≤ half of a 4032px iPhone photo, which lets
# libjpeg draft-mode decode at 1/2 scale — the full bitmap is never allocated.
# The extraction path uses its own higher cap (EXTRACT_MAX_LONG_EDGE=4096 in
# comic_extraction.py — barcode-preserving). Env-overridable for booth tuning.
GRADING_MAX_LONG_EDGE = int(os.environ.get('GRADING_MAX_LONG_EDGE', '2000'))

# These will be imported from wsgi.py when needed
from auth import require_auth, require_approved
from admin import log_api_usage
from models import SONNET, get_model, call_with_fallback

# Module imports with fallbacks (set by wsgi.py)
get_valuation_with_ebay = None
extract_from_base64 = None
moderate_image = None
log_moderation_incident = None
get_image_hash = None
ANTHROPIC_API_KEY = None
ANTHROPIC_AVAILABLE = False
anthropic = None


def init_modules(valuation_func, extraction_func, moderation_func, 
                 log_mod_func, hash_func, anthropic_key, anthropic_lib, anthropic_avail):
    """Initialize modules from wsgi.py"""
    global get_valuation_with_ebay, extract_from_base64, moderate_image
    global log_moderation_incident, get_image_hash, ANTHROPIC_API_KEY
    global anthropic, ANTHROPIC_AVAILABLE
    
    get_valuation_with_ebay = valuation_func
    extract_from_base64 = extraction_func
    moderate_image = moderation_func
    log_moderation_incident = log_mod_func
    get_image_hash = hash_func
    ANTHROPIC_API_KEY = anthropic_key
    anthropic = anthropic_lib
    ANTHROPIC_AVAILABLE = anthropic_avail


class _GradeTimings:
    """Segment timer for /api/grade. Deliberately a SEPARATE, self-contained
    twin of _Timings in sales_valuation.py rather than a shared base class.

    WHY DUPLICATED AND NOT REFACTORED. That harness is deployed, verified, and
    is currently the only instrument measuring the FMV leg (557146d, live
    2026-08-09). Factoring both onto a common parent would edit working
    production instrumentation to add instrumentation elsewhere — and the fields
    genuinely differ (that one emits per-query row counts; this one emits token
    counts and image counts). Two small honest twins beat one clever shared
    thing here.

    WHAT THE SEGMENTS MEAN, and why each is separated:

      cap          the per-tier monthly cap check. One SELECT, sometimes an
                   UPDATE + commit. Expected small; isolated because it is the
                   only DB work that happens BEFORE the body is read.
      body         request.get_json(). ⚠️ THIS IS NOT JUST PARSING — it is where
                   the multi-megabyte base64 request body is read off the wire.
                   On a mobile uplink this can be the largest segment in the
                   whole request and it is invisible to every other measure.
      normalize    normalize_for_photo_type per photo: decode (incl. HEIC),
                   EXIF-transpose, downscale to GRADING_MAX_LONG_EDGE, re-encode
                   JPEG. The 2026-07-16 OOM code path. CPU-bound, N photos.
      quality      check_photo_quality_base64 — first image only.
      moderation   AWS Rekognition. ⚠️ Counted separately AND per call, because
                   unlike the quality gate this loop has no `break`: it makes one
                   network round trip PER PHOTO, sequentially.
      vision       the Anthropic Sonnet call(s). runs=1 is one call; runs>1 fans
                   out across a thread pool, so elapsed is the SLOWEST call, not
                   the sum — hence vision_calls is emitted beside it.
      parse        parse_grading_response / parse_multi_run_responses.
      post         counter increment, usage read, snap, retention scheduling.
      total        handler entry → response.

    ⚠️ WHAT THIS STILL CANNOT SEE (same blind spot as the valuation harness, and
    it must be stated rather than assumed away): time the request spent QUEUED IN
    GUNICORN before the handler ran, and TLS/upload time before gunicorn began
    handing the body over. `total` starts at handler entry. If `total` comes back
    materially below what the browser shows, the remainder is queueing, upload,
    or WSGI — not anything below.
    """
    __slots__ = ('t0', 't0_wall', 'marks', 'extras')

    def __init__(self):
        self.t0 = time.perf_counter()
        self.t0_wall = time.time()
        self.marks = {}
        self.extras = {}

    def mark(self, name):
        self.marks[name] = time.perf_counter()

    def note(self, **kw):
        self.extras.update(kw)

    def emit(self, outcome, title=None, issue=None):
        """One greppable line, prefix [GRADE-TIMING]. print() for the same reason
        the valuation harness uses it: PYTHONUNBUFFERED=1 is set in the Dockerfile
        so it flushes immediately (L-2026-020)."""
        try:
            def span(a, b):
                if a in self.marks and b in self.marks:
                    return (self.marks[b] - self.marks[a]) * 1000.0
                return -1.0

            total_ms = (time.perf_counter() - self.t0) * 1000.0
            try:
                receipt_ms = max(0.0, (self.t0_wall - g.start_time) * 1000.0)
            except Exception:
                receipt_ms = -1.0

            parts = [
                'total=%.0fms' % total_ms,
                'before_request_to_handler=%.0fms' % receipt_ms,
                'cap=%.0fms' % span('handler', 'cap_done'),
                'body=%.0fms' % span('cap_done', 'body_done'),
                'normalize=%.0fms' % span('normalize_start', 'normalize_done'),
                'imgmeas=%.0fms' % span('normalize_done', 'imgmeas_done'),
                'quality=%.0fms' % span('imgmeas_done', 'quality_done'),
                'moderation=%.0fms' % span('quality_done', 'moderation_done'),
                'vision=%.0fms' % span('vision_start', 'vision_done'),
                'parse=%.0fms' % span('vision_done', 'parse_done'),
                'post=%.0fms' % span('parse_done', 'response'),
            ]
            for k in ('images', 'payload_kb', 'norm_kb', 'dims', 'runs',
                      'vision_calls', 'moderation_calls', 'model',
                      'in_tok', 'out_tok', 'cache_create', 'cache_read'):
                if k in self.extras:
                    parts.append('%s=%s' % (k, self.extras[k]))
            parts.append('outcome=%s' % outcome)
            parts.append('title=%r' % (title or '')[:60])
            parts.append('issue=%r' % (issue or ''))
            print('[GRADE-TIMING] ' + ' '.join(parts))
        except Exception:
            # Instrumentation must never break the endpoint it measures.
            pass


class _ExtractTimings(_GradeTimings):
    """Segment timer for /api/extract — the comic-ID leg.

    Separate from the grade leg because they are separate requests at separate
    user moments (upload vs the grade button). Treating them as one ~30s item is
    what the roadmap did from June to 2026-08-10; this line and [GRADE-TIMING]
    are what let them be costed apart.

    Marks inside extract_from_base64 are recorded through the duck-typed
    recorder this class satisfies (.mark/.note), so comic_extraction never
    imports anything from routes.

      body        get_json() — reads the base64 photo off the wire.
      quality     the LENIENT extract-floor gate.
      moderation  one Rekognition round trip (single photo here — unlike
                  /api/grade, which loops).
      normalize   decode + EXIF/orientation + downscale to EXTRACT_MAX_LONG_EDGE
                  (4096, barcode-preserving — higher than the grading cap).
      barcode     pyzbar scan across 4 rotations. barcode=hit|miss|error.
      vision1     the FIRST Sonnet pass, alone.
      vision2     pass 1 → all vision done. ⚠️ Non-zero ONLY when the 180 deg
                  re-read fired, so it is the direct latency cost of that path.
                  Named vision2, NOT reread, because `reread` is the STATE field
                  below and one line must never carry the same key twice
                  meaning two different things (L-SW-2026-020).
      post        barcode decode, field cleanup, response build.

    ⚠️ THE POINT OF reread=. It is emitted on every request, including
    not_needed. The old code printed only when the re-read FIRED, so a clean run
    logged nothing and its absence was unreadable — healthy and never-ran looked
    identical. Same silence the drift guard had.
    """
    __slots__ = ()

    def emit(self, outcome, title=None, issue=None):
        try:
            def span(a, b):
                if a in self.marks and b in self.marks:
                    return (self.marks[b] - self.marks[a]) * 1000.0
                return -1.0

            total_ms = (time.perf_counter() - self.t0) * 1000.0
            try:
                receipt_ms = max(0.0, (self.t0_wall - g.start_time) * 1000.0)
            except Exception:
                receipt_ms = -1.0

            parts = [
                'total=%.0fms' % total_ms,
                'before_request_to_handler=%.0fms' % receipt_ms,
                'body=%.0fms' % span('handler', 'body_done'),
                'quality=%.0fms' % span('body_done', 'quality_done'),
                'moderation=%.0fms' % span('quality_done', 'moderation_done'),
                'normalize=%.0fms' % span('normalize_start', 'normalize_done'),
                'barcode=%.0fms' % span('normalize_done', 'barcode_done'),
                'vision1=%.0fms' % span('barcode_done', 'vision1_done'),
                'vision2=%.0fms' % span('vision1_done', 'vision_done'),
                'post=%.0fms' % span('vision_done', 'post_done'),
            ]
            for k in ('payload_kb', 'photo_type', 'barcode', 'vision_calls',
                      'reread', 'reread_reason', 'model', 'in_tok', 'out_tok',
                      'outcome_detail'):
                if k in self.extras:
                    parts.append('%s=%s' % (k, self.extras[k]))
            parts.append('outcome=%s' % outcome)
            print('[EXTRACT-TIMING] ' + ' '.join(parts))
        except Exception:
            pass


@grading_bp.route('/valuate', methods=['POST'])
@require_auth
@require_approved
def api_valuate():
    """Get comic valuation using eBay market data"""
    if not get_valuation_with_ebay:
        return jsonify({'success': False, 'error': 'Valuation module not available'}), 503
    
    data = request.get_json() or {}
    title = data.get('title', '')
    issue = data.get('issue', '')
    
    if not title or not issue:
        return jsonify({'success': False, 'error': 'Title and issue are required'}), 400
    
    result = get_valuation_with_ebay(title, issue, data.get('grade', 'VF'), 
                                      data.get('publisher'), data.get('year'))
    
    # Log API usage if result indicates web search was used
    if isinstance(result, dict) and result.get('source') == 'web_search':
        log_api_usage(g.user_id, '/api/valuate', SONNET, 
                      result.get('input_tokens', 0), result.get('output_tokens', 0))
    
    # Convert dataclass to dict if needed
    if hasattr(result, '__dict__') and not isinstance(result, dict):
        result = result.__dict__
    
    return jsonify(result)


@grading_bp.route('/cache/check', methods=['POST'])
@require_auth  
@require_approved
def api_cache_check():
    """Check if a comic title/issue combination exists in search_cache"""
    import psycopg2
    import db as _dbpool

    data = request.get_json() or {}
    title = data.get('title', '').strip()
    issue = data.get('issue', '').strip()
    
    if not title or not issue:
        return jsonify({'success': False, 'error': 'Title and issue are required'}), 400
    
    # Build search key matching existing format: "title|issue" (lowercase, no grade)
    search_key = f"{title.lower()}|{issue}"
    
    database_url = os.environ.get('DATABASE_URL')
    conn = None
    
    try:
        conn = _dbpool.get_db()
        cur = conn.cursor()
        
        # Check if cache entry exists (recent within 48 hours)
        cur.execute("""
            SELECT cached_at 
            FROM search_cache 
            WHERE search_key = %s 
            AND cached_at > CURRENT_TIMESTAMP - INTERVAL '48 hours'
        """, (search_key,))
        
        result = cur.fetchone()
        
        if result:
            return jsonify({
                'success': True,
                'cached': True,
                'lastChecked': result[0].isoformat()
            })
        else:
            return jsonify({
                'success': True, 
                'cached': False,
                'lastChecked': None
            })
            
    except Exception as e:
        print(f"Cache check error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
        
    finally:
        if conn:
            cur.close()
            conn.close()


@grading_bp.route('/extract', methods=['POST'])
@require_auth
@require_approved
def api_extract():
    """Extract comic information from image using AI"""
    _t = _ExtractTimings()
    _t.mark('handler')

    if not extract_from_base64:
        _t.emit('module_unavailable')
        return jsonify({'success': False, 'error': 'Extraction module not available'}), 503

    data = request.get_json() or {}
    _t.mark('body_done')
    image_data = data.get('image')

    if not image_data:
        _t.emit('no_image')
        return jsonify({'success': False, 'error': 'Image data is required'}), 400

    _t.note(payload_kb=int(len(image_data) / 1024))

    # Photo quality gate — catch tiny/blurry photos before Claude API call.
    # Batch 7: extraction only needs to READ the cover, so use the lenient
    # 'extract' floor (legible eBay covers ~394px must pass here; the stricter
    # grading floor is applied later at /api/grade).
    from routes.fingerprint_utils import check_photo_quality_base64
    quality = check_photo_quality_base64(image_data, purpose='extract')
    if not quality['ok']:
        _t.mark('quality_done')
        _t.emit('quality_fail')
        return jsonify({
            'success': False,
            'quality_issue': True,
            'quality_message': quality['message'],
            'tip': quality['tip'],
            'error': quality['message']
        }), 400
    _t.mark('quality_done')

    # Content moderation check BEFORE processing
    if moderate_image:
        mod_result = moderate_image(image_data)
        if mod_result.get('blocked'):
            log_moderation_incident(g.user_id, '/api/extract', mod_result, get_image_hash(image_data))
            _t.mark('moderation_done')
            _t.emit('moderation_blocked')
            return jsonify({
                'success': False,
                'error': 'Image rejected: inappropriate content detected.',
                'moderation': True
            }), 400
        # Log warnings (but allow through)
        if mod_result.get('warnings'):
            log_moderation_incident(g.user_id, '/api/extract', mod_result, get_image_hash(image_data))
    _t.mark('moderation_done')

    media_type = data.get('media_type', 'image/jpeg')
    # Per-photo orientation policy is server-side (centerfold is EXIF-only).
    # Defaults to 'front' — the app.html main extraction path is always the cover.
    photo_type = data.get('photo_type', 'front')
    _t.note(photo_type=photo_type)
    result = extract_from_base64(image_data, media_type, photo_type, timings=_t)

    if result.get('success'):
        # Extraction runs on the sonnet tier (comic_extraction.call_with_fallback);
        # log the actual model so per-extract cost attribution stays accurate after
        # the 2026-06-16 haiku→sonnet identification flip.
        # ⚠️ These token counts were a structural 0 until 2026-08-10 —
        # extract_from_base64 never returned the keys this line reads. The model
        # name was right, so every api_usage row for /api/extract looked
        # well-formed while recording no cost at all (L-SW-2026-016). The
        # function now returns real counts summed across every vision pass.
        log_api_usage(g.user_id, '/api/extract', get_model('sonnet'),
                      result.get('input_tokens', 0), result.get('output_tokens', 0))

    _t.note(model=get_model('sonnet'))
    _t.emit('ok' if result.get('success') else 'fail')
    return jsonify(result)


@grading_bp.route('/messages', methods=['POST'])
@require_auth
@require_approved
def api_messages():
    """Anthropic API proxy for AI-powered grading analysis"""
    if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
        return jsonify({'error': 'Anthropic API not available'}), 503
    
    data = request.get_json() or {}
    
    # Photo quality gate — check images before expensive Claude grading call
    from routes.fingerprint_utils import check_photo_quality_base64
    for msg in data.get('messages', []):
        content = msg.get('content', [])
        if isinstance(content, list):
            for block in content:
                if block.get('type') == 'image' and block.get('source', {}).get('type') == 'base64':
                    image_data = block['source'].get('data', '')
                    if image_data:
                        # Batch 7: grading keeps the strict floor (purpose='grade').
                        quality = check_photo_quality_base64(image_data, purpose='grade')
                        if not quality['ok']:
                            return jsonify({
                                'error': quality['message'],
                                'quality_fail': True,
                                'tip': quality['tip'],
                                'width': quality.get('width'),
                                'height': quality.get('height')
                            }), 400
                        break  # Only check first image — rest are same session photos
            break  # Only need to check first message block

    # Content moderation: check any images in the messages
    if moderate_image:
        for msg in data.get('messages', []):
            content = msg.get('content', [])
            if isinstance(content, list):
                for block in content:
                    if block.get('type') == 'image' and block.get('source', {}).get('type') == 'base64':
                        image_data = block['source'].get('data', '')
                        if image_data:
                            mod_result = moderate_image(image_data)
                            if mod_result.get('blocked'):
                                log_moderation_incident(g.user_id, '/api/messages', mod_result, get_image_hash(image_data))
                                return jsonify({
                                    'error': 'Image rejected: inappropriate content detected.',
                                    'moderation': True
                                }), 400
                            if mod_result.get('warnings'):
                                log_moderation_incident(g.user_id, '/api/messages', mod_result, get_image_hash(image_data))
    
    # --- Per-photo grading-input orientation normalization (server-side,
    #     authoritative). The grading frontend sends `photo_type` for steps
    #     2-4 (spine/back/centerfold); normalize each image block before the
    #     vision call so the model never reads a sideways photo. centerfold is
    #     EXIF-only (never force-rotated to portrait). Absent photo_type (e.g. the
    #     follow-up-chat caller) → skip, preserving prior behavior. Strip the
    #     field so it isn't forwarded to the Anthropic API (unknown key). ---
    photo_type = data.pop('photo_type', None)
    if photo_type:
        from comic_extraction import normalize_for_photo_type
        for msg in data.get('messages', []):
            content = msg.get('content', [])
            if not isinstance(content, list):
                continue
            for block in content:
                if block.get('type') == 'image' and block.get('source', {}).get('type') == 'base64':
                    src = block['source']
                    try:
                        src['data'] = normalize_for_photo_type(src.get('data', ''), photo_type,
                                                               max_long_edge=GRADING_MAX_LONG_EDGE)
                        src['media_type'] = 'image/jpeg'  # normalizer always emits JPEG
                    except Exception as e:
                        # Never fail the grade over a normalize hiccup — send original.
                        print(f"[Grading] photo normalize skipped ({photo_type}): {e}")

    data['temperature'] = 0  # Force deterministic responses for consistent grading

    # Centralize model selection: ignore any client-supplied `model` (the
    # frontend historically hard-coded a now-retiring string) and resolve the
    # model from models.py via the requested tier (default 'sonnet'), with
    # automatic fallback if the primary 404s. One place to update next time.
    data.pop('model', None)
    tier = data.pop('tier', 'sonnet')
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    try:
        response = call_with_fallback(client, tier, **data)

        log_api_usage(g.user_id, '/api/messages', get_model(tier),
                      response.usage.input_tokens, response.usage.output_tokens)

        response_data = {
            'id': response.id,
            'type': response.type,
            'role': response.role,
            'content': [{'type': block.type, 'text': getattr(block, 'text', '')} for block in response.content],
            'usage': {'input_tokens': response.usage.input_tokens, 'output_tokens': response.usage.output_tokens}
        }
        return jsonify(response_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ──────────────────────────────────────────────
# NEW: Structured Grading Endpoint (v2)
# ──────────────────────────────────────────────

@grading_bp.route('/grade', methods=['POST'])
@require_auth
@require_approved
def api_grade():
    """
    Structured comic grading with category scoring and optional multi-run.

    Accepts:
        images: list of {base64, media_type, label} objects
        title: comic title (from extraction)
        issue: issue number
        publisher: publisher name
        runs: number of grading passes (1-3, default 1)

    Returns:
        Computed grade with full category breakdown
    """
    _t = _GradeTimings()
    _t.mark('handler')

    if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
        _t.emit('anthropic_unavailable')
        return jsonify({'error': 'Anthropic API not available'}), 503

    # ── Grading cap check (per-tier monthly cap; admins exempt) ──
    import psycopg2
    import db as _dbpool
    from psycopg2.extras import RealDictCursor
    from datetime import datetime, timezone
    # Per-tier monthly cap sourced from billing PLANS (single source of truth
    # shared with the pricing page + /my-plan): Free 25 / Pro 100 / Guard 250 /
    # Dealer 1000. Enforced against the gradings_this_month counter that already
    # gates today — the legacy billing valuations_this_month counter stays unused
    # (the account.html usage meter still reads it; reconciling those two counters
    # is a separate freemium-pass item, intentionally NOT bridged here).
    from routes.billing import PLANS
    DEFAULT_GRADING_LIMIT = PLANS['free']['valuations_per_month']

    database_url = os.environ.get('DATABASE_URL')
    cap_conn = None
    try:
        cap_conn = _dbpool.get_db(dict_rows=True)
        cap_cur = cap_conn.cursor()

        cap_cur.execute(
            "SELECT plan, is_admin, gradings_this_month, gradings_reset_date FROM users WHERE id = %s",
            (g.user_id,)
        )
        cap_user = cap_cur.fetchone()

        if cap_user and not cap_user.get('is_admin', False):
            plan_key = (cap_user.get('plan') or 'free').strip().lower()
            monthly_limit = PLANS.get(plan_key, PLANS['free']).get(
                'valuations_per_month', DEFAULT_GRADING_LIMIT)
            now = datetime.now(timezone.utc)
            reset_date = cap_user.get('gradings_reset_date')

            # Reset counter if we're in a new month
            if reset_date is None or (now.year > reset_date.year or now.month > reset_date.month):
                # Calculate next month's first day for reset display
                if now.month == 12:
                    next_reset = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
                else:
                    next_reset = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

                cap_cur.execute(
                    "UPDATE users SET gradings_this_month = 0, gradings_reset_date = %s WHERE id = %s",
                    (next_reset, g.user_id)
                )
                cap_conn.commit()
                gradings_used = 0
                resets_at = next_reset.strftime('%b %d')
            else:
                gradings_used = cap_user.get('gradings_this_month', 0) or 0
                resets_at = reset_date.strftime('%b %d') if reset_date else 'next month'

            # Enforce cap
            if gradings_used >= monthly_limit:
                cap_cur.close()
                cap_conn.close()
                _t.mark('cap_done')
                _t.emit('monthly_limit')
                return jsonify({
                    'success': False,
                    'error': 'monthly_limit',
                    'limit': monthly_limit,
                    'used': gradings_used,
                    'resets_at': resets_at
                }), 429

        cap_cur.close()
    except Exception as e:
        print(f"[WARN] Grading cap check failed (allowing grading): {e}")
    finally:
        if cap_conn:
            try:
                cap_conn.close()
            except:
                pass
    # ── End grading cap check ──
    _t.mark('cap_done')

    # ⚠️ get_json() is where the request BODY is read off the wire, not merely
    # parsed — the payload carries up to 4 base64 photos. On a phone uplink this
    # segment can dominate the request, and nothing downstream would show it.
    data = request.get_json() or {}
    _t.mark('body_done')
    images = data.get('images', [])
    title = data.get('title', 'Unknown')
    issue = data.get('issue', '?')
    publisher = data.get('publisher', 'Unknown')
    num_runs = min(max(data.get('runs', 1), 1), 3)  # clamp 1-3
    _t.note(images=len(images), runs=num_runs,
            payload_kb=int(sum(len(i.get('base64') or '')
                               for i in images) / 1024))

    if not images:
        _t.emit('no_images', title, issue)
        return jsonify({'error': 'At least one image is required'}), 400

    # ── Per-photo normalization BEFORE anything touches the bytes (Section F
    #    Gate 0). This endpoint historically sent raw client bytes + client
    #    media_type straight to the Anthropic API — so HEIC (iPhone default)
    #    hit an API that only accepts JPEG/PNG/GIF/WebP, and EXIF-rotated
    #    photos went to the model sideways (the normalizer was wired into
    #    /api/messages and /api/extract only). normalize_for_photo_type
    #    decodes (incl. HEIC via pillow-heif), fixes orientation per photo
    #    type, and always emits upright JPEG — which also means the quality
    #    gate, Rekognition moderation, and grade retention below all operate
    #    on bytes they can actually read. Labels map 1:1 to photo types
    #    ('Front Cover'→front, 'Spine'→spine, 'Back Cover'→back,
    #    'Centerfold'→centerfold — the landscape-allowed type).
    #    Unlike /api/messages' send-original fallback, an undecodable photo
    #    here fails LOUD with the quality-gate error shape (the frontend
    #    already renders it): forwarding unreadable bytes would just resurface
    #    as an opaque Anthropic 400 → generic 500.
    #    max_long_edge=GRADING_MAX_LONG_EDGE: this endpoint normalizes up to 4
    #    photos per request — full-resolution 12MP decodes OOM-killed the 512MB
    #    instance twice on 2026-07-16. The Anthropic API downscales to ~1568px
    #    internally, so the model sees the same pixels either way.
    from comic_extraction import normalize_for_photo_type
    _t.mark('normalize_start')
    for img in images:
        if not img.get('base64'):
            continue
        label = img.get('label') or 'Photo'
        photo_type = label.lower().split()[0]  # front/spine/back/centerfold
        try:
            img['base64'] = normalize_for_photo_type(img['base64'], photo_type,
                                                     max_long_edge=GRADING_MAX_LONG_EDGE)
            img['media_type'] = 'image/jpeg'  # normalizer always emits JPEG
        except ValueError as e:
            print(f"[Grading] {label} photo undecodable: {e}")
            _t.mark('normalize_done')
            _t.emit('undecodable_photo', title, issue)
            return jsonify({
                'error': f"We couldn't read your {label} photo — the file may be "
                         f"corrupted or in a format we can't process.",
                'quality_fail': True,
                'tip': 'Re-take the photo with your camera, or convert it to JPEG and re-upload.'
            }), 400

    _t.mark('normalize_done')

    # ── Post-normalization measurement. payload_kb above is the INBOUND size;
    #    this is what actually goes to the model, and the two are not the same
    #    number. Separated into its own segment so this diagnostic can never be
    #    mistaken for normalize cost.
    #    WHY DIMENSIONS AND NOT JUST BYTES: Anthropic bills image input at
    #    roughly (w*h)/750 tokens, so dims are the only thing that explains a
    #    token count — and they are also how much detail the grader actually
    #    sees. _decode_normalize_encode draft-decodes at 1/2 before thumbnailing,
    #    so output lands anywhere in (cap/2, cap] — 1000..2000px at the current
    #    cap. A photo landing at the bottom of that band gives the model a
    #    QUARTER of the pixel area of one landing at the top. That is an accuracy
    #    question wearing a token question's clothes, and the strict grading
    #    quality floor exists precisely because defects need detail.
    #    Image.open() parses the JPEG header only — it does NOT decode pixels, so
    #    this allocates the compressed bytes and nothing like a bitmap (the
    #    2026-07-16 OOM class is not in play here).
    try:
        from io import BytesIO as _BytesIO
        import base64 as _b64
        from PIL import Image as _PILImage
        _dims, _norm_chars = [], 0
        for img in images:
            _b = img.get('base64') or ''
            if not _b:
                continue
            _norm_chars += len(_b)
            with _PILImage.open(_BytesIO(_b64.b64decode(_b))) as _im:
                _dims.append('%dx%d' % _im.size)
        _t.note(norm_kb=int(_norm_chars / 1024), dims=','.join(_dims) or 'none')
    except Exception as _e:
        _t.note(dims='unmeasured:%s' % type(_e).__name__)
    _t.mark('imgmeas_done')

    # Photo quality gate
    from routes.fingerprint_utils import check_photo_quality_base64
    for img in images:
        b64 = img.get('base64', '')
        if b64:
            # Batch 7: grading keeps the strict resolution floor (defects need
            # detail) — explicit purpose for clarity vs the lenient extract path.
            quality = check_photo_quality_base64(b64, purpose='grade')
            if not quality['ok']:
                _t.mark('quality_done')
                _t.emit('quality_fail', title, issue)
                return jsonify({
                    'error': quality['message'],
                    'quality_fail': True,
                    'tip': quality['tip'],
                    'width': quality.get('width'),
                    'height': quality.get('height')
                }), 400
            break  # Only check first image
    _t.mark('quality_done')

    # Content moderation
    # ⚠️ Note the absence of a `break` here, unlike the quality gate above: this
    # is one Rekognition network round trip PER PHOTO, sequentially. moderation_calls
    # is emitted so the count is a measurement rather than a reading of this loop.
    _mod_calls = 0
    if moderate_image:
        for img in images:
            b64 = img.get('base64', '')
            if b64:
                _mod_calls += 1
                mod_result = moderate_image(b64)
                if mod_result.get('blocked'):
                    log_moderation_incident(g.user_id, '/api/grade', mod_result, get_image_hash(b64))
                    _t.note(moderation_calls=_mod_calls)
                    _t.mark('moderation_done')
                    _t.emit('moderation_blocked', title, issue)
                    return jsonify({
                        'error': 'Image rejected: inappropriate content detected.',
                        'moderation': True
                    }), 400
                if mod_result.get('warnings'):
                    log_moderation_incident(g.user_id, '/api/grade', mod_result, get_image_hash(b64))
    _t.note(moderation_calls=_mod_calls)
    _t.mark('moderation_done')

    # Build image content blocks for Anthropic API
    image_content = []
    photo_labels = []
    for img in images:
        image_content.append({
            'type': 'image',
            'source': {
                'type': 'base64',
                'media_type': img.get('media_type', 'image/jpeg'),
                'data': img.get('base64', '')
            }
        })
        photo_labels.append(img.get('label', 'Photo'))

    # Build structured grading prompt
    from grading_engine import build_grading_prompt, parse_grading_response, parse_multi_run_responses
    prompt_text = build_grading_prompt(title, issue, publisher, photo_labels)

    # Function to make one grading call
    def run_grading():
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        # Route through models.py sonnet tier with automatic fallback (was a
        # direct create(model=SONNET) with no fallback).
        response = call_with_fallback(
            client, 'sonnet',
            max_tokens=2048,
            temperature=0,
            messages=[{
                'role': 'user',
                'content': [
                    *image_content,
                    {'type': 'text', 'text': prompt_text}
                ]
            }]
        )
        return response

    try:
        total_input_tokens = 0
        total_output_tokens = 0
        _t.mark('vision_start')

        # ⚠️ input_tokens does NOT include cached input. The API reports
        # cache_creation_input_tokens and cache_read_input_tokens as SEPARATE
        # fields, and summing only input_tokens silently undercounts whenever
        # they are non-zero. No cache_control is set anywhere in this path, so
        # both should read 0 — which is exactly why they are worth emitting:
        # a non-zero here means the assumption stopped holding and api_usage
        # started under-reporting, in the same shape as the /api/extract
        # structural zero one path over. Prove the 0, do not assume it.
        cache_create = cache_read = 0

        def _cache_of(resp):
            u = getattr(resp, 'usage', None)
            return ((getattr(u, 'cache_creation_input_tokens', 0) or 0),
                    (getattr(u, 'cache_read_input_tokens', 0) or 0))

        if num_runs == 1:
            # Single run — most common, fastest
            response = run_grading()
            total_input_tokens = response.usage.input_tokens
            total_output_tokens = response.usage.output_tokens
            cache_create, cache_read = _cache_of(response)
            _t.mark('vision_done')
            _t.note(vision_calls=1)

            response_text = response.content[0].text
            result = parse_grading_response(response_text)
            result['run_count'] = 1

        else:
            # Multi-run with thread pool for parallel execution.
            # ⚠️ These run CONCURRENTLY, so `vision` measures the slowest call,
            # not the sum — vision_calls is what makes the cost visible.
            raw_responses = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_runs) as executor:
                futures = [executor.submit(run_grading) for _ in range(num_runs)]
                for future in concurrent.futures.as_completed(futures):
                    resp = future.result()
                    total_input_tokens += resp.usage.input_tokens
                    total_output_tokens += resp.usage.output_tokens
                    _cc, _cr = _cache_of(resp)
                    cache_create += _cc
                    cache_read += _cr
                    raw_responses.append(resp.content[0].text)
            _t.mark('vision_done')
            _t.note(vision_calls=len(raw_responses))

            result = parse_multi_run_responses(raw_responses)

        _t.mark('parse_done')
        _t.note(model=get_model('sonnet'),
                in_tok=total_input_tokens, out_tok=total_output_tokens,
                cache_create=cache_create, cache_read=cache_read)

        # Log total API usage (get_model reflects the active model, incl. fallback)
        log_api_usage(g.user_id, '/api/grade', get_model('sonnet'),
                      total_input_tokens, total_output_tokens)

        # Increment grading counter for usage cap
        try:
            inc_conn = _dbpool.get_db()
            inc_cur = inc_conn.cursor()
            inc_cur.execute(
                """UPDATE users
                   SET gradings_this_month = COALESCE(gradings_this_month, 0) + 1,
                       gradings_reset_date = COALESCE(gradings_reset_date,
                           date_trunc('month', CURRENT_TIMESTAMP + INTERVAL '1 month'))
                   WHERE id = %s""",
                (g.user_id,)
            )
            inc_conn.commit()
            inc_cur.close()
            inc_conn.close()
        except Exception as e:
            print(f"[WARN] Failed to increment grading counter: {e}")

        # Add metadata
        result['title'] = title
        result['issue'] = issue
        result['publisher'] = publisher
        result['photos_used'] = len(images)
        result['confidence'] = {1: 65, 2: 78, 3: 88, 4: 94}.get(len(images), 65)
        result['usage'] = {
            'input_tokens': total_input_tokens,
            'output_tokens': total_output_tokens
        }

        # Map defects to flat arrays for backward compatibility with frontend
        defects = result.get('defects', {})
        result['front_defects'] = defects.get('front', [])
        result['spine_defects'] = defects.get('spine', [])
        result['back_defects'] = defects.get('back', [])
        result['interior_defects'] = defects.get('interior', [])
        result['other_defects'] = defects.get('other', [])

        # Map grade fields for backward compat
        result['grade_reasoning'] = result.get('observations', '')
        result['year'] = data.get('year', '')

        # --- Task 3: enforce CGC-scale display grade + retain raw average ---
        # grading_engine already snaps final_grade; this is a defensive guard so an
        # off-scale value can never reach the client (the equivalence claim). We
        # keep the unsnapped weighted average as raw_grade for calibration (task 4
        # priors) and log it. Canonical step list lives once in grading_engine.
        from grading_engine import snap_to_cgc_grade
        raw_grade = result.get('raw_score', result.get('final_grade'))
        result['raw_grade'] = raw_grade
        if isinstance(result.get('final_grade'), (int, float)):
            snapped, snapped_label, _ = snap_to_cgc_grade(float(result['final_grade']))
            result['final_grade'] = snapped
            if not result.get('grade_label'):
                result['grade_label'] = snapped_label
        print(f"[Grading] grade served: final={result.get('final_grade')} "
              f"raw={raw_grade} runs={result.get('run_count')}")

        # Include grading usage info for frontend counter
        try:
            usage_conn = _dbpool.get_db(dict_rows=True)
            usage_cur = usage_conn.cursor()
            usage_cur.execute("SELECT gradings_this_month, is_admin FROM users WHERE id = %s", (g.user_id,))
            usage_row = usage_cur.fetchone()
            if usage_row and not usage_row.get('is_admin'):
                result['grading_usage'] = {
                    'used': usage_row.get('gradings_this_month', 0) or 0,
                    'limit': MONTHLY_GRADING_LIMIT
                }
            usage_cur.close()
            usage_conn.close()
        except Exception:
            pass

        # --- Persist this grade submission for retention/diagnosis ---
        # Per docs/technical/GRADE_RETENTION_SPEC.md. Runs on a background thread so it
        # adds NO latency to the grade response. Captures request state explicitly (the
        # thread runs outside the request context). Never blocks or fails the grade.
        try:
            from grade_retention import persist_grade_submission_async
            persist_grade_submission_async(
                user_id=g.user_id,
                images=images,
                photo_labels=photo_labels,
                result=result,
                model=get_model('sonnet'),
                database_url=database_url,
            )
        except Exception as persist_err:
            print(f"[Grading] retention persist scheduling failed (non-fatal): {persist_err}")

        _t.mark('response')
        _t.emit('ok', title, issue)
        return jsonify(result)

    except json.JSONDecodeError as e:
        _t.mark('response')
        _t.emit('parse_error', title, issue)
        return jsonify({'error': f'Failed to parse grading response: {str(e)}'}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        _t.mark('response')
        _t.emit('error:%s' % type(e).__name__, title, issue)
        return jsonify({'error': str(e)}), 500
