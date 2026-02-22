// lib/sale-tracker.js - Track and store sold items
// NO require() or module.exports - uses window global

window.SaleTracker = (function() {
  'use strict';

  const STORAGE_KEY = 'whatnot_sales';

  // Record a sale
  function record(sale) {
    chrome.storage.local.get([STORAGE_KEY], (result) => {
      const sales = result[STORAGE_KEY] || [];
      
      // Add new sale
      sales.push({
        ...sale,
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        recordedAt: new Date().toISOString()
      });

      // Keep last 5000 sales
      while (sales.length > 5000) {
        sales.shift();
      }

      chrome.storage.local.set({ [STORAGE_KEY]: sales }, () => {
        console.log('[SaleTracker] Saved sale:', sale.title);
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

  return {
    record,
    getAll,
    getRecent,
    getStats,
    clear,
    exportToJSON,
    search
  };
})();
