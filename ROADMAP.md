# CollectionCalc Roadmap

## Vision

**CollectionCalc is a multi-collectible valuation platform.** 

Comics are the first vertical. Future expansion includes:
- Sports cards (baseball, basketball, football, hockey)
- Trading card games (Pokémon, Magic: The Gathering, Yu-Gi-Oh!)
- Coins & numismatics
- Stamps
- Vinyl records
- Video games
- Sneakers
- Watches

Our goal: Build the most accurate, user-informed valuation tool by combining real market data with community feedback - across ALL collectibles.

**Competitive Moat:** Live auction data from Whatnot Valuator extension gives us unique, real-time price discovery data that competitors don't have.

---

## Completed ✅

### Phase 0: Core MVP
- [x] Database schema (SQLite → PostgreSQL)
- [x] Basic valuation model with grade adjustments
- [x] Comic lookup system
- [x] API server (Flask)
- [x] Deployed to Render
- [x] Basic frontend UI

### Phase 1: Infrastructure
- [x] GitHub repo setup
- [x] CORS support for frontend
- [x] Health check endpoints
- [x] Error handling
- [x] Frontend hosted on Cloudflare Pages
- [x] Backend hosted on Render

### Phase 2: eBay-Powered Valuation Model ✅
Real market data with intelligent weighting.

- [x] AI web search for market prices (eBay, GoCollect, etc.)
- [x] Parse recent sale prices with dates and grades
- [x] Recency weighting (this week 100% → older 25%)
- [x] Volume-based confidence scoring
- [x] Price variance analysis
- [x] Database + market data blending
- [x] 48-hour result caching for consistency
- [x] Title alias table (ASM → Amazing Spider-Man)
- [x] AI spelling correction ("Captian" → "Captain")

### Phase 2.5: Brand & UX ✅
- [x] Brand guidelines document (Option 3: Dark + Gradient)
- [x] New color scheme (Indigo/Purple/Cyan)
- [x] Animated calculator loading icon
- [x] Thinking steps display
- [x] Price formatting with commas

### Phase 2.7: Three-Tier Pricing ✅
Actionable pricing for different selling scenarios.

- [x] Three-tier valuation display:
  - **Quick Sale** - Lowest BIN or floor price (sell fast)
  - **Fair Value** - Median sold price (market value)
  - **High End** - Maximum recent sold (premium/patient seller)
- [x] Buy It Now price integration (current market ceiling)
- [x] Tighter grade filtering (±0.5 grade tolerance)
- [x] Cache now stores all pricing tiers
- [x] PostgreSQL database migration (from SQLite)
- [x] Per-tier confidence scoring

### Phase 2.8: eBay Listing Integration ✅ (January 19, 2026)
**MILESTONE: First live eBay listing created from CollectionCalc!**

One-click listing from valuation results.

- [x] eBay Developer account registered
- [x] eBay Developer API approved
- [x] OAuth flow for user eBay accounts (Production)
- [x] "List on eBay" buttons (3 price tiers)
- [x] AI-generated descriptions (300 char limit for mobile)
- [x] Listing preview modal with editable description
- [x] Placeholder image support
- [x] Auto-find user's business policies (shipping, payment, returns)
- [x] Auto-create merchant location
- [x] Package weight/dimensions for calculated shipping
- [x] Condition mapping (grade → eBay condition enum)
- [x] Create eBay listing via Inventory API
- [x] Listing published to live eBay! 🎉

**Technical details:**
- Category ID: 259104 (Comics & Graphic Novels)
- Package: 1" x 11" x 7", 8 oz, LETTER type
- SKU: CC-{title}-{issue}-{timestamp}
- Condition: LIKE_NEW, USED_EXCELLENT, USED_VERY_GOOD, USED_GOOD, USED_ACCEPTABLE

### Phase 2.85: QuickList Batch Processing ✅ (January 20, 2026)
**Full pipeline from photo to eBay draft listing.**

- [x] Draft mode for eBay listings (`publish=False` by default)
- [x] Photo upload to eBay Picture Services
- [x] Backend extraction via Claude vision (`comic_extraction.py`)
- [x] Batch processing endpoints:
  - `/api/extract` - Extract single comic from photo
  - `/api/batch/process` - Extract + Valuate + Describe multiple comics
  - `/api/batch/list` - Upload images + Create drafts (after approval)
