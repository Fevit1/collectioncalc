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
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Backend (Render.com)                                 │
│                   collectioncalc.onrender.com                           │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Flask API (wsgi.py v3.7)                    │   │
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
│  │  ┌─────────────┐  ┌─────────────┐                               │   │
│  │  │ collections │  │ password_   │                               │   │
│  │  │             │  │ resets      │                               │   │
│  │  │ - user_id   │  │             │                               │   │
│  │  │ - comic data│  │ - token     │                               │   │
│  │  │ - created   │  │ - expires   │                               │   │
│  │  └─────────────┘  └─────────────┘                               │   │
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
│ - Signatures    │  NEW    │
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
│ - Grade match   │                  │
└─────────────────┘                  │
         │                           │
         ▼                           │
┌─────────────────┐                  │
│ Calculate Tiers │                  │
│ - Quick: 15th   │                  │
│ - Fair: median  │                  │
│ - High: 85th    │                  │
└─────────────────┘                  │
         │                           │
         ▼                           │
┌─────────────────┐                  │
│ Cache Result    │◄─────────────────┘
│ (48hr TTL)      │
└─────────────────┘
         │
         ▼
    Return to user
```

---

## Data Flow: Photo Extraction

```
User uploads photo
         │
         ▼
┌─────────────────────────┐
│ Image Processing        │
│ (Frontend - app.js)     │
│                         │
│ 1. Read EXIF orientation│
│ 2. Auto-rotate if needed│
│ 3. Scale to 1200-2400px │
│ 4. Compress to <5MB     │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ /api/messages           │
│ (Anthropic Proxy)       │
│                         │
│ Claude Vision extracts: │
│ - Title                 │
│ - Issue # (multi-loc)   │
│ - Publisher             │
│ - Year                  │
│ - Grade                 │
│ - Defects               │
│ - Signature detected?   │
│ - Signature analysis    │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ If signature_detected:  │
│                         │
│ - List all creators     │
│ - Confidence % each     │
│ - Most likely signer    │
│ - Characteristics       │
│                         │
│ Auto-check "Signed" box │
│ Auto-fill signer name   │
└─────────────────────────┘
         │
         ▼
    Display for user review
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
| `wsgi.py` | Flask routes (v3.7) |
| `ebay_valuation.py` | Valuation logic, caching |
| `ebay_oauth.py` | eBay OAuth flow |
| `ebay_listing.py` | Listing creation, image upload |
| `ebay_description.py` | AI description generation |
| `comic_extraction.py` | Backend extraction via Claude vision |
| `auth.py` | User auth (signup, login, JWT, password reset) |

---

*Last updated: January 22, 2026 (Session 7)*
