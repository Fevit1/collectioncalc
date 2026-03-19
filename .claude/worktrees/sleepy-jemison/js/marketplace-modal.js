// ===================================================
// Marketplace Prep Modal Logic (generic for all platforms)
// Extracted from collection.html — Session 81 refactor
// ===================================================

let mpComic = null;
let mpCurrentPlatform = null;

// Platform metadata (matches backend PLATFORMS config)
const MP_PLATFORMS = {
    whatnot:      { name: 'Whatnot',              color: '#ff6b35', hasNotes: true,  startLabel: 'Starting Bid',   buyLabel: 'Buy Now',          subtitle: 'Prep for Live Auction' },
    mercari:      { name: 'Mercari',              color: '#4dc0e8', hasNotes: false, startLabel: null,             buyLabel: 'Listing Price',    subtitle: 'Prep Listing' },
    facebook:     { name: 'Facebook Marketplace',  color: '#1877f2', hasNotes: false, startLabel: null,             buyLabel: 'Listing Price',    subtitle: 'Prep Listing' },
    heritage:     { name: 'Heritage Auctions',     color: '#1a3c6e', hasNotes: true,  startLabel: 'Estimated Value', buyLabel: 'Reserve Suggestion', subtitle: 'Prep Consignment' },
    comicconnect: { name: 'ComicConnect',          color: '#cc0000', hasNotes: true,  startLabel: 'Estimated Value', buyLabel: 'Reserve Suggestion', subtitle: 'Prep Consignment' },
    mycomicshop:  { name: 'MyComicShop',           color: '#336699', hasNotes: false, startLabel: null,             buyLabel: 'Listing Price',    subtitle: 'Prep Listing' },
    comc:         { name: 'COMC',                  color: '#e67e22', hasNotes: false, startLabel: null,             buyLabel: 'Suggested Price',  subtitle: 'Prep Consignment' },
    hipcomic:     { name: 'Hip Comics',            color: '#8b5cf6', hasNotes: false, startLabel: null,             buyLabel: 'Listing Price',    subtitle: 'Prep Listing' }
};

const MP_PASTE_HINTS = {
    whatnot:      'Open Whatnot Seller Dashboard → Create Listing → Paste fields',
    mercari:      'Open Mercari → Sell → Fill in fields → Upload photos',
    facebook:     'Facebook → Marketplace → Create New Listing → Item for Sale',
    heritage:     'Submit at HA.com/Consign → Comics & Comic Art',
    comicconnect: 'ComicConnect.com → Sell → Submit consignment request',
    mycomicshop:  'MyComicShop.com → Sell → Search for title → Enter details',
    comc:         'Ship item to COMC → They scan and list → Set your price online',
    hipcomic:     'HipComic.com → Sell Comics → Create listing → Paste details'
};

