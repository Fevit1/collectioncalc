"""
Utils Blueprint - Health checks, debug routes, and utility endpoints
"""
from flask import Blueprint, jsonify, request, send_from_directory
from auth import validate_beta_code
import os

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
    """Health check endpoint — minimal public response.

    check_all() must still RUN here: the dependency monitor has no cron — its
    scheduling piggybacks on health-check polling, and the state-change alert
    email fires from inside check_all(). Only the OUTPUT stays private:
    installed versions, dependency gaps, and monitoring notes are recon
    material, so the detail (plus runtime flags like barcode/moderation) lives
    behind /api/admin/dependency-status. Render's probe needs only the 200;
    `version` is kept for deploy verification."""
    try:
        from dependency_monitor import check_all
        check_all()  # side effects only — never expose results, never fail the probe
    except Exception as e:
        print(f"[Health] dependency check error: {e}")
    return jsonify({'status': 'ok', 'version': '5.6.0'})


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


@utils_bp.route('/verify')
def serve_verify():
    """Serve the public verify page"""
    # Get the directory where this file is located, then go up one level to project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return send_from_directory(base_dir, 'verify.html')
