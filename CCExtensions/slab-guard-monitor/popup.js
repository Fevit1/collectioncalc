/**
 * Slab Guard Monitor - Popup Script
 * Handles login, role tabs, match display, and settings.
 */

const API_BASE = 'https://collectioncalc-docker.onrender.com';

// ============================================================
// DOM ELEMENTS
// ============================================================

const loginScreen = document.getElementById('loginScreen');
const mainScreen = document.getElementById('mainScreen');
const loginForm = document.getElementById('loginForm');
const loginError = document.getElementById('loginError');
const loginBtn = document.getElementById('loginBtn');
const logoutBtn = document.getElementById('logoutBtn');
const userName = document.getElementById('userName');
const settingsBtn = document.getElementById('settingsBtn');
const autoScanToggle = document.getElementById('autoScanToggle');

// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
  const settings = await getSettings();

  if (settings.authToken) {
    showMainScreen(settings);
  } else {
    showLoginScreen();
  }

  setupTabs();
  setupEventListeners();
});

function getSettings() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ action: 'getSettings' }, resolve);
  });
}

// ============================================================
// LOGIN / LOGOUT
// ============================================================

function showLoginScreen() {
  loginScreen.style.display = 'block';
  mainScreen.style.display = 'none';
}

function showMainScreen(settings) {
  loginScreen.style.display = 'none';
  mainScreen.style.display = 'block';

  userName.textContent = settings.userEmail || 'User';
  autoScanToggle.checked = settings.autoScanEnabled !== false;

  // Load data for current tab
  loadOwnerData();
  loadSightingAlerts();
  loadStolenCount();
}

loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  loginError.textContent = '';
  loginBtn.textContent = 'Signing in...';
  loginBtn.disabled = true;

  const email = document.getElementById('emailInput').value;
  const password = document.getElementById('passwordInput').value;

  const result = await new Promise((resolve) => {
    chrome.runtime.sendMessage({
      action: 'login',
      data: { email, password }
    }, resolve);
  });

  if (result.success) {
    const settings = await getSettings();
    showMainScreen(settings);
  } else {
    loginError.textContent = result.error || 'Login failed';
    loginBtn.textContent = 'Sign In';
    loginBtn.disabled = false;
  }
});

logoutBtn.addEventListener('click', async () => {
  await new Promise((resolve) => {
    chrome.runtime.sendMessage({ action: 'logout' }, resolve);
  });
  showLoginScreen();
});

// ============================================================
// TABS
// ============================================================

function setupTabs() {
  const tabs = document.querySelectorAll('.tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      // Deactivate all
      tabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      // Activate clicked
      tab.classList.add('active');
      const tabId = tab.getAttribute('data-tab');
      document.getElementById(`tab-${tabId}`).classList.add('active');
    });
  });
}

// ============================================================
// OWNER TAB DATA
// ============================================================

async function loadOwnerData() {
  // Get match reports
  const result = await new Promise((resolve) => {
    chrome.runtime.sendMessage({ action: 'getMyMatches' }, resolve);
  });

  if (result.success && result.matches) {
    document.getElementById('matchCount').textContent = result.match_count || 0;
    renderMatchList(result.matches);
  }

  // Get scan count from storage
  const stored = await chrome.storage.local.get(['scanCountToday', 'registeredCount']);
  document.getElementById('scannedToday').textContent = stored.scanCountToday || 0;
  document.getElementById('registeredCount').textContent = stored.registeredCount || '--';
}

