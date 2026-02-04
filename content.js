// eBay Comic Collector - Content Script
// Parses sold comic listings and sends to CollectionCalc

(function() {
  'use strict';

  console.log('eBay Collector: Script starting...');
  console.log('eBay Collector: URL =', window.location.href);

  const API_BASE = 'https://collectioncalc-docker.onrender.com';
  
  // Only run on sold listings pages
  if (!window.location.href.includes('LH_Sold=1') && 
      !window.location.href.includes('LH_Complete=1') &&
      !document.querySelector('.srp-save-null-search__heading')?.textContent?.includes('sold')) {
    console.log('eBay Collector: Not a sold listings page, exiting');
    return;
  }
  
  console.log('eBay Collector: This is a sold listings page, proceeding...');

  // Parse a single listing item
  function parseListingItem(item) {
    try {
      // New eBay structure (2025+)
      const linkEl = item.querySelector('a.s-card__link');
      const imageEl = item.querySelector('img.s-card__image');
      
      // Get title from image alt or link text
      const title = imageEl?.alt || linkEl?.textContent?.trim() || '';
      
      // Get all text content to extract price and date
      const allText = item.innerText || '';
      
      // Extract price - look for $XX.XX pattern
      const priceMatch = allText.match(/\$([0-9,]+\.?\d*)/);
      const price = priceMatch ? parseFloat(priceMatch[1].replace(',', '')) : 0;
      
      // Extract date - "Sold MMM DD, YYYY"
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
      
      // Skip sponsored/ad items that aren't sold listings
      if (!allText.includes('Sold') || allText.startsWith('Shop on eBay')) return null;
      
      // Get listing URL and image
      const listingUrl = linkEl?.href || '';
      const imageUrl = imageEl?.src || '';
      
      // Extract item ID from URL
      const itemIdMatch = listingUrl.match(/\/itm\/(\d+)/);
      const ebayItemId = itemIdMatch ? itemIdMatch[1] : '';
      
      // Parse comic details from title
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

  // Parse comic title to extract details
  function parseComicTitle(title) {
    const result = {
      title: '',
      issue: '',
      publisher: '',
      condition: '',
      graded: false,
      grade: null
    };
    
    // Detect grading
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
    
    // Extract issue number
    const issueMatch = title.match(/#\s*(\d+)/);
    if (issueMatch) {
      result.issue = issueMatch[1];
    }
    
    // Detect publisher
    const publishers = ['Marvel', 'DC', 'Image', 'Dark Horse', 'IDW', 'Valiant', 'Boom', 'Dynamite'];
    for (const pub of publishers) {
      if (title.toLowerCase().includes(pub.toLowerCase())) {
        result.publisher = pub;
        break;
      }
    }
    
    // Clean title
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

  // Collect all sales from the page
  function collectSales() {
    // eBay's current structure uses li.s-card for listing items
    const items = document.querySelectorAll('li.s-card');
    console.log('eBay Collector: Found', items.length, 'items with li.s-card selector');
    
    const sales = [];
    
    items.forEach((item, index) => {
      const parsed = parseListingItem(item);
      if (parsed && parsed.sale_price > 0) {
        sales.push(parsed);
        if (index < 3) {
          console.log('eBay Collector: Parsed item', index, parsed.raw_title?.substring(0, 50));
        }
      }
    });
    
    return sales;
  }

  // Send sales to backend
  async function sendSales(sales) {
    if (sales.length === 0) return { saved: 0, duplicates: 0 };
    
    try {
      const response = await fetch(`${API_BASE}/api/ebay-sales/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ sales })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      return await response.json();
    } catch (e) {
      console.error('Error sending sales:', e);
      return { error: e.message };
    }
  }

  // Show toast notification
  function showToast(message, isError = false) {
    const toast = document.createElement('div');
    toast.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: ${isError ? '#e74c3c' : '#2ecc71'};
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      z-index: 999999;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      animation: slideIn 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.style.animation = 'fadeOut 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  // Add animation styles
  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
    @keyframes fadeOut {
      from { opacity: 1; }
      to { opacity: 0; }
    }
  `;
  document.head.appendChild(style);

  // Main execution
  async function main() {
    // Small delay to ensure page is fully loaded
    await new Promise(r => setTimeout(r, 1000));
    
    const sales = collectSales();
    
    if (sales.length === 0) {
      console.log('eBay Collector: No comic sales found on this page');
      return;
    }
    
    console.log(`eBay Collector: Found ${sales.length} sales`);
    
    // Store locally first
    const stored = await chrome.storage.local.get(['collectedSales', 'totalCollected']);
    const existing = stored.collectedSales || [];
    const existingIds = new Set(existing.map(s => s.ebay_item_id));
    
    const newSales = sales.filter(s => s.ebay_item_id && !existingIds.has(s.ebay_item_id));
    
    if (newSales.length > 0) {
      // Save to local storage
      const updated = [...existing, ...newSales].slice(-500); // Keep last 500
      const totalCollected = (stored.totalCollected || 0) + newSales.length;
      
      await chrome.storage.local.set({ 
        collectedSales: updated,
        totalCollected: totalCollected,
        lastCollection: new Date().toISOString()
      });
      
      // Try to send to backend
      const result = await sendSales(newSales);
      
      if (result.error) {
        showToast(`📊 Saved ${newSales.length} locally (sync later)`, false);
      } else {
        showToast(`📊 Collected ${newSales.length} new sales`, false);
      }
    }
  }

  main();
})();
