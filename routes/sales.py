"""
Sales Blueprint - Market sales data and FMV calculation endpoints
Routes: /api/sales/*, /api/ebay-sales/*
"""
import os
import hashlib
from flask import Blueprint, jsonify, request, g
import psycopg2
from psycopg2.extras import RealDictCursor

# Create blueprint
sales_bp = Blueprint('sales', __name__, url_prefix='/api')

# Module imports (will be set by wsgi.py)
upload_sale_image = None
upload_image = None
scan_barcode_from_base64 = None
R2_AVAILABLE = False


def init_modules(r2_available, upload_sale_func, upload_image_func, scan_barcode_func):
    """Initialize modules from wsgi.py"""
    global R2_AVAILABLE, upload_sale_image, upload_image, scan_barcode_from_base64
    R2_AVAILABLE = r2_available
    upload_sale_image = upload_sale_func
    upload_image = upload_image_func
    scan_barcode_from_base64 = scan_barcode_func


@sales_bp.route('/ebay-sales/batch', methods=['POST'])
def add_ebay_sales_batch():
    """Batch insert eBay sales from browser extension with R2 image backup"""
    import requests
    import base64
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    database_url = os.environ.get('DATABASE_URL')
    conn = None
    
    def backup_image_to_r2(sale):
        """Download image from eBay and upload to R2"""
        try:
            image_url = sale.get('image_url', '')
            ebay_item_id = sale.get('ebay_item_id', '')
            
            if not image_url or not ebay_item_id:
                return None
            
            # Download from eBay
            response = requests.get(image_url, timeout=10)
            if response.status_code != 200:
                return None
            
            # Convert to base64
            image_b64 = base64.b64encode(response.content).decode('utf-8')
            
            # Determine content type
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            ext = 'webp' if 'webp' in content_type else 'jpg'
            
            # Upload to R2
            path = f"ebay-covers/{ebay_item_id}.{ext}"
            result = upload_image(image_b64, path, content_type)
            
            if result.get('success'):
                return {'ebay_item_id': ebay_item_id, 'r2_url': result['url']}
            return None
        except Exception as e:
            print(f"Image backup error for {sale.get('ebay_item_id')}: {e}")
            return None
    
    try:
        data = request.get_json()
        sales = data.get('sales', [])
        
        if not sales:
            return jsonify({'error': 'No sales provided'}), 400
        
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        saved = 0
        duplicates = 0
        saved_sales = []  # Track which sales were actually saved
        
        # Step 1: Insert all sales to database
        for sale in sales:
            content = f"{sale.get('raw_title', '')}|{sale.get('sale_price', '')}|{sale.get('sale_date', '')}"
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:32]
            
            try:
                cur.execute("""
                    INSERT INTO ebay_sales (
                        raw_title, parsed_title, issue_number, publisher,
                        sale_price, sale_date, condition, graded, grade,
                        listing_url, image_url, ebay_item_id, content_hash
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ebay_item_id) DO NOTHING
                """, (
                    sale.get('raw_title'),
                    sale.get('parsed_title'),
                    sale.get('issue_number'),
                    sale.get('publisher'),
                    sale.get('sale_price'),
                    sale.get('sale_date'),
                    sale.get('condition'),
                    sale.get('graded', False),
                    sale.get('grade'),
                    sale.get('listing_url'),
                    sale.get('image_url'),
                    sale.get('ebay_item_id'),
                    content_hash
                ))
                
                if cur.rowcount > 0:
                    saved += 1
                    saved_sales.append(sale)
                else:
                    duplicates += 1
                    
                conn.commit()
                
            except Exception as e:
                duplicates += 1
                conn.rollback()
        
        # Step 2: Parallel image backup for newly saved sales (max 5 concurrent)
        images_backed_up = 0
        if saved_sales:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(backup_image_to_r2, sale): sale for sale in saved_sales}
                
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        # Update database with R2 URL
                        try:
                            cur.execute("""
                                UPDATE ebay_sales 
                                SET r2_image_url = %s 
                                WHERE ebay_item_id = %s
                            """, (result['r2_url'], result['ebay_item_id']))
                            conn.commit()
                            images_backed_up += 1
                        except Exception as e:
                            print(f"Error updating R2 URL: {e}")
                            conn.rollback()
        
        return jsonify({
            'success': True,
            'saved': saved,
            'duplicates': duplicates,
            'images_backed_up': images_backed_up,
            'total': len(sales)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@sales_bp.route('/ebay-sales/stats', methods=['GET'])
def get_ebay_sales_stats():
    """Get statistics about collected eBay sales"""
    database_url = os.environ.get('DATABASE_URL')
    conn = None
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM ebay_sales")
        total = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(*) FROM ebay_sales 
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
        """)
        last_week = cur.fetchone()[0]
        
        return jsonify({
            'total_sales': total,
            'last_7_days': last_week
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@sales_bp.route('/sales/record', methods=['POST'])
def api_record_sale():
    """
    Record a sale from Whatnot extension.
    Optionally accepts 'image' field with base64 data to upload to R2.
    Now includes barcode scanning when image provided.
    """
    data = request.get_json() or {}
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'success': False, 'error': 'Database not configured'}), 500
    
    # Check if image data is included
    image_data = data.get('image')
    image_url = data.get('image_url')  # Existing URL (legacy)
    
    # Barcode fields - can come from request or be scanned from image
    upc_main = data.get('upc_main')
    upc_addon = data.get('upc_addon')
    is_reprint = data.get('is_reprint', False)
    
    # If image provided and no barcode data, try to scan it
    if image_data and not upc_main and scan_barcode_from_base64:
        barcode_result = scan_barcode_from_base64(image_data)
        if barcode_result:
            upc_main = barcode_result.get('upc_main')
            upc_addon = barcode_result.get('upc_addon')
            is_reprint = barcode_result.get('is_reprint', False)
    
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO market_sales (source, title, series, issue, grade, grade_source, slab_type,
                variant, is_key, is_facsimile, price, sold_at, raw_title, seller, bids, viewers, 
                image_url, source_id, upc_main, upc_addon, is_reprint)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_id) DO UPDATE SET 
                price = EXCLUDED.price, 
                sold_at = EXCLUDED.sold_at,
                upc_main = COALESCE(EXCLUDED.upc_main, market_sales.upc_main),
                upc_addon = COALESCE(EXCLUDED.upc_addon, market_sales.upc_addon),
                is_reprint = COALESCE(EXCLUDED.is_reprint, market_sales.is_reprint)
            RETURNING id
        """, (data.get('source', 'whatnot'), data.get('title'), data.get('series'), data.get('issue'),
              data.get('grade'), data.get('grade_source'), data.get('slab_type'), data.get('variant'),
              data.get('is_key', False), data.get('is_facsimile', False), data.get('price'), data.get('sold_at'), 
              data.get('raw_title'), data.get('seller'), data.get('bids'), data.get('viewers'), 
              image_url, data.get('source_id'), upc_main, upc_addon, is_reprint))
        
        sale_id = cur.fetchone()['id']
        conn.commit()
        
        # If image data was provided, upload to R2 and update the record
        if image_data and R2_AVAILABLE and upload_sale_image:
            r2_result = upload_sale_image(sale_id, image_data, 'front')
            if r2_result.get('success'):
                cur.execute(
                    "UPDATE market_sales SET image_url = %s WHERE id = %s",
                    (r2_result['url'], sale_id)
                )
                conn.commit()
                image_url = r2_result['url']
        
        cur.close()
        conn.close()
        return jsonify({
            'success': True, 
            'id': sale_id, 
            'image_url': image_url,
            'upc_main': upc_main,
            'upc_addon': upc_addon,
            'is_reprint': is_reprint
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@sales_bp.route('/sales/count', methods=['GET'])
def api_sales_count():
    """Get total count of sales in database"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'count': 0})
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM market_sales")
        count = cur.fetchone()['count']
        cur.close()
        conn.close()
        return jsonify({'count': count})
    except:
        return jsonify({'count': 0})


@sales_bp.route('/sales/recent', methods=['GET'])
def api_sales_recent():
    """Get recent sales (default 20)"""
    limit = request.args.get('limit', 20, type=int)
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        return jsonify({'success': False, 'error': 'Database not configured'}), 500
    
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        cur.execute("SELECT * FROM market_sales ORDER BY created_at DESC LIMIT %s", (limit,))
        sales = cur.fetchall()
        cur.close()
        conn.close()
        
        sales_list = []
        for s in sales:
            sale = dict(s)
            for key, val in sale.items():
                if hasattr(val, 'isoformat'):
                    sale[key] = val.isoformat()
                elif hasattr(val, '__float__'):
                    sale[key] = float(val)
            sales_list.append(sale)
        
        return jsonify({'success': True, 'sales': sales_list})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@sales_bp.route('/sales/fmv', methods=['GET'])
def api_sales_fmv():
    """
    Get Fair Market Value data for a comic based on sales history.
    Groups sales by grade tier and returns averages.
    Now pulls from BOTH market_sales (Whatnot) AND ebay_sales.
    
    Query params:
        title: Comic title (required)
        issue: Issue number (optional)
        days: Number of days to look back (default 90)
    """
    title = request.args.get('title', '')
    issue = request.args.get('issue', '')
    days = request.args.get('days', 90, type=int)
    
    # Reject literal "null" or "undefined" issue values
    if issue in ['null', 'undefined', 'None', 'NaN']:
        issue = ''
    
    if not title:
        return jsonify({'success': False, 'error': 'Title is required'}), 400
    
    # Server-side garbage title filter (belt & suspenders with extension filter)
    if len(title) < 3:
        return jsonify({'success': False, 'count': 0, 'tiers': None})
    
    # Skip titles that are just numbers/symbols
    import re
    if re.match(r'^[\d\s$#%.,]+$', title):
        return jsonify({'success': False, 'count': 0, 'tiers': None})
    
    # Skip known garbage patterns
    title_lower = title.lower()
    garbage_patterns = [
        'available', 'remaining', 'left', 'in stock', 'bid now', 'starting',
        'mystery', 'random', 'surprise', 'bundle', 'lot of', 'choice', 'pick',
        'awesome comic', 'comic on screen', 'on screen', 'product', 'item', 'listing'
    ]
    if any(p in title_lower for p in garbage_patterns):
        return jsonify({'success': False, 'count': 0, 'tiers': None})
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return jsonify({'success': False, 'error': 'Database not configured'}), 500
    
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        # Query 1: market_sales (Whatnot data)
        # Filter out reprints if barcode detected them
        market_query = """
            SELECT grade, price, 'whatnot' as source
            FROM market_sales
            WHERE (
                LOWER(title) LIKE LOWER(%s) 
                OR LOWER(series) LIKE LOWER(%s)
                OR LOWER(raw_title) LIKE LOWER(%s)
            )
            AND price > 0
            AND (is_reprint IS NULL OR is_reprint = false)
            AND created_at > NOW() - INTERVAL '%s days'
        """
        market_params = [f'%{title}%', f'%{title}%', f'%{title}%', days]
        
        if issue:
            market_query += " AND (issue = %s OR issue = %s)"
            market_params.extend([str(issue), issue])
        
        cur.execute(market_query, market_params)
        market_sales = cur.fetchall()
        
        # Query 2: ebay_sales (eBay Collector data)
        # Filter out facsimiles, lots, bundles, reprints, and very low prices
        ebay_query = """
            SELECT grade, sale_price as price, 'ebay' as source
            FROM ebay_sales
            WHERE (
                LOWER(parsed_title) LIKE LOWER(%s) 
                OR LOWER(raw_title) LIKE LOWER(%s)
            )
            AND sale_price > 5
            AND (is_reprint IS NULL OR is_reprint = false)
            AND created_at > NOW() - INTERVAL '%s days'
            AND LOWER(parsed_title) NOT LIKE '%%facsimile%%'
            AND LOWER(raw_title) NOT LIKE '%%facsimile%%'
            AND LOWER(parsed_title) NOT LIKE '%%reprint%%'
            AND LOWER(raw_title) NOT LIKE '%%reprint%%'
            AND LOWER(raw_title) NOT LIKE '%%2nd print%%'
            AND LOWER(raw_title) NOT LIKE '%%3rd print%%'
            AND LOWER(raw_title) NOT LIKE '%%4th print%%'
            AND LOWER(parsed_title) NOT LIKE '%%lot %%'
            AND LOWER(raw_title) NOT LIKE '%%lot of%%'
            AND LOWER(parsed_title) NOT LIKE '%%set of%%'
            AND LOWER(raw_title) NOT LIKE '%%bundle%%'
        """
        ebay_params = [f'%{title}%', f'%{title}%', days]
        
        if issue:
            ebay_query += " AND issue_number = %s"
            ebay_params.append(str(issue))
        
        cur.execute(ebay_query, ebay_params)
        ebay_sales = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Combine both sources
        all_sales = list(market_sales) + list(ebay_sales)
        
        if not all_sales:
            # No sales data found - provide intelligent fallback estimates
            grade_param = request.args.get('grade', type=float)
            publisher = request.args.get('publisher', '').lower()
            year = request.args.get('year', type=int)
            
            # Grade-based baseline values (raw comics)
            grade_baselines = {
                10.0: 50, 9.8: 45, 9.6: 40, 9.4: 35, 9.2: 30, 9.0: 25,
                8.5: 20, 8.0: 18, 7.5: 16, 7.0: 14, 6.5: 12, 6.0: 10,
                5.5: 9, 5.0: 8, 4.5: 7, 4.0: 6, 3.5: 5, 3.0: 4, 2.0: 3, 1.0: 2
            }
            
            # Get baseline from grade
            raw_estimate = grade_baselines.get(grade_param, 8)  # Default to $8
            
            # Publisher multiplier (Big 2 worth more)
            if any(pub in publisher for pub in ['marvel', 'dc']):
                raw_estimate *= 1.3
            elif any(pub in publisher for pub in ['image', 'dark horse', 'idw']):
                raw_estimate *= 1.1
            
            # Era adjustment (older = more valuable generally)
            if year:
                if year < 1970:  # Silver Age
                    raw_estimate *= 2.0
                elif year < 1984:  # Bronze Age
                    raw_estimate *= 1.5
                elif year < 1992:  # Copper Age
                    raw_estimate *= 1.2
                # Modern age (1992+) = no multiplier
            
            # Slabbed premium (typically 40-60% for raw comics without known value)
            slabbed_estimate = raw_estimate * 1.5
            grading_cost = 30  # Standard grading fee
            
            # Round to 2 decimals
            raw_estimate = round(raw_estimate, 2)
            slabbed_estimate = round(slabbed_estimate, 2)
            
            return jsonify({
                'success': True, 
                'count': 0, 
                'tiers': None,
                'raw_fmv': raw_estimate,
                'slabbed_fmv': slabbed_estimate,
                'grading_cost': grading_cost,
                'estimated': True,
                'note': 'Estimate based on grade/publisher/era - limited sales data available'
            })
        
        # Group by grade tiers
        tiers = {
            'low': [],    # < 4.5
            'mid': [],    # 4.5 - 7.9
            'high': [],   # 8.0 - 8.9
            'top': []     # 9.0+
        }
        
        whatnot_count = 0
        ebay_count = 0
        
        for sale in all_sales:
            grade = sale.get('grade')
            price = float(sale.get('price', 0))
            source = sale.get('source', 'unknown')
            
            if price <= 0:
                continue
            
            # Count by source
            if source == 'whatnot':
                whatnot_count += 1
            elif source == 'ebay':
                ebay_count += 1
                
            if grade is None:
                tiers['mid'].append(price)
            elif grade >= 9.0:
                tiers['top'].append(price)
            elif grade >= 8.0:
                tiers['high'].append(price)
            elif grade >= 4.5:
                tiers['mid'].append(price)
            else:
                tiers['low'].append(price)
        
        # Calculate averages
        result_tiers = {}
        tier_labels = {
            'low': '<4.5',
            'mid': '4.5-7.9',
            'high': '8.0-8.9',
            'top': '9.0+'
        }
        
        for tier, prices in tiers.items():
            if prices:
                result_tiers[tier] = {
                    'avg': round(sum(prices) / len(prices), 2),
                    'min': round(min(prices), 2),
                    'max': round(max(prices), 2),
                    'count': len(prices),
                    'grades': tier_labels[tier]
                }

        # Calculate raw_fmv and slabbed_fmv from tier data based on user's grade
        grade_param = request.args.get('grade', 5.0, type=float)

        # Determine which tier the user's grade falls into
        if grade_param >= 9.0:
            user_tier = 'top'
        elif grade_param >= 8.0:
            user_tier = 'high'
        elif grade_param >= 4.5:
            user_tier = 'mid'
        else:
            user_tier = 'low'

        # Get raw FMV from the user's tier, or fall back to nearest available tier
        tier_priority = {
            'top': ['top', 'high', 'mid', 'low'],
            'high': ['high', 'mid', 'top', 'low'],
            'mid': ['mid', 'high', 'low', 'top'],
            'low': ['low', 'mid', 'high', 'top']
        }

        raw_fmv = 0
        for t in tier_priority.get(user_tier, ['mid']):
            if t in result_tiers:
                raw_fmv = result_tiers[t]['avg']
                break

        # Slabbed FMV: use the next tier up if available, otherwise apply 1.5x premium
        slabbed_fmv = raw_fmv * 1.5  # Default: 50% slab premium
        tier_order = ['low', 'mid', 'high', 'top']
        user_tier_idx = tier_order.index(user_tier) if user_tier in tier_order else 1
        for i in range(user_tier_idx + 1, len(tier_order)):
            higher_tier = tier_order[i]
            if higher_tier in result_tiers:
                slabbed_fmv = result_tiers[higher_tier]['avg']
                break

        # Ensure slabbed is always >= raw
        if slabbed_fmv < raw_fmv:
            slabbed_fmv = raw_fmv * 1.5

        grading_cost = 30
        if raw_fmv >= 1000:
            grading_cost = 150
        elif raw_fmv >= 400:
            grading_cost = 85
        elif raw_fmv >= 200:
            grading_cost = 50

        raw_fmv = round(raw_fmv, 2)
        slabbed_fmv = round(slabbed_fmv, 2)

        return jsonify({
            'success': True,
            'title': title,
            'issue': issue,
            'count': len(all_sales),
            'sources': {
                'whatnot': whatnot_count,
                'ebay': ebay_count
            },
            'tiers': result_tiers if result_tiers else None,
            'raw_fmv': raw_fmv,
            'slabbed_fmv': slabbed_fmv,
            'grading_cost': grading_cost
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
