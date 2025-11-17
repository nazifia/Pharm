/**
 * Offline Helper Functions
 * Convenient wrapper functions for common offline operations
 */

/**
 * Safe wrapper to queue offline actions
 * @param {string} actionType - Type of action (e.g., 'add_item', 'update_customer')
 * @param {object} data - Data for the action
 * @param {number} priority - Priority level (1=highest, 10=lowest)
 * @returns {Promise<boolean>} Success status
 */
async function queueOfflineAction(actionType, data, priority = 5) {
    try {
        if (!window.offlineHandler) {
            console.warn('[OfflineHelpers] Offline handler not available');
            return false;
        }

        const success = await window.offlineHandler.queueAction(actionType, data, priority);

        if (success) {
            console.log(`[OfflineHelpers] Queued ${actionType}:`, data);
        }

        return success;

    } catch (error) {
        console.error(`[OfflineHelpers] Failed to queue ${actionType}:`, error);
        return false;
    }
}

/**
 * Submit form with offline support
 * @param {HTMLFormElement} form - Form element
 * @param {string} apiEndpoint - Online API endpoint
 * @param {string} actionType - Offline action type
 * @param {function} onSuccess - Success callback
 * @param {function} onError - Error callback
 */
async function submitFormWithOffline(form, apiEndpoint, actionType, onSuccess, onError) {
    try {
        const formData = new FormData(form);
        const jsonData = Object.fromEntries(formData.entries());

        // Try online submission first
        if (navigator.onLine) {
            try {
                const response = await fetch(apiEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify(jsonData)
                });

                if (response.ok) {
                    const result = await response.json();
                    if (onSuccess) onSuccess(result);
                    return true;
                }
            } catch (error) {
                console.log('[OfflineHelpers] Online submission failed, using offline mode');
            }
        }

        // Fallback to offline mode
        const queued = await queueOfflineAction(actionType, jsonData, 3);

        if (queued) {
            if (onSuccess) {
                onSuccess({
                    offline: true,
                    message: 'Saved offline. Will sync when online.'
                });
            }
            return true;
        } else {
            throw new Error('Failed to queue action');
        }

    } catch (error) {
        console.error('[OfflineHelpers] Form submission failed:', error);
        if (onError) onError(error);
        return false;
    }
}

/**
 * Get CSRF token from cookie
 * @returns {string} CSRF token
 */
