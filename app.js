        const API_URL = 'https://collectioncalc.onrender.com';
        let currentMode = 'manual';
        let extractedItems = [];
        let uploadedFiles = []; // Store file references for rotation
        let currentSort = 'default';
        let originalOrder = []; // Store original order for "Order Added" sort
        
        // eBay integration state
        let ebayUserId = localStorage.getItem('ebay_user_id') || generateUserId();
        let ebayConnected = false;
        
        // ============================================
        // AUTH STATE
        // ============================================
        let authToken = localStorage.getItem('cc_auth_token') || null;
        let currentUser = null;
        let pendingVerificationEmail = null;
        
        // Check auth on page load
        document.addEventListener('DOMContentLoaded', () => {
            checkAuthState();
            handleAuthRedirects();
        });
        
        async function checkAuthState() {
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
                    // Token invalid/expired
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
            // Handle email verification redirect
            const urlParams = new URLSearchParams(window.location.search);
            const verifyToken = urlParams.get('token');
            const action = urlParams.get('action');
            
            if (verifyToken && !action) {
                // Email verification
                verifyEmail(verifyToken);
            } else if (action === 'reset-password' && verifyToken) {
                // Password reset
                openAuthModal('reset');
                window.resetToken = verifyToken;
            }
            
            // Clean up URL
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
                
                // Show email (truncated if long)
                const email = currentUser.email;
                userEmailEl.textContent = email.length > 20 ? email.slice(0, 17) + '...' : email;
                userAvatarEl.textContent = email.charAt(0).toUpperCase();
                
                // Show admin button only for admins
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
            // Update tabs
            document.getElementById('tabLogin').classList.toggle('active', tab === 'login');
            document.getElementById('tabSignup').classList.toggle('active', tab === 'signup');
            
            // Update forms
            document.getElementById('loginForm').classList.toggle('active', tab === 'login');
            document.getElementById('signupForm').classList.toggle('active', tab === 'signup');
            document.getElementById('forgotForm').classList.toggle('active', tab === 'forgot');
            document.getElementById('resetForm').classList.toggle('active', tab === 'reset');
            document.getElementById('verificationNeeded').classList.toggle('active', tab === 'verify');
            
            // Update header
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
        
        // Close menu when clicking outside
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
            
            // For now, just show a basic alert - will build full collection view later
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
        
        // Helper to get auth headers
        function getAuthHeaders() {
            const headers = { 'Content-Type': 'application/json' };
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }
            return headers;
        }
        
        function saveAllToCollection() {
            // Get all valued comics from extractedItems
            const valuedComics = extractedItems.filter(item => item.valuation);
            
            if (valuedComics.length === 0) {
                alert('No valued comics to save. Get valuations first!');
                return;
            }
            
            // Format for saving
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
                image: item.image ? item.image.substring(0, 500) + '...' : null, // Truncate image for storage
                saved_date: new Date().toISOString()
            }));
            
            saveToCollection(comics);
        }

        function generateUserId() {
            const id = 'user_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('ebay_user_id', id);
            return id;
        }
        
        async function checkEbayConnection() {
            try {
                const response = await fetch(`${API_URL}/api/ebay/status?user_id=${ebayUserId}`);
                const data = await response.json();
                ebayConnected = data.connected;
                return ebayConnected;
            } catch (e) {
                console.log('eBay status check failed:', e);
                return false;
            }
        }
        
        async function connectEbay() {
            try {
                const response = await fetch(`${API_URL}/api/ebay/auth?user_id=${ebayUserId}`);
                const data = await response.json();
                
                // Open eBay auth in popup
                const popup = window.open(data.auth_url, 'ebay_auth', 'width=600,height=700');
                
                // Listen for completion
                window.addEventListener('message', async (event) => {
                    if (event.data.type === 'ebay_auth') {
                        if (event.data.success) {
                            ebayConnected = true;
                            updateEbayUI();
                        }
                    }
                });
            } catch (e) {
                console.error('eBay connect failed:', e);
                alert('Failed to connect to eBay. Please try again.');
            }
        }
        
        function updateEbayUI() {
            const ebaySection = document.getElementById('ebaySection');
            if (ebaySection) {
                if (ebayConnected) {
                    ebaySection.innerHTML = `
                        <p class="ebay-connected">✓ eBay Connected</p>
                        <div class="list-buttons" id="listButtons"></div>
                    `;
                } else {
                    ebaySection.innerHTML = `
                        <button class="ebay-connect-btn" onclick="connectEbay()">
                            <svg class="ebay-logo" viewBox="0 0 24 24" fill="currentColor"><path d="M7.95 5.63c-3.16 0-5.7 2.31-5.7 5.16 0 2.13 1.39 3.94 3.34 4.65v.01c.3.11.59.25.86.41.97.57 1.62 1.57 1.62 2.73 0 1.78-1.5 3.22-3.36 3.22-.93 0-1.77-.37-2.38-.96l-.01-.01c-.15-.15-.38-.15-.53 0-.15.15-.15.38 0 .53.76.74 1.8 1.19 2.92 1.19 2.31 0 4.11-1.79 4.11-3.97 0-1.51-.85-2.82-2.1-3.55-.32-.19-.67-.35-1.03-.48v-.01c-1.55-.57-2.62-2.01-2.62-3.71 0-2.22 1.89-4.01 4.23-4.01 1.4 0 2.64.66 3.41 1.67.12.16.35.19.51.07.16-.12.19-.35.07-.51-.92-1.21-2.41-2-4.09-2h.75zM16.05 5.63c-3.16 0-5.7 2.31-5.7 5.16s2.54 5.16 5.7 5.16 5.7-2.31 5.7-5.16-2.54-5.16-5.7-5.16zm0 9.17c-2.34 0-4.23-1.79-4.23-4.01s1.89-4.01 4.23-4.01 4.23 1.79 4.23 4.01-1.89 4.01-4.23 4.01z"/></svg>
                            Connect eBay Account
                        </button>
                        <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 8px;">List items directly from your valuations</p>
                    `;
                }
            }
        }
        
        // Pending listing data
        let pendingListing = null;
        
        // Placeholder image (base64 encoded SVG with calculator icon)
        const PLACEHOLDER_IMAGE = `data:image/svg+xml;base64,${btoa(`
            <svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
                <defs>
                    <linearGradient id="calcGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#4f46e5"/>
                        <stop offset="100%" stop-color="#7c3aed"/>
                    </linearGradient>
                    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#0f0f1a"/>
                        <stop offset="100%" stop-color="#1a1a2e"/>
                    </linearGradient>
                </defs>
                <rect width="300" height="300" fill="url(#bgGrad)"/>
                <!-- Calculator icon - centered and larger -->
                <g transform="translate(102, 60) scale(3)">
                    <rect x="4" y="2" width="24" height="28" rx="3" stroke="url(#calcGrad)" stroke-width="2.5" fill="none"/>
                    <rect x="7" y="5" width="18" height="7" rx="1" fill="#0f0f1a" stroke="#4f46e5" stroke-width="1"/>
                    <text x="9" y="10.5" fill="#06b6d4" font-family="Arial" font-size="5" font-weight="bold">$---.--</text>
                    <rect x="7" y="15" width="4" height="3" rx="0.5" fill="#4f46e5"/>
                    <rect x="14" y="15" width="4" height="3" rx="0.5" fill="#4f46e5"/>
                    <rect x="21" y="15" width="4" height="3" rx="0.5" fill="#7c3aed"/>
                    <rect x="7" y="20" width="4" height="3" rx="0.5" fill="#4f46e5"/>
                    <rect x="14" y="20" width="4" height="3" rx="0.5" fill="#4f46e5"/>
                    <rect x="21" y="20" width="4" height="3" rx="0.5" fill="#06b6d4"/>
                    <rect x="7" y="25" width="4" height="3" rx="0.5" fill="#4f46e5"/>
                    <rect x="14" y="25" width="4" height="3" rx="0.5" fill="#4f46e5"/>
                    <rect x="21" y="25" width="4" height="3" rx="0.5" fill="#10b981"/>
                </g>
                <text x="150" y="210" text-anchor="middle" fill="#7c3aed" font-family="Arial" font-size="16" font-weight="bold">CollectionCalc</text>
                <text x="150" y="240" text-anchor="middle" fill="#94a3b8" font-family="Arial" font-size="12">Photo Coming Soon</text>
                <text x="150" y="260" text-anchor="middle" fill="#64748b" font-family="Arial" font-size="10">Add your photo on eBay</text>
            </svg>
        `)}`;
        
        async function listOnEbay(title, issue, price, tier) {
            if (!ebayConnected) {
                alert('Please connect your eBay account first');
                return;
            }
            
            // Get the grade from the form
            const grade = document.getElementById('grade')?.value || 'VF';
            
            // Store pending listing data
            pendingListing = { title, issue, price, tier, grade, description: '', image: null };
            
            // Show modal with loading state
            const modal = document.getElementById('listingModal');
            const modalBody = document.getElementById('listingModalBody');
            
            modalBody.innerHTML = `
                <div class="listing-generating">
                    <div class="spinner"></div>
                    <p>Generating professional description...</p>
                </div>
            `;
            
            modal.classList.add('show');
            document.getElementById('confirmListingBtn').disabled = true;
            
            try {
                // Generate description via API
                const response = await fetch(`${API_URL}/api/ebay/generate-description`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        title: title,
                        issue: issue,
                        grade: grade,
                        price: price
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    pendingListing.description = result.description;
                    showListingPreview();
                } else {
                    throw new Error(result.error || 'Failed to generate description');
                }
            } catch (e) {
                console.error('Description generation error:', e);
                // Use a basic fallback description
                pendingListing.description = `<p><b>Condition:</b> ${grade}</p><p>Please review photos carefully. Feel free to ask any questions!</p>`;
                showListingPreview();
            }
        }
        
        async function listItemOnEbay(idx) {
            const item = extractedItems[idx];
            if (!item) return;
            
            if (!ebayConnected) {
                connectEbay();
                return;
            }
            
            const price = item.selectedPrice || item.fair_value || item.value || 0;
            const tierNames = { quick: 'Quick Sale', fair: 'Fair Value', high: 'High End' };
            const tier = tierNames[item.selectedTier] || 'Fair Value';
            const grade = item.grade || 'VF';
            
            // Store pending listing data
            pendingListing = { 
                title: item.title, 
                issue: item.issue, 
                price, 
                tier, 
                grade, 
                description: '',
                image: item.image || null
            };
            
            // Show modal with loading state
            const modal = document.getElementById('listingModal');
            const modalBody = document.getElementById('listingModalBody');
            
            modalBody.innerHTML = `
                <div class="listing-generating">
                    <div class="spinner"></div>
                    <p>Generating professional description...</p>
                </div>
            `;
            
            modal.classList.add('show');
            document.getElementById('confirmListingBtn').disabled = true;
            
            try {
                // Generate description via API
                const response = await fetch(`${API_URL}/api/ebay/generate-description`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        title: item.title,
                        issue: item.issue,
                        grade: grade,
                        price: price
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    pendingListing.description = result.description;
                    showListingPreview();
                } else {
                    throw new Error(result.error || 'Failed to generate description');
                }
            } catch (e) {
                console.error('Description generation error:', e);
                pendingListing.description = `<p><b>Condition:</b> ${grade}</p><p>Please review photos carefully. Feel free to ask any questions!</p>`;
                showListingPreview();
            }
        }
        
        function showListingPreview() {
            const modalBody = document.getElementById('listingModalBody');
            const { title, issue, price, tier, grade, description } = pendingListing;
            
            modalBody.innerHTML = `
                <div class="listing-preview-row">
                    <div class="listing-preview-label">Title</div>
                    <div class="listing-preview-value">${title} #${issue} - ${grade} Condition</div>
                </div>
                
                <div class="listing-preview-row">
                    <div class="listing-preview-label">Price (${tier})</div>
                    <div class="listing-preview-price">$${price.toFixed(2)}</div>
                </div>
                
                <div class="listing-preview-row">
                    <div class="listing-preview-label">${pendingListing.image ? 'Your Photo' : 'Placeholder Image'}</div>
                    <img src="${pendingListing.image || PLACEHOLDER_IMAGE}" alt="${pendingListing.image ? 'Comic cover' : 'Photo Coming Soon'}" class="listing-preview-image">
                    ${!pendingListing.image ? `<p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 5px;">
                        You can add your actual photos after listing on eBay
                    </p>` : ''}
                </div>
                
                <div class="listing-preview-row">
                    <div class="listing-preview-label">Description (editable)</div>
                    <textarea class="listing-description-edit" id="listingDescription" 
                        oninput="validateListingDescription()">${escapeHtml(description)}</textarea>
                    <div class="listing-validation" id="descriptionValidation"></div>
                </div>
            `;
            
            document.getElementById('confirmListingBtn').disabled = false;
            validateListingDescription();
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        async function validateListingDescription() {
            const description = document.getElementById('listingDescription').value;
            const validationDiv = document.getElementById('descriptionValidation');
            const confirmBtn = document.getElementById('confirmListingBtn');
            
            // Basic client-side validation
            const issues = [];
            if (description.length > 4000) {
                issues.push(`Too long (${description.length}/4000 chars)`);
            }
            if (description.length < 50) {
                issues.push('Too short (minimum 50 characters)');
            }
            if (/https?:\/\/|www\./i.test(description)) {
                issues.push('External links not allowed');
            }
            
            if (issues.length > 0) {
                validationDiv.className = 'listing-validation invalid';
                validationDiv.textContent = '⚠️ ' + issues.join(', ');
                confirmBtn.disabled = true;
            } else {
                validationDiv.className = 'listing-validation valid';
                validationDiv.textContent = '✓ Description looks good (' + description.length + '/4000 chars)';
                confirmBtn.disabled = false;
            }
            
            // Update pending listing
            pendingListing.description = description;
        }
        
        function closeListingModal() {
            document.getElementById('listingModal').classList.remove('show');
            pendingListing = null;
        }
        
        async function confirmListing() {
            if (!pendingListing) return;
            
            const confirmBtn = document.getElementById('confirmListingBtn');
            confirmBtn.disabled = true;
            confirmBtn.textContent = 'Creating listing...';
            
            try {
                const response = await fetch(`${API_URL}/api/ebay/list`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: ebayUserId,
                        title: pendingListing.title,
                        issue: pendingListing.issue,
                        price: pendingListing.price,
                        grade: pendingListing.grade,
                        description: pendingListing.description
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    closeListingModal();
                    alert(`✅ Listed successfully!\n\nView your listing:\n${result.listing_url}`);
                    window.open(result.listing_url, '_blank');
                } else if (result.needs_setup) {
                    alert(`⚠️ Setup Required\n\n${result.error}\n\nPlease set up your seller account on eBay first.`);
                } else {
                    alert(`❌ Listing failed\n\n${result.error}`);
                }
            } catch (e) {
                console.error('Listing error:', e);
                alert(`❌ Error creating listing: ${e.message}`);
            } finally {
                confirmBtn.disabled = false;
                confirmBtn.textContent = 'Confirm & List on eBay';
            }
        }
        
        document.addEventListener('DOMContentLoaded', async () => {
            // Check eBay connection status
            await checkEbayConnection();
            
            const uploadArea = document.getElementById('uploadArea');
            uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('dragover'); });
            uploadArea.addEventListener('dragleave', () => { uploadArea.classList.remove('dragover'); });
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                if (e.dataTransfer.files.length > 0) handlePhotoUpload(e.dataTransfer.files);
            });
        });
        
