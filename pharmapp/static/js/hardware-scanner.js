/**
 * Hardware Barcode Scanner Support
 * Detects input from USB/Bluetooth barcode scanners and triggers lookups
 * Works alongside camera-based scanning
 */

console.log('[Hardware Scanner] Module loading...');

class HardwareScannerHandler {
    constructor(options = {}) {
        this.mode = options.mode || 'retail'; // 'retail' or 'wholesale'
        this.inputBuffer = '';
        this.lastInputTime = 0;
        this.scannerSpeed = 50; // Optimized to 50ms for faster USB scanners (Bluetooth may need adjustment)
        this.minBarcodeLength = 3; // Minimum barcode length
        this.maxBarcodeLength = 50; // Maximum barcode length
        this.enabled = true;
        this.inputTimeout = null;
        this.bufferProcessTimeout = 100; // Reduced to 100ms for faster processing
        this.statusIndicator = null;
        this.maxRetries = 3; // Increased retry attempts for better reliability

        // Performance optimization: cache for recently scanned items
        this.recentlyScanned = new Map(); // barcode -> {item, timestamp}
        this.recentScanCacheTimeout = 60000; // 60 seconds cache

        // Debouncing to prevent duplicate scans
        this.lastScannedBarcode = null;
        this.lastScanTimestamp = 0;
        this.duplicateScanThreshold = 300; // 0.3 seconds to prevent duplicate scans

        console.log(`[Hardware Scanner] Initialized for ${this.mode} mode`);
    }

    /**
     * Initialize hardware scanner listeners
     */
    init() {
        // Listen for keypress events globally
        document.addEventListener('keypress', this.handleKeyPress.bind(this));
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
        this.createStatusIndicator();
        console.log('[Hardware Scanner] Event listeners attached');
    }

    /**
     * Create floating status indicator
     */
    createStatusIndicator() {
        // Create floating indicator
        const indicator = document.createElement('div');
        indicator.id = 'hardware-scanner-status';
        indicator.style.cssText = `
            position: fixed;
            bottom: 80px;
            right: 20px;
            background: #17a2b8;
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            font-size: 14px;
            z-index: 9999;
            display: none;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        `;
        indicator.innerHTML = '<i class="fas fa-barcode"></i> Hardware Scanner Ready';
        document.body.appendChild(indicator);
        this.statusIndicator = indicator;

        // Show briefly on init
        this.showStatus('Hardware Scanner Ready', 2000);
    }

    /**
     * Show status message
     */
    showStatus(message, duration = 1000) {
        if (this.statusIndicator) {
            this.statusIndicator.innerHTML = `<i class="fas fa-barcode"></i> ${message}`;
            this.statusIndicator.style.display = 'block';

            setTimeout(() => {
                this.statusIndicator.style.display = 'none';
            }, duration);
        }
    }

