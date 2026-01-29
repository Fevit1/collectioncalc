













\# Claude Working Notes - CollectionCalc Project



\## - most recent update (to override info below):



* Add to "Bugs Fixed Today":
* ✅ Mobile JS broken: app.html still referenced old app.js path instead of modular /js/\*.js files from v2.96.0 split
* 
* Add to "Pending":
* Mobile UI testing on actual device (tabs work now, need visual/layout review)
* 
* Session note:
* Claude in Chrome connection issue - not resolved, used DevTools mobile emulation instead







\## IMPORTANT RULES

1\. \*\*Always describe what I plan to build and wait for Mike's approval BEFORE writing any code. Do not build until approved.\*\*

2\. \*\*Break large code changes into small chunks\*\* to avoid "thinking longer than usual" failures.

3\. \*\*Update this file at checkpoints\*\* (see Checkpoint System below).

4\. \*\*Proactively push back and provide input\*\* - Mike wants Claude to flag potential issues, suggest alternatives, and ask "have you considered..." when there are trade-offs. Don't just execute - use knowledge from other projects and patterns.

5\. \*\*Follow brand guidelines\*\* - All user-facing text, UI elements, animations, and design decisions should align with BRAND\_GUIDELINES.md. Check terminology, tone, and visual principles before implementing.

6\. \*\*Verify file integrity before delivering\*\* - Check line count, verify proper closing brackets/braces, and compare to original if editing. Files have been truncated in the past.



\## Checkpoint System

Update CLAUDE\_NOTES.md when:

\- ✅ After any context compacting (conversation got long)

\- ✅ After completing a major feature

\- ✅ Before ending a session

\- ✅ If Mike says "let's checkpoint" or "update notes"



This ensures we can recover quickly if a conversation fails or needs to restart.



\## About Mike

\- \*\*Name:\*\* Mike (legal name Don, goes by Mike)

\- \*\*Role:\*\* Product Manager in high tech, manages people (not hands-on dev)

\- \*\*Background:\*\* Former eBay employee (marketing/content supply chain, not engineering)

\- \*\*Technical comfort:\*\* Decent SQL skills, but not a developer

\- \*\*Strengths:\*\* Product vision, feature prioritization, testing, user feedback, UI/UX decisions

\- \*\*Learning style:\*\* Appreciates guidance but wants Claude to recognize when he's mastered something and stop over-explaining

\- \*\*Collaboration style:\*\* Wants Claude to push back on decisions (UI, data flow, database, backend) and proactively share knowledge



\## What Mike's Comfortable With

\- ✅ Render dashboard (deployments, environment variables, redeploys)

\- ✅ Git workflow (add, commit, push)

\- ✅ PowerShell aliases (`purge`, `deploy`)

\- ✅ Testing the app and providing feedback

\- ✅ SQL concepts

\- ✅ Product decisions and prioritization



\## Where They Need More Guidance

\- ⚠️ Complex Python debugging - explain error meanings

\- ⚠️ Architecture decisions - explain trade-offs



\## Project: CollectionCalc / Slab Worthy



\### Core Info

\- \*\*What it is:\*\* AI-powered comic book valuation and pre-grading assessment tool

\- \*\*Stack:\*\* Python/Flask backend, vanilla HTML/JS frontend, PostgreSQL database

\- \*\*Hosted on:\*\* Render.com

\- \*\*Live URL:\*\* https://collectioncalc.com

\- \*\*Version:\*\* 2.95.0



\### Key Product Features

\- \*\*Manual Entry\*\* - Type title/issue/grade for valuation

\- \*\*Photo Upload\*\* - AI extracts comic info from cover photo

\- \*\*Slab Worthy?\*\* - 4-photo grading assessment flow (Patent Pending, filed Jan 27, 2026)

\- \*\*Slab Report\*\* - Output of Slab Worthy with grade estimate and recommendation

\- \*\*Whatnot Extension\*\* - Browser extension for live stream valuations



\### Key Files

\- `app.html` - Main frontend

\- `app.js` - Frontend JavaScript

\- `styles.css` - Styling

\- `ebay\_valuation.py` - Backend valuation logic

\- `comic\_extraction.py` - AI photo analysis

\- `wsgi.py` - Flask app entry point

\- `auth.py` - Authentication

\- `admin.py` - Admin panel



\### Brand Guidelines Summary

Reference BRAND\_GUIDELINES.md for full details. Key points:

\- \*\*Voice:\*\* Expert, approachable, honest, helpful (not salesy or hyperbolic)

\- \*\*Terminology:\*\* Use "assess" or "check" not "grade" (CGC grades, we assess)

\- \*\*Animations:\*\* Purposeful and informative, NOT gambling metaphors (no slots, dice, spinning wheels)

\- \*\*Loading text:\*\* "Analyzing..." matches existing patterns

\- \*\*Patent Pending:\*\* Display on Slab Worthy feature, not on Slab Report output



\## Current Session (January 28, 2026)



\### Bugs Fixed Today

1\. ✅ Button text: "Grade Another" → "Check Another" (avoids grading terminology)

2\. ✅ FMV cache key mismatch: Added grade normalization (VF+/VF/VF- → "VF")

3\. ✅ Image rotation: Added "↻ Rotate" button for manual rotation

4\. ✅ Rotation banner update: Comic ID banners now update after rotation

5\. ✅ Loading state: Show "Analyzing..." during rotation re-analysis

6\. ✅ Patent Pending placement: Moved from "Slab Report" to top of Slab Worthy flow



\### Documents Updated Today

\- BRAND\_GUIDELINES.md v2.0 - Expanded with voice, terminology, animation principles, GenAI compatibility



\### Pending

\- Mobile parity fixes (user found "lots of problems")

\- FAQ content (pressing, newsstand vs direct, valuation methodology, grade scale, CGC costs)

\- Pricing model

\- Business model canvas

\- Competitive analysis (CovrPrice, GoCollect, Key Collector, CLZ, ComicMint AI)



\## Deployment Commands

```powershell

\# Deploy and clear cache

git add .; git commit -m "message"; git push; purge



\# Just clear Cloudflare cache

purge

```