function renderMatchList(matches) {
  const list = document.getElementById('matchList');

  if (!matches || matches.length === 0) {
    list.innerHTML = '<div class="empty-state">No matches yet. Browse eBay to start scanning.</div>';
    return;
  }

  list.innerHTML = matches.slice(0, 10).map(m => {
    const isStolen = m.comic && m.comic.title;
    const badgeClass = m.status === 'confirmed' ? 'stolen' : m.status === 'dismissed' ? 'clear' : 'match';
    const badgeText = m.status === 'confirmed' ? 'Confirmed' : m.status === 'dismissed' ? 'Dismissed' : 'Pending';
    const date = m.reported_at ? new Date(m.reported_at).toLocaleDateString() : '';

    return `
      <div class="list-item" onclick="window.open('${m.listing_url}', '_blank')">
        <span class="li-icon">\u{1F6E1}\u{FE0F}</span>
        <div>
          <div class="li-title">${m.comic?.title || 'Unknown'} #${m.comic?.issue_number || '?'}</div>
          <div class="li-sub">${m.serial_number} \u{2022} ${m.confidence || 0}% \u{2022} ${date}</div>
        </div>
        <span class="li-badge ${badgeClass}">${badgeText}</span>
      </div>
    `;
  }).join('');
}

// ============================================================
// SIGHTING ALERTS (Owner tab)
// ============================================================

async function loadSightingAlerts() {
  const result = await new Promise((resolve) => {
    chrome.runtime.sendMessage({ action: 'getMySightings' }, resolve);
  });

  if (result.success) {
    document.getElementById('sightingCount').textContent = result.unresponded || 0;
    renderSightingList(result.sightings);
  }
}

function renderSightingList(sightings) {
  const list = document.getElementById('sightingList');

  if (!sightings || sightings.length === 0) {
    list.innerHTML = '<div class="empty-state">No sighting reports yet.</div>';
    return;
  }

  list.innerHTML = sightings.slice(0, 8).map(s => {
    const date = s.created_at ? new Date(s.created_at).toLocaleDateString() : '';
    const responded = !!s.owner_response;
    const responseLabels = {
      'confirmed_mine': 'Confirmed',
      'not_mine': 'Not Mine',
      'investigating': 'Checking'
    };

    let badgeClass, badgeText;
    if (s.owner_response === 'confirmed_mine') {
      badgeClass = 'stolen';
      badgeText = 'Confirmed';
    } else if (s.owner_response === 'not_mine') {
      badgeClass = 'clear';
      badgeText = 'Not Mine';
    } else if (s.owner_response === 'investigating') {
      badgeClass = 'match';
      badgeText = 'Checking';
    } else {
      badgeClass = 'match';
      badgeText = 'New';
    }

    return `
      <div class="list-item" onclick="window.open('${s.listing_url}', '_blank')">
        <span class="li-icon">${responded ? '\u{1F4CB}' : '\u{1F514}'}</span>
        <div>
          <div class="li-title">${s.title || 'Unknown'} #${s.issue || '?'}</div>
          <div class="li-sub">${s.serial_number} \u{2022} ${date}</div>
        </div>
        <span class="li-badge ${badgeClass}">${badgeText}</span>
      </div>
    `;
  }).join('');
}

// ============================================================
// STOLEN COUNT (Law Enforcement tab)
// ============================================================

async function loadStolenCount() {
  const result = await new Promise((resolve) => {
    chrome.runtime.sendMessage({ action: 'getStolenHashes' }, resolve);
  });

  if (result.stolenHashCount !== undefined) {
    document.getElementById('stolenCount').textContent = result.stolenHashCount;
  }
}

// ============================================================
// SERIAL VERIFICATION (Dealer + Law Enforcement tabs)
// ============================================================