function setMode(mode) {
    currentMode = mode;
    document.getElementById('modeManual').classList.toggle('active', mode === 'manual');
    document.getElementById('modePhoto').classList.toggle('active', mode === 'photo');
    document.getElementById('modeGrading').classList.toggle('active', mode === 'grading');
    document.getElementById('manualMode').style.display = mode === 'manual' ? 'block' : 'none';
    document.getElementById('photoMode').style.display = mode === 'photo' ? 'block' : 'none';
    document.getElementById('gradingMode').style.display = mode === 'grading' ? 'block' : 'none';
    document.getElementById('bulkMode').style.display = 'none';
    document.getElementById('resultsMode').style.display = 'none';
    document.getElementById('result').classList.remove('show');
}
        
        function resetToPhoto() {
            document.getElementById('bulkMode').style.display = 'none';
            document.getElementById('photoMode').style.display = 'block';
        }
        
        function resetApp() {
            extractedItems = [];
            originalOrder = [];
            currentSort = 'default';
            document.getElementById('result').classList.remove('show');
            document.getElementById('resultsMode').style.display = 'none';
            document.getElementById('bulkMode').style.display = 'none';
            // Reset sort dropdown
            const sortSelect = document.getElementById('sortSelect');
            if (sortSelect) sortSelect.value = 'default';
            if (currentMode === 'photo') {
                document.getElementById('photoMode').style.display = 'block';
            }
        }
        
        // Photo upload and extraction
        async function handlePhotoUpload(files) {
            if (!files || files.length === 0) return;
            
            const fileArray = Array.from(files);
            document.getElementById('photoMode').style.display = 'none';
            document.getElementById('bulkMode').style.display = 'block';
            document.getElementById('progressContainer').style.display = 'block';
            document.getElementById('valuateAllBtn').disabled = true;
            
            for (let i = 0; i < fileArray.length; i++) {
                const file = fileArray[i];
                const fileIndex = uploadedFiles.length;
                uploadedFiles.push(file); // Store file for potential rotation
                updateProgress((i / fileArray.length) * 100, `Extracting ${i + 1} of ${fileArray.length}: ${file.name}`);
                
                try {
                    const extracted = await extractFromPhoto(file, 0);
                    extracted.fileIndex = fileIndex; // Track which file this came from
                    extracted.rotation = 0; // Track current rotation
                    extractedItems.push(extracted);
                    renderItemsList();
                } catch (error) {
                    console.error('Error extracting:', error);
                    extractedItems.push({
                        title: file.name.replace(/\.[^/.]+$/, ''),
                        issue: '',
                        publisher: '',
                        year: '',
                        grade: 'VF',
                        edition: 'unknown',
                        error: error.message,
                        fileIndex: fileIndex,
                        rotation: 0
                    });
                    renderItemsList();
                }
                
                // 3 second delay between photos
                if (i < fileArray.length - 1) {
                    await new Promise(resolve => setTimeout(resolve, 3000));
                }
            }
            
            updateProgress(100, 'Extraction complete!');
            setTimeout(() => {
                document.getElementById('progressContainer').style.display = 'none';
                document.getElementById('valuateAllBtn').disabled = false;
            }, 1000);
        }
        
        // Read EXIF orientation from image file
        // Returns orientation value 1-8, or 1 if not found
        async function getExifOrientation(file) {
            return new Promise((resolve) => {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const view = new DataView(e.target.result);
                    // Check for JPEG
                    if (view.getUint16(0, false) !== 0xFFD8) {
                        resolve(1);
                        return;
                    }
                    let offset = 2;
                    while (offset < view.byteLength) {
                        const marker = view.getUint16(offset, false);
                        offset += 2;
                        if (marker === 0xFFE1) { // APP1 marker (EXIF)
                            if (view.getUint32(offset + 2, false) !== 0x45786966) { // "Exif"
                                resolve(1);
                                return;
                            }
                            const little = view.getUint16(offset + 8, false) === 0x4949;
                            const tags = view.getUint16(offset + 16, little);
                            for (let i = 0; i < tags; i++) {
                                const tagOffset = offset + 18 + i * 12;
                                if (view.getUint16(tagOffset, little) === 0x0112) { // Orientation tag
                                    const orientation = view.getUint16(tagOffset + 8, little);
                                    console.log(`EXIF orientation: ${orientation}`);
                                    resolve(orientation);
                                    return;
                                }
                            }
                        } else if ((marker & 0xFF00) !== 0xFF00) {
                            break;
                        } else {
                            offset += view.getUint16(offset, false);
                        }
                    }
                    resolve(1); // Default: no rotation needed
                };
                reader.onerror = () => resolve(1);
                reader.readAsArrayBuffer(file.slice(0, 65536)); // Only read first 64KB for EXIF
            });
        }
        
        // Process image for optimal quality while staying under Anthropic's 5MB limit
        // Prioritizes preserving detail for signature detection
        // rotation: 0, 90, 180, 270 degrees clockwise (manual override)
        async function processImageForExtraction(file, manualRotation = 0) {
            // Get EXIF orientation first
            const exifOrientation = await getExifOrientation(file);
            
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onerror = reject;
                reader.onload = (e) => {
                    const img = new Image();
                    img.onerror = () => reject(new Error('Failed to load image'));
                    img.onload = () => {
                        const canvas = document.createElement('canvas');
                        const ctx = canvas.getContext('2d');
                        
                        let width = img.width;
                        let height = img.height;
                        
                        // Calculate total rotation needed (EXIF + manual)
                        // EXIF orientation to degrees: 1=0°, 3=180°, 6=90°, 8=270°
                        const exifRotation = {1: 0, 2: 0, 3: 180, 4: 180, 5: 90, 6: 90, 7: 270, 8: 270}[exifOrientation] || 0;
                        let totalRotation = (exifRotation + manualRotation) % 360;
                        
                        console.log(`Original image: ${width}x${height}, EXIF rotation: ${exifRotation}°, manual: ${manualRotation}°`);
                        
                        // Auto-rotate landscape images to portrait (comics are always taller than wide)
                        // Calculate what dimensions would be AFTER EXIF rotation
                        const postExifSwap = (exifRotation === 90 || exifRotation === 270);
                        const effectiveWidth = postExifSwap ? height : width;
                        const effectiveHeight = postExifSwap ? width : height;
                        
                        if (effectiveWidth > effectiveHeight && manualRotation === 0) {
                            // Image is landscape after EXIF correction - rotate 90° to make portrait
                            console.log('Auto-rotating landscape to portrait');
                            totalRotation = (totalRotation + 90) % 360;
                        }
                        
                        console.log(`Final rotation: ${totalRotation}°`);
                        
                        // Swap dimensions if rotating 90 or 270 degrees
                        const swapDimensions = totalRotation === 90 || totalRotation === 270;
                        if (swapDimensions) {
                            [width, height] = [height, width];
                        }
                        
                        // Ensure minimum resolution for detail (signatures need at least 1200px)
                        const minDimension = 1200;
                        const maxDimension = 2400; // Cap to avoid huge files
                        
                        // Scale up small images to minimum resolution
                        const currentMax = Math.max(width, height);
                        if (currentMax < minDimension) {
                            const upscale = minDimension / currentMax;
                            width = Math.round(width * upscale);
                            height = Math.round(height * upscale);
                            console.log(`Upscaling to ${width}x${height} for detail`);
                        }
                        
                        // Scale down very large images
                        if (currentMax > maxDimension) {
                            const downscale = maxDimension / currentMax;
                            width = Math.round(width * downscale);
                            height = Math.round(height * downscale);
                            console.log(`Downscaling to ${width}x${height}`);
                        }
                        
                        // Anthropic limit is 5MB base64, target 4.5MB for safety
                        const maxSizeBytes = 4.5 * 1024 * 1024;
                        
                        // Try high quality first, only reduce if necessary
                        const qualities = [0.95, 0.90, 0.85, 0.80, 0.70, 0.60];
                        const scales = [1, 0.95, 0.90, 0.85, 0.75];
                        
                        for (const scale of scales) {
                            const scaledWidth = Math.round(width * scale);
                            const scaledHeight = Math.round(height * scale);
                            canvas.width = scaledWidth;
                            canvas.height = scaledHeight;
                            
                            // Use high-quality image smoothing
                            ctx.imageSmoothingEnabled = true;
                            ctx.imageSmoothingQuality = 'high';
                            
                            // Apply rotation
                            ctx.save();
                            ctx.translate(scaledWidth / 2, scaledHeight / 2);
                            ctx.rotate(totalRotation * Math.PI / 180);
                            if (swapDimensions) {
                                ctx.drawImage(img, -scaledHeight / 2, -scaledWidth / 2, scaledHeight, scaledWidth);
                            } else {
                                ctx.drawImage(img, -scaledWidth / 2, -scaledHeight / 2, scaledWidth, scaledHeight);
                            }
                            ctx.restore();
                            
                            for (const quality of qualities) {
                                const dataUrl = canvas.toDataURL('image/jpeg', quality);
                                const base64 = dataUrl.split(',')[1];
                                const sizeBytes = base64.length;
                                
                                if (sizeBytes <= maxSizeBytes) {
                                    console.log(`Processed image: ${scaledWidth}x${scaledHeight}, ${Math.round(quality * 100)}% quality, ${(sizeBytes / 1024 / 1024).toFixed(2)}MB`);
                                    resolve({ base64, mediaType: 'image/jpeg' });
                                    return;
                                }
                            }
                        }
                        
                        // Fallback: aggressive compression
                        const fallbackWidth = Math.round(width * 0.6);
                        const fallbackHeight = Math.round(height * 0.6);
                        canvas.width = fallbackWidth;
                        canvas.height = fallbackHeight;
                        ctx.imageSmoothingEnabled = true;
                        ctx.imageSmoothingQuality = 'high';
                        ctx.save();
                        ctx.translate(fallbackWidth / 2, fallbackHeight / 2);
                        ctx.rotate(totalRotation * Math.PI / 180);
                        if (swapDimensions) {
                            ctx.drawImage(img, -fallbackHeight / 2, -fallbackWidth / 2, fallbackHeight, fallbackWidth);
                        } else {
                            ctx.drawImage(img, -fallbackWidth / 2, -fallbackHeight / 2, fallbackWidth, fallbackHeight);
                        }
                        ctx.restore();
                        const dataUrl = canvas.toDataURL('image/jpeg', 0.5);
                        const base64 = dataUrl.split(',')[1];
                        console.log(`Processed image (fallback): ${canvas.width}x${canvas.height}, ${(base64.length / 1024 / 1024).toFixed(2)}MB`);
                        resolve({ base64, mediaType: 'image/jpeg' });
                    };
                    img.src = e.target.result;
                };
                reader.readAsDataURL(file);
            });
        }
        
        async function extractFromPhoto(file, manualRotation = 0) {
            // Always process through canvas for consistent quality
            const fileSizeMB = file.size / 1024 / 1024;
            console.log(`Processing ${file.name}: ${fileSizeMB.toFixed(2)}MB`);
            
            const processed = await processImageForExtraction(file, manualRotation);
            const base64Data = processed.base64;
            const mediaType = processed.mediaType;
            
            const prompt = `Analyze this comic book image and extract information. Return ONLY a JSON object with these fields:

IDENTIFICATION FIELDS:
- title: Comic book title (usually the largest text on the cover). Include the main series name only, NOT "Annual" or "Special" - those go in issue_type.
- issue: Issue number - CRITICAL: You MUST find the issue number. Search these locations thoroughly:
  * Top-left corner near price (Marvel standard)
  * Top-right corner (DC standard)
  * Small text WITHIN or NEAR the title logo
  * Near the barcode/UPC area (bottom corners)
  * Near creator credits at bottom of cover
  * Sometimes the number is VERY SMALL or integrated into the cover design
  Look for "#1", "#2", "No. 1", or just a standalone number. First issues often have the "1" stylized or small. IGNORE prices (60¢, $1.00, $2.99). If this appears to be a first issue of a series, the issue number is "1".
- issue_type: CRITICAL - Look carefully for these indicators on the cover:
  * "Annual" or "ANNUAL" → return "Annual"
  * "King-Size Special" or "KING-SIZE SPECIAL" → return "Annual" (these are annuals)
  * "Giant-Size" or "GIANT-SIZE" → return "Giant-Size"
  * "Special" or "SPECIAL" (standalone) → return "Special"
  * "Special Edition" → return "Special Edition"
  * If none of these are present → return "Regular"
  These indicators are often in LARGE TEXT at the top of the cover or in a banner. They dramatically affect the comic's value - an Annual #6 is completely different from Regular #6.
- publisher: Publisher name (Marvel, DC, Image, etc.) - often in small text at top
- year: Publication year - look for copyright text or indicia, usually small text
- edition: Look at the BOTTOM-LEFT CORNER. If you see a UPC BARCODE, return "newsstand". If you see ARTWORK or LOGO, return "direct". If unclear, return "unknown".
- printing: Look for "2nd Printing", "3rd Print", "Second Printing", etc. anywhere on cover. Return "1st" if no printing indicator found, otherwise "2nd", "3rd", etc.
- cover: Look for cover variant indicators like "Cover A", "Cover B", "Variant Cover", "1:25", "1:50", "Incentive", "Virgin", etc. Return the variant info if found, otherwise empty string.
- variant: Other variant description if applicable (e.g., "McFarlane variant", "Artgerm cover"), otherwise empty string

CONDITION ASSESSMENT FIELDS:
Examine the comic's PHYSICAL CONDITION carefully. You can only see the front cover, so assess what's visible.

IMPORTANT - DISTINGUISH BETWEEN:
1. COMIC DEFECTS (on the actual comic) - These affect grade
2. BAG/SLEEVE ARTIFACTS (on the protective covering) - IGNORE these:
   - Price stickers on the outside of a bag
   - Reflections or glare from plastic sleeve
   - Tape on the bag opening
   - Bag wrinkles or cloudiness
   If the comic appears to be in a bag/sleeve, look THROUGH it to assess the comic itself.

3. SIGNATURE DETECTION (Two-step process):

   STEP 1 - SCAN: Before analyzing other fields, systematically scan the ENTIRE cover for any handwriting or signatures. Check ALL these areas:
   - Sky, moon, or background areas
   - Across character faces or bodies
   - Title/logo area
   - All four corners
   - Margins and edges
   - Near creator credits
   Look for: Gold/silver metallic ink (very common), black sharpie, blue/red marker, pen signatures
   
   STEP 2 - ANALYZE: If you found ANYTHING that looks like handwriting/signature:
   - Note exactly where it is located
   - Describe its appearance (ink color, style)
   - Look at creator credits at bottom of cover
   - Compare signature to creator names to estimate who signed

- suggested_grade: Based on visible condition, suggest one of: MT, NM, VF, FN, VG, G, FR, PR. Be conservative - grade what you can see.
- defects: Array of visible defects found ON THE COMIC (not on bag). Examples: "Tear on front cover", "Spine roll", "Color-breaking crease", "Corner wear", "Staining". Return empty array [] if no defects visible.
- grade_reasoning: Brief explanation of grade choice, e.g., "VF - Minor spine stress visible, corners sharp"

SIGNATURE ANALYSIS FIELDS:
- signature_detected: boolean - Did you find ANY handwriting/signature in Step 1? Even if faint or hard to read, set true if you see something.
- signature_analysis: If signature_detected is true, provide this object (otherwise null):
  {
    "creators": [{"name": "Full Name", "role": "Artist/Writer/Inker/Colorist"}],
    "confidence_scores": [{"name": "Full Name", "confidence": 55, "reasoning": "brief reason"}],
    "most_likely_signer": {"name": "Name", "confidence": 55},
    "signature_characteristics": "Location on cover, ink color (gold/silver/black/blue), style (neat/cursive/messy), any legible letters"
  }
  
  When assigning confidence: Any creator could have signed (writer, artist, inker, colorist). Give roughly equal initial weight to all listed creators. Increase confidence only if legible letters clearly match a specific name.

GRADE GUIDE (be conservative):
- MT (10.0): Perfect, virtually flawless
- NM (9.4): Nearly perfect, minor imperfections only
- VF (8.0): Minor wear, small stress marks OK, still attractive
- FN (6.0): Moderate wear, minor creases, slightly rolled spine OK
- VG (4.0): Significant wear, small tears, creases, still complete
- G (2.0): Heavy wear, larger creases, small pieces may be missing
- FR (1.5): Major wear, tears, pieces missing but still readable
- PR (1.0): Severe damage, may be incomplete

CRITICAL RULES:
1. Do NOT confuse prices (60¢, $1.50, 25p) with issue numbers. Issue numbers are preceded by "#" or "No." and are typically 1-4 digits.
2. ALWAYS check for "Annual", "King-Size Special", "Giant-Size", or "Special" - these are DIFFERENT series than the regular comic and have very different values.
3. If you see "KING-SIZE SPECIAL" anywhere, the issue_type MUST be "Annual".
4. For condition: You can ONLY see the front cover. Note this limitation.
5. Ignore bag/sleeve artifacts. Assess the comic itself.
6. SIGNATURES ARE COMMON: Look very carefully for gold, silver, or metallic ink signatures. They're often hard to see. If you see ANY handwriting that could be an autograph, set signature_detected to true.
7. ISSUE NUMBER IS REQUIRED: Look everywhere - corners, near title, near barcode, near credits. First issues often have small or stylized "1". Do NOT leave issue blank if you can find any number.

Be accurate. If unsure about any field, use reasonable estimates.`;
            
            const response = await fetch(`${API_URL}/api/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    // STANDARD TIER: Sonnet - good for most extraction, ~$0.01/comic
                    model: 'claude-sonnet-4-20250514',
                    
                    // PREMIUM TIER: Opus - better signature detection, ~$0.05/comic
                    // Proven to work! See Session 7 testing with Moon Knight #1 signed by Danny Miki
                    // TODO: Gate behind "Super User" pricing tier in future
                    // model: 'claude-opus-4-5-20251101',
                    
                    max_tokens: 1000,
                    messages: [{ role: 'user', content: [
                        { type: 'image', source: { type: 'base64', media_type: mediaType, data: base64Data }},
                        { type: 'text', text: prompt }
                    ]}]
                })
            });
            
            const data = await response.json();
            if (data.error) throw new Error(data.error.message || 'API Error');
            
            const textContent = data.content.filter(item => item.type === 'text').map(item => item.text).join('');
            const jsonMatch = textContent.match(/\{[\s\S]*\}/);
            
            if (jsonMatch) {
                const extracted = JSON.parse(jsonMatch[0]);
                // Include the image for preview and eBay listing
                extracted.image = `data:${mediaType};base64,${base64Data}`;
                // Use suggested_grade as the grade if present (for valuation)
                if (extracted.suggested_grade && !extracted.grade) {
                    extracted.grade = extracted.suggested_grade;
                }
                // Auto-populate signed fields if AI detected a signature
                if (extracted.signature_detected && extracted.signature_analysis) {
                    extracted.is_signed = true;
                    if (extracted.signature_analysis.most_likely_signer) {
                        extracted.signer = extracted.signature_analysis.most_likely_signer.name;
                    }
                }
                return extracted;
            } else {
                throw new Error('Could not extract data');
            }
        }
        
        function updateProgress(percent, text) {
            document.getElementById('progressFill').style.width = percent + '%';
            document.getElementById('progressText').textContent = text;
        }
        
        function renderItemsList() {
            const container = document.getElementById('itemsList');
            container.innerHTML = extractedItems.map((item, idx) => `
                <div class="item-card ${item.value ? 'has-value' : ''}" id="item-${idx}">
                    <div class="item-header">
                        <span class="item-number">${idx + 1}</span>
                        <span class="item-title">${item.title || 'Unknown'} #${item.issue || '?'}</span>
                        ${item.value ? `<span class="item-value">$${item.value.toFixed(2)}</span>` : ''}
                        ${item.fileIndex !== undefined ? `<button class="item-rotate" onclick="rotateItem(${idx})" title="Rotate image 90°">↻</button>` : ''}
                        <button class="item-delete" onclick="deleteItem(${idx})">×</button>
                    </div>
                    <div class="item-content" style="display: flex; gap: 15px;">
                        ${item.image ? `<img src="${item.image}" alt="Comic cover" style="width: 80px; height: auto; border-radius: 4px; object-fit: cover;">` : ''}
                        <div class="item-fields-wrapper" style="flex: 1;">
                    <div class="item-fields">
                        <div class="form-group">
                            <label>Title</label>
                            <input type="text" value="${item.title || ''}" onchange="updateItem(${idx}, 'title', this.value)">
                        </div>
                        <div class="form-group">
                            <label>Issue</label>
                            <input type="text" value="${item.issue || ''}" onchange="updateItem(${idx}, 'issue', this.value)">
                        </div>
                        <div class="form-group">
                            <label>Year</label>
                            <input type="text" value="${item.year || ''}" onchange="updateItem(${idx}, 'year', this.value)">
                        </div>
                        <div class="form-group">
                            <label>Grade</label>
                            <select onchange="updateItem(${idx}, 'grade', this.value)">
                                <option value="MT" ${(item.suggested_grade || item.grade) === 'MT' ? 'selected' : ''}>MT</option>
                                <option value="NM" ${(item.suggested_grade || item.grade) === 'NM' ? 'selected' : ''}>NM</option>
                                <option value="VF" ${(item.suggested_grade || item.grade) === 'VF' || (!item.suggested_grade && !item.grade) ? 'selected' : ''}>VF</option>
                                <option value="FN" ${(item.suggested_grade || item.grade) === 'FN' ? 'selected' : ''}>FN</option>
                                <option value="VG" ${(item.suggested_grade || item.grade) === 'VG' ? 'selected' : ''}>VG</option>
                                <option value="G" ${(item.suggested_grade || item.grade) === 'G' || (item.suggested_grade || item.grade) === 'GD' ? 'selected' : ''}>G</option>
                                <option value="FR" ${(item.suggested_grade || item.grade) === 'FR' ? 'selected' : ''}>FR</option>
                                <option value="PR" ${(item.suggested_grade || item.grade) === 'PR' ? 'selected' : ''}>PR</option>
                            </select>
                        </div>
                    </div>
                    <div class="item-fields" style="margin-top: 10px;">
                        <div class="form-group">
                            <label>Printing</label>
                            <select onchange="updateItem(${idx}, 'printing', this.value)">
                                <option value="1st" ${item.printing === '1st' || !item.printing ? 'selected' : ''}>1st</option>
                                <option value="2nd" ${item.printing === '2nd' ? 'selected' : ''}>2nd</option>
                                <option value="3rd" ${item.printing === '3rd' ? 'selected' : ''}>3rd</option>
                                <option value="4th" ${item.printing === '4th' ? 'selected' : ''}>4th+</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Cover</label>
                            <input type="text" value="${item.cover || ''}" placeholder="A, B, 1:25..." onchange="updateItem(${idx}, 'cover', this.value)">
                        </div>
                        <div class="form-group">
                            <label>Variant</label>
                            <input type="text" value="${item.variant || ''}" placeholder="Artist name..." onchange="updateItem(${idx}, 'variant', this.value)">
                        </div>
                        <div class="form-group">
                            <label>Edition</label>
                            <select onchange="updateItem(${idx}, 'edition', this.value)">
                                <option value="direct" ${item.edition === 'direct' ? 'selected' : ''}>Direct</option>
                                <option value="newsstand" ${item.edition === 'newsstand' ? 'selected' : ''}>Newsstand</option>
                                <option value="unknown" ${item.edition === 'unknown' || !item.edition ? 'selected' : ''}>Unknown</option>
                            </select>
                        </div>
                    </div>
                    <div class="item-fields" style="margin-top: 10px;">
                        <div class="form-group" style="display: flex; align-items: center; gap: 8px;">
                            <input type="checkbox" id="signed-${idx}" ${item.is_signed ? 'checked' : ''} onchange="updateItem(${idx}, 'is_signed', this.checked); document.getElementById('signer-group-${idx}').style.display = this.checked ? 'block' : 'none';">
                            <label for="signed-${idx}" style="margin: 0; cursor: pointer;">✍️ Signed copy</label>
                        </div>
                        <div class="form-group" id="signer-group-${idx}" style="display: ${item.is_signed ? 'block' : 'none'};">
                            <label>Signed by</label>
                            <input type="text" value="${item.signer || ''}" placeholder="e.g., Stan Lee, Scott Snyder" onchange="updateItem(${idx}, 'signer', this.value)">
                        </div>
                    </div>
                    ${(item.defects && item.defects.length > 0) || item.grade_reasoning ? `
                    <div class="condition-assessment" style="margin-top: 12px; padding: 10px; background: rgba(99, 102, 241, 0.1); border-radius: 6px; border-left: 3px solid var(--brand-indigo);">
                        <div style="font-weight: 600; font-size: 12px; color: var(--brand-indigo); margin-bottom: 6px;">📋 Condition Assessment</div>
                        ${item.grade_reasoning ? `<div style="font-size: 13px; margin-bottom: 6px;">${item.grade_reasoning}</div>` : ''}
                        ${item.defects && item.defects.length > 0 ? `
                        <div style="font-size: 12px; margin-bottom: 4px;">
                            <span style="color: var(--status-error);">⚠️ Defects:</span> ${item.defects.join(', ')}
                        </div>` : ''}
                    </div>
                    ` : ''}
                    ${item.signature_detected && item.signature_analysis ? `
                    <div class="signature-analysis" style="margin-top: 12px; padding: 10px; background: rgba(16, 185, 129, 0.1); border-radius: 6px; border-left: 3px solid var(--status-success);">
                        <div style="font-weight: 600; font-size: 12px; color: var(--status-success); margin-bottom: 8px;">🖊️ Signature Analysis</div>
                        ${item.signature_analysis.most_likely_signer ? `
                        <div style="font-size: 14px; font-weight: 600; margin-bottom: 8px;">
                            Most likely: ${item.signature_analysis.most_likely_signer.name} (${item.signature_analysis.most_likely_signer.confidence}% confidence)
                        </div>` : ''}
                        ${item.signature_analysis.confidence_scores && item.signature_analysis.confidence_scores.length > 0 ? `
                        <div style="font-size: 12px; margin-bottom: 8px;">
                            <div style="color: var(--text-secondary); margin-bottom: 4px;">All creators on cover:</div>
                            ${item.signature_analysis.confidence_scores.map(c => `
                                <div style="display: flex; justify-content: space-between; padding: 2px 0;">
                                    <span>${c.name}</span>
                                    <span style="color: ${c.confidence >= 50 ? 'var(--status-success)' : c.confidence >= 25 ? 'var(--status-warning)' : 'var(--text-muted)'}; font-weight: 500;">${c.confidence}%</span>
                                </div>
                            `).join('')}
                        </div>` : ''}
                        ${item.signature_analysis.signature_characteristics ? `
                        <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">
                            <em>${item.signature_analysis.signature_characteristics}</em>
                        </div>` : ''}
                        <div style="font-size: 10px; color: var(--text-muted); border-top: 1px solid rgba(255,255,255,0.1); padding-top: 6px; margin-top: 6px;">
                            ⚠️ For definitive authentication, submit to CGC or CBCS
                        </div>
                    </div>
                    ` : ''}
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        function updateItem(idx, field, value) {
            extractedItems[idx][field] = value;
            
            // Update header if title or issue changed
            if (field === 'title' || field === 'issue') {
                const card = document.getElementById('item-' + idx);
                if (card) {
                    const titleSpan = card.querySelector('.item-title');
                    if (titleSpan) {
                        const item = extractedItems[idx];
                        titleSpan.textContent = `${item.title || 'Unknown'} #${item.issue || '?'}`;
                    }
                }
            }
        }
        
        function deleteItem(idx) {
            extractedItems.splice(idx, 1);
            renderItemsList();
            if (extractedItems.length === 0) {
                resetToPhoto();
            }
        }
        
        async function rotateItem(idx) {
            const item = extractedItems[idx];
            if (item.fileIndex === undefined || !uploadedFiles[item.fileIndex]) {
                console.error('Cannot rotate: no file reference');
                return;
            }
            
            // Rotate 90 degrees clockwise
            const newRotation = ((item.rotation || 0) + 90) % 360;
            const file = uploadedFiles[item.fileIndex];
            
            // Show loading state on the card
            const card = document.getElementById('item-' + idx);
            if (card) {
                card.style.opacity = '0.5';
            }
            
            try {
                console.log(`Rotating item ${idx} to ${newRotation}°`);
                const extracted = await extractFromPhoto(file, newRotation);
                
                // Preserve fileIndex and update rotation
                extracted.fileIndex = item.fileIndex;
                extracted.rotation = newRotation;
                
                // Replace the item
                extractedItems[idx] = extracted;
                renderItemsList();
            } catch (error) {
                console.error('Error re-extracting after rotation:', error);
                // Just update the image rotation without re-extracting
                item.rotation = newRotation;
                renderItemsList();
            }
        }
        
        async function valuateAll() {
            const btn = document.getElementById('valuateAllBtn');
            btn.disabled = true;
            document.getElementById('progressContainer').style.display = 'block';
            
            for (let i = 0; i < extractedItems.length; i++) {
                const item = extractedItems[i];
                updateProgress((i / extractedItems.length) * 100, `Valuating ${i + 1} of ${extractedItems.length}`);
                
                // Show thinking animation for this comic
                showThinking(`Calculating: ${item.title} #${item.issue}`, [
                    'Checking database for matches',
                    'Searching market data',
                    'Crunching the numbers',
                    'Calculating confidence score',
                    'Generating valuation'
                ]);
                
                try {
                    const result = await getValuation(item);
                    extractedItems[i] = { ...item, ...result };
                    renderItemsList();
                    
                    // Brief pause for UI update (Tier 2 rate limits allow rapid calls)
                    if (i < extractedItems.length - 1) {
                        updateProgress(((i + 1) / extractedItems.length) * 100, `Starting next valuation...`);
                        await new Promise(resolve => setTimeout(resolve, 2000));
                    }
                } catch (error) {
                    extractedItems[i].error = error.message;
                }
            }
            
            hideThinking();
            btn.disabled = false;
            document.getElementById('progressContainer').style.display = 'none';
            showResults();
        }
        
        async function getValuation(item, forceRefresh = false) {
            const response = await fetch(`${API_URL}/api/valuate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: item.title,
                    issue: item.issue,
                    year: parseInt(item.year) || null,
                    publisher: item.publisher || null,
                    grade: item.grade || 'VF',
                    printing: item.printing || '1st',
                    cover: item.cover || '',
                    variant: item.variant || '',
                    edition: item.edition || '',
                    issue_type: item.issue_type || 'Regular',
                    is_signed: item.is_signed || false,
                    signer: item.signer || '',
                    force_refresh: forceRefresh
                })
            });
            
            const json = await response.json();
            if (json.error) throw new Error(json.error);
            
            return {
                value: json.final_value,
                confidence: json.confidence,
                confidence_score: json.confidence_score,
                source: json.source,
                reasoning: json.reasoning,
                ebay_sales: json.ebay_sales,
                ebay_price_range: json.ebay_price_range,
                sales_data: json.sales_data || [],
                quick_sale: json.quick_sale,
                fair_value: json.fair_value,
                high_end: json.high_end,
                lowest_bin: json.lowest_bin
            };
        }
        
        function sortResults(sortBy) {
            currentSort = sortBy;
            
            // Store original order if not already stored
            if (originalOrder.length === 0 || originalOrder.length !== extractedItems.length) {
                originalOrder = extractedItems.map((item, idx) => ({ ...item, originalIndex: idx }));
            }
            
            // Sort based on selection
            switch (sortBy) {
                case 'value-high':
                    extractedItems.sort((a, b) => {
                        const aVal = a.selectedPrice || a.fair_value || a.value || 0;
                        const bVal = b.selectedPrice || b.fair_value || b.value || 0;
                        return bVal - aVal;
                    });
                    break;
                case 'value-low':
                    extractedItems.sort((a, b) => {
                        const aVal = a.selectedPrice || a.fair_value || a.value || 0;
                        const bVal = b.selectedPrice || b.fair_value || b.value || 0;
                        return aVal - bVal;
                    });
                    break;
                case 'title':
                    extractedItems.sort((a, b) => {
                        const aTitle = (a.title || '').toLowerCase();
                        const bTitle = (b.title || '').toLowerCase();
                        if (aTitle === bTitle) {
                            return (parseInt(a.issue) || 0) - (parseInt(b.issue) || 0);
                        }
                        return aTitle.localeCompare(bTitle);
                    });
                    break;
                case 'default':
                default:
                    // Restore original order
                    if (originalOrder.length > 0) {
                        extractedItems = originalOrder.map(item => {
                            const current = extractedItems.find(e => 
                                e.title === item.title && e.issue === item.issue
                            );
                            return current || item;
                        });
                    }
                    break;
            }
            
            showResults();
        }
        
        function showResults() {
            document.getElementById('bulkMode').style.display = 'none';
            document.getElementById('resultsMode').style.display = 'block';
            
            const total = extractedItems.reduce((sum, item) => sum + (item.selectedPrice || item.fair_value || item.value || 0), 0);
            const valued = extractedItems.filter(item => item.value).length;
            
            document.getElementById('totalValue').textContent = '$' + total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            document.getElementById('itemCount').textContent = `${valued} item${valued !== 1 ? 's' : ''} valued`;
            
            document.getElementById('resultsList').innerHTML = extractedItems.map((item, idx) => {
                const quickSale = item.quick_sale || item.value * 0.85 || 0;
                const fairValue = item.fair_value || item.value || 0;
                const highEnd = item.high_end || item.value * 1.15 || 0;
                const selectedTier = item.selectedTier || 'fair';
                
                // Set default selected price if not set
                if (!item.selectedPrice) {
                    item.selectedPrice = fairValue;
                    item.selectedTier = 'fair';
                }
                
                return `
                <div class="item-card has-value">
                    <div class="item-header">
                        <span class="item-number">${idx + 1}</span>
                        <span class="item-title">${item.title} #${item.issue}${item.printing && item.printing !== '1st' ? ` (${item.printing} Print)` : ''}${item.cover ? ` Cover ${item.cover}` : ''}</span>
                        ${(item.sales_data && item.sales_data.length > 0) || item.defects || item.signature_detected || item.grade_reasoning ? `<button class="item-details-btn" onclick="toggleDetails(${idx})" title="View details">📊</button>` : ''}
                    </div>
                    <div class="result-content" style="display: flex; gap: 15px; align-items: flex-start;">
                        ${item.image ? `<img src="${item.image}" alt="Comic cover" style="width: 80px; height: auto; border-radius: 4px; object-fit: cover; flex-shrink: 0;">` : ''}
                        <div class="result-details" style="flex: 1;">
                    <div class="price-tiers">
                        <div class="price-tier ${selectedTier === 'quick' ? 'selected' : ''}" onclick="selectPriceTier(${idx}, 'quick', ${quickSale.toFixed(2)})">
                            <div class="price-tier-label">Quick Sale</div>
                            <div class="price-tier-value">$${quickSale.toFixed(2)}</div>
                        </div>
                        <div class="price-tier ${selectedTier === 'fair' ? 'selected' : ''}" onclick="selectPriceTier(${idx}, 'fair', ${fairValue.toFixed(2)})">
                            <div class="price-tier-label">Fair Value</div>
                            <div class="price-tier-value">$${fairValue.toFixed(2)}</div>
                        </div>
                        <div class="price-tier ${selectedTier === 'high' ? 'selected' : ''}" onclick="selectPriceTier(${idx}, 'high', ${highEnd.toFixed(2)})">
                            <div class="price-tier-label">High End</div>
                            <div class="price-tier-value">$${highEnd.toFixed(2)}</div>
                        </div>
                    </div>
                    <div class="price-tier-hint">Click a price to select it for listing</div>
                    <button class="list-btn" onclick="listItemOnEbay(${idx})" ${ebayConnected ? '' : 'disabled'}>
                        ${ebayConnected ? '🛒 List on eBay' : '🔗 Connect eBay to List'}
                    </button>
                    ${(item.sales_data && item.sales_data.length > 0) || item.defects || item.signature_detected || item.grade_reasoning ? `
                    <div class="sales-details" id="details-${idx}">
                        ${item.sales_data && item.sales_data.length > 0 ? `
                        <h5>📊 Sales Data Used for Valuation</h5>
                        ${item.sales_data.map(sale => `
                            <div class="sale-item">
                                <div>
                                    <span class="sale-price">$${sale.price.toFixed(2)}</span>
                                    <span class="sale-meta"> · ${sale.source || 'Unknown source'}</span>
                                    ${sale.grade ? `<span class="sale-meta"> · Grade: ${sale.grade}</span>` : ''}
                                </div>
                                <div>
                                    <span class="sale-meta">${sale.date || 'Unknown date'}</span>
                                    ${sale.weight ? `<span class="sale-weight">${(sale.weight * 100).toFixed(0)}% weight</span>` : ''}
                                </div>
                            </div>
                        `).join('')}
                        ` : ''}
                        ${(item.defects && item.defects.length > 0) || item.grade_reasoning ? `
                        <div style="${item.sales_data && item.sales_data.length > 0 ? 'margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.1);' : ''}">
                            <h5 style="margin-bottom: 8px;">📋 Condition Assessment</h5>
                            ${item.grade_reasoning ? `<div style="font-size: 13px; margin-bottom: 6px; color: var(--text-secondary);">${item.grade_reasoning}</div>` : ''}
                            ${item.defects && item.defects.length > 0 ? `
                            <div style="font-size: 12px; margin-bottom: 4px;">
                                <span style="color: var(--status-error);">⚠️ Defects:</span> ${item.defects.join(', ')}
                            </div>` : ''}
                        </div>
                        ` : ''}
                        ${item.signature_detected && item.signature_analysis ? `
                        <div style="${(item.sales_data && item.sales_data.length > 0) || item.defects || item.grade_reasoning ? 'margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.1);' : ''}">
                            <h5 style="margin-bottom: 8px; color: var(--status-success);">🖊️ Signature Analysis</h5>
                            ${item.signature_analysis.most_likely_signer ? `
                            <div style="font-size: 14px; font-weight: 600; margin-bottom: 8px;">
                                Most likely: ${item.signature_analysis.most_likely_signer.name} (${item.signature_analysis.most_likely_signer.confidence}% confidence)
                            </div>` : ''}
                            ${item.signature_analysis.confidence_scores && item.signature_analysis.confidence_scores.length > 0 ? `
                            <div style="font-size: 12px; margin-bottom: 8px;">
                                <div style="color: var(--text-secondary); margin-bottom: 4px;">All creators on cover:</div>
                                ${item.signature_analysis.confidence_scores.map(c => `
                                    <div style="display: flex; justify-content: space-between; padding: 2px 0; max-width: 250px;">
                                        <span>${c.name}</span>
                                        <span style="color: ${c.confidence >= 50 ? 'var(--status-success)' : c.confidence >= 25 ? 'var(--status-warning)' : 'var(--text-muted)'}; font-weight: 500;">${c.confidence}%</span>
                                    </div>
                                `).join('')}
                            </div>` : ''}
                            ${item.signature_analysis.signature_characteristics ? `
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">
                                <em>${item.signature_analysis.signature_characteristics}</em>
                            </div>` : ''}
                            <div style="font-size: 10px; color: var(--text-muted);">
                                ⚠️ For definitive authentication, submit to CGC or CBCS
                            </div>
                        </div>
                        ` : ''}
                    </div>
                    ` : ''}
                        </div>
                    </div>
                </div>
            `}).join('');
        }
        
        function selectPriceTier(idx, tier, price) {
            extractedItems[idx].selectedTier = tier;
            extractedItems[idx].selectedPrice = price;
            showResults(); // Re-render to update selection and total
        }
        
        function toggleDetails(idx) {
            const details = document.getElementById('details-' + idx);
            if (details) {
                details.classList.toggle('show');
            }
        }
        
        function downloadExcel() {
            const data = extractedItems.map(item => ({
                Title: item.title,
                Issue: item.issue,
                Publisher: item.publisher,
                Year: item.year,
                Grade: item.grade,
                Printing: item.printing || '1st',
                Cover: item.cover || '',
                Variant: item.variant || '',
                Edition: item.edition || '',
                Value: item.value || 0,
                Confidence: item.confidence || '',
                Source: item.source || '',
                Samples: item.samples ? item.samples.join(', ') : ''
            }));
            
            const ws = XLSX.utils.json_to_sheet(data);
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, 'Collection');
            XLSX.writeFile(wb, 'CollectionCalc_Valuations.xlsx');
        }
        
        async function refreshItem(idx) {
            const item = extractedItems[idx];
            const samples = [];
            
            showThinking(`Refreshing: ${item.title} #${item.issue}`, [
                'Sample 1: Searching...',
                'Sample 2: Waiting...',
                'Sample 3: Waiting...',
                'Calculating average...',
                'Updating value...'
            ]);
            
            // Run 3 valuations
            for (let s = 0; s < 3; s++) {
                // Update step text
                document.getElementById('step' + (s + 1) + 'Text').textContent = `Sample ${s + 1}: Searching...`;
                document.getElementById('step' + (s + 1)).classList.remove('pending');
                document.getElementById('step' + (s + 1)).classList.add('active');
                
                try {
                    const result = await getValuation(item, true);  // Force refresh to bypass cache
                    samples.push(result.value);
                    
                    // Mark step done with value
                    document.getElementById('step' + (s + 1) + 'Text').textContent = `Sample ${s + 1}: $${result.value.toFixed(2)}`;
                    document.getElementById('step' + (s + 1)).classList.remove('active');
                    document.getElementById('step' + (s + 1)).classList.add('done');
                    
                } catch (error) {
                    document.getElementById('step' + (s + 1) + 'Text').textContent = `Sample ${s + 1}: Error`;
                    document.getElementById('step' + (s + 1)).classList.remove('active');
                    document.getElementById('step' + (s + 1)).classList.add('done');
                }
                
                // 60 second delay between samples (except after last)
                if (s < 2) {
                    for (let sec = 60; sec > 0; sec--) {
                        document.getElementById('step' + (s + 2) + 'Text').textContent = `Sample ${s + 2}: Waiting ${sec}s...`;
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                }
            }
            
            // Calculate average
            document.getElementById('step4').classList.remove('pending');
            document.getElementById('step4').classList.add('active');
            document.getElementById('step4Text').textContent = 'Calculating average...';
            
            if (samples.length > 0) {
                const avgValue = samples.reduce((a, b) => a + b, 0) / samples.length;
                
                document.getElementById('step4').classList.remove('active');
                document.getElementById('step4').classList.add('done');
                document.getElementById('step4Text').textContent = `Average: $${avgValue.toFixed(2)}`;
                
                // Update item
                document.getElementById('step5').classList.remove('pending');
                document.getElementById('step5').classList.add('active');
                document.getElementById('step5Text').textContent = 'Updating value...';
                
                extractedItems[idx].value = avgValue;
                extractedItems[idx].samples = samples;
                extractedItems[idx].source = 'refreshed (3 samples)';
                extractedItems[idx].confidence = 'HIGH';
                
                // Save to database cache
                try {
                    await fetch(`${API_URL}/api/cache/update`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            title: item.title,
                            issue: item.issue,
                            value: avgValue,
                            samples: samples
                        })
                    });
                } catch (e) {
                    console.error('Failed to update cache:', e);
                }
                
                await new Promise(resolve => setTimeout(resolve, 500));
                
                document.getElementById('step5').classList.remove('active');
                document.getElementById('step5').classList.add('done');
                document.getElementById('step5Text').textContent = `Updated: $${avgValue.toFixed(2)} (saved to database)`;
            }
            
            // Update displays
            setTimeout(() => {
                hideThinking();
                // Capture original order for "Order Added" sort
                originalOrder = extractedItems.map((item, idx) => ({ ...item, originalIndex: idx }));
                showResults();
            }, 1500);
        }
        
        function showThinking(title, steps) {
            document.getElementById('thinkingTitle').textContent = title;
            // Make all steps visible and reset them
            for (let i = 1; i <= 5; i++) {
                const step = document.getElementById('step' + i);
                step.style.display = 'flex';
                step.classList.remove('active', 'done');
                step.classList.add('pending');
                if (steps && steps[i-1]) {
                    document.getElementById('step' + i + 'Text').textContent = steps[i-1];
                }
            }
            document.getElementById('thinking').classList.add('show');
            animateThinking();
        }
        
        function hideThinking() {
            document.getElementById('thinking').classList.remove('show');
        }
        
        function animateThinking() {
            const delays = [0, 1500, 3000, 5000, 7000];
            delays.forEach((delay, index) => {
                setTimeout(() => {
                    if (index > 0) {
                        const prev = document.getElementById('step' + index);
                        prev.classList.remove('active');
                        prev.classList.add('done');
                    }
                    const el = document.getElementById('step' + (index + 1));
                    el.classList.remove('pending');
                    el.classList.add('active');
                }, delay);
            });
        }
        
        function showWaiting(completedTitle, value) {
            document.getElementById('thinkingTitle').textContent = '✓ ' + completedTitle;
            // Mark all steps as done
            for (let i = 1; i <= 5; i++) {
                const step = document.getElementById('step' + i);
                step.classList.remove('active', 'pending');
                step.classList.add('done');
            }
            // Update step text to show result and countdown
            document.getElementById('step1Text').textContent = value ? `Valued at $${value.toFixed(2)}` : 'Valuation complete';
            document.getElementById('step2Text').textContent = '';
            document.getElementById('step3Text').textContent = 'Waiting for rate limit...';
            document.getElementById('step4Text').textContent = '';
            document.getElementById('step5Text').textContent = '';
            // Hide steps 2, 4, 5
            document.getElementById('step2').style.display = 'none';
            document.getElementById('step4').style.display = 'none';
            document.getElementById('step5').style.display = 'none';
        }
        
        function updateWaitingCountdown(seconds, nextItem) {
            document.getElementById('step3Text').textContent = `Next: ${nextItem.title} #${nextItem.issue} in ${seconds}s`;
            document.getElementById('step3').classList.remove('done');
            document.getElementById('step3').classList.add('active');
        }
        
        function resetThinkingSteps() {
            // Make all steps visible again
            for (let i = 1; i <= 5; i++) {
                document.getElementById('step' + i).style.display = 'flex';
            }
        }
        
        // Manual form submission
        document.getElementById('valuationForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const data = {
                title: document.getElementById('title').value,
                issue: document.getElementById('issue').value,
                year: null,
                publisher: null,
                grade: document.getElementById('grade').value,
                is_signed: false,
                signer: ''
            };
            
            const btn = document.getElementById('submitBtn');
            btn.disabled = true;
            btn.textContent = 'Calculating...';
            showThinking('Calculating value...', [
                'Checking database for matches',
                'Searching market data',
                'Crunching the numbers',
                'Calculating confidence score',
                'Generating valuation'
            ]);
            
            try {
                const response = await fetch(`${API_URL}/api/valuate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const json = await response.json();
                if (json.error) throw new Error(json.error);
                
                const resultCard = document.getElementById('resultCard');
                const resultContent = document.getElementById('resultContent');
                resultCard.classList.remove('error');
                
                let confClass = 'medium';
                if (json.confidence === 'HIGH') confClass = 'high';
                else if (json.confidence === 'MEDIUM-HIGH') confClass = 'medium-high';
                else if (json.confidence === 'LOW') confClass = 'low';
                
                let sourceText = json.source || 'estimate';
                if (sourceText === 'ebay') sourceText = '📊 Market Data';
                else if (sourceText === 'database') sourceText = '📁 Database';
                
                const formatPrice = (val) => val ? val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—';
                
                const quickSale = json.quick_sale || (json.final_value * 0.7);
                const fairValue = json.fair_value || json.final_value;
                const highEnd = json.high_end || (json.final_value * 1.3);
                
                // Get tier confidences (fallback to overall confidence)
                const quickSaleConf = json.quick_sale_confidence || json.confidence_score || 50;
                const fairValueConf = json.fair_value_confidence || json.confidence_score || 50;
                const highEndConf = json.high_end_confidence || json.confidence_score || 50;
                
                // Helper to get confidence label
                const getConfLabel = (score) => {
                    if (score >= 70) return 'High';
                    if (score >= 50) return 'Medium';
                    if (score >= 30) return 'Low';
                    return 'Very Low';
                };
                
                // Build details section content
                const salesCount = json.ebay_sales || 0;
                const priceRange = json.ebay_price_range ? `$${formatPrice(json.ebay_price_range[0])} - $${formatPrice(json.ebay_price_range[1])}` : '—';
                
                resultContent.innerHTML = `
                    <p class="result-label">Value Range</p>
                    <div class="price-tiers">
                        <div class="tier quick-sale">
                            <span class="tier-label">Quick Sale</span>
                            <span class="tier-price">$${formatPrice(quickSale)}</span>
                            <span class="tier-desc">Sell fast</span>
                        </div>
                        <div class="tier fair-value">
                            <span class="tier-label">Fair Value</span>
                            <span class="tier-price">$${formatPrice(fairValue)}</span>
                            <span class="tier-desc">Market median</span>
                        </div>
                        <div class="tier high-end">
                            <span class="tier-label">High End</span>
                            <span class="tier-price">$${formatPrice(highEnd)}</span>
                            <span class="tier-desc">Premium price</span>
                        </div>
                    </div>
                    <button class="details-toggle" onclick="this.classList.toggle('active'); this.nextElementSibling.classList.toggle('show');">
                        Details
                    </button>
                    <div class="details-section">
                        <div class="stat-row">
                            <span class="stat-label">Recent Sales</span>
                            <span class="stat-value">${salesCount}</span>
                        </div>
                        <div class="stat-row">
                            <span class="stat-label">Price Range</span>
                            <span class="stat-value">${priceRange}</span>
                        </div>
                        <div class="stat-row">
                            <span class="stat-label">Data Source</span>
                            <span class="stat-value">${sourceText}</span>
                        </div>
                        <h4 style="margin-top: 15px;">Confidence</h4>
                        <div class="stat-row">
                            <span class="stat-label">Quick Sale</span>
                            <span class="stat-value">${getConfLabel(quickSaleConf)} (${quickSaleConf}%)</span>
                        </div>
                        <div class="stat-row">
                            <span class="stat-label">Fair Value</span>
                            <span class="stat-value">${getConfLabel(fairValueConf)} (${fairValueConf}%)</span>
                        </div>
                        <div class="stat-row">
                            <span class="stat-label">High End</span>
                            <span class="stat-value">${getConfLabel(highEndConf)} (${highEndConf}%)</span>
                        </div>
                        <h4 style="margin-top: 15px;">Analysis</h4>
                        <p>${json.reasoning || 'No additional details'}</p>
                    </div>
                    <div class="ebay-section" id="ebaySection"></div>
                `;
                
                // Update eBay section based on connection status
                updateEbayUI();
                
                // Store current comic info for listing
                window.currentComic = {
                    title: data.title,
                    issue: data.issue,
                    quickSale: quickSale,
                    fairValue: fairValue,
                    highEnd: highEnd
                };
                
                // If connected, show list buttons
                if (ebayConnected) {
                    const escTitle = data.title.replace(/'/g, "\\'");
                    const escIssue = data.issue.replace(/'/g, "\\'");
                    document.getElementById('listButtons').innerHTML = `
                        <button class="list-btn" onclick="listOnEbay('${escTitle}', '${escIssue}', ${quickSale}, 'Quick Sale')">
                            List at $${formatPrice(quickSale)}
                        </button>
                        <button class="list-btn" onclick="listOnEbay('${escTitle}', '${escIssue}', ${fairValue}, 'Fair Value')">
                            List at $${formatPrice(fairValue)}
                        </button>
                        <button class="list-btn" onclick="listOnEbay('${escTitle}', '${escIssue}', ${highEnd}, 'High End')">
                            List at $${formatPrice(highEnd)}
                        </button>
                    `;
                }
                
                document.getElementById('result').classList.add('show');
                
            } catch (error) {
                document.getElementById('resultCard').classList.add('error');
                document.getElementById('resultContent').innerHTML = `<p class="result-label">Error</p><div class="price">${error.message}</div>`;
                document.getElementById('result').classList.add('show');
            }
            
            hideThinking();
            btn.disabled = false;
            btn.textContent = 'Get Valuation';
        });
// ============================================
// GRADE MY COMIC MODE - JavaScript
// Add this to the END of app.js
// ============================================

// Device detection
const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

// Grading state
let gradingState = {
    currentStep: 1,
    photos: {
        1: null,  // front cover (required)
        2: null,  // spine
        3: null,  // back
        4: null   // centerfold
    },
    additionalPhotos: [],
    extractedData: null,  // from front cover
    defectsByArea: {},
    finalGrade: null,
    confidence: 0
};

// Initialize grading mode on page load
document.addEventListener('DOMContentLoaded', () => {
    initGradingMode();
});

function initGradingMode() {
    // Update text based on device
    const uploadTitles = document.querySelectorAll('.grading-upload .upload-title');
    uploadTitles.forEach(el => {
        if (!isMobile) {
            el.textContent = el.textContent.replace('Tap to photograph', 'Click to upload');
        }
    });
    
    // Add capture attribute for mobile (defaults to camera)
    if (isMobile) {
        document.querySelectorAll('#gradingMode input[type="file"]').forEach(input => {
            input.setAttribute('capture', 'environment');
        });
    }
}

// Photo Tips Modal
function togglePhotoTips() {
    const modal = document.getElementById('photoTipsModal');
    modal.classList.add('show');
}

function closePhotoTips() {
    const modal = document.getElementById('photoTipsModal');
    modal.classList.remove('show');
}

// Handle grading photo upload
async function handleGradingPhoto(step, files) {
    if (!files || files.length === 0) return;
    
    const file = files[0];
    const uploadArea = document.getElementById(`gradingUpload${step}`);
    const preview = document.getElementById(`gradingPreview${step}`);
    const previewImg = document.getElementById(`gradingImg${step}`);
    const previewInfo = document.getElementById(`gradingInfo${step}`);
    const feedback = document.getElementById(`gradingFeedback${step}`);
    const feedbackText = document.getElementById(`gradingFeedbackText${step}`);
    const nextBtn = document.getElementById(`gradingNext${step}`);
    
    // Show loading state
    uploadArea.style.display = 'none';
    feedback.style.display = 'flex';
    feedback.className = 'grading-feedback';
    feedbackText.textContent = 'Analyzing image...';
    
    try {
        // Process image
        const processed = await processImageForExtraction(file, 0);
        
        // Show preview
        previewImg.src = `data:${processed.mediaType};base64,${processed.base64}`;
        
        // Store photo
        gradingState.photos[step] = {
            base64: processed.base64,
            mediaType: processed.mediaType
        };
        
        if (step === 1) {
            // Front cover - do full extraction + quality check
            let result = await analyzeGradingPhoto(step, processed);
            
            // Check if image is upside-down and auto-correct
            if (result.is_upside_down) {
                console.log('Image detected as upside-down, auto-rotating 180°');
                feedbackText.textContent = 'Auto-correcting orientation...';
                
                // Rotate 180°
                const img = new Image();
                await new Promise((resolve, reject) => {
                    img.onload = resolve;
                    img.onerror = reject;
                    img.src = `data:${processed.mediaType};base64,${processed.base64}`;
                });
                
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.translate(canvas.width / 2, canvas.height / 2);
                ctx.rotate(Math.PI); // 180 degrees
                ctx.drawImage(img, -img.width / 2, -img.height / 2);
                
                const rotatedDataUrl = canvas.toDataURL('image/jpeg', 0.92);
                const rotatedBase64 = rotatedDataUrl.split(',')[1];
                
                // Update stored photo and preview
                processed.base64 = rotatedBase64;
                gradingState.photos[step] = {
                    base64: rotatedBase64,
                    mediaType: 'image/jpeg'
                };
                previewImg.src = rotatedDataUrl;
                
                // Re-analyze with corrected orientation
                result = await analyzeGradingPhoto(step, { base64: rotatedBase64, mediaType: 'image/jpeg' });
            }
            
            if (result.quality_issue) {
                // Quality problem - show feedback, allow retry
                feedback.className = 'grading-feedback';
                feedbackText.textContent = result.quality_message;
                feedback.style.display = 'flex';
                preview.style.display = 'block';
                nextBtn.disabled = false; // Let them continue anyway
            } else {
                feedback.style.display = 'none';
            }
            
            // Store extracted data
            gradingState.extractedData = result;
            
            // Show preview with extracted info (with edit button)
            previewInfo.innerHTML = `
                <div class="extracted-title">
                    <span id="extractedTitleText">${result.title || 'Unknown'} #${result.issue || '?'}</span>
                    <button type="button" class="btn-edit-inline" onclick="editComicInfo()">✏️ Edit</button>
                </div>
                <div id="editComicForm" style="display: none; margin: 10px 0;">
                    <input type="text" id="editTitle" placeholder="Title" value="${result.title || ''}" style="margin-bottom: 8px; width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary);">
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <input type="text" id="editIssue" placeholder="Issue #" value="${result.issue || ''}" style="width: 80px; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary);">
                        <button type="button" class="btn-secondary btn-small" onclick="saveComicEdit()">Save</button>
                        <button type="button" class="btn-secondary btn-small" onclick="cancelComicEdit()">Cancel</button>
                    </div>
                </div>
                <div class="extracted-grade">Cover condition: ${result.suggested_grade || 'Analyzing...'}</div>
                ${result.defects && result.defects.length > 0 ? 
                    `<div class="extracted-defects">⚠️ ${result.defects.join(', ')}</div>` : 
                    '<div class="extracted-defects" style="color: var(--status-success);">✓ No major defects detected</div>'}
            `;
            
            // Store defects
            gradingState.defectsByArea['Front Cover'] = result.defects || [];
            
            // Update comic ID banner for subsequent steps
            updateComicIdBanners(result);
            
        } else {
            // Steps 2-4: Just analyze for defects
            const result = await analyzeGradingPhoto(step, processed);
            
            if (result.quality_issue) {
                feedback.className = 'grading-feedback';
                feedbackText.textContent = result.quality_message;
                feedback.style.display = 'flex';
            } else {
                feedback.style.display = 'none';
            }
            
            // Show defects found
            const areaNames = { 2: 'Spine', 3: 'Back Cover', 4: 'Centerfold' };
            const areaName = areaNames[step];
            
            previewInfo.innerHTML = `
                <div class="extracted-grade">${areaName} condition: ${result.suggested_grade || 'Good'}</div>
                ${result.defects && result.defects.length > 0 ? 
                    `<div class="extracted-defects">⚠️ ${result.defects.join(', ')}</div>` : 
                    '<div class="extracted-defects" style="color: var(--status-success);">✓ No defects found</div>'}
            `;
            
            // Store defects
            gradingState.defectsByArea[areaName] = result.defects || [];
        }
        
        preview.style.display = 'block';
        nextBtn.disabled = false;
        
    } catch (error) {
        console.error('Error analyzing photo:', error);
        feedback.className = 'grading-feedback error';
        feedbackText.textContent = 'Error analyzing image. Please try again.';
        feedback.style.display = 'flex';
        uploadArea.style.display = 'block';
    }
}

// Edit comic info functions
function editComicInfo() {
    document.getElementById('extractedTitleText').style.display = 'none';
    document.querySelector('.btn-edit-inline').style.display = 'none';
    document.getElementById('editComicForm').style.display = 'block';
}

function saveComicEdit() {
    const newTitle = document.getElementById('editTitle').value;
    const newIssue = document.getElementById('editIssue').value;
    
    // Update state
    gradingState.extractedData.title = newTitle;
    gradingState.extractedData.issue = newIssue;
    
    // Update display
    document.getElementById('extractedTitleText').textContent = `${newTitle} #${newIssue}`;
    document.getElementById('extractedTitleText').style.display = 'inline';
    document.querySelector('.btn-edit-inline').style.display = 'inline';
    document.getElementById('editComicForm').style.display = 'none';
    
    // Update banners in steps 2-4
    updateComicIdBanners(gradingState.extractedData);
}

function cancelComicEdit() {
    document.getElementById('extractedTitleText').style.display = 'inline';
    document.querySelector('.btn-edit-inline').style.display = 'inline';
    document.getElementById('editComicForm').style.display = 'none';
}

// Analyze a grading photo with Claude
async function analyzeGradingPhoto(step, processed) {
    const prompts = {
        1: `Analyze this comic book FRONT COVER image. Return a JSON object with:

IMAGE ORIENTATION CHECK (do this FIRST):
- is_upside_down: boolean - Is this image upside-down? (text inverted, characters upside-down). If true, still try to extract info but flag this.

IMAGE QUALITY CHECK:
- quality_issue: boolean - Is the image too blurry, too dark, has glare, cut off edges, or at a bad angle?
- quality_message: If quality_issue is true, specific feedback like "Image is too blurry - hold phone steadier" or "Glare detected on cover - try a different angle"

IDENTIFICATION (extract from cover):
- title: Comic book title (series name). READ THE TITLE CAREFULLY - stylized/artistic fonts can be tricky. Look at ALL text on the cover.
- issue: Issue number (CRITICAL: find this, check corners near price, near barcode, in title area)
- publisher: Publisher name
- year: Publication year if visible
- variant: Variant info if applicable

CONDITION ASSESSMENT:
- suggested_grade: One of MT, NM, VF, FN, VG, G, FR, PR
- defects: Array of visible defects (e.g., "Corner wear top right", "Color-breaking crease", "Spine stress")
- grade_reasoning: Brief explanation

SIGNATURE CHECK:
- signature_detected: boolean
- signature_analysis: If detected, describe location, ink color, any identifiable characteristics

Return ONLY valid JSON, no markdown.`,

        2: `Analyze this comic book SPINE image for condition defects. Return a JSON object with:

IMAGE QUALITY CHECK:
- quality_issue: boolean - Is the spine clearly visible and in focus?
- quality_message: Feedback if quality is poor

CONDITION ASSESSMENT:
- suggested_grade: Based on spine alone (MT, NM, VF, FN, VG, G, FR, PR)
- defects: Array of spine-specific defects (e.g., "Spine roll", "Stress marks", "Color breaking tick", "Spine split 1 inch", "Bindery tear")
- grade_reasoning: Brief explanation

Return ONLY valid JSON, no markdown.`,

        3: `Analyze this comic book BACK COVER image for condition defects. Return a JSON object with:

IMAGE QUALITY CHECK:
- quality_issue: boolean - Is the back cover clearly visible and in focus?
- quality_message: Feedback if quality is poor

CONDITION ASSESSMENT:
- suggested_grade: Based on back cover alone (MT, NM, VF, FN, VG, G, FR, PR)
- defects: Array of defects (e.g., "Staining", "Crease", "Writing/stamp", "Subscription label", "Corner wear")
- grade_reasoning: Brief explanation

Return ONLY valid JSON, no markdown.`,

        4: `Analyze this comic book CENTERFOLD/STAPLES image. Return a JSON object with:

IMAGE QUALITY CHECK:
- quality_issue: boolean - Are the staples and centerfold clearly visible?
- quality_message: Feedback if quality is poor

CONDITION ASSESSMENT:
- suggested_grade: Based on interior (MT, NM, VF, FN, VG, G, FR, PR)
- defects: Array of defects (e.g., "Rusty staples", "Loose centerfold", "Detached centerfold", "Re-stapled", "Interior staining", "Brittle pages")
- grade_reasoning: Brief explanation

Return ONLY valid JSON, no markdown.`
    };
    
    const response = await fetch(`${API_URL}/api/messages`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
            model: 'claude-sonnet-4-20250514',
            max_tokens: 1024,
            messages: [{
                role: 'user',
                content: [
                    {
                        type: 'image',
                        source: {
                            type: 'base64',
                            media_type: processed.mediaType,
                            data: processed.base64
                        }
                    },
                    {
                        type: 'text',
                        text: prompts[step]
                    }
                ]
            }]
        })
    });
    
    const data = await response.json();
    
    if (data.error) {
        throw new Error(data.error.message || 'API error');
    }
    
    // Parse JSON response
    let resultText = data.content[0].text;
    // Clean up any markdown code blocks
    resultText = resultText.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
    
    try {
        return JSON.parse(resultText);
    } catch (e) {
        console.error('Failed to parse response:', resultText);
        return { 
            quality_issue: false,
            suggested_grade: 'VF',
            defects: []
        };
    }
}

