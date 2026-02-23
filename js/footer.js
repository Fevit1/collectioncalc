// eslint-disable-next-line
// Universal Footer for Slab Worthy
// Include via <script src="/js/footer.js"></script> before </body>
// Automatically injects the standard branded footer.
// Skip: verify.html (has its own simplified footer)
"use strict";
(function() {
    // Don't inject if page already opted out
    if (document.querySelector('[data-no-universal-footer]')) return;

    // Inject footer CSS if not already present (pages that include index.html styles already have it)
    if (!document.querySelector('.footer-logo')) {
        const style = document.createElement('style');
        style.textContent = `
            .footer {
                padding: 2rem 1rem;
                background: var(--purple-dark, #0f0f1a);
                border-top: 1px solid rgba(124, 58, 237, 0.2);
            }
            .footer-content {
                max-width: 600px;
                margin: 0 auto;
                display: flex;
                flex-wrap: wrap;
                justify-content: space-between;
                align-items: flex-start;
                gap: 1.5rem;
            }
            .footer-brand { flex: 1; min-width: 140px; }
            .footer-logo {
                font-family: 'Bangers', cursive;
                font-size: 1.2rem;
                background: linear-gradient(180deg, var(--gold-light, #facc15), var(--gold-mid, #ca8a04));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 0.2rem;
            }
            .footer-tagline { color: var(--text-secondary, rgba(255,255,255,0.5)); font-size: 0.7rem; }
            .footer-links { display: flex; gap: 1.5rem; flex-wrap: wrap; }
            .footer-col h4 {
                font-size: 0.6rem;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: var(--text-secondary, rgba(255,255,255,0.5));
                margin-bottom: 0.5rem;
            }
            .footer-col ul { list-style: none; padding: 0; margin: 0; }
            .footer-col li { margin-bottom: 0.3rem; }
            .footer-col a {
                color: var(--text-primary, rgba(255,255,255,0.9));
                text-decoration: none;
                font-size: 0.75rem;
                transition: color 0.2s;
            }
            .footer-col a:hover { color: var(--purple-light, #a78bfa); }
            .footer-bottom {
                max-width: 600px;
                margin: 1.5rem auto 0;
                padding-top: 1rem;
                border-top: 1px solid rgba(124, 58, 237, 0.1);
                text-align: center;
                color: var(--text-secondary, rgba(255,255,255,0.5));
                font-size: 0.65rem;
            }
        `;
        document.head.appendChild(style);
    }

    // Remove any existing footer (we're replacing it)
    const existingFooter = document.querySelector('footer');
    if (existingFooter) existingFooter.remove();

    // Create and inject the universal footer
    const footer = document.createElement('footer');
    footer.className = 'footer';
    footer.innerHTML = `
        <div class="footer-content">
            <div class="footer-brand">
                <div class="footer-logo">SLAB WORTHY\u2122</div>
                <p class="footer-tagline">Powered by CollectionCalc\u2122</p>
            </div>
            <div class="footer-links">
                <div class="footer-col">
                    <h4>Product</h4>
                    <ul>
                        <li><a href="/#how-it-works">How It Works</a></li>
                        <li><a href="/pricing.html">Pricing</a></li>
                        <li><a href="/faq.html">FAQ</a></li>
                    </ul>
                </div>
                <div class="footer-col">
                    <h4>Company</h4>
                    <ul>
                        <li><a href="/about.html">About</a></li>
                        <li><a href="/contact.html">Contact</a></li>
                    </ul>
                </div>
                <div class="footer-col">
                    <h4>Legal</h4>
                    <ul>
                        <li><a href="/privacy.html">Privacy</a></li>
                        <li><a href="/terms.html">Terms</a></li>
                    </ul>
                </div>
            </div>
        </div>
        <div class="footer-bottom">
            <p>\u00A9 2026 Slab Worthy. Patent Pending.</p>
            <p style="margin-top: 0.3rem; font-size: 0.55rem;">Powered by CollectionCalc\u2122 \u2022 CGC\u00AE and CBCS\u00AE are registered trademarks of their respective owners.</p>
        </div>
    `;

    // Insert before the service worker script or at end of body
    const swScript = document.querySelector('script[src="/sw.js"]') ||
                     Array.from(document.querySelectorAll('script')).find(s => s.textContent.includes('serviceWorker'));
    if (swScript) {
        swScript.parentNode.insertBefore(footer, swScript);
    } else {
        document.body.appendChild(footer);
    }
})();
