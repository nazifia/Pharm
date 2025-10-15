# Transfer Request Fixes - Retail & Wholesale

## Issue Summary
The transfer request creation was showing both success and error messages simultaneously, indicating that the request was being created but with incorrect logic.

## Root Cause
The `create_transfer_request_wholesale` function in `pharmapp/store/views.py` was **ignoring** the `from_wholesale` parameter and hardcoding all transfers as `from_wholesale=True`, regardless of the actual transfer direction.

## Transfer Request Logic

### Model Structure (TransferRequest)
```python
class TransferRequest(models.Model):
    wholesale_item = ForeignKey('WholesaleItem')  # Set when retail requests from wholesale
    retail_item = ForeignKey('Item')              # Set when wholesale requests from retail
    from_wholesale = BooleanField()               # True = wholesale requesting, False = retail requesting
```

### Transfer Directions

#### 1. Wholesale → Retail (Retail requesting from Wholesale)
- **Initiated by**: Retail user
- **Template**: `retail_transfer_request.html`
- **Form parameter**: `from_wholesale="false"`
- **Model fields**:
  - `wholesale_item` = source item (WholesaleItem)
  - `retail_item` = None
  - `from_wholesale` = False
- **Flow**: Wholesale stock → Retail stock

#### 2. Retail → Wholesale (Wholesale requesting from Retail)
- **Initiated by**: Wholesale user
- **Template**: `wholesale_transfer_request.html`
- **Form parameter**: `from_wholesale="true"`
- **Model fields**:
  - `retail_item` = source item (Item)
  - `wholesale_item` = None
  - `from_wholesale` = True
- **Flow**: Retail stock → Wholesale stock

## Files Modified

### 1. pharmapp/store/views.py
**Function**: `create_transfer_request_wholesale` (lines 4909-4965)

**Before**:
```python
elif request.method == "POST":
    try:
        requested_quantity = int(request.POST.get("requested_quantity", 0))
        item_id = request.POST.get("item_id")
        from_wholesale = request.POST.get("from_wholesale", "false").lower() == "true"

        if not item_id or requested_quantity <= 0:
            return JsonResponse({"success": False, "message": "Invalid input provided."}, status=400)

        source_item = get_object_or_404(Item, id=item_id)  # ❌ Always gets retail item

        transfer = TransferRequest.objects.create(
            retail_item=source_item,
            requested_quantity=requested_quantity,
            from_wholesale=True,  # ❌ Always hardcoded to True
            status="pending",
            created_at=timezone.now()
        )
```

**After**:
```python
elif request.method == "POST":
    logger.info(f"POST request received for transfer creation: {request.POST}")
    try:
        requested_quantity = int(request.POST.get("requested_quantity", 0))
        item_id = request.POST.get("item_id")
        from_wholesale = request.POST.get("from_wholesale", "false").lower() == "true"

        if not item_id or requested_quantity <= 0:
            return JsonResponse({"success": False, "message": "Invalid input provided."}, status=400)

        # Get the source item based on transfer direction
        if from_wholesale:
            # Wholesale requesting from Retail (Retail → Wholesale transfer)
            source_item = get_object_or_404(Item, id=item_id)
            if source_item.stock < requested_quantity:
                return JsonResponse({"success": False, "message": f"Insufficient stock. Available: {source_item.stock}"}, status=400)
                
            transfer = TransferRequest.objects.create(
                retail_item=source_item,
                requested_quantity=requested_quantity,
                from_wholesale=True,
                status="pending",
                created_at=timezone.now()
            )
            logger.info(f"Created transfer request: Retail→Wholesale ({source_item.name} x{requested_quantity})")
        else:
            # Retail requesting from Wholesale (Wholesale → Retail transfer)
            source_item = get_object_or_404(WholesaleItem, id=item_id)
            if source_item.stock < requested_quantity:
                return JsonResponse({"success": False, "message": f"Insufficient stock. Available: {source_item.stock}"}, status=400)
                
            transfer = TransferRequest.objects.create(
                wholesale_item=source_item,
                requested_quantity=requested_quantity,
                from_wholesale=False,
                status="pending",
                created_at=timezone.now()
            )
            logger.info(f"Created transfer request: Wholesale→Retail ({source_item.name} x{requested_quantity})")
```

### 2. pharmapp/wholesale/views.py
**Function**: `create_transfer_request` (lines 3677-3705)

**Changes**:
- Updated comments to correctly reflect transfer direction
- Added stock validation before creating transfer
- Improved logging messages for clarity

