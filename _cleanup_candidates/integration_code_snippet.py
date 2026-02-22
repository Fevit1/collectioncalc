"""
Ready-to-use code snippets for integrating title_normalizer into Flask routes.
Copy these into your routes/sales.py or routes/ebay.py files.
"""

# ============================================================================
# SNIPPET 1: Import at top of file
# ============================================================================
from title_normalizer import normalize_title


# ============================================================================
# SNIPPET 2: eBay Sales Batch Endpoint Integration
# ============================================================================

# Find your /api/ebay-sales/batch endpoint and add this normalization step
# BEFORE inserting into the database:

def normalize_ebay_sale(sale_dict):
    """
    Normalize an eBay sale dictionary in-place.
    Call this for each sale before INSERT.
    """
    raw_title = sale_dict.get('raw_title')

    if raw_title:
        normalized = normalize_title(raw_title)

        # Add normalized fields (these match your ebay_sales columns)
        sale_dict['canonical_title'] = normalized['canonical_title']
        sale_dict['issue_number'] = normalized['issue_number']
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

    return sale_dict


# Usage in your batch endpoint:
@ebay_sales_bp.route('/ebay-sales/batch', methods=['POST'])
def batch_insert_ebay_sales():
    data = request.json
    sales = data.get('sales', [])

    # Normalize each sale
    for sale in sales:
        sale = normalize_ebay_sale(sale)

    # Then continue with your existing INSERT logic...
    # for sale in sales:
    #     cursor.execute(INSERT_SQL, sale)


# ============================================================================
# SNIPPET 3: Whatnot/Market Sales Endpoint Integration
# ============================================================================

def normalize_market_sale(sale_dict):
    """
    Normalize a Whatnot/market sale dictionary in-place.
    Call this for each sale before INSERT.
    """
    raw_title = sale_dict.get('raw_title') or sale_dict.get('title')

    if raw_title:
        normalized = normalize_title(raw_title)

        # Add normalized fields (these match your market_sales columns)
        sale_dict['canonical_title'] = normalized['canonical_title']
        sale_dict['normalized_issue_number'] = normalized['issue_number']  # Note: different column name
        sale_dict['grade_from_title'] = normalized['grade_from_title']
        sale_dict['grading_company'] = normalized['grading_company']
        sale_dict['is_variant'] = normalized['is_variant']
        sale_dict['is_signed'] = normalized['is_signed']
        sale_dict['is_lot'] = normalized['is_lot']
        sale_dict['is_key_issue'] = normalized['is_key_issue']
        sale_dict['key_issue_claim'] = normalized['key_issue_claim']
        sale_dict['creators'] = normalized['creators']
        sale_dict['title_notes'] = normalized['title_notes']

    return sale_dict


# Usage in your market sales endpoint:
@sales_bp.route('/sales', methods=['POST'])
def create_market_sale():
    data = request.json

    # Normalize the sale
    data = normalize_market_sale(data)

    # Then continue with your existing INSERT logic...
    # cursor.execute(INSERT_SQL, data)


# ============================================================================
# SNIPPET 4: Error Handling (Optional but Recommended)
# ============================================================================

def normalize_ebay_sale_safe(sale_dict):
    """
    Safe wrapper with error handling.
    If normalization fails, log error and continue with raw data.
    """
    try:
        return normalize_ebay_sale(sale_dict)
    except Exception as e:
        print(f"Title normalization failed for: {sale_dict.get('raw_title')}")
        print(f"Error: {str(e)}")
        # Return original dict unchanged - sale still gets saved
        return sale_dict


# ============================================================================
# DEPLOYMENT CHECKLIST
# ============================================================================
"""
Before deploying:

1. ✅ Copy these 4 files to backend root:
   - title_normalizer.py
   - known_titles.json
   - known_creators.json
   - title_mappings.json

2. ✅ Add to requirements.txt:
   rapidfuzz>=3.0.0

3. ✅ Find your sales endpoints in routes/ and add normalization

4. ✅ Test locally:
   python -c "from title_normalizer import normalize_title; print(normalize_title('Batman #1'))"

5. ✅ Commit, push, and deploy

6. ✅ Test with real data:
   - Scrape 1 eBay sale with extension
   - Check database for populated normalized columns
   - Verify creators, canonical_title, flags are correct

7. ✅ Monitor logs for any normalization errors
"""
