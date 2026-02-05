// ============================================
// GRADE MY COMIC MODE - JavaScript
// Add this to the END of app.js
// ============================================

// Device detection
const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

// Grading state
let gradingState = {
    currentStep: 1,
    photos: {
        1: null,  // front cover (required)
        2: null,  // spine
        3: null,  // back
        4: null   // centerfold
    },
    additionalPhotos: [],
    extractedData: null,  // from front cover
    defectsByArea: {},
    finalGrade: null,
    confidence: 0
};

// Thinking progress messages (shown during valuation)
const thinkingMessages = [
    // Identification Phase
    "Confirming comic identification...",
    "Checking for variants and printings...",
    "Verifying issue type (regular vs. annual)...",
    // Market Research Phase
    "Searching recent eBay sold listings...",
    "Filtering for comparable condition...",
    "Analyzing sale prices from the past 90 days...",
    "Checking for price outliers...",
    // Valuation Phase
    "Calculating fair market value for raw copy...",
    "Estimating slabbed value with CGC premium...",
    "Factoring in current grading costs...",
    "Comparing grading tiers (Modern, Economy, Express)...",
    // Recommendation Phase
    "Calculating potential return on investment...",
    "Weighing grading cost vs. value increase...",
    "Preparing your Slab Report..."
];

let thinkingInterval = null;
let thinkingIndex = 0;

function startThinkingAnimation(elementId) {
    thinkingIndex = 0;
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // Initial message
    element.innerHTML = `
        <div class="thinking-box" style="display: flex; align-items: center; gap: 12px; padding: 16px; background: rgba(79, 70, 229, 0.1); border-radius: 8px; border: 1px solid rgba(79, 70, 229, 0.3);">
            <div class="thinking-indicator" style="width: 20px; height: 20px; border: 2px solid rgba(79, 70, 229, 0.3); border-top-color: var(--brand-indigo, #4f46e5); border-radius: 50%; animation: spin 1s linear infinite;"></div>
            <span class="thinking-text" style="color: var(--text-secondary, #a1a1aa); font-size: 0.95rem; transition: opacity 0.15s ease;">${thinkingMessages[0]}</span>
        </div>
        <style>
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        </style>
    `;
    
    // Cycle through messages
    thinkingInterval = setInterval(() => {
        thinkingIndex = (thinkingIndex + 1) % thinkingMessages.length;
        const textEl = element.querySelector('.thinking-text');
        if (textEl) {
            textEl.style.opacity = '0';
            setTimeout(() => {
                textEl.textContent = thinkingMessages[thinkingIndex];
                textEl.style.opacity = '1';
            }, 150);
        }
    }, 2000); // Change message every 2 seconds
}

function stopThinkingAnimation() {
    if (thinkingInterval) {
        clearInterval(thinkingInterval);
        thinkingInterval = null;
    }
}

// Animated dots for "Analyzing" text
let dotsInterval = null;
let dotsCount = 1;

function startDotsAnimation(element, baseText = 'Analyzing') {
    dotsCount = 1;
    if (typeof element === 'string') {
        element = document.getElementById(element);
    }
    if (!element) return;
    
    element.textContent = baseText + '.';
    
    dotsInterval = setInterval(() => {
        dotsCount = (dotsCount % 3) + 1;
        element.textContent = baseText + '.'.repeat(dotsCount);
    }, 400); // Cycle every 400ms
}

function stopDotsAnimation() {
    if (dotsInterval) {
        clearInterval(dotsInterval);
        dotsInterval = null;
    }
}

// Initialize grading mode on page load
document.addEventListener('DOMContentLoaded', () => {
    initGradingMode();
});

function initGradingMode() {
    // Update text based on device
    const uploadTitles = document.querySelectorAll('.grading-upload .upload-title');
    uploadTitles.forEach(el => {
        if (!isMobile) {
            el.textContent = el.textContent.replace('Tap to photograph', 'Click to upload');
        }
    });
    
    // Add capture attribute for mobile (defaults to camera)
    if (isMobile) {
        document.querySelectorAll('#gradingMode input[type="file"]').forEach(input => {
            input.setAttribute('capture', 'environment');
        });
    }
}

// Photo Tips Modal
function togglePhotoTips() {
    const modal = document.getElementById('photoTipsModal');
    modal.classList.add('show');
}

function closePhotoTips() {
    const modal = document.getElementById('photoTipsModal');
    modal.classList.remove('show');
}