**After**:
```python
# Get the source item based on transfer direction
if from_wholesale:
    # Wholesale requesting from Retail (Retail → Wholesale transfer)
    source_item = get_object_or_404(Item, id=item_id)
    if source_item.stock < requested_quantity:
        return JsonResponse({"success": False, "message": f"Insufficient stock. Available: {source_item.stock}"}, status=400)
        
    transfer = TransferRequest.objects.create(
        retail_item=source_item,
        requested_quantity=requested_quantity,
        from_wholesale=True,
        status="pending",
        created_at=timezone.now()
    )
    logger.info(f"Created transfer request: Retail→Wholesale ({source_item.name} x{requested_quantity})")
else:
    # Retail requesting from Wholesale (Wholesale → Retail transfer)
    source_item = get_object_or_404(WholesaleItem, id=item_id)
    if source_item.stock < requested_quantity:
        return JsonResponse({"success": False, "message": f"Insufficient stock. Available: {source_item.stock}"}, status=400)
        
    transfer = TransferRequest.objects.create(
        wholesale_item=source_item,
        requested_quantity=requested_quantity,
        from_wholesale=False,
        status="pending",
        created_at=timezone.now()
    )
    logger.info(f"Created transfer request: Wholesale→Retail ({source_item.name} x{requested_quantity})")
```

## Improvements Made

### 1. Proper Direction Handling ✅
- Both views now correctly handle transfer direction based on `from_wholesale` parameter
- Correct model fields are populated based on direction

### 2. Stock Validation ✅
- Added stock availability check before creating transfer request
- Returns clear error message if insufficient stock

### 3. Better Error Handling ✅
- Added logging for debugging
- Improved error messages
- Proper exception handling for AJAX and regular requests

### 4. Correct Model Field Assignment ✅
- `from_wholesale=True`: Sets `retail_item` (wholesale requesting from retail)
- `from_wholesale=False`: Sets `wholesale_item` (retail requesting from wholesale)

### 5. Clear Logging ✅
- Log messages now clearly indicate direction: "Retail→Wholesale" or "Wholesale→Retail"
- Includes item name and quantity for easy debugging

## Testing Checklist

### Wholesale → Retail Transfer
- [ ] Navigate to `/transfer/create/` (retail view)
- [ ] Search for wholesale items
- [ ] Select a wholesale item
- [ ] Enter quantity (less than available stock)
- [ ] Submit form
- [ ] Verify: Success message only (no error)
- [ ] Verify: Transfer request created with `from_wholesale=False`
- [ ] Verify: `wholesale_item` field is set

### Retail → Wholesale Transfer
- [ ] Navigate to `/transfer_wholesale/` (wholesale view)
- [ ] Search for retail items
- [ ] Select a retail item
- [ ] Enter quantity (less than available stock)
- [ ] Submit form
- [ ] Verify: Success message only (no error)
- [ ] Verify: Transfer request created with `from_wholesale=True`
- [ ] Verify: `retail_item` field is set

### Stock Validation
- [ ] Try to request more than available stock
- [ ] Verify: Error message shows available quantity
- [ ] Verify: Transfer request is NOT created

## URLs Reference

### Retail URLs (store app)
- Create transfer request: `/transfer/create/` → `create_transfer_request_wholesale`
- Pending requests: `/pending_transfer_requests/` → `pending_transfer_requests`
- Approve transfer: `/transfer/approve/<id>/` → `approve_transfer`
- Reject transfer: `/transfer/reject/<id>/` → `reject_transfer`

### Wholesale URLs (wholesale app)
- Create transfer request: `/transfer_wholesale/` → `create_transfer_request`
- Pending requests: `/wholesale_pending_transfer_requests/` → `pending_wholesale_transfer_requests`
- Approve transfer: `/wholesale/approve/<id>/` → `wholesale_approve_transfer`
- Reject transfer: `/transfer/reject/<id>/` → `reject_wholesale_transfer`

## Expected Behavior

### Before Fix
- ❌ Both success and error messages appeared
- ❌ Wrong transfer direction was created
- ❌ Retail requesting from wholesale created `from_wholesale=True` (incorrect)
- ❌ No stock validation

### After Fix
- ✅ Only success message appears on successful creation
- ✅ Only error message appears on failure
- ✅ Correct transfer direction is created
- ✅ Retail requesting from wholesale creates `from_wholesale=False` (correct)
- ✅ Wholesale requesting from retail creates `from_wholesale=True` (correct)
- ✅ Stock validation prevents over-requesting
- ✅ Clear error messages guide users

