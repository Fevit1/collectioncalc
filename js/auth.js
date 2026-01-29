// ============================================
// AUTH.JS - Authentication and user management
// ============================================

// Check auth on page load
document.addEventListener('DOMContentLoaded', () => {
    checkAuthState();
    handleAuthRedirects();
});

async function checkAuthState() {
    // Load token from localStorage if not already set
    if (!authToken) {
        authToken = localStorage.getItem('cc_auth_token');
    }
    
    if (!authToken) {
        updateAuthUI(false);
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/api/auth/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await response.json();
        
        if (data.success) {
            currentUser = data.user;
            updateAuthUI(true);
        } else {
            localStorage.removeItem('cc_auth_token');
            authToken = null;
            updateAuthUI(false);
        }
    } catch (e) {
        console.error('Auth check failed:', e);
        updateAuthUI(false);
    }
}

function handleAuthRedirects() {
    const urlParams = new URLSearchParams(window.location.search);
    const verifyToken = urlParams.get('token');
    const action = urlParams.get('action');
    
    if (verifyToken && !action) {
        verifyEmail(verifyToken);
    } else if (action === 'reset-password' && verifyToken) {
        openAuthModal('reset');
        window.resetToken = verifyToken;
    }
    
    if (verifyToken || action) {
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

async function verifyEmail(token) {
    try {
        const response = await fetch(`${API_URL}/api/auth/verify/${token}`);
        const data = await response.json();
        
        if (data.success) {
            if (data.token) {
                authToken = data.token;
                localStorage.setItem('cc_auth_token', authToken);
                currentUser = data.user;
                updateAuthUI(true);
            }
            showAuthSuccess('Email verified! You are now logged in.');
        } else {
            showAuthError(data.error || 'Verification failed');
        }
    } catch (e) {
        showAuthError('Verification failed. Please try again.');
    }
}

function updateAuthUI(loggedIn) {
    const loggedOutEl = document.getElementById('authLoggedOut');
    const loggedInEl = document.getElementById('authLoggedIn');
    const userEmailEl = document.getElementById('userEmail');
    const userAvatarEl = document.getElementById('userAvatar');
    const adminMenuItem = document.getElementById('adminMenuItem');
    
    if (loggedIn && currentUser) {
        loggedOutEl.style.display = 'none';
        loggedInEl.style.display = 'flex';
        
        const email = currentUser.email;
        userEmailEl.textContent = email.length > 20 ? email.slice(0, 17) + '...' : email;
        userAvatarEl.textContent = email.charAt(0).toUpperCase();
        
        if (adminMenuItem) {
            adminMenuItem.style.display = currentUser.is_admin ? 'block' : 'none';
        }
    } else {
        loggedOutEl.style.display = 'flex';
        loggedInEl.style.display = 'none';
        if (adminMenuItem) {
            adminMenuItem.style.display = 'none';
        }
    }
}

// ============================================
// AUTH MODAL
// ============================================

function openAuthModal(tab = 'login') {
    const modal = document.getElementById('authModal');
    modal.classList.add('show');
    switchAuthTab(tab);
    clearAuthMessages();
}

function closeAuthModal() {
    const modal = document.getElementById('authModal');
    modal.classList.remove('show');
    clearAuthMessages();
}

function switchAuthTab(tab) {
    document.getElementById('tabLogin').classList.toggle('active', tab === 'login');
    document.getElementById('tabSignup').classList.toggle('active', tab === 'signup');
    
    document.getElementById('loginForm').classList.toggle('active', tab === 'login');
    document.getElementById('signupForm').classList.toggle('active', tab === 'signup');
    document.getElementById('forgotForm').classList.toggle('active', tab === 'forgot');
    document.getElementById('resetForm').classList.toggle('active', tab === 'reset');
    document.getElementById('verificationNeeded').classList.toggle('active', tab === 'verify');
    
    const title = document.getElementById('authModalTitle');
    const subtitle = document.getElementById('authModalSubtitle');
    
    if (tab === 'login') {
        title.textContent = 'Welcome Back';
        subtitle.textContent = 'Log in to save your collection';
    } else if (tab === 'signup') {
        title.textContent = 'Create Account';
        subtitle.textContent = 'Save your collection and access it anywhere';
    } else if (tab === 'forgot') {
        title.textContent = 'Reset Password';
        subtitle.textContent = '';
    } else if (tab === 'reset') {
        title.textContent = 'Set New Password';
        subtitle.textContent = '';
    } else if (tab === 'verify') {
        title.textContent = 'Verify Email';
        subtitle.textContent = '';
    }
    
    clearAuthMessages();
}

function showForgotPassword() {
    switchAuthTab('forgot');
}

function clearAuthMessages() {
    document.getElementById('authError').classList.remove('show');
    document.getElementById('authError').textContent = '';
    document.getElementById('authSuccess').classList.remove('show');
    document.getElementById('authSuccess').textContent = '';
}

function showAuthError(msg) {
    const el = document.getElementById('authError');
    el.textContent = msg;
    el.classList.add('show');
}

function showAuthSuccess(msg) {
    const el = document.getElementById('authSuccess');
    el.textContent = msg;
    el.classList.add('show');
}

// ============================================
// AUTH HANDLERS
// ============================================

async function handleLogin(e) {
    e.preventDefault();
    clearAuthMessages();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const btn = document.getElementById('loginBtn');
    
    btn.disabled = true;
    btn.textContent = 'Logging in...';
    
    try {
        const response = await fetch(`${API_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            authToken = data.token;
            localStorage.setItem('cc_auth_token', authToken);
            currentUser = data.user;
            updateAuthUI(true);
            closeAuthModal();
        } else if (data.needs_verification) {
            pendingVerificationEmail = email;
            switchAuthTab('verify');
        } else {
            showAuthError(data.error || 'Login failed');
        }
    } catch (e) {
        showAuthError('Connection error. Please try again.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Log In';
    }
}

async function handleSignup(e) {
    e.preventDefault();
    clearAuthMessages();
    
    const email = document.getElementById('signupEmail').value;
    const password = document.getElementById('signupPassword').value;
    const confirm = document.getElementById('signupPasswordConfirm').value;
    const btn = document.getElementById('signupBtn');
    
    if (password !== confirm) {
        showAuthError('Passwords do not match');
        return;
    }
    
    btn.disabled = true;
    btn.textContent = 'Creating account...';
    
    try {
        const response = await fetch(`${API_URL}/api/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            pendingVerificationEmail = email;
            switchAuthTab('verify');
            showAuthSuccess('Account created! Check your email to verify.');
        } else {
            showAuthError(data.error || 'Signup failed');
        }
    } catch (e) {
        showAuthError('Connection error. Please try again.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Create Account';
    }
}

async function handleForgotPassword(e) {
    e.preventDefault();
    clearAuthMessages();
    
    const email = document.getElementById('forgotEmail').value;
    const btn = document.getElementById('forgotBtn');
    
    btn.disabled = true;
    btn.textContent = 'Sending...';
    
    try {
        const response = await fetch(`${API_URL}/api/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        
        const data = await response.json();
        showAuthSuccess(data.message || 'If an account exists, a reset email has been sent.');
    } catch (e) {
        showAuthError('Connection error. Please try again.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Send Reset Link';
    }
}

async function handleResetPassword(e) {
    e.preventDefault();
    clearAuthMessages();
    
    const password = document.getElementById('resetPassword').value;
    const confirm = document.getElementById('resetPasswordConfirm').value;
    const btn = document.getElementById('resetBtn');
    
    if (password !== confirm) {
        showAuthError('Passwords do not match');
        return;
    }
    
    if (!window.resetToken) {
        showAuthError('Invalid reset link. Please request a new one.');
        return;
    }
    
    btn.disabled = true;
    btn.textContent = 'Resetting...';
    
    try {
        const response = await fetch(`${API_URL}/api/auth/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: window.resetToken, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (data.token) {
                authToken = data.token;
                localStorage.setItem('cc_auth_token', authToken);
                currentUser = data.user;
                updateAuthUI(true);
            }
            showAuthSuccess('Password reset! You are now logged in.');
            setTimeout(() => closeAuthModal(), 2000);
        } else {
            showAuthError(data.error || 'Reset failed');
        }
    } catch (e) {
        showAuthError('Connection error. Please try again.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Reset Password';
    }
}

async function resendVerification() {
    if (!pendingVerificationEmail) {
        showAuthError('Please enter your email first');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/api/auth/resend-verification`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: pendingVerificationEmail })
        });
        
        const data = await response.json();
        showAuthSuccess(data.message || 'Verification email sent!');
    } catch (e) {
        showAuthError('Failed to resend. Please try again.');
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('cc_auth_token');
    updateAuthUI(false);
    closeUserMenu();
}

// ============================================
// USER MENU
// ============================================

function toggleUserMenu() {
    const dropdown = document.getElementById('userMenuDropdown');
    dropdown.classList.toggle('show');
}

function closeUserMenu() {
    const dropdown = document.getElementById('userMenuDropdown');
    dropdown.classList.remove('show');
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('.user-menu')) {
        closeUserMenu();
    }
});

// ============================================
// COLLECTION FUNCTIONS
// ============================================

async function saveToCollection(comics) {
    if (!authToken) {
        openAuthModal('login');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/api/collection/save`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ comics })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`✅ Saved ${data.count} comic(s) to your collection!`);
        } else {
            alert('Failed to save: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Connection error. Please try again.');
    }
}

async function showCollection() {
    if (!authToken) {
        openAuthModal('login');
        return;
    }
    
    closeUserMenu();
    
    try {
        const response = await fetch(`${API_URL}/api/collection`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (data.count === 0) {
                alert('📚 Your collection is empty!\n\nValue some comics and click "Save to Collection" to get started.');
            } else {
                alert(`📚 Your Collection\n\n${data.count} comic(s) saved.\n\nFull collection view coming soon!`);
            }
        } else {
            alert('Failed to load collection: ' + (data.error || 'Unknown error'));
        }
    } catch (e) {
        alert('Connection error. Please try again.');
    }
}

function saveAllToCollection() {
    const valuedComics = extractedItems.filter(item => item.valuation);
    
    if (valuedComics.length === 0) {
        alert('No valued comics to save. Get valuations first!');
        return;
    }
    
    const comics = valuedComics.map(item => ({
        title: item.title,
        issue: item.issue,
        grade: item.grade,
        publisher: item.publisher,
        year: item.year,
        printing: item.printing,
        cover: item.cover,
        variant: item.variant,
        edition: item.edition,
        is_signed: item.is_signed,
        signer: item.signer,
        defects: item.defects,
        valuation: item.valuation,
        image: item.image ? item.image.substring(0, 500) + '...' : null,
        saved_date: new Date().toISOString()
    }));
    
    saveToCollection(comics);
}

console.log('auth.js loaded');
