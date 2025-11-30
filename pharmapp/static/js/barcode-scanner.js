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
        this.scanCooldown = 100; // Ultra-fast: 0.1 second cooldown
        this.isProcessing = false; // Flag to prevent processing multiple scans simultaneously

        // Performance optimization: cache for recently scanned items
        this.recentlyScanned = new Map(); // barcode -> {item, timestamp}
        this.recentScanCacheTimeout = 60000; // 60 seconds cache for better offline performance
        
        // Fast scan mode optimization
        this.fastScanMode = options.fastScanMode || false;  // Initialize fast mode if specified
        
        // Ultra-fast configuration - optimized for speed
        this.config = {
            fps: 60,  // Maximum frame rate for fastest detection
            qrbox: 250,  // Fixed size for faster processing (instead of dynamic calculation)
            aspectRatio: 1.0,  // 1:1 for simpler processing
            // Only scan most common formats for speed
            formatsToSupport: [
                Html5QrcodeSupportedFormats.QR_CODE,
                Html5QrcodeSupportedFormats.EAN_13,
                Html5QrcodeSupportedFormats.CODE_128,
                Html5QrcodeSupportedFormats.UPC_A
            ],
            // Minimal experimental features for maximum speed
            disableFlip: true,  // No horizontal flip - saves processing
            rememberSelection: true,
            videoConstraints: {
                facingMode: "environment",
                advanced: [{ zoom: 1.0 }]
            }
        };

        // Add advanced scanning options for better sensitivity
        // Using 'ideal' instead of 'min' to make it more forgiving
        this.advancedScanOptions = {
            videoConstraints: {
                facingMode: { ideal: 'environment' },
                width: { ideal: 1280 },      // Reasonable resolution
                height: { ideal: 720 },
                frameRate: { ideal: 30 }     // Standard framerate
            }
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
     * Set scan mode (fast/slow)
     * @param {boolean} mode - true for fast mode, false for normal mode
     */
    setFastScanMode(mode) {
        this.fastScanMode = mode;
        console.log('[Barcode Scanner] Fast scan mode:', mode ? 'enabled' : 'disabled');
    }

    /**
     * Request camera permission
     */
    requestCameraPermission() {
        return new Promise((resolve, reject) => {
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: 'environment',
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    }
                })
                .then(stream => {
                    console.log('[Barcode Scanner] Camera permission granted');
                    // Stop the stream immediately as Html5Qrcode will request it again
                    stream.getTracks().forEach(track => track.stop());
                    resolve(stream);
                })
                .catch(error => {
                    console.error('[Barcode Scanner] Camera permission denied:', error);
                    reject(error);
                });
            } else {
                const error = new Error('Camera API not available in this browser');
                console.error('[Barcode Scanner]', error.message);
                reject(error);
            }
        });
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
     * Start camera scanning with retry logic
     */
    async startScanning() {
        console.log('[Barcode Scanner] ===== START SCANNING CALLED =====');
        console.log('[Barcode Scanner] Current scanning status:', this.isScanning);

        if (this.isScanning) {
            console.warn('[Barcode Scanner] Already scanning');
            return;
        }

        const maxRetries = 10;
        const fixedDelay = 1000; // 1 second fixed delay

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

                // Fixed 1 second delay between retries
                console.log(`[Barcode Scanner] Retrying in ${fixedDelay}ms... (${attempt + 1}/${maxRetries})`);
                
                // Show retry status to user
                this.showStatus(`Camera start failed, retrying... (${attempt + 1}/${maxRetries})`, fixedDelay);
                
                // Wait before retrying
                await new Promise(resolve => setTimeout(resolve, fixedDelay));
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
            
            // Use cached item directly, skip API request
            this.onSuccess(cachedScan.item, decodedText);
            
            const scanTime = performance.now() - scanStartTime;
            console.log(`[Barcode Scanner] Cache hit processed in ${scanTime.toFixed(2)}ms`);
            
            // Performance monitoring - track scan times
            this.trackScanPerformance(decodedText, scanTime, 'cache_hit');
            
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
                    
                    // Track performance for successful API request
                    this.trackScanPerformance(decodedText, performance.now() - scanStartTime, 'api_request');
                }
            })
            .catch(error => {
                // Track performance for failed API request
                this.trackScanPerformance(decodedText, performance.now() - scanStartTime, 'scan_error');
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
     * Look up barcode in database (online/offline) with enhanced retry logic
     */
    async lookupBarcode(barcode, retryCount = 0) {
        const maxRetries = 1;
        const retryDelay = Math.min(1000 * Math.pow(2, retryCount), 5000); // Exponential backoff, max 5s

        try {
            // Try online API first
            if (navigator.onLine) {
                console.log(`[Barcode Scanner] Online lookup attempt ${retryCount + 1}/${maxRetries + 1}`);
                
                const response = await fetch('/api/barcode/lookup/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify({
                        barcode: barcode,
                        mode: this.mode
                    }),
                    // Add timeout to prevent hanging requests
                    signal: AbortSignal.timeout(3000) // 3 second timeout
                });

                if (response.ok) {
                    const data = await response.json();
                    console.log('[Barcode Scanner] Item found online:', data.item);
                    this.onSuccess(data.item, barcode);
                    return;
                }

                // If item not found (404), offer to add new item
                if (response.status === 404) {
                    console.log('[Barcode Scanner] Item not found online, trying offline...');
                    const offlineItem = await this.lookupBarcodeOffline(barcode);
                    if (offlineItem) {
                        this.onSuccess(offlineItem, barcode);
                        return;
                    }
                    
                    // Item not found anywhere - trigger add item flow
                    console.log('[Barcode Scanner] Item not found anywhere, triggering add item flow');
                    this.onItemNotFound(barcode);
                    return;
                }

                // Network error - retry if possible
                if (!response.ok && retryCount < maxRetries) {
                    console.log(`[Barcode Scanner] Network error, retrying in ${retryDelay}ms...`);
                    this.showStatus(`Network error, retrying... (${retryCount + 1}/${maxRetries})`, 2000);
                    await new Promise(resolve => setTimeout(resolve, retryDelay));
                    return this.lookupBarcode(barcode, retryCount + 1);
                }

            } else {
                // Offline mode - search IndexedDB
                console.log('[Barcode Scanner] Offline mode, searching IndexedDB...');
                const offlineItem = await this.lookupBarcodeOffline(barcode);
                if (offlineItem) {
                    this.onSuccess(offlineItem, barcode);
                    return;
                }
                
                // Item not found offline - queue for when back online or offer to add
                console.log('[Barcode Scanner] Item not found offline, queuing for later or add new');
                this.onItemNotFoundOffline(barcode);
                return;
            }

            // If we get here, all attempts failed
            this.showError(`Unable to find item for barcode: ${barcode}`);
            this.onError(new Error('Item not found after all attempts'), barcode);

        } catch (error) {
            console.error('[Barcode Scanner] Lookup error:', error);

            // Handle different error types
            if (error.name === 'AbortError') {
                console.log('[Barcode Scanner] Request timed out');
                if (retryCount < maxRetries) {
                    console.log(`[Barcode Scanner] Timeout, retrying in ${retryDelay}ms...`);
                    this.showStatus(`Request timeout, retrying... (${retryCount + 1}/${maxRetries})`, 2000);
                    await new Promise(resolve => setTimeout(resolve, retryDelay));
                    return this.lookupBarcode(barcode, retryCount + 1);
                }
            } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
                console.log('[Barcode Scanner] Network error, trying offline fallback');
                // Try offline as fallback for network errors
                try {
                    const offlineItem = await this.lookupBarcodeOffline(barcode);
                    if (offlineItem) {
                        this.onSuccess(offlineItem, barcode);
                        return;
                    }
                } catch (offlineError) {
                    console.error('[Barcode Scanner] Offline lookup also failed:', offlineError);
                }
            }

            this.showError('Failed to lookup barcode: ' + error.message);
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
     * Handle item not found (online mode) - trigger add item flow
     */
    onItemNotFound(barcode) {
        console.log('[Barcode Scanner] Item not found, showing add item modal');
        
        // Try to use the global add item modal if available
        if (typeof window.showAddItemModal === 'function') {
            window.showAddItemModal(barcode, this.mode);
        } else {
            // Fallback to prompt or create modal dynamically
            this.showAddItemDialog(barcode);
        }
    }

    /**
     * Handle item not found (offline mode) - queue for later or offer to add
     */
    onItemNotFoundOffline(barcode) {
        console.log('[Barcode Scanner] Item not found offline');
        
        // Add to pending items queue for when back online
        if (window.dbManager) {
            this.queueBarcodeForLater(barcode);
        }
        
        // Also offer to add item offline if supported
        if (typeof window.showAddItemModal === 'function') {
            window.showAddItemModal(barcode, this.mode, true); // true = offline mode
        } else {
            this.showAddItemDialog(barcode, true);
        }
    }

    /**
     * Queue barcode for later processing when back online
     */
    async queueBarcodeForLater(barcode) {
        try {
            if (!window.dbManager) {
                console.warn('[Barcode Scanner] Cannot queue barcode: IndexedDB not available');
                return;
            }

            const queuedItem = {
                id: Date.now(), // Temporary ID
                barcode: barcode,
                mode: this.mode,
                action: 'lookup_when_online',
                timestamp: new Date().toISOString(),
                status: 'pending'
            };

            await window.dbManager.add('pendingActions', queuedItem);
            console.log('[Barcode Scanner] Barcode queued for later processing:', barcode);
            this.showStatus('Item queued for when back online', 3000);
        } catch (error) {
            console.error('[Barcode Scanner] Failed to queue barcode:', error);
        }
    }

    /**
     * Show add item dialog (fallback when modal not available)
     */
    showAddItemDialog(barcode, isOffline = false) {
        const message = isOffline 
            ? `Item not found for barcode: ${barcode}\n\nWould you like to:\n1. Add this item now (offline)\n2. Queue for when back online\n3. Cancel`
            : `Item not found for barcode: ${barcode}\n\nWould you like to add this item to inventory?`;

        // Show a user-friendly dialog instead of navigating directly
        this.showAddItemDialog(barcode, isOffline);

        // Don't navigate directly - the add_item view requires POST and authentication
    }

    /**
     * Handle offline item creation
     */
    async queueOfflineItemCreation(barcode) {
        try {
            // Create a basic item structure that user can complete later
            const offlineItem = {
                id: `offline_${Date.now()}`,
                barcode: barcode,
                name: `New Item - ${barcode}`,
                mode: this.mode,
                action: 'create_item',
                timestamp: new Date().toISOString(),
                status: 'pending_completion',
                required_fields: ['name', 'cost', 'stock']
            };

            await window.dbManager.add('pendingActions', offlineItem);
            this.showSuccess('Item queued for completion when online. Please complete item details.');
        } catch (error) {
            console.error('[Barcode Scanner] Failed to queue offline item:', error);
            this.showError('Failed to queue item for offline creation');
        }
    }

    /**
     * Show status message (enhanced)
     */
    showStatus(message, duration = 1000) {
        console.log('[Barcode Scanner]', message);

        // Try to use offline handler if available
        if (window.offlineHandler && window.offlineHandler.showInAppNotification) {
            window.offlineHandler.showInAppNotification(
                'Scanner Status',
                message,
                'info'
            );
        } else {
            // Create temporary status indicator
            const existingStatus = document.getElementById('scanner-status');
            if (existingStatus) {
                existingStatus.remove();
            }

            const statusDiv = document.createElement('div');
            statusDiv.id = 'scanner-status';
            statusDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #17a2b8;
                color: white;
                padding: 10px 15px;
                border-radius: 5px;
                font-size: 14px;
                z-index: 9999;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            `;
            statusDiv.textContent = message;
            document.body.appendChild(statusDiv);

            setTimeout(() => {
                if (statusDiv.parentNode) {
                    statusDiv.parentNode.removeChild(statusDiv);
                }
            }, duration);
        }
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
     * Track scan performance metrics
     */
    trackScanPerformance(barcode, scanTime, source = 'scan') {
        // Store performance data
        const performanceData = {
            barcode: barcode,
            scanTime: scanTime,
            source: source,  // 'cache_hit', 'api_request', 'scan_error'
            timestamp: Date.now()
        };
        
        // Log to console for debugging
        console.log(`[Barcode Scanner] Performance: ${source} - ${scanTime.toFixed(2)}ms for barcode ${barcode}`);
        
        // Store in performance array for analysis
        if (!this.performanceMetrics) {
            this.performanceMetrics = [];
        }
        
        this.performanceMetrics.push(performanceData);
        
        // Keep only last 50 metrics to prevent memory issues
        if (this.performanceMetrics.length > 50) {
            this.performanceMetrics = this.performanceMetrics.slice(-50);
        }
        
        // Check for performance issues
        this.checkPerformanceThresholds(performanceData);
    }
    
    /**
     * Check if performance meets acceptable thresholds
     */
    checkPerformanceThresholds(performanceData) {
        const thresholds = {
            cache_hit: 100,     // ms
            api_request: 500,  // ms
            scan_error: 1000     // ms
        };
        
        const threshold = thresholds[performanceData.source] || 1000;
        
        if (performanceData.scanTime > threshold) {
            console.warn(`[Barcode Scanner] SLOW SCAN: ${performanceData.scanTime.toFixed(2)}ms > ${threshold}ms threshold`);
        }
    }
    
    /**
     * Get performance statistics
     */
    getPerformanceStats() {
        if (!this.performanceMetrics || this.performanceMetrics.length === 0) {
            return null;
        }
        
        const recentMetrics = this.performanceMetrics.slice(-10);  // Last 10 scans
        
        const avgScanTime = recentMetrics.reduce((sum, metric) => sum + metric.scanTime, 0) / recentMetrics.length;
        const cacheHits = recentMetrics.filter(m => m.source === 'cache_hit').length;
        
        return {
            averageScanTime: avgScanTime,
            cacheHitRate: (cacheHits / recentMetrics.length) * 100,
            totalScans: this.performanceMetrics.length
        };
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
