# Claude Notes - CollectionCalc Development

## Purpose
This document provides context for Claude (AI assistant) when continuing development work on CollectionCalc. It captures key decisions, patterns, and gotchas learned across sessions.

---

## Session History

### Session 10 (January 26, 2026) - Facsimile Detection, Signatures & Extension Fixes
**Major accomplishments:**
- Facsimile detection in vision.js (detects reprints, warns user)
- Signature database created (40+ creators with style descriptions)
- Signatures admin page (`/signatures.html`) for managing reference images
- FMV endpoint (`/api/sales/fmv`) for extension grade-tier pricing
- Admin button added to app.html header
- Fixed truncated app.html (missing `<script>` tag)
- Fixed extension auto-scan (removed hasGoodDOMData check to always capture images)
- Added debug interface to content.js (`ValuatorDebug.getAutoScanState()`)

**Key decisions:**
- Always auto-scan even with "good" DOM data - we want images for every sale
- Facsimile detection is prompt-based (no fine-tuning needed yet)
- Signature database starts with text descriptions, images added via admin UI
- R2 stores signature references at `/signatures/{id}.jpg`

**Files created/modified:**
- `vision.js` - Added facsimile detection to extraction prompt
- `collectioncalc.js` - Added `getFMV()` function and `is_facsimile` field
- `content.js` - Removed hasGoodDOMData check, added ValuatorDebug interface
- `wsgi.py` - Added `/api/sales/fmv` and signature admin endpoints
- `signatures.html` - New admin page for signature management
- `admin.html` - Added link to signatures page
- `app.html` - Fixed truncation, script tag restored
- `db_migrate_signatures.py` - Migration for creator_signatures and signature_matches tables

**Database tables added:**
```sql
creator_signatures (
    id, creator_name, role, reference_image_url, 
    signature_style, verified, source, notes, 
    created_at, updated_at
)

signature_matches (
    id, sale_id, signature_id, confidence, 
    match_method, created_at
)
```

**Known issue - Multi-tab auto-scan:**
- Second Whatnot tab sometimes gets stuck on "Preparing..."
- Root cause: Chrome throttles background tabs when memory is high
- Manual scan still works on both tabs
- Debug tools added: `ValuatorDebug.getAutoScanState()` and `.resetAutoScan()`
- Workaround: Close unused tabs to free memory, or use manual scan

### Session 9 (January 26, 2026) - Beta Access & R2 Images
**Major accomplishments:**
- Beta code gate system (landing page, validation, usage tracking)
- User approval workflow (admin approves new signups)
- Admin dashboard with Natural Language Query (NLQ)
- Request logging for mobile debugging
- Cloudflare R2 image storage integration
- Whatnot extension updated to upload images
- NLQ results now show image thumbnails

