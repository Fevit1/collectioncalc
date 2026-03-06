// ===================================================
// Collection Page — Core Logic
// Extracted from collection.html — Session 81 refactor
// ===================================================

// Collection state
let collection = [];
let filteredCollection = [];
let currentView = 'list';
let columnSortField = 'title';
let columnSortDir = 'asc';

function columnSort(field) {
    if (columnSortField === field) {
        columnSortDir = columnSortDir === 'asc' ? 'desc' : 'asc';
    } else {
        columnSortField = field;
        columnSortDir = (field === 'fmv' || field === 'valuation' || field === 'grade') ? 'desc' : 'asc';
    }
    // Update header UI
    document.querySelectorAll('.table-headers .sortable').forEach(el => {
        el.classList.remove('active', 'asc', 'desc');
    });
    const activeHeader = document.querySelector(`.table-headers .sortable[data-sort="${field}"]`);
    if (activeHeader) {
        activeHeader.classList.add('active', columnSortDir);
    }
    filterAndDisplay();
}

// Load collection on page load
document.addEventListener('DOMContentLoaded', () => {
    loadCollection();
    setupEventListeners();

    // If returning from eBay OAuth, reopen the listing modal for the comic we were working on
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('ebay') === 'connected') {
        // Clean the URL without reloading
        window.history.replaceState({}, '', window.location.pathname);

        // Reopen the Create Listing modal after collection loads
        const pendingComicId = localStorage.getItem('sw_ebay_pending_comic');
        if (pendingComicId) {
            localStorage.removeItem('sw_ebay_pending_comic');
            // Wait for collection to load, then open the modal
            const waitForCollection = setInterval(() => {
                if (collection && collection.length > 0) {
                    clearInterval(waitForCollection);
                    const comicId = parseInt(pendingComicId);
                    if (collection.find(c => c.id === comicId)) {
                        openEbayListingModal(comicId);
                    }
                }
            }, 200);
            // Safety timeout — stop waiting after 10s
            setTimeout(() => clearInterval(waitForCollection), 10000);
        }
    }
});

function setupEventListeners() {
    // Search
    document.getElementById('searchInput').addEventListener('input', filterAndDisplay);

    // Sort (both list and gallery dropdowns)
    document.getElementById('listSortSelect').addEventListener('change', () => {
        // Dropdown sort overrides column header sort
        columnSortField = null;
        document.querySelectorAll('.table-headers .sortable').forEach(el => {
            el.classList.remove('active', 'asc', 'desc');
        });
        filterAndDisplay();
    });
    document.getElementById('gallerySortSelect').addEventListener('change', filterAndDisplay);

    // Filter
    document.getElementById('filterSelect').addEventListener('change', filterAndDisplay);

    // Era filter
    document.getElementById('eraFilter').addEventListener('change', filterAndDisplay);

    // Export gallery
    const exportBtn = document.getElementById('exportGallery');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportGalleryImage);
    }

    // View toggle
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentView = btn.dataset.view;
            // Show correct sort dropdown for each view
            document.getElementById('listSortGroup').style.display = currentView === 'list' ? '' : 'none';
            document.getElementById('gallerySortGroup').style.display = currentView === 'gallery' ? '' : 'none';
            filterAndDisplay();
        });
    });
}

async function loadCollection() {
    try {
        const token = localStorage.getItem('cc_token');
        if (!token) {
            window.location.href = '/login.html';
            return;
        }

        const response = await fetch(`${API_URL}/api/collection`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            collection = data.items || [];
            filteredCollection = [...collection];
            updateSummary();
            filterAndDisplay();
        } else {
            console.error('Failed to load collection');
        }
    } catch (error) {
        console.error('Error loading collection:', error);
    }
}

