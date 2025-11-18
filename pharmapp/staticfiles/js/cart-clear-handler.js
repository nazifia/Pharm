/**
 * Cart Clear Handler
 * Ensures offline cart is cleared when receipt is generated
 */

/**
 * Clear both online and offline carts
 * @param {boolean} isWholesale - Whether this is wholesale cart
 */
async function clearAllCarts(isWholesale = false) {
    console.log(`[CartClearHandler] Clearing all ${isWholesale ? 'wholesale' : 'retail'} carts`);

    try {
        // Clear offline cart if available
        if (typeof clearCartOffline !== 'undefined') {
            await clearCartOffline(isWholesale);
            console.log('[CartClearHandler] Offline cart cleared');
        }

        // Update cart display
        if (typeof updateLocalCartCount !== 'undefined') {
            await updateLocalCartCount(isWholesale);
            console.log('[CartClearHandler] Cart display updated');
        }

        return true;
    } catch (error) {
        console.error('[CartClearHandler] Error clearing carts:', error);
        return false;
    }
}

/**
 * Initialize cart clearing on receipt generation
 */
function initializeCartClearHandler() {
    console.log('[CartClearHandler] Initializing cart clear handler');

    // Listen for receipt generation success
    window.addEventListener('receipt-generated', async function(event) {
        const isWholesale = event.detail?.isWholesale || false;
        console.log(`[CartClearHandler] Receipt generated, clearing ${isWholesale ? 'wholesale' : 'retail'} cart`);
        await clearAllCarts(isWholesale);
    });

    // Also check URL for receipt page and clear cart
    const currentUrl = window.location.pathname;
    if (currentUrl.includes('/receipt/') || currentUrl.includes('/view_receipt/')) {
        const isWholesale = currentUrl.includes('wholesale');
        console.log(`[CartClearHandler] On receipt page, clearing ${isWholesale ? 'wholesale' : 'retail'} cart`);
        // Small delay to ensure offline systems are initialized
        setTimeout(async () => {
            await clearAllCarts(isWholesale);
        }, 300);
    }

    console.log('[CartClearHandler] Cart clear handler initialized');
}

// Initialize when DOM is ready
if (typeof window !== 'undefined') {
    window.addEventListener('load', function() {
        // Quick initialization for offline systems
        setTimeout(() => {
            if (typeof isOfflineModeAvailable !== 'undefined' && isOfflineModeAvailable()) {
                initializeCartClearHandler();
            } else {
                console.warn('[CartClearHandler] Offline mode not available, only online cart will be cleared');
            }
        }, 200);
    });
}
