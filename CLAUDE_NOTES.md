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
- `wsgi.py` - Flask routes (v3.7)
- `requirements.txt` - Python dependencies

## QuickList - The Full Pipeline
**QuickList** is our name for the complete flow from photo to eBay listing:

1. **Upload** - User uploads photos of comics
2. **Extract** - AI reads photo, pulls title, issue, grade, newsstand/direct, etc.
3. **Derive** - AI determines publisher, year, description
4. **Review** - User reviews extraction, can modify/approve
5. **Valuate** - Get three-tier pricing (Quick Sale, Fair Value, High End)
6. **List** - Create eBay draft listing (user publishes when ready)

## Current State (January 22, 2026)

### Session 7 Progress 🔧

**1. Fixed API Key Issue**
- Frontend was calling `/api/messages` without API key
- Backend was expecting `X-API-Key` header
- Root cause: "Remove API key screen" commit updated frontend but old backend was deployed
- Fix: Redeployed wsgi.py which uses server-side `ANTHROPIC_API_KEY`

**2. Split Frontend into 3 Files** ✅
- `index.html` was ~3500 lines and causing upload truncation issues
- Now split into:
  - `index.html` (310 lines) - HTML structure only
  - `styles.css` (1350 lines) - All CSS  
  - `app.js` (2030 lines) - All JavaScript
- Deployment unchanged: `git push; purge` for frontend

**3. Signature Confidence Analysis** ✅ (UI ready, needs better images to test)
- New prompt fields: `signature_detected`, `signature_analysis`
- `signature_analysis` contains:
  - `creators` - all creators on cover with roles
  - `confidence_scores` - array with name, confidence %, reasoning
  - `most_likely_signer` - highest confidence match
  - `signature_characteristics` - ink color, position, style
- New green "🖊️ Signature Analysis" UI box
- Shows confidence % for each creator
- Disclaimer about CGC/CBCS for authentication
- Auto-populates "Signed copy" checkbox with most likely signer

**4. Improved Issue # Extraction** ✅
- Now searches multiple locations: top-left, top-right, near barcode, near title
- Added hint about DC comics (top-right)
- Added "CRITICAL: You MUST find the issue number"
- Fixed Moon Knight #1 detection (was blank before)

**5. Improved Image Quality** ✅
- All images now processed through canvas (not just large ones)
- Upscales small images to 1200px minimum
- Maintains 75%+ scale, 60%+ quality minimum
- Better logging of dimensions/quality in console

**6. EXIF Orientation + Rotate Button** 🔧 NEEDS DEBUGGING
- Added EXIF orientation reading (auto-rotates based on photo metadata)
- Added ↻ rotate button on item cards
- Button rotates image 90° clockwise and re-extracts
- **STATUS: Deployed but not working - needs debugging next session**

### Known Issues / TODOs
- [ ] **EXIF rotation not working** - deployed but needs debugging
- [ ] More progress steps during valuation (users think it's frozen)
- [ ] Custom price entry (not just the three tiers)

### Premium Tier Discovery (Session 7) 💎
**Opus can detect subtle signatures that Sonnet cannot!**

Testing with Moon Knight #1 (signed by Danny Miki in gold marker):
| Model | Result |
|-------|--------|
| Sonnet | `signature_detected: false` ❌ |
| Opus | `signature_detected: true`, listed all creators with confidence % ✅ |

**Current state:** Opus detects signature EXISTS and lists all possible signers. User picks correct one. (It guessed Finch but was actually Miki - can't identify WHO signed, just THAT it's signed.)

**Future enhancement:** Reference signature database
- Buy verified creator signatures on eBay (~$1 each)
- Store as reference images
- AI compares uploaded signature to references
- Mike researching this approach

**Product opportunity:** Premium/Super User tier with Opus extraction
- Cost: ~$0.05/comic (vs $0.01 Sonnet)
- Value prop: Better signature detection
- Code ready: Just uncomment Opus line in app.js

**Code location:** `app.js` line ~1211
```javascript
// STANDARD TIER: Sonnet
model: 'claude-sonnet-4-20250514',

// PREMIUM TIER: Opus (commented out)
// model: 'claude-opus-4-5-20251101',
```

### CGC/CBCS Signature Database Research
- **No public API available** for signature verification
- JSA (CGC partner) has ~1 million signature images - internal only
- CBCS has "exemplars" library - internal only
- Authentication requires physical submission: $25/signature
- Our approach: AI-assisted confidence scores with disclaimer

### Image Quality Findings
- Facebook/Messenger compress images heavily (~458x638 = 0.3MP)
- Need 3000+ pixel images for signature detection
- **Tell testers to email original photos**, not send via social media

## API Endpoints (Current)
| Endpoint | Purpose |
|----------|---------|
| `/api/valuate` | Get three-tier valuation for a comic |
| `/api/messages` | Proxy to Anthropic (frontend extraction) |
| `/api/extract` | Backend extraction from photo |
| `/api/batch/process` | QuickList Step 1: Extract + Valuate + Describe (multiple) |
| `/api/batch/list` | QuickList Step 2: Upload images + Create drafts |
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

## Related Documents
- [ROADMAP.md](ROADMAP.md) - Feature backlog with version history
- [ARCHITECTURE.md](ARCHITECTURE.md) - System diagrams (needs update for 3-file split)

---
*Last updated: January 22, 2026 (Session 7 - Split files, signature analysis, image quality, EXIF rotation)*
