# CollectionCalc / Slab Worthy — Production Database Documentation

**Last updated:** February 28, 2026 (Session 69)

## Overview

Slab Worthy uses PostgreSQL hosted on Render. The database stores user accounts, comic collections, market sales data, eBay integration tokens, Slab Guard registry, signature references, billing, and admin analytics.

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

## Tables (16 total)

### 1. users
User accounts with authentication, approval, and billing fields.

```sql
CREATE TABLE users (
    id                          SERIAL PRIMARY KEY,
    email                       TEXT UNIQUE NOT NULL,
    password_hash               TEXT NOT NULL,
    email_verified              BOOLEAN DEFAULT FALSE,
    email_verification_token    TEXT,
    email_verification_expires  TIMESTAMP,
    is_approved                 BOOLEAN DEFAULT FALSE,
    is_admin                    BOOLEAN DEFAULT FALSE,
    approved_at                 TIMESTAMPTZ,
    approved_by                 INTEGER REFERENCES users(id),
    beta_code_used              TEXT,
    plan                        VARCHAR(20) DEFAULT 'free',
    stripe_customer_id          VARCHAR(255),
    stripe_subscription_id      VARCHAR(255),
    subscription_status         VARCHAR(20) DEFAULT 'none',
    billing_period              VARCHAR(10) DEFAULT 'monthly',
    current_period_end          TIMESTAMP,
    valuations_this_month       INTEGER DEFAULT 0,
    valuations_reset_date       TIMESTAMP,
    display_name                VARCHAR(100),
    phone                       VARCHAR(20),
    phone_verified              BOOLEAN DEFAULT FALSE,
    marketing_consent           BOOLEAN DEFAULT FALSE,
    created_at                  TIMESTAMP DEFAULT NOW(),
    last_login                  TIMESTAMP,
    updated_at                  TIMESTAMP DEFAULT NOW()
);
```

---

### 2. collections
User's saved comic collection items. Each row is one comic with grading data, photos, and valuation.

```sql
CREATE TABLE collections (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title               TEXT,
    issue               TEXT,
    publisher           TEXT,
    year                INTEGER,
    grade               NUMERIC,
    grade_label         TEXT,
    confidence          NUMERIC,
    defects             JSONB,
    photos              JSONB,
    raw_value           NUMERIC,
    slabbed_value       NUMERIC,
    roi                 NUMERIC,
    verdict             TEXT,
    my_valuation        NUMERIC,
    grading_id          TEXT,
    is_slabbed          BOOLEAN DEFAULT FALSE,
    slab_cert_number    VARCHAR(30),
    slab_company        VARCHAR(10),
    slab_grade          VARCHAR(10),
    slab_label_type     VARCHAR(30),
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_collections_user_id ON collections(user_id);
```

**FK Dependencies:** `comic_registry.comic_id` references this table. Must cascade deletes through registry → sighting_reports → match_reports before deleting a collection item.

---

### 3. market_sales
Primary table for all sales data from multiple sources.

```sql
CREATE TABLE market_sales (
    id              SERIAL PRIMARY KEY,
    source          TEXT NOT NULL,           -- 'whatnot', 'ebay_auction', 'ebay_bin'
    title           TEXT,
    series          TEXT,
    issue           TEXT,
    grade           NUMERIC,
    grade_source    TEXT,                    -- 'cgc', 'cbcs', 'raw', 'vision'
    slab_type       TEXT,
    variant         TEXT,
    is_key          BOOLEAN DEFAULT FALSE,
    price           NUMERIC NOT NULL,
    sold_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    raw_title       TEXT,
    seller          TEXT,
    bids            INTEGER,
    viewers         INTEGER,
    image_url       TEXT,
    source_id       TEXT,
    upc_main        TEXT,
    upc_addon       TEXT,
    is_reprint      BOOLEAN,
    UNIQUE(source, source_id)
);

CREATE INDEX idx_market_sales_lookup ON market_sales(series, issue, grade);
CREATE INDEX idx_market_sales_recency ON market_sales(sold_at DESC);
CREATE INDEX idx_market_sales_source ON market_sales(source);
```

---

### 4. search_cache
Caches eBay valuation results (48-hour TTL).

```sql
CREATE TABLE search_cache (
    id                      SERIAL PRIMARY KEY,
    title                   TEXT,
    issue                   TEXT,
    search_key              TEXT,
    estimated_value         REAL,
    confidence              TEXT,
    confidence_score        INTEGER,
    num_sales               INTEGER,
    price_min               REAL,
    price_max               REAL,
    sales_data              TEXT,       -- JSON array of sales
    reasoning               TEXT,
    cached_at               TIMESTAMP,
    quick_sale              REAL,
    fair_value              REAL,
    high_end                REAL,
    lowest_bin              REAL,
    quick_sale_confidence   INTEGER,
    fair_value_confidence   INTEGER,
    high_end_confidence     INTEGER
);
```

