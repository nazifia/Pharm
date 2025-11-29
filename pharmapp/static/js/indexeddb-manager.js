/**
 * IndexedDB Manager for PharmApp Offline Storage
 * Handles all offline data storage and retrieval
 */

class IndexedDBManager {
    constructor() {
        this.dbName = 'PharmAppDB';
        this.version = 5;  // Incremented for barcode support
        this.db = null;
        this.stores = {
            items: 'items',
            wholesaleItems: 'wholesaleItems',
            customers: 'customers',
            wholesaleCustomers: 'wholesaleCustomers',
            suppliers: 'suppliers',
            sales: 'sales',
            pendingActions: 'pendingActions',
            receipts: 'receipts',
            cart: 'cart',
            wholesaleCart: 'wholesaleCart',
            dispensingLog: 'dispensingLog',
            syncMetadata: 'syncMetadata'
        };
    }

    /**
     * Initialize the database
     */
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.version);

            request.onerror = () => {
                console.error('IndexedDB open error:', request.error);
                reject(request.error);
            };

            request.onsuccess = () => {
                this.db = request.result;
                console.log('[IndexedDB] Database opened successfully');
                resolve(this.db);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                console.log('[IndexedDB] Upgrading database from version', event.oldVersion, 'to', event.newVersion);

                // Create object stores if they don't exist
                this.createObjectStores(db);
            };
        });
    }

    /**
     * Create all necessary object stores
     */
    createObjectStores(db) {
        // Items store (retail)
        if (!db.objectStoreNames.contains(this.stores.items)) {
            const itemStore = db.createObjectStore(this.stores.items, { keyPath: 'id' });
            itemStore.createIndex('name', 'name', { unique: false });
            itemStore.createIndex('brand', 'brand', { unique: false });
            itemStore.createIndex('dosage_form', 'dosage_form', { unique: false });
            itemStore.createIndex('updated_at', 'updated_at', { unique: false });
            itemStore.createIndex('barcode', 'barcode', { unique: false });  // Barcode index
        } else if (db.version >= 5) {
            // Add barcode index to existing store
            const transaction = event.target.transaction;
            const itemStore = transaction.objectStore(this.stores.items);
            if (!itemStore.indexNames.contains('barcode')) {
                itemStore.createIndex('barcode', 'barcode', { unique: false });
            }
        }

        // Wholesale items store
        if (!db.objectStoreNames.contains(this.stores.wholesaleItems)) {
            const wholesaleStore = db.createObjectStore(this.stores.wholesaleItems, { keyPath: 'id' });
            wholesaleStore.createIndex('name', 'name', { unique: false });
            wholesaleStore.createIndex('brand', 'brand', { unique: false });
            wholesaleStore.createIndex('updated_at', 'updated_at', { unique: false });
            wholesaleStore.createIndex('barcode', 'barcode', { unique: false });  // Barcode index
        } else if (db.version >= 5) {
            // Add barcode index to existing store
            const transaction = event.target.transaction;
            const wholesaleStore = transaction.objectStore(this.stores.wholesaleItems);
            if (!wholesaleStore.indexNames.contains('barcode')) {
                wholesaleStore.createIndex('barcode', 'barcode', { unique: false });
            }
        }

        // Customers store (retail)
        if (!db.objectStoreNames.contains(this.stores.customers)) {
            const customerStore = db.createObjectStore(this.stores.customers, { keyPath: 'id' });
            customerStore.createIndex('name', 'name', { unique: false });
            customerStore.createIndex('phone', 'phone', { unique: false });
        }

        // Wholesale customers store
        if (!db.objectStoreNames.contains(this.stores.wholesaleCustomers)) {
            const wholesaleCustomerStore = db.createObjectStore(this.stores.wholesaleCustomers, { keyPath: 'id' });
            wholesaleCustomerStore.createIndex('name', 'name', { unique: false });
        }

        // Suppliers store
        if (!db.objectStoreNames.contains(this.stores.suppliers)) {
            const supplierStore = db.createObjectStore(this.stores.suppliers, { keyPath: 'id' });
            supplierStore.createIndex('name', 'name', { unique: false });
        }

        // Sales store
        if (!db.objectStoreNames.contains(this.stores.sales)) {
            const salesStore = db.createObjectStore(this.stores.sales, { keyPath: 'id', autoIncrement: true });
            salesStore.createIndex('created_at', 'created_at', { unique: false });
            salesStore.createIndex('synced', 'synced', { unique: false });
        }

        // Receipts store
        if (!db.objectStoreNames.contains(this.stores.receipts)) {
            const receiptStore = db.createObjectStore(this.stores.receipts, { keyPath: 'id', autoIncrement: true });
            receiptStore.createIndex('receipt_id', 'receipt_id', { unique: true });
            receiptStore.createIndex('synced', 'synced', { unique: false });
        }

        // Cart store (retail)
        if (!db.objectStoreNames.contains(this.stores.cart)) {
            const cartStore = db.createObjectStore(this.stores.cart, { keyPath: 'id', autoIncrement: true });
            cartStore.createIndex('item_id', 'item_id', { unique: false });
            cartStore.createIndex('user_id', 'user_id', { unique: false });
        }

        // Wholesale cart store
        if (!db.objectStoreNames.contains(this.stores.wholesaleCart)) {
            const wholesaleCartStore = db.createObjectStore(this.stores.wholesaleCart, { keyPath: 'id', autoIncrement: true });
            wholesaleCartStore.createIndex('item_id', 'item_id', { unique: false });
            wholesaleCartStore.createIndex('user_id', 'user_id', { unique: false });
        }

        // Dispensing log store
        if (!db.objectStoreNames.contains(this.stores.dispensingLog)) {
            const dispensingStore = db.createObjectStore(this.stores.dispensingLog, { keyPath: 'id', autoIncrement: true });
            dispensingStore.createIndex('synced', 'synced', { unique: false });
        }

        // Pending actions queue
        if (!db.objectStoreNames.contains(this.stores.pendingActions)) {
            const actionStore = db.createObjectStore(this.stores.pendingActions, { keyPath: 'id', autoIncrement: true });
            actionStore.createIndex('timestamp', 'timestamp', { unique: false });
            actionStore.createIndex('priority', 'priority', { unique: false });
            actionStore.createIndex('synced', 'synced', { unique: false });
        }

        // Sync metadata store
        if (!db.objectStoreNames.contains(this.stores.syncMetadata)) {
            db.createObjectStore(this.stores.syncMetadata, { keyPath: 'key' });
        }
    }

    /**
     * Add or update a record
     */
    async put(storeName, data) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.put(data);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Add multiple records in bulk
     */
    async bulkPut(storeName, dataArray) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            let count = 0;

            dataArray.forEach(data => {
                const request = store.put(data);
                request.onsuccess = () => count++;
            });

            transaction.oncomplete = () => resolve(count);
            transaction.onerror = () => reject(transaction.error);
        });
    }

    /**
     * Get a record by key
     */
    async get(storeName, key) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.get(key);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Get a single record by index
     */
    async getByIndex(storeName, indexName, key) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const index = store.index(indexName);
            const request = index.get(key);

            request.onsuccess = () => {
                // Return first result or null if not found
                resolve(request.result || null);
            };
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Get all records from a store
     */
    async getAll(storeName, indexName = null, query = null) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            let request;

            if (indexName && query) {
                const index = store.index(indexName);
                request = index.getAll(query);
            } else {
                request = store.getAll();
            }

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Delete a record
     */
    async delete(storeName, key) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.delete(key);

            request.onsuccess = () => resolve(true);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Clear all records from a store
     */
    async clear(storeName) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.clear();

            request.onsuccess = () => resolve(true);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Search items by name (fuzzy search)
     */
    async searchItems(searchTerm, isWholesale = false) {
        const storeName = isWholesale ? this.stores.wholesaleItems : this.stores.items;
        const allItems = await this.getAll(storeName);

        const searchLower = searchTerm.toLowerCase();
        return allItems.filter(item =>
            item.name.toLowerCase().includes(searchLower) ||
            (item.brand && item.brand.toLowerCase().includes(searchLower))
        );
    }

    /**
     * Add pending action to queue
     */
    async addPendingAction(action) {
        const actionWithMetadata = {
            ...action,
            timestamp: new Date().toISOString(),
            priority: action.priority || 5,
            synced: false,
            retryCount: 0
        };
        return await this.put(this.stores.pendingActions, actionWithMetadata);
    }

    /**
     * Get all pending actions (not synced)
     */
    async getPendingActions() {
        return await this.getAll(this.stores.pendingActions, 'synced', false);
    }

    /**
     * Mark action as synced
     */
    async markActionSynced(actionId) {
        const action = await this.get(this.stores.pendingActions, actionId);
        if (action) {
            action.synced = true;
            action.syncedAt = new Date().toISOString();
            await this.put(this.stores.pendingActions, action);
        }
    }

    /**
     * Update sync metadata
     */
    async updateSyncMetadata(key, value) {
        return await this.put(this.stores.syncMetadata, { key, value, updated_at: new Date().toISOString() });
    }

    /**
     * Get sync metadata
     */
    async getSyncMetadata(key) {
        const result = await this.get(this.stores.syncMetadata, key);
        return result ? result.value : null;
    }

    /**
     * Get items with low stock
     */
    async getLowStockItems(isWholesale = false) {
        const storeName = isWholesale ? this.stores.wholesaleItems : this.stores.items;
        const allItems = await this.getAll(storeName);

        return allItems.filter(item =>
            parseFloat(item.stock || 0) <= parseFloat(item.low_stock_threshold || 0)
        );
    }

    /**
     * Get items expiring soon (within 30 days)
     */
    async getExpiringItems(days = 30, isWholesale = false) {
        const storeName = isWholesale ? this.stores.wholesaleItems : this.stores.items;
        const allItems = await this.getAll(storeName);

        const futureDate = new Date();
        futureDate.setDate(futureDate.getDate() + days);

        return allItems.filter(item => {
            if (!item.exp_date) return false;
            const expDate = new Date(item.exp_date);
            return expDate <= futureDate && expDate >= new Date();
        });
    }

    /**
     * Get cart total
     */
    async getCartTotal(userId = null) {
        const cartItems = userId
            ? await this.getAll(this.stores.cart, 'user_id', userId)
            : await this.getAll(this.stores.cart);

        return cartItems.reduce((total, item) => {
            const subtotal = (parseFloat(item.price || 0) * parseFloat(item.quantity || 0)) - parseFloat(item.discount_amount || 0);
            return total + Math.max(subtotal, 0);
        }, 0);
    }

    /**
     * Search for item by barcode
     * @param {string} barcode - The barcode to search for
     * @param {boolean} isWholesale - Whether to search in wholesale items
     * @returns {Promise<Object|null>} - The item if found, null otherwise
     */
    async searchByBarcode(barcode, isWholesale = false) {
        const storeName = isWholesale ? this.stores.wholesaleItems : this.stores.items;

        if (!this.db) {
            await this.init();
        }

        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction([storeName], 'readonly');
                const store = transaction.objectStore(storeName);
                const index = store.index('barcode');

                const request = index.get(barcode);

                request.onsuccess = () => {
                    const result = request.result;
                    console.log('[IndexedDB] Barcode search result:', result);
                    resolve(result || null);
                };

                request.onerror = () => {
                    console.error('[IndexedDB] Barcode search error:', request.error);
                    reject(request.error);
                };
            } catch (error) {
                console.error('[IndexedDB] Barcode search exception:', error);
                reject(error);
            }
        });
    }

    /**
     * Get all items with a specific barcode (handles duplicates)
     * @param {string} barcode - The barcode to search for
     * @param {boolean} isWholesale - Whether to search in wholesale items
     * @returns {Promise<Array>} - Array of items with matching barcode
     */
    async getAllByBarcode(barcode, isWholesale = false) {
        const storeName = isWholesale ? this.stores.wholesaleItems : this.stores.items;

        if (!this.db) {
            await this.init();
        }

        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction([storeName], 'readonly');
                const store = transaction.objectStore(storeName);
                const index = store.index('barcode');

                const request = index.getAll(barcode);

                request.onsuccess = () => {
                    const results = request.result || [];
                    console.log('[IndexedDB] Found', results.length, 'items with barcode:', barcode);
                    resolve(results);
                };

                request.onerror = () => {
                    console.error('[IndexedDB] Barcode getAll error:', request.error);
                    reject(request.error);
                };
            } catch (error) {
                console.error('[IndexedDB] Barcode getAll exception:', error);
                reject(error);
            }
        });
    }

    /**
     * Close database connection
     */
    close() {
        if (this.db) {
            this.db.close();
            this.db = null;
        }
    }
}

// Create global instance
const dbManager = new IndexedDBManager();

// Initialize on page load
if (typeof window !== 'undefined') {
    window.addEventListener('load', async () => {
        try {
            await dbManager.init();
            console.log('[IndexedDB] Manager initialized successfully');

            // Expose globally
            window.dbManager = dbManager;

            // Dispatch custom event
            window.dispatchEvent(new CustomEvent('indexeddb-ready'));
        } catch (error) {
            console.error('[IndexedDB] Initialization failed:', error);
        }
    });
}
