# Claude Working Notes - CollectionCalc Project

## IMPORTANT RULE
**Always describe what I plan to build and wait for Mike's approval BEFORE writing any code. Do not build until approved.**

## About Mike
- **Name:** Mike (legal name Don, goes by Mike)
- **Role:** Product Manager in high tech, manages people (not hands-on dev)
- **Background:** Former eBay employee (marketing/content supply chain, not engineering)
- **Technical comfort:** Decent SQL skills, but not a developer
- **Strengths:** Product vision, feature prioritization, testing, user feedback, UI/UX decisions
- **Learning style:** Appreciates guidance but wants Claude to recognize when he's mastered something and stop over-explaining

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
- `ebay_listing.py` - eBay listing creation via Inventory API (includes policy lookup, merchant location, package dimensions)
- `ebay_description.py` - AI-generated descriptions (300 char, key issues, mobile-optimized)
- `index.html` - Frontend (single page app)
- `wsgi.py` - Flask routes (v3.3)
- `requirements.txt` - Python dependencies

## Current State (January 19, 2026)

### Just Completed (This Session) 🎉
**MAJOR MILESTONE: First live eBay listing created from CollectionCalc!**

- Upgraded Anthropic API to Tier 2 (450k tokens/min, $60 credits)
- Switched from eBay Sandbox to Production
- Fixed OAuth redirect URLs (collectioncalc.onrender.com)
- eBay business policies setup (shipping, payment, returns)
- Fixed condition enums (LIKE_NEW, USED_EXCELLENT, etc.)
- Added auto-create merchant location
- Added policy lookup (finds user's existing policies)
- Added placeholder image support (temporary Mercari URL)
- Added package weight/dimensions for calculated shipping
- Fixed SKU uniqueness (timestamp-based)
- Fixed category ID (259104 = Comics & Graphic Novels)
- **Successfully created and published live eBay listing!**

### eBay Integration Technical Details
- **Category ID:** 259104 (Comics & Graphic Novels - leaf category)
- **Package dimensions:** 1" x 11" x 7", 8 oz, packageType: LETTER
- **Condition mapping:** MT/NM→LIKE_NEW, VF→USED_EXCELLENT, FN/VG→USED_VERY_GOOD, G→USED_GOOD, FR/PR→USED_ACCEPTABLE
- **SKU format:** `CC-{title}-{issue}-{timestamp}` (ensures uniqueness)
- **Placeholder image:** Currently using external URL (need to host our own)

### Pending Decision
- **Draft vs Live:** Currently listings go live immediately. Mike considering whether to:
  1. Change to create drafts only (user publishes after adding photos)
  2. Add UI option for "Save as Draft" vs "List Now"

### Known Issues / TODOs
- Need to host our own placeholder image (not use Mercari's)
- Photo upload not yet implemented
- Listings go live immediately (no draft option yet)
- Before other users: Must implement eBay account deletion notification endpoint

### Anthropic API Rate Limits
| Tier | Tokens/Min | Tokens/Day | Requirement |
|------|-----------|------------|-------------|
| Tier 1 | 30,000 | 1M | Default |
| **Tier 2 (Current)** | **450,000** | **50M** | **$40 spend** |
| Tier 3 | 1,000,000 | 100M | $200 spend |
| Tier 4 | 2,000,000+ | Unlimited | Enterprise |

Tier 2 is sufficient for beta. Consider Tier 3 only if processing 100+ comics regularly.

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
- **Details on demand:** Confidence and analysis hidden behind toggle
- **Three tiers:** Quick Sale (green), Fair Value (highlighted), High End (amber)
- **No confidence colors on boxes:** Too confusing without context
- **48-hour cache:** Balance between freshness and API costs
- **Future pricing:** ~$400/week for 25k comics if doing weekly refresh (defer until revenue)
- **eBay description tone:** Professional (sets us apart, looks reliable)
- **eBay returns:** Let eBay handle via seller's existing policies
- **Calculated shipping:** Requires package dimensions in inventory item

## Pre-Launch Requirements (Before Other Users)
- [ ] Implement eBay account deletion notification endpoint (GDPR compliance)
- [ ] Host our own placeholder image (not external URL)
- [ ] Decide on draft vs live listing default
- [ ] Photo upload for listings

## Future Considerations
- **Bulk processing:** Tier 2 comfortable for 20-50 comics/minute, 100+ may need pacing
- **Travel agent AI:** Mike's idea for future product (autonomous booking with user approval)

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
*Last updated: January 19, 2026*
