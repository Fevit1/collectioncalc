# CollectionCalc Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER BROWSER                                   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Frontend (Cloudflare Pages)                   │   │
│  │                       collectioncalc.com                         │   │
│  │                                                                   │   │
│  │  ┌─────────────────────────────────────────────────────────┐    │   │
│  │  │  index.html  │  styles.css  │  app.js                   │    │   │
│  │  │  (310 lines) │  (1350 lines)│  (2030 lines)             │    │   │
│  │  └─────────────────────────────────────────────────────────┘    │   │
│  │                                                                   │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │   │
│  │  │  Manual   │  │   Photo   │  │ Valuation │  │   eBay    │    │   │
│  │  │   Entry   │  │  Upload   │  │  Results  │  │  Listing  │    │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │   │
│  │                                                                   │   │
│  │  ┌───────────┐  ┌───────────┐                                   │   │
│  │  │   Auth    │  │ Collection│                                   │   │
│  │  │  Login    │  │   View    │                                   │   │
│  │  └───────────┘  └───────────┘                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              Whatnot Valuator (Chrome Extension)                 │   │
│  │                     v2.40.1 - Live Auctions                      │   │
│  │                                                                   │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │   │
│  │  │  Apollo   │  │  Claude   │  │   Key     │  │   Sale    │    │   │
│  │  │  Reader   │  │  Vision   │  │ Database  │  │  Tracker  │    │   │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Backend (Render.com)                                 │
│                   collectioncalc.onrender.com                           │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Flask API (wsgi.py v3.8)                    │   │
│  │                                                                   │   │
│  │  VALUATION                                                        │   │
│  │  /api/valuate          - Get comic valuation (3 tiers)           │   │
│  │  /api/lookup           - Database lookup                         │   │
│  │  /api/messages         - Anthropic proxy (frontend extraction)   │   │
│  │                                                                   │   │
│  │  QUICKLIST (Batch Processing)                                    │   │
│  │  /api/extract          - Extract single comic from photo         │   │
│  │  /api/batch/process    - Extract + Valuate + Describe (batch)    │   │
│  │  /api/batch/list       - Upload images + Create drafts (batch)   │   │
│  │                                                                   │   │
│  │  MARKET SALES (Whatnot Integration) 🆕                           │   │
│  │  /api/sales/record     - Record sale from extension              │   │
│  │  /api/sales/count      - Get total sales count                   │   │
│  │  /api/sales/recent     - Get recent sales                        │   │
│  │                                                                   │   │
│  │  EBAY INTEGRATION                                                 │   │
│  │  /api/ebay/auth        - Start OAuth flow                        │   │
│  │  /api/ebay/callback    - OAuth callback                          │   │
│  │  /api/ebay/status      - Check connection                        │   │
│  │  /api/ebay/list        - Create listing (draft or live)          │   │
│  │  /api/ebay/upload-image - Upload to eBay Picture Services        │   │
│  │  /api/ebay/generate-description - AI description                 │   │
│  │  /api/ebay/disconnect  - Remove eBay connection                  │   │
│  │                                                                   │   │
│  │  USER AUTH                                                        │   │
│  │  /api/auth/signup      - Create new account                      │   │
│  │  /api/auth/login       - Authenticate, return JWT                │   │
│  │  /api/auth/verify/:id  - Verify email address                    │   │
│  │  /api/auth/forgot-password - Send reset email                    │   │
│  │  /api/auth/reset-password  - Reset with token                    │   │
│  │  /api/auth/me          - Get current user                        │   │
│  │                                                                   │   │
│  │  COLLECTIONS                                                      │   │
│  │  /api/collection       - Get user's saved comics                 │   │
│  │  /api/collection/save  - Save comics to collection               │   │
│  │  /api/collection/:id   - Update/delete collection item           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│       ┌────────────────────────────┼────────────────────────────┐      │
│       │                            │                            │       │
│       ▼                            ▼                            ▼       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │  ebay_     │  │  ebay_     │  │  ebay_     │  │  comic_    │       │
│  │ valuation  │  │  oauth     │  │  listing   │  │ extraction │       │
│  │   .py      │  │   .py      │  │   .py      │  │   .py      │       │
│  │            │  │            │  │            │  │            │       │
│  │ - Search   │  │ - OAuth    │  │ - Inventory│  │ - Claude   │       │
│  │ - Parse    │  │ - Tokens   │  │ - Offers   │  │   vision   │       │
│  │ - Calculate│  │ - Refresh  │  │ - Publish  │  │ - Extract  │       │
│  │ - Cache    │  │ - Store    │  │ - Images   │  │   info     │       │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘       │
│       │                                                │               │
│       │               ┌────────────┐                   │               │
│       │               │   auth.py  │                   │               │
│       │               │            │                   │               │
│       │               │ - Signup   │                   │               │
│       │               │ - Login    │                   │               │
│       │               │ - JWT      │                   │               │
│       │               │ - Password │                   │               │
│       │               │   reset    │                   │               │
│       │               └────────────┘                   │               │
│       │                     │                          │               │
│       └─────────────────────┼──────────────────────────┘              │
│                             │                                          │
│                             ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    PostgreSQL Database                           │   │
│  │                   (Render Managed)                               │   │
│  │                                                                   │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │ search_cache│  │ ebay_tokens │  │   users     │              │   │
│  │  │             │  │             │  │             │              │   │
│  │  │ - prices    │  │ - user_id   │  │ - email     │              │   │
│  │  │ - timestamp │  │ - access    │  │ - password  │              │   │
│  │  │ - samples   │  │ - refresh   │  │ - verified  │              │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │   │
│  │                                                                   │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │ collections │  │ password_   │  │market_sales │ 🆕          │   │
│  │  │             │  │ resets      │  │             │              │   │
│  │  │ - user_id   │  │             │  │ - source    │              │   │
│  │  │ - comic data│  │ - token     │  │ - price     │              │   │
│  │  │ - created   │  │ - expires   │  │ - sold_at   │              │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                    │                               │
                    │                               │
                    ▼                               ▼
         ┌───────────────────┐           ┌───────────────────┐
         │   Anthropic API   │           │     eBay API      │
         │                   │           │                   │
         │ - Claude Sonnet   │           │ - Browse API      │
         │ - Web search      │           │ - Inventory API   │
         │ - Photo analysis  │           │ - Account API     │
         │ - Descriptions    │           │ - OAuth           │
         └───────────────────┘           │ - Picture Services│
                                         └───────────────────┘
                    │
                    ▼
         ┌───────────────────┐
         │   Resend API      │
         │                   │
         │ - Email verify    │
         │ - Password reset  │
         └───────────────────┘