async function openMarketplacePrepModal(comicId, platformKey) {
    mpComic = collection.find(c => c.id === comicId);
    if (!mpComic) { alert('Comic not found'); return; }

    mpCurrentPlatform = platformKey;
    const platform = MP_PLATFORMS[platformKey];
    if (!platform) { alert('Unknown platform'); return; }

    // Style the modal header with platform color
    const header = document.getElementById('mpModalHeader');
    header.style.background = `linear-gradient(135deg, ${platform.color}, ${adjustColor(platform.color, -30)})`;
    header.style.borderBottom = `2px solid ${platform.color}40`;

    // Set platform badge and subtitle
    document.getElementById('mpPlatformBadge').textContent = platform.name;
    document.getElementById('mpPlatformBadge').style.color = platform.color;
    document.getElementById('mpModalSubtitle').textContent = platform.subtitle;

    // Comic preview (photos are nested in mpComic.photos object)
    const mpPhotos = mpComic.photos || {};
    document.getElementById('mpComicPreview').innerHTML = `
        <div class="comic-preview-image">
            ${(mpPhotos.front || mpPhotos.spine) ? `<img src="${mpPhotos.front || mpPhotos.spine}" alt="${mpComic.title}">` : '📖'}
        </div>
        <div class="comic-preview-details">
            <div class="comic-preview-title">${mpComic.title}</div>
            <div class="comic-preview-meta">
                #${mpComic.issue || '?'} • ${mpComic.publisher || 'Unknown'} • ${mpComic.year || '?'}
            </div>
            <span class="comic-preview-grade">${mpComic.grade || 'N/A'}</span>
        </div>
    `;

    // Configure pricing cards based on platform
    const pricingEl = document.getElementById('mpPricingCards');
    if (platform.startLabel) {
        pricingEl.innerHTML = `
            <div class="pricing-card">
                <div class="price-label">${platform.startLabel}</div>
                <div class="price-value" id="mpStartPrice">$--</div>
                <div class="price-hint" id="mpStartHint"></div>
            </div>
            <div class="pricing-card">
                <div class="price-label">${platform.buyLabel}</div>
                <div class="price-value" id="mpBuyNow">$--</div>
                <div class="price-hint">Based on FMV</div>
            </div>
        `;
    } else {
        pricingEl.innerHTML = `
            <div class="pricing-card" style="grid-column: span 2;">
                <div class="price-label">${platform.buyLabel}</div>
                <div class="price-value" id="mpBuyNow">$--</div>
                <div class="price-hint">Based on FMV</div>
            </div>
        `;
    }

    // Show/hide notes section
    const notesSection = document.getElementById('mpShowNotesSection');
    notesSection.style.display = platform.hasNotes ? 'block' : 'none';
    if (platform.hasNotes) {
        document.getElementById('mpShowNotesLabel').textContent =
            platformKey === 'whatnot' ? 'Show Prep Notes (Talking Points)' : 'Prep Notes';
        document.getElementById('mpShowNotesHint').textContent =
            platformKey === 'whatnot' ? 'Reference during your live stream' : 'Key details for your submission';
    }

    // Photos (photos are nested in mpComic.photos object)
    const photosEl = document.getElementById('mpPhotos');
    const photoSlots = [
        { name: 'Front', url: mpPhotos.front },
        { name: 'Spine', url: mpPhotos.spine },
        { name: 'Back', url: mpPhotos.back },
        { name: 'Center', url: mpPhotos.centerfold }
    ];
    photosEl.innerHTML = photoSlots.map(p => {
        if (p.url) {
            return `<div class="photo-download-item">
                <img src="${p.url}" alt="${p.name}">
                <a href="${p.url}" target="_blank" download>${p.name}</a>
            </div>`;
        }
        return `<div class="photo-download-item no-photo">${p.name}: N/A</div>`;
    }).join('');

    // Show/hide Download All Photos button
    const hasPhotos = photoSlots.some(p => p.url);
    const dlBtn = document.getElementById('mpDownloadAllPhotos');
    if (dlBtn) dlBtn.style.display = hasPhotos ? 'inline-block' : 'none';

    // Paste instructions
    document.getElementById('mpPasteHint').textContent = MP_PASTE_HINTS[platformKey] || '';

    // Copy All button color
    const copyBtn = document.getElementById('mpCopyAllBtn');
    copyBtn.style.background = `linear-gradient(135deg, ${platform.color}, ${adjustColor(platform.color, -20)})`;

    // Pre-populate with fallback content immediately (never leave fields empty)
    const fmv = mpComic.is_slabbed ? (mpComic.slabbed_value || mpComic.raw_value || 9.99) : (mpComic.raw_value || 9.99);
    const fallbackTitle = `${mpComic.title} #${mpComic.issue || '?'} ${mpComic.grade || ''}`.trim();
    const fallbackDesc = `${mpComic.title} #${mpComic.issue || '?'} (${mpComic.publisher || 'Unknown'}, ${mpComic.year || '?'}) — Grade: ${mpComic.grade || 'N/A'}. A great pickup for any collection!`;
    let fallbackNotes = `• ${mpComic.title} #${mpComic.issue || '?'}\n• ${mpComic.publisher || ''} ${mpComic.year || ''}\n• Graded ${mpComic.grade || 'N/A'} by Slab Worthy AI\n• FMV: $${fmv.toFixed(2)}`;
    if (mpComic.registry_serial) {
        fallbackNotes += `\n• Slab Guard Verified: ${mpComic.registry_serial}`;
        fallbackNotes += `\n  Verify: https://slabworthy.com/verify.html?serial=${mpComic.registry_serial}`;
    }
    console.log('[MP] Pre-populating fields. Title:', fallbackTitle, 'Desc:', fallbackDesc.substring(0, 50));

    // Helper: set content on contenteditable div fields
    function mpSetField(id, val) {
        const el = document.getElementById(id);
        if (!el) { console.error('[MP] Element not found:', id); return; }
        // Use textContent for contenteditable divs (guaranteed visible rendering)
        el.textContent = val;
        console.log(`[MP] Set ${id} = "${val.substring(0, 40)}..." (length=${val.length})`);
    }

    mpSetField('mpTitle', fallbackTitle);
    mpSetField('mpDescription', fallbackDesc);
    if (platform.hasNotes) {
        mpSetField('mpShowNotes', fallbackNotes);
    }

    const preStartEl = document.getElementById('mpStartPrice');
    if (preStartEl) preStartEl.textContent = platformKey === 'whatnot' ? '$0.99' : `$${(fmv * 0.5).toFixed(2)}`;
    const preBuyEl = document.getElementById('mpBuyNow');
    if (preBuyEl) preBuyEl.textContent = `$${fmv.toFixed(2)}`;

    // Show modal
    document.getElementById('mpModalOverlay').classList.add('active');

    // Verify fields have content after render (debug)
    requestAnimationFrame(() => {
        const t = document.getElementById('mpTitle');
        const d = document.getElementById('mpDescription');
        const n = document.getElementById('mpShowNotes');
        const tVal = t?.textContent || '(empty)';
        const dVal = d?.textContent || '(empty)';
        const nVal = n?.textContent || '(empty)';
        console.log(`[MP] Post-render check: title="${tVal}", desc="${dVal.substring(0,40)}"`);
        if (t && !t.textContent) { t.textContent = fallbackTitle; console.warn('[MP] Title was empty after render, re-set'); }
        if (d && !d.textContent) { d.textContent = fallbackDesc; console.warn('[MP] Desc was empty after render, re-set'); }

        // Show debug strip (TEMPORARY)
        const dbg = document.getElementById('mpDebugStrip');
        if (dbg) {
            dbg.textContent = `DEBUG: Title[${tVal.length}]="${tVal.substring(0,30)}" | Desc[${dVal.length}]="${dVal.substring(0,30)}" | Notes[${nVal.length}]="${nVal.substring(0,30)}"`;
        }
    });

    // Try AI generation (will overwrite fallback content ONLY if it returns real content)
    generateMarketplaceContent(platformKey);
}

