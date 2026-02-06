# Route Mapping Reference
**Quick lookup: Which route is in which file?**

## 🗺️ Complete Route Map

### utils.py (3 routes)
```
GET  /                          → health()
GET  /health                    → health()
GET  /api/debug/prompt-check    → debug_prompt()
POST /api/beta/validate         → api_validate_beta()
```

### auth_routes.py (7 routes)
```
POST /api/auth/signup               → api_signup()
POST /api/auth/login                → api_login()
GET  /api/auth/verify/<token>       → api_verify_email(token)
POST /api/auth/resend-verification  → api_resend_verification()
POST /api/auth/forgot-password      → api_forgot_password()
POST /api/auth/reset-password       → api_reset_password()
GET  /api/auth/me                   → api_get_me()
```

### admin_routes.py (18 routes)
```
GET    /api/admin/dashboard                        → api_admin_dashboard()
GET    /api/admin/users                            → api_admin_users()
POST   /api/admin/users/<id>/approve               → api_approve_user(user_id)
POST   /api/admin/users/<id>/reject                → api_reject_user(user_id)
GET    /api/admin/beta-codes                       → api_get_beta_codes()
POST   /api/admin/beta-codes                       → api_create_beta_code()
GET    /api/admin/errors                           → api_get_errors()
GET    /api/admin/usage                            → api_get_usage()
GET    /api/admin/moderation                       → api_get_moderation()
POST   /api/admin/nlq                              → api_nlq()
GET    /api/admin/signatures                       → api_get_signatures()
POST   /api/admin/signatures                       → api_add_signature()
POST   /api/admin/signatures/<id>/images           → api_add_signature_image(sig_id)
DELETE /api/admin/signatures/images/<id>           → api_delete_signature_image(image_id)
POST   /api/admin/signatures/<id>/image            → api_upload_signature_image(sig_id)
POST   /api/admin/signatures/<id>/verify           → api_verify_signature(sig_id)
POST   /api/admin/backfill-barcodes                → api_backfill_barcodes()
GET    /api/admin/barcode-stats                    → api_barcode_stats()
```

### grading.py (4 routes)
```
POST /api/valuate      → api_valuate()
POST /api/cache/check  → api_cache_check()
POST /api/extract      → api_extract()
POST /api/messages     → api_messages()
```

### sales.py (6 routes)
```
POST /api/ebay-sales/batch  → add_ebay_sales_batch()
GET  /api/ebay-sales/stats  → get_ebay_sales_stats()
POST /api/sales/record      → api_record_sale()
GET  /api/sales/count       → api_sales_count()
GET  /api/sales/recent      → api_sales_recent()
GET  /api/sales/fmv         → api_sales_fmv()
```

### images.py (4 routes)
```
POST /api/images/upload           → api_r2_upload_image()
POST /api/images/upload-for-sale  → api_upload_image_for_sale()
POST /api/images/submission       → api_upload_submission_image()
GET  /api/images/status           → api_images_status()
```

### barcodes.py (2 routes)
```
GET  /api/barcode-test  → barcode_test()
POST /api/barcode-scan  → barcode_scan()
```

### ebay.py (7 routes)
```
POST /api/ebay/account-deletion     → api_ebay_account_deletion()
GET  /api/ebay/auth                 → api_ebay_auth()
GET  /api/ebay/callback             → api_ebay_callback()
GET  /api/ebay/status               → api_ebay_status()
POST /api/ebay/generate-description → api_generate_description()
POST /api/ebay/upload-image         → api_ebay_upload_image()
POST /api/ebay/list                 → api_ebay_list()
```

### collection.py (3 routes)
```
GET    /api/collection         → api_get_collection()
POST   /api/collection/save    → api_save_collection()
DELETE /api/collection/<id>    → api_delete_collection_item(item_id)
```

---

## 📁 File Organization

### By Feature Area:
```
Authentication & Users
├── auth_routes.py (7 routes)
└── admin_routes.py (18 routes)

Core Grading Features
├── grading.py (4 routes)
└── images.py (4 routes)

Sales & Market Data
├── sales.py (6 routes)
└── ebay.py (7 routes)

Utilities
├── utils.py (3 routes)
├── barcodes.py (2 routes)
└── collection.py (3 routes)
```

### By Complexity:
```
Simple (< 100 lines)
├── utils.py (72 lines)
├── barcodes.py (145 lines)
└── auth_routes.py (85 lines)

Medium (100-300 lines)
├── collection.py (91 lines)
├── images.py (183 lines)
├── ebay.py (184 lines)
└── grading.py (224 lines)

Complex (300+ lines)
├── sales.py (570 lines)
└── admin_routes.py (638 lines)
```

---

## 🔍 Quick Lookup Examples

**"Where's the login route?"**
→ `routes/auth_routes.py` → `api_login()`

**"Where's the FMV calculation?"**
→ `routes/sales.py` → `api_sales_fmv()`

**"Where's the admin dashboard?"**
→ `routes/admin_routes.py` → `api_admin_dashboard()`

**"Where's the image upload?"**
→ `routes/images.py` → `api_r2_upload_image()`

**"Where's the eBay OAuth?"**
→ `routes/ebay.py` → `api_ebay_auth()` and `api_ebay_callback()`

---

## 🎯 Route Prefixes

Each blueprint has a URL prefix that makes organization clear:

```python
utils_bp         → no prefix (/, /health, /api/beta/*)
auth_bp          → /api/auth/*
admin_bp         → /api/admin/*
grading_bp       → /api/*  (valuate, extract, cache, messages)
sales_bp         → /api/*  (sales/*, ebay-sales/*)
images_bp        → /api/images/*
barcodes_bp      → /api/*  (barcode-*)
ebay_bp          → /api/ebay/*
collection_bp    → /api/collection/*
```

---

## 📊 Stats

```
Total Routes: 54
Total Blueprints: 9
Average Routes per Blueprint: 6
Largest Blueprint: admin_routes.py (18 routes, 638 lines)
Smallest Blueprint: barcodes.py (2 routes, 145 lines)
Most Complex Route: api_sales_fmv() (193 lines)
```

---

## 🚦 Route Dependencies

Some routes depend on external modules:

### Requires Anthropic API:
- `/api/valuate` (optional, for web search fallback)
- `/api/extract`
- `/api/messages`
- `/api/ebay/generate-description`

### Requires R2 Storage:
- `/api/images/*`
- `/api/sales/record` (for image uploads)
- `/api/admin/signatures/*/images`

### Requires Barcode Scanning (Docker):
- `/api/barcode-test`
- `/api/barcode-scan`
- `/api/admin/backfill-barcodes`

### Requires eBay OAuth:
- `/api/ebay/auth`
- `/api/ebay/callback`
- `/api/ebay/list`
- `/api/ebay/upload-image`

### Requires Content Moderation (AWS):
- `/api/extract` (optional, checks images)
- `/api/images/submission` (optional, checks images)
- `/api/messages` (optional, checks images)
- `/api/admin/moderation` (to view incidents)