// Handle grading photo upload
async function handleGradingPhoto(step, files) {
    if (!files || files.length === 0) return;
    
    const file = files[0];
    // DEBUG: Log file info
    console.log('DEBUG handleGradingPhoto: file name:', file.name, 'type:', file.type, 'size:', file.size);
    
    const uploadArea = document.getElementById(`gradingUpload${step}`);
    const preview = document.getElementById(`gradingPreview${step}`);
    const previewImg = document.getElementById(`gradingImg${step}`);
    const previewInfo = document.getElementById(`gradingInfo${step}`);
    const feedback = document.getElementById(`gradingFeedback${step}`);
    const feedbackText = document.getElementById(`gradingFeedbackText${step}`);
    const nextBtn = document.getElementById(`gradingNext${step}`);
    
    // Show loading state
    uploadArea.style.display = 'none';
    feedback.style.display = 'flex';
    feedback.className = 'grading-feedback';
    startDotsAnimation(feedbackText, 'Analyzing image');
    
    try {
        // Process image
        const processed = await processImageForExtraction(file, 0);
        
        // Show preview
        previewImg.src = `data:${processed.mediaType};base64,${processed.base64}`;
        
        // Store photo
        gradingState.photos[step] = {
            base64: processed.base64,
            mediaType: processed.mediaType
        };
        
        if (step === 1) {
            // Front cover - do full extraction + quality check
            let result = await analyzeGradingPhoto(step, processed);
            
            // Check if image is upside-down and auto-correct
            if (result.is_upside_down) {
                console.log('Image detected as upside-down, auto-rotating 180°');
                stopDotsAnimation();
                feedbackText.textContent = 'Auto-correcting orientation...';
                
                // Rotate 180°
                const img = new Image();
                await new Promise((resolve, reject) => {
                    img.onload = resolve;
                    img.onerror = reject;
                    img.src = `data:${processed.mediaType};base64,${processed.base64}`;
                });
                
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.translate(canvas.width / 2, canvas.height / 2);
                ctx.rotate(Math.PI); // 180 degrees
                ctx.drawImage(img, -img.width / 2, -img.height / 2);
                
                const rotatedDataUrl = canvas.toDataURL('image/jpeg', 0.92);
                const rotatedBase64 = rotatedDataUrl.split(',')[1];
                
                // Update stored photo and preview
                processed.base64 = rotatedBase64;
                gradingState.photos[step] = {
                    base64: rotatedBase64,
                    mediaType: 'image/jpeg'
                };
                previewImg.src = rotatedDataUrl;
                
                // Re-analyze with corrected orientation
                result = await analyzeGradingPhoto(step, { base64: rotatedBase64, mediaType: 'image/jpeg' });
            }
            
            if (result.quality_issue) {
                // Quality problem - show feedback, allow retry
                stopDotsAnimation();
                feedback.className = 'grading-feedback';
                feedbackText.textContent = result.quality_message;
                feedback.style.display = 'flex';
                preview.style.display = 'block';
                nextBtn.disabled = false; // Let them continue anyway
            } else {
                stopDotsAnimation();
                feedback.style.display = 'none';
            }
            
            // Store extracted data
            gradingState.extractedData = result;
            
            // Show preview with extracted info (with edit button)
            previewInfo.innerHTML = `
                <div class="extracted-title">
                    <span id="extractedTitleText">${result.title || 'Unknown'} #${result.issue || '?'}</span>
                    <button type="button" class="btn-edit-inline" onclick="editComicInfo()">✏️ Edit</button>
                </div>
                <div id="editComicForm" style="display: none; margin: 10px 0;">
                    <input type="text" id="editTitle" placeholder="Title" value="${result.title || ''}" style="margin-bottom: 8px; width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary);">
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <input type="text" id="editIssue" placeholder="Issue #" value="${result.issue || ''}" style="width: 80px; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary);">
                        <button type="button" class="btn-secondary btn-small" onclick="saveComicEdit()">Save</button>
                        <button type="button" class="btn-secondary btn-small" onclick="cancelComicEdit()">Cancel</button>
                    </div>
                </div>
                <div class="extracted-grade">Cover condition: ${result.suggested_grade || 'Analyzing...'}</div>
                ${result.defects && result.defects.length > 0 ? 
                    `<div class="extracted-defects">⚠️ ${result.defects.join(', ')}</div>` : 
                    '<div class="extracted-defects" style="color: var(--status-success);">✓ No major defects detected</div>'}
            `;
            
            // Store defects
            gradingState.defectsByArea['Front Cover'] = result.defects || [];
            
            // Update comic ID banner for subsequent steps
            updateComicIdBanners(result);
            
        } else {
            // Steps 2-4: Analyze for defects with auto-rotation
            let result = await analyzeGradingPhoto(step, processed);
            
            // Check if image is upside-down and auto-correct
            if (result.is_upside_down) {
                console.log(`Step ${step}: Image detected as upside-down, auto-rotating 180°`);
                stopDotsAnimation();
                feedbackText.textContent = 'Auto-correcting orientation...';
                
                // Rotate 180°
                const img = new Image();
                await new Promise((resolve, reject) => {
                    img.onload = resolve;
                    img.onerror = reject;
                    img.src = `data:${processed.mediaType};base64,${processed.base64}`;
                });
                
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.translate(canvas.width / 2, canvas.height / 2);
                ctx.rotate(Math.PI); // 180 degrees
                ctx.drawImage(img, -img.width / 2, -img.height / 2);
                
                const rotatedDataUrl = canvas.toDataURL('image/jpeg', 0.92);
                const rotatedBase64 = rotatedDataUrl.split(',')[1];
                
                // Update stored photo and preview
                processed.base64 = rotatedBase64;
                gradingState.photos[step] = {
                    base64: rotatedBase64,
                    mediaType: 'image/jpeg'
                };
                previewImg.src = rotatedDataUrl;
                
                // Re-analyze with corrected orientation
                result = await analyzeGradingPhoto(step, { base64: rotatedBase64, mediaType: 'image/jpeg' });
            }
            
            if (result.quality_issue) {
                stopDotsAnimation();
                feedback.className = 'grading-feedback';
                feedbackText.textContent = result.quality_message;
                feedback.style.display = 'flex';
            } else {
                stopDotsAnimation();
                feedback.style.display = 'none';
            }
            
            // Show defects found
            const areaNames = { 2: 'Spine', 3: 'Back Cover', 4: 'Centerfold' };
            const areaName = areaNames[step];
            
            previewInfo.innerHTML = `
                <div class="extracted-grade">${areaName} condition: ${result.suggested_grade || 'Good'}</div>
                ${result.defects && result.defects.length > 0 ? 
                    `<div class="extracted-defects">⚠️ ${result.defects.join(', ')}</div>` : 
                    '<div class="extracted-defects" style="color: var(--status-success);">✓ No defects found</div>'}
            `;
            
            // Store defects
            gradingState.defectsByArea[areaName] = result.defects || [];
        }
        
        preview.style.display = 'block';
        nextBtn.disabled = false;
        
    } catch (error) {
        console.error('Error analyzing photo:', error);
        stopDotsAnimation();
        // DEBUG: Show actual error on mobile
        alert('DEBUG ERROR: ' + error.message + '\n\nStack: ' + (error.stack || 'no stack'));
        feedback.className = 'grading-feedback error';
        feedbackText.textContent = 'Error analyzing image. Please try again.';
        feedback.style.display = 'flex';
        uploadArea.style.display = 'block';
    }
}

// Edit comic info functions
function editComicInfo() {
    document.getElementById('extractedTitleText').style.display = 'none';
    document.querySelector('.btn-edit-inline').style.display = 'none';
    document.getElementById('editComicForm').style.display = 'block';
}

function saveComicEdit() {
    const newTitle = document.getElementById('editTitle').value;
    const newIssue = document.getElementById('editIssue').value;
    
    // Update state
    gradingState.extractedData.title = newTitle;
    gradingState.extractedData.issue = newIssue;
    
    // Update display
    document.getElementById('extractedTitleText').textContent = `${newTitle} #${newIssue}`;
    document.getElementById('extractedTitleText').style.display = 'inline';
    document.querySelector('.btn-edit-inline').style.display = 'inline';
    document.getElementById('editComicForm').style.display = 'none';
    
    // Update banners in steps 2-4
    updateComicIdBanners(gradingState.extractedData);
}

function cancelComicEdit() {
    document.getElementById('extractedTitleText').style.display = 'inline';
    document.querySelector('.btn-edit-inline').style.display = 'inline';
    document.getElementById('editComicForm').style.display = 'none';
}