// Update comic ID banners in steps 2-4
function updateComicIdBanners(extractedData) {
    const bannerHTML = `
        <img class="comic-thumb" src="data:${gradingState.photos[1].mediaType};base64,${gradingState.photos[1].base64}" alt="Cover">
        <div class="comic-info">
            <div class="comic-title">${extractedData.title || 'Unknown'} #${extractedData.issue || '?'}</div>
            <div class="comic-details">${extractedData.publisher || ''} ${extractedData.year || ''}</div>
        </div>
    `;
    
    [2, 3, 4].forEach(step => {
        const banner = document.getElementById(`gradingComicId${step}`);
        if (banner) {
            banner.innerHTML = bannerHTML;
            banner.style.display = 'flex';
        }
    });
}

// Show loading state on comic ID banners during re-analysis
function setComicIdBannersLoading() {
    const loadingHTML = `
        <div class="comic-info" style="font-style: italic; color: var(--text-muted);">
            Analyzing...
        </div>
    `;
    
    [2, 3, 4].forEach(step => {
        const banner = document.getElementById(`gradingComicId${step}`);
        if (banner) {
            banner.innerHTML = loadingHTML;
        }
    });
}

// Retake a photo
function retakeGradingPhoto(step) {
    const uploadArea = document.getElementById(`gradingUpload${step}`);
    const preview = document.getElementById(`gradingPreview${step}`);
    const feedback = document.getElementById(`gradingFeedback${step}`);
    const nextBtn = document.getElementById(`gradingNext${step}`);
    const input = document.getElementById(`gradingInput${step}`);
    
    // Reset state
    gradingState.photos[step] = null;
    
    // Reset UI
    preview.style.display = 'none';
    feedback.style.display = 'none';
    uploadArea.style.display = 'block';
    nextBtn.disabled = true;
    
    // Clear input
    input.value = '';
}

