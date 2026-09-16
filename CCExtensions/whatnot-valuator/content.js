// content.js - Main entry point for Whatnot Comic Valuator
// NO require() or module.exports - pure browser JavaScript

(function() {
  'use strict';

  console.log('[Valuator] 🚀 Initializing Comic Valuator v2.46.0...');
  console.log('[Valuator] Vision:', window.ComicVision ? '✅ Loaded' : '❌ Not loaded');
  console.log('[Valuator] CollectionCalc:', window.SupabaseClient ? '✅ Connected' : '❌ Not loaded');

  let currentItemId = null;
  let overlayEl = null;
  let isMinimized = false;
  let salesCount = 0;
  let previousListing = null;  // Track the listing that was showing before current
  let currentListing = null;   // Current listing for manual grade recalc
  let currentParsed = null;    // Current parsed data for manual grade recalc
  let manualGrade = null;      // User-entered grade
  let lastSaleCheck = null;    // Prevent duplicate sale recording
  let lastSaleTime = 0;        // Timestamp of last sale for debounce
  let appliedVisionData = null; // Vision data that was applied via "Use This"
  let autoScanEnabled = true;   // Auto-scan toggle state (default ON)
  let lastAutoScanId = null;    // Prevent duplicate auto-scans
  let pendingAutoScanKey = null; // Listing waiting for bidding to start
  let isScanning = false;       // Prevent concurrent scans
  let scanCooldownUntil = 0;    // Timestamp - no new scans until this time
  let lastScannedListingId = null; // Track by listing.id only (not title)
  let lastScanTime = 0;         // When we last scanned

  // 2.44.0 — held-state ownership (queue item 2). Before this build appliedVisionData and
  // previousListing were cleared ONLY after a recorded sale, so a listing that ended without
  // a detected sale left the previous book's identity, grade and image on the next sale
  // record. Now: vision is stamped with the listing it was scanned for and attaches only to
  // that listing's sale; a held previous listing expires at the next switch or after
  // HELD_PREVIOUS_EXPIRY_MS; a scan whose listing changed while it ran is discarded.
  // Every drop is logged, counted, and shown in the overlay.
  //
  // 2.45.0 — IDENTITY IS THE LISTING ID, NEVER THE CHANGE KEY. The watcher's "new item" test is
  // the key `id-title` (or a price drop), and that key moves on a DOM title reading or a price
  // scrape while the listing id does not (a "flap"; the 2026-09-15 field buffer showed flaps
  // every 500 ms on one id). 2.43.0 tolerated flaps because its switch branch only overwrote a
  // slot; 2.44.0 attached consequences to the same branch and every flap became a false
  // "ended unsold" that could drop vision for the listing still on screen. Now: the unsold
  // rule, the expiry counter and the vision drop fire only when the listing ID changes; a flap
  // keeps 2.43.0's snapshot semantics and is recorded as its own timing entry.
  let previousListingHeldAt = 0;         // when previousListing was captured
  let lastSwitchAt = 0;                  // last REAL switch (id changed), for the timing buffer
  let lastSoldListingId = null;          // 2.45.0 — a listing whose sale is recorded is not
                                         // held as "previous" again: 2.43.0 re-held it at the
                                         // next switch, so the NEXT listing's sold text resolved
                                         // to the already-sold previous and was deduped away
                                         // (harness-reproduced 2026-09-15), and 2.44.0 counted
                                         // the same stale hold as an unsold listing.
  // 2.46.0 — a sold text is CONSUMED by the record it produced and ignored until it changes or
  // disappears. Before this, the previous lot's "X won!" banner persisting across the seller's
  // price reset for the next lot was re-detected once the same-id hold released (~10 s) and
  // recorded at the NEXT lot's opening price (stream 2257274543, 2026-09-15, half an hour of
  // them). Known limit: two consecutive lots won by the same user under a banner that never
  // disappears in between register once.
  let consumedSaleSig = null;
  let lastConsumedSig = null;   // survives a one-poll banner blink (see the debounce branch)
  // The signature is taken from the auction FOOTER first (its first line is "<winner> won!"), and
  // only from the whole page when the footer carries no sold text — a pinned chat line such as
  // "congrats you won!" earlier in the page must not become the signature of every sale.
  function saleTextSignature(footerText, pageText) {
    const line = footerText.split('\n').find(l => /\bwon\b/.test(l) || l.includes('sold'));
    if (line) {
      const w = line.match(/(\S{1,40})\s+won\b/);
      return w ? 'won:' + w[1] : 'footer:' + line.replace(/\s+/g, ' ').trim().slice(0, 120);
    }
    const m = pageText.match(/(\S{1,40})\s+won[!\n]/);
    return m ? 'page-won:' + m[1] : 'page:' + pageText.slice(0, 40);
  }
  let relistedSinceSale = false;         // ...UNLESS a same-id price reset was seen after that
                                         // sale (a second copy under the same id/label): then
                                         // the ending listing is a different sale and IS held,
                                         // so its late sold text attributes to it, not to the
                                         // listing after (verifier finding, 2026-09-15).
  const HELD_PREVIOUS_EXPIRY_MS = 10000; // PROVISIONAL (WWLO 2026-09-15): measured from 'sw'
                                         // entries (real switches) only, never from 'flap'
                                         // entries. Do not change without that measurement.
  const dropCounts = { mismatch: 0, fallbackId: 0, unsoldExpiry: 0, lateScan: 0 };

  function isFallbackId(id) {
    return typeof id === 'string' && id.startsWith('dom-');
  }

  function recordDrop(kind, detail) {
    dropCounts[kind] = (dropCounts[kind] || 0) + 1;
    console.warn(`[Valuator] DROP ${kind}: ${detail}`);
    renderDropCounts();
  }

  function renderDropCounts() {
    const el = overlayEl && overlayEl.querySelector('.valuator-drops');
    if (!el) return;
    el.textContent = `drops · mismatch ${dropCounts.mismatch} · fallback-id ${dropCounts.fallbackId}` +
      ` · unsold-expiry ${dropCounts.unsoldExpiry} · late-scan ${dropCounts.lateScan}`;
  }

  // Timing ring buffer — measures the gap between a REAL listing switch and the sold text, the
  // number HELD_PREVIOUS_EXPIRY_MS is a guess at. Entries are compact arrays (2.45.0 shape):
  //   ['sw',   t, fromId, toId, fromTitle, fromPrice, toTitle, toPrice]  listing ID changed
  //   ['flap', t, id, fromTitle, fromPrice, toTitle, toPrice]            key moved, id did not
  //   ['sale', t, msSinceRealSwitch, usedPrev, soldId]                   sale detected
  // Ids and titles are cut to 40 chars: ~210 bytes per entry as JSON for ASCII, up to ~450
  // for a title of 4-byte characters with escapes, so 500 entries is under 110 KB typical and
  // under 250 KB worst case, of the 10 MB chrome.storage.local quota (whatnot_sales is capped
  // at 500 for the same reason). Writes are coalesced to one per 2 s so a flapping listing
  // does not rewrite the buffer every poll. Read it with ValuatorDebug.getTiming(). Entries
  // written by 2.44.0 (['sw', t, fromId, toId] with from == to) are flaps mislabelled as
  // switches: ignore them.
  const TIMING_KEY = 'valuator_timing';
  const TIMING_MAX = 500;
  let timingBuffer = null;   // loaded from storage on first use
  let timingPending = [];    // entries that arrive while that first load is in flight
  let timingFlushTimer = null;
  // 2.46.0 — read, merge by timestamp, write: every content-script instance (one per open stream)
  // used to rewrite the stored array from its own copy, so the last tab to flush won and the
  // others' history was lost (09-15: a 69-entry chain overwritten by a 6-entry one). The merge
  // is a union keyed on the entry's own JSON, sorted by t, capped at TIMING_MAX — so the merged
  // bound is unchanged: 500 entries, under 110 KB typical / 250 KB worst case.
  function flushTiming() {
    timingFlushTimer = null;
    const local = timingBuffer;
    const write = (stored) => {
      if (chrome.runtime && chrome.runtime.lastError) {
        // the read failed: writing now would replace the other tabs' history with ours alone.
        // Keep ours in memory; the next push re-arms the flush and retries the merge.
        return;
      }
      const seen = new Set(); const merged = [];
      for (const e of [...(Array.isArray(stored) ? stored : []), ...local]) {
        const k = JSON.stringify(e);
        if (!seen.has(k)) { seen.add(k); merged.push(e); }
      }
      merged.sort((a, b) => (a[1] || 0) - (b[1] || 0));
      while (merged.length > TIMING_MAX) merged.shift();
      timingBuffer = merged;
      try { chrome.storage.local.set({ [TIMING_KEY]: merged }); } catch (err) { /* storage gone */ }
    };
    try {
      chrome.storage.local.get([TIMING_KEY], (result) => write(result && result[TIMING_KEY]));
    } catch (e) { write([]); }
  }
  function recordTiming(entry) {
    const push = (e) => {
      timingBuffer.push(e);
      while (timingBuffer.length > TIMING_MAX) timingBuffer.shift();
      if (!timingFlushTimer) timingFlushTimer = setTimeout(flushTiming, 2000);
    };
    if (timingBuffer) { push(entry); return; }
    timingPending.push(entry);
    while (timingPending.length > TIMING_MAX) timingPending.shift();
    if (timingPending.length > 1) return; // a load is already in flight; it will drain the queue
    const drain = (loaded) => {
      timingBuffer = Array.isArray(loaded) ? loaded : [];
      const queued = timingPending; timingPending = [];
      queued.forEach(push);
    };
    try {
      chrome.storage.local.get([TIMING_KEY], (result) => drain(result && result[TIMING_KEY]));
    } catch (e) { drain([]); }
  }
  const shortId = (id) => (id == null ? null : String(id).slice(0, 40));

  // The held previous listing ended without a detected sale: drop it, and drop held vision
  // only when that vision was scanned for it. Vision scanned for the listing now moving into
  // the held slot must survive, because the sold text for it arrives AFTER the switch.
  function dropHeldPrevious(reason) {
    const held = previousListing;
    previousListing = null;
    previousListingHeldAt = 0;
    let detail = `held listing ${held.id} "${held.title}" ended without a detected sale (${reason})`;
    // 2.45.0 — never drop vision owned by the listing that is on screen now
    const ownedByCurrent = currentListing && appliedVisionData &&
      appliedVisionData.forListingId === currentListing.id;
    if (appliedVisionData && appliedVisionData.forListingId === held.id && !ownedByCurrent) {
      detail += `; dropped its vision "${appliedVisionData.title}"`;
      appliedVisionData = null;
    }
    recordDrop('unsoldExpiry', detail);
  }

  function expireHeldPrevious() {
    if (!previousListing || !previousListingHeldAt) return;
    if (Date.now() - previousListingHeldAt <= HELD_PREVIOUS_EXPIRY_MS) return;
    if (currentListing && previousListing.id === currentListing.id) {
      // 2.45.0 — a same-id snapshot (held at a flap or a price reset) of the listing still on
      // screen: releasing it is housekeeping, not an unsold listing. No counter, no vision.
      previousListing = null;
      previousListingHeldAt = 0;
      console.log('[Valuator] released same-id snapshot of', currentListing.id, 'after', HELD_PREVIOUS_EXPIRY_MS, 'ms');
      return;
    }
    dropHeldPrevious(`timeout ${HELD_PREVIOUS_EXPIRY_MS} ms`);
  }

  // Vision attaches to a sale only when it was scanned for the listing that sold. On a
  // mismatch it is withheld from this record; it is discarded unless it belongs to the
  // listing that is current now (the usual mismatch: the previous listing's sold text lands
  // after the next listing was already scanned), in which case it is kept for that sale.
  function visionForSale(soldListing) {
    const v = appliedVisionData;
    if (!v) return null;
    const soldId = soldListing ? soldListing.id : null;
    if (v.forListingId != null && soldId != null && v.forListingId === soldId) return v;
    const kind = (isFallbackId(v.forListingId) || isFallbackId(soldId)) ? 'fallbackId' : 'mismatch';
    const keep = currentListing && v.forListingId != null && v.forListingId === currentListing.id;
    recordDrop(kind, `vision "${v.title}" was scanned for listing ${v.forListingId}, sold listing is ${soldId}` +
      (keep ? ' (kept for the current listing)' : ' (discarded)'));
    if (!keep) appliedVisionData = null;
    return null;
  }

  // Initialize
  function init() {
    createOverlay();
    startWatching();
    registerWithBackground();
    console.log('[Valuator] ✅ Ready!');
  }

  // Register tab with background service
  function registerWithBackground() {
    const streamTitle = document.title || 'Whatnot Live';
    chrome.runtime.sendMessage({
      type: 'TAB_READY',
      streamTitle: streamTitle
    }).catch(() => {});
  }

  // Create the overlay element
  function createOverlay() {
    overlayEl = document.createElement('div');
    overlayEl.id = 'comic-valuator-overlay';
    overlayEl.innerHTML = `
      <div class="valuator-header">
        <span>📊 Comic Valuator</span>
        <div class="valuator-header-buttons">
          <button class="valuator-settings" title="Account Settings">⚙️</button>
          <button class="valuator-toggle" title="Minimize">−</button>
        </div>
      </div>
      <div class="valuator-body">
        <div class="valuator-title">Waiting for auction...</div>
        <div class="valuator-details">
          <div class="valuator-grade"></div>
          <div class="valuator-note"></div>
        </div>
        <div class="valuator-current">Current: --</div>
        <div class="valuator-fmv-grid">
          <div class="fmv-col"><span class="fmv-price">--</span><span class="fmv-tier">&lt;4.5</span></div>
          <div class="fmv-col"><span class="fmv-price">--</span><span class="fmv-tier">4.5-7.9</span></div>
          <div class="fmv-col"><span class="fmv-price">--</span><span class="fmv-tier">8-8.9</span></div>
          <div class="fmv-col"><span class="fmv-price">--</span><span class="fmv-tier">9+</span></div>
        </div>
        <div class="valuator-verdict"></div>
        <div class="valuator-scan">
          <button id="vision-scan" title="Scan comic from video">📷 Scan</button>
          <span class="scan-status"></span>
        </div>
        <div class="valuator-last-scan" style="display:none;">
          <div class="last-scan-header">Last Scan</div>
          <div class="last-scan-content">
            <img class="last-scan-thumb" src="" alt="" />
            <div class="last-scan-info">
              <div class="last-scan-title"></div>
              <div class="last-scan-details"></div>
              <div class="last-scan-sold"></div>
            </div>
          </div>
        </div>
        <div class="valuator-timer"></div>
        <a class="valuator-ebay" href="#" target="_blank" style="display:none;">🔍 Check eBay</a>
      </div>
      <div class="valuator-footer">📈 <span class="sale-count">0</span> sales tracked</div>
      <div class="valuator-drops" title="Held vision or listing data dropped instead of being recorded (2.44.0)">drops · mismatch 0 · fallback-id 0 · unsold-expiry 0 · late-scan 0</div>
      <div class="valuator-api-modal" style="display:none;">
        <div class="api-modal-content">
          <h4>🔐 Sign In Required</h4>
          <p>Vision scanning requires a Slab Worthy account (Guard+ plan).</p>
          <p style="margin-top:8px;font-size:12px;color:#aaa;">Right-click the extension icon → Options to sign in.</p>
          <div class="api-modal-buttons">
            <button id="api-key-cancel">Close</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(overlayEl);

    // Toggle minimize
    overlayEl.querySelector('.valuator-toggle').addEventListener('click', () => {
      isMinimized = !isMinimized;
      overlayEl.querySelector('.valuator-body').style.display = isMinimized ? 'none' : 'block';
      overlayEl.querySelector('.valuator-toggle').textContent = isMinimized ? '+' : '−';
    });
    
    // Vision scan button
    const scanBtn = overlayEl.querySelector('#vision-scan');
    scanBtn.addEventListener('click', handleVisionScan);
    
    // Auth modal
    overlayEl.querySelector('.valuator-settings').addEventListener('click', showApiModal);
    overlayEl.querySelector('#api-key-cancel').addEventListener('click', hideApiModal);
  }

  // Vision scan state
  let lastVisionResult = null;

  // Handle vision scan button click
  async function handleVisionScan() {
    const scanBtn = overlayEl.querySelector('#vision-scan');
    const statusEl = overlayEl.querySelector('.scan-status');
    
    // Prevent concurrent scans
    if (isScanning) {
      console.log('[Valuator] Scan skipped - already scanning');
      return;
    }
    
    // Check for video element first
    const video = document.querySelector('video');
    if (!video) {
      statusEl.textContent = '❌ No video';
      console.log('[Valuator] Scan skipped - no video element');
      return;
    }
    
    // Check for API key first
    if (window.ComicVision) {
      const hasKey = await window.ComicVision.hasApiKey();
      if (!hasKey) {
        showApiModal();
        return;
      }
    }
    
    // Set scanning flag
    isScanning = true;

    // Update UI to show scanning
    scanBtn.disabled = true;
    scanBtn.textContent = '📷 Scan';
    statusEl.textContent = 'Scanning...';

    // 2.44.0 — the listing this scan is FOR. Checked again when the result arrives.
    const scanListingId = currentListing ? currentListing.id : null;

    try {
      const result = await window.ComicVision.scan();
      const nowListingId = currentListing ? currentListing.id : null;

      if (nowListingId !== scanListingId) {
        // Late result: the listing changed while the scan ran. Applying it would stamp the
        // next listing with this one's book.
        statusEl.textContent = 'Scan outdated';
        recordDrop('lateScan', `scan started on listing ${scanListingId} returned on ${nowListingId}` +
          (result && result.title ? ` (result "${result.title}")` : ''));
      } else if (result.error) {
        statusEl.textContent = '❌ ' + result.error;
        console.log('[Vision] Error:', result.error);
        // Still show the card with error state
        showScanError(result.error, result.frameData);
      } else {
        // Show result in overlay
        result.forListingId = scanListingId;
        lastVisionResult = result;
        showVisionResult(result);
        statusEl.textContent = 'Complete';
      }
    } catch (e) {
      statusEl.textContent = '❌ Scan failed';
      console.error('[Vision] Scan error:', e);
    }
    
    // Reset button and scanning flag
    scanBtn.disabled = false;
    scanBtn.textContent = '📷 Scan';
    isScanning = false;
  }

  // Show scan error in Last Scan card
  function showScanError(error, frameData) {
    const cardEl = overlayEl.querySelector('.valuator-last-scan');
    const thumbEl = cardEl.querySelector('.last-scan-thumb');
    const titleEl = cardEl.querySelector('.last-scan-title');
    const detailsEl = cardEl.querySelector('.last-scan-details');
    const soldEl = cardEl.querySelector('.last-scan-sold');
    
    // Set thumbnail if available
    if (frameData) {
      thumbEl.src = frameData;
      thumbEl.style.display = 'block';
    } else {
      thumbEl.style.display = 'none';
    }
    
    titleEl.textContent = '⚠️ Scan failed';
    detailsEl.textContent = error || 'Unknown error';
    soldEl.textContent = '';
    soldEl.style.display = 'none';
    
    cardEl.style.display = 'block';
  }

  // Display vision result in Last Scan card and auto-apply
  function showVisionResult(result) {
    const cardEl = overlayEl.querySelector('.valuator-last-scan');
    const thumbEl = cardEl.querySelector('.last-scan-thumb');
    const titleEl = cardEl.querySelector('.last-scan-title');
    const detailsEl = cardEl.querySelector('.last-scan-details');
    const soldEl = cardEl.querySelector('.last-scan-sold');
    
    // Check local key database if Vision didn't return keyInfo
    if (!result.keyInfo && result.title && result.issue && window.lookupKeyInfo) {
      const localKeyInfo = window.lookupKeyInfo(result.title, result.issue);
      if (localKeyInfo) {
        result.keyInfo = localKeyInfo;
        console.log('[Valuator] Key info from database:', localKeyInfo);
      }
    }
    
    // Set thumbnail
    if (result.frameData) {
      thumbEl.src = result.frameData;
      thumbEl.style.display = 'block';
    } else {
      thumbEl.style.display = 'none';
    }
    
    // Title with key icon if applicable
    let titleText = result.title 
      ? `${result.title}${result.issue ? ' #' + result.issue : ''}`
      : 'Unknown comic';
    if (result.keyInfo) {
      titleText += ' 🔑';
    }
    titleEl.textContent = titleText;
    
    // Details
    let details = [];
    if (result.grade) {
      if (result.slabType === 'raw') {
        details.push(`~${result.grade}`);
      } else {
        details.push(result.grade);
      }
    }
    if (result.slabType) details.push(result.slabType.toUpperCase());
    if (result.variant) details.push(result.variant);
    if (result.keyInfo) details.push(result.keyInfo);
    
    detailsEl.textContent = details.join(' • ') || '';
    
    // Clear sold price (will be set when item sells)
    soldEl.textContent = '';
    soldEl.style.display = 'none';
    
    // Show card
    cardEl.style.display = 'block';
    
    // Auto-apply the result
    applyVisionResult();
  }

  // Apply vision result to current listing
  function applyVisionResult() {
    if (!lastVisionResult) return;
    
    const result = lastVisionResult;
    
    // Store vision data for sale recording (including image)
    appliedVisionData = {
      title: result.title,
      issue: result.issue,
      slabType: result.slabType,
      variant: result.variant,
      keyInfo: result.keyInfo,
      isKey: !!result.keyInfo,  // Boolean for database
      grade: result.grade,
      frameData: result.frameData,  // Save the scanned image
      forListingId: result.forListingId == null ? null : result.forListingId  // 2.44.0 owner
    };
    
    // Update the overlay with vision data
    const titleEl = overlayEl.querySelector('.valuator-title');
    titleEl.textContent = result.title 
      ? `${result.title}${result.issue ? ' #' + result.issue : ''}`
      : titleEl.textContent;
    
    // Set the grade if found
    if (result.grade) {
      manualGrade = result.grade;
      
      // Update parsed data
      if (currentParsed) {
        currentParsed.grade = result.grade;
        currentParsed.series = result.title || currentParsed.series;
        currentParsed.issue = result.issue || currentParsed.issue;
      }
      
      // Recalculate valuation
      if (currentParsed && currentListing) {
        const valuation = window.Valuator ? window.Valuator.lookup(currentParsed) : null;
        updateOverlay(currentListing, currentParsed, valuation);
      }
    }
    
    // Update slab type in current listing for when sale is recorded
    if (result.slabType && currentListing) {
      currentListing.slabType = result.slabType;
    }
    
    // Show key info
    if (result.keyInfo) {
      const noteEl = overlayEl.querySelector('.valuator-note');
      noteEl.textContent = result.keyInfo;
      noteEl.style.display = 'block';
    }
    
    // Don't dismiss - keep card visible until next scan
    console.log('[Vision] ✅ Applied result:', appliedVisionData.title);
  }

  // Clear last scan card (called when new scan starts)
  function clearLastScanCard() {
    const cardEl = overlayEl.querySelector('.valuator-last-scan');
    cardEl.style.display = 'none';
    lastVisionResult = null;
  }

  // Show auth modal (directs user to extension Options for login)
  function showApiModal() {
    const modal = overlayEl.querySelector('.valuator-api-modal');
    modal.style.display = 'flex';
  }

  // Hide auth modal
  function hideApiModal() {
    overlayEl.querySelector('.valuator-api-modal').style.display = 'none';
  }

  // Check if title is garbage (generic placeholder)
  function isGarbageTitle(title) {
    if (!title) return true;
    const lower = title.toLowerCase();
    const garbagePatterns = [
      'awesome comic',
      'comic on screen',
      'comic book on screen',
      'on screen',
      'product',
      'item',
      'listing',
      'available',        // "91 Available"
      'remaining',        // "X remaining"
      'left',             // "X left"
      'in stock',
      'bid now',
      'starting',
      'mystery',
      'random',
      'surprise',
      'bundle',
      'lot of',
      'choice',
      'pick',
      /^comic\s*#?\d*$/i,  // just "Comic" or "Comic #1"
      /^book\s*#?\d*$/i,
      /^\$\d+/,           // Starts with dollar amount "$30"
      /^\d+\s*(available|left|remaining)/i, // "91 Available"
      /^#?\d+$/,          // Just a number like "91" or "#5"
    ];
    
    // Also reject if title is too short or just numbers/symbols
    if (title.length < 3) return true;
    if (/^[\d\s$#%]+$/.test(title)) return true;  // Only numbers/symbols
    
    for (const pattern of garbagePatterns) {
      if (typeof pattern === 'string') {
        if (lower.includes(pattern)) return true;
      } else if (pattern.test(lower)) {
        return true;
      }
    }
    return false;
  }

  // Check if DOM has good data (not garbage placeholder)
  function hasGoodDOMData(listing, parsed) {
    // If title is garbage, DOM data is bad
    if (isGarbageTitle(listing.title)) return false;
    
    // If we have a parsed series and issue, DOM is good
    if (parsed && parsed.series && parsed.issue) return true;
    
    // If title looks like a real comic title (has issue number pattern)
    if (listing.title && /#\d+|\s\d+\s*$/.test(listing.title)) return true;
    
    return false;
  }

  // Check if bidding has started for this listing
  function isBiddingActive(listing) {
    // Check DOM for "Auction hasn't started" - this overrides everything
    const auctionBanner = document.querySelector('[class*="Footer"], [class*="footer"], [class*="Banner"], [class*="banner"]');
    if (auctionBanner && /auction hasn't started/i.test(auctionBanner.innerText)) {
      return false;
    }
    
    // Also check the entire visible page for this text
    const pageText = document.body?.innerText || '';
    if (/auction hasn't started/i.test(pageText)) {
      return false;
    }
    
    // Check DOM for "Winning" text (indicates active bidding)
    if (auctionBanner && /winning/i.test(auctionBanner.innerText)) return true;
    
    // Timer is set and in the future AND has actual bids (not just pre-bids)
    // Note: bidCount can include pre-bids, so we rely more on DOM signals
    if (listing.endsAt) {
      const endTime = new Date(listing.endsAt).getTime();
      const now = Date.now();
      // If timer is running (less than 60 seconds), auction is definitely active
      if (endTime > now && endTime - now < 60000) return true;
    }
    
    return false;
  }

  // Auto-scan when enabled - scans immediately on new item detection
  // Session 61: Removed bidding gate — scan as soon as item appears so user
  // can identify the comic BEFORE deciding to bid. Fast auctions ($3 start)
  // sell instantly, so waiting for bidding means missing the scan entirely.
  async function maybeAutoScan(listing) {
    if (!autoScanEnabled) return;
    if (!listing) return;
    if (isScanning) return;  // Already scanning

    // Check if we already scanned this listing.id recently (regardless of title)
    if (listing.id === lastScannedListingId && Date.now() - lastScanTime < 30000) {
      console.log('[Valuator] Auto-scan skipped - already scanned listing', listing.id);
      return;
    }

    // Make sure we're on a live auction page with video
    const video = document.querySelector('video');
    if (!video) {
      console.log('[Valuator] Auto-scan skipped - no video element (not a live auction?)');
      return;
    }

    // Check scan cooldown (prevents duplicate scans when title updates mid-scan)
    if (Date.now() < scanCooldownUntil) {
      console.log('[Valuator] Auto-scan skipped - in cooldown period');
      return;
    }

    // Check for auth token
    if (window.ComicVision) {
      const hasKey = await window.ComicVision.hasApiKey();
      if (!hasKey) {
        console.log('[Valuator] Auto-scan skipped - not signed in');
        return;
      }
    }

    // Scan immediately - mark this listing as scanned
    lastAutoScanId = `${listing.id}-${listing.title}`;
    lastScannedListingId = listing.id;
    lastScanTime = Date.now();
    scanCooldownUntil = Date.now() + 10000; // 10s cooldown prevents duplicate scans
    pendingAutoScanKey = null;
    console.log('[Valuator] 🤖 Auto-scanning:', listing.title);

    // Small delay to let video stabilize on new item
    const statusEl = overlayEl.querySelector('.scan-status');
    statusEl.textContent = 'Scanning...';
    await new Promise(r => setTimeout(r, 1500));

    // Trigger scan
    handleVisionScan();
  }
  
  // checkPendingAutoScan removed in Session 61 — scans fire immediately now

  // Watch for auction changes
  let watchCount = 0;
  let watchIntervalId = null;  // Store interval ID for cleanup
  let teardownRegistered = false;  // 2.46.0
  
  function startWatching() {
    // Clear any existing interval first
    if (watchIntervalId) {
      clearInterval(watchIntervalId);
    }
    
    watchIntervalId = setInterval(() => {
      try {
        const listing = window.ApolloReader ? window.ApolloReader.getCurrentListing() : null;
        
        watchCount++;
        
        // Use title as part of ID since sellers reuse same product for different comics
        const listingKey = listing ? `${listing.id}-${listing.title}` : null;
        
        // Detect new item via: key change OR significant price drop (new auction started)
        const priceDropped = listing && currentListing && 
          listing.price < currentListing.price * 0.5 && // Price dropped >50%
          listing.price <= 2000; // And now under $20 (typical starting bid)
        
        const isNewItem = listing && (listingKey !== currentItemId || priceDropped);
        
        // Check if listing.id actually changed (truly new auction item)
        const listingIdChanged = listing && currentListing && listing.id !== currentListing.id;
        
        if (isNewItem) {
          // Save previous listing before switching (for sale detection)
          if (currentListing) {
            const now = Date.now();
            if (listingIdChanged) {
              // 2.45.0 — a REAL switch. A previous listing still held here whose id is neither
              // the listing ending now nor the one arriving saw no detected sale across the whole
              // listing that just ended: it ended unsold. Drop it before it is overwritten. A held
              // same-id snapshot of the ending listing is simply refreshed (2.44.0 counted that as
              // unsold — the false fire).
              if (previousListing && previousListing.id !== currentListing.id &&
                  previousListing.id !== listing.id) {
                dropHeldPrevious('switch');
              }
              if (currentListing.id === lastSoldListingId && !relistedSinceSale) {
                // its sale is already recorded: nothing to wait for, nothing to expire
                previousListing = null;
                previousListingHeldAt = 0;
              } else {
                previousListing = { ...currentListing };
                previousListingHeldAt = now;
              }
              lastSwitchAt = now;
              recordTiming(['sw', now, shortId(currentListing.id), shortId(listing.id),
                shortId(currentListing.title), currentListing.price, shortId(listing.title), listing.price]);
            } else {
              // 2.45.0 — a FLAP (or a same-id price reset): the key moved, the id did not. Not a
              // listing end. 2.43.0 semantics kept: hold the snapshot only when nothing else is
              // held or the held one is this same listing (keeps the pre-reset price for a
              // same-label relist); a held previous with ANOTHER id is left alone so its sold text
              // still attributes to it.
              if (!previousListing || previousListing.id === listing.id) {
                previousListing = { ...currentListing };
                previousListingHeldAt = now;
              }
              if (priceDropped && listing.id === lastSoldListingId) relistedSinceSale = true;
              recordTiming(['flap', now, shortId(listing.id),
                shortId(currentListing.title), currentListing.price, shortId(listing.title), listing.price]);
            }
          }
          currentItemId = listingKey;
          currentListing = listing;
          
          // Reset scan tracking only when the actual listing ID changes
          // (not on title fluctuations from Apollo cache updates)
          if (listingIdChanged) {
            lastAutoScanId = null;
            pendingAutoScanKey = null;
            isScanning = false;
            lastScannedListingId = null;
            lastScanTime = 0;
          }
          
          if (priceDropped) {
            // Check if we already scanned this listing.id recently
            if (listing.id === lastScannedListingId && Date.now() - lastScanTime < 30000) {
              console.log('[Valuator] Price-drop scan skipped - already scanned listing', listing.id);
              processListing(listing);
            } else {
              console.log('[Valuator] 🆕 New listing detected (price reset):', listing.title, '$' + (listing.price/100));
              // Force scan - DOM data is clearly stale if price dropped but title didn't change
              processListing(listing);
              if (autoScanEnabled) {
                // Set cooldown to prevent duplicate scans if title updates during delay
                scanCooldownUntil = Date.now() + 10000; // 10 second cooldown
                const scanKey = `${listing.id}-${listing.title}`;
                lastAutoScanId = scanKey;
                lastScannedListingId = listing.id;
                lastScanTime = Date.now();
                console.log('[Valuator] 🔄 Force scanning due to stale DOM data');
                setTimeout(() => {
                  // Update scanKey in case title changed during delay
                  lastAutoScanId = `${currentListing.id}-${currentListing.title}`;
                  handleVisionScan();
                }, 1500);
              }
            }
          } else {
            console.log('[Valuator] 🆕 New listing detected:', listing.title, '$' + (listing.price/100));
            processListing(listing);
            // Auto-scan if enabled and title looks like garbage
            maybeAutoScan(listing);
          }
        }
        
        // Update timer
        if (listing && listing.endsAt) {
          updateTimer(listing.endsAt);
        }
        
        // 2.44.0 — a held previous listing older than the bound is not a sale candidate
        expireHeldPrevious();

        // Check for sale
        checkForSale(listing);

      } catch (e) {
        console.log('[Valuator] Watch error:', e.message);
      }
    }, 500);
    
    // Cleanup when tab closes or navigates away. 2.46.0: registered ONCE (startWatching re-runs
    // on every tab-visible resume and used to stack these), and 'pagehide' instead of 'unload',
    // which whatnot.com's permissions policy refuses (logged as a violation, never fired).
    if (teardownRegistered) return;
    teardownRegistered = true;
    window.addEventListener('beforeunload', cleanupWatcher);
    window.addEventListener('pagehide', cleanupWatcher);

    // Also listen for visibility changes (tab hidden = pause, reduces server load)
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        console.log('[Valuator] Tab hidden - pausing watcher');
        if (watchIntervalId) {
          clearInterval(watchIntervalId);
          watchIntervalId = null;
        }
      } else {
        console.log('[Valuator] Tab visible - resuming watcher');
        if (!watchIntervalId) {
          startWatching();
        }
      }
    });
  }
  
  // Cleanup function to stop polling
  function cleanupWatcher() {
    if (watchIntervalId) {
      clearInterval(watchIntervalId);
      watchIntervalId = null;
      console.log('[Valuator] 🛑 Watch interval cleaned up');
    }
  }

  // Process a new listing
  function processListing(listing) {
    console.log('[Valuator] New item:', listing.title);
    
    // Reset grade for new item
    manualGrade = null;
    
    // Reset FMV display while loading
    const fmvPrices = overlayEl.querySelectorAll('.fmv-price');
    fmvPrices.forEach(el => el.textContent = '--');
    
    // Parse the title
    const parsed = window.ComicNormalizer ? 
      window.ComicNormalizer.parse(listing.title, listing.subtitle) : 
      { raw: listing.title };
    
    // Store for manual grade recalc
    currentListing = listing;
    currentParsed = parsed;
    
    // Look up valuation
    const valuation = window.Valuator ? 
      window.Valuator.lookup(parsed) : 
      null;
    
    // Update overlay
    updateOverlay(listing, parsed, valuation);
    
    // Notify background
    chrome.runtime.sendMessage({
      type: 'ITEM_UPDATE',
      item: { ...listing, parsed, valuation }
    }).catch(() => {});
  }

  // Update the overlay UI
  async function updateOverlay(listing, parsed, valuation) {
    const currentBid = listing.price ? listing.price / 100 : 0;
    const isLive = isBiddingActive(listing);
    
    // Title - always show the original title from DOM/listing
    const titleEl = overlayEl.querySelector('.valuator-title');
    titleEl.textContent = listing.title?.substring(0, 50) || 'Unknown';
    
    // Grade
    const gradeEl = overlayEl.querySelector('.valuator-grade');
    if (parsed.grade) {
      gradeEl.textContent = `Grade: ${parsed.grade}`;
      gradeEl.style.display = 'block';
    } else {
      gradeEl.style.display = 'none';
    }
    
    // Note (1st appearance, etc) - only from Vision, not static data
    const noteEl = overlayEl.querySelector('.valuator-note');
    // Note is now set by Vision applyVisionResult, not static data
    // Don't show unreliable static notes
    if (!appliedVisionData) {
      noteEl.style.display = 'none';
    }
    
    // Current/Starting/Pre-bid price label
    const bidCount = listing.bidCount || listing.bids || 0;
    const hasPrebids = bidCount > 0 && !isLive;
    let priceLabel;
    let priceText;
    if (isLive) {
      priceLabel = 'Current';
      priceText = `${priceLabel}: $${currentBid.toFixed(0)}`;
    } else if (hasPrebids) {
      priceLabel = 'Pre-bid';
      priceText = `${priceLabel}: $${currentBid.toFixed(0)} (${bidCount} bid${bidCount > 1 ? 's' : ''})`;
    } else {
      priceLabel = 'Starting';
      priceText = `${priceLabel}: $${currentBid.toFixed(0)}`;
    }
    const currentEl = overlayEl.querySelector('.valuator-current');
    currentEl.textContent = priceText;
    currentEl.classList.toggle('price-starting', !isLive && !hasPrebids);
    currentEl.classList.toggle('price-prebid', hasPrebids);
    currentEl.classList.toggle('price-live', isLive);
    
    // FMV - from real Supabase data with grade tiers
    const fmvPrices = overlayEl.querySelectorAll('.fmv-price');
    const verdictEl = overlayEl.querySelector('.valuator-verdict');
    
    // Query real sales data (but not for garbage titles)
    const title = parsed.series || listing.title;
    const issue = parsed.issue;
    
    // Helper to update FMV prices
    const setFmvPrices = (values) => {
      fmvPrices.forEach((el, i) => {
        el.textContent = values[i] || '--';
      });
    };
    
    // Don't query FMV for garbage titles - data would be meaningless
    if (isGarbageTitle(title)) {
      setFmvPrices(['--', '--', '--', '--']);
      verdictEl.textContent = 'Scan needed';
      verdictEl.className = 'valuator-verdict';
    } else {
      // Show loading state
      setFmvPrices(['...', '...', '...', '...']);
      
      let fmvData = null;
      if (window.SupabaseClient && title) {
        fmvData = await window.SupabaseClient.getFMV(title, issue);
      }
      
      if (fmvData && fmvData.count > 0 && fmvData.tiers) {
        const t = fmvData.tiers;
        
        // Update prices - N/A if no data for tier
        setFmvPrices([
          t.low ? `$${t.low.avg}` : 'N/A',
          t.mid ? `$${t.mid.avg}` : 'N/A',
          t.high ? `$${t.high.avg}` : 'N/A',
          t.top ? `$${t.top.avg}` : 'N/A'
        ]);
        
        // Verdict based on current item's grade vs tier
        const currentGrade = parsed.grade || manualGrade;
        let relevantAvg = null;
        
        if (currentGrade) {
          if (currentGrade >= 9.0 && t.top) relevantAvg = t.top.avg;
          else if (currentGrade >= 8.0 && t.high) relevantAvg = t.high.avg;
          else if (currentGrade >= 4.5 && t.mid) relevantAvg = t.mid.avg;
          else if (t.low) relevantAvg = t.low.avg;
        }
        
        if (relevantAvg) {
          if (currentBid < relevantAvg * 0.7) {
            verdictEl.textContent = '🔥 Below Market!';
            verdictEl.className = 'valuator-verdict verdict-great';
          } else if (currentBid < relevantAvg * 0.95) {
            verdictEl.textContent = '👍 Good Price';
            verdictEl.className = 'valuator-verdict verdict-good';
          } else if (currentBid <= relevantAvg * 1.1) {
            verdictEl.textContent = '✅ Fair Price';
            verdictEl.className = 'valuator-verdict verdict-fair';
          } else {
            verdictEl.textContent = '⚠️ Above Market';
            verdictEl.className = 'valuator-verdict verdict-over';
          }
        } else {
          verdictEl.textContent = '';
          verdictEl.className = 'valuator-verdict';
        }
      } else {
        setFmvPrices(['N/A', 'N/A', 'N/A', 'N/A']);
        verdictEl.textContent = '';
        verdictEl.className = 'valuator-verdict';
      }
    }
    
    // eBay link
    const ebayEl = overlayEl.querySelector('.valuator-ebay');
    if (parsed.series && parsed.issue) {
      const query = encodeURIComponent(`${parsed.series} ${parsed.issue} ${parsed.grade || ''}`);
      ebayEl.href = `https://www.ebay.com/sch/i.html?_nkw=${query}&LH_Complete=1&LH_Sold=1`;
      ebayEl.style.display = 'block';
    } else {
      ebayEl.style.display = 'none';
    }
  }

  // Update countdown timer
  function updateTimer(endsAt) {
    const timerEl = overlayEl.querySelector('.valuator-timer');
    const now = Date.now();
    const end = new Date(endsAt).getTime();
    const remaining = Math.max(0, Math.floor((end - now) / 1000));
    
    if (remaining > 0) {
      timerEl.textContent = `⏱️ ${remaining}s`;
      timerEl.style.color = remaining <= 5 ? '#ff4444' : '#ffd700';
    } else {
      timerEl.textContent = '';
    }
  }

  // Check for sale completion
  function checkForSale(listing) {
    // Check footer area for sale indicators
    const footer = document.querySelector('[class*="Footer"]');
    const footerText = footer?.innerText?.toLowerCase() || '';
    const pageText = document.body.innerText.toLowerCase();
    
    // Look for "X won!" pattern or "Sold" in footer
    const hasSaleInFooter = footerText.includes('sold') || /\bwon\b/.test(footerText);
    const hasWinner = pageText.includes(' won!') || pageText.includes(' won\n');
    const hasSale = hasSaleInFooter || hasWinner;

    if (!hasSale) {
      if (consumedSaleSig !== null) {
        console.log('[Valuator] sold text cleared; the next sold text is a new sale');
        consumedSaleSig = null;
      }
      return;
    }

    // 2.46.0 — this sold text already produced a record: ignore it until it changes or clears.
    // Deliberately NOT scoped to the listing id: a banner that persists across a real listing
    // change would otherwise record the next lot at its opening price on the new id. The cost is
    // the documented limit (same winner on consecutive lots with no banner gap registers once).
    const saleSig = saleTextSignature(footerText, pageText);
    const soldListing = previousListing || listing;
    if (!soldListing) return;
    if (consumedSaleSig !== null && saleSig === consumedSaleSig) return;
    
    // DEBOUNCE: Ignore sales within 30 seconds of last recorded sale
    const now = Date.now();
    if (now - lastSaleTime < 30000) {
      // the banner blinked out for a poll and came back inside the debounce: still the same sale
      if (saleSig === lastConsumedSig && soldListing.id === lastSoldListingId) consumedSaleSig = saleSig;
      return; // Too soon, skip
    }
    
    const saleKey = `${soldListing.id}-${soldListing.price}-${soldListing.title}`;
    
    if (saleKey !== lastSaleCheck) {
      console.log('[Valuator] 🎯 Sale detected! Item:', soldListing.title, '(using', previousListing ? 'previous' : 'current', 'listing)');
      lastSaleCheck = saleKey;
      lastSaleTime = now;  // Update debounce timer
      recordTiming(['sale', now, lastSwitchAt ? now - lastSwitchAt : null, previousListing ? 1 : 0,
        shortId(soldListing.id)]);

      // 2.44.0 — vision is used only if it was scanned for the listing that sold
      const vision = visionForSale(soldListing);
      
      const parsed = window.ComicNormalizer ? 
        window.ComicNormalizer.parse(soldListing.title, soldListing.subtitle) : 
        { raw: soldListing.title };
      
      // Extract bid count and viewers from listing
      const bids = soldListing.bidCount || soldListing.bids || null;
      const viewers = soldListing.viewers || null;
      
      // Better title/issue parsing - handles "Black Panther 1" and "Black Panther #1"
      let cleanTitle = parsed.series || soldListing.title || '';
      let issueNum = parsed.issue || null;
      
      // If normalizer didn't find issue, try to parse it ourselves
      if (!issueNum && soldListing.title) {
        // Match "#123" or trailing " 123"
        const issueMatch = soldListing.title.match(/#(\d+)|[^\d](\d+)\s*$/);
        if (issueMatch) {
          issueNum = parseInt(issueMatch[1] || issueMatch[2]);
        }
      }
      
      // Strip issue number from title (both "#123" and trailing " 123")
      if (!parsed.series && soldListing.title) {
        cleanTitle = soldListing.title
          .replace(/#\d+.*$/, '')      // Remove "#123" and anything after
          .replace(/\s+\d+\s*$/, '')   // Remove trailing " 123"
          .trim();
      }
      
      // Detect slab type (CGC, CBCS, PGX, etc.)
      const titleAndCondition = `${soldListing.title || ''} ${soldListing.subtitle || ''}`.toUpperCase();
      let slabType = null;
      if (titleAndCondition.includes('CGC')) slabType = 'CGC';
      else if (titleAndCondition.includes('CBCS')) slabType = 'CBCS';
      else if (titleAndCondition.includes('PGX')) slabType = 'PGX';
      else if (titleAndCondition.includes('SLAB')) slabType = 'slabbed';
      
      // Detect variant type
      let variant = null;
      const variantPatterns = [
        { pattern: /35\s*¢|35\s*CENT/i, value: '35¢ price variant' },
        { pattern: /30\s*¢|30\s*CENT/i, value: '30¢ price variant' },
        { pattern: /NEWSSTAND/i, value: 'newsstand' },
        { pattern: /DIRECT\s*(EDITION)?/i, value: 'direct' },
        { pattern: /VIRGIN/i, value: 'virgin' },
        { pattern: /SKETCH/i, value: 'sketch' },
        { pattern: /RATIO\s*VARIANT|1:\d+/i, value: (m) => m[0].includes(':') ? m[0].match(/1:\d+/)[0] : 'ratio variant' },
        { pattern: /INCENTIVE/i, value: 'incentive' },
        { pattern: /VARIANT\s*COVER|CVR\s*[B-Z]/i, value: 'variant cover' },
        { pattern: /HOMAGE/i, value: 'homage' },
        { pattern: /FACSIMILE/i, value: 'facsimile' },
        { pattern: /REPRINT/i, value: 'reprint' },
        { pattern: /2ND\s*PRINT|SECOND\s*PRINT/i, value: '2nd print' },
        { pattern: /3RD\s*PRINT|THIRD\s*PRINT/i, value: '3rd print' },
      ];
      
      for (const { pattern, value } of variantPatterns) {
        const match = titleAndCondition.match(pattern);
        if (match) {
          variant = typeof value === 'function' ? value(match) : value;
          break;
        }
      }
      
      // Try to extract numeric grade from CGC/CBCS listings (e.g., "CGC 9.8")
      let numericGrade = parsed.grade || manualGrade || null;
      let gradeSource = null;
      
      if (!numericGrade && slabType) {
        const gradeMatch = titleAndCondition.match(/(?:CGC|CBCS|PGX)\s*(\d+\.?\d*)/);
        if (gradeMatch) {
          numericGrade = parseFloat(gradeMatch[1]);
          gradeSource = 'dom';
        }
      }
      
      // Track grade source
      if (numericGrade) {
        if (!gradeSource) {
          // Determine source based on how we got the grade
          if (manualGrade) {
            gradeSource = 'seller_verbal';  // User typed it (probably from seller)
          } else if (vision?.grade) {
            // Vision provided the grade. 2.44.0: was `finalSlabType`, a const declared further
            // down this block — a TDZ ReferenceError that threw away the sale whenever the
            // seller's label carried a grade and vision had one (harness-confirmed 2026-09-15).
            gradeSource = (vision.slabType && vision.slabType !== 'raw') ? 'slab_label' : 'vision_cover';
          } else if (slabType && slabType !== 'raw') {
            gradeSource = 'slab_label';  // From slab
          } else {
            gradeSource = 'dom';  // From condition field
          }
        }
      }
      
      // Prefer Vision data if user clicked "Use This"
      const finalTitle = vision?.title || cleanTitle;
      const finalIssue = vision?.issue || issueNum;
      const finalSlabType = vision?.slabType || slabType;
      const finalVariant = vision?.variant || variant;

      // If grade came from Vision and user applied it
      if (vision?.grade && !manualGrade) {
        numericGrade = vision.grade;
        // Distinguish slab label vs cover-only estimate
        if (vision.slabType && vision.slabType !== 'raw') {
          gradeSource = 'slab_label';  // Vision read it from slab
        } else {
          gradeSource = 'vision_cover';  // Cover-only estimate
        }
      }
      
      const sale = {
        title: finalTitle,
        series: parsed.series || null,
        issue: finalIssue,
        grade: numericGrade,
        gradeSource: gradeSource,
        condition: soldListing.subtitle || null,
        slabType: finalSlabType,
        variant: finalVariant,
        isKey: vision?.isKey || false,
        price: soldListing.price / 100,
        bids: bids,
        viewers: viewers,
        seller: soldListing.seller || null,
        platform: 'whatnot',
        rawTitle: soldListing.title,
        imageDataUrl: vision?.frameData || null,  // Scanned image
        timestamp: Date.now()
      };
      
      // Update Last Scan card with sold price
      const soldEl = overlayEl.querySelector('.last-scan-sold');
      if (soldEl) {
        soldEl.textContent = `SOLD $${sale.price}`;
        soldEl.style.display = 'block';
      }
      
      // Clear vision data after recording. Vision withheld and kept for the current listing
      // (see visionForSale) survives; everything else is spent or already dropped.
      if (appliedVisionData === vision || !(currentListing && appliedVisionData &&
          appliedVisionData.forListingId === currentListing.id)) {
        appliedVisionData = null;
      }

      // Flash overlay green
      console.log('[Valuator] 💚 Flashing green for sale!');
      overlayEl.classList.add('sale-flash');
      setTimeout(() => overlayEl.classList.remove('sale-flash'), 2000);
      
      // Record sale locally
      if (window.SaleTracker) {
        window.SaleTracker.record(sale);
      }
      
      // Push to Supabase (cloud database) - only if valid data
      // Expanded blocklist based on real data analysis
      const badTitles = [
        'bid', 'bids', 'sold', 'won', 'shipping', 'custom', 'awaiting',
        'lot', 'choice', 'pick', 'mystery', 'bundle', 'buck', 'comic book'
      ];
      const titleLower = (sale.title || '').toLowerCase().trim();
      const isValidSale = sale.title && 
                          sale.title.length > 2 && 
                          !badTitles.some(bad => titleLower.includes(bad));
      
      if (window.SupabaseClient && isValidSale) {
        window.SupabaseClient.insertSale(sale);
      } else if (!isValidSale) {
        console.log('[Valuator] ⚠️ Skipped invalid sale:', sale.title);
      }
      
      // Notify background
      chrome.runtime.sendMessage({
        type: 'SALE_RECORDED',
        sale: sale
      }).catch(() => {});
      
      // Update count
      salesCount++;
      const countEl = overlayEl.querySelector('.sale-count');
      if (countEl) countEl.textContent = salesCount;
      
      // Clear previousListing after recording
      previousListing = null;
      previousListingHeldAt = 0;
      lastSoldListingId = soldListing.id;  // 2.45.0
      relistedSinceSale = false;
      consumedSaleSig = saleSig;           // 2.46.0
      lastConsumedSig = saleSig;
      manualGrade = null;  // Reset for next item
      
      console.log('[Valuator] 💰 SALE:', sale);
    }
  }

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Debug interface
  window.ValuatorDebug = {
    // 2.44.0 — drop counters and the switch-to-sale timing ring buffer
    getDropCounts: () => ({ ...dropCounts }),
    getTiming: () => new Promise(resolve => {
      if (timingBuffer) { resolve(timingBuffer.slice()); return; }
      try {
        chrome.storage.local.get([TIMING_KEY], (result) => resolve((result && result[TIMING_KEY]) || []));
      } catch (e) { resolve([]); }
    }),
    getStats: () => {
      return new Promise(resolve => {
        chrome.runtime.sendMessage({ type: 'GET_STATS' }, response => {
          console.log('Stats:', response?.stats);
          resolve(response?.stats);
        });
      });
    },
    getAllSales: () => {
      return new Promise(resolve => {
        chrome.runtime.sendMessage({ type: 'GET_ALL_SALES' }, response => {
          console.log('Sales:', response?.sales);
          resolve(response?.sales);
        });
      });
    },
    download: async () => {
      const response = await new Promise(resolve => {
        chrome.runtime.sendMessage({ type: 'GET_ALL_SALES' }, resolve);
      });
      const sales = response?.sales || [];
      const blob = new Blob([JSON.stringify(sales, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `whatnot-sales-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      console.log(`Downloaded ${sales.length} sales`);
    },
    clearHistory: () => {
      chrome.runtime.sendMessage({ type: 'CLEAR_HISTORY' });
      console.log('History cleared');
    }
  };

})();
