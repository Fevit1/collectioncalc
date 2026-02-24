// eBay Comic Collector - Popup Script v2

const API_BASE = 'https://collectioncalc-docker.onrender.com';

async function loadStats() {
  const data = await chrome.storage.local.get(['collectedSales', 'totalCollected', 'lastCollection', 'sessionCollected']);

  const total = data.totalCollected || 0;
  const pending = (data.collectedSales || []).length;
  const session = data.sessionCollected || 0;

  document.getElementById('totalCount').textContent = total.toLocaleString();
  document.getElementById('pendingCount').textContent = pending.toLocaleString();

  // Show session count if exists
  const sessionEl = document.getElementById('sessionCount');
  if (sessionEl) {
    sessionEl.textContent = session.toLocaleString();
  }

  const recentList = document.getElementById('recentList');
  const sales = data.collectedSales || [];

  if (sales.length === 0) {
    recentList.innerHTML = '<div class="empty">Browse eBay sold listings to collect data</div>';
  } else {
    const recent = sales.slice(-10).reverse();
    recentList.innerHTML = recent.map(sale => `
      <div class="sale-item">
        <span class="sale-title" title="${sale.raw_title}">${sale.raw_title}</span>
        <span class="sale-price">$${sale.sale_price.toFixed(2)}</span>
      </div>
    `).join('');
  }

  if (data.lastCollection) {
    const lastDate = new Date(data.lastCollection);
    document.getElementById('status').textContent = `Last: ${lastDate.toLocaleDateString()} ${lastDate.toLocaleTimeString()}`;
  }
}

async function syncSales() {
  const statusEl = document.getElementById('status');
  const syncBtn = document.getElementById('syncBtn');

  syncBtn.disabled = true;
  statusEl.textContent = 'Syncing...';
  statusEl.className = 'status';

  try {
    const data = await chrome.storage.local.get(['collectedSales']);
    const sales = data.collectedSales || [];

    if (sales.length === 0) {
      statusEl.textContent = 'Nothing to sync';
      syncBtn.disabled = false;
      return;
    }

    const response = await fetch(`${API_BASE}/api/ebay-sales/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sales })
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const result = await response.json();

    // Clear synced sales
    await chrome.storage.local.set({ collectedSales: [] });

    statusEl.textContent = `✓ Synced ${result.saved || sales.length} sales`;
    statusEl.className = 'status success';

    loadStats();
  } catch (e) {
    statusEl.textContent = `Error: ${e.message}`;
    statusEl.className = 'status error';
  }

  syncBtn.disabled = false;
}

async function resetSession() {
  await chrome.storage.local.set({ sessionCollected: 0 });
  document.getElementById('status').textContent = 'Session counter reset';
  loadStats();
}

async function clearData() {
  if (confirm('Clear all collected sales? This cannot be undone.')) {
    await chrome.storage.local.set({
      collectedSales: [],
      totalCollected: 0,
      sessionCollected: 0,
      lastCollection: null
    });
    loadStats();
    document.getElementById('status').textContent = 'Cleared';
  }
}

document.getElementById('syncBtn').addEventListener('click', syncSales);
document.getElementById('clearBtn').addEventListener('click', clearData);

// Session reset button (if it exists in popup.html)
const resetBtn = document.getElementById('resetSessionBtn');
if (resetBtn) {
  resetBtn.addEventListener('click', resetSession);
}

loadStats();