// Debounce timer for rotation analysis
let rotationDebounceTimer = null;

// Rotate photo 90 degrees clockwise and re-analyze
async function rotateGradingPhoto(step) {
    const photo = gradingState.photos[step];
    if (!photo || !photo.base64) {
        console.error('No photo to rotate');
        return;
    }
    
    const feedback = document.getElementById(`gradingFeedback${step}`);
    const feedbackText = document.getElementById(`gradingFeedbackText${step}`);
    const previewImg = document.getElementById(`gradingImg${step}`);
    const previewInfo = document.getElementById(`gradingInfo${step}`);
    const nextBtn = document.getElementById(`gradingNext${step}`);
    
    // Cancel any pending analysis
    if (rotationDebounceTimer) {
        clearTimeout(rotationDebounceTimer);
        rotationDebounceTimer = null;
    }
    
    // Immediately rotate the image visually
    try {
        const img = new Image();
        await new Promise((resolve, reject) => {
            img.onload = resolve;
            img.onerror = reject;
            img.src = `data:${photo.mediaType};base64,${photo.base64}`;
        });
        
        // Create rotated canvas
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Swap dimensions for 90° rotation
        canvas.width = img.height;
        canvas.height = img.width;
        
        // Rotate 90° clockwise
        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.rotate(90 * Math.PI / 180);
        ctx.drawImage(img, -img.width / 2, -img.height / 2);
        
        // Get new base64
        const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
        const newBase64 = dataUrl.split(',')[1];
        
        // Update stored photo immediately
        gradingState.photos[step] = {
            base64: newBase64,
            mediaType: 'image/jpeg',
            rotation: ((photo.rotation || 0) + 90) % 360
        };
        
        // Update preview immediately
        previewImg.src = dataUrl;
        
        // Show loading state
        feedback.style.display = 'flex';
        feedback.className = 'grading-feedback';
        feedbackText.textContent = 'Rotate again or wait to analyze...';
        
        // Clear the old title/info while waiting
        if (step === 1) {
            previewInfo.innerHTML = `<div style="color: var(--text-muted); font-style: italic;">Analyzing...</div>`;
            setComicIdBannersLoading();
        }
        
        // Debounce: wait 2.5 seconds before analyzing (in case user rotates again)
        rotationDebounceTimer = setTimeout(async () => {
            feedbackText.textContent = 'Analyzing...';
            await performRotationAnalysis(step, newBase64, feedback, feedbackText, previewInfo, nextBtn);
        }, 2500);
        
    } catch (error) {
        console.error('Error rotating photo:', error);
        feedbackText.textContent = 'Error rotating image. Please try retaking the photo.';
    }
}