```

---

## Whatnot Valuator (Chrome Extension)

**Purpose:** Real-time comic valuation during live Whatnot auctions + market data acquisition.

The Whatnot Valuator extension serves two critical functions:
1. **User Value:** Shows FMV during live auctions so users know what to bid
2. **Data Acquisition:** Captures actual sale prices (unique competitive moat)

### Extension Architecture

```
whatnot-valuator/
├── manifest.json          # v2.40.1, MV3 extension config
├── content.js             # Main overlay, auction monitoring, sale capture
├── background.js          # Service worker, badge updates
├── inject.js              # Apollo GraphQL cache reader (injected)
├── styles.css             # Overlay styling
├── popup.html/js          # Extension popup with stats
├── lib/
│   ├── apollo-reader.js   # Reads Whatnot's Apollo cache for listing data
│   ├── normalizer.js      # Parses comic titles → series/issue/grade
│   ├── valuator.js        # Static FMV database (deprecated, kept for reference)
│   ├── sale-tracker.js    # Local sale storage
│   ├── collectioncalc.js  # CollectionCalc API client
│   ├── vision.js          # Claude Vision API for comic scanning
│   └── audio.js           # Audio transcription (built but hidden)
└── data/
    └── keys.js            # Key issue database (500+ keys) + lookupKeyInfo()
```

### Data Flow: Whatnot → CollectionCalc

```
┌──────────────────────────────────────────────────────────────────┐
│                    WHATNOT LIVE AUCTION                          │
│                                                                   │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐   │
│  │  Apollo Cache │───▶│ Content Script│───▶│  Sale Tracker │   │
│  │  (Listing ID, │    │ (Monitors DOM │    │ (Debounce,    │   │
│  │   Title, Bids)│    │  for "Sold")  │    │  Validation)  │   │
│  └───────────────┘    └───────────────┘    └───────────────┘   │
│                              │                      │            │
│                              ▼                      │            │
│                    ┌───────────────┐               │            │
│                    │ Claude Vision │               │            │
│                    │ (Auto-scan    │               │            │
│                    │  comic cover) │               │            │
│                    └───────────────┘               │            │
│                              │                      │            │
│                              └──────────────────────┘            │
│                                        │                         │
└────────────────────────────────────────│─────────────────────────┘
                                         │
                                         ▼
                          POST /api/sales/record
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    COLLECTIONCALC DATABASE                       │
│                                                                  │
│  market_sales (618+ records as of Jan 25, 2026)                 │
│  ┌──────────┬────────┬───────┬───────┬───────────┬───────────┐ │
│  │ source   │ title  │ issue │ grade │   price   │  sold_at  │ │
│  ├──────────┼────────┼───────┼───────┼───────────┼───────────┤ │
│  │ whatnot  │ ASM    │ 300   │ 9.4   │   $485    │ 2026-01-25│ │
│  │ whatnot  │ Batman │ 1     │ raw   │   $140    │ 2026-01-24│ │
│  │ ebay_auc │ X-Men  │ 1     │ 8.0   │  $1,200   │ 2026-01-20│ │
│  └──────────┴────────┴───────┴───────┴───────────┴───────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture (3-File Split)

