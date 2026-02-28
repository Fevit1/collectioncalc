"""
eBay Sales Blueprint - Batch ingestion, title backfill, and stats
Routes: /api/ebay-sales/*
"""
import os
import hashlib
from flask import Blueprint, jsonify, request
import psycopg2

# NORMALIZATION IMPORT
from title_normalizer import normalize_title

# Create blueprint
ebay_sales_bp = Blueprint('ebay_sales', __name__, url_prefix='/api')

# Module imports (will be set by wsgi.py)
upload_image = None
R2_AVAILABLE = False


def init_modules(r2_available, upload_image_func):
    """Initialize modules from wsgi.py"""
    global R2_AVAILABLE, upload_image
    R2_AVAILABLE = r2_available
    upload_image = upload_image_func


def normalize_ebay_sale(sale_dict):
    """
    Normalize an eBay sale dictionary in-place.
    Call this for each sale before INSERT.
    """
    raw_title = sale_dict.get('raw_title')

    if raw_title:
        try:
            normalized = normalize_title(raw_title)

            # Add normalized fields
            sale_dict['canonical_title'] = normalized['canonical_title']
            sale_dict['issue_number'] = normalized['issue_number']
            sale_dict['title_year'] = normalized.get('title_year')
            sale_dict['grade_from_title'] = normalized['grade_from_title']
            sale_dict['grading_company'] = normalized['grading_company']
            sale_dict['is_facsimile'] = normalized['is_facsimile']
            sale_dict['is_reprint'] = normalized['is_reprint']
            sale_dict['is_variant'] = normalized['is_variant']
            sale_dict['is_signed'] = normalized['is_signed']
            sale_dict['is_lot'] = normalized['is_lot']
            sale_dict['is_key_issue'] = normalized['is_key_issue']
            sale_dict['key_issue_claim'] = normalized['key_issue_claim']
            sale_dict['creators'] = normalized['creators']
            sale_dict['title_notes'] = normalized['title_notes']
        except Exception as e:
            print(f"Title normalization failed for: {raw_title}")
            print(f"Error: {str(e)}")
            # Continue without normalization - sale still gets saved

    return sale_dict


@ebay_sales_bp.route('/ebay-sales/batch', methods=['POST'])
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

        # NORMALIZE EACH SALE BEFORE INSERT
        for sale in sales:
            sale = normalize_ebay_sale(sale)

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
                        listing_url, image_url, ebay_item_id, content_hash,
                        canonical_title, grade_from_title, grading_company,
                        is_facsimile, is_reprint, is_variant, is_signed, is_lot,
                        is_key_issue, key_issue_claim, creators, title_notes,
                        title_year
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    content_hash,
                    # Normalized fields
                    sale.get('canonical_title'),
                    sale.get('grade_from_title'),
                    sale.get('grading_company'),
                    sale.get('is_facsimile', False),
                    sale.get('is_reprint', False),
                    sale.get('is_variant', False),
                    sale.get('is_signed', False),
                    sale.get('is_lot', False),
                    sale.get('is_key_issue', False),
                    sale.get('key_issue_claim'),
                    sale.get('creators'),
                    sale.get('title_notes'),
                    sale.get('title_year')
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


@ebay_sales_bp.route('/ebay-sales/backfill-titles', methods=['POST'])
def backfill_canonical_titles():
    """
    Re-run title_normalizer on all ebay_sales with NULL canonical_title.
    POST /api/ebay-sales/backfill-titles
    Optional query param: ?limit=100 (default: all)
    """
    database_url = os.environ.get('DATABASE_URL')
    conn = None
    try:
        limit = request.args.get('limit', type=int)
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # Fetch all records with NULL canonical_title
        query = "SELECT id, raw_title FROM ebay_sales WHERE canonical_title IS NULL"
        if limit:
            query += f" LIMIT {limit}"
        cur.execute(query)
        rows = cur.fetchall()

        if not rows:
            return jsonify({'success': True, 'message': 'No NULL canonical_titles found', 'updated': 0})

        updated = 0
        failed = 0
        failures = []

        for row_id, raw_title in rows:
            if not raw_title:
                failed += 1
                continue

            try:
                normalized = normalize_title(raw_title)
                canonical = normalized.get('canonical_title')

                if canonical:
                    cur.execute("""
                        UPDATE ebay_sales SET
                            canonical_title = %s,
                            grade_from_title = %s,
                            grading_company = %s,
                            is_facsimile = %s,
                            is_reprint = %s,
                            is_variant = %s,
                            is_signed = %s,
                            is_lot = %s,
                            is_key_issue = %s,
                            key_issue_claim = %s,
                            creators = %s,
                            title_notes = %s,
                            title_year = %s
                        WHERE id = %s
                    """, (
                        canonical,
                        normalized.get('grade_from_title'),
                        normalized.get('grading_company'),
                        normalized.get('is_facsimile', False),
                        normalized.get('is_reprint', False),
                        normalized.get('is_variant', False),
                        normalized.get('is_signed', False),
                        normalized.get('is_lot', False),
                        normalized.get('is_key_issue', False),
                        normalized.get('key_issue_claim'),
                        normalized.get('creators'),
                        normalized.get('title_notes'),
                        normalized.get('title_year')
                    ))
                    updated += 1
                else:
                    failed += 1
                    failures.append({'id': row_id, 'raw_title': raw_title, 'reason': 'normalizer returned None'})
            except Exception as e:
                failed += 1
                failures.append({'id': row_id, 'raw_title': raw_title, 'reason': str(e)})

        conn.commit()

        return jsonify({
            'success': True,
            'total_null': len(rows),
            'updated': updated,
            'still_null': failed,
            'sample_failures': failures[:20]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@ebay_sales_bp.route('/ebay-sales/stats', methods=['GET'])
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
