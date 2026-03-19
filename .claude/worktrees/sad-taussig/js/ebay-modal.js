// ===================================================
// eBay Listing Modal Logic
// Extracted from collection.html — Session 81 refactor
// ===================================================

let currentComic = null;
// ebayConnected is declared in auth.js - ensure it exists globally
if (typeof window.ebayConnected === 'undefined') {
    window.ebayConnected = false;
}
let uploadedImageUrls = [];
let currentListingFormat = 'FIXED_PRICE';

function setListingFormat(format) {
    currentListingFormat = format;
    // Toggle button active states
    document.querySelectorAll('.format-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.format === format);
    });
    // Toggle field visibility
    document.getElementById('fixedPriceFields').style.display = format === 'FIXED_PRICE' ? 'block' : 'none';
    document.getElementById('auctionFields').style.display = format === 'AUCTION' ? 'block' : 'none';
    // Pre-fill auction start price from FMV if switching to auction
    if (format === 'AUCTION' && currentComic) {
        const fmv = currentComic.is_slabbed ? (currentComic.slabbed_value || currentComic.raw_value || 9.99) : (currentComic.raw_value || 9.99);
        const startPrice = document.getElementById('auctionStartPrice');
        if (!startPrice.value) {
            startPrice.value = '0.99'; // Low start to drive bidding
        }
        document.getElementById('auctionFmvHint').textContent = `FMV: $${fmv.toFixed(2)}`;
    }
}

async function openEbayListingModal(comicId) {
    // Find comic in collection
    currentComic = collection.find(c => c.id === comicId);
    if (!currentComic) {
        alert('Comic not found');
        return;
    }

    // Show modal
    document.getElementById('ebayModalOverlay').classList.add('active');

    // Check eBay connection
    await checkEbayConnection();

    // Populate form
    populateListingForm();

    // Generate description
    await generateDescription();
}

function closeEbayModal() {
    document.getElementById('ebayModalOverlay').classList.remove('active');
    currentComic = null;
    uploadedImageUrls = [];
}

function closeModalOnBackdrop(event) {
    if (event.target === event.currentTarget) {
        closeEbayModal();
    }
}

