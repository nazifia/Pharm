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
        this.scannerSpeed = 100; // Increased from 50ms to 100ms for Bluetooth scanners
        this.minBarcodeLength = 3; // Minimum barcode length
        this.maxBarcodeLength = 50; // Maximum barcode length
        this.enabled = true;
        this.inputTimeout = null;
        this.bufferProcessTimeout = 150; // Increased from 100ms to 150ms
        this.statusIndicator = null;
        this.maxRetries = 2; // Max retry attempts for network errors

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

        console.log(`[Hardware Scanner] Processing barcode: ${barcode}`);

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
     * Look up barcode in database (online/offline) with retry logic
     */
    async lookupBarcode(barcode, retryCount = 0) {
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
                    console.log('[Hardware Scanner] Item found online:', data.item);
                    this.onItemFound(data.item, barcode);
                    this.showStatus('Item Found!', 1500);
                    return;
                }

                // If 404, try offline
                if (response.status === 404) {
                    console.log('[Hardware Scanner] Item not found online, trying offline...');
                    const offlineItem = await this.lookupBarcodeOffline(barcode);
                    if (offlineItem) {
                        this.onItemFound(offlineItem, barcode);
                        this.showStatus('Item Found (Offline)', 1500);
                        return;
                    }
                }

                // Network error - retry
                if (response.status >= 500 && retryCount < this.maxRetries) {
                    console.log(`[Hardware Scanner] Server error, retrying (${retryCount + 1}/${this.maxRetries})...`);
                    this.showStatus(`Retrying... (${retryCount + 1}/${this.maxRetries})`, 1000);
                    await new Promise(resolve => setTimeout(resolve, 500));  // Wait 500ms
                    return this.lookupBarcode(barcode, retryCount + 1);
                }
            } else {
                // Offline mode
                console.log('[Hardware Scanner] Offline mode, searching IndexedDB...');
                const offlineItem = await this.lookupBarcodeOffline(barcode);
                if (offlineItem) {
                    this.onItemFound(offlineItem, barcode);
                    this.showStatus('Item Found (Offline)', 1500);
                    return;
                }
            }

            // Not found anywhere
            this.showError(`Item not found for barcode: ${barcode}`);

        } catch (error) {
            console.error('[Hardware Scanner] Lookup error:', error);

            // Retry on network errors
            if (retryCount < this.maxRetries) {
                console.log(`[Hardware Scanner] Network error, retrying (${retryCount + 1}/${this.maxRetries})...`);
                this.showStatus(`Retrying... (${retryCount + 1}/${this.maxRetries})`, 1000);
                await new Promise(resolve => setTimeout(resolve, 500));
                return this.lookupBarcode(barcode, retryCount + 1);
            }

            // Try offline as last resort
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

            this.showError('Failed to lookup barcode');
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
