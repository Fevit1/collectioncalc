# CollectionCalc Product Roadmap

## Vision
Build the most accurate, transparent, and user-friendly comic book valuation tool powered by AI vision + deterministic pricing models.

## Priorities
**Cheap > Good > Fast** (until market validation)

## Budget Target
- Phase 1: ~$0-3/month
- Phase 2: ~$15/month  
- Phase 3: ~$50/month (with revenue)

## Target Users
- **Primary**: Collectors cataloging personal collections (like Mike with 600 comics)
- **Secondary**: Sellers pricing inventory for sale
- **Future**: Dealers, shops, auction houses

---

## ✅ COMPLETED (Phase 0)

### Core MVP
- [x] Photo upload (bulk + single)
- [x] Claude Vision extraction (title, issue, publisher, year, grade, edition)
- [x] Web search valuations
- [x] Edit interface with all fields
- [x] Excel export
- [x] Dark mode React app
- [x] Local testing setup (proxy-server.py)

### Performance Optimization
- [x] Rate limit handling (3-sec delays for extraction, 40-sec for valuation)
- [x] Local pricing database (SQLite)
- [x] 143 starter comics with values
- [x] 55 key issues documented

### Valuation Model v1
- [x] Deterministic pricing algorithm
- [x] Grade multipliers (23 grades)
- [x] Edition multipliers (newsstand, CGC, signatures, etc.)
- [x] Explainable calculations ("show your work")
- [x] Confidence scoring

### Feedback System v1
- [x] User correction logging
- [x] Suggested weight adjustments
- [x] Basic analytics

---

## 🚧 CURRENT (Phase 1) - User Management & Security

### Three-Tier Model System
- [x] Tier 1: Global model (protected, admin-curated)
- [x] Tier 2: Personal adjustments (per-user overrides)
- [x] Tier 3: Feedback analytics (insight only)

### User Management
- [x] User profiles with trust scores
- [x] Exclude/include users from feedback consideration
- [x] Correction count tracking
- [x] Audit trail for adjustments

### Reporting Engine
- [x] Accuracy overview report
- [x] Grade analysis report
- [x] Edition analysis report
- [x] Publisher analysis report
- [x] User contribution report
- [x] Outlier detection report
- [x] Time series trends report
- [ ] Export reports to PDF/Excel

### Documentation & Diagrams
- [x] Architecture diagram (Mermaid)
- [x] Database schema diagram (Mermaid)
- [x] Budget/hosting strategy
- [x] API documentation
- [ ] GitHub Pages hosting for docs

### API v3
- [x] POST /api/valuate (full breakdown)
- [x] POST /api/feedback (log corrections)
- [x] User adjustments endpoints
- [x] User exclusion endpoints
- [x] Reporting endpoints
- [x] Admin endpoints
- [ ] Rate limiting per user

---

## 📋 NEXT (Phase 2) - Intelligence & Visualization

### Natural Language Query Interface
- [ ] "Show me all VF corrections from last week"
- [ ] "Which grades are we undervaluing?"
- [ ] "Compare Marvel vs DC accuracy"
- [ ] "Find users with suspicious patterns"
- [ ] Query → SQL generation → Results → Visualization

### Auto-Generated Visualizations
- [ ] Accuracy trend charts
- [ ] Grade multiplier comparison
- [ ] User contribution pie chart
- [ ] Outlier scatter plot
- [ ] Time series line graphs
- [ ] Publisher breakdown bar chart

### Dashboard UI
- [ ] Real-time metrics dashboard
- [ ] Filterable data tables
- [ ] Interactive charts (Chart.js/D3)
- [ ] Admin panel for user management
- [ ] One-click report generation

### Advanced Analytics
- [ ] Anomaly detection (auto-flag outliers)
- [ ] Cohort analysis (new users vs veterans)
- [ ] A/B testing framework (test weight changes)
- [ ] Predictive accuracy (before applying changes)

---

## 🔮 FUTURE (Phase 3) - Scale & Monetization

