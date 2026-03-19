# Whatnot Comic Valuator - Roadmap

## Current Status (v2.40.1 - January 2026)

**Whatnot Valuator is a Chrome extension that provides real-time comic valuations during Whatnot live auctions.** It's part of the larger CollectionCalc ecosystem and serves as a unique data acquisition pipeline for live auction sales data.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     WHATNOT VALUATOR                            │
│                   Chrome Extension v2.40.1                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Apollo Cache │  │ Claude Vision│  │ Key Database │           │
│  │   Reader     │  │   Scanner    │  │  (500+ keys) │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│         │                 │                 │                    │
│         ▼                 ▼                 ▼                    │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Content Script                           ││
│  │  - Listing detection  - Auto-scan  - Sale tracking          ││
│  └─────────────────────────────────────────────────────────────┘│
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│               COLLECTIONCALC BACKEND (Render)                   │
│              collectioncalc.onrender.com                        │
├─────────────────────────────────────────────────────────────────┤
│  POST /api/sales/record  │  GET /api/sales/count                │
│  GET /api/sales/recent   │  GET /api/valuate                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              POSTGRESQL DATABASE (Render)                       │
│               collectioncalc-db                                 │
├─────────────────────────────────────────────────────────────────┤
│  market_sales    │ search_cache  │ users  │ collections         │
│  (618+ records)  │ (eBay cache)  │        │                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✅ Completed Features

### Phase 1: Foundation (v1.0-v1.5)
- [x] Chrome extension skeleton (MV3)
- [x] Draggable overlay on Whatnot auction pages
- [x] Basic title parsing with ComicNormalizer
- [x] Static FMV database (later deprecated)
- [x] eBay sold link generation

### Phase 2: Data Collection (v2.0-v2.18)
- [x] Apollo GraphQL cache reader
- [x] Real-time listing detection
- [x] Sale detection (DOM "Sold" text monitoring)
- [x] Local sale tracking (chrome.storage)
- [x] ~~Supabase~~ → CollectionCalc cloud integration
- [x] Multi-tab support
- [x] Extension popup with stats

### Phase 3A: Data Quality (v2.19-v2.21)
- [x] 30-second debounce for duplicate prevention
- [x] Bad title blocklist (lot, choice, pick, mystery, bundle, buck)
- [x] Bids capture
- [x] Viewer count capture
- [x] Slab type detection (CGC/CBCS/PGX)
- [x] Improved title/issue parsing

### Phase 3B: Computer Vision (v2.22-v2.27)
- [x] Claude Vision API integration
- [x] Video frame capture from live stream
- [x] Comic identification (title, issue, grade, variant)
- [x] Manual scan button (📷 Scan)
- [x] Vision result UI with Apply/Dismiss
- [x] API key management (⚙️ Settings)
- [x] Vision data persists for sale recording
- [x] Variant detection (newsstand, price variants, virgin, etc.)

### Phase 3C: Smart Automation (v2.28-v2.39)
- [x] Auto-scan toggle (defaults ON)
- [x] Smart scan trigger (only when DOM has garbage data)
- [x] Real FMV from database (replaced static database)
- [x] grade_source tracking (slab_label, seller_verbal, vision_cover, dom)
- [x] Raw grade estimates with "cover-only" warning
- [x] Skip FMV for garbage titles
- [x] Wait for bidding before auto-scan
- [x] Price-drop detection for new item signal
- [x] Duplicate scan prevention (10-second cooldown)
- [x] Local key issue database lookup (500+ keys)

### Phase 3D: CollectionCalc Integration (v2.40)
- [x] Migrated from Supabase to CollectionCalc PostgreSQL
- [x] 618 historical sales migrated
- [x] `/api/sales/record` endpoint for sale recording
- [x] `/api/sales/count` endpoint for stats
- [x] `/api/sales/recent` endpoint for FMV queries

### Phase 3E: Audio Transcription (v2.25 - Built, Hidden)
- [x] Audio capture from video element
- [x] OpenAI Whisper integration
- [x] Grade parsing from speech
- [ ] Better UX (currently hidden - hard to time with seller)

