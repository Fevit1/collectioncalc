# Changelog

All notable changes to the Whatnot Comic Valuator extension.

## [2.40.2] - 2026-01-25

### Fixed
- Double-scan bug - now tracks by `listing.id` instead of title
- Added `lastScannedListingId` for 30-second scan protection per listing
- Price-drop scans now respect the listing.id cooldown

## [2.40.1] - 2026-01-25

### Changed
- Fixed API URL to point to `collectioncalc.onrender.com` (bypasses Cloudflare frontend)

## [2.40.0] - 2026-01-25

### Changed
- **MAJOR: Migrated from Supabase to CollectionCalc API**
- Replaced `lib/supabase.js` with `lib/collectioncalc.js`
- Sales now write directly to CollectionCalc PostgreSQL database
- 618 historical sales migrated to new `market_sales` table

### Added
- New CollectionCalc API client with same interface as Supabase
- `getSalesCount()` function

### Removed
- Supabase dependency completely removed
- No longer need Supabase account or API keys

## [2.39.3] - 2026-01-25

### Added
- Local key issue database lookup after Vision scan
- Added Captain Marvel #1 entries to keys database
- `lookupKeyInfo()` function checks local database if Vision misses key info

### Fixed
- Key issues now detected even when Vision doesn't mention them
- Captain Marvel #1, Marvel Super-Heroes #12-13 added to database

## [2.39.2] - 2026-01-25

### Fixed
- Duplicate scan bug - added 10-second cooldown after force-scanning
- `scanCooldownUntil` prevents multiple scans when title updates mid-scan

## [2.39.1] - 2026-01-25

### Fixed
- Stale listing detection - DOM title wasn't updating between auction items
- Added price-drop detection as secondary signal for new items
- Force scan when price drops >50% and resets under $20
- Reset scan tracking flags (`lastAutoScanId`, `pendingAutoScanKey`, `isScanning`) on new item

## [2.39.0] - 2026-01-24

### Added
- Last Scan card now always shows (even on errors)
- `showScanError()` function displays error with thumbnail
- Helps debug why scans fail

## [2.36.0] - 2026-01-24

### Added
- Auto-scan now defaults to ON
- Scanned images saved to Supabase Storage
- `image_url` field in database stores comic scan images
- `uploadImage()` function in supabase.js

### Database Migration Required
```sql
ALTER TABLE whatnot_sales ADD COLUMN IF NOT EXISTS image_url TEXT;
```

### Supabase Storage Setup Required
1. Create a storage bucket named `comic-scans`
2. Set bucket to public (for image URLs to work)
3. Add RLS policy allowing anon inserts

## [2.35.2] - 2026-01-24

### Fixed
- Added video check to `handleVisionScan` (prevents error on manual scan)
- Changed vision.js `console.error` to `console.log` (cleaner extension page)

### Database Migration Required
```sql
ALTER TABLE whatnot_sales ADD COLUMN IF NOT EXISTS seller TEXT;
ALTER TABLE whatnot_sales ADD COLUMN IF NOT EXISTS platform TEXT DEFAULT 'whatnot';
```

## [2.35.1] - 2026-01-24

### Fixed
- Auto-scan no longer triggers on pages without video (homepage, etc.)
- Added video element check before attempting scan

## [2.35.0] - 2026-01-24

### Changed
- Auto-scan now waits for bidding to start before triggering
- Queues scan when listing detected, triggers when bids > 0 or timer starts
- More reliable scanning during live auctions

### Added
- `isBiddingActive()` function checks: bid count, timer, "Winning" text
- `checkPendingAutoScan()` monitors queued scans for bid state changes
- Better console logging: "🕐 Auto-scan queued (waiting for bidding)"

## [2.34.0] - 2026-01-24

### Added
- Raw comic grade estimates from Vision (with "cover-only" warning)
- `vision_cover` grade source for cover-only estimates
- Clear UI labeling: "Grade: ~8.0 (cover only)"

### Changed
- Vision prompt now estimates raw grades with low confidence (0.3-0.5)
- Grade display shows `~` prefix for cover estimates

## [2.33.0] - 2026-01-24

### Fixed
- Skip FMV query for garbage titles (was showing misleading data)
- Show "FMV: Scan needed" instead of querying meaningless titles

## [2.32.0] - 2026-01-24

### Fixed
- Removed misleading static key notes (e.g., wrong "1st Fantastic Four" display)
- Key info now only shows from Vision scan results

## [2.31.0] - 2026-01-24

### Changed
- Smart auto-scan: skips when DOM has good data (title + issue)
- Respects seller data over Vision when available

## [2.30.0] - 2026-01-24

### Changed
- Auto-scan triggers on ALL new listings (when enabled)
- Added 1.5 second delay for video stabilization

## [2.29.0] - 2026-01-24

### Added
- Real FMV from Supabase sales data
- `getFMV()` function queries actual recorded sales
- Shows price range and sale count: "FMV: $25-$100 (5 sales)"
- Verdict based on real market data

### Changed
- Deprecated static FMV database
- FMV now shows "No sales data" when no matches found

## [2.28.0] - 2026-01-24

