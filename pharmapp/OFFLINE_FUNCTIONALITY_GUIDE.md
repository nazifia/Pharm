# Offline-First Functionality Guide

## Overview

PharmApp now includes comprehensive offline-first functionality that allows the application to work seamlessly without an internet connection. All changes made offline are automatically queued and synchronized when the connection is restored.

## Features

### 1. **Automatic Offline Detection**
- Real-time connection status monitoring
- Visual indicators for online/offline state
- Automatic fallback to offline mode

### 2. **Local Data Storage**
- IndexedDB for robust client-side storage
- Stores all critical data (inventory, customers, suppliers, sales, etc.)
- Automatic data persistence across sessions

### 3. **Background Sync**
- Automatic synchronization when connection is restored
- Queued actions with retry mechanism
- Conflict resolution for data integrity

### 4. **Progressive Web App (PWA)**
- Installable on desktop and mobile devices
- Offline-capable with service worker
- App-like experience

## Architecture

```
┌─────────────────────────────────────────────┐
│           User Interface (Django)            │
└──────────────────┬──────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
    ▼              ▼              ▼
┌────────┐  ┌─────────────┐  ┌─────────┐
│ Online │  │ Offline     │  │ Service │
│ API    │  │ IndexedDB   │  │ Worker  │
└────────┘  └─────────────┘  └─────────┘
    │              │              │
    └──────────────┴──────────────┘
                   │
            ┌──────┴──────┐
            │             │
            ▼             ▼
    ┌──────────────┐  ┌──────────────┐
    │ Sync Manager │  │ DB Manager   │
    └──────────────┘  └──────────────┘
```

## Components

### 1. IndexedDB Manager (`indexeddb-manager.js`)
Handles all client-side data storage operations.

**Key Methods:**
- `init()` - Initialize the database
- `put(storeName, data)` - Add/update a record
- `bulkPut(storeName, dataArray)` - Bulk insert records
- `get(storeName, key)` - Retrieve a record
- `getAll(storeName)` - Get all records
- `addPendingAction(action)` - Queue an action for sync
- `getPendingActions()` - Get all unsynced actions

### 2. Sync Manager (`sync-manager.js`)
Manages bidirectional data synchronization.

**Key Methods:**
- `downloadInitialData()` - Download data from server
- `syncPendingActions()` - Upload pending changes
- `performFullSync()` - Full bidirectional sync
- `scheduleAutoSync(minutes)` - Schedule automatic sync

### 3. Offline Handler (`offline-handler.js`)
Coordinates offline functionality and UI updates.

**Key Methods:**
- `init()` - Initialize offline handler
- `queueAction(actionType, data, priority)` - Queue an action
- `manualSync()` - Trigger manual sync
- `showNotification(title, message, type)` - Show user notification

### 4. Service Worker (`sw.js`)
Provides offline-first caching and background sync.

**Features:**
- Cache-first strategy for static resources
- Network-first strategy for API calls
- Background sync for pending actions
- Automatic cache management

## Usage

### Basic Integration

#### 1. Queuing Offline Actions

When performing an operation that modifies data, queue it for sync:

```javascript
// Example: Adding a new item
async function addItemOffline(itemData) {
    if (window.offlineHandler) {
        await window.offlineHandler.queueAction('add_item', itemData, 5);
        console.log('Item queued for sync');
    }
}
```

#### 2. Checking Connection Status

```javascript
// Check if online
if (window.offlineHandler && window.offlineHandler.isOnline) {
    // Perform online-only operations
} else {
    // Use offline mode
}
```

#### 3. Manual Sync

```javascript
// Trigger manual sync
if (window.offlineHandler) {
    await window.offlineHandler.manualSync();
}
```

### Advanced Integration

#### 1. Form Submission with Offline Support

```javascript
document.querySelector('#myForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = {
        name: document.querySelector('#name').value,
        quantity: document.querySelector('#quantity').value,
        // ... other fields
    };

    // Try online submission first
    if (navigator.onLine) {
        try {
            const response = await fetch('/api/items/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                showSuccess('Item added successfully');
                return;
            }
        } catch (error) {
            console.log('Online submission failed, using offline mode');
        }
    }

    // Fallback to offline mode
    await window.offlineHandler.queueAction('add_item', formData);
    showSuccess('Item queued. Will sync when online.');
});
```

#### 2. Searching Offline Data

```javascript
async function searchItems(searchTerm) {
    if (window.dbManager) {
        const results = await window.dbManager.searchItems(searchTerm);
        displayResults(results);
    }
}
```

#### 3. Getting Cart Total

```javascript
async function updateCartTotal() {
    if (window.dbManager) {
        const total = await window.dbManager.getCartTotal();
        document.querySelector('#cartTotal').textContent = total.toFixed(2);
    }
}
```

## Action Types

The system supports the following action types:

### Inventory Actions
- `add_item` - Add new inventory item
- `update_item` - Update existing item
- `delete_item` - Delete item

### Sales Actions
- `add_sale` - Create new sale
- `add_receipt` - Generate receipt
- `add_dispensing` - Log dispensing

### Customer Actions
- `add_customer` - Add new customer
- `update_customer` - Update customer info

### Supplier Actions
- `add_supplier` - Add new supplier
- `update_supplier` - Update supplier info

### Wholesale Actions
- `add_wholesale_item` - Add wholesale item
- `add_wholesale_sale` - Create wholesale sale

### Cart Actions
- `add_to_cart` - Add item to cart
- `update_cart` - Update cart item
- `remove_from_cart` - Remove from cart

