# Backend Integration Guide: Auto-Normalize Sales

This guide shows how to integrate the title normalizer into your Flask backend so new sales are automatically normalized as they come in.

## Step 1: Copy Files to Backend

Copy these files from `V2/` to your backend root directory:

```
CC/
├── title_normalizer.py          # Core normalizer
├── known_titles.json            # 180+ known titles
├── known_creators.json          # 70+ creators
└── title_mappings.json          # Limited series mappings
```

## Step 2: Add Dependencies

Add to `requirements.txt`:
```
rapidfuzz>=3.0.0
```

Then rebuild your Docker container.

## Step 3: Modify eBay Sales Endpoint

In `routes/sales.py` (or wherever `/api/ebay-sales/batch` is defined):

```python
from title_normalizer import normalize_title

@ebay_sales_bp.route('/ebay-sales/batch', methods=['POST'])
def batch_insert():
    data = request.json
    sales = data.get('sales', [])

    for sale in sales:
        raw_title = sale.get('raw_title')

        # NORMALIZE TITLE AUTOMATICALLY
        if raw_title:
            normalized = normalize_title(raw_title)

            # Add normalized fields to sale dict
            sale['canonical_title'] = normalized['canonical_title']
            sale['issue_number'] = normalized['issue_number']
            sale['grade_from_title'] = normalized['grade_from_title']
            sale['grading_company'] = normalized['grading_company']
            sale['is_facsimile'] = normalized['is_facsimile']
            sale['is_reprint'] = normalized['is_reprint']
            sale['is_variant'] = normalized['is_variant']
            sale['is_signed'] = normalized['is_signed']
            sale['is_lot'] = normalized['is_lot']
            sale['is_key_issue'] = normalized['is_key_issue']
            sale['key_issue_claim'] = normalized['key_issue_claim']
            sale['creators'] = normalized['creators']
            sale['title_notes'] = normalized['title_notes']

    # Continue with your existing INSERT logic...
    # cursor.execute(INSERT_SQL, ...)
```

## Step 4: Modify Whatnot/Market Sales Endpoint

In `routes/sales.py` (or wherever market_sales are inserted):

```python
from title_normalizer import normalize_title

@sales_bp.route('/sales', methods=['POST'])
def create_sale():
    data = request.json
    raw_title = data.get('raw_title') or data.get('title')

    # NORMALIZE TITLE AUTOMATICALLY
    if raw_title:
        normalized = normalize_title(raw_title)

        # Add normalized fields
        data['canonical_title'] = normalized['canonical_title']
        data['normalized_issue_number'] = normalized['issue_number']
        data['grade_from_title'] = normalized['grade_from_title']
        data['grading_company'] = normalized['grading_company']
        data['is_variant'] = normalized['is_variant']
        data['is_signed'] = normalized['is_signed']
        data['is_lot'] = normalized['is_lot']
        data['is_key_issue'] = normalized['is_key_issue']
        data['key_issue_claim'] = normalized['key_issue_claim']
        data['creators'] = normalized['creators']
        data['title_notes'] = normalized['title_notes']

    # Continue with your existing INSERT logic...
```

## Step 5: Update INSERT Statements

Make sure your SQL INSERT statements include all the normalized columns:

**For ebay_sales:**
```sql
INSERT INTO ebay_sales (
    raw_title, canonical_title, issue_number, grade_from_title,
    grading_company, is_facsimile, is_reprint, is_variant,
    is_signed, is_lot, is_key_issue, key_issue_claim,
    creators, title_notes,
    -- ... other fields ...
) VALUES (
    %(raw_title)s, %(canonical_title)s, %(issue_number)s, %(grade_from_title)s,
    %(grading_company)s, %(is_facsimile)s, %(is_reprint)s, %(is_variant)s,
    %(is_signed)s, %(is_lot)s, %(is_key_issue)s, %(key_issue_claim)s,
    %(creators)s, %(title_notes)s,
    -- ... other values ...
)
```

**For market_sales:**
```sql
INSERT INTO market_sales (
    raw_title, canonical_title, normalized_issue_number, grade_from_title,
    grading_company, is_variant, is_signed, is_lot,
    is_key_issue, key_issue_claim, creators, title_notes,
    -- ... other fields ...
) VALUES (
    %(raw_title)s, %(canonical_title)s, %(normalized_issue_number)s, %(grade_from_title)s,
    %(grading_company)s, %(is_variant)s, %(is_signed)s, %(is_lot)s,
    %(is_key_issue)s, %(key_issue_claim)s, %(creators)s, %(title_notes)s,
    -- ... other values ...
)
```

## Step 6: Test

After deployment:

1. Use your eBay Collector extension to scrape a few sales
2. Check the database - normalized fields should be populated automatically
3. Use Whatnot extension to capture a sale
4. Verify market_sales has normalized data

## Performance Note

The normalizer is fast (~1-2ms per title). For batch inserts of 100+ sales:
- Total overhead: ~100-200ms
- Acceptable for user-facing API responses
- No caching needed

## Updating Known Titles/Creators

To add new titles or creators:

1. Edit `known_titles.json` or `known_creators.json`
2. Commit and push
3. Redeploy backend (Docker will reload the JSON files)

No code changes needed!

## Rollback Plan

If issues arise:
1. Remove `normalize_title()` calls from routes
2. Normalized columns will remain NULL for new records
3. Can run batch script later to backfill

---

**Next:** Deploy these changes and test with a few live sales captures!
