from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# CORS headers for frontend
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-API-Key')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

# Simple health check
@app.route('/')
def home():
    return jsonify({
        "status": "CollectionCalc API is running",
        "version": "3.1",
        "features": ["database_lookup", "ebay_valuation", "recency_weighting", "photo_extraction", "ebay_oauth"]
    })

@app.route('/api/messages', methods=['POST', 'OPTIONS'])
def proxy_messages():
    """Proxy requests to Anthropic API for photo extraction and valuations."""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': {'message': 'Missing X-API-Key header'}}), 401
        
        # Get request body
        data = request.get_json()
        
        # Forward to Anthropic API
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01'
            },
            json=data,
            timeout=120  # 2 minute timeout for vision requests
        )
        
        # Return Anthropic's response
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.Timeout:
        return jsonify({'error': {'message': 'Request timed out'}}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({'error': {'message': f'Request failed: {str(e)}'}}), 502
    except Exception as e:
        return jsonify({'error': {'message': str(e)}}), 500

@app.route('/api/valuate', methods=['POST', 'OPTIONS'])
def valuate():
    """Enhanced valuation with eBay data."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from comic_lookup import lookup_comic
        from ebay_valuation import get_valuation_with_ebay
        
        data = request.get_json()
        force_refresh = data.get('force_refresh', False)
        
        # Try database lookup first
        db_result = lookup_comic(
            title=data.get('title', ''),
            issue=data.get('issue', ''),
            publisher=data.get('publisher')
        )
        
        # Get valuation with eBay data
        result = get_valuation_with_ebay(
            title=data.get('title', ''),
            issue=data.get('issue', ''),
            grade=data.get('grade', 'NM'),
            publisher=data.get('publisher'),
            year=data.get('year'),
            db_result=db_result,
            force_refresh=force_refresh
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/valuate/simple', methods=['POST', 'OPTIONS'])
def valuate_simple():
    """Original simple valuation (database only, no eBay)."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from valuation_model import ValuationModel
        from comic_lookup import lookup_comic
        
        data = request.get_json()
        model = ValuationModel()
        
        # Try database lookup first
        db_result = lookup_comic(
            title=data.get('title', ''),
            issue=data.get('issue', ''),
            publisher=data.get('publisher')
        )
        
        base_value = db_result.get('base_value', 50.0) if db_result.get('found') else 50.0
        
        result = model.calculate_value(
            base_nm_value=base_value,
            grade=data.get('grade', 'NM'),
            edition=data.get('edition', 'direct'),
            year=data.get('year'),
            publisher=data.get('publisher', 'Unknown')
        )
        
        return jsonify({
            'final_value': result.final_value,
            'confidence': result.confidence_score,
            'db_found': db_result.get('found', False),
            'steps': result.calculation_steps
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/lookup', methods=['GET'])
def lookup():
    try:
        from comic_lookup import lookup_comic
        
        title = request.args.get('title', '')
        issue = request.args.get('issue', '')
        publisher = request.args.get('publisher')
        
        result = lookup_comic(title=title, issue=issue, publisher=publisher)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache/update', methods=['POST', 'OPTIONS'])
def update_cache():
    """Update the price cache with a new value (admin function for refresh)."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from ebay_valuation import update_cached_value
        
        data = request.get_json()
        title = data.get('title', '')
        issue = data.get('issue', '')
        new_value = data.get('value')
        samples = data.get('samples', [])
        
        if not title or not issue or new_value is None:
            return jsonify({'error': 'Missing required fields: title, issue, value'}), 400
        
        success = update_cached_value(title, issue, new_value, samples)
        
        return jsonify({
            'success': success,
            'title': title,
            'issue': issue,
            'new_value': new_value
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache/check', methods=['GET'])
def check_cache():
    """Debug endpoint to check if a comic is in the cache."""
    debug_info = {}
    
    try:
        import os
        debug_info['DATABASE_URL_set'] = 'DATABASE_URL' in os.environ
        debug_info['DATABASE_URL_preview'] = os.environ.get('DATABASE_URL', '')[:50] + '...' if os.environ.get('DATABASE_URL') else None
        
        try:
            import psycopg2
            debug_info['psycopg2_installed'] = True
        except ImportError as e:
            debug_info['psycopg2_installed'] = False
            debug_info['psycopg2_error'] = str(e)
            
        from ebay_valuation import get_cached_result, expand_title_alias, get_db_connection, HAS_POSTGRES, POSTGRES_IMPORT_ERROR
        debug_info['ebay_valuation_has_postgres'] = HAS_POSTGRES
        debug_info['ebay_valuation_import_error'] = POSTGRES_IMPORT_ERROR
        
        title = request.args.get('title', '')
        issue = request.args.get('issue', '')
        
        # Expand alias
        expanded_title = expand_title_alias(title)
        search_key = f"{expanded_title.lower().strip()}|{issue.strip()}"
        
        # Check if database connection works
        conn = get_db_connection()
        db_connected = conn is not None
        debug_info['connection_result'] = 'success' if conn else 'failed'
        
        # Try to get cached result
        cached = get_cached_result(expanded_title, issue)
        
        # Get all cache entries count
        cache_count = 0
        all_keys = []
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM search_cache')
                cache_count = cursor.fetchone()[0]
                cursor.execute('SELECT search_key, estimated_value, cached_at FROM search_cache ORDER BY cached_at DESC LIMIT 10')
                all_keys = [{'key': row[0], 'value': row[1], 'cached_at': str(row[2])} for row in cursor.fetchall()]
                cursor.close()
                conn.close()
            except Exception as e:
                all_keys = [{'error': str(e)}]
                debug_info['query_error'] = str(e)
        
        return jsonify({
            'input_title': title,
            'expanded_title': expanded_title,
            'issue': issue,
            'search_key': search_key,
            'database_connected': db_connected,
            'total_cached_entries': cache_count,
            'recent_entries': all_keys,
            'found_in_cache': cached is not None,
            'cached_value': cached.estimated_value if cached else None,
            'cached_confidence': cached.confidence if cached else None,
            'debug': debug_info
        })
    except Exception as e:
        debug_info['exception'] = str(e)
        return jsonify({'error': str(e), 'debug': debug_info}), 500

# ============================================
# eBay OAuth Integration Routes
# ============================================

@app.route('/api/ebay/auth', methods=['GET'])
def ebay_auth():
    """Start eBay OAuth flow - redirects user to eBay login."""
    try:
        from ebay_oauth import get_auth_url
        
        # Get user_id from query param (frontend generates and stores this)
        user_id = request.args.get('user_id', 'default')
        
        # Generate auth URL with state parameter for security
        auth_url = get_auth_url(state=user_id)
        
        return jsonify({
            'auth_url': auth_url,
            'message': 'Redirect user to auth_url to connect their eBay account'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ebay/callback', methods=['GET'])
def ebay_callback():
    """Handle eBay OAuth callback after user authorizes."""
    try:
        from ebay_oauth import exchange_code_for_token, save_user_token
        
        # Get authorization code from eBay
        auth_code = request.args.get('code')
        state = request.args.get('state', 'default')  # This is the user_id we passed
        
        if not auth_code:
            # User declined or error occurred
            error = request.args.get('error_description', 'Authorization failed')
            return f"""
            <html>
            <head><title>eBay Connection Failed</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>❌ Connection Failed</h1>
                <p>{error}</p>
                <p><a href="https://collectioncalc.com">Return to CollectionCalc</a></p>
                <script>
                    // Notify opener window if this was a popup
                    if (window.opener) {{
                        window.opener.postMessage({{ type: 'ebay_auth', success: false, error: '{error}' }}, '*');
                        window.close();
                    }}
                </script>
            </body>
            </html>
            """
        
        # Exchange code for tokens
        token_data = exchange_code_for_token(auth_code)
        
        # Save tokens for this user
        save_user_token(state, token_data)
        
        return f"""
        <html>
        <head><title>eBay Connected!</title></head>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>✅ eBay Connected!</h1>
            <p>Your eBay account is now linked to CollectionCalc.</p>
            <p>You can now list items directly from your valuations.</p>
            <p><a href="https://collectioncalc.com">Return to CollectionCalc</a></p>
            <script>
                // Notify opener window if this was a popup
                if (window.opener) {{
                    window.opener.postMessage({{ type: 'ebay_auth', success: true, user_id: '{state}' }}, '*');
                    window.close();
                }}
            </script>
        </body>
        </html>
        """
    except Exception as e:
        return f"""
        <html>
        <head><title>eBay Connection Error</title></head>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1>❌ Connection Error</h1>
            <p>{str(e)}</p>
            <p><a href="https://collectioncalc.com">Return to CollectionCalc</a></p>
        </body>
        </html>
        """, 500

@app.route('/api/ebay/status', methods=['GET'])
def ebay_status():
    """Check if user has connected their eBay account."""
    try:
        from ebay_oauth import is_user_connected
        
        user_id = request.args.get('user_id', 'default')
        connected = is_user_connected(user_id)
        
        return jsonify({
            'connected': connected,
            'user_id': user_id
        })
    except Exception as e:
        return jsonify({'error': str(e), 'connected': False}), 500

@app.route('/api/ebay/disconnect', methods=['POST', 'OPTIONS'])
def ebay_disconnect():
    """Disconnect user's eBay account."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from ebay_oauth import disconnect_user
        
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        
        success = disconnect_user(user_id)
        
        return jsonify({
            'success': success,
            'message': 'eBay account disconnected' if success else 'Failed to disconnect'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