---

### 5. comic_registry (Slab Guard)
Perceptual hash fingerprints for registered comics, enabling theft recovery.

```sql
CREATE TABLE comic_registry (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    comic_id                INTEGER NOT NULL REFERENCES collections(id),
    fingerprint_hash        VARCHAR(16) NOT NULL,
    fingerprint_composite   JSONB,
    fingerprint_algorithm   VARCHAR(20) DEFAULT 'comp_v3_edge',
    confidence_score        DECIMAL(5,2),
    serial_number           VARCHAR(20) UNIQUE NOT NULL,  -- Format: SW-2026-000001
    registration_date       TIMESTAMP DEFAULT NOW(),
    status                  VARCHAR(20) DEFAULT 'active',
    monitoring_enabled      BOOLEAN DEFAULT TRUE,
    certificate_url         TEXT,
    certificate_generated_at TIMESTAMP,
    reported_stolen_date    TIMESTAMP,
    police_report_number    VARCHAR(100),
    recovery_date           TIMESTAMP,
    recovery_notes          TEXT,
    notes                   TEXT,
    alert_email             VARCHAR(255),
    alert_phone             VARCHAR(20),
    slab_cert_number        VARCHAR(30),
    slab_company            VARCHAR(10),
    slab_label_type         VARCHAR(30),
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW(),
    UNIQUE(comic_id)
);

CREATE INDEX idx_comic_registry_fingerprint ON comic_registry(fingerprint_hash);
CREATE INDEX idx_comic_registry_user ON comic_registry(user_id);
CREATE INDEX idx_comic_registry_status ON comic_registry(status);
CREATE INDEX idx_comic_registry_serial ON comic_registry(serial_number);
```

---

### 6. sighting_reports
Public reports of spotted stolen comics.

```sql
CREATE TABLE sighting_reports (
    id              SERIAL PRIMARY KEY,
    serial_number   VARCHAR(20) NOT NULL REFERENCES comic_registry(serial_number),
    listing_url     TEXT NOT NULL,
    reporter_email  VARCHAR(255),
    message         TEXT,
    reporter_ip     VARCHAR(45),
    created_at      TIMESTAMP DEFAULT NOW(),
    owner_notified  BOOLEAN DEFAULT FALSE,
    owner_response  VARCHAR(50)
);
```

---

### 7. match_reports
Automated marketplace match reports from browser extension/API.

```sql
CREATE TABLE match_reports (
    id                  SERIAL PRIMARY KEY,
    registry_id         INTEGER REFERENCES comic_registry(id) ON DELETE CASCADE,
    reporter_user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    marketplace         VARCHAR(50) DEFAULT 'ebay',
    listing_url         TEXT NOT NULL,
    listing_item_id     VARCHAR(100),
    listing_image_url   TEXT,
    listing_fingerprint VARCHAR(16),
    hamming_distance    INTEGER,
    confidence_score    DECIMAL(5,2),
    status              VARCHAR(20) DEFAULT 'pending',
    reported_at         TIMESTAMP DEFAULT NOW(),
    reviewed_at         TIMESTAMP,
    reviewer_notes      TEXT
);
```

---

### 8. blocked_reporters
Rate-limited or blocked sighting reporters.

```sql
CREATE TABLE blocked_reporters (
    id          SERIAL PRIMARY KEY,
    ip_address  VARCHAR(45) NOT NULL UNIQUE,
    reason      VARCHAR(100) DEFAULT 'auto: rate limit exceeded',
    blocked_at  TIMESTAMP DEFAULT NOW(),
    expires_at  TIMESTAMP,
    blocked_by  VARCHAR(50) DEFAULT 'system'
);
```

---

### 9. ebay_tokens
eBay OAuth tokens for listing integration.

