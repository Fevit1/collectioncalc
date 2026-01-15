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
│  │  - Form inputs (title, issue, grade, publisher, year)   │    │
│  │  - Animated calculator loading                          │    │
│  │  - Thinking steps display                               │    │
│  │  - Results with confidence indicators                   │    │
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
│  └────────┬─────────┘ │ - Spelling   │ └──────────────────┘    │
│           │           └──────┬───────┘                          │
│           ▼                  │                                   │
│  ┌──────────────────┐        │                                   │
│  │comics_pricing.db │        │                                   │
│  │   (144 comics)   │        │                                   │
│  └──────────────────┘        │                                   │
│                              │                                   │
│  ┌──────────────────┐        │                                   │
│  │ price_cache.db   │◄───────┘                                   │
│  │ (48hr TTL)       │                                            │
│  └──────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Web Search API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ANTHROPIC API                               │
│                                                                  │
│  - Claude with web_search tool                                   │
│  - Searches: eBay, GoCollect, CovrPrice, Heritage, etc.         │
│  - Returns JSON with prices, dates, grades, sources             │
│  - Corrects spelling errors                                      │
└─────────────────────────────────────────────────────────────────┘
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
3. Check price_cache.db (48hr TTL)
         │                    │
         │ HIT               │ MISS
         ▼                    ▼
4a. Return cached       4b. Check comics_pricing.db
    result                        │
                         ┌───────┴───────┐
                         │ FOUND         │ NOT FOUND
                         ▼               ▼
                   5a. Search web    5b. Search web
                       for market        for prices
                       validation        │
                         │               │
                         ▼               ▼
                   6a. Blend DB +   6b. Use web
                       web prices       prices only
                         │               │
                         └───────┬───────┘
                                 ▼
                   7. Calculate confidence score
                      - Volume factor
                      - Recency factor  
                      - Variance factor
                                 │
                                 ▼
                   8. Cache result (48hr)
                                 │
                                 ▼
                   9. Return to user
```

## Databases

### comics_pricing.db (Static Reference)

```sql
CREATE TABLE comics (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    issue TEXT NOT NULL,
    year INTEGER,
    publisher TEXT,
    base_value REAL,
    notes TEXT
);
```

**144 comics** covering key issues from major publishers.

### price_cache.db (Dynamic Cache)

```sql
CREATE TABLE search_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    issue TEXT NOT NULL,
    search_key TEXT UNIQUE NOT NULL,
    estimated_value REAL,
    confidence TEXT,
    confidence_score INTEGER,
    num_sales INTEGER,
    price_min REAL,
    price_max REAL,
    sales_data TEXT,  -- JSON
    reasoning TEXT,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**48-hour TTL** - Results expire after 2 days for fresh data.

## Key Algorithms

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

### Blending Strategy

| Scenario | Action |
|----------|--------|
| DB + High confidence web (70%+) | Use web price |
| DB + Low confidence web | 50/50 blend |
| DB only | Grade-adjusted DB value |
| Web only | Direct web price |
| Neither | Default estimate, VERY LOW confidence |

## Files

| File | Purpose |
|------|---------|
| `wsgi.py` | Flask API server, routes |
| `ebay_valuation.py` | Web search, caching, aliases, spelling |
| `valuation_model.py` | Grade adjustments, era factors |
| `comic_lookup.py` | Database search |
| `database_schema.py` | Schema definitions |
| `comics_pricing.db` | Reference database |
| `price_cache.db` | Search result cache |
| `index.html` | Frontend UI |

## Hosting

| Component | Host | URL | Cost |
|-----------|------|-----|------|
| Frontend | Cloudflare Pages | collectioncalc.pages.dev | Free |
| Backend | Render | collectioncalc.onrender.com | Free |
| AI | Anthropic API | api.anthropic.com | ~$0.03/search |

## Environment Variables

| Variable | Location | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Render | Web search API access |

---

*Last updated: January 2026*
