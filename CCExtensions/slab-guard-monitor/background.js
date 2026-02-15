/**
 * Slab Guard Monitor - Background Service Worker
 * Manages stolen hash cache, periodic refresh, and badge count.
 */

const API_BASE = 'https://collectioncalc-docker.onrender.com';
const CACHE_REFRESH_HOURS = 6;
const ALARM_NAME = 'refresh-stolen-hashes';

// ============================================================
// STOLEN HASH CACHE
// ============================================================

async function refreshStolenHashes() {
  console.log('Slab Guard: Refreshing stolen hash cache...');

  try {
    const response = await fetch(`${API_BASE}/api/monitor/stolen-hashes`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    if (data.success) {
      await chrome.storage.local.set({
        stolenHashes: data.stolen_comics,
        stolenHashCount: data.count,
        stolenHashesLastUpdated: data.last_updated
      });
      console.log(`Slab Guard: Cached ${data.count} stolen hashes`);
    }
  } catch (e) {
    console.error('Slab Guard: Failed to refresh stolen hashes:', e);
  }
}

// ============================================================
// AUTH HELPERS
// ============================================================

async function getAuthToken() {
  const result = await chrome.storage.local.get(['authToken']);
  return result.authToken || null;
}

async function getAuthHeaders() {
  const token = await getAuthToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

// ============================================================
// API CALLS (proxied for content scripts)
// ============================================================

async function checkImage(imageUrl, stolenOnly = false) {
  try {
    const response = await fetch(`${API_BASE}/api/monitor/check-image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_url: imageUrl,
        stolen_only: stolenOnly,
        max_distance: 20
      })
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (e) {
    console.error('Slab Guard: check-image error:', e);
    return { success: false, error: e.message };
  }
}

async function reportMatch(matchData) {
  const headers = await getAuthHeaders();

  try {
    const response = await fetch(`${API_BASE}/api/monitor/report-match`, {
      method: 'POST',
      headers,
      body: JSON.stringify(matchData)
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (e) {
    console.error('Slab Guard: report-match error:', e);
    return { success: false, error: e.message };
  }
}

async function getMyMatches() {
  const headers = await getAuthHeaders();

  try {
    const response = await fetch(`${API_BASE}/api/monitor/my-matches`, { headers });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (e) {
    console.error('Slab Guard: my-matches error:', e);
    return { success: false, error: e.message };
  }
}

async function loginUser(email, password) {
  try {
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();
    if (data.success && data.token) {
      await chrome.storage.local.set({
        authToken: data.token,
        userEmail: email,
        userName: data.user?.name || email,
        userRole: data.user?.role || 'owner'
      });
    }
    return data;
  } catch (e) {
    return { success: false, error: e.message };
  }
}

// ============================================================
// BADGE MANAGEMENT
// ============================================================

async function updateBadge() {
  const result = await chrome.storage.local.get(['unreviewedMatchCount']);
  const count = result.unreviewedMatchCount || 0;

  if (count > 0) {
    chrome.action.setBadgeText({ text: String(count) });
    chrome.action.setBadgeBackgroundColor({ color: '#e74c3c' });
  } else {
    chrome.action.setBadgeText({ text: '' });
  }
}

// ============================================================
// MESSAGE HANDLER (from content scripts & popup)
// ============================================================

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const { action, data } = message;

  switch (action) {
    case 'checkImage':
      checkImage(data.imageUrl, data.stolenOnly)
        .then(sendResponse);
      return true; // async response

    case 'reportMatch':
      reportMatch(data)
        .then(sendResponse);
      return true;

    case 'getMyMatches':
      getMyMatches()
        .then(sendResponse);
      return true;

    case 'login':
      loginUser(data.email, data.password)
        .then(sendResponse);
      return true;

    case 'logout':
      chrome.storage.local.remove(['authToken', 'userEmail', 'userName', 'userRole'])
        .then(() => sendResponse({ success: true }));
      return true;

    case 'refreshHashes':
      refreshStolenHashes()
        .then(() => sendResponse({ success: true }));
      return true;

    case 'getStolenHashes':
      chrome.storage.local.get(['stolenHashes', 'stolenHashCount', 'stolenHashesLastUpdated'])
        .then(sendResponse);
      return true;

    case 'updateBadge':
      chrome.storage.local.set({ unreviewedMatchCount: data.count })
        .then(() => {
          updateBadge();
          sendResponse({ success: true });
        });
      return true;

    case 'getSettings':
      chrome.storage.local.get([
        'autoScanEnabled', 'scanSensitivity', 'notificationsEnabled',
        'soundAlerts', 'authToken', 'userEmail', 'userName', 'userRole'
      ]).then(sendResponse);
      return true;

    default:
      sendResponse({ error: 'Unknown action' });
  }
});

// ============================================================
// ALARMS (periodic hash refresh)
// ============================================================

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) {
    refreshStolenHashes();
  }
});

// ============================================================
// INSTALL / STARTUP
// ============================================================

chrome.runtime.onInstalled.addListener(() => {
  console.log('Slab Guard Monitor installed!');

  // Set defaults
  chrome.storage.local.set({
    autoScanEnabled: true,
    scanSensitivity: 'medium', // low=5, medium=10, high=15
    notificationsEnabled: true,
    soundAlerts: false,
    unreviewedMatchCount: 0
  });

  // Initial hash fetch
  refreshStolenHashes();

  // Set up periodic refresh
  chrome.alarms.create(ALARM_NAME, {
    periodInMinutes: CACHE_REFRESH_HOURS * 60
  });
});

chrome.runtime.onStartup.addListener(() => {
  refreshStolenHashes();
  updateBadge();
});
