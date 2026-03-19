// background.js - Service Worker for multi-tab sale aggregation
// NO require() or module.exports - pure browser JavaScript

const tabData = new Map();
let allSales = [];

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const tabId = sender.tab?.id;
  
  switch (message.type) {
    case 'TAB_READY':
      tabData.set(tabId, {
        url: sender.tab.url,
        title: message.streamTitle || 'Unknown Stream',
        currentItem: null,
        sales: []
      });
      console.log(`[BG] Tab ${tabId} registered: ${message.streamTitle}`);
      sendResponse({ success: true });
      break;
      
    case 'ITEM_UPDATE':
      if (tabData.has(tabId)) {
        tabData.get(tabId).currentItem = message.item;
      }
      sendResponse({ success: true });
      break;
      
    case 'SALE_RECORDED':
      if (tabData.has(tabId)) {
        const sale = {
          ...message.sale,
          tabId,
          streamTitle: tabData.get(tabId).title,
          timestamp: Date.now()
        };
        tabData.get(tabId).sales.push(sale);
        allSales.push(sale);
        
        // Save to storage
        chrome.storage.local.get(['salesHistory'], (result) => {
          const history = result.salesHistory || [];
          history.push(sale);
          // Keep last 1000 sales
          if (history.length > 1000) history.shift();
          chrome.storage.local.set({ salesHistory: history });
        });
        
        console.log(`[BG] Sale recorded: ${sale.title} - $${sale.price}`);
      }
      sendResponse({ success: true });
      break;
      
    case 'GET_ALL_TABS':
      const tabs = Array.from(tabData.entries()).map(([id, data]) => ({
        tabId: id,
        ...data
      }));
      sendResponse({ tabs });
      break;
      
    case 'GET_ALL_SALES':
      chrome.storage.local.get(['salesHistory'], (result) => {
        sendResponse({ sales: result.salesHistory || [] });
      });
      return true; // Keep channel open for async response
      
    case 'GET_STATS':
      chrome.storage.local.get(['salesHistory'], (result) => {
        const history = result.salesHistory || [];
        const stats = {
          totalSales: history.length,
          activeTabs: tabData.size,
          recentSales: history.slice(-20).reverse()
        };
        sendResponse({ stats });
      });
      return true;
      
    case 'CLEAR_HISTORY':
      chrome.storage.local.set({ salesHistory: [] });
      allSales = [];
      sendResponse({ success: true });
      break;
  }
  
  return false;
});

// Clean up when tab closes
chrome.tabs.onRemoved.addListener((tabId) => {
  if (tabData.has(tabId)) {
    console.log(`[BG] Tab ${tabId} closed, removing from tracking`);
    tabData.delete(tabId);
  }
});

console.log('[BG] Whatnot Valuator background service started');
