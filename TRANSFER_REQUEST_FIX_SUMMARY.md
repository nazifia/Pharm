# Transfer Request Duplicate Message Fix

## Issue Description
When creating a transfer request (both retail and wholesale), both success and error messages were appearing simultaneously:
- Green success message: "Transfer request created successfully"
- Red error message: "An error occurred while creating the transfer request"

## Root Cause
The issue was caused by mixing Django's messages framework with AJAX/JSON responses:

1. **Django Messages**: The views were calling `messages.success()` which adds messages to the session
2. **JSON Response**: The views were also returning `JsonResponse()` with success/error messages
3. **Template Display**: The templates were displaying both the Django messages (from the messages framework) AND the JSON response messages (via JavaScript)

Additionally, the wholesale template was using HTMX (`hx-post`) which expects HTML responses, but the view was returning JSON, causing inconsistent behavior.

## Changes Made

### 1. Backend Changes (Views)

#### File: `pharmapp/wholesale/views.py`
- **Line 3707**: Removed `messages.success(request, "Transfer request created successfully.")`
- Now only returns JSON response for AJAX requests

#### File: `pharmapp/store/views.py`
- **Line 4949**: Removed `messages.success(request, "Transfer request created successfully.")`
- Now only returns JSON response for AJAX requests

### 2. Frontend Changes (Templates)

#### File: `pharmapp/templates/wholesale/wholesale_transfer_request.html`
- **Changed from HTMX to Fetch API**: Replaced `hx-post`, `hx-target`, `hx-swap` attributes with standard form
- **Added form ID**: `id="transfer-form"` for JavaScript handling
- **Added button elements**: `id="submit-btn"`, `id="btn-text"` for loading state management
- **Updated JavaScript**: Replaced HTMX-based script with fetch API implementation (similar to retail template)
- **Added proper error handling**: Consistent with retail template

## How It Works Now

### For Both Retail and Wholesale Transfer Requests:

1. **User submits form**: JavaScript intercepts the form submission
2. **AJAX request**: Form data is sent via fetch API with `X-Requested-With: XMLHttpRequest` header
3. **Server response**: View returns ONLY JSON response (no Django messages)
4. **Client-side display**: JavaScript displays the appropriate message in the `#transfer-response` div
5. **No duplicate messages**: Only one message is shown based on the JSON response

### Success Flow:
```
User clicks "Send Request" 
→ JavaScript prevents default form submission
→ Fetch API sends POST request with AJAX header
→ View creates transfer request
→ View returns JSON: {"success": true, "message": "Transfer request created successfully."}
→ JavaScript displays green success alert
→ Form is reset
```

### Error Flow:
```
User clicks "Send Request"
→ JavaScript prevents default form submission
→ Fetch API sends POST request with AJAX header
→ View encounters error (e.g., insufficient stock)
→ View returns JSON: {"success": false, "message": "Insufficient stock. Available: X"}
→ JavaScript displays red error alert
→ Form remains filled for user to correct
```

## Benefits

1. **No duplicate messages**: Only one message is displayed at a time
2. **Consistent behavior**: Both retail and wholesale use the same approach (fetch API)
3. **Better UX**: No page reload, instant feedback
4. **Proper separation**: Django messages for page reloads, JSON for AJAX
5. **Maintainable**: Both templates use the same pattern

## Testing Checklist

- [ ] Retail transfer request (Wholesale → Retail) shows only success message
- [ ] Wholesale transfer request (Retail → Wholesale) shows only success message
- [ ] Error cases (insufficient stock) show only error message
- [ ] Form resets after successful submission
- [ ] Loading spinner appears during submission
- [ ] Button is disabled during submission
- [ ] Stock validation works correctly
- [ ] Search functionality still works
- [ ] No console errors in browser

## Files Modified

1. `pharmapp/wholesale/views.py` - Removed Django messages from AJAX handler
2. `pharmapp/store/views.py` - Removed Django messages from AJAX handler
3. `pharmapp/templates/wholesale/wholesale_transfer_request.html` - Changed from HTMX to fetch API

