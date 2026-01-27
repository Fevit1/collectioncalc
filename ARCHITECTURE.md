# CollectionCalc / Slab Worthy Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                              │
├─────────────────┬─────────────────┬─────────────────────────────────┤
│  CollectionCalc │  Slab Worthy?   │   Whatnot Extension             │
│  Web App        │  (Same app)     │   Chrome Extension              │
│  - Valuations   │  - 4-photo      │   - Live auction overlay        │
│  - eBay listing │    grading      │   - Auto-scan covers            │
│  - Collection   │  - Grade report │   - Sale capture                │
│                 │  - ROI calc     │   - Signature detection         │
└────────┬────────┴────────┬────────┴─────────────────┬───────────────┘
         │                 │                          │
         │    HTTPS/REST   │                          │
         ▼                 ▼                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    COLLECTIONCALC API                                │
│                 (collectioncalc.onrender.com)                        │
├─────────────────────────────────────────────────────────────────────┤
│  /api/valuate      - Three-tier comic valuation                      │
│  /api/messages     - Anthropic proxy (frontend extraction)           │
│  /api/extract      - Backend photo extraction                        │
│  /api/batch/*      - QuickList bulk processing                       │
│  /api/sales/*      - Market data recording/retrieval                 │
│  /api/ebay/*       - eBay OAuth + listing                           │
│  /api/auth/*       - User authentication                            │
│  /api/collection   - User collection CRUD                           │
│  /api/admin/*      - Admin functions, NLQ                           │
│  /api/images/*     - R2 image upload                                │
└────────┬────────────────────┬───────────────────────┬───────────────┘
         │                    │                       │
         ▼                    ▼                       ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐
│   PostgreSQL    │  │  Anthropic API  │  │    External Services    │
│   (Render)      │  │  Claude Vision  │  ├─────────────────────────┤
├─────────────────┤  │  + Messages     │  │  eBay API (listings)    │
│ users           │  └─────────────────┘  │  Cloudflare R2 (images) │
│ collections     │                       │  Resend (email)         │
│ market_sales    │                       │  eBay Browse API (data) │
│ search_cache    │                       └─────────────────────────┘
│ creator_sigs    │
│ beta_codes      │
│ ebay_tokens     │
└─────────────────┘
```

## File Structure

```
cc/v2/
├── ─────────── FRONTEND (Cloudflare Pages) ───────────
├── index.html           # Beta landing page
├── app.html             # Main application (with Slab Worthy tab)
├── admin.html           # Admin dashboard
├── signatures.html      # Signature reference admin
├── styles.css           # All CSS (+ grading styles appended)
├── app.js               # All JavaScript (+ grading script appended)
│
├── ─────────── BACKEND (Render) ───────────
├── wsgi.py              # Flask app, all routes
├── auth.py              # Authentication (JWT, signup, login, reset)
├── admin.py             # Admin functions, NLQ
├── ebay_valuation.py    # Valuation logic, caching
├── ebay_oauth.py        # eBay OAuth flow
├── ebay_listing.py      # eBay Inventory API
├── ebay_description.py  # AI description generation
├── comic_extraction.py  # Backend Claude Vision extraction
├── r2_storage.py        # Cloudflare R2 integration
├── requirements.txt     # Python dependencies
│
├── ─────────── CHROME EXTENSION ───────────
├── whatnot-valuator/
│   ├── manifest.json    # Extension config
│   ├── content.js       # Main overlay, auction monitoring
│   ├── lib/
│   │   ├── collectioncalc.js  # API client
│   │   └── vision.js          # Claude Vision (facsimile detection)
│   └── data/
│       └── keys.js      # 500+ key issue database
│
└── ─────────── DOCUMENTATION ───────────
    ├── CLAUDE_NOTES.md  # Session notes, context for Claude
    ├── ROADMAP.md       # Feature backlog, version history
    └── ARCHITECTURE.md  # This file
```

**NOTE:** All frontend files are in `cc/v2/` root. There is NO `frontend/` subfolder.

## Slab Worthy Feature Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SLAB WORTHY? FLOW                             │
│                    (Patent Pending)                              │
└─────────────────────────────────────────────────────────────────┘

User clicks "🔲 Slab Worthy?" tab
            │
            ▼
┌─────────────────────┐
│ Step 1: FRONT COVER │ ◄── REQUIRED
│ (Photo capture)     │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │ AI Check  │ → Quality feedback (blur/dark/glare)
     │ Extract   │ → Title, Issue, Publisher, Year
     │ Defects   │ → Cover condition assessment
     └─────┬─────┘
           │
           ▼
┌─────────────────────┐
│ Step 2: SPINE       │ ◄── Recommended (skippable)
└──────────┬──────────┘
           │ → Spine roll, stress marks, splits
           ▼
┌─────────────────────┐
│ Step 3: BACK COVER  │ ◄── Recommended (skippable)
└──────────┬──────────┘
           │ → Back defects, stains, labels
           ▼
┌─────────────────────┐
│ Step 4: CENTERFOLD  │ ◄── Recommended (skippable)
└──────────┬──────────┘
           │ → Staples, interior, attachment
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
search_cache (id, cache_key, result_json, created_at)  -- 48hr TTL

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
| Cloudflare R2 | Image storage | Access Key |
| Resend | Transactional email | API Key |

## Security

- **JWT tokens** for user authentication (24hr expiry)
- **Beta codes** gate new signups
- **Admin approval** required for full access
- **CORS** restricted to collectioncalc.com
- **Rate limiting** on API endpoints
- **Passwords** hashed with bcrypt

## Deployment

| Component | Platform | Trigger |
|-----------|----------|---------|
| Frontend | Cloudflare Pages | Git push + `purge` command |
| Backend | Render.com | Git push + `deploy` command |
| Database | Render PostgreSQL | Managed |
| Images | Cloudflare R2 | API upload |

---

*Last updated: January 27, 2026*
*Patent Pending: Multi-angle comic grading system*