function closeMarketplaceModal() {
    document.getElementById('mpModalOverlay').classList.remove('active');
    mpComic = null;
    mpCurrentPlatform = null;
}

async function generateMarketplaceContent(platformKey) {
    const aiStatus = document.getElementById('mpAiStatus');
    const aiText = document.getElementById('mpAiStatusText');
    const platform = MP_PLATFORMS[platformKey];
    const token = localStorage.getItem('cc_token');

    aiStatus.style.display = 'flex';
    aiStatus.className = 'mp-ai-status generating';
    aiText.textContent = `Generating ${platform.name} content with AI...`;
    console.log(`[MP] Generating content for ${platformKey}...`);

    try {
        const fmv = mpComic.is_slabbed ? (mpComic.slabbed_value || mpComic.raw_value || 9.99) : (mpComic.raw_value || 9.99);

        // Use dedicated Whatnot endpoint for better content; generic marketplace for others
        const endpoint = platformKey === 'whatnot'
            ? `${API_URL}/api/whatnot/generate-content`
            : `${API_URL}/api/marketplace/generate-content`;

        const basePayload = { title: mpComic.title, issue: mpComic.issue, grade: mpComic.grade, price: fmv, publisher: mpComic.publisher, year: mpComic.year, assessment_id: mpComic.id, registry_serial: mpComic.registry_serial || null };
        const payload = platformKey === 'whatnot'
            ? basePayload
            : { ...basePayload, platform: platformKey };

        console.log(`[MP] POST ${endpoint}`, JSON.stringify(payload));

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        console.log(`[MP] Response status: ${response.status}`);
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`[MP] Error response body:`, errorText);
            throw new Error(`HTTP ${response.status}: ${errorText.substring(0, 200)}`);
        }
        const data = await response.json();
        console.log(`[MP] Response data:`, JSON.stringify(data).substring(0, 500));

        if (data.success) {
            const titleEl = document.getElementById('mpTitle');
            const descEl = document.getElementById('mpDescription');
            const notesEl = document.getElementById('mpShowNotes');

            // ONLY overwrite if API returned actual content (never clear fallback with empty)
            if (data.listing_title && data.listing_title.trim()) {
                titleEl.textContent = data.listing_title;
                console.log('[MP] AI title set:', data.listing_title);
            } else {
                console.warn('[MP] API returned empty listing_title, keeping fallback');
            }
            if (data.description && data.description.trim()) {
                descEl.textContent = data.description;
                console.log('[MP] AI desc set:', data.description.substring(0, 50));
            } else {
                console.warn('[MP] API returned empty description, keeping fallback');
            }
            if (platform.hasNotes && data.show_notes && data.show_notes.trim()) {
                notesEl.textContent = data.show_notes;
                console.log('[MP] AI notes set:', data.show_notes.substring(0, 50));
            }

            // Pricing
            const startEl = document.getElementById('mpStartPrice');
            if (startEl && data.suggested_start != null) {
                startEl.textContent = `$${data.suggested_start.toFixed(2)}`;
                const hintEl = document.getElementById('mpStartHint');
                if (hintEl) {
                    hintEl.textContent = platformKey === 'whatnot' ? 'Low starts drive bidding' : 'Based on market data';
                }
            }
            const buyEl = document.getElementById('mpBuyNow');
            if (buyEl) {
                buyEl.textContent = `$${(data.suggested_buy_now || fmv).toFixed(2)}`;
            }

            const sourceLabel = data.source === 'ai' ? '✓ AI content generated' : '✓ Content ready (template)';
            aiStatus.className = 'mp-ai-status success';
            aiText.textContent = sourceLabel;
            setTimeout(() => { aiStatus.style.display = 'none'; }, 4000);

            // Update debug strip after AI content
            const dbg2 = document.getElementById('mpDebugStrip');
            if (dbg2) {
                dbg2.textContent = `DEBUG (${data.source}): Title[${titleEl.textContent.length}]="${titleEl.textContent.substring(0,30)}" | Desc[${descEl.textContent.length}]="${descEl.textContent.substring(0,30)}"`;
            }
        } else {
            throw new Error(data.error || 'Generation failed');
        }
    } catch (error) {
        console.error(`[MP] ${platform.name} content generation error:`, error);
        aiStatus.className = 'mp-ai-status error';
        aiText.innerHTML = `✗ AI unavailable — edit below or <a href="#" onclick="event.preventDefault(); generateMarketplaceContent('${platformKey}')" style="color:#ff6b35;text-decoration:underline;">retry</a>`;
        // Fallback content was already pre-populated in openMarketplacePrepModal
        // Update debug strip on error
        const dbg3 = document.getElementById('mpDebugStrip');
        const tEl = document.getElementById('mpTitle');
        const dEl = document.getElementById('mpDescription');
        if (dbg3) {
            dbg3.textContent = `DEBUG (error: ${error.message.substring(0,40)}): Title[${tEl?.textContent?.length}]="${tEl?.textContent?.substring(0,30)}" | Desc[${dEl?.textContent?.length}]="${dEl?.textContent?.substring(0,30)}"`;
        }
    }
}

