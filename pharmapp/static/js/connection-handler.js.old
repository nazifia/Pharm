class ConnectionHandler {
    constructor() {
        this.statusElement = document.getElementById('connection-status');
        this.syncStatusElement = document.querySelector('.sync-status');
        this.init();
    }

    init() {
        // Monitor online/offline status
        window.addEventListener('online', () => this.handleConnectionChange(true));
        window.addEventListener('offline', () => this.handleConnectionChange(false));
        
        // Initial check
        this.handleConnectionChange(navigator.onLine);
        
        // Set up periodic sync check
        setInterval(() => this.checkSync(), 60000); // Check every minute
    }

    handleConnectionChange(isOnline) {
        this.statusElement.className = `connection-status ${isOnline ? 'online' : 'offline'}`;
        this.statusElement.querySelector('.status-text').textContent = isOnline ? 'Online' : 'Offline';
        
        if (isOnline) {
            this.triggerSync();
        }
    }

    async triggerSync() {
        this.syncStatusElement.classList.remove('hidden');
        
        try {
            await OfflineStorage.processSyncQueue();
            this.showSyncSuccess();
        } catch (error) {
            this.showSyncError();
        } finally {
            setTimeout(() => {
                this.syncStatusElement.classList.add('hidden');
            }, 3000);
        }
    }

    async checkSync() {
        if (navigator.onLine) {
            const pendingActions = await OfflineStorage.getPendingSyncCount();
            if (pendingActions > 0) {
                this.triggerSync();
            }
        }
    }
}

// Initialize when the page loads
const connectionHandler = new ConnectionHandler();