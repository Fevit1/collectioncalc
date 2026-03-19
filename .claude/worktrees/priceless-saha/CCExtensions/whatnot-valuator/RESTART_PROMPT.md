# Whatnot Comic Valuator - Restart Prompt

## Current Version: 2.40.1

## Quick Context
Chrome extension for real-time comic book valuation during Whatnot live auctions. Part of the **CollectionCalc** ecosystem. Captures sales data to CollectionCalc PostgreSQL database (on Render), uses Claude Vision API for comic identification, shows FMV from collected sales data.

**Key change in v2.40:** Migrated from Supabase to CollectionCalc backend. Extension now writes directly to CollectionCalc's PostgreSQL.

## Architecture
```
whatnot-valuator/
├── manifest.json          # v2.40.1, MV3 extension config
├── content.js             # Main overlay, auction monitoring, sale capture
├── background.js          # Service worker, badge updates
├── inject.js              # Apollo GraphQL cache reader (injected)
├── styles.css             # Overlay styling
├── popup.html/js          # Extension popup with stats
├── lib/
│   ├── apollo-reader.js   # Reads Whatnot's Apollo cache for listing data
│   ├── normalizer.js      # Parses comic titles → series/issue/grade
│   ├── valuator.js        # OLD static FMV database (deprecated, kept for reference)
│   ├── sale-tracker.js    # Local sale storage
│   ├── collectioncalc.js  # CollectionCalc API client (replaced supabase.js)
│   ├── vision.js          # Claude Vision API for comic scanning
│   └── audio.js           # Audio transcription (built but hidden from UI)
├── data/
│   └── keys.js            # Key issue database (500+ keys) + lookupKeyInfo()
├── CHANGELOG.md           # Version history
├── ROADMAP.md             # Feature roadmap and architecture
└── RESTART_PROMPT.md      # This file
```

## Key Features Working
1. **Overlay** - Draggable panel shows title, grade, price, FMV, verdict
2. **Apollo Reader** - Extracts listing data from Whatnot's GraphQL cache
3. **Sale Detection** - 30-sec debounce prevents duplicates when "Sold" text detected
4. **CollectionCalc Integration** - All sales pushed to CollectionCalc PostgreSQL
5. **Vision Scanning** - Claude API reads comics from video frames
6. **Auto-Scan** - Triggers when DOM has garbage titles (e.g., "Awesome comic on screen")
7. **Price-Drop Detection** - Detects new items when price resets (v2.39)
8. **Key Issue Lookup** - Local database of 500+ keys checked after Vision scan
9. **Multi-tab** - Works across multiple auction tabs simultaneously

## Database (CollectionCalc PostgreSQL on Render)

**Connection:** `collectioncalc.onrender.com`

### market_sales Table
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
```

### API Endpoints (wsgi.py)
- `POST /api/sales/record` - Record a sale from extension
- `GET /api/sales/count` - Get total sales count
- `GET /api/sales/recent` - Get recent sales

### Database Connection (DBeaver)
| Field | Value |
|-------|-------|
| Host | `dpg-d5knv4koud1c73dt21pg-a.oregon-postgres.render.com` |
| Port | `5432` |
| Database | `collectioncalc_db` |
| Username | `collectioncalc_db_user` |
| Password | (in Render dashboard) |

## Recent Session Changes (Jan 25, 2026)

### v2.39.1-2.39.3 - Bug Fixes
- Fixed stale listing detection (DOM title not updating between items)
- Added price-drop detection as new item signal
- Fixed duplicate scan bug with 10-second cooldown
- Added key issue database lookup after Vision scan
- Added Captain Marvel #1 and other keys to database

### v2.40.0-2.40.1 - CollectionCalc Migration
- **MAJOR: Replaced Supabase with CollectionCalc**
- Created `lib/collectioncalc.js` (same interface as old supabase.js)
- Migrated 618 historical sales to `market_sales` table
- Added API endpoints in wsgi.py
- Fixed API URL to point to Render directly (not Cloudflare frontend)

## grade_source Values
- `slab_label` / `cgc` / `cbcs` - Read from graded slab label (high confidence)
- `seller_verbal` - User typed what seller said (reliable)
- `vision_cover` / `vision` - Vision estimated from cover only (use with caution)
- `dom` / `raw` - From DOM condition field

## Known Issues / Limitations
1. Vision sees only video frame (one angle of front cover)
2. Raw grade estimates are cover-only - seller sees spine/back/pages
3. Audio transcription built but disabled (hard to time with seller)
4. Some sellers use garbage DOM titles requiring Vision scan
5. Stale DOM data - mitigated by price-drop detection

## API Keys Required
- **Anthropic** (Vision): Stored in chrome.storage.local as `anthropic_api_key`
- Cost: ~$0.01-0.03 per Vision scan

## Testing Commands
```javascript
// In browser console on Whatnot auction page:
window.ApolloReader.getCurrentListing()  // Get current listing from Apollo cache
window.lookupKeyInfo('Amazing Spider-Man', '300')  // Test key lookup
```

```bash
# Test CollectionCalc API:
curl https://collectioncalc.onrender.com/api/sales/count
# Returns: {"count": 618}
```

## Next Steps (Suggested)
1. **Unified FMV Engine** - Combine Whatnot + eBay data with intelligent weighting
2. **Friend Beta Prep** - Analytics, feedback link, landing copy
3. **Visual Tuning Dashboard** - Admin UI for FMV model parameters
4. **Audio Transcription** - Re-enable with better UX

## Files Location
- Extension source: /home/claude/whatnot-valuator/whatnot-valuator/
- Output zips: /mnt/user-data/outputs/
- Transcripts: /mnt/transcripts/

## Related Files (CollectionCalc Backend)
- wsgi.py - Flask API with sales endpoints
- ebay_valuation.py - eBay FMV calculation logic
- Database: search_cache, users, collections, market_sales

## User Context (Mike)
- 30+ years MarTech experience (eBay marketing, Adobe, Intuit)
- Product Manager, not hands-on developer
- Building CollectionCalc as proof-of-concept for Relevantsee principles
- Whatnot Valuator is unique data acquisition pipeline (competitive moat)
- Ultimate goal: Acquisition target for eBay or Amazon
