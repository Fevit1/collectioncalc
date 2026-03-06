# Slab Worthy

**AI-powered grading, valuation, and collection management for comics and collectibles.**

Slab Worthy helps collectors answer the question every owner asks: "Is this worth getting graded?" Using AI vision for grading, real eBay sales data for valuations, and tools for listing and selling, Slab Worthy is a one-stop platform for comic collectors — with baseball card support planned for Q4 2026.

## Core Features

**AI Grading** — Upload photos of your comic and get a structured grade (0.5–10.0 scale) using an 8-category scoring system. Consistent results backed by multi-run averaging.

**Real-Time Valuations** — Grade-specific fair market values powered by 24,000+ eBay sales. Median-based FMV with outlier trimming and bootstrap 95% confidence intervals.

**Collection Management** — Track your entire collection with sortable columns, search, era filtering, and bulk actions. Optimistic UI for instant feedback.

**eBay Listing Integration** — List comics directly to eBay from your collection. Supports fixed-price and auction formats with OAuth 2.0 authentication.

**Signature Identification** — Reference database of 23+ artists with 97 signature images. AI-powered matching with premium analysis (signing adds ~40-57% to value).

**Slab Guard Registration** — Register comics with perceptual fingerprinting for theft detection and provenance tracking. Patent pending (Application #63/990,743).

**Slabbing ROI Calculator** — Factors in CGC grading costs (2026 pricing), current raw value, and graded FMV to tell you if slabbing is worth it.

**Multi-Platform Marketplace Prep** — AI-generated listing content for Whatnot, eBay, Mercari, Facebook, Heritage, and more. Download photos, copy-paste to seller dashboards.

## Planned: Baseball Card Vertical (Q4 2026)

Card-specific grading (centering, corners, edges, surface), PSA/BGS/SGC cost calculator, card extraction (player, year, set, card number), and Slab Guard for cards. TAM: 15-20M card-collecting households in the US.

## Tech Stack

- **Backend**: Python / Flask (19 blueprints, 87 routes)
- **Database**: PostgreSQL on Render (16 tables)
- **Frontend**: Vanilla HTML/CSS/JS on Cloudflare Pages
- **Image Storage**: Cloudflare R2
- **AI**: Anthropic Claude API (grading, extraction, signature matching)
- **Payments**: Stripe (subscription billing)
- **Marketplace**: eBay Inventory API (OAuth 2.0)
- **Auth**: JWT with role-based access (user, approved, admin)

## Architecture

```
Cloudflare Pages (Frontend)
    ├── app.html          — Grading flow (upload → grade → value → save)
    ├── collection.html   — Collection management + eBay listing
    ├── verify.html       — Slab Guard verification
    ├── signatures.html   — Admin signature management
    └── index.html        — Landing page + waitlist

         │ API calls (JWT auth)
         ▼

Render (Backend — Flask)
    ├── routes/           — 19 blueprint files
    │   ├── auth.py, collection.py, grading.py
    │   ├── sales_valuation.py, sales_ebay.py
    │   ├── ebay.py, signatures.py, monitor.py
    │   └── admin_routes.py, billing.py, ...
    ├── grading_engine.py — 8-category structured grading
    ├── comic_extraction.py — AI vision extraction
    ├── ebay_listing.py   — eBay Inventory API integration
    └── wsgi.py           — App factory + blueprint registration

         │ Data
         ▼

PostgreSQL (Render)         Cloudflare R2 (Images)
    16 tables                   Comic photos
    24,000+ eBay sales          Signature references
    Comic registry              Grading uploads
```

## Documentation

- [Database Schema (Production)](docs/technical/DATABASE_PRODUCTION.md) — All 16 tables with full column schemas
- [Route Mapping](routes/ROUTE_MAPPING.md) — All 87 routes across 19 blueprint files
- [API Reference](docs/technical/API_REFERENCE.md) — Backend modules and function signatures
- [Comic Registry Schema](docs/technical/COMIC_REGISTRY_SCHEMA.md) — Slab Guard fingerprinting system
- [Budget & Hosting](docs/business/BUDGET.md) — Infrastructure costs
- [Year 1 P&L](docs/business/SlabWorthy_Year1_PnL.xlsx) — Revenue/cost projection for 15K users

## Project Status

**Pre-launch (Session 80)** — Targeting GalaxyCon San Jose (Aug 21-23, 2026) for alpha launch, with soft launch July 21, 2026. Baseball card vertical planned for Q4 2026.

**Year 1 projection (15K users):** $739K revenue, $379K net profit (51% margin) including employee + marketing costs.

Founder: Mike Berry

---

*Slab Worthy — Know before you slab.*
