# Route Mapping Reference
**Quick lookup: Which route is in which file?**

**Last updated:** February 28, 2026 (Session 69)

---

## Complete Route Map (87 routes across 19 files)

### utils.py (5 routes, no url_prefix)
```
GET  /                          → health()
GET  /health                    → health()
GET  /api/debug/prompt-check    → debug_prompt()
POST /api/beta/validate         → api_validate_beta()
GET  /verify                    → serve_verify()
```

### auth_routes.py (7 routes, prefix=/api/auth)
```
POST /api/auth/signup               → api_signup()
POST /api/auth/login                → api_login()
GET  /api/auth/verify/<token>       → api_verify_email(token)
POST /api/auth/resend-verification  → api_resend_verification()
POST /api/auth/forgot-password      → api_forgot_password()
POST /api/auth/reset-password       → api_reset_password()
GET  /api/auth/me                   → api_get_me()               [auth]
```

### admin_routes.py (20 routes, prefix=/api/admin) [all admin-only]
```
GET    /api/admin/dashboard                        → api_admin_dashboard()
GET    /api/admin/users                            → api_admin_users()
POST   /api/admin/users/<id>/approve               → api_approve_user()
POST   /api/admin/users/<id>/reject                → api_reject_user()
GET    /api/admin/beta-codes                       → api_get_beta_codes()
POST   /api/admin/beta-codes                       → api_create_beta_code()
GET    /api/admin/errors                           → api_get_errors()
GET    /api/admin/usage                            → api_get_usage()
GET    /api/admin/moderation                       → api_get_moderation()
POST   /api/admin/nlq                              → api_nlq()
GET    /api/admin/signatures                       → api_get_signatures()
POST   /api/admin/signatures                       → api_add_signature()
POST   /api/admin/signatures/<id>/images           → api_add_signature_image()
DELETE /api/admin/signatures/images/<id>           → api_delete_signature_image()
DELETE /api/admin/signatures/<id>                  → api_delete_signature()
POST   /api/admin/signatures/<id>/image            → api_upload_signature_image() [legacy]
POST   /api/admin/signatures/<id>/verify           → api_verify_signature()
POST   /api/admin/backfill-barcodes                → api_backfill_barcodes()
GET    /api/admin/barcode-stats                    → api_barcode_stats()
GET    /api/admin/slab-guard-stats                 → api_slab_guard_stats()
```

### grading.py (5 routes, prefix=/api) [auth+approved]
```
POST /api/valuate      → api_valuate()
POST /api/cache/check  → api_cache_check()
POST /api/extract      → api_extract()
POST /api/messages     → api_messages()
POST /api/grade        → api_grade()
```

### sales_ebay.py (3 routes, prefix=/api)
```
POST /api/ebay-sales/batch            → add_ebay_sales_batch()
POST /api/ebay-sales/backfill-titles  → backfill_canonical_titles()
GET  /api/ebay-sales/stats            → get_ebay_sales_stats()
```

### sales_market.py (3 routes, prefix=/api)
```
POST /api/sales/record  → api_record_sale()
GET  /api/sales/count   → api_sales_count()
GET  /api/sales/recent  → api_sales_recent()
```

### sales_valuation.py (2 routes, prefix=/api)
```
GET /api/sales/valuation  → api_sales_valuation()
GET /api/sales/fmv        → api_sales_fmv()
```

### images.py (7 routes, prefix=/api/images)
```
POST /api/images/upload           → api_r2_upload_image()
POST /api/images/upload-for-sale  → api_upload_image_for_sale()
POST /api/images/submission       → api_upload_submission_image()
GET  /api/images/status           → api_images_status()
POST /api/images/upload-extra     → api_upload_extra_photo()      [auth+approved]
POST /api/images/delete-extra     → api_delete_extra_photo()      [auth+approved]
GET  /api/images/extra-types      → api_extra_photo_types()
```

### barcodes.py (2 routes, prefix=/api)
```
GET  /api/barcode-test  → barcode_test()
POST /api/barcode-scan  → barcode_scan()
```

### ebay.py (7 routes, prefix=/api/ebay)
```
POST /api/ebay/account-deletion     → api_ebay_account_deletion()    [GDPR]
GET  /api/ebay/auth                 → api_ebay_auth()                [auth+approved]
GET  /api/ebay/callback             → api_ebay_callback()
GET  /api/ebay/status               → api_ebay_status()              [auth+approved]
POST /api/ebay/generate-description → api_generate_description()     [auth+approved]
POST /api/ebay/upload-image         → api_ebay_upload_image()        [auth+approved]
POST /api/ebay/list                 → api_ebay_list()                [auth+approved]
```

### collection.py (4 routes, prefix=/api/collection) [auth+approved]
```
GET    /api/collection                      → api_get_collection()
POST   /api/collection/save                 → api_save_collection()
DELETE /api/collection/<id>                 → api_delete_collection_item()
PATCH  /api/collection/<id>/valuation       → api_update_valuation()
```

### registry.py (4 routes, prefix=/api/registry)
```
POST /api/registry/register             → register_comic()           [auth+approved]
GET  /api/registry/my-sightings         → get_my_sightings()         [auth]
POST /api/registry/sighting-response    → respond_to_sighting()      [auth]
GET  /api/registry/status/<comic_id>    → get_registration_status()  [auth+approved]
```

