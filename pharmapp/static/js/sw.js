/**
 * Enhanced Service Worker for PharmApp
 * Provides offline-first caching and background sync
 */

const CACHE_NAME = 'pharmapp-v5';
const API_CACHE_NAME = 'pharmapp-api-v5';
const OFFLINE_URL = '/offline/';

// Core app shell files
const URLS_TO_CACHE = [
    '/',
    '/offline/',
    '/static/css/sb-admin-2.min.css',
    '/static/vendor/fontawesome-free/css/all.min.css',
    '/static/vendor/jquery/jquery.min.js',
    '/static/vendor/bootstrap/js/bootstrap.bundle.min.js',
    '/static/vendor/jquery-easing/jquery.easing.min.js',
    '/static/js/sb-admin-2.min.js',
    '/static/js/indexeddb-manager.js',
    '/static/js/htmx-offline-adapter.js',
    '/static/js/sync-manager.js',
    '/static/js/offline-handler.js'
];

console.log('[ServiceWorker] Loading...');

/**
 * Install event - cache core app shell
 */
self.addEventListener('install', event => {
    console.log('[ServiceWorker] Installing...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[ServiceWorker] Caching app shell');
                return cache.addAll(URLS_TO_CACHE.map(url => new Request(url, { cache: 'reload' })));
            })
            .then(() => {
                console.log('[ServiceWorker] App shell cached');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('[ServiceWorker] Failed to cache app shell:', error);
            })
    );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', event => {
    console.log('[ServiceWorker] Activating...');

    event.waitUntil(
        Promise.all([
            self.clients.claim(),
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames
                        .filter(cacheName =>
                            cacheName.startsWith('pharmapp-') &&
                            cacheName !== CACHE_NAME &&
                            cacheName !== API_CACHE_NAME
                        )
                        .map(cacheName => {
                            console.log('[ServiceWorker] Removing old cache:', cacheName);
                            return caches.delete(cacheName);
                        })
                );
            })
        ]).then(() => {
            console.log('[ServiceWorker] Activated');
        })
    );
});

/**
 * Fetch event - serve from cache, fallback to network
 * Implements stale-while-revalidate strategy for most requests
 */
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Skip chrome extension requests
    if (url.protocol === 'chrome-extension:') {
        return;
    }

    // API requests - network first, cache fallback
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirstStrategy(request));
        return;
    }

    // Static files and pages - cache first, network fallback
    event.respondWith(cacheFirstStrategy(request));
});

/**
 * Network-first strategy (for API calls)
 * Try network, fall back to cache if offline
 */
async function networkFirstStrategy(request) {
    try {
        const networkResponse = await fetch(request);

        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(API_CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }

        return networkResponse;

    } catch (error) {
        console.log('[ServiceWorker] Network failed, trying cache for:', request.url);

        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }

        // Return offline response for navigation requests
        if (request.mode === 'navigate') {
            const offlineResponse = await caches.match(OFFLINE_URL);
            if (offlineResponse) {
                return offlineResponse;
            }
        }

        // Return a basic offline response
        return new Response('Offline', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: new Headers({ 'Content-Type': 'text/plain' })
        });
    }
}

/**
 * Cache-first strategy (for static resources)
 * Serve from cache, update cache in background
 */
async function cacheFirstStrategy(request) {
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
        // Return cached version immediately
        // Update cache in background (stale-while-revalidate)
        event.waitUntil(updateCache(request));
        return cachedResponse;
    }

    // Not in cache, fetch from network
    try {
        const networkResponse = await fetch(request);

        // Cache the new response
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }

        return networkResponse;

    } catch (error) {
        console.log('[ServiceWorker] Network and cache failed for:', request.url);

        // For navigation requests, show offline page
        if (request.mode === 'navigate') {
            const offlineResponse = await caches.match(OFFLINE_URL);
            if (offlineResponse) {
                return offlineResponse;
            }
        }

        return new Response('Offline', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: new Headers({ 'Content-Type': 'text/plain' })
        });
    }
}

/**
 * Update cache in background
 */
async function updateCache(request) {
    try {
        const networkResponse = await fetch(request);

        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            await cache.put(request, networkResponse);
            console.log('[ServiceWorker] Updated cache for:', request.url);
        }
    } catch (error) {
        // Silently fail - we're already serving from cache
        console.log('[ServiceWorker] Background update failed for:', request.url);
    }
}

/**
 * Background Sync - sync pending actions when online
 */
self.addEventListener('sync', event => {
    console.log('[ServiceWorker] Sync event:', event.tag);

    if (event.tag === 'sync-pending-actions') {
        event.waitUntil(syncPendingActions());
    } else if (event.tag === 'sync-from-server') {
        event.waitUntil(syncFromServer());
    } else if (event.tag.startsWith('sync-')) {
        event.waitUntil(syncPendingActions());
    }
});

/**
 * Sync pending actions to server
 */
