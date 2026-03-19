// ============================================
// UTILS.JS - Shared constants, state, and utilities
// ============================================

const API_URL = 'https://collectioncalc-docker.onrender.com';

// App state - shared across all modules
let currentMode = 'manual';
let extractedItems = [];
let uploadedFiles = [];
let currentSort = 'default';
let originalOrder = [];

// eBay integration state
let ebayUserId = localStorage.getItem('ebay_user_id') || generateUserId();
let ebayConnected = false;

// Auth state
let authToken = localStorage.getItem('cc_auth_token') || null;
let currentUser = null;
let pendingVerificationEmail = null;

// ============================================
// UTILITY FUNCTIONS
// ============================================

function generateUserId() {
    const id = 'user_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('ebay_user_id', id);
    return id;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }
    return headers;
}

// ============================================
// IMAGE PROCESSING UTILITIES
// ============================================

async function getExifOrientation(file) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const view = new DataView(e.target.result);
            if (view.getUint16(0, false) !== 0xFFD8) {
                resolve(1);
                return;
            }
            let offset = 2;
            while (offset < view.byteLength) {
                const marker = view.getUint16(offset, false);
                offset += 2;
                if (marker === 0xFFE1) {
                    if (view.getUint32(offset + 2, false) !== 0x45786966) {
                        resolve(1);
                        return;
                    }
                    const little = view.getUint16(offset + 8, false) === 0x4949;
                    const tags = view.getUint16(offset + 16, little);
                    for (let i = 0; i < tags; i++) {
                        const tagOffset = offset + 18 + i * 12;
                        if (view.getUint16(tagOffset, little) === 0x0112) {
                            const orientation = view.getUint16(tagOffset + 8, little);
                            console.log(`EXIF orientation: ${orientation}`);
                            resolve(orientation);
                            return;
                        }
                    }
                } else if ((marker & 0xFF00) !== 0xFF00) {
                    break;
                } else {
                    offset += view.getUint16(offset, false);
                }
            }
            resolve(1);
        };
        reader.onerror = () => resolve(1);
        reader.readAsArrayBuffer(file.slice(0, 65536));
    });
}

