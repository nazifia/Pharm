/**
 * Offline Handler for PharmApp
 * Coordinates offline functionality and provides user feedback
 */

class OfflineHandler {
    constructor() {
        this.isOnline = navigator.onLine;
        this.syncRegistered = false;
        this.statusIndicator = null;
        this.syncStatus = null;
    }

    /**
     * Initialize offline handler
     */
    async init() {
        console.log('[OfflineHandler] Initializing...');

        // Wait for service worker to be ready
        if ('serviceWorker' in navigator) {
            await this.registerServiceWorker();
            await this.registerBackgroundSync();
        } else {
            console.warn('[OfflineHandler] Service Workers not supported');
        }

        // Set up connection monitoring
        this.setupConnectionMonitoring();

        // Set up UI elements
        this.setupUIElements();

        // Set up message listener
        this.setupMessageListener();

        // Initialize UI state
        this.updateConnectionStatus(navigator.onLine);

        console.log('[OfflineHandler] Initialized successfully');
    }

    /**
     * Wait for service worker (registered in base.html)
     */
    async registerServiceWorker() {
        try {
            // Wait for service worker to be ready (registered by base template)
            const registration = await navigator.serviceWorker.ready;

            console.log('[OfflineHandler] Service Worker ready:', registration.scope);

            // Handle updates
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                console.log('[OfflineHandler] New Service Worker found');

                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        // New service worker available
                        this.showUpdateNotification();
                    }
                });
            });

            return registration;

        } catch (error) {
            console.error('[OfflineHandler] Service Worker not available:', error);
        }
    }

    /**
     * Register background sync
     */
    async registerBackgroundSync() {
        try {
            const registration = await navigator.serviceWorker.ready;

            if (!registration || !('sync' in registration)) {
                console.warn('[OfflineHandler] Background Sync not supported');
                return;
            }

            await registration.sync.register('sync-pending-actions');
            this.syncRegistered = true;
            console.log('[OfflineHandler] Background Sync registered');
        } catch (error) {
            console.error('[OfflineHandler] Background Sync registration failed:', error);
        }
    }

    /**
     * Set up connection monitoring
     */
    setupConnectionMonitoring() {
        window.addEventListener('online', async () => {
            console.log('[OfflineHandler] Connection restored');
            this.isOnline = true;
            this.updateConnectionStatus(true);

            // Trigger sync
            await this.triggerSync();
        });

        window.addEventListener('offline', () => {
            console.log('[OfflineHandler] Connection lost');
            this.isOnline = false;
            this.updateConnectionStatus(false);
        });

        // Periodic connection check
        setInterval(async () => {
            const wasOnline = this.isOnline;
            this.isOnline = await this.checkConnection();

            if (wasOnline !== this.isOnline) {
                this.updateConnectionStatus(this.isOnline);

                if (this.isOnline) {
                    await this.triggerSync();
                }
            }
        }, 10000); // Check every 10 seconds
    }

    /**
     * Check internet connection
     */
    async checkConnection() {
        if (!navigator.onLine) return false;

        try {
            const response = await fetch('/api/health/', {
                method: 'HEAD',
                cache: 'no-cache',
                timeout: 5000
            });
            return response.ok;
        } catch {
            return false;
        }
    }

    /**
     * Set up UI elements
     */
    setupUIElements() {
        this.statusIndicator = document.querySelector('#connection-status');
        this.statusDot = document.querySelector('.status-dot');
        this.statusText = document.querySelector('.status-text');
        this.syncStatus = document.querySelector('.sync-status');
        this.syncText = document.querySelector('.sync-text');

        // Create pending actions indicator if not exists
        if (!document.querySelector('.pending-actions-indicator')) {
            this.createPendingActionsIndicator();
        }
    }

    /**
     * Create pending actions indicator
     */
    createPendingActionsIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'pending-actions-indicator hidden';
        indicator.innerHTML = `
            <span class="pending-icon">⏳</span>
            <span class="pending-count">0</span> pending
        `;

        if (this.statusIndicator) {
            this.statusIndicator.appendChild(indicator);
        }
    }

    /**
     * Update connection status UI
     */
    updateConnectionStatus(isOnline) {
        if (!this.statusDot || !this.statusText) return;

        if (isOnline) {
            this.statusDot.classList.remove('offline');
            this.statusDot.classList.add('online');
            this.statusText.textContent = 'Online';
            this.statusIndicator?.classList.remove('offline');
        } else {
            this.statusDot.classList.add('offline');
            this.statusDot.classList.remove('online');
            this.statusText.textContent = 'Offline';
            this.statusIndicator?.classList.add('offline');
        }
    }

    /**
     * Trigger sync
     */
    async triggerSync() {
        if (!this.isOnline) {
            console.log('[OfflineHandler] Cannot sync while offline');
            return false;
        }

        try {
            // Show sync indicator
            if (this.syncStatus) {
                this.syncStatus.classList.remove('hidden');
            }

            // Try background sync first
            if (this.syncRegistered) {
                const registration = await navigator.serviceWorker.ready;
                await registration.sync.register('sync-pending-actions');
                console.log('[OfflineHandler] Background sync triggered');
            } else {
                // Fallback to manual sync
                if (window.syncManager) {
                    await window.syncManager.performFullSync();
                }
            }

            return true;

        } catch (error) {
            console.error('[OfflineHandler] Sync trigger failed:', error);
            return false;

        } finally {
            // Hide sync indicator after delay
            setTimeout(() => {
                if (this.syncStatus) {
                    this.syncStatus.classList.add('hidden');
                }
            }, 1000);
        }
    }

    /**
     * Set up message listener for service worker messages
     */
    setupMessageListener() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.addEventListener('message', event => {
                console.log('[OfflineHandler] Message from SW:', event.data);

                if (event.data.type === 'SYNC_COMPLETE') {
                    this.handleSyncComplete(event.data);
                } else if (event.data.type === 'SYNC_FAILED') {
                    this.handleSyncFailed(event.data);
                } else if (event.data.type === 'SERVER_SYNC_COMPLETE') {
                    this.handleServerSyncComplete(event.data);
                }
            });
        }

        // Listen for sync status changes from sync manager
        window.addEventListener('sync-status-change', event => {
            const { status, message } = event.detail;
            this.updateSyncStatus(status, message);
        });
    }

    /**
     * Handle sync completion
     */
    handleSyncComplete(data) {
        console.log('[OfflineHandler] Sync completed:', data);
        this.showNotification('Sync Complete', 'All changes have been synced to the server', 'success');
        this.updatePendingCount(0);
    }

    /**
     * Handle sync failure
     */
    handleSyncFailed(data) {
        console.error('[OfflineHandler] Sync failed:', data);
        this.showNotification('Sync Failed', 'Some changes could not be synced. Will retry later.', 'warning');
    }

    /**
     * Handle server sync completion
     */
    handleServerSyncComplete(data) {
        console.log('[OfflineHandler] Server sync completed:', data);
        // Refresh page data if needed
        window.dispatchEvent(new CustomEvent('data-updated'));
    }

    /**
     * Update sync status
     */
    updateSyncStatus(status, message) {
        if (!this.syncText) return;

        this.syncText.textContent = message;

        if (status === 'syncing' || status === 'downloading') {
            this.syncStatus?.classList.remove('hidden');
        } else {
            setTimeout(() => {
                this.syncStatus?.classList.add('hidden');
            }, 1000);
        }
    }

    /**
     * Update pending actions count
     */
    async updatePendingCount(count = null) {
        const indicator = document.querySelector('.pending-actions-indicator');
        const countElement = document.querySelector('.pending-count');

        if (!indicator || !countElement) return;

        // Get count from IndexedDB if not provided
        if (count === null && window.dbManager) {
            const pendingActions = await window.dbManager.getPendingActions();
            count = pendingActions.length;
        }

        countElement.textContent = count;

        if (count > 0) {
            indicator.classList.remove('hidden');
        } else {
            indicator.classList.add('hidden');
        }
    }

    /**
     * Show notification to user
     * Only uses in-app notifications (browser notifications disabled)
     */
    showNotification(title, message, type = 'info') {
        // Use in-app notification only (browser notifications disabled)
        this.showInAppNotification(title, message, type);
    }

    /**
     * Show in-app notification
     */
    showInAppNotification(title, message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${this.getBootstrapAlertType(type)} alert-dismissible fade show offline-notification`;
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
        notification.innerHTML = `
            <strong>${title}</strong><br>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 150);
        }, 3000);
    }

    /**
     * Get Bootstrap alert type
     */
    getBootstrapAlertType(type) {
        const typeMap = {
            success: 'success',
            error: 'danger',
            warning: 'warning',
            info: 'info'
        };
        return typeMap[type] || 'info';
    }

    /**
     * Show service worker update notification
     */
    showUpdateNotification() {
        const notification = document.createElement('div');
        notification.className = 'alert alert-info alert-dismissible fade show offline-notification';
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
        notification.innerHTML = `
            <strong>Update Available</strong><br>
            A new version is available.
            <button type="button" class="btn btn-sm btn-primary ms-2" onclick="location.reload()">Reload</button>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);
    }

    /**
     * Request notification permission - REMOVED
     * Notification permissions are no longer requested automatically
     * Users can enable notifications manually if needed
     */
    async requestNotificationPermission() {
        // No longer automatically requesting notification permission
        console.log('[OfflineHandler] Notification permission removed - using in-app notifications only');
        return false;
    }

    /**
     * Add action to queue
     */
    async queueAction(actionType, data, priority = 5) {
        if (!window.dbManager) {
            console.error('[OfflineHandler] IndexedDB not ready');
            return false;
        }

        try {
            const action = {
                actionType,
                data,
                priority,
                timestamp: new Date().toISOString()
            };

            await window.dbManager.addPendingAction(action);
            console.log('[OfflineHandler] Action queued:', actionType);

            // Update pending count
            await this.updatePendingCount();

            // Trigger sync if online
            if (this.isOnline) {
                await this.triggerSync();
            }

            return true;

        } catch (error) {
            console.error('[OfflineHandler] Failed to queue action:', error);
            return false;
        }
    }

    /**
     * Manual sync trigger (for button click)
     */
    async manualSync() {
        if (!this.isOnline) {
            this.showNotification('Cannot Sync', 'You are currently offline. Sync will happen automatically when connection is restored.', 'warning');
            return false;
        }

        this.showInAppNotification('Syncing...', 'Synchronizing data with server', 'info');
        const success = await this.triggerSync();

        if (success) {
            this.showInAppNotification('Sync Complete', 'All data synchronized successfully', 'success');
        } else {
            this.showInAppNotification('Sync Failed', 'Could not complete sync. Please try again.', 'error');
        }

        return success;
    }
}

// Create global instance and initialize
const offlineHandler = new OfflineHandler();

if (typeof window !== 'undefined') {
    window.addEventListener('load', async () => {
        await offlineHandler.init();
        window.offlineHandler = offlineHandler;

        // Notification permissions removed - using in-app notifications only

        // Update pending count periodically
        if (window.dbManager) {
            setInterval(() => {
                offlineHandler.updatePendingCount();
            }, 3000); // Every 3 seconds
        }

        console.log('[OfflineHandler] Ready');
    });
}
