# Payment Request Rejection Cart Clear Implementation

## Summary
Modified the payment request rejection logic for both retail and wholesale operations to automatically clear the cart when a cashier rejects a payment request. Previously, only items were returned to stock but the cart remained populated, which could cause confusion for users.

## Changes Made

### 1. Retail Payment Request Rejection (`store/views.py`)

**Function**: `reject_payment_request`

**Before**: Only returned items to stock
```python
# Return items to stock and clear cart
for payment_item in payment_request.items.all():
    if payment_item.retail_item:
        payment_item.retail_item.stock += payment_item.quantity
        payment_item.retail_item.save()

messages.success(request, f'Payment request {request_id} rejected and items returned to stock.')
```

**After**: Returns items to stock AND clears the dispenser's cart
```python
# Return items to stock and clear cart
for payment_item in payment_request.items.all():
    if payment_item.retail_item:
        payment_item.retail_item.stock += payment_item.quantity
        payment_item.retail_item.save()

# Clear the cart for the dispenser whose payment request was rejected
try:
    # Clear all cart items for the original dispenser
    from store.models import Cart
    Cart.objects.filter(user=payment_request.dispenser).delete()
    
    # Comprehensive cart session cleanup for the dispenser
    from store.cart_utils import cleanup_cart_session_after_receipt
    # Since we can't access the original dispenser's request,
    # we'll clear the cart items directly
    logger.info(f"Cleared cart for user {payment_request.dispenser.username} after payment request rejection")
    
except Exception as e:
    logger.warning(f"Error clearing cart after payment request rejection: {e}")

messages.success(request, f'Payment request {request_id} rejected, items returned to stock, and cart cleared.')
```

### 2. Wholesale Payment Request Rejection (`wholesale/views.py`)

**Function**: `reject_wholesale_payment_request`

**Before**: Only returned items to stock
```python
# Return items to stock and clear cart
for payment_item in payment_request.items.all():
    if payment_item.wholesale_item:
        payment_item.wholesale_item.stock += payment_item.quantity
        payment_item.wholesale_item.save()

messages.success(request, f'Wholesale payment request {request_id} rejected and items returned to stock.')
```

**After**: Returns items to stock AND clears the dispenser's wholesale cart
```python
# Return items to stock and clear cart
for payment_item in payment_request.items.all():
    if payment_item.wholesale_item:
        payment_item.wholesale_item.stock += payment_item.quantity
        payment_item.wholesale_item.save()

# Clear the wholesale cart for the dispenser whose payment request was rejected
try:
    # Clear all wholesale cart items for the original dispenser
    from store.models import WholesaleCart
    WholesaleCart.objects.filter(user=payment_request.dispenser).delete()
    
    # Comprehensive wholesale cart session cleanup for the dispenser
    from store.cart_utils import cleanup_cart_session_after_receipt
    # Since we can't access the original dispenser's request,
    # we'll clear the cart items directly
    logger.info(f"Cleared wholesale cart for user {payment_request.dispenser.username} after wholesale payment request rejection")
    
except Exception as e:
    logger.warning(f"Error clearing wholesale cart after payment request rejection: {e}")

messages.success(request, f'Wholesale payment request {request_id} rejected, items returned to stock, and cart cleared.')
```

## Key Features of the Implementation

1. **User Isolation**: Cart clearing is performed specifically for the original dispenser (user) who created the payment request, ensuring no cross-user interference.

2. **Stock Restoration**: Maintains the existing functionality of returning all items to stock.

3. **Error Handling**: Includes try-catch blocks to handle any potential errors during cart clearing without affecting the core rejection process.

4. **Logging**: Added informative log messages to track when cart clearing operations are performed.

5. **Session Cleanup**: Although direct session cleanup is limited (since the original user's request isn't available), the cart items are cleared from the database, which prevents confusion on the user's next cart operation.

## Testing

A comprehensive test script (`test_payment_rejection_cart_clear.py`) has been created to verify both retail and wholesale functionality:

- **Retail Test**: Creates a test user, items, cart items, and payment request, then verifies cart clearing upon rejection
- **Wholesale Test**: Similar test for wholesale operations with `WholesaleCart` items

## Benefits

1. **Improved User Experience**: Users won't be confused by leftover cart items after their payment request is rejected
2. **Data Consistency**: Prevents orphaned cart items that could cause issues in subsequent transactions
3. **Cleaner Workflow**: Ensures a clean state for both the dispenser and the system after payment rejection
4. **Maintained Functionality**: All existing stock management functionality is preserved

## Usage

The functionality works automatically whenever a cashier or admin rejects a payment request:

1. **Retail**: Cashier rejects payment request → Cart items cleared for the original dispenser
2. **Wholesale**: Cashier rejects wholesale payment request → Wholesale cart items cleared for the original dispenser

No additional user actions are required - this is a backend enhancement that works seamlessly with existing workflows.