async function processImageForExtraction(file, manualRotation = 0) {
    const exifOrientation = await getExifOrientation(file);
    
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = reject;
        reader.onload = (e) => {
            const img = new Image();
            img.onerror = () => reject(new Error('Failed to load image'));
            img.onload = () => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                let width = img.width;
                let height = img.height;
                
                const exifRotation = {1: 0, 2: 0, 3: 180, 4: 180, 5: 90, 6: 90, 7: 270, 8: 270}[exifOrientation] || 0;
                let totalRotation = (exifRotation + manualRotation) % 360;
                
                console.log(`Original image: ${width}x${height}, EXIF rotation: ${exifRotation}°, manual: ${manualRotation}°`);
                
                // Auto-rotate landscape images to portrait (comics are always taller than wide)
                const postExifSwap = (exifRotation === 90 || exifRotation === 270);
                const effectiveWidth = postExifSwap ? height : width;
                const effectiveHeight = postExifSwap ? width : height;
                
                if (effectiveWidth > effectiveHeight && manualRotation === 0) {
                    console.log('Auto-rotating landscape to portrait');
                    totalRotation = (totalRotation + 90) % 360;
                }
                
                console.log(`Final rotation: ${totalRotation}°`);
                
                const swapDimensions = totalRotation === 90 || totalRotation === 270;
                if (swapDimensions) {
                    [width, height] = [height, width];
                }
                
                const minDimension = 1200;
                const maxDimension = 2400;
                
                const currentMax = Math.max(width, height);
                if (currentMax < minDimension) {
                    const upscale = minDimension / currentMax;
                    width = Math.round(width * upscale);
                    height = Math.round(height * upscale);
                    console.log(`Upscaling to ${width}x${height} for detail`);
                }
                
                if (currentMax > maxDimension) {
                    const downscale = maxDimension / currentMax;
                    width = Math.round(width * downscale);
                    height = Math.round(height * downscale);
                    console.log(`Downscaling to ${width}x${height}`);
                }
                
                const maxSizeBytes = 4.5 * 1024 * 1024;
                const qualities = [0.95, 0.90, 0.85, 0.80, 0.70, 0.60];
                const scales = [1, 0.95, 0.90, 0.85, 0.75];
                
                for (const scale of scales) {
                    const scaledWidth = Math.round(width * scale);
                    const scaledHeight = Math.round(height * scale);
                    canvas.width = scaledWidth;
                    canvas.height = scaledHeight;
                    
                    ctx.imageSmoothingEnabled = true;
                    ctx.imageSmoothingQuality = 'high';
                    
                    ctx.save();
                    ctx.translate(scaledWidth / 2, scaledHeight / 2);
                    ctx.rotate(totalRotation * Math.PI / 180);
                    if (swapDimensions) {
                        ctx.drawImage(img, -scaledHeight / 2, -scaledWidth / 2, scaledHeight, scaledWidth);
                    } else {
                        ctx.drawImage(img, -scaledWidth / 2, -scaledHeight / 2, scaledWidth, scaledHeight);
                    }
                    ctx.restore();
                    
                    for (const quality of qualities) {
                        const dataUrl = canvas.toDataURL('image/jpeg', quality);
                        const base64 = dataUrl.split(',')[1];
                        const sizeBytes = base64.length;
                        
                        if (sizeBytes <= maxSizeBytes) {
                            console.log(`Processed image: ${scaledWidth}x${scaledHeight}, ${Math.round(quality * 100)}% quality, ${(sizeBytes / 1024 / 1024).toFixed(2)}MB`);
                            resolve({ base64, mediaType: 'image/jpeg' });
                            return;
                        }
                    }
                }
                
                // Fallback: aggressive compression
                const fallbackWidth = Math.round(width * 0.6);
                const fallbackHeight = Math.round(height * 0.6);
                canvas.width = fallbackWidth;
                canvas.height = fallbackHeight;
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = 'high';
                ctx.save();
                ctx.translate(fallbackWidth / 2, fallbackHeight / 2);
                ctx.rotate(totalRotation * Math.PI / 180);
                if (swapDimensions) {
                    ctx.drawImage(img, -fallbackHeight / 2, -fallbackWidth / 2, fallbackHeight, fallbackWidth);
                } else {
                    ctx.drawImage(img, -fallbackWidth / 2, -fallbackHeight / 2, fallbackWidth, fallbackHeight);
                }
                ctx.restore();
                const dataUrl = canvas.toDataURL('image/jpeg', 0.5);
                const base64 = dataUrl.split(',')[1];
                console.log(`Processed image (fallback): ${canvas.width}x${canvas.height}, ${(base64.length / 1024 / 1024).toFixed(2)}MB`);
                resolve({ base64, mediaType: 'image/jpeg' });
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    });
}

// ============================================
// THINKING/LOADING UI
// ============================================

function showThinking(title, steps) {
    const thinking = document.getElementById('thinkingOverlay');
    const thinkingTitle = document.getElementById('thinkingTitle');
    const thinkingSteps = document.getElementById('thinkingSteps');
    
    thinkingTitle.textContent = title;
    thinkingSteps.innerHTML = steps.map((step, i) => 
        `<div class="thinking-step" id="thinkingStep${i}">${step}</div>`
    ).join('');
    
    thinking.classList.add('show');
    animateThinking();
}

function hideThinking() {
    document.getElementById('thinkingOverlay').classList.remove('show');
}

function animateThinking() {
    const steps = document.querySelectorAll('.thinking-step');
    let currentStep = 0;
    
    const interval = setInterval(() => {
        steps.forEach((step, i) => {
            step.classList.toggle('active', i === currentStep);
        });
        currentStep = (currentStep + 1) % steps.length;
        
        if (!document.getElementById('thinkingOverlay').classList.contains('show')) {
            clearInterval(interval);
        }
    }, 1500);
}

function showWaiting(completedTitle, value) {
    const overlay = document.getElementById('thinkingOverlay');
    const title = document.getElementById('thinkingTitle');
    const steps = document.getElementById('thinkingSteps');
    
    title.textContent = '⏳ Rate Limited';
    steps.innerHTML = `
        <div class="thinking-step active">
            ✅ ${completedTitle}: ${value}
        </div>
        <div class="thinking-step" id="waitCountdown">
            Waiting <span id="waitSeconds">30</span>s for next item...
        </div>
    `;
    overlay.classList.add('show');
}

function updateWaitingCountdown(seconds, nextItem) {
    const el = document.getElementById('waitSeconds');
    if (el) el.textContent = seconds;
}

function resetThinkingSteps() {
    const steps = document.querySelectorAll('.thinking-step');
    steps.forEach(step => step.classList.remove('active', 'completed'));
}

