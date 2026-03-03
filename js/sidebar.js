// ============================================
// SIDEBAR.JS - Shared sidebar navigation for authenticated pages
// Include via <script src="/js/sidebar.js"></script> before </body>
//
// Usage: Add data-sidebar-page="pageName" to <body> to highlight active nav item.
// Valid page names: dashboard, grade, collection, ebay, whatnot, slab-guard,
//                   signature-id, market-pulse, price-lookup, faq, account, admin, signatures
//
// The script will:
// 1. Inject all sidebar CSS
// 2. Create the sidebar + mobile topbar
// 3. Wrap existing body content in the app-shell grid
// 4. Handle collapse/expand, mobile drawer, tooltips, logout
// ============================================
"use strict";
(function() {
    // Don't inject if page opted out
    if (document.querySelector('[data-no-sidebar]')) return;

    // Don't inject if not logged in
    const token = localStorage.getItem('cc_token');
    if (!token) return;

    // Detect active page from body attribute or URL
    const activePage = document.body.getAttribute('data-sidebar-page') || detectPage();
    function detectPage() {
        const path = window.location.pathname.toLowerCase();
        if (path.includes('dashboard')) return 'dashboard';
        if (path.includes('app.html')) return 'grade';
        if (path.includes('collection')) return 'collection';
        if (path.includes('account')) return 'account';
        if (path.includes('admin.html')) return 'admin';
        if (path.includes('signatures')) return 'signatures';
        if (path.includes('verify')) return 'slab-guard';
        if (path.includes('faq')) return 'faq';
        return '';
    }

    // Get user info
    let displayName = 'User';
    let initials = 'U';
    try {
        const userData = JSON.parse(localStorage.getItem('cc_user') || '{}');
        const email = userData.email || '';
        const namePart = email.split('@')[0] || 'User';
        displayName = namePart.charAt(0).toUpperCase() + namePart.slice(1);
        initials = displayName.charAt(0).toUpperCase();
    } catch (e) {}

    // Check if admin
    let isAdmin = false;
    try {
        const userData = JSON.parse(localStorage.getItem('cc_user') || '{}');
        isAdmin = userData.is_admin === true;
    } catch (e) {}

    // ==========================================
    // INJECT CSS
    // ==========================================
    const style = document.createElement('style');
    style.id = 'sidebar-styles';
    style.textContent = `
        /* Override any page-level body flex/grid/padding to prevent conflicts */
        body { display: block !important; padding: 0 !important; }

        /* Sidebar App Shell */
        .sw-app-shell {
            display: grid;
            grid-template-columns: var(--sidebar-width, 240px) 1fr;
            min-height: 100vh;
            transition: grid-template-columns 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .sw-app-shell.collapsed {
            grid-template-columns: var(--sidebar-collapsed, 64px) 1fr;
        }

        /* Sidebar */
        .sw-sidebar {
            background: var(--bg-sidebar, #0e0e1a);
            border-right: 1px solid var(--border, rgba(124, 58, 237, 0.15));
            padding: 1.25rem 0;
            display: flex;
            flex-direction: column;
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
            overflow-x: hidden;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 100;
            scrollbar-width: thin;
            scrollbar-color: rgba(124, 58, 237, 0.3) transparent;
        }
        .sw-sidebar::-webkit-scrollbar { width: 4px; }
        .sw-sidebar::-webkit-scrollbar-track { background: transparent; }
        .sw-sidebar::-webkit-scrollbar-thumb {
            background: rgba(124, 58, 237, 0.3);
            border-radius: 4px;
        }
        .sw-sidebar::-webkit-scrollbar-thumb:hover {
            background: rgba(124, 58, 237, 0.5);
        }
        .sw-sidebar-toggle-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 1rem 0 1.25rem;
            margin-bottom: 1.5rem;
            min-height: 36px;
        }
        .sw-sidebar-logo {
            font-family: 'Bangers', cursive;
            font-size: 1.5rem;
            background: linear-gradient(135deg, var(--gold-light, #fef08a), var(--gold-dark, #ca8a04));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 1px;
            white-space: nowrap;
            transition: opacity 0.2s, transform 0.2s;
            text-decoration: none;
        }
        .collapsed .sw-sidebar-logo {
            opacity: 0; transform: translateX(-10px);
            position: absolute; pointer-events: none;
        }
        .sw-sidebar-logo-icon {
            font-family: 'Bangers', cursive;
            font-size: 1.3rem;
            background: linear-gradient(135deg, var(--gold-light, #fef08a), var(--gold-dark, #ca8a04));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 1px;
            display: none;
            width: 100%;
            text-align: center;
        }
        .collapsed .sw-sidebar-logo-icon { display: block; }
        .sw-toggle-btn {
            width: 30px; height: 30px;
            border-radius: 8px;
            border: 1px solid var(--border, rgba(124, 58, 237, 0.15));
            background: rgba(124, 58, 237, 0.06);
            color: var(--text-secondary, #94a3b8);
            cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            font-size: 0.85rem;
            transition: all 0.15s;
            flex-shrink: 0;
        }
        .sw-toggle-btn:hover {
            background: rgba(124, 58, 237, 0.15);
            color: var(--text-primary, #ffffff);
        }
        .collapsed .sw-toggle-btn { margin: 0 auto; }

        /* Sidebar Sections */
        .sw-sidebar-section { margin-bottom: 1.25rem; }
        .sw-sidebar-label {
            font-size: 0.6rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-secondary, #94a3b8);
            padding: 0 1.25rem;
            margin-bottom: 0.4rem;
            white-space: nowrap;
            overflow: hidden;
            transition: opacity 0.2s;
        }
        .collapsed .sw-sidebar-label { opacity: 0; height: 0; margin: 0; padding: 0; }
        .sw-sidebar-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.6rem 1.25rem;
            cursor: pointer;
            transition: all 0.15s;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-secondary, #94a3b8);
            border-left: 3px solid transparent;
            white-space: nowrap;
            position: relative;
            text-decoration: none;
        }
        .sw-sidebar-item:hover {
            background: rgba(124, 58, 237, 0.06);
            color: var(--text-primary, #ffffff);
        }
        .sw-sidebar-item.active {
            background: rgba(124, 58, 237, 0.08);
            color: var(--text-primary, #ffffff);
            border-left-color: var(--purple-brand, #7c3aed);
        }
        .sw-sidebar-item .sw-icon {
            width: 20px; text-align: center; font-size: 1rem; flex-shrink: 0;
        }
        .sw-sidebar-item .sw-label {
            overflow: hidden;
            transition: opacity 0.2s, width 0.3s;
        }
        .collapsed .sw-sidebar-item .sw-label { opacity: 0; width: 0; }
        .sw-sidebar-item .sw-badge {
            margin-left: auto;
            font-size: 0.65rem;
            background: rgba(124, 58, 237, 0.2);
            color: var(--purple-light, #a855f7);
            padding: 1px 7px;
            border-radius: 99px;
            font-weight: 600;
            transition: opacity 0.2s;
        }
        .collapsed .sw-sidebar-item .sw-badge {
            opacity: 0; position: absolute; pointer-events: none;
        }
        .collapsed .sw-sidebar-item {
            justify-content: center;
            padding: 0.6rem 0;
            border-left-width: 0;
        }
        .collapsed .sw-sidebar-item.active {
            border-left-width: 0;
            background: rgba(124, 58, 237, 0.12);
        }
        /* Tooltip on collapsed hover */
        .collapsed .sw-sidebar-item:hover::after {
            content: attr(data-tooltip);
            position: absolute;
            left: calc(var(--sidebar-collapsed, 64px) - 4px);
            top: 50%;
            transform: translateY(-50%);
            background: var(--bg-card, #12121f);
            border: 1px solid var(--border, rgba(124, 58, 237, 0.15));
            color: var(--text-primary, #ffffff);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.75rem;
            white-space: nowrap;
            z-index: 200;
            pointer-events: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }

        .sw-sidebar-spacer { flex: 1; }
        .sw-sidebar-user {
            display: flex; align-items: center; gap: 0.75rem;
            padding: 1rem 1.25rem;
            border-top: 1px solid var(--border, rgba(124, 58, 237, 0.15));
            margin-top: auto;
            overflow: hidden;
        }
        .sw-sidebar-user-avatar {
            width: 34px; height: 34px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--purple-brand, #7c3aed), var(--purple-light, #a855f7));
            display: flex; align-items: center; justify-content: center;
            font-size: 0.75rem; font-weight: 700; flex-shrink: 0;
            color: white;
        }
        .sw-sidebar-user-info {
            flex: 1; min-width: 0;
            transition: opacity 0.2s;
        }
        .collapsed .sw-sidebar-user-info { opacity: 0; width: 0; overflow: hidden; }
        .collapsed .sw-sidebar-user { justify-content: center; padding: 1rem 0; }
        .sw-sidebar-user-name {
            font-size: 0.8rem; font-weight: 600;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            color: var(--text-primary, #ffffff);
        }
        .sw-sidebar-logout {
            color: var(--text-secondary, #94a3b8);
            text-decoration: none;
            font-size: 0.65rem;
            cursor: pointer;
            background: none; border: none; padding: 0;
            font-family: inherit;
        }
        .sw-sidebar-logout:hover { color: var(--text-primary, #ffffff); }

        /* Main content wrapper */
        .sw-page-content {
            overflow-y: auto;
            min-height: 100vh;
        }

        /* Mobile overlay */
        .sw-mobile-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.6);
            z-index: 999;
        }
        .sw-mobile-overlay.visible { display: block; }
        .sw-mobile-topbar {
            display: none;
            align-items: center;
            justify-content: space-between;
            padding: 0.75rem 1.25rem;
            background: var(--bg-sidebar, #0e0e1a);
            border-bottom: 1px solid var(--border, rgba(124, 58, 237, 0.15));
        }
        .sw-mobile-topbar .sw-mobile-logo {
            font-family: 'Bangers', cursive;
            font-size: 1.4rem;
            background: linear-gradient(135deg, var(--gold-light, #fef08a), var(--gold-dark, #ca8a04));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .sw-hamburger {
            width: 36px; height: 36px;
            border-radius: 8px;
            border: 1px solid var(--border, rgba(124, 58, 237, 0.15));
            background: transparent;
            color: var(--text-secondary, #94a3b8);
            cursor: pointer;
            font-size: 1.1rem;
            display: flex; align-items: center; justify-content: center;
        }

        @media (max-width: 900px) {
            .sw-app-shell { grid-template-columns: 1fr !important; }
            .sw-sidebar {
                position: fixed; left: 0; top: 0;
                width: 240px;
                transform: translateX(-100%);
                z-index: 1000;
                transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .sw-sidebar.mobile-open { transform: translateX(0); }
            .sw-mobile-topbar { display: flex !important; }
        }
        @media (min-width: 901px) {
            .sw-mobile-overlay { display: none !important; }
            .sw-mobile-topbar { display: none !important; }
        }

        /* Hide the old page headers on sidebar pages */
        .sw-page-content > .container > header:first-child,
        .sw-page-content > header:first-child {
            /* Don't hide — pages may still need their headers for now */
        }
    `;
    document.head.appendChild(style);

    // ==========================================
    // BUILD SIDEBAR HTML
    // ==========================================
    function isActive(page) { return activePage === page ? 'active' : ''; }
    function comingSoon(name) { return "javascript:void(0)"; }

    const adminItems = isAdmin ? `
        <div class="sw-sidebar-section">
            <div class="sw-sidebar-label">Admin</div>
            <a href="/admin.html" class="sw-sidebar-item ${isActive('admin')}" data-tooltip="Admin Panel">
                <span class="sw-icon">&#128736;</span> <span class="sw-label">Admin Panel</span>
            </a>
            <a href="/signatures.html" class="sw-sidebar-item ${isActive('signatures')}" data-tooltip="Signatures DB">
                <span class="sw-icon">&#128221;</span> <span class="sw-label">Signatures DB</span>
            </a>
        </div>
    ` : '';

    const sidebarHTML = `
        <div class="sw-sidebar-toggle-row">
            <a href="/dashboard.html" class="sw-sidebar-logo">SLAB WORTHY</a>
            <div class="sw-sidebar-logo-icon">SW</div>
            <button class="sw-toggle-btn" id="swToggleBtn" title="Toggle sidebar">
                <span id="swToggleIcon">&#171;</span>
            </button>
        </div>

        <div class="sw-sidebar-section">
            <div class="sw-sidebar-label">Main</div>
            <a href="/dashboard.html" class="sw-sidebar-item ${isActive('dashboard')}" data-tooltip="Dashboard">
                <span class="sw-icon">&#127968;</span> <span class="sw-label">Dashboard</span>
            </a>
            <a href="/app.html" class="sw-sidebar-item ${isActive('grade')}" data-tooltip="Grade a Comic">
                <span class="sw-icon">&#128248;</span> <span class="sw-label">Grade a Comic</span>
            </a>
            <a href="/collection.html" class="sw-sidebar-item ${isActive('collection')}" data-tooltip="My Collection">
                <span class="sw-icon">&#128218;</span> <span class="sw-label">My Collection</span>
            </a>
        </div>

        <div class="sw-sidebar-section">
            <div class="sw-sidebar-label">Sell</div>
            <a href="/collection.html" class="sw-sidebar-item ${isActive('ebay')}" data-tooltip="eBay Listings">
                <span class="sw-icon">&#128176;</span> <span class="sw-label">eBay Listings</span>
            </a>
            <a href="#" onclick="alert('Whatnot Prep \u2014 coming soon!'); return false;" class="sw-sidebar-item ${isActive('whatnot')}" data-tooltip="Whatnot Prep">
                <span class="sw-icon">&#127908;</span> <span class="sw-label">Whatnot Prep</span>
            </a>
        </div>

        <div class="sw-sidebar-section">
            <div class="sw-sidebar-label">Tools</div>
            <a href="/verify.html" class="sw-sidebar-item ${isActive('slab-guard')}" data-tooltip="Slab Guard">
                <span class="sw-icon">&#128737;&#65039;</span> <span class="sw-label">Slab Guard</span>
            </a>
            <a href="#" onclick="alert('Signature ID \u2014 coming soon!'); return false;" class="sw-sidebar-item ${isActive('signature-id')}" data-tooltip="Signature ID">
                <span class="sw-icon">&#9997;&#65039;</span> <span class="sw-label">Signature ID</span>
            </a>
            <a href="#" onclick="alert('Market Pulse \u2014 coming soon!'); return false;" class="sw-sidebar-item ${isActive('market-pulse')}" data-tooltip="Market Pulse">
                <span class="sw-icon">&#128200;</span> <span class="sw-label">Market Pulse</span>
            </a>
            <a href="#" onclick="alert('Price Lookup \u2014 coming soon!'); return false;" class="sw-sidebar-item ${isActive('price-lookup')}" data-tooltip="Price Lookup">
                <span class="sw-icon">&#128202;</span> <span class="sw-label">Price Lookup</span>
            </a>
        </div>

        ${adminItems}

        <div class="sw-sidebar-section">
            <div class="sw-sidebar-label">More</div>
            <a href="/faq.html" class="sw-sidebar-item ${isActive('faq')}" data-tooltip="FAQ">
                <span class="sw-icon">&#10067;</span> <span class="sw-label">FAQ</span>
            </a>
            <a href="/account.html" class="sw-sidebar-item ${isActive('account')}" data-tooltip="Account">
                <span class="sw-icon">&#9881;&#65039;</span> <span class="sw-label">Account</span>
            </a>
        </div>

        <div class="sw-sidebar-spacer"></div>

        <div class="sw-sidebar-user">
            <div class="sw-sidebar-user-avatar">${initials}</div>
            <div class="sw-sidebar-user-info">
                <div class="sw-sidebar-user-name">${displayName}</div>
                <button class="sw-sidebar-logout" onclick="window.swSidebarLogout()">Log Out</button>
            </div>
        </div>
    `;

    // ==========================================
    // DOM MANIPULATION — wrap existing content
    // ==========================================

    // Create mobile overlay
    const overlay = document.createElement('div');
    overlay.className = 'sw-mobile-overlay';
    overlay.id = 'swMobileOverlay';
    overlay.onclick = function() { window.swCloseMobileNav(); };

    // Create mobile topbar
    const topbar = document.createElement('div');
    topbar.className = 'sw-mobile-topbar';
    topbar.innerHTML = `
        <button class="sw-hamburger" onclick="window.swOpenMobileNav()">&#9776;</button>
        <div class="sw-mobile-logo">SLAB WORTHY</div>
        <div style="width:36px"></div>
    `;

    // Create sidebar element
    const sidebar = document.createElement('aside');
    sidebar.className = 'sw-sidebar';
    sidebar.id = 'swSidebar';
    sidebar.innerHTML = sidebarHTML;

    // Create app shell wrapper
    const appShell = document.createElement('div');
    appShell.className = 'sw-app-shell';
    appShell.id = 'swAppShell';

    // Restore collapsed state
    if (localStorage.getItem('sidebar_collapsed') === 'true') {
        appShell.classList.add('collapsed');
    }

    // Create page content wrapper
    const pageContent = document.createElement('div');
    pageContent.className = 'sw-page-content';

    // Move all existing body children into the page content wrapper
    while (document.body.firstChild) {
        pageContent.appendChild(document.body.firstChild);
    }

    // Assemble: body → overlay + topbar + appShell(sidebar + pageContent)
    appShell.appendChild(sidebar);
    appShell.appendChild(pageContent);
    document.body.appendChild(overlay);
    document.body.appendChild(topbar);
    document.body.appendChild(appShell);

    // ==========================================
    // GLOBAL FUNCTIONS
    // ==========================================
    window.swToggleSidebar = function() {
        const shell = document.getElementById('swAppShell');
        const icon = document.getElementById('swToggleIcon');
        shell.classList.toggle('collapsed');
        icon.innerHTML = shell.classList.contains('collapsed') ? '&#187;' : '&#171;';
        localStorage.setItem('sidebar_collapsed', shell.classList.contains('collapsed'));
    };

    window.swOpenMobileNav = function() {
        document.getElementById('swSidebar').classList.add('mobile-open');
        document.getElementById('swMobileOverlay').classList.add('visible');
    };

    window.swCloseMobileNav = function() {
        document.getElementById('swSidebar').classList.remove('mobile-open');
        document.getElementById('swMobileOverlay').classList.remove('visible');
    };

    window.swSidebarLogout = function() {
        localStorage.removeItem('cc_token');
        localStorage.removeItem('cc_user');
        window.location.replace('/login.html');
    };

    // Wire up toggle button
    document.getElementById('swToggleBtn').onclick = window.swToggleSidebar;

    // Update toggle icon if collapsed
    if (localStorage.getItem('sidebar_collapsed') === 'true') {
        document.getElementById('swToggleIcon').innerHTML = '&#187;';
    }
})();
