# PharmApp Offline Functionality Guide

## Overview

PharmApp includes comprehensive **offline-first** capabilities that allow users to continue working without internet connection. All changes are saved locally and automatically synchronized when the connection is restored.

## How It Works

### 1. **Automatic Offline Detection**
- The app continuously monitors internet connectivity
- Visual indicators show current connection status (top-right corner)
- Automatic fallback to offline mode when connection is lost

### 2. **Local Data Storage (IndexedDB)**
- All critical data is cached locally in the browser
- Includes: inventory items, customers, suppliers, cart data
- Supports both retail and wholesale operations

### 3. **Action Queue**
- User actions performed offline are queued locally
- Each action has a priority level (1=highest, 10=lowest)
- Actions are automatically synced when connection is restored

### 4. **Automatic Synchronization**
- Background sync triggers automatically when online
- Bidirectional sync: upload pending changes + download latest data
- Conflict resolution ensures data integrity

---

## Supported Offline Operations

### ✅ **Fully Supported (Work Offline)**

#### Inventory Management
- View all inventory items (retail & wholesale)
- Search items by name, brand, or dosage form
- Check stock levels and prices
- View low stock items
- View expiring items (within 30 days)

#### Cart Operations
- **Add items to cart** (retail & wholesale)
- Update cart quantities
- Remove items from cart
- View cart totals
- All cart changes saved locally

#### Customer Management
- View customer lists
- Search customers
- View customer wallet balances

#### Supplier Management
- View supplier lists
- Search suppliers

### ⚠️ **Limited Support (Requires Online)**
- Creating new inventory items (queued for sync)
- Processing payments and receipts
- Procurement operations
- User management
- Reports and analytics

---

## User Interface Elements

### Connection Status Indicator
**Location:** Top-right corner of every page

- 🟢 **Green Dot + "Online"**: Connected to internet
- 🔴 **Red Dot + "Offline"**: No internet connection
- ↻ **Sync Icon**: Synchronization in progress

### Pending Actions Badge
**Shows:** Number of queued offline actions waiting to sync

- Displayed when there are pending changes
- Updates in real-time
- Disappears after successful sync

### Offline Notifications
- **Success (Green)**: Action saved successfully
- **Warning (Yellow)**: Action saved offline, will sync later
- **Error (Red)**: Action failed

---

## Step-by-Step Usage Guide

### Scenario 1: Working While Offline

**Step 1:** User loses internet connection
```
→ Status indicator changes to "Offline" (red dot)
→ Optional notification: "You're offline"
```

**Step 2:** User adds items to cart
```
→ Item is added to local IndexedDB
→ Action is queued for synchronization
→ User sees: "Added [item] to cart (offline). Will sync when connection is restored."
→ Pending actions count increases
```

**Step 3:** User continues working
```
→ All supported operations work normally
→ Each action is saved locally and queued
```

**Step 4:** Connection restored
```
→ Status indicator changes to "Online" (green)
→ Background sync automatically triggered
→ Queued actions uploaded to server
→ Latest data downloaded from server
→ Notification: "Sync Complete - All changes synced to server"
→ Pending count returns to 0
```

### Scenario 2: Starting Offline (First Time)

**If user opens app without internet:**
```
1. App loads from cached files (Service Worker)
2. Shows offline page with available features
3. User can view cached data
4. User can perform offline operations
5. When online, initial data is downloaded automatically
```

---

## Technical Architecture

### Components

#### 1. **Service Worker** (`static/js/sw.js`)
- Caches app shell and static assets
- Intercepts network requests
- Provides offline fallbacks
- Handles background sync events

#### 2. **IndexedDB Manager** (`static/js/indexeddb-manager.js`)
- Manages local database (PharmAppDB)
- Stores: items, customers, suppliers, carts, pending actions
- Provides search and query methods

#### 3. **Sync Manager** (`static/js/sync-manager.js`)
- Handles bidirectional synchronization
- Groups actions by type for batch processing
- Implements retry logic (max 3 attempts)
- Manages CSRF tokens for Django

