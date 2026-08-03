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
  const data = await chrome.storage.local.get([
    'collectedSales', 'lastCollection', 'unsyncedCount', 'runSaved', 'runExpiresAt']);

  // Saved this run — server-confirmed inserts since the last idle gap.
  // The boundary is read as an ABSOLUTE expiry that content.js persists, so this
  // file holds NO duration constant to drift out of step with it.
  // Renders "—" when no run is in progress: printing 0 would claim a run exists
  // that saved nothing, which is a different (and false) statement.
  const runLive = data.runExpiresAt && Date.now() <= data.runExpiresAt;
  document.getElementById('runCount').textContent =
    runLive ? (data.runSaved || 0).toLocaleString() : '—';

  // ⚠️ FIXED 2026-08-03: this used to show collectedSales.length under the label
  // "Pending Sync". That array is the rolling 1000-item LOCAL DEDUP buffer — it
  // sits at the cap permanently and has nothing to do with what is pending.
  // `unsyncedCount` is the real figure (sales whose send failed and that no
  // successful Sync has flushed since).
  document.getElementById('pendingCount').textContent = (data.unsyncedCount || 0).toLocaleString();

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

    // Sync is the only real flush, so it is the only thing that may clear the
    // unsynced counter that content.js maintains for its buffer-risk warning.
    //
    // A successful Sync also inserts rows the run counter never saw (content.js
    // deliberately adds nothing on a failed send), so credit them here — this
    // closes the "reads low after a failure a later Sync repairs" gap. Only a
    // numeric result.saved counts, same rule as noteSaved: never fall back to
    // the local length.
    const credited = typeof result.saved === 'number' ? result.saved : 0;
    const r = await chrome.storage.local.get(['runSaved', 'runExpiresAt']);
    const patch = { collectedSales: [], unsyncedCount: 0 };

    // ⚠️ CREDIT ONLY INTO A RUN THAT IS ALREADY LIVE, and never start one here.
    //
    // Without the gate this path RESURRECTED a dead run: a Tuesday run's 1,190
    // would be added to Thursday's flush of 50 and the tile would read 1,240
    // "saved this run", with a two-day-old runStartedAt rendering as a plausible
    // clock time. Nothing zeroes runSaved at expiry (content.js clears it lazily
    // on the next capture), so storage routinely holds a live-looking total from
    // a dead run.
    //
    // And a manual Sync is a FLUSH, not a capture run — so when no run is live
    // these rows are simply not attributed to one. Inventing a run to hold them
    // would be the same over-claiming this pass exists to remove. The rows are
    // still in the corpus; Postgres is where that total lives.
    //
    // This also means the popup never writes runExpiresAt and therefore holds no
    // duration constant — content.js remains the single source of the boundary.
    if (r.runExpiresAt && Date.now() <= r.runExpiresAt && credited) {
      patch.runSaved = (r.runSaved || 0) + credited;
    }
    await chrome.storage.local.set(patch);
    // `??` not `||` — saved === 0 is the NORMAL all-duplicates outcome when Sync
    // re-POSTs the buffer after a successful content.js send, and `||` printed
    // "✓ Synced 1000 sales" for it, contradicting the tile that added 0.
    statusEl.textContent = `✓ Synced ${result.saved ?? sales.length} sales`;
    statusEl.className = 'status success';
    loadStats();
  } catch (e) {
    statusEl.textContent = `Error: ${e.message}`;
    statusEl.className = 'status error';
  }

  syncBtn.disabled = false;
}

async function resetSession() {
  // Repurposed 2026-08-03. This used to zero `sessionCollected`, which is now a
  // retired key nothing reads — the button would have looked like it worked and
  // done nothing. It now zeroes the run counter that actually backs the display.
  // runExpiresAt is left alone: content.js owns the boundary, and zeroing the
  // count should not silently extend or end the run.
  await chrome.storage.local.set({ runSaved: 0, runStartedAt: Date.now() });
  document.getElementById('status').textContent = 'Run count reset';
  loadStats();
}

async function clearData() {
  if (confirm('Clear all collected sales? This cannot be undone.')) {
    await chrome.storage.local.set({
      collectedSales: [], lastCollection: null, unsyncedCount: 0,
      runSaved: 0, runStartedAt: null, runExpiresAt: null
    });
    // REMOVE, don't set-to-0: the retired keys were previously written as 0 here,
    // which kept them in storage forever and CREATED them on a fresh install —
    // the opposite of clearing them.
    await chrome.storage.local.remove(['totalCollected', 'sessionCollected', 'runTouchedAt']);
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