As of Session 7, the frontend is split into 3 files for maintainability:

| File | Lines | Purpose |
|------|-------|---------|
| `index.html` | ~310 | HTML structure only |
| `styles.css` | ~1350 | All CSS styling |
| `app.js` | ~2030 | All JavaScript logic |

**Benefits:**
- Easier to edit (no truncation issues)
- Browser caching (CSS/JS cached separately)
- Standard web practice

**Image Processing (app.js):**
- EXIF orientation detection (auto-rotate photos)
- Upscales small images to 1200px minimum
- Downscales large images to 2400px max
- Quality: 60-95% JPEG
- Manual rotate button (↻) for edge cases

---

## Data Flow: QuickList (Batch Processing)

**QuickList** is the full pipeline from photo upload to eBay draft listing.

```
User uploads photos of comics (1-20)
                │
                ▼
┌───────────────────────────────────┐
│ /api/batch/process                │
│ (Extract + Valuate + Describe)    │
└───────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│ Comic Extraction (Claude Vision)  │
│ - Title, Issue, Grade             │
│ - Publisher, Year                 │
│ - Newsstand/Direct                │
│ - Variant detection               │
│ - Signature detection             │
└───────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│ User Reviews/Edits Extraction     │
│ (Can correct AI mistakes)         │
└───────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│ Valuation (eBay + Whatnot data)   │
│ - Quick Sale                      │
│ - Fair Value (default)            │
│ - High End                        │
└───────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│ AI Description Generation         │
│ (300 char, mobile-optimized)      │
└───────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│ /api/batch/list                   │
│ - Upload images to eBay           │
│ - Create draft listings           │
└───────────────────────────────────┘
                │
                ▼
        User reviews drafts
        in eBay Seller Hub
        and publishes when ready
```

---

## Data Flow: Unified FMV Engine (Planned)

Future architecture combining multiple data sources:

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                                │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Whatnot   │  │    eBay     │  │PriceCharting│             │
│  │   (Live)    │  │ (Completed) │  │ (Aggregated)│             │
│  │             │  │             │  │             │             │
│  │  618+ sales │  │ Web search  │  │   Future    │             │
│  │  Real-time  │  │ 48hr cache  │  │   $200/mo   │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┴────────────────┘                     │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 UNIFIED FMV ENGINE                       │   │
│  │                                                          │   │
│  │  1. Source Weighting                                     │   │
│  │     - Whatnot: 1.0x (real auction, true price discovery) │   │
│  │     - eBay Auction: 0.9x (competitive bidding)           │   │
│  │     - eBay BIN: 0.7x (asking price, not sold)            │   │
│  │                                                          │   │
│  │  2. Recency Weighting                                    │   │
│  │     - This week: 100%                                    │   │
│  │     - 1-2 weeks: 85%                                     │   │
│  │     - 2-4 weeks: 70%                                     │   │
│  │     - 1-2 months: 50%                                    │   │
│  │     - 2-3 months: 30%                                    │   │
│  │                                                          │   │
│  │  3. Grade Matching                                       │   │
│  │     - Exact grade: 100%                                  │   │
│  │     - ±0.5 grade: 80%                                    │   │
│  │     - ±1.0 grade: 50%                                    │   │
│  │                                                          │   │
│  │  4. Confidence Scoring                                   │   │
│  │     - 5+ recent sales = High                             │   │
│  │     - 3-4 sales = Medium                                 │   │
│  │     - 1-2 sales = Low                                    │   │
│  │     - 0 sales = No data                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    OUTPUT                                │   │
│  │                                                          │   │
│  │  GET /api/fmv?title=Amazing+Spider-Man&issue=300&grade=9.4 │
│  │                                                          │   │
│  │  {                                                       │   │
│  │    "quick_sale": 420,                                    │   │
│  │    "fair_value": 485,                                    │   │
│  │    "high_end": 550,                                      │   │
│  │    "confidence": "high",                                 │   │
│  │    "sources": {                                          │   │
│  │      "whatnot": 3,                                       │   │
│  │      "ebay": 8                                           │   │
│  │    }                                                     │   │
│  │  }                                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints Summary

