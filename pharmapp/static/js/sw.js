const CACHE_NAME = 'pharmapp-v1';
const API_CACHE_NAME = 'pharmapp-api-v1';
const OFFLINE_URL = '/offline/';

const URLS_TO_CACHE = [
    // Core routes
    '/',
    '/dashboard/',
    '/store/',
    '/wholesale/',
    '/customer/',
    '/supplier/',
    '/offline/',
    
    // Static assets
    '/',
    '/index/',
    '/login/',
    '/offline/',
    '/static/img/icon-192x192.png',
    '/static/img/icon-512x512.png',
    '/static/manifest.json',
    '/static/js/offline.js',
    '/static/js/form-handler.js',
    // '/static/js/transactions.js',
    '/static/vendor/jquery/jquery.min.js',
    '/static/vendor/bootstrap/js/bootstrap.bundle.min.js',
    '/static/vendor/jquery-easing/jquery.easing.min.js',
    '/static/js/sb-admin-2.min.js',
    '/static/vendor/chart.js/Chart.min.js',
    '/static/css/sb-admin-2.min.css',
    '/static/vendor/fontawesome-free/css/all.min.css',
];

const API_ENDPOINTS = [
    '/api/data/initial/',
    '/api/inventory/',
    '/api/customers/',
    '/api/suppliers/',
    '/api/wholesale/',
];

console.log('Service Worker: File loaded');

async function cacheUrls(cacheName, urls) {
    const cache = await caches.open(cacheName);
    const failedUrls = [];
    
    for (const url of urls) {
        try {
            await cache.add(url);
            console.log(`[ServiceWorker] Cached: ${url}`);
        } catch (error) {
            console.warn(`[ServiceWorker] Failed to cache: ${url}`, error);
            failedUrls.push(url);
        }
    }
    
    return failedUrls;
}

self.addEventListener('install', event => {
    console.log('[ServiceWorker] Install');
    event.waitUntil(
        Promise.all([
            cacheUrls(CACHE_NAME, URLS_TO_CACHE).then(failedUrls => {
                if (failedUrls.length > 0) {
                    console.warn('[ServiceWorker] Some app shell URLs failed to cache:', failedUrls);
                }
            }),
            cacheUrls(API_CACHE_NAME, API_ENDPOINTS).then(failedUrls => {
                if (failedUrls.length > 0) {
                    console.warn('[ServiceWorker] Some API endpoints failed to cache:', failedUrls);
                }
            })
        ]).then(() => {
            console.log('[ServiceWorker] Install complete');
            return self.skipWaiting();
        })
    );
});

self.addEventListener('activate', event => {
    console.log('[ServiceWorker] Activate');
    event.waitUntil(
        Promise.all([
            self.clients.claim(),
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames
                        .filter(cacheName => 
                            (cacheName.startsWith('pharmapp-') && 
                             cacheName !== CACHE_NAME && 
                             cacheName !== API_CACHE_NAME))
                        .map(cacheName => {
                            console.log('[ServiceWorker] Removing old cache', cacheName);
                            return caches.delete(cacheName);
                        })
                );
            })
        ])
    );
});

self.addEventListener('fetch', event => {
    const isApiRequest = API_ENDPOINTS.some(endpoint => 
        event.request.url.includes(endpoint));
    
    event.respondWith(
        caches.open(isApiRequest ? API_CACHE_NAME : CACHE_NAME)
            .then(cache => {
                return cache.match(event.request)
                    .then(response => {
                        if (response) {
                            console.log('[ServiceWorker] Return cache', event.request.url);
                            return response;
                        }

                        return fetch(event.request)
                            .then(networkResponse => {
                                if (!networkResponse || 
                                    networkResponse.status !== 200 || 
                                    networkResponse.type !== 'basic') {
                                    return networkResponse;
                                }

                                const responseToCache = networkResponse.clone();
                                cache.put(event.request, responseToCache);
                                return networkResponse;
                            })
                            .catch(() => {
                                if (event.request.mode === 'navigate') {
                                    return caches.match(OFFLINE_URL);
                                }
                            });
                    });
            })
    );
});