    /**
     * Handle keypress events (character input)
     */
    handleKeyPress(e) {
        if (!this.enabled) return;

        // Ignore if user is typing in an input field (except search fields)
        const activeElement = document.activeElement;
        const isSearchInput = activeElement && (
            activeElement.id === 'search-input' ||
            activeElement.classList.contains('scanner-input')
        );

        // Allow scanner input in search fields or when no input is focused
        if (activeElement &&
            (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA') &&
            !isSearchInput) {
            return;
        }

        const currentTime = Date.now();
        const timeDiff = currentTime - this.lastInputTime;

        // If input is very fast (< scannerSpeed ms), it's likely a scanner
        const isFastInput = timeDiff < this.scannerSpeed && this.inputBuffer.length > 0;

        if (isFastInput || this.inputBuffer.length === 0) {
            // Add character to buffer
            this.inputBuffer += e.key;
            this.lastInputTime = currentTime;

            // Clear any existing timeout
            if (this.inputTimeout) {
                clearTimeout(this.inputTimeout);
            }

            // Set timeout to process buffer if no more input comes
            this.inputTimeout = setTimeout(() => {
                this.processBuffer();
            }, this.bufferProcessTimeout);

            console.log(`[Hardware Scanner] Buffer: ${this.inputBuffer} (${timeDiff}ms since last char)`);

            // Visual feedback when buffering
            if (this.inputBuffer.length > 5) {
                this.showStatus(`Scanning... (${this.inputBuffer.length} chars)`, 500);
            }
        } else {
            // Slow input - likely human typing, reset buffer
            this.inputBuffer = e.key;
            this.lastInputTime = currentTime;
        }
    }

    /**
     * Handle keydown events (special keys like Enter)
     */
    handleKeyDown(e) {
        if (!this.enabled) return;

        // Enter key pressed - process the buffer immediately
        if (e.key === 'Enter' && this.inputBuffer.length >= this.minBarcodeLength) {
            e.preventDefault();

            if (this.inputTimeout) {
                clearTimeout(this.inputTimeout);
            }

            console.log('[Hardware Scanner] Enter key detected, processing buffer');
            this.processBuffer();
        }

        // Escape key - clear buffer
        if (e.key === 'Escape') {
            this.clearBuffer();
        }
    }

    /**
     * Process the accumulated input buffer
     */
    async processBuffer() {
        const barcode = this.inputBuffer.trim();

        // Validate barcode length
        if (barcode.length < this.minBarcodeLength || barcode.length > this.maxBarcodeLength) {
            console.log(`[Hardware Scanner] Invalid barcode length: ${barcode.length}`);
            this.clearBuffer();
            return;
        }

        // Check for duplicate scan within threshold
        const currentTime = Date.now();
        if (this.lastScannedBarcode === barcode &&
            (currentTime - this.lastScanTimestamp) < this.duplicateScanThreshold) {
            console.log('[Hardware Scanner] Duplicate scan detected, ignoring');
            this.clearBuffer();
            return;
        }

        console.log(`[Hardware Scanner] Processing barcode: ${barcode}`);

        // Update last scan tracking
        this.lastScannedBarcode = barcode;
        this.lastScanTimestamp = currentTime;

        // Check cache first for recently scanned items
        const cachedScan = this.recentlyScanned.get(barcode);
        if (cachedScan && (currentTime - cachedScan.timestamp) < this.recentScanCacheTimeout) {
            console.log('[Hardware Scanner] Found in cache:', cachedScan.item);
            this.clearBuffer();
            this.onItemFound(cachedScan.item, barcode);
            this.showSuccess(`Cached: ${cachedScan.item.name}`);
            return;
        }

        // Clear buffer before processing
        this.clearBuffer();

        // Look up the barcode
        try {
            await this.lookupBarcode(barcode);
        } catch (error) {
            console.error('[Hardware Scanner] Lookup failed:', error);
            this.showError(`Failed to lookup barcode: ${barcode}`);
        }
    }

    /**
     * Look up barcode in database (online/offline) with enhanced retry logic
     */
    async lookupBarcode(barcode, retryCount = 0) {
        const maxRetries = 3;
        const retryDelay = Math.min(1000 * Math.pow(2, retryCount), 5000); // Exponential backoff, max 5s

        try {
            // Try online API first
            if (navigator.onLine) {
                console.log(`[Hardware Scanner] Online lookup attempt ${retryCount + 1}/${maxRetries + 1}`);
                
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
                    signal: AbortSignal.timeout(10000) // 10 second timeout
                });

                if (response.ok) {
                    const data = await response.json();
                    console.log('[Hardware Scanner] Item found online:', data.item);

                    // Cache the result for faster subsequent scans
                    this.recentlyScanned.set(barcode, {
                        item: data.item,
                        timestamp: Date.now()
                    });

                    this.onItemFound(data.item, barcode);
                    this.showStatus('Item Found!', 1500);
                    return;
                }

                // If item not found (404), offer to add new item
                if (response.status === 404) {
                    console.log('[Hardware Scanner] Item not found online, trying offline...');
                    const offlineItem = await this.lookupBarcodeOffline(barcode);
                    if (offlineItem) {
                        // Cache the offline result too
                        this.recentlyScanned.set(barcode, {
                            item: offlineItem,
                            timestamp: Date.now()
                        });

                        this.onItemFound(offlineItem, barcode);
                        this.showStatus('Item Found (Offline)', 1500);
                        return;
                    }
                    
                    // Item not found anywhere - trigger add item flow
                    console.log('[Hardware Scanner] Item not found anywhere, triggering add item flow');
                    this.onItemNotFound(barcode);
                    return;
                }

                // Network error - retry if possible
                if (!response.ok && retryCount < maxRetries) {
                    console.log(`[Hardware Scanner] Network error, retrying in ${retryDelay}ms...`);
                    this.showStatus(`Network error, retrying... (${retryCount + 1}/${maxRetries})`, 2000);
                    await new Promise(resolve => setTimeout(resolve, retryDelay));
                    return this.lookupBarcode(barcode, retryCount + 1);
                }

            } else {
                // Offline mode - search IndexedDB
                console.log('[Hardware Scanner] Offline mode, searching IndexedDB...');
                const offlineItem = await this.lookupBarcodeOffline(barcode);
                if (offlineItem) {
                    // Cache the offline result too
                    this.recentlyScanned.set(barcode, {
                        item: offlineItem,
                        timestamp: Date.now()
                    });

                    this.onItemFound(offlineItem, barcode);
                    this.showStatus('Item Found (Offline)', 1500);
                    return;
                }
                
                // Item not found offline - queue for when back online or offer to add
                console.log('[Hardware Scanner] Item not found offline, queuing for later or add new');
                this.onItemNotFoundOffline(barcode);
                return;
            }

            // If we get here, all attempts failed
            this.showError(`Unable to find item for barcode: ${barcode}`);

        } catch (error) {
            console.error('[Hardware Scanner] Lookup error:', error);

            // Handle different error types
            if (error.name === 'AbortError') {
                console.log('[Hardware Scanner] Request timed out');
                if (retryCount < maxRetries) {
                    console.log(`[Hardware Scanner] Timeout, retrying in ${retryDelay}ms...`);
                    this.showStatus(`Request timeout, retrying... (${retryCount + 1}/${maxRetries})`, 2000);
                    await new Promise(resolve => setTimeout(resolve, retryDelay));
                    return this.lookupBarcode(barcode, retryCount + 1);
                }
            } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
                console.log('[Hardware Scanner] Network error, trying offline fallback');
                // Try offline as fallback for network errors
                try {
                    const offlineItem = await this.lookupBarcodeOffline(barcode);
                    if (offlineItem) {
                        this.onItemFound(offlineItem, barcode);
                        this.showStatus('Item Found (Offline)', 1500);
                        return;
                    }
                } catch (offlineError) {
                    console.error('[Hardware Scanner] Offline lookup also failed:', offlineError);
                }
            }

