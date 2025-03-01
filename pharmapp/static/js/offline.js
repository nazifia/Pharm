// IndexedDB setup
const DB_NAME = 'PharmAppOfflineDB';
const DB_VERSION = 1;
let db;

// Open the database
function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    
    request.onerror = event => {
      console.error('IndexedDB error:', event.target.errorCode);
      reject('Could not open IndexedDB');
    };
    
    request.onsuccess = event => {
      db = event.target.result;
      console.log('IndexedDB opened successfully');
      resolve(db);
    };
    
    request.onupgradeneeded = event => {
      const db = event.target.result;
      
      // Create object stores
      if (!db.objectStoreNames.contains('offlineActions')) {
        db.createObjectStore('offlineActions', { keyPath: 'id', autoIncrement: true });
      }
      
      if (!db.objectStoreNames.contains('items')) {
        db.createObjectStore('items', { keyPath: 'id' });
      }
      
      if (!db.objectStoreNames.contains('customers')) {
        db.createObjectStore('customers', { keyPath: 'id' });
      }
    };
  });
}

// Check if online
function isOnline() {
  return navigator.onLine;
}

// Save action to be performed when back online
async function saveOfflineAction(actionType, data) {
  try {
    const db = await openDB();
    const tx = db.transaction('offlineActions', 'readwrite');
    const store = tx.objectStore('offlineActions');
    
    const action = {
      actionType,
      data,
      timestamp: new Date().toISOString()
    };
    
    await store.add(action);
    await tx.complete;
    
    console.log('Action saved for offline sync:', action);
    updateOfflineStatus();
    
    return true;
  } catch (error) {
    console.error('Error saving offline action:', error);
    return false;
  }
}

// Get all pending offline actions
async function getPendingActions() {
  try {
    const db = await openDB();
    const tx = db.transaction('offlineActions', 'readonly');
    const store = tx.objectStore('offlineActions');
    
    return await store.getAll();
  } catch (error) {
    console.error('Error getting pending actions:', error);
    return [];
  }
}

// Cache data for offline use
async function cacheData() {
  try {
    if (!isOnline()) {
      console.log('Cannot cache data while offline');
      return false;
    }
    
    // Fetch data from server
    const response = await fetch('/offline/cache-data/');
    if (!response.ok) {
      throw new Error('Failed to fetch data for caching');
    }
    
    const data = await response.json();
    const db = await openDB();
    
    // Cache items
    if (data.items && data.items.length > 0) {
      const itemsTx = db.transaction('items', 'readwrite');
      const itemsStore = itemsTx.objectStore('items');
      
      // Clear existing items
      await itemsStore.clear();
      
      // Add new items
      for (const item of data.items) {
        await itemsStore.add(item);
      }
      
      await itemsTx.complete;
      console.log('Items cached successfully');
    }
    
    // Cache customers
    if (data.customers && data.customers.length > 0) {
      const customersTx = db.transaction('customers', 'readwrite');
      const customersStore = customersTx.objectStore('customers');
      
      // Clear existing customers
      await customersStore.clear();
      
      // Add new customers
      for (const customer of data.customers) {
        await customersStore.add(customer);
      }
      
      await customersTx.complete;
      console.log('Customers cached successfully');
    }
    
    return true;
  } catch (error) {
    console.error('Error caching data:', error);
    return false;
  }
}

// Update UI to show offline status and pending actions
async function updateOfflineStatus() {
  const statusElement = document.getElementById('connection-status');
  if (!statusElement) return;
  
  if (isOnline()) {
    statusElement.innerHTML = '<span class="badge bg-success">Online</span>';
    
    // Check for pending actions
    const pendingActions = await getPendingActions();
    if (pendingActions.length > 0) {
      statusElement.innerHTML += ` <span class="badge bg-warning">${pendingActions.length} pending sync</span>`;
    }
  } else {
    statusElement.innerHTML = '<span class="badge bg-danger">Offline</span>';
    
    // Check for pending actions
    const pendingActions = await getPendingActions();
    if (pendingActions.length > 0) {
      statusElement.innerHTML += ` <span class="badge bg-warning">${pendingActions.length} pending</span>`;
    }
  }
}

