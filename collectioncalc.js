/**
 * CollectionCalc API Client for Whatnot Valuator Extension
 * 
 * Handles:
 * - Recording sales to CollectionCalc database
 * - Uploading images to R2 via backend
 * - Fetching recent sales for deduplication
 * 
 * Replaces the old Supabase integration.
 */

const COLLECTIONCALC_API = 'https://collectioncalc.onrender.com';

/**
 * Record a sale to CollectionCalc
 * @param {Object} saleData - Sale information
 * @param {string} saleData.title - Comic title
 * @param {string} saleData.series - Series name
 * @param {string} saleData.issue - Issue number
 * @param {string} saleData.grade - Grade (e.g., "9.8")
 * @param {string} saleData.grade_source - "CGC", "CBCS", "RAW"
 * @param {string} saleData.slab_type - Slab type if applicable
 * @param {string} saleData.variant - Variant description
 * @param {boolean} saleData.is_key - Is this a key issue
 * @param {number} saleData.price - Sale price in dollars
 * @param {string} saleData.sold_at - ISO timestamp of sale
 * @param {string} saleData.raw_title - Original title from Whatnot
 * @param {string} saleData.seller - Seller username
 * @param {number} saleData.bids - Number of bids
 * @param {number} saleData.viewers - Number of viewers
 * @param {string} saleData.source_id - Unique ID from Whatnot (for dedup)
 * @param {string} [saleData.image] - Base64 encoded image (optional)
 * @returns {Promise<{success: boolean, id?: number, error?: string}>}
 */
async function recordSale(saleData) {
    try {
        const response = await fetch(`${COLLECTIONCALC_API}/api/sales/record`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                source: 'whatnot',
                title: saleData.title,
                series: saleData.series,
                issue: saleData.issue,
                grade: saleData.grade,
                grade_source: saleData.grade_source,
                slab_type: saleData.slab_type,
                variant: saleData.variant,
                is_key: saleData.is_key || false,
                price: saleData.price,
                sold_at: saleData.sold_at || new Date().toISOString(),
                raw_title: saleData.raw_title,
                seller: saleData.seller,
                bids: saleData.bids,
                viewers: saleData.viewers,
                source_id: saleData.source_id,
                // Include image if provided - backend will upload to R2
                image: saleData.image || null
            })
        });

        const data = await response.json();
        
        if (data.success) {
            console.log(`[CollectionCalc] Sale recorded: ${saleData.title} #${saleData.issue} - $${saleData.price}`);
            if (data.image_url) {
                console.log(`[CollectionCalc] Image uploaded: ${data.image_url}`);
            }
        } else {
            console.error('[CollectionCalc] Failed to record sale:', data.error);
        }
        
        return data;
    } catch (error) {
        console.error('[CollectionCalc] API error:', error);
        return { success: false, error: error.message };
    }
}

/**
 * Upload an image for an existing sale
 * Use this if you need to upload the image separately from recording the sale
 * @param {number} saleId - The sale ID returned from recordSale
 * @param {string} imageBase64 - Base64 encoded image data
 * @returns {Promise<{success: boolean, url?: string, error?: string}>}
 */
async function uploadSaleImage(saleId, imageBase64) {
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
            console.log(`[CollectionCalc] Image uploaded for sale ${saleId}: ${data.url}`);
        } else {
            console.error('[CollectionCalc] Failed to upload image:', data.error);
        }
        
        return data;
    } catch (error) {
        console.error('[CollectionCalc] Image upload error:', error);
        return { success: false, error: error.message };
    }
}

/**
 * Get recent sales (for deduplication and overlay display)
 * @param {number} [limit=100] - Maximum number of sales to fetch
 * @returns {Promise<{success: boolean, sales?: Array, error?: string}>}
 */
async function getRecentSales(limit = 100) {
    try {
        const response = await fetch(
            `${COLLECTIONCALC_API}/api/sales/recent?source=whatnot&limit=${limit}`
        );

        const data = await response.json();
        
        if (data.success) {
            console.log(`[CollectionCalc] Fetched ${data.sales.length} recent sales`);
        }
        
        return data;
    } catch (error) {
        console.error('[CollectionCalc] Failed to fetch recent sales:', error);
        return { success: false, error: error.message };
    }
}

/**
 * Get total sales count
 * @returns {Promise<{count: number}>}
 */
async function getSalesCount() {
    try {
        const response = await fetch(`${COLLECTIONCALC_API}/api/sales/count`);
        return await response.json();
    } catch (error) {
        console.error('[CollectionCalc] Failed to get sales count:', error);
        return { count: 0 };
    }
}

/**
 * Check if a sale has already been recorded (by source_id)
 * @param {string} sourceId - The Whatnot listing ID
 * @param {Array} recentSales - Array of recent sales to check against
 * @returns {boolean}
 */
function isDuplicateSale(sourceId, recentSales) {
    if (!recentSales || !Array.isArray(recentSales)) return false;
    return recentSales.some(sale => sale.source_id === sourceId);
}

/**
 * Capture a frame from video element and convert to base64
 * @param {HTMLVideoElement} videoElement - The video element to capture from
 * @param {number} [quality=0.8] - JPEG quality (0-1)
 * @returns {string|null} - Base64 encoded image or null if failed
 */
function captureVideoFrame(videoElement, quality = 0.8) {
    try {
        const canvas = document.createElement('canvas');
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoElement, 0, 0);
        
        // Convert to base64 JPEG
        const dataUrl = canvas.toDataURL('image/jpeg', quality);
        
        // Return just the base64 part (remove data:image/jpeg;base64, prefix)
        // Actually, keep the full data URL - backend handles both formats
        return dataUrl;
    } catch (error) {
        console.error('[CollectionCalc] Failed to capture video frame:', error);
        return null;
    }
}

/**
 * Capture center region of video (where comic usually is)
 * @param {HTMLVideoElement} videoElement - The video element to capture from
 * @param {number} [cropPercent=0.6] - What percentage of center to keep (0-1)
 * @param {number} [quality=0.8] - JPEG quality (0-1)
 * @returns {string|null} - Base64 encoded image or null if failed
 */
function captureVideoCenterFrame(videoElement, cropPercent = 0.6, quality = 0.8) {
    try {
        const vw = videoElement.videoWidth;
        const vh = videoElement.videoHeight;
        
        // Calculate crop region (center)
        const cropW = vw * cropPercent;
        const cropH = vh * cropPercent;
        const startX = (vw - cropW) / 2;
        const startY = (vh - cropH) / 2;
        
        const canvas = document.createElement('canvas');
        canvas.width = cropW;
        canvas.height = cropH;
        
        const ctx = canvas.getContext('2d');
        ctx.drawImage(
            videoElement,
            startX, startY, cropW, cropH,  // Source rectangle
            0, 0, cropW, cropH              // Destination rectangle
        );
        
        return canvas.toDataURL('image/jpeg', quality);
    } catch (error) {
        console.error('[CollectionCalc] Failed to capture center frame:', error);
        return null;
    }
}

// Export for use in extension
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        recordSale,
        uploadSaleImage,
        getRecentSales,
        getSalesCount,
        isDuplicateSale,
        captureVideoFrame,
        captureVideoCenterFrame,
        COLLECTIONCALC_API
    };
}

// Also expose globally for content scripts
if (typeof window !== 'undefined') {
    window.CollectionCalc = {
        recordSale,
        uploadSaleImage,
        getRecentSales,
        getSalesCount,
        isDuplicateSale,
        captureVideoFrame,
        captureVideoCenterFrame,
        API_URL: COLLECTIONCALC_API
    };
}
