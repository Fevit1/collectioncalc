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

## Key Files
- `ebay_valuation.py` - Main backend logic (valuations, caching, API, per-tier confidence)
- `ebay_oauth.py` - eBay OAuth flow, token storage/refresh
- `ebay_listing.py` - eBay listing creation via Inventory API (now with draft mode, image upload)
- `ebay_description.py` - AI-generated descriptions (300 char, key issues, mobile-optimized)
- `comic_extraction.py` - Backend extraction via Claude vision (with Vision Guide prompt)
- `index.html` - Frontend (single page app)
- `wsgi.py` - Flask routes (v3.4)
- `requirements.txt` - Python dependencies

## QuickList - The Full Pipeline
**QuickList** is our name for the complete flow from photo to eBay listing:

1. **Upload** - User uploads photos of comics
2. **Extract** - AI reads photo, pulls title, issue, grade, newsstand/direct, etc.
3. **Derive** - AI determines publisher, year, description
4. **Review** - User reviews extraction, can modify/approve
5. **Valuate** - Get three-tier pricing (Quick Sale, Fair Value, High End)
6. **List** - Create eBay draft listing (user publishes when ready)

## Current State (January 20, 2026)

### Completed This Session 🎉
**QuickList batch processing + UI overhaul + Vision Guide**

- **Draft mode for eBay** - Listings now create as drafts by default (`publish=False`)
- **Photo upload to eBay** - New `upload_image_to_ebay()` function, `/api/ebay/upload-image` endpoint
- **Backend extraction** - New `comic_extraction.py` with Claude vision
- **Batch endpoints:**
  - `/api/extract` - Extract single comic from photo
  - `/api/batch/process` - Extract + Valuate + Describe multiple comics (no eBay yet)
  - `/api/batch/list` - Upload images + Create drafts (after user approval)
- **Input validation** - Max 20 comics per batch, 10MB max image size
- **Removed 60-second delay** - Was leftover from Tier 1, slowing batch valuations
- **UI updates:**
  - Three price boxes (Quick Sale, Fair Value, High End) side by side
  - Fair Value selected by default with visual highlight
  - "List on eBay" button per comic in batch results
  - Removed confidence row from main display (details available via 📊 icon)
  - Removed refresh/regenerate button
  - **Sort options** - Sort by Value (High/Low), Title (A-Z), or Order Added
  - **Header sync fix** - Editing title/issue field now updates header immediately
- **Vision Guide for extraction** - Improved prompt to distinguish issue numbers from prices (fixed FF #242 being read as #206)

### Known Issues / TODOs
- [ ] More progress steps during valuation (users think it's frozen)
- [ ] Custom price entry (not just the three tiers)
- [ ] Host our own placeholder image (not external URL)
- [ ] eBay account deletion notification endpoint (GDPR)

### API Endpoints (Current)
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

### eBay Integration Technical Details
- **Category ID:** 259104 (Comics & Graphic Novels - leaf category)
- **Package dimensions:** 1" x 11" x 7", 8 oz, packageType: LETTER
- **Condition mapping:** MT/NM→LIKE_NEW, VF→USED_EXCELLENT, FN/VG→USED_VERY_GOOD, G→USED_GOOD, FR/PR→USED_ACCEPTABLE
- **SKU format:** `CC-{title}-{issue}-{timestamp}` (ensures uniqueness)
- **Draft mode:** `publish=False` (default) returns `drafts_url` to Seller Hub

### Anthropic API Rate Limits
| Tier | Tokens/Min | Tokens/Day | Requirement |
|------|-----------|------------|-------------|
| Tier 1 | 30,000 | 1M | Default |
| **Tier 2 (Current)** | **450,000** | **50M** | **$40 spend** |
| Tier 3 | 1,000,000 | 100M | $200 spend |
| Tier 4 | 2,000,000+ | Unlimited | Enterprise |

Tier 2 is sufficient for beta. No more delays needed between valuations!

## Deployment Process
1. Claude creates/updates files in `/mnt/user-data/outputs/`
2. Mike downloads the file(s) to `cc/v2` folder
3. Mike runs: `git add .; git commit -m "message"; git push; deploy`
   - Note: `deploy` is a PowerShell alias that triggers Render deploy hook
   - Must include `git push` or Render rebuilds old code!

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

## Pre-Launch Requirements (Before Other Users)
- [ ] Implement eBay account deletion notification endpoint (GDPR compliance)
- [ ] Host our own placeholder image (not external URL)
- [x] Draft mode for listings (done!)
- [x] Photo upload for listings (done!)
- [x] Test full QuickList flow with real comics (done - 5 comics tested!)

## Future Considerations
- **Batch listing groups:** e.g., "List all 12 issues of Secret Wars" as a batch action
- **Bulk processing:** Tier 2 comfortable for 20-50 comics/minute
- **Travel agent AI:** Mike's idea for future product (autonomous booking with user approval)
- **Parallel valuations:** Could speed up batch processing further

## Friends Beta Checklist
- [ ] Analytics (know who's using it)
- [ ] Mobile works
- [ ] Cloudflare Access (auth)
- [ ] Custom domain live
- [ ] Feedback mechanism (Report Issue link?)
- [ ] Landing copy explains what it does
- [ ] Error states handled gracefully
- [ ] Anthropic billing alerts set

## Related Documents
- [ROADMAP.md](ROADMAP.md) - Feature backlog with version history
- [ARCHITECTURE.md](ARCHITECTURE.md) - System diagrams

---
*Last updated: January 20, 2026 (Session 2)*
