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
        is_facsimile: sale.isFacsimile || false,
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
        console.log(`[CollectionCalc] ✅ Sale recorded: ${sale.title} - $${sale.price}`);
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

  // Expose as SupabaseClient for backwards compatibility with content.js
  window.SupabaseClient = {
    insertSale,
    getRecentSales,
    getSalesCount,
    uploadImage
  };

  // Also expose as CollectionCalc for new code
  window.CollectionCalc = {
    insertSale,
    getRecentSales,
    getSalesCount,
    uploadImage,
    API_URL: COLLECTIONCALC_API
  };

  console.log('[CollectionCalc] ✅ API client loaded (replaces Supabase)');

})();
