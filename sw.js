// ============================================================================
// Slab Worthy service worker
//
// ⚠️ BUMP CACHE_NAME on any deploy that changes a precached asset. The activate
//    handler deletes every cache whose name differs from CACHE_NAME — so if the
//    name never changes, that eviction NEVER RUNS. It never ran under 'slabworthy-v1',
//    which was hardcoded from day one.
//
// POLICY (rewritten 2026-07-29):
//   * HTML documents are NEVER cached. Previously every successful page load was
//     stored, so a user whose connection blipped could be served an arbitrarily old
//     page — e.g. the removed private-beta signup panel — with no way for us to fix
//     it remotely. Slab Worthy cannot function offline anyway (grading and valuation
//     both need the API), so caching app HTML bought nothing and was the only route
//     to a stale-UI bug.
//   * A failed navigation now serves /offline.html, not a cached real page.
//     Previously it fell back to cached /index.html, so a failed request for
//     /account.html silently showed the marketing homepage — which reads as
//     "the app logged me out".
//   * Static assets (CSS / JS / icons / fonts / images) are network-first with a
//     cache fallback. Network-first on purpose: HTML is always fresh now, and a
//     cache-first JS bundle could be stale against fresh HTML, which is worse than
//     being slightly slower.
//   * API requests and non-GET requests are never touched.
// ============================================================================

const CACHE_VERSION = 'v3-20260801';
const CACHE_NAME = `slabworthy-${CACHE_VERSION}`;

const OFFLINE_URL = '/offline.html';

// Static assets only — NO HTML pages beyond the offline fallback.
// cache.add() failures are swallowed per-item so one missing file can't abort install.
const STATIC_ASSETS = [
    OFFLINE_URL,
    '/styles.css',
    '/favicon.svg',
    '/js/app.js',
    '/js/auth.js',
    '/js/collection.js',
    '/js/footer.js',
    '/js/grading.js',
    '/js/pixel.js',
    '/js/sidebar.js',
    '/js/utils.js',
    '/icons/icon-192x192.png',
    '/icons/icon-512x512.png'
];

// ── Install ─────────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => Promise.allSettled(
                STATIC_ASSETS.map(url => cache.add(url).catch(() => {}))
            ))
            .then(() => self.skipWaiting())
    );
});

// ── Activate ────────────────────────────────────────────────────────────────
// Now genuinely functional: CACHE_NAME changed, so every older cache (including
// the long-lived 'slabworthy-v1' and all the stale HTML inside it) is deleted the
// first time this version activates.
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(keys => Promise.all(
                keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
            ))
            .then(() => self.clients.claim())
    );
});

// ── Fetch ───────────────────────────────────────────────────────────────────
function isNavigation(request) {
    return request.mode === 'navigate' || request.destination === 'document';
}

self.addEventListener('fetch', event => {
    const { request } = event;

    // Never interfere with writes, API traffic, or extension URLs.
    if (request.method !== 'GET') return;
    if (request.url.includes('/api/')) return;
    if (request.url.startsWith('chrome-extension://')) return;

    // Only handle our own origin; let cross-origin requests go straight through.
    if (new URL(request.url).origin !== self.location.origin) return;

    // ── HTML documents: network-only, offline page on failure. Never stored. ──
    if (isNavigation(request)) {
        event.respondWith(
            fetch(request).catch(() =>
                caches.match(OFFLINE_URL).then(
                    cached => cached || new Response(
                        '<h1>You\'re offline</h1><p>Check your connection and try again.</p>',
                        { status: 503, headers: { 'Content-Type': 'text/html' } }
                    )
                )
            )
        );
        return;
    }

    // ── Static assets: network-first, cache the result, fall back to cache. ──
    event.respondWith(
        fetch(request)
            .then(response => {
                if (response.ok) {
                    const copy = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
                }
                return response;
            })
            .catch(() => caches.match(request).then(
                cached => cached || new Response('Offline', { status: 503 })
            ))
    );
});