function updateProgress(percent, text) {
    document.getElementById('progressBar').style.width = percent + '%';
    document.getElementById('progressText').textContent = text;
}

// ============================================
// SIGNATURE IDENTIFICATION (shared across pages)
// ============================================

/**
 * Call /api/signatures/identify with a cover image.
 * @param {string} imageB64 - Base64-encoded cover image (no data URI prefix)
 * @param {string} mediaType - MIME type (default 'image/jpeg')
 * @param {number|null} comicId - Optional comic ID for DB recording
 * @returns {object} API response with signatures array
 */
async function identifySignatures(imageB64, mediaType = 'image/jpeg', comicId = null) {
    const payload = { image: imageB64, media_type: mediaType };
    if (comicId) payload.comic_id = comicId;

    const response = await fetch(`${API_URL}/api/signatures/identify`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({ error: 'Request failed' }));
        throw new Error(err.error || `HTTP ${response.status}`);
    }
    return await response.json();
}

/** Get color for confidence score display. */
function getSignatureConfidenceColor(confidence) {
    if (confidence >= 0.8) return 'var(--status-success)';
    if (confidence >= 0.6) return 'var(--status-warning)';
    if (confidence >= 0.3) return '#ef4444';
    return 'var(--text-muted)';
}

/**
 * Identify signatures using v2 orchestrator (3-pass Opus with metadata pre-filter).
 * @param {string} imageB64 - Base64-encoded cover image
 * @param {object} metadata - Optional: { publisher, title, year }
 * @returns {object} V2 API response with top5, flags, stability_scores, etc.
 */
