# Where We Left Off - Mar 4, 2026

## Session 75 (Mar 4, 2026) — eBay Username Root Cause + Favicon Redesign

### eBay Username Bug — Root Cause Found & Fixed
**The mystery is solved:** OAuth scopes were missing `commerce.identity.readonly`.
- The eBay Identity API requires this scope to call `/commerce/identity/v1/user/`
- Without it, the API returned 403 — caught silently by try/except, username never saved
- The backfill in `/api/ebay/status` also failed for the same reason
- **Fix:** Added `commerce.identity.readonly` to `EBAY_SCOPES` in `ebay_oauth.py`
- Changed fallback text from "user" to "Connected" in collection.html and modal-ebay-listing.html
- **Action required:** Mike needs to disconnect and reconnect eBay after deploying to get a new token with the updated scope

### Favicon Redesign (In Progress)
- Current favicon: circle with gradient bg + gradient gold text → blurry/unreadable at 16px
- Created `favicon-options.html` comparison page with 6 options at 64/32/16px + tab simulations
- Options include: solid indigo, purple, dark bg, gradient bg — with white or gold text
- Both dark and light tab bar simulations included
- **Waiting for Mike's pick** before replacing `favicon.svg`

### Code Review: Draft + Auction Flows
- Reviewed `ebay_listing.py` `create_listing()` — draft flow (publish=False) creates inventory item + offer but skips publish, returns Seller Hub drafts URL
- Auction flow sends `start_price`, `auction_duration`, `reserve_price`, `buy_it_now_price` with proper validation
- Frontend `createListing(false)` for draft, `createListing(true)` for publish — both look clean
- No bugs found in code review — ready for live testing

### Files Modified This Session
- `ebay_oauth.py` — Added `commerce.identity.readonly` to EBAY_SCOPES
- `collection.html` — Changed username fallback from "user" to "Connected"
- `modal-ebay-listing.html` — Fixed `data.username` → `data.ebay_username`, fallback "Connected"
- `favicon-options.html` — New comparison page (6 favicon options)

### What's Next (Priority Order)
1. **Deploy + reconnect eBay** — verify username now displays correctly
2. **Pick favicon** — Mike to choose from options page, then replace favicon.svg
3. **Test fixed-price draft listing** — click "Save as Draft" instead of Publish
4. **Test auction listing** — toggle to Auction, set starting bid, duration, reserve, BIN
5. **Plan Whatnot integration** — research seller tools, design "Prep for Whatnot" feature
6. **Valuation endpoint testing** — 12-case test plan
7. **Mobile testing** — full grading flow on real devices

---

## Session 74 (Mar 4, 2026) — eBay Listing E2E: First Successful Publish!

### Major Milestone
**First successful eBay listing published via Slab Worthy!**
- Listing URL: https://www.ebay.com/itm/147183901233
- All 4 photos uploaded successfully via R2 proxy → eBay createImageFromUrl
- AI-generated description with Slab Worthy Assessment ID footer
- KEY ISSUE detection in listing titles working

### Bugs Fixed This Session (7 commits)

**1. eBay username not saving after OAuth (`routes/ebay.py`):**
- Added eBay Identity API call (`/commerce/identity/v1/user/`) in OAuth callback
- Saves username via `save_ebay_user_id()` after token exchange
- Added backfill logic in `/api/ebay/status` — if DB has no username, fetches from API and saves (self-healing for existing connections)

**2. OAuth callback redirect (`routes/ebay.py`):**
- Changed redirect from `{FRONTEND_URL}?ebay=connected` → `{FRONTEND_URL}/account.html?ebay=connected`
- Fixed stale default FRONTEND_URL from `collectioncalc.com` → `slabworthy.com`

**3. Grade type crash causing 500 on /api/ebay/list (`ebay_listing.py`):**
- Root cause: `grade.upper()` fails when grade is numeric (8.5, 9.8 float from JSON)
- Lines 322-323 were OUTSIDE the try/except block, so error returned HTML not JSON
- Fix: Added NUMERIC_TO_LETTER mapping for all CGC grades → eBay condition codes
- Listing title shows original numeric grade (e.g. "9.8") for buyer clarity

**4. closeUserMenu null reference (`js/auth.js`):**
- `document.getElementById('userMenuDropdown')` returns null on pages without the element
- Fix: added null check (`if (dropdown) dropdown.classList.remove(...)`)

**5. eBay URL policy violation (`collection.html`):**
- eBay flagged listings with slabworthy.com URL as "Offering to buy/sell outside eBay"
- Changed footer from full URL to just: `Slab Worthy™ Assessment ID: {id}`

**6. KEY ISSUE in listing title (`ebay_listing.py` + `collection.html`):**
- Frontend: after AI generates description, detects "KEY ISSUE" and updates title field
  e.g. "Iron Man #7 KEY ISSUE Comic Book - 6.5"
- User can still manually edit title before publishing
- Backend: accepts `listing_title` from frontend, uses it if provided

**7. Frontend title synced to backend (`routes/ebay.py` + `ebay_listing.py`):**
- Frontend sends user-editable `listingTitle` as `listing_title` in API call
- Backend uses provided title instead of auto-generating (respects user edits)
- Fallback auto-generation still works if no title provided

---

## Session 73 (Mar 3, 2026) — eBay Image Upload Debug Marathon

### Context
AWS UAE data center was struck by objects (drone/missile) on March 1, causing AWS outages
that affected Anthropic/Claude infrastructure throughout this session.

### What We Fixed
- Fixed photo URL mismatch (`currentComic.photos.*` vs flat properties)
- Fixed CORS by switching to server-side R2 proxy fetch
- Added `sell.marketing` OAuth scope
- Added disconnect endpoint + Connected Accounts UI to account.html
- Confirmed sidebar + footer working across all pages