// Perform the actual analysis after debounce
async function performRotationAnalysis(step, base64, feedback, feedbackText, previewInfo, nextBtn) {
    try {
        if (step === 1) {
            const result = await analyzeGradingPhoto(step, { base64, mediaType: 'image/jpeg' });
            
            // Update extracted data
            gradingState.extractedData = result;
            
            // Update comic ID banners on all subsequent steps
            updateComicIdBanners(gradingState.extractedData);
            
            // Update title display
            previewInfo.innerHTML = `
                <div class="extracted-title">
                    <span id="extractedTitleText">${result.title || 'Unknown'} #${result.issue || '?'}</span>
                    <button type="button" class="btn-edit-inline" onclick="editComicInfo()">✏️ Edit</button>
                </div>
                <div id="editComicForm" style="display: none; margin: 10px 0;">
                    <input type="text" id="editTitle" placeholder="Title" value="${result.title || ''}" style="margin-bottom: 8px; width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary);">
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <span>#</span>
                        <input type="text" id="editIssue" placeholder="Issue" value="${result.issue || ''}" style="width: 80px; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-primary); color: var(--text-primary);">
                        <button type="button" class="btn-primary btn-small" onclick="saveComicInfo()">Save</button>
                        <button type="button" class="btn-secondary btn-small" onclick="cancelComicEdit()">Cancel</button>
                    </div>
                </div>
                <div style="font-size: 0.9rem; color: var(--text-muted); margin-top: 4px;">
                    Cover condition: ${result.suggested_grade || 'Analyzing...'}
                </div>
                ${result.defects && result.defects.length > 0 ? `
                    <div style="font-size: 0.85rem; color: var(--brand-amber); margin-top: 4px;">
                        ⚠️ ${result.defects.join(', ')}
                    </div>
                ` : ''}
            `;
            
            // Store defects
            gradingState.defectsByArea['Front Cover'] = result.defects || [];
            
            if (result.quality_issue) {
                feedbackText.textContent = result.quality_message;
            } else {
                feedback.style.display = 'none';
            }
        } else {
            // For other steps, re-analyze for defects
            const result = await analyzeGradingPhoto(step, { base64, mediaType: 'image/jpeg' });
            const areaName = {2: 'Spine', 3: 'Back Cover', 4: 'Centerfold/Interior'}[step];
            gradingState.defectsByArea[areaName] = result.defects || [];
            
            // Update info display
            previewInfo.innerHTML = result.defects && result.defects.length > 0 
                ? `<div style="font-size: 0.85rem; color: var(--brand-amber);">⚠️ ${result.defects.join(', ')}</div>`
                : `<div style="font-size: 0.85rem; color: var(--brand-green);">✓ No defects detected</div>`;
            
            feedback.style.display = 'none';
        }
        
        nextBtn.disabled = false;
        
    } catch (error) {
        console.error('Error analyzing rotated photo:', error);
        feedbackText.textContent = 'Error analyzing image. Please try again.';
    }
}

