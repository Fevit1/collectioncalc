# Copy audit — about, pricing, faq, contact, verify — 2026-09-20

Read-only. No edits made. These five pages became crawlable on 2026-09-20 (`0a35a6b`) without an audit. Rule: the
page matches the product as deployed in this repo today. Audited by a read-only agent; the two findings that
change a decision (F1, F4) were re-checked by hand against the code. **Awaiting Mike's approval before any edit.**

## ⚠️ F0 — THE HOMEPAGE SENTENCE SHIPPED TODAY IS FALSE AGAINST THE CODE
`index.html` (shipped `0a35a6b`): "Registration isn't open to new accounts yet; verifying is free for everyone."
**In the deployed code registration is OPEN to every plan:** `PLANS['free']['slab_guard_registrations'] = 3`, Pro 25
(`routes/billing.py:61,80`); `/api/registry/register` checks only that count (`routes/registry.py:521-534`); the
Register button is live on every collection row and on the grade result (`js/collection.js`, `app.html`).
`pricing.html:744,769` and `faq.html:509,530` say so ("Register 3 comics", "included on every plan, including
Free"). What is closed is the **Guard TIER** (unpurchasable), not registration. I wrote that sentence from Mike's
answer ("a free user can verify by serial only") and his confirmation, without checking the mechanism — the lesson
candidate from 09-17 (copy checked against copy, not against the code), committed by me two days later.
**One position has to be picked, and it is Mike's:** (a) registration IS open → the homepage is wrong; proposed:
"Slab Guard™ — comic fingerprinting. Register your comics (3 on Free, 25 on Pro); anyone can verify a serial for
free." or (b) registration SHOULD be closed → then the code, pricing and FAQ are wrong and closing it is a backend
change. Until then the homepage under-claims (safe for a buyer, wrong for the record).

## Ranked findings (1 = most misleading to a paying visitor)

| # | where | claim | verdict | evidence | proposed copy |
|---|---|---|---|---|---|
| F1 | pricing.html:767, compare row :837-839 | "Multi-photo grading (4 angles)" as a PRO-only benefit (Free "—") | **FALSE** | `/api/grade` takes four photos on every plan; only the monthly cap is checked (`routes/grading.py:503-640`); `app.html:1096-1134` gives everyone four slots; `account.html:760-767` already says "every tier, free included". The one real Pro photo feature (`/api/images/upload-extra`) has no frontend caller. | Delete the Pro bullet and the compare row; add to Free: "4-photo grading (front, spine, back, centerfold)". Pro then differs on its caps: 100 gradings, 25 registrations. |
| F2 | pricing.html:856 | "14-day free trial. No credit card required to start." | **PARTLY — second sentence FALSE** | Checkout is `mode='subscription'`, `payment_method_types=['card']`, no `payment_method_collection='if_required'` (`routes/billing.py:648-662`); 14 days true (`:163`). | "Yes. Pro comes with a 14-day free trial. You enter a card at checkout and are not charged until the trial ends; cancel before then and you pay nothing." |
| F3 | pricing.html:804, meta :9; verify.html:518-519 | "our Chrome extension monitors eBay listings and flags candidate sightings"; "Slab Guard theft monitoring"; "monitors marketplace listings" | **FALSE** | No scheduler anywhere; `routes/monitor.py` is request-driven; the only monitor is the unpublished unpacked extension, gated on `chrome_extension` = Guard/Dealer, both unpurchasable (`billing.py:156`). `faq.html:540-550` itself says the extension is "in development and not yet available" — the pages contradict each other. | pricing: "Slab Guard records a comic with a visual fingerprint and a serial number anyone can look up… A browser extension that flags listings while you browse eBay is in development and not yet available." Meta: "Slab Worthy pricing. AI comic grading estimates, fair market value from recent sales, and Slab Guard comic registration." verify: "Slab Guard™ records each comic with a visual fingerprint and a serial number. Buyers can check any serial before purchase." |
| F4 | pricing.html:744,769,842-844; faq.html:509,530 | "Register 3 comics" / "25" / "included on every plan, including Free" | **TRUE in code — contradicts the homepage** | see F0 | depends on F0's decision |
| F5 | faq.html:580-582, :593 | "multi-signal forensic analysis… metadata, compression patterns, lighting… to detect screenshots"; "may be asked to provide additional proof of possession" | **FALSE** | `utils/photo_authenticity.py` is a CLI nothing imports; registration runs `assess_photo_quality` only — resolution, blur, keypoints, EXIF orientation (`routes/registry.py:133-213, 591-607`). No flag/review/challenge flow exists. | "When you register a comic we check the front-cover photo for resolution, sharpness and detail. Photos too small or too blurry to fingerprint are refused; marginal ones get a warning. We do not currently detect screenshots or web-saved images." Delete the "What if my photo gets flagged" item. |
| F6 | faq.html:489 | "unique visual fingerprint using Amazon Rekognition" | **FALSE** | Fingerprint = pHash/dHash/aHash/wHash + edge-strip hashes via `imagehash` (`routes/registry.py:6, 373-376, 415-418`); Rekognition is content moderation only. | "…we generate a visual fingerprint from your photos and assign a serial number anyone can verify publicly." |
| F7 | pricing.html:866 (and terms.html:406) | "Monitoring alerts will pause on the free plan"; "we never delete them" | **FALSE / PARTLY** | Nothing sends or pauses monitoring alerts; `marketplace_monitoring` is only read by `/plans` and `/my-plan`; sighting emails go out on every plan (`routes/verify.py:598-609`). Deleting a collection item deletes its registration (`routes/collection.py:263`). ⚠️ terms.html is a legal page — same line, separate decision. | "Your registered comics stay registered when you downgrade. If you are over your new plan's limit you can't register more until you upgrade or remove some. Sighting reports still reach you on every plan." |
| F8 | verify.html:714-728 | public "Signature" row printing "NN% label" | **PARTLY — contradicts today's rule** | `routes/verify.py:264-273` returns creator + confidence; Mike's 09-20 rule: no "high", no bare percentage. Seen beside it: the response also returns the raw `cover_url` and a masked owner email though its docstring says "without PII". | "Signature match (AI, not authentication): {creator}" with no number — ships with the prompt unit's badge copy, or hide the row until then. |
| F9 | about.html:335, :326 | "Not vague ranges. Not hedging. A clear recommendation." | **PARTLY** | `app.html:2923, 2965-2969` renders ROUGH ESTIMATE, MARGINAL, YEAR NEEDED and "Can't say" by design. | ":335 → "A clear recommendation when the sales support one, and a plainly labelled rough estimate when they don't." :326 → "…a straight answer where the data supports one: Worth the Slab, Marginal, or Keep it Raw." |
| F10 | faq.html:395-397 | FMV factors: "Edition variations and variants", "Current market demand and trends", "Time-based pricing patterns" | **FALSE / PARTLY** | Trimmed median + bootstrap CI over 365 days (`routes/sales_valuation.py:5-8, 732`); variants are EXCLUDED, not valued (`:466-467, 593`); no trend or recency term; Market Pulse is SOON. | "Sold prices from eBay and Whatnot over the past year" · "Sales at comparable grades" · "The median, with outliers trimmed" · "Sales labelled as variants, newsstand or direct editions are left out" |
| F11 | faq.html:614, 640, 656 | support email shows as "[email protected]" | **BROKEN** | Cloudflare email-obfuscation residue pasted into the SOURCE (`__cf_email__` spans) with no decode script on the live page; the link at :614 goes nowhere. Checked: `privacy.html` and `terms.html` are CLEAN in source — Cloudflare obfuscates them at the edge and injects `email-decode.min.js`, so they work. Only `faq.html` (2) and `app.html` (1) have the residue saved into the source. | plain `mailto:support@slabworthy.com`, as `contact.html:369` does. |
| F12 | pricing.html:875-876 | "the Dealer plan gives you the tools. The serial verification feature lets you check any Slab Guard serial" | **PARTLY** | Dealer unpurchasable (`billing.py:156, 591`); serial verification is public and free (`routes/verify.py:144`). | "The Dealer plan is in development and not yet available. Serial verification is already free for everyone at slabworthy.com/verify. Email us if you run a shop and want to hear when Dealer opens." |
| F13 | pricing.html:768 | "Personal adjustments" as a Pro benefit | **FALSE** | `user_adjustments.py` is an orphan SQLite module; "My Val" is on every plan (`routes/collection.py:286-311`). | delete the bullet |
| F14 | pricing.html:788, 793 | "Notify me →" | **PARTLY** | goes to the general contact form; no notify list exists | "Contact us →" |
| F15 | about.html:350 | "We don't sell your info. Ever." | **PARTLY** | `js/footer.js:12-20` loads the Meta Pixel; `privacy.html:316, 349` says that sharing may be a "sale"/"share" under CCPA. | "We don't sell your info for money. We use the Meta Pixel to measure our ads; details and opt-out are in the Privacy Policy." |
| F16 | faq.html:550 vs verify.html:745-752 | "use Report a Sighting" for any match | **PARTLY** | the form shows only when status is `reported_stolen` | "If a comic's serial shows Reported Stolen, the verify page lets you Report a Sighting and the owner is alerted…" |
| F17 | faq.html:641; contact.html:316, 365 | "respond within 24 hours" | **UNVERIFIABLE — and false next week** | solo founder offline ~5 days from 09-23 | "We usually reply within a few days." |
| F18 | pricing.html:733 | Free: "Try everything" | **PARTLY** | Free lacks the Pro caps and Signature ID | "Grade and value your comics. No credit card needed." |
| F19 | faq.html:299 | "faster if we've previously assessed this comic in similar condition" | **PARTLY** | the cache is title+issue valuation, 48 h; condition is not in it and grading always runs | "Most assessments finish in a minute or two after upload." |
| F20 | faq.html:359 | "All your assessments are saved in My Collection" | **PARTLY** | saving is a user action | "Save an assessment to My Collection to keep it." |
| F21 | faq.html:610-611 | "Over 10MB"; "JPG, PNG, and WEBP" | **PARTLY** | picker accepts HEIC too; no 10 MB constant found | "We accept JPG, PNG, WEBP and HEIC." |
| F22 | faq.html:331 | "We'll note this limitation in your Slab Report" | **UNVERIFIABLE** | only a pre-grade warning found (`app.html:1165`) | "We warn you before grading when photos are missing." |
| F23 | faq.html:509 | serial format "SW-YYYY-NNNNNN" | **FALSE (minor)** | alphanumeric: `routes/registry.py:81-108`, `verify.html:436` | "SW-YYYY-XXXXXX" |
| F24 | about.html:362 | CollectionCalc "same team… a platform" | **UNVERIFIABLE** | external site | "Slab Worthy grew out of CollectionCalc, the same founder's earlier collector tools." |
| F25 | faq.html:393 | "tens of thousands of sales and growing every day" | **UNVERIFIABLE from repo; "every day" overstated** | capture is human-run, not a feed | "…and growing as we capture more" |

**Not claims, but found:** `faq.html` and `verify.html` have no meta description (Google will pick its own snippet —
on verify that is the false monitoring paragraph, F3); `verify.html` sets `data-no-universal-footer` so the shared
footer never renders though a comment expects it; `faq.html:520, 549` link to `/check.html`, which robots now
disallows — and `/check` takes a PHOTO, not a serial, so "needs a serial" in the 09-20 record is wrong;
"The owner has been notified" on verify shows even when `owner_notified` is false.
**NOT found on any of the five pages:** Sell Alerts, PDF/CSV/export, "launching", "summer 2026", convention
language, "CGC-equivalent", "guaranteed", "real-time". No page states a retention period; no page says "Patented".

## Verified TRUE (so they need no change)
Pro $4.99 / $49.99 and "Save $9.89 / 17%" (`billing.py:75-76`); 25 and 100 gradings a month, 429 at the cap
(`billing.py:60,79`; `grading.py:553-607`); 14-day trial (`billing.py:163`); Free needs no card; Guard and Dealer shown
with no price and no checkout, refused server-side (`billing.py:156, 591-595`); over-limit registration block on
downgrade (`billing.py:381-400`); "Patent pending" wording everywhere, no count stated; four photos with the front
cover the minimum; sales from eBay and Whatnot; "not affiliated with CGC/CBCS"; public verification with no login;
sighting email without exposing the owner, 3 per serial per 24 h (`verify.py:373-447`).

## Unverifiable from the repo (what would settle each)
Live Stripe price IDs = $4.99/$49.99 (env vars → Stripe dashboard); whether the Stripe PORTAL lets a subscriber
switch to Guard, which would bypass the purchase gate (`billing.py:148-152` warns of it → Stripe dashboard);
cancel-at-period-end behaviour; refund practice ("no questions asked" is stronger than the terms' "contact us").

## Coverage
Read in full: the five pages' head and body copy, `js/footer.js`. Read in part: `routes/billing.py` 1-750,
`routes/verify.py`, `routes/grading.py` 480-640, `routes/registry.py`, `routes/images.py`, `routes/monitor.py`,
`app.html`, `account.html`, `robots.txt`. Grepped only: `routes/collection.py`, `routes/sales_valuation.py`,
`routes/vision.py`, `auth.py`, `js/sidebar.js`, `js/collection.js`, `check.html`, `terms.html`, `privacy.html`.
Not checked: the database, the Stripe dashboard, the Render environment, the full Slab Report render, upload size
limits in `js/utils.js`, `privacy.html` and `terms.html` themselves.