#### 4. **Offline Handler** (`static/js/offline-handler.js`)
- Coordinates all offline functionality
- Monitors connection status
- Manages UI updates and notifications
- Triggers sync on connection restore

#### 5. **Offline Helpers** (`static/js/offline-helpers.js`)
- Convenient wrapper functions
- `queueOfflineAction()` - Queue any action
- `submitFormWithOffline()` - Submit forms with offline support
- `searchItemsOffline()` - Search local data
- `addToCartOffline()` - Add to cart offline

#### 6. **Cart Offline** (`static/js/cart-offline.js`)
- Specialized cart operations
- Handles add to cart (retail & wholesale)
- Updates local cart displays
- Syncs cart with server

### Data Flow

```
┌─────────────┐
│   User      │
│   Action    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐      Online?
│  Check Network  │────────────┐
│     Status      │            │
└─────────┬───────┘            │
          │                    │
    ┌─────▼─────┐         ┌───▼────┐
    │  Offline  │         │ Online │
    └─────┬─────┘         └───┬────┘
          │                   │
          ▼                   ▼
  ┌───────────────┐   ┌───────────────┐
  │   IndexedDB   │   │   Django API  │
  │  + Queue for  │   │   (Direct)    │
  │     Sync      │   └───────────────┘
  └───────┬───────┘
          │
    ┌─────▼─────┐
    │  Online?  │
    └─────┬─────┘
          │ Yes
          ▼
  ┌───────────────┐
  │  Background   │
  │     Sync      │
  └───────┬───────┘
          │
          ▼
  ┌───────────────┐
  │  Django API   │
  │   (Batch)     │
  └───────────────┘
```

---

## API Endpoints

### Sync Endpoints (All POST)
- `/api/inventory/sync/` - Sync inventory changes
- `/api/cart/sync/` - Sync cart actions
- `/api/wholesale-cart/sync/` - Sync wholesale cart
- `/api/sales/sync/` - Sync sales transactions
- `/api/customers/sync/` - Sync customer data
- `/api/suppliers/sync/` - Sync supplier data
- `/api/receipts/sync/` - Sync receipts
- `/api/dispensing/sync/` - Sync dispensing logs

### Data Endpoints
- `GET /api/health/` - Check server connectivity
- `GET /api/data/initial/` - Download all data for offline cache

---

## Developer Guide

### Adding Offline Support to a New Form

**Method 1: Using the Partial Template**
```django
{% include 'partials/offline_form.html' with
    form_id="my-form"
    action_type="add_my_entity"
    entity_name="record"
%}
```

**Method 2: Custom JavaScript**
```javascript
// In your template
<form id="myForm" action="/api/my-endpoint/" method="post">
    {% csrf_token %}
    <!-- form fields -->
    <button type="submit">Save</button>
</form>

<script>
document.getElementById('myForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    await submitFormWithOffline(
        this,
        '/api/my-endpoint/',
        'add_my_entity',
        (result) => {
            if (result.offline) {
                showWarningMessage('Saved offline. Will sync later.');
            } else {
                showSuccessMessage('Saved successfully!');
            }
        },
        (error) => {
            showErrorMessage('Failed: ' + error.message);
        }
    );
});
</script>
```

### Queuing Custom Actions

```javascript
// Queue any offline action
await queueOfflineAction('custom_action', {
    field1: 'value1',
    field2: 'value2'
}, 5); // priority 5
```

### Searching Offline Data

```javascript
// Search items
const results = await searchItemsOffline('aspirin', false); // retail
const wholesaleResults = await searchItemsOffline('aspirin', true); // wholesale

// Get low stock items
const lowStock = await getLowStockItemsOffline(false);

// Get expiring items (within 30 days)
const expiring = await getExpiringItemsOffline(30, false);
```

### Manual Sync Trigger

```javascript
// Trigger sync manually
if (window.offlineHandler) {
    await window.offlineHandler.manualSync();
}

// Or use sync manager directly
if (window.syncManager) {
    await window.syncManager.performFullSync();
}
```

---

## Adding a Manual Sync Button

Add this to any template:

