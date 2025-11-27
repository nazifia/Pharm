/**
 * Barcode Scanner Module
 * Handles barcode and QR-code scanning with offline support
 * Supports UPC, EAN-13, Code-128, and QR codes
 */

console.log('[Barcode Scanner] Loading module...');

class BarcodeScanner {
    constructor(options = {}) {
        this.scannerId = options.scannerId || 'barcode-scanner';
        this.mode = options.mode || 'retail'; // 'retail' or 'wholesale'
        this.onSuccess = options.onSuccess || this.defaultSuccessHandler;
        this.onError = options.onError || this.defaultErrorHandler;
        this.scanner = null;
        this.isScanning = false;

        // Safe configuration that works with or without Html5QrcodeSupportedFormats
        this.config = {
            fps: 10,
            qrbox: { width: 250, height: 250 },
            // Use formatsToSupport if available, otherwise rely on default formats
            ...(typeof Html5QrcodeSupportedFormats !== 'undefined' && {
                formatsToSupport: [
                    Html5QrcodeSupportedFormats.QR_CODE,
                    Html5QrcodeSupportedFormats.UPC_A,
                    Html5QrcodeSupportedFormats.UPC_E,
                    Html5QrcodeSupportedFormats.EAN_13,
                    Html5QrcodeSupportedFormats.EAN_8,
                    Html5QrcodeSupportedFormats.CODE_128,
                    Html5QrcodeSupportedFormats.CODE_39,
                ]
            })
        };
    }

    /**
     * Initialize the scanner
     */
    async init() {
        try {
            this.scanner = new Html5Qrcode(this.scannerId);
            console.log('[Barcode Scanner] Initialized successfully');
            return true;
        } catch (error) {
            console.error('[Barcode Scanner] Initialization error:', error);
            this.showError('Failed to initialize scanner');
            return false;
        }
    }

    /**
     * Start camera scanning
     */
    async startScanning() {
        if (this.isScanning) {
            console.warn('[Barcode Scanner] Already scanning');
            return;
        }

        try {
            // Check if Html5Qrcode is available
            if (typeof Html5Qrcode === 'undefined') {
                throw new Error('Html5Qrcode library not loaded');
            }

            // Initialize scanner if not already initialized
            if (!this.scanner) {
                const initialized = await this.init();
                if (!initialized) {
                    throw new Error('Scanner initialization failed');
                }
            }

            // Request camera permission explicitly
            console.log('[Barcode Scanner] Requesting camera permission...');

            // Start the scanner with proper configuration
            await this.scanner.start(
                { facingMode: "environment" }, // Use back camera on mobile
                this.config,
                this.onScanSuccess.bind(this),
                this.onScanFailure.bind(this)
            );

            this.isScanning = true;
            console.log('[Barcode Scanner] Camera started successfully');
        } catch (error) {
            console.error('[Barcode Scanner] Failed to start camera:', error);

            // Provide more specific error messages
            let errorMessage = 'Failed to start camera. ';
            if (error.name === 'NotAllowedError' || error.message.includes('Permission')) {
                errorMessage += 'Camera access was denied. Please allow camera permissions and try again.';
            } else if (error.name === 'NotFoundError') {
                errorMessage += 'No camera found on this device.';
            } else if (error.name === 'NotReadableError') {
                errorMessage += 'Camera is already in use by another application.';
            } else if (error.message.includes('library not loaded')) {
                errorMessage += 'Barcode scanner library failed to load. Please refresh the page.';
            } else {
                errorMessage += error.message || 'Please check your camera permissions and try again.';
            }

            this.showError(errorMessage);
            throw error;
        }
    }

    /**
     * Stop camera scanning
     */
    async stopScanning() {
        if (!this.isScanning || !this.scanner) {
            return;
        }

        try {
            await this.scanner.stop();
            this.isScanning = false;
            console.log('[Barcode Scanner] Camera stopped');
        } catch (error) {
            console.error('[Barcode Scanner] Failed to stop camera:', error);
        }
    }

    /**
     * Scan from image file
     */
    async scanFile(file) {
        try {
            const decodedText = await Html5Qrcode.scanFile(file, true);
            await this.onScanSuccess(decodedText);
        } catch (error) {
            console.error('[Barcode Scanner] File scan error:', error);
            this.showError('Could not read barcode from image');
        }
    }

    /**
     * Handle successful scan
     */
    async onScanSuccess(decodedText, decodedResult) {
        console.log('[Barcode Scanner] Scanned:', decodedText);

        // Stop scanning to prevent multiple reads
        if (this.isScanning) {
            await this.stopScanning();
        }

        // Lookup the barcode
        await this.lookupBarcode(decodedText);
    }

