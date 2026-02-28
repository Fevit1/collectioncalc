# Slab Worthy API Reference

**Last updated:** February 28, 2026 (Session 69)

## Purpose
This document lists the actual function names exported from each module.
**Reference this before writing import statements to avoid mismatches.**

---

## Module: `ebay_valuation.py`

| Function | Description |
|----------|-------------|
| `get_valuation_with_ebay()` | Main valuation function — combines DB + eBay data |
| `search_ebay_sold()` | Search eBay sold listings via Claude |
| `expand_title_alias()` | Expand abbreviations (ASM → Amazing Spider-Man) |
| `get_cached_result()` | Check cache for existing valuation |
| `save_to_cache()` | Save valuation result to cache |
| `update_cached_value()` | Update cached valuation with new sales data |
| `calculate_confidence()` | Calculate confidence level and score |
| `calculate_tier_confidence()` | Calculate per-tier confidence scores |
| `get_grade_value()` | Convert grade string to numeric value |
| `is_grade_compatible()` | Check if sale grade is compatible with requested grade |
| `normalize_grade_for_cache()` | Normalize grade for cache lookups |
| `get_recency_weight()` | Calculate weight multiplier based on sale recency |

**Common mistake:** Don't use `get_ebay_valuation` — it doesn't exist.

---

## Module: `ebay_oauth.py`

| Function | Description |
|----------|-------------|
| `get_auth_url()` | Generate eBay OAuth URL |
| `exchange_code_for_token()` | Exchange auth code for access token |
| `refresh_access_token()` | Refresh expired token |
| `save_user_token()` | Save token to database |
| `get_user_token()` | Get user's token (refreshes if needed) |
| `is_user_connected()` | Check if user has valid eBay connection |
| `disconnect_user()` | Remove user's eBay connection |
| `save_ebay_user_id()` | Save eBay's user ID to our DB |
| `delete_user_by_ebay_id()` | GDPR deletion by eBay user ID |
| `init_ebay_tokens_table()` | Create ebay_tokens table if needed |
| `is_sandbox_mode()` | Check if using eBay sandbox |

**Common mistakes:**
- Don't use `exchange_code` — use `exchange_code_for_token`
- Don't use `get_valid_token` — use `get_user_token`

---

## Module: `ebay_listing.py`

| Function | Description |
|----------|-------------|
| `create_listing()` | Create eBay listing (Fixed Price or Auction) |
| `upload_image_to_ebay()` | Upload image to eBay Picture Services |
| `get_or_create_merchant_location()` | Set up merchant location |
| `get_or_create_listing_policies()` | Get business policies |
| `get_listing_status()` | Check listing status |
| `get_api_url()` | Get eBay API URL (production or sandbox) |

**`create_listing()` full signature (Session 69):**
```python
def create_listing(
    user_id: str, title: str, issue: str, price: float,
    grade: str = 'VF', description: str = None, publish: bool = False,
    image_urls: list = None, listing_format: str = 'FIXED_PRICE',
    auction_duration: str = 'DAYS_7', start_price: float = None,
    reserve_price: float = None, buy_it_now_price: float = None
) -> dict
```

---

## Module: `ebay_description.py`

| Function | Description |
|----------|-------------|
| `generate_description()` | Generate AI description (targets 235-245 chars for mobile) |
| `validate_description()` | Validate description for eBay compliance |

---

## Module: `comic_extraction.py`

| Function | Description |
|----------|-------------|
| `extract_from_photo()` | Extract comic info from raw image bytes |
| `extract_from_base64()` | Extract comic info from base64-encoded image |
| `scan_barcode()` | Scan image for UPC barcode |
| `decode_barcode()` | Decode 5-digit UPC supplement code |

---

## Module: `auth.py`

| Function | Description |
|----------|-------------|
| `signup()` | Create new user account |
| `login()` | Authenticate user |
| `verify_email()` | Verify email with token |
| `resend_verification()` | Resend verification email |
| `forgot_password()` | Send password reset email |
| `reset_password()` | Reset password with token |
| `generate_jwt()` | Generate JWT token |
| `verify_jwt()` | Verify JWT token |
| `get_user_by_id()` | Get user by ID |
| `get_user_by_email()` | Get user by email |
| `get_current_user()` | Get current user from JWT token |
| `validate_beta_code()` | Check if beta code is valid |
| `use_beta_code()` | Mark beta code as used |
| `create_beta_code()` | Create new beta code (admin) |
| `list_beta_codes()` | List all beta codes (admin) |
| `approve_user()` | Approve pending user (admin) |
| `reject_user()` | Reject and delete user (admin) |
| `get_pending_users()` | Get users awaiting approval |
| `get_all_users()` | Get all users (admin) |
| `is_user_admin()` | Check if user is admin |
| `is_user_approved()` | Check if user is approved |
| `require_auth` | Decorator: require JWT authentication |
| `require_approved` | Decorator: require user approval |
| `require_admin_auth` | Decorator: require admin authentication |

---

## Module: `admin.py`

| Function | Description |
|----------|-------------|
| `log_request()` | Log API request to database |
| `log_api_usage()` | Log Anthropic API usage |
| `get_dashboard_stats()` | Get admin dashboard statistics |
| `get_recent_errors()` | Get recent failed requests |
| `get_endpoint_stats()` | Get stats by endpoint |
| `get_device_breakdown()` | Get requests by device type |
| `natural_language_query()` | Execute NLQ via Claude |
| `get_nlq_history()` | Get past NLQ queries |
| `get_anthropic_usage_summary()` | Get API usage summary |

---

## Module: `content_moderation.py`

| Function | Description |
|----------|-------------|
| `moderate_image()` | Check image via AWS Rekognition |
| `log_moderation_incident()` | Log moderation event to DB |
| `get_image_hash()` | Generate SHA256 hash of image |
| `get_moderation_incidents()` | Get recent incidents (admin) |
| `get_moderation_stats()` | Get moderation stats (admin) |

---

## Module: `r2_storage.py`

| Function | Description |
|----------|-------------|
| `get_r2_client()` | Get S3 client for Cloudflare R2 |
| `upload_image()` | Upload image to R2 |
| `upload_to_r2()` | Alias for upload_image |
| `upload_sale_image()` | Upload image for a sale |
| `upload_submission_image()` | Upload B4Cert submission image |
| `upload_temp_image()` | Upload temp image during extraction |
| `delete_image()` | Delete image from R2 |
| `get_image_url()` | Get public URL for image |
| `move_temp_to_sale()` | Move temp image to permanent location |
| `check_r2_connection()` | Test R2 connection status |

---

## Module: `title_normalizer.py`

| Function | Description |
|----------|-------------|
| `normalize_title()` | Parse raw eBay title into structured fields |

---

## Critical Endpoints (Don't Delete!)

| Endpoint | Purpose | Required By |
|----------|---------|-------------|
| `/api/ebay/account-deletion` | GDPR compliance | eBay (they poll this) |
| `/api/sales/record` | Whatnot extension writes | Chrome extension |
| `/api/sales/recent` | Whatnot extension reads | Chrome extension |
| `/api/ebay-sales/batch` | eBay collector writes | Chrome extension |
| `/api/monitor/*` | Slab Guard monitoring | Slab Guard extension |
| `/api/billing/webhook` | Stripe events | Stripe |
| `/health` or `/` | Health check | Render |

---

*Last updated: February 28, 2026 (Session 69)*
