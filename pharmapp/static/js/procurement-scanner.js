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
        this.scanCooldown = 1000;  // 1 second cooldown

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
            fps: 60,  // High frame rate for responsive scanning
            qrbox: { width: 350, height: 350 },
            aspectRatio: 1.0,
            formatsToSupport: [
                Html5QrcodeSupportedFormats.QR_CODE,
                Html5QrcodeSupportedFormats.EAN_13,
                Html5QrcodeSupportedFormats.CODE_128,
                Html5QrcodeSupportedFormats.UPC_A
            ]
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

        console.log('[Scanner] Barcode detected:', barcode);
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
        // Trigger the "Add Item" button
        const addBtn = document.getElementById('add-item');
        if (!addBtn) {
            this.showError('Add Item button not found');
            return;
        }

        addBtn.click();

        // Wait for new row to be added to DOM
        setTimeout(() => {
            const rows = document.querySelectorAll('#item-formset tbody tr');
            const newRow = rows[rows.length - 1];
            this.populateRow(newRow, data);
        }, 150);
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

        // Visual feedback - highlight row
        row.classList.add('new-row');
        setTimeout(() => row.classList.remove('new-row'), 2000);

        console.log('[Scanner] Row populated successfully');
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

        if (errorDiv) {
            errorDiv.querySelector('.error-text').textContent = message;
            errorDiv.style.display = 'block';
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