function getCsrfToken() {
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
 * Search items with offline fallback
 * @param {string} searchTerm - Search term
 * @param {boolean} isWholesale - Whether to search wholesale items
 * @returns {Promise<Array>} Search results
 */
async function searchItemsOffline(searchTerm, isWholesale = false) {
    if (!searchTerm || !window.dbManager) {
        return [];
    }

    try {
        return await window.dbManager.searchItems(searchTerm, isWholesale);
    } catch (error) {
        console.error('[OfflineHelpers] Search failed:', error);
        return [];
    }
}

/**
 * Get low stock items
 * @param {boolean} isWholesale - Whether to check wholesale items
 * @returns {Promise<Array>} Low stock items
 */
async function getLowStockItemsOffline(isWholesale = false) {
    if (!window.dbManager) {
        return [];
    }

    try {
        return await window.dbManager.getLowStockItems(isWholesale);
    } catch (error) {
        console.error('[OfflineHelpers] Failed to get low stock items:', error);
        return [];
    }
}

/**
 * Get expiring items
 * @param {number} days - Number of days to check ahead
 * @param {boolean} isWholesale - Whether to check wholesale items
 * @returns {Promise<Array>} Expiring items
 */
async function getExpiringItemsOffline(days = 30, isWholesale = false) {
    if (!window.dbManager) {
        return [];
    }

    try {
        return await window.dbManager.getExpiringItems(days, isWholesale);
    } catch (error) {
        console.error('[OfflineHelpers] Failed to get expiring items:', error);
        return [];
    }
}

/**
 * Add item to cart with offline support
 * @param {object} cartItem - Cart item data
 * @returns {Promise<boolean>} Success status
 */
async function addToCartOffline(cartItem) {
    try {
        if (!window.dbManager) {
            console.warn('[OfflineHelpers] Database not available');
            return false;
        }

        // Add to IndexedDB cart
        await window.dbManager.put(window.dbManager.stores.cart, {
            ...cartItem,
            id: Date.now(), // Temporary ID
            created_at: new Date().toISOString()
        });

        // Queue for sync
        await queueOfflineAction('add_to_cart', cartItem, 4);

        return true;

    } catch (error) {
        console.error('[OfflineHelpers] Failed to add to cart:', error);
        return false;
    }
}

/**
 * Get cart items
 * @param {number} userId - User ID (optional)
 * @returns {Promise<Array>} Cart items
 */
async function getCartItemsOffline(userId = null) {
    if (!window.dbManager) {
        return [];
    }

    try {
        return userId
            ? await window.dbManager.getAll(window.dbManager.stores.cart, 'user_id', userId)
            : await window.dbManager.getAll(window.dbManager.stores.cart);
    } catch (error) {
        console.error('[OfflineHelpers] Failed to get cart items:', error);
        return [];
    }
}

/**
 * Get cart total
 * @param {number} userId - User ID (optional)
 * @returns {Promise<number>} Cart total
 */
async function getCartTotalOffline(userId = null) {
    if (!window.dbManager) {
        return 0;
    }

    try {
        return await window.dbManager.getCartTotal(userId);
    } catch (error) {
        console.error('[OfflineHelpers] Failed to get cart total:', error);
        return 0;
    }
}

/**
 * Show success message
 * @param {string} message - Success message
 */
function showSuccessMessage(message) {
    if (window.offlineHandler) {
        window.offlineHandler.showInAppNotification('Success', message, 'success');
    } else {
        alert(message);
    }
}

/**
 * Show error message
 * @param {string} message - Error message
 */
function showErrorMessage(message) {
    if (window.offlineHandler) {
        window.offlineHandler.showInAppNotification('Error', message, 'error');
    } else {
        alert(message);
    }
}

/**
 * Show warning message
 * @param {string} message - Warning message
 */
function showWarningMessage(message) {
    if (window.offlineHandler) {
        window.offlineHandler.showInAppNotification('Warning', message, 'warning');
    } else {
        alert(message);
    }
}

/**
 * Show info message
 * @param {string} message - Info message
 */
function showInfoMessage(message) {
    if (window.offlineHandler) {
        window.offlineHandler.showInAppNotification('Info', message, 'info');
    } else {
        alert(message);
    }
}

/**
 * Check if offline mode is available
 * @returns {boolean} Availability status
 */
function isOfflineModeAvailable() {
    return !!(window.dbManager && window.syncManager && window.offlineHandler);
}

/**
 * Check if currently online
 * @returns {boolean} Online status
 */
function isCurrentlyOnline() {
    return window.offlineHandler ? window.offlineHandler.isOnline : navigator.onLine;
}

/**
 * Get pending actions count
 * @returns {Promise<number>} Number of pending actions
 */
async function getPendingActionsCount() {
    if (!window.dbManager) {
        return 0;
    }

    try {
        const actions = await window.dbManager.getPendingActions();
        return actions.length;
    } catch (error) {
        console.error('[OfflineHelpers] Failed to get pending count:', error);
        return 0;
    }
}

/**
 * Trigger manual sync
 * @returns {Promise<boolean>} Success status
 */
async function triggerManualSync() {
    if (!window.offlineHandler) {
        showErrorMessage('Offline functionality not available');
        return false;
    }

    return await window.offlineHandler.manualSync();
}

/**
 * Initialize form with offline support
 * @param {string} formSelector - Form CSS selector
 * @param {string} apiEndpoint - Online API endpoint
 * @param {string} actionType - Offline action type
 */
function initializeOfflineForm(formSelector, apiEndpoint, actionType) {
    const form = document.querySelector(formSelector);

    if (!form) {
        console.warn(`[OfflineHelpers] Form not found: ${formSelector}`);
        return;
    }

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const submitButton = form.querySelector('[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = 'Saving...';
        }

        const success = await submitFormWithOffline(
            form,
            apiEndpoint,
            actionType,
            (result) => {
                if (result.offline) {
                    showWarningMessage(result.message);
                } else {
                    showSuccessMessage('Saved successfully');
                }
                form.reset();
            },
            (error) => {
                showErrorMessage('Failed to save: ' + error.message);
            }
        );

        if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = 'Submit';
        }
    });

    console.log(`[OfflineHelpers] Initialized offline form: ${formSelector}`);
}

/**
 * Setup search with offline support
 * @param {string} inputSelector - Search input CSS selector
 * @param {string} resultsSelector - Results container CSS selector
 * @param {boolean} isWholesale - Whether to search wholesale items
 */
function initializeOfflineSearch(inputSelector, resultsSelector, isWholesale = false) {
    const input = document.querySelector(inputSelector);
    const resultsContainer = document.querySelector(resultsSelector);

    if (!input || !resultsContainer) {
        console.warn('[OfflineHelpers] Search elements not found');
        return;
    }

    let searchTimeout;

    input.addEventListener('input', function() {
        clearTimeout(searchTimeout);

        searchTimeout = setTimeout(async () => {
            const searchTerm = input.value.trim();

            if (searchTerm.length < 2) {
                resultsContainer.innerHTML = '';
                return;
            }

            const results = await searchItemsOffline(searchTerm, isWholesale);

            if (results.length === 0) {
                resultsContainer.innerHTML = '<p>No results found</p>';
                return;
            }

            resultsContainer.innerHTML = results.map(item => `
                <div class="search-result-item">
                    <strong>${item.name}</strong>
                    <span>${item.brand || ''}</span>
                    <span>Stock: ${item.stock || 0}</span>
                    <span>Price: ${item.price || 0}</span>
                </div>
            `).join('');
        }, 300);
    });

    console.log(`[OfflineHelpers] Initialized offline search: ${inputSelector}`);
}

// Export for use in modules (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        queueOfflineAction,
        submitFormWithOffline,
        searchItemsOffline,
        getLowStockItemsOffline,
        getExpiringItemsOffline,
        addToCartOffline,
        getCartItemsOffline,
        getCartTotalOffline,
        showSuccessMessage,
        showErrorMessage,
        showWarningMessage,
        showInfoMessage,
        isOfflineModeAvailable,
        isCurrentlyOnline,
        getPendingActionsCount,
        triggerManualSync,
        initializeOfflineForm,
        initializeOfflineSearch,
        getCsrfToken
    };
}