- [x] Input validation (max 20 comics, 10MB images)
- [x] Removed 60-second delay between valuations (was Tier 1 leftover)
- [x] UI: Three price boxes (Quick/Fair/High) with Fair Value default
- [x] UI: "List on eBay" button per comic in batch results
- [x] UI: Removed confidence row (details via 📊 icon)
- [x] UI: Removed regenerate button
- [x] UI: Sort options (Value High/Low, Title A-Z, Order Added)
- [x] UI: Header syncs when editing title/issue fields
- [x] Vision Guide v1: Improved extraction prompt (distinguishes issue numbers from prices)

**QuickList Flow:**
1. Upload → 2. Extract → 3. Review/Edit → 4. Valuate → 5. Describe → 6. List as Draft

### Phase 2.86: QuickList Polish ✅ (January 21, 2026)
Refine the batch experience.

- [x] Sort options (by value, title) in batch results ✅
- [x] Vision Guide v1 for extraction (price vs issue number) ✅
- [x] GDPR account deletion endpoint ✅
- [x] Smart image compression (client-side, files > 3.5MB) ✅
- [x] Image thumbnails in extraction view ✅
- [x] Image thumbnails in results view ✅
- [x] Image in listing preview modal ✅
- [x] Mobile extraction/valuation/listing working ✅
- [x] `purge` command for Cloudflare cache ✅
- [ ] More progress steps during valuation (keep users engaged)
- [ ] Custom price entry (not just the three tiers)

### Phase 2.88: User Auth & Collections ✅ (January 21, 2026)
**Users can create accounts and save their comics.**

- [x] Email/password authentication (signup, login, logout)
- [x] Email verification via Resend (collectioncalc.com domain)
- [x] Forgot password / password reset flow
- [x] JWT tokens (30-day expiry)
- [x] Database tables: users, collections, password_resets
- [x] Save comics to collection
- [x] View collection (basic)
- [x] Auth UI in header (login/signup buttons, user menu)
- [x] "Save to Collection" button in results view

**Technical details:**
- Auth backend: `auth.py` with bcrypt password hashing
- Email service: Resend (3k emails/mo free)
- Frontend: Modal-based login/signup forms
- Storage: PostgreSQL (same DB as valuations)

### Phase 2.89: Frontend Code Refactor ✅ (January 22, 2026)
Split monolithic index.html for maintainability.

- [x] Split into 3 files:
  - `index.html` (~310 lines) - HTML structure only
  - `styles.css` (~1350 lines) - All CSS
  - `app.js` (~2030 lines) - All JavaScript
- [x] Same deployment process (git push; purge)
- [x] Fixes file truncation issues during editing

### Phase 2.9: Whatnot Integration ✅ (January 25, 2026)
**MILESTONE: Live auction data pipeline operational!**

Chrome extension captures real-time Whatnot sales → CollectionCalc database.

- [x] Whatnot Valuator Chrome extension (v2.40.1)
- [x] Apollo GraphQL cache reader (extracts listing data)
- [x] Claude Vision auto-scanning (identifies comics from video)
- [x] Sale detection with 30-second debounce
- [x] Price-drop detection for new item signals
- [x] Key issue database (500+ keys) with local lookup
- [x] `market_sales` table created in PostgreSQL
- [x] API endpoints: `/api/sales/record`, `/api/sales/count`, `/api/sales/recent`
- [x] Migrated 618 historical sales from Supabase → Render
- [x] Extension writes directly to CollectionCalc (Supabase removed)

**Extension Architecture:**
```
whatnot-valuator/
├── content.js          # Main overlay, auction monitoring
├── lib/
│   ├── apollo-reader.js   # Reads Whatnot's GraphQL cache
│   ├── collectioncalc.js  # API client (replaced supabase.js)
│   ├── vision.js          # Claude Vision API scanning
│   └── keys.js            # 500+ key issue database
```

**Why This Matters:**
- **Unique data**: Live auction prices = true price discovery (not asking prices)
- **Competitive moat**: Competitors rely on completed eBay sales only

### Phase 2.91: Beta Access & Admin Dashboard ✅ (January 26, 2026) 🆕
**MILESTONE: Private beta infrastructure complete!**

Controlled access system with full admin capabilities.

