// lib/supabase.js - Supabase client for Whatnot Valuator
// Pushes sales data to cloud database for CollectionCalc integration

window.SupabaseClient = (function() {
  'use strict';

  const SUPABASE_URL = 'https://kvtfywxvawdolgxyiari.supabase.co';
  const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt2dGZ5d3h2YXdkb2xneHlpYXJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkyMTQ4OTksImV4cCI6MjA4NDc5MDg5OX0.AOXmVVNI6Tu1LPbmzuglr3F4GHN1VcPAF8jnDz-xxFY';
  const STORAGE_BUCKET = 'comic-scans';

  // Upload image to Supabase Storage
  async function uploadImage(dataUrl) {
    try {
      // Convert data URL to blob
      const response = await fetch(dataUrl);
      const blob = await response.blob();
      
      // Generate unique filename
      const timestamp = Date.now();
      const random = Math.random().toString(36).substring(2, 8);
      const filename = `scan_${timestamp}_${random}.jpg`;
      
      // Upload to Supabase Storage
      const uploadResponse = await fetch(
        `${SUPABASE_URL}/storage/v1/object/${STORAGE_BUCKET}/${filename}`,
        {
          method: 'POST',
          headers: {
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
            'Content-Type': 'image/jpeg'
          },
          body: blob
        }
      );
      
      if (uploadResponse.ok) {
        // Return public URL
        const publicUrl = `${SUPABASE_URL}/storage/v1/object/public/${STORAGE_BUCKET}/${filename}`;
        console.log('[Supabase] 📷 Image uploaded:', filename);
        return publicUrl;
      } else {
        const errorText = await uploadResponse.text();
        console.error('[Supabase] ❌ Image upload failed:', uploadResponse.status, errorText);
        return null;
      }
    } catch (error) {
      console.error('[Supabase] ❌ Image upload error:', error.message);
      return null;
    }
  }

  // Insert a sale into Supabase
  async function insertSale(sale) {
    try {
      // Upload image first if present
      let imageUrl = null;
      if (sale.imageDataUrl) {
        imageUrl = await uploadImage(sale.imageDataUrl);
      }
      
      const response = await fetch(`${SUPABASE_URL}/rest/v1/whatnot_sales`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': SUPABASE_ANON_KEY,
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
          'Prefer': 'return=minimal'
        },
        body: JSON.stringify({
          title: sale.title || null,
          series: sale.series || null,
          issue: sale.issue || null,
          grade: sale.grade || null,
          grade_source: sale.gradeSource || null,
          condition: sale.condition || null,
          slab_type: sale.slabType || null,
          variant: sale.variant || null,
          is_key: sale.isKey || false,
          price: sale.price || 0,
          bids: sale.bids || null,
          viewers: sale.viewers || null,
          seller: sale.seller || null,
          platform: sale.platform || 'whatnot',
          image_url: imageUrl,
          raw_title: sale.rawTitle || null,
          sold_at: new Date().toISOString()
        })
      });

      if (response.ok) {
        console.log('[Supabase] ✅ Sale saved to cloud:', sale.title);
        return true;
      } else {
        const errorText = await response.text();
        console.error('[Supabase] ❌ Failed to save sale:', response.status, errorText);
        return false;
      }
    } catch (error) {
      console.error('[Supabase] ❌ Network error:', error.message);
      return false;
    }
  }

  // Query sales (for CollectionCalc integration)
  async function querySales(params = {}) {
    try {
      let url = `${SUPABASE_URL}/rest/v1/whatnot_sales?select=*`;
      
      // Add filters
      if (params.title) {
        url += `&title=ilike.*${encodeURIComponent(params.title)}*`;
      }
      if (params.series) {
        url += `&series=ilike.*${encodeURIComponent(params.series)}*`;
      }
      if (params.issue) {
        url += `&issue=eq.${params.issue}`;
      }
      
      // Order by most recent
      url += '&order=sold_at.desc&limit=50';

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'apikey': SUPABASE_ANON_KEY,
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
        }
      });

      if (response.ok) {
        return await response.json();
      } else {
        console.error('[Supabase] Query failed:', response.status);
        return [];
      }
    } catch (error) {
      console.error('[Supabase] Query error:', error.message);
      return [];
    }
  }

  // Get FMV (Fair Market Value) from real sales data - with grade tiers
  async function getFMV(title, issue) {
    if (!title) return null;
    
    try {
      // Clean title for search
      const cleanTitle = title.trim();
      
      // Build query URL - search by title, optionally by issue
      let url = `${SUPABASE_URL}/rest/v1/whatnot_sales?select=price,grade,slab_type,sold_at`;
      url += `&title=ilike.*${encodeURIComponent(cleanTitle)}*`;
      
      if (issue) {
        url += `&issue=eq.${issue}`;
      }
      
      url += '&order=sold_at.desc&limit=50';

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'apikey': SUPABASE_ANON_KEY,
          'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
        }
      });

      if (!response.ok) {
        console.error('[Supabase] FMV query failed:', response.status);
        return null;
      }

      const sales = await response.json();
      
      if (!sales || sales.length === 0) {
        return { count: 0, message: 'No sales data' };
      }

      // Define grade tiers
      const tiers = {
        low: { min: 0, max: 4.4, label: '<4.5', sales: [] },      // <4.5
        mid: { min: 4.5, max: 7.9, label: '4.5-7.9', sales: [] }, // 4.5-7.9
        high: { min: 8.0, max: 8.9, label: '8-8.9', sales: [] },  // 8.0-8.9
        top: { min: 9.0, max: 10, label: '9+', sales: [] }        // 9.0+
      };
      
      // Sort sales into tiers
      for (const sale of sales) {
        const price = parseFloat(sale.price);
        if (isNaN(price)) continue;
        
        const grade = parseFloat(sale.grade);
        
        // No grade or raw = low tier
        if (!sale.grade || isNaN(grade)) {
          tiers.low.sales.push(price);
        } else if (grade < 4.5) {
          tiers.low.sales.push(price);
        } else if (grade < 8.0) {
          tiers.mid.sales.push(price);  // 4.5-7.9
        } else if (grade < 9.0) {
          tiers.high.sales.push(price); // 8.0-8.9
        } else {
          tiers.top.sales.push(price);  // 9.0+
        }
      }
      
      // Calculate avg for each tier
      const calcTier = (tierData) => {
        if (tierData.sales.length === 0) return null;
        const avg = tierData.sales.reduce((a, b) => a + b, 0) / tierData.sales.length;
        return {
          label: tierData.label,
          avg: Math.round(avg),
          count: tierData.sales.length
        };
      };
      
      const result = {
        count: sales.length,
        tiers: {
          low: calcTier(tiers.low),
          mid: calcTier(tiers.mid),
          high: calcTier(tiers.high),
          top: calcTier(tiers.top)
        }
      };

      return result;
    } catch (error) {
      console.error('[Supabase] FMV error:', error.message);
      return null;
    }
  }

  // Get recent sales
  async function getRecentSales(limit = 20) {
    try {
      const response = await fetch(
        `${SUPABASE_URL}/rest/v1/whatnot_sales?select=*&order=sold_at.desc&limit=${limit}`,
        {
          method: 'GET',
          headers: {
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
          }
        }
      );

      if (response.ok) {
        return await response.json();
      }
      return [];
    } catch (error) {
      console.error('[Supabase] Error fetching recent sales:', error.message);
      return [];
    }
  }

  // Get stats
  async function getStats() {
    try {
      const response = await fetch(
        `${SUPABASE_URL}/rest/v1/whatnot_sales?select=price`,
        {
          method: 'GET',
          headers: {
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': `Bearer ${SUPABASE_ANON_KEY}`
          }
        }
      );

      if (response.ok) {
        const sales = await response.json();
        const totalSales = sales.length;
        const totalValue = sales.reduce((sum, s) => sum + (parseFloat(s.price) || 0), 0);
        return {
          totalSales,
          totalValue: totalValue.toFixed(2),
          avgPrice: totalSales > 0 ? (totalValue / totalSales).toFixed(2) : 0
        };
      }
      return { totalSales: 0, totalValue: 0, avgPrice: 0 };
    } catch (error) {
      console.error('[Supabase] Stats error:', error.message);
      return { totalSales: 0, totalValue: 0, avgPrice: 0 };
    }
  }

  return {
    insertSale,
    querySales,
    getRecentSales,
    getStats,
    getFMV,
    SUPABASE_URL
  };
})();