            // Retry on network errors if we haven't exceeded max retries
            if (retryCount < maxRetries) {
                console.log(`[Hardware Scanner] Network error, retrying (${retryCount + 1}/${maxRetries})...`);
                this.showStatus(`Retrying... (${retryCount + 1}/${maxRetries})`, 1000);
                await new Promise(resolve => setTimeout(resolve, retryDelay));
                return this.lookupBarcode(barcode, retryCount + 1);
            }

            this.showError('Failed to lookup barcode: ' + error.message);
        }
    }

    /**
     * Look up barcode in IndexedDB (offline)
     */
    async lookupBarcodeOffline(barcode) {
        if (!window.dbManager) {
            console.error('[Hardware Scanner] IndexedDB not available');
            return null;
        }

        try {
            const storeName = this.mode === 'retail' ? 'items' : 'wholesaleItems';
            const allItems = await window.dbManager.getAll(storeName);

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
                        // Find item by ID
                        item = allItems.find(item => item.id === itemId);
                        if (item) {
                            console.log('[Hardware Scanner] Item found offline by QR code:', item);
                        }
                    } else {
                        console.warn(`[Hardware Scanner] QR code mode mismatch: ${qrMode} vs ${this.mode}`);
                    }
                }
            } else {
                // Traditional barcode lookup
                item = allItems.find(item => item.barcode === barcode);
                if (item) {
                    console.log('[Hardware Scanner] Item found offline by barcode:', item);
                }
            }

            if (!item) {
                console.log('[Hardware Scanner] Item not found in offline storage');
            }

            return item;

        } catch (error) {
            console.error('[Hardware Scanner] Offline lookup error:', error);
            return null;
        }
    }

    /**
     * Handle item found - use the same callback as camera scanner
     */
    onItemFound(item, barcode) {
        console.log('[Hardware Scanner] Item found, triggering callback');

        // Use the global callback if it exists (same as camera scanner)
        if (typeof window.onBarcodeItemFound === 'function') {
            window.onBarcodeItemFound(item, barcode);
        } else {
            console.warn('[Hardware Scanner] No callback defined, showing alert');
            alert(`Found: ${item.name}\nBarcode: ${barcode}\nPrice: ₦${item.price}`);
        }

        this.showSuccess(`Scanned: ${item.name}`);
    }

    /**
     * Show error message
     */
    showError(message) {
        console.error('[Hardware Scanner]', message);

        // Try to use offline handler if available
        if (window.offlineHandler && window.offlineHandler.showInAppNotification) {
            window.offlineHandler.showInAppNotification(
                'Scanner Error',
                message,
                'error'
            );
        } else {
            // Fallback to alert
            alert(message);
        }
    }

    /**
     * Handle item not found (online mode) - trigger add item flow
     */
    onItemNotFound(barcode) {
        console.log('[Hardware Scanner] Item not found, showing add item modal');
        
        // Try to use global add item modal if available
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
        console.log('[Hardware Scanner] Item not found offline');
        
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
                console.warn('[Hardware Scanner] Cannot queue barcode: IndexedDB not available');
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
            console.log('[Hardware Scanner] Barcode queued for later processing:', barcode);
            this.showStatus('Item queued for when back online', 3000);
        } catch (error) {
            console.error('[Hardware Scanner] Failed to queue barcode:', error);
        }
    }

    /**
     * Show add item dialog (fallback when modal not available)
     */
    showAddItemDialog(barcode, isOffline = false) {
        const message = isOffline 
            ? `Item not found for barcode: ${barcode}\n\nWould you like to:\n1. Add this item now (offline)\n2. Queue for when back online\n3. Cancel`
            : `Item not found for barcode: ${barcode}\n\nWould you like to add this item to inventory?`;

        const response = confirm(message + '\n\nClick OK to add item, Cancel to skip.');
        
        if (response) {
            // Navigate to add item page with pre-filled barcode
            const addUrl = this.mode === 'wholesale' 
                ? `/wholesale/add_wholesale_item/?barcode=${encodeURIComponent(barcode)}`
                : `/store/add_item/?barcode=${encodeURIComponent(barcode)}`;
            
            if (isOffline) {
                this.queueOfflineItemCreation(barcode);
            } else {
                window.location.href = addUrl;
            }
        }
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
            console.error('[Hardware Scanner] Failed to queue offline item:', error);
            this.showError('Failed to queue item for offline creation');
        }
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        console.log('[Hardware Scanner]', message);

        // Try to use offline handler if available
        if (window.offlineHandler && window.offlineHandler.showInAppNotification) {
            window.offlineHandler.showInAppNotification(
                'Item Scanned',
                message,
                'success'
            );
        }
    }

    /**
     * Get CSRF token
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
     * Clear input buffer
     */
    clearBuffer() {
        this.inputBuffer = '';
        this.lastInputTime = 0;
        if (this.inputTimeout) {
            clearTimeout(this.inputTimeout);
            this.inputTimeout = null;
        }
    }

    /**
     * Enable scanner
     */
    enable() {
        this.enabled = true;
        console.log('[Hardware Scanner] Enabled');
    }

    /**
     * Disable scanner
     */
    disable() {
        this.enabled = false;
        this.clearBuffer();
        console.log('[Hardware Scanner] Disabled');
    }

    /**
     * Destroy scanner and remove listeners
     */
    destroy() {
        document.removeEventListener('keypress', this.handleKeyPress);
        document.removeEventListener('keydown', this.handleKeyDown);
        this.clearBuffer();
        console.log('[Hardware Scanner] Destroyed');
    }
}

// Make HardwareScannerHandler available globally
window.HardwareScannerHandler = HardwareScannerHandler;

console.log('[Hardware Scanner] Module loaded successfully');
