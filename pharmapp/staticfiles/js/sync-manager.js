/**
 * Sync Manager for PharmApp
 * Handles bidirectional sync between IndexedDB and server
 */

class SyncManager {
    constructor() {
        this.isSyncing = false;
        this.syncInProgress = new Set();
        this.maxRetries = 3;
        this.retryDelay = 1000; // 1 second
        this.endpoints = {
            inventory: '/api/inventory/sync/',
            sales: '/api/sales/sync/',
            customers: '/api/customers/sync/',
            suppliers: '/api/suppliers/sync/',
            wholesale: '/api/wholesale/sync/',
            initialData: '/api/data/initial/',
            receipts: '/api/receipts/sync/',
            dispensing: '/api/dispensing/sync/',
            cart: '/api/cart/sync/'
        };
    }

    /**
     * Check if online
     */
    async isOnline() {
        if (!navigator.onLine) return false;

        try {
            const response = await fetch('/api/health/', {
                method: 'HEAD',
                cache: 'no-cache'
            });
            return response.ok;
        } catch {
            return false;
        }
    }

    /**
     * Download initial data from server
     */
    async downloadInitialData() {
        if (!window.dbManager) {
            console.error('[SyncManager] IndexedDB not ready');
            return false;
        }

        try {
            console.log('[SyncManager] Downloading initial data...');
            this.updateSyncStatus('downloading', 'Downloading data...');

            const response = await fetch(this.endpoints.initialData, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) throw new Error('Failed to fetch initial data');

            const data = await response.json();

            // Store inventory items
            if (data.inventory && data.inventory.length > 0) {
                await window.dbManager.bulkPut(window.dbManager.stores.items, data.inventory);
                console.log(`[SyncManager] Stored ${data.inventory.length} retail items`);
            }

            // Store wholesale items
            if (data.wholesale && data.wholesale.length > 0) {
                await window.dbManager.bulkPut(window.dbManager.stores.wholesaleItems, data.wholesale);
                console.log(`[SyncManager] Stored ${data.wholesale.length} wholesale items`);
            }

            // Store customers
            if (data.customers && data.customers.length > 0) {
                await window.dbManager.bulkPut(window.dbManager.stores.customers, data.customers);
                console.log(`[SyncManager] Stored ${data.customers.length} customers`);
            }

            // Store wholesale customers
            if (data.wholesale_customers && data.wholesale_customers.length > 0) {
                await window.dbManager.bulkPut(window.dbManager.stores.wholesaleCustomers, data.wholesale_customers);
                console.log(`[SyncManager] Stored ${data.wholesale_customers.length} wholesale customers`);
            }

            // Store suppliers
            if (data.suppliers && data.suppliers.length > 0) {
                await window.dbManager.bulkPut(window.dbManager.stores.suppliers, data.suppliers);
                console.log(`[SyncManager] Stored ${data.suppliers.length} suppliers`);
            }

            // Update last sync timestamp
            await window.dbManager.updateSyncMetadata('lastFullSync', new Date().toISOString());

            console.log('[SyncManager] Initial data download complete');
            this.updateSyncStatus('success', 'Data downloaded successfully');
            return true;

        } catch (error) {
            console.error('[SyncManager] Error downloading initial data:', error);
            this.updateSyncStatus('error', 'Download failed: ' + error.message);
            return false;
        }
    }

    /**
     * Sync pending actions to server
     */
    async syncPendingActions() {
        if (!window.dbManager) {
            console.error('[SyncManager] IndexedDB not ready');
            return false;
        }

        if (this.isSyncing) {
            console.log('[SyncManager] Sync already in progress');
            return false;
        }

        if (!(await this.isOnline())) {
            console.log('[SyncManager] Offline, skipping sync');
            return false;
        }

        try {
            this.isSyncing = true;
            this.updateSyncStatus('syncing', 'Syncing data...');

            const pendingActions = await window.dbManager.getPendingActions();

            if (pendingActions.length === 0) {
                console.log('[SyncManager] No pending actions to sync');
                this.updateSyncStatus('success', 'All data synced');
                return true;
            }

            console.log(`[SyncManager] Found ${pendingActions.length} pending actions`);

            // Group actions by type
            const groupedActions = this.groupActionsByType(pendingActions);

            // Sync each group
            for (const [type, actions] of Object.entries(groupedActions)) {
                if (actions.length > 0) {
                    await this.syncActionGroup(type, actions);
                }
            }

            this.updateSyncStatus('success', 'Sync completed');
            console.log('[SyncManager] All pending actions synced successfully');
            return true;

        } catch (error) {
            console.error('[SyncManager] Sync error:', error);
            this.updateSyncStatus('error', 'Sync failed: ' + error.message);
            return false;

        } finally {
            this.isSyncing = false;
        }
    }

