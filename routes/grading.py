"""
Grading Blueprint - Comic valuation and extraction endpoints
Routes: /api/valuate, /api/extract, /api/cache/check, /api/messages
"""
import os
from flask import Blueprint, jsonify, request, g

# Create blueprint
grading_bp = Blueprint('grading', __name__, url_prefix='/api')

# These will be imported from wsgi.py when needed
from auth import require_auth, require_approved
from admin import log_api_usage

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
        log_api_usage(g.user_id, '/api/valuate', 'claude-sonnet-4-20250514', 
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
        conn = psycopg2.connect(database_url)
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
    if not extract_from_base64:
        return jsonify({'success': False, 'error': 'Extraction module not available'}), 503
    
    data = request.get_json() or {}
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({'success': False, 'error': 'Image data is required'}), 400
    
    # Content moderation check BEFORE processing
    if moderate_image:
        mod_result = moderate_image(image_data)
        if mod_result.get('blocked'):
            log_moderation_incident(g.user_id, '/api/extract', mod_result, get_image_hash(image_data))
            return jsonify({
                'success': False, 
                'error': 'Image rejected: inappropriate content detected.',
                'moderation': True
            }), 400
        # Log warnings (but allow through)
        if mod_result.get('warnings'):
            log_moderation_incident(g.user_id, '/api/extract', mod_result, get_image_hash(image_data))
    
    media_type = data.get('media_type', 'image/jpeg')
    result = extract_from_base64(image_data, media_type)
    
    if result.get('success'):
        log_api_usage(g.user_id, '/api/extract', 'claude-sonnet-4-20250514',
                      result.get('input_tokens', 0), result.get('output_tokens', 0))
    
    return jsonify(result)


@grading_bp.route('/messages', methods=['POST'])
@require_auth
@require_approved
def api_messages():
    """Anthropic API proxy for AI-powered grading analysis"""
    if not ANTHROPIC_AVAILABLE or not ANTHROPIC_API_KEY:
        return jsonify({'error': 'Anthropic API not available'}), 503
    
    data = request.get_json() or {}
    
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
    
    data['temperature'] = 0  # Force deterministic responses for consistent grading
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    try:
        response = client.messages.create(**data)
        
        log_api_usage(g.user_id, '/api/messages', data.get('model', 'unknown'),
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
