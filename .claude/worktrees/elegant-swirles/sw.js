const CACHE_NAME = 'slabworthy-v1';
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/app.html',
    '/login.html',
    '/pricing.html',
    '/verify.html',
    '/collection.html',
    '/account.html',
    '/faq.html',
    '/about.html',
    '/styles.css',
    '/js/app.js',
    '/js/auth.js',
    '/js/grading.js',
    '/js/utils.js',
    '/icons/icon-192x192.png',
    '/icons/icon-512x512.png'
];

// Install - cache static assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                // Cache what we can, don't fail if some aren't available
                return Promise.allSettled(
                    STATIC_ASSETS.map(url => cache.add(url).catch(() => {}))
                );
            })
            .then(() => self.skipWaiting())
    );
});

// Activate - clean up old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(keys => Promise.all(
                keys.filter(key => key !== CACHE_NAME)
                    .map(key => caches.delete(key))
            ))
            .then(() => self.clients.claim())
    );
});

// Fetch - network first, fall back to cache
self.addEventListener('fetch', event => {
    const { request } = event;

    // Skip non-GET requests (API calls, form submissions)
    if (request.method !== 'GET') return;

    // Skip API requests - always go to network
    if (request.url.includes('/api/')) return;

    // Skip Chrome extension requests
    if (request.url.startsWith('chrome-extension://')) return;

    event.respondWith(
        fetch(request)
            .then(response => {
                // Cache successful responses
                if (response.ok) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME)
                        .then(cache => cache.put(request, responseClone));
                }
                return response;
            })
            .catch(() => {
                // Network failed, try cache
                return caches.match(request)
                    .then(cached => {
                        if (cached) return cached;
                        // If it's a page request, show the cached index
                        if (request.mode === 'navigate') {
                            return caches.match('/index.html');
                        }
                        return new Response('Offline', { status: 503 });
                    });
            })
    );
});
