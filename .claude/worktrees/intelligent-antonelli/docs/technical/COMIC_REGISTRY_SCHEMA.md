# Comic Registry Database Schema (Slab Guard)

**Created:** February 12, 2026
**Status:** LIVE — Fully implemented and deployed
**Last updated:** February 28, 2026 (Session 69)

---

## Table: `comic_registry`

### Purpose
Stores perceptual hash fingerprints for registered comics, linking to user collections and enabling theft recovery through marketplace monitoring.

### Schema Definition

```sql
CREATE TABLE comic_registry (
    id                      SERIAL PRIMARY KEY,

    -- Foreign Keys (NOTE: references collections, not graded_comics)
    user_id                 INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    comic_id                INTEGER NOT NULL REFERENCES collections(id),

    -- Fingerprint Data
    fingerprint_hash        VARCHAR(16) NOT NULL,       -- 64-bit pHash as hex string
    fingerprint_composite   JSONB,                      -- Multi-algorithm composite fingerprint
    fingerprint_algorithm   VARCHAR(20) DEFAULT 'comp_v3_edge',
    confidence_score        DECIMAL(5,2),               -- 0.00 to 100.00

    -- Registration Info
    serial_number           VARCHAR(20) UNIQUE NOT NULL, -- Format: SW-2026-000001
    registration_date       TIMESTAMP DEFAULT NOW(),
    status                  VARCHAR(20) DEFAULT 'active',

    -- Monitoring
    monitoring_enabled      BOOLEAN DEFAULT TRUE,

    -- Certificate
    certificate_url         TEXT,
    certificate_generated_at TIMESTAMP,

    -- Theft Reporting
    reported_stolen_date    TIMESTAMP,
    police_report_number    VARCHAR(100),
    recovery_date           TIMESTAMP,
    recovery_notes          TEXT,

    -- Metadata
    notes                   TEXT,
    alert_email             VARCHAR(255),
    alert_phone             VARCHAR(20),

    -- Slab info (denormalized from collections for quick lookups)
    slab_cert_number        VARCHAR(30),
    slab_company            VARCHAR(10),
    slab_label_type         VARCHAR(30),

    -- Audit
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW(),

    UNIQUE(comic_id)
);
```

### Indexes
```sql
CREATE INDEX idx_comic_registry_fingerprint ON comic_registry(fingerprint_hash);
CREATE INDEX idx_comic_registry_user ON comic_registry(user_id);
CREATE INDEX idx_comic_registry_status ON comic_registry(status);
CREATE INDEX idx_comic_registry_serial ON comic_registry(serial_number);
CREATE INDEX idx_comic_registry_monitoring ON comic_registry(monitoring_enabled) WHERE monitoring_enabled = TRUE;
CREATE INDEX idx_comic_registry_stolen ON comic_registry(status, reported_stolen_date) WHERE status = 'reported_stolen';
```

---

## Related Tables

### sighting_reports
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

### match_reports
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

### blocked_reporters
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

## Relationships

### To `users` Table
- One user can register many comics
- CASCADE: User deleted → registrations deleted

### To `collections` Table (NOT graded_comics)
- `comic_id INTEGER NOT NULL REFERENCES collections(id)`
- One comic can have one registration (UNIQUE constraint)
- **WARNING:** No ON DELETE CASCADE — must manually delete registry entries before deleting collection items. See `routes/collection.py` `api_delete_collection_item()` for the cascade logic using savepoints.

---

## API Endpoints (LIVE)

### Register Comic
```
POST /api/registry/register         [auth+approved]
Body: { comic_id: 123 }
```

### Get Registration Status
```
GET /api/registry/status/<comic_id> [auth+approved]
```

### Get My Sightings
```
GET /api/registry/my-sightings      [auth]
```

### Respond to Sighting
```
POST /api/registry/sighting-response [auth]
```

### Verify Serial (Public)
```
GET/POST /api/verify/lookup/<serial_number>  [Turnstile protected]
```

### Report Sighting (Public)
```
POST /api/verify/report-sighting    [rate-limited]
```

### Marketplace Monitoring
```
POST /api/monitor/check-image       → fingerprint matching
POST /api/monitor/check-hash        → hash comparison
GET  /api/monitor/stolen-hashes     → stolen hash list
POST /api/monitor/report-match      → match reporting
POST /api/monitor/compare-copies    → copy comparison
```

---

## Serial Number Format

**Pattern:** `SW-YYYY-NNNNNN`
- `SW-2026-000001` — First registration in 2026
- `SW-2026-000042` — 42nd registration

---

## Status Values
- `active` — Normal registered comic
- `reported_stolen` — Owner reported stolen
- `recovered` — Comic was recovered after theft
- `archived` — User deactivated registration

---

*Schema live since: February 2026*
*Patent pending: 63/XXX,XXX*