---

## 🔄 In Progress

### Data Collection
- Collecting sales data across various auctions
- Building FMV database through usage
- **618+ sales recorded** (migrated to CollectionCalc)

---

## 📋 Planned Features

### Phase 4: Unified FMV Engine
- [ ] Multi-source data integration (Whatnot + eBay + PriceCharting)
- [ ] Intelligent source weighting
- [ ] Steeper recency decay (recent sales weighted higher)
- [ ] API: `GET /api/fmv?title=X&issue=Y&grade=Z`
- [ ] Extension calls unified FMV instead of local calculation

### Phase 5: Visual Tuning Dashboard
- [ ] Admin interface for FMV model parameters
- [ ] Sliders for recency decay, source weights
- [ ] Live preview of price impact
- [ ] A/B testing support
- [ ] Rollback capability

### Phase 6: Self-Improving Model
- [ ] Collect prediction accuracy metrics
- [ ] AI recommends weight adjustments
- [ ] Human approval workflow
- [ ] Eventually: auto-tune within guardrails

### Phase 7: Friend Beta Prep
- [ ] Analytics (track usage patterns)
- [ ] Feedback mechanism (Report Issue link)
- [ ] Landing page copy
- [ ] Error states handled gracefully
- [ ] API key instructions

### Phase 8: Enhanced Features
- [ ] Re-enable audio with better UX
- [ ] Continuous listening mode
- [ ] Bid recommendations
- [ ] Watchlist integration
- [ ] Mobile companion app

---

## 💡 Ideas Backlog

- Browser notification on deals
- Export sales to CSV
- Compare prices across sellers
- Grading company price differences
- Signature series premium calculation
- Census data integration
- Seller reputation tracking
- Day/time auction patterns

---

## Data Sources

| Source | Type | Unique Value | Status |
|--------|------|--------------|--------|
| Whatnot Live | Live auction | True price discovery | ✅ 618+ sales |
| eBay Completed | Auction + BIN | Highest volume | ✅ In CollectionCalc |
| eBay Active BIN | Current listings | Price ceiling | ✅ In CollectionCalc |
| PriceCharting | Aggregated | Historical trends | 📋 Planned |
| GoCollect | CGC census | Population data | 📋 Planned |

---

## Known Limitations

| Limitation | Impact | Current Workaround |
|------------|--------|-------------------|
| Vision sees cover only | Can't assess spine/back/pages | Trust seller, mark as "cover estimate" |
| Audio timing hard | Miss seller's verbal grade | Manual grade input |
| Some sellers use garbage titles | DOM data useless | Auto-scan with Vision |
| Stale DOM data | Title doesn't update between items | Price-drop detection (v2.39) |

---

## Version History Summary

| Version | Date | Key Changes |
|---------|------|-------------|
| v1.0 | Jan 2026 | Basic overlay |
| v2.0 | Jan 2026 | Apollo reader, sale detection |
| v2.10 | Jan 2026 | Supabase integration |
| v2.19 | Jan 2026 | Duplicate prevention, bad title filter |
| v2.22 | Jan 2026 | Vision scanning |
| v2.28 | Jan 2026 | Auto-scan |
| v2.29 | Jan 2026 | Real FMV from Supabase |
| v2.34 | Jan 2026 | Raw grade estimates, grade_source tracking |
| v2.39 | Jan 2026 | Price-drop detection, key database lookup |
| v2.40 | Jan 2026 | **CollectionCalc integration** (Supabase removed) |
| v2.40.1 | Jan 2026 | Fixed API URL |

---

## Cost Estimates

| Feature | Cost | Notes |
|---------|------|-------|
| Vision scan | ~$0.01-0.03 | Per scan (Claude Sonnet) |
| Audio transcription | ~$0.006/min | OpenAI Whisper (unused) |
| CollectionCalc DB | $7/month | Render PostgreSQL Basic |
| 100 scans/session | ~$1-3 | Typical auction session |