### Added
- Auto-scan toggle checkbox
- Smart garbage title detection
- Auto-triggers Vision when DOM title is placeholder

### Removed
- Audio button (🎤 Hear) from UI (backend kept for future)

## [2.27.0] - 2026-01-24

### Fixed
- Vision data now persists for sale recording
- Applied Vision title/issue used instead of DOM garbage
- Clear manual grade after sale recorded

## [2.26.0] - 2026-01-24

### Added
- Variant field in database and UI
- Variant detection: newsstand, price variants (35¢, 30¢), virgin, sketch, ratio variants, reprints
- Vision prompt updated to detect variants

## [2.25.0] - 2026-01-24

### Added
- Audio capture module (lib/audio.js)
- OpenAI Whisper integration for transcription
- Grade parsing from speech
- 🎤 Hear button (later removed in v2.28)
- `grade_source` field tracking

## [2.24.0] - 2026-01-24

### Changed
- Vision no longer estimates raw grades
- Show "Raw comic - use seller's grade" message
- Added coverNote field for visual observations

## [2.23.0] - 2026-01-24

### Added
- Raw grade estimation from Vision (later reverted)
- Grade confidence display

## [2.22.0] - 2026-01-24

### Added
- Vision scanning with Claude API (lib/vision.js)
- 📷 Scan button
- ⚙️ Settings button for API key
- Video frame capture to base64
- Vision result card with Apply/Dismiss
- API key storage in chrome.storage.local

## [2.21.0] - 2026-01-24

### Added
- Slab type detection (CGC, CBCS, PGX)
- `slab_type` field in database
- Auto-extract grade from slab titles (e.g., "CGC 9.8")

## [2.20.0] - 2026-01-24

### Added
- Viewer count capture
- `viewers` field in database

### Fixed
- Title parsing handles "Black Panther 1" format
- Issue extraction for both "#1" and trailing " 1"

## [2.19.0] - 2026-01-24

### Added
- Bids field capture
- 30-second debounce for sale detection

### Fixed
- Duplicate sales from persistent "Sold" text
- Expanded bad title blocklist: lot, choice, pick, mystery, bundle, buck, comic book

## [2.18.0] - Previous Session

### Added
- Multi-tab passive collection
- Supabase cloud integration
- Extension popup with stats

---

## Architecture Change (v2.40.0+)

**The extension no longer uses Supabase.** Sales data is now stored in CollectionCalc's PostgreSQL database on Render.

### New Database: CollectionCalc (Render PostgreSQL)

Connection: `collectioncalc.onrender.com`

**market_sales table:**
```sql
CREATE TABLE market_sales (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,              -- 'whatnot', 'ebay_auction', 'ebay_bin', 'pricecharting'
    title TEXT,
    series TEXT,
    issue TEXT,                        -- TEXT to handle "1A", "300B" variants
    grade NUMERIC,
    grade_source TEXT,                 -- 'cgc', 'cbcs', 'raw', 'vision'
    slab_type TEXT,
    variant TEXT,
    is_key BOOLEAN DEFAULT FALSE,
    price NUMERIC NOT NULL,
    sold_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    raw_title TEXT,
    seller TEXT,
    bids INTEGER,
    viewers INTEGER,
    image_url TEXT,
    source_id TEXT,                    -- External ID for deduplication
    UNIQUE(source, source_id)
);

CREATE INDEX idx_market_sales_lookup ON market_sales(series, issue, grade);
CREATE INDEX idx_market_sales_recency ON market_sales(sold_at DESC);
CREATE INDEX idx_market_sales_source ON market_sales(source);
```

### API Endpoints

- `POST /api/sales/record` - Record a sale
- `GET /api/sales/count` - Get total sales count
- `GET /api/sales/recent` - Get recent sales

---

## Legacy Database Migrations (Supabase - Pre v2.40)

These are historical and no longer needed for new installs:

```sql
-- v2.19+
ALTER TABLE whatnot_sales ADD COLUMN IF NOT EXISTS bids INTEGER;

-- v2.20+
ALTER TABLE whatnot_sales ADD COLUMN IF NOT EXISTS viewers INTEGER;

-- v2.21+
ALTER TABLE whatnot_sales ADD COLUMN IF NOT EXISTS slab_type TEXT;

-- v2.25+
ALTER TABLE whatnot_sales ADD COLUMN IF NOT EXISTS grade_source TEXT;

-- v2.26+
ALTER TABLE whatnot_sales ADD COLUMN IF NOT EXISTS variant TEXT;

-- v2.35+
ALTER TABLE whatnot_sales ADD COLUMN IF NOT EXISTS seller TEXT;
ALTER TABLE whatnot_sales ADD COLUMN IF NOT EXISTS platform TEXT DEFAULT 'whatnot';

-- v2.36+
ALTER TABLE whatnot_sales ADD COLUMN IF NOT EXISTS image_url TEXT;
```

## Data Cleanup

Remove garbage-titled records:

```sql
DELETE FROM market_sales 
WHERE title ILIKE '%awesome comic%' 
   OR title ILIKE '%comic on screen%'
   OR title ILIKE '%comic book on screen%';
```
