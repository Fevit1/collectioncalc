# eBay Comic Collector Chrome Extension

A passive Chrome extension that collects comic book sale data from eBay sold listings as you browse.

## What It Does

- **Automatic collection**: Detects when you're on eBay sold listings pages
- **Parses comic data**: Extracts title, issue number, price, date, grade info
- **Local storage**: Saves data locally even if backend is unavailable
- **Sync to backend**: Sends collected sales to CollectionCalc for FMV calculations
- **Deduplication**: Won't save the same sale twice

## Files Included

| File | Purpose |
|------|---------|
| `manifest.json` | Extension configuration |
| `content.js` | Parses eBay sold listings |
| `popup.html/js` | Stats UI when you click the icon |
| `migrate_ebay_sales.sql` | Database table (run on Render Postgres) |
| `api_endpoints.py` | Backend routes to add to `wsgi.py` |

## Setup Steps

### 1. Database Migration

In DBeaver or psql, run the migration:

```bash
psql $DATABASE_URL -f migrate_ebay_sales.sql
```

### 2. Add API Endpoints

Copy the routes from `api_endpoints.py` into your `wsgi.py`.

Add this import at the top if not already there:
```python
import hashlib
```

### 3. Deploy Backend

```bash
git add .; git commit -m "Add eBay sales endpoints"; git push
```

### 4. Install Extension

1. Go to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top right)
3. Click **Load unpacked**
4. Select this `ebay-collector` folder

### 5. Create Icons (Optional)

The extension needs icon files. Create simple 16x16, 48x48, and 128x128 PNG files named:
- `icon16.png`
- `icon48.png`
- `icon128.png`

Or use any comic-themed icons you like.

## How to Use

1. Go to eBay
2. Search for comics (e.g., "Amazing Spider-Man 300")
3. Click the **Sold Items** filter on the left
4. Extension automatically captures sales data
5. Toast notification shows: "📊 Collected X new sales"

Each page you browse = more data in your database!

## Why This Is Legal

| Web Scraping | This Extension |
|--------------|----------------|
| Bot makes requests | You make requests |
| High server load | Zero additional load |
| Violates ToS | Just reads your browser |
| Gets blocked | Nothing to block |

It's automated note-taking of pages you're already viewing - same as Honey, Keepa, and password managers.

## API Endpoints

The extension expects these endpoints on your backend:

- `POST /api/ebay-sales/batch` - Batch insert sales
- `GET /api/ebay-sales/stats` - Get collection statistics
- `GET /api/ebay-sales/lookup?title=X&issue=Y` - Look up FMV

## Troubleshooting

**Extension not loading?**
- Make sure you selected the folder, not the zip file
- Check for errors in `chrome://extensions/`

**Sales not syncing?**
- Check the popup for pending count
- Click "Sync Now" to manually sync
- Verify backend is running and endpoints are deployed

**No toast notifications?**
- Make sure you're on a **Sold Items** page
- Look for `LH_Sold=1` in the URL
