# Wholesale Receipt Customer Display Fix - Instructions

## Problem
Wholesale receipts are showing "WALK-IN CUSTOMER" instead of the registered customer name, even when a customer was selected.

## Root Cause
The issue is that the `wholesale_customer_id` is stored in the **dispenser's session** when they select a customer, but when the **cashier** completes the payment request, they're using their own session which doesn't have this information.

The customer information must be passed through the `PaymentRequest` model's `wholesale_customer` field.

## Diagnostic Steps

### Step 1: Run the Diagnostic Script
```bash
cd pharmapp
python manage.py shell < check_payment_request_customer.py
```

This will show you:
- Recent payment requests and whether they have a wholesale_customer
- Recent receipts and their customer information
- All wholesale customers in the database

### Step 2: Test the Workflow
1. **As Dispenser:**
   - Select a registered wholesale customer
   - Add items to cart
   - Send to cashier (create payment request)
   - **Check the console output** - it should print:
     ```
     Debug - Found wholesale customer from session: [Customer Name] (ID: [ID])
     Debug - Creating payment request with wholesale customer: [Customer Name] (ID: [ID])
     Debug - Payment request created with ID: [Request ID], wholesale_customer: [Customer Name]
     ```

2. **As Cashier:**
   - Accept the payment request
   - Complete the payment
   - **Check the console output** - it should print:
     ```
     Debug - Payment request has wholesale customer: [Customer Name] (ID: [ID])
     Debug - Sales created with wholesale_customer: [Customer Name]
     Debug - Receipt created with wholesale_customer: [Customer Name], buyer_name: [Customer Name]
     ```

3. **View the Receipt:**
   - The receipt should now show the customer name instead of "WALK-IN CUSTOMER"

## Expected Behavior

### If Working Correctly:
- Payment request will have `wholesale_customer` set
- Receipt will display the customer name
- Console will show customer information at each step

### If Still Broken:
Check which step is failing:

#### Problem 1: Session doesn't have customer ID
**Symptom:** Console shows "Debug - No wholesale_customer_id found in session"
**Solution:** The customer selection isn't storing the ID properly. Check that you're clicking "Select item" button for a registered customer.

#### Problem 2: Payment request has no customer
**Symptom:** Console shows "Debug - Creating payment request with NO wholesale customer (walk-in)"
**Solution:** The session customer ID is not being retrieved. This is the main issue we fixed.

#### Problem 3: Receipt has no customer
**Symptom:** Console shows "Debug - Receipt created with wholesale_customer: None"
**Solution:** The payment request doesn't have a customer, so the receipt can't have one either.

## Code Changes Made

### 1. Fixed Session Retrieval in `send_to_wholesale_cashier`
**File:** `pharmapp/wholesale/views.py` (lines 3930-3943)

Changed from using `get_user_session_data()` to direct session access:
```python
# OLD (BROKEN):
customer_id = get_user_session_data(request, 'wholesale_customer_id')

# NEW (FIXED):
customer_id = request.session.get('wholesale_customer_id')
```

### 2. Added Debug Logging
Added comprehensive debug messages throughout the flow to track customer information.

### 3. Added Recovery Logic
Added safety checks to recover customer information if it's lost during the process.

## Manual Fix (If Diagnostic Shows Payment Requests Without Customers)

If you have existing payment requests without customers, you can manually update them:

```python
# Run in Django shell
from store.models import PaymentRequest
from customer.models import WholesaleCustomer

# Find payment requests without customers
prs = PaymentRequest.objects.filter(payment_type='wholesale', wholesale_customer__isnull=True, status='pending')

# For each one, you'll need to manually assign the correct customer
# Example:
pr = PaymentRequest.objects.get(request_id='PRQ:12345678')
customer = WholesaleCustomer.objects.get(id=1)  # Replace with correct customer ID
pr.wholesale_customer = customer
pr.save()
```

## Testing Checklist

- [ ] Run diagnostic script
- [ ] Select a registered wholesale customer
- [ ] Add items to cart
- [ ] Send to cashier
- [ ] Check console for "Debug - Creating payment request with wholesale customer: [Name]"
- [ ] As cashier, accept payment request
- [ ] Complete payment
- [ ] Check console for "Debug - Receipt created with wholesale_customer: [Name]"
- [ ] View receipt - should show customer name, not "WALK-IN CUSTOMER"

## If Issue Persists

If the issue still persists after following these steps:

1. **Check the console output** - Share the debug messages
2. **Run the diagnostic script** - Share the output
3. **Check if customer is in database** - Verify the customer exists
4. **Check session middleware** - Ensure Django sessions are working properly

The debug messages will tell us exactly where the customer information is being lost.

