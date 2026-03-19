"""
Market Sales Blueprint - Whatnot/marketplace sale recording and queries
Routes: /api/sales/record, /api/sales/count, /api/sales/recent
"""
import os
from flask import Blueprint, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor

# NORMALIZATION IMPORT
from title_normalizer import normalize_title

# Create blueprint
market_sales_bp = Blueprint('market_sales', __name__, url_prefix='/api')

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


def normalize_market_sale(sale_dict):
    """
    Normalize a Whatnot/market sale dictionary in-place.
    Call this for each sale before INSERT.
    """
    raw_title = sale_dict.get('raw_title') or sale_dict.get('title')

    if raw_title:
        try:
            normalized = normalize_title(raw_title)

            # Add normalized fields
            sale_dict['canonical_title'] = normalized['canonical_title']
            sale_dict['normalized_issue_number'] = normalized['issue_number']
            sale_dict['grade_from_title'] = normalized['grade_from_title']
            sale_dict['grading_company'] = normalized['grading_company']
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


@market_sales_bp.route('/sales/record', methods=['POST'])
def api_record_sale():
    """
    Record a sale from Whatnot extension.
    Optionally accepts 'image' field with base64 data to upload to R2.
    Now includes barcode scanning when image provided.
    """
    data = request.get_json() or {}

    # NORMALIZE THE SALE BEFORE INSERT
    data = normalize_market_sale(data)

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
                image_url, source_id, upc_main, upc_addon, is_reprint,
                canonical_title, normalized_issue_number, grade_from_title, grading_company,
                is_variant, is_signed, is_lot, is_key_issue, key_issue_claim, creators, title_notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, source_id) DO UPDATE SET
                price = EXCLUDED.price,
                sold_at = EXCLUDED.sold_at,
                upc_main = COALESCE(EXCLUDED.upc_main, market_sales.upc_main),
                upc_addon = COALESCE(EXCLUDED.upc_addon, market_sales.upc_addon),
                is_reprint = COALESCE(EXCLUDED.is_reprint, market_sales.is_reprint),
                canonical_title = EXCLUDED.canonical_title,
                normalized_issue_number = EXCLUDED.normalized_issue_number,
                grade_from_title = EXCLUDED.grade_from_title,
                grading_company = EXCLUDED.grading_company,
                is_variant = EXCLUDED.is_variant,
                is_signed = EXCLUDED.is_signed,
                is_lot = EXCLUDED.is_lot,
                is_key_issue = EXCLUDED.is_key_issue,
                key_issue_claim = EXCLUDED.key_issue_claim,
                creators = EXCLUDED.creators,
                title_notes = EXCLUDED.title_notes
            RETURNING id
        """, (data.get('source', 'whatnot'), data.get('title'), data.get('series'), data.get('issue'),
              data.get('grade'), data.get('grade_source'), data.get('slab_type'), data.get('variant'),
              data.get('is_key', False), data.get('is_facsimile', False), data.get('price'), data.get('sold_at'),
              data.get('raw_title'), data.get('seller'), data.get('bids'), data.get('viewers'),
              image_url, data.get('source_id'), upc_main, upc_addon, is_reprint,
              # Normalized fields
              data.get('canonical_title'), data.get('normalized_issue_number'),
              data.get('grade_from_title'), data.get('grading_company'),
              data.get('is_variant', False), data.get('is_signed', False),
              data.get('is_lot', False), data.get('is_key_issue', False),
              data.get('key_issue_claim'), data.get('creators'), data.get('title_notes')))

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


@market_sales_bp.route('/sales/count', methods=['GET'])
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


@market_sales_bp.route('/sales/recent', methods=['GET'])
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
