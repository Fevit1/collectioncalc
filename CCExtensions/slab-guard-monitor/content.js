/**
 * Slab Guard Monitor - Content Script
 * Injected into eBay search results and item pages.
 *
 * Features:
 * - Auto-scan: checks listing images against Slab Guard registry on search pages
 * - Manual check: floating "Check with Slab Guard" button on item pages
 * - Visual overlays: shield badges on matched listings
 */

(function () {
  'use strict';

  console.log('Slab Guard Monitor: Content script loaded');

  const SCAN_THROTTLE_MS = 600;  // delay between API checks
  const MAX_AUTO_SCANS = 15;     // max listings to auto-check per page

  // Track what we've already checked
  const checkedImages = new Set();
  let scanInProgress = false;

  // ============================================================
  // UTILITY: Detect page type
  // ============================================================

  function isSearchPage() {
    return window.location.pathname.startsWith('/sch/');
  }

  function isItemPage() {
    return window.location.pathname.startsWith('/itm/');
  }

  // ============================================================
  // UTILITY: Send message to background
  // ============================================================

  function sendMessage(action, data = {}) {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ action, data }, (response) => {
        resolve(response || { error: 'No response' });
      });
    });
  }

  // ============================================================
  // UTILITY: Create shield badge element
  // ============================================================

  function createShieldBadge(alertLevel, text, tooltip) {
    const badge = document.createElement('div');
    badge.className = 'sg-shield-badge';

    const colors = {
      critical: { bg: '#dc2626', border: '#991b1b', icon: '\u{1F6A8}' },  // red - stolen
      high:     { bg: '#ea580c', border: '#9a3412', icon: '\u{26A0}\u{FE0F}' },   // orange - high match
      medium:   { bg: '#eab308', border: '#a16207', icon: '\u{1F50D}' },  // yellow - possible
      low:      { bg: '#6b7280', border: '#4b5563', icon: '\u{2139}\u{FE0F}' },   // gray - weak
      verified: { bg: '#16a34a', border: '#15803d', icon: '\u{2705}' },  // green - registered (not stolen)
      clear:    { bg: '#667eea', border: '#5a67d8', icon: '\u{1F6E1}\u{FE0F}' }   // blue - checked, no match
    };

    const color = colors[alertLevel] || colors.clear;

    badge.style.cssText = `
      position: absolute;
      top: 8px;
      left: 8px;
      background: ${color.bg};
      border: 2px solid ${color.border};
      color: white;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      z-index: 10000;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      display: flex;
      align-items: center;
      gap: 4px;
      line-height: 1;
      white-space: nowrap;
    `;

    badge.innerHTML = `<span>${color.icon}</span><span>${text}</span>`;
    badge.title = tooltip;

    return badge;
  }

  // ============================================================
  // UTILITY: Show toast
  // ============================================================

  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    const bg = type === 'error' ? '#dc2626'
      : type === 'warning' ? '#ea580c'
      : type === 'success' ? '#16a34a'
      : '#667eea';

    toast.style.cssText = `
      position: fixed;
      bottom: 80px;
      right: 20px;
      background: ${bg};
      color: white;
      padding: 12px 20px;
      border-radius: 10px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      font-weight: 500;
      z-index: 999999;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
      animation: sgSlideIn 0.3s ease;
      max-width: 350px;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // ============================================================
  // AUTO-SCAN: Search results pages
  // ============================================================

  async function autoScanSearchResults() {
    // Check if auto-scan is enabled
    const settings = await sendMessage('getSettings');
    if (!settings.autoScanEnabled) {
      console.log('Slab Guard: Auto-scan disabled');
      return;
    }

    if (scanInProgress) return;
    scanInProgress = true;

    console.log('Slab Guard: Starting auto-scan of search results...');
    showToast('\u{1F6E1}\u{FE0F} Slab Guard scanning listings...', 'info');

    // Find listing cards (eBay 2025+ structure)
    const items = document.querySelectorAll('li.s-card');
    console.log(`Slab Guard: Found ${items.length} listing cards`);

    let scanned = 0;
    let matchesFound = 0;

    for (const item of items) {
      if (scanned >= MAX_AUTO_SCANS) break;

      const imageEl = item.querySelector('img.s-card__image') || item.querySelector('img');
      if (!imageEl || !imageEl.src) continue;

      const imageUrl = imageEl.src;

      // Skip if already checked or if it's a placeholder/tiny image
      if (checkedImages.has(imageUrl)) continue;
      if (imageUrl.includes('s-l64') || imageUrl.includes('s-l96')) continue;

      // Get a higher-res version of the image
      const hiResUrl = imageUrl
        .replace(/s-l\d+/, 's-l500')
        .replace(/s-l\d+\./, 's-l500.');

      checkedImages.add(imageUrl);
      scanned++;

      // Throttle requests
      await new Promise(r => setTimeout(r, SCAN_THROTTLE_MS));

      try {
        const result = await sendMessage('checkImage', {
          imageUrl: hiResUrl,
          stolenOnly: false
        });

        if (result.success && result.match_count > 0) {
          const topMatch = result.matches[0];
          matchesFound++;

          // Make the listing card position relative for badge overlay
          const cardContainer = imageEl.closest('.s-card__image-wrapper') || imageEl.parentElement;
          if (cardContainer) {
            cardContainer.style.position = 'relative';

            let alertLevel, badgeText, tooltip;

            if (topMatch.status === 'reported_stolen') {
              alertLevel = topMatch.alert_level === 'critical' ? 'critical' : 'high';
              badgeText = 'STOLEN';
              tooltip = `Reported stolen! ${topMatch.comic.title} #${topMatch.comic.issue_number} (${topMatch.confidence}% match)`;
            } else {
              alertLevel = 'verified';
              badgeText = 'Registered';
              tooltip = `Registered: ${topMatch.comic.title} #${topMatch.comic.issue_number} (${topMatch.serial_number})`;
            }

            const badge = createShieldBadge(alertLevel, badgeText, tooltip);

            // Click badge to see details
            badge.addEventListener('click', (e) => {
              e.preventDefault();
              e.stopPropagation();
              showMatchPanel(topMatch, hiResUrl);
            });

            cardContainer.appendChild(badge);
          }
        }
      } catch (e) {
        console.error('Slab Guard: Scan error for item:', e);
      }
    }

    scanInProgress = false;

    if (matchesFound > 0) {
      showToast(`\u{1F6E1}\u{FE0F} Found ${matchesFound} registered comic(s)!`, matchesFound > 0 ? 'warning' : 'info');
    } else {
      showToast(`\u{1F6E1}\u{FE0F} Scanned ${scanned} listings \u{2014} no matches`, 'info');
    }
  }

  // ============================================================
  // MANUAL CHECK: Item page button
  // ============================================================

  function injectCheckButton() {
    // Don't inject twice
    if (document.getElementById('sg-check-button')) return;

    const btn = document.createElement('button');
    btn.id = 'sg-check-button';
    btn.innerHTML = '\u{1F6E1}\u{FE0F} Check with Slab Guard';
    btn.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: none;
      padding: 14px 24px;
      border-radius: 12px;
      font-size: 15px;
      font-weight: 700;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      cursor: pointer;
      z-index: 999999;
      box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 8px;
    `;

    btn.addEventListener('mouseenter', () => {
      btn.style.transform = 'scale(1.05)';
      btn.style.boxShadow = '0 6px 25px rgba(102, 126, 234, 0.6)';
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.transform = 'scale(1)';
      btn.style.boxShadow = '0 4px 20px rgba(102, 126, 234, 0.4)';
    });

    btn.addEventListener('click', handleManualCheck);
    document.body.appendChild(btn);
  }

  async function handleManualCheck() {
    const btn = document.getElementById('sg-check-button');
    const originalText = btn.innerHTML;
    btn.innerHTML = '\u{1F504} Checking...';
    btn.disabled = true;
    btn.style.opacity = '0.7';

    try {
      // Find the main listing image
      const mainImage = getMainListingImage();
      if (!mainImage) {
        showToast('Could not find listing image', 'error');
        return;
      }

      console.log('Slab Guard: Checking image:', mainImage);

      const result = await sendMessage('checkImage', {
        imageUrl: mainImage,
        stolenOnly: false
      });

      if (!result.success) {
        showToast(`Check failed: ${result.error}`, 'error');
        return;
      }

      if (result.match_count === 0) {
        showToast('Not found in Slab Guard registry', 'info');
        showNoMatchPanel();
      } else {
        const topMatch = result.matches[0];
        if (topMatch.status === 'reported_stolen') {
          showToast(`\u{1F6A8} ALERT: This comic is REPORTED STOLEN!`, 'error');
        } else {
          showToast(`\u{2705} This comic is registered with Slab Guard`, 'success');
        }
        showMatchPanel(topMatch, mainImage);
      }
    } catch (e) {
      console.error('Slab Guard: Manual check error:', e);
      showToast('Check failed. Please try again.', 'error');
    } finally {
      btn.innerHTML = originalText;
      btn.disabled = false;
      btn.style.opacity = '1';
    }
  }

  function getMainListingImage() {
    // eBay item page: find the main/hero image
    // Try various selectors for different eBay layouts
    const selectors = [
      '.ux-image-magnify__image--original',  // magnified view
      '.ux-image-carousel-item img',          // carousel
      '#icImg',                                // classic layout
      '.mainImgHldr img',                      // older layout
      'img[data-zoom-src]',                    // zoom-capable images
      '.ux-image-filmstrip-carousel-item img', // filmstrip
      'img.s-card__image'                      // card view
    ];

    for (const sel of selectors) {
      const img = document.querySelector(sel);
      if (img) {
        // Prefer data-zoom-src (highest quality) or src
        const url = img.getAttribute('data-zoom-src') || img.src;
        if (url && url.startsWith('http')) return url;
      }
    }

    return null;
  }

  // ============================================================
  // MATCH RESULT PANELS
  // ============================================================

  function showMatchPanel(match, listingImageUrl) {
    // Remove existing panel
    const existing = document.getElementById('sg-match-panel');
    if (existing) existing.remove();

    const isStolen = match.status === 'reported_stolen';
    const borderColor = isStolen ? '#dc2626' : '#16a34a';
    const statusBg = isStolen ? '#fef2f2' : '#f0fdf4';
    const statusColor = isStolen ? '#dc2626' : '#16a34a';
    const statusText = isStolen ? '\u{1F6A8} REPORTED STOLEN' : '\u{2705} REGISTERED';

    const panel = document.createElement('div');
    panel.id = 'sg-match-panel';
    panel.style.cssText = `
      position: fixed;
      top: 50%;
      right: 20px;
      transform: translateY(-50%);
      width: 360px;
      background: white;
      border: 3px solid ${borderColor};
      border-radius: 16px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
      z-index: 1000000;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      animation: sgSlideIn 0.3s ease;
      overflow: hidden;
    `;

    panel.innerHTML = `
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 16px 20px; color: white; display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 20px;">\u{1F6E1}\u{FE0F}</span>
          <span style="font-weight: 700; font-size: 16px;">Slab Guard</span>
        </div>
        <button id="sg-close-panel" style="background: none; border: none; color: white; font-size: 20px; cursor: pointer; padding: 0 4px;">&times;</button>
      </div>

      <div style="background: ${statusBg}; padding: 12px 20px; border-bottom: 1px solid ${borderColor}20;">
        <div style="color: ${statusColor}; font-weight: 800; font-size: 15px;">${statusText}</div>
      </div>

      <div style="padding: 20px;">
        <div style="margin-bottom: 16px;">
          <div style="font-size: 11px; text-transform: uppercase; color: #9ca3af; font-weight: 600; letter-spacing: 0.5px;">Comic</div>
          <div style="font-size: 16px; font-weight: 700; color: #1f2937; margin-top: 2px;">
            ${match.comic.title || 'Unknown'} #${match.comic.issue_number || '?'}
          </div>
          ${match.comic.publisher ? `<div style="font-size: 13px; color: #6b7280;">${match.comic.publisher}</div>` : ''}
          ${match.comic.grade ? `<div style="font-size: 13px; color: #6b7280;">Grade: ${match.comic.grade}</div>` : ''}
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
          <div>
            <div style="font-size: 11px; text-transform: uppercase; color: #9ca3af; font-weight: 600;">Serial</div>
            <div style="font-size: 14px; font-weight: 600; color: #667eea;">${match.serial_number}</div>
          </div>
          <div>
            <div style="font-size: 11px; text-transform: uppercase; color: #9ca3af; font-weight: 600;">Match</div>
            <div style="font-size: 14px; font-weight: 600; color: ${match.confidence >= 90 ? '#dc2626' : match.confidence >= 70 ? '#ea580c' : '#6b7280'};">${match.confidence}%</div>
          </div>
          <div>
            <div style="font-size: 11px; text-transform: uppercase; color: #9ca3af; font-weight: 600;">Owner</div>
            <div style="font-size: 13px; color: #374151;">${match.owner_display}</div>
          </div>
          <div>
            <div style="font-size: 11px; text-transform: uppercase; color: #9ca3af; font-weight: 600;">Registered</div>
            <div style="font-size: 13px; color: #374151;">${match.registration_date ? new Date(match.registration_date).toLocaleDateString() : 'N/A'}</div>
          </div>
        </div>

        ${isStolen ? `
        <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 12px; margin-bottom: 16px;">
          <div style="font-size: 12px; font-weight: 600; color: #dc2626; margin-bottom: 4px;">Reported Stolen</div>
          <div style="font-size: 12px; color: #7f1d1d;">
            ${match.reported_stolen_date ? new Date(match.reported_stolen_date).toLocaleDateString() : 'Date unknown'}
          </div>
        </div>
        ` : ''}

        <div style="display: flex; flex-direction: column; gap: 8px;">
          <div style="display: flex; gap: 8px;">
            ${isStolen ? `
            <button id="sg-report-btn" style="flex: 1; background: #dc2626; color: white; border: none; padding: 10px; border-radius: 8px; font-weight: 700; font-size: 13px; cursor: pointer;">
              \u{1F6A8} Report This Match
            </button>
            ` : ''}
            <a href="https://slabworthy.com/verify" target="_blank" style="flex: 1; display: block; text-align: center; background: #f3f4f6; color: #374151; text-decoration: none; padding: 10px; border-radius: 8px; font-weight: 600; font-size: 13px;">
              Verify on SlabWorthy
            </a>
          </div>
          <button id="sg-sighting-btn" style="width: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 10px; border-radius: 8px; font-weight: 700; font-size: 13px; cursor: pointer;">
            \u{1F4E8} Report to Owner
          </button>
        </div>
      </div>

      <div style="background: #f9fafb; padding: 8px 20px; border-top: 1px solid #e5e7eb;">
        <div style="font-size: 11px; color: #9ca3af; text-align: center;">
          Slab Guard\u2122 by SlabWorthy.com
        </div>
      </div>
    `;

    document.body.appendChild(panel);

    // Close button
    document.getElementById('sg-close-panel').addEventListener('click', () => panel.remove());

    // Report button (internal match report for stolen comics)
    const reportBtn = document.getElementById('sg-report-btn');
    if (reportBtn) {
      reportBtn.addEventListener('click', async () => {
        reportBtn.textContent = 'Reporting...';
        reportBtn.disabled = true;

        const result = await sendMessage('reportMatch', {
          serial_number: match.serial_number,
          listing_url: window.location.href,
          ebay_item_id: extractEbayItemId(),
          listing_image_url: listingImageUrl,
          confidence: match.confidence,
          hamming_distance: match.hamming_distance,
          marketplace: 'ebay'
        });

        if (result.success) {
          reportBtn.textContent = '\u{2705} Reported!';
          reportBtn.style.background = '#16a34a';
          showToast('Match reported! The owner will be notified.', 'success');
        } else {
          reportBtn.textContent = 'Failed - try again';
          reportBtn.disabled = false;
          showToast(result.error || 'Report failed', 'error');
        }
      });
    }

    // Report to Owner button (sighting alert via email)
    const sightingBtn = document.getElementById('sg-sighting-btn');
    if (sightingBtn) {
      sightingBtn.addEventListener('click', async () => {
        sightingBtn.textContent = '\u{1F4E8} Sending alert...';
        sightingBtn.disabled = true;
        sightingBtn.style.opacity = '0.7';

        const result = await sendMessage('reportSighting', {
          serial_number: match.serial_number,
          listing_url: window.location.href,
          message: `Spotted on eBay: ${document.title}`
        });

        if (result.success) {
          sightingBtn.textContent = '\u{2705} Owner notified!';
          sightingBtn.style.background = '#16a34a';
          showToast('The registered owner has been alerted about this listing.', 'success');
        } else {
          sightingBtn.textContent = '\u{274C} ' + (result.error || 'Failed');
          sightingBtn.style.background = '#dc2626';
          setTimeout(() => {
            sightingBtn.textContent = '\u{1F4E8} Report to Owner';
            sightingBtn.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
            sightingBtn.disabled = false;
            sightingBtn.style.opacity = '1';
          }, 3000);
          showToast(result.error || 'Could not alert the owner. Please try again.', 'error');
        }
      });
    }
  }

  function showNoMatchPanel() {
    const existing = document.getElementById('sg-match-panel');
    if (existing) existing.remove();

    const panel = document.createElement('div');
    panel.id = 'sg-match-panel';
    panel.style.cssText = `
      position: fixed;
      top: 50%;
      right: 20px;
      transform: translateY(-50%);
      width: 320px;
      background: white;
      border: 2px solid #667eea;
      border-radius: 16px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
      z-index: 1000000;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      animation: sgSlideIn 0.3s ease;
      overflow: hidden;
    `;

    panel.innerHTML = `
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 16px 20px; color: white; display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 20px;">\u{1F6E1}\u{FE0F}</span>
          <span style="font-weight: 700; font-size: 16px;">Slab Guard</span>
        </div>
        <button id="sg-close-panel" style="background: none; border: none; color: white; font-size: 20px; cursor: pointer;">&times;</button>
      </div>
      <div style="padding: 30px 20px; text-align: center;">
        <div style="font-size: 40px; margin-bottom: 12px;">\u{1F6E1}\u{FE0F}</div>
        <div style="font-size: 16px; font-weight: 700; color: #374151; margin-bottom: 8px;">Not Found</div>
        <div style="font-size: 13px; color: #6b7280; line-height: 1.5;">
          This comic is not currently registered in the Slab Guard registry.
        </div>
      </div>
      <div style="background: #f9fafb; padding: 8px 20px; border-top: 1px solid #e5e7eb;">
        <div style="font-size: 11px; color: #9ca3af; text-align: center;">Slab Guard\u2122 by SlabWorthy.com</div>
      </div>
    `;

    document.body.appendChild(panel);
    document.getElementById('sg-close-panel').addEventListener('click', () => panel.remove());

    // Auto-close after 8 seconds
    setTimeout(() => { if (panel.parentNode) panel.remove(); }, 8000);
  }

  // ============================================================
  // HELPERS
  // ============================================================

  function extractEbayItemId() {
    const match = window.location.pathname.match(/\/itm\/(\d+)/);
    return match ? match[1] : null;
  }

  // ============================================================
  // INITIALIZATION
  // ============================================================

  async function init() {
    // Small delay to let page render
    await new Promise(r => setTimeout(r, 1500));

    if (isSearchPage()) {
      console.log('Slab Guard: Search page detected, starting auto-scan');
      autoScanSearchResults();
    }

    if (isItemPage()) {
      console.log('Slab Guard: Item page detected, injecting check button');
      injectCheckButton();
    }
  }

  init();
})();