async function identifySignaturesV2(imageB64, metadata = {}) {
    const formData = new FormData();
    formData.append('image', imageB64);
    if (metadata.publisher) formData.append('publisher', metadata.publisher);
    if (metadata.title) formData.append('title', metadata.title);
    if (metadata.year) {
        const yr = parseInt(metadata.year);
        if (yr) {
            formData.append('era_decade', yr < 1970 ? 'pre-1970' : `${Math.floor(yr / 10) * 10}s`);
        }
    }
    formData.append('signature_location', 'cover');

    const response = await fetch(`${API_URL}/api/signatures/v2/match`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${authToken}` },
        body: formData
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({ error: 'Request failed' }));
        if (response.status === 429 && err.error === 'sig_limit') {
            return { sig_limit: true, limit: err.limit, used: err.used, resets_at: err.resets_at };
        }
        throw new Error(err.error || `HTTP ${response.status}`);
    }
    return await response.json();
}

/**
 * Render v2 signature identification results into a container element.
 * @param {object} result - API response from /api/signatures/v2/match
 * @param {HTMLElement} container - Target element to render into
 */
function displaySignatureV2Results(result, container) {
    if (!result.top5 || result.top5.length === 0 || result.top5[0].confidence < 0.25) {
        container.innerHTML = `
            <div style="padding: 12px; background: rgba(99, 102, 241, 0.1); border-radius: 6px; border-left: 3px solid var(--brand-indigo);">
                <div style="font-size: 13px; color: var(--text-secondary);">No signatures detected on this cover.</div>
            </div>`;
        container.style.display = 'block';
        return;
    }

    const top = result.top5[0];
    const confColor = getSignatureConfidenceColor(top.confidence);
    const flags = result.flags || {};

    container.innerHTML = `
        <div style="margin-top: 12px; padding: 12px; background: rgba(16, 185, 129, 0.1); border-radius: 6px; border-left: 3px solid var(--status-success);">
            <div style="font-weight: 600; font-size: 12px; color: var(--status-success); margin-bottom: 10px;">
                Signature Identification (v2 — ${result.pass_count || 3} analysis passes)
            </div>
            <div style="margin-bottom: 12px; padding: 10px; background: rgba(0,0,0,0.2); border-radius: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div style="font-size: 14px; font-weight: 600;">${top.creator}</div>
                    <div style="padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; color: #fff; background: ${confColor};">
                        ${Math.round(top.confidence * 100)}% ${top.confidence_label || ''}
                    </div>
                </div>
                ${top.match_evidence ? `<div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;">${top.match_evidence.slice(0, 3).join(' · ')}</div>` : ''}
                ${flags.high_confusion_pair ? '<div style="font-size: 11px; color: #f59e0b; margin-top: 4px;">Similar to another creator — verify carefully</div>' : ''}
            </div>
            ${result.top5.length > 1 ? `
            <div style="font-size: 11px; margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.1);">
                <div style="color: var(--text-muted); margin-bottom: 4px;">Other candidates:</div>
                ${result.top5.slice(1, 4).map(c => `
                    <div style="display: flex; justify-content: space-between; padding: 1px 0;">
                        <span>${c.creator}</span>
                        <span style="color: ${getSignatureConfidenceColor(c.confidence)}; font-weight: 500;">${Math.round(c.confidence * 100)}%</span>
                    </div>
                `).join('')}
            </div>` : ''}
            <div style="font-size: 10px; color: var(--text-muted); border-top: 1px solid rgba(255,255,255,0.1); padding-top: 6px; margin-top: 6px;">
                For definitive authentication, submit to CGC Signature Series or CBCS Verified Signature
                · ${result.latency_ms ? `${(result.latency_ms / 1000).toFixed(1)}s` : ''}
            </div>
        </div>`;
    container.style.display = 'block';
}

/**
 * Render signature identification results into a container element.
 * @param {object} result - API response from /api/signatures/identify
 * @param {HTMLElement} container - Target element to render into
 */
function displaySignatureIdentifyResults(result, container) {
    if (!result.signatures || result.signatures.length === 0) {
        container.innerHTML = `
            <div style="padding: 12px; background: rgba(99, 102, 241, 0.1); border-radius: 6px; border-left: 3px solid var(--brand-indigo);">
                <div style="font-size: 13px; color: var(--text-secondary);">No signatures detected on this cover.</div>
            </div>`;
        container.style.display = 'block';
        return;
    }

    container.innerHTML = `
        <div style="margin-top: 12px; padding: 12px; background: rgba(16, 185, 129, 0.1); border-radius: 6px; border-left: 3px solid var(--status-success);">
            <div style="font-weight: 600; font-size: 12px; color: var(--status-success); margin-bottom: 10px;">
                Signature Identification — ${result.signatures_found} signature${result.signatures_found !== 1 ? 's' : ''} found
            </div>
            ${result.signatures.map(sig => `
                <div style="margin-bottom: 12px; padding: 10px; background: rgba(0,0,0,0.2); border-radius: 6px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div style="font-size: 14px; font-weight: 600;">
                            ${sig.best_match.artist_name || 'UNKNOWN'}
                        </div>
                        <div style="padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; color: #fff; background: ${getSignatureConfidenceColor(sig.best_match.confidence)};">
                            ${Math.round(sig.best_match.confidence * 100)}%${sig.best_match.is_confident ? ' ✓' : ''}
                        </div>
                    </div>
                    <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">
                        ${sig.location || ''} ${sig.ink_color ? '· ' + sig.ink_color : ''} ${sig.style ? '· ' + sig.style : ''}
                    </div>
                    ${sig.candidates && sig.candidates.length > 1 ? `
                    <div style="font-size: 11px; margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.1);">
                        <div style="color: var(--text-muted); margin-bottom: 4px;">Other candidates:</div>
                        ${sig.candidates.slice(1).map(c => `
                            <div style="display: flex; justify-content: space-between; padding: 1px 0;">
                                <span>${c.artist_name}</span>
                                <span style="color: ${getSignatureConfidenceColor(c.confidence)}; font-weight: 500;">${Math.round(c.confidence * 100)}%</span>
                            </div>
                        `).join('')}
                    </div>` : ''}
                    ${sig.candidates && sig.candidates[0] && sig.candidates[0].reasoning ? `
                    <div style="font-size: 11px; color: var(--text-secondary); margin-top: 6px; font-style: italic;">
                        ${sig.candidates[0].reasoning}
                    </div>` : ''}
                </div>
            `).join('')}
            <div style="font-size: 10px; color: var(--text-muted); border-top: 1px solid rgba(255,255,255,0.1); padding-top: 6px; margin-top: 4px;">
                For definitive authentication, submit to CGC Signature Series or CBCS Verified Signature
                ${result.references_used ? ` · Matched against ${result.references_used} reference artists` : ''}
            </div>
        </div>`;
    container.style.display = 'block';
}

/**
 * Fetch an image from a URL and return base64 data.
 * Used by collection page to convert R2 photo URLs.
 */
async function fetchImageAsBase64(url) {
    const response = await fetch(url);
    const blob = await response.blob();
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const dataUri = reader.result;
            const b64 = dataUri.split(',')[1];
            const mediaType = dataUri.split(';')[0].split(':')[1] || 'image/jpeg';
            resolve({ base64: b64, mediaType });
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

console.log('utils.js loaded');
