"""
Vision Blueprint - Proxied Anthropic Vision API for Chrome extensions
Routes: /api/vision/analyze

Moves the Claude Vision API call from the browser extension to the backend,
enabling:
- Server-side API key management (no key in extension)
- Feature gating by plan (guard+ only via chrome_extension feature)
- Per-user rate limiting
- Token usage logging for cost tracking
- Content moderation before expensive API calls

Session 61: Created to replace direct Anthropic API calls from whatnot-valuator extension
"""
import os
import json
import time
from functools import wraps
from flask import Blueprint, jsonify, request, g
from auth import require_auth, require_approved
from admin import log_api_usage

# Create blueprint
vision_bp = Blueprint('vision', __name__, url_prefix='/api/vision')

# Module-level variables (initialized by wsgi.py)
anthropic = None
ANTHROPIC_API_KEY = None
ANTHROPIC_AVAILABLE = False
moderate_image = None
log_moderation_incident = None
get_image_hash = None
check_feature_access = None


def init_modules(anthropic_lib, anthropic_key, anthropic_avail,
                 moderation_func, log_mod_func, hash_func, feature_access_func):
    """Initialize modules from wsgi.py"""
    global anthropic, ANTHROPIC_API_KEY, ANTHROPIC_AVAILABLE
    global moderate_image, log_moderation_incident, get_image_hash
    global check_feature_access

    anthropic = anthropic_lib
    ANTHROPIC_API_KEY = anthropic_key
    ANTHROPIC_AVAILABLE = anthropic_avail
    moderate_image = moderation_func
    log_moderation_incident = log_mod_func
    get_image_hash = hash_func
    check_feature_access = feature_access_func


# ============================================
# PER-USER RATE LIMITING
# ============================================

_vision_rate_store = {}  # user_id -> (count, window_start)
VISION_RATE_LIMIT_MAX = 30     # scans per window
VISION_RATE_LIMIT_WINDOW = 60  # seconds


def rate_limit_per_user(f):
    """Rate limiter for Vision API - 30 calls/minute per user"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = g.user_id
        now = time.time()

        if user_id in _vision_rate_store:
            count, window_start = _vision_rate_store[user_id]
            if now - window_start > VISION_RATE_LIMIT_WINDOW:
                _vision_rate_store[user_id] = (1, now)
            elif count >= VISION_RATE_LIMIT_MAX:
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded. Max 30 scans/minute.'
                }), 429
            else:
                _vision_rate_store[user_id] = (count + 1, window_start)
        else:
            _vision_rate_store[user_id] = (1, now)

        return f(*args, **kwargs)
    return decorated


# ============================================
# VISION ANALYSIS PROMPT
# ============================================

VISION_PROMPT = """You are analyzing a comic book shown in a live auction video. Extract the following information if visible:

1. **Title/Series**: The comic book series name (e.g., "Amazing Spider-Man", "X-Men")
2. **Issue Number**: The issue number
3. **Slab Type**: If it's a CGC/CBCS/PGX slab, identify which. Otherwise "raw"
4. **Grade**:
   - For SLABS: Read the exact numeric grade from the label (e.g., 9.8, 9.6). High confidence.
   - For RAW comics: Estimate condition based on visible cover only - look for wear, creases, spine stress, corner dings, color fading. Use standard grades (9.8, 9.6, 9.4, 9.2, 9.0, 8.5, 8.0, 7.5, 7.0, 6.5, 6.0, 5.0, 4.0, 3.0). Be conservative since you can only see the front cover!
5. **Grade Confidence**:
   - SLAB: 0.9+ (reading label directly)
   - RAW: 0.3-0.5 (cover-only estimate)
6. **Variant**: Identify if this is a variant edition:
   - Price variants: "35¢", "30¢" on cover
   - Newsstand vs Direct edition
   - Virgin cover, Sketch cover
   - Ratio variants (1:25, 1:50, etc.)
7. **Key Info**: Any notable info (1st appearance, signature, etc.)
8. **Facsimile Check**: CRITICAL - Look for ANY of these facsimile indicators:
   - "FACSIMILE EDITION" text anywhere on cover (often at top or bottom)
   - Small "Facsimile" or "Facsimile Edition" in corner boxes
   - Modern reprint indicators (often have "MARVEL" or "DC" trade dress style from 2019+)
   - UPC barcode style may differ from original (modern barcodes on classic covers)
   - Price ($3.99, $4.99, $5.99) that doesn't match the vintage cover price shown
   - Perfect print quality on what should be a worn vintage comic
   If you see ANY facsimile indicators, set isFacsimile: true

