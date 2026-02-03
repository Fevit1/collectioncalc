# Slab Worthy / CollectionCalc Roadmap

## Current Version: 4.2.1 (February 2, 2026)

### 🎉 PATENT PENDING
Provisional patent filed for multi-angle comic grading system.

---

## 🚨 Immediate Priorities

### Legal/Compliance (BLOCKING)
- [ ] **Create privacy.html** - Currently 404, linked from footer
- [ ] **Create terms.html** - Currently 404, linked from footer
- [ ] **Set up support@slabworthy.com** - Linked from footer

### Testing
- [ ] **Mobile testing** - Full Slab Worthy flow on phone
- [ ] **Comic-shaped upload boxes** - Verify on small screens

---

## High Priority

### Whatnot Auction Integration
**Goal:** Create Whatnot auctions directly from graded comics

**Requirements:**
- [ ] Whatnot API research / partnership inquiry
- [ ] Authentication flow
- [ ] Auction creation endpoint
- [ ] Listing templates optimized for Whatnot format
- [ ] "List to Whatnot" button in grade report

**Note:** Landing page promises "Whatnot integration coming soon!" - need timeline

### My Collection Feature
**Goal:** Users can save, view, and manage their graded comics

**Desktop (easier):**
- [ ] Collection grid/list view
- [ ] Filter by grade, title, value
- [ ] Sort options
- [ ] Total collection value
- [ ] Export to CSV

**Mobile (harder - limited real estate):**
- [ ] Compact card view
- [ ] Swipe actions
- [ ] Quick filters
- [ ] Consider bottom sheet for details

### Mobile UX: Better Image Picker
**Problem:** Standard file picker shows tiny thumbnails
**Desired:** Gallery-style view like native Pixel camera app

**Options:**
- Custom image picker component with larger previews
- PWA with File System Access API
- Native-like gallery grid before upload
- Consider: Is this worth the complexity?

---

## Medium Priority

### Branding Consistency
- [ ] Decide: Should collectioncalc.com show CollectionCalc or Slab Worthy branding?
- [ ] Update email templates (verification, password reset) - still say "CollectionCalc"
- [ ] Update Chrome extensions to reference Slab Worthy
- [ ] Consider more playful tone - "Slab Worthy" is casual phrase, current design may be too formal

### Technical Debt: wsgi.py Refactoring
**Current:** ~1,900 lines
**Threshold:** Refactor at ~2,500 lines

**Plan:** Split using Flask Blueprints
```
wsgi.py (main app, ~200 lines)
routes/
  auth.py      - authentication endpoints
  admin.py     - admin/NLQ endpoints
  sales.py     - FMV, market data
  images.py    - R2 upload, barcode scanning
  grading.py   - extraction, grading
```

### Analytics Improvements
Current: Basic admin console analytics
Consider:
- [ ] User journey tracking (where do people drop off?)
- [ ] Grading completion rates
- [ ] Popular comic titles
- [ ] Time-to-grade metrics
- [ ] A/B testing framework

---

## Privacy & Compliance

### GDPR Requirements (EU Users)
Even if US-only for now, good practice to implement:

**Required:**
- [ ] Clear privacy policy explaining data collection
- [ ] Cookie consent banner (if using tracking cookies)
- [ ] Right to access - users can request their data
- [ ] Right to deletion - users can delete account and data
- [ ] Data portability - export user data
- [ ] Clear consent for marketing emails

**Implementation:**
- [ ] Add "Delete my account" option in user settings
- [ ] Add "Export my data" option
- [ ] Cookie consent component (if needed)
- [ ] Update privacy policy with GDPR language

### US State Privacy Laws

**California (CCPA/CPRA):**
- Right to know what data is collected
- Right to delete personal information
- Right to opt-out of sale of data
- "Do Not Sell My Personal Information" link (if applicable)

**Other States:**
- Virginia (VCDPA), Colorado (CPA), Connecticut (CTDPA) have similar requirements
- Generally: transparency, access, deletion rights

**Recommended Privacy Policy Sections:**
1. What data we collect (email, photos, grading history)
2. How we use it (provide service, improve AI)
3. How we store it (encrypted, US servers)
4. Third parties (Anthropic for AI, Cloudflare for hosting)
5. User rights (access, delete, export)
6. Contact info
7. Updates policy

---

## Recently Completed

### v4.2.1 - Reprint Filter (Session 23)
- [x] FMV excludes reprints (barcode + text detection)
- [x] Filters: "2nd print", "3rd print", "reprint"

### v4.2.0 - eBay Data Integration (Session 23)
- [x] FMV queries both market_sales AND ebay_sales
- [x] 10x more sales data for valuations
- [x] Source breakdown in response

