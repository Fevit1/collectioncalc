from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# CORS headers for frontend
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-API-Key, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    return response

# Simple health check
@app.route('/')
def home():
    return jsonify({
        "status": "CollectionCalc API is running",
        "version": "3.8",
        "features": ["database_lookup", "ebay_valuation", "recency_weighting", "photo_extraction", "ebay_oauth", "ebay_listing", "ebay_description_generator", "quicklist_batch", "draft_mode", "image_upload", "issue_type_detection", "gdpr_account_deletion", "user_auth", "collections", "market_sales"]
    })

@app.route('/api/messages', methods=['POST', 'OPTIONS'])
def proxy_messages():
    """Proxy requests to Anthropic API for photo extraction and valuations."""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # Use server-side API key (users don't need their own)
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            return jsonify({'error': {'message': 'Server API key not configured'}}), 500
        
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
        issue_type = data.get('issue_type')  # "Regular", "Annual", "Giant-Size", etc.
        is_signed = data.get('is_signed', False)  # Whether comic is signed
        signer = data.get('signer', '')  # Name of signer (e.g., "Stan Lee")
        
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
            force_refresh=force_refresh,
            issue_type=issue_type,
            is_signed=is_signed,
            signer=signer
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

@app.route('/api/ebay/debug', methods=['GET'])
def ebay_debug():
    """Debug endpoint to check eBay configuration."""
    import os
    from ebay_oauth import is_sandbox_mode, EBAY_TOKEN_URL, EBAY_SANDBOX_TOKEN_URL
    
    sandbox_mode = is_sandbox_mode()
    token_url = EBAY_SANDBOX_TOKEN_URL if sandbox_mode else EBAY_TOKEN_URL
    
    return jsonify({
        'sandbox_mode': sandbox_mode,
        'EBAY_SANDBOX_env': os.environ.get('EBAY_SANDBOX', 'NOT SET'),
        'token_url_being_used': token_url,
        'client_id_set': bool(os.environ.get('EBAY_CLIENT_ID')),
        'client_id_preview': os.environ.get('EBAY_CLIENT_ID', '')[:20] + '...' if os.environ.get('EBAY_CLIENT_ID') else None,
        'client_secret_set': bool(os.environ.get('EBAY_CLIENT_SECRET')),
        'runame_set': bool(os.environ.get('EBAY_RUNAME')),
        'runame': os.environ.get('EBAY_RUNAME', 'NOT SET')
    })

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

@app.route('/api/ebay/account-deletion', methods=['GET', 'POST'])
def ebay_account_deletion():
    """
    Handle eBay Marketplace Account Deletion notifications (GDPR compliance).
    
    GET: eBay sends a challenge to verify endpoint ownership
    POST: eBay notifies us when a user deletes their account or revokes access
    
    Required env var: EBAY_VERIFICATION_TOKEN (set in eBay Developer Portal)
    """
    if request.method == 'GET':
        # eBay challenge verification
        # eBay sends: GET /api/ebay/account-deletion?challenge_code=XXXX
        challenge_code = request.args.get('challenge_code')
        
        if not challenge_code:
            return jsonify({'error': 'Missing challenge_code'}), 400
        
        # Get our verification token from environment
        verification_token = os.environ.get('EBAY_VERIFICATION_TOKEN')
        if not verification_token:
            print("WARNING: EBAY_VERIFICATION_TOKEN not set!")
            return jsonify({'error': 'Verification token not configured'}), 500
        
        # eBay expects: SHA256(challenge_code + verification_token + endpoint_url)
        import hashlib
        endpoint_url = os.environ.get('EBAY_DELETION_ENDPOINT', 
                                       'https://collectioncalc.onrender.com/api/ebay/account-deletion')
        
        hash_input = challenge_code + verification_token + endpoint_url
        response_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        print(f"eBay challenge received. Responding with hash.")
        
        # eBay expects JSON response with challengeResponse
        return jsonify({'challengeResponse': response_hash})
    
    elif request.method == 'POST':
        # Actual deletion notification
        try:
            from ebay_oauth import delete_user_by_ebay_id
            
            data = request.get_json()
            
            # eBay sends notification with user info
            # Format: {"metadata": {...}, "notification": {"data": {"userId": "..."}}}
            notification = data.get('notification', {})
            notification_data = notification.get('data', {})
            ebay_user_id = notification_data.get('userId') or notification_data.get('username')
            
            if not ebay_user_id:
                # Try alternate format
                ebay_user_id = data.get('userId') or data.get('username')
            
            if not ebay_user_id:
                print(f"Account deletion notification received but no user ID found: {data}")
                # Still return 200 to acknowledge receipt
                return jsonify({
                    'success': True, 
                    'message': 'Notification received, no user ID found to delete'
                })
            
            print(f"eBay account deletion request for user: {ebay_user_id}")
            
            # Delete user's tokens from our database
            deleted = delete_user_by_ebay_id(ebay_user_id)
            
            if deleted:
                print(f"Successfully deleted tokens for eBay user: {ebay_user_id}")
            else:
                print(f"No tokens found for eBay user: {ebay_user_id} (may already be deleted)")
            
            # Always return 200 to acknowledge receipt
            return jsonify({
                'success': True,
                'message': 'Account deletion processed',
                'user_deleted': deleted
            })
            
        except Exception as e:
            print(f"Error processing account deletion: {e}")
            # Still return 200 to prevent eBay from retrying
            return jsonify({
                'success': True,
                'message': 'Notification received',
                'error': str(e)
            })