// Utility: darken/lighten a hex color
function adjustColor(hex, amount) {
    hex = hex.replace('#', '');
    const r = Math.max(0, Math.min(255, parseInt(hex.substr(0,2), 16) + amount));
    const g = Math.max(0, Math.min(255, parseInt(hex.substr(2,2), 16) + amount));
    const b = Math.max(0, Math.min(255, parseInt(hex.substr(4,2), 16) + amount));
    return `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`;
}

function copyMpField(fieldId, btn) {
    const field = document.getElementById(fieldId);
    if (!field) { console.warn('[MP] copyMpField: element not found:', fieldId); return; }
    const text = field.textContent || field.innerText || '';
    navigator.clipboard.writeText(text).then(() => {
        btn.textContent = '✓';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = '📋'; btn.classList.remove('copied'); }, 2000);
    }).catch(() => {
        // Fallback: select and copy
        const range = document.createRange();
        range.selectNodeContents(field);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.execCommand('copy');
        sel.removeAllRanges();
        btn.textContent = '✓';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = '📋'; btn.classList.remove('copied'); }, 2000);
    });
}

function copyAllMp(btn) {
    if (!mpCurrentPlatform) return;
    const platform = MP_PLATFORMS[mpCurrentPlatform];
    const title = document.getElementById('mpTitle')?.textContent || '';
    const desc = document.getElementById('mpDescription')?.textContent || '';
    const buyNow = document.getElementById('mpBuyNow')?.textContent || '';
    const startPrice = document.getElementById('mpStartPrice')?.textContent || '';
    const notes = platform?.hasNotes ? (document.getElementById('mpShowNotes')?.textContent || '') : '';

    let allText = `Title: ${title}`;
    if (startPrice && platform?.startLabel) allText += `\n${platform.startLabel}: ${startPrice}`;
    if (buyNow) allText += `\n${platform?.buyLabel || 'Price'}: ${buyNow}`;
    allText += `\n\nDescription:\n${desc}`;
    if (notes) allText += `\n\nPrep Notes:\n${notes}`;

    navigator.clipboard.writeText(allText).then(() => {
        btn.textContent = '✓ Copied!';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = '📋 Copy All'; btn.classList.remove('copied'); }, 2500);
    }).catch(() => {
        const ta = document.createElement('textarea');
        ta.value = allText;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        btn.textContent = '✓ Copied!';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = '📋 Copy All'; btn.classList.remove('copied'); }, 2500);
    });
}

