/**
 * Stock Validation Module
 * Validates cart stock before checkout and provides adjustment UI
 */

console.log('[Stock Validation] Module loading...');

// Stock validation function
async function validateCartStock(mode = 'retail') {
    const endpoint = mode === 'retail'
        ? '/validate_cart_stock/'
        : '/wholesale/validate_wholesale_cart_stock/';

    try {
        const response = await fetch(endpoint, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('[Stock Validation] Result:', data);

        return data;
    } catch (error) {
        console.error('[Stock Validation] Error:', error);
        throw error;
    }
}

// Show stock validation modal
function showStockValidationModal(unavailableItems, mode = 'retail') {
    console.log('[Stock Validation] Showing modal for', unavailableItems.length, 'items');

    const modalBody = document.getElementById('unavailableItemsList');
    if (!modalBody) {
        console.error('[Stock Validation] Modal body not found');
        return;
    }

    // Clear existing content
    modalBody.innerHTML = '';

    // Populate table with unavailable items
    unavailableItems.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <strong>${item.name}</strong>
            </td>
            <td>${item.brand}</td>
            <td class="stock-insufficient">
                ${item.requested_quantity} ${item.unit}
            </td>
            <td class="stock-available">
                ${item.available_stock} ${item.unit}
            </td>
            <td>
                <button class="btn btn-sm btn-primary btn-adjust"
                        data-cart-id="${item.id}"
                        data-available="${item.available_stock}"
                        data-mode="${mode}">
                    <i class="fas fa-edit"></i> Adjust
                </button>
                <button class="btn btn-sm btn-danger btn-remove"
                        data-cart-id="${item.id}"
                        data-mode="${mode}">
                    <i class="fas fa-trash"></i> Remove
                </button>
            </td>
        `;
        modalBody.appendChild(row);
    });

    // Add event listeners to adjust buttons
    document.querySelectorAll('.btn-adjust').forEach(btn => {
        btn.addEventListener('click', function() {
            const cartId = this.dataset.cartId;
            const available = this.dataset.available;
            const mode = this.dataset.mode;
            adjustCartItemQuantity(cartId, available, mode);
        });
    });

    // Add event listeners to remove buttons
    document.querySelectorAll('.btn-remove').forEach(btn => {
        btn.addEventListener('click', function() {
            const cartId = this.dataset.cartId;
            const mode = this.dataset.mode;
            removeCartItem(cartId, mode);
        });
    });

    // Show the modal
    $('#stockValidationModal').modal('show');
}

// Adjust cart item quantity
async function adjustCartItemQuantity(cartId, newQuantity, mode = 'retail') {
    try {
        // Calculate quantity to remove (difference between current and new)
        const quantityToRemove = parseFloat(newQuantity);

        const endpoint = mode === 'retail'
            ? `/update_cart_quantity/${cartId}/`
            : `/wholesale/update_wholesale_cart_quantity/${cartId}/`;

        const formData = new FormData();
        formData.append('quantity', quantityToRemove);
        formData.append('csrfmiddlewaretoken', getCsrfToken());

        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        });

        if (response.ok) {
            console.log('[Stock Validation] Quantity adjusted successfully');
            // Reload page to reflect changes
            window.location.reload();
        } else {
            console.error('[Stock Validation] Failed to adjust quantity');
            alert('Failed to adjust quantity. Please try again.');
        }
    } catch (error) {
        console.error('[Stock Validation] Error adjusting quantity:', error);
        alert('Error adjusting quantity. Please try again.');
    }
}

// Remove cart item
async function removeCartItem(cartId, mode = 'retail') {
    if (!confirm('Are you sure you want to remove this item from cart?')) {
        return;
    }

    try {
        const endpoint = mode === 'retail'
            ? `/update_cart_quantity/${cartId}/`
            : `/wholesale/update_wholesale_cart_quantity/${cartId}/`;

        // Get the cart item to find its quantity
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `quantity=999999&csrfmiddlewaretoken=${getCsrfToken()}`, // Remove all
            credentials: 'same-origin'
        });

        if (response.ok) {
            console.log('[Stock Validation] Item removed successfully');
            window.location.reload();
        } else {
            console.error('[Stock Validation] Failed to remove item');
            alert('Failed to remove item. Please try again.');
        }
    } catch (error) {
        console.error('[Stock Validation] Error removing item:', error);
        alert('Error removing item. Please try again.');
    }
}

// Get CSRF token
function getCsrfToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    return '';
}

// Adjust all items to available stock
document.addEventListener('DOMContentLoaded', function() {
    const adjustAllBtn = document.getElementById('adjustAllBtn');
    if (adjustAllBtn) {
        adjustAllBtn.addEventListener('click', function() {
            const adjustButtons = document.querySelectorAll('.btn-adjust');
            adjustButtons.forEach(btn => btn.click());
        });
    }
});

// Export functions for global use
window.validateCartStock = validateCartStock;
window.showStockValidationModal = showStockValidationModal;

console.log('[Stock Validation] Module loaded successfully');
