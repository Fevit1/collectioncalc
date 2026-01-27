# Claude Working Notes - CollectionCalc Project

## IMPORTANT RULES
1. **Always describe what I plan to build and wait for Mike's approval BEFORE writing any code. Do not build until approved.**
2. **Break large code changes into small chunks** to avoid "thinking longer than usual" failures.
3. **Update this file at checkpoints** (see Checkpoint System below).
4. **Proactively push back and provide input** - Mike wants Claude to flag potential issues, suggest alternatives, and ask "have you considered..." when there are trade-offs. Don't just execute - use knowledge from other projects and patterns.

## Checkpoint System
Update CLAUDE_NOTES.md when:
- ✅ After any context compacting (conversation got long)
- ✅ After completing a major feature
- ✅ Before ending a session
- ✅ If Mike says "let's checkpoint" or "update notes"

This ensures we can recover quickly if a conversation fails or needs to restart.

## About Mike
- **Name:** Mike (legal name Don, goes by Mike)
- **Role:** Product Manager in high tech, manages people (not hands-on dev)
- **Background:** Former eBay employee (marketing/content supply chain, not engineering)
- **Technical comfort:** Decent SQL skills, but not a developer
- **Strengths:** Product vision, feature prioritization, testing, user feedback, UI/UX decisions
- **Learning style:** Appreciates guidance but wants Claude to recognize when he's mastered something and stop over-explaining
- **Collaboration style:** Wants Claude to push back on decisions (UI, data flow, database, backend) and proactively share knowledge

## What Mike's Comfortable With
- ✅ Render dashboard (deployments, environment variables, redeploys)
- ✅ Git workflow (add, commit, push - can do from memory!)
- ✅ `git status` to check what's staged
- ✅ Testing the app and providing feedback
- ✅ SQL concepts
- ✅ Product decisions and prioritization
- ✅ Cloudflare Pages deployment
- ✅ PowerShell aliases (created `deploy` command)
- ✅ Curl basics (for deploy hooks)
- ✅ eBay Developer Portal (credentials, RuNames, OAuth setup)
- ✅ eBay Business Policies
- ✅ Knows frontend vs backend deployment (`purge` vs `deploy`)
- ✅ DBeaver for database management (Session 8) 🆕
- ✅ Chrome extension installation/testing (Session 8) 🆕

## Where Mike May Need More Guidance
- ⚠️ New terminal/bash commands - explain what each command does
- ⚠️ Python debugging - don't assume he can interpret error messages
- ⚠️ File structure - be explicit about where files go and why
- ⚠️ New workflows - guide first time, then trust him after that
- ⚠️ API integrations - explain the concepts before diving into code