function updateSummary() {
    const totalComics = collection.length;
    const rawValue = collection.reduce((sum, comic) => sum + (comic.raw_value || 0), 0);
    const slabbedValue = collection.reduce((sum, comic) => sum + (comic.slabbed_value || 0), 0);
    const potentialProfit = slabbedValue - rawValue;
    const worthSlabbing = collection.filter(c => c.verdict === 'worth-it').length;

    document.getElementById('totalComics').textContent = totalComics;
    document.getElementById('rawValue').textContent = `$${rawValue.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById('slabbedValue').textContent = `$${slabbedValue.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById('potentialProfit').textContent = `${potentialProfit >= 0 ? '+' : ''}$${potentialProfit.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById('worthSlabbingCount').textContent = `${worthSlabbing} worth slabbing`;

    // Show/hide empty state
    if (totalComics === 0) {
        document.getElementById('comicsContainer').style.display = 'none';
        document.getElementById('emptyState').style.display = 'block';
    } else {
        document.getElementById('comicsContainer').style.display = currentView === 'grid' ? 'grid' : 'flex';
        document.getElementById('emptyState').style.display = 'none';
    }
}

function filterAndDisplay() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const filterValue = document.getElementById('filterSelect').value;
    const eraValue = document.getElementById('eraFilter').value;
    const listSortValue = document.getElementById('listSortSelect').value;
    const gallerySortValue = document.getElementById('gallerySortSelect').value;

    // Filter
    filteredCollection = collection.filter(comic => {
        // Search filter
        const matchesSearch = !searchTerm ||
            comic.title.toLowerCase().includes(searchTerm) ||
            comic.issue.toLowerCase().includes(searchTerm);

        // Verdict filter
        const matchesFilter = filterValue === 'all' || comic.verdict === filterValue;

        // Era filter
        let matchesEra = true;
        if (eraValue !== 'all' && comic.year) {
            const year = parseInt(comic.year);
            switch(eraValue) {
                case 'golden': matchesEra = year >= 1938 && year <= 1956; break;
                case 'silver': matchesEra = year >= 1956 && year <= 1970; break;
                case 'bronze': matchesEra = year >= 1970 && year <= 1985; break;
                case 'copper': matchesEra = year >= 1985 && year <= 1992; break;
                case 'modern': matchesEra = year >= 1992; break;
            }
        }

        return matchesSearch && matchesFilter && matchesEra;
    });

    // Sort — use dropdown + column headers in list view, dropdown in gallery
    if (currentView === 'list') {
        // If column header was clicked, use that; otherwise use dropdown
        if (columnSortField) {
            const dir = columnSortDir === 'asc' ? 1 : -1;
            filteredCollection.sort((a, b) => {
                switch(columnSortField) {
                    case 'title': {
                        const cmp = a.title.localeCompare(b.title);
                        if (cmp !== 0) return cmp * dir;
                        return ((parseInt(a.issue) || 0) - (parseInt(b.issue) || 0)) * dir;
                    }
                    case 'year':
                        return ((parseInt(a.year) || 0) - (parseInt(b.year) || 0)) * dir;
                    case 'issue':
                        return ((parseInt(a.issue) || 0) - (parseInt(b.issue) || 0)) * dir;
                    case 'grade':
                        return ((parseFloat(a.grade) || 0) - (parseFloat(b.grade) || 0)) * dir;
                    case 'fmv':
                        return ((a.raw_value || 0) - (b.raw_value || 0)) * dir;
                    case 'valuation':
                        return ((parseFloat(a.my_valuation) || 0) - (parseFloat(b.my_valuation) || 0)) * dir;
                    default:
                        return 0;
                }
            });
        } else {
            filteredCollection.sort((a, b) => {
                switch(listSortValue) {
                    case 'date-desc': return new Date(b.created_at) - new Date(a.created_at);
                    case 'date-asc': return new Date(a.created_at) - new Date(b.created_at);
                    case 'value-desc': return (b.raw_value || 0) - (a.raw_value || 0);
                    case 'value-asc': return (a.raw_value || 0) - (b.raw_value || 0);
                    case 'grade-desc': return parseFloat(b.grade) - parseFloat(a.grade);
                    case 'title-asc': {
                        const cmp = a.title.localeCompare(b.title);
                        if (cmp !== 0) return cmp;
                        return (parseInt(a.issue) || 0) - (parseInt(b.issue) || 0);
                    }
                    default: return 0;
                }
            });
        }
    } else {
        filteredCollection.sort((a, b) => {
            switch(gallerySortValue) {
                case 'series':
                    const titleCompare = a.title.localeCompare(b.title);
                    if (titleCompare !== 0) return titleCompare;
                    return (parseInt(a.issue) || 0) - (parseInt(b.issue) || 0);
                case 'value-high':
                    return (b.raw_value || 0) - (a.raw_value || 0);
                case 'value-low':
                    return (a.raw_value || 0) - (b.raw_value || 0);
                case 'grade-high':
                    return parseFloat(b.grade) - parseFloat(a.grade);
                case 'grade-low':
                    return parseFloat(a.grade) - parseFloat(b.grade);
                case 'recent':
                    return new Date(b.created_at) - new Date(a.created_at);
                default:
                    return 0;
            }
        });
    }

    displayCollection();
}

function displayCollection() {
    const container = document.getElementById('comicsContainer');
    const tableHeaders = document.getElementById('tableHeaders');
    const exportBtn = document.getElementById('exportGallery');

    // Set container class based on view
    if (currentView === 'list') {
        container.className = 'comics-list';
    } else if (currentView === 'gallery') {
        container.className = 'comics-gallery';
    }

    // Show/hide table headers based on view
    if (currentView === 'list' && filteredCollection.length > 0) {
        tableHeaders.style.display = 'grid';
    } else {
        tableHeaders.style.display = 'none';
    }

    // Show/hide export button (only for gallery view)
    if (exportBtn) {
        exportBtn.style.display = currentView === 'gallery' ? 'inline-block' : 'none';
    }

    if (filteredCollection.length === 0 && collection.length > 0) {
        container.innerHTML = '<div class="empty-state"><p style="color: var(--text-secondary);">No comics match your filters</p></div>';
        return;
    }

    container.innerHTML = filteredCollection.map(comic => createComicCard(comic)).join('');
}

function createComicCard(comic) {
    const roi = (comic.slabbed_value || 0) - (comic.raw_value || 0);
    const roiClass = roi > 0 ? 'positive' : 'negative';
    const verdictClass = comic.verdict === 'worth-it' ? 'worth-it' : 'keep-raw';
    const verdictText = comic.verdict === 'worth-it' ? '✓ Worth It' : 'Keep Raw';

    // Get first available photo (prefer front, then spine, then back, then centerfold)
    let photoUrl = null;
    if (comic.photos) {
        photoUrl = comic.photos.front || comic.photos.spine || comic.photos.back || comic.photos.centerfold;
    }

    // For list view, create a simplified table row
    if (currentView === 'list') {
        // Build defects list
        const defectsList = comic.defects && comic.defects.length > 0
            ? comic.defects.map(d => `<li>${d}</li>`).join('')
            : '<div class="no-defects">No defects detected</div>';

        const defectsTooltip = `
            <div class="defects-tooltip">
                <h4>Detected Defects</h4>
                ${comic.defects && comic.defects.length > 0
                    ? `<ul class="defects-list">${defectsList}</ul>`
                    : defectsList}
            </div>
        `;

        const myValInput = comic.my_valuation
            ? `$${comic.my_valuation.toFixed(2)}`
            : '';

        return `
            <div class="comic-card" data-id="${comic.id}">
                <div class="comic-thumbnail">
                    ${photoUrl ? `<img src="${photoUrl}" alt="${comic.title}">` : '📖'}
                </div>
                <div class="comic-title">${comic.title}</div>
                <div class="comic-issue">${comic.year || '—'}</div>
                <div class="comic-issue">#${comic.issue}</div>
                <div class="comic-grade">
                    ${comic.grade} ${comic.grade_label || ''}
                    ${defectsTooltip}
                </div>
                <div class="value-amount">$${(comic.is_slabbed ? (comic.slabbed_value || comic.raw_value || 0) : (comic.raw_value || 0)).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                <div>
                    <input
                        type="text"
                        class="my-valuation-input"
                        placeholder="$0.00"
                        value="${myValInput}"
                        data-comic-id="${comic.id}"
                        onblur="updateMyValuation(${comic.id}, this.value)"
                    />
                </div>
                <div class="comic-actions">
                    ${guardButton(comic)}
                    <div class="sell-dropdown-wrapper">
                        <button class="action-btn sell-btn" onclick="toggleSellDropdown(event, ${comic.id})">
                            Sell ▾
                        </button>
                        <div class="sell-dropdown" id="sellDropdown-${comic.id}"></div>
                    </div>
                    <button class="action-btn danger" onclick="deleteComic(${comic.id})">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    }

    // Gallery view - framed covers with expand-in-place details
    if (currentView === 'gallery') {
        // Build defects list
        const defectsList = comic.defects && comic.defects.length > 0
            ? comic.defects.map(d => `<li>${d}</li>`).join('')
            : '<div class="no-defects">No defects detected</div>';

        const defectsTooltip = `
            <div class="defects-tooltip">
                <h4>Detected Defects</h4>
                ${comic.defects && comic.defects.length > 0
                    ? `<ul class="defects-list">${defectsList}</ul>`
                    : defectsList}
            </div>
        `;

        const myValInput = comic.my_valuation
            ? `$${comic.my_valuation.toFixed(2)}`
            : '';

        return `
            <div class="comic-frame" data-id="${comic.id}" onclick="toggleGalleryExpand(${comic.id})">
                <div class="frame-outer">
                    <div class="frame-inner">
                        <div class="comic-cover">
                            ${photoUrl ? `<img src="${photoUrl}" alt="${comic.title}">` : '📖'}
                        </div>
                    </div>
                </div>
                <div class="comic-details">
                    <div class="detail-row">
                        <span class="detail-label">Title</span>
                        <span class="detail-value">${comic.title} #${comic.issue}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Grade</span>
                        <span class="detail-value detail-grade">
                            ${comic.grade} ${comic.grade_label || ''}
                            ${defectsTooltip}
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">FMV${comic.is_slabbed ? ' (Slabbed)' : ' (Raw)'}</span>
                        <span class="detail-value">$${(comic.is_slabbed ? (comic.slabbed_value || comic.raw_value || 0) : (comic.raw_value || 0)).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">My Valuation</span>
                        <input
                            type="text"
                            class="my-valuation-input"
                            placeholder="$0.00"
                            value="${myValInput}"
                            data-comic-id="${comic.id}"
                            onclick="event.stopPropagation()"
                            onblur="updateMyValuation(${comic.id}, this.value)"
                        />
                    </div>
                    <div class="detail-actions">
                        ${guardButton(comic, true)}
                        <div class="sell-dropdown-wrapper">
                            <button class="action-btn sell-btn" onclick="event.stopPropagation(); toggleSellDropdown(event, ${comic.id})">
                                Sell ▾
                            </button>
                            <div class="sell-dropdown" id="sellDropdownDetail-${comic.id}"></div>
                        </div>
                        <button class="action-btn danger" onclick="event.stopPropagation(); deleteComic(${comic.id})">
                            🗑️ Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
}

async function updateMyValuation(comicId, valueStr) {
    // Parse the value - remove $ and commas
    const cleaned = valueStr.replace(/[$,]/g, '').trim();
    if (!cleaned) {
        // Empty value - clear my_valuation
        const value = null;
        await saveMyValuation(comicId, value);
        return;
    }

    const value = parseFloat(cleaned);
    if (isNaN(value)) {
        alert('Please enter a valid dollar amount');
        return;
    }

    await saveMyValuation(comicId, value);
}

async function saveMyValuation(comicId, value) {
    try {
        const token = localStorage.getItem('cc_token');
        const response = await fetch(`${API_URL}/api/collection/${comicId}/valuation`, {
            method: 'PATCH',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ my_valuation: value })
        });

        if (response.ok) {
            // Update local data
            const comic = collection.find(c => c.id == comicId);
            if (comic) {
                comic.my_valuation = value;
            }
            const filteredComic = filteredCollection.find(c => c.id == comicId);
            if (filteredComic) {
                filteredComic.my_valuation = value;
            }
            console.log('My valuation saved:', value);
        } else {
            alert('Failed to save valuation');
        }
    } catch (error) {
        console.error('Error saving valuation:', error);
        alert('Error saving valuation');
    }
}

async function deleteComic(comicId) {
    // Check if user has dismissed the warning
    const skipWarning = localStorage.getItem('cc_skip_delete_warning') === 'true';

    if (!skipWarning) {
        // Show custom confirmation modal
        const confirmed = await showDeleteConfirmation();
        if (!confirmed) return;
    }

    const token = localStorage.getItem('cc_token');
    const numId = Number(comicId);

    // --- Optimistic UI: remove instantly, API call in background ---
    const row = document.querySelector(`.comic-card[data-id="${comicId}"], .comic-card[data-id="${numId}"], .comic-frame[data-id="${comicId}"], .comic-frame[data-id="${numId}"]`);
    if (row) {
        row.style.transition = 'opacity 0.15s, transform 0.15s';
        row.style.opacity = '0';
        row.style.transform = 'translateX(-20px)';
        setTimeout(() => row.remove(), 150);
    }

    // Remove from local arrays immediately
    const removedItem = collection.find(c => Number(c.id) === numId);
    collection = collection.filter(c => Number(c.id) !== numId);
    filteredCollection = filteredCollection.filter(c => Number(c.id) !== numId);
    updateSummary();

    // Fire API call in background (no await blocking the UI)
    fetch(`${API_URL}/api/collection/${comicId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
    }).then(async response => {
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            if (removedItem) collection.push(removedItem);
            displayCollection();
            showToast('Delete failed: ' + (errData.error || response.status), 'error');
        }
    }).catch(err => {
        console.error('Delete request failed:', err);
        if (removedItem) collection.push(removedItem);
        displayCollection();
        showToast('Network error — comic restored', 'error');
    });
}

