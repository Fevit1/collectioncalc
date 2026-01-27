// content.js - Main entry point for Whatnot Comic Valuator
// NO require() or module.exports - pure browser JavaScript

(function() {
  'use strict';

  console.log('[Valuator] 🚀 Initializing Comic Valuator v2.40.2...');
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
          <button class="valuator-settings" title="API Settings">⚙️</button>
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
      <div class="valuator-api-modal" style="display:none;">
        <div class="api-modal-content">
          <h4>🔑 Anthropic API Key</h4>
          <p>For Vision scanning (📷):</p>
          <input type="password" id="api-key-input" placeholder="sk-ant-..." />
          <div class="api-modal-buttons">
            <button id="api-key-save">Save</button>
            <button id="api-key-cancel">Cancel</button>
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
    
    // API key modal
    overlayEl.querySelector('.valuator-settings').addEventListener('click', showApiModal);
    overlayEl.querySelector('#api-key-save').addEventListener('click', saveApiKey);
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
    
    try {
      const result = await window.ComicVision.scan();
      
      if (result.error) {
        statusEl.textContent = '❌ ' + result.error;
        console.log('[Vision] Error:', result.error);
        // Still show the card with error state
        showScanError(result.error, result.frameData);
      } else {
        // Show result in overlay
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
      isFacsimile: result.isFacsimile || false,  // Facsimile edition detection
      grade: result.grade,
      frameData: result.frameData  // Save the scanned image
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

  // Show API key modal
  function showApiModal() {
    const modal = overlayEl.querySelector('.valuator-api-modal');
    modal.style.display = 'flex';
    
    // Load existing key (masked)
    if (window.ComicVision) {
      window.ComicVision.loadApiKey().then(key => {
        if (key) {
          overlayEl.querySelector('#api-key-input').placeholder = 'sk-ant-....' + key.slice(-4);
        }
      });
    }
  }

  // Hide API key modal
  function hideApiModal() {
    overlayEl.querySelector('.valuator-api-modal').style.display = 'none';
  }

  // Save API key
  async function saveApiKey() {
    const input = overlayEl.querySelector('#api-key-input');
    const key = input.value.trim();
    
    if (key && key.startsWith('sk-')) {
      await window.ComicVision.saveApiKey(key);
      input.value = '';
      hideApiModal();
      console.log('[Vision] 🔑 API key saved');
      
      const statusEl = overlayEl.querySelector('.scan-status');
      statusEl.textContent = '🔑 Key saved!';
      setTimeout(() => statusEl.textContent = '', 2000);
    } else {
      input.style.borderColor = '#f44336';
      setTimeout(() => input.style.borderColor = '', 1000);
    }
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
      /^comic\s*#?\d*$/,  // just "Comic" or "Comic #1"
      /^book\s*#?\d*$/,
    ];
    
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

  // Auto-scan when enabled (only when bidding starts, skip if DOM has good data)
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
    
    const scanKey = `${listing.id}-${listing.title}`;
    
    // Already scanned this item
    if (scanKey === lastAutoScanId) return;
    
    // Check if DOM already has good data - seller knows better!
    const parsed = window.ComicNormalizer ? 
      window.ComicNormalizer.parse(listing.title, listing.subtitle) : {};
    
    if (hasGoodDOMData(listing, parsed)) {
      console.log('[Valuator] Auto-scan skipped - DOM has good data:', listing.title);
      return;
    }
    
    // Check for API key
    if (window.ComicVision) {
      const hasKey = await window.ComicVision.hasApiKey();
      if (!hasKey) {
        console.log('[Valuator] Auto-scan skipped - no API key');
        return;
      }
    }
    
    // Check if bidding has started
    if (!isBiddingActive(listing)) {
      // Mark this listing as pending - will scan when bidding starts
      pendingAutoScanKey = scanKey;
      const statusEl = overlayEl.querySelector('.scan-status');
      statusEl.textContent = 'Preparing...';
      console.log('[Valuator] 🕐 Auto-scan queued (waiting for bidding):', listing.title);
      return;
    }
    
    // Bidding is active - scan now!
    lastAutoScanId = scanKey;
    lastScannedListingId = listing.id;  // Track by ID
    lastScanTime = Date.now();
    pendingAutoScanKey = null;
    console.log('[Valuator] 🤖 Auto-scanning (bidding started, DOM is garbage):', listing.title);
    
    // Small delay to let video stabilize on new item
    const statusEl = overlayEl.querySelector('.scan-status');
    statusEl.textContent = 'Preparing...';
    await new Promise(r => setTimeout(r, 1500));
    
    // Trigger scan
    handleVisionScan();
  }
  
  // Check if pending scan should now trigger (bidding started)
  function checkPendingAutoScan(listing) {
    if (!autoScanEnabled) return;
    if (!pendingAutoScanKey) return;
    if (isScanning) return;  // Already scanning
    
    // Make sure we have a video element
    const video = document.querySelector('video');
    if (!video) return;
    
    const scanKey = `${listing.id}-${listing.title}`;
    if (scanKey !== pendingAutoScanKey) return; // Different listing now
    if (scanKey === lastAutoScanId) return; // Already scanned
    
    if (isBiddingActive(listing)) {
      console.log('[Valuator] 🤖 Bidding started - triggering queued auto-scan');
      maybeAutoScan(listing);
    }
  }

  // Watch for auction changes
  let watchCount = 0;
  function startWatching() {
    setInterval(() => {
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
            previousListing = { ...currentListing };
          }
          currentItemId = listingKey;
          currentListing = listing;
          
          // Reset scan tracking for new item
          lastAutoScanId = null;
          pendingAutoScanKey = null;
          isScanning = false;
          
          // Only reset listing ID tracking if the actual ID changed
          if (listingIdChanged) {
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
        
        // Check for sale
        checkForSale(listing);
        
        // Check if pending auto-scan should trigger (bidding started)
        if (listing) {
          checkPendingAutoScan(listing);
        }
        
      } catch (e) {
        console.log('[Valuator] Watch error:', e.message);
      }
    }, 500);
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
    
    if (!hasSale) return;
    
    // DEBOUNCE: Ignore sales within 30 seconds of last recorded sale
    const now = Date.now();
    if (now - lastSaleTime < 30000) {
      return; // Too soon, skip
    }
    
    // Use previousListing if available (the item that just sold)
    // Fall back to current listing if no previous exists
    const soldListing = previousListing || listing;
    if (!soldListing) return;
    
    const saleKey = `${soldListing.id}-${soldListing.price}-${soldListing.title}`;
    
    if (saleKey !== lastSaleCheck) {
      console.log('[Valuator] 🎯 Sale detected! Item:', soldListing.title, '(using', previousListing ? 'previous' : 'current', 'listing)');
      lastSaleCheck = saleKey;
      lastSaleTime = now;  // Update debounce timer
      
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
          } else if (appliedVisionData?.grade) {
            // Vision provided the grade
            gradeSource = (finalSlabType && finalSlabType !== 'raw') ? 'slab_label' : 'vision_cover';
          } else if (slabType && slabType !== 'raw') {
            gradeSource = 'slab_label';  // From slab
          } else {
            gradeSource = 'dom';  // From condition field
          }
        }
      }
      
      // Prefer Vision data if user clicked "Use This"
      const finalTitle = appliedVisionData?.title || cleanTitle;
      const finalIssue = appliedVisionData?.issue || issueNum;
      const finalSlabType = appliedVisionData?.slabType || slabType;
      const finalVariant = appliedVisionData?.variant || variant;
      
      // If grade came from Vision and user applied it
      if (appliedVisionData?.grade && !manualGrade) {
        numericGrade = appliedVisionData.grade;
        // Distinguish slab label vs cover-only estimate
        if (appliedVisionData.slabType && appliedVisionData.slabType !== 'raw') {
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
        isKey: appliedVisionData?.isKey || false,
        isFacsimile: appliedVisionData?.isFacsimile || false,
        price: soldListing.price / 100,
        bids: bids,
        viewers: viewers,
        seller: soldListing.seller || null,
        platform: 'whatnot',
        rawTitle: soldListing.title,
        imageDataUrl: appliedVisionData?.frameData || null,  // Scanned image
        timestamp: Date.now()
      };
      
      // Update Last Scan card with sold price
      const soldEl = overlayEl.querySelector('.last-scan-sold');
      if (soldEl) {
        soldEl.textContent = `SOLD $${sale.price}`;
        soldEl.style.display = 'block';
      }
      
      // Clear vision data after recording
      appliedVisionData = null;
      
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