### Valuation
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/valuate` | POST | Get three-tier valuation |
| `/api/lookup` | GET | Database lookup (no AI) |
| `/api/messages` | POST | Anthropic proxy for frontend |

### QuickList (Batch)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/extract` | POST | Extract single comic from photo |
| `/api/batch/process` | POST | Extract + Valuate + Describe (batch) |
| `/api/batch/list` | POST | Upload images + Create drafts |

### Market Sales (Whatnot Integration) 🆕
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sales/record` | POST | Record sale from extension |
| `/api/sales/count` | GET | Get total sales count |
| `/api/sales/recent` | GET | Get recent sales |

### eBay
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ebay/auth` | GET | Start OAuth flow |
| `/api/ebay/callback` | GET | OAuth callback |
| `/api/ebay/status` | GET | Check connection |
| `/api/ebay/list` | POST | Create listing (draft/live) |
| `/api/ebay/upload-image` | POST | Upload to Picture Services |
| `/api/ebay/generate-description` | POST | AI description |
| `/api/ebay/disconnect` | POST | Remove eBay connection |

### User Auth
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/signup` | POST | Create new account |
| `/api/auth/login` | POST | Authenticate, return JWT |
| `/api/auth/verify/<token>` | GET | Verify email address |
| `/api/auth/forgot-password` | POST | Send reset email |
| `/api/auth/reset-password` | POST | Reset with token |
| `/api/auth/me` | GET | Get current user (requires JWT) |

### Collections
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/collection` | GET | Get user's saved comics |
| `/api/collection/save` | POST | Save comics to collection |
| `/api/collection/<id>` | PUT/DELETE | Update/delete collection item |

### Input Validation (Batch Endpoints)
- Max 20 comics per batch
- Max 10MB per image
- Supported formats: JPEG, PNG, WebP, HEIC

---

## Database Schema

### search_cache
Stores eBay valuation results for 48-hour caching.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| search_key | VARCHAR | "{title}\|{issue}" normalized |
| estimated_value | DECIMAL | Fair value (median) |
| quick_sale_value | DECIMAL | Quick sale price |
| high_end_value | DECIMAL | High end price |
| confidence | DECIMAL | 0.0 - 1.0 |
| sample_count | INTEGER | Number of sales found |
| samples | JSONB | Raw sale data |
| cached_at | TIMESTAMP | When cached |

### market_sales 🆕
Stores actual sales from all sources (Whatnot, eBay, etc.).

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| source | TEXT | 'whatnot', 'ebay_auction', 'ebay_bin' |
| title | TEXT | Comic title |
| series | TEXT | Series name |
| issue | TEXT | Issue number (TEXT for "1A" variants) |
| grade | NUMERIC | Numeric grade (9.8, 9.4, etc.) |
| grade_source | TEXT | 'cgc', 'cbcs', 'raw', 'vision' |
| slab_type | TEXT | 'CGC', 'CBCS', 'PGX', 'raw' |
| variant | TEXT | 'newsstand', '35¢ price variant', etc. |
| is_key | BOOLEAN | Is this a key issue? |
| price | NUMERIC | Sale price |
| sold_at | TIMESTAMPTZ | When sold |
| created_at | TIMESTAMPTZ | When recorded |
| raw_title | TEXT | Original title from source |
| seller | TEXT | Seller username |
| bids | INTEGER | Number of bids (Whatnot) |
| viewers | INTEGER | Viewer count (Whatnot) |
| image_url | TEXT | Image of the comic |
| source_id | TEXT | External ID for deduplication |

**Indexes:**
- `idx_market_sales_lookup ON (series, issue, grade)` - FMV queries
- `idx_market_sales_recency ON (sold_at DESC)` - Recent sales
- `idx_market_sales_source ON (source)` - Filter by source

**Current Data:** 618+ records (migrated from Supabase Jan 25, 2026)

### ebay_tokens
Stores OAuth tokens for eBay API access.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| user_id | VARCHAR | User identifier |
| access_token | TEXT | eBay access token |
| refresh_token | TEXT | eBay refresh token |
| expires_at | TIMESTAMP | Token expiration |
| created_at | TIMESTAMP | When created |
| updated_at | TIMESTAMP | Last updated |

### users
Stores user accounts.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| email | VARCHAR | User email (unique) |
| password_hash | VARCHAR | Bcrypt hash |
| email_verified | BOOLEAN | Email confirmed? |
| verification_token | VARCHAR | Email verify token |
| created_at | TIMESTAMP | When created |

