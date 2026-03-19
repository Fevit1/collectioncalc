"""
Marketplace Blueprint - Content generation for multi-platform selling prep
Routes: /api/marketplace/*

No OAuth or direct API integration for these platforms.
Generates optimized content for sellers to copy into each platform's dashboard.
"""
from flask import Blueprint, jsonify, request, g
from auth import require_auth, require_approved

# Create blueprint
marketplace_bp = Blueprint('marketplace', __name__, url_prefix='/api/marketplace')

# Module references (set by init_modules)
generate_platform_content = None
get_all_platforms = None


def init_modules(gen_content_func, get_platforms_func):
    """Initialize modules from wsgi.py"""
    global generate_platform_content, get_all_platforms
    generate_platform_content = gen_content_func
    get_all_platforms = get_platforms_func


@marketplace_bp.route('/platforms', methods=['GET'])
@require_auth
def api_marketplace_platforms():
    """Return list of available marketplace platforms and their configs."""
    if not get_all_platforms:
        return jsonify({'success': False, 'error': 'Marketplace module not available'}), 503
    return jsonify({'success': True, 'platforms': get_all_platforms()})


@marketplace_bp.route('/generate-content', methods=['POST'])
@require_auth
@require_approved
def api_marketplace_generate_content():
    """Generate platform-optimized listing content."""
    if not generate_platform_content:
        return jsonify({'success': False, 'error': 'Marketplace module not available'}), 503

    data = request.get_json() or {}

    platform = data.get('platform', '')
    title = data.get('title', '')
    issue = data.get('issue', '')
    grade = data.get('grade', '')
    price = data.get('price', 0)
    publisher = data.get('publisher')
    year = data.get('year')

    if not platform:
        return jsonify({'success': False, 'error': 'Platform is required'}), 400
    if not title:
        return jsonify({'success': False, 'error': 'Comic title is required'}), 400

    result = generate_platform_content(
        platform_key=platform,
        title=title,
        issue=issue,
        grade=grade,
        price=price,
        publisher=publisher,
        year=year
    )

    return jsonify(result)