async function verifySerial(serialNumber, resultElementId) {
  const resultEl = document.getElementById(resultElementId);
  resultEl.innerHTML = '<div style="font-size: 12px; color: #6b7280;">Checking...</div>';

  try {
    const response = await fetch(`${API_BASE}/api/verify/lookup/${encodeURIComponent(serialNumber)}`);
    const data = await response.json();

    if (data.success) {
      const isStolen = data.status === 'reported_stolen';
      const statusColor = isStolen ? '#dc2626' : '#16a34a';
      const statusIcon = isStolen ? '\u{1F6A8}' : '\u{2705}';
      const statusText = isStolen ? 'REPORTED STOLEN' : 'Active Registration';

      resultEl.innerHTML = `
        <div style="background: ${isStolen ? '#fef2f2' : '#f0fdf4'}; border: 1px solid ${isStolen ? '#fecaca' : '#bbf7d0'}; border-radius: 8px; padding: 10px; margin-top: 8px;">
          <div style="font-weight: 700; color: ${statusColor}; font-size: 13px; margin-bottom: 4px;">
            ${statusIcon} ${statusText}
          </div>
          <div style="font-size: 12px; color: #374151;">
            <strong>${data.comic?.title || 'Unknown'} #${data.comic?.issue_number || '?'}</strong><br>
            Grade: ${data.comic?.grade || 'N/A'} &bull; ${data.comic?.publisher || ''}<br>
            Owner: ${data.owner?.display_name || 'Anonymous'}<br>
            Registered: ${data.registration_date ? new Date(data.registration_date).toLocaleDateString() : 'N/A'}
          </div>
        </div>
      `;

      // Save to dealer history
      saveDealerCheck(serialNumber, data);
    } else {
      resultEl.innerHTML = `
        <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; margin-top: 8px; text-align: center;">
          <div style="font-size: 13px; color: #6b7280;">\u{2139}\u{FE0F} Serial number not found</div>
        </div>
      `;
    }
  } catch (e) {
    resultEl.innerHTML = `<div style="color: #dc2626; font-size: 12px;">Error: ${e.message}</div>`;
  }
}

async function saveDealerCheck(serial, data) {
  const stored = await chrome.storage.local.get(['dealerHistory']);
  const history = stored.dealerHistory || [];
  history.unshift({
    serial,
    title: data.comic?.title,
    issue: data.comic?.issue_number,
    status: data.status,
    checked_at: new Date().toISOString()
  });
  // Keep last 20
  await chrome.storage.local.set({ dealerHistory: history.slice(0, 20) });
  renderDealerHistory(history);
}

async function renderDealerHistory(history) {
  if (!history) {
    const stored = await chrome.storage.local.get(['dealerHistory']);
    history = stored.dealerHistory || [];
  }

  const list = document.getElementById('dealerHistory');
  if (history.length === 0) {
    list.innerHTML = '<div class="empty-state">No checks yet.</div>';
    return;
  }

  list.innerHTML = history.slice(0, 8).map(h => {
    const isStolen = h.status === 'reported_stolen';
    const badgeClass = isStolen ? 'stolen' : 'clear';
    const badgeText = isStolen ? 'Stolen' : 'OK';
    return `
      <div class="list-item">
        <span class="li-icon">${isStolen ? '\u{1F6A8}' : '\u{2705}'}</span>
        <div>
          <div class="li-title">${h.title || 'Unknown'} #${h.issue || '?'}</div>
          <div class="li-sub">${h.serial} \u{2022} ${new Date(h.checked_at).toLocaleDateString()}</div>
        </div>
        <span class="li-badge ${badgeClass}">${badgeText}</span>
      </div>
    `;
  }).join('');
}

// ============================================================
// EVENT LISTENERS
// ============================================================

function setupEventListeners() {
  // Auto-scan toggle
  autoScanToggle.addEventListener('change', () => {
    chrome.storage.local.set({ autoScanEnabled: autoScanToggle.checked });
  });

  // Dealer verify
  document.getElementById('verifySerialBtn').addEventListener('click', () => {
    const serial = document.getElementById('serialInput').value.trim();
    if (serial) verifySerial(serial, 'verifyResult');
  });

  // Law enforcement verify
  document.getElementById('leVerifyBtn').addEventListener('click', () => {
    const serial = document.getElementById('leSerialInput').value.trim();
    if (serial) verifySerial(serial, 'leVerifyResult');
  });

  // Enter key on serial inputs
  document.getElementById('serialInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const serial = e.target.value.trim();
      if (serial) verifySerial(serial, 'verifyResult');
    }
  });

  document.getElementById('leSerialInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const serial = e.target.value.trim();
      if (serial) verifySerial(serial, 'leVerifyResult');
    }
  });

  // Settings button
  settingsBtn.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  // Load dealer history on tab switch
  document.querySelector('[data-tab="dealer"]').addEventListener('click', () => {
    renderDealerHistory();
  });
}