### verify.py (3 routes, prefix=/api/verify)
```
GET/POST /api/verify/lookup/<serial_number>  → lookup_serial()       [public, Turnstile]
GET      /api/verify/watermark/<serial>      → get_watermarked_image()
POST     /api/verify/report-sighting         → report_sighting()     [public, rate-limited]
```

### monitor.py (6 routes, prefix=/api/monitor)
```
POST /api/monitor/check-image    → check marketplace image
POST /api/monitor/check-hash     → hash comparison
GET  /api/monitor/stolen-hashes  → stolen hash list
POST /api/monitor/report-match   → match reporting
POST /api/monitor/compare-copies → copy comparison
POST /api/monitor/capture-sale   → sale capture
```

### billing.py (7 routes, prefix=/api/billing)
```
GET  /api/billing/plans             → get_plans()                [public]
GET  /api/billing/my-plan           → get_my_plan()              [auth]
POST /api/billing/check-feature     → check_feature()            [auth]
POST /api/billing/create-checkout   → create_checkout_session()  [auth]
POST /api/billing/customer-portal   → create_customer_portal()   [auth]
POST /api/billing/webhook           → stripe_webhook()           [Stripe]
POST /api/billing/record-valuation  → record_valuation()         [auth]
```

### vision.py (1 route, prefix=/api/vision)
```
POST /api/vision/analyze  → analyze_vision()  [auth+approved, rate-limited]
```

### contact.py (1 route, prefix=/api)
```
POST /api/contact  → submit_contact()  [public, Turnstile+rate-limited]
```

### waitlist.py (3 routes, prefix=/api)
```
POST /api/waitlist          → subscribe()  [public, rate-limited]
GET  /api/waitlist/verify   → verify()     [public, token-based]
GET  /api/waitlist/count    → count()      [public]
```

### signatures.py (4 routes, prefix=/api/signatures)
```
POST /api/signatures/match             → api_match_signature()    [auth+approved]
GET  /api/signatures/db-stats          → api_db_stats()
GET  /api/signatures/signed-sales      → api_signed_sales()
GET  /api/signatures/premium-analysis  → api_premium_analysis()
```

---

## By Feature Area

```
Authentication & Users
├── auth_routes.py      (7 routes)
├── admin_routes.py     (20 routes)
└── waitlist.py         (3 routes)

Core Grading & Vision
├── grading.py          (5 routes)
├── vision.py           (1 route)
└── images.py           (7 routes)

Sales & Market Data
├── sales_ebay.py       (3 routes)
├── sales_market.py     (3 routes)
└── sales_valuation.py  (2 routes)

eBay Integration
└── ebay.py             (7 routes)

Collection & Selling
└── collection.py       (4 routes)

Slab Guard (Theft Recovery)
├── registry.py         (4 routes)
├── verify.py           (3 routes)
└── monitor.py          (6 routes)

Signatures
└── signatures.py       (4 routes)

Billing
└── billing.py          (7 routes)

Utilities
├── utils.py            (5 routes)
├── barcodes.py         (2 routes)
└── contact.py          (1 route)
```

---

## Stats

```
Total Routes:     87
Total Blueprints: 19 (18 registered in wsgi.py + utils)
Auth Patterns:
  - Public:           15 routes
  - Auth only:         8 routes
  - Auth + Approved:  42 routes
  - Admin only:       20 routes
  - Turnstile/token:   2 routes
```

---

## Critical Endpoints (Don't Delete!)

| Endpoint | Purpose | Required By |
|----------|---------|-------------|
| `/api/ebay/account-deletion` | GDPR compliance | eBay (they poll this) |
| `/api/sales/record` | Whatnot extension writes | Chrome extension |
| `/api/sales/recent` | Whatnot extension reads | Chrome extension |
| `/api/ebay-sales/batch` | eBay collector writes | Chrome extension |
| `/api/monitor/*` | Slab Guard monitoring | Slab Guard extension |
| `/api/billing/webhook` | Stripe payment events | Stripe |
| `/health` or `/` | Health check | Render |

---

## Route Dependencies

### Requires Anthropic API:
- `/api/valuate`, `/api/extract`, `/api/messages`, `/api/grade`
- `/api/ebay/generate-description`
- `/api/vision/analyze`
- `/api/admin/nlq`

### Requires R2 Storage:
- `/api/images/*`
- `/api/sales/record` (image uploads)
- `/api/admin/signatures/*/images`

### Requires Barcode Scanning (Docker):
- `/api/barcode-test`, `/api/barcode-scan`
- `/api/admin/backfill-barcodes`

### Requires eBay OAuth:
- `/api/ebay/auth`, `/api/ebay/callback`
- `/api/ebay/list`, `/api/ebay/upload-image`

### Requires Stripe:
- `/api/billing/create-checkout`, `/api/billing/customer-portal`
- `/api/billing/webhook`

### Requires Content Moderation (AWS):
- `/api/extract`, `/api/images/submission`, `/api/messages` (optional)
