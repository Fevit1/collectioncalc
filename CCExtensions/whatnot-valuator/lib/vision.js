// lib/vision.js - Computer Vision for Whatnot Comic Valuator
// Captures video frames and sends to Slab Worthy backend for Claude Vision analysis
//
// Session 61: Migrated from direct Anthropic API calls to backend proxy
// - API key is now server-side (no more chrome.storage API key)
// - Auth via Slab Worthy JWT token (guard+ plan required)
// - Rate limiting and usage tracking handled server-side

window.ComicVision = (function() {
  'use strict';

  const API_BASE = 'https://collectioncalc-docker.onrender.com';

  // Get JWT token from chrome.storage
  async function getAuthToken() {
    return new Promise(resolve => {
      chrome.storage.local.get('slab_worthy_jwt', result => {
        resolve(result.slab_worthy_jwt || null);
      });
    });
  }

  // Check if user is authenticated (has JWT token)
  async function hasApiKey() {
    const token = await getAuthToken();
    return !!token;
  }

  // Legacy compatibility - returns JWT token instead of API key
  async function loadApiKey() {
    return await getAuthToken();
  }

  // Legacy compatibility - no-op since key is server-side now
  async function saveApiKey(key) {
    console.log('[Vision] API key management moved to backend. Use Settings to login.');
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

  // Send image to backend Vision API proxy for analysis
  async function analyzeImage(base64Image) {
    const token = await getAuthToken();

    if (!token) {
      console.error('[Vision] No auth token configured');
      return { error: 'Not signed in. Right-click extension icon → Options to login with your Slab Worthy account.' };
    }

    try {
      console.log('[Vision] 🔍 Sending to backend Vision API...');

      const response = await fetch(`${API_BASE}/api/vision/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          image: base64Image,
          media_type: 'image/jpeg',
          context: {
            source: 'whatnot',
            timestamp: Date.now()
          }
        })
      });

      if (!response.ok) {
        let errorData = {};
        try {
          errorData = await response.json();
        } catch (e) {
          errorData = { error: `HTTP ${response.status}` };
        }

        if (response.status === 401) {
          console.error('[Vision] Auth expired');
          return { error: 'Session expired. Open extension Options to sign in again.' };
        }
        if (response.status === 403) {
          console.error('[Vision] Feature not allowed:', errorData.error);
          return { error: errorData.error || 'Vision scanning requires Guard or Dealer plan.' };
        }
        if (response.status === 429) {
          console.error('[Vision] Rate limited');
          return { error: 'Too many scans. Wait a moment and try again.' };
        }

        console.error('[Vision] API error:', response.status, errorData);
        return { error: `API error: ${response.status}` };
      }

      const data = await response.json();

      if (!data.success) {
        console.error('[Vision] Analysis failed:', data.error);
        return { error: data.error || 'Analysis failed' };
      }

      console.log('[Vision] ✅ Parsed result:', data);

      // Log facsimile detection
      if (data.isFacsimile) {
        console.log('[Vision] ⚠️ FACSIMILE DETECTED:', data.facsimileNote);
      }

      return data;

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

  return {
    scan,
    captureVideoFrame,
    analyzeImage,
    saveApiKey,    // Legacy no-op
    loadApiKey,    // Legacy: returns JWT token
    hasApiKey      // Returns true if JWT token exists
  };
})();
