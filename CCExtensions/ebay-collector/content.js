// eBay Comic Collector - Content Script v3
// v3: Added SlabGuard scam detection on individual listing pages
// Existing sold-listings collection is completely unchanged below

(function() {
  'use strict';

  const API_BASE = 'https://collectioncalc-docker.onrender.com';
  const BANNER_ID = 'sw-collector-banner';
  const SG_BANNER_ID = 'sw-slabguard-banner';

  // ─── Route: item pages go to SlabGuard, search pages go to collector ───

  const isItemPage = window.location.href.includes('/itm/');

  if (isItemPage) {
    initSlabGuard();
    return;
  }

  if (!window.location.href.includes('LH_Sold=1') &&
      !window.location.href.includes('LH_Complete=1') &&
      !document.querySelector('.srp-save-null-search__heading')?.textContent?.includes('sold')) {
    return;
  }


  // ════════════════════════════════════════════════════════════
  // SLABGUARD — Item page scam detection

// SlabGuard — Real-time signal scraper for eBay listing pages
// Runs locally in the browser, no backend call needed for scoring

function scrapeListingSignals() {
  const signals = [];
  let score = 0;
  const pageText = document.body.innerText || '';
  const pageHTML = document.body.innerHTML || '';

  // ── 1. Seller feedback score ──
  // eBay shows seller feedback as "(NNN)" near seller name
  // Selectors: .x-sellercard-atf__info__about-seller, .ux-seller-section
  // Target feedback count specifically — avoid grabbing seller username digits
  const feedbackEl =
    document.querySelector('[data-testid="ux-seller-section__item--feedback"] .ux-textspans') ||
    document.querySelector('.ux-seller-section__item--feedback .ux-textspans--BOLD') ||
    document.querySelector('.x-sellercard-atf__info__about-seller [class*="feedback"]');

  let feedbackScore = null;
  if (feedbackEl) {
    const match = feedbackEl.textContent.match(/([\d,]+)/);
    if (match) feedbackScore = parseInt(match[1].replace(',', ''));
  }

  // Also try parsing from page text pattern "(123)" near "feedback"
  if (feedbackScore === null) {
    const fbMatch = pageText.match(/\((\d+)\)\s*feedback/i) ||
                    pageText.match(/feedback score[:\s]+(\d+)/i);
    if (fbMatch) feedbackScore = parseInt(fbMatch[1]);
  }

  if (feedbackScore !== null && feedbackScore < 10) {
    score += 25;
    signals.push(`Seller has zero/low feedback (${feedbackScore} reviews)`);
  } else if (feedbackScore !== null && feedbackScore < 50) {
    score += 10;
    signals.push(`Seller has low feedback (${feedbackScore} reviews)`);
  }

  // ── 2. Seller location / international ──
  // eBay shows "Item location: City, Country"
  const locationEl =
    document.querySelector('.ux-labels-values--itemLocation .ux-textspans') ||
    document.querySelector('[data-testid="x-item-location"] .ux-textspans') ||
    document.querySelector('[data-testid="itemLocation"] .ux-textspans') ||
    document.querySelector('.ux-textspans[itemprop="availableAtOrFrom"]') ||
    document.querySelector('.vi-acc-del-area .ux-textspans') ||
    document.querySelector('[class*="itemLocation"] .ux-textspans');

  let locationText = locationEl?.textContent?.trim() || '';

  // Broaden text scan — try multiple patterns
  if (!locationText) {
    const locMatch =
      pageText.match(/Item\s+location\s*:?\s*([^\n<]{3,50})/i) ||
      pageText.match(/Located\s+in\s*:?\s*([^\n<]{3,50})/i) ||
      pageText.match(/Ships\s+from\s*:?\s*([^\n<]{3,50})/i);
    if (locMatch) locationText = locMatch[1].trim();
  }

  const domesticKeywords = ['United States', 'US', 'USA'];
  const isInternational = locationText &&
    !domesticKeywords.some(k => locationText.includes(k)) &&
    locationText.length > 2;

  if (isInternational) {
    score += 20;
    signals.push(`Seller is international (${locationText.substring(0, 30)})`);
  }

  // ── 3. Photo count ──
  // eBay image gallery: .ux-image-carousel-item, or count of thumbnails
  const photoThumbnails =
    document.querySelectorAll('.ux-image-carousel-item').length ||
    document.querySelectorAll('.ux-image-magnify__image--original').length ||
    document.querySelectorAll('[data-idx]').length;

  // Also check for "X of Y" image counter text
  const imgCountMatch = pageText.match(/(\d+)\s+of\s+(\d+)\s+image/i);
  const totalPhotos = imgCountMatch ? parseInt(imgCountMatch[2]) : photoThumbnails;

  if (totalPhotos === 1) {
    score += 15;
    signals.push('Listing has only a single photo');
  } else if (totalPhotos === 0) {
    score += 10;
    signals.push('No photos detected in listing');
  }

  // ── 4. No returns policy ──
  const returnsEl =
    document.querySelector('.ux-labels-values--returns .ux-textspans') ||
    document.querySelector('[data-testid="x-returns-minview"] .ux-textspans');

  const returnsText = returnsEl?.textContent?.toLowerCase() || '';
  const noReturnsInPage = pageText.toLowerCase().includes('no returns') ||
                          pageText.toLowerCase().includes('all sales final');

  if (returnsText.includes('no returns') || noReturnsInPage) {
    score += 10;
    signals.push('Seller does not accept returns');
  }

  // ── 5. New seller (member since) ──
  // eBay shows "Member since: Jan-01-24" or similar
  const memberMatch = pageText.match(/Member\s+since[:\s]+(\w+-\d+-\d+)/i) ||
                      pageText.match(/Joined\s+(\w+\s+\d{4})/i);

  if (memberMatch) {
    const memberText = memberMatch[1];
    // Try to parse year
    const yearMatch = memberText.match(/(\d{2,4})$/);
    if (yearMatch) {
      let year = parseInt(yearMatch[1]);
      if (year < 100) year += 2000; // "24" -> 2024
      const currentYear = new Date().getFullYear();
      if (currentYear - year <= 1) {
        score += 10;
        signals.push(`Seller account is new (joined ${memberText})`);
      }
    }
  }

  // ── 6. Price vs CGC grading context ──
  // If title mentions CGC + high grade but price is very low
  const titleEl = document.querySelector('h1.x-item-title__mainTitle span') ||
                  document.querySelector('.x-item-title__mainTitle') ||
                  document.querySelector('h1[itemprop="name"]');
  const title = titleEl?.textContent?.trim() || document.title || '';

  const priceEl = document.querySelector('.x-price-primary .ux-textspans--BOLD') ||
                  document.querySelector('[data-testid="x-price-primary"] .ux-textspans');
  const priceText = priceEl?.textContent?.replace(/[^0-9.]/g, '') || '';
  const price = parseFloat(priceText) || 0;

  const cgcMatch = title.match(/CGC\s+([\d.]+)/i);
  const gradeStr = cgcMatch ? cgcMatch[1] : null;
  const grade = gradeStr ? parseFloat(gradeStr) : null;

  // High grade comic (8.0+) priced under $100 is suspicious
  if (grade && grade >= 8.0 && price > 0 && price < 100) {
    score += 20;
    signals.push(`Suspiciously low price for a CGC ${grade} ($${price})`);
  }

  // ── 7. Keyword stuffing / AI description ──
  // Look at description iframe text length vs line breaks
  // We can check the visible description area
  const descEl = document.querySelector('#desc_div') ||
                 document.querySelector('.ux-layout-section--description');

  if (descEl) {
    const descText = descEl.innerText || '';
    const wordCount = descText.split(/\s+/).length;
    const lineBreaks = (descText.match(/\n/g) || []).length;
    // AI descriptions tend to be long walls of text with few natural breaks
    if (wordCount > 300 && lineBreaks < 5) {
      score += 10;
      signals.push('Description appears AI-generated or keyword-stuffed');
    }
  }

  // ── 8. Payment method warnings ──
  // If listing mentions wire transfer, Zelle, Venmo, crypto
  const suspiciousPayments = ['wire transfer', 'western union', 'zelle', 'venmo', 'cashapp', 'crypto', 'bitcoin'];
  for (const method of suspiciousPayments) {
    if (pageText.toLowerCase().includes(method)) {
      score += 25;
      signals.push(`Suspicious payment method requested: ${method}`);
      break;
    }
  }

  // ── 9. Amazing Fantasy 15 / key issue sanity check ──
  // These are almost always fakes at low prices
  const keyIssues = [
    { pattern: /amazing fantasy\s*#?\s*15/i, minLegitPrice: 500 },
    { pattern: /amazing spider.?man\s*#?\s*1\b/i, minLegitPrice: 300 },
    { pattern: /incredible hulk\s*#?\s*1\b/i, minLegitPrice: 500 },
    { pattern: /x.?men\s*#?\s*1\b/i, minLegitPrice: 200 },
    { pattern: /fantastic four\s*#?\s*1\b/i, minLegitPrice: 500 },
    { pattern: /action comics\s*#?\s*1\b/i, minLegitPrice: 5000 },
    { pattern: /detective comics\s*#?\s*27\b/i, minLegitPrice: 5000 },
  ];

  for (const keyIssue of keyIssues) {
    if (keyIssue.pattern.test(title) && price > 0 && price < keyIssue.minLegitPrice) {
      score += 30;
      signals.push(`Key issue priced suspiciously low ($${price})`);
      break;
    }
  }

  return { score, signals, meta: { feedbackScore, locationText, totalPhotos, price, title } };
}



  // ════════════════════════════════════════════════════════════

  // Extract the main listing image URL from eBay's DOM
  function getMainImageUrl() {
    // eBay renders the main image in several possible elements
    const selectors = [
      '.ux-image-magnify__image--original',
      '.ux-image-carousel-item.active img',
      '#icImg',
      '.vi-image-gallery__image--enlarged',
      'img[data-zoom-src]',
      '.ux-image-magnify img',
    ];
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el) {
        // Prefer data-zoom-src (full res) over src (thumbnail)
        const url = el.getAttribute('data-zoom-src') || el.src || '';
        if (url && url.startsWith('http') && !url.includes('gif')) return url;
      }
    }
    // Fallback: try eBay's predictable CDN pattern using item ID
    const itemMatch = window.location.href.match(/\/itm\/(\d+)/);
    if (itemMatch) return `https://i.ebayimg.com/images/g/${itemMatch[1]}/s-l1600.jpg`;
    return null;
  }

  // Extract seller ID from eBay listing page
  function getSellerId() {
    // eBay seller username appears in several places
    const selectors = [
      '.x-sellercard-atf__info__about-seller a',
      '[data-testid="ux-seller-section__item--seller"] a',
      '.ux-seller-section__item--seller a',
      '#seller-profile a',
    ];
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el) {
        const text = el.textContent.trim();
        if (text && text.length > 0) return text;
      }
    }
    // Fallback: look for seller name in page text
    const match = document.body.innerText.match(/Sold by[:\s]+([\w-]+)/i);
    if (match) return match[1];
    return null;
  }

  async function initSlabGuard() {
    const itemIdMatch = window.location.href.match(/\/itm\/(\d+)/);
    if (!itemIdMatch) return;
    const ebayItemId = itemIdMatch[1];

    const stored = await chrome.storage.local.get(['sw_token']);
    const token = stored.sw_token;

    injectSlabGuardStyles();

    // Step 1: Let eBay render, then run local signal analysis
    await new Promise(r => setTimeout(r, 1800));
    const local = scrapeListingSignals();
    console.log('[SlabGuard DEBUG] Local signals:', local.signals);
    console.log('[SlabGuard DEBUG] Meta:', JSON.stringify(local.meta));
    console.log('[SlabGuard DEBUG] Image URL:', getMainImageUrl());
    console.log('[SlabGuard DEBUG] Seller ID:', getSellerId());

    // Step 2: Call backend to check approved flagged DB (only if logged in)
    let dbFlagged = false;
    let dbMatchType = null;
    let data = {};
    if (token) {
      showSlabGuardBanner({ state: 'checking' });
      try {
        // 5-second hard timeout so banner never hangs indefinitely
        const checkController = new AbortController();
        const checkTimeout = setTimeout(() => checkController.abort(), 5000);
        const res = await fetch(`${API_BASE}/api/slabguard/check`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          signal: checkController.signal,
          body: JSON.stringify({
            ebay_item_id: ebayItemId,
            ebay_url: window.location.href,
            image_url: getMainImageUrl(),
            seller_id: getSellerId()
          })
        });
        clearTimeout(checkTimeout);
        if (res.ok) {
          data = await res.json();
          console.log('[SlabGuard DEBUG] DB response:', JSON.stringify(data));
          dbFlagged = data.matched || false;
          dbMatchType = data.match_type || "item_id";
        }
      } catch (e) {
        if (e.name === 'AbortError') {
          console.warn('[SlabGuard] DB check timed out after 5s — showing local signals only');
        } else {
          console.warn('[SlabGuard] DB check failed:', e.message);
        }
      }
    }

    // Step 3: Merge results
    const finalScore = dbFlagged ? Math.min(99, local.score + (data.risk_boost || 40)) : local.score;
    const finalSignals = [...local.signals];
    if (dbFlagged) {
      const signalLabels = {
        'phash':     'Image matches a previous scam listing',
        'seller_id': 'Seller has been reported as a scammer',
        'item_id':   'This listing ID has been reported as a scam'
      };
      // Show a pill for every match type returned
      const dbMatchTypes = Array.isArray(data.match_types) ? data.match_types
                         : (data.match_type ? [data.match_type] : ['item_id']);
      dbMatchTypes.reverse().forEach(mt => {
        finalSignals.unshift(signalLabels[mt] || 'Known scam pattern');
      });
    }

    if (finalScore === 0 && !dbFlagged) {
      showSlabGuardBanner({ state: 'safe', ebayItemId, token });
      setTimeout(removeSGBanner, 4000);
    } else {
      showSlabGuardBanner({
        state: 'danger',
        riskScore: Math.min(finalScore, 99),
        signals: finalSignals,
        ebayItemId,
        token
      });
    }
  }

  function removeSGBanner() {
    const b = document.getElementById(SG_BANNER_ID);
    if (b) b.remove();
    document.body.style.marginTop = '';
  }

  function showSlabGuardBanner({ state, riskScore, signals, ebayItemId, token }) {
    removeSGBanner();
    const banner = document.createElement('div');
    banner.id = SG_BANNER_ID;

    if (state === 'checking') {
      banner.innerHTML = `
        <div class="sg-inner sg-checking">
          <span class="sg-logo">🛡️ SlabGuard</span>
          <span class="sg-msg">Checking listing safety...</span>
        </div>`;
      document.body.prepend(banner);
      document.body.style.marginTop = '40px';
      return;
    }

    if (state === 'safe') {
      banner.innerHTML = `
        <div class="sg-inner sg-safe">
          <span class="sg-logo">🛡️ SlabGuard</span>
          <span class="sg-msg">✅ No known scam signals detected</span>
          <button class="sg-flag-btn" id="sg-flag-btn">Flag This Listing</button>
          <button class="sg-dismiss" id="sg-dismiss">✕</button>
        </div>`;
      document.body.prepend(banner);
      document.body.style.marginTop = '40px';
      document.getElementById('sg-dismiss').addEventListener('click', removeSGBanner);
      document.getElementById('sg-flag-btn').addEventListener('click', () => openFlagModal(ebayItemId, token));
      return;
    }

    if (state === 'danger') {
      const level = riskScore >= 60 ? 'HIGH' : 'MEDIUM';
      const signalPills = (signals || []).map(s => `<span class="sg-pill">${s}</span>`).join('');
      banner.innerHTML = `
        <div class="sg-inner sg-danger">
          <div class="sg-danger-left">
            <span class="sg-shield-pulse">🛡️</span>
            <div class="sg-danger-text">
              <strong>${level} RISK</strong> — This listing matches known scam patterns
              <div class="sg-pills">${signalPills}</div>
            </div>
          </div>
          <div class="sg-danger-right">
            <span class="sg-score">${riskScore}</span>
            <span class="sg-score-label">Risk Score</span>
          </div>
          <button class="sg-report-btn" id="sg-report-btn">⚑ Report to SW</button>
          <button class="sg-dismiss" id="sg-dismiss">✕</button>
        </div>`;
      document.body.prepend(banner);
      document.body.style.marginTop = '64px';
      document.getElementById('sg-dismiss').addEventListener('click', removeSGBanner);
      document.getElementById('sg-report-btn').addEventListener('click', () => openFlagModal(ebayItemId, token, riskScore, signals));
    }
  }

  function openFlagModal(ebayItemId, token, riskScore, signals) {
    document.getElementById('sg-modal')?.remove();
    const modal = document.createElement('div');
    modal.id = 'sg-modal';
    modal.innerHTML = `
      <div class="sg-modal-overlay" id="sg-modal-overlay">
        <div class="sg-modal-box">
          <h3>🛡️ Flag This Listing</h3>
          <p>Submitting eBay item <strong>#${ebayItemId}</strong> for SlabGuard review.</p>
          <p class="sg-modal-sub">Our team will review this and update the scam database within 24 hours.</p>
          <div class="sg-modal-actions">
            <button class="sg-modal-cancel" id="sg-modal-cancel">Cancel</button>
            <button class="sg-modal-submit" id="sg-modal-submit">Submit Report</button>
          </div>
          <div id="sg-modal-status"></div>
        </div>
      </div>`;
    document.body.appendChild(modal);

    document.getElementById('sg-modal-cancel').addEventListener('click', () => modal.remove());
    document.getElementById('sg-modal-overlay').addEventListener('click', (e) => {
      if (e.target.id === 'sg-modal-overlay') modal.remove();
    });
    document.getElementById('sg-modal-submit').addEventListener('click', async () => {
      const btn = document.getElementById('sg-modal-submit');
      const statusEl = document.getElementById('sg-modal-status');
      btn.disabled = true;
      btn.textContent = 'Submitting...';
      try {
        const res = await fetch(`${API_BASE}/api/slabguard/submit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({
            ebay_item_id: ebayItemId,
            ebay_url: window.location.href,
            risk_score: riskScore || 50,
            signals: signals || {}
          })
        });
        const data = await res.json();
        if (data.success) {
          statusEl.innerHTML = '<span style="color:#4ecdc4">✅ Submitted! Thank you for helping the community.</span>';
          setTimeout(() => modal.remove(), 2000);
        } else {
          statusEl.innerHTML = `<span style="color:#e74c3c">⚠️ ${data.error || 'Submission failed'}</span>`;
          btn.disabled = false;
          btn.textContent = 'Submit Report';
        }
      } catch (e) {
        statusEl.innerHTML = '<span style="color:#e74c3c">⚠️ Network error — please try again</span>';
        btn.disabled = false;
        btn.textContent = 'Submit Report';
      }
    });
  }

  function injectSlabGuardStyles() {
    const style = document.createElement('style');
    style.textContent = `
      #${SG_BANNER_ID} { position:fixed; top:0; left:0; right:0; z-index:999999; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; animation:sgSlideDown 0.3s ease; }
      @keyframes sgSlideDown { from{transform:translateY(-100%);opacity:0} to{transform:translateY(0);opacity:1} }
      @keyframes sgPulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.15)} }
      .sg-inner { display:flex; align-items:center; gap:12px; padding:10px 20px; font-size:13px; color:white; }
      .sg-checking { background:#374151; opacity:0.85; }
      .sg-safe { background:linear-gradient(135deg,#065f46,#047857); box-shadow:0 2px 12px rgba(4,120,87,0.4); }
      .sg-danger { background:linear-gradient(135deg,#7f1d1d,#b91c1c); box-shadow:0 2px 16px rgba(185,28,28,0.5); padding:12px 20px; flex-wrap:wrap; gap:10px; }
      .sg-logo { font-weight:700; background:rgba(255,255,255,0.15); padding:3px 8px; border-radius:4px; white-space:nowrap; }
      .sg-msg { flex:1; font-weight:500; }
      .sg-danger-left { display:flex; align-items:flex-start; gap:10px; flex:1; }
      .sg-danger-text { display:flex; flex-direction:column; gap:6px; }
      .sg-shield-pulse { font-size:22px; animation:sgPulse 1.2s ease infinite; }
      .sg-pills { display:flex; flex-wrap:wrap; gap:6px; margin-top:4px; }
      .sg-pill { background:rgba(255,255,255,0.2); border:1px solid rgba(255,255,255,0.3); padding:2px 8px; border-radius:12px; font-size:11px; }
      .sg-danger-right { display:flex; flex-direction:column; align-items:center; background:rgba(0,0,0,0.25); border-radius:8px; padding:6px 12px; min-width:60px; }
      .sg-score { font-size:22px; font-weight:800; }
      .sg-score-label { font-size:10px; opacity:0.8; }
      .sg-flag-btn,.sg-report-btn { background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.4); color:white; padding:6px 14px; border-radius:5px; cursor:pointer; font-size:12px; font-weight:600; white-space:nowrap; }
      .sg-report-btn { background:rgba(255,255,255,0.2); border-color:rgba(255,255,255,0.5); }
      .sg-flag-btn:hover,.sg-report-btn:hover { background:rgba(255,255,255,0.3); }
      .sg-dismiss { background:none; border:1px solid rgba(255,255,255,0.3); color:white; padding:4px 8px; border-radius:4px; cursor:pointer; font-size:12px; }
      .sg-dismiss:hover { background:rgba(255,255,255,0.1); }
      .sg-modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:9999999; display:flex; align-items:center; justify-content:center; }
      .sg-modal-box { background:#1a1a2e; border:1px solid rgba(255,255,255,0.1); border-radius:12px; padding:28px; max-width:420px; width:90%; color:white; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }
      .sg-modal-box h3 { margin-bottom:12px; font-size:16px; }
      .sg-modal-box p { font-size:13px; color:#ccc; margin-bottom:8px; }
      .sg-modal-sub { font-size:12px; color:#888; }
      .sg-modal-actions { display:flex; gap:10px; margin-top:20px; }
      .sg-modal-cancel { flex:1; padding:10px; background:rgba(255,255,255,0.1); border:none; border-radius:6px; color:white; cursor:pointer; font-size:13px; }
      .sg-modal-submit { flex:1; padding:10px; background:#b91c1c; border:none; border-radius:6px; color:white; cursor:pointer; font-size:13px; font-weight:600; }
      .sg-modal-submit:disabled { opacity:0.6; cursor:not-allowed; }
      .sg-modal-submit:hover:not(:disabled) { background:#991b1b; }
      #sg-modal-status { margin-top:12px; font-size:12px; text-align:center; }
    `;
    document.head.appendChild(style);
  }


  // ════════════════════════════════════════════════════════════
  // SOLD LISTINGS COLLECTOR — unchanged from v2
  // ════════════════════════════════════════════════════════════

  // ─── Animation styles ───
  const style = document.createElement('style');
  style.textContent = `
    @keyframes swSlideDown {
      from { transform: translateY(-100%); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }
    @keyframes swPulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.7; }
    }
    #${BANNER_ID} {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 999999;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      animation: swSlideDown 0.3s ease;
    }
    #${BANNER_ID} .sw-banner-inner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 20px;
      background: linear-gradient(135deg, #6B21A8 0%, #7C3AED 100%);
      color: white;
      font-size: 14px;
      box-shadow: 0 2px 12px rgba(107, 33, 168, 0.4);
    }
    #${BANNER_ID} .sw-banner-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    #${BANNER_ID} .sw-banner-logo {
      font-weight: 700;
      font-size: 13px;
      background: rgba(255,255,255,0.15);
      padding: 3px 8px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }
    #${BANNER_ID} .sw-banner-status {
      font-weight: 500;
    }
    #${BANNER_ID} .sw-banner-stats {
      display: flex;
      gap: 16px;
      font-size: 13px;
      opacity: 0.9;
    }
    #${BANNER_ID} .sw-stat {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    #${BANNER_ID} .sw-stat-num {
      font-weight: 700;
      font-size: 15px;
    }
    #${BANNER_ID} .sw-collecting {
      animation: swPulse 1.5s ease infinite;
    }
    #${BANNER_ID} .sw-banner-dismiss {
      background: none;
      border: 1px solid rgba(255,255,255,0.3);
      color: white;
      padding: 4px 10px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
    }
    #${BANNER_ID} .sw-banner-dismiss:hover {
      background: rgba(255,255,255,0.1);
    }
    #${BANNER_ID} .sw-page-info {
      background: rgba(245, 158, 11, 0.25);
      border: 1px solid rgba(245, 158, 11, 0.5);
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 500;
    }
  `;
  document.head.appendChild(style);


  // ─── Banner UI ───

  function createBanner() {
    let banner = document.getElementById(BANNER_ID);
    if (banner) return banner;

    banner = document.createElement('div');
    banner.id = BANNER_ID;
    banner.innerHTML = `
      <div class="sw-banner-inner">
        <div class="sw-banner-left">
          <span class="sw-banner-logo">SW</span>
          <span class="sw-banner-status sw-collecting">⏳ Collecting...</span>
        </div>
        <div class="sw-banner-stats"></div>
        <button class="sw-banner-dismiss" title="Minimize banner">✕</button>
      </div>
    `;
    document.body.prepend(banner);
    document.body.style.marginTop = '44px';

    banner.querySelector('.sw-banner-dismiss').addEventListener('click', () => {
      banner.querySelector('.sw-banner-inner').style.padding = '4px 12px';
      banner.querySelector('.sw-banner-stats').style.display = 'none';
      banner.querySelector('.sw-banner-dismiss').style.display = 'none';
      document.body.style.marginTop = '28px';
    });

    return banner;
  }

  function updateBanner(opts) {
    const banner = document.getElementById(BANNER_ID);
    if (!banner) return;

    const statusEl = banner.querySelector('.sw-banner-status');
    const statsEl = banner.querySelector('.sw-banner-stats');

    if (opts.status) {
      statusEl.textContent = opts.status;
      statusEl.classList.remove('sw-collecting');
    }
    if (opts.collecting) {
      statusEl.classList.add('sw-collecting');
    }
    if (opts.stats) {
      const { newCount, dupeCount, totalOnPage, pageInfo, run } = opts.stats;
      let statsHtml = '';
      if (newCount !== undefined) statsHtml += `<span class="sw-stat"><span class="sw-stat-num">${newCount}</span> new</span>`;
      if (dupeCount !== undefined && dupeCount > 0) statsHtml += `<span class="sw-stat"><span class="sw-stat-num">${dupeCount}</span> dupes</span>`;
      if (totalOnPage !== undefined) statsHtml += `<span class="sw-stat"><span class="sw-stat-num">${totalOnPage}</span> on page</span>`;
      // Run-scoped saved count. Shows the run's START TIME rather than the reset
      // rule, so the idle-gap boundary is self-evident (see noteSaved).
      if (run) {
        const since = new Date(run.startedAt)
          .toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
        statsHtml += `<span class="sw-stat">|</span><span class="sw-stat">`
                  + `<span class="sw-stat-num">${run.saved.toLocaleString()}</span>`
                  + ` saved this run &middot; since ${since}</span>`;
      }
      if (pageInfo) statsHtml += `<span class="sw-page-info">${pageInfo}</span>`;
      statsEl.innerHTML = statsHtml;
    }
    // Buffer-risk warning. Appended AFTER the stats assignment so a stats
    // update in the same call cannot clobber it.
    if (opts.warning) {
      const w = document.createElement('span');
      w.className = 'sw-stat sw-buffer-warn';
      w.style.cssText = 'margin-left:10px;padding:2px 8px;border-radius:4px;font-weight:700;' +
        (opts.warning.severe ? 'background:#7f1d1d;color:#fecaca;'
                             : 'background:#78350f;color:#fde68a;');
      w.textContent = opts.warning.text;
      statsEl.appendChild(w);
    }
  }


  // ─── Pagination detection ───

  function getPageInfo() {
    // Display-only (feeds the banner) — MUST stay read-only: no pagination
    // behavior ever gets added here (capture is human-paced by standing rule).
    // Loosened [class*=...] fallbacks added alongside the pre-2026-07
    // selectors; unverified against the new markup, degrade to 1/1/null.
    const paginationText = (document.querySelector('.srp-controls__count-heading') ||
                            document.querySelector('[class*="count-heading"]'))?.textContent || '';
    const resultsMatch = paginationText.match(/([\d,]+)\+?\s*results/i);
    const totalResults = resultsMatch ? parseInt(resultsMatch[1].replace(',', '')) : null;

    const pageButtons = document.querySelectorAll('nav.pagination a, .pagination__items a, nav[class*="pagination"] a');
    const currentPage = document.querySelector(
      'nav.pagination .pagination__item--current, .pagination__items .pagination__item--current, ' +
      '[class*="pagination"] [aria-current="page"]');

    let currentPageNum = 1;
    let totalPages = 1;

    if (currentPage) currentPageNum = parseInt(currentPage.textContent) || 1;

    pageButtons.forEach(btn => {
      const num = parseInt(btn.textContent);
      if (!isNaN(num) && num > totalPages) totalPages = num;
    });

    const urlPageMatch = window.location.href.match(/[&?]_pgn=(\d+)/);
    if (urlPageMatch) currentPageNum = parseInt(urlPageMatch[1]);

    return { currentPageNum, totalPages, totalResults };
  }


  // ─── Parse a single listing item ───

  function parseListingItem(item) {
    try {
      // eBay markup restructure (~2026-07, diagnosed 2026-07-12): the s-card
      // family is gone. Item container is div.su-item-card carrying
      // data-listingid; title link is a[class*="item-card__title"] with the
      // text in a nested span. Old selectors kept as fallbacks in case of
      // A/B remnants. Title priority REVERSED vs the s-card era: link text is
      // now primary (new markup's img alt content is unverified — never let
      // junk alt text feed raw_title -> parseComicTitle -> the corpus).
      const linkEl = item.querySelector('a[class*="item-card__title"]') ||
                     item.querySelector('a.s-card__link');
      const imageEl = item.querySelector('img.s-card__image') ||
                      item.querySelector('img');

      const title = linkEl?.textContent?.trim() || imageEl?.alt || '';
      const allText = item.innerText || '';

      const priceMatch = allText.match(/\$([0-9,]+\.?\d*)/);
      const price = priceMatch ? parseFloat(priceMatch[1].replace(',', '')) : 0;

      let saleDate = new Date().toISOString().split('T')[0];
      const dateMatch = allText.match(/Sold\s+(\w{3})\s+(\d{1,2}),?\s*(\d{4})?/i);
      if (dateMatch) {
        const months = { Jan:0, Feb:1, Mar:2, Apr:3, May:4, Jun:5, Jul:6, Aug:7, Sep:8, Oct:9, Nov:10, Dec:11 };
        // Normalize casing before the lookup: the ~2026-07 markup uppercases
        // the sold badge via CSS text-transform, and innerText is
        // RENDERING-AWARE — "SOLD JUL 12" reached this lookup as 'JUL',
        // missed, and silently stamped TODAY's date on the sale (corpus
        // freshness poison). Regex was already /i; the lookup wasn't.
        const monthKey = dateMatch[1].charAt(0).toUpperCase() + dateMatch[1].slice(1).toLowerCase();
        const month = months[monthKey];
        const day = parseInt(dateMatch[2]);
        const year = dateMatch[3] ? parseInt(dateMatch[3]) : new Date().getFullYear();
        if (month !== undefined) saleDate = new Date(year, month, day).toISOString().split('T')[0];
      }

      if (!title || price <= 0) return null;
      // Case-INSENSITIVE sold guard: the uppercase-via-CSS badge made the old
      // .includes('Sold') reject 267 of 279 legitimate items (the real
      // "12 captured" root cause, 2026-07-16 diagnostic — NOT hydration timing).
      if (!/sold/i.test(allText) || allText.startsWith('Shop on eBay')) return null;

      const listingUrl = linkEl?.href || '';
      const imageUrl = imageEl?.src || '';
      // Item id: the container's data-listingid attribute is authoritative
      // (survives cosmetic class renames); the href regex stays as fallback.
      // Accept the attribute ONLY if it is a plain numeric item id: the DB
      // dedup key is ON CONFLICT (ebay_item_id), so a non-numeric token here
      // would silently stop re-captures from matching existing corpus rows.
      const itemIdMatch = listingUrl.match(/\/itm\/(\d+)/);
      const dsId = item.dataset?.listingid || '';
      const ebayItemId = /^\d{9,15}$/.test(dsId) ? dsId : (itemIdMatch ? itemIdMatch[1] : '');
      const parsed = parseComicTitle(title);

      return {
        raw_title: title,
        parsed_title: parsed.title,
        issue_number: parsed.issue,
        publisher: parsed.publisher,
        sale_price: price,
        sale_date: saleDate,
        condition: parsed.condition,
        graded: parsed.graded,
        grade: parsed.grade,
        listing_url: listingUrl,
        image_url: imageUrl,
        ebay_item_id: ebayItemId
      };
    } catch (e) {
      console.error('eBay Collector: Error parsing item:', e);
      return null;
    }
  }


  // ─── Parse comic title ───

  function parseComicTitle(title) {
    const result = { title: '', issue: '', publisher: '', condition: '', graded: false, grade: null };

    const cgcMatch = title.match(/CGC\s+([\d.]+)/i);
    const cbcsMatch = title.match(/CBCS\s+([\d.]+)/i);
    if (cgcMatch) { result.graded = true; result.grade = parseFloat(cgcMatch[1]); result.condition = `CGC ${cgcMatch[1]}`; }
    else if (cbcsMatch) { result.graded = true; result.grade = parseFloat(cbcsMatch[1]); result.condition = `CBCS ${cbcsMatch[1]}`; }

    const issueMatch = title.match(/#\s*(\d+)/);
    if (issueMatch) result.issue = issueMatch[1];

    const publishers = ['Marvel', 'DC', 'Image', 'Dark Horse', 'IDW', 'Valiant', 'Boom', 'Dynamite'];
    for (const pub of publishers) {
      if (title.toLowerCase().includes(pub.toLowerCase())) { result.publisher = pub; break; }
    }

    let cleanTitle = title
      .replace(/CGC\s+[\d.]+/gi, '')
      .replace(/CBCS\s+[\d.]+/gi, '')
      .replace(/\b(VF|NM|FN|VG|GD|FR|PR)[\+\-]?\s*([\d.]+)?\b/gi, '')
      .replace(/#\s*\d+/, '')
      .replace(/\s+/g, ' ')
      .trim();

    result.title = cleanTitle;
    return result;
  }


  // ─── Collect all sales from page ───

  function collectSales() {
    // Container = anything carrying data-listingid (the ~2026-07 markup puts
    // it directly on div.su-item-card). A data attribute outlives BEM class
    // renames — the previous li.s-card selector died silently in an eBay
    // restructure ("0 sales" on every page, capture pipeline down 7/12-7/16).
    // Old selector kept as fallback. parseListingItem() returning null is the
    // junk filter: a stray data-listingid carrier with no title/price is skipped.
    let items = document.querySelectorAll('[data-listingid]');
    if (items.length === 0) items = document.querySelectorAll('li.s-card');
    const sales = [];
    items.forEach(item => {
      const parsed = parseListingItem(item);
      if (parsed && parsed.sale_price > 0) sales.push(parsed);
    });
    return sales;
  }


  // ─── Send sales to backend ───

  // Client-side cap so a hung request is distinguishable from an absent server.
  // Generous on purpose: after the 2026-08-02 backend fix a batch should answer
  // in well under 3s, so hitting this at all means something is wrong.
  const SYNC_TIMEOUT_MS = 120000;

  // Returns { ok:true, ...serverJson } or
  //         { ok:false, kind, detail, status?, error }   ← `error` kept for
  // backwards compatibility with any older truthiness check.
  //
  // ⚠️ kind is the ACTUAL failure mode, never a guess. The previous version
  // collapsed every failure into "backend offline" — which on 2026-08-02
  // reported an outage while all 293 batch requests were returning HTTP 200
  // (the server was just slow; the rows DID save). Asserting an unverified
  // cause is the L-SW-2026-007 failure shape, so each branch below reports
  // only what it actually observed.
  async function sendSales(sales) {
    if (sales.length === 0) return { ok: true, saved: 0, duplicates: 0 };

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), SYNC_TIMEOUT_MS);
    try {
      const response = await fetch(`${API_BASE}/api/ebay-sales/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sales }),
        signal: controller.signal
      });

      if (!response.ok) {
        // The server answered and rejected/failed — it is demonstrably reachable.
        console.error(`eBay Collector: server returned HTTP ${response.status}`);
        return { ok: false, kind: 'http', status: response.status,
                 detail: `HTTP ${response.status}`, error: `HTTP ${response.status}` };
      }

      try {
        const json = await response.json();
        return { ok: true, ...json };
      } catch (e) {
        // 2xx with an unreadable body — the write may well have happened.
        console.error('eBay Collector: could not parse server response:', e);
        return { ok: false, kind: 'parse', detail: 'unreadable response body',
                 error: 'unreadable response body' };
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        const secs = Math.round(SYNC_TIMEOUT_MS / 1000);
        console.error(`eBay Collector: no response within ${secs}s`);
        return { ok: false, kind: 'timeout', detail: `no reply in ${secs}s`,
                 error: `timeout after ${secs}s` };
      }
      // TypeError: Failed to fetch — DNS, connection refused, offline, CORS.
      console.error('eBay Collector: network error:', e);
      return { ok: false, kind: 'network', detail: e.message || 'fetch failed',
               error: e.message || 'fetch failed' };
    } finally {
      clearTimeout(timer);
    }
  }


  // Banner text for a failed sync. Each string commits only to what was
  // observed — critically, a timeout says the data MAY have saved, because a
  // slow-but-successful request is exactly what happened on 2026-08-02 and
  // re-sending is the wrong reflex there.
  function syncFailureLabel(result, count) {
    switch (result.kind) {
      case 'timeout':
        return `⏳ ${count} buffered — server did not reply (${result.detail}). ` +
               `It MAY have saved them; check before re-sending.`;
      case 'network':
        return `📡 ${count} buffered — backend unreachable (${result.detail}).`;
      case 'http':
        return result.status >= 500
          ? `⚠️ ${count} buffered — server error ${result.status} (server is up).`
          : `⚠️ ${count} buffered — server rejected the batch (${result.status}).`;
      case 'parse':
        return `⚠️ ${count} buffered — server replied but the response was unreadable; ` +
               `the save may have succeeded.`;
      default:
        return `⚠️ ${count} buffered — sync failed (${result.detail || 'unknown'}).`;
    }
  }


  // ─── Unsynced-buffer risk ───
  //
  // `collectedSales` is NOT a pending queue. It is a rolling window of the last
  // BUFFER_CAP sales used for LOCAL DEDUP, and it is never cleared on a
  // successful send — so its SIZE sits at the cap during normal operation and
  // says nothing about risk. What matters is how many sales failed to reach the
  // server, because:
  //   · local dedup (below, and in processScan) skips them on a revisit, so
  //     re-walking the page does NOT re-send them; and
  //   · .slice(-BUFFER_CAP) silently drops the OLDEST entries, so an unsynced
  //     sale that rotates out is unrecoverable by ANY path, Sync included.
  // Tracked additively as `unsyncedCount`. The cap and the dedup logic are
  // deliberately UNCHANGED in this pass — this only makes the risk visible.
  const BUFFER_CAP = 1000;             // must match .slice(-1000) below
  const BUFFER_WARN_AT = 240;          // ≈ one eBay page of sold listings
  const BUFFER_WARN_SEVERE_AT = 750;   // 75% of cap — ~1 page of headroom left

  // ⚠️ This counter is a LOWER BOUND on risk, not a safe/unsafe line. The cap is
  // filled by ALL captures, synced and unsynced alike, so unsynced entries can
  // rotate out well before the count itself reaches BUFFER_WARN_SEVERE_AT (e.g.
  // 500 unsynced interleaved with 600 synced already drops 100). Absence of the
  // severe warning therefore does NOT prove nothing was dropped — the wording
  // below says "may already be" for that reason.
  function bufferWarning(unsynced) {
    if (!unsynced || unsynced < BUFFER_WARN_AT) return null;
    if (unsynced >= BUFFER_WARN_SEVERE_AT) {
      return { severe: true,
               text: `⚠ ${unsynced} UNSYNCED against a ${BUFFER_CAP} cap — the oldest ` +
                     `may already be dropped. Open the extension and press Sync.` };
    }
    return { severe: false,
             text: `⚠ ${unsynced} unsynced (cap ${BUFFER_CAP}) — press Sync in the ` +
                   `extension popup.` };
  }

  // Count sales whose send FAILED and that no successful Sync has flushed since.
  // Cleared only by the popup's Sync button (the only real flush) — NOT by a
  // later successful page send, because local dedup means that send did not
  // include the earlier failed items.
  //
  // Serialized through a promise chain: two processScan() runs CAN overlap (the
  // observer's debounce cancels a pending timer, not an in-flight scan parked on
  // `await sendSales`, which can sit for up to SYNC_TIMEOUT_MS). An unguarded
  // read-modify-write on chrome.storage.local would lose updates precisely when
  // sends are slow and failing — i.e. exactly when this warning matters.
  let _unsyncedGate = Promise.resolve(0);

  function noteSyncOutcome(result, attempted) {
    _unsyncedGate = _unsyncedGate.then(async () => {
      const current = (await chrome.storage.local.get(['unsyncedCount'])).unsyncedCount || 0;
      if (result.ok) return current;
      const next = current + attempted;
      await chrome.storage.local.set({ unsyncedCount: next });
      return next;
    }).catch(() => 0);   // never let the gate reject and wedge later callers
    return _unsyncedGate;
  }


  // ─── Run-scoped SAVED counter ───
  //
  // Replaces `sessionCollected`, which was wrong twice: it never reset per
  // session (only a popup button nobody presses — observed live at 235,216) and
  // it counted LOCALLY-NOVEL items, not rows the server actually inserted. A
  // real-sounding label over a number the code never measured.
  //
  // NO LIFETIME FIGURE IS KEPT ANY MORE. Postgres is the authority for
  // cumulative totals — `SELECT COUNT(*) FROM ebay_sales WHERE created_at > …`
  // is exact, survives a browser profile, and distinguishes inserted from
  // later-deleted. A local approximation of that is a liability, not an asset.
  //
  // BOUNDARY = AN IDLE GAP, not a calendar day and not the tab lifetime. eBay
  // pagination navigates, so a tab-scoped counter would reset every page and
  // merely duplicate `newCount`; a day boundary splits an evening run that
  // crosses local midnight. An idle gap matches how capture actually happens:
  // sit down, walk N searches, stop.
  //
  // DISCOVERABILITY: the banner shows the run's START TIME, not the reset rule
  // ("saved this run · since 3:42 PM"). The boundary becomes self-evident
  // without a tooltip, which a banner cannot carry.
  //
  // "SAVED" MEANS SERVER-CONFIRMED, STRICTLY. Only a numeric `result.saved` is
  // added; a missing field adds 0 — NEVER `newSales.length`, because falling
  // back to the local count is exactly what made the old counter wrong. A
  // failed send adds nothing, so the figure reads LOW after a failure that a
  // later popup Sync repairs. That is the safe direction under this label.
  //
  // ⚠️ KNOWN LIMITATION, deliberately unfixed (semantics before precision):
  // the read-modify-write below is UNGATED, so two overlapping processScan()
  // runs can both read the same base and the second write wins — the figure can
  // UNDER-count under concurrency. `unsyncedCount` above is gated against the
  // same race; this one is not. Do not read this number as exact.
  const RUN_IDLE_GAP_MS = 90 * 60 * 1000;   // 90 min with no capture = a new run

  // ⚠️ THE WRITER PERSISTS THE BOUNDARY, as an ABSOLUTE `runExpiresAt` — not a
  // timestamp the reader has to re-apply a duration to. This is deliberate: the
  // popup is a separate script that cannot import this module, so a duration
  // would have to be duplicated there, and the two copies are consulted for
  // DIFFERENT decisions (here: when to reset; there: when to hide). That drift
  // is silent in one direction and it had already happened once in this change.
  // With an absolute expiry there is exactly one source of truth and the popup
  // holds no constant at all.
  //
  // Expiry is computed off the send, not off `lastCollection` — the latter is
  // written BEFORE the send, so deriving the gap from it would pin it near zero
  // and no run would ever expire. Refreshed even when saved === 0, so a run does
  // not roll over mid-run just because sends are failing.
  async function noteSaved(result) {
    const saved = (result && result.ok && typeof result.saved === 'number') ? result.saved : 0;
    const now = Date.now();
    const s = await chrome.storage.local.get(['runSaved', 'runStartedAt', 'runExpiresAt']);
    const isNewRun = !s.runExpiresAt || now > s.runExpiresAt;
    const runStartedAt = isNewRun ? now : (s.runStartedAt || now);
    const runSaved = (isNewRun ? 0 : (s.runSaved || 0)) + saved;
    await chrome.storage.local.set({
      runSaved, runStartedAt, runExpiresAt: now + RUN_IDLE_GAP_MS });
    return { saved: runSaved, startedAt: runStartedAt };
  }

  // Read without extending the run — for banner paths that performed no send.
  // Returns null when no run is in progress, so the banner OMITS the figure
  // rather than asserting 0 (which would claim a run exists that saved nothing).
  async function readRun() {
    const s = await chrome.storage.local.get(['runSaved', 'runStartedAt', 'runExpiresAt']);
    if (!s.runExpiresAt || Date.now() > s.runExpiresAt) return null;
    return { saved: s.runSaved || 0,
             startedAt: s.runStartedAt || (s.runExpiresAt - RUN_IDLE_GAP_MS) };
  }


  // ─── Main execution ───

  async function main() {
    createBanner();
    updateBanner({ status: '⏳ Scanning page...', collecting: true });
    await new Promise(r => setTimeout(r, 1500));

    const sales = collectSales();
    const pageInfo = getPageInfo();

    if (sales.length === 0) {
      // Not necessarily an error under the lazy-hydrating markup: items may
      // not have rendered yet. The hydration observer keeps watching.
      updateBanner({ status: '⏳ Waiting for listings to render — scroll to load more', stats: { totalOnPage: 0 } });
      return 0;
    }

    const stored = await chrome.storage.local.get(['collectedSales']);
    const existing = stored.collectedSales || [];
    const existingIds = new Set(existing.map(s => s.ebay_item_id));
    const newSales = sales.filter(s => s.ebay_item_id && !existingIds.has(s.ebay_item_id));
    const dupeCount = sales.length - newSales.length;

    updateBanner({ status: '📡 Syncing to backend...', collecting: true, stats: { newCount: newSales.length, dupeCount, totalOnPage: sales.length } });

    if (newSales.length > 0) {
      const updated = [...existing, ...newSales].slice(-1000);
      // `totalCollected` / `sessionCollected` are no longer written — both were
      // the SAME unreconciled increment, surfaced under two different labels.
      // Replaced by the run-scoped, server-confirmed counter (see noteSaved);
      // cumulative totals come from Postgres, not from here.
      await chrome.storage.local.set({ collectedSales: updated, lastCollection: new Date().toISOString() });

      const result = await sendSales(newSales);
      const unsynced = await noteSyncOutcome(result, newSales.length);
      const run = await noteSaved(result);

      let pageInfoStr = null;
      if (pageInfo.totalPages > 1) {
        pageInfoStr = `Page ${pageInfo.currentPageNum} of ${pageInfo.totalPages}`;
        pageInfoStr += pageInfo.currentPageNum < pageInfo.totalPages ? ' — click Next →' : ' — last page ✓';
      }

      if (!result.ok) {
        // ⚠️ `newCount` here is ATTEMPTED, not saved — nothing reached the server.
        // Labelled "new" by updateBanner; see the audit note in the ship report.
        updateBanner({ status: syncFailureLabel(result, newSales.length), stats: { newCount: newSales.length, dupeCount, totalOnPage: sales.length, run, pageInfo: pageInfoStr }, warning: bufferWarning(unsynced) });
      } else {
        updateBanner({ status: `✅ ${result.saved ?? newSales.length} new sales synced`, stats: { newCount: result.saved ?? newSales.length, dupeCount: (result.duplicates || 0) + dupeCount, totalOnPage: sales.length, run, pageInfo: pageInfoStr }, warning: bufferWarning(unsynced) });
      }
      // Seed the observer's cumulative counter with the SERVER-inserted count
      // (local count only when the send failed and the server total is unknown).
      return result.ok ? (result.saved ?? newSales.length) : newSales.length;
    } else {
      let pageInfoStr = null;
      if (pageInfo.totalPages > 1) pageInfoStr = `Page ${pageInfo.currentPageNum} of ${pageInfo.totalPages}`;
      // No send happened, so READ the run without touching it.
      const run = await readRun();
      updateBanner({ status: '📋 All listings already collected', stats: { newCount: 0, dupeCount: sales.length, totalOnPage: sales.length, run, pageInfo: pageInfoStr } });
    }
    return 0;
  }


  // ─── Continuous capture: rescan as eBay lazy-hydrates (2026-07 markup) ───
  //
  // The ~2026-07 restructure changed the RENDERING MODEL, not just class
  // names: result items exist as [data-listingid] shells and hydrate their
  // title/price/"Sold" content progressively (largely as the HUMAN scrolls).
  // The original single-shot scan at T+1.5s therefore caught only the
  // first-hydrated batch (observed live: 12 of 287 containers, 2026-07-16).
  // A debounced MutationObserver re-runs the same pure-DOM scan whenever the
  // page renders more content, and syncs only ids not yet captured this page.
  //
  // ⚠️ CAPTURE-SAFETY INVARIANT (do not weaken): this observer sends ZERO
  // requests to eBay and drives ZERO navigation/scrolling — it passively
  // reacts to content eBay renders because the human scrolled. Pagination
  // stays a human click on eBay's native Next. See feedback_ebay_capture_safety.

  const pageCapturedIds = new Set();   // ids captured THIS page (all sources)
  let pageSyncedCount = 0;             // cumulative new-synced this page

  async function processScan() {
    const sales = collectSales().filter(s => s.ebay_item_id && !pageCapturedIds.has(s.ebay_item_id));
    if (sales.length === 0) return;    // silent no-op: never touches the banner,
                                       // so banner mutations can't self-trigger loops

    const stored = await chrome.storage.local.get(['collectedSales']);
    const existing = stored.collectedSales || [];
    const existingIds = new Set(existing.map(s => s.ebay_item_id));
    sales.forEach(s => pageCapturedIds.add(s.ebay_item_id));
    const newSales = sales.filter(s => !existingIds.has(s.ebay_item_id));
    if (newSales.length === 0) return;

    const updated = [...existing, ...newSales].slice(-1000);
    // Legacy `totalCollected` / `sessionCollected` no longer written — see the
    // note at the equivalent write in main().
    await chrome.storage.local.set({
      collectedSales: updated,
      lastCollection: new Date().toISOString()
    });

    const result = await sendSales(newSales);
    const failed = !result.ok;
    const unsynced = await noteSyncOutcome(result, newSales.length);
    const run = await noteSaved(result);
    // Count ONLY what the SERVER confirmed inserting — never the pre-dedup local
    // count. ON CONFLICT drops items already in the corpus from earlier captures
    // (observed 2026-07-16: banner claimed 265, server inserted 203).
    //
    // ⚠️ A FAILED send adds NOTHING. It previously added `newSales.length`, which
    // was never subtracted — so a later successful scan rendered
    // "✅ 150 synced this page" under a green tick when only 50 were confirmed,
    // with the failure text already scrolled out of the banner. Attempted-but-
    // unconfirmed is tracked separately and honestly by `unsyncedCount`.
    pageSyncedCount += (!failed && typeof result.saved === 'number')
      ? result.saved
      : (!failed ? newSales.length : 0);
    updateBanner({
      status: failed
        ? `${syncFailureLabel(result, newSales.length)} — watching as you scroll`
        : `✅ ${pageSyncedCount} synced this page — watching as you scroll`,
      stats: { newCount: pageSyncedCount, totalOnPage: pageCapturedIds.size, run },
      warning: bufferWarning(unsynced)
    });
  }

  function watchForHydration() {
    // Seed with everything the initial main() scan already handled, so the
    // first observer pass doesn't double-sync it.
    collectSales().forEach(s => { if (s.ebay_item_id) pageCapturedIds.add(s.ebay_item_id); });

    let debounce = null;
    const observer = new MutationObserver(() => {
      clearTimeout(debounce);
      debounce = setTimeout(() => { processScan().catch(e => console.error('eBay Collector: rescan error:', e)); }, 800);
    });
    // characterData + attributes included deliberately: the 2026-07-16
    // diagnostic showed this page mutates mostly by ATTRIBUTE (287 attr vs 47
    // childList fires in 60s) — a childList-only observer can miss renders.
    observer.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true });
    window.addEventListener('pagehide', () => observer.disconnect(), { once: true });
  }

  main().then(initialCount => {
    pageSyncedCount = initialCount || 0;  // observer banner counts continue from the initial batch
    watchForHydration();
  });
})();
