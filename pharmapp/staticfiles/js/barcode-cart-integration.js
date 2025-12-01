/**
 * Barcode Cart Integration Module
 * Handles adding scanned items to cart for both retail and wholesale modes
 * Works both online and offline with automatic synchronization
 */

console.log('[Barcode Cart Integration] Module loading...');

class BarcodeCartIntegration {
    constructor(options = {}) {
        this.mode = options.mode || 'retail'; // 'retail' or 'wholesale'
        this.autoAdd = options.autoAdd !== false; // Default to true
        this.defaultQuantity = options.defaultQuantity || 1;
        this.showNotifications = options.showNotifications !== false; // Default to true

        console.log(`[Barcode Cart Integration] Initialized for ${this.mode} mode`);
    }

    /**
     * Main callback for when a barcode scan finds an item
     * This is the function that should be set as window.onBarcodeItemFound
     */
    async onItemScanned(item, barcode) {
        console.log('[Barcode Cart Integration] Item scanned:', item);

        try {
            if (this.autoAdd) {
                // Automatically add to cart
                await this.addToCart(item, this.defaultQuantity);
            } else {
                // Show item details and let user decide
                this.showItemDialog(item, barcode);
            }
        } catch (error) {
            console.error('[Barcode Cart Integration] Error processing scanned item:', error);
            this.showError('Failed to add item to cart: ' + error.message);
        }
    }

    /**
     * Add item to cart (online or offline)
     */
    async addToCart(item, quantity = 1, discount = 0) {
        const currentTime = Date.now();

        try {
            // Prepare cart data
            const cartData = {
                item_id: item.id,
                item_name: item.name,
                quantity: quantity,
                price: parseFloat(item.price || item.cost),
                discount: parseFloat(discount),
                barcode: item.barcode,
                mode: this.mode,
                timestamp: new Date().toISOString(),
                scanned: true  // Flag to indicate this was added via barcode scan
            };

            // Check if online
            if (navigator.onLine) {
                // Online: send to server
                await this.addToCartOnline(cartData);
            } else {
                // Offline: store locally
                await this.addToCartOffline(cartData);
            }

            // Show success notification
            this.showSuccess(`Added ${item.name} to cart (Qty: ${quantity})`);

            // Highlight the item in the UI if it exists
            this.highlightScannedItem(item.id);

            // Refresh cart display if available
            this.refreshCartDisplay();

        } catch (error) {
            console.error('[Barcode Cart Integration] Add to cart failed:', error);
            throw error;
        }
    }

    /**
     * Add to cart via API (online)
     */
    async addToCartOnline(cartData) {
        const endpoint = this.mode === 'retail'
            ? '/api/cart/add/'  // Retail cart endpoint
            : '/api/wholesale-cart/add/';  // Wholesale cart endpoint

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify(cartData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || error.message || 'Failed to add item to cart');
        }

