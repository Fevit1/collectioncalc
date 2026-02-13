# Comic Registry Database Schema

**Created:** February 12, 2026
**Purpose:** Store comic fingerprints for theft recovery and ownership verification
**Status:** Design phase - ready for implementation

---

## Table: `comic_registry`

### Purpose
Stores perceptual hash fingerprints for registered comics, linking to graded comics and enabling theft recovery through marketplace monitoring.

### Schema Definition

```sql
CREATE TABLE comic_registry (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Foreign Keys
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    comic_id INTEGER NOT NULL REFERENCES graded_comics(id) ON DELETE CASCADE,

    -- Fingerprint Data
    fingerprint_hash VARCHAR(16) NOT NULL,  -- 64-bit pHash as hex string (16 chars)
    fingerprint_algorithm VARCHAR(20) DEFAULT 'phash',  -- 'phash', 'sift', 'deep_learning'
    confidence_score DECIMAL(5,2),  -- 0.00 to 100.00

    -- Registration Info
    serial_number VARCHAR(20) UNIQUE NOT NULL,  -- Format: SW-2026-000001
    registration_date TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'reported_stolen', 'recovered', 'archived'

    -- Certificate
    certificate_url TEXT,  -- Cloudflare R2 URL for PDF certificate
    certificate_generated_at TIMESTAMP,

    -- Theft Reporting
    reported_stolen_date TIMESTAMP,
    police_report_number VARCHAR(100),
    recovery_date TIMESTAMP,
    recovery_notes TEXT,

    -- Metadata
    notes TEXT,  -- User notes about this registration
    monitoring_enabled BOOLEAN DEFAULT TRUE,  -- Enable marketplace monitoring
    alert_email VARCHAR(255),  -- Override email for alerts (defaults to user email)
    alert_phone VARCHAR(20),  -- Optional SMS alerts

    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    UNIQUE(comic_id)  -- Each comic can only be registered once
);
```

### Indexes for Performance

```sql
-- Fast fingerprint matching (billions of comparisons)
CREATE INDEX idx_comic_registry_fingerprint ON comic_registry(fingerprint_hash);

-- User lookups (my registered comics)
CREATE INDEX idx_comic_registry_user ON comic_registry(user_id);

-- Status filtering (active/stolen/recovered)
CREATE INDEX idx_comic_registry_status ON comic_registry(status);

-- Serial number lookups (certificate verification)
CREATE INDEX idx_comic_registry_serial ON comic_registry(serial_number);

-- Monitoring queries (comics with alerts enabled)
CREATE INDEX idx_comic_registry_monitoring ON comic_registry(monitoring_enabled) WHERE monitoring_enabled = TRUE;

-- Stolen comics queries
CREATE INDEX idx_comic_registry_stolen ON comic_registry(status, reported_stolen_date) WHERE status = 'reported_stolen';
```

---

## Field Descriptions

### Core Identification
- **id**: Auto-incrementing primary key
- **user_id**: Owner of the comic (links to users table)
- **comic_id**: The graded comic being registered (links to graded_comics table)

### Fingerprint Data
- **fingerprint_hash**: 64-bit pHash stored as 16-character hex string (e.g., "8f373714b7a1dfc3")
- **fingerprint_algorithm**: Algorithm used ('phash' for MVP, 'sift'/'deep_learning' for future)
- **confidence_score**: Quality score of fingerprint (0-100, higher = more defects = more unique)

### Registration Info
- **serial_number**: Human-readable unique ID (format: SW-2026-000001, SW-2026-000002, etc.)
- **registration_date**: When comic was registered
- **status**:
  - `active` - Normal registered comic
  - `reported_stolen` - Owner reported stolen
  - `recovered` - Comic was recovered after theft
  - `archived` - User deactivated registration

### Certificate
- **certificate_url**: Cloudflare R2 URL for downloadable PDF ownership certificate
- **certificate_generated_at**: When PDF was created

### Theft Reporting
- **reported_stolen_date**: When owner marked comic as stolen
- **police_report_number**: Optional police case number
- **recovery_date**: When comic was recovered
- **recovery_notes**: Details about recovery (e.g., "Found on eBay listing #...")

### Metadata
- **notes**: Free-text user notes (e.g., "Bought at SDCC 2024", "Part of collection insurance")
- **monitoring_enabled**: Whether to monitor marketplaces for this comic
- **alert_email**: Override email (defaults to user.email)
- **alert_phone**: Optional SMS alerts for high-value matches

### Audit
- **created_at**: Record creation timestamp
- **updated_at**: Last modification timestamp

---

## Relationships

### To `users` Table
```sql
user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
```
- One user can register many comics
- If user is deleted, their registrations are deleted (CASCADE)