- [x] **Beta Code Gate**
  - Landing page with beta code entry
  - Beta codes table with uses_allowed, uses_remaining, expiry
  - Pre-created codes: BETA-MIKE, BETA-001 through BETA-005
  - Validation endpoint: `/api/beta/validate`

- [x] **User Approval Workflow**
  - New users start as `is_approved = FALSE`
  - Admins approve/reject from dashboard
  - Unapproved users see "Pending Approval" message
  - Approval updates `approved_at` and `approved_by`

- [x] **Admin Dashboard** (`/admin.html`)
  - Stats overview: users, pending approvals, API calls, costs, sales tracked, beta codes
  - User management tab: approve/reject buttons
  - Beta codes tab: create new codes, view usage
  - Errors tab: recent failed requests with device type
  - API Usage tab: Anthropic token costs by endpoint
  - **Natural Language Query (NLQ)**: Ask questions in plain English, Claude converts to SQL
  
- [x] **Request Logging**
  - `request_logs` table tracks all API calls
  - Device type detection (mobile/tablet/desktop)
  - Response times, error messages
  - User attribution via JWT

- [x] **API Usage Tracking**
  - `api_usage` table for Anthropic token costs
  - Per-endpoint breakdown
  - Monthly cost calculations

**New Files:**
- `auth.py` - Updated with beta code and approval logic
- `admin.py` - Admin functions including NLQ
- `db_migrate_beta.py` - Database migration script
- `landing.html` → `index.html` - Beta landing page
- `admin.html` - Admin dashboard

### Phase 2.92: R2 Image Storage ✅ (January 26, 2026) 🆕
**MILESTONE: Live auction images now stored permanently!**

Replaced dead Supabase image URLs with Cloudflare R2.

- [x] **Cloudflare R2 Setup**
  - Bucket: `collectioncalc-images`
  - Public URL enabled for serving
  - S3-compatible API via boto3

- [x] **Backend Integration**
  - `r2_storage.py` module for uploads
  - `/api/images/upload` endpoint
  - `/api/images/upload-for-sale` endpoint  
  - `/api/images/submission` endpoint (B4Cert ready)
  - `/api/images/status` health check
  - Images uploaded inline with sale recording

- [x] **Extension Updated**
  - `collectioncalc.js` sends images with sale data
  - Drop-in replacement for SupabaseClient
  - Images from Vision scans stored permanently

- [x] **Admin Dashboard Enhancement**
  - NLQ results show image thumbnails
  - Clickable thumbnails open full image
  - URLs rendered as links

**Image Path Structure (B4Cert ready):**
```
/sales/{sale_id}/front.jpg           # Whatnot captures
/submissions/{id}/front.jpg          # B4Cert (future)
/submissions/{id}/back.jpg
/submissions/{id}/spine.jpg  
/submissions/{id}/centerfold.jpg
```

