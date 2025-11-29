/**
 * Cart Offline Support
 * Handles add to cart functionality with offline support
 */

/**
 * Handle add to cart with offline support (retail or wholesale)
 * @param {HTMLFormElement} form - The form element
 * @param {object} itemData - Item data from the form
 * @param {boolean} isWholesale - Whether this is a wholesale cart
 * @returns {Promise<boolean>} Success status
 */
async function handleAddToCart(form, itemData, isWholesale = false) {
    const formData = new FormData(form);
    const quantity = parseFloat(formData.get('quantity') || (isWholesale ? '0.5' : '1'));
    const unit = formData.get('unit') || 'unit';
    const itemId = itemData.item_id;

    // Get user ID from Django template context or session
    const userId = window.currentUserId; // Should be set by Django template

    if (!userId) {
        showErrorMessage('User not authenticated');
        return false;
    }

    const cartData = {
        user_id: userId,
        item_id: itemId,
        quantity: quantity,
        unit: unit,
        price: itemData.price || 0,
        item_name: itemData.name || 'Unknown Item'
    };

    const actionType = isWholesale ? 'add_to_wholesale_cart' : 'add_to_cart';
    const cartType = isWholesale ? 'wholesale cart' : 'cart';

    // Prevent concurrent submissions for the same item
    const submissionKey = `cart-submit-${itemId}-${isWholesale}`;

    if (!window.pendingCartSubmissions) {
        window.pendingCartSubmissions = new Set();
    }

    if (window.pendingCartSubmissions.has(submissionKey)) {
        console.warn('[CartOffline] Submission already in progress for this item');
        return false;
    }

    window.pendingCartSubmissions.add(submissionKey);

    try {
        // Check if online
        if (navigator.onLine && window.offlineHandler && window.offlineHandler.isOnline) {
            // Try online submission first
            try {
                const csrfToken = getCsrfToken();
                const response = await fetch(form.action, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: formData,
                    signal: AbortSignal.timeout(10000)  // 10 second timeout
                });

                if (response.ok) {
                    showSuccessMessage(`Added ${quantity} ${unit} of ${cartData.item_name} to ${cartType}`);

                    // Update cart widget if available via HTMX
                    if (typeof htmx !== 'undefined') {
                        const widgetId = isWholesale ? '#wholesale-cart-summary-widget' : '#cart-summary-widget';
                        htmx.trigger(widgetId, 'refresh');
                    }

                    return true;
                }
            } catch (error) {
                // Distinguish timeout from network errors
                if (error.name === 'TimeoutError' || error.name === 'AbortError') {
                    // Ambiguous - might have succeeded server-side
                    console.warn('[CartOffline] Request timed out - submission status unknown');
                    showWarningMessage(
                        `Request timed out. Please check your ${cartType} to verify if the item was added.`
                    );
                    return false; // DON'T fallback to offline on timeout
                }
                // Only true network errors fall through to offline mode
                console.log('[CartOffline] Network error, falling back to offline mode:', error);
            }
        }

        // Offline mode or online submission clearly failed
        console.log('[CartOffline] Using offline mode');

        // Add to local cart store AND queue for sync
        const success = await addToCartOffline(cartData, isWholesale);

        if (success) {
            showWarningMessage(
                `Added ${quantity} ${unit} of ${cartData.item_name} to ${cartType} (offline). ` +
                'Will sync when connection is restored.'
            );

            // Update local cart count and display
            await updateLocalCartCount(isWholesale);

            return true;
        } else {
            throw new Error('Failed to add to offline cart');
        }

    } catch (error) {
        console.error('[CartOffline] Failed to add to cart:', error);
        showErrorMessage('Failed to add item to cart: ' + error.message);
        return false;
    } finally {
        // Always cleanup submission lock
        window.pendingCartSubmissions.delete(submissionKey);
    }
}

/**
 * Update local cart count display (retail or wholesale)
 * @param {boolean} isWholesale - Whether this is wholesale cart
 */
