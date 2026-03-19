// lib/sale-tracker.js - Track and store sold items
// NO require() or module.exports - uses window global

window.SaleTracker = (function() {
  'use strict';

  const STORAGE_KEY = 'whatnot_sales';

  // Record a sale
  function record(sale) {
    chrome.storage.local.get([STORAGE_KEY], (result) => {
      const sales = result[STORAGE_KEY] || [];
      
      // Strip large fields to save storage quota (images already uploaded to R2)
      const { imageDataUrl, frameData, ...saleWithoutImage } = sale;
      
      // Add new sale (without image data)
      sales.push({
        ...saleWithoutImage,
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        recordedAt: new Date().toISOString()
      });

      // Keep last 500 sales (reduced from 5000 to stay under quota)
      while (sales.length > 500) {
        sales.shift();
      }

      chrome.storage.local.set({ [STORAGE_KEY]: sales }, () => {
        if (chrome.runtime.lastError) {
          console.error('[SaleTracker] Storage error:', chrome.runtime.lastError.message);
        } else {
          console.log('[SaleTracker] Saved sale:', sale.title);
        }
      });
    });
  }

  // Get all sales
  function getAll() {
    return new Promise((resolve) => {
      chrome.storage.local.get([STORAGE_KEY], (result) => {
        resolve(result[STORAGE_KEY] || []);
      });
    });
  }

  // Get recent sales
  function getRecent(count = 20) {
    return new Promise((resolve) => {
      chrome.storage.local.get([STORAGE_KEY], (result) => {
        const sales = result[STORAGE_KEY] || [];
        resolve(sales.slice(-count).reverse());
      });
    });
  }

  // Get stats
  function getStats() {
    return new Promise((resolve) => {
      chrome.storage.local.get([STORAGE_KEY], (result) => {
        const sales = result[STORAGE_KEY] || [];
        
        const stats = {
          totalSales: sales.length,
          totalValue: sales.reduce((sum, s) => sum + (s.price || 0), 0),
          avgPrice: 0,
          topSeries: {},
          recentSales: sales.slice(-10).reverse()
        };

        if (sales.length > 0) {
          stats.avgPrice = Math.round(stats.totalValue / sales.length);
        }

        // Count by series
        for (const sale of sales) {
          if (sale.series) {
            stats.topSeries[sale.series] = (stats.topSeries[sale.series] || 0) + 1;
          }
        }

        resolve(stats);
      });
    });
  }

  // Compact storage - remove image data from old sales and trim to limit
  function compactStorage() {
    return new Promise((resolve) => {
      chrome.storage.local.get([STORAGE_KEY], (result) => {
        const sales = result[STORAGE_KEY] || [];
        
        // Strip image data from all sales
        const compacted = sales.map(sale => {
          const { imageDataUrl, frameData, ...rest } = sale;
          return rest;
        });
        
        // Keep only last 500
        const trimmed = compacted.slice(-500);
        
        chrome.storage.local.set({ [STORAGE_KEY]: trimmed }, () => {
          if (chrome.runtime.lastError) {
            console.error('[SaleTracker] Compact failed:', chrome.runtime.lastError.message);
            resolve(false);
          } else {
            console.log(`[SaleTracker] Compacted: ${sales.length} → ${trimmed.length} sales`);
            resolve(true);
          }
        });
      });
    });
  }

  // Clear all sales
  function clear() {
    return new Promise((resolve) => {
      chrome.storage.local.set({ [STORAGE_KEY]: [] }, () => {
        console.log('[SaleTracker] Cleared all sales');
        resolve();
      });
    });
  }

  // Export to JSON
  function exportToJSON() {
    return new Promise((resolve) => {
      chrome.storage.local.get([STORAGE_KEY], (result) => {
        const sales = result[STORAGE_KEY] || [];
        const json = JSON.stringify(sales, null, 2);
        resolve(json);
      });
    });
  }

  // Search sales
  function search(query) {
    return new Promise((resolve) => {
      chrome.storage.local.get([STORAGE_KEY], (result) => {
        const sales = result[STORAGE_KEY] || [];
        const q = query.toLowerCase();
        
        const matches = sales.filter(sale => 
          (sale.title && sale.title.toLowerCase().includes(q)) ||
          (sale.series && sale.series.toLowerCase().includes(q))
        );
        
        resolve(matches);
      });
    });
  }

  // Auto-compact on load to fix any bloated storage
  compactStorage();

  return {
    record,
    getAll,
    getRecent,
    getStats,
    clear,
    compactStorage,
    exportToJSON,
    search
  };
})();
