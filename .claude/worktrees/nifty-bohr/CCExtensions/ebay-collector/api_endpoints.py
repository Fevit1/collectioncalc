"""
eBay Sales API Endpoints
Add these to your wsgi.py file

Required import at top of wsgi.py:
    import hashlib
"""

# Add this route to wsgi.py

@app.route('/api/ebay-sales/batch', methods=['POST'])
def add_ebay_sales_batch():
    """
    Batch insert eBay sales from browser extension.
    Deduplicates using ebay_item_id and content_hash.
    """
    try:
        data = request.get_json()
        sales = data.get('sales', [])
        
        if not sales:
            return jsonify({'error': 'No sales provided'}), 400
        
        saved = 0
        duplicates = 0
        
        for sale in sales:
            # Create content hash for deduplication
            content = f"{sale.get('raw_title', '')}|{sale.get('sale_price', '')}|{sale.get('sale_date', '')}"
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:32]
            
            try:
                cursor = get_db().cursor()
                cursor.execute("""
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
                
                if cursor.rowcount > 0:
                    saved += 1
                else:
                    duplicates += 1
                    
                get_db().commit()
                
            except Exception as e:
                duplicates += 1
                get_db().rollback()
        
        return jsonify({
            'success': True,
            'saved': saved,
            'duplicates': duplicates,
            'total': len(sales)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ebay-sales/stats', methods=['GET'])
def get_ebay_sales_stats():
    """Get statistics about collected eBay sales."""
    try:
        cursor = get_db().cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM ebay_sales")
        total = cursor.fetchone()[0]
        
        # Last 7 days
        cursor.execute("""
            SELECT COUNT(*) FROM ebay_sales 
            WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
        """)
        last_week = cursor.fetchone()[0]
        
        # Top publishers
        cursor.execute("""
            SELECT publisher, COUNT(*) as cnt 
            FROM ebay_sales 
            WHERE publisher IS NOT NULL
            GROUP BY publisher 
            ORDER BY cnt DESC 
            LIMIT 5
        """)
        top_publishers = [{'publisher': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Average price by graded status
        cursor.execute("""
            SELECT graded, AVG(sale_price) as avg_price, COUNT(*) as cnt
            FROM ebay_sales
            GROUP BY graded
        """)
        by_graded = [{'graded': row[0], 'avg_price': float(row[1]) if row[1] else 0, 'count': row[2]} 
                     for row in cursor.fetchall()]
        
        return jsonify({
            'total_sales': total,
            'last_7_days': last_week,
            'top_publishers': top_publishers,
            'by_graded_status': by_graded
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ebay-sales/lookup', methods=['GET'])
def lookup_ebay_fmv():
    """
    Look up FMV based on collected eBay data.
    Query params: title, issue, graded (optional)
    """
    try:
        title = request.args.get('title', '')
        issue = request.args.get('issue', '')
        graded = request.args.get('graded', '').lower() == 'true'
        
        if not title:
            return jsonify({'error': 'Title required'}), 400
        
        cursor = get_db().cursor()
        
        # Search with fuzzy matching
        cursor.execute("""
            SELECT 
                COUNT(*) as sale_count,
                AVG(sale_price) as avg_price,
                MIN(sale_price) as min_price,
                MAX(sale_price) as max_price,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sale_price) as median_price
            FROM ebay_sales
            WHERE 
                (parsed_title ILIKE %s OR raw_title ILIKE %s)
                AND (%s = '' OR issue_number = %s)
                AND graded = %s
                AND sale_date > CURRENT_DATE - INTERVAL '90 days'
        """, (f'%{title}%', f'%{title}%', issue, issue, graded))
        
        row = cursor.fetchone()
        
        if row and row[0] > 0:
            return jsonify({
                'found': True,
                'sale_count': row[0],
                'avg_price': round(float(row[1]), 2) if row[1] else None,
                'min_price': round(float(row[2]), 2) if row[2] else None,
                'max_price': round(float(row[3]), 2) if row[3] else None,
                'median_price': round(float(row[4]), 2) if row[4] else None,
                'data_source': 'ebay_collected'
            })
        else:
            return jsonify({
                'found': False,
                'message': 'No matching sales found'
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
