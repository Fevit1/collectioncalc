// lib/vision.js - Computer Vision for Whatnot Comic Valuator
// Captures video frames and uses Claude Vision API to extract comic data

window.ComicVision = (function() {
  'use strict';

  let apiKey = null;

  // Load API key from storage
  async function loadApiKey() {
    return new Promise(resolve => {
      chrome.storage.local.get('anthropic_api_key', result => {
        apiKey = result.anthropic_api_key || null;
        resolve(apiKey);
      });
    });
  }

  // Save API key to storage
  async function saveApiKey(key) {
    apiKey = key;
    return new Promise(resolve => {
      chrome.storage.local.set({ anthropic_api_key: key }, resolve);
    });
  }

  // Capture current video frame as base64
  function captureVideoFrame() {
    try {
      // Find the video element
      const video = document.querySelector('video');
      if (!video) {
        console.log('[Vision] No video element found');
        return null;
      }

      const vw = video.videoWidth || 640;
      const vh = video.videoHeight || 480;
      
      // Create canvas for full frame (for Vision API)
      const fullCanvas = document.createElement('canvas');
      fullCanvas.width = vw;
      fullCanvas.height = vh;
      const fullCtx = fullCanvas.getContext('2d');
      fullCtx.drawImage(video, 0, 0, vw, vh);
      
      // Create canvas for cropped thumbnail (center 60% of frame)
      // This focuses on where the comic typically is held
      const cropPercent = 0.6;
      const cropW = Math.round(vw * cropPercent);
      const cropH = Math.round(vh * cropPercent);
      const cropX = Math.round((vw - cropW) / 2);
      const cropY = Math.round((vh - cropH) / 2);
      
      const thumbCanvas = document.createElement('canvas');
      thumbCanvas.width = cropW;
      thumbCanvas.height = cropH;
      const thumbCtx = thumbCanvas.getContext('2d');
      thumbCtx.drawImage(video, cropX, cropY, cropW, cropH, 0, 0, cropW, cropH);
      
      // Convert to base64 (JPEG for smaller size)
      const fullBase64 = fullCanvas.toDataURL('image/jpeg', 0.8);
      const thumbBase64 = thumbCanvas.toDataURL('image/jpeg', 0.85);
      
      // Remove the data URL prefix to get just base64
      const fullBase64Data = fullBase64.replace(/^data:image\/\w+;base64,/, '');
      
      console.log('[Vision] 📷 Frame captured:', vw, 'x', vh, '(thumb:', cropW, 'x', cropH, ')');
      return {
        base64: fullBase64Data,      // Full frame for Vision API
        width: vw,
        height: vh,
        dataUrl: fullBase64,         // Full frame data URL
        thumbDataUrl: thumbBase64    // Cropped center for thumbnail/storage
      };
    } catch (e) {
      console.error('[Vision] Capture error:', e.message);
      return null;
    }
  }

  // Send image to Claude Vision API for analysis
  async function analyzeImage(base64Image) {
    if (!apiKey) {
      await loadApiKey();
    }
    
    if (!apiKey) {
      console.error('[Vision] No API key configured');
      return { error: 'No API key. Click ⚙️ to add your Anthropic API key.' };
    }

    try {
      console.log('[Vision] 🔍 Sending to Claude Vision API...');
      
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01',
          'anthropic-dangerous-direct-browser-access': 'true'
        },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 600,
          messages: [{
            role: 'user',
            content: [
              {
                type: 'image',
                source: {
                  type: 'base64',
                  media_type: 'image/jpeg',
                  data: base64Image
                }
              },
              {
                type: 'text',
                text: `You are analyzing a comic book shown in a live auction video. Extract the following information if visible:

1. **Title/Series**: The comic book series name (e.g., "Amazing Spider-Man", "X-Men")
2. **Issue Number**: The issue number
3. **Slab Type**: If it's a CGC/CBCS/PGX slab, identify which. Otherwise "raw"
4. **Grade**: 
   - For SLABS: Read the exact numeric grade from the label (e.g., 9.8, 9.6). High confidence.
   - For RAW comics: Estimate condition based on visible cover only - look for wear, creases, spine stress, corner dings, color fading. Use standard grades (9.8, 9.6, 9.4, 9.2, 9.0, 8.5, 8.0, 7.5, 7.0, 6.5, 6.0, 5.0, 4.0, 3.0). Be conservative since you can only see the front cover!
5. **Grade Confidence**: 
   - SLAB: 0.9+ (reading label directly)
   - RAW: 0.3-0.5 (cover-only estimate)
6. **Variant**: Identify if this is a variant edition:
   - Price variants: "35¢", "30¢" on cover
   - Newsstand vs Direct edition
   - Virgin cover, Sketch cover
   - Ratio variants (1:25, 1:50, etc.)
7. **Key Info**: Any notable info (1st appearance, signature, etc.)
8. **Facsimile Check**: CRITICAL - Look for ANY of these facsimile indicators:
   - "FACSIMILE EDITION" text anywhere on cover (often at top or bottom)
   - Small "Facsimile" or "Facsimile Edition" in corner boxes
   - Modern reprint indicators (often have "MARVEL" or "DC" trade dress style from 2019+)
   - UPC barcode style may differ from original (modern barcodes on classic covers)
   - Price ($3.99, $4.99, $5.99) that doesn't match the vintage cover price shown
   - Perfect print quality on what should be a worn vintage comic
   If you see ANY facsimile indicators, set isFacsimile: true

Respond ONLY with valid JSON in this exact format:
{
  "title": "Series Name",
  "issue": 123,
  "grade": 8.0,
  "gradeConfidence": 0.4,
  "gradeNote": "Cover-only estimate" or "Read from CGC label",
  "slabType": "CGC" or "CBCS" or "PGX" or "raw",
  "variant": "newsstand" or null,
  "isFacsimile": false,
  "facsimileNote": null or "Facsimile Edition text visible at top",
  "keyInfo": "1st appearance of Venom",
  "confidence": 0.9
}

CRITICAL for RAW grades: Always include gradeNote "Cover-only estimate" and keep gradeConfidence between 0.3-0.5. The seller can see back, spine, pages - they know better!

CRITICAL for FACSIMILES: Facsimile editions are modern reprints worth $5-15, NOT the valuable original. Look carefully for "FACSIMILE EDITION" text - it's often subtle but always present on reprints. Common facsimiles: Amazing Fantasy 15, Giant-Size X-Men 1, Incredible Hulk 181, Batman Adventures 12. When in doubt about a "pristine" copy of a classic key issue, suspect it may be a facsimile.

If you cannot see a comic book clearly, respond with: {"error": "Cannot identify comic", "confidence": 0}`
              }
            ]
          }]
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('[Vision] API error:', response.status, errorText);
        return { error: `API error: ${response.status}` };
      }

      const data = await response.json();
      const text = data.content?.[0]?.text || '';
      
      console.log('[Vision] Raw response:', text);
      
      // Parse JSON from response
      try {
        // Find JSON in response (in case there's extra text)
        const jsonMatch = text.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          const result = JSON.parse(jsonMatch[0]);
          console.log('[Vision] ✅ Parsed result:', result);
          
          // Log facsimile detection
          if (result.isFacsimile) {
            console.log('[Vision] ⚠️ FACSIMILE DETECTED:', result.facsimileNote);
          }
          
          return result;
        }
      } catch (e) {
        console.error('[Vision] JSON parse error:', e.message);
      }
      
      return { error: 'Could not parse response', raw: text };
      
    } catch (e) {
      console.error('[Vision] API call failed:', e.message);
      return { error: e.message };
    }
  }

  // Main scan function - capture and analyze
  async function scan() {
    console.log('[Vision] 🎬 Starting scan...');
    
    const frame = captureVideoFrame();
    if (!frame) {
      return { error: 'Could not capture video frame' };
    }
    
    const result = await analyzeImage(frame.base64);
    result.frameData = frame.thumbDataUrl; // Cropped center for thumbnail/storage
    
    return result;
  }

  // Check if API key is configured
  async function hasApiKey() {
    await loadApiKey();
    return !!apiKey;
  }

  return {
    scan,
    captureVideoFrame,
    analyzeImage,
    saveApiKey,
    loadApiKey,
    hasApiKey
  };
})();