@app.route('/api/ebay/list', methods=['POST', 'OPTIONS'])
def ebay_list():
    """Create an eBay listing for a comic."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from ebay_listing import create_listing
        
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        title = data.get('title')
        issue = data.get('issue')
        price = data.get('price')
        grade = data.get('grade', 'VF')
        description = data.get('description')  # User-approved description
        publish = data.get('publish', False)  # Default to draft mode
        image_urls = data.get('image_urls')  # List of eBay-hosted image URLs
        
        if not all([title, issue, price]):
            return jsonify({'success': False, 'error': 'Missing required fields: title, issue, price'}), 400
        
        result = create_listing(user_id, title, issue, float(price), grade, description, publish, image_urls)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ebay/upload-image', methods=['POST', 'OPTIONS'])
def ebay_upload_image():
    """Upload an image to eBay Picture Services."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from ebay_listing import upload_image_to_ebay
        from ebay_oauth import get_user_token
        import base64
        
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        image_base64 = data.get('image')  # Base64 encoded image
        filename = data.get('filename', 'comic.jpg')
        
        if not image_base64:
            return jsonify({'success': False, 'error': 'Missing required field: image (base64)'}), 400
        
        # Get user's access token
        token_data = get_user_token(user_id)
        if not token_data or not token_data.get('access_token'):
            return jsonify({'success': False, 'error': 'Not connected to eBay. Please connect your account.'}), 401
        
        # Decode base64 image
        try:
            # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
            if ',' in image_base64:
                image_base64 = image_base64.split(',')[1]
            image_data = base64.b64decode(image_base64)
        except Exception as e:
            return jsonify({'success': False, 'error': f'Invalid base64 image: {str(e)}'}), 400
        
        # Upload to eBay
        result = upload_image_to_ebay(token_data['access_token'], image_data, filename)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/extract', methods=['POST', 'OPTIONS'])
