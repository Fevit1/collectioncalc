# Slab Guard Monitor — Chrome Extension Plan

## Overview
Build a single Chrome extension ("Slab Guard Monitor") that lets owners, police, and comic store owners watch eBay listings for stolen comics registered with Slab Guard. Includes both auto-scanning of visible listings and a manual "Check this listing" button.

---

## Part 1: New Backend API Endpoints

Before the extension can work, the server needs a fingerprint-matching API.

### New route file: `routes/monitor.py`

**1. `POST /api/monitor/check-image`** (public, rate-limited)
- Accepts: `{ image_url: "https://i.ebayimg.com/..." }`
- Downloads image, generates pHash
- Compares against all `comic_registry` entries using Hamming distance
- Returns matches with confidence scores
- Response: `{ matches: [{ serial_number, title, issue, grade, status, confidence, hamming_distance, owner_display }] }`
- Threshold: ≤10 bits = HIGH match, 11-20 = POSSIBLE, >20 = no match

**2. `POST /api/monitor/check-hash`** (public, rate-limited)
- Accepts: `{ fingerprint_hash: "8f373714b7a1dfc3" }`
- Same comparison logic but skips image download (for pre-computed hashes)
- Faster for batch scanning

**3. `GET /api/monitor/stolen-hashes`** (API-key auth)
- Returns all fingerprint hashes where `status = 'reported_stolen'`
- Used by extension to cache stolen hashes locally for faster client-side pre-filtering
- Only returns hashes + serial numbers (no PII)

**4. `POST /api/monitor/report-match`** (requires auth)
- Accepts: `{ serial_number, ebay_listing_url, ebay_item_id, match_confidence }`
- Creates a `match_reports` record
- Sends email alert to comic owner
- Response: confirmation

### New DB table: `match_reports`
```sql
CREATE TABLE match_reports (
    id SERIAL PRIMARY KEY,
    registry_id INTEGER REFERENCES comic_registry(id),
    reporter_user_id INTEGER REFERENCES users(id),
    marketplace VARCHAR(50) DEFAULT 'ebay',
    listing_url TEXT NOT NULL,
    listing_item_id VARCHAR(100),
    listing_image_url TEXT,
    listing_fingerprint VARCHAR(16),
    hamming_distance INTEGER,
    confidence_score DECIMAL(5,2),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, confirmed, dismissed
    reported_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    reviewer_notes TEXT
);
```

---

## Part 2: Chrome Extension Structure

### File structure
```
CCExtensions/slab-guard-monitor/
├── manifest.json          # MV3 manifest
├── content.js             # Injected into eBay pages — auto-scan + manual check button
├── background.js          # Service worker — manages cached stolen hashes, periodic refresh
├── popup.html             # Extension popup — login, role selector, status, recent matches
├── popup.js               # Popup logic
├── popup.css              # Popup styles (Slab Worthy brand colors)
├── options.html           # Settings page — scan sensitivity, notification preferences
├── options.js             # Settings logic
├── icons/
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── lib/
    └── phash-js.js        # Client-side pHash (optional, for pre-filtering without API call)
```

### manifest.json highlights
- `host_permissions`: `https://www.ebay.com/*`, `https://slabworthy.com/*`, `https://collectioncalc-docker.onrender.com/*`
- `permissions`: `storage`, `activeTab`, `alarms` (for periodic hash refresh)
- Content script matches: `https://www.ebay.com/sch/*`, `https://www.ebay.com/itm/*`
- Background service worker for hash caching

---

## Part 3: Extension Features by Component

### A. Content Script (content.js) — eBay Pages

**Auto-scan mode (search results pages):**
1. Detects when user is browsing eBay search results
2. Extracts listing image URLs from visible cards (reuse selectors from ebay-collector)
3. For each image: sends to `/api/monitor/check-image`
4. If match found: overlays a red/yellow/green shield badge on the listing card
   - RED shield: "REPORTED STOLEN" (status = reported_stolen, hamming ≤ 10)
   - YELLOW shield: "Possible Match" (hamming 11-20)
   - GREEN shield: "Registered ✓" (active registration, not stolen)
