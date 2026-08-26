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

  const COLLECTIONCALC_API = 'https://collectioncalc-docker.onrender.com';

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

  // ⚰️ REMOVED 2026-08-25: uploadImage(saleId, imageBase64). DEAD.
  // REASON: exported but never invoked anywhere in this extension — sale
  // images ship inline with insertSale via POST /api/sales/record, and the
  // backend does its own R2 upload. Its endpoint (/api/images/upload-for-sale)
  // was deleted in the same unit (routes/images.py carries the tombstone), so
  // restoring this function would call a 404.

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

  // ⚠️ THE NAME `SupabaseClient` IS A LIE ABOUT THE MECHANISM. READ THIS BEFORE
  // TRUSTING IT.
  //
  // Nothing below touches Supabase. Every method here fetches
  // COLLECTIONCALC_API (Render), and `insertSale` lands rows in the
  // `market_sales` table in Render PostgreSQL via POST /api/sales/record.
  // Slab Worthy has no Supabase dependency at all: the old `lib/supabase.js`
  // was orphaned at v2.40 (absent from manifest.json, so never loaded) and
  // deleted 2026-08-08.
  //
  // The name persists ONLY because `content.js` calls
  // `window.SupabaseClient.insertSale()` / `.getFMV()`, and this extension is
  // loaded unpacked and reloaded by hand. A rename is two coordinated edits
  // with a manual reload between them, and a missed reload is
  // indistinguishable from a successful one, so renaming risks silently
  // killing Whatnot capture to satisfy a naming preference. Deliberately not
  // renamed 2026-08-08 (Mike's call).
  //
  // If you DO rename it later, `window.SupabaseClient` has FIVE references in
  // content.js, not two. Per L-2026-026, change every one in the SAME commit:
  // the two call sites (990 insertSale, 720 getFMV), the two truthiness guards
  // that gate them (989, 719), and the startup log (9). Miss a guard and
  // capture goes silently dead while the log still says "Connected". Bump
  // manifest.json (minor), reload unpacked, and verify a real row lands in
  // market_sales before calling it done. `window.CollectionCalc` below is the
  // correctly-named alias; migrate content.js onto that.
  window.SupabaseClient = {
    insertSale,
    getRecentSales,
    getSalesCount,
    getFMV
  };

  // Also expose as CollectionCalc for new code
  window.CollectionCalc = {
    insertSale,
    getRecentSales,
    getSalesCount,
    getFMV,
    API_URL: COLLECTIONCALC_API
  };

  console.log('[CollectionCalc] ✅ API client loaded (replaces Supabase)');

})();