// Navigate to next step
function nextGradingStep(currentStep) {
    // Mark current step as completed
    const currentStepEl = document.getElementById(`gradingStep${currentStep}`);
    currentStepEl.classList.remove('active');
    currentStepEl.classList.add('completed');
    
    // Hide current content
    document.getElementById(`gradingContent${currentStep}`).classList.remove('active');
    
    // Show next step
    const nextStep = currentStep + 1;
    const nextStepEl = document.getElementById(`gradingStep${nextStep}`);
    nextStepEl.classList.add('active');
    document.getElementById(`gradingContent${nextStep}`).classList.add('active');
    
    gradingState.currentStep = nextStep;
}

// Skip a step
function skipGradingStep(step) {
    // Mark as skipped
    const stepEl = document.getElementById(`gradingStep${step}`);
    stepEl.classList.remove('active');
    stepEl.classList.add('skipped');
    
    // Hide current content
    document.getElementById(`gradingContent${step}`).classList.remove('active');
    
    // Determine next step
    let nextStep;
    if (step === 4) {
        // Go to report
        nextStep = 5;
        generateGradeReport();
    } else {
        nextStep = step + 1;
    }
    
    // Show next step
    const nextStepEl = document.getElementById(`gradingStep${nextStep}`);
    nextStepEl.classList.add('active');
    document.getElementById(`gradingContent${nextStep}`).classList.add('active');
    
    gradingState.currentStep = nextStep;
}

