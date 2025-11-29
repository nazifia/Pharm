const offlineUtils = {
    db: null,
    
    async initDB() {
        if (this.db) return;
        
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('PharmAppDB', 3);  // Increment version
            
            request.onerror = () => reject(request.error);
            
            request.onsuccess = () => {
                this.db = request.result;
                resolve();
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Create stores if they don't exist
                const stores = [
                    { name: 'store', keyPath: 'id' },
                    { name: 'sales', keyPath: 'id', autoIncrement: true },
                    { name: 'customers', keyPath: 'id' },
                    { name: 'suppliers', keyPath: 'id' },
                    { name: 'wholesale', keyPath: 'id' },
                    { name: 'pendingActions', keyPath: 'id', autoIncrement: true }
                ];
                
                stores.forEach(store => {
                    if (!db.objectStoreNames.contains(store.name)) {
                        db.createObjectStore(store.name, store);
                    }
                });
            };
        });
    },

    async saveOfflineAction(actionType, data) {
        await this.initDB();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['pendingActions'], 'readwrite');
            const store = transaction.objectStore('pendingActions');
            
            const action = {
                actionType,
                data,
                timestamp: new Date().toISOString(),
                status: 'pending'
            };
            
            const request = store.add(action);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },

    async getPendingActions() {
        await this.initDB();
        return this.getOfflineData('pendingActions');
    },

    async getOfflineData(storeName) {
        await this.initDB();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.getAll();
            
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }
};

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await offlineUtils.initDB();
        console.log('IndexedDB initialized successfully');
    } catch (error) {
        console.error('Failed to initialize IndexedDB:', error);
    }
});
