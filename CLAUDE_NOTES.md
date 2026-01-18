# Claude Working Notes - CollectionCalc Project

## IMPORTANT RULE
**Always describe what I plan to build and wait for Mike's approval BEFORE writing any code. Do not build until approved.**

## About Mike
- **Name:** Mike (not "this user"!)
- **Role:** Product Manager in high tech, manages people (not hands-on dev)
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

## Project: CollectionCalc
- **What it is:** AI-powered comic book valuation tool
- **Vision:** Multi-collectible platform (comics first, then sports cards, Pokemon, etc.)
- **Stack:** Python/Flask backend, vanilla HTML/JS frontend, PostgreSQL database
- **Hosted on:** Render.com (backend + DB), Cloudflare Pages (frontend)
- **Live URL:** https://collectioncalc.com (pending Cloudflare setup)

## Key Files
- `ebay_valuation.py` - Main backend logic (valuations, caching, API, per-tier confidence)
- `ebay_oauth.py` - eBay OAuth flow, token storage/refresh
- `ebay_listing.py` - eBay listing creation via Inventory API
- `ebay_description.py` - AI-generated descriptions (300 char, key issues, mobile-optimized)
- `index.html` - Frontend (single page app)
- `wsgi.py` - Flask routes (v3.3)
- `requirements.txt` - Python dependencies

## Current State (January 18, 2026)

### Just Completed (This Session)
- eBay OAuth integration working (sandbox)
- eBay "List on eBay" buttons for all 3 price tiers
- Listing preview modal with editable description
- AI-generated descriptions:
  - 300 character limit (mobile-optimized for eBay)
  - Highlights KEY ISSUES (first appearances, etc.)
  - Excludes title/publisher/year (shown in eBay fields)
  - Excludes grade (shown in eBay item specifics)
  - No "review photos" text (seller policies handle that)
- Fixed profanity filter (word boundaries - "Cassidy" no longer flagged)
- Placeholder image with branded calculator icon
- Render upgraded to Starter tier ($7/mo) - no more cold starts

### Known Issues
- Rate limit (30k tokens/min) - hit during rapid testing
- Description caching not implemented yet (planned)

### In Progress
- eBay listing actually posting to eBay (sandbox testing)
- Waiting to test AI descriptions without rate limits

### Next Session Should
1. Test AI description generation (wait for rate limits to clear)
2. Confirm listing posts to eBay sandbox
3. Consider description caching to avoid rate limits
4. Set up eBay seller policies (shipping, returns) in sandbox

## Deployment Process
1. Claude creates/updates files in `/mnt/user-data/outputs/`
2. Mike downloads the file(s) to `cc/v2` folder
3. Mike runs: `git add .; git commit -m "message"; git push; deploy`
   - Note: `deploy` is a PowerShell alias that triggers Render deploy hook
   - Must include `git push` or Render rebuilds old code!

## Product Decisions Made
- **Keep it simple:** Users just need Title, Issue, Grade
- **Details on demand:** Confidence and analysis hidden behind toggle
- **Three tiers:** Quick Sale (green), Fair Value (highlighted), High End (amber)
- **No confidence colors on boxes:** Too confusing without context
- **48-hour cache:** Balance between freshness and API costs
- **Future pricing:** ~$400/week for 25k comics if doing weekly refresh (defer until revenue)
- **eBay description tone:** Professional (sets us apart, looks reliable)
- **eBay returns:** Let eBay handle via seller's existing policies

## Future Considerations
- **Bulk processing costs:** Need to understand how processing 5, 10, 100 comics at once affects Anthropic API costs and response time. Consider batching strategies, Haiku for bulk operations, or parallel vs sequential processing. (Cross this bridge when we build bulk features)

## Friends Beta Checklist
- [ ] Analytics (know who's using it)
- [ ] Mobile works
- [ ] Cloudflare Access (auth)
- [ ] Custom domain live
- [ ] Feedback mechanism (Report Issue link?)
- [ ] Landing copy explains what it does
- [ ] Error states handled gracefully
- [ ] Anthropic billing alerts set

## Future Investigation
- [ ] **Bulk processing costs** - Understand how processing multiple comics (10, 50, 100) affects Anthropic API costs and response time. Important for pricing decisions.

## Roadmap Items (from conversations)
- [ ] Fuzzy matching for misspelled titles (save API costs)
- [ ] Description caching (avoid regenerating same comic)
- [ ] Best Offer support (enable/disable, auto-accept/decline thresholds)
- [ ] Bulk photo/video upload + extraction
- [ ] Table view for multi-comic results  
- [ ] Batch description generation
- [ ] Bulk listing with batch review
- [ ] User tone preference setting for descriptions
- [ ] Mobile timeout fix for fresh valuations

---
*Last updated: January 18, 2026*