// Handle additional photos
async function handleAdditionalPhoto(files) {
    if (!files || files.length === 0) return;
    
    const file = files[0];
    
    try {
        // Process image with EXIF rotation (same as other photos)
        const processed = await processImageForExtraction(file, 0);
        
        gradingState.additionalPhotos.push({
            base64: processed.base64,
            mediaType: processed.mediaType
        });
        
        // Update thumbnail display
        renderAdditionalPhotos();
    } catch (error) {
        console.error('Error processing additional photo:', error);
        // Fallback to direct read if processing fails
        const reader = new FileReader();
        reader.onload = (e) => {
            const base64 = e.target.result.split(',')[1];
            gradingState.additionalPhotos.push({
                base64: base64,
                mediaType: file.type
            });
            renderAdditionalPhotos();
        };
        reader.readAsDataURL(file);
    }
    
    // Clear input
    document.getElementById('additionalPhotoInput').value = '';
}

function renderAdditionalPhotos() {
    const container = document.getElementById('additionalPhotos');
    container.innerHTML = gradingState.additionalPhotos.map((photo, idx) => `
        <div style="position: relative; display: inline-block;">
            <img class="additional-photo-thumb" src="data:${photo.mediaType};base64,${photo.base64}" alt="Additional ${idx + 1}">
            <button class="additional-photo-remove" onclick="removeAdditionalPhoto(${idx})">×</button>
        </div>
    `).join('');
}

function removeAdditionalPhoto(idx) {
    gradingState.additionalPhotos.splice(idx, 1);
    renderAdditionalPhotos();
}

