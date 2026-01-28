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

## About Mike
- **Name:** Mike (legal name Don, goes by Mike)
- **Role:** Product Manager in high tech, manages people (not hands-on dev)
- **Background:** Former eBay employee (marketing/content supply chain, not engineering), went to law school but didn't practice
- **Technical comfort:** Decent SQL skills, but not a developer
- **Learning style:** Appreciates guidance but wants Claude to recognize when he's mastered something and stop over-explaining
- **Collaboration style:** Wants Claude to push back on decisions and proactively share knowledge

## What Mike's Comfortable With
- ✅ Render dashboard, Git workflow, Cloudflare Pages
- ✅ PowerShell aliases (`deploy`, `purge`)
- ✅ eBay Developer Portal, Business Policies
- ✅ DBeaver for database management
- ✅ Chrome extension installation/testing
- ✅ USPTO Patent Center filing 🆕

## Communication Preferences
- Concise is good, but don't skip steps for new workflows
- **PowerShell syntax:** Use semicolons not `&&` for chained commands

## Project: CollectionCalc / Slab Worthy

### Brand Split
- **CollectionCalc** = Backend, valuations, eBay listings, collection storage
- **Slab Worthy** = Pre-grade assessment tool ("should I submit to CGC?")

### Domains
- collectioncalc.com (live)
- slabworthy.com (registered)

### Stack
- Python/Flask backend, vanilla HTML/JS frontend, PostgreSQL
- Hosted on: Render.com (backend + DB), Cloudflare Pages (frontend)

## Key Files

**Frontend (ALL IN cc/v2/ root - NO frontend/ subfolder!):**
- `app.html` - Main application (with Slab Worthy tab)
- `styles.css` - All CSS (grading styles appended)
- `app.js` - All JavaScript (grading script appended)
- `admin.html`, `signatures.html`, `index.html`

**Backend:**
- `wsgi.py`, `ebay_valuation.py`, `ebay_oauth.py`, `ebay_listing.py`
- `comic_extraction.py`, `auth.py`, `admin.py`, `r2_storage.py`

## Current State (January 28, 2026)

### Session 12 Progress 🆕

**Deployed Slab Worthy to Production! ✅**
- Fixed truncated app.html (was missing `<script src="app.js"></script>`)
- Added defensive null checks to grading report rendering
- Feature is LIVE and working

**Bug Found During Testing:**
- Rotated comic photos cause misidentification (Atari Force at 90° → read as "Alpha Flight", "A-Force")
- Need to auto-orient images before sending to Claude Vision

### Session 11 Progress

**1. PATENT FILED! 🎉**
- "System and Method for Automated Comic Book Condition Assessment Using Multi-Angle Imaging and Artificial Intelligence"
- USPTO, Small Entity ($320)
- **STATUS: PATENT PENDING**
- Priority date: January 27, 2026

**2. Built "Slab Worthy?" Feature**
- New tab with custom SVG slab icon
- 5-step flow: Front (required) → Spine → Back → Centerfold → Report
- Device detection (mobile: camera, desktop: upload)
- Photo quality feedback
- Grade report with "Should you grade?" recommendation
- Confidence scales: 1 photo = 65%, 4 photos = 94%

### Backlog Items (Prioritize Next Session)

**Bugs/Quick Fixes:**
- [ ] **Image rotation fix** - Auto-orient photos before Claude Vision (EXIF or detect orientation)
- [ ] **Button text** - Change "Grade Another" → "Slab Worthy Another"

**Performance:**
- [ ] **Valuation speed** - "Should you grade?" takes too long
- [ ] **FMV caching check** - Verify we're caching valuations (same comic+grade shouldn't re-call API)

**Business/Legal Questions:**
- [ ] **Trademark "Slab Report"?** - Distinctive term for our grade analysis output
- [ ] **Trademark "Slab Worthy"?** - Core brand term
- [ ] **CGC partnership** - Affiliate/commission for referrals? User discount? How to track users? (Blockchain for attribution?)

**Product Questions:**
- [ ] **Keep Photo Upload mode?** - Now that Slab Worthy exists, is it redundant?
- [ ] **Batch grading** - Can users Slab Worthy multiple comics at once? Should they?

### Testing Needed
- [ ] Test Slab Worthy with real comic photos (various conditions)
- [ ] Compare 1-photo vs 4-photo grading accuracy
- [ ] Buy CGC-graded comics to validate accuracy
- [ ] Test rotated/sideways photos

### Session 10 Progress (Jan 26)
- Facsimile detection, signature database, FMV endpoint
- Admin fixes, extension auto-scan fixes
- slabworthy.com registered

## Deployment Process
- **Frontend:** `git add .; git commit -m "msg"; git push; purge`
- **Backend:** `git add .; git commit -m "msg"; git push; deploy`

## Key Product Decisions
- **Pre-grade positioning** - NOT competing with CGC/CBCS
- **"Slab Worthy?"** branding for grading feature
- **4 photos:** Front (required), Spine, Back, Centerfold (recommended)
- **Patent covers:** Multi-angle photo + AI + economic decision engine

---
*Last updated: January 28, 2026 (Session 12)*