async function checkEbayConnection() {
    const token = localStorage.getItem('cc_token');

    try {
        const response = await fetch(`${API_URL}/api/ebay/status`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        const data = await response.json();
        window.ebayConnected = data.connected || false;

        const indicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        const connectBtn = document.getElementById('connectBtn');
        const publishBtn = document.getElementById('publishBtn');

        if (window.ebayConnected) {
            indicator.classList.remove('disconnected');
            statusText.textContent = `Connected to eBay as ${data.ebay_username || 'Connected'}`;
            connectBtn.style.display = 'none';
            publishBtn.disabled = false;
        } else {
            indicator.classList.add('disconnected');
            statusText.textContent = 'Not connected to eBay';
            connectBtn.style.display = 'block';
            publishBtn.disabled = true;
        }
    } catch (error) {
        console.error('Error checking eBay connection:', error);
    }
}

async function connectToEbay() {
    // Fetch the eBay OAuth URL from the backend (requires JWT auth),
    // then redirect the browser to it
    const token = localStorage.getItem('cc_token');
    if (!token) {
        alert('Please log in first.');
        return;
    }
    try {
        const response = await fetch(`${API_URL}/api/ebay/auth?return_to=collection.html`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        if (data.success && data.url) {
            // Remember which comic was open so we can reopen the modal after OAuth
            if (currentComic && currentComic.id) {
                localStorage.setItem('sw_ebay_pending_comic', currentComic.id);
            }
            window.location.href = data.url;
        } else {
            alert('Could not start eBay connection: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        alert('Error connecting to eBay. Please try again.');
        console.error('connectToEbay error:', err);
    }
}

function populateListingForm() {
    // Reset format to Fixed Price
    setListingFormat('FIXED_PRICE');
    // Reset auction fields
    document.getElementById('auctionStartPrice').value = '';
    document.getElementById('auctionReservePrice').value = '';
    document.getElementById('auctionBuyItNow').value = '';
    document.getElementById('auctionDuration').value = 'DAYS_7';

    // Comic preview
    const preview = document.getElementById('comicPreview');
    preview.innerHTML = `
        <div class="comic-preview-image">
            ${(currentComic.photos && (currentComic.photos.front || currentComic.photos.spine)) ? `<img src="${currentComic.photos.front || currentComic.photos.spine}" alt="${currentComic.title}">` : '📖'}
        </div>
        <div class="comic-preview-details">
            <div class="comic-preview-title">${currentComic.title}</div>
            <div class="comic-preview-meta">
                #${currentComic.issue || '?'} • ${currentComic.publisher || 'Unknown'} • ${currentComic.year || '?'}
            </div>
            <span class="comic-preview-grade">${currentComic.grade || 'N/A'}</span>
        </div>
    `;

    // Title - auto-generate (eBay max 80 chars)
    const title = `${currentComic.title} #${currentComic.issue || '?'} Comic Book - ${currentComic.grade || 'VG'} ${currentComic.publisher || ''}`.trim();
    document.getElementById('listingTitle').value = title.substring(0, 80);
    updateCharCounter('title');

    // Price - suggest FMV or slightly below
    const suggestedPrice = currentComic.is_slabbed ? (currentComic.slabbed_value || currentComic.raw_value || 9.99) : (currentComic.raw_value || 9.99);
    document.getElementById('listingPrice').value = suggestedPrice.toFixed(2);
    document.getElementById('priceSuggestion').textContent = `FMV: $${suggestedPrice.toFixed(2)}`;

    // Grading ID
    const gradingId = currentComic.grading_id || 'SW-' + currentComic.id;
    document.getElementById('gradingIdDisplay').value = gradingId;
}

async function generateDescription() {
    const aiStatus = document.getElementById('aiStatus');
    const descriptionField = document.getElementById('listingDescription');
    const token = localStorage.getItem('cc_token');

    aiStatus.style.display = 'flex';
    aiStatus.className = 'ai-status generating';
    document.getElementById('aiStatusText').textContent = 'Generating description with AI...';

    try {
        const response = await fetch(`${API_URL}/api/ebay/generate-description`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: currentComic.title,
                issue: currentComic.issue,
                grade: currentComic.grade,
                price: parseFloat(document.getElementById('listingPrice').value),
                publisher: currentComic.publisher,
                year: currentComic.year
            })
        });

        const data = await response.json();

        if (data.success) {
            // Add grading ID to description
            const gradingId = document.getElementById('gradingIdDisplay').value;
            const fullDescription = data.description +
                `\n\nSlab Worthy™ Assessment ID: ${gradingId}`;

            descriptionField.value = fullDescription;
            updateCharCounter('desc');

            // Update title with KEY ISSUE if the AI flagged it
            if (data.description.toUpperCase().includes('KEY ISSUE')) {
                const titleInput = document.getElementById('listingTitle');
                const currentTitle = titleInput.value;
                if (!currentTitle.toUpperCase().includes('KEY ISSUE')) {
                    const keyTitle = `${currentComic.title} #${currentComic.issue || '?'} KEY ISSUE Comic Book - ${currentComic.grade || 'VG'}`.substring(0, 80);
                    titleInput.value = keyTitle;
                    updateCharCounter('title');
                }
            }

            aiStatus.className = 'ai-status success';
            document.getElementById('aiStatusText').textContent = '✓ Description generated';
            setTimeout(() => { aiStatus.style.display = 'none'; }, 3000);
        } else {
            throw new Error(data.error || 'Failed to generate');
        }
    } catch (error) {
        console.error('Description generation error:', error);
        aiStatus.className = 'ai-status error';
        document.getElementById('aiStatusText').textContent = '✗ Failed - edit manually';

        // Fallback description
        const gradingId = document.getElementById('gradingIdDisplay').value;
        descriptionField.value = `${currentComic.title} #${currentComic.issue} in ${currentComic.grade} condition.\n\nSlab Worthy™ Assessment ID: ${gradingId}`;
        updateCharCounter('desc');
    }
}

function updateCharCounter(field) {
    if (field === 'title') {
        const input = document.getElementById('listingTitle');
        const counter = document.getElementById('titleCounter');
        const length = input.value.length;
        counter.textContent = `${length} / 80`;
        if (length > 70) counter.classList.add('warning');
        else counter.classList.remove('warning');
    } else if (field === 'desc') {
        const input = document.getElementById('listingDescription');
        const counter = document.getElementById('descCounter');
        const length = input.value.length;
        counter.textContent = `${length} / 4000`;
        if (length > 3500) counter.classList.add('warning');
        else counter.classList.remove('warning');
    }
}

// Add event listeners for char counters
document.addEventListener('DOMContentLoaded', () => {
    const titleInput = document.getElementById('listingTitle');
    const descInput = document.getElementById('listingDescription');

    if (titleInput) titleInput.addEventListener('input', () => updateCharCounter('title'));
    if (descInput) descInput.addEventListener('input', () => updateCharCounter('desc'));
});

async function uploadPhotosToEbay() {
    const token = localStorage.getItem('cc_token');
    const p = currentComic.photos || {};
    const photos = [
        { name: 'Front', url: p.front },
        { name: 'Spine', url: p.spine },
        { name: 'Back', url: p.back },
        { name: 'Center', url: p.centerfold }
    ];

    uploadedImageUrls = [];
    const statusItems = document.querySelectorAll('.photo-status-item');

    // Check if ANY photos exist — if not, proceed with eBay placeholder
    const hasAnyPhotos = photos.some(ph => ph.url);
    if (!hasAnyPhotos) {
        for (let i = 0; i < statusItems.length; i++) {
            statusItems[i].textContent = `${photos[i].name}: ⏭ No photo`;
        }
        console.log('No photos available — listing will use placeholder image');
        return true; // Allow listing to proceed; ebay_listing.py uses placeholder
    }

    for (let i = 0; i < photos.length; i++) {
        const photo = photos[i];
        const statusItem = statusItems[i];

        if (!photo.url) {
            statusItem.textContent = `${photo.name}: ⚠️ Missing`;
            statusItem.classList.add('error');
            continue;
        }

        statusItem.textContent = `${photo.name}: ⏳`;
        statusItem.classList.add('uploading');

        try {
            // Send R2 URL to backend — backend fetches + uploads to eBay (avoids CORS)
            const uploadResponse = await fetch(`${API_URL}/api/ebay/upload-image`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ image_url: photo.url, filename: 'comic.jpg' })
            });

            const data = await uploadResponse.json();

            if (data.success && data.image_url) {
                uploadedImageUrls.push(data.image_url);
                statusItem.textContent = `${photo.name}: ✓`;
                statusItem.classList.remove('uploading');
                statusItem.classList.add('success');
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        } catch (error) {
            console.error(`Error uploading ${photo.name}:`, error);
            statusItem.textContent = `${photo.name}: ✗`;
            statusItem.classList.remove('uploading');
            statusItem.classList.add('error');
        }
    }

    return uploadedImageUrls.length > 0;
}

