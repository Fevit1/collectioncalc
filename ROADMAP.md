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

---

## In Progress 🔨

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

---

## Planned 📋

### Phase 2.87: Extraction Accuracy (Vision Guide v2)
Further improve AI's ability to read comic covers.

**Completed (v1):**
- [x] Distinguish prices (60¢, $1.50) from issue numbers (#242)
- [x] Look for "#" or "No." prefix for issue numbers
- [x] Focus on TOP-LEFT area for issue numbers

**Vision Guide v2 contents (future):**
- [ ] Issue number location patterns by publisher/era (Marvel top-left, DC varies)
- [ ] Ignore: price stickers, store stamps, grade labels, bag reflections
- [ ] Multiple numbers context: price vs issue vs volume vs year
- [ ] Barcode area for newsstand detection
- [ ] Common OCR confusions (#1 vs #7, etc.)

### Phase 2.9: Cache Refresh Strategy
Keep valuations fresh without breaking the bank.

| Phase | Trigger | Cost Impact |
|-------|---------|-------------|
| **Now** | 48-hour expiration, refresh on next search | $0 extra |
| **Beta** | Hybrid: serve stale, background refresh if >7 days | $0 extra |
| **Production** | Weekly background refresh for active comics | ~$80-165/week |
| **Scale** | Use Haiku for bulk refreshes | ~$40/week |

- [ ] Implement hybrid stale-while-revalidate
- [ ] Track "active" comics (searched in last 30 days)
- [ ] Background job infrastructure (when revenue supports)
- [ ] Model selection for refresh (Sonnet vs Haiku)

---

### Phase 2.95: UI Improvements
Better experience for different use cases.

- [ ] Bulk results table view (for multi-comic valuations)
- [ ] Advanced Options toggle:
  - CGC/CBCS certified checkbox + grade (e.g., 9.8)
  - Autographed checkbox + signer name
  - Newsstand vs Direct edition
  - Variant cover description
- [ ] Mobile-responsive refinements
- [ ] User tone preference for descriptions (professional/casual)
- [ ] Fuzzy matching for misspelled titles (save API costs, improve UX)

---

### Phase 2.96: eBay Listing Enhancements
Polish the listing experience.

- [ ] Description caching (avoid regenerating same comic)
- [ ] Best Offer support (enable/disable, auto-accept/decline thresholds)
- [ ] Bulk listing from multi-comic valuations ("List all at Fair Value")
- [ ] Batch listing groups (e.g., "List all 12 issues of Secret Wars")
- [ ] Video upload support
- [ ] Promoted listings option (commission boost)
- [ ] eBay account deletion notification endpoint (required before other users)
- [ ] Host our own placeholder image (not external URL)

---

### Phase 3: Admin Tuning Dashboard
Owner controls for model refinement.

- [ ] Web dashboard for adjusting weights
  - Recency decay curve
  - Volume thresholds
  - Variance tolerance
- [ ] Preview changes across sample comics
- [ ] A/B testing framework
- [ ] Rollback capability

### Phase 4: User Adjustments
Let users provide feedback and personalize.

- [ ] "This seems high/low" feedback buttons
- [ ] User adjustment history
- [ ] Optional: Personal weight preferences
- [ ] Track all adjustments as training data

### Phase 5: Model Learning
Use community data to improve base model.

- [ ] Analyze adjustment patterns
  - "Users consistently lower VG prices by 15%"
  - "Golden Age books undervalued by 20%"
- [ ] Generate proposed model changes
- [ ] Admin approval workflow
- [ ] Version history for model changes

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

### Phase 7: Photo Upload (Now part of QuickList)
~~AI-powered comic identification.~~ **Moved to Phase 2.85**

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
| MVP (Current) | ~$7 | Render Starter + PostgreSQL |
| Beta | ~$15-25 | + Anthropic Tier 2 |
| Production | ~$50-100 | When revenue justifies |

### Anthropic API Costs
- **Current Tier:** Tier 2 (450k tokens/min, $60 credits deposited)
- **Capacity:** 20-50 comics/minute comfortable, 100+ may need pacing
- **Cost per valuation:** ~$0.01-0.02 (with caching)
- **Cost per QuickList (extract+valuate+describe):** ~$0.02-0.03

---

## Success Metrics

### Accuracy Metrics
- **User adjustments trending toward zero** - Model matches expectations
- **Confidence calibration** - High confidence = accurate predictions
- **Extraction accuracy** - % of issue numbers read correctly

### Coverage Metrics
- **DB hit rate** - % of lookups found in database vs requiring AI search
- **Collectible verticals** - Number of active verticals (target: 5+ by 2027)

### Engagement Metrics
- **Return users** - Users coming back to value more items
- **Collections tracked** - Total items in user portfolios
- **Feedback submissions** - Community corrections submitted
- **eBay listings created** - Conversion from valuation to listing
- **QuickList completions** - Users completing full photo-to-listing flow

### Business Metrics
- **Cost per valuation** - Target: <$0.01 average (with DB caching)
- **API revenue** - Third-party integrations (future)

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| Jan 21, 2026 | 2.86.1 | GDPR endpoint, smart image compression, thumbnails (extraction/results/preview), mobile fixes, `purge` command |
| Jan 20, 2026 | 2.85.1 | Sort options, Vision Guide v1 (issue# vs price), header sync fix |
| Jan 20, 2026 | 2.85.0 | 🚀 **QuickList batch processing!** Draft mode, photo upload, backend extraction, batch endpoints, UI overhaul |
| Jan 19, 2026 | 2.8.0 | 🎉 **First live eBay listing!** Production OAuth, business policies, package dimensions |
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

*Last updated: January 21, 2026 (Session 4)*
