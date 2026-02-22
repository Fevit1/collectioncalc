/**
 * CollectionCalc API Client for Whatnot Valuator Extension
 * 
 * DROP-IN REPLACEMENT for SupabaseClient
 * Exposes window.SupabaseClient for backwards compatibility
 * 
 * Handles:
 * - Recording sales to CollectionCalc database
 * - Uploading images to R2 via backend
 * - Fetching recent sales for deduplication
 * 
 * Updated: Session 10 - Added facsimile support
 */

(function() {
  'use strict';

  const COLLECTIONCALC_API = 'https://collectioncalc.onrender.com';

  /**
   * Insert a sale - matches SupabaseClient.insertSale() interface
   * @param {Object} sale - Sale data from content.js
   */
  async function insertSale(sale) {
    try {
      // Map from content.js format to API format
      const payload = {
        source: 'whatnot',
        title: sale.title,
        series: sale.series || null,
        issue: sale.issue || null,
        grade: sale.grade || null,
        grade_source: sale.gradeSource || null,
        slab_type: sale.slabType || null,
        variant: sale.variant || null,
        is_key: sale.isKey || false,
        is_facsimile: sale.isFacsimile || false,  // NEW: Facsimile flag
        price: sale.price,
        sold_at: sale.timestamp ? new Date(sale.timestamp).toISOString() : new Date().toISOString(),
        raw_title: sale.rawTitle || sale.title,
        seller: sale.seller || null,
        bids: sale.bids || null,
        viewers: sale.viewers || null,
        source_id: `whatnot_${sale.timestamp || Date.now()}`,
        // Include image if available - backend will upload to R2
        image: sale.imageDataUrl || null
      };

      const response = await fetch(`${COLLECTIONCALC_API}/api/sales/record`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      
      if (data.success) {
        // Enhanced logging for facsimiles
        const facsimileNote = sale.isFacsimile ? ' [FACSIMILE]' : '';
        console.log(`[CollectionCalc] ✅ Sale recorded: ${sale.title} - $${sale.price}${facsimileNote}`);
        if (data.image_url) {
          console.log(`[CollectionCalc] 📷 Image uploaded: ${data.image_url}`);
        }
      } else {
        console.error('[CollectionCalc] ❌ Failed:', data.error);
      }
      
      return data;
    } catch (error) {
      console.error('[CollectionCalc] ❌ API error:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Get recent sales - for deduplication and overlay display
   * @param {number} [limit=100] - Maximum number of sales to fetch
   */
  async function getRecentSales(limit = 100) {
    try {
      const response = await fetch(
        `${COLLECTIONCALC_API}/api/sales/recent?source=whatnot&limit=${limit}`
      );
      const data = await response.json();
      
      if (data.success) {
        console.log(`[CollectionCalc] Fetched ${data.sales.length} recent sales`);
        return data.sales;
      }
      return [];
    } catch (error) {
      console.error('[CollectionCalc] Failed to fetch recent sales:', error);
      return [];
    }
  }

  /**
   * Get total sales count
   */
  async function getSalesCount() {
    try {
      const response = await fetch(`${COLLECTIONCALC_API}/api/sales/count`);
      const data = await response.json();
      return data.count || 0;
    } catch (error) {
      console.error('[CollectionCalc] Failed to get sales count:', error);
      return 0;
    }
  }

  /**
   * Upload image separately (if needed after sale is recorded)
   * @param {number} saleId - The sale ID
   * @param {string} imageBase64 - Base64 encoded image
   */
  async function uploadImage(saleId, imageBase64) {
    try {
      const response = await fetch(`${COLLECTIONCALC_API}/api/images/upload-for-sale`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          sale_id: saleId,
          image: imageBase64
        })
      });

      const data = await response.json();
      
      if (data.success) {
        console.log(`[CollectionCalc] 📷 Image uploaded for sale ${saleId}`);
      }
      
      return data;
    } catch (error) {
      console.error('[CollectionCalc] Image upload error:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Get Fair Market Value data for a comic from sales history
   * @param {string} title - Comic title
   * @param {string|number} issue - Issue number
   * @returns {Object} FMV data with tiers
   */
  async function getFMV(title, issue) {
    // Skip API call if missing required data
    if (!title || title.length < 3) {
      console.log('[CollectionCalc] FMV skipped - title too short:', title);
      return { count: 0, tiers: null };
    }
    
    // Skip garbage titles that slip through
    const titleLower = title.toLowerCase();
    const garbagePatterns = [
      'available', 'remaining', 'left', 'in stock', 'bid', 'starting',
      'mystery', 'random', 'bundle', 'lot', 'choice', 'pick'
    ];
    if (garbagePatterns.some(p => titleLower.includes(p))) {
      console.log('[CollectionCalc] FMV skipped - garbage title:', title);
      return { count: 0, tiers: null };
    }
    
    // Skip if title is just numbers/symbols (e.g., "$30", "91")
    if (/^[\d\s$#%.,]+$/.test(title)) {
      console.log('[CollectionCalc] FMV skipped - numbers only:', title);
      return { count: 0, tiers: null };
    }
    
    // Build URL - only include issue if it's actually set
    let url = `${COLLECTIONCALC_API}/api/sales/fmv?title=${encodeURIComponent(title)}`;
    if (issue !== null && issue !== undefined && issue !== '') {
      url += `&issue=${encodeURIComponent(issue)}`;
    }
    
    try {
      const response = await fetch(url);
      const data = await response.json();
      
      if (data.success) {
        const issueStr = issue ? ` #${issue}` : '';
        console.log(`[CollectionCalc] FMV for ${title}${issueStr}:`, data);
        return data;
      }
      return { count: 0, tiers: null };
    } catch (error) {
      console.error('[CollectionCalc] FMV lookup error:', error);
      return { count: 0, tiers: null };
    }
  }

  // Expose as SupabaseClient for backwards compatibility with content.js
  window.SupabaseClient = {
    insertSale,
    getRecentSales,
    getSalesCount,
    uploadImage,
    getFMV
  };

  // Also expose as CollectionCalc for new code
  window.CollectionCalc = {
    insertSale,
    getRecentSales,
    getSalesCount,
    uploadImage,
    getFMV,
    API_URL: COLLECTIONCALC_API
  };

  console.log('[CollectionCalc] ✅ API client loaded (replaces Supabase)');

})();
