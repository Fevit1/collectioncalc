# CollectionCalc Database Documentation

## Overview

CollectionCalc uses PostgreSQL hosted on Render. The database stores:
- Market sales data (from Whatnot, eBay, etc.)
- eBay valuation cache
- User accounts and collections

## Connection Details

### Production (Render)
- **Host:** `dpg-d5knv4koud1c73dt21pg-a.oregon-postgres.render.com`
- **Port:** `5432`
- **Database:** `collectioncalc_db`
- **Username:** `collectioncalc_db_user`
- **Password:** (stored in Render dashboard)
- **Region:** Oregon (US West)
- **Version:** PostgreSQL 18

### Connection with DBeaver
Use the **Main** tab (not URL) with individual fields.

---

## Tables

### market_sales
Primary table for all sales data from multiple sources.

```sql
CREATE TABLE market_sales (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,              -- 'whatnot', 'ebay_auction', 'ebay_bin', 'pricecharting'
    
    -- Comic identity
    title TEXT,
    series TEXT,
    issue TEXT,                        -- TEXT to handle "1A", "300B" variants
    grade NUMERIC,
    grade_source TEXT,                 -- 'cgc', 'cbcs', 'raw', 'vision'
    slab_type TEXT,
    variant TEXT,
    is_key BOOLEAN DEFAULT FALSE,
    
    -- Sale data
    price NUMERIC NOT NULL,
    sold_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Source-specific context
    raw_title TEXT,
    seller TEXT,
    bids INTEGER,
    viewers INTEGER,
    image_url TEXT,
    source_id TEXT,                    -- External ID for deduplication
    
    UNIQUE(source, source_id)
);

-- Indexes for performance
CREATE INDEX idx_market_sales_lookup ON market_sales(series, issue, grade);
CREATE INDEX idx_market_sales_recency ON market_sales(sold_at DESC);
CREATE INDEX idx_market_sales_source ON market_sales(source);
```

**Source Values:**
- `whatnot` - Live Whatnot auction sales (from browser extension)
- `ebay_auction` - eBay completed auction sales
- `ebay_bin` - eBay Buy It Now sales
- `pricecharting` - PriceCharting aggregated data (future)

**Current Data:** 618+ records (migrated from Supabase on Jan 25, 2026)

---

### search_cache
Caches eBay valuation results (48-hour TTL).

```sql
CREATE TABLE search_cache (
    id SERIAL PRIMARY KEY,
    title TEXT,
    issue TEXT,
    search_key TEXT,
    estimated_value REAL,
    confidence TEXT,
    confidence_score INTEGER,
    num_sales INTEGER,
    price_min REAL,
    price_max REAL,
    sales_data TEXT,                   -- JSON array of sales
    reasoning TEXT,
    cached_at TIMESTAMP,
    quick_sale REAL,
    fair_value REAL,
    high_end REAL,
    lowest_bin REAL,
    quick_sale_confidence INTEGER,
    fair_value_confidence INTEGER,
    high_end_confidence INTEGER
);
```

---

### users
User authentication for CollectionCalc web app.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    -- Additional fields as needed
);
```

---

### collections
User's saved comic collections.

```sql
CREATE TABLE collections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    comic_data JSONB,                  -- Full comic details as JSON
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

### password_resets
Password reset tokens.

```sql
CREATE TABLE password_resets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    token TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### ebay_tokens
eBay OAuth tokens for listing functionality.

```sql
CREATE TABLE ebay_tokens (
    id SERIAL PRIMARY KEY,
    -- Token fields
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints

### Sales API (wsgi.py)

**POST /api/sales/record**
Record a sale from Whatnot extension.
```json
{
  "source": "whatnot",
  "title": "Amazing Spider-Man",
  "series": "Amazing Spider-Man", 
  "issue": "300",
  "grade": 9.4,
  "grade_source": "cgc",
  "slab_type": "CGC",
  "price": 485.00,
  "sold_at": "2026-01-25T12:00:00Z"
}
```

**GET /api/sales/count**
Returns total sales count.
```json
{"count": 618}
```

**GET /api/sales/recent?limit=20&source=whatnot**
Returns recent sales.

---

## Migration History

### Jan 25, 2026 - Supabase → Render
- Created `market_sales` table
- Migrated 618 records from Supabase `whatnot_sales`
- Updated Whatnot extension to use CollectionCalc API

### Migration Script Reference
```sql
-- Import from CSV (DBeaver export from Supabase)
-- Used INSERT...ON CONFLICT for deduplication
INSERT INTO market_sales (...) VALUES (...) 
ON CONFLICT (source, source_id) DO NOTHING;
```

---

## Useful Queries

### Count by source
```sql
SELECT source, COUNT(*) 
FROM market_sales 
GROUP BY source;
```

### Recent Whatnot sales
```sql
SELECT title, issue, grade, price, sold_at 
FROM market_sales 
WHERE source = 'whatnot' 
ORDER BY sold_at DESC 
LIMIT 20;
```

### FMV by title/issue
```sql
SELECT 
    AVG(price) as avg_price,
    MIN(price) as min_price,
    MAX(price) as max_price,
    COUNT(*) as sales_count
FROM market_sales
WHERE series ILIKE '%spider-man%' 
  AND issue = '300'
  AND sold_at > NOW() - INTERVAL '90 days';
```

### Clean garbage titles
```sql
DELETE FROM market_sales 
WHERE title ILIKE '%awesome comic%' 
   OR title ILIKE '%comic on screen%';
```

---

## Backup & Recovery

Render provides automatic backups for the Basic tier ($7/month).

Manual backup via pg_dump:
```bash
pg_dump "postgresql://user:pass@host:5432/db" > backup.sql
```

