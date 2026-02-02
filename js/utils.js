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

console.log('utils.js loaded');
