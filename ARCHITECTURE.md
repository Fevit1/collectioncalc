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
│  │                      Flask API (wsgi.py)                         │   │
│  │                                                                   │   │
│  │  /api/valuate          - Get comic valuation                     │   │
│  │  /api/lookup           - Database lookup                         │   │
│  │  /api/messages         - Anthropic proxy                         │   │
│  │  /api/ebay/auth        - Start OAuth flow                        │   │
│  │  /api/ebay/callback    - OAuth callback                          │   │
│  │  /api/ebay/status      - Check connection                        │   │
│  │  /api/ebay/list        - Create listing                          │   │
│  │  /api/ebay/generate-description - AI description                 │   │
│  │  /api/ebay/disconnect  - Remove eBay connection                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│          ┌─────────────────────────┼─────────────────────────┐         │
│          │                         │                         │          │
│          ▼                         ▼                         ▼          │
│  ┌───────────────┐      ┌───────────────┐      ┌───────────────┐       │
│  │ ebay_valuation│      │  ebay_oauth   │      │ ebay_listing  │       │
│  │     .py       │      │     .py       │      │     .py       │       │
│  │               │      │               │      │               │       │
│  │ - Search eBay │      │ - OAuth flow  │      │ - Create inv  │       │
│  │ - Parse prices│      │ - Token mgmt  │      │ - Create offer│       │
│  │ - Calculate   │      │ - Refresh     │      │ - Publish     │       │
│  │ - Cache       │      │ - Store/load  │      │ - Policies    │       │
│  └───────────────┘      └───────────────┘      └───────────────┘       │
│          │                         │                         │          │
│          └─────────────────────────┼─────────────────────────┘         │
│                                    │                                     │
│                                    ▼                                     │
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
         └───────────────────┘           └───────────────────┘
```

---

## Data Flow: Valuation

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

## Data Flow: eBay Listing

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
│ - Placeholder image           │
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
│ Publish Offer                 │
│ (eBay Inventory API)          │
│ → Listing goes LIVE           │
└───────────────────────────────┘
                │
                ▼
        Return listing URL
        to frontend
```

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
  - Photo analysis (comic identification)
  - Description generation

### eBay API
- **Environment:** Production
- **APIs Used:**
  - Browse API (searching)
  - Inventory API (listings)
  - Account API (policies)
  - OAuth (authentication)
- **Key Settings:**
  - Category: 259104 (Comics & Graphic Novels)
  - Condition enums: LIKE_NEW, USED_EXCELLENT, etc.
  - Package: 1"×11"×7", 8oz, LETTER

---

## Security Considerations

1. **API Keys:** Stored as environment variables in Render
2. **eBay Tokens:** Encrypted at rest in PostgreSQL
3. **CORS:** Configured for frontend domain only
4. **OAuth State:** Random state parameter prevents CSRF
5. **No PII Storage:** Only eBay tokens, no personal data

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

*Last updated: January 19, 2026*
