# CollectionCalc Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CLOUDFLARE PAGES                               │
│                collectioncalc.pages.dev                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    index.html                            │    │
│  │  - Brand UI (Indigo/Purple/Cyan gradient)               │    │
│  │  - Simplified form (title, issue, grade only)           │    │
│  │  - Animated calculator loading                          │    │
│  │  - Thinking steps display                               │    │
│  │  - Three-tier pricing (Quick Sale/Fair Value/High End)  │    │
│  │  - Details toggle (sales count, confidence, analysis)   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS POST /api/valuate
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        RENDER                                    │
│              collectioncalc.onrender.com                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Flask API (wsgi.py)                   │    │
│  │  - /api/valuate (POST) - Full valuation with market data│    │
│  │  - /api/valuate/simple (POST) - Database only           │    │
│  │  - /api/lookup (GET) - Raw database lookup              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│  ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐    │
│  │  comic_lookup.py │ │ebay_valuation│ │valuation_model.py│    │
│  │                  │ │    .py       │ │                  │    │
│  │ - Title search   │ │ - Web search │ │ - Grade adjust   │    │
│  │ - Issue lookup   │ │ - Caching    │ │ - Era factors    │    │
│  │ - Fuzzy match    │ │ - Aliases    │ │ - Publisher adj  │    │
│  └──────────────────┘ │ - Spelling   │ └──────────────────┘    │
│                       │ - Grade filter│                         │
│                       │ - BIN prices │                          │
│                       └──────┬───────┘                          │
└──────────────────────────────┼──────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                                 ▼
┌─────────────────────────┐      ┌─────────────────────────────────┐
│   RENDER PostgreSQL     │      │         ANTHROPIC API           │
│                         │      │                                 │
│  search_cache table     │      │  - Claude with web_search tool  │
│  - Tiered pricing       │      │  - eBay sold listings           │
│  - 48hr TTL             │      │  - Buy It Now prices            │
│  - Grade-filtered data  │      │  - Returns structured JSON      │
└─────────────────────────┘      └─────────────────────────────────┘
```

## Data Flow

### Valuation Request Flow

```
1. User enters: "ASM #300 VF"
                    │
                    ▼
2. Alias expansion: "Amazing Spider-Man #300 VF"
                    │
                    ▼
3. Check PostgreSQL cache (48hr TTL)
         │                    │
         │ HIT               │ MISS
         ▼                    ▼
4a. Return cached       4b. AI web search
    result (with            │
    3 price tiers)          ▼
                       5. Parse results:
                          - Sold listings (with grades)
                          - Buy It Now prices
                                 │
                                 ▼
                       6. Filter by grade (±0.5 tolerance)
                          VF request → only VF-, VF, VF+ sales
                                 │
                                 ▼
                       7. Calculate three tiers:
                          - Quick Sale = lowest BIN or min sold
                          - Fair Value = median sold
                          - High End = max sold
                                 │
                                 ▼
                       8. Calculate confidence score
                          - Volume factor
                          - Recency factor  
                          - Variance factor
                                 │
                                 ▼
                       9. Cache result (48hr)
                          with all three tiers
                                 │
                                 ▼
                      10. Return to user:
                          {
                            quick_sale: $X,
                            fair_value: $Y,
                            high_end: $Z,
                            lowest_bin: $B,
                            confidence: "MEDIUM-HIGH"
                          }
