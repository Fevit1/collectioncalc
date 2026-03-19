// inject.js - Runs in PAGE context to access Apollo cache
// This file is injected via web_accessible_resources to bypass CSP

(function() {
  'use strict';
  
  // Listen for requests from content script
  document.addEventListener('apolloDataRequest', (e) => {
    const eventId = e.detail?.eventId;
    if (!eventId) return;
    
    try {
      const cache = window.__APOLLO_CLIENT__?.cache?.data?.data || null;
      const jsonData = cache ? JSON.stringify(cache) : null;
      
      document.dispatchEvent(new CustomEvent('apolloDataResponse', {
        detail: { eventId: eventId, data: jsonData }
      }));
    } catch (err) {
      document.dispatchEvent(new CustomEvent('apolloDataResponse', {
        detail: { eventId: eventId, data: null, error: err.message }
      }));
    }
  });
  
  console.log('[Valuator Inject] Page context bridge ready');
})();
