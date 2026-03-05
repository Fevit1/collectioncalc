"""
Whatnot Blueprint - Content generation for Whatnot live auction prep
Routes: /api/whatnot/*

No OAuth or direct API integration (Whatnot has no public API).
This generates optimized content for sellers to copy into Whatnot's dashboard.
"""
from flask import Blueprint, jsonify, request, g
from auth import require_auth, require_approved

# Create blueprint
whatnot_bp = Blueprint('whatnot', __name__, url_prefix='/api/whatnot')

# Module reference (set by init_modules)
generate_whatnot_content = None


def init_modules(gen_content_func):
    """Initialize modules from wsgi.py"""
    global generate_whatnot_content
    generate_whatnot_content = gen_content_func


@whatnot_bp.route('/generate-content', methods=['POST'])
@require_auth
@require_approved
def api_whatnot_generate_content():
    """Generate Whatnot-optimized listing content and show prep notes."""
    if not generate_whatnot_content:
        print("[Whatnot] generate_whatnot_content module not available!")
        return jsonify({'success': False, 'error': 'Whatnot module not available'}), 503

    data = request.get_json() or {}

    title = data.get('title', '')
    issue = data.get('issue', '')
    grade = data.get('grade', '')
    price = data.get('price', 0)
    publisher = data.get('publisher')
    year = data.get('year')

    if not title:
        return jsonify({'success': False, 'error': 'Comic title is required'}), 400

    print(f"[Whatnot] Generating content for: {title} #{issue} grade={grade} price={price}")

    result = generate_whatnot_content(
        title=title,
        issue=issue,
        grade=grade,
        price=price,
        publisher=publisher,
        year=year
    )

    print(f"[Whatnot] Result: success={result.get('success')}, source={result.get('source')}, ai_error={result.get('ai_error', 'none')}")
    return jsonify(result)