// Analyze a grading photo with Claude
async function analyzeGradingPhoto(step, processed) {
    // DEBUG: Check authToken
    console.log('DEBUG: authToken exists:', !!authToken, 'length:', authToken ? authToken.length : 0);
    if (!authToken) {
        alert('DEBUG: No authToken! User may not be logged in.');
    }
    
    // Step 1: Use backend /api/extract for full extraction (single source of truth)
    if (step === 1) {
        const response = await fetch(`${API_URL}/api/extract`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                image: processed.base64,
                media_type: processed.mediaType
            })
        });
        
        console.log('DEBUG API /api/extract response status:', response.status);
        if (!response.ok) {
            const errorText = await response.text();
            alert('DEBUG API Error: Status ' + response.status + '\n\n' + errorText.substring(0, 500));
            throw new Error('API returned ' + response.status);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Extraction failed');
        }
        
        // Return the extracted data (map to expected format)
        const extracted = data.extracted;
        return {
            // Identification
            title: extracted.title,
            issue: extracted.issue,
            publisher: extracted.publisher,
            year: extracted.year,
            variant: extracted.variant,
            // New fields now available from backend
            edition: extracted.edition,
            printing: extracted.printing,
            cover: extracted.cover,
            is_facsimile: extracted.is_facsimile,
            barcode_digits: extracted.barcode_digits,
            issue_type: extracted.issue_type,
            // Condition
            suggested_grade: extracted.suggested_grade,
            defects: extracted.defects || [],
            grade_reasoning: extracted.grade_reasoning,
            // Signatures
            signature_detected: extracted.signatures && extracted.signatures.length > 0,
            signature_analysis: extracted.signatures ? extracted.signatures.join('; ') : null,
            signatures: extracted.signatures || [],
            // Orientation
            is_upside_down: extracted.is_upside_down || false
        };
    }
    
    // Steps 2-4: Use existing prompts for spine, back, centerfold
    const prompts = {
        2: `Analyze this comic book SPINE image for condition defects. Return a JSON object with:

IMAGE ORIENTATION CHECK (do this FIRST):
- is_upside_down: boolean - Is this image upside-down? Check if any text on the spine is inverted.

IMAGE QUALITY CHECK:
- quality_issue: boolean - Is the spine clearly visible and in focus?
- quality_message: Feedback if quality is poor

CONDITION ASSESSMENT:
- suggested_grade: Based on spine alone (MT, NM, VF, FN, VG, G, FR, PR)
- defects: Array of spine-specific defects (e.g., "Spine roll", "Stress marks", "Color breaking tick", "Spine split 1 inch", "Bindery tear")
- grade_reasoning: Brief explanation

Return ONLY valid JSON, no markdown.`,

        3: `Analyze this comic book BACK COVER image for condition defects. Return a JSON object with:

IMAGE ORIENTATION CHECK (do this FIRST):
- is_upside_down: boolean - Is this image upside-down? Check if any text (ads, barcodes, price) is inverted.

IMAGE QUALITY CHECK:
- quality_issue: boolean - Is the back cover clearly visible and in focus?
- quality_message: Feedback if quality is poor

CONDITION ASSESSMENT:
- suggested_grade: Based on back cover alone (MT, NM, VF, FN, VG, G, FR, PR)
- defects: Array of defects (e.g., "Staining", "Crease", "Writing/stamp", "Subscription label", "Corner wear")
- grade_reasoning: Brief explanation

Return ONLY valid JSON, no markdown.`,

        4: `Analyze this comic book CENTERFOLD/STAPLES image. Return a JSON object with:

IMAGE ORIENTATION CHECK (do this FIRST):
- is_upside_down: boolean - Is this image upside-down? Check if any visible text or the staple orientation suggests the image is inverted.

IMAGE QUALITY CHECK:
- quality_issue: boolean - Are the staples and centerfold clearly visible?
- quality_message: Feedback if quality is poor

CONDITION ASSESSMENT:
- suggested_grade: Based on interior (MT, NM, VF, FN, VG, G, FR, PR)
- defects: Array of defects (e.g., "Rusty staples", "Loose centerfold", "Detached centerfold", "Re-stapled", "Interior staining", "Brittle pages")
- grade_reasoning: Brief explanation

Return ONLY valid JSON, no markdown.`
    };
    
    const response = await fetch(`${API_URL}/api/messages`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
            model: 'claude-sonnet-4-20250514',
            max_tokens: 1024,
            messages: [{
                role: 'user',
                content: [
                    {
                        type: 'image',
                        source: {
                            type: 'base64',
                            media_type: processed.mediaType,
                            data: processed.base64
                        }
                    },
                    {
                        type: 'text',
                        text: prompts[step]
                    }
                ]
            }]
        })
    });
    
    // DEBUG: Log response status
    console.log('DEBUG API response status:', response.status);
    if (!response.ok) {
        const errorText = await response.text();
        alert('DEBUG API Error: Status ' + response.status + '\n\n' + errorText.substring(0, 500));
        throw new Error('API returned ' + response.status);
    }
    
    const data = await response.json();
    
    if (data.error) {
        throw new Error(data.error.message || 'API error');
    }
    
    // Parse JSON response
    let resultText = data.content[0].text;
    // Clean up any markdown code blocks
    resultText = resultText.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
    
    try {
        return JSON.parse(resultText);
    } catch (e) {
        console.error('Failed to parse response:', resultText);
        return { 
            quality_issue: false,
            suggested_grade: 'VF',
            defects: []
        };
    }
}

// Update comic ID banners in steps 2-4
function updateComicIdBanners(extractedData) {
    const bannerHTML = `
        <img class="comic-thumb" src="data:${gradingState.photos[1].mediaType};base64,${gradingState.photos[1].base64}" alt="Cover">
        <div class="comic-info">
            <div class="comic-title">${extractedData.title || 'Unknown'} #${extractedData.issue || '?'}</div>
            <div class="comic-details">${extractedData.publisher || ''} ${extractedData.year || ''}</div>
        </div>
    `;
    
    [2, 3, 4].forEach(step => {
        const banner = document.getElementById(`gradingComicId${step}`);
        if (banner) {
            banner.innerHTML = bannerHTML;
            banner.style.display = 'flex';
        }
    });
}

// Show loading state on comic ID banners during re-analysis
function setComicIdBannersLoading() {
    const loadingHTML = `
        <div class="comic-info" style="font-style: italic; color: var(--text-muted);">
            Analyzing...
        </div>
    `;
    
    [2, 3, 4].forEach(step => {
        const banner = document.getElementById(`gradingComicId${step}`);
        if (banner) {
            banner.innerHTML = loadingHTML;
        }
    });
}

