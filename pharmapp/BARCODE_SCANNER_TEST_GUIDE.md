# Barcode Scanner Testing Guide

## Prerequisites
✅ Server is running on http://127.0.0.1:8000
✅ You are logged in to the system
✅ Browser console is open (Press F12)

---

## Test 1: Retail Dispensing (/dispense/)

### Steps:
1. Navigate to: http://127.0.0.1:8000/dispense/
2. Look for "Scan" button next to the search input
3. Click the "Scan" button
4. Modal should open with title "Scan Barcode or QR Code"

### Expected Console Logs:
```
[Barcode Scanner] Loading module...
[Barcode Scanner] Module loaded successfully - Html5Qrcode library available
[Scanner Modal] Script loading...
[Scanner Modal] Initializing script...
[Scanner Modal] All elements found, setting up event listeners...
[Scanner Modal] Script loaded and ready
[Scanner Modal] Modal opened in retail mode
[Scanner Modal] BarcodeScanner class available: true
[Scanner Modal] Html5Qrcode library available: true
[Scanner Modal] Initialized successfully in retail mode
```

5. Click "Start Camera" button
6. When browser asks for camera permission, click "Allow"

### Expected Result:
- ✅ Camera starts and shows live video feed
- ✅ Black preview area is replaced with camera view
- ✅ "Start Camera" button changes to "Stop Camera"
- ✅ Status shows "Camera ready - point at barcode"

### Test Scanning:
7. Point camera at a barcode
8. System should automatically scan and lookup the item
9. If item exists: Shows item details and fills search field
10. If item doesn't exist: Shows "Item not found for barcode: XXXXX"

**Status: [ ] PASS  [ ] FAIL**  
**Notes:** _________________________

---

## Test 2: Wholesale Dispensing (/wholesale/dispense/)

### Steps:
1. Navigate to: http://127.0.0.1:8000/wholesale/dispense/
2. Look for "Scan" button next to the search input
3. Click the "Scan" button
4. Modal should open

### Expected Console Logs:
```
[Scanner Modal] Modal opened in wholesale mode
[Scanner Modal] BarcodeScanner class available: true
[Scanner Modal] Html5Qrcode library available: true
[Scanner Modal] Initialized successfully in wholesale mode
```

5. Click "Start Camera"
6. Allow camera permission

### Expected Result:
- ✅ Camera starts successfully
- ✅ Can scan barcodes
- ✅ Searches in wholesale items

**Status: [ ] PASS  [ ] FAIL**  
**Notes:** _________________________

---

## Test 3: Retail Inventory - Add Item (/store/)

### Steps:
1. Navigate to: http://127.0.0.1:8000/store/
2. Click "Add Item" button
3. Modal opens with add item form
4. Look for barcode field with a scan icon button
5. Click the scan icon button
6. Barcode scanner modal should open

### Expected Console Logs:
```
[Scanner Modal] Modal opened in retail mode
```

7. Click "Start Camera"
8. Scan a barcode

### Expected Result:
- ✅ Camera starts
- ✅ After scanning, barcode is filled into the barcode field in the add item form
- ✅ Scanner modal closes automatically

**Status: [ ] PASS  [ ] FAIL**  
**Notes:** _________________________

---

## Test 4: Retail Inventory - Edit Item (/store/)

### Steps:
1. Navigate to: http://127.0.0.1:8000/store/
2. Click "Edit" on any item in the inventory list
3. Edit modal opens
4. Look for barcode field with scan icon
5. Click the scan icon
6. Scanner modal opens

7. Click "Start Camera"
8. Scan a barcode

### Expected Result:
- ✅ Camera starts
- ✅ Scanned barcode fills the barcode field
- ✅ Scanner modal closes

**Status: [ ] PASS  [ ] FAIL**  
**Notes:** _________________________

---

## Test 5: Wholesale Inventory - Add Item (/wholesales/)

### Steps:
1. Navigate to: http://127.0.0.1:8000/wholesales/
2. Click "Add Item" button
3. Add wholesale item modal opens
4. Find barcode field with scan icon
5. Click scan icon
6. Scanner modal opens

### Expected Console Logs:
```
[Scanner Modal] Modal opened in wholesale mode
```

7. Click "Start Camera"
8. Scan barcode

### Expected Result:
- ✅ Camera starts
- ✅ Barcode fills into form
- ✅ Modal closes after scan

**Status: [ ] PASS  [ ] FAIL**  
**Notes:** _________________________

---

## Test 6: Wholesale Inventory - Edit Item (/wholesales/)

### Steps:
1. Navigate to: http://127.0.0.1:8000/wholesales/
2. Click "Edit" on any wholesale item
3. Edit modal opens
4. Click scan icon for barcode field
5. Scanner modal opens
6. Click "Start Camera"
7. Scan barcode

### Expected Result:
- ✅ Camera starts
- ✅ Barcode updates in form
- ✅ Modal closes

**Status: [ ] PASS  [ ] FAIL**  
**Notes:** _________________________

---

## Common Issues & Solutions

### Issue: "Scanner not initialized"
**Solution:** Close and reopen the modal

### Issue: "Camera permission denied"
**Solution:** 
1. Click the camera icon in browser address bar
2. Allow camera access
3. Refresh page and try again

### Issue: "Barcode scanner library not loaded"
**Solution:** Hard refresh the page (Ctrl + Shift + R)

### Issue: Camera shows but doesn't scan
**Solution:** 
1. Ensure barcode is clear and well-lit
2. Hold steady for 1-2 seconds
3. Try different angles

### Issue: "Item not found"
**Solution:** The barcode doesn't exist in your database
1. Add the item first with a barcode
2. Or manually enter the barcode number in the form

---

## Alternative Testing Methods

### Manual Entry (No Camera):
1. Open scanner modal
2. Scroll down to "Or enter barcode manually:"
3. Type a barcode number
4. Click "Lookup"
5. Should search and find the item (or show not found)

### Image Upload:
1. Open scanner modal
2. Scroll to "Or upload barcode image:"
3. Click "Choose File"
4. Select an image of a barcode
5. System should scan the image

---

## Success Criteria

✅ All 6 tests pass
✅ Camera starts on all pages
✅ Barcodes can be scanned
✅ Error messages are clear and helpful
✅ No console errors (except 404 for non-existent barcodes)

---

## Report Results

After testing, please report:
1. Which tests passed/failed
2. Any console errors encountered
3. Screenshots of any issues
4. Browser and OS information

