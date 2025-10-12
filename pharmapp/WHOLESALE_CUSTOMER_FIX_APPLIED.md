# Wholesale Customer Display Fix - APPLIED

## Problem
Wholesale receipts were showing "WALK-IN CUSTOMER" instead of the registered customer name, even when a customer was selected during the transaction.

## Root Cause
The wholesale side was using **direct session access** (`request.session['wholesale_customer_id']`) while the retail side uses **proper session utility functions** (`set_user_customer_id` and `get_user_customer_id`).

### Why This Matters
The session utility functions store data in a **user-specific namespace** (`user_data` with key `user_{user.id}_customer_id`), which ensures proper session isolation between different users (dispenser vs cashier).

When using direct session access:
- Dispenser stores: `request.session['wholesale_customer_id'] = 123`
- Cashier tries to read: `request.session.get('wholesale_customer_id')` → Returns `None` (different session)

When using session utilities:
- Dispenser stores: `set_user_customer_id(request, 123)` → Stores as `user_data['user_5_customer_id'] = 123`
- Dispenser reads: `get_user_customer_id(request)` → Reads from `user_data['user_5_customer_id']` → Returns `123`
- Customer info is then stored in `PaymentRequest.wholesale_customer`
- Cashier uses `payment_request.wholesale_customer` (not session) → Customer preserved!

## Solution Applied

### 1. Fixed `select_wholesale_items` Function
**File:** `pharmapp/wholesale/views.py` (lines 976-983)

**BEFORE:**
```python
customer = get_object_or_404(WholesaleCustomer, id=pk)
# Store wholesale customer ID in session for later use
request.session['wholesale_customer_id'] = customer.id
print(f"Debug - Storing wholesale_customer_id in session: {customer.id} for customer: {customer.name}")
print(f"Debug - Session keys after customer selection: {list(request.session.keys())}")
request.session.modified = True
```

**AFTER:**
```python
customer = get_object_or_404(WholesaleCustomer, id=pk)
# Store customer ID in user-specific session for later use (same as retail)
from userauth.session_utils import set_user_customer_id
set_user_customer_id(request, customer.id)
```

### 2. Fixed `send_to_wholesale_cashier` Function
**File:** `pharmapp/wholesale/views.py` (lines 3924-3933)

**BEFORE:**
```python
# Get wholesale customer info (from session or from the cart customer)
from customer.models import WholesaleCustomer
wholesale_customer = None

# Try to get wholesale customer from session first (using direct session access)
customer_id = request.session.get('wholesale_customer_id')
if customer_id:
    try:
        wholesale_customer = WholesaleCustomer.objects.get(id=customer_id)
        print(f"Debug - Found wholesale customer from session: {wholesale_customer.name} (ID: {customer_id})")
    except WholesaleCustomer.DoesNotExist:
        print(f"Debug - Wholesale customer with ID {customer_id} not found in database")
        # Clear invalid session customer ID
        if 'wholesale_customer_id' in request.session:
            del request.session['wholesale_customer_id']
            request.session.modified = True
else:
    print("Debug - No wholesale_customer_id found in session")

# If not found, try to get from the cart items' customer
if not wholesale_customer:
    cart_items = WholesaleCart.objects.filter(user=request.user)
    if cart_items.exists():
        # Use the customer associated with the first cart item
        first_cart_item = cart_items.first()
        if hasattr(first_cart_item, 'wholesale_customer') and first_cart_item.wholesale_customer:
            wholesale_customer = first_cart_item.wholesale_customer
            print(f"Debug - Found wholesale customer from cart item: {wholesale_customer.name}")
```

**AFTER:**
```python
# Get customer info (same pattern as retail)
from customer.models import WholesaleCustomer
from userauth.session_utils import get_user_customer_id
wholesale_customer = None
customer_id = get_user_customer_id(request)
if customer_id:
    try:
        wholesale_customer = WholesaleCustomer.objects.get(id=customer_id)
    except WholesaleCustomer.DoesNotExist:
        pass
```

### 3. Fixed `wholesale_receipt` Function
**File:** `pharmapp/wholesale/views.py` (lines 1639-1647)

