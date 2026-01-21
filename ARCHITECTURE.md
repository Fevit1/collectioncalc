# CollectionCalc Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER BROWSER                                   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Frontend (Cloudflare Pages)                   │   │
│  │                   collectioncalc.pages.dev                       │   │
│  │                                                                   │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │   │
│  │  │  Manual   │  │   Photo   │  │ Valuation │  │   eBay    │    │   │
│  │  │   Entry   │  │  Upload   │  │  Results  │  │  Listing  │    │   │
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
│  │                      Flask API (wsgi.py v3.4)                    │   │
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
│  │  EBAY INTEGRATION                                                 │   │
│  │  /api/ebay/auth        - Start OAuth flow                        │   │
│  │  /api/ebay/callback    - OAuth callback                          │   │
│  │  /api/ebay/status      - Check connection                        │   │
│  │  /api/ebay/list        - Create listing (draft or live)          │   │
│  │  /api/ebay/upload-image - Upload to eBay Picture Services        │   │
│  │  /api/ebay/generate-description - AI description                 │   │
│  │  /api/ebay/disconnect  - Remove eBay connection                  │   │
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
│       │                   │              │              │               │
│       └───────────────────┼──────────────┼──────────────┘              │
│                           │              │                              │
│                           ▼              ▼                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    PostgreSQL Database                           │   │
│  │                   (Render Managed)                               │   │
│  │                                                                   │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │ search_cache│  │ ebay_tokens │  │  comics     │              │   │
│  │  │             │  │             │  │ (future)    │              │   │
│  │  │ - prices    │  │ - user_id   │  │             │              │   │
│  │  │ - timestamp │  │ - access    │  │             │              │   │
│  │  │ - samples   │  │ - refresh   │  │             │              │   │
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
```

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
    ┌───────────┴───────────┐
    │   For each comic:     │
    │                       │
    ▼                       │
┌─────────────────┐         │
│ Extract         │         │
│ (Claude Vision) │         │
│ - Title         │         │
│ - Issue #       │         │
│ - Grade         │         │
│ - Edition       │         │
│ - Publisher     │         │
│ - Year          │         │
└─────────────────┘         │
         │                  │
         ▼                  │
┌─────────────────┐         │
│ Valuate         │         │
│ (Cache or API)  │         │
│ - Quick Sale    │         │
│ - Fair Value    │         │
│ - High End      │         │
└─────────────────┘         │
         │                  │
         ▼                  │
┌─────────────────┐         │
│ Describe        │         │
│ (Claude)        │         │
│ - 300 char max  │         │
│ - Key issues    │         │
└─────────────────┘         │
         │                  │
         └──────────────────┘
                │
                ▼
        Return results to user
        (extraction, valuations, descriptions)
                │
                ▼
┌───────────────────────────────────┐
│ USER REVIEWS & APPROVES           │
│ - Edit grades, issue numbers      │
│ - Select price tier (Fair default)│
│ - Click "List on eBay"            │
└───────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│ /api/batch/list                   │
│ (Upload Images + Create Drafts)   │
└───────────────────────────────────┘
                │
    ┌───────────┴───────────┐
    │   For each comic:     │
    │                       │
    ▼                       │
┌─────────────────┐         │
│ Upload Image    │         │
│ (eBay Picture   │         │
│  Services)      │         │
└─────────────────┘         │
         │                  │
         ▼                  │
┌─────────────────┐         │
│ Create Listing  │         │
│ (Draft mode)    │         │
│ - Inventory item│         │
│ - Offer         │         │
│ - Skip publish  │         │
└─────────────────┘         │
         │                  │
         └──────────────────┘
                │
                ▼
        Return draft URLs
        (user publishes when ready)
```

---

## Data Flow: Single Valuation

```
User enters comic info
         │
         ▼
┌─────────────────┐
│ Check Cache     │──────────────────┐
│ (48hr valid)    │                  │ Cache HIT
└─────────────────┘                  │
         │ Cache MISS                │
         ▼                           │
┌─────────────────┐                  │
│ Anthropic API   │                  │
│ Web Search      │                  │
│ (eBay prices)   │                  │
└─────────────────┘                  │
         │                           │
         ▼                           │
┌─────────────────┐                  │
│ Parse & Weight  │                  │
│ - Recency       │                  │
│ - Volume        │                  │
│ - Variance      │                  │
└─────────────────┘                  │
         │                           │
         ▼                           │
┌─────────────────┐                  │
│ Calculate Tiers │                  │
│ - Quick Sale    │                  │
│ - Fair Value    │                  │
│ - High End      │                  │
└─────────────────┘                  │
         │                           │
         ▼                           │
┌─────────────────┐                  │
│ Save to Cache   │                  │
└─────────────────┘                  │
         │                           │
         └───────────┬───────────────┘
                     │
                     ▼
            Return valuation
            to frontend
```