// Retake a photo
function retakeGradingPhoto(step) {
    const uploadArea = document.getElementById(`gradingUpload${step}`);
    const preview = document.getElementById(`gradingPreview${step}`);
    const feedback = document.getElementById(`gradingFeedback${step}`);
    const nextBtn = document.getElementById(`gradingNext${step}`);
    const cameraInput = document.getElementById(`gradingCamera${step}`);
    const galleryInput = document.getElementById(`gradingGallery${step}`);
    
    // Reset state
    gradingState.photos[step] = null;
    
    // Reset UI
    preview.style.display = 'none';
    feedback.style.display = 'none';
    uploadArea.style.display = 'flex';
    nextBtn.disabled = true;
    
    // Clear both inputs
    if (cameraInput) cameraInput.value = '';
    if (galleryInput) galleryInput.value = '';
}

// Debounce timer for rotation analysis
let rotationDebounceTimer = null;

// Rotate photo 90 degrees clockwise and re-analyze
async function rotateGradingPhoto(step) {
    const photo = gradingState.photos[step];
    if (!photo || !photo.base64) {
        console.error('No photo to rotate');
        return;
    }
    
    const feedback = document.getElementById(`gradingFeedback${step}`);
    const feedbackText = document.getElementById(`gradingFeedbackText${step}`);
    const previewImg = document.getElementById(`gradingImg${step}`);
    const previewInfo = document.getElementById(`gradingInfo${step}`);
    const nextBtn = document.getElementById(`gradingNext${step}`);
    
    // Cancel any pending analysis
    if (rotationDebounceTimer) {
        clearTimeout(rotationDebounceTimer);
        rotationDebounceTimer = null;
    }
    
    // Immediately rotate the image visually
    try {
        const img = new Image();
        await new Promise((resolve, reject) => {
            img.onload = resolve;
            img.onerror = reject;
            img.src = `data:${photo.mediaType};base64,${photo.base64}`;
        });
        
        // Create rotated canvas
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Swap dimensions for 90° rotation
        canvas.width = img.height;
        canvas.height = img.width;
        
        // Rotate 90° clockwise
        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.rotate(90 * Math.PI / 180);
        ctx.drawImage(img, -img.width / 2, -img.height / 2);
        
        // Get new base64
        const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
        const newBase64 = dataUrl.split(',')[1];
        
        // Update stored photo immediately
        gradingState.photos[step] = {
            base64: newBase64,
            mediaType: 'image/jpeg',
            rotation: ((photo.rotation || 0) + 90) % 360
        };
        
        // Update preview immediately
        previewImg.src = dataUrl;
        
        // Show loading state
        feedback.style.display = 'flex';
        feedback.className = 'grading-feedback';
        feedbackText.textContent = 'Rotate again or wait to analyze...';
        
        // Clear the old title/info while waiting
        if (step === 1) {
            previewInfo.innerHTML = `<div style="color: var(--text-muted); font-style: italic;">Analyzing...</div>`;
            setComicIdBannersLoading();
        }
        
        // Debounce: wait 2.5 seconds before analyzing (in case user rotates again)
        rotationDebounceTimer = setTimeout(async () => {
            feedbackText.textContent = 'Analyzing...';
            await performRotationAnalysis(step, newBase64, feedback, feedbackText, previewInfo, nextBtn);
        }, 2500);
        
    } catch (error) {
        console.error('Error rotating photo:', error);
        feedbackText.textContent = 'Error rotating image. Please try retaking the photo.';
    }
}

// Perform the actual analysis after debounce
async function performRotationAnalysis(step, base64, feedback, feedbackText, previewInfo, nextBtn) {
    try {
        if (step === 1) {
            const result = await analyzeGradingPhoto(step, { base64, mediaType: 'image/jpeg' });
            
            // Update extracted data
            gradingState.extractedData = result;
            
            // Update comic ID banners on all subsequent steps
            updateComicIdBanners(gradingState.extractedData);
            
            // Update title display
            previewInfo.innerHTML = `
                <div class="extracted-title">
                    <span id="extractedTitleText">${result.title || 'Unknown'} #${result.issue || '?'}</span>
                    <button type="button" class="btn-edit-inline" onclick="editComicInfo()">✏️ Edit</button>
                </div>
                <div id="editComicForm" style="display: none; margin: 10px 0;">
                    <input type="text" id="editTitle" placeholder="Title" value="${result.title || ''}" style="margin-bottom: 8px; width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary);">
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <span>#</span>
                        <input type="text" id="editIssue" placeholder="Issue" value="${result.issue || ''}" style="width: 80px; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary);">
                        <button type="button" class="btn-primary btn-small" onclick="saveComicInfo()">Save</button>
                        <button type="button" class="btn-secondary btn-small" onclick="cancelComicEdit()">Cancel</button>
                    </div>
                </div>
                <div style="font-size: 0.9rem; color: var(--text-muted); margin-top: 4px;">
                    Cover condition: ${result.suggested_grade || 'Analyzing...'}
                </div>
                ${result.defects && result.defects.length > 0 ? `
                    <div style="font-size: 0.85rem; color: var(--brand-amber); margin-top: 4px;">
                        ⚠️ ${result.defects.join(', ')}
                    </div>
                ` : ''}
            `;
            
            // Store defects
            gradingState.defectsByArea['Front Cover'] = result.defects || [];
            
            if (result.quality_issue) {
                feedbackText.textContent = result.quality_message;
            } else {
                feedback.style.display = 'none';
            }
        } else {
            // For other steps, re-analyze for defects
            const result = await analyzeGradingPhoto(step, { base64, mediaType: 'image/jpeg' });
            const areaName = {2: 'Spine', 3: 'Back Cover', 4: 'Centerfold/Interior'}[step];
            gradingState.defectsByArea[areaName] = result.defects || [];
            
            // Update info display
            previewInfo.innerHTML = result.defects && result.defects.length > 0 
                ? `<div style="font-size: 0.85rem; color: var(--brand-amber);">⚠️ ${result.defects.join(', ')}</div>`
                : `<div style="font-size: 0.85rem; color: var(--brand-green);">✓ No defects detected</div>`;
            
            feedback.style.display = 'none';
        }
        
        nextBtn.disabled = false;
        
    } catch (error) {
        console.error('Error analyzing rotated photo:', error);
        feedbackText.textContent = 'Error analyzing image. Please try again.';
    }
}

