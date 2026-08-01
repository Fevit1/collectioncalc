// ============================================================================
// Slab Worthy — Meta (Facebook) Pixel
//
// ⚠️ NEVER add <script src="/js/pixel.js"> directly to a page. This file is
//    injected by the three shared includes (js/footer.js, js/sidebar.js and the
//    root footer.js) via ensurePixel(). faq.html and pricing.html load BOTH
//    footer.js and sidebar.js, so a hand-added tag would be the third copy on
//    those pages and every PageView would be counted twice.
//
// COVERAGE (verified 2026-08-01 by reading every <script src> in the repo):
//    /js/footer.js  → about, check, collectioncalc, contact, faq, index, login,
//                     pricing, privacy, terms, waitlist-confirmed, waitlist
//    /footer.js     → sightings  (root duplicate of js/footer.js — both are live)
//    /js/sidebar.js → account, admin, app, collection, dashboard, faq, pricing,
//                     signatures
//    Not covered (no shared include): modal-ebay-listing, offline, verify.
//    dashboard.html loads sidebar.js and NOT footer.js — that is why the pixel
//    has to be injected from sidebar.js as well, and why it is injected ABOVE
//    sidebar.js's "not logged in → return" guard.
//
// PRIVACY: disclosed in privacy.html § "Advertising & Analytics Cookies", which
//    ships and deploys as its own unit BEFORE this file. Do not deploy this file
//    until that section is live. What we send is limited to PageView plus the two
//    conversion events below — no email, name, phone, payment data, images,
//    grades or collection contents. Advanced Matching and the Conversions API are
//    deliberately NOT enabled; turning either on would start transmitting contact
//    details and would make the disclosure inaccurate.
// ============================================================================
"use strict";
(function () {
    // ── The one and only place the pixel id is written ──────────────────────
    // Replace the placeholder with the real id from Meta Events Manager
    // (Events Manager → Data sources → your pixel → the 15–16 digit number).
    var META_PIXEL_ID = '4401241006789951';

    // Installs an inert API that satisfies every caller instantly.
    //
    // ⚠️ LOAD-BEARING: callers wait for window.SlabWorthyPixel before proceeding
    // (login.html defers the post-verification redirect on it). If the disabled
    // path simply returned without defining anything, every caller would poll
    // until its timeout — measured at 10.8s per verification with the placeholder
    // id in place, i.e. a 10-second stall on the signup flow for a pixel that
    // isn't even switched on yet. Always define the API, even when inert.
    function installInert(reason) {
        window.SlabWorthyPixel = {
            ready: false,
            disabledReason: reason,
            track: function () { return false; },
            whenDispatched: function (cb) { try { cb(); } catch (e) { /* non-fatal */ } }
        };
    }

    // Refuse to initialise while the placeholder is still in place. fbq would
    // otherwise accept the bogus id and fail silently at Meta's end, which reads
    // exactly like "the pixel is installed and working" right up until you check
    // Events Manager and find nothing.
    if (!/^\d{15,16}$/.test(META_PIXEL_ID)) {
        console.warn('[SlabWorthyPixel] META_PIXEL_ID is not set in /js/pixel.js — pixel not initialised.');
        installInert('no-pixel-id');
        return;
    }

    // Guard against a second execution (belt and braces — ensurePixel() in the
    // shared includes already de-dupes the <script> tag itself).
    if (window.SlabWorthyPixel && window.SlabWorthyPixel.ready) return;

    // ── Meta base pixel ─────────────────────────────────────────────────────
    // Standard Meta bootstrap. Note it installs fbq as a QUEUE first, so any
    // fbq(...) call made before fbevents.js finishes downloading is buffered and
    // replayed — events cannot be lost to a slow network.
    /* eslint-disable */
    !function (f, b, e, v, n, t, s) {
        if (f.fbq) return; n = f.fbq = function () {
            n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
        };
        if (!f._fbq) f._fbq = n;
        n.push = n; n.loaded = !0; n.version = '2.0'; n.queue = [];
        t = b.createElement(e); t.async = !0; t.src = v;
        s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s);
    }(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
    /* eslint-enable */

    window.fbq('init', META_PIXEL_ID);
    window.fbq('track', 'PageView');

    // ── Public helper ───────────────────────────────────────────────────────
    // track(eventName, params, onceKey)
    //
    // onceKey (optional): a localStorage key. When supplied, the event fires at
    // most once per browser for that key. This is a SECOND line of defence — the
    // primary one-time guarantee is server-side (see login.html), because
    // localStorage is per-device and is cleared by a private window.
    window.SlabWorthyPixel = {
        ready: true,

        track: function (eventName, params, onceKey) {
            // The sentinel is best-effort and is deliberately NOT allowed to
            // suppress the event when storage is unavailable (private windows,
            // blocked cookies, quota exceeded). The authoritative once-per-user
            // guarantee is server-side — see the comment block in login.html —
            // so failing open here loses no correctness and saves the conversion.
            var canStore = false;
            if (onceKey) {
                try {
                    if (localStorage.getItem(onceKey)) return false;
                    canStore = true;
                } catch (e) {
                    canStore = false;
                }
            }

            try {
                window.fbq('track', eventName, params || {});
            } catch (e) {
                // fbq absent or stubbed by a privacy extension. Return WITHOUT
                // writing the sentinel — burning it here would permanently
                // suppress a conversion that was never actually sent.
                return false;
            }

            if (onceKey && canStore) {
                try { localStorage.setItem(onceKey, '1'); } catch (e) { /* best effort */ }
            }
            return true;
        },

        // whenDispatched(cb, timeoutMs)
        //
        // Calls cb once the real fbevents.js has replaced the bootstrap stub —
        // i.e. once queued events have actually been sent, rather than sitting in
        // fbq.queue in memory.
        //
        // WHY THIS EXISTS: login.html fires CompleteRegistration and then
        // immediately does window.location.href = '/dashboard.html'. If
        // fbevents.js is still in flight at that moment, the queued event is
        // discarded with the document and the conversion is lost — silently, and
        // precisely for the event the ad campaign optimises on. The API call that
        // triggers it goes to Render, which can cold-start, so "the network call
        // was slower than the CDN" is not a safe assumption in either direction.
        //
        // Bounded so a blocked or ad-blocked pixel can never strand the user on
        // the login page: on timeout we proceed with the navigation regardless.
        whenDispatched: function (cb, timeoutMs) {
            var waited = 0;
            var step = 50;
            var limit = typeof timeoutMs === 'number' ? timeoutMs : 1200;
            (function poll() {
                try {
                    // fbq.callMethod is defined only by fbevents.js itself; the
                    // bootstrap stub above deliberately does not set it.
                    if (!window.fbq || window.fbq.callMethod || waited >= limit) { cb(); return; }
                    waited += step;
                    setTimeout(poll, step);
                } catch (e) { cb(); }
            })();
        }
    };
})();
