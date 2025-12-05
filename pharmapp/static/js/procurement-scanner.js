/**
 * Procurement Barcode Scanner Integration
 * Integrates Html5Qrcode with procurement form
 * Supports global (add new row) and per-row (populate existing) modes
 */

console.log('[Procurement Scanner] Loading...');

class ProcurementScanner {
    constructor() {
        this.scanner = null;
        this.isScanning = false;
        this.currentRow = null;
        this.mode = 'global';  // 'global' or 'row'
        this.lastScanTime = 0;
        this.scanCooldown = 500;  // 0.5 second cooldown (reduced from 1000ms for faster consecutive scans)

        this.init();
    }

    init() {
        // Attach modal event listeners
        $('#scannerModal').on('shown.bs.modal', () => this.startScanner());
        $('#scannerModal').on('hidden.bs.modal', () => this.stopScanner());

        // Attach button listeners
        this.attachEventListeners();

        console.log('[Procurement Scanner] Initialized');
    }

    attachEventListeners() {
        // Global scan button
        const globalBtn = document.getElementById('global-scan-btn');
        if (globalBtn) {
            globalBtn.addEventListener('click', () => {
                this.mode = 'global';
                this.currentRow = null;
                $('#scannerModal').modal('show');
            });
        }

        // Per-row scan buttons (use event delegation for dynamic rows)
        document.addEventListener('click', (e) => {
            if (e.target.closest('.scan-row-btn')) {
                const btn = e.target.closest('.scan-row-btn');
                const rowIndex = parseInt(btn.getAttribute('data-row-index'));

                this.mode = 'row';
                this.currentRow = document.querySelectorAll('#item-formset tbody tr')[rowIndex];

                if (!this.currentRow) {
                    console.error('Row not found for index:', rowIndex);
                    return;
                }

                $('#scannerModal').modal('show');
            }
        });
    }

    startScanner() {
        if (this.isScanning) {
            console.log('[Scanner] Already scanning');
            return;
        }

        // Configure scanner for optimal performance
        const config = {
            fps: 120,  // Maximum frame rate for responsive scanning (increased from 60)
            qrbox: { width: 450, height: 450 },  // Larger scan area for better detection (increased from 350)
            aspectRatio: 1.0,
            disableFlip: false,  // Allow horizontal flip for better detection
            formatsToSupport: [
                Html5QrcodeSupportedFormats.QR_CODE,
                Html5QrcodeSupportedFormats.EAN_13,
                Html5QrcodeSupportedFormats.EAN_8,
                Html5QrcodeSupportedFormats.CODE_128,
                Html5QrcodeSupportedFormats.CODE_39,
                Html5QrcodeSupportedFormats.UPC_A,
                Html5QrcodeSupportedFormats.UPC_E
            ],
            videoConstraints: {
                facingMode: "environment",
                width: { ideal: 1920 },      // Higher resolution for better detection
                height: { ideal: 1080 },
                frameRate: { ideal: 60 }     // Higher framerate
            }
        };

        this.scanner = new Html5Qrcode('barcode-scanner');

        this.scanner.start(
            { facingMode: 'environment' },  // Use back camera
            config,
            (decodedText) => this.handleScanSuccess(decodedText),
            (errorMessage) => {
                // Suppress frequent scan errors (normal during scanning)
                console.debug('[Scanner] Scanning...', errorMessage);
            }
        ).then(() => {
            this.isScanning = true;
            console.log('[Scanner] Started successfully');
        }).catch(err => {
            console.error('[Scanner] Start failed:', err);
            this.showError('Failed to start scanner. Please check camera permissions.');
        });
    }

    stopScanner() {
        if (this.scanner && this.isScanning) {
            this.scanner.stop().then(() => {
                this.isScanning = false;
                console.log('[Scanner] Stopped');
            }).catch(err => {
                console.error('[Scanner] Stop failed:', err);
            });
        }
    }

