# LOCATIONS — Where Things Live in This Repo

*Read this first when returning to Slab Worthy after time away. One-page index of where to look for everything. Updated: 2026-05-26.*

---

## Identity / Strategy

| Looking for | Path |
|---|---|
| Project overview for humans | `README.md` |
| DO (Claude Code) operating context | `CLAUDE.md` |
| BO (Claude.ai) primer | `docs/SW_BO_PRIMER.md` *(mirror of BO project upload)* |
| Three patents (pending) | `docs/business/provisional_patent_*.docx`, `docs/business/PATENT_FILING_GUIDE.md` |
| Brand guide | **OVERDUE.** Old `BRAND_GUIDELINES.txt` is at `archive/old-brand/` (pre-pivot, indigo brand, not current). Current brand exists only in `CLAUDE.md` header and the live CSS. |

## Business / Financials / Market

| Looking for | Path |
|---|---|
| Year 1 P&L (canonical) | `docs/business/SlabWorthy_Year1_PnL.xlsx` |
| Competitive analysis | `docs/business/COMPETITORS.txt` |
| Hosting/infra costs | `docs/business/BUDGET.md` |
| Slab Guard B2B licensing pitch | `docs/business/Slab_Guard_Licensing_Proposal.docx`, `docs/business/SlabGuard_WhitePaper_DRAFT.docx`, `docs/business/Slab_Guard_Marketing_Overview.docx` |
| Facebook content / calendar | `docs/business/SW Facebook Content.docx`, `SW_Facebook_Calendar.docx` *(at root, untracked)* |

## Engineering

| Looking for | Path |
|---|---|
| Entry point (Flask) | `wsgi.py` |
| All routes (87 endpoints, 19 blueprints) | `routes/` |
| Route catalog | `routes/ROUTE_MAPPING.md` |
| Grading engine | `grading_engine.py` |
| Comic extraction (AI vision) | `comic_extraction.py` |
| Signature matcher v2 | `routes/signatures.py` (HTTP), `signatures/` (logic) |
| eBay integration | `ebay_oauth.py`, `ebay_listing.py`, `ebay_description.py`, `ebay_valuation.py` |
| Marketplace prep (non-eBay) | `marketplace_prep.py`, `whatnot_description.py` |
| Third-party dependency monitor | `dependency_monitor.py` |
| DB migrations | `migrations/` (also root-level `db_migrate_*.py` legacy scripts) |
| Architecture map | `docs/technical/ARCHITECTURE.txt` |
| API reference | `docs/technical/API_REFERENCE.md` |
| DB schema (16 tables) | `docs/technical/DATABASE_PRODUCTION.md` |
| Comic Registry / Slab Guard schema | `docs/technical/COMIC_REGISTRY_SCHEMA.md` |
| Fingerprinting concept | `docs/technical/COMIC_FINGERPRINTING_CONCEPT.txt`, `docs/technical/FINGERPRINTING_PROJECT_SUMMARY.md` |
| Troubleshooting playbook | `docs/technical/TROUBLESHOOTING.md` |

## Frontend (Cloudflare Pages, root-level HTML)

| Looking for | Path |
|---|---|
| Landing page | `index.html` |
| Grading flow | `app.html` |
| Collection management (modular) | `collection.html` + `js/collection.js`, `js/ebay-modal.js`, `js/marketplace-modal.js` |
| Verify page (Slab Guard lookup) | `verify.html` |
| Account / billing | `account.html` |
| Admin dashboard | `admin.html` |
| Signature admin | `signatures.html` |
| Sidebar (shared) | `js/sidebar.js` |

## Sessions / Planning

| Looking for | Path |
|---|---|
| Most recent session detail | `docs/sessions/WHERE_WE_LEFT_OFF.md` |
| Full session history | `docs/sessions/CLAUDE_NOTES.txt` |
| Roadmap (mixed planning + session log) | `docs/sessions/ROADMAP.txt` |
| Active to-do list | `TODO.md` |
| Initial plan (historical) | `PLAN.md` |
| Unified admin plan | `docs/UNIFIED_ADMIN_PLAN.md` |

## Deploy / Ops

| Looking for | Path |
|---|---|
| Render config | `render.yaml` |
| Docker | `Dockerfile`, `Aptfile` |
| Python deps | `requirements.txt` |
| Cloudflare Pages routing | `_redirects`, `_routes.json` |
| Service worker (PWA) | `sw.js`, `manifest.json` |
| Android TWA | `android-twa/` |
| Health check endpoint | `https://collectioncalc-docker.onrender.com/health` |

## Archive (stale-but-keep)

See `archive/README.md` for the index. Patches, mockups, old FB assets, old P&L drafts, SDCC plan, pre-pivot brand guide, .docx duplicates, old test plans.

---

## Things this index does NOT solve

- **Repo name vs product name mismatch.** The GitHub repo is `Fevit1/collectioncalc`. The product is Slab Worthy. Rename is deferred until after GalaxyCon (Render hooks, Cloudflare config, webhooks all reference the old name).
- **Schema-exceeds-wiring risk.** Files documented here may describe capability that's not fully wired in production. When in doubt, grep for the consuming code path before relying on a feature.
- **Currency.** This index assumes the cleanup state as of 2026-05-26. Update when meaningful new top-level files land.