## UI Components

### Connection Status Indicator

Already integrated in `base.html`:

```html
<div id="connection-status" class="connection-status">
    <div class="status-indicator">
        <span class="status-dot"></span>
        <span class="status-text">Online</span>
    </div>
    <div class="sync-status hidden">
        <span class="sync-icon">↻</span>
        <span class="sync-text">Syncing...</span>
    </div>
</div>
```

### Manual Sync Button

Add to your template:

```html
<button onclick="window.offlineHandler.manualSync()" class="sync-button">
    Sync Now
</button>
```

### Pending Actions Counter

Automatically displayed when there are pending actions.

## API Endpoints

### Health Check
```
GET /api/health/
```
Returns: `{ "status": "ok", "timestamp": "..." }`

### Initial Data Download
```
GET /api/data/initial/
```
Returns: All inventory, customers, suppliers, wholesale items

### Sync Endpoints
```
POST /api/inventory/sync/
POST /api/sales/sync/
POST /api/customers/sync/
POST /api/suppliers/sync/
POST /api/wholesale/sync/
POST /api/receipts/sync/
POST /api/dispensing/sync/
POST /api/cart/sync/
```

All sync endpoints expect:
```json
{
    "pendingActions": [
        {
            "actionType": "add_item",
            "data": { ... },
            "timestamp": "2025-01-17T12:00:00Z",
            "priority": 5
        }
    ]
}
```

## Event System

The offline system dispatches custom events:

### IndexedDB Ready
```javascript
window.addEventListener('indexeddb-ready', () => {
    console.log('IndexedDB is ready');
});
```

### Sync Status Change
```javascript
window.addEventListener('sync-status-change', (event) => {
    const { status, message } = event.detail;
    console.log(`Sync status: ${status} - ${message}`);
});
```

### Data Updated
```javascript
window.addEventListener('data-updated', () => {
    console.log('Data has been updated, refresh UI');
});
```

## Best Practices

### 1. **Always Check for Availability**
```javascript
if (window.dbManager && window.syncManager && window.offlineHandler) {
    // Offline functionality is available
}
```

### 2. **Provide User Feedback**
Always inform users about offline operations:
```javascript
if (!navigator.onLine) {
    showWarning('You are offline. Changes will sync when online.');
}
```

### 3. **Handle Sync Failures**
```javascript
window.addEventListener('sync-status-change', (event) => {
    if (event.detail.status === 'error') {
        showError('Sync failed. Will retry automatically.');
    }
});
```

### 4. **Prioritize Critical Actions**
Use higher priority (lower number) for critical operations:
```javascript
// Critical sale - priority 1
await window.offlineHandler.queueAction('add_sale', saleData, 1);

// Regular update - priority 5
await window.offlineHandler.queueAction('update_item', itemData, 5);
```

### 5. **Test Offline Scenarios**
Use Chrome DevTools:
1. Open DevTools (F12)
2. Go to Network tab
3. Select "Offline" from throttling dropdown
4. Test your application

## Troubleshooting

### Issue: Service Worker Not Registering
**Solution:** Check browser console for errors. Ensure HTTPS or localhost.

### Issue: Data Not Syncing
**Solution:**
1. Check browser console for errors
2. Verify network connectivity
3. Check pending actions: `await window.dbManager.getPendingActions()`

### Issue: IndexedDB Not Working
**Solution:**
1. Check if IndexedDB is supported: `!!window.indexedDB`
2. Clear browser data and reload
3. Check browser privacy settings

### Issue: Duplicate Data After Sync
**Solution:** Ensure unique IDs are used for all records. Check sync endpoint logic for proper update vs. create logic.

## Performance Considerations

### 1. **Batch Operations**
Use `bulkPut` for multiple records:
```javascript
await window.dbManager.bulkPut('items', itemsArray);
```

### 2. **Limit Auto-Sync Frequency**
Default is 5 minutes. Adjust if needed:
```javascript
window.syncManager.scheduleAutoSync(10); // 10 minutes
```

### 3. **Clean Up Old Data**
Periodically clear synced actions:
```javascript
// This is handled automatically by the sync manager
```

### 4. **Monitor Storage Usage**
```javascript
if (navigator.storage && navigator.storage.estimate) {
    const estimate = await navigator.storage.estimate();
    console.log(`Used: ${estimate.usage} / ${estimate.quota} bytes`);
}
```

## Security Considerations

1. **CSRF Protection:** All POST requests include CSRF token
2. **Data Validation:** Server validates all synced data
3. **Authentication:** Sync requires authenticated user
4. **Encryption:** Use HTTPS in production for data transmission

## Future Enhancements

- Conflict resolution UI for manual merge
- Selective sync (choose what to sync)
- Compression for large data transfers
- Differential sync (only changed fields)
- Multi-device sync detection

## Support

For issues or questions:
1. Check browser console for error messages
2. Review this documentation
3. Check the codebase architecture in CLAUDE.md
4. Contact development team

## Testing Checklist

- [ ] Service Worker registers successfully
- [ ] IndexedDB initializes without errors
- [ ] Connection status indicator works
- [ ] Data persists in offline mode
- [ ] Pending actions queue correctly
- [ ] Sync triggers when coming online
- [ ] Manual sync works
- [ ] Notifications display correctly
- [ ] Forms work in offline mode
- [ ] Data doesn't duplicate after sync
- [ ] Performance is acceptable
- [ ] Works on target browsers/devices