// Navigate to next step
function nextGradingStep(currentStep) {
    // Mark current step as completed
    const currentStepEl = document.getElementById(`gradingStep${currentStep}`);
    currentStepEl.classList.remove('active');
    currentStepEl.classList.add('completed');
    
    // Hide current content
    document.getElementById(`gradingContent${currentStep}`).classList.remove('active');
    
    // Show next step
    const nextStep = currentStep + 1;
    const nextStepEl = document.getElementById(`gradingStep${nextStep}`);
    nextStepEl.classList.add('active');
    document.getElementById(`gradingContent${nextStep}`).classList.add('active');
    
    gradingState.currentStep = nextStep;
}

// Skip a step
function skipGradingStep(step) {
    // Mark as skipped
    const stepEl = document.getElementById(`gradingStep${step}`);
    stepEl.classList.remove('active');
    stepEl.classList.add('skipped');
    
    // Hide current content
    document.getElementById(`gradingContent${step}`).classList.remove('active');
    
    // Determine next step
    let nextStep;
    if (step === 4) {
        // Go to report
        nextStep = 5;
        generateGradeReport();
    } else {
        nextStep = step + 1;
    }
    
    // Show next step
    const nextStepEl = document.getElementById(`gradingStep${nextStep}`);
    nextStepEl.classList.add('active');
    document.getElementById(`gradingContent${nextStep}`).classList.add('active');
    
    gradingState.currentStep = nextStep;
}

// Handle additional photos
async function handleAdditionalPhoto(files) {
    if (!files || files.length === 0) return;
    
    const file = files[0];
    
    try {
        // Process image with EXIF rotation (same as other photos)
        const processed = await processImageForExtraction(file, 0);
        
        gradingState.additionalPhotos.push({
            base64: processed.base64,
            mediaType: processed.mediaType
        });
        
        // Update thumbnail display
        renderAdditionalPhotos();
    } catch (error) {
        console.error('Error processing additional photo:', error);
        // Fallback to direct read if processing fails
        const reader = new FileReader();
        reader.onload = (e) => {
            const base64 = e.target.result.split(',')[1];
            gradingState.additionalPhotos.push({
                base64: base64,
                mediaType: file.type
            });
            renderAdditionalPhotos();
        };
        reader.readAsDataURL(file);
    }
    
    // Clear input
    document.getElementById('additionalPhotoInput').value = '';
}

function renderAdditionalPhotos() {
    const container = document.getElementById('additionalPhotos');
    container.innerHTML = gradingState.additionalPhotos.map((photo, idx) => `
        <div style="position: relative; display: inline-block;">
            <img class="additional-photo-thumb" src="data:${photo.mediaType};base64,${photo.base64}" alt="Additional ${idx + 1}">
            <button class="additional-photo-remove" onclick="removeAdditionalPhoto(${idx})">×</button>
        </div>
    `).join('');
}

function removeAdditionalPhoto(idx) {
    gradingState.additionalPhotos.splice(idx, 1);
    renderAdditionalPhotos();
}