5. Rate-limited: max 10 checks per page load, throttled 500ms apart

**Manual check (individual listing pages):**
1. On `ebay.com/itm/*` pages, inject a floating "🛡️ Check with Slab Guard" button
2. Click → grabs the main listing image → sends to API
3. Shows result in an overlay panel:
   - No match: "Not found in Slab Guard registry"
   - Match: Shows comic details, serial number, status, confidence %
   - If stolen: prominent red alert + "Report this match" button

**Visual overlays:**
- Small shield icon badges on listing cards (colored by match status)
- Slide-in panel for detailed results on individual listings
- Toast notifications for scan progress

### B. Background Service Worker (background.js)

1. On install/alarm: fetch `/api/monitor/stolen-hashes` → cache in chrome.storage.local
2. Refresh stolen hash cache every 6 hours via `chrome.alarms`
3. Content script can do quick client-side pre-filter against cached hashes before hitting API
4. Manages API key storage after login

### C. Popup (popup.html/js)

**Logged out state:**
- Slab Guard branding
- Login form (email/password → gets JWT from slabworthy.com auth)
- "Don't have an account? Sign up at slabworthy.com"

**Logged in state — Role tabs:**

**Owner tab:**
- "My Registered Comics" count
- Recent match alerts (any listings matching their comics)
- Quick link to slabworthy.com/verify
- Toggle auto-scan on/off

**Dealer tab (comic store owners):**
- "Verify Before You Buy" — paste a serial number to check
- Scan mode toggle
- Recent checks history

**Law Enforcement tab:**
- Total stolen comics in registry
- Search by serial number
- Bulk check tool (paste multiple image URLs)
- Contact info for Slab Worthy support

**All roles:**
- Settings gear → opens options page
- Scan statistics (X listings checked today)
- Badge count on extension icon showing unreviewed matches

### D. Options Page (options.html/js)

- Auto-scan: ON/OFF
- Scan sensitivity: High (≤15 bits) / Medium (≤10 bits) / Low (≤5 bits)
- Notifications: Desktop notifications for matches ON/OFF
- Sound alert for stolen matches ON/OFF
- Check frequency for hash cache refresh

---

## Part 4: Build Order

### Step 1 — Backend API (build first)
1. Create `routes/monitor.py` with check-image, check-hash, stolen-hashes endpoints
2. Create `match_reports` DB migration
3. Register blueprint in wsgi.py
4. Test with curl/Postman

### Step 2 — Extension Skeleton
1. Create manifest.json, popup, icons
2. Implement login flow (reuse JWT auth from slabworthy.com)
3. Build popup UI with role tabs
4. Basic "Check this listing" manual button on eBay item pages

### Step 3 — Manual Check Feature
1. Content script on `ebay.com/itm/*` pages
2. Grab listing image, call check-image API
3. Display results overlay panel
4. "Report match" button → calls report-match API

### Step 4 — Auto-Scan Feature
1. Content script on `ebay.com/sch/*` pages
2. Extract listing images from search results
3. Throttled batch checking
4. Shield badge overlays on listing cards
5. Background hash caching for pre-filtering

### Step 5 — Alerts & Notifications
1. Email alerts to owners when match reported
2. Chrome desktop notifications
3. Badge count on extension icon
4. Match history in popup

---

## Part 5: Technical Notes

- **Rate limiting**: Server-side rate limit on check-image (e.g., 60/min per IP). Extension throttles client-side too.
- **Image fetching**: eBay images are public CDN URLs (i.ebayimg.com), so downloading for pHash is straightforward.
- **Hamming distance**: Calculated in Python as `bin(int(hash1, 16) ^ int(hash2, 16)).count('1')` — O(n) against all registered comics is fine for MVP (<100k registrations).
- **Privacy**: Match results never expose owner email. Only hashed display name shown. Full contact only via official Slab Worthy channels.
- **Brand consistency**: Extension uses Slab Worthy purple gradient (#667eea → #764ba2), shield icon, same typography.