### v4.1.0 - Slab Worthy Rebrand (Session 23)
- [x] slabworthy.com live as custom domain
- [x] New branding throughout
- [x] Removed Photo Upload tab
- [x] Slab Worthy as default tab
- [x] Comic-shaped upload boxes
- [x] Desktop/mobile text variants

### v4.0.0 - Docker + Barcode (Session 22)
- [x] Docker deployment with pyzbar
- [x] Barcode scanning live
- [x] UPC storage in database

---

## Known Bugs

- [ ] 🐛 **Auto-rotation steps 2-4** - Code added but not working
- [ ] 🐛 **Photo Upload mode removed** - Was it used for testing? May need alternative

---

## Backlog

### Features
- [ ] Grade report sharing/export (PDF, image)
- [ ] Batch grading (multiple comics)
- [ ] Price alerts
- [ ] Value tracking over time
- [ ] Collection analytics

### Admin
- [ ] Slab Premium Admin Panel
- [ ] Prompt Management Admin Page
- [ ] User management improvements

### Future Verticals (Post-Comics Success)
- [ ] Coins (coinworthy.com)
- [ ] Cards (cardworthy.com) 
- [ ] Stamps (stampworthy.com)

---

## Company Foundation

### Mission
**Helping collectors maximize the value of their collection.**

### Founder Background
Mike Berry - Former eBay, CTO org supporting Marketing department
- Built "Complete Your Collection" - identified collectors (e.g., Star Wars figures) and recommended complementary items
- Targeted merchandising based on purchase/browsing behavior
- Deep understanding of collector psychology and data-driven personalization

**Product insight from this:** We should track browsing/collecting behavior to:
- Recommend what to grade next
- Alert on price movements for items they're interested in
- "Complete your collection" style recommendations
- Personalized grading priorities based on their collection

### Values
*(To be defined - Mike reflecting on these questions)*

**Questions to consider:**
- What do you want collectors to feel when they use Slab Worthy?
- What would you never compromise on?
- What makes Slab Worthy different from a faceless tool?
- When things go wrong, how do we make it right?
- What kind of company do you want to build?

**Candidate values (starting points):**
- Collector-first (we succeed when they succeed)
- Transparency (honest grades, real data)
- Accessibility (make expert knowledge available to everyone)
- Trust (their data, their collection, their control)
- Continuous improvement (always learning, always better)

### Leadership Philosophy

**The Leadership Challenge (Kouzes & Posner) - 5 Practices:**
1. **Model the Way** - Clarify values, set the example
2. **Inspire a Shared Vision** - Envision the future, enlist others
3. **Challenge the Process** - Search for opportunities, experiment and take risks
4. **Enable Others to Act** - Foster collaboration, strengthen others
5. **Encourage the Heart** - Recognize contributions, celebrate values and victories

**Situational Leadership (Hersey & Blanchard):**
Adapt leadership style to the development level of the person/team:
- **Directing** (S1) - High task, low relationship - for new/learning
- **Coaching** (S2) - High task, high relationship - for developing
- **Supporting** (S3) - Low task, high relationship - for capable but uncertain
- **Delegating** (S4) - Low task, low relationship - for self-reliant performers

**Application:** As Slab Worthy grows, leadership style shifts. Early stage = more directing/coaching. Scaled team = more supporting/delegating.

---

## Founder Context & Vision

### The Goal
**$100M revenue in 5 years** via multi-vertical expansion

### Personal Situation
- Currently unemployed, actively looking for work
- ~$500K runway (2-4 years depending on burn)
- If employed: well-funded side project that can still grow
- **Domain expertise:** Mike worked in eBay's Collectibles division - knows the categories, the buyers, the data

### Milestones That Validate "Go Full-Time"
- [ ] 1,000 paying users
- [ ] $10K MRR
- [ ] Clear product-market fit (retention, referrals)

### Path to $100M - Multi-Vertical Expansion

**The Math:**
| Price Point | Users Needed for $100M |
|-------------|------------------------|
| $10/mo ($120/yr) | 833K paying users |
| $20/mo ($240/yr) | 417K paying users |
| $50/yr one-time | 2M paying users |

**Comics alone probably caps at $20-30M.** Multi-vertical is required.

### Vertical Expansion Roadmap