**BEFORE:**
```python
# Get wholesale customer ID from session if it exists
wholesale_customer_id = request.session.get('wholesale_customer_id')
wholesale_customer = None
if wholesale_customer_id:
    try:
        wholesale_customer = WholesaleCustomer.objects.get(id=wholesale_customer_id)
        print(f"Found wholesale customer from session: {wholesale_customer.name}")
    except WholesaleCustomer.DoesNotExist:
        print(f"Wholesale customer with ID {wholesale_customer_id} not found in database")
        # Clear invalid session customer ID
        if 'wholesale_customer_id' in request.session:
            del request.session['wholesale_customer_id']
            request.session.modified = True
else:
    print("No wholesale_customer_id found in session")

# Additional debugging: Check if we should have a customer but don't
print(f"Debug - Session keys: {list(request.session.keys())}")
print(f"Debug - wholesale_customer_id: {wholesale_customer_id}")
```

**AFTER:**
```python
# Get customer ID from user-specific session if it exists (same pattern as retail)
from userauth.session_utils import get_user_customer_id
customer_id = get_user_customer_id(request)
wholesale_customer = None
if customer_id:
    try:
        wholesale_customer = WholesaleCustomer.objects.get(id=customer_id)
    except WholesaleCustomer.DoesNotExist:
        pass
```

### 4. Removed Debug Logging and Recovery Logic
- Removed all `print()` debug statements
- Removed recovery mechanisms that tried to restore customer information
- Removed complex fallback logic that tried to get customer from cart items
- Cleaned up the code to match the retail pattern exactly

## How It Works Now

### Complete Workflow:

1. **Dispenser Selects Customer** (`select_wholesale_items`):
   - Customer ID is stored in dispenser's user-specific session using `set_user_customer_id(request, customer.id)`
   - This stores it as: `request.session['user_data']['user_{dispenser_id}_customer_id'] = customer.id`

2. **Dispenser Adds Items to Cart**:
   - Cart items are linked to the dispenser user
   - Customer info remains in dispenser's session

3. **Dispenser Sends to Cashier** (`send_to_wholesale_cashier`):
   - Retrieves customer ID from dispenser's session using `get_user_customer_id(request)`
   - Creates `PaymentRequest` with `wholesale_customer` field set
   - Customer info is now stored in the database (not just session)

4. **Cashier Accepts Payment Request**:
   - Cashier views the payment request
   - Customer info is read from `payment_request.wholesale_customer` (not session)

5. **Cashier Completes Payment** (`complete_wholesale_payment_request`):
   - Uses `payment_request.wholesale_customer` to create sales and receipt
   - Receipt is created with the customer information from the payment request

6. **Receipt Display**:
   - Receipt shows customer name from `receipt.wholesale_customer.name`
   - No longer shows "WALK-IN CUSTOMER" for registered customers

## Comparison with Retail (Working Pattern)

### Retail Pattern (Already Working):
```python
# In select_items (store/views.py line 2988-2989)
from userauth.session_utils import set_user_customer_id
set_user_customer_id(request, customer.id)

# In send_to_cashier (store/views.py line 861-868)
from userauth.session_utils import get_user_customer_id
customer = None
customer_id = get_user_customer_id(request)
if customer_id:
    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        pass
```

### Wholesale Pattern (Now Fixed to Match):
```python
# In select_wholesale_items (wholesale/views.py line 980-983)
from userauth.session_utils import set_user_customer_id
set_user_customer_id(request, customer.id)

# In send_to_wholesale_cashier (wholesale/views.py line 3926-3933)
from userauth.session_utils import get_user_customer_id
wholesale_customer = None
customer_id = get_user_customer_id(request)
if customer_id:
    try:
        wholesale_customer = WholesaleCustomer.objects.get(id=customer_id)
    except WholesaleCustomer.DoesNotExist:
        pass
```

## Testing Instructions

1. **Select a registered wholesale customer**
2. **Add items to cart**
3. **Send to cashier** (create payment request)
4. **As cashier, accept the payment request**
5. **Complete the payment**
6. **View the receipt** - it should now show the customer name instead of "WALK-IN CUSTOMER"

## Expected Result

✅ Wholesale receipts will now display the registered customer's name
✅ The customer information flows correctly from dispenser → payment request → cashier → receipt
✅ The wholesale system now works exactly like the retail system (which was already working correctly)

## Files Modified

1. `pharmapp/wholesale/views.py`:
   - `select_wholesale_items` function (lines 976-983)
   - `send_to_wholesale_cashier` function (lines 3924-3933)
   - `wholesale_receipt` function (lines 1639-1647)
   - `complete_wholesale_payment_request` function (removed debug logging)

## No Database Changes Required

This fix only changes how session data is stored and retrieved. No database migrations are needed.

