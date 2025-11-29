/**
 * HTMX Offline Adapter
 * Integrates HTMX requests with offline functionality
 */

(function() {
    'use strict';

    console.log('[HTMX Offline] Adapter loading...');

    // Wait for HTMX and offline systems to be ready
    document.addEventListener('DOMContentLoaded', function() {
        if (typeof htmx === 'undefined') {
            console.warn('[HTMX Offline] HTMX not loaded');
            return;
        }

        console.log('[HTMX Offline] Initializing adapter...');

        // Listen for HTMX request errors
        document.body.addEventListener('htmx:sendError', async function(evt) {
            console.log('[HTMX Offline] Request failed, checking if offline:', evt.detail);

            // Check if this is an offline error
            if (!navigator.onLine || (window.offlineHandler && !window.offlineHandler.isOnline)) {
                console.log('[HTMX Offline] Offline detected, handling request');

                const target = evt.detail.elt;
                const xhr = evt.detail.xhr;

                // Check if this is an add-to-cart request
                if (target && target.action && target.action.includes('/add_to_cart/')) {
                    evt.preventDefault(); // Prevent HTMX error handling

                    await handleOfflineAddToCart(target, evt);
                } else if (target && target.action && target.action.includes('/add_to_wholesale_cart/')) {
                    evt.preventDefault();

                    await handleOfflineAddToCart(target, evt, true);
                } else {
                    // Generic offline handling for other requests
                    console.log('[HTMX Offline] Generic offline handling for:', target.action);

                    if (window.offlineHandler) {
                        window.offlineHandler.showInAppNotification(
                            'Offline',
                            'You are offline. This action will be queued and synced when online.',
                            'warning'
                        );
                    }
                }
            }
        });

        // Listen for successful online requests to update offline data
        document.body.addEventListener('htmx:afterOnLoad', function(evt) {
            // If we're online and request succeeded, might want to refresh IndexedDB
            if (navigator.onLine && window.syncManager) {
                // Optionally trigger data refresh
                // window.syncManager.syncFromServer();
            }
        });

        console.log('[HTMX Offline] Adapter initialized successfully');
    });

    /**
     * Handle add to cart when offline (retail or wholesale)
     */
    async function handleOfflineAddToCart(form, evt, isWholesale = false) {
        try {
            console.log('[HTMX Offline] Handling offline cart addition');

            // Extract item ID from form action URL
            const actionUrl = form.action;
            const itemIdMatch = actionUrl.match(/add_to_(?:wholesale_)?cart\/(\d+)/);
            const itemId = itemIdMatch ? parseInt(itemIdMatch[1]) : null;

            if (!itemId) {
                throw new Error('Could not extract item ID from form');
            }

            // Get form data
            const formData = new FormData(form);
            const quantity = parseFloat(formData.get('quantity') || (isWholesale ? '0.5' : '1'));
            const unit = formData.get('unit') || 'unit';

            // Get user ID
            const userId = window.currentUserId || (window.user && window.user.id);

            if (!userId) {
                throw new Error('User not authenticated');
            }

            // Get item details from form or data attributes
            const itemName = form.dataset.itemName ||
                           form.querySelector('[data-item-name]')?.dataset.itemName ||
                           formData.get('item_name') ||
                           'Unknown Item';

            const itemPrice = parseFloat(
                form.dataset.itemPrice ||
                form.querySelector('[data-item-price]')?.dataset.itemPrice ||
                formData.get('price') ||
                0
            );

            // Create cart data
            const cartData = {
                user_id: userId,
                item_id: itemId,
                quantity: quantity,
                unit: unit,
                price: itemPrice,
                item_name: itemName
            };

            const actionType = isWholesale ? 'add_to_wholesale_cart' : 'add_to_cart';
            const cartType = isWholesale ? 'wholesale cart' : 'cart';

            console.log('[HTMX Offline] Cart data:', cartData);

            // Add to offline cart
            if (window.addToCartOffline) {
                const success = await window.addToCartOffline(cartData, isWholesale);

                if (success) {
                    // Show success message
                    if (window.showWarningMessage) {
                        window.showWarningMessage(
                            `Added ${quantity} ${unit} of ${itemName} to ${cartType} (offline). ` +
                            'Will sync when connection is restored.'
                        );
                    }

                    // Update local cart display
                    if (window.updateLocalCartCount) {
                        await window.updateLocalCartCount(isWholesale);
                    }

                    // Reset form
                    form.reset();
                    const quantityInput = form.querySelector('input[name="quantity"]');
                    if (quantityInput) {
                        quantityInput.value = isWholesale ? '0.5' : '1';
                    }

                    // Trigger HTMX success event manually for any listeners
                    htmx.trigger(form, 'htmx:afterSwap', {
                        offline: true,
                        target: form
                    });

                    console.log('[HTMX Offline] Successfully added to offline cart');
                } else {
                    throw new Error('Failed to add to offline cart');
                }
            } else {
                throw new Error('Offline cart function not available');
            }

        } catch (error) {
            console.error('[HTMX Offline] Error handling offline cart:', error);

            if (window.showErrorMessage) {
                window.showErrorMessage('Failed to add to cart: ' + error.message);
            } else {
                alert('Failed to add to cart: ' + error.message);
            }
        }
    }

    /**
     * Check if request should be handled offline
     */
    function shouldHandleOffline() {
        return !navigator.onLine || (window.offlineHandler && !window.offlineHandler.isOnline);
    }

})();

console.log('[HTMX Offline] Adapter script loaded');