| Vertical | Brand | Grading Cos | Market Notes | Revenue Potential |
|----------|-------|-------------|--------------|-------------------|
| **Comics** | Slab Worthy | CGC, CBCS | 500K-1M graded/year | $15-25M |
| **Sports Cards** | CardWorthy? | PSA, BGS, SGC | Massive market, $10B+ industry | $25-40M |
| **Pokemon/TCG** | CardWorthy? | PSA, BGS, CGC | Huge Gen Z/Millennial audience | $15-25M |
| **Coins** | CoinWorthy? | PCGS, NGC | Established older demographic | $15-25M |
| **Sneakers** | SoleWorthy? KickWorthy? | - | Authentication, not grading | $10-20M |
| **Stamps** | StampWorthy? | PSA, PSE | Smaller, older demographic | $5-10M |
| **Sports Memorabilia** | ? | PSA, Beckett, JSA | Autographs, jerseys, bats | $5-15M |
| **Vintage Toys** | ? | AFA (Action Figure Authority) | Star Wars, GI Joe, etc. | $5-10M |
| **Watches** | ? | Various auth services | Authentication focus | $5-10M |
| **Wine** | ? | WA, Vinous ratings | Different model - storage/provenance | $5-10M |

**Full eBay Collectibles Categories (potential verticals):**
- Trading Cards (sports, Pokemon, Magic, Yu-Gi-Oh)
- Comics
- Coins & Paper Money
- Stamps
- Sports Memorabilia
- Entertainment Memorabilia
- Vintage & Antique Toys
- Art
- Pottery & Glass
- Militaria
- Rocks, Fossils & Minerals
- Breweriana
- Tobacciana

### Prioritized Expansion Order

**Phase 1 (2026):** Comics - prove the model ✅ IN PROGRESS

**Phase 2 (2027):** Sports Cards + Pokemon
- Largest grading markets
- Similar workflow to comics
- PSA alone grades millions/year

**Phase 3 (2028):** Coins
- Established market
- Higher average value items
- PCGS/NGC are well-known

**Phase 4 (2029+):** Sneakers, Memorabilia, expand based on data

### What Changes Per Vertical

| Component | Comics | Cards | Coins | Sneakers |
|-----------|--------|-------|-------|----------|
| AI prompts | Comic defects | Centering, corners, surface | Wear, luster, strike | Authenticity, condition |
| Grading scale | 0.5-10 | 1-10 | 1-70 | Pass/Fail + condition |
| Photo angles | Front, spine, back, centerfold | Front, back, edges, corners | Obverse, reverse, edge | Multiple angles, box, tags |
| Market data | eBay, Whatnot | eBay, PWCC, Goldin | eBay, Heritage, GreatCollections | StockX, GOAT, eBay |

### What Stays the Same (Shared Backend)
- User authentication
- Payment/subscription system
- Image processing pipeline
- AI vision infrastructure
- Collection management
- R2 storage
- Admin dashboard

---

## Finance & Fundraising

### Documents to Update/Create
- [ ] **Investor Pitch Deck** - existing draft needs refresh
- [ ] **FAQ Document** - existing draft needs refresh
- [ ] **Financial Model** - spreadsheet with projections

### Financial Model Components

**Revenue Forecast:**
- User growth assumptions (month over month)
- Conversion rate: free → paid
- Churn rate assumptions
- ARPU (Average Revenue Per User)
- Revenue = Users × Conversion × Price - Churn

**Cost Structure:**
| Category | Items | Est. Monthly |
|----------|-------|--------------|
| Infrastructure | Render, Cloudflare, R2, Anthropic API | $50-500+ |
| Payments | Stripe fees (2.9% + $0.30) | Variable |
| Email | Resend or similar | $20-50 |
| Domains | slabworthy.com, etc. | ~$2/mo amortized |
| Marketing | Ads, content, Lucent.ai | TBD |
| Legal | Terms, trademark, etc. | One-time + minimal |

**Key Metrics to Model:**
- CAC (Customer Acquisition Cost)
- LTV (Lifetime Value)
- LTV:CAC ratio (want 3:1 or better)
- Months to payback
- Gross margin
- Burn rate
- Runway

**Break-even Analysis:**
- Fixed costs per month
- Variable cost per user
- Revenue per user
- Break-even = Fixed Costs ÷ (Revenue - Variable Cost per User)

### Pro Forma Structure (3-Year)

**Year 1 (2026):**
- Beta → Launch
- Focus on product-market fit
- Likely unprofitable, funded by savings/angel

**Year 2 (2027):**
- Growth phase
- Marketing spend increases
- Target: Break-even or small profit

**Year 3 (2028):**
- Scale / expand verticals (coins, cards)
- Profitability
- Potential Series A if scaling aggressively

### Fundraising Considerations

**Bootstrap vs. Raise:**
- Current burn rate is low (Render ~$7-20/mo)
- Could bootstrap to profitability
- Raising makes sense if: want to move faster, hire, marketing blitz