    /**
     * Handle scan failure (continuous, not an error)
     */
    onScanFailure(error) {
        // This is called continuously while scanning, so we don't log it
        // Only actual errors are logged
    }

    /**
     * Look up barcode in database (online/offline)
     */
    async lookupBarcode(barcode) {
        try {
            // Try online API first
            if (navigator.onLine) {
                const response = await fetch('/api/barcode/lookup/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        barcode: barcode,
                        mode: this.mode
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    console.log('[Barcode Scanner] Item found online:', data.item);
                    this.onSuccess(data.item, barcode);
                    return;
                }

                // If not found online, try offline
                if (response.status === 404) {
                    console.log('[Barcode Scanner] Item not found online, trying offline...');
                    const offlineItem = await this.lookupBarcodeOffline(barcode);
                    if (offlineItem) {
                        this.onSuccess(offlineItem, barcode);
                        return;
                    }
                }
            } else {
                // Offline mode - search IndexedDB
                console.log('[Barcode Scanner] Offline mode, searching IndexedDB...');
                const offlineItem = await this.lookupBarcodeOffline(barcode);
                if (offlineItem) {
                    this.onSuccess(offlineItem, barcode);
                    return;
                }
            }

            // Not found anywhere
            this.showError(`Item not found for barcode: ${barcode}`);
            this.onError(new Error('Item not found'), barcode);

        } catch (error) {
            console.error('[Barcode Scanner] Lookup error:', error);

            // Try offline as fallback
            try {
                const offlineItem = await this.lookupBarcodeOffline(barcode);
                if (offlineItem) {
                    this.onSuccess(offlineItem, barcode);
                    return;
                }
            } catch (offlineError) {
                console.error('[Barcode Scanner] Offline lookup also failed:', offlineError);
            }

            this.showError('Failed to lookup barcode');
            this.onError(error, barcode);
        }
    }

    /**
     * Look up barcode in IndexedDB (offline)
     */
    async lookupBarcodeOffline(barcode) {
        if (!window.dbManager) {
            console.error('[Barcode Scanner] IndexedDB not available');
            return null;
        }

        try {
            const storeName = this.mode === 'retail' ? 'items' : 'wholesaleItems';
            const allItems = await window.dbManager.getAll(storeName);

            // Find item with matching barcode
            const item = allItems.find(item => item.barcode === barcode);

            if (item) {
                console.log('[Barcode Scanner] Item found offline:', item);
                return item;
            }

            console.log('[Barcode Scanner] Item not found in offline storage');
            return null;

        } catch (error) {
            console.error('[Barcode Scanner] Offline lookup error:', error);
            return null;
        }
    }

    /**
     * Default success handler
     */
    defaultSuccessHandler(item, barcode) {
        console.log('[Barcode Scanner] Success:', item);
        alert(`Found: ${item.name}\nBarcode: ${barcode}\nPrice: ${item.price}`);
    }

    /**
     * Default error handler
     */
    defaultErrorHandler(error, barcode) {
        console.error('[Barcode Scanner] Error:', error);
    }

    /**
     * Show error message to user
     */
    showError(message) {
        console.error('[Barcode Scanner]', message);

        // Try to use offline handler if available
        if (window.offlineHandler && window.offlineHandler.showInAppNotification) {
            window.offlineHandler.showInAppNotification(
                'Barcode Scan Error',
                message,
                'error'
            );
        } else {
            // Fallback to alert
            alert(message);
        }
    }

    /**
     * Show success message to user
     */
    showSuccess(message) {
        console.log('[Barcode Scanner]', message);

        // Try to use offline handler if available
        if (window.offlineHandler && window.offlineHandler.showInAppNotification) {
            window.offlineHandler.showInAppNotification(
                'Barcode Scanned',
                message,
                'success'
            );
        }
    }

    /**
     * Clean up and destroy scanner
     */
    async destroy() {
        if (this.isScanning) {
            await this.stopScanning();
        }
        this.scanner = null;
        console.log('[Barcode Scanner] Destroyed');
    }
}

// Make BarcodeScanner available globally
window.BarcodeScanner = BarcodeScanner;

// Check if Html5Qrcode library is loaded
if (typeof Html5Qrcode !== 'undefined') {
    console.log('[Barcode Scanner] Module loaded successfully - Html5Qrcode library available');
} else {
    console.error('[Barcode Scanner] Module loaded but Html5Qrcode library NOT available!');
    console.error('[Barcode Scanner] Make sure html5-qrcode library is loaded before barcode-scanner.js');
}