        const result = await response.json();
        console.log('[Barcode Cart Integration] Item added to cart online:', result);
        return result;
    }

    /**
     * Add to cart offline (IndexedDB)
     */
    async addToCartOffline(cartData) {
        if (!window.dbManager) {
            throw new Error('Offline storage not available');
        }

        // Add to local cart
        const storeName = this.mode === 'retail' ? 'cart' : 'wholesaleCart';

        // Create cart item with temporary ID
        const cartItem = {
            id: `offline_${Date.now()}`,
            ...cartData,
            synced: false,
            offline_created: true
        };

        await window.dbManager.add(storeName, cartItem);
        console.log('[Barcode Cart Integration] Item added to cart offline:', cartItem);

        // Queue for sync when back online
        await this.queueCartSyncAction(cartItem);

        this.showStatus('Item added to offline cart. Will sync when online.', 3000);
        return cartItem;
    }

    /**
     * Queue cart action for sync when back online
     */
    async queueCartSyncAction(cartItem) {
        if (!window.dbManager) return;

        const syncAction = {
            id: Date.now(),
            actionType: 'add_to_cart',
            type: 'add_to_cart',
            data: cartItem,
            timestamp: new Date().toISOString(),
            status: 'pending'
        };

        await window.dbManager.add('pendingActions', syncAction);
        console.log('[Barcode Cart Integration] Cart action queued for sync');
    }

    /**
     * Show item dialog with quantity selector
     */
    showItemDialog(item, barcode) {
        // Check if there's a custom dialog handler
        if (typeof window.showScanItemDialog === 'function') {
            window.showScanItemDialog(item, barcode, this.mode);
            return;
        }

        // Fallback to simple prompt
        const quantity = prompt(
            `Add ${item.name} to cart?\n\n` +
            `Price: ₦${item.price || item.cost}\n` +
            `Stock: ${item.stock}\n\n` +
            `Enter quantity:`,
            '1'
        );

        if (quantity && parseFloat(quantity) > 0) {
            this.addToCart(item, parseFloat(quantity));
        }
    }

    /**
     * Highlight scanned item in UI
     */
    highlightScannedItem(itemId) {
        // Look for item card in search results
        const itemCard = document.querySelector(`[data-item-id="${itemId}"]`);

        if (itemCard) {
            // Add highlight class
            itemCard.classList.add('barcode-scanned-item');

            // Scroll into view
            itemCard.scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Remove highlight after 3 seconds
            setTimeout(() => {
                itemCard.classList.remove('barcode-scanned-item');
            }, 3000);
        }
    }

    /**
     * Refresh cart display (trigger HTMX or reload)
     */
    refreshCartDisplay() {
        // Check if HTMX is available
        if (typeof htmx !== 'undefined') {
            // Trigger HTMX refresh on cart widget
            const cartWidget = document.querySelector('#cart-summary-widget');
            if (cartWidget && cartWidget.getAttribute('hx-get')) {
                htmx.trigger(cartWidget, 'refresh');
            }
        }

        // Also update any cart counters
        const cartCounters = document.querySelectorAll('.cart-count, .cart-badge');
        cartCounters.forEach(counter => {
            const currentCount = parseInt(counter.textContent) || 0;
            counter.textContent = currentCount + 1;
        });
    }

    /**
     * Get CSRF token from cookies
     */
    getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }

    /**
     * Show success notification
     */
    showSuccess(message) {
        if (!this.showNotifications) return;

        if (window.offlineHandler && window.offlineHandler.showInAppNotification) {
            window.offlineHandler.showInAppNotification(
                'Item Added',
                message,
                'success'
            );
        } else {
            this.showToast(message, 'success');
        }
    }

    /**
     * Show error notification
     */
    showError(message) {
        if (!this.showNotifications) return;

        if (window.offlineHandler && window.offlineHandler.showInAppNotification) {
            window.offlineHandler.showInAppNotification(
                'Error',
                message,
                'error'
            );
        } else {
            alert(message);
        }
    }

    /**
     * Show status message
     */
    showStatus(message, duration = 2000) {
        if (!this.showNotifications) return;

        if (window.offlineHandler && window.offlineHandler.showInAppNotification) {
            window.offlineHandler.showInAppNotification(
                'Status',
                message,
                'info'
            );
        } else {
            this.showToast(message, 'info');
        }
    }

    /**
     * Show toast notification (fallback)
     */
    showToast(message, type = 'info') {
        const existingToast = document.getElementById('barcode-toast');
        if (existingToast) {
            existingToast.remove();
        }

        const colors = {
            success: '#28a745',
            error: '#dc3545',
            info: '#17a2b8',
            warning: '#ffc107'
        };

        const toast = document.createElement('div');
        toast.id = 'barcode-toast';
        toast.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: ${colors[type] || colors.info};
            color: white;
            padding: 12px 20px;
            border-radius: 5px;
            font-size: 14px;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: slideInRight 0.3s ease-out;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.animation = 'slideOutRight 0.3s ease-in';
                setTimeout(() => toast.remove(), 300);
            }
        }, 2000);
    }

    /**
     * Set mode (retail/wholesale)
     */
    setMode(mode) {
        this.mode = mode;
        console.log('[Barcode Cart Integration] Mode changed to:', mode);
    }

    /**
     * Enable/disable auto-add
     */
    setAutoAdd(enabled) {
        this.autoAdd = enabled;
        console.log('[Barcode Cart Integration] Auto-add:', enabled ? 'enabled' : 'disabled');
    }
}

// Make BarcodeCartIntegration available globally
window.BarcodeCartIntegration = BarcodeCartIntegration;

// Initialize a default instance for retail mode
// Pages can override this by creating their own instance
if (!window.barcodeCartHandler) {
    window.barcodeCartHandler = new BarcodeCartIntegration({
        mode: 'retail',
        autoAdd: true,
        showNotifications: true
    });

    // Set global callback that barcode scanner will use
    window.onBarcodeItemFound = function(item, barcode) {
        window.barcodeCartHandler.onItemScanned(item, barcode);
    };

    console.log('[Barcode Cart Integration] Default handler initialized');
}

// Add CSS animations
if (!document.getElementById('barcode-cart-styles')) {
    const style = document.createElement('style');
    style.id = 'barcode-cart-styles';
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

console.log('[Barcode Cart Integration] Module loaded successfully');