// Generate the final grade report
async function generateGradeReport() {
    // Show report section
    document.getElementById(`gradingContent4`).classList.remove('active');
    document.getElementById(`gradingStep4`).classList.remove('active');
    document.getElementById(`gradingStep4`).classList.add('completed');
    document.getElementById(`gradingStep5`).classList.add('active');
    document.getElementById(`gradingContent5`).classList.add('active');
    
    gradingState.currentStep = 5;
    
    // Show loading state with progress steps (with null checks)
    const gradeResultBig = document.getElementById('gradeResultBig');
    const gradeResultLabel = document.getElementById('gradeResultLabel');
    const gradePhotosUsed = document.getElementById('gradePhotosUsed');
    const defectsList = document.getElementById('defectsList');
    const recommendationValues = document.getElementById('recommendationValues');
    const recommendationVerdict = document.getElementById('recommendationVerdict');
    
    if (gradeResultBig) gradeResultBig.textContent = '...';
    if (gradeResultLabel) {
        gradeResultLabel.textContent = 'Analyzing photos.';
        startDotsAnimation(gradeResultLabel, 'Analyzing photos');
    }
    if (gradePhotosUsed) gradePhotosUsed.innerHTML = '<span style="color: var(--text-muted);">Processing images...</span>';
    if (defectsList) defectsList.innerHTML = '<span style="color: var(--text-muted);">Finding defects...</span>';
    if (recommendationValues) recommendationValues.innerHTML = '';
    if (recommendationVerdict) recommendationVerdict.innerHTML = '<p style="text-align: center; color: var(--text-muted);">Calculating value...</p>';
    
    // Build multi-image prompt
    const imageContent = [];
    const photoLabels = [];
    
    // Add all captured photos
    Object.entries(gradingState.photos).forEach(([step, photo]) => {
        if (photo) {
            const labels = { 1: 'Front Cover', 2: 'Spine', 3: 'Back Cover', 4: 'Centerfold' };
            imageContent.push({
                type: 'image',
                source: {
                    type: 'base64',
                    media_type: photo.mediaType,
                    data: photo.base64
                }
            });
            photoLabels.push(labels[step]);
        }
    });
    
    // Add additional photos
    gradingState.additionalPhotos.forEach((photo, idx) => {
        imageContent.push({
            type: 'image',
            source: {
                type: 'base64',
                media_type: photo.mediaType,
                data: photo.base64
            }
        });
        photoLabels.push(`Additional ${idx + 1}`);
    });
    
    // Calculate photos used for confidence
    const photosUsed = Object.values(gradingState.photos).filter(p => p !== null).length;
    const baseConfidence = { 1: 65, 2: 78, 3: 88, 4: 94 }[photosUsed] || 65;
    const additionalBoost = Math.min(gradingState.additionalPhotos.length * 2, 4);
    const confidence = Math.min(baseConfidence + additionalBoost, 98);
    
    try {
        // Send all images for comprehensive grading
        const response = await fetch(`${API_URL}/api/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                model: 'claude-sonnet-4-20250514',
                max_tokens: 2048,
                messages: [{
                    role: 'user',
                    content: [
                        ...imageContent,
                        {
                            type: 'text',
                            text: `You are grading this comic book using ${photoLabels.length} photos: ${photoLabels.join(', ')}.

The comic has been identified as: ${gradingState.extractedData?.title || 'Unknown'} #${gradingState.extractedData?.issue || '?'}

Based on ALL images provided, give a comprehensive grade assessment.

Return a JSON object with these EXACT top-level keys:

{
  "title": "Series name",
  "issue": "Issue number",
  "publisher": "Publisher",
  "year": "Year if visible",
  "final_grade": 9.4,
  "grade_label": "NM",
  "grade_reasoning": "Detailed explanation",
  "front_defects": ["array", "of", "defects"],
  "spine_defects": ["array", "of", "defects"],
  "back_defects": ["array", "of", "defects"],
  "interior_defects": ["array", "of", "defects"],
  "other_defects": ["array", "of", "defects"],
  "signature_detected": false,
  "signature_info": null
}

Use numeric grades like 9.8, 9.4, 9.0, 8.5, 8.0, 7.5, 7.0, 6.5, 6.0, 5.5, 5.0, 4.5, 4.0, 3.0, 2.0, 1.0.
Grade labels: MT, NM+, NM, NM-, VF+, VF, VF-, FN+, FN, FN-, VG+, VG, VG-, G, FR, PR.

Return ONLY valid JSON, no markdown, no nested objects.`
                        }
                    ]
                }]
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error.message || 'API error');
        }
        
        let resultText = data.content[0].text;
        resultText = resultText.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
        
        const result = JSON.parse(resultText);
        gradingState.finalGrade = result;
        gradingState.confidence = confidence;
        
        // Update UI
        renderGradeReport(result, confidence, photoLabels);
        
        // Get valuation for "should you grade?" calculation
        await calculateGradingRecommendation(result);
        
    } catch (error) {
        console.error('Error generating grade report:', error);
        stopDotsAnimation();
        const bigEl = document.getElementById('gradeResultBig');
        const labelEl = document.getElementById('gradeResultLabel');
        if (bigEl) bigEl.textContent = 'Error';
        if (labelEl) labelEl.textContent = 'Failed to analyze. Please try again.';
    }
}

// Render the grade report
function renderGradeReport(result, confidence, photoLabels) {
    // Stop any running animations
    stopDotsAnimation();
    
    // Handle both flat and nested response structures from Claude
    const comic = result['COMIC IDENTIFICATION'] || result;
    const grade = result['COMPREHENSIVE GRADE'] || result;
    const defects = result['DEFECTS BY AREA'] || result;
    const sig = result['SIGNATURE'] || result;
    
    // Comic info - prefer user-edited data
    const displayTitle = gradingState.extractedData?.title || comic.title || 'Unknown';
    const displayIssue = gradingState.extractedData?.issue || comic.issue || '?';
    
    // Helper function for safe element access
    const safeSet = (id, prop, value) => {
        const el = document.getElementById(id);
        if (!el) {
            console.error(`Element not found: ${id}`);
            return false;
        }
        if (prop === 'innerHTML') el.innerHTML = value;
        else if (prop === 'textContent') el.textContent = value;
        else if (prop === 'style.display') el.style.display = value;
        return true;
    };
    
    safeSet('gradeReportComic', 'innerHTML', `
        <div class="comic-title-big">${displayTitle} #${displayIssue}</div>
        <div class="comic-meta">${comic.publisher || ''} ${comic.year || ''}</div>
    `);
    
    // Grade result
    safeSet('gradeResultBig', 'textContent', grade.final_grade || '--');
    safeSet('gradeResultLabel', 'textContent', grade.grade_label || 'Grade');
    
    // Show quality warning only if confidence < 75%
    const warningEl = document.getElementById('gradeQualityWarning');
    if (warningEl) {
        if (confidence < 75) {
            warningEl.style.display = 'flex';
        } else {
            warningEl.style.display = 'none';
        }
    }
    
    // Photos used badges
    const allLabels = ['Front', 'Spine', 'Back', 'Center'];
    safeSet('gradePhotosUsed', 'innerHTML', allLabels.map((label, idx) => {
        const used = gradingState.photos[idx + 1] !== null;
        return `<span class="photo-badge ${used ? 'used' : 'skipped'}">${label}${used ? ' ✓' : ''}</span>`;
    }).join(''));
    
    // Defects - handle both flat and nested structures
    const frontDefects = defects.front_defects || [];
    const spineDefects = defects.spine_defects || [];
    const backDefects = defects.back_defects || [];
    const interiorDefects = defects.interior_defects || [];
    
    const defectsHTML = [];
    
    if (frontDefects.length > 0) {
        defectsHTML.push(`
            <div class="defect-area">
                <span class="defect-area-label">Front</span>
                <div class="defect-area-items">${frontDefects.map(d => `<span class="defect-item">${d}</span>`).join('')}</div>
            </div>
        `);
    }
    if (spineDefects.length > 0) {
        defectsHTML.push(`
            <div class="defect-area">
                <span class="defect-area-label">Spine</span>
                <div class="defect-area-items">${spineDefects.map(d => `<span class="defect-item">${d}</span>`).join('')}</div>
            </div>
        `);
    }
    if (backDefects.length > 0) {
        defectsHTML.push(`
            <div class="defect-area">
                <span class="defect-area-label">Back</span>
                <div class="defect-area-items">${backDefects.map(d => `<span class="defect-item">${d}</span>`).join('')}</div>
            </div>
        `);
    }
    if (interiorDefects.length > 0) {
        defectsHTML.push(`
            <div class="defect-area">
                <span class="defect-area-label">Interior</span>
                <div class="defect-area-items">${interiorDefects.map(d => `<span class="defect-item">${d}</span>`).join('')}</div>
            </div>
        `);
    }
    
    safeSet('defectsList', 'innerHTML', defectsHTML.length > 0 
        ? defectsHTML.join('') 
        : '<div class="no-defects">✓ No significant defects detected</div>');
    
    // Signature
    const sigDetected = sig.signature_detected || false;
    if (sigDetected) {
        safeSet('gradeReportSignature', 'style.display', 'block');
        const sigInfo = sig.signature_info || {};
        safeSet('signatureInfo', 'innerHTML', `
            <p>${sigInfo.likely_signer || 'Unknown signer'}</p>
            <p style="font-size: 0.9rem; color: var(--text-secondary);">
                ${sigInfo.ink_color || ''} ink, ${sigInfo.location || 'on cover'}
            </p>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 8px;">
                ⚠️ For authenticated value, submit to CGC Signature Series or CBCS Verified
            </p>
        `);
    } else {
        safeSet('gradeReportSignature', 'style.display', 'none');
    }
}

// Calculate "should you grade?" recommendation
async function calculateGradingRecommendation(gradeResult) {
    // Start thinking animation
    startThinkingAnimation('recommendationVerdict');
    
    // Handle nested structure
    const comic = gradeResult['COMIC IDENTIFICATION'] || gradeResult;
    const grade = gradeResult['COMPREHENSIVE GRADE'] || gradeResult;
    
    // Prefer user-edited data
    const title = gradingState.extractedData?.title || comic.title;
    const issue = gradingState.extractedData?.issue || comic.issue;
    
    // Convert letter grade to numeric for valuation lookup
    const gradeMap = {
        'MT': 'NM', '10.0': 'NM', '9.8': 'NM', '9.6': 'NM', '9.4': 'NM',
        'NM': 'NM', 'NM+': 'NM', 'NM-': 'NM',
        'VF': 'VF', 'VF+': 'VF', 'VF-': 'VF', '8.5': 'VF', '8.0': 'VF',
        'FN': 'FN', 'FN+': 'FN', 'FN-': 'FN', '6.5': 'FN', '6.0': 'FN',
        'VG': 'VG', 'VG+': 'VG', 'VG-': 'VG', '4.5': 'VG', '4.0': 'VG',
        'G': 'G', 'GD': 'G', '2.5': 'G', '2.0': 'G',
        'FR': 'FR', '1.5': 'FR',
        'PR': 'PR', '1.0': 'PR', '0.5': 'PR'
    };
    
    const gradeLabel = grade.grade_label || gradeResult.grade_label;
    const finalGrade = grade.final_grade || gradeResult.final_grade;
    const lookupGrade = gradeMap[gradeLabel] || gradeMap[String(finalGrade)] || 'VF';
    
    try {
        // Check cache status first
        try {
            const cacheResponse = await fetch(`${API_URL}/api/cache/check`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify({
                    title: title,
                    issue: issue,
                    grade: lookupGrade
                })
            });
            
            const cacheResult = await cacheResponse.json();
            
            // Show warning if not cached
            if (cacheResult.success && !cacheResult.cached) {
                showCacheWarning();
            }
        } catch (cacheError) {
            // Don't block on cache check failure - just proceed normally
            console.log('Cache check failed, proceeding with valuation:', cacheError);
        }
        
        // Get valuation
        const response = await fetch(`${API_URL}/api/valuate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                title: title,
                issue: issue,
                grade: lookupGrade
            })
        });
        
        const valuation = await response.json();
        
        if (valuation.error) {
            throw new Error(valuation.error);
        }
        
        // Calculate recommendation using tiered slab premium model
        const rawValue = valuation.fair_value || valuation.final_value || 0;
        const slabPremium = getSlabPremium(rawValue);
        const gradingCost = getGradingCost(rawValue);
        
        const slabbedValue = rawValue * slabPremium;
        const valueIncrease = slabbedValue - rawValue;
        const netBenefit = valueIncrease - gradingCost;
        const roi = gradingCost > 0 ? ((netBenefit / gradingCost) * 100).toFixed(0) : 0;
        
        // Render recommendation with CLEARER math
        const isWorthIt = netBenefit > 0;
        
        // Stop thinking animation before showing results
        stopThinkingAnimation();
        
        document.getElementById('recommendationValues').innerHTML = `
            <div class="recommendation-math">
                <div class="math-row">
                    <span class="math-label">Raw value (Fair Market):</span>
                    <span class="math-value">$${rawValue.toFixed(2)}</span>
                </div>
                <div class="math-row">
                    <span class="math-label">+ Slab premium:</span>
                    <span class="math-value positive">+$${valueIncrease.toFixed(2)}</span>
                </div>
                <div class="math-row">
                    <span class="math-label">= Slabbed value:</span>
                    <span class="math-value">$${slabbedValue.toFixed(2)}</span>
                </div>
                <div class="math-divider"></div>
                <div class="math-row">
                    <span class="math-label">− Grading cost (CGC):</span>
                    <span class="math-value negative">−$${gradingCost.toFixed(2)}</span>
                </div>
                <div class="math-divider"></div>
                <div class="math-row math-total ${isWorthIt ? 'positive' : 'negative'}">
                    <span class="math-label">Net ${isWorthIt ? 'profit' : 'loss'} from grading:</span>
                    <span class="math-value">${isWorthIt ? '+' : ''}$${netBenefit.toFixed(2)}</span>
                </div>
            </div>
        `;
        
        // Verdict
        let verdictHTML;
        if (netBenefit > gradingCost * 0.5) {
            // Good ROI
            verdictHTML = `
                <div class="recommendation-verdict submit">
                    <div class="verdict-icon">✅</div>
                    <div class="verdict-text">SUBMIT FOR GRADING</div>
                    <div class="verdict-reason">You'll make ~$${netBenefit.toFixed(2)} profit after grading costs</div>
                </div>
            `;
        } else if (netBenefit > 0) {
            // Marginal
            verdictHTML = `
                <div class="recommendation-verdict" style="background: rgba(99, 102, 241, 0.1); border-color: var(--brand-indigo);">
                    <div class="verdict-icon">🤔</div>
                    <div class="verdict-text" style="color: var(--brand-indigo);">CONSIDER GRADING</div>
                    <div class="verdict-reason">Small profit of $${netBenefit.toFixed(2)} - worth it if you want the slab for your collection</div>
                </div>
            `;
        } else {
            // Not worth it
            verdictHTML = `
                <div class="recommendation-verdict keep-raw">
                    <div class="verdict-icon">📦</div>
                    <div class="verdict-text">KEEP RAW</div>
                    <div class="verdict-reason">You'd lose $${Math.abs(netBenefit).toFixed(2)} - grading costs more than the value increase</div>
                </div>
            `;
        }
        
        document.getElementById('recommendationVerdict').innerHTML = verdictHTML;
        
    } catch (error) {
        console.error('Error calculating recommendation:', error);
        stopThinkingAnimation();
        document.getElementById('recommendationValues').innerHTML = `
            <p style="color: var(--text-muted); text-align: center;">Could not retrieve market values</p>
        `;
        document.getElementById('recommendationVerdict').innerHTML = '';
    }
}

