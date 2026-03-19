# Slab Guard Monitor - Chrome Extension

**Version:** 1.0.0
**Purpose:** Monitor eBay listings for stolen comics registered with Slab Guard

---

## Installation (Developer Mode)

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked**
4. Select the `slab-guard-monitor` folder
5. The shield icon appears in your toolbar

---

## Features

### Auto-Scan (eBay Search Pages)
When you browse eBay comic search results, the extension automatically:
- Extracts listing images
- Checks each against the Slab Guard registry
- Overlays shield badges on matches:
  - **RED** = REPORTED STOLEN
  - **ORANGE** = High confidence match
  - **GREEN** = Registered (not stolen)
  - **BLUE** = Checked, no match

### Manual Check (eBay Item Pages)
On any eBay listing page:
- Click the floating purple **"Check with Slab Guard"** button
- See a detailed match panel with comic info, serial number, and confidence %
- If stolen: **Report This Match** button alerts the owner

### Role-Based Popup
- **Owner tab**: See your registered comics, match alerts, toggle auto-scan
- **Dealer tab**: Verify serial numbers before buying. Check history.
- **Law Enforcement tab**: Search stolen registry, bulk tools, contact info

### Settings
- Toggle auto-scan on/off
- Adjust scan sensitivity (Low/Medium/High)
- Desktop notifications for stolen matches
- Sound alerts

---

## Backend API Endpoints

The extension communicates with these Slab Guard API endpoints:

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/monitor/check-image` | POST | No | Check image URL against registry |
| `/api/monitor/check-hash` | POST | No | Check pre-computed pHash |
| `/api/monitor/stolen-hashes` | GET | No | Get all stolen fingerprints (for caching) |
| `/api/monitor/report-match` | POST | Yes | Report a match on marketplace |
| `/api/monitor/my-matches` | GET | Yes | Get match reports for your comics |
| `/api/verify/lookup/:serial` | GET | No | Verify a serial number |

---

## File Structure

```
slab-guard-monitor/
├── manifest.json      # MV3 Chrome extension manifest
├── background.js      # Service worker: hash caching, API proxy, badge mgmt
├── content.js         # eBay page injection: auto-scan + manual check
├── content.css        # Animations for overlays and badges
├── popup.html         # Extension popup UI
├── popup.js           # Popup logic: login, tabs, match display
├── popup.css          # Popup styles (Slab Worthy brand)
├── options.html       # Settings page
├── icons/
│   ├── icon16.png     # Toolbar icon
│   ├── icon48.png     # Extensions page
│   └── icon128.png    # Chrome Web Store
└── README.md          # This file
```

---

## Deployment Checklist

Before deploying:
1. [ ] Run `db_migrate_match_reports.py` on production database
2. [ ] Deploy backend with new `routes/monitor.py`
3. [ ] Test check-image endpoint with a real eBay image URL
4. [ ] Load extension in Chrome dev mode
5. [ ] Test on eBay search page (auto-scan)
6. [ ] Test on eBay item page (manual check)
7. [ ] Test serial verification in Dealer tab
8. [ ] Get Cloudflare Turnstile key for verify page (if not done)

---

*Built: February 14, 2026*
*Slab Guard™ by SlabWorthy.com*
