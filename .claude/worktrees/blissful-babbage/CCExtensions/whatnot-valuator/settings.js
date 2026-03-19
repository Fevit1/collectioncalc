// settings.js - Extension authentication settings page
// Handles login/logout to Slab Worthy backend for Vision API access

const API_BASE = 'https://collectioncalc-docker.onrender.com';

document.addEventListener('DOMContentLoaded', async () => {
  // Check if already authenticated
  const token = await getStored('slab_worthy_jwt');
  if (token) {
    // Validate token is still good
    const valid = await validateToken(token);
    if (valid) {
      showAuthSection();
    } else {
      // Token expired, clear it
      await clearAuth();
      showLoginSection();
    }
  } else {
    showLoginSection();
  }

  // Event listeners
  document.getElementById('login-btn').addEventListener('click', handleLogin);
  document.getElementById('logout-btn').addEventListener('click', handleLogout);

  // Allow Enter key to submit
  document.getElementById('password').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleLogin();
  });
});


// ============================================
// LOGIN / LOGOUT
// ============================================

async function handleLogin() {
  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;
  const errorDiv = document.getElementById('error');
  const loginBtn = document.getElementById('login-btn');

  errorDiv.textContent = '';

  if (!email || !password) {
    errorDiv.textContent = 'Email and password are required.';
    return;
  }

  // Disable button during request
  loginBtn.disabled = true;
  loginBtn.textContent = 'Signing in...';

  try {
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    if (!data.success) {
      errorDiv.textContent = data.error || 'Login failed.';
      loginBtn.disabled = false;
      loginBtn.textContent = 'Sign In';
      return;
    }

    // Store credentials
    await chrome.storage.local.set({
      slab_worthy_jwt: data.token,
      slab_worthy_email: email,
      slab_worthy_plan: data.user?.plan || 'free',
      slab_worthy_user_id: data.user?.id || null
    });

    // Clear form
    document.getElementById('email').value = '';
    document.getElementById('password').value = '';

    showAuthSection();
    console.log('[Settings] Logged in:', email, 'Plan:', data.user?.plan);

  } catch (e) {
    errorDiv.textContent = `Connection error: ${e.message}`;
  }

  loginBtn.disabled = false;
  loginBtn.textContent = 'Sign In';
}


async function handleLogout() {
  await clearAuth();
  showLoginSection();
  console.log('[Settings] Logged out');
}


// ============================================
// TOKEN VALIDATION
// ============================================

async function validateToken(token) {
  try {
    // Use the billing plan endpoint as a lightweight token check
    const response = await fetch(`${API_BASE}/api/billing/my-plan`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
      const data = await response.json();
      // Update stored plan info in case it changed
      if (data.plan) {
        await chrome.storage.local.set({
          slab_worthy_plan: data.plan
        });
      }
      return true;
    }

    return false;
  } catch (e) {
    // Network error - assume token is still valid (offline mode)
    console.log('[Settings] Token validation failed (network):', e.message);
    return true;
  }
}


// ============================================
// UI HELPERS
// ============================================

function showLoginSection() {
  document.getElementById('login-section').style.display = 'block';
  document.getElementById('auth-section').style.display = 'none';
}

async function showAuthSection() {
  document.getElementById('login-section').style.display = 'none';
  document.getElementById('auth-section').style.display = 'block';

  // Populate user info
  const email = await getStored('slab_worthy_email');
  const plan = await getStored('slab_worthy_plan');

  document.getElementById('user-email').textContent = email || 'Unknown';

  const planEl = document.getElementById('user-plan');
  planEl.textContent = (plan || 'free').toUpperCase();
  planEl.className = `plan-badge plan-${plan || 'free'}`;

  // Show feature status
  const featureEl = document.getElementById('feature-status');
  const hasVision = ['guard', 'dealer'].includes(plan);

  if (hasVision) {
    featureEl.innerHTML = '<div style="color:#2ed573; font-size:13px;">📷 Vision scanning enabled</div>';
  } else {
    featureEl.innerHTML = `
      <div style="color:#e94560; font-size:13px;">
        📷 Vision scanning requires Guard or Dealer plan.
        <a href="https://slabworthy.com/pricing.html" target="_blank" style="color:#e94560;">Upgrade</a>
      </div>
    `;
  }
}


// ============================================
// STORAGE HELPERS
// ============================================

function getStored(key) {
  return new Promise(resolve => {
    chrome.storage.local.get(key, result => {
      resolve(result[key] || null);
    });
  });
}

async function clearAuth() {
  return chrome.storage.local.remove([
    'slab_worthy_jwt',
    'slab_worthy_email',
    'slab_worthy_plan',
    'slab_worthy_user_id'
  ]);
}