function showDeleteConfirmation() {
    return new Promise((resolve) => {
        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:9999;';

        const modal = document.createElement('div');
        modal.style.cssText = 'background:#1a1a2e;border:1px solid #27272a;border-radius:16px;padding:24px;max-width:400px;width:90%;color:#fff;font-family:Inter,sans-serif;';
        modal.innerHTML = `
            <h3 style="margin:0 0 12px;font-size:1.1rem;">Delete this comic?</h3>
            <p style="color:#a1a1aa;font-size:0.9rem;margin:0 0 20px;">This will permanently remove it from your collection.</p>
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:0.85rem;color:#a1a1aa;margin-bottom:20px;">
                <input type="checkbox" id="skipDeleteWarning" style="width:16px;height:16px;accent-color:#6366f1;cursor:pointer;">
                Don't show this warning again
            </label>
            <div style="display:flex;gap:12px;justify-content:flex-end;">
                <button id="deleteCancel" style="padding:8px 20px;background:#252542;border:1px solid #27272a;border-radius:8px;color:#fff;cursor:pointer;font-size:0.9rem;">Cancel</button>
                <button id="deleteConfirm" style="padding:8px 20px;background:#ef4444;border:none;border-radius:8px;color:#fff;cursor:pointer;font-weight:600;font-size:0.9rem;">Delete</button>
            </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        modal.querySelector('#deleteConfirm').addEventListener('click', () => {
            if (modal.querySelector('#skipDeleteWarning').checked) {
                localStorage.setItem('cc_skip_delete_warning', 'true');
            }
            overlay.remove();
            resolve(true);
        });

        modal.querySelector('#deleteCancel').addEventListener('click', () => {
            overlay.remove();
            resolve(false);
        });

        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
                resolve(false);
            }
        });
    });
}

function viewDetails(comicId) {
    // TODO: Show modal with full details
    const comic = collection.find(c => c.id === comicId);
    if (comic) {
        alert(`Details for ${comic.title} #${comic.issue}\n\nGrade: ${comic.grade}\nRaw: $${comic.raw_value}\nSlabbed: $${comic.slabbed_value}`);
    }
}

function listOnEbay(comicId) {
    openEbayListingModal(comicId);
}

// ===================================================
// Sell Dropdown
// ===================================================

const SELL_PLATFORMS = [
    { key: 'ebay', name: 'eBay', color: '#e53238', tag: 'Direct', action: 'ebay' },
    { divider: true },
    { key: 'whatnot', name: 'Whatnot', color: '#ff6b35', tag: 'Prep', action: 'prep' },
    { key: 'mercari', name: 'Mercari', color: '#4dc0e8', tag: 'Prep', action: 'prep' },
    { key: 'facebook', name: 'Facebook Marketplace', color: '#1877f2', tag: 'Prep', action: 'prep' },
    { divider: true },
    { key: 'heritage', name: 'Heritage Auctions', color: '#1a3c6e', tag: 'Prep', action: 'prep' },
    { key: 'comicconnect', name: 'ComicConnect', color: '#cc0000', tag: 'Prep', action: 'prep' },
    { key: 'mycomicshop', name: 'MyComicShop', color: '#336699', tag: 'Prep', action: 'prep' },
    { key: 'comc', name: 'COMC', color: '#e67e22', tag: 'Prep', action: 'prep' },
    { key: 'hipcomic', name: 'Hip Comics', color: '#8b5cf6', tag: 'Prep', action: 'prep' }
];

function toggleSellDropdown(event, comicId) {
    event.stopPropagation();
    // Close any open dropdowns first
    document.querySelectorAll('.sell-dropdown.active').forEach(d => d.classList.remove('active'));
    document.querySelectorAll('.comic-card.sell-open, .comic-frame.sell-open').forEach(c => c.classList.remove('sell-open'));

    const targetDropdown = event.target.closest('.sell-dropdown-wrapper').querySelector('.sell-dropdown');

    // Build dropdown content (rebuild each time to reflect preference changes)
    let prefs = {};
    try { prefs = JSON.parse(localStorage.getItem('sw_sell_platforms') || '{}'); } catch(e) {}
    targetDropdown.innerHTML = SELL_PLATFORMS.map(p => {
        if (p.divider) return '<div class="sell-dropdown-divider"></div>';
        // eBay always enabled; prep platforms check prefs
        const enabled = p.action === 'ebay' || prefs[p.key] === true;
        const cls = enabled ? '' : ' disabled';
        const click = enabled ? `onclick="event.stopPropagation(); sellAction('${p.action}', '${p.key}', ${comicId})"` : '';
        return `<button class="sell-dropdown-item${cls}" ${click}>
            <span class="platform-dot" style="background:${p.color}"></span>
            ${p.name}
            <span class="platform-tag">${p.tag}</span>
        </button>`;
    }).join('') + '<a class="sell-dropdown-manage" href="/account.html#platforms" onclick="event.stopPropagation()">Manage Platforms</a>';

    targetDropdown.classList.toggle('active');
    // Elevate the parent card so dropdown escapes stacking context
    const parentCard = event.target.closest('.comic-card, .comic-frame');
    if (parentCard && targetDropdown.classList.contains('active')) {
        parentCard.classList.add('sell-open');
    }
}

// Close dropdowns when clicking elsewhere
document.addEventListener('click', () => {
    document.querySelectorAll('.sell-dropdown.active').forEach(d => d.classList.remove('active'));
    document.querySelectorAll('.comic-card.sell-open, .comic-frame.sell-open').forEach(c => c.classList.remove('sell-open'));
});

function sellAction(action, platformKey, comicId) {
    // Close dropdown
    document.querySelectorAll('.sell-dropdown.active').forEach(d => d.classList.remove('active'));
    document.querySelectorAll('.sell-open').forEach(c => c.classList.remove('sell-open'));

    if (action === 'ebay') {
        openEbayListingModal(comicId);
    } else if (action === 'prep') {
        openMarketplacePrepModal(comicId, platformKey);
    }
}

// ===================================================
// Slab Guard — Guard Button + Actions
// ===================================================

function guardButton(comic, stopProp) {
    const sp = stopProp ? 'event.stopPropagation(); ' : '';
    const id = comic.id;

    if (!comic.registry_serial) {
        // Not registered — simple Register button
        return `<button class="guard-btn" id="guardBtn-${id}" onclick="${sp}registerComic(${id}, this)">🛡️ Register</button>`;
    }

    // Registered — shield button showing status + dropdown for actions
    let statusClass = 'registered';
    let label = '🛡️';
    let serial = comic.registry_serial;
    if (comic.registry_status === 'reported_stolen') {
        statusClass = 'stolen';
        label = '🚨';
    } else if (comic.registry_status === 'recovered') {
        statusClass = 'recovered';
        label = '✅';
    }

    // Sighting badge — show count if comic has unread sightings
    const sightingCount = comic.sighting_count || 0;
    const sightingBadge = sightingCount > 0 ? `<span class="sighting-badge">${sightingCount}</span>` : '';

    let dropdownItems = '';
    // Serial number info row
    dropdownItems += `<div class="guard-dropdown-info">${serial}</div>`;

    if (comic.registry_status === 'active') {
        dropdownItems += `<button class="guard-dropdown-item danger" onclick="${sp}reportStolenComic(${id})">🚨 Report Stolen</button>`;
    } else if (comic.registry_status === 'reported_stolen') {
        dropdownItems += `<button class="guard-dropdown-item success" onclick="${sp}markRecoveredComic(${id})">✅ Mark Recovered</button>`;
    } else if (comic.registry_status === 'recovered') {
        dropdownItems += `<button class="guard-dropdown-item danger" onclick="${sp}reportStolenComic(${id})">🚨 Report Stolen Again</button>`;
    }

    // Sightings link — show if there are sightings
    if (sightingCount > 0) {
        dropdownItems += `<button class="guard-dropdown-item" onclick="${sp}window.location.href='/sightings.html?comic_id=${id}&serial=${encodeURIComponent(serial)}'">🔍 View Sightings (${sightingCount})</button>`;
    }

    // Copy serial to clipboard
    dropdownItems += `<button class="guard-dropdown-item" onclick="${sp}navigator.clipboard.writeText('${serial}'); this.textContent='Copied!'; setTimeout(()=>this.textContent='📋 Copy Serial',1500)">📋 Copy Serial</button>`;

    // View on verify page
    dropdownItems += `<button class="guard-dropdown-item" onclick="${sp}window.open('https://slabworthy.com/verify.html?serial=${serial}','_blank')">🔗 View Verify Page</button>`;

    return `<div class="guard-wrapper">
        <button class="guard-btn ${statusClass}" onclick="${sp}toggleGuardDropdown(event, ${id})">
            ${label} <span class="guard-serial">${serial.slice(-6)}</span>${sightingBadge} ▾
        </button>
        <div class="guard-dropdown" id="guardDropdown-${id}">
            ${dropdownItems}
        </div>
    </div>`;
}

function toggleGuardDropdown(event, comicId) {
    event.stopPropagation();
    const dropdown = document.getElementById(`guardDropdown-${comicId}`);
    const wasActive = dropdown.classList.contains('active');
    // Close all guard dropdowns
    document.querySelectorAll('.guard-dropdown.active').forEach(d => d.classList.remove('active'));
    if (!wasActive) dropdown.classList.add('active');
}

// Close guard dropdowns on outside click
document.addEventListener('click', () => {
    document.querySelectorAll('.guard-dropdown.active').forEach(d => d.classList.remove('active'));
});

async function registerComic(comicId, btn) {
    // Show registering animation with animated ellipses
    const origHTML = btn.innerHTML;
    btn.innerHTML = '🛡️ Registering';
    btn.classList.add('registering');
    btn.disabled = true;

    try {
        const token = localStorage.getItem('cc_token');
        const response = await fetch(`${API_URL}/api/registry/register`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ comic_id: comicId })
        });
        const data = await response.json();

        if (!data.success) {
            btn.innerHTML = origHTML;
            btn.classList.remove('registering');
            btn.disabled = false;
            // Show error inline on the button briefly
            const errorMsg = data.quality_failed
                ? 'Photo quality too low'
                : data.upgrade_required
                    ? 'Upgrade required'
                    : (data.error || 'Registration failed');
            btn.innerHTML = '❌ ' + errorMsg;
            btn.style.color = 'var(--status-error)';
            btn.style.borderColor = 'var(--status-error)';
            setTimeout(() => {
                btn.innerHTML = origHTML;
                btn.style.color = '';
                btn.style.borderColor = '';
            }, 3000);
            if (data.upgrade_required && data.upgrade_url) {
                setTimeout(() => window.location.href = data.upgrade_url, 1500);
            }
            return;
        }

        // Success — flash green with serial, then reload
        btn.classList.remove('registering');
        btn.classList.add('register-success');
        btn.innerHTML = `🛡️ ${data.serial_number}`;
        setTimeout(() => loadCollection(), 1200);
    } catch (error) {
        btn.innerHTML = origHTML;
        btn.classList.remove('registering');
        btn.disabled = false;
        console.error('Registration error:', error);
        btn.innerHTML = '❌ Error — retry';
        btn.style.color = 'var(--status-error)';
        setTimeout(() => { btn.innerHTML = origHTML; btn.style.color = ''; }, 3000);
    }
}