### Scaling Infrastructure (When Revenue Justifies)
- [ ] Render paid tier ($7/mo) - Always-on
- [ ] PostgreSQL migration (if needed)
- [ ] Redis caching
- [ ] Background job queue
- [ ] Monitoring (BetterStack)

### Database Expansion
- [ ] Partner with pricing API (GoCollect, Overstreet)
- [ ] Web scraper improvements
- [ ] Cover image recognition (variant detection)
- [ ] Barcode/UPC scanning
- [ ] Historical price tracking

### Production Infrastructure (Budget-Conscious)
- [ ] GitHub repository setup
- [ ] Cloudflare Pages (frontend) - FREE
- [ ] Render free tier (backend) - FREE
- [ ] SQLite (keep for now) - FREE
- [ ] Custom domain DNS setup
- [ ] Environment variables config
- [ ] CI/CD auto-deploy from GitHub

### User Features
- [ ] User accounts & authentication
- [ ] Collection management
- [ ] Wishlist / want list
- [ ] Price alerts ("Notify me when ASM #300 drops below $1000")
- [ ] Social features (share collection)
- [ ] Mobile app (React Native)

### Monetization
- [ ] Free tier: 50 comics/month, basic features
- [ ] Pro tier ($9/mo): Unlimited, full history, exports
- [ ] Dealer tier ($29/mo): API access, bulk operations
- [ ] Enterprise: Custom integrations

### Partnerships
- [ ] eBay integration (import sold listings)
- [ ] CGC/CBCS census data
- [ ] Convention app partnerships
- [ ] Comic shop POS integration

---

## 🎯 Portfolio Milestones

### Demo-Ready (Current Focus)
- [ ] Complete Mike's 600 comic cataloging
- [ ] Record demo video showing full workflow
- [ ] Document architecture decisions
- [ ] Prepare interview talking points

### Public Launch
- [ ] Landing page (collectioncalc.com)
- [ ] Beta signup
- [ ] Product Hunt launch
- [ ] Reddit /r/comicbookcollecting post

### Growth Metrics to Track
- Users signed up
- Comics cataloged
- Corrections submitted
- Model accuracy over time
- User retention (weekly active)

---

## Technical Debt & Improvements

### Code Quality
- [ ] Add unit tests
- [ ] Type hints throughout
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Error handling improvements
- [ ] Logging standardization

### Performance
- [ ] Batch photo processing optimization
- [ ] Database query optimization
- [ ] Image compression
- [ ] Lazy loading for large collections

### Security
- [ ] Input validation
- [ ] SQL injection prevention (parameterized queries ✓)
- [ ] Rate limiting
- [ ] HTTPS enforcement
- [ ] API key rotation

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2024-01-14 | Use SQLite over PostgreSQL | Simpler for MVP, portable |
| 2024-01-14 | Deterministic model over ML | Explainability, no training data needed |
| 2024-01-14 | Three-tier feedback system | Prevent bad actor manipulation |
| 2024-01-14 | Personal adjustments allowed | Power users want control |
| 2024-01-14 | NLQ interface in Phase 2 | Core functionality first |

---

## Interview Talking Points

### Problem Solving
> "The AI was returning inconsistent values for the same comic. I built a deterministic valuation model that shows its work - users see exactly how each factor affects the price."

### Security Thinking
> "I realized crowd-sourced feedback could be manipulated, so I designed a three-tier system: a protected global model, personal user adjustments, and feedback that informs but doesn't automatically update the model."

### Product Thinking
> "The rate limits weren't a bug to work around - they were a product constraint that led to a better architecture. Local database + selective web search is actually a better UX than hitting the API for everything."

### Full-Stack Skills
> "This project touches computer vision, NLP, database design, API development, algorithm design, and now analytics/reporting - it's a complete AI product, not just an API wrapper."

---

## Next Actions (This Week)

1. ~~Build user adjustments module~~  ✅
2. ~~Build reporting engine~~ ✅
3. ~~Create roadmap~~ ✅
4. Update API server with all new endpoints
5. Test with Captain America Annual #8 specifically
6. Integrate with existing frontend (cc-v8-slow.html)
7. Run Mike's 600 comics through the system
8. Record demo video
