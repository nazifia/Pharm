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

        // Debouncing to prevent multiple scans of same barcode
        this.lastScannedCode = null;
        this.lastScanTime = 0;
        this.scanCooldown = 500; // Reduced to 0.5 second for faster scanning
        this.isProcessing = false; // Flag to prevent processing multiple scans simultaneously
        
        // Performance optimization: cache for recently scanned items
        this.recentlyScanned = new Map(); // barcode -> {item, timestamp}
        this.recentScanCacheTimeout = 30000; // 30 seconds cache
        
        // Optimized configuration for fast scanning
        this.config = {
            fps: 60,  // Increased to 60 FPS for faster detection
            qrbox: this.calculateQrBoxSize(),  // Dynamic sizing based on screen width
            aspectRatio: 1.777778,  // 16:9 for better camera utilization
            // Use formatsToSupport only if library is confirmed loaded
            formatsToSupport: this.getSupportedFormats()
        };
    }

    /**
     * Calculate responsive QR box size based on screen width
     */
    calculateQrBoxSize() {
        const width = window.innerWidth;
        if (width < 576) return { width: 200, height: 200 };  // Mobile
        if (width < 768) return { width: 250, height: 250 };  // Large mobile
        if (width < 992) return { width: 300, height: 300 };  // Tablet
        return { width: 350, height: 350 };  // Desktop
    }

    /**
     * Get supported barcode formats safely
     */
    getSupportedFormats() {
        if (typeof Html5QrcodeSupportedFormats === 'undefined') {
            console.warn('[Barcode Scanner] Html5QrcodeSupportedFormats not available, using defaults');
            return undefined;  // Let library use all default formats
        }

        return [
            Html5QrcodeSupportedFormats.QR_CODE,
            Html5QrcodeSupportedFormats.UPC_A,
            Html5QrcodeSupportedFormats.UPC_E,
            Html5QrcodeSupportedFormats.EAN_13,
            Html5QrcodeSupportedFormats.EAN_8,
            Html5QrcodeSupportedFormats.CODE_128,
            Html5QrcodeSupportedFormats.CODE_39,
        ];
    }

    /**
     * Get CSRF token from cookies
     */
    getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
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

            // Defensive checks for error properties to prevent undefined errors
            const errorName = error?.name || '';
            const errorMsg = error?.message || '';

            if (errorName === 'NotAllowedError' || errorMsg.includes('Permission')) {
                errorMessage += 'Camera access was denied. Please allow camera permissions and try again.';
            } else if (errorName === 'NotFoundError') {
                errorMessage += 'No camera found on this device.';
            } else if (errorName === 'NotReadableError') {
                errorMessage += 'Camera is already in use by another application.';
            } else if (errorMsg.includes('library not loaded')) {
                errorMessage += 'Barcode scanner library failed to load. Please refresh the page.';
            } else {
                errorMessage += errorMsg || 'Please check your camera permissions and try again.';
            }

            this.showError(errorMessage);
            throw error;
        }
    }

    /**
     * Start camera scanning with retry logic
     */
    async startScanning() {
        console.log('[Barcode Scanner] ===== START SCANNING CALLED =====');
        console.log('[Barcode Scanner] Current scanning status:', this.isScanning);

        if (this.isScanning) {
            console.warn('[Barcode Scanner] Already scanning');
            return;
        }

        const maxRetries = 3;
        const baseDelay = 1000; // 1 second base delay

        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                // Check if Html5Qrcode is available
                console.log('[Barcode Scanner] Checking if Html5Qrcode is available...');
                console.log('[Barcode Scanner] Html5Qrcode type:', typeof Html5Qrcode);

                if (typeof Html5Qrcode === 'undefined') {
                    console.error('[Barcode Scanner] Html5Qrcode library not loaded!');
                    throw new Error('Html5Qrcode library not loaded');
                }

                console.log('[Barcode Scanner] Html5Qrcode is available ✓');

                // Initialize scanner if not already initialized
                if (!this.scanner) {
                    const initialized = await this.init();
                    if (!initialized) {
                        throw new Error('Scanner initialization failed');
                    }
                }

                // Request camera permission
                console.log('[Barcode Scanner] ===== STARTING CAMERA =====');
                console.log('[Barcode Scanner] Scanner object:', this.scanner);
                console.log('[Barcode Scanner] Fast scan mode:', this.fastScanMode);
                console.log('[Barcode Scanner] Attempt:', attempt + 1, 'of', maxRetries + 1);

                // Use different configurations for retry attempts
                const cameraConfig = this.getCameraConfigForAttempt(attempt);
                const fastConfig = this.getScanConfigForAttempt(attempt);

                console.log('[Barcode Scanner] Camera config:', cameraConfig);
                console.log('[Barcode Scanner] Scan config:', fastConfig);
                console.log('[Barcode Scanner] Starting camera with optimized settings...');

                await this.scanner.start(
                    cameraConfig,
                    fastConfig,
                    this.onScanSuccess.bind(this),
                    this.onScanFailure.bind(this)
                );

                console.log('[Barcode Scanner] ✅ Camera started successfully');

                this.isScanning = true;
                console.log('[Barcode Scanner] ===== CAMERA STARTED SUCCESSFULLY =====');
                return; // Success, exit retry loop

            } catch (error) {
                console.error('[Barcode Scanner] ===== CAMERA START FAILED =====');
                console.error('[Barcode Scanner] Error name:', error?.name);
                console.error('[Barcode Scanner] Error message:', error?.message);
                console.error('[Barcode Scanner] Full error:', error);
                console.error('[Barcode Scanner] Attempt:', attempt + 1, 'of', maxRetries + 1);

                // Check if this is a non-retryable error
                if (this.isNonRetryableError(error)) {
                    const errorMessage = this.getErrorMessage(error);
                    this.showError(errorMessage);
                    throw error;
                }

                // If this was the last attempt, give up
                if (attempt === maxRetries) {
                    const errorMessage = this.getErrorMessage(error) + ' All retry attempts failed.';
                    this.showError(errorMessage);
                    throw error;
                }

                // Calculate delay with exponential backoff
                const delay = Math.min(baseDelay * Math.pow(2, attempt), 8000); // Max 8 seconds
                console.log(`[Barcode Scanner] Retrying in ${delay}ms... (${attempt + 1}/${maxRetries})`);
                
                // Show retry status to user
                this.showStatus(`Camera start failed, retrying... (${attempt + 1}/${maxRetries})`, delay);
                
                // Wait before retrying
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }

    /**
     * Get camera configuration for specific retry attempt
     */
    getCameraConfigForAttempt(attempt) {
        switch(attempt) {
            case 0: // First attempt - standard config
                return { facingMode: "environment" };
            case 1: // Second attempt - lower resolution
                return {
                    facingMode: "environment",
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                };
            case 2: // Third attempt - basic constraints only
                return { facingMode: { ideal: "environment" } };
            default: // Fallback - most basic
                return { facingMode: "environment" };
        }
    }

    /**
     * Get scan configuration for specific retry attempt
     */
    getScanConfigForAttempt(attempt) {
        const baseConfig = this.fastScanMode ? {
            ...this.config,
            // Fast mode optimizations
            disableFlip: true,
            focusDecoded: true,
            'try-harder': false,
            'zoom': 0.8,
            'showTorch': false,
            'showScanRegion': false,
            // Reduce timeouts for faster startup
            'timeout': 2000  // 2 seconds instead of 10
        } : this.config;

        // Apply additional constraints for retry attempts
        switch(attempt) {
            case 1: // Second attempt - more relaxed settings
                return {
                    ...baseConfig,
                    'timeout': 5000, // Increase timeout
                    'try-harder': true,
                    'zoom': 0.6
                };
            case 2: // Third attempt - maximum compatibility
                return {
                    ...baseConfig,
                    'timeout': 8000, // Even longer timeout
                    'try-harder': true,
                    'disableFlip': false, // Allow flipping
                    'formatsToSupport': [
                        Html5QrcodeSupportedFormats.QR_CODE,
                        Html5QrcodeSupportedFormats.EAN_13,
                        Html5QrcodeSupportedFormats.CODE_128
                    ] // Fewer formats for better detection
                };
            default:
                return baseConfig;
        }
    }

    /**
     * Check if error is non-retryable
     */
    isNonRetryableError(error) {
        const errorName = error?.name || '';
        const errorMsg = error?.message || '';

        return (
            errorName === 'NotAllowedError' || // Permission denied
            errorMsg.includes('Permission') ||
            errorName === 'NotFoundError' || // No camera found
            errorMsg.includes('library not loaded') || // Library issue
            errorName === 'SecurityError' || // Security restriction
            errorMsg.includes('not allowed')
        );
    }

    /**
     * Get user-friendly error message
     */
    getErrorMessage(error) {
        const errorName = error?.name || '';
        const errorMsg = error?.message || '';

        let errorMessage = 'Failed to start camera. ';

        if (errorName === 'NotAllowedError' || errorMsg.includes('Permission')) {
            errorMessage += 'Camera access was denied. Please allow camera permissions and try again.';
        } else if (errorName === 'NotFoundError') {
            errorMessage += 'No camera found on this device.';
        } else if (errorName === 'NotReadableError') {
            errorMessage += 'Camera is already in use by another application.';
        } else if (errorName === 'OverconstrainedError' || errorMsg.includes('Constraints')) {
            errorMessage += 'Camera does not support required configuration.';
        } else if (errorMsg.includes('library not loaded')) {
            errorMessage += 'Barcode scanner library failed to load. Please refresh the page.';
        } else {
            errorMessage += errorMsg || 'Please check your camera permissions and try again.';
        }

        return errorMessage;
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
     * Manual retry method for camera initialization
     */
    async retryCameraStart() {
        console.log('[Barcode Scanner] Manual retry requested');
        
        // Clear any existing scanner state
        if (this.scanner) {
            try {
                await this.scanner.stop();
            } catch (error) {
                console.log('[Barcode Scanner] Error stopping existing scanner:', error);
            }
        }
        
        // Reset scanner instance for clean retry
        this.scanner = null;
        this.isScanning = false;
        
        // Try to start scanning again
        return await this.startScanning();
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
        // Performance logging
        const scanStartTime = performance.now();
        
        // Debouncing - prevent processing same barcode multiple times rapidly
        const currentTime = Date.now();

        if (this.isProcessing) {
            console.log('[Barcode Scanner] Already processing a scan, skipping...');
            return;
        }

        // Check cache first for recently scanned items
        const cachedScan = this.recentlyScanned.get(decodedText);
        if (cachedScan && (currentTime - cachedScan.timestamp) < this.recentScanCacheTimeout) {
            console.log('[Barcode Scanner] Found in cache:', cachedScan.item);
            this.playSuccessBeep();
            this.flashSuccessIndicator();
            this.onSuccess(cachedScan.item, decodedText);
            
            const scanTime = performance.now() - scanStartTime;
            console.log(`[Barcode Scanner] Cache hit processed in ${scanTime.toFixed(2)}ms`);
            return;
        }

        if (this.lastScannedCode === decodedText &&
            (currentTime - this.lastScanTime) < this.scanCooldown) {
            console.log('[Barcode Scanner] Same barcode scanned too soon, ignoring');
            return;
        }

        // Mark as processing
        this.isProcessing = true;
        this.lastScannedCode = decodedText;
        this.lastScanTime = currentTime;

        console.log('[Barcode Scanner] Scanned:', decodedText);

        // Visual and audio feedback
        this.playSuccessBeep();
        this.flashSuccessIndicator();

        // Keep scanner running for continuous scanning
        // Lookup the barcode asynchronously without blocking the scanner
        this.lookupBarcode(decodedText)
            .then(item => {
                if (item) {
                    // Cache the successful lookup
                    this.recentlyScanned.set(decodedText, {
                        item: item,
                        timestamp: currentTime
                    });
                    
                    // Clean old cache entries
                    this.cleanExpiredCache();
                }
            })
            .finally(() => {
                // Reset processing flag immediately for faster response
                this.isProcessing = false;
                
                const scanTime = performance.now() - scanStartTime;
                console.log(`[Barcode Scanner] Scan processed in ${scanTime.toFixed(2)}ms`);
            });
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
                        'X-CSRFToken': this.getCsrfToken()
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
     * Clean expired entries from the scan cache
     */
    cleanExpiredCache() {
        const currentTime = Date.now();
        const expiredKeys = [];
        
        for (const [barcode, scanData] of this.recentlyScanned.entries()) {
            if (currentTime - scanData.timestamp > this.recentScanCacheTimeout) {
                expiredKeys.push(barcode);
            }
        }
        
        expiredKeys.forEach(key => this.recentlyScanned.delete(key));
        
        if (expiredKeys.length > 0) {
            console.log(`[Barcode Scanner] Cleaned ${expiredKeys.length} expired cache entries`);
        }
    }

    /**
     * Look up barcode or QR code in IndexedDB (offline) - optimized for performance
     */
    async lookupBarcodeOffline(barcode) {
        if (!window.dbManager) {
            console.error('[Barcode Scanner] IndexedDB not available');
            return null;
        }

        try {
            const storeName = this.mode === 'retail' ? 'items' : 'wholesaleItems';

            // Check if this is a PharmApp QR code
            const isQRCode = barcode.startsWith('PHARM-');

            let item = null;

            if (isQRCode) {
                // Parse QR code: PHARM-RETAIL-123 or PHARM-WHOLESALE-123
                const parts = barcode.split('-');
                if (parts.length === 3) {
                    const qrMode = parts[1].toLowerCase();
                    const itemId = parseInt(parts[2]);

                    // Verify mode matches
                    if (qrMode === this.mode) {
                        // Optimized: Try to get specific item by ID using index if available
                        try {
                            item = await window.dbManager.get(storeName, itemId);
                            if (item) {
                                console.log('[Barcode Scanner] Item found offline by QR code (optimized):', item);
                                return item;
                            }
                        } catch (indexError) {
                            // Fallback to search if index not available
                            console.log('[Barcode Scanner] Index lookup failed, falling back to search');
                        }
                        
                        // Fallback: search through all items
                        const allItems = await window.dbManager.getAll(storeName);
                        item = allItems.find(item => item.id === itemId);
                        if (item) {
                            console.log('[Barcode Scanner] Item found offline by QR code (fallback):', item);
                        }
                    } else {
                        console.warn(`[Barcode Scanner] QR code mode mismatch: ${qrMode} vs ${this.mode}`);
                    }
                }
            } else {
                // Optimized: Try to get item by barcode using index if available
                try {
                    item = await window.dbManager.getByIndex(storeName, 'barcode', barcode);
                    if (item) {
                        console.log('[Barcode Scanner] Item found offline by barcode (optimized):', item);
                        return item;
                    }
                } catch (indexError) {
                    // Fallback to search if index not available
                    console.log('[Barcode Scanner] Index lookup failed, falling back to search');
                }
                
                // Fallback: search through all items only if necessary
                const allItems = await window.dbManager.getAll(storeName);
                item = allItems.find(item => item.barcode === barcode);
                if (item) {
                    console.log('[Barcode Scanner] Item found offline by barcode (fallback):', item);
                }
            }

            if (!item) {
                console.log('[Barcode Scanner] Item not found in offline storage');
            }

            return item;

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
     * Play success beep sound
     */
    playSuccessBeep() {
        if (typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined') {
            try {
                const AudioCtx = window.AudioContext || window.webkitAudioContext;
                const audioCtx = new AudioCtx();
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();

                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);

                oscillator.frequency.value = 800;  // High pitch for success
                oscillator.type = 'sine';
                gainNode.gain.value = 0.3;

                oscillator.start(audioCtx.currentTime);
                oscillator.stop(audioCtx.currentTime + 0.1);
            } catch (e) {
                console.log('[Barcode Scanner] Audio feedback not available');
            }
        }
    }

    /**
     * Flash success indicator on scanner element
     */
    flashSuccessIndicator() {
        const scanner = document.getElementById(this.scannerId);
        if (scanner) {
            scanner.style.border = '5px solid #28a745';
            setTimeout(() => {
                scanner.style.border = '';
            }, 500);
        }
    }

    /**
     * Clear last scanned code to allow immediate re-scan
     * Useful when user wants to scan the same item again
     */
    clearLastScan() {
        this.lastScannedCode = null;
        this.lastScanTime = 0;
        this.isProcessing = false;
        this.recentlyScanned.clear(); // Clear cache for fresh start
        console.log('[Barcode Scanner] Scan history and cache cleared - ready for immediate re-scan');
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