```

## Database

### Render PostgreSQL (Managed Service)

CollectionCalc uses Render's managed PostgreSQL for persistent storage. This replaced the original SQLite files in January 2026.

**Why PostgreSQL?**
- Render's free tier SQLite files don't persist across deploys
- Managed service = automatic backups, no file management
- Scales better for future growth

### search_cache Table

```sql
CREATE TABLE search_cache (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    issue TEXT NOT NULL,
    search_key TEXT UNIQUE NOT NULL,
    estimated_value REAL,
    confidence TEXT,
    confidence_score INTEGER,
    num_sales INTEGER,
    price_min REAL,
    price_max REAL,
    sales_data TEXT,  -- JSON array of sales
    reasoning TEXT,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Three-tier pricing (added Jan 2026)
    quick_sale REAL,      -- Lowest BIN or floor price
    fair_value REAL,      -- Median sold price
    high_end REAL,        -- Maximum recent sold
    lowest_bin REAL       -- Current Buy It Now price
);
```

**48-hour TTL** - Results expire after 2 days for fresh market data.

## Key Algorithms

### Grade Filtering

Sales are filtered to match the requested grade within ±0.5 on the grade scale:

| Grade | Value | Accepts |
|-------|-------|---------|
| MT | 10.0 | MT only |
| NM | 9.4 | NM-, NM, NM+ |
| VF | 8.0 | VF-, VF, VF+ |
| FN | 6.0 | FN-, FN, FN+ |
| VG | 4.0 | VG-, VG, VG+ |
| G | 2.0 | G-, G, G+ |
| Raw | 6.0 | ~FN equivalent |

This prevents a VF request from being skewed by NM or FN sales.

### Three-Tier Pricing

| Tier | Calculation | Use Case |
|------|-------------|----------|
| Quick Sale | Lowest BIN, or min sold if no BIN | Sell fast |
| Fair Value | Median of grade-filtered sales | Market value |
| High End | Max of grade-filtered sales | Patient seller |

### Recency Weighting

| Sale Age | Weight |
|----------|--------|
| This week | 100% |
| This month | 90% |
| Last 3 months | 70% |
| Last year | 50% |
| Older | 25% |

### Confidence Scoring

```
Base: 50 points

Volume Factor (+/- 25):
  10+ sales: +25
  5-9 sales: +15
  2-4 sales: +5
  1 sale: -15
  0 sales: -25

Recency Factor (+/- 15):
  < 30 days: +15
  < 90 days: +10
  < 365 days: 0
  > 365 days: -10

Variance Factor (+/- 10):
  CV < 0.1: +10
  CV < 0.25: +5
  CV < 0.5: -5
  CV > 0.5: -10

Labels:
  90+: HIGH
  70-89: MEDIUM-HIGH
  50-69: MEDIUM
  30-49: LOW
  <30: VERY LOW
```

### Per-Tier Confidence Adjustments

Each pricing tier gets its own confidence score based on data quality:

| Tier | Adjustments |
|------|-------------|
| **Quick Sale** | +15 if BIN data exists; -5 if no BIN; +10 if multiple sales near floor |
| **Fair Value** | Uses base confidence (median is most stable metric) |
| **High End** | -25 if max >2x median (outlier); -15 if max >1.5x median; +10 if multiple high sales |

### Data Source Strategy

| Scenario | Action |
|----------|--------|
| Cache hit (< 48hr) | Return cached tiered pricing |
| Cache miss | AI web search → calculate tiers → cache |
| No sales found | Return error, VERY LOW confidence |

*Note: The original local database (comics_pricing.db) is no longer used. All pricing comes from real-time market data via AI web search.*

## Files

| File | Purpose |
|------|---------|
| `wsgi.py` | Flask API server, routes |
| `ebay_valuation.py` | Web search, caching, aliases, spelling, grade filtering, tiered pricing |
| `valuation_model.py` | Grade adjustments, era factors |
| `comic_lookup.py` | Database search (legacy) |
| `database_schema.py` | Schema definitions (legacy) |
| `index.html` | Frontend UI |
| `requirements.txt` | Python dependencies (includes psycopg2) |

## Hosting

| Component | Host | URL | Cost |
|-----------|------|-----|------|
| Frontend | Cloudflare Pages | collectioncalc.pages.dev | Free |
| Backend | Render | collectioncalc.onrender.com | Free |
| Database | Render PostgreSQL | (internal) | Free |
| AI | Anthropic API | api.anthropic.com | ~$0.03/search |

## Environment Variables

| Variable | Location | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Render | Web search API access |
| `DATABASE_URL` | Render | PostgreSQL connection string (auto-set by Render) |

---

*Last updated: January 17, 2026*