```sql
CREATE TABLE ebay_tokens (
    id              SERIAL PRIMARY KEY,
    user_id         TEXT UNIQUE NOT NULL,
    access_token    TEXT,
    refresh_token   TEXT,
    token_expiry    TIMESTAMP,
    ebay_username   TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### 10. password_resets

```sql
CREATE TABLE password_resets (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token       TEXT NOT NULL UNIQUE,
    expires_at  TIMESTAMP NOT NULL,
    used        BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

---

### 11. beta_codes

```sql
CREATE TABLE beta_codes (
    id              SERIAL PRIMARY KEY,
    code            TEXT UNIQUE NOT NULL,
    created_by      INTEGER REFERENCES users(id),
    uses_allowed    INTEGER DEFAULT 1,
    uses_remaining  INTEGER DEFAULT 1,
    expires_at      TIMESTAMPTZ,
    note            TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE
);
```

---

### 12. creator_signatures
Signature reference database for premium analysis.

```sql
CREATE TABLE creator_signatures (
    id                  SERIAL PRIMARY KEY,
    creator_name        VARCHAR(255) NOT NULL,
    role                VARCHAR(50),
    reference_image_url TEXT,
    signature_style     TEXT,
    verified            BOOLEAN DEFAULT FALSE,
    source              VARCHAR(255),
    notes               TEXT,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);
```

---

### 13. signature_images
Multiple reference images per creator signature.

```sql
CREATE TABLE signature_images (
    id          SERIAL PRIMARY KEY,
    creator_id  INTEGER REFERENCES creator_signatures(id) ON DELETE CASCADE,
    image_url   TEXT NOT NULL,
    era         VARCHAR(100),
    notes       TEXT,
    source      VARCHAR(255),
    created_at  TIMESTAMP DEFAULT NOW()
);
```

---

### 14. signature_matches
Links detected signatures to market sales.

```sql
CREATE TABLE signature_matches (
    id              SERIAL PRIMARY KEY,
    sale_id         INTEGER REFERENCES market_sales(id),
    signature_id    INTEGER REFERENCES creator_signatures(id),
    confidence      DECIMAL(3,2),
    match_method    VARCHAR(50),
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

### 15. waitlist

```sql
CREATE TABLE waitlist (
    id                  SERIAL PRIMARY KEY,
    email               TEXT UNIQUE NOT NULL,
    interests           TEXT[] DEFAULT '{}',
    verified            BOOLEAN DEFAULT FALSE,
    verification_token  TEXT,
    ip_address          TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    verified_at         TIMESTAMPTZ
);
```

---

### 16. Admin/Analytics Tables

```sql
-- Request logging
CREATE TABLE request_logs (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER REFERENCES users(id),
    endpoint            TEXT NOT NULL,
    method              TEXT NOT NULL,
    status_code         INTEGER,
    response_time_ms    INTEGER,
    error_message       TEXT,
    request_size_bytes  INTEGER,
    response_size_bytes INTEGER,
    user_agent          TEXT,
    ip_address          TEXT,
    device_type         TEXT,
    request_data        JSONB,
    response_summary    TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Anthropic API usage tracking
CREATE TABLE api_usage (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER REFERENCES users(id),
    endpoint            TEXT NOT NULL,
    model               TEXT,
    input_tokens        INTEGER DEFAULT 0,
    output_tokens       INTEGER DEFAULT 0,
    estimated_cost_usd  NUMERIC(10, 6),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Admin NLQ history
CREATE TABLE admin_nlq_history (
    id                  SERIAL PRIMARY KEY,
    admin_id            INTEGER REFERENCES users(id),
    natural_query       TEXT NOT NULL,
    generated_sql       TEXT,
    result_count        INTEGER,
    execution_time_ms   INTEGER,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Key Relationships

```
users ──┬── collections ──── comic_registry ──┬── sighting_reports
        │                                     └── match_reports
        ├── password_resets
        ├── beta_codes (created_by)
        ├── request_logs
        ├── api_usage
        └── admin_nlq_history

creator_signatures ──┬── signature_images
                     └── signature_matches ── market_sales
```

---

## Migration History

| Date | Migration | Description |
|------|-----------|-------------|
| Jan 25, 2026 | Initial | market_sales, search_cache (migrated from Supabase) |
| Feb 2026 | db_migrate_auth.py | users, password_resets, collections |
| Feb 2026 | db_migrate_beta.py | beta_codes, request_logs, api_usage, admin_nlq_history |
| Feb 2026 | db_migrate_slab_fields.py | Added slab columns to collections + comic_registry |
| Feb 2026 | db_migrate_sightings.py | sighting_reports, blocked_reporters |
| Feb 2026 | db_migrate_match_reports.py | match_reports |
| Feb 2026 | db_migrate_signatures.py | creator_signatures, signature_matches |
| Feb 2026 | db_migrate_signature_images.py | signature_images |
| Feb 2026 | db_migrate_composite_fingerprints.py | Added fingerprint_composite to comic_registry |
| Feb 2026 | db_migrate_waitlist.py | waitlist |
| Feb 2026 | db_migrate_billing.py | Added billing columns to users |
| Feb 2026 | db_migrate_profile.py | Added profile columns to users |
| Feb 2026 | db_migrate_facsimile.py | Added facsimile detection columns |

---

## Backup & Recovery

Render provides automatic backups for the Basic tier ($7/month).

Manual backup via pg_dump:
```bash
pg_dump "postgresql://user:pass@host:5432/db" > backup.sql
```