## Communication Preferences
- Concise is good, but don't skip steps
- For new workflows: Give explicit "do this, then this" instructions
- For learned workflows: Trust him to do it (don't over-explain git anymore)
- After creating files: Always explain the next action needed
- Check in if something might be confusing
- **PowerShell syntax:** Use semicolons not `&&` for chained commands
  - Correct: `git add .; git commit -m "message"; git push; deploy`
  - Wrong: `git add . && git commit -m "message" && git push && deploy`

## Project: CollectionCalc
- **What it is:** AI-powered comic book valuation tool
- **Vision:** Multi-collectible platform (comics first, then sports cards, Pokemon, etc.)
- **Stack:** Python/Flask backend, vanilla HTML/JS frontend, PostgreSQL database
- **Hosted on:** Render.com (backend + DB), Cloudflare Pages (frontend)
- **Live URL:** https://collectioncalc.com (frontend), https://collectioncalc.onrender.com (backend API)
- **Note:** Backend is `collectioncalc.onrender.com` NOT `collectioncalc-v2.onrender.com`

## Key Files - NOW SPLIT INTO 3 FILES!
**Frontend (Cloudflare Pages):**
- `index.html` - HTML structure only (~310 lines)
- `styles.css` - All CSS (~1350 lines)
- `app.js` - All JavaScript (~2030 lines)

**Backend (Render):**
- `ebay_valuation.py` - Main backend logic (valuations, caching, API, per-tier confidence)
- `ebay_oauth.py` - eBay OAuth flow, token storage/refresh
- `ebay_listing.py` - eBay listing creation via Inventory API (now with draft mode, image upload)
- `ebay_description.py` - AI-generated descriptions (300 char, key issues, mobile-optimized)
- `comic_extraction.py` - Backend extraction via Claude vision (with Vision Guide prompt)
- `auth.py` - User authentication (signup, login, JWT, password reset)
- `wsgi.py` - Flask routes (v3.8) 🆕

**Whatnot Valuator (Chrome Extension):** 🆕
- `manifest.json` - Extension config (v2.40.1)
- `content.js` - Main overlay, auction monitoring, sale capture
- `lib/collectioncalc.js` - API client (replaced supabase.js)
- `lib/vision.js` - Claude Vision scanning
- `data/keys.js` - 500+ key issue database

## QuickList - The Full Pipeline
**QuickList** is our name for the complete flow from photo to eBay listing:

1. **Upload** - User uploads photos of comics
2. **Extract** - AI reads photo, pulls title, issue, grade, newsstand/direct, etc.
3. **Derive** - AI determines publisher, year, description
4. **Review** - User reviews extraction, can modify/approve
5. **Valuate** - Get three-tier pricing (Quick Sale, Fair Value, High End)
6. **List** - Create eBay draft listing (user publishes when ready)

## Current State (January 25, 2026)

### Session 8 Progress 🔧 🆕

**1. Fixed Whatnot Extension Auto-Scan Bugs**
- **Stale listing detection** - DOM title wasn't updating between auction items
- Solution: Added price-drop detection (>50% drop + under $20 = new item)
- **Duplicate scans** - Multiple scans firing for same item
- Solution: Added 10-second cooldown after force-scanning

**2. Fixed Key Issue Detection**
- Captain Marvel #1 wasn't showing 🔑 icon
- Root cause: Key database existed but wasn't being queried after Vision scan
- Solution: Added `lookupKeyInfo()` function that checks local database (500+ keys)
- Added Captain Marvel #1, Marvel Super-Heroes #12-13 to database

**3. Set Up DBeaver** ✅
- Installed DBeaver for database management
- Connected to both Supabase (via pooler) and Render PostgreSQL
- Can now query/manage databases with GUI

**4. Created market_sales Table** ✅
```sql
CREATE TABLE market_sales (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,              -- 'whatnot', 'ebay_auction', 'ebay_bin'
    title TEXT,
    series TEXT,
    issue TEXT,                        -- TEXT for "1A" variants
    grade NUMERIC,
    grade_source TEXT,
    slab_type TEXT,
    variant TEXT,
    is_key BOOLEAN DEFAULT FALSE,
    price NUMERIC NOT NULL,
    sold_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    raw_title TEXT,
    seller TEXT,
    bids INTEGER,
    viewers INTEGER,
    image_url TEXT,
    source_id TEXT,
    UNIQUE(source, source_id)
);
```

**5. Migrated 618 Sales from Supabase → Render** ✅
- Exported CSV from Supabase via DBeaver
- Generated INSERT statements
- Loaded into Render PostgreSQL
- All historical data preserved

**6. Built Sales API Endpoints** ✅
Added to wsgi.py (now v3.8):
- `POST /api/sales/record` - Record sales from extension
- `GET /api/sales/count` - Get total count
- `GET /api/sales/recent` - Get recent sales

**7. Rewired Extension to CollectionCalc** ✅
- Replaced `lib/supabase.js` with `lib/collectioncalc.js`
- Same interface, different backend
- Extension now writes directly to CollectionCalc PostgreSQL
- **Supabase dependency completely removed!**

### Extension Version Progression (Session 8)
| Version | Changes |
|---------|---------|
| v2.39.1 | Fixed stale listing detection (price-drop signal) |
| v2.39.2 | Fixed duplicate scans (10-second cooldown) |
| v2.39.3 | Added key issue database lookup |
| v2.40.0 | Migrated to CollectionCalc API |
| v2.40.1 | Fixed API URL (Render not Cloudflare) |

### Database Connection Details 🆕
**Render PostgreSQL:**
| Field | Value |
|-------|-------|
| Host | `dpg-d5knv4koud1c73dt21pg-a.oregon-postgres.render.com` |
| Port | `5432` |
| Database | `collectioncalc_db` |
| Username | `collectioncalc_db_user` |
| Password | (in Render dashboard) |

**Tables:**
- `search_cache` - eBay valuation cache (48hr TTL)
- `market_sales` - All sales from all sources (618+ records) 🆕
- `users` - User accounts
- `collections` - Saved comics
- `password_resets` - Reset tokens
- `ebay_tokens` - OAuth tokens

### Known Issues / TODOs
- [ ] **EXIF rotation not working** - deployed but needs debugging (Session 7)
- [ ] More progress steps during valuation (users think it's frozen)
- [ ] Custom price entry (not just the three tiers)
- [ ] Unified FMV engine (combine Whatnot + eBay data) 🆕

### Premium Tier Discovery (Session 7) 💎
**Opus can detect subtle signatures that Sonnet cannot!**

Testing with Moon Knight #1 (signed by Danny Miki in gold marker):
| Model | Result |
|-------|--------|
| Sonnet | `signature_detected: false` ❌ |
| Opus | `signature_detected: true`, listed all creators with confidence % ✅ |

**Current state:** Opus detects signature EXISTS and lists all possible signers. User picks correct one. (It guessed Finch but was actually Miki - can't identify WHO signed, just THAT it's signed.)

**Code location:** `app.js` line ~1211
```javascript
// STANDARD TIER: Sonnet
model: 'claude-sonnet-4-20250514',

// PREMIUM TIER: Opus (commented out)
// model: 'claude-opus-4-5-20251101',
```

## API Endpoints (Current)
| Endpoint | Purpose |
|----------|---------|
| `/api/valuate` | Get three-tier valuation for a comic |
| `/api/messages` | Proxy to Anthropic (frontend extraction) |
| `/api/extract` | Backend extraction from photo |
| `/api/batch/process` | QuickList Step 1: Extract + Valuate + Describe (multiple) |
| `/api/batch/list` | QuickList Step 2: Upload images + Create drafts |
| `/api/sales/record` | Record sale from Whatnot extension 🆕 |
| `/api/sales/count` | Get total sales count 🆕 |
| `/api/sales/recent` | Get recent sales 🆕 |
| `/api/ebay/upload-image` | Upload single image to eBay Picture Services |
| `/api/ebay/list` | Create eBay listing (supports `publish` and `image_urls` params) |
| `/api/ebay/generate-description` | AI-generated 300-char description |
| `/api/ebay/auth` | Start eBay OAuth flow |
| `/api/ebay/callback` | eBay OAuth callback |
| `/api/ebay/status` | Check eBay connection status |
| `/api/auth/signup` | Create new user account |
| `/api/auth/login` | Authenticate, return JWT |
| `/api/auth/verify/<token>` | Verify email address |
| `/api/auth/forgot-password` | Send password reset email |
| `/api/auth/reset-password` | Reset password with token |
| `/api/auth/me` | Get current user (requires JWT) |
| `/api/collection` | Get user's saved comics |
| `/api/collection/save` | Save comics to collection |
| `/api/collection/<id>` | Update/delete collection item |

## Deployment Process
1. Claude creates/updates files in `/mnt/user-data/outputs/`
2. Mike downloads the file(s) to `cc/v2` folder
3. **Frontend changes (index.html, styles.css, app.js):** `git add .; git commit -m "message"; git push; purge`
4. **Backend changes (*.py files):** `git add .; git commit -m "message"; git push; deploy`
5. **Both:** `git add .; git commit -m "message"; git push; deploy; purge`

**PowerShell aliases:**
- `deploy` - triggers Render deploy hook (backend)
- `purge` - purges Cloudflare cache (frontend)

## eBay Credentials (Production)
- **App ID:** DonBerry-Collecti-PRD-8b446dc71-59cfad05
- **RuName:** Don_Berry-DonBerry-Collec-cipbkmzlb
- **Redirect URL:** https://collectioncalc.onrender.com/api/ebay/callback
- **Environment:** Production (EBAY_SANDBOX=false or not set)

## Product Decisions Made
- **Keep it simple:** Users just need Title, Issue, Grade
- **Details on demand:** Confidence and analysis hidden behind toggle (📊 icon)
- **Three tiers:** Quick Sale, Fair Value (default/highlighted), High End
- **QuickList flow:** Extract → Review → Valuate → List (user approves before eBay interaction)
- **48-hour cache:** Balance between freshness and API costs
- **eBay description tone:** Professional (sets us apart, looks reliable)
- **eBay returns:** Let eBay handle via seller's existing policies
- **Calculated shipping:** Requires package dimensions in inventory item
- **Price selection:** User picks tier or enters custom price (Fair Value default)
- **Signature detection:** AI confidence scores with CGC/CBCS disclaimer
- **Whatnot integration:** Extension writes to CollectionCalc, not Supabase 🆕

## Environment Variables (Render)
| Key | Purpose |
|-----|---------|
| `DATABASE_URL` | PostgreSQL connection |
| `ANTHROPIC_API_KEY` | AI valuations/extraction |
| `EBAY_CLIENT_ID` | eBay API |
| `EBAY_CLIENT_SECRET` | eBay API |
| `EBAY_RUNAME` | eBay OAuth redirect |
| `RESEND_API_KEY` | Email service |
| `RESEND_FROM_EMAIL` | noreply@collectioncalc.com |
| `JWT_SECRET` | Auth token signing |
| `FRONTEND_URL` | https://collectioncalc.com |

## Friends Beta Checklist
- [ ] Analytics (know who's using it)
- [x] Mobile works ✅
- [x] User auth (email/password) ✅
- [x] Custom domain live ✅ - collectioncalc.com
- [ ] Feedback mechanism (Report Issue link?)
- [ ] Landing copy explains what it does
- [ ] Error states handled gracefully
- [ ] Anthropic billing alerts set
- [x] Collections (save comics) ✅
- [x] Whatnot data pipeline ✅ 🆕

## Related Documents
- [ROADMAP.md](ROADMAP.md) - Feature backlog with version history
- [ARCHITECTURE.md](ARCHITECTURE.md) - System diagrams (updated Session 8)

## Quick Reference - Testing Commands

**Test CollectionCalc API:**
```bash
curl https://collectioncalc.onrender.com/api/sales/count
# Returns: {"count": 618}
```

**Test Whatnot Extension (browser console on Whatnot page):**
```javascript
window.ApolloReader.getCurrentListing()  // Get current listing
window.lookupKeyInfo('Amazing Spider-Man', '300')  // Test key lookup
```

**DBeaver Quick Connect:**
- Host: `dpg-d5knv4koud1c73dt21pg-a.oregon-postgres.render.com`
- Database: `collectioncalc_db`
- User: `collectioncalc_db_user`

---
*Last updated: January 25, 2026 (Session 8 - Whatnot integration, market_sales table, 618 sales migrated)*