// Slab Premium Calculator - Based on market research (Jan 2026)
// Premium is inversely proportional to raw value:
// - Low value books get huge boost from slab legitimacy
// - High value books already command trust, smaller premium
function getSlabPremium(rawValue) {
    const tiers = [
        { max: 10, premium: 4.0 },      // $0-10: 300% premium - slab = legitimacy
        { max: 15, premium: 3.5 },      // $10-15: 250%
        { max: 20, premium: 3.0 },      // $15-20: 200%
        { max: 30, premium: 2.7 },      // $20-30: 170%
        { max: 40, premium: 2.4 },      // $30-40: 140%
        { max: 50, premium: 2.2 },      // $40-50: 120%
        { max: 75, premium: 2.0 },      // $50-75: 100% - "doubles the value" rule
        { max: 100, premium: 1.85 },    // $75-100: 85%
        { max: 150, premium: 1.7 },     // $100-150: 70%
        { max: 200, premium: 1.6 },     // $150-200: 60%
        { max: 300, premium: 1.5 },     // $200-300: 50%
        { max: 400, premium: 1.45 },    // $300-400: 45%
        { max: 500, premium: 1.4 },     // $400-500: 40%
        { max: 750, premium: 1.35 },    // $500-750: 35%
        { max: 1000, premium: 1.3 },    // $750-1000: 30%
        { max: 1500, premium: 1.25 },   // $1000-1500: 25%
        { max: 2500, premium: 1.22 },   // $1500-2500: 22%
        { max: 5000, premium: 1.18 },   // $2500-5000: 18%
        { max: 10000, premium: 1.15 },  // $5000-10000: 15%
        { max: Infinity, premium: 1.12 } // $10000+: 12% floor
    ];
    
    // Find tier and interpolate for smooth curve
    let prevTier = { max: 0, premium: 4.5 };
    for (const tier of tiers) {
        if (rawValue <= tier.max) {
            // Linear interpolation between tiers
            const range = tier.max === Infinity ? 10000 : tier.max - prevTier.max;
            const position = Math.min((rawValue - prevTier.max) / range, 1);
            return prevTier.premium - (prevTier.premium - tier.premium) * position;
        }
        prevTier = tier;
    }
    return 1.12; // Floor for ultra-high value
}