// Sync offline actions when back online
async function syncOfflineActions() {
  if (!isOnline()) {
    console.log('Cannot sync while offline');
    return false;
  }
  
  try {
    // Try to use the Background Sync API if available
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
      const registration = await navigator.serviceWorker.ready;
      await registration.sync.register('sync-offline-actions');
      console.log('Sync registered with service worker');
      return true;
    } else {
      // Fallback for browsers that don't support Background Sync
      console.log('Background Sync not supported, using fallback');
      
      const pendingActions = await getPendingActions();
      if (pendingActions.length === 0) {
        console.log('No actions to sync');
        return true;
      }
      
      console.log('Syncing', pendingActions.length, 'offline actions');
      
      // Get CSRF token
      const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
      
      // Send actions to server
      const response = await fetch('/offline/sync/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ actions: pendingActions })
      });
      
      if (response.ok) {
        // Clear synced actions
        const db = await openDB();
        const tx = db.transaction('offlineActions', 'readwrite');
        await tx.objectStore('offlineActions').clear();
        await tx.complete;
        
        console.log('Sync completed successfully');
        updateOfflineStatus();
        
        // Show success message
        showNotification('Sync Complete!', 'Your offline actions have been synchronized.', 'success');
        
        // Reload page after a short delay to show updated data
        setTimeout(() => {
          window.location.reload();
        }, 2000);
        
        return true;
      } else {
        console.error('Sync failed:', await response.text());
        return false;
      }
    }
  } catch (error) {
    console.error('Error during sync:', error);
    return false;
  }
}

// Show notification
function showNotification(title, message, type = 'info') {
  const container = document.querySelector('.container') || document.body;
  
  const alertDiv = document.createElement('div');
  alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
  alertDiv.innerHTML = `
    <strong>${title}</strong> ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;
  
  container.prepend(alertDiv);
  
  // Auto-dismiss after 5 seconds
  setTimeout(() => {
    alertDiv.classList.remove('show');
    setTimeout(() => alertDiv.remove(), 150);
  }, 5000);
}

// Register event listeners
document.addEventListener('DOMContentLoaded', async () => {
  // Initialize IndexedDB
  await openDB();
  
  // Cache data on load if online
  if (isOnline()) {
    await cacheData();
  }
  
  // Update offline status
  updateOfflineStatus();
  
  // Add event listeners for online/offline events
  window.addEventListener('online', () => {
    console.log('Back online');
    updateOfflineStatus();
    
    // Try to sync when back online
    syncOfflineActions();
  });
  
  window.addEventListener('offline', () => {
    console.log('Gone offline');
    updateOfflineStatus();
  });
  
  // Add sync button if it exists
  const syncButton = document.getElementById('sync-button');
  if (syncButton) {
    syncButton.addEventListener('click', () => {
      syncOfflineActions();
    });
  }
  
  // Listen for messages from service worker
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', event => {
      if (event.data.type === 'SYNC_COMPLETED') {
        console.log('Received sync completion message from service worker');
        updateOfflineStatus();
        
        if (event.data.success) {
          // Show success message
          showNotification('Sync Complete!', 'Your offline actions have been synchronized.', 'success');
          
          // Reload page after a short delay
          setTimeout(() => {
            window.location.reload();
          }, 2000);
        }
      }
    });
  }
});

// Register service worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/js/sw.js')
      .then(registration => {
        console.log('ServiceWorker registration successful with scope:', registration.scope);
      })
      .catch(error => {
        console.error('ServiceWorker registration failed:', error);
      });
  });
}

// Export functions for use in other scripts
window.offlineUtils = {
  isOnline,
  saveOfflineAction,
  getPendingActions,
  syncOfflineActions
};