Respond ONLY with valid JSON in this exact format:
{
  "title": "Series Name",
  "issue": 123,
  "grade": 8.0,
  "gradeConfidence": 0.4,
  "gradeNote": "Cover-only estimate" or "Read from CGC label",
  "slabType": "CGC" or "CBCS" or "PGX" or "raw",
  "variant": "newsstand" or null,
  "isFacsimile": false,
  "facsimileNote": null or "Facsimile Edition text visible at top",
  "keyInfo": "1st appearance of Venom",
  "confidence": 0.9
}

CRITICAL for RAW grades: Always include gradeNote "Cover-only estimate" and keep gradeConfidence between 0.3-0.5. The seller can see back, spine, pages - they know better!

CRITICAL for FACSIMILES: Facsimile editions are modern reprints worth $5-15, NOT the valuable original. Look carefully for "FACSIMILE EDITION" text - it's often subtle but always present on reprints. Common facsimiles: Amazing Fantasy 15, Giant-Size X-Men 1, Incredible Hulk 181, Batman Adventures 12. When in doubt about a "pristine" copy of a classic key issue, suspect it may be a facsimile.

If you cannot see a comic book clearly, respond with: {"error": "Cannot identify comic", "confidence": 0}"""


# ============================================
# ENDPOINTS
# ============================================

@vision_bp.route('/analyze', methods=['POST'])
@require_auth
@require_approved
@rate_limit_per_user
def analyze_vision():
    """
    Analyze a comic book image using Claude Vision API.

    Requires: guard+ plan (chrome_extension feature)

    Request body:
        image: base64 encoded JPEG image data
        media_type: image MIME type (default: image/jpeg)
        context: optional dict with source info

    Returns:
        JSON with comic identification results
    """
    # Check Anthropic availability
    if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
        return jsonify({
            'success': False,
            'error': 'Vision API not available'
        }), 503

    # Check feature access (guard+ plan required)
    if check_feature_access:
        allowed, message = check_feature_access(g.user_id, 'chrome_extension')
        if not allowed:
            return jsonify({
                'success': False,
                'error': f'Vision scanning requires Guard or Dealer plan. {message}'
            }), 403

    # Parse request
    data = request.get_json() or {}
    image_data = data.get('image')
    media_type = data.get('media_type', 'image/jpeg')

    if not image_data:
        return jsonify({
            'success': False,
            'error': 'Image data is required'
        }), 400

    # Content moderation check BEFORE expensive Vision API call
    if moderate_image:
        try:
            mod_result = moderate_image(image_data)
            if mod_result.get('blocked'):
                if log_moderation_incident and get_image_hash:
                    log_moderation_incident(
                        g.user_id, '/api/vision/analyze',
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
                        g.user_id, '/api/vision/analyze',
                        mod_result, get_image_hash(image_data)
                    )
        except Exception as e:
            # Don't block on moderation errors - log and continue
            print(f"[Vision] Moderation error (continuing): {e}")

    # Call Anthropic Vision API
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        response = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=600,
            temperature=0,  # Deterministic for consistent grading
            messages=[{
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': media_type,
                            'data': image_data
                        }
                    },
                    {
                        'type': 'text',
                        'text': VISION_PROMPT
                    }
                ]
            }]
        )

        # Log token usage
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        log_api_usage(g.user_id, '/api/vision/analyze', 'claude-sonnet-4-20250514',
                      input_tokens, output_tokens)

        # Parse response
        text = response.content[0].text if response.content else ''

        try:
            # Find JSON in response (in case there's extra text)
            json_match = None
            # Look for JSON object in the text
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_match = text[start:end + 1]

            if json_match:
                result = json.loads(json_match)
                result['success'] = True
                result['usage'] = {
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens
                }
                return jsonify(result)
            else:
                return jsonify({
                    'success': False,
                    'error': 'Could not parse Vision response',
                    'raw': text[:200]
                }), 500

        except json.JSONDecodeError as e:
            return jsonify({
                'success': False,
                'error': f'Invalid JSON in Vision response: {str(e)}',
                'raw': text[:200]
            }), 500

    except Exception as e:
        print(f"[Vision] API error: {e}")
        error_msg = str(e)

        # Provide user-friendly error messages
        if 'authentication' in error_msg.lower() or '401' in error_msg:
            return jsonify({
                'success': False,
                'error': 'Vision API authentication failed. Contact support.'
            }), 503

        return jsonify({
            'success': False,
            'error': f'Vision analysis failed: {error_msg}'
        }), 500
