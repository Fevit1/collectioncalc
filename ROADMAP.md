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

### Phase 2.9: Whatnot Integration ✅ (January 25, 2026) 🆕
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
- **Accurate FMV**: Real bidding behavior, not list prices
- **Growing dataset**: 618+ sales and counting

---

## In Progress 🔨

### Phase 2.87: Extraction Accuracy (Vision Guide v2)
Further improve AI's ability to read comic covers.

**Completed (v1):**
- [x] Distinguish prices (60¢, $1.50) from issue numbers (#242)
- [x] Look for "#" or "No." prefix for issue numbers
- [x] Focus on TOP-LEFT area for issue numbers

**Completed (v2 - Session 7):**
- [x] Multi-location issue search (top-left, top-right, near barcode, near title)
- [x] DC comics support (issue # often top-right)
- [x] Signature detection with confidence analysis
- [x] Signature analysis UI (green box with creator confidence %)
- [x] Auto-populate "Signed copy" checkbox from AI detection
- [x] Frontend split into 3 files (index.html, styles.css, app.js)
- [x] Improved image quality processing (upscale small images to 1200px)

**In Progress:**
- [ ] EXIF auto-rotation (code deployed, needs debugging)
- [ ] Manual rotate button (↻) (code deployed, needs debugging)

**Pending (v2):**
- [ ] Ignore: price stickers, store stamps, grade labels, bag reflections
- [ ] Multiple numbers context: price vs issue vs volume vs year
- [ ] Common OCR confusions (#1 vs #7, etc.)

**Known Limitation:** Signature detection requires high-quality images (~3000px). Facebook/Messenger-compressed images (~500px) are too degraded. Tell testers to EMAIL original photos.

---

## Planned 📋

### Phase 3: Unified FMV Engine 🆕
Combine Whatnot + eBay data with intelligent weighting.

**Architecture:**
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Whatnot   │  │    eBay     │  │PriceCharting│
│   (Live)    │  │ (Completed) │  │ (Aggregated)│
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┴────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │   UNIFIED FMV ENGINE  │
            │                       │
            │  - Source weighting   │
            │  - Recency decay      │
            │  - Grade matching     │
            │  - Confidence scoring │
            └───────────────────────┘
```

**Implementation:**
- [ ] `GET /api/fmv?title=X&issue=Y&grade=Z` endpoint
- [ ] Query `market_sales` table for Whatnot data
- [ ] Query `search_cache` for eBay data
- [ ] Source weighting: Whatnot 1.0x, eBay Auction 0.9x, eBay BIN 0.7x
- [ ] Steeper recency decay (recent sales weighted higher)
- [ ] Update extension to call unified FMV

### Phase 4: Visual Tuning Dashboard
Admin interface for FMV model parameters.

- [ ] Web UI for adjusting weights
- [ ] Sliders for recency decay curve
- [ ] Sliders for source weights
- [ ] Live preview of price impact
- [ ] A/B testing support
- [ ] Rollback capability
- [ ] Audit log of changes

### Phase 5: Self-Improving Model
AI recommends weight adjustments based on prediction accuracy.

- [ ] Collect prediction vs actual sale metrics
- [ ] Calculate prediction error over time
- [ ] AI analyzes patterns and suggests weight changes
- [ ] Human approval workflow
- [ ] Eventually: auto-tune within guardrails

### Phase 5.5: Price Database Integration
License professional price data for faster, more accurate valuations.

**Business Case:**
- Cost: ~$200/mo for API access
- Break-even: ~20 paying users at $10/mo
- Competitive necessity: Ludex and competitors use similar data

**Candidates to evaluate:**
| Provider | Data | Pros | Cons |
|----------|------|------|------|
| GoCollect | 500k+ comics, CGC census, trends | Most comprehensive | Higher cost |
| GPA (GPAnalysis) | CGC sales focus | Accurate for slabs | Less raw data |
| PriceCharting | Comics + games + cards | Multi-vertical | Less depth |

**Implementation:**
- [ ] Evaluate GoCollect vs GPA vs PriceCharting APIs
- [ ] License price database (~$200/mo when revenue supports)
- [ ] Build import pipeline (weekly sync)
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

### Phase 7: Friend Beta Prep 🆕
Get ready for external testers.

- [ ] Analytics (track usage patterns)
- [ ] Feedback mechanism (Report Issue link)
- [ ] Landing page copy explains what it does
- [ ] Error states handled gracefully
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
- **Whatnot prediction accuracy** - FMV vs actual Whatnot sale price 🆕

### Coverage Metrics
- **DB hit rate** - % of lookups found in database vs requiring AI search
- **Collectible verticals** - Number of active verticals (target: 5+ by 2027)
- **Whatnot sales captured** - 618+ and growing 🆕

### Engagement Metrics
- **Return users** - Users coming back to value more items
- **Collections tracked** - Total items in user portfolios
- **Feedback submissions** - Community corrections submitted
- **eBay listings created** - Conversion from valuation to listing
- **QuickList completions** - Users completing full photo-to-listing flow
- **Whatnot auction sessions** - Active extension users 🆕

### Business Metrics
- **Cost per valuation** - Target: <$0.01 average (with DB caching)
- **API revenue** - Third-party integrations (future)

---

## Data Sources

| Source | Type | Unique Value | Status |
|--------|------|--------------|--------|
| Whatnot Live | Live auction | True price discovery | ✅ 618+ sales |
| eBay Completed | Auction + BIN | Highest volume | ✅ Web search + cache |
| eBay Active BIN | Current listings | Price ceiling | ✅ In valuations |
| PriceCharting | Aggregated | Historical trends | 📋 Planned ($200/mo) |
| GoCollect | CGC census | Population data | 📋 Planned |

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
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
- [Competitive Analysis](COMPETITIVE_ANALYSIS.md) - Market research & academic findings
- [Database](DATABASE.md) - Schema documentation
- [Budget](BUDGET.md) - Hosting strategy

---

*Last updated: January 25, 2026 (Session 8 - Whatnot integration, market_sales table, unified FMV plans)*
