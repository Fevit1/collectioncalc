// eBay Comic Collector - Content Script v2
// Auto-collects sold comic listings and syncs to backend
// Human drives the browser (search, click next), extension does the rest

(function() {
  'use strict';

  const API_BASE = 'https://collectioncalc-docker.onrender.com';
  const BANNER_ID = 'sw-collector-banner';

  // Only run on sold listings pages
  if (!window.location.href.includes('LH_Sold=1') &&
      !window.location.href.includes('LH_Complete=1') &&
      !document.querySelector('.srp-save-null-search__heading')?.textContent?.includes('sold')) {
    return;
  }

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

    // Push page content down so banner doesn't overlap
    document.body.style.marginTop = '44px';

    // Dismiss button minimizes to a small indicator
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
      const { newCount, dupeCount, totalOnPage, pageInfo, sessionTotal } = opts.stats;
      let statsHtml = '';

      if (newCount !== undefined) {
        statsHtml += `<span class="sw-stat"><span class="sw-stat-num">${newCount}</span> new</span>`;
      }
      if (dupeCount !== undefined && dupeCount > 0) {
        statsHtml += `<span class="sw-stat"><span class="sw-stat-num">${dupeCount}</span> dupes</span>`;
      }
      if (totalOnPage !== undefined) {
        statsHtml += `<span class="sw-stat"><span class="sw-stat-num">${totalOnPage}</span> on page</span>`;
      }
      if (sessionTotal !== undefined) {
        statsHtml += `<span class="sw-stat">|</span><span class="sw-stat"><span class="sw-stat-num">${sessionTotal}</span> session total</span>`;
      }
      if (pageInfo) {
        statsHtml += `<span class="sw-page-info">${pageInfo}</span>`;
      }

      statsEl.innerHTML = statsHtml;
    }
  }


  // ─── Pagination detection ───

  function getPageInfo() {
    // eBay shows "Page X of Y" or pagination nav
    const paginationText = document.querySelector('.srp-controls__count-heading')?.textContent || '';

    // Try to detect "X,XXX+ results" pattern
    const resultsMatch = paginationText.match(/([\d,]+)\+?\s*results/i);
    const totalResults = resultsMatch ? parseInt(resultsMatch[1].replace(',', '')) : null;

    // Check for pagination nav - eBay uses <nav> with page buttons
    const pageButtons = document.querySelectorAll('nav.pagination a, .pagination__items a');
    const currentPage = document.querySelector('nav.pagination .pagination__item--current, .pagination__items .pagination__item--current');

    let currentPageNum = 1;
    let totalPages = 1;

    if (currentPage) {
      currentPageNum = parseInt(currentPage.textContent) || 1;
    }

    // Find the highest page number in pagination
    pageButtons.forEach(btn => {
      const num = parseInt(btn.textContent);
      if (!isNaN(num) && num > totalPages) {
        totalPages = num;
      }
    });

    // Also check the eBay URL for page param
    const urlPageMatch = window.location.href.match(/[&?]_pgn=(\d+)/);
    if (urlPageMatch) {
      currentPageNum = parseInt(urlPageMatch[1]);
    }

    return { currentPageNum, totalPages, totalResults };
  }


  // ─── Parse a single listing item ───

  function parseListingItem(item) {
    try {
      const linkEl = item.querySelector('a.s-card__link');
      const imageEl = item.querySelector('img.s-card__image');

      const title = imageEl?.alt || linkEl?.textContent?.trim() || '';
      const allText = item.innerText || '';

      // Extract price
      const priceMatch = allText.match(/\$([0-9,]+\.?\d*)/);
      const price = priceMatch ? parseFloat(priceMatch[1].replace(',', '')) : 0;

      // Extract date
      let saleDate = new Date().toISOString().split('T')[0];
      const dateMatch = allText.match(/Sold\s+(\w{3})\s+(\d{1,2}),?\s*(\d{4})?/i);
      if (dateMatch) {
        const months = { Jan:0, Feb:1, Mar:2, Apr:3, May:4, Jun:5, Jul:6, Aug:7, Sep:8, Oct:9, Nov:10, Dec:11 };
        const month = months[dateMatch[1]];
        const day = parseInt(dateMatch[2]);
        const year = dateMatch[3] ? parseInt(dateMatch[3]) : new Date().getFullYear();
        if (month !== undefined) {
          saleDate = new Date(year, month, day).toISOString().split('T')[0];
        }
      }

      if (!title || price <= 0) return null;
      if (!allText.includes('Sold') || allText.startsWith('Shop on eBay')) return null;

      const listingUrl = linkEl?.href || '';
      const imageUrl = imageEl?.src || '';

      const itemIdMatch = listingUrl.match(/\/itm\/(\d+)/);
      const ebayItemId = itemIdMatch ? itemIdMatch[1] : '';

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
    const result = {
      title: '',
      issue: '',
      publisher: '',
      condition: '',
      graded: false,
      grade: null
    };

    const cgcMatch = title.match(/CGC\s+([\d.]+)/i);
    const cbcsMatch = title.match(/CBCS\s+([\d.]+)/i);
    if (cgcMatch) {
      result.graded = true;
      result.grade = parseFloat(cgcMatch[1]);
      result.condition = `CGC ${cgcMatch[1]}`;
    } else if (cbcsMatch) {
      result.graded = true;
      result.grade = parseFloat(cbcsMatch[1]);
      result.condition = `CBCS ${cbcsMatch[1]}`;
    }

    const issueMatch = title.match(/#\s*(\d+)/);
    if (issueMatch) {
      result.issue = issueMatch[1];
    }

    const publishers = ['Marvel', 'DC', 'Image', 'Dark Horse', 'IDW', 'Valiant', 'Boom', 'Dynamite'];
    for (const pub of publishers) {
      if (title.toLowerCase().includes(pub.toLowerCase())) {
        result.publisher = pub;
        break;
      }
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
    const items = document.querySelectorAll('li.s-card');
    const sales = [];

    items.forEach(item => {
      const parsed = parseListingItem(item);
      if (parsed && parsed.sale_price > 0) {
        sales.push(parsed);
      }
    });

    return sales;
  }


  // ─── Send sales to backend ───

  async function sendSales(sales) {
    if (sales.length === 0) return { saved: 0, duplicates: 0 };

    try {
      const response = await fetch(`${API_BASE}/api/ebay-sales/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sales })
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (e) {
      console.error('eBay Collector: Sync error:', e);
      return { error: e.message };
    }
  }



  // ─── Main execution ───

  async function main() {
    // Create the banner immediately
    createBanner();
    updateBanner({ status: '⏳ Scanning page...', collecting: true });

    // Small delay to ensure page is fully rendered
    await new Promise(r => setTimeout(r, 1500));

    // Collect sales from the page
    const sales = collectSales();
    const pageInfo = getPageInfo();

    if (sales.length === 0) {
      updateBanner({
        status: '⚠️ No comic sales found on this page',
        stats: { totalOnPage: 0 }
      });
      return;
    }

    // Check against local storage for deduplication
    const stored = await chrome.storage.local.get(['collectedSales', 'totalCollected', 'sessionCollected']);
    const existing = stored.collectedSales || [];
    const existingIds = new Set(existing.map(s => s.ebay_item_id));

    const newSales = sales.filter(s => s.ebay_item_id && !existingIds.has(s.ebay_item_id));
    const dupeCount = sales.length - newSales.length;

    // Update banner to show we're syncing
    updateBanner({
      status: '📡 Syncing to backend...',
      collecting: true,
      stats: {
        newCount: newSales.length,
        dupeCount,
        totalOnPage: sales.length
      }
    });

    if (newSales.length > 0) {
      // Save to local storage
      const updated = [...existing, ...newSales].slice(-1000); // Keep last 1000 (was 500)
      const totalCollected = (stored.totalCollected || 0) + newSales.length;
      const sessionCollected = (stored.sessionCollected || 0) + newSales.length;

      await chrome.storage.local.set({
        collectedSales: updated,
        totalCollected,
        sessionCollected,
        lastCollection: new Date().toISOString()
      });

      // Auto-sync to backend
      const result = await sendSales(newSales);

      // Build page info string
      let pageInfoStr = null;
      if (pageInfo.totalPages > 1) {
        pageInfoStr = `Page ${pageInfo.currentPageNum} of ${pageInfo.totalPages}`;
        if (pageInfo.currentPageNum < pageInfo.totalPages) {
          pageInfoStr += ' — click Next →';
        } else {
          pageInfoStr += ' — last page ✓';
        }
      }

      if (result.error) {
        updateBanner({
          status: `💾 ${newSales.length} saved locally (backend offline)`,
          stats: {
            newCount: newSales.length,
            dupeCount,
            totalOnPage: sales.length,
            sessionTotal: sessionCollected,
            pageInfo: pageInfoStr
          }
        });
      } else {
        updateBanner({
          status: `✅ ${newSales.length} new sales synced`,
          stats: {
            newCount: result.saved || newSales.length,
            dupeCount: (result.duplicates || 0) + dupeCount,
            totalOnPage: sales.length,
            sessionTotal: sessionCollected,
            pageInfo: pageInfoStr
          }
        });

      }
    } else {
      // All duplicates - this title might be "mined out" on this page
      let pageInfoStr = null;
      if (pageInfo.totalPages > 1) {
        pageInfoStr = `Page ${pageInfo.currentPageNum} of ${pageInfo.totalPages}`;
      }

      const sessionCollected = stored.sessionCollected || 0;

      updateBanner({
        status: '📋 All listings already collected',
        stats: {
          newCount: 0,
          dupeCount: sales.length,
          totalOnPage: sales.length,
          sessionTotal: sessionCollected,
          pageInfo: pageInfoStr
        }
      });
    }
  }

  main();
})();