**Environment Variables Added:**
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_ACCOUNT_ID`
- `R2_BUCKET_NAME`
- `R2_ENDPOINT`
- `R2_PUBLIC_URL`

---

## 🔄 In Progress

### Phase 3: FMV Engine Enhancement
- [ ] Incorporate Whatnot live sales into FMV calculations
- [ ] Use DB as primary source, fall back to real-time search for misses
- [ ] Add price history charts to UI
- [ ] Add "trending up/down" indicators
- [ ] CGC census integration (population reports - how rare is a 9.8?)

**Mike's Note:** Background in hotel revenue management / dynamic pricing applies here. Same problem domain - predicting optimal price based on features. Comics features: title, issue, grade, key status, market heat.

### Phase 6: Price Prediction & Trends
Forecast future values based on market momentum.

#### 6.1 - Trend Analysis
- [ ] Track price history over time per comic
- [ ] Calculate momentum (rate of change)
- [ ] Identify acceleration (is growth speeding up or slowing?)

#### 6.2 - Prediction Model
| Trend Signal | Prediction |
|--------------|------------|
| Strong upward + accelerating | "Expected +X% in 30 days" |
| Upward but slowing | "Growth may stabilize" |
| Flat | "Stable pricing expected" |
| Downward | "Expected -X% in 30 days" |

#### 6.3 - Prediction Confidence
- More historical data = higher confidence
- Recent volatility = lower confidence
- External factors (movie announcements, etc.) = flag as "catalyst detected"

#### 6.4 - Dashboards
- [ ] Individual comic price chart with forecast line
- [ ] **Top 10 Hottest** - Fastest predicted increases
- [ ] **Top 10 Cooling** - Biggest predicted decreases
- [ ] **Trending Now** - Comics with sudden momentum shifts

#### 6.5 - Alerts (Future)
- [ ] "Absolute Batman #1 jumped 15% this week"
- [ ] User watchlists with price alerts
- [ ] Weekly "market movers" email digest

### Phase 7: Friend Beta Prep ✅ (Mostly Complete)
Get ready for external testers.

- [x] Beta code gate
- [x] User approval workflow
- [x] Admin dashboard with NLQ
- [x] Request logging for debugging
- [ ] Analytics (track usage patterns)
- [ ] Feedback mechanism (Report Issue link)
- [x] Landing page copy explains what it does
- [x] Error states handled gracefully
- [ ] API key instructions for Whatnot extension

### Phase 8: Advanced Features
- [ ] Price history charts
- [ ] Collection portfolio tracking
- [ ] Price alerts ("notify me if X drops below $50")
- [ ] Export to CSV/PDF
- [ ] Public API for third-party integrations

### Phase 9: Multi-Collectible Expansion
Extend platform to additional verticals.

| Phase | Vertical | Complexity | Key Features |
|-------|----------|------------|--------------|
| 9.1 | Sports Cards | Medium | PSA/BGS grades, rookie flags, auto/jersey |
| 9.2 | Pokémon/TCGs | Medium | Set info, rarity, 1st edition, holo types |
| 9.3 | Coins | High | Mint marks, die varieties, strike quality |
| 9.4 | Vinyl Records | Medium | Pressing info, matrix numbers, Discogs data |
| 9.5 | Sneakers | Medium | Colorway, collabs, deadstock status |
| 9.6 | Watches | High | Complex market, authentication needs |

#### Shared Core Engine (reusable across verticals)
- [ ] eBay search abstraction
- [ ] Recency weighting (universal)
- [ ] Confidence scoring (universal)
- [ ] Price prediction (universal)
- [ ] User adjustments (universal)
- [ ] Photo upload/recognition (per-vertical training)

---

## Budget Phases 💰

| Phase | Monthly Cost | Stack |
|-------|--------------|-------|
| MVP (Current) | ~$7 | Render Starter + PostgreSQL Basic |
| Beta | ~$15-25 | + Anthropic Tier 2 |
| Production | ~$50-100 | When revenue justifies |

### Anthropic API Costs
- **Current Tier:** Tier 2 (450k tokens/min, $60 credits deposited)
- **Capacity:** 20-50 comics/minute comfortable, 100+ may need pacing
- **Cost per valuation:** ~$0.01-0.02 (with caching)
- **Cost per QuickList (extract+valuate+describe):** ~$0.02-0.03
- **Cost per Whatnot Vision scan:** ~$0.01-0.03

### Premium Tier Opportunity 💎 (Discovered Session 7)
**Opus model provides significantly better signature detection.**

| Feature | Sonnet (Standard) | Opus (Premium) |
|---------|-------------------|----------------|
| Cost per extraction | ~$0.01 | ~$0.05 |
| Basic extraction | ✅ Great | ✅ Great |
| Obvious signatures | ✅ Works | ✅ Works |
| Subtle signatures (gold/metallic on dark) | ❌ Misses | ✅ Detects |

**Proven:** Moon Knight #1 signed by Danny Miki (gold marker)
- Sonnet: `signature_detected: false`
- Opus: `signature_detected: true`, listed all creators with confidence %
- Note: Opus detects THAT a signature exists, but can't reliably identify WHO signed

**Future enhancement:** Reference Signature Database
- Collect verified creator signatures (eBay ~$1 each)
- Store as reference images
- AI compares uploaded signature to references for identification
- Could significantly improve "who signed" accuracy

**Implementation:** Code is ready in app.js - just uncomment the Opus line.

**Pricing idea:** "Super User" tier at ~$10/month could include:
- Opus-powered extraction
- Priority processing
- Extended collection storage
- Advanced analytics

---

## Success Metrics

### Accuracy Metrics
- **User adjustments trending toward zero** - Model matches expectations
- **Confidence calibration** - High confidence = accurate predictions
- **Extraction accuracy** - % of issue numbers read correctly
- **Signature detection accuracy** - % of signatures detected (needs quality images)
- **Whatnot prediction accuracy** - FMV vs actual Whatnot sale price

### Coverage Metrics
- **DB hit rate** - % of lookups found in database vs requiring AI search
- **Collectible verticals** - Number of active verticals (target: 5+ by 2027)
- **Whatnot sales captured** - 3,300+ and growing 🆕
- **R2 images stored** - New metric starting Jan 26 🆕

### Engagement Metrics
- **Return users** - Users coming back to value more items
- **Collections tracked** - Total items in user portfolios
- **Feedback submissions** - Community corrections submitted
- **eBay listings created** - Conversion from valuation to listing
- **QuickList completions** - Users completing full photo-to-listing flow
- **Whatnot auction sessions** - Active extension users
- **Beta users approved** - New metric 🆕

### Business Metrics
- **Cost per valuation** - Target: <$0.01 average (with DB caching)
- **API revenue** - Third-party integrations (future)

---

## Data Sources

| Source | Type | Unique Value | Status |
|--------|------|--------------|--------|
| Whatnot Live | Live auction | True price discovery | ✅ 3,300+ sales |
| eBay Completed | Auction + BIN | Highest volume | ✅ Web search + cache |
| eBay Active BIN | Current listings | Price ceiling | ✅ In valuations |
| PriceCharting | Aggregated | Historical trends | 📋 Planned ($200/mo) |
| GoCollect | CGC census | Population data | 📋 Planned |

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| Jan 26, 2026 | 2.92.0 | 📷 **R2 Image Storage!** Cloudflare R2 integration, images with sales, admin thumbnails |
| Jan 26, 2026 | 2.91.0 | 🔐 **Beta Access System!** Beta codes, user approval, admin dashboard, NLQ, request logging |
| Jan 25, 2026 | 2.90.0 | 🔗 **Whatnot Integration!** market_sales table, /api/sales/* endpoints, 618 sales migrated, extension v2.40.1 |
| Jan 22, 2026 | 2.89.1 | 💎 **Opus Premium tier tested!** Signature detection works with Opus, code ready for Premium pricing |
| Jan 22, 2026 | 2.89.0 | 📁 **Frontend 3-file split!** index.html/styles.css/app.js, signature confidence UI, improved issue # detection |
| Jan 21, 2026 | 2.88.0 | 🔐 **User auth & collections!** Email/password signup, JWT tokens, save comics, Resend email integration |
| Jan 21, 2026 | 2.86.3 | 🐛 **Cache key fix!** Grade now included in cache key |
| Jan 21, 2026 | 2.86.2 | 📋 **Visual condition assessment!** Defect detection, signature detection |
| Jan 21, 2026 | 2.86.1 | GDPR endpoint, smart image compression, thumbnails, mobile fixes |
| Jan 20, 2026 | 2.85.1 | Sort options, Vision Guide v1, header sync fix |
| Jan 20, 2026 | 2.85.0 | 🚀 **QuickList batch processing!** Draft mode, photo upload, backend extraction |
| Jan 19, 2026 | 2.8.0 | 🎉 **First live eBay listing!** Production OAuth, business policies |
| Jan 18, 2026 | 2.7.5 | AI descriptions, listing preview modal, Anthropic Tier 2 upgrade |
| Jan 17, 2026 | 2.7.0 | eBay OAuth (sandbox), listing buttons |
| Jan 15, 2026 | 2.5.0 | Three-tier pricing, PostgreSQL migration |

---

## Related Documents

- [Claude Notes](CLAUDE_NOTES.md) - Session context and working notes
- [Architecture](ARCHITECTURE.md) - System diagrams
- [Brand Guidelines](BRAND_GUIDELINES.md) - Colors, typography, UI components
- [API Reference](API_REFERENCE.md) - Function names and import patterns 🆕
- [Competitive Analysis](COMPETITIVE_ANALYSIS.md) - Market research & academic findings
- [Database](DATABASE.md) - Schema documentation
- [Budget](BUDGET.md) - Hosting strategy

---

*Last updated: January 26, 2026 (Session 9 - Beta access, admin dashboard, R2 image storage)*