async function saveAsDraft() {
    if (!window.ebayConnected) {
        alert('Please connect to eBay first');
        return;
    }

    await createListing(false); // false = draft
}

async function publishListing() {
    if (!window.ebayConnected) {
        alert('Please connect to eBay first');
        return;
    }

    await createListing(true); // true = publish
}

async function createListing(publish) {
    const token = localStorage.getItem('cc_token');
    const publishBtn = document.getElementById('publishBtn');
    const draftBtn = document.getElementById('draftBtn');

    // Disable buttons
    publishBtn.disabled = true;
    draftBtn.disabled = true;
    publishBtn.textContent = publish ? '⏳ Publishing...' : '⏳ Creating...';

    try {
        // Upload photos first
        const photosUploaded = await uploadPhotosToEbay();
        if (!photosUploaded) {
            throw new Error('Failed to upload photos');
        }

        // Build listing data based on format
        const isAuction = currentListingFormat === 'AUCTION';
        const listingData = {
            title: currentComic.title,
            listing_title: document.getElementById('listingTitle').value,
            issue: currentComic.issue,
            price: isAuction
                ? parseFloat(document.getElementById('auctionStartPrice').value || '0.99')
                : parseFloat(document.getElementById('listingPrice').value),
            grade: currentComic.grade,
            publisher: currentComic.publisher,
            year: currentComic.year,
            description: document.getElementById('listingDescription').value,
            image_urls: uploadedImageUrls,
            publish: publish,
            grading_id: document.getElementById('gradingIdDisplay').value,
            listing_format: currentListingFormat
        };

        // Add auction-specific fields with validation
        if (isAuction) {
            const startPrice = parseFloat(document.getElementById('auctionStartPrice').value || '0.99');
            if (startPrice <= 0) {
                alert('Starting bid must be greater than $0.00');
                publishBtn.disabled = !window.ebayConnected;
                draftBtn.disabled = false;
                publishBtn.textContent = '🚀 Publish Now';
                return;
            }
            listingData.start_price = startPrice;
            listingData.auction_duration = document.getElementById('auctionDuration').value;
            const reserve = document.getElementById('auctionReservePrice').value;
            if (reserve) {
                const reservePrice = parseFloat(reserve);
                if (reservePrice <= startPrice) {
                    alert('Reserve price must be higher than the starting bid ($' + startPrice.toFixed(2) + ')');
                    publishBtn.disabled = !window.ebayConnected;
                    draftBtn.disabled = false;
                    publishBtn.textContent = '🚀 Publish Now';
                    return;
                }
                listingData.reserve_price = reservePrice;
            }
            const bin = document.getElementById('auctionBuyItNow').value;
            if (bin) {
                const binPrice = parseFloat(bin);
                const minBin = listingData.reserve_price || startPrice;
                if (binPrice <= minBin) {
                    alert('Buy It Now price must be higher than ' + (listingData.reserve_price ? 'the reserve price' : 'the starting bid') + ' ($' + minBin.toFixed(2) + ')');
                    publishBtn.disabled = !window.ebayConnected;
                    draftBtn.disabled = false;
                    publishBtn.textContent = '🚀 Publish Now';
                    return;
                }
                listingData.buy_it_now_price = binPrice;
            }
        }

        const response = await fetch(`${API_URL}/api/ebay/list`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(listingData)
        });

        const data = await response.json();

        if (data.success) {
            const formatLabel = data.format === 'AUCTION' ? 'Auction' : 'Fixed Price';
            if (publish && data.listing_url) {
                const durationNote = data.auction_duration ? ` (${data.auction_duration.replace('DAYS_', '')} days)` : '';
                alert(`✓ ${formatLabel} listing live on eBay!${durationNote}\n\nView at: ${data.listing_url}`);
                window.open(data.listing_url, '_blank');
            } else {
                alert(`✓ ${formatLabel} draft saved!\n\nView in eBay Seller Hub: ${data.drafts_url || 'eBay dashboard'}`);
            }
            closeEbayModal();
        } else {
            throw new Error(data.error || 'Listing failed');
        }
    } catch (error) {
        console.error('Listing error:', error);
        alert(`Failed to create listing:\n${error.message}\n\nPlease try again or check your eBay connection.`);
    } finally {
        // Re-enable buttons
        publishBtn.disabled = !window.ebayConnected;
        draftBtn.disabled = false;
        publishBtn.textContent = '🚀 Publish Now';
    }
}