### To `graded_comics` Table
```sql
comic_id INTEGER NOT NULL REFERENCES graded_comics(id) ON DELETE CASCADE
UNIQUE(comic_id)  -- Each comic can only be registered once
```
- One comic can have one registration
- Registration requires a graded comic (can't register without photos)
- If comic is deleted, registration is deleted (CASCADE)

---

## Serial Number Format

**Pattern:** `SW-YYYY-NNNNNN`

**Examples:**
- `SW-2026-000001` - First registration in 2026
- `SW-2026-000042` - 42nd registration
- `SW-2027-000001` - First registration in 2027 (resets yearly)

**Generation Logic:**
```python
def generate_serial_number():
    year = datetime.now().year
    # Get max serial for current year
    result = db.execute(
        "SELECT MAX(CAST(SUBSTRING(serial_number FROM 9) AS INTEGER)) "
        "FROM comic_registry WHERE serial_number LIKE :pattern",
        {"pattern": f"SW-{year}-%"}
    ).scalar()
    next_num = (result or 0) + 1
    return f"SW-{year}-{next_num:06d}"
```

---

## Common Queries

### Register a Comic
```sql
INSERT INTO comic_registry (
    user_id,
    comic_id,
    fingerprint_hash,
    serial_number,
    confidence_score
) VALUES (
    :user_id,
    :comic_id,
    :fingerprint_hash,
    :serial_number,
    :confidence_score
);
```

### Get User's Registered Comics
```sql
SELECT
    cr.serial_number,
    cr.registration_date,
    cr.status,
    gc.title,
    gc.issue_number,
    gc.grade,
    gc.photos
FROM comic_registry cr
JOIN graded_comics gc ON cr.comic_id = gc.id
WHERE cr.user_id = :user_id
ORDER BY cr.registration_date DESC;
```

### Find Matching Fingerprints (Theft Recovery)
```sql
-- Exact match (unlikely but check first)
SELECT * FROM comic_registry
WHERE fingerprint_hash = :query_hash
AND status = 'reported_stolen';

-- Similar matches (Hamming distance <= 10 bits)
-- Note: This is a naive approach. In production, use specialized indexing (BK-tree, VP-tree)
SELECT
    cr.*,
    u.email as owner_email,
    gc.title,
    gc.issue_number
FROM comic_registry cr
JOIN users u ON cr.user_id = u.id
JOIN graded_comics gc ON cr.comic_id = gc.id
WHERE cr.status = 'reported_stolen'
AND cr.monitoring_enabled = TRUE
-- Hamming distance calculation would happen in Python
ORDER BY cr.reported_stolen_date DESC;
```

### Report Comic as Stolen
```sql
UPDATE comic_registry
SET
    status = 'reported_stolen',
    reported_stolen_date = NOW(),
    police_report_number = :report_number
WHERE id = :registry_id
AND user_id = :user_id;  -- Security: only owner can report
```

### Mark Comic as Recovered
```sql
UPDATE comic_registry
SET
    status = 'recovered',
    recovery_date = NOW(),
    recovery_notes = :notes
WHERE id = :registry_id
AND user_id = :user_id;
```

### Get All Active Registrations (for marketplace monitoring)
```sql
SELECT
    id,
    fingerprint_hash,
    serial_number,
    user_id,
    comic_id
FROM comic_registry
WHERE status = 'active'
AND monitoring_enabled = TRUE;
```

---

## Migration SQL

### Create Table
```sql
-- Run this in Render PostgreSQL console or via migration script

CREATE TABLE comic_registry (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    comic_id INTEGER NOT NULL REFERENCES graded_comics(id) ON DELETE CASCADE,
    fingerprint_hash VARCHAR(16) NOT NULL,
    fingerprint_algorithm VARCHAR(20) DEFAULT 'phash',
    confidence_score DECIMAL(5,2),
    serial_number VARCHAR(20) UNIQUE NOT NULL,
    registration_date TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active',
    certificate_url TEXT,
    certificate_generated_at TIMESTAMP,
    reported_stolen_date TIMESTAMP,
    police_report_number VARCHAR(100),
    recovery_date TIMESTAMP,
    recovery_notes TEXT,
    notes TEXT,
    monitoring_enabled BOOLEAN DEFAULT TRUE,
    alert_email VARCHAR(255),
    alert_phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(comic_id)
);

CREATE INDEX idx_comic_registry_fingerprint ON comic_registry(fingerprint_hash);
CREATE INDEX idx_comic_registry_user ON comic_registry(user_id);
CREATE INDEX idx_comic_registry_status ON comic_registry(status);
CREATE INDEX idx_comic_registry_serial ON comic_registry(serial_number);
CREATE INDEX idx_comic_registry_monitoring ON comic_registry(monitoring_enabled) WHERE monitoring_enabled = TRUE;
CREATE INDEX idx_comic_registry_stolen ON comic_registry(status, reported_stolen_date) WHERE status = 'reported_stolen';
```

### Rollback
```sql
DROP TABLE IF EXISTS comic_registry CASCADE;
```

---

## Data Size Estimates

### Storage Per Record
- Base row: ~500 bytes
- With indexes: ~1KB per registration

### Scale Projections
- 1,000 users × 100 comics = 100,000 registrations = 100MB
- 10,000 users × 100 comics = 1M registrations = 1GB
- 100,000 users × 100 comics = 10M registrations = 10GB

**Conclusion:** Storage is not a concern. Query performance on fingerprint matching will be the bottleneck.

---

## Performance Considerations

### Fingerprint Matching Challenge
**Problem:** Need to find similar hashes (Hamming distance <= 10) among millions of registrations.

**Naive Approach (MVP):**
```python
# O(n) - Check every registered comic
for registered in all_registrations:
    distance = hamming_distance(query_hash, registered.fingerprint_hash)
    if distance <= 10:
        matches.append(registered)
```

**Optimized Approach (Future):**
- **BK-Tree** - Metric tree for Hamming distance queries (O(log n))
- **VP-Tree** - Vantage point tree for similarity search
- **LSH** - Locality-sensitive hashing for approximate matching
- **Postgres Extensions** - pg_similarity or custom C extension

**MVP Decision:** Start naive. Optimize when we hit 100k+ registrations.

---

## Security Considerations

### Access Control
```python
# Only owner can register their comics
if comic.user_id != current_user.id:
    abort(403, "You can only register your own comics")

# Only owner can report stolen
if registry.user_id != current_user.id:
    abort(403, "You can only report your own comics as stolen")

# Only owner (or admin) can mark recovered
if registry.user_id != current_user.id and not current_user.is_admin:
    abort(403, "Unauthorized")
```

### Data Retention
- Active registrations: Keep indefinitely
- Recovered comics: Keep for 1 year after recovery (audit trail)
- Archived registrations: Keep for 90 days, then hard delete
- User deletion: CASCADE deletes all their registrations

### Privacy
- Fingerprint hashes are NOT personally identifiable
- Owner contact info only shared with law enforcement upon valid request
- Marketplace matches trigger alerts, but don't expose owner publicly

---

## API Endpoints (Future)

### Register Comic
```
POST /api/registry/register
Body: { comic_id: 123 }
Response: {
    serial_number: "SW-2026-000042",
    certificate_url: "https://r2.../certificates/SW-2026-000042.pdf",
    fingerprint_hash: "8f373714b7a1dfc3",
    confidence_score: 87.5
}
```

### Get My Registrations
```
GET /api/registry/mine
Response: [
    {
        serial_number: "SW-2026-000042",
        registration_date: "2026-02-12T10:30:00Z",
        status: "active",
        comic: { title: "Iron Man", issue: 200, grade: 8.5 }
    }
]
```

### Report Stolen
```
POST /api/registry/:serial/report-stolen
Body: { police_report_number: "PD2026-1234" }
Response: { status: "reported_stolen", monitoring_enabled: true }
```

### Check for Matches (Marketplace Integration)
```
POST /api/registry/check-match
Body: { fingerprint_hash: "8f373714b7a1dfc3" }
Response: {
    match_found: true,
    confidence: 95.2,
    serial_number: "SW-2026-000042",
    status: "reported_stolen",
    reported_date: "2026-02-10T14:00:00Z"
}
```

---

## Next Steps

### Week 3 (Database Setup)
1. Run migration to create `comic_registry` table
2. Add indexes for performance
3. Test with sample data
4. Verify foreign key constraints

### Week 4 (MVP Implementation)
1. Add pHash generation to grading pipeline
2. Create "Register" button in grade report
3. Generate serial numbers on registration
4. Create ownership certificate PDF
5. Display registered comics in My Collection

### Month 2 (Monitoring System)
1. Build fingerprint matching algorithm
2. Implement marketplace scrapers
3. Email alert system
4. Admin dashboard for reviewing matches

---

## Related Files
- `/V2/comic_fingerprint_test.py` - Proof-of-concept pHash testing
- `/V2/FINGERPRINT_TEST_RESULTS.txt` - Validation results
- `/V2/provisional_patent_comic_fingerprinting.docx` - Patent application
- `/V2/FINGERPRINTING_PROJECT_SUMMARY.md` - Business plan

---

*Schema designed: February 12, 2026*
*Ready for implementation: Week 3 (Feb 2026)*
*Patent pending: 63/XXX,XXX (awaiting serial number)*
