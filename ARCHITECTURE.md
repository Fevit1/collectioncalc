# CollectionCalc / Slab Worthy Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            USER INTERFACES                                   │
├─────────────────┬─────────────────┬──────────────────┬──────────────────────┤
│  CollectionCalc │  Slab Worthy?   │ Whatnot Extension│  eBay Collector      │
│  Web App        │  (Same app)     │ Chrome Extension │  Chrome Extension    │
│  - Valuations   │  - 4-photo      │ - Live auction   │  - Passive scraping  │
│  - eBay listing │    grading      │   overlay        │  - Sold listings     │
│  - Collection   │  - Grade report │ - Auto-scan      │  - R2 image backup   │
│                 │  - ROI calc     │ - Sale capture   │  - Local + cloud     │
└────────┬────────┴────────┬────────┴────────┬─────────┴──────────┬───────────┘
         │                 │                 │                    │
         │    HTTPS/REST   │                 │                    │
         ▼                 ▼                 ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COLLECTIONCALC API                                   │
│                   (collectioncalc-docker.onrender.com)                       │
│                         🐳 DOCKER DEPLOYMENT                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  /api/valuate        - Three-tier comic valuation                            │
│  /api/messages       - Anthropic proxy (frontend extraction)                 │
│  /api/extract        - Backend photo extraction + barcode scanning           │
│  /api/barcode-test   - Verify pyzbar/libzbar0 loaded (NEW)                  │
│  /api/barcode-scan   - Direct barcode scanning endpoint (NEW)               │
│  /api/batch/*        - QuickList bulk processing                             │
│  /api/sales/*        - Market data recording/retrieval                       │
│  /api/ebay/*         - eBay OAuth + listing                                 │
│  /api/ebay-sales/*   - eBay Collector data ingestion                        │
│  /api/auth/*         - User authentication                                  │
│  /api/collection     - User collection CRUD                                 │
│  /api/admin/*        - Admin functions, NLQ                                 │
│  /api/images/*       - R2 image upload                                      │
└────────┬────────────────────┬───────────────────────┬───────────────────────┘
         │                    │                       │
         ▼                    ▼                       ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐
│   PostgreSQL    │  │  Anthropic API  │  │    External Services    │
│   (Render)      │  │  Claude Vision  │  ├─────────────────────────┤
├─────────────────┤  │  + Messages     │  │  eBay API (listings)    │
│ users           │  └─────────────────┘  │  Cloudflare R2 (images) │
│ collections     │                       │  Resend (email)         │
│ market_sales    │  ┌─────────────────┐  │  eBay Browse API (data) │
│ ebay_sales      │  │  pyzbar/libzbar │  └─────────────────────────┘
│ search_cache    │  │  Barcode Scan   │
│ creator_sigs    │  │  (Docker only)  │
│ beta_codes      │  └─────────────────┘
│ ebay_tokens     │
└─────────────────┘
```

## Docker Deployment

**Why Docker:** Barcode scanning requires `pyzbar` Python library which depends on `libzbar0` system library. Render's native Python environment cannot install system packages. Docker solves this.

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y libzbar0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "wsgi:app", "--timeout", "300", "--bind", "0.0.0.0:10000"]
```

**Render Services:**
| Service | Type | Status | Purpose |
|---------|------|--------|---------|
| `collectioncalc-docker` | Docker | **ACTIVE** | Production backend with barcode scanning |
| `collectioncalc` | Python | SUSPENDED | Legacy (saved $7/mo) |

## File Structure

```
cc/v2/
├── ─────────── FRONTEND (Cloudflare Pages) ───────────
├── index.html           # Beta landing page
├── app.html             # Main application (with Slab Worthy tab)
├── admin.html           # Admin dashboard
├── signatures.html      # Signature reference admin
├── styles.css           # All CSS (+ grading styles appended)
│
├── js/                  # JavaScript modules (split for maintainability)
│   ├── utils.js         # Shared state, constants, API_URL → Docker backend
│   ├── auth.js          # Authentication, user menu, collection functions
│   ├── app.js           # Core app: eBay, photo upload, valuation, manual entry
│   └── grading.js       # Slab Worthy: 4-photo flow, grade report, ROI calc
│
├── ─────────── BACKEND (Render Docker) ───────────
├── Dockerfile           # Docker config with libzbar0
├── wsgi.py              # Flask app, all routes, barcode endpoints
├── auth.py              # Authentication (JWT, signup, login, reset)
├── admin.py             # Admin functions, NLQ
├── ebay_valuation.py    # Valuation logic, caching
├── ebay_oauth.py        # eBay OAuth flow
├── ebay_listing.py      # eBay Inventory API
├── ebay_description.py  # AI description generation
├── comic_extraction.py  # Backend Claude Vision extraction + barcode scanning
├── r2_storage.py        # Cloudflare R2 integration
├── requirements.txt     # Python dependencies (includes pyzbar)
│
├── ─────────── CHROME EXTENSIONS ───────────
├── whatnot-valuator/    # Whatnot live stream valuations (v2.41.2)
│   ├── manifest.json    # Extension config
│   ├── content.js       # Main overlay, auction monitoring
│   ├── lib/
│   │   ├── collectioncalc.js  # API client
│   │   └── vision.js          # Claude Vision (facsimile detection)
│   └── data/
│       └── keys.js      # 500+ key issue database
│
├── ebay-collector/      # eBay sold listings collector (v1.0.3)
│   ├── manifest.json    # Extension config
│   ├── content.js       # Page scraping, sale parsing
│   ├── popup.html       # Stats popup UI
│   ├── popup.js         # Sync button, stats display
│   └── icons/           # Extension icons
│
└── ─────────── DOCUMENTATION ───────────
    ├── CLAUDE_NOTES.txt # Session notes, context for Claude
    ├── ROADMAP.md       # Feature backlog, version history
    ├── BRAND_GUIDELINES.md  # Colors, typography, UI standards
    └── ARCHITECTURE.md  # This file
```

## Barcode Scanning Flow (NEW)

```
┌─────────────────────────────────────────────────────────────────┐
│                    BARCODE SCANNING FLOW                         │
│                    (Requires Docker)                             │
└─────────────────────────────────────────────────────────────────┘

User uploads comic photo
      │
      ▼
┌─────────────────────┐
│ /api/extract        │
│ comic_extraction.py │
└──────────┬──────────┘
           │
           ├─► scan_barcode() called first
           │
           ▼
┌─────────────────────┐
│ pyzbar.decode()     │
│ Try rotations:      │
│ 0°, 90°, 180°, 270° │
└──────────┬──────────┘
           │
           ├─► Found? Extract UPC data
           │   - upc_main (12 digits)
           │   - upc_addon (5 digits, if present)
           │   - rotation detected
           │
           ▼
┌─────────────────────┐
│ Claude Vision       │
│ Extract metadata:   │
│ - Title, Issue      │
│ - Publisher, Year   │
│ - Grade, Defects    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MERGED RESULT                                 │
├─────────────────────────────────────────────────────────────────┤
│  {                                                               │
│    "title": "Amethyst Princess of Gemworld",                    │
│    "issue": "1",                                                 │
│    "upc_main": "070989311176",                                  │
│    "barcode_scanned": {                                         │
│      "type": "UPCA",                                            │
│      "upc_main": "070989311176",                                │
│      "upc_addon": null,                                         │
│      "rotation": 0                                               │
│    }                                                             │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Comic Barcode Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    UPC BARCODE FORMAT                            │
└─────────────────────────────────────────────────────────────────┘

Main UPC (12 digits)          5-Digit Addon (EAN-5)
┌────────────────────┐        ┌─────────────────┐
│  0 70989 31117 6   │        │     0 0 1 1 1   │
│  └─────┬─────┘     │        │     └─┬─┘└┬┘└┬┘ │
│        │           │        │       │   │  │  │
│  Series Identifier │        │   Issue  Cover Print
│  (same for all     │        │   001=1  1=A  1=1st
│   issues of title) │        │   002=2  2=B  2=2nd
└────────────────────┘        │   003=3  3=C  3=3rd
                              └─────────────────┘

Examples:
- 00111 = Issue #1, Cover A, 1st printing (ORIGINAL)
- 00112 = Issue #1, Cover A, 2nd printing (REPRINT!)
- 00121 = Issue #1, Cover B, 1st printing (VARIANT)
- 00211 = Issue #2, Cover A, 1st printing
```

**Why This Matters:**
- Spawn #1 first print: ~$300
- Spawn #1 second print: ~$25
- Without barcode detection, we can't tell them apart!

## JavaScript Module Dependencies

```
┌─────────────┐
│  app.html   │
└─────┬───────┘
      │ loads (in order)
      ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  utils.js   │────▶│  auth.js    │────▶│  app.js     │────▶│ grading.js  │
│             │     │             │     │             │     │             │
│ - Constants │     │ - JWT       │     │ - eBay mode │     │ - Slab      │
│ - State     │     │ - Login     │     │ - Photo     │     │   Worthy    │
│ - API_URL   │     │ - User menu │     │ - Manual    │     │ - 4 photos  │
│   (Docker)  │     │ - Collection│     │ - Valuation │     │ - Report    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
      ▲                   ▲                   ▲                   ▲
      │                   │                   │                   │
      └───────────────────┴───────────────────┴───────────────────┘
                    All modules share window.state
```

**API_URL Configuration:**
```javascript
// js/utils.js line 5
const API_URL = 'https://collectioncalc-docker.onrender.com';
```

## eBay Collector Extension

```
┌─────────────────────────────────────────────────────────────────┐
│                    eBay COLLECTOR FLOW                           │
└─────────────────────────────────────────────────────────────────┘

User browses eBay sold listings
      │
      ▼
┌─────────────────────┐
│ content.js triggers │ (on pages with LH_Sold=1)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Parse li.s-card     │ (eBay's 2026 HTML structure)
│ elements            │
└──────────┬──────────┘
           │
           ├─► Extract: title, price, date, condition
           ├─► Parse: issue #, publisher, grade (CGC/CBCS)
           ├─► Get: listing URL, image URL, eBay item ID
           │
           ▼
┌─────────────────────┐
│ Local Storage       │ (immediate, offline-capable)
│ + Show green toast  │ "📊 Collected X new sales"
└──────────┬──────────┘
           │
           ▼ (Sync Now button or auto)
┌─────────────────────┐
│ POST /api/ebay-     │
│ sales/batch         │
└──────────┬──────────┘
           │
           ├─► Insert to ebay_sales (dedupe by item ID)
           │
           ▼
┌─────────────────────┐
│ Parallel R2 Backup  │ (5 concurrent)
│ Download eBay image │
│ Upload to R2        │
│ Store r2_image_url  │
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ Response:           │
│ - saved: 61         │
│ - duplicates: 0     │
│ - images_backed_up: │
│   58                │
└─────────────────────┘
```

## Slab Worthy Grading Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SLAB WORTHY FLOW                              │
│                    (Patent Pending)                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────┐
│ Step 1: FRONT COVER │ ◄── REQUIRED
├─────────────────────┤
│ Barcode Scan │ → UPC detection (pyzbar)
│ Claude Vision:      │
│ Extract   │ → Title, Issue, Publisher, Year
│ Defects   │ → Cover condition assessment
└─────┬─────┘
      │
      ▼
┌─────────────────────┐
│ Step 2: SPINE       │ ◄── Recommended (skippable)
└──────────┬──────────┘
           │ → Spine roll, stress marks, splits
           │ → Auto-rotation check
           ▼
┌─────────────────────┐
│ Step 3: BACK COVER  │ ◄── Recommended (skippable)
└──────────┬──────────┘
           │ → Back defects, stains, labels
           │ → Auto-rotation check
           ▼
┌─────────────────────┐
│ Step 4: CENTERFOLD  │ ◄── Recommended (skippable)
└──────────┬──────────┘
           │ → Staples, interior, attachment
           │ → Auto-rotation check
           │
           │ (+ Optional additional photos)
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GRADE REPORT                                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐                                            │
│  │     8.5        │  ◄── Predicted Grade                        │
│  │   VF+          │                                             │
│  │  ████████░░    │  ◄── Confidence (scales with # of photos)   │
│  │   88%          │      1 photo: 65%  │  4 photos: 94%         │
│  └─────────────────┘                                            │
│                                                                 │
│  BARCODE: 070989311176 (1st printing detected)                  │
│                                                                 │
│  DEFECTS FOUND:                                                 │
│  ├─ Front: Corner wear (top right), light spine stress          │
│  ├─ Spine: Minor tick marks                                     │
│  ├─ Back: None                                                  │
│  └─ Interior: Slight staple rust                                │
│                                                                 │
│  💰 SHOULD YOU GRADE?                                           │
│  ├─ Raw Value:      $45.00                                      │
│  ├─ Slabbed Value:  $58.50 (est.)                              │
│  ├─ Grading Cost:   ~$30                                        │
│  ├─ Net Benefit:    -$16.50                                     │
│  │                                                              │
│  │  ┌──────────────────────────┐                               │
│  │  │   📦 KEEP RAW            │                               │
│  │  │   Grading cost exceeds   │                               │
│  │  │   likely value increase  │                               │
│  │  └──────────────────────────┘                               │
│  │                                                              │
│  └─ [Save to Collection] [Get Full Valuation]                   │
└─────────────────────────────────────────────────────────────────┘
```

## Valuation Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   REQUEST   │────▶│  CHECK      │────▶│  SEARCH     │
│  Title,     │     │  CACHE      │     │  eBay API   │
│  Issue,     │     │  (48hr TTL) │     │  + Market   │
│  Grade      │     │             │     │  Sales DB   │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                          │                    │
                    HIT   │              MISS  │
                          ▼                    ▼
                   ┌─────────────┐     ┌─────────────┐
                   │  RETURN     │     │  CALCULATE  │
                   │  CACHED     │     │  3 TIERS    │
                   │  RESULT     │     │  + Cache    │
                   └─────────────┘     └─────────────┘
                                              │
                                              ▼
                   ┌──────────────────────────────────────────┐
                   │           THREE-TIER VALUATION           │
                   ├──────────────────────────────────────────┤
                   │  Quick Sale:  $35-40   (floor/minimum)   │
                   │  Fair Value:  $50-55   (highlighted)     │
                   │  High End:    $70-80   (ceiling/max)     │
                   │                                          │
                   │  Confidence: 78%  ████████░░             │
                   │  Based on: 12 recent sales               │
                   └──────────────────────────────────────────┘
```

## Database Schema

```sql
-- Users & Auth
users (id, email, password_hash, is_verified, is_approved, is_admin, created_at)
beta_codes (id, code, max_uses, current_uses, created_by, created_at)

-- Collections
collections (id, user_id, title, issue, grade, purchase_price, notes, created_at)

-- Market Data
market_sales (id, title, issue, grade, price, platform, sold_date, created_at)
    -- PLANNED: upc_main, upc_addon, is_reprint columns
search_cache (id, cache_key, result_json, created_at)  -- 48hr TTL

-- eBay Collector Data
ebay_sales (
    id, 
    ebay_item_id,        -- Unique, used for deduplication
    raw_title,           -- Original eBay listing title
    parsed_title,        -- Cleaned title
    issue_number,        -- Extracted issue #
    publisher,           -- Marvel, DC, Image, etc.
    sale_price,          -- Final sale price
    sale_date,           -- When it sold
    condition,           -- e.g., "CGC 9.8"
    graded,              -- Boolean
    grade,               -- Numeric grade
    listing_url,         -- eBay listing URL
    image_url,           -- eBay image URL (may expire)
    r2_image_url,        -- Permanent R2 backup URL
    content_hash,        -- For deduplication
    created_at
    -- PLANNED: upc_main, upc_addon, is_reprint columns
)

-- View for Fair Market Value calculations
comic_fmv (view) - 90-day rolling FMV by title/issue

-- Signatures
creator_signatures (id, creator_name, signature_url, signature_type, notes)
signature_matches (id, user_id, comic_title, issue, matched_creator, confidence)

-- eBay Integration
ebay_tokens (id, user_id, access_token, refresh_token, expires_at)

-- Logging
request_logs (id, endpoint, method, user_id, ip_address, created_at)
api_usage (id, user_id, endpoint, tokens_used, created_at)
```

## External APIs

| Service | Purpose | Auth |
|---------|---------|------|
| Anthropic Claude | Vision extraction, valuations, descriptions | API Key |
| eBay Browse API | Market data, completed listings | OAuth |
| eBay Inventory API | Create draft listings | OAuth |
| Cloudflare R2 | Image storage (sales + eBay covers) | Access Key |
| Resend | Transactional email | API Key |

## R2 Storage Structure

```
collectioncalc-images/
├── sales/              # Whatnot sale images
│   └── {sale_id}/
│       └── front.jpg
├── submissions/        # B4Cert grading submissions  
│   └── {submission_id}/
│       ├── front.jpg
│       ├── back.jpg
│       ├── spine.jpg
│       └── centerfold.jpg
├── ebay-covers/        # eBay Collector images
│   └── {ebay_item_id}.webp
└── temp/               # Temporary uploads
```

## Security

- **JWT tokens** for user authentication (24hr expiry)
- **Beta codes** gate new signups
- **Admin approval** required for full access
- **CORS** restricted to collectioncalc.com + onrender.com
- **Rate limiting** on API endpoints
- **Passwords** hashed with bcrypt

## Deployment

| Component | Platform | Trigger |
|-----------|----------|---------|
| Frontend | Cloudflare Pages | Git push + `purge` command |
| Backend | Render.com Docker ($7/mo) | Git push + `deploy` command |
| Database | Render PostgreSQL | Managed |
| Images | Cloudflare R2 | API upload |

**Note:** Auto-deploy is DISABLED. Always run `deploy` command after pushing backend changes.

---

*Last updated: February 2, 2026*
*Patent Pending: Multi-angle comic grading system*