```html
<button onclick="triggerManualSync()" class="btn btn-primary">
    <i class="fas fa-sync"></i> Sync Now
</button>

<script>
async function triggerManualSync() {
    if (!window.offlineHandler) {
        alert('Offline functionality not available');
        return;
    }

    const success = await window.offlineHandler.manualSync();

    if (success) {
        console.log('Sync completed successfully');
    }
}
</script>
```

---

## Troubleshooting

### Problem: Offline mode not working
**Solutions:**
1. Check browser console for errors
2. Verify IndexedDB is supported: `'indexedDB' in window`
3. Verify Service Worker is registered: Check DevTools → Application → Service Workers
4. Clear cache and reload: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)

### Problem: Data not syncing
**Solutions:**
1. Check internet connection
2. Check browser console for sync errors
3. Manually trigger sync: Call `window.offlineHandler.manualSync()`
4. Check pending actions: `window.dbManager.getPendingActions()`

### Problem: Service Worker not registering
**Solutions:**
1. Ensure site is served over HTTPS (or localhost)
2. Check `/sw.js` is accessible
3. Check for JavaScript errors in console
4. Verify service worker scope in DevTools

### Problem: Sync failing with CSRF errors
**Solutions:**
1. Verify CSRF token is present in cookies
2. Check Django CSRF middleware is enabled
3. Ensure `X-CSRFToken` header is sent in requests

---

## Testing Offline Mode

### Chrome DevTools Method
1. Open Chrome DevTools (F12)
2. Go to **Network** tab
3. Select **Offline** from throttling dropdown
4. Test application functionality
5. Switch back to **Online** and verify sync

### Manual Testing Steps
1. ✅ Add items to cart while online → verify success
2. ✅ Disconnect internet
3. ✅ Verify status indicator shows "Offline"
4. ✅ Add more items to cart → verify they're queued
5. ✅ Check pending actions count
6. ✅ Reconnect internet
7. ✅ Verify automatic sync occurs
8. ✅ Verify all changes reflected in database
9. ✅ Verify pending count returns to 0

---

## Performance Considerations

### Cache Management
- Service Worker caches up to **50MB** of data
- Old caches automatically deleted on version upgrade
- IndexedDB has no practical size limit (browser-dependent)

### Sync Frequency
- **Automatic:** Triggered when connection restored
- **Background:** Every 5 minutes when online
- **Manual:** User can trigger anytime

### Optimization Tips
1. **Limit bulk operations** - Sync in batches to avoid timeout
2. **Priority queuing** - Critical actions sync first
3. **Retry logic** - Failed actions retry up to 3 times
4. **Data freshness** - Download initial data only on first load

---

## Security Considerations

### CSRF Protection
All API requests include Django CSRF token from cookies

### Data Validation
Server validates all synced data before saving

### User Authentication
Offline operations tied to authenticated user ID

### Sensitive Data
Payment and financial data requires online connection

---

## Browser Compatibility

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| Service Worker | ✅ | ✅ | ✅ | ✅ |
| IndexedDB | ✅ | ✅ | ✅ | ✅ |
| Background Sync | ✅ | ❌ | ❌ | ✅ |
| Push Notifications | ✅ | ✅ | ✅ | ✅ |

**Note:** Without Background Sync, fallback to manual/periodic sync is used.

---

## Future Enhancements

- [ ] Offline sales transaction processing
- [ ] Offline receipt generation
- [ ] Conflict resolution UI
- [ ] Sync progress indicators
- [ ] Selective data download (reduce initial load)
- [ ] Push notifications for sync completion
- [ ] Export/import offline data

---

## Support

For issues or questions:
1. Check browser console for error messages
2. Review this documentation
3. Contact system administrator
4. File bug report with detailed logs

---

## Summary

PharmApp's offline functionality provides:
- ✅ **Zero-downtime** cart and inventory operations
- ✅ **Automatic sync** when connection restored
- ✅ **Visual feedback** for all operations
- ✅ **Data integrity** with retry and conflict handling
- ✅ **Browser-native** technology (no plugins required)

Users can work seamlessly regardless of internet connectivity!
