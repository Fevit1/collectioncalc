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
//
// ⚠️ "NETWORK-FIRST" WAS A LIE UNTIL 2026-08-08. READ THIS BEFORE TRUSTING IT.
//    fetch() with no `cache` option uses mode 'default', which CONSULTS THE HTTP
//    CACHE. Static assets are served `public, max-age=14400, must-revalidate`, so
//    "network-first" actually meant "browser-HTTP-cache-first for up to four
//    hours." Two sessions were lost to a shipped fix that looked broken.
//    TWO of this file's THREE fetch() call sites now pass `cache: 'no-cache'`:
//    the install precache and the static-asset branch. The NAVIGATION branch
//    deliberately does NOT — it stays a bare fetch(request), because HTML is served
//    `max-age=0, must-revalidate`, so mode 'default' already finds an always-stale
//    entry and revalidates against the origin on every navigation. Note that HTML's
//    freshness therefore lives in a Cloudflare setting, NOT in this file. Do not
//    "consistency-fix" the navigation branch by adding the option: passing a
//    non-empty init downgrades a request's mode from 'navigate' to 'same-origin'
//    per the Request constructor, changing Sec-Fetch-Mode and unsetting the
//    reload-navigation flag.
//    'no-cache' forces revalidation
//    against the origin while still permitting a conditional request. Assets carry
//    strong ETags, so an unchanged file costs a 304 and not a body. 'no-store' was
//    considered and rejected: it would re-download ~279 KB on every app.html load
//    (grading.js 117K + styles.css 70K + app.js 64K + utils.js 27K) for no
//    correctness gain over 'no-cache'.
//
// ⚠️ THIS DOES NOT FIX A COLD FIRST LOAD. The fetch handler only sees requests
//    this worker intercepts, so a brand-new device, or any load before the worker
//    is controlling the page, still reads the four-hour HTTP cache. Do not read
//    this file and conclude the caching layer is done. The `max-age=14400` is not
//    set anywhere in this repo (there is no `_headers` file); it is almost
//    certainly the Cloudflare zone Browser Cache TTL, and a dashboard Cache Rule
//    on /sw.js and /js/* is the actual root-cause fix. This change is mitigation
//    for the repeat-visit case, which is the case that burned us.
//
// ⚠️ sw.js ITSELF IS NOT SUBJECT TO max-age=14400. Every page calls
//    navigator.serviceWorker.register('/sw.js') with no options, so
//    `updateViaCache` defaults to "imports" — the browser bypasses the HTTP cache
//    for the worker script and uses it only for importScripts() children, of which
//    this file has none. A new worker is ONE RELOAD away, not four hours. Do not
//    budget a four-hour wait when verifying a change to this file.
// ============================================================================

// ⚠️ CACHE_VERSION IS AN INSTRUMENT, NOT A FIX. Bumped by hand, deliberately.
//    It renames CACHE_NAME, which makes the activate handler evict older caches.
//    That clears CACHE STORAGE ONLY. It has never had any effect on the HTTP
//    cache, so bumping it would NOT have prevented either staleness incident —
//    the `cache: 'no-cache'` options below are what fix those.
//    Its remaining real job is evicting assets DELETED from STATIC_ASSETS.
//    Its useful job is verification: after a deploy, `caches.keys()` in the
//    console returning this version and no older one proves the new worker was
//    fetched, installed, and activated.
//    Deriving this from a git SHA was scoped and DROPPED 2026-08-08: there is no
//    build step (no package.json, no bundler), `deploy` is Render-only and is
//    skipped on frontend-only changes, and a pre-commit hook cannot know the SHA
//    of the commit it is creating. Every available hook was skippable, which would
//    have rebuilt the silent-failure mode being removed. If the Cloudflare Pages
//    project turns out to have a build command, CF_PAGES_COMMIT_SHA is a better
//    mechanism than any of those and is worth its own unit.
const CACHE_VERSION = 'v4-20260808';
const CACHE_NAME = `slabworthy-${CACHE_VERSION}`;

const OFFLINE_URL = '/offline.html';

// Static assets only — NO HTML pages beyond the offline fallback.
// Fetch failures are swallowed per-item so one missing file can't abort install.
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
// ⚠️ This used to call cache.add(url). cache.add() is defined as fetch-then-put
//    and it uses the DEFAULT cache mode, with no parameter to override it — so it
//    could seed Cache Storage from a four-hour-stale HTTP copy at install time,
//    and that stale body would then serve every offline fallback until some later
//    request happened to overwrite it. That is the SAME assumption encoded at the
//    fetch handler below (L-SW-2026-026: a guard and the value it protected are one
//    assumption written twice; fix one and the other becomes silently wrong).
//    Expanded to an explicit fetch + put so `cache: 'no-cache'` can be passed.
//    The !response.ok throw replicates cache.add()'s behaviour of refusing to store
//    a non-2xx response; without it an error page would be cached as the asset.
//    The per-item .catch() is preserved: one missing file must not abort install.
function precache(cache, url) {
    return fetch(new Request(url, { cache: 'no-cache' })).then(response => {
        if (!response.ok) throw new Error(`precache ${response.status}: ${url}`);
        return cache.put(url, response);
    });
}

// ⚠️ OFFLINE_URL IS PRECACHED SEPARATELY AND ITS FAILURE IS NOT SWALLOWED.
//    Reason, found in review of this change: 'no-cache' means all 13 precache
//    fetches must now reach the origin, where cache.add() could previously be
//    satisfied from a fresh HTTP-cache entry with no network at all. So a flaky or
//    offline first activation can now fail EVERY item. Swallowing them all would
//    let skipWaiting() run, activate would delete the previous cache, and
//    clients.claim() would hand users an EMPTY Cache Storage.
//    The static assets survive that: the fetch handler cache.put()s every
//    successful response, so they self-heal on the next online load.
//    /offline.html CANNOT self-heal — nothing on the site ever requests it, so
//    install is its only writer, and install does not re-run for a worker that
//    already activated. It would degrade PERMANENTLY, for the life of this worker
//    version, to the inline 503 below — which is exactly the fallback the
//    2026-07-29 policy rewrite existed to replace with a real page.
//    So: if /offline.html cannot be fetched, install REJECTS and this worker never
//    activates, leaving the previous worker and its good copy in place. Fail closed.
//    The browser retries the update on a later navigation.
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache =>
                precache(cache, OFFLINE_URL).then(() => Promise.allSettled(
                    // Filtered from STATIC_ASSETS rather than listed again, so the
                    // precache set stays written in exactly one place.
                    STATIC_ASSETS
                        .filter(url => url !== OFFLINE_URL)
                        .map(url => precache(cache, url).catch(() => {}))
                ))
            )
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
    // `cache: 'no-cache'` is the fix, and it is load-bearing — WITHOUT IT THIS IS
    // NOT NETWORK-FIRST. Bare fetch(request) uses mode 'default' and reads the
    // browser HTTP cache, where these assets sit fresh for max-age=14400 (4h).
    // 'no-cache' forces an origin revalidation but allows a conditional request, so
    // an unchanged asset costs a 304 rather than a full body. See the header block.
    // The .catch() below still reads CACHE STORAGE, which this option does not
    // affect, so the offline fallback and /offline.html are unchanged.
    event.respondWith(
        fetch(request, { cache: 'no-cache' })
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