**If Raising:**
- Angel round: $50-250K for runway + marketing
- Seed round: $500K-2M for team + growth
- What's the use of funds? (X% product, Y% marketing, Z% ops)

**Investor Pitch Updates Needed:**
- [ ] Traction metrics (users, grades completed, retention)
- [ ] Market size (comic grading market, CGC revenue as proxy)
- [ ] Competitive landscape
- [ ] Team slide
- [ ] Financial projections
- [ ] Ask amount and use of funds

---

## Business/Legal

### Monetization & Payments

**Pricing Model Options:**
- [ ] Freemium (X free grades/month, then paid)
- [ ] Subscription tiers (Basic/Pro/Unlimited)
- [ ] Pay-per-grade (credits system)
- [ ] One-time purchase vs. recurring

**Questions to answer:**
- What's the free tier limit? (3 grades/month? 5?)
- What features are gated? (AI grading, collection, eBay listing)
- Annual discount?

**Payment Processing:**
- [ ] **Stripe** - industry standard, handles subscriptions, easy integration
- [ ] Stripe Checkout for payment flow
- [ ] Stripe Customer Portal for self-service (upgrade, downgrade, cancel)
- [ ] Webhook handling for subscription events
- [ ] Receipts and invoices

**Cancellation Flow:**
- [ ] Self-service cancel via Stripe Customer Portal
- [ ] Grace period? (access through end of billing period)
- [ ] Win-back email sequence?
- [ ] Exit survey (why are you leaving?)

### Terms & Conditions

**Must include:**
- [ ] IP Protection - "You will not copy, reproduce, or create derivative works..."
- [ ] Look at Tabi's language for reference
- [ ] Service limitations and disclaimers
- [ ] Grading is estimate, not guarantee
- [ ] User-generated content rights
- [ ] Account termination conditions
- [ ] Dispute resolution

**Acceptance flow:**
- [ ] Checkbox on signup: "I agree to Terms and Privacy Policy"
- [ ] Store timestamp of acceptance
- [ ] Re-acceptance required when terms change materially

### Customer Support

**Chatbot on Site:**
- [ ] AI chatbot for FAQ, how-to, troubleshooting
- [ ] Escalation to email for complex issues
- [ ] Options: Intercom, Crisp, custom with Claude API

**Phone Support (Future):**
- [ ] AI voice agent for phone support
- [ ] Walk users through grading process
- [ ] Options: Bland.ai, Vapi, Retell.ai
- [ ] Consider: Is phone support needed for this demographic?

### Marketing Plan

**Phase 1: Organic/Low Cost**
- [ ] Comic collector subreddits (r/comicbookcollecting, r/comicbooks)
- [ ] Facebook groups (comic collectors, CGC fans)
- [ ] YouTube tutorial video (how to use Slab Worthy)
- [ ] SEO: "should I grade my comic", "is my comic worth grading"
- [ ] Comic convention presence (virtual or physical)

**Phase 2: Paid Acquisition**
- [ ] Google Ads on grading-related searches
- [ ] Facebook/Instagram ads targeting comic collectors
- [ ] Influencer partnerships (comic YouTubers, TikTokers)

**Phase 3: Video Marketing**
- [ ] **Lucent.ai** - Mike is part owner
- [ ] TikTok content (quick grading demos, before/after values)
- [ ] Facebook video ads
- [ ] YouTube pre-roll on comic content
- [ ] Instagram Reels

**Messaging angles:**
- "Is your comic worth grading? Find out in 60 seconds"
- "Don't waste $50 grading a $20 comic"
- "AI-powered grading assessment"
- "Know before you slab"

### Trademarks (Not Urgent)
- [ ] "Slab Worthy" - $250-350 USPTO filing
- [ ] "CollectionCalc" - lower priority
- Currently using ™ (unregistered) - provides common law protection

### CGC Partnership
- [ ] Affiliate/referral commission exploration
- [ ] User discounts for using recommendation
- [ ] Attribution tracking

---

## Patent Coverage

**Title:** System and Method for Automated Comic Book Condition Assessment Using Multi-Angle Imaging and Artificial Intelligence

**Status:** Provisional filed January 27, 2026
**Deadline:** File utility patent by January 27, 2027

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 4.2.1 | Feb 2, 2026 | Reprint filter |
| 4.2.0 | Feb 2, 2026 | eBay data in FMV |
| 4.1.0 | Feb 2, 2026 | Slab Worthy rebrand |
| 4.0.0 | Feb 2, 2026 | Docker + barcode scanning |
| 3.0.0 | Feb 1, 2026 | eBay Collector extension |

---

*Last updated: February 2, 2026 (Session 23)*