def extract_comic():
    """Extract comic info from a photo using AI vision."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from comic_extraction import extract_from_base64
        
        data = request.get_json()
        image_base64 = data.get('image')  # Base64 encoded image
        filename = data.get('filename', 'comic.jpg')
        
        if not image_base64:
            return jsonify({'success': False, 'error': 'Missing required field: image (base64)'}), 400
        
        result = extract_from_base64(image_base64, filename)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/batch/process', methods=['POST', 'OPTIONS'])
def batch_process():
    """
    Process multiple comics: Extract + Valuate + Generate Description.
    No eBay interaction - returns results for user review.
    Part of QuickList pipeline: Extract → Valuate → Describe → List
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    # Validation limits
    MAX_BATCH_SIZE = 20  # Max comics per request
    MAX_IMAGE_SIZE_MB = 10  # Max image size in MB
    MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024
    
    try:
        from comic_extraction import extract_from_base64
        from ebay_valuation import get_valuation_with_ebay
        from ebay_description import generate_description
        
        data = request.get_json()
        comics = data.get('comics', [])
        
        if not comics:
            return jsonify({'success': False, 'error': 'No comics provided'}), 400
        
        # Validate batch size
        if len(comics) > MAX_BATCH_SIZE:
            return jsonify({
                'success': False, 
                'error': f'Too many comics. Maximum {MAX_BATCH_SIZE} per request, received {len(comics)}'
            }), 400
        
        results = []
        errors = []
        
        for idx, comic in enumerate(comics):
            comic_result = {'index': idx}
            
            try:
                image_base64 = comic.get('image')
                filename = comic.get('filename', f'comic_{idx}.jpg')
                
                if not image_base64:
                    errors.append({'index': idx, 'error': 'Missing image data'})
                    continue
                
                # Validate image size (base64 is ~33% larger than binary)
                estimated_size = len(image_base64) * 3 / 4
                if estimated_size > MAX_IMAGE_SIZE_BYTES:
                    errors.append({
                        'index': idx, 
                        'error': f'Image too large. Maximum {MAX_IMAGE_SIZE_MB}MB, received ~{round(estimated_size / 1024 / 1024, 1)}MB'
                    })
                    continue
                
                if not image_base64:
                    errors.append({'index': idx, 'error': 'Missing image data'})
                    continue
                
                # Step 1: Extract comic info from photo
                extraction = extract_from_base64(image_base64, filename)
                
                if not extraction.get('success'):
                    errors.append({'index': idx, 'error': extraction.get('error', 'Extraction failed'), 'step': 'extract'})
                    continue
                
                extracted = extraction.get('extracted', {})
                comic_result['extracted'] = extracted
                comic_result['image'] = image_base64  # Keep for later listing
                comic_result['filename'] = filename
                
                # Step 2: Get valuation
                title = extracted.get('title', '')
                issue = extracted.get('issue', '')
                grade = extracted.get('suggested_grade') or extracted.get('grade', 'VF')
                publisher = extracted.get('publisher')
                year = extracted.get('year')
                issue_type = extracted.get('issue_type')  # "Regular", "Annual", "Giant-Size", etc.
                
                # Check for signatures - auto-detect signed comics
                is_signed = extracted.get('is_signed', False)
                signer = extracted.get('signer', '')
                signatures = extracted.get('signatures', [])
                if signatures and not is_signed:
                    # Check if AI detected a creator signature
                    for sig in signatures:
                        if 'creator' in sig.lower() and 'defect' not in sig.lower():
                            is_signed = True
                            # Try to extract name from parentheses
                            import re
                            name_match = re.search(r'\(([^)]+)\)', sig)
                            if name_match:
                                signer = name_match.group(1)
                            break
                
                if title and issue:
                    valuation = get_valuation_with_ebay(
                        title=title,
                        issue=issue,
                        grade=grade,
                        publisher=publisher,
                        year=year,
                        issue_type=issue_type,
                        is_signed=is_signed,
                        signer=signer
                    )
                    comic_result['valuation'] = valuation
                else:
                    comic_result['valuation'] = {'error': 'Missing title or issue for valuation'}
                
                # Step 3: Generate description
                price = 0
                if comic_result.get('valuation') and comic_result['valuation'].get('fair_value'):
                    price = comic_result['valuation']['fair_value']
                
                desc_result = generate_description(
                    title=title,
                    issue=issue,
                    grade=grade,
                    price=price,
                    publisher=publisher,
                    year=year
                )
                
                if desc_result.get('success'):
                    comic_result['description'] = desc_result.get('description', '')
                else:
                    comic_result['description'] = ''
                    comic_result['description_error'] = desc_result.get('error')
                
                results.append(comic_result)
                
            except Exception as e:
                errors.append({'index': idx, 'error': str(e)})
        
        return jsonify({
            'success': True,
            'results': results,
            'errors': errors,
            'processed': len(results),
            'failed': len(errors)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/batch/list', methods=['POST', 'OPTIONS'])
def batch_list():
    """
    Create eBay draft listings for approved comics.
    Uploads images to eBay, then creates drafts.
    Part of QuickList pipeline: Extract → Valuate → Describe → List
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    # Validation limits
    MAX_BATCH_SIZE = 20  # Max comics per request
    MAX_IMAGE_SIZE_MB = 10  # Max image size in MB
    MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024
    
    try:
        from ebay_listing import upload_image_to_ebay, create_listing
        from ebay_oauth import get_user_token
        import base64
        
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        comics = data.get('comics', [])
        publish = data.get('publish', False)  # Default to draft
        
        if not comics:
            return jsonify({'success': False, 'error': 'No comics provided'}), 400
        
        # Validate batch size
        if len(comics) > MAX_BATCH_SIZE:
            return jsonify({
                'success': False, 
                'error': f'Too many comics. Maximum {MAX_BATCH_SIZE} per request, received {len(comics)}'
            }), 400
        
        # Get user's eBay token
        token_data = get_user_token(user_id)
        if not token_data or not token_data.get('access_token'):
            return jsonify({'success': False, 'error': 'Not connected to eBay. Please connect your account.'}), 401
        
        access_token = token_data['access_token']
        
        results = []
        errors = []
        
        for idx, comic in enumerate(comics):
            comic_result = {'index': idx}
            
            try:
                # Required fields
                title = comic.get('title')
                issue = comic.get('issue')
                grade = comic.get('grade', 'VF')
                description = comic.get('description', '')
                image_base64 = comic.get('image')
                filename = comic.get('filename', f'comic_{idx}.jpg')
                
                # Price: user specifies, or picks tier, or defaults to fair_value
                price = comic.get('price')
                if not price:
                    # Check if user specified a tier
                    price_tier = comic.get('price_tier', 'fair_value')
                    valuation = comic.get('valuation', {})
                    if price_tier == 'quick_sale':
                        price = valuation.get('quick_sale_value') or valuation.get('quick_sale')
                    elif price_tier == 'high_end':
                        price = valuation.get('high_end_value') or valuation.get('high_end')
                    else:
                        price = valuation.get('fair_value') or valuation.get('estimated_value')
                
                if not all([title, issue, price]):
                    errors.append({'index': idx, 'error': 'Missing required fields: title, issue, price'})
                    continue
                
                # Step 1: Upload image to eBay (if provided)
                image_urls = None
                if image_base64:
                    # Validate image size
                    estimated_size = len(image_base64) * 3 / 4
                    if estimated_size > MAX_IMAGE_SIZE_BYTES:
                        comic_result['image_warning'] = f'Image too large ({round(estimated_size / 1024 / 1024, 1)}MB), using placeholder'
                    else:
                        try:
                            # Remove data URL prefix if present
                            if ',' in image_base64:
                                image_base64 = image_base64.split(',')[1]
                            image_data = base64.b64decode(image_base64)
                            
                            upload_result = upload_image_to_ebay(access_token, image_data, filename)
                            
                            if upload_result.get('success') and upload_result.get('image_url'):
                                image_urls = [upload_result['image_url']]
                                comic_result['image_url'] = upload_result['image_url']
                            else:
                                comic_result['image_warning'] = upload_result.get('error', 'Image upload failed, using placeholder')
                        except Exception as e:
                            comic_result['image_warning'] = f'Image upload failed: {str(e)}, using placeholder'
                
                # Step 2: Create draft listing
                listing_result = create_listing(
                    user_id=user_id,
                    title=title,
                    issue=issue,
                    price=float(price),
                    grade=grade,
                    description=description,
                    publish=publish,
                    image_urls=image_urls
                )
                
                if listing_result.get('success'):
                    comic_result['listing'] = listing_result
                    comic_result['success'] = True
                    results.append(comic_result)
                else:
                    errors.append({
                        'index': idx,
                        'error': listing_result.get('error', 'Listing creation failed'),
                        'detail': listing_result
                    })
                
            except Exception as e:
                errors.append({'index': idx, 'error': str(e)})
        
        return jsonify({
            'success': True,
            'results': results,
            'errors': errors,
            'listed': len(results),
            'failed': len(errors)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ebay/generate-description', methods=['POST', 'OPTIONS'])
def generate_ebay_description():
    """Generate an AI-powered description for an eBay listing."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from ebay_description import generate_description, validate_description
        
        data = request.get_json()
        title = data.get('title')
        issue = data.get('issue')
        grade = data.get('grade', 'VF')
        price = data.get('price', 0)
        publisher = data.get('publisher')
        year = data.get('year')
        
        if not all([title, issue]):
            return jsonify({'success': False, 'error': 'Missing required fields: title, issue'}), 400
        
        result = generate_description(title, issue, grade, float(price), publisher, year)
        
        # Also validate the generated description
        if result.get('success'):
            validation = validate_description(result['description'])
            result['validation'] = validation
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ebay/validate-description', methods=['POST', 'OPTIONS'])
def validate_ebay_description():
    """Validate a user-edited description before submission."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from ebay_description import validate_description
        
        data = request.get_json()
        description = data.get('description', '')
        
        result = validate_description(description)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'valid': False, 'issues': [str(e)]}), 500

# ============================================
# AUTH ROUTES
# ============================================

@app.route('/api/auth/signup', methods=['POST', 'OPTIONS'])
def auth_signup():
    """Create a new user account."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from auth import signup
        
        data = request.get_json()
        email = data.get('email', '')
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password are required'}), 400
        
        result = signup(email, password)
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def auth_login():
    """Authenticate user and return JWT token."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from auth import login
        
        data = request.get_json()
        email = data.get('email', '')
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password are required'}), 400
        
        result = login(email, password)
        status_code = 200 if result.get('success') else 401
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/verify/<token>', methods=['GET'])
def auth_verify_email(token):
    """Verify user's email address."""
    try:
        from auth import verify_email
        
        result = verify_email(token)
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/resend-verification', methods=['POST', 'OPTIONS'])
def auth_resend_verification():
    """Resend email verification link."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from auth import resend_verification
        
        data = request.get_json()
        email = data.get('email', '')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email is required'}), 400
        
        result = resend_verification(email)
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/forgot-password', methods=['POST', 'OPTIONS'])
def auth_forgot_password():
    """Send password reset email."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from auth import forgot_password
        
        data = request.get_json()
        email = data.get('email', '')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email is required'}), 400
        
        result = forgot_password(email)
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/reset-password', methods=['POST', 'OPTIONS'])
def auth_reset_password():
    """Reset password using token from email."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from auth import reset_password
        
        data = request.get_json()
        token = data.get('token', '')
        new_password = data.get('password', '')
        
        if not token or not new_password:
            return jsonify({'success': False, 'error': 'Token and new password are required'}), 400
        
        result = reset_password(token, new_password)
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/me', methods=['GET', 'OPTIONS'])
def auth_me():
    """Get current user from JWT token."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from auth import get_current_user
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing or invalid Authorization header'}), 401
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        result = get_current_user(token)
        status_code = 200 if result.get('success') else 401
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# COLLECTION ROUTES
# ============================================

@app.route('/api/collection', methods=['GET', 'OPTIONS'])
def get_collection():
    """Get user's saved comics collection."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from auth import verify_jwt
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Authenticate
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        token = auth_header[7:]
        payload = verify_jwt(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401
        
        user_id = payload['user_id']
        
        # Get collection from database
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'), cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT id, comic_data, created_at, updated_at
                FROM collections
                WHERE user_id = %s
                ORDER BY updated_at DESC
            """, (user_id,))
            
            items = cur.fetchall()
            
            # Format response
            collection = []
            for item in items:
                comic = item['comic_data']
                comic['collection_id'] = item['id']
                comic['saved_at'] = item['created_at'].isoformat() if item['created_at'] else None
                comic['updated_at'] = item['updated_at'].isoformat() if item['updated_at'] else None
                collection.append(comic)
            
            return jsonify({
                'success': True,
                'collection': collection,
                'count': len(collection)
            })
        finally:
            cur.close()
            conn.close()
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/collection/save', methods=['POST', 'OPTIONS'])
def save_to_collection():
    """Save comics to user's collection."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from auth import verify_jwt
        import psycopg2
        from psycopg2.extras import RealDictCursor, Json
        
        # Authenticate
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        token = auth_header[7:]
        payload = verify_jwt(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401
        
        user_id = payload['user_id']
        
        data = request.get_json()
        comics = data.get('comics', [])
        
        if not comics:
            return jsonify({'success': False, 'error': 'No comics provided'}), 400
        
        if len(comics) > 100:
            return jsonify({'success': False, 'error': 'Maximum 100 comics per save'}), 400
        
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'), cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        try:
            saved = []
            for comic in comics:
                # Insert into collection
                cur.execute("""
                    INSERT INTO collections (user_id, comic_data)
                    VALUES (%s, %s)
                    RETURNING id
                """, (user_id, Json(comic)))
                
                result = cur.fetchone()
                comic['collection_id'] = result['id']
                saved.append(comic)
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'saved': saved,
                'count': len(saved)
            })
        except Exception as e:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/collection/<int:item_id>', methods=['DELETE', 'OPTIONS'])
def delete_from_collection(item_id):
    """Remove a comic from user's collection."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from auth import verify_jwt
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Authenticate
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        token = auth_header[7:]
        payload = verify_jwt(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401
        
        user_id = payload['user_id']
        
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'), cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        try:
            # Delete only if belongs to this user
            cur.execute("""
                DELETE FROM collections
                WHERE id = %s AND user_id = %s
                RETURNING id
            """, (item_id, user_id))
            
            deleted = cur.fetchone()
            conn.commit()
            
            if deleted:
                return jsonify({'success': True, 'deleted_id': item_id})
            else:
                return jsonify({'success': False, 'error': 'Item not found'}), 404
        finally:
            cur.close()
            conn.close()
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/collection/<int:item_id>', methods=['PUT', 'OPTIONS'])
def update_collection_item(item_id):
    """Update a comic in user's collection."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        from auth import verify_jwt
        import psycopg2
        from psycopg2.extras import RealDictCursor, Json
        
        # Authenticate
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        token = auth_header[7:]
        payload = verify_jwt(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401
        
        user_id = payload['user_id']
        
        data = request.get_json()
        comic_data = data.get('comic_data')
        
        if not comic_data:
            return jsonify({'success': False, 'error': 'No comic data provided'}), 400
        
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'), cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        try:
            # Update only if belongs to this user
            cur.execute("""
                UPDATE collections
                SET comic_data = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s
                RETURNING id
            """, (Json(comic_data), item_id, user_id))
            
            updated = cur.fetchone()
            conn.commit()
            
            if updated:
                return jsonify({'success': True, 'updated_id': item_id})
            else:
                return jsonify({'success': False, 'error': 'Item not found'}), 404
        finally:
            cur.close()
            conn.close()
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# MARKET SALES API (Whatnot Extension Integration)
# ============================================

@app.route('/api/sales/record', methods=['POST', 'OPTIONS'])
def record_sale():
    """Record a sale from Whatnot extension (or other sources)."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        import psycopg2
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Required field
        if 'price' not in data:
            return jsonify({'error': 'Price is required'}), 400
        
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        
        # Generate source_id if not provided
        source_id = data.get('source_id')
        if not source_id:
            import uuid
            source_id = str(uuid.uuid4())
        
        # Insert sale record
        cursor.execute("""
            INSERT INTO market_sales (
                source, title, series, issue, grade, grade_source, 
                slab_type, variant, is_key, price, sold_at, raw_title, 
                seller, bids, viewers, image_url, source_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (source, source_id) DO NOTHING
            RETURNING id
        """, (
            data.get('source', 'whatnot'),
            data.get('title'),
            data.get('series'),
            str(data.get('issue')) if data.get('issue') else None,
            data.get('grade'),
            data.get('grade_source'),
            data.get('slab_type'),
            data.get('variant'),
            data.get('is_key', False),
            data.get('price'),
            data.get('sold_at'),
            data.get('raw_title'),
            data.get('seller'),
            data.get('bids'),
            data.get('viewers'),
            data.get('image_url'),
            source_id
        ))
        
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if result:
            return jsonify({'success': True, 'id': result[0]}), 201
        else:
            return jsonify({'success': True, 'message': 'Duplicate skipped'}), 200
            
    except Exception as e:
        print(f"Error recording sale: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sales/count', methods=['GET', 'OPTIONS'])
def get_sales_count():
    """Get total sales count (for extension display)."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        import psycopg2
        
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        
        source = request.args.get('source')
        if source:
            cursor.execute("SELECT COUNT(*) FROM market_sales WHERE source = %s", (source,))
        else:
            cursor.execute("SELECT COUNT(*) FROM market_sales")
        
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return jsonify({'count': count}), 200
        
    except Exception as e:
        print(f"Error getting sales count: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sales/recent', methods=['GET', 'OPTIONS'])
def get_recent_sales():
    """Get recent sales for display."""
    if request.method == 'OPTIONS':
        return '', 204
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'), cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        limit = min(int(request.args.get('limit', 20)), 100)
        source = request.args.get('source')
        
        if source:
            cursor.execute("""
                SELECT * FROM market_sales 
                WHERE source = %s 
                ORDER BY sold_at DESC 
                LIMIT %s
            """, (source, limit))
        else:
            cursor.execute("""
                SELECT * FROM market_sales 
                ORDER BY sold_at DESC 
                LIMIT %s
            """, (limit,))
        
        sales = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert to JSON-serializable format
        result = []
        for sale in sales:
            sale_dict = dict(sale)
            # Convert datetime objects to ISO strings
            if sale_dict.get('sold_at'):
                sale_dict['sold_at'] = sale_dict['sold_at'].isoformat()
            if sale_dict.get('created_at'):
                sale_dict['created_at'] = sale_dict['created_at'].isoformat()
            result.append(sale_dict)
        
        return jsonify({'sales': result, 'count': len(result)}), 200
        
    except Exception as e:
        print(f"Error getting recent sales: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
