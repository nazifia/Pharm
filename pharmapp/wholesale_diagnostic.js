// ===========================================================
// Wholesale Transfer Page Diagnostic Script
// ===========================================================
//
// INSTRUCTIONS:
// 1. Navigate to: http://127.0.0.1:8000/wholesale/transfer/multiple/
// 2. Open browser console (F12)
// 3. Copy and paste this entire script
// 4. Press Enter to run
// 5. Review the results in console
//
// ===========================================================

(function() {
    console.log('═══════════════════════════════════════════════════════');
    console.log('WHOLESALE TRANSFER PAGE DIAGNOSTIC');
    console.log('═══════════════════════════════════════════════════════\n');

    const results = {
        passed: [],
        failed: [],
        warnings: []
    };

    // Test 1: Document Ready State
    console.log('Test 1: Document Ready State');
    console.log('  Ready state:', document.readyState);
    if (document.readyState === 'complete') {
        results.passed.push('Document fully loaded');
    } else {
        results.warnings.push('Document not fully loaded');
    }

    // Test 2: Initialization Function Executed
    console.log('\nTest 2: Checking Console for Initialization Log');
    console.log('  (Check above for "[Wholesale Transfer] Initializing features")');

    // Test 3: Calculation Function Exists
    console.log('\nTest 3: calculateProcurementValuesWholesale Function');
    const calcFunctionExists = typeof window.calculateProcurementValuesWholesale === 'function';
    console.log('  Function exists:', calcFunctionExists);
    if (calcFunctionExists) {
        results.passed.push('✅ Calculation function is defined');
    } else {
        results.failed.push('❌ Calculation function is NOT defined');
    }

    // Test 4: Edit Buttons
    console.log('\nTest 4: Edit Stock Buttons');
    const editButtons = document.querySelectorAll('.edit-stock-btn-wholesale');
    console.log('  Edit buttons found:', editButtons.length);
    if (editButtons.length > 0) {
        results.passed.push(`Found ${editButtons.length} edit buttons`);

        // Check if buttons are clickable
        const firstBtn = editButtons[0];
        const isDisabled = firstBtn.disabled || firstBtn.hasAttribute('disabled');
        const pointerEvents = window.getComputedStyle(firstBtn).pointerEvents;

        console.log('  First button disabled:', isDisabled);
        console.log('  First button pointer-events:', pointerEvents);

        if (!isDisabled && pointerEvents !== 'none') {
            results.passed.push('✅ Edit buttons are clickable');
        } else {
            results.failed.push('❌ Edit buttons are NOT clickable');
        }
    } else {
        results.warnings.push('⚠️ No edit buttons found (no wholesale items?)');
    }

    // Test 5: Modal Elements
    console.log('\nTest 5: Edit Stock Modal');
    const modal = document.getElementById('editStockModalWholesale');
    const modalInput = document.getElementById('new-stock-wholesale');
    const modalSaveBtn = document.getElementById('save-stock-btn-wholesale');

    console.log('  Modal exists:', !!modal);
    console.log('  Modal input exists:', !!modalInput);
    console.log('  Modal save button exists:', !!modalSaveBtn);

    if (modal && modalInput && modalSaveBtn) {
        results.passed.push('✅ Modal elements present');
    } else {
        results.failed.push('❌ Modal elements missing');
    }

    // Test 6: Procurement Value Cells
    console.log('\nTest 6: Procurement Value Cells');
    const procValueCells = document.querySelectorAll('.procurement-value');
    console.log('  Procurement value cells found:', procValueCells.length);
    if (procValueCells.length > 0) {
        results.passed.push(`Found ${procValueCells.length} procurement value cells`);
    } else {
        results.warnings.push('⚠️ No procurement value cells found');
    }

    // Test 7: Summary Elements
    console.log('\nTest 7: Procurement Values Summary');
    const grandTotalEl = document.getElementById('grand-procurement-total-wholesale');
    const averageEl = document.getElementById('average-item-value-wholesale');
    const itemCountEl = document.getElementById('total-items-count-wholesale');

    console.log('  Grand total element exists:', !!grandTotalEl);
    console.log('  Average element exists:', !!averageEl);
    console.log('  Item count element exists:', !!itemCountEl);

    if (grandTotalEl && averageEl && itemCountEl) {
        const grandTotal = grandTotalEl.textContent;
        const average = averageEl.textContent;
        const itemCount = itemCountEl.textContent;

        console.log('  Grand total value: ₦' + grandTotal);
        console.log('  Average value: ₦' + average);
        console.log('  Item count:', itemCount);

        // Check if values are populated (not 0.00)
        if (grandTotal !== '0.00' && grandTotal !== '0' && grandTotal !== '') {
            results.passed.push('✅ Procurement values summary is displaying data');
        } else {
            results.warnings.push('⚠️ Procurement values summary shows 0 (no items or not calculated)');
        }
    } else {
        results.failed.push('❌ Procurement values summary elements missing');
    }

    // Test 8: jQuery Loaded
    console.log('\nTest 8: jQuery');
    console.log('  jQuery loaded:', typeof $ !== 'undefined');
    if (typeof $ !== 'undefined') {
        results.passed.push('jQuery loaded');
    } else {
        results.failed.push('❌ jQuery NOT loaded');
    }

    // Test 9: Event Listeners
    console.log('\nTest 9: Testing Edit Button Click');
    if (editButtons.length > 0) {
        console.log('  Click the first edit button to test if modal opens...');
        console.log('  (You can click manually or run: editButtons[0].click())');
    }

    // Display Summary
    console.log('\n═══════════════════════════════════════════════════════');
    console.log('SUMMARY');
    console.log('═══════════════════════════════════════════════════════');

    console.log('\n✅ PASSED (' + results.passed.length + '):');
    results.passed.forEach(msg => console.log('  ' + msg));

    if (results.failed.length > 0) {
        console.log('\n❌ FAILED (' + results.failed.length + '):');
        results.failed.forEach(msg => console.log('  ' + msg));
    }

    if (results.warnings.length > 0) {
        console.log('\n⚠️  WARNINGS (' + results.warnings.length + '):');
        results.warnings.forEach(msg => console.log('  ' + msg));
    }

    console.log('\n═══════════════════════════════════════════════════════');

    if (results.failed.length === 0) {
        console.log('✅ ALL CRITICAL TESTS PASSED!');
        console.log('The wholesale transfer page should be fully functional.');
    } else {
        console.log('❌ SOME TESTS FAILED');
        console.log('Please review the failures above.');
    }

    console.log('═══════════════════════════════════════════════════════\n');

    // Return results for programmatic access
    return {
        passed: results.passed,
        failed: results.failed,
        warnings: results.warnings,
        allPassed: results.failed.length === 0
    };
})();