**Key decisions:**
- Used word-boundary regex for SQL keyword blocking in NLQ (prevents `created_at` from matching `create`)
- Extension sends images inline with sale data (backend uploads to R2)
- R2 path structure: `/sales/{id}/front.jpg` (ready for B4Cert's 4-image flow)
- Admin dashboard at `/admin.html`, main app at `/app.html`, landing at `/index.html`

**Files created/modified:**
- `auth.py` - Added beta code and approval functions
- `admin.py` - Admin dashboard backend, NLQ
- `r2_storage.py` - R2 upload module
- `wsgi.py` - Added admin, image, and beta endpoints
- `landing.html` → `index.html` - Beta gate landing page
- `admin.html` - Admin dashboard
- `collectioncalc.js` - Extension API client (replaces Supabase)
- `API_REFERENCE.md` - Function names to prevent import errors

### Session 8 (January 25, 2026) - Whatnot Integration
- Migrated from Supabase to CollectionCalc PostgreSQL
- Created `market_sales` table
- Extension writes directly to CollectionCalc backend
- 618 historical sales migrated

### Session 7 (January 22, 2026) - Frontend Refactor
- Split index.html into 3 files (index.html, styles.css, app.js)
- Opus vs Sonnet testing for signature detection
- Premium tier concept validated

### Sessions 1-6
- Core valuation engine
- eBay integration
- QuickList batch processing
- User auth and collections

---

## Code Patterns

### Import Pattern (wsgi.py)
Always use try/except for module imports to prevent deployment failures:
```python
try:
    from module_name import function_name
except ImportError as e:
    print(f"module_name import error: {e}")
    function_name = None
```

### Auth Decorators
```python
@require_auth          # Verifies JWT, sets g.user_id
@require_approved      # Requires is_approved=True (or is_admin)
@require_admin_auth    # Requires is_admin=True
```

### R2 Image Upload
```python
from r2_storage import upload_sale_image, upload_to_r2
result = upload_sale_image(sale_id, base64_image_data, 'front')
# Returns: {'success': True, 'url': 'https://pub-xxx.r2.dev/sales/123/front.jpg'}

# For signatures:
result = upload_to_r2(f"signatures/{sig_id}.jpg", base64_data)
```

### NLQ Safety
The NLQ system blocks dangerous SQL keywords using word boundaries:
```python
dangerous = ['insert', 'update', 'delete', 'drop', 'truncate', 'alter', 'grant', 'revoke']
for word in dangerous:
    if re.search(rf'\b{word}\b', sql_lower):
        # Block query
```
Note: `create` was removed from the list because it matched `created_at`.

---

## Common Gotchas

### Function Name Mismatches
**Always check `API_REFERENCE.md` before writing imports!**

Common mistakes:
| Wrong | Correct |
|-------|---------|
| `get_ebay_valuation` | `get_valuation_with_ebay` |
| `exchange_code` | `exchange_code_for_token` |
| `get_valid_token` | `get_user_token` |
| `create_ebay_listing` | `create_listing` |
| `generate_ebay_description` | `generate_description` |
| `extract_comic_from_image` | `extract_from_base64` |

### Duplicate Function Names
Flask requires unique function names for endpoints. If you get `AssertionError: View function mapping is overwriting an existing endpoint`:
```python
# Wrong - both named api_upload_image
@app.route('/api/ebay/upload-image')
def api_upload_image(): ...

@app.route('/api/images/upload')
def api_upload_image(): ...  # Conflict!

# Right - unique names
@app.route('/api/ebay/upload-image')
def api_ebay_upload_image(): ...

@app.route('/api/images/upload')
def api_r2_upload_image(): ...
```

### Extension SupabaseClient Interface
The extension's `content.js` calls `window.SupabaseClient.insertSale(sale)`. The new `collectioncalc.js` must expose this interface for backwards compatibility:
```javascript
window.SupabaseClient = {
    insertSale,
    getRecentSales,
    getSalesCount,
    uploadImage,
    getFMV  // Added Session 10
};
```

### R2 Public Access
R2 buckets are private by default. Must enable "Public Development URL" in Cloudflare dashboard to serve images publicly.

### CORS on Sales Endpoints
The `/api/sales/*` endpoints are called by the extension from whatnot.com. CORS must allow `*` origins (already configured in wsgi.py).

### HTML File Truncation
When editing large HTML files, they can get truncated. Always verify the closing tags and `<script>` references are present. Session 10 fix: `app.html` was missing closing tags and `<script src="app.js"></script>`.

---

## Database Tables Added

### Session 10 - Signatures
```sql
-- Creator signature references
creator_signatures (
    id SERIAL PRIMARY KEY,
    creator_name VARCHAR(255) NOT NULL,
    role VARCHAR(50),                    -- artist, writer, cover_artist, etc.
    reference_image_url TEXT,            -- R2 URL
    signature_style TEXT,                -- "Large flowing signature, often dated"
    verified BOOLEAN DEFAULT FALSE,
    source VARCHAR(255),                 -- "eBay purchase", "CGC verified"
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)

-- Signature match records (for future AI matching)
signature_matches (
    id SERIAL PRIMARY KEY,
    sale_id INTEGER REFERENCES market_sales(id),
    signature_id INTEGER REFERENCES creator_signatures(id),
    confidence DECIMAL(3,2),
    match_method VARCHAR(50),            -- "ai_vision", "manual"
    created_at TIMESTAMP DEFAULT NOW()
)

-- Facsimile detection (column added to existing table)
market_sales ADD COLUMN is_facsimile BOOLEAN DEFAULT FALSE
```

### Session 9 - Beta & Admin
```sql
-- Run via: python db_migrate_beta.py on Render shell

-- Beta codes
beta_codes (code, uses_allowed, uses_remaining, expires_at, note, is_active, created_by, created_at)

-- User fields added
users ADD COLUMN is_approved BOOLEAN DEFAULT FALSE
users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE  
users ADD COLUMN approved_at TIMESTAMP
users ADD COLUMN approved_by INTEGER
users ADD COLUMN beta_code_used VARCHAR(50)

-- Request logging
request_logs (endpoint, method, status_code, response_time_ms, user_id, device_type, error_message, request_data, created_at)

-- API usage tracking
api_usage (user_id, endpoint, model, input_tokens, output_tokens, cost_usd, created_at)

-- NLQ history
admin_nlq_history (admin_id, question, generated_sql, result_count, execution_time_ms, created_at)
```

---

## Environment Variables

### Required for Full Functionality
```bash
# Database
DATABASE_URL

# Auth
JWT_SECRET

# Email
RESEND_API_KEY

# AI
ANTHROPIC_API_KEY

# eBay
EBAY_CLIENT_ID
EBAY_CLIENT_SECRET
EBAY_RUNAME

# R2 Storage (new in Session 9)
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
R2_ACCOUNT_ID
R2_BUCKET_NAME=collectioncalc-images
R2_ENDPOINT
R2_PUBLIC_URL
```

---

## Testing Checklist

### After Backend Deploy
1. Check Render logs for import errors
2. Test `/api/images/status` returns `connected: true`
3. Test NLQ with a simple query
4. Verify no 404s on `/api/ebay/account-deletion` (eBay polls this)
5. Test `/api/sales/fmv?title=Spider-Man&issue=1` returns tier data

### After Extension Update
1. Reload extension in chrome://extensions
2. Check for console errors on Whatnot page
3. Verify `[CollectionCalc] ✅ API client loaded` appears
4. Record a sale with vision scan
5. Verify image appears in NLQ results with R2 URL
6. Test auto-scan triggers on new listings

### After Frontend Deploy
1. Run `purge` to clear Cloudflare cache
2. Test beta code flow on landing page
3. Test login persistence
4. Test admin dashboard at /admin.html
5. Test signatures page at /signatures.html
6. Verify admin button appears for admin users

---

## Extension Debug Tools (Added Session 10)

```javascript
// Check auto-scan state
ValuatorDebug.getAutoScanState()
// Returns: { autoScanEnabled, isScanning, scanCooldownUntil, lastScannedListingId, ... }

// Reset stuck auto-scan
ValuatorDebug.resetAutoScan()

// Force trigger a scan
ValuatorDebug.forceScan()

// Get session stats
ValuatorDebug.getStats()

// Download all sales as JSON
ValuatorDebug.download()
```

---

## Quick Commands

```bash
# Deploy backend (Render auto-deploys, or manual if set)
cd cc/v2
git add .; git commit -m "msg"; git push; deploy

# Deploy frontend + clear cache
cd cc/v2
git add .; git commit -m "msg"; git push; purge

# Combined deploy
git add .; git commit -m "msg"; git push; deploy; purge

# Run database migration (in Render shell)
python db_migrate_signatures.py

# Set yourself as admin (in DBeaver)
UPDATE users SET is_admin = TRUE, is_approved = TRUE WHERE email = 'your@email.com';

# Add facsimile column (in DBeaver)
ALTER TABLE market_sales ADD COLUMN IF NOT EXISTS is_facsimile BOOLEAN DEFAULT FALSE;
```

---

## Future Considerations

### Signature Matching
Current setup: Text descriptions only. Future:
1. Collect reference images (eBay ~$1-5 for cheap signed comics)
2. Upload to R2 via signatures admin page
3. AI compares incoming signatures to references
4. Return creator name + confidence %

### Facsimile Handling
Current: Detection only. Future:
- Auto-adjust FMV to $5-15 when facsimile detected
- Show prominent warning badge in UI
- Prevent accidental overpayment

### Image Cropping
Current images include background noise from Whatnot video. Options:
1. Vision-guided crop (Claude returns bounding box)
2. Center crop (60-70% of frame)
3. AI background removal

### B4Cert Integration
R2 storage is already set up for 4-image submissions:
```
/submissions/{id}/front.jpg
/submissions/{id}/back.jpg
/submissions/{id}/spine.jpg
/submissions/{id}/centerfold.jpg
```

---

*Last updated: January 26, 2026 (Session 10)*