// Estimate grading cost based on value
function getGradingCost(value) {
    if (value >= 1000) return 150; // Walkthrough tier
    if (value >= 400) return 85;   // Express tier
    if (value >= 200) return 50;   // Economy tier
    return 30; // Modern tier (minimum)
}

// Reset grading mode
function resetGrading() {
    // Reset state
    gradingState = {
        currentStep: 1,
        photos: { 1: null, 2: null, 3: null, 4: null },
        additionalPhotos: [],
        extractedData: null,
        defectsByArea: {},
        finalGrade: null,
        confidence: 0
    };
    
    // Reset all step indicators
    for (let i = 1; i <= 5; i++) {
        const stepEl = document.getElementById(`gradingStep${i}`);
        stepEl.classList.remove('active', 'completed', 'skipped');
        if (i === 1) stepEl.classList.add('active');
        
        const contentEl = document.getElementById(`gradingContent${i}`);
        contentEl.classList.remove('active');
        if (i === 1) contentEl.classList.add('active');
    }
    
    // Reset all inputs and previews
    for (let i = 1; i <= 4; i++) {
        document.getElementById(`gradingUpload${i}`).style.display = 'flex';
        document.getElementById(`gradingPreview${i}`).style.display = 'none';
        document.getElementById(`gradingFeedback${i}`).style.display = 'none';
        // Clear both camera and gallery inputs
        const cameraInput = document.getElementById(`gradingCamera${i}`);
        const galleryInput = document.getElementById(`gradingGallery${i}`);
        if (cameraInput) cameraInput.value = '';
        if (galleryInput) galleryInput.value = '';
        if (i > 1) {
            document.getElementById(`gradingNext${i}`).disabled = true;
        }
    }
    document.getElementById('gradingNext1').disabled = true;
    
    // Clear additional photos
    document.getElementById('additionalPhotos').innerHTML = '';
    
    // Clear comic ID banners
    [2, 3, 4].forEach(step => {
        const banner = document.getElementById(`gradingComicId${step}`);
        if (banner) banner.innerHTML = '';
    });
    
    // Hide quality warning
    const warningEl = document.getElementById('gradeQualityWarning');
    if (warningEl) warningEl.style.display = 'none';
}

// Save graded comic to collection
function saveGradeToCollection() {
    if (!gradingState.finalGrade || !gradingState.extractedData) {
        alert('No grade data to save');
        return;
    }
    
    // Handle nested structure
    const grade = gradingState.finalGrade['COMPREHENSIVE GRADE'] || gradingState.finalGrade;
    
    // Use existing saveToCollection logic
    const comicData = {
        title: gradingState.extractedData.title,
        issue: gradingState.extractedData.issue,
        grade: grade.grade_label || grade.final_grade,
        notes: `Graded via 4-photo analysis. ${grade.grade_reasoning || ''}`
    };
    
    // This would call your existing collection save API
    alert('Save to collection coming soon!');
}

// Cache warning functionality
function showCacheWarning() {
    // Create warning element if it doesn't exist
    let warningEl = document.getElementById('cacheWarning');
    if (!warningEl) {
        warningEl = document.createElement('div');
        warningEl.id = 'cacheWarning';
        warningEl.className = 'cache-warning';
        warningEl.innerHTML = `
            <div class="cache-warning-content">
                <div class="cache-warning-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                        <rect x="3" y="1" width="18" height="22" rx="2" stroke="currentColor" stroke-width="2" fill="none"/>
                        <rect x="6" y="4" width="12" height="13" rx="1" fill="rgba(217, 119, 6, 0.15)" stroke="currentColor" stroke-width="1"/>
                        <text x="12" y="14" text-anchor="middle" fill="currentColor" font-size="10" font-weight="bold" font-family="Arial">?</text>
                        <rect x="6" y="18" width="12" height="3" rx="0.5" fill="currentColor"/>
                    </svg>
                </div>
                <span class="cache-warning-text">This grade of this comic hasn't been checked recently. Market research may take 60-90 seconds...</span>
            </div>
        `;
        
        // Insert before the recommendation verdict section
        const verdictSection = document.getElementById('recommendationVerdict');
        if (verdictSection && verdictSection.parentNode) {
            verdictSection.parentNode.insertBefore(warningEl, verdictSection);
        } else {
            // Fallback: append to grading section
            const gradingSection = document.getElementById('gradingSection');
            if (gradingSection) {
                gradingSection.appendChild(warningEl);
            }
        }
    }
    
    // Show with fade-in animation
    warningEl.style.display = 'block';
    warningEl.style.opacity = '0';
    
    // Trigger fade-in
    requestAnimationFrame(() => {
        warningEl.style.transition = 'opacity 0.3s ease-in-out';
        warningEl.style.opacity = '1';
    });
    
    // Auto-dismiss after 4 seconds
    setTimeout(() => {
        warningEl.style.opacity = '0';
        setTimeout(() => {
            warningEl.style.display = 'none';
        }, 300); // Wait for fade-out animation
    }, 4000);
}

console.log('grading.js loaded');