    async handleScanSuccess(barcode) {
        // Debounce scans
        const now = Date.now();
        if (now - this.lastScanTime < this.scanCooldown) {
            console.log('[Scanner] Scan too soon, ignoring');
            return;
        }
        this.lastScanTime = now;

        // Check if already processing another scan
        if (this.isProcessing) {
            console.log('[Scanner] Already processing a scan, ignoring');
            return;
        }

        console.log('[Scanner] Barcode detected:', barcode);

        // Check for duplicate barcode in existing rows BEFORE API call
        if (this.mode === 'global') {
            const existingBarcodes = Array.from(
                document.querySelectorAll('#item-formset input[name$="-barcode"]')
            ).map(input => input.value.trim()).filter(val => val);

            if (existingBarcodes.includes(barcode)) {
                this.showError(`⚠️ Duplicate barcode detected!\n\nBarcode ${barcode} already exists in the form.\n\nPlease scan a different item.`);
                return;
            }
        }

        this.showResult('Processing barcode: ' + barcode);

        try {
            // Detect if we're on wholesale or retail page
            const isWholesale = window.location.pathname.includes('/wholesale/');
            const url = isWholesale
                ? `/wholesale/search-wholesale-item-by-barcode/?barcode=${encodeURIComponent(barcode)}`
                : `/store/search-item-by-barcode/?barcode=${encodeURIComponent(barcode)}`;

            const response = await fetch(url, {
                credentials: 'same-origin',  // Include session cookies for authentication
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'  // Identify as AJAX request
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.error) {
                this.showError(data.error);
                return;
            }

            // Process based on mode
            if (this.mode === 'global') {
                this.addNewRowWithData(data);
            } else if (this.mode === 'row' && this.currentRow) {
                this.populateRow(this.currentRow, data);
            }

            // Success feedback and close
            this.showResult('✓ Item added successfully!');
            setTimeout(() => {
                $('#scannerModal').modal('hide');
            }, 1000);

        } catch (error) {
            console.error('[Scanner] Lookup failed:', error);
            this.showError('Failed to lookup barcode: ' + error.message);
        }
    }

    addNewRowWithData(data) {
        // Prevent duplicate processing
        if (this.isProcessing) {
            console.log('[Scanner] Already processing, ignoring duplicate scan');
            return;
        }
        this.isProcessing = true;

        try {
            const tableBody = document.querySelector('#item-formset tbody');
            const totalForms = document.querySelector('input[name="form-TOTAL_FORMS"]');

            if (!totalForms || !tableBody) {
                this.showError('Form structure not found');
                this.isProcessing = false;
                return;
            }

            const formIdx = parseInt(totalForms.value);

            // Check for duplicate barcode in existing rows
            const existingBarcodes = Array.from(tableBody.querySelectorAll('input[name$="-barcode"]'))
                .map(input => input.value.trim())
                .filter(val => val);

            if (existingBarcodes.includes(data.barcode)) {
                this.showError(`Barcode ${data.barcode} already exists in the form`);
                this.isProcessing = false;
                return;
            }

            // Clone the last row template
            const lastRow = tableBody.querySelector('tr:last-child');
            if (!lastRow) {
                this.showError('No template row found');
                this.isProcessing = false;
                return;
            }

            const newRow = lastRow.cloneNode(true);

            // Update form field names and IDs for new index
            newRow.querySelectorAll('input, select, textarea').forEach(input => {
                if (input.name) {
                    input.name = input.name.replace(/-\d+-/, `-${formIdx}-`);
                }
                if (input.id) {
                    input.id = input.id.replace(/-\d+-/, `-${formIdx}-`);
                }

                // Clear values for new row
                if (input.type !== 'hidden') {
                    if (input.tagName === 'SELECT') {
                        input.selectedIndex = 0;
                    } else {
                        input.value = '';
                    }
                } else if (input.name && input.name.includes('markup')) {
                    input.value = '0';
                }
            });

            // Reset subtotal display
            const subtotalCell = newRow.querySelector('.subtotal');
            if (subtotalCell) {
                subtotalCell.textContent = '₦0.00';
            }

            // Update scan button data-row-index
            const scanBtn = newRow.querySelector('.scan-row-btn');
            if (scanBtn) {
                scanBtn.setAttribute('data-row-index', formIdx);
            }

            // Add row to DOM FIRST
            tableBody.appendChild(newRow);

            // Increment form count
            totalForms.value = formIdx + 1;

            // NOW populate the row (DOM is ready)
            this.populateRow(newRow, data);

            // Setup event listeners for the new row
            if (typeof addCalculationListeners === 'function') {
                addCalculationListeners(newRow);
            }
            if (typeof setupItemSearch === 'function') {
                setupItemSearch(newRow);
            }

            console.log('[Scanner] Row added and populated successfully');

        } catch (error) {
            console.error('[Scanner] Error adding row:', error);
            this.showError('Failed to add row: ' + error.message);
        } finally {
            // Release processing lock after a small delay
            setTimeout(() => {
                this.isProcessing = false;
            }, 500);
        }
    }

    populateRow(row, data) {
        if (!row) {
            console.error('[Scanner] No row to populate');
            return;
        }

        const parsed = data.parsed;
        const results = data.results;

        // Always populate barcode field
        const barcodeInput = row.querySelector('input[name$="-barcode"]');
        if (barcodeInput) {
            barcodeInput.value = data.barcode;
        }

        // If we have matching items, use first match
        if (results && results.length > 0) {
            const item = results[0];

            const itemNameInput = row.querySelector('input[name$="-item_name"]');
            const brandInput = row.querySelector('input[name$="-brand"]');
            const dosageFormSelect = row.querySelector('select[name$="-dosage_form"]');
            const unitSelect = row.querySelector('select[name$="-unit"]');
            const costPriceInput = row.querySelector('input[name$="-cost_price"]');
            const expiryDateInput = row.querySelector('input[name$="-expiry_date"]');

            if (itemNameInput) itemNameInput.value = item.name;
            if (brandInput) brandInput.value = item.brand;

            // Set select options
            if (dosageFormSelect) {
                Array.from(dosageFormSelect.options).forEach(option => {
                    if (option.value === item.dosage_form) {
                        option.selected = true;
                    }
                });
            }

            if (unitSelect) {
                Array.from(unitSelect.options).forEach(option => {
                    if (option.value === item.unit) {
                        option.selected = true;
                    }
                });
            }

            if (costPriceInput && item.cost_price) {
                costPriceInput.value = item.cost_price;
            }

            if (expiryDateInput && item.expiry_date) {
                expiryDateInput.value = item.expiry_date;
            }
        }

        // If GS1 format with product name, use it (if no match found)
        if (parsed.is_gs1_format && parsed.product_name && (!results || results.length === 0)) {
            const itemNameInput = row.querySelector('input[name$="-item_name"]');
            if (itemNameInput) {
                itemNameInput.value = parsed.product_name;
            }
        }

        // Use parsed expiry date if available and not overridden
        if (parsed.expiry_date) {
            const expiryDateInput = row.querySelector('input[name$="-expiry_date"]');
            if (expiryDateInput && !expiryDateInput.value) {
                expiryDateInput.value = parsed.expiry_date;
            }
        }

        // Trigger calculations (subtotal, grand total)
        const costPriceInput = row.querySelector('input[name$="-cost_price"]');
        const quantityInput = row.querySelector('input[name$="-quantity"]');

        if (costPriceInput) {
            costPriceInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
        if (quantityInput) {
            quantityInput.dispatchEvent(new Event('input', { bubbles: true }));
        }

        // Enhanced visual feedback - highlight row with success color
        row.classList.add('new-row', 'table-success');
        row.style.transition = 'background-color 0.3s ease';

        // Pulse animation with fade out
        setTimeout(() => {
            row.classList.remove('table-success');
        }, 2000);

        setTimeout(() => {
            row.classList.remove('new-row');
        }, 2500);

        // Show success toast if available
        const itemName = (results && results.length > 0) ? results[0].name : 'Item';
        console.log('[Scanner] Row populated successfully:', itemName);
    }

    showResult(message) {
        const resultDiv = document.getElementById('scan-result');
        const errorDiv = document.getElementById('scan-error');

        if (resultDiv) {
            resultDiv.querySelector('.result-text').textContent = message;
            resultDiv.style.display = 'block';
        }
        if (errorDiv) {
            errorDiv.style.display = 'none';
        }
    }

    showError(message) {
        const resultDiv = document.getElementById('scan-result');
        const errorDiv = document.getElementById('scan-error');

        // Make errors more user-friendly
        let userMessage = message;

        if (message.includes('already exists') || message.includes('Duplicate')) {
            // Already formatted with emoji in handleScanSuccess
            userMessage = message;
        } else if (message.includes('not found') || message.includes('No results')) {
            userMessage = `ℹ️ Item not found in database.\n\nBarcode will be saved for this new item.`;
        } else if (message.includes('camera') || message.includes('permissions')) {
            userMessage = `📷 Camera access required.\n\nPlease allow camera permissions and try again.`;
        } else if (message.includes('Failed to start')) {
            userMessage = `📷 Unable to start camera.\n\nPlease check permissions and try again.`;
        }

        if (errorDiv) {
            const errorText = errorDiv.querySelector('.error-text');
            if (errorText) {
                errorText.textContent = userMessage;
            }
            errorDiv.style.display = 'block';

            // Auto-hide error after 5 seconds
            setTimeout(() => {
                if (errorDiv) {
                    errorDiv.style.display = 'none';
                }
            }, 5000);
        }
        if (resultDiv) {
            resultDiv.style.display = 'none';
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('global-scan-btn')) {
        window.procurementScanner = new ProcurementScanner();
        console.log('[Procurement Scanner] Ready');
    }
});