async function syncPendingActions() {
    console.log('[ServiceWorker] Syncing pending actions...');

    try {
        // Open IndexedDB
        const db = await openDatabase();
        const pendingActions = await getAllPendingActions(db);

        if (pendingActions.length === 0) {
            console.log('[ServiceWorker] No pending actions to sync');
            return;
        }

        console.log(`[ServiceWorker] Found ${pendingActions.length} pending actions`);

        // Group by type and sync
        const grouped = groupActionsByType(pendingActions);

        for (const [type, actions] of Object.entries(grouped)) {
            if (actions.length > 0) {
                await syncActionGroup(type, actions, db);
            }
        }

        console.log('[ServiceWorker] Sync completed successfully');

        // Notify all clients
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'SYNC_COMPLETE',
                success: true,
                timestamp: new Date().toISOString()
            });
        });

    } catch (error) {
        console.error('[ServiceWorker] Sync failed:', error);

        // Notify clients of failure
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'SYNC_FAILED',
                error: error.message,
                timestamp: new Date().toISOString()
            });
        });

        throw error; // Re-throw to trigger retry
    }
}

/**
 * Sync data from server
 */
async function syncFromServer() {
    console.log('[ServiceWorker] Syncing from server...');

    try {
        const response = await fetch('/api/data/initial/');
        if (!response.ok) throw new Error('Failed to fetch data');

        const data = await response.json();

        // Store in IndexedDB
        const db = await openDatabase();
        await storeInitialData(db, data);

        console.log('[ServiceWorker] Server sync completed');

        // Notify clients
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'SERVER_SYNC_COMPLETE',
                timestamp: new Date().toISOString()
            });
        });

    } catch (error) {
        console.error('[ServiceWorker] Server sync failed:', error);
        throw error;
    }
}

/**
 * Helper functions for IndexedDB operations
 */
function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('PharmAppDB', 4);

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

function getAllPendingActions(db) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['pendingActions'], 'readonly');
        const store = transaction.objectStore('pendingActions');
        const index = store.index('synced');
        const request = index.getAll(false);

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

function groupActionsByType(actions) {
    const grouped = {
        inventory: [],
        sales: [],
        customers: [],
        suppliers: [],
        wholesale: [],
        receipts: [],
        dispensing: [],
        cart: []
    };

    actions.forEach(action => {
        const type = action.actionType || action.type;
        if (type.includes('item') || type.includes('inventory')) {
            grouped.inventory.push(action);
        } else if (type.includes('sale')) {
            grouped.sales.push(action);
        } else if (type.includes('customer')) {
            grouped.customers.push(action);
        } else if (type.includes('supplier')) {
            grouped.suppliers.push(action);
        } else if (type.includes('wholesale')) {
            grouped.wholesale.push(action);
        } else if (type.includes('receipt')) {
            grouped.receipts.push(action);
        } else if (type.includes('dispensing')) {
            grouped.dispensing.push(action);
        } else if (type.includes('cart')) {
            grouped.cart.push(action);
        }
    });

    return grouped;
}

async function syncActionGroup(type, actions, db) {
    const endpoints = {
        inventory: '/api/inventory/sync/',
        sales: '/api/sales/sync/',
        customers: '/api/customers/sync/',
        suppliers: '/api/suppliers/sync/',
        wholesale: '/api/wholesale/sync/',
        receipts: '/api/receipts/sync/',
        dispensing: '/api/dispensing/sync/',
        cart: '/api/cart/sync/'
    };

    const endpoint = endpoints[type];
    if (!endpoint) return;

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pendingActions: actions })
        });

        if (!response.ok) throw new Error(`Sync failed for ${type}`);

        // Mark actions as synced
        const transaction = db.transaction(['pendingActions'], 'readwrite');
        const store = transaction.objectStore('pendingActions');

        for (const action of actions) {
            const updated = { ...action, synced: true, syncedAt: new Date().toISOString() };
            store.put(updated);
        }

        await new Promise((resolve, reject) => {
            transaction.oncomplete = resolve;
            transaction.onerror = () => reject(transaction.error);
        });

        console.log(`[ServiceWorker] Synced ${actions.length} ${type} actions`);

    } catch (error) {
        console.error(`[ServiceWorker] Failed to sync ${type}:`, error);
        throw error;
    }
}

async function storeInitialData(db, data) {
    const transaction = db.transaction(
        ['items', 'wholesaleItems', 'customers', 'wholesaleCustomers', 'suppliers'],
        'readwrite'
    );

    if (data.inventory) {
        const itemStore = transaction.objectStore('items');
        data.inventory.forEach(item => itemStore.put(item));
    }

    if (data.wholesale) {
        const wholesaleStore = transaction.objectStore('wholesaleItems');
        data.wholesale.forEach(item => wholesaleStore.put(item));
    }

    if (data.customers) {
        const customerStore = transaction.objectStore('customers');
        data.customers.forEach(customer => customerStore.put(customer));
    }

    if (data.wholesale_customers) {
        const wholesaleCustomerStore = transaction.objectStore('wholesaleCustomers');
        data.wholesale_customers.forEach(customer => wholesaleCustomerStore.put(customer));
    }

    if (data.suppliers) {
        const supplierStore = transaction.objectStore('suppliers');
        data.suppliers.forEach(supplier => supplierStore.put(supplier));
    }

    return new Promise((resolve, reject) => {
        transaction.oncomplete = resolve;
        transaction.onerror = () => reject(transaction.error);
    });
}

/**
 * Message handler - respond to messages from clients
 */
self.addEventListener('message', event => {
    console.log('[ServiceWorker] Message received:', event.data);

    if (event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    } else if (event.data.type === 'SYNC_NOW') {
        event.waitUntil(syncPendingActions());
    } else if (event.data.type === 'DOWNLOAD_DATA') {
        event.waitUntil(syncFromServer());
    }
});

console.log('[ServiceWorker] Loaded successfully');
