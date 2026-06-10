# eBay API — Sold/Completed Data Access Investigation (2026-06-08)

**Run by:** Claude — read-only investigation, **no code changes**. Parallel to Batch 5.
**Question:** With our current eBay developer credentials, can the Browse API (or any
current eBay API) return sold/completed listing data for comic searches? What tier/approval
is needed, what's the data shape, recency, rate limits — and how does it compare to what the
manual extension captures? This is the prerequisite for an **automated collector** AND
**Sell Now Alerts**.

> Context: the coverage audit found capture stalled ~67 days (late March → this weekend)
> across both feeds. The manual-extension model failed silently the moment attention moved.
> This investigates the durable, automated replacement.

---

## TL;DR

- **No current eBay API gives us sold comps with the credentials we have today.** Our OAuth
  app is provisioned with **Sell-side scopes only** (inventory/account/fulfillment/marketing
  + identity) — that's the "list your comic on eBay" feature. We have **zero Buy-side access**.
- **The Browse API cannot return sold data.** It is active-listings-only by design. Useful for
  *current asking prices / lowest Buy-It-Now* (relevant to Sell Now Alerts' "list it now" side),
  but it is **not a comps source**.
- **The Finding API is dead.** `findCompletedItems` (what our orphaned `slab_premium_analysis.py`
  still calls) was sold-restricted back in Oct 2020 and the entire Finding API was
  **decommissioned Feb 5, 2025**. That script cannot work and should be treated as dead code.
- **The only supported sold-data API is Marketplace Insights** (`buy.marketplace.insights`
  scope). It returns sold prices/dates over a **rolling 90-day window**. It is a **Limited
  Release** API gated behind eBay business approval — historically very hard for a solo
  developer to get. **We do not currently have it.**
- **Bottom line:** the durable automated collector is *technically* a good fit for Marketplace
  Insights, but it is **blocked on an approval we have to apply for and may not get**. Until
  then there is no first-party API path to sold comps. The decision Mike needs to make is
  about the **access application**, not about code.

---

## 1. What our app actually has today

From `ebay_oauth.py` — our requested OAuth scopes:

```
api_scope                              (base)
sell.inventory
sell.account
sell.fulfillment
sell.marketing
commerce.identity.readonly
```

**All Sell-side.** These power the user-facing "list your graded comic on eBay" flow
(`ebay_listing.py`, `ebay_oauth.py`, `routes/ebay.py`) and per-user OAuth tokens stored in
`ebay_tokens`. **There is no `buy.browse` and no `buy.marketplace.insights` scope** — we have
no Buy-side API access at all.

Env vars in use: `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `EBAY_RUNAME`, `EBAY_APP_ID`
(values not inspected; secrets not printed). These identify the app but the *scopes/approvals*
are what gate sold data, and ours are Sell-only.

**Dead code flag:** `slab_premium_analysis.py` still calls the Finding API
(`https://svcs.ebay.com/services/search/FindingService/v1`, `findCompletedItems`). That
endpoint was decommissioned in Feb 2025 — the script is non-functional and should be removed
or rewritten (not in this read-only task; flagging for backlog).

---

## 2. The current model (what we're replacing)

The live collector is **HTML scraping**, not an API:

- `CCExtensions/ebay-collector/content.js` runs on eBay **Sold** search pages (requires
  `LH_Sold=1` in the URL) and parses the DOM with `querySelector` against eBay's markup.
- It POSTs parsed rows to `/api/ebay-sales/batch` (`CCExtensions/ebay-collector/api_endpoints.py`),
  deduped on `ebay_item_id` + a content hash.
- **Captured fields:** `raw_title`, `parsed_title`, `issue_number`, `publisher`, `sale_price`,
  `sale_date`, `condition`, `graded`, `grade`, `listing_url`, `image_url`, `ebay_item_id`.
  Server-side enrichment then adds `canonical_title`, UPC, `is_reprint/_lot/_facsimile`, etc.

**Why it failed:** it depends on a human running the extension over eBay search pages. When
attention moved, capture silently stopped for 67 days — exactly the failure the audit found.
It is also brittle to eBay DOM changes and arguably against eBay's scraping terms.

---

## 3. eBay API options for sold/completed data — current (June 2026) state

| API | Sold data? | Scope / tier | Status | Notes |
|---|---|---|---|---|
| **Finding API** (`findCompletedItems`) | ~~Yes~~ | App ID (legacy) | **DECOMMISSIONED Feb 5, 2025** | Sold access restricted since Oct 15, 2020. What `slab_premium_analysis.py` uses. Dead. |
| **Shopping API** | Partial | legacy | **Decommissioned 2025** | Same retirement wave. Not an option. |
| **Browse API** (`buy.browse`) | **No** | Buy, standard | Active | **Active listings only.** Good for current ask / lowest BIN, not comps. |
| **Marketplace Insights API** (`buy.marketplace.insights`) | **Yes** | Buy, **Limited Release** | Active, **gated** | The *only* supported sold-comps API. 90-day window. Requires eBay business approval. |

### Marketplace Insights API — the only real path

- **Endpoint:** `GET /buy/marketplace_insights/v1_beta/item_sales/search` (still `_beta`).
- **OAuth scope:** `https://api.ebay.com/oauth/api_scope/buy.marketplace.insights`
  (application access token — client-credentials, not per-user). **We are not granted this.**
- **Recency window:** **rolling last 90 days** of sold items only. (No deep history — same
  90-day horizon a buyer sees in the app's "Sold" filter.)
- **Query shape:** keyword `q` + `category_ids` (comics = `259104`) + `filter` (conditions,
  price, buying options, **`lastSoldDate`** range — a filter unique to this API), sortable,
  paginated (up to ~240 items/page).
- **Per-item fields returned (`ItemSales`):** `itemId`, `title`, `condition` + `conditionId`,
  `categories`/`leafCategoryIds`, `image` (+ `additionalImages`), `itemWebUrl`, `itemHref`,
  `itemGroupType`, `seller` (username, feedback score/%), **`lastSoldPrice`** (value+currency),
  **`lastSoldDate`**, **`totalSoldQuantity`**, `marketplaceId`.
- **Rate limits:** Buy APIs default to roughly **5,000 calls/app/day** for standard tiers;
  Marketplace Insights' exact quota is assigned on approval and is not publicly fixed. Treat
  "~5k/day" as a planning placeholder, not a confirmed number — confirm in the developer
  console once/if granted.
- **Access reality:** Limited Release. Community evidence through 2026 is consistent — eBay
  tells most applicants it's "limited to approved partners, can't grant at this time," and solo
  developers rarely get in. Approval, if pursued, goes through eBay Developer Support /
  business-unit review.

---

## 4. Data-shape comparison: extension vs. Marketplace Insights vs. Browse

| Dimension | Extension (today) | Marketplace Insights | Browse API |
|---|---|---|---|
| Sold price | ✅ per listing | ✅ `lastSoldPrice` | ❌ |
| Sold date | ✅ `sale_date` | ✅ `lastSoldDate` | ❌ |
| History depth | Whatever pages you load (can include old) | **90 days only** | n/a |
| Title / item id | ✅ | ✅ `title` / `itemId` | ✅ |
| Image URL | ✅ | ✅ `image` | ✅ |
| Listing URL | ✅ | ✅ `itemWebUrl` | ✅ |
| Condition | ✅ (string) | ✅ `condition`/`conditionId` | ✅ |
| **Grade (CGC/CBCS 9.8 etc.)** | ✅ parsed from title | ⚠️ **only if in title** — must parse, same as today | ⚠️ same |
| Graded boolean | ✅ derived | ⚠️ derive from title | ⚠️ |
| Volume signal | implicit (row count) | ✅ `totalSoldQuantity` | ❌ |
| Current ask / lowest BIN | ❌ | ❌ | ✅ (active listings) |

**Key takeaways for the collector:**
- Marketplace Insights is a **clean structured replacement** for the extension's sold-comp
  gathering — same essential fields, plus `totalSoldQuantity`, minus the brittleness and the
  human-in-the-loop. An automated server-side job (client-credentials token, cron) would not
  silently stall the way the extension did, and it'd feed the same columns our pipeline already
  has.
- **But two real limitations:** (1) **90-day horizon** — we could no longer capture the deep
  historical comps the extension occasionally grabbed; we'd accumulate history ourselves over
  time by running daily and storing rows. (2) **Grade still isn't a first-class field** — CGC
  grade must be parsed from `title` exactly as today, so our `title_normalizer.py` /
  enrichment stays necessary.
- **Browse API is complementary, not a substitute.** It gives *active* asking prices / lowest
  BIN — which is exactly the "here's what it's listing for now" half of **Sell Now Alerts**.
  The comps (is-it-worth-listing) half still needs Marketplace Insights or our stored history.

---

## 5. Implications for the two downstream features

**Automated collector (replacing the extension):**
- *Ideal path:* Marketplace Insights, daily server-side job per tracked key/category, store
  rows → builds rolling history, no human, no silent stall. Fits our schema directly.
- *Blocker:* requires `buy.marketplace.insights` approval we don't have. **This is a
  go/no-go gate, not an engineering task.**
- *If approval is denied:* options narrow to (a) continue/ harden the scraping extension with
  a scheduled/headless runner + a dead-man's-switch alert (monitor `created_at` recency and
  alert when capture stalls — directly addresses the 67-day silent failure), or (b) a paid
  third-party sold-data provider (e.g. marketplace-data vendors/aggregators), with cost and
  ToS review.

**Sell Now Alerts:**
- The "what's it listing for right now" side is **buildable today-ish** with the **Browse API**
  (`buy.browse` — a standard scope we can request without Limited-Release approval), giving
  current asks / lowest BIN.
- The "is now a good time to sell vs. recent sold comps" side needs **Marketplace Insights**
  (or our own accumulated sold history). So Sell Now Alerts can ship a useful v1 on Browse +
  our existing 47k-row corpus, with the sold-trend layer gated on the same approval.

---

## 6. Recommendation (decision points for Mike — not building)

1. **Apply for Marketplace Insights access now.** It's the only first-party sold-comps path and
   the application is the long pole. Worst case it's denied; best case it unblocks the durable
   collector. Requires reaching eBay Developer Support / business-unit review from our existing
   developer account.
2. **Request `buy.browse` in parallel** (standard tier, no Limited-Release gate). It unblocks
   the Sell Now Alerts "current price" side regardless of the Insights decision, and is generally
   useful.
3. **Don't wait on approval to fix the silent-stall failure mode.** Independent of which data
   path wins, add a capture-freshness monitor (alert when `max(created_at)` on `ebay_sales` /
   `market_sales` ages past N days). That's the cheapest, highest-value reliability fix and
   maps to our existing `dependency_monitor.py` pattern. (Flagging — not implementing here.)
4. **Retire `slab_premium_analysis.py`'s Finding API path** (dead since Feb 2025) so it doesn't
   mislead future work.
5. If Insights is denied, bring back a costed comparison of (a) hardened scheduled scraping vs.
   (b) a paid sold-data vendor, before committing.

---

## Sources

- [eBay Marketplace Insights API access — eBay Community](https://community.ebay.com/t5/eBay-APIs-Talk-to-your-fellow/Marketplace-Insights-API-access/td-p/34838736)
- [Access to sold/completed listing data — options for non-partner developers (eBay Community)](https://community.ebay.com/t5/eBay-APIs-Talk-to-your-fellow/Access-to-sold-completed-listing-data-what-options-do-non/td-p/35398955/jump-to/first-unread-message)
- [Marketplace Insights API overview — eBay Developers](https://developer.ebay.com/api-docs/buy/static/api-insights.html)
- [Marketplace Insights item_sales/search — eBay Developers](https://developer.ebay.com/api-docs/buy/marketplace-insights/resources/item_sales/methods/search)
- [ItemSales type reference — eBay Developers](https://net-ebay.codebase.ebay.com/api-docs/buy/marketplace-insights/types/sal:ItemSales)
- [Alert: Finding API and Shopping API to be decommissioned in 2025 — eBay Community](https://community.ebay.com/t5/Traditional-APIs-Search/Alert-Finding-API-and-Shopping-API-to-be-decommissioned-in-2025/td-p/34222062)
- [API Deprecation Status — eBay Developers](https://developer.ebay.com/develop/get-started/api-deprecation-status)
- [Browse API Overview — eBay Developers](https://developer.ebay.com/api-docs/buy/browse/overview.html)
- [Filter Browse API by lastSoldDate (active-only confirmation) — eBay Community](https://community.ebay.com/t5/RESTful-Buy-APIs-Browse/Filter-Browse-API-by-lastSoldDate/td-p/34291585)

*Findings only. No code changed; no DB writes. eBay doc pages are JS-heavy and several
timed out on fetch — field/limit details cross-checked against eBay community + reference
threads above; confirm exact rate-limit quota in the developer console if/when Insights is granted.*
