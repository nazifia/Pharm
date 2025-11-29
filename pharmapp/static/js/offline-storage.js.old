const OfflineStorage = {
    db: null,
    DB_NAME: 'PharmAppDB',
    DB_VERSION: 4,
    
    async init() {
        if (this.db) return this.db;
        
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.DB_NAME, this.DB_VERSION);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve(this.db);
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Define stores with indexes
                const stores = [
                    {
                        name: 'items',
                        keyPath: 'id',
                        indexes: [
                            { name: 'name', keyPath: 'name', options: { unique: false } },
                            { name: 'updated_at', keyPath: 'updated_at', options: { unique: false } }
                        ]
                    },
                    {
                        name: 'sales',
                        keyPath: 'id',
                        autoIncrement: true,
                        indexes: [
                            { name: 'date', keyPath: 'date', options: { unique: false } },
                            { name: 'synced', keyPath: 'synced', options: { unique: false } }
                        ]
                    },
                    {
                        name: 'syncQueue',
                        keyPath: 'id',
                        autoIncrement: true,
                        indexes: [
                            { name: 'timestamp', keyPath: 'timestamp', options: { unique: false } },
                            { name: 'type', keyPath: 'type', options: { unique: false } }
                        ]
                    }
                ];
                
                stores.forEach(store => {
                    if (!db.objectStoreNames.contains(store.name)) {
                        const objectStore = db.createObjectStore(store.name, {
                            keyPath: store.keyPath,
                            autoIncrement: store.autoIncrement
                        });
                        
                        // Create indexes
                        if (store.indexes) {
                            store.indexes.forEach(index => {
                                objectStore.createIndex(index.name, index.keyPath, index.options);
                            });
                        }
                    }
                });
            };
        });
    },

    async addToSyncQueue(action) {
        const db = await this.init();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(['syncQueue'], 'readwrite');
            const store = transaction.objectStore('syncQueue');
            
            const syncItem = {
                ...action,
                timestamp: new Date().toISOString(),
                retries: 0,
                synced: false
            };
            
            const request = store.add(syncItem);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },

    async processSyncQueue() {
        const db = await this.init();
        const items = await this.getAllFromStore('syncQueue');
        
        for (const item of items) {
            try {
                const response = await fetch('/api/sync/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(item)
                });
                
                if (response.ok) {
                    await this.removeFromSyncQueue(item.id);
                } else {
                    await this.updateSyncQueueItem(item.id, { 
                        retries: item.retries + 1 
                    });
                }
            } catch (error) {
                console.error('Sync failed:', error);
            }
        }
    }
};

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', () => {
    OfflineStorage.init();
});