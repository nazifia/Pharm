# Hardware Barcode Scanner Integration Guide

## Overview

Your PharmApp now supports **BOTH** scanning methods:
1. **Camera-based scanning** (existing) - Uses phone/webcam camera
2. **Hardware barcode scanners** (new) - USB/Bluetooth handheld devices

## How Hardware Scanners Work

Physical barcode scanners (USB/Bluetooth) act as **keyboard input devices**:
- When you scan a barcode, the device "types" the barcode value
- Usually adds an **Enter key** at the end
- Input is **very fast** (< 50ms between characters)
- No special drivers needed - works like a keyboard

## Supported Scanner Types

✅ **USB Barcode Scanners** (Plug & Play)
✅ **Bluetooth Barcode Scanners** (Paired to computer/tablet)
✅ **2D QR Code Scanners** (Reads both barcodes and QR codes)
✅ **Wireless Scanners** (2.4GHz dongles)

### Recommended Devices

**Budget Option ($20-50):**
- Symcode 1D Barcode Scanner USB
- Netum Wireless Barcode Scanner
- TaoTronics TT-BS030

**Professional Option ($50-150):**
- Honeywell Voyager 1200g (USB)
- Zebra DS2208 (2D scanner, reads QR codes)
- Datalogic QuickScan QD2430 (2D)

**Wireless Option ($80-200):**
- Tera Wireless Barcode Scanner
- Zebra DS4308-SR (Bluetooth)
- Socket Mobile S700 (Bluetooth)

## Integration Steps

### Step 1: Add Hardware Scanner Script

Add this to your dispense templates **AFTER** the barcode-scanner.js script:

```html
<!-- Existing camera scanner -->
<script src="{% static 'js/barcode-scanner.js' %}"></script>

<!-- NEW: Hardware scanner support -->
<script src="{% static 'js/hardware-scanner.js' %}"></script>
```

### Step 2: Initialize Hardware Scanner

Add this JavaScript initialization:

```javascript
<script>
// Initialize hardware scanner
let hardwareScanner;

document.addEventListener('DOMContentLoaded', function() {
    // Determine mode based on current page
    const mode = window.location.pathname.includes('wholesale') ? 'wholesale' : 'retail';

    // Create hardware scanner instance
    hardwareScanner = new HardwareScannerHandler({ mode: mode });

    // Initialize scanner
    hardwareScanner.init();

    console.log('Hardware scanner ready!');
});

// Optional: Disable hardware scanner when camera scanner is active
function onCameraScannerStart() {
    if (hardwareScanner) {
        hardwareScanner.disable();
    }
}

function onCameraScannerStop() {
    if (hardwareScanner) {
        hardwareScanner.enable();
    }
}
</script>
```

### Step 3: Update Your Templates

#### For Retail Dispense (templates/store/dispense.html)

Add after line 660 (after existing barcode scanner initialization):

```html
<!-- Hardware Scanner Support -->
<script src="{% static 'js/hardware-scanner.js' %}"></script>
<script>
    // Initialize hardware scanner for retail
    let hardwareScanner = new HardwareScannerHandler({ mode: 'retail' });
    hardwareScanner.init();

    // Disable hardware scanner when camera modal is open
    $('#barcodeScannerModal').on('shown.bs.modal', function() {
        if (hardwareScanner) hardwareScanner.disable();
    });

    $('#barcodeScannerModal').on('hidden.bs.modal', function() {
        if (hardwareScanner) hardwareScanner.enable();
    });
</script>
```

#### For Wholesale Dispense (templates/wholesale/dispense_wholesale.html)

Add similar code with `mode: 'wholesale'`:

```html
<!-- Hardware Scanner Support -->
<script src="{% static 'js/hardware-scanner.js' %}"></script>
<script>
    // Initialize hardware scanner for wholesale
    let hardwareScanner = new HardwareScannerHandler({ mode: 'wholesale' });
    hardwareScanner.init();

    // Disable hardware scanner when camera modal is open
    $('#barcodeScannerModal').on('shown.bs.modal', function() {
        if (hardwareScanner) hardwareScanner.disable();
    });

    $('#barcodeScannerModal').on('hidden.bs.modal', function() {
        if (hardwareScanner) hardwareScanner.enable();
    });
</script>
```

## Usage

### For Camera Scanning (Existing)
1. Click "Scan Barcode" button
2. Point camera at barcode/QR code
3. Item automatically found and added to search results

### For Hardware Scanner (New)
1. **Just scan!** No button click needed
2. Point scanner at barcode
3. Press trigger button on scanner
4. Item automatically found and added to search results

## Configuration Options

You can customize the hardware scanner:

```javascript
let hardwareScanner = new HardwareScannerHandler({
    mode: 'retail',                // 'retail' or 'wholesale'
    scannerSpeed: 50,              // Max ms between chars (default: 50)
    minBarcodeLength: 3,           // Minimum barcode length (default: 3)
    maxBarcodeLength: 50,          // Maximum barcode length (default: 50)
});
```

## How It Works

### Detection Logic

The hardware scanner detects rapid keyboard input:

1. **Fast Input Detection** - If characters arrive < 50ms apart, it's likely a scanner
2. **Buffer Accumulation** - Builds complete barcode string
3. **Enter Key Trigger** - Processes barcode when Enter is pressed
4. **Automatic Lookup** - Calls same API as camera scanner
5. **Result Display** - Uses same callback (`window.onBarcodeItemFound`)

### Input Protection

The system intelligently ignores scanner input when:
- User is typing in text fields (except search field)
- User is filling forms
- Hardware scanner is manually disabled

### Offline Support

Hardware scanners work offline using the same IndexedDB cache:
- Searches IndexedDB when offline
- Supports PharmApp QR codes (`PHARM-RETAIL-123`)
- Supports standard UPC/EAN barcodes

## Testing

### Without Physical Scanner

Simulate hardware scanner input:
1. Focus on the dispense page (not in any input field)
2. Type a barcode quickly (e.g., "123456789")
3. Press Enter
4. Should trigger lookup

### With Physical Scanner

1. Connect USB scanner (no driver needed)
2. Go to dispense page
3. Scan any barcode
4. Should automatically lookup and display item

## Troubleshooting

### Scanner Not Working

**Problem:** Nothing happens when I scan
**Solution:**
- Check scanner is properly connected (USB light should be on)
- Ensure page is focused (click anywhere on page first)
- Verify scanner is configured to send "Enter" after scan
- Check browser console for "[Hardware Scanner]" messages

**Problem:** Scanner types into wrong field
**Solution:**
- Click somewhere outside input fields before scanning
- The script automatically detects and handles this

**Problem:** Scanner triggers twice
**Solution:**
- Check scanner settings - may have "duplicate scan prevention" disabled
- Adjust `scannerSpeed` configuration if needed

### Performance Issues

**Problem:** Slow response
**Solution:**
- Check network connectivity
- Enable offline mode and sync data
- Clear browser cache

## Scanner Configuration

Most USB scanners can be configured using special barcodes from the manual:

**Common Settings to Configure:**
1. **Add Enter/Return suffix** - Scanner should send Enter key after barcode
2. **Disable prefix** - Remove any prefix characters
3. **Set to USB HID mode** - Standard keyboard emulation
4. **Disable beep** (optional) - For silent operation

Consult your scanner's manual for configuration barcodes.

## API Endpoints Used

The hardware scanner uses the same endpoints as camera scanner:

```
POST /api/barcode/lookup/
Body: {
    "barcode": "123456789",
    "mode": "retail"
}

Response: {
    "item": {
        "id": 1,
        "name": "Paracetamol",
        "price": 500,
        "stock": 100,
        ...
    }
}
```

## Security Notes

✅ **Safe** - No security issues with hardware scanners
✅ **Input Validation** - Barcode length checked (3-50 chars)
✅ **CSRF Protection** - All API calls include CSRF token
✅ **Offline First** - Works without internet

## Benefits

1. **Faster Operations** - No need to open camera modal
2. **Better Accuracy** - Hardware scanners rarely misread
3. **Ergonomic** - Handheld scanning is more comfortable
4. **Dual Mode** - Use camera OR hardware, whichever is convenient
5. **Professional** - More suitable for high-volume operations
6. **Offline Support** - Works without internet connection

## Next Steps

1. **Test with simulation** (typing + Enter)
2. **Purchase a hardware scanner** if needed
3. **Configure scanner** to add Enter suffix
4. **Train staff** on new capability
5. **Monitor performance** in production

## Support

For issues:
1. Check browser console for errors
2. Test with manual typing + Enter
3. Verify scanner configuration
4. Check CLAUDE.md for general guidance
