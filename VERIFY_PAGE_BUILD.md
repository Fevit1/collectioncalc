# Public Verify Page - Build Summary

## What Was Built

### 1. Backend API (`routes/verify.py`)
✅ **Two endpoints created:**

**GET `/api/verify/lookup/:serial_number`**
- Public endpoint (no auth required)
- Validates serial number format (SW-YYYY-NNNNNN)
- Returns comic details with privacy protection:
  - Email hashing: `mike@gmail.com` → `m***e@g***l.com`
  - Shows: title, issue, publisher, year, grade, status
  - Registration date
  - Theft status (active/reported_stolen/recovered)
  - Watermarked cover image URL

**GET `/api/verify/watermark/:serial_number`**
- Returns watermarked cover image (JPEG)
- Adds serial number overlay (top-right corner, 30% opacity)
- Adds "SLABWORTHY.COM" watermark (bottom center)
- Semi-transparent black background for readability

### 2. Frontend Page (`verify.html`)
✅ **Clean, professional public-facing page:**
- Beautiful gradient purple background
- Simple serial number input (auto-formats uppercase)
- Cloudflare Turnstile bot protection
- Displays comic details in card format
- Shows watermarked cover image
- Status badges (✅ Active, ⚠️ Reported Stolen, 🔄 Recovered)
- "What is this?" educational section
- Patent pending notice
- Mobile responsive

### 3. Integration (`wsgi.py` + `routes/utils.py`)
✅ **Registered and configured:**
- Imported `ImageDraw` and `ImageFont` from PIL
- Registered `verify_bp` blueprint
- Initialized with imagehash and PIL modules
- Added `/verify` route to serve the HTML page

---

## How to Access

**URL:** `https://slabworthy.com/verify`

**API Endpoints:**
- `https://collectioncalc-docker.onrender.com/api/verify/lookup/SW-2026-000001`
- `https://collectioncalc-docker.onrender.com/api/verify/watermark/SW-2026-000001`

---

## TODO Before Testing

### 🔴 REQUIRED: Get Cloudflare Turnstile Site Key

**Why:** Bot protection requires a Turnstile site key (free, better than reCAPTCHA)

**Steps:**
1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Select your domain (slabworthy.com)
3. Go to **Turnstile** in the sidebar
4. Click **"Add Site"**
5. Configure:
   - **Site name:** SlabWorthy Verify
   - **Domain:** slabworthy.com
   - **Widget mode:** Managed (Recommended)
6. Copy the **Site Key** (starts with `0x4...`)
7. Replace in `verify.html` line 121:
   ```html
   data-sitekey="YOUR_SITE_KEY_HERE"
   ```
   with:
   ```html
   data-sitekey="0x4AAAAAAA..."  <!-- Your actual key -->
   ```

**Note:** Until you add the site key, the verify button will be disabled. Users won't be able to verify comics.

---

## How to Test

### Test 1: Registration Button (Should Work Now!)
1. Go to slabworthy.com
2. Grade a comic
3. Click "Save to Collection"
4. **🛡️ Theft Protection section should appear!**
5. Click "🔒 Register This Comic"
6. Should see: "Registered as SW-2026-XXXXXX"

### Test 2: Verify Page (After Adding Turnstile Key)
1. Copy the serial number from registration
2. Go to slabworthy.com/verify
3. Paste serial number (e.g., SW-2026-000001)
4. Complete Turnstile challenge (if shown)
5. Click "Verify Comic"
6. Should see:
   - ✅ Active status badge
   - Watermarked cover image (with serial number overlay)
   - Comic details (title, issue, grade, etc.)
   - Hashed email (m***e@g***l.com)
   - Registration date

### Test 3: Watermarked Image API
Visit: `https://collectioncalc-docker.onrender.com/api/verify/watermark/SW-2026-000001`
Should download a JPEG with:
- Serial number in top-right corner
- "SLABWORTHY.COM" at bottom
- Semi-transparent backgrounds for readability

---

## Privacy Features Implemented

✅ **Email hashing:**
- `mike@gmail.com` → `m***e@g***l.com`
- `john.doe@example.com` → `j******e@e*****e.com`

✅ **No PII exposed:**
- No phone numbers
- No addresses
- No full names
- No user IDs

✅ **Public data only:**
- Comic details (title, issue, grade)
- Registration date
- Theft status
- Watermarked image

---

## Image Watermarking Details

**Visible watermarks added:**
1. **Serial number (top-right):**
   - Font size: 4% of image width
   - Color: White with 80% opacity
   - Background: Semi-transparent black (50% opacity)
   - Position: 20px from top-right

2. **Domain watermark (bottom-center):**
   - Text: "SLABWORTHY.COM"
   - Font size: 60% of serial number font
   - Color: White with 60% opacity
   - Background: Semi-transparent black
   - Centered horizontally

**Why watermark?**
- Prevents image theft/reuse
- Proves ownership via serial number
- Makes it harder to resell stolen comics

---

## Files Modified

```
routes/verify.py         NEW - 230 lines (API endpoints)
verify.html              NEW - 450 lines (frontend page)
wsgi.py                  MODIFIED - added verify blueprint
routes/utils.py          MODIFIED - added /verify route
```

---

## Deployment Commands

```powershell
git add routes/verify.py verify.html wsgi.py routes/utils.py
git commit -m "Add public verify page with watermarking and bot protection"
git push origin main
deploy
purge
```

**After deployment:**
1. Add Turnstile site key to verify.html
2. Commit and deploy again
3. Test both features!

---

## Next Steps After Testing

### Phase 1 Enhancements:
- [ ] Add "Report Stolen" button (owner only)
- [ ] Email alerts when comic is verified
- [ ] Analytics: track how many times each comic is verified
- [ ] QR code generation (print on label, links to verify page)

### Phase 2 - eBay Integration:
- [ ] Auto-include serial number in listing descriptions
- [ ] Watermarked image upload to eBay
- [ ] Template text for eBay listings

### Phase 3 - Monitoring:
- [ ] Automated eBay scraping for registered serials
- [ ] Email alerts on matches
- [ ] Dashboard showing monitoring status

---

## How CGC Does It (For Reference)

**CGC Cert Lookup:**
- Simple input: enter cert number
- Shows comic details
- No PII exposed
- Uses standard CAPTCHA (not as nice as Turnstile)
- URL: https://www.cgccomics.com/certlookup/

**Our improvements:**
✅ Better bot protection (Turnstile)
✅ Watermarked images (CGC doesn't do this)
✅ Theft status tracking (CGC doesn't have this)
✅ Prettier UI (subjective, but ours looks good!)

---

**Built:** Feb 13, 2026
**Status:** Ready to test after Turnstile key added
**Patent:** Pending