---

## Data Flow: eBay Listing (Single)

```
User clicks "List on eBay" at $X price
                │
                ▼
┌───────────────────────────────┐
│ Check eBay Connection         │
│ (ebay_tokens table)           │
└───────────────────────────────┘
                │
       ┌────────┴────────┐
       │                 │
   Connected         Not Connected
       │                 │
       │                 ▼
       │    ┌───────────────────────────┐
       │    │ OAuth Flow                │
       │    │ 1. Redirect to eBay       │
       │    │ 2. User authorizes        │
       │    │ 3. Callback with code     │
       │    │ 4. Exchange for tokens    │
       │    │ 5. Store in DB            │
       │    └───────────────────────────┘
       │                 │
       └────────┬────────┘
                │
                ▼
┌───────────────────────────────┐
│ Generate AI Description       │
│ (Anthropic Claude)            │
│ - 300 char limit              │
│ - Key issues highlighted      │
│ - Mobile optimized            │
└───────────────────────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Show Preview Modal            │
│ - Editable description        │
│ - Confirm price               │
└───────────────────────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Create Inventory Item         │
│ (eBay Inventory API)          │
│ - Title, description          │
│ - Condition (LIKE_NEW, etc)   │
│ - Package dimensions          │
│ - Image URLs                  │
└───────────────────────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Get/Create Merchant Location  │
│ - Check existing locations    │
│ - Create if none exist        │
└───────────────────────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Get User's Business Policies  │
│ (eBay Account API)            │
│ - Fulfillment (shipping)      │
│ - Payment                     │
│ - Return                      │
└───────────────────────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Create Offer                  │
│ (eBay Inventory API)          │
│ - Link to inventory item      │
│ - Set price                   │
│ - Attach policies             │
│ - Set category (259104)       │
└───────────────────────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Publish? (based on param)     │
│                               │
│ publish=true  → Goes LIVE     │
│ publish=false → Returns draft │
│                 URL to Seller │
│                 Hub           │
└───────────────────────────────┘
                │
                ▼
        Return listing/draft URL
        to frontend
```

---

## API Endpoints Reference

### Valuation
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/valuate` | POST | Get three-tier valuation for a comic |
| `/api/lookup` | GET | Database lookup (no AI) |
| `/api/messages` | POST | Proxy to Anthropic (frontend extraction) |

### QuickList (Batch)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/extract` | POST | Extract single comic info from photo |
| `/api/batch/process` | POST | Extract + Valuate + Describe (1-20 comics) |
| `/api/batch/list` | POST | Upload images + Create drafts (1-20 comics) |

### eBay Integration
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ebay/auth` | GET | Start OAuth flow |
| `/api/ebay/callback` | GET | OAuth callback |
| `/api/ebay/status` | GET | Check connection status |
| `/api/ebay/list` | POST | Create listing (supports `publish`, `image_urls`) |
| `/api/ebay/upload-image` | POST | Upload image to eBay Picture Services |
| `/api/ebay/generate-description` | POST | Generate AI description |
| `/api/ebay/disconnect` | POST | Remove eBay connection |

### Input Validation (Batch Endpoints)
- Max 20 comics per batch
- Max 10MB per image
- Supported formats: JPEG, PNG, WebP, HEIC

---

## Database Schema

### search_cache
Stores valuation results for 48-hour caching.

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

---

## External Services

### Anthropic API
- **Model:** Claude Sonnet 4
- **Tier:** 2 (450k tokens/min)
- **Uses:**
  - Web search for eBay prices
  - Photo analysis (comic extraction)
  - Description generation

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

---

## Security Considerations

1. **API Keys:** Stored as environment variables in Render
2. **eBay Tokens:** Encrypted at rest in PostgreSQL
3. **CORS:** Configured for frontend domain only
4. **OAuth State:** Random state parameter prevents CSRF
5. **No PII Storage:** Only eBay tokens, no personal data
6. **Input Validation:** Max image size (10MB), max batch size (20)

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

---

## Key Files

| File | Purpose |
|------|---------|
| `wsgi.py` | Flask routes (v3.4) |
| `ebay_valuation.py` | Valuation logic, caching |
| `ebay_oauth.py` | eBay OAuth flow |
| `ebay_listing.py` | Listing creation, image upload |
| `ebay_description.py` | AI description generation |
| `comic_extraction.py` | **NEW** Backend extraction via Claude vision (with Vision Guide prompt) |
| `index.html` | Frontend SPA |

---

*Last updated: January 20, 2026 (Session 2)*