async function updateLocalCartCount(isWholesale = false) {
    try {
        if (!window.dbManager) return;

        const userId = window.currentUserId;
        const cartItems = await getCartItemsOffline(userId, isWholesale);
        const totalItems = cartItems.reduce((sum, item) => sum + (parseFloat(item.quantity) || 0), 0);
        const totalPrice = cartItems.reduce((sum, item) => {
            const subtotal = (parseFloat(item.price || 0) * parseFloat(item.quantity || 0));
            return sum + subtotal;
        }, 0);

        console.log(`[CartOffline] ${isWholesale ? 'Wholesale' : 'Retail'} cart items:`, cartItems.length, 'Total:', totalPrice);

        // Update cart count badge if exists
        const cartBadge = document.querySelector(isWholesale ? '.wholesale-cart-count-badge' : '.cart-count-badge');
        if (cartBadge) {
            cartBadge.textContent = Math.round(totalItems * 10) / 10; // Round to 1 decimal
            if (totalItems > 0) {
                cartBadge.style.display = 'inline-block';
            }
        }

        // Update cart summary widget
        const widgetSelector = isWholesale ? '#wholesale-cart-summary-widget' : '#cart-summary-widget';
        const cartWidget = document.querySelector(widgetSelector);

        if (cartWidget) {
            const countElement = cartWidget.querySelector('.cart-count');
            const totalElement = cartWidget.querySelector('.cart-total');

            if (countElement) {
                countElement.textContent = cartItems.length;
            }

            if (totalElement) {
                totalElement.textContent = `₦${totalPrice.toFixed(2)}`;
            }

            // Show offline indicator
            const offlineIndicator = cartWidget.querySelector('.offline-indicator');
            if (!offlineIndicator && cartItems.length > 0) {
                const indicator = document.createElement('span');
                indicator.className = 'badge badge-warning offline-indicator ml-2';
                indicator.textContent = 'Offline';
                indicator.style.fontSize = '0.7em';
                cartWidget.querySelector('.card-title, h6')?.appendChild(indicator);
            }
        }

    } catch (error) {
        console.error('[CartOffline] Failed to update cart count:', error);
    }
}

/**
 * Initialize add to cart forms with offline support
 */
function initializeCartOfflineSupport() {
    console.log('[CartOffline] Initializing cart offline support');

    // Listen for form submissions on add-to-cart forms
    document.addEventListener('submit', async function(e) {
        const form = e.target;

        // Check if this is an add-to-cart form (retail or wholesale)
        const isRetailCart = form.action && form.action.includes('/add_to_cart/');
        const isWholesaleCart = form.action && form.action.includes('/add_to_wholesale_cart/');

        if (!isRetailCart && !isWholesaleCart) {
            return;
        }

        e.preventDefault();
        e.stopPropagation();

        // Disable submit button
        const submitButton = form.querySelector('button[type="submit"]');
        const originalButtonText = submitButton ? submitButton.innerHTML : '';
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
        }

        try {
            // Extract item ID from form action URL
            const actionUrl = form.action;
            const itemIdMatch = isWholesaleCart
                ? actionUrl.match(/add_to_wholesale_cart\/(\d+)/)
                : actionUrl.match(/add_to_cart\/(\d+)/);
            const itemId = itemIdMatch ? parseInt(itemIdMatch[1]) : null;

            if (!itemId) {
                throw new Error('Could not extract item ID from form');
            }

            // Get item data from form or data attributes
            const itemData = {
                item_id: itemId,
                name: form.dataset.itemName || form.querySelector('[data-item-name]')?.dataset.itemName || '',
                price: parseFloat(form.dataset.itemPrice || form.querySelector('[data-item-price]')?.dataset.itemPrice || 0)
            };

            // Handle the submission with offline support
            await handleAddToCart(form, itemData, isWholesaleCart);

            // Reset quantity input
            const quantityInput = form.querySelector('input[name="quantity"]');
            if (quantityInput) {
                quantityInput.value = isWholesaleCart ? '0.5' : '1';
            }

        } catch (error) {
            console.error('[CartOffline] Error in form submission:', error);
            showErrorMessage('Failed to add to cart: ' + error.message);
        } finally {
            // Re-enable submit button
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = originalButtonText;
            }
        }
    });

    // Update cart count on page load (check both retail and wholesale)
    updateLocalCartCount(false); // Retail
    updateLocalCartCount(true);  // Wholesale

    console.log('[CartOffline] Cart offline support initialized');
}

// Initialize when DOM is ready and offline systems are available
if (typeof window !== 'undefined') {
    window.addEventListener('load', function() {
        // Quick initialization for offline systems
        setTimeout(() => {
            if (isOfflineModeAvailable()) {
                initializeCartOfflineSupport();
            } else {
                console.warn('[CartOffline] Offline mode not available, cart will work online only');
            }
        }, 200);
    });

    // Re-check when coming back online
    window.addEventListener('online', function() {
        console.log('[CartOffline] Connection restored, cart can sync');
        if (window.offlineHandler) {
            window.offlineHandler.triggerSync();
        }
    });
}
