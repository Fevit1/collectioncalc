// eBay Comic Collector - Popup Script v3
// v3: Added SlabGuard stats + SW login/logout

const API_BASE = 'https://collectioncalc-docker.onrender.com';

// ─── Auth ───

async function getToken() {
  const data = await chrome.storage.local.get(['sw_token', 'sw_email']);
  return { token: data.sw_token || null, email: data.sw_email || null };
}

async function login() {
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const statusEl = document.getElementById('login-status');
  const btn = document.getElementById('login-btn');

  if (!email || !password) {
    statusEl.textContent = 'Email and password required';
    statusEl.style.color = '#e74c3c';
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Logging in...';
  statusEl.textContent = '';

  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();

    if (data.token) {
      await chrome.storage.local.set({ sw_token: data.token, sw_email: email });
      showLoggedIn(email);
      loadSlabGuardStats(data.token);
    } else {
      statusEl.textContent = data.error || 'Login failed';
      statusEl.style.color = '#e74c3c';
    }
  } catch (e) {
    statusEl.textContent = 'Network error';
    statusEl.style.color = '#e74c3c';
  }

  btn.disabled = false;
  btn.textContent = 'Log In';
}

async function logout() {
  await chrome.storage.local.remove(['sw_token', 'sw_email']);
  showLoggedOut();
}

function showLoggedIn(email) {
  document.getElementById('login-form').style.display = 'none';
  document.getElementById('logged-in-info').style.display = 'block';
  document.getElementById('logged-in-email').textContent = `✓ ${email}`;
  document.getElementById('login-section-title').textContent = '🔐 Account';
  document.getElementById('sg-logged-in').style.display = 'block';
  document.getElementById('sg-logged-out').style.display = 'none';
}

function showLoggedOut() {
  document.getElementById('login-form').style.display = 'block';
  document.getElementById('logged-in-info').style.display = 'none';
  document.getElementById('login-section-title').textContent = '🔐 Slab Worthy Login';
  document.getElementById('sg-logged-in').style.display = 'none';
  document.getElementById('sg-logged-out').style.display = 'block';
  document.getElementById('sg-flagged').textContent = '0';
  document.getElementById('sg-my-reports').textContent = '0';
}


// ─── SlabGuard stats ───

async function loadSlabGuardStats(token) {
  if (!token) return;
  try {
    const res = await fetch(`${API_BASE}/api/admin/slabguard/stats`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!res.ok) return;
    const data = await res.json();
    if (data.success) {
      document.getElementById('sg-flagged').textContent = data.flagged_images || 0;
    }
  } catch (e) {
    // silent fail
  }
}


// ─── Sales stats ───

async function loadStats() {
  const data = await chrome.storage.local.get(['collectedSales', 'totalCollected', 'lastCollection', 'sessionCollected']);

  document.getElementById('totalCount').textContent = (data.totalCollected || 0).toLocaleString();
  document.getElementById('pendingCount').textContent = (data.collectedSales || []).length.toLocaleString();
  document.getElementById('sessionCount').textContent = (data.sessionCollected || 0).toLocaleString();

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


// ─── Sync ───

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
    await chrome.storage.local.set({ collectedSales: [], totalCollected: 0, sessionCollected: 0, lastCollection: null });
    loadStats();
    document.getElementById('status').textContent = 'Cleared';
  }
}


// ─── Init ───

async function init() {
  await loadStats();

  const { token, email } = await getToken();
  if (token && email) {
    showLoggedIn(email);
    loadSlabGuardStats(token);
  } else {
    showLoggedOut();
  }
}

document.getElementById('syncBtn').addEventListener('click', syncSales);
document.getElementById('clearBtn').addEventListener('click', clearData);
document.getElementById('resetSessionBtn').addEventListener('click', resetSession);
document.getElementById('login-btn').addEventListener('click', login);
document.getElementById('logout-btn').addEventListener('click', logout);
document.getElementById('login-password').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') login();
});

init();
