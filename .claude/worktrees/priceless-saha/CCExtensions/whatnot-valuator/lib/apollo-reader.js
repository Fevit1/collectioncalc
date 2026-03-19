// lib/apollo-reader.js - Extract data from Whatnot's Apollo GraphQL cache
// NO require() or module.exports - uses window global

window.ApolloReader = (function() {
  'use strict';

  let cachedData = null;
  let lastFetch = 0;
  let bridgeReady = false;
  
  // Inject the page-context script via src (bypasses CSP)
  function injectBridge() {
    if (document.getElementById('valuator-inject')) return;
    
    const script = document.createElement('script');
    script.id = 'valuator-inject';
    script.src = chrome.runtime.getURL('inject.js');
    script.onload = () => {
      bridgeReady = true;
      console.log('[ApolloReader] Bridge script loaded');
    };
    script.onerror = (e) => {
      console.log('[ApolloReader] Bridge script failed to load:', e);
    };
    (document.head || document.documentElement).appendChild(script);
  }
  
  // Request data from page context via CustomEvent
  function requestData() {
    return new Promise((resolve) => {
      const eventId = 'apollo-data-' + Date.now() + '-' + Math.random();
      
      const handler = (e) => {
        if (e.detail && e.detail.eventId === eventId) {
          document.removeEventListener('apolloDataResponse', handler);
          resolve(e.detail.data);
        }
      };
      document.addEventListener('apolloDataResponse', handler);
      
      // Send request to page context
      document.dispatchEvent(new CustomEvent('apolloDataRequest', {
        detail: { eventId: eventId }
      }));
      
      // Timeout fallback
      setTimeout(() => {
        document.removeEventListener('apolloDataResponse', handler);
        resolve(null);
      }, 300);
    });
  }

  // Get the Apollo cache (with caching to reduce requests)
  async function getCache() {
    const now = Date.now();
    // Refresh cache every 400ms
    if (cachedData && (now - lastFetch) < 400) {
      return cachedData;
    }
    
    if (!bridgeReady) {
      injectBridge();
      return cachedData; // Return old cache while bridge loads
    }
    
    try {
      const jsonData = await requestData();
      if (jsonData) {
        cachedData = JSON.parse(jsonData);
        lastFetch = now;
      }
      return cachedData;
    } catch (e) {
      console.log('[ApolloReader] Cache access error:', e.message);
      return cachedData;
    }
  }
  
  // Synchronous version using last cached data
  function getCacheSync() {
    return cachedData;
  }

  // Find current active listing (sync version using cached data)
  function getCurrentListing() {
    const cache = getCacheSync();
    
    // First try to get real title from DOM (the auction bar)
    const domInfo = getAuctionInfoFromDOM();
    
    if (!cache) {
      getCache(); // Trigger refresh
      // If we have DOM info, return that
      if (domInfo) {
        return {
          id: 'dom-' + Date.now(),
          title: domInfo.title,
          subtitle: domInfo.condition || '',
          price: domInfo.price || 0,
          bidCount: domInfo.bids || 0,
          viewers: domInfo.viewers || null,
          seller: domInfo.seller || null,
          endsAt: null,
          isLive: true,
          fromDOM: true
        };
      }
      return null;
    }

    try {
      // Look for ListingNode entries
      const listingKeys = Object.keys(cache).filter(k => 
        k.includes('ListingNode') || k.includes('Listing:')
      );

      if (listingKeys.length === 0) {
        // Fallback to DOM if no cache
        if (domInfo) {
          return {
            id: 'dom-' + Date.now(),
            title: domInfo.title,
            subtitle: domInfo.condition || '',
            price: domInfo.price || 0,
            bidCount: domInfo.bids || 0,
            viewers: domInfo.viewers || null,
            seller: domInfo.seller || null,
            endsAt: null,
            isLive: true,
            fromDOM: true
          };
        }
        return null;
      }

      // Find the most recently updated listing by updatedAtMs
      let bestListing = null;
      let bestTimestamp = 0;

      for (const key of listingKeys) {
        const listing = cache[key];
        if (!listing || !listing.title) continue;
        
        // Skip if it's clearly sold/ended
        if (listing.publicStatus === 'ENDED' || listing.publicStatus === 'SOLD') continue;

        const timestamp = listing.updatedAtMs || 0;
        
        if (timestamp > bestTimestamp) {
          bestTimestamp = timestamp;
          bestListing = listing;
        }
      }
      
      // Fallback: if no timestamps, get first active one
      if (!bestListing) {
        for (const key of listingKeys) {
          const listing = cache[key];
          if (listing && listing.title && listing.publicStatus !== 'ENDED') {
            bestListing = listing;
            break;
          }
        }
      }

      if (!bestListing) return null;
      
      // Merge DOM info if available (DOM has real auction item title)
      const normalized = normalizeListing(bestListing);
      if (domInfo && domInfo.title) {
        normalized.title = domInfo.title;
        normalized.subtitle = domInfo.condition || normalized.subtitle;
        if (domInfo.price) normalized.price = domInfo.price;
        normalized.fromDOM = true;
      }
      
      return normalized;
    } catch (e) {
      console.log('[ApolloReader] Parse error:', e.message);
      return null;
    }
  }
  
  // Scrape auction info from the video footer/action bar
  function getAuctionInfoFromDOM() {
    try {
      // Get seller username from stream header
      let seller = null;
      
      // Try to find seller name near Follow button or in header
      const followBtn = document.querySelector('button[class*="follow" i], [class*="Follow"]');
      if (followBtn) {
        // Seller name is usually in a sibling or parent element
        const header = followBtn.closest('[class*="header" i], [class*="Host" i], [class*="Stream" i]') || followBtn.parentElement?.parentElement;
        if (header) {
          // Look for username-like text (no spaces, reasonable length)
          const links = header.querySelectorAll('a[href*="/user/"], a[href*="/@"]');
          for (const link of links) {
            const username = link.textContent?.trim();
            if (username && username.length > 1 && username.length < 30 && !/follow/i.test(username)) {
              seller = username;
              break;
            }
          }
        }
      }
      
      // Fallback: look for seller in URL
      if (!seller) {
        const urlMatch = window.location.pathname.match(/\/live\/([^\/\?]+)/);
        if (urlMatch) {
          seller = urlMatch[1];
        }
      }
      
      // Get footer text which contains auction info
      const footer = document.querySelector('[class*="Footer"]');
      if (!footer) return null;
      
      const text = footer.innerText;
      if (!text) return null;
      
      // Parse the footer text
      // Format (position-based): 
      //   Line 0: "username is Winning!" or "username won!"
      //   Line 1: "Title Here #123"      <-- TITLE
      //   Line 2: "Condition"            <-- CONDITION
      //   Line 3: "X Bid(s)"
      //   Line 4: "Shipping..."
      //   Line 5+: "$X", timer, etc.
      const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
      
      let title = null;
      let condition = null;
      let price = 0;
      let bids = 0;
      let winningLineIndex = -1;
      
      // First, find the "Winning" or "won" line
      for (let i = 0; i < lines.length; i++) {
        if (/winning|won/i.test(lines[i])) {
          winningLineIndex = i;
          break;
        }
      }
      
      // Title is the line after "Winning/won"
      if (winningLineIndex >= 0 && winningLineIndex + 1 < lines.length) {
        const titleCandidate = lines[winningLineIndex + 1];
        // Make sure it's not a condition, bid count, price, or shipping line
        if (titleCandidate &&
            !/^(VF|NM|FN|VG|GD|CGC|CBCS|Raw|Fine|Near Mint|Very Fine|Very Good|Good|Fair|Poor)/i.test(titleCandidate) &&
            !/^\d+\s+Bid/i.test(titleCandidate) &&
            !/^\$\d+$/.test(titleCandidate) &&
            !/shipping/i.test(titleCandidate) &&
            !/^\d{1,2}:\d{2}$/.test(titleCandidate)) {
          title = titleCandidate;
        }
      }
      
      // Condition is typically the line after title (winningLineIndex + 2)
      if (winningLineIndex >= 0 && winningLineIndex + 2 < lines.length) {
        const conditionCandidate = lines[winningLineIndex + 2];
        if (/^(VF|NM|FN|VG|GD|CGC|CBCS|Raw|Fine|Near Mint|Very Fine|Very Good|Good|Fair|Poor)/i.test(conditionCandidate)) {
          condition = conditionCandidate;
        }
      }
      
      // Also scan for price and bids anywhere in the text
      for (const line of lines) {
        // Price line (just "$X" or "$XX" or "$XXX")
        if (/^\$\d+$/.test(line)) {
          price = parseInt(line.replace('$', '')) * 100;
        }
        // Bid count line - multiple formats: "3 Bids", "3 Bid(s)", "1 Bid"
        if (/^\d+\s+Bid/i.test(line)) {
          const match = line.match(/^(\d+)/);
          if (match) bids = parseInt(match[1]);
        }
      }
      
      // Fallback: if no title found via position, try old method
      if (!title) {
        for (const line of lines) {
          // Skip known non-title patterns
          if (/winning|won/i.test(line)) continue;
          if (/shipping/i.test(line)) continue;
          if (/^\d{1,2}:\d{2}$/.test(line)) continue;
          if (/^\$\d+$/.test(line)) continue;
          if (/^\d+\s+Bid/i.test(line)) continue;
          if (/^(VF|NM|FN|VG|GD|CGC|CBCS|Raw|Fine|Near Mint|Very Fine|Very Good|Good|Fair|Poor)/i.test(line)) continue;
          if (/^(Awaiting|Custom|Pre-bid)/i.test(line)) continue;
          
          // Valid title candidate
          if (line.length > 2 && line.length < 150) {
            title = line;
            break;
          }
        }
      }
      
      // Get viewer count from page (usually near top of stream)
      const viewers = getViewerCount();
      
      if (title) {
        return { title, condition, price, bids, viewers, seller };
      }
    } catch (e) {
      console.log('[ApolloReader] DOM scrape error:', e.message);
    }
    return null;
  }
  
  // Get viewer/attendee count from the page
  function getViewerCount() {
    try {
      // Look for viewer count - usually displayed with an icon near video
      // Common patterns: "92" viewers, shown with eye/person icon
      const pageText = document.body.innerText;
      
      // Try to find it in elements with viewer-related classes
      const viewerElements = document.querySelectorAll('[class*="viewer"], [class*="Viewer"], [class*="watching"], [class*="Watching"], [class*="audience"], [class*="Audience"]');
      for (const el of viewerElements) {
        const num = el.innerText.match(/(\d+)/);
        if (num) return parseInt(num[1]);
      }
      
      // Look for the red/pink badge near the top with viewer count
      const badges = document.querySelectorAll('[class*="Badge"], [class*="badge"], [class*="Count"], [class*="count"]');
      for (const el of badges) {
        const text = el.innerText.trim();
        // If it's just a number (like "92"), it's likely viewer count
        if (/^\d+$/.test(text) && parseInt(text) > 5 && parseInt(text) < 10000) {
          return parseInt(text);
        }
      }
      
      return null;
    } catch (e) {
      return null;
    }
  }
  
  // Normalize listing data
  function normalizeListing(listing) {
    return {
      id: listing.id || listing.__ref,
      title: listing.title || '',
      subtitle: listing.subtitle || listing.description || '',
      price: listing.price?.amount || 
             listing.currentPrice?.amount || 
             (typeof listing.price === 'number' ? listing.price : 0),
      bidCount: listing.currentBidCount || listing.bidCount || 0,
      endsAt: listing.endsAt || listing.activeTimedListingEvent?.endsAt || null,
      imageUrl: listing.imageUrl || 
                listing.images?.[0]?.url || null,
      isLive: listing.isLive || false,
      auctionState: listing.auctionState || null,
      publicStatus: listing.publicStatus || null
    };
  }

  // Fallback: try to extract from DOM
  function getFromDOM() {
    try {
      // Title - usually in a heading
      const titleEl = document.querySelector('[data-testid="listing-title"]') ||
                      document.querySelector('.listing-title') ||
                      document.querySelector('h1');
      
      // Price - look for dollar amount
      const priceEl = document.querySelector('[data-testid="current-price"]') ||
                      document.querySelector('.current-price') ||
                      document.querySelector('[class*="price"]');
      
      if (!titleEl) return null;

      const priceText = priceEl?.textContent || '';
      const priceMatch = priceText.match(/\$?([\d,]+)/);
      const price = priceMatch ? parseInt(priceMatch[1].replace(',', '')) * 100 : 0;

      return {
        id: 'dom-' + Date.now(),
        title: titleEl.textContent?.trim() || '',
        subtitle: '',
        price: price,
        bidCount: 0,
        endsAt: null,
        imageUrl: null
      };
    } catch (e) {
      return null;
    }
  }

  // Get all listings in cache
  function getAllListings() {
    const cache = getCacheSync();
    if (!cache) return [];

    const listings = [];
    const keys = Object.keys(cache).filter(k => 
      k.includes('ListingNode') || k.includes('Listing:')
    );

    for (const key of keys) {
      const listing = cache[key];
      if (listing && listing.title) {
        listings.push({
          id: listing.id || key,
          title: listing.title,
          price: listing.currentPrice?.amount || listing.price || 0
        });
      }
    }

    return listings;
  }

  // Inject bridge on load
  injectBridge();
  
  // Refresh cache periodically
  setInterval(() => getCache(), 500);

  return {
    getCache,
    getCacheSync,
    getCurrentListing,
    getFromDOM,
    getAllListings
  };
})();
