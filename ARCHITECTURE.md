# CollectionCalc Architecture

## System Overview

CollectionCalc is a multi-component platform for comic book valuation, listing, and market data collection.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACES                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐           │
│  │   Main App       │  │  Admin Dashboard │  │ Whatnot Extension│           │
│  │  (app.html)      │  │  (admin.html)    │  │  (Chrome MV3)    │           │
│  │                  │  │                  │  │                  │           │
│  │ • Valuations     │  │ • User mgmt      │  │ • Live overlay   │           │
│  │ • QuickList      │  │ • Beta codes     │  │ • Vision scan    │           │
│  │ • Collections    │  │ • NLQ queries    │  │ • Sale capture   │           │
│  │ • eBay listing   │  │ • Error logs     │  │ • FMV display    │           │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘           │
│           │                     │                     │                      │
│           └─────────────────────┼─────────────────────┘                      │
│                                 │                                            │
│  ┌──────────────────────────────┴───────────────────────────────────────┐   │
│  │                     Landing Page (index.html)                         │   │
│  │                    Beta code gate for new users                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLOUDFLARE (Frontend)                                │
│                        collectioncalc.com                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Cloudflare Pages          │  Cloudflare R2                                  │
│  • index.html (landing)    │  • collectioncalc-images bucket                │
│  • app.html (main app)     │  • /sales/{id}/front.jpg                       │
│  • admin.html (dashboard)  │  • /submissions/{id}/*.jpg (B4Cert ready)      │
│  • styles.css              │                                                 │
│  • app.js                  │  Public URL: pub-xxx.r2.dev                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          RENDER (Backend)                                    │
│                    collectioncalc.onrender.com                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         Flask Application                               │ │
│  │                           wsgi.py (~1000 lines)                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│  ┌─────────────┬─────────────┬─────┴─────┬─────────────┬─────────────┐      │
│  │             │             │           │             │             │      │
│  ▼             ▼             ▼           ▼             ▼             ▼      │
│ ┌───────┐  ┌───────┐  ┌───────────┐  ┌───────┐  ┌───────────┐  ┌────────┐  │
│ │auth.py│  │admin  │  │ebay_      │  │comic_ │  │ebay_      │  │r2_     │  │
│ │       │  │.py    │  │valuation  │  │extract│  │listing.py │  │storage │  │
│ │• Login│  │• NLQ  │  │.py        │  │ion.py │  │           │  │.py     │  │
│ │• Beta │  │• Logs │  │• FMV calc │  │• Vision│ │• Create   │  │• Upload│  │
│ │• JWT  │  │• Stats│  │• eBay API │  │• Claude│ │• Policies │  │• Serve │  │
│ └───────┘  └───────┘  └───────────┘  └───────┘  └───────────┘  └────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌─────────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL        │  │   Anthropic     │  │   eBay API      │
│   (Render)          │  │   Claude API    │  │                 │
├─────────────────────┤  ├─────────────────┤  ├─────────────────┤
│ • users             │  │ • Valuations    │  │ • OAuth         │
│ • collections       │  │ • Extraction    │  │ • Inventory     │
│ • market_sales      │  │ • Descriptions  │  │ • Pictures      │
│ • search_cache      │  │ • NLQ           │  │ • Fulfillment   │
│ • request_logs      │  │                 │  │                 │
│ • api_usage         │  │ Models:         │  │                 │
│ • beta_codes        │  │ • claude-sonnet │  │                 │
│ • ebay_tokens       │  │ • claude-opus   │  │                 │
└─────────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Database Schema

### Core Tables

```sql
-- User accounts and authentication
users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT FALSE,      -- Admin must approve
    is_admin BOOLEAN DEFAULT FALSE,
    approved_at TIMESTAMP,
    approved_by INTEGER,
    beta_code_used VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)

-- Beta access codes
beta_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    uses_allowed INTEGER DEFAULT 1,
    uses_remaining INTEGER DEFAULT 1,
    expires_at TIMESTAMP,
    note TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
)

-- User comic collections
collections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(255),
    issue VARCHAR(50),
    grade VARCHAR(10),
    quick_sale_price DECIMAL(10,2),
    fair_value_price DECIMAL(10,2),
    high_end_price DECIMAL(10,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
)

-- Live auction sales data (from Whatnot)
market_sales (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) DEFAULT 'whatnot',
    source_id VARCHAR(255),                  -- For deduplication
    title VARCHAR(255),
    series VARCHAR(255),
    issue VARCHAR(50),
    grade DECIMAL(3,1),
    grade_source VARCHAR(50),                -- slab_label, seller_verbal, vision_cover, dom
    slab_type VARCHAR(50),                   -- CGC, CBCS, PGX, raw
    variant VARCHAR(255),
    is_key BOOLEAN DEFAULT FALSE,
    price DECIMAL(10,2),
    sold_at TIMESTAMP,
    raw_title TEXT,
    seller VARCHAR(255),
    bids INTEGER,
    viewers INTEGER,
    image_url TEXT,                          -- R2 URL
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source, source_id)
)

-- Valuation cache (48-hour TTL)
search_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(255) UNIQUE,           -- title:issue:grade
    result JSONB,
    created_at TIMESTAMP DEFAULT NOW()
)

-- Request logging for debugging
request_logs (
    id SERIAL PRIMARY KEY,
    endpoint VARCHAR(255),
    method VARCHAR(10),
    status_code INTEGER,
    response_time_ms INTEGER,
    user_id INTEGER,
    device_type VARCHAR(50),                 -- mobile, tablet, desktop
    error_message TEXT,
    request_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
)

-- Anthropic API usage tracking
api_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    endpoint VARCHAR(255),
    model VARCHAR(100),
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT NOW()
)

-- Admin NLQ query history
admin_nlq_history (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES users(id),
    question TEXT,
    generated_sql TEXT,
    result_count INTEGER,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
)

-- eBay OAuth tokens
ebay_tokens (
    id SERIAL PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    token_expiry TIMESTAMP,
    ebay_username TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/signup` | Create account (requires beta code) | - |
| POST | `/api/auth/login` | Get JWT token | - |
| GET | `/api/auth/me` | Get current user | JWT |
| POST | `/api/auth/verify` | Verify email | Token |
| POST | `/api/auth/resend-verification` | Resend email | - |
| POST | `/api/auth/forgot-password` | Request reset | - |
| POST | `/api/auth/reset-password` | Reset password | Token |

### Beta & Admin
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/beta/validate` | Check beta code | - |
| GET | `/api/admin/dashboard` | Get stats | Admin |
| GET | `/api/admin/users` | List all users | Admin |
| POST | `/api/admin/users/{id}/approve` | Approve user | Admin |
| POST | `/api/admin/users/{id}/reject` | Reject user | Admin |
| GET | `/api/admin/beta-codes` | List codes | Admin |
| POST | `/api/admin/beta-codes` | Create code | Admin |
| GET | `/api/admin/errors` | Recent errors | Admin |
| GET | `/api/admin/usage` | API costs | Admin |
| POST | `/api/admin/nlq` | Natural language query | Admin |

### Valuation
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/valuate` | Get comic valuation | JWT+Approved |
| POST | `/api/extract` | Extract from image | JWT+Approved |
| POST | `/api/messages` | Anthropic proxy | JWT+Approved |

### eBay Integration
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/ebay/auth` | Get OAuth URL | JWT+Approved |
| GET | `/api/ebay/callback` | OAuth callback | - |
| GET | `/api/ebay/status` | Connection status | JWT+Approved |
| POST | `/api/ebay/generate-description` | AI description | JWT+Approved |
| POST | `/api/ebay/upload-image` | Upload to eBay | JWT+Approved |
| POST | `/api/ebay/list` | Create listing | JWT+Approved |
| POST | `/api/ebay/account-deletion` | GDPR compliance | - |

### Market Sales (Whatnot Extension)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/sales/record` | Record sale (+ image) | - |
| GET | `/api/sales/count` | Total sales count | - |
| GET | `/api/sales/recent` | Recent sales list | - |

### Images (R2 Storage)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/images/upload` | Upload image | - |
| POST | `/api/images/upload-for-sale` | Upload + update sale | - |
| POST | `/api/images/submission` | B4Cert upload | - |
| GET | `/api/images/status` | R2 connection check | - |

### Collections
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/collection` | Get user's comics | JWT+Approved |
| POST | `/api/collection` | Save comic | JWT+Approved |
| DELETE | `/api/collection/{id}` | Remove comic | JWT+Approved |

---

## External Services

### Cloudflare
- **Pages**: Static frontend hosting
- **R2**: Image storage (S3-compatible)
- **DNS**: collectioncalc.com

### Render
- **Web Service**: Flask backend
- **PostgreSQL**: Database

### Anthropic
- **Claude Sonnet**: Valuations, extraction, descriptions
- **Claude Opus**: Premium signature detection

### eBay
- **OAuth**: User authentication
- **Inventory API**: Listing creation
- **Browse API**: Market data

### Resend
- **Email**: Verification, password reset

---

## Environment Variables

### Render Backend
```bash
# Database
DATABASE_URL=postgresql://...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# eBay
EBAY_CLIENT_ID=...
EBAY_CLIENT_SECRET=...
EBAY_RUNAME=...
EBAY_SANDBOX=false

# Cloudflare R2
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_ACCOUNT_ID=...
R2_BUCKET_NAME=collectioncalc-images
R2_ENDPOINT=https://xxx.r2.cloudflarestorage.com
R2_PUBLIC_URL=https://pub-xxx.r2.dev

# Email
RESEND_API_KEY=re_...

# App
JWT_SECRET=...
FRONTEND_URL=https://collectioncalc.com
```

### Whatnot Extension
```javascript
// Stored in chrome.storage.local
ANTHROPIC_API_KEY  // For Vision scanning
```

---

## Deployment

### Backend (Render)
```bash
cd cc/v2
git add .
git commit -m "Description"
git push
# Auto-deploys via GitHub integration
```

### Frontend (Cloudflare Pages)
```bash
cd cc/v2/frontend
git add .
git commit -m "Description"  
git push
purge  # Clear Cloudflare cache
```

### Extension (Chrome)
1. Update version in manifest.json
2. Load unpacked in chrome://extensions
3. Or package and upload to Chrome Web Store

---

## File Structure

### Backend (cc/v2/)
```
cc/v2/
├── wsgi.py                 # Main Flask app (~1000 lines)
├── auth.py                 # Authentication & beta codes
├── admin.py                # Admin functions & NLQ
├── r2_storage.py           # Cloudflare R2 integration
├── ebay_valuation.py       # FMV calculations
├── ebay_oauth.py           # eBay OAuth flow
├── ebay_listing.py         # eBay Inventory API
├── ebay_description.py     # AI descriptions
├── comic_extraction.py     # Vision extraction
├── db_migrate_beta.py      # Database migrations
├── requirements.txt        # Python dependencies
└── docs/
    ├── ROADMAP.md
    ├── ARCHITECTURE.md
    ├── API_REFERENCE.md
    ├── CLAUDE_NOTES.md
    └── ...
```

### Frontend (cc/v2/frontend/)
```
frontend/
├── index.html              # Beta landing page
├── app.html                # Main application
├── admin.html              # Admin dashboard
├── styles.css              # All CSS
└── app.js                  # All JavaScript
```

### Extension (whatnot-valuator/)
```
whatnot-valuator/
├── manifest.json           # MV3 manifest
├── content.js              # Main content script
├── background.js           # Service worker
├── popup.html              # Extension popup
├── styles.css              # Overlay styles
├── lib/
│   ├── collectioncalc.js   # API client
│   ├── apollo-reader.js    # GraphQL cache reader
│   ├── vision.js           # Claude Vision
│   ├── sale-tracker.js     # Local tracking
│   ├── valuator.js         # FMV display
│   ├── normalizer.js       # Title parsing
│   ├── audio.js            # Audio transcription
│   └── keys.js             # Key issue database
└── data/
    └── keys.js             # 500+ key issues
```

---

*Last updated: January 26, 2026*