### collections
Stores saved comics.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| user_id | INTEGER | FK to users |
| comic_data | JSONB | Full comic data |
| created_at | TIMESTAMP | When saved |
| updated_at | TIMESTAMP | Last modified |

### password_resets
Stores password reset tokens.

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| user_id | INTEGER | FK to users |
| token | VARCHAR | Reset token |
| expires_at | TIMESTAMP | Token expiration |
| used | BOOLEAN | Already used? |
| created_at | TIMESTAMP | When created |

---

## Database Connection

### Production (Render PostgreSQL)
| Field | Value |
|-------|-------|
| Host | `dpg-d5knv4koud1c73dt21pg-a.oregon-postgres.render.com` |
| Port | `5432` |
| Database | `collectioncalc_db` |
| Username | `collectioncalc_db_user` |
| Password | (stored in Render dashboard) |

### DBeaver Setup
- Use **Main** connection tab (not URL)
- Enter individual fields
- SSL required
- Test connection before saving

---

## External Services

### Anthropic API
- **Standard Model:** Claude Sonnet 4 (`claude-sonnet-4-20250514`)
- **Premium Model:** Claude Opus 4.5 (`claude-opus-4-5-20251101`) - commented out, ready for Premium tier
- **Tier:** 2 (450k tokens/min)
- **Uses:**
  - Web search for eBay prices
  - Photo analysis (comic extraction)
  - Description generation
  - Signature analysis
  - Whatnot Vision scanning

**Model Comparison (tested Session 7):**
| Capability | Sonnet | Opus |
|------------|--------|------|
| Cost | ~$0.01/comic | ~$0.05/comic |
| Basic extraction | ✅ | ✅ |
| Subtle signature detection | ❌ | ✅ (detects existence, not WHO) |

### eBay API
- **Environment:** Production
- **APIs Used:**
  - Browse API (searching)
  - Inventory API (listings, offers)
  - Account API (policies, locations)
  - OAuth (authentication)
  - Picture Services (image upload)
- **Key Settings:**
  - Category: 259104 (Comics & Graphic Novels)
  - Condition enums: LIKE_NEW, USED_EXCELLENT, etc.
  - Package: 1"×11"×7", 8oz, LETTER
  - Default: Draft mode (publish=false)

### Resend API
- **Domain:** collectioncalc.com
- **Uses:**
  - Email verification
  - Password reset emails

---

## Security Considerations

1. **API Keys:** Stored as environment variables in Render
2. **eBay Tokens:** Encrypted at rest in PostgreSQL
3. **User Passwords:** Bcrypt hashed
4. **JWT Tokens:** 30-day expiry, signed with secret
5. **CORS:** Configured for frontend domain only
6. **OAuth State:** Random state parameter prevents CSRF
7. **Input Validation:** Max image size (10MB), max batch size (20)

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| DATABASE_URL | PostgreSQL connection string |
| ANTHROPIC_API_KEY | Claude API key |
| EBAY_CLIENT_ID | eBay app ID (production) |
| EBAY_CLIENT_SECRET | eBay cert ID (production) |
| EBAY_RUNAME | eBay redirect URL name |
| EBAY_DEV_ID | eBay developer ID |
| EBAY_SANDBOX | "false" for production |
| RESEND_API_KEY | Email service API key |
| RESEND_FROM_EMAIL | noreply@collectioncalc.com |
| JWT_SECRET | Auth token signing key |
| FRONTEND_URL | https://collectioncalc.com |

---

## Key Files

### Frontend (Cloudflare Pages)
| File | Purpose |
|------|---------|
| `index.html` | HTML structure (~310 lines) |
| `styles.css` | All CSS (~1350 lines) |
| `app.js` | All JavaScript (~2030 lines) |

### Backend (Render)
| File | Purpose |
|------|---------|
| `wsgi.py` | Flask routes (v3.8) |
| `ebay_valuation.py` | Valuation logic, caching |
| `ebay_oauth.py` | eBay OAuth flow |
| `ebay_listing.py` | Listing creation, image upload |
| `ebay_description.py` | AI description generation |
| `comic_extraction.py` | Backend extraction via Claude vision |
| `auth.py` | User auth (signup, login, JWT, password reset) |

### Whatnot Valuator (Chrome Extension)
| File | Purpose |
|------|---------|
| `manifest.json` | Extension config (v2.40.1) |
| `content.js` | Main overlay, sale detection |
| `lib/collectioncalc.js` | API client for sales |
| `lib/vision.js` | Claude Vision scanning |
| `data/keys.js` | 500+ key issue database |

---

*Last updated: January 25, 2026 (Session 8 - Whatnot integration, market_sales table, unified FMV architecture)*
