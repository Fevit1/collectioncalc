# Claude Working Notes - CollectionCalc Project

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
- `index.html` - Frontend (single page app)
- `wsgi.py` - Flask routes
- `requirements.txt` - Python dependencies

## Current State (January 17, 2026)

### Just Completed
- Three-tier pricing (Quick Sale / Fair Value / High End)
- Per-tier confidence scoring (different confidence for each price tier)
- UI simplification:
  - Removed Publisher and Year fields (AI auto-detects)
  - Added "Details" toggle (replaces Market Data button)
  - Confidence scores now in Details section
  - Clean, minimal results display

### In Progress
- eBay Developer account approval (waiting ~1-2 business days)
- Cloudflare Access setup for authentication (weekend task)

### Tomorrow's Agenda (Weekend)
1. **Analytics setup** - Track usage (Mike has Wordle site with 90 users/day, wants better insights)
2. **Mobile testing** - Make sure it works on phone before friends try it
3. **Cloudflare custom domain** - Point collectioncalc.com to Pages
4. **Cloudflare Access** - Email-based auth for friends beta

### Next Up
- Cloudflare custom domain setup (collectioncalc.com)
- Cloudflare Access (email-based auth for friends beta)
- eBay listing integration (once API approved)
- Bulk results table view (future UI improvement)
- Advanced options (CGC, signed comics, etc.)

## Deployment Process
1. Claude creates/updates files in `/mnt/user-data/outputs/`
2. Mike downloads the file(s) to `cc/v2` folder
3. Mike runs: `git add .` → `git commit -m "message"` → `git push`
4. Render auto-deploys from GitHub

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
- [ ] Bulk photo/video upload + extraction
- [ ] Table view for multi-comic results  
- [ ] Batch description generation
- [ ] Bulk listing with batch review
- [ ] User tone preference setting for descriptions
- [ ] Mobile timeout fix for fresh valuations

---
*Last updated: January 17, 2026*
