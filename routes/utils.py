"""
Utils Blueprint - Health checks, debug routes, and utility endpoints
"""
from flask import Blueprint, jsonify, request
from auth import validate_beta_code

# Create blueprint
utils_bp = Blueprint('utils', __name__)

# These will be set by wsgi.py when registering the blueprint
BARCODE_AVAILABLE = False
MODERATION_AVAILABLE = False

def init_globals(barcode_available, moderation_available):
    """Called from wsgi.py to set global flags"""
    global BARCODE_AVAILABLE, MODERATION_AVAILABLE
    BARCODE_AVAILABLE = barcode_available
    MODERATION_AVAILABLE = moderation_available


@utils_bp.route('/')
@utils_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'version': '4.2.4',
        'barcode': BARCODE_AVAILABLE,
        'moderation': MODERATION_AVAILABLE
    })


@utils_bp.route('/api/debug/prompt-check')
def debug_prompt():
    """Debug endpoint to check extraction prompt"""
    from comic_extraction import EXTRACTION_PROMPT
    return jsonify({
        'prompt_length': len(EXTRACTION_PROMPT),
        'has_new_schema': 'YOU MUST RETURN EXACTLY' in EXTRACTION_PROMPT,
        'first_100_chars': EXTRACTION_PROMPT[:100]
    })


@utils_bp.route('/api/beta/validate', methods=['POST'])
def api_validate_beta():
    """Validate a beta access code"""
    data = request.get_json() or {}
    code = data.get('code', '')
    result = validate_beta_code(code)
    return jsonify(result)