// Generate the final grade report
async function generateGradeReport() {
    // Show report section
    document.getElementById(`gradingContent4`).classList.remove('active');
    document.getElementById(`gradingStep4`).classList.remove('active');
    document.getElementById(`gradingStep4`).classList.add('completed');
    document.getElementById(`gradingStep5`).classList.add('active');
    document.getElementById(`gradingContent5`).classList.add('active');
    
    gradingState.currentStep = 5;
    
    // Show loading state with progress steps (with null checks)
    const gradeResultBig = document.getElementById('gradeResultBig');
    const gradeResultLabel = document.getElementById('gradeResultLabel');
    const gradePhotosUsed = document.getElementById('gradePhotosUsed');
    const defectsList = document.getElementById('defectsList');
    const recommendationValues = document.getElementById('recommendationValues');
    const recommendationVerdict = document.getElementById('recommendationVerdict');
    
    if (gradeResultBig) gradeResultBig.textContent = '...';
    if (gradeResultLabel) gradeResultLabel.textContent = 'Analyzing photos...';
    if (gradePhotosUsed) gradePhotosUsed.innerHTML = '<span style="color: var(--text-muted);">Processing images...</span>';
    if (defectsList) defectsList.innerHTML = '<span style="color: var(--text-muted);">Finding defects...</span>';
    if (recommendationValues) recommendationValues.innerHTML = '';
    if (recommendationVerdict) recommendationVerdict.innerHTML = '<p style="text-align: center; color: var(--text-muted);">Calculating value...</p>';
    
    // Build multi-image prompt
    const imageContent = [];
    const photoLabels = [];
    
    // Add all captured photos
    Object.entries(gradingState.photos).forEach(([step, photo]) => {
        if (photo) {
            const labels = { 1: 'Front Cover', 2: 'Spine', 3: 'Back Cover', 4: 'Centerfold' };
            imageContent.push({
                type: 'image',
                source: {
                    type: 'base64',
                    media_type: photo.mediaType,
                    data: photo.base64
                }
            });
            photoLabels.push(labels[step]);
        }
    });
    
    // Add additional photos
    gradingState.additionalPhotos.forEach((photo, idx) => {
        imageContent.push({
            type: 'image',
            source: {
                type: 'base64',
                media_type: photo.mediaType,
                data: photo.base64
            }
        });
        photoLabels.push(`Additional ${idx + 1}`);
    });
    
    // Calculate photos used for confidence
    const photosUsed = Object.values(gradingState.photos).filter(p => p !== null).length;
    const baseConfidence = { 1: 65, 2: 78, 3: 88, 4: 94 }[photosUsed] || 65;
    const additionalBoost = Math.min(gradingState.additionalPhotos.length * 2, 4);
    const confidence = Math.min(baseConfidence + additionalBoost, 98);
    
    try {
        // Send all images for comprehensive grading
        const response = await fetch(`${API_URL}/api/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                model: 'claude-sonnet-4-20250514',
                max_tokens: 2048,
                messages: [{
                    role: 'user',
                    content: [
                        ...imageContent,
                        {
                            type: 'text',
                            text: `You are grading this comic book using ${photoLabels.length} photos: ${photoLabels.join(', ')}.

The comic has been identified as: ${gradingState.extractedData?.title || 'Unknown'} #${gradingState.extractedData?.issue || '?'}

Based on ALL images provided, give a comprehensive grade assessment.

Return a JSON object with these EXACT top-level keys:

{
  "title": "Series name",
  "issue": "Issue number",
  "publisher": "Publisher",
  "year": "Year if visible",
  "final_grade": 9.4,
  "grade_label": "NM",
  "grade_reasoning": "Detailed explanation",
  "front_defects": ["array", "of", "defects"],
  "spine_defects": ["array", "of", "defects"],
  "back_defects": ["array", "of", "defects"],
  "interior_defects": ["array", "of", "defects"],
  "other_defects": ["array", "of", "defects"],
  "signature_detected": false,
  "signature_info": null
}

Use numeric grades like 9.8, 9.4, 9.0, 8.5, 8.0, 7.5, 7.0, 6.5, 6.0, 5.5, 5.0, 4.5, 4.0, 3.0, 2.0, 1.0.
Grade labels: MT, NM+, NM, NM-, VF+, VF, VF-, FN+, FN, FN-, VG+, VG, VG-, G, FR, PR.

Return ONLY valid JSON, no markdown, no nested objects.`
                        }
                    ]
                }]
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error.message || 'API error');
        }
        
        let resultText = data.content[0].text;
        resultText = resultText.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
        
        const result = JSON.parse(resultText);
        gradingState.finalGrade = result;
        gradingState.confidence = confidence;
        
        // Update UI
        renderGradeReport(result, confidence, photoLabels);
        
        // Get valuation for "should you grade?" calculation
        await calculateGradingRecommendation(result);
        
    } catch (error) {
        console.error('Error generating grade report:', error);
        const bigEl = document.getElementById('gradeResultBig');
        const labelEl = document.getElementById('gradeResultLabel');
        if (bigEl) bigEl.textContent = 'Error';
        if (labelEl) labelEl.textContent = 'Failed to analyze. Please try again.';
    }
}

// Render the grade report
function renderGradeReport(result, confidence, photoLabels) {
    // Handle both flat and nested response structures from Claude
    const comic = result['COMIC IDENTIFICATION'] || result;
    const grade = result['COMPREHENSIVE GRADE'] || result;
    const defects = result['DEFECTS BY AREA'] || result;
    const sig = result['SIGNATURE'] || result;
    
    // Comic info - prefer user-edited data
    const displayTitle = gradingState.extractedData?.title || comic.title || 'Unknown';
    const displayIssue = gradingState.extractedData?.issue || comic.issue || '?';
    
    // Helper function for safe element access
    const safeSet = (id, prop, value) => {
        const el = document.getElementById(id);
        if (!el) {
            console.error(`Element not found: ${id}`);
            return false;
        }
        if (prop === 'innerHTML') el.innerHTML = value;
        else if (prop === 'textContent') el.textContent = value;
        else if (prop === 'style.display') el.style.display = value;
        return true;
    };
    
    safeSet('gradeReportComic', 'innerHTML', `
        <div class="comic-title-big">${displayTitle} #${displayIssue}</div>
        <div class="comic-meta">${comic.publisher || ''} ${comic.year || ''}</div>
    `);
    
    // Grade result
    safeSet('gradeResultBig', 'textContent', grade.final_grade || '--');
    safeSet('gradeResultLabel', 'textContent', grade.grade_label || 'Grade');
    
    // Show quality warning only if confidence < 75%
    const warningEl = document.getElementById('gradeQualityWarning');
    if (warningEl) {
        if (confidence < 75) {
            warningEl.style.display = 'flex';
        } else {
            warningEl.style.display = 'none';
        }
    }
    
    // Photos used badges
    const allLabels = ['Front', 'Spine', 'Back', 'Center'];
    safeSet('gradePhotosUsed', 'innerHTML', allLabels.map((label, idx) => {
        const used = gradingState.photos[idx + 1] !== null;
        return `<span class="photo-badge ${used ? 'used' : 'skipped'}">${label}${used ? ' ✓' : ''}</span>`;
    }).join(''));
    
    // Defects - handle both flat and nested structures
    const frontDefects = defects.front_defects || [];
    const spineDefects = defects.spine_defects || [];
    const backDefects = defects.back_defects || [];
    const interiorDefects = defects.interior_defects || [];
    
    const defectsHTML = [];
    
    if (frontDefects.length > 0) {
        defectsHTML.push(`
            <div class="defect-area">
                <span class="defect-area-label">Front</span>
                <div class="defect-area-items">${frontDefects.map(d => `<span class="defect-item">${d}</span>`).join('')}</div>
            </div>
        `);
    }
    if (spineDefects.length > 0) {
        defectsHTML.push(`
            <div class="defect-area">
                <span class="defect-area-label">Spine</span>
                <div class="defect-area-items">${spineDefects.map(d => `<span class="defect-item">${d}</span>`).join('')}</div>
            </div>
        `);
    }
    if (backDefects.length > 0) {
        defectsHTML.push(`
            <div class="defect-area">
                <span class="defect-area-label">Back</span>
                <div class="defect-area-items">${backDefects.map(d => `<span class="defect-item">${d}</span>`).join('')}</div>
            </div>
        `);
    }
    if (interiorDefects.length > 0) {
        defectsHTML.push(`
            <div class="defect-area">
                <span class="defect-area-label">Interior</span>
                <div class="defect-area-items">${interiorDefects.map(d => `<span class="defect-item">${d}</span>`).join('')}</div>
            </div>
        `);
    }
    
    safeSet('defectsList', 'innerHTML', defectsHTML.length > 0 
        ? defectsHTML.join('') 
        : '<div class="no-defects">✓ No significant defects detected</div>');
    
    // Signature
    const sigDetected = sig.signature_detected || false;
    if (sigDetected) {
        safeSet('gradeReportSignature', 'style.display', 'block');
        const sigInfo = sig.signature_info || {};
        safeSet('signatureInfo', 'innerHTML', `
            <p>${sigInfo.likely_signer || 'Unknown signer'}</p>
            <p style="font-size: 0.9rem; color: var(--text-secondary);">
                ${sigInfo.ink_color || ''} ink, ${sigInfo.location || 'on cover'}
            </p>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 8px;">
                ⚠️ For authenticated value, submit to CGC Signature Series or CBCS Verified
            </p>
        `);
    } else {
        safeSet('gradeReportSignature', 'style.display', 'none');
    }
}

// Calculate "should you grade?" recommendation
async function calculateGradingRecommendation(gradeResult) {
    // Handle nested structure
    const comic = gradeResult['COMIC IDENTIFICATION'] || gradeResult;
    const grade = gradeResult['COMPREHENSIVE GRADE'] || gradeResult;
    
    // Prefer user-edited data
    const title = gradingState.extractedData?.title || comic.title;
    const issue = gradingState.extractedData?.issue || comic.issue;
    
    // Convert letter grade to numeric for valuation lookup
    const gradeMap = {
        'MT': 'NM', '10.0': 'NM', '9.8': 'NM', '9.6': 'NM', '9.4': 'NM',
        'NM': 'NM', 'NM+': 'NM', 'NM-': 'NM',
        'VF': 'VF', 'VF+': 'VF', 'VF-': 'VF', '8.5': 'VF', '8.0': 'VF',
        'FN': 'FN', 'FN+': 'FN', 'FN-': 'FN', '6.5': 'FN', '6.0': 'FN',
        'VG': 'VG', 'VG+': 'VG', 'VG-': 'VG', '4.5': 'VG', '4.0': 'VG',
        'G': 'G', 'GD': 'G', '2.5': 'G', '2.0': 'G',
        'FR': 'FR', '1.5': 'FR',
        'PR': 'PR', '1.0': 'PR', '0.5': 'PR'
    };
    
    const gradeLabel = grade.grade_label || gradeResult.grade_label;
    const finalGrade = grade.final_grade || gradeResult.final_grade;
    const lookupGrade = gradeMap[gradeLabel] || gradeMap[String(finalGrade)] || 'VF';
    
    try {
        // Get valuation
        const response = await fetch(`${API_URL}/api/valuate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                title: title,
                issue: issue,
                grade: lookupGrade
            })
        });
        
        const valuation = await response.json();
        
        if (valuation.error) {
            throw new Error(valuation.error);
        }
        
        // Calculate recommendation
        const rawValue = valuation.fair_value || valuation.final_value || 0;
        const slabPremium = 1.3; // Slabbed comics typically sell for 30% more
        const gradingCost = getGradingCost(rawValue);
        
        const slabbedValue = rawValue * slabPremium;
        const valueIncrease = slabbedValue - rawValue;
        const netBenefit = valueIncrease - gradingCost;
        const roi = gradingCost > 0 ? ((netBenefit / gradingCost) * 100).toFixed(0) : 0;
        
        // Render recommendation with CLEARER math
        const isWorthIt = netBenefit > 0;
        
        document.getElementById('recommendationValues').innerHTML = `
            <div class="recommendation-math">
                <div class="math-row">
                    <span class="math-label">Raw value (Fair Market):</span>
                    <span class="math-value">$${rawValue.toFixed(2)}</span>
                </div>
                <div class="math-row">
                    <span class="math-label">+ Slab premium (~30%):</span>
                    <span class="math-value positive">+$${valueIncrease.toFixed(2)}</span>
                </div>
                <div class="math-row">
                    <span class="math-label">= Slabbed value:</span>
                    <span class="math-value">$${slabbedValue.toFixed(2)}</span>
                </div>
                <div class="math-divider"></div>
                <div class="math-row">
                    <span class="math-label">− Grading cost (CGC):</span>
                    <span class="math-value negative">−$${gradingCost.toFixed(2)}</span>
                </div>
                <div class="math-divider"></div>
                <div class="math-row math-total ${isWorthIt ? 'positive' : 'negative'}">
                    <span class="math-label">Net ${isWorthIt ? 'profit' : 'loss'} from grading:</span>
                    <span class="math-value">${isWorthIt ? '+' : ''}$${netBenefit.toFixed(2)}</span>
                </div>
            </div>
        `;
        
        // Verdict
        let verdictHTML;
        if (netBenefit > gradingCost * 0.5) {
            // Good ROI
            verdictHTML = `
                <div class="recommendation-verdict submit">
                    <div class="verdict-icon">✅</div>
                    <div class="verdict-text">SUBMIT FOR GRADING</div>
                    <div class="verdict-reason">You'll make ~$${netBenefit.toFixed(2)} profit after grading costs</div>
                </div>
            `;
        } else if (netBenefit > 0) {
            // Marginal
            verdictHTML = `
                <div class="recommendation-verdict" style="background: rgba(99, 102, 241, 0.1); border-color: var(--brand-indigo);">
                    <div class="verdict-icon">🤔</div>
                    <div class="verdict-text" style="color: var(--brand-indigo);">CONSIDER GRADING</div>
                    <div class="verdict-reason">Small profit of $${netBenefit.toFixed(2)} - worth it if you want the slab for your collection</div>
                </div>
            `;
        } else {
            // Not worth it
            verdictHTML = `
                <div class="recommendation-verdict keep-raw">
                    <div class="verdict-icon">📦</div>
                    <div class="verdict-text">KEEP RAW</div>
                    <div class="verdict-reason">You'd lose $${Math.abs(netBenefit).toFixed(2)} - grading costs more than the value increase</div>
                </div>
            `;
        }
        
        document.getElementById('recommendationVerdict').innerHTML = verdictHTML;
        
    } catch (error) {
        console.error('Error calculating recommendation:', error);
        document.getElementById('recommendationValues').innerHTML = `
            <p style="color: var(--text-muted); text-align: center;">Could not retrieve market values</p>
        `;
        document.getElementById('recommendationVerdict').innerHTML = '';
    }
}

// Estimate grading cost based on value
function getGradingCost(value) {
    if (value >= 1000) return 150; // Walkthrough tier
    if (value >= 400) return 85;   // Express tier
    if (value >= 200) return 50;   // Economy tier
    return 30; // Modern tier (minimum)
}

// Reset grading mode
function resetGrading() {
    // Reset state
    gradingState = {
        currentStep: 1,
        photos: { 1: null, 2: null, 3: null, 4: null },
        additionalPhotos: [],
        extractedData: null,
        defectsByArea: {},
        finalGrade: null,
        confidence: 0
    };
    
    // Reset all step indicators
    for (let i = 1; i <= 5; i++) {
        const stepEl = document.getElementById(`gradingStep${i}`);
        stepEl.classList.remove('active', 'completed', 'skipped');
        if (i === 1) stepEl.classList.add('active');
        
        const contentEl = document.getElementById(`gradingContent${i}`);
        contentEl.classList.remove('active');
        if (i === 1) contentEl.classList.add('active');
    }
    
    // Reset all inputs and previews
    for (let i = 1; i <= 4; i++) {
        document.getElementById(`gradingUpload${i}`).style.display = 'block';
        document.getElementById(`gradingPreview${i}`).style.display = 'none';
        document.getElementById(`gradingFeedback${i}`).style.display = 'none';
        document.getElementById(`gradingInput${i}`).value = '';
        if (i > 1) {
            document.getElementById(`gradingNext${i}`).disabled = true;
        }
    }
    document.getElementById('gradingNext1').disabled = true;
    
    // Clear additional photos
    document.getElementById('additionalPhotos').innerHTML = '';
    
    // Clear comic ID banners
    [2, 3, 4].forEach(step => {
        const banner = document.getElementById(`gradingComicId${step}`);
        if (banner) banner.innerHTML = '';
    });
    
    // Hide quality warning
    const warningEl = document.getElementById('gradeQualityWarning');
    if (warningEl) warningEl.style.display = 'none';
}

// Save graded comic to collection
function saveGradeToCollection() {
    if (!gradingState.finalGrade || !gradingState.extractedData) {
        alert('No grade data to save');
        return;
    }
    
    // Handle nested structure
    const grade = gradingState.finalGrade['COMPREHENSIVE GRADE'] || gradingState.finalGrade;
    
    // Use existing saveToCollection logic
    const comicData = {
        title: gradingState.extractedData.title,
        issue: gradingState.extractedData.issue,
        grade: grade.grade_label || grade.final_grade,
        notes: `Graded via 4-photo analysis. ${grade.grade_reasoning || ''}`
    };
    
    // This would call your existing collection save API
    alert('Save to collection coming soon!');
}