async function reportStolenComic(comicId) {
    // No confirm modal — act immediately, button changes color
    document.querySelectorAll('.guard-dropdown.active').forEach(d => d.classList.remove('active'));
    const btn = document.querySelector(`#guardBtn-${comicId}`) ||
                document.querySelector(`.guard-btn.registered[onclick*="${comicId}"]`) ||
                document.querySelector(`.guard-btn.recovered[onclick*="${comicId}"]`);
    if (btn) {
        btn.innerHTML = '🚨 Reporting...';
        btn.disabled = true;
    }
    try {
        const token = localStorage.getItem('cc_token');
        const response = await fetch(`${API_URL}/api/registry/report-stolen/${comicId}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (!data.success) {
            if (btn) { btn.innerHTML = '❌ ' + (data.error || 'Failed'); btn.disabled = false; }
            setTimeout(() => loadCollection(), 2000);
            return;
        }
        // Flash stolen color then reload
        if (btn) {
            btn.classList.add('report-success');
            btn.innerHTML = '🚨 Reported Stolen';
        }
        setTimeout(() => loadCollection(), 1200);
    } catch (error) {
        console.error('Report stolen error:', error);
        if (btn) { btn.innerHTML = '❌ Error'; btn.disabled = false; }
        setTimeout(() => loadCollection(), 2000);
    }
}

async function markRecoveredComic(comicId) {
    // No confirm modal — act immediately, button changes color
    document.querySelectorAll('.guard-dropdown.active').forEach(d => d.classList.remove('active'));
    const btn = document.querySelector(`.guard-btn.stolen[onclick*="${comicId}"]`);
    if (btn) {
        btn.innerHTML = '✅ Recovering...';
        btn.disabled = true;
    }
    try {
        const token = localStorage.getItem('cc_token');
        const response = await fetch(`${API_URL}/api/registry/mark-recovered/${comicId}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (!data.success) {
            if (btn) { btn.innerHTML = '❌ ' + (data.error || 'Failed'); btn.disabled = false; }
            setTimeout(() => loadCollection(), 2000);
            return;
        }
        // Flash recovered color then reload
        if (btn) {
            btn.classList.add('recover-success');
            btn.innerHTML = '✅ Recovered!';
        }
        setTimeout(() => loadCollection(), 1200);
    } catch (error) {
        console.error('Mark recovered error:', error);
        if (btn) { btn.innerHTML = '❌ Error'; btn.disabled = false; }
        setTimeout(() => loadCollection(), 2000);
    }
}

// ===================================================
// Gallery View
// ===================================================

function toggleGalleryExpand(comicId) {
    const frame = document.querySelector(`.comic-frame[data-id="${comicId}"]`);
    if (!frame) return;

    // Close all other expanded frames first
    document.querySelectorAll('.comic-frame.expanded').forEach(f => {
        if (f !== frame) {
            f.classList.remove('expanded');
        }
    });

    // Toggle this frame
    frame.classList.toggle('expanded');
}

async function exportGalleryImage() {
    const container = document.getElementById('comicsContainer');
    if (!container) return;

    try {
        // Temporarily collapse all expanded items for clean export
        const expandedFrames = document.querySelectorAll('.comic-frame.expanded');
        expandedFrames.forEach(f => f.classList.remove('expanded'));

        // Import html2canvas if not already loaded
        if (typeof html2canvas === 'undefined') {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
            document.head.appendChild(script);
            await new Promise(resolve => script.onload = resolve);
        }

        // Capture the gallery
        const canvas = await html2canvas(container, {
            backgroundColor: '#0f0f1a',
            scale: 2, // Higher quality
            logging: false,
            width: 1200,
            height: 1200
        });

        // Add watermark
        const ctx = canvas.getContext('2d');
        ctx.font = '12px Inter';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
        ctx.textAlign = 'right';
        ctx.fillText('Created with Slab Worthy™', canvas.width - 12, canvas.height - 12);

        // Download
        canvas.toBlob(blob => {
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.download = 'my-collection.png';
            link.href = url;
            link.click();
            URL.revokeObjectURL(url);
        });

    } catch (error) {
        console.error('Export error:', error);
        alert('Failed to export gallery. Please try again.');
    }
}

function exportSelected() {
    // TODO: Export to Excel
    alert('Export functionality coming soon!');
}

function deleteSelected() {
    // TODO: Bulk delete
    alert('Bulk delete coming soon!');
}

function clearSelection() {
    document.getElementById('bulkActions').classList.remove('show');
}