    /**
     * Group actions by type for batch processing
     */
    groupActionsByType(actions) {
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

    /**
     * Sync a group of actions to their endpoint
     */
    async syncActionGroup(type, actions) {
        const endpoint = this.endpoints[type];
        if (!endpoint) {
            console.warn(`[SyncManager] No endpoint for type: ${type}`);
            return;
        }

        try {
            console.log(`[SyncManager] Syncing ${actions.length} ${type} actions...`);

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ pendingActions: actions })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Server returned ${response.status}`);
            }

            const result = await response.json();

            // Mark actions as synced
            for (const action of actions) {
                await window.dbManager.markActionSynced(action.id);
            }

            console.log(`[SyncManager] ${type} sync successful:`, result);

        } catch (error) {
            console.error(`[SyncManager] Error syncing ${type}:`, error);

            // Increment retry count for failed actions
            for (const action of actions) {
                const storedAction = await window.dbManager.get(window.dbManager.stores.pendingActions, action.id);
                if (storedAction) {
                    storedAction.retryCount = (storedAction.retryCount || 0) + 1;
                    storedAction.lastError = error.message;
                    storedAction.lastAttempt = new Date().toISOString();

                    // If max retries exceeded, mark as failed
                    if (storedAction.retryCount >= this.maxRetries) {
                        storedAction.failed = true;
                        console.error(`[SyncManager] Action ${action.id} failed after ${this.maxRetries} retries`);
                    }

                    await window.dbManager.put(window.dbManager.stores.pendingActions, storedAction);
                }
            }

            throw error;
        }
    }

    /**
     * Sync data from server (download updates)
     */
    async syncFromServer() {
        if (!(await this.isOnline())) {
            console.log('[SyncManager] Offline, cannot sync from server');
            return false;
        }

        try {
            const lastSync = await window.dbManager.getSyncMetadata('lastFullSync');
            console.log('[SyncManager] Last sync:', lastSync);

            // Download latest data
            await this.downloadInitialData();

            return true;

        } catch (error) {
            console.error('[SyncManager] Error syncing from server:', error);
            return false;
        }
    }

    /**
     * Full bidirectional sync
     */
    async performFullSync() {
        console.log('[SyncManager] Starting full bidirectional sync...');

        try {
            // First, upload pending changes
            await this.syncPendingActions();

            // Then, download latest data
            await this.syncFromServer();

            console.log('[SyncManager] Full sync completed successfully');
            return true;

        } catch (error) {
            console.error('[SyncManager] Full sync failed:', error);
            return false;
        }
    }

    /**
     * Get CSRF token from cookie
     */
    getCsrfToken() {
        const name = 'csrftoken';
        const cookies = document.cookie.split(';');

        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                return decodeURIComponent(cookie.substring(name.length + 1));
            }
        }

        return '';
    }

    /**
     * Update sync status in UI
     */
    updateSyncStatus(status, message) {
        const event = new CustomEvent('sync-status-change', {
            detail: { status, message, timestamp: new Date().toISOString() }
        });
        window.dispatchEvent(event);

        // Also update UI elements if they exist
        const syncStatusEl = document.querySelector('.sync-status');
        const syncTextEl = document.querySelector('.sync-text');

        if (syncStatusEl && syncTextEl) {
            syncTextEl.textContent = message;

            if (status === 'syncing' || status === 'downloading') {
                syncStatusEl.classList.remove('hidden');
            } else {
                setTimeout(() => {
                    syncStatusEl.classList.add('hidden');
                }, 2000);
            }
        }
    }

    /**
     * Schedule automatic sync
     */
    scheduleAutoSync(intervalMinutes = 5) {
        // Clear existing interval if any
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
        }

        // Set up new interval
        this.syncInterval = setInterval(async () => {
            if (await this.isOnline()) {
                console.log('[SyncManager] Auto-sync triggered');
                await this.syncPendingActions();
            }
        }, intervalMinutes * 60 * 1000);

        console.log(`[SyncManager] Auto-sync scheduled every ${intervalMinutes} minutes`);
    }

    /**
     * Stop automatic sync
     */
    stopAutoSync() {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
            this.syncInterval = null;
            console.log('[SyncManager] Auto-sync stopped');
        }
    }
}

// Create global instance
const syncManager = new SyncManager();

// Initialize on page load
if (typeof window !== 'undefined') {
    window.addEventListener('load', () => {
        window.syncManager = syncManager;

        // Wait for IndexedDB to be ready
        window.addEventListener('indexeddb-ready', async () => {
            console.log('[SyncManager] IndexedDB ready, checking for initial sync...');

            // Check if we need initial data
            const lastSync = await window.dbManager.getSyncMetadata('lastFullSync');

            if (!lastSync && navigator.onLine) {
                console.log('[SyncManager] First time setup, downloading initial data...');
                await syncManager.downloadInitialData();
            }

            // Schedule auto-sync every 5 minutes
            syncManager.scheduleAutoSync(5);

            // Sync on online event
            window.addEventListener('online', async () => {
                console.log('[SyncManager] Connection restored, syncing...');
                await syncManager.performFullSync();
            });
        });
    });
}