async function downloadAllMpPhotos() {
    if (!mpComic) return;
    const photos = mpComic.photos || {};
    const slots = [
        { name: 'front', url: photos.front },
        { name: 'spine', url: photos.spine },
        { name: 'back', url: photos.back },
        { name: 'centerfold', url: photos.centerfold }
    ].filter(p => p.url);

    if (!slots.length) { alert('No photos available'); return; }

    const btn = document.getElementById('mpDownloadAllPhotos');
    const origText = btn.textContent;
    btn.textContent = `⬇ Downloading ${slots.length}...`;
    btn.disabled = true;

    const comicSlug = `${mpComic.title}_${mpComic.issue || ''}`.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 30);

    for (const photo of slots) {
        try {
            const resp = await fetch(photo.url);
            const blob = await resp.blob();
            const ext = photo.url.match(/\.(jpg|jpeg|png|webp)/i)?.[1] || 'jpg';
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `${comicSlug}_${photo.name}.${ext}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(a.href);
            // Small delay between downloads so browser doesn't block them
            await new Promise(r => setTimeout(r, 300));
        } catch (e) {
            console.error(`[MP] Failed to download ${photo.name}:`, e);
        }
    }

    btn.textContent = '✓ Downloaded!';
    setTimeout(() => { btn.textContent = origText; btn.disabled = false; }, 2500);
}
