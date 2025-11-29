# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **dual-mode Django pharmacy management system** supporting both **retail** and **wholesale** operations with offline-sync capabilities, designed for pharmaceutical operations in Africa/Lagos timezone.

## Development Commands

### Running the Server
```bash
python manage.py runserver
```

### Database Management
```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Migrate specific app
python manage.py migrate store
python manage.py migrate wholesale

# Create superuser
python manage.py createsuperuser
```

### Static Files
```bash
# Collect static files for production
python manage.py collectstatic --noinput
```

### Testing
```bash
# Run all tests
python manage.py test

# Test specific app
python manage.py test store
python manage.py test userauth
python manage.py test wholesale

# Test specific test case
python manage.py test store.tests.TestInventoryManagement
```

### Shell Access
```bash
# Django shell
python manage.py shell

# Shell with imports
python manage.py shell_plus  # if django-extensions installed
```

## Core Architecture

### Django Apps Structure

**Primary Apps:**
- **store** - Retail pharmacy operations (inventory, sales, receipts, stock management)
- **wholesale** - Wholesale operations (parallel structure to retail for bulk sales)
- **userauth** - Custom authentication with phone number login and role-based permissions
- **customer** - Customer management with digital wallet system (retail & wholesale)
- **supplier** - Supplier management and procurement workflows
- **chat** - Internal communication with rich messaging features
- **notebook** - Note-taking and knowledge management
- **api** - REST API endpoints for offline-sync with mobile apps

### Authentication System

**Critical:** This system uses **mobile number authentication**, not username.
- `USERNAME_FIELD = 'mobile'` in User model
- Always authenticate with phone number

**Role Hierarchy:**
1. Admin - Full system access
2. Manager - Financial reports, inventory, procurement approval
3. Pharmacist - Medication dispensing, inventory, sales
4. Pharm-Tech - Inventory, sales, stock checks
5. Salesperson - Basic sales operations
6. Cashier - Payment processing only (separate user type)
7. Wholesale Manager - Wholesale-specific admin
8. Wholesale Operator - Wholesale inventory and sales
9. Wholesale Salesperson - Wholesale sales

**Permission Checking:**
```python
# ALWAYS use these methods for permission checks
user.has_permission('permission_name')  # Check single permission
user.get_permissions()  # Get all effective permissions
user.get_role_permissions()  # Get role-based only
user.get_individual_permissions()  # Get user-specific overrides

# Superusers bypass all permission checks automatically
```

**Important Permission Patterns:**
- Retail/Wholesale separation: `operate_retail` vs `operate_wholesale` vs `operate_all`
- Most users have ONE mode, not both
- Separate permissions for customers, procurement, stock checks, expiry per mode
- Individual permissions (UserPermission model) override role-based permissions

### Dual-Store Pattern (Retail/Wholesale)

Nearly identical models exist for both modes:
- `Item` / `WholesaleItem`
- `Cart` / `WholesaleCart`
- `SalesItem` / `WholesaleSalesItem`
- `Receipt` / `WholesaleReceipt`
- `Customer` / `WholesaleCustomer`
- `Wallet` / `WholesaleCustomerWallet`

**Shared models:**
- `Sales` - Used by both modes with discriminator fields
- `Notification` - System-wide alerts
- `User`, `Profile`, `ActivityLog` - Authentication/tracking

**Transfer System:**
- `TransferRequest` model handles inter-store transfers
- Supports retail ↔ wholesale item movement
- Requires approval workflow

### Critical Business Workflows

#### 1. Dispenser → Cashier Workflow
```
1. Dispenser adds items to cart
2. Dispenser sends cart to cashier (cart.status = 'sent_to_cashier')
3. PaymentRequest created linking dispenser and cashier
4. Cashier accepts/rejects request
5. Cashier processes payment → generates Receipt
6. Items move from Cart to DispensingLog
```

#### 2. Procurement Flow
```
1. Create Procurement (status: 'draft' or 'completed')
2. Add ProcurementItem with cost, markup %, expiry date
3. Signals auto-calculate subtotals and procurement total
4. If status='completed', items auto-move to StoreItem
5. StoreItem → distributed to retail or wholesale inventory
```

#### 3. Stock Check & Adjustment
```
1. Create StockCheck (physical count)
2. Add StockCheckItem for each item with actual_quantity
3. System calculates discrepancies (expected vs actual)
4. Approval process (pending → approved)
5. StockAdjustment records created for audit trail
6. Item.stock updated atomically
```

#### 4. Wallet System
```
- Digital wallet per customer (retail & wholesale separate)
- TransactionHistory tracks all wallet operations
- Negative balance tracking (wallet_went_negative flag)
- Payment method='Wallet' deducts from balance during sales
- Add funds via customer management interface
```

#### 5. Split Payment Support
```
- Receipt can have multiple ReceiptPayment/WholesaleReceiptPayment records
- Each payment: method (Cash/Wallet/Transfer) + amount + status
- Receipt status auto-calculated: Paid, Partially Paid, Unpaid
- Based on: sum(payments.amount) vs receipt.total_amount
```

### Database Configuration

**Dual Database Setup:**
- `default` - Main database (SQLite by default, can swap to MySQL via settings)
- `offline` - Separate SQLite for offline operations
- `DATABASE_ROUTERS = ['pharmapp.routers.OfflineRouter']`

**To switch to MySQL:**
Uncomment MySQL config in `pharmapp/settings.py` lines 266-290 and configure `.env`:
```
DB_NAME=pharmapp_db
DB_USER=pharmapp_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
```

### Session & Security

**Session Configuration:**
- 20-minute auto-logout on inactivity
- Session age: 1200s (20 minutes)
- `SESSION_SAVE_EVERY_REQUEST = True` - Resets expiration on each request
- Session validation middleware checks for session hijacking
- IP change detection and user agent tracking

**Critical Security Middleware (in order):**
1. `CorsMiddleware` - CORS for mobile apps
2. `PerformanceMonitoringMiddleware` - Response time tracking
3. `QueryCountMiddleware` - Database query monitoring (warns >50)
4. `ConnectionDetectionMiddleware` - Online/offline detection
5. `ActivityMiddleware` - Logs all user actions to ActivityLog
6. `RoleBasedAccessMiddleware` - URL-level role enforcement
7. `AutoLogoutMiddleware` - 20-minute inactivity timeout
8. `SessionValidationMiddleware` - Anti-hijacking protection
9. `UserActivityTrackingMiddleware` - Session activity tracking
10. `SessionCleanupMiddleware` - Expired session cleanup

### Offline-Sync API

**Mobile app integration (Capacitor):**
- CORS allowed: `capacitor://localhost`
- API endpoints under `/api/`:
  - `POST /api/inventory/sync/` - Sync inventory changes
  - `POST /api/sales/sync/` - Sync sales transactions
  - `POST /api/customers/sync/` - Sync customer data
  - `GET /api/data/initial/` - Bootstrap offline cache

**Offline workflow:**
1. Mobile app uses `offline` database when disconnected
2. Queues pending actions locally
3. On reconnect, syncs to `default` database via API
4. Atomic transactions ensure data integrity

### Key Models & Fields

#### Stock Management
- All inventory models use **DecimalField** for quantities (not integers)
- `Item.stock`, `WholesaleItem.stock` - Current inventory level
- `low_stock_threshold` - Triggers low stock notifications
- `exp_date` - Expiry date tracking (DateField)

#### Discount Support
- `Cart.discount_amount`, `SalesItem.discount_amount`, `DispensingLog.discount_amount`
- Subtotal calculated as: `(price × quantity) - discount_amount`
- Never negative: `max(subtotal, 0)`

#### Return Tracking
- `Sales.is_returned`, `Receipt.has_returns`, `DispensingLog.is_returned`
- Fields: `return_date`, `return_amount`, `return_processed_by`
- Related returns tracked via DispensingLog

#### ShortUUID Patterns
- Cart: `'CID: ' + 5 digits`
- Receipt: `5 digits` (no prefix)
- Cashier: `'CSH:' + 8 digits`
- PaymentRequest: `'PRQ:' + 8 digits`

### Performance Optimizations

**Database:**
- Connection pooling: `CONN_MAX_AGE = 60` (reuse for 60s)
- Indexes on: `name`, `brand`, `dosage_form` for fast search
- Composite indexes for common query patterns
- Use `select_related()` / `prefetch_related()` to avoid N+1 queries

**Caching:**
- LocMemCache (in-memory, max 2000 entries)
- Search results cached 5 minutes
- Performance metrics cached per request

**Monitoring:**
- Performance middleware adds headers: `X-Response-Time`, `X-DB-Queries`
- Warns if response >1s or queries >50
- Available in templates via `performance_metrics` context

### Template Context

**Available in ALL templates (via context processors):**
- All `can_*` permission checks (e.g., `can_manage_users`)
- All `is_*` role checks (e.g., `is_admin`, `is_manager`)
- `user_role` - Current user's role name
- `user_permissions` - List of permission names
- `marquee_text` - Global marquee message (cached)
- `performance_metrics` - Query count & response time (DEBUG only)

### Common Patterns

#### Always Check Authentication First
```python
# CORRECT
if user.is_authenticated:
    profile = user.profile  # Safe

# INCORRECT - Can raise RelatedObjectDoesNotExist
profile = user.profile
```

#### Create Default Profile if Missing
```python
from userauth.models import Profile
profile, created = Profile.objects.get_or_create(
    user=user,
    defaults={'role': 'Salesperson'}  # Default role
)
```

#### Use Atomic Transactions for Stock Updates
```python
from django.db import transaction

with transaction.atomic():
    item = Item.objects.select_for_update().get(id=item_id)
    item.stock -= quantity
    item.save()
```

#### Notification Creation
```python
from store.models import Notification

Notification.objects.create(
    user=user,  # Or None for system-wide
    notification_type='low_stock',
    priority='high',
    title='Low Stock Alert',
    message=f'{item.name} is running low',
    related_object_type='item',
    related_object_id=item.id
)
```

### Important Constants

- **Timezone:** `'Africa/Lagos'`
- **Auto-logout:** 20 minutes (1200 seconds)
- **Session age:** 20 minutes
- **Max form fields:** 10,000
- **File upload max:** 5MB
- **Query warning threshold:** 50 queries per request
- **Response time warning:** 1 second

### Testing Considerations

When writing tests:
- Use `self.client.force_login(user)` for authenticated tests
- Create test users with specific roles via `Profile.objects.create()`
- Test both retail and wholesale modes separately
- Mock offline database routing for sync tests
- Test permission checks for each role level
- Verify atomic transactions for stock operations

### Common Gotchas

1. **Username vs Mobile:** Never use `username` for authentication - use `mobile` field
2. **Profile Creation:** Always create Profile after creating User (or use signals)
3. **Superuser Permissions:** Superusers bypass ALL permission checks
4. **Decimal Quantities:** Stock quantities are Decimal, not integers
5. **Session Engine Conflict:** Settings has two `SESSION_ENGINE` definitions (line 294 and 319) - database sessions win
6. **Crispy Forms:** Comments say "Removed" but still in INSTALLED_APPS - functionally unused
7. **Channels:** WebSocket support commented out - don't use channels routing
8. **Activity Logging:** All user actions auto-logged - no manual logging needed
9. **Cart Status:** Check cart.status before processing (`'active'`, `'sent_to_cashier'`, `'processed'`)
10. **Markup Percentage:** Procurement markup is 0-100%, not decimal (50 = 50%, not 0.50)

### Environment Variables

Required in `.env` file:
```
SECRET_KEY=your-secret-key-here
DEBUG=True  # or False for production
ALLOWED_HOSTS=localhost,127.0.0.1

# Optional - for MySQL
DB_NAME=pharmapp_db
DB_USER=pharmapp_user
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=3306
```

### Offline-First Functionality

PharmApp includes comprehensive offline-first capabilities:

### Architecture
- **Service Worker** (`static/js/sw.js`) - Offline caching and background sync
- **IndexedDB Manager** (`static/js/indexeddb-manager.js`) - Client-side data storage
- **Sync Manager** (`static/js/sync-manager.js`) - Bidirectional data synchronization
- **Offline Handler** (`static/js/offline-handler.js`) - Coordination and UI updates
- **Helper Functions** (`static/js/offline-helpers.js`) - Convenient wrappers

### Key Features
1. **Automatic offline detection** with visual indicators
2. **Local data persistence** via IndexedDB
3. **Background sync** with automatic retry
4. **Queue-based action system** for offline operations
5. **Conflict resolution** for data integrity

### Basic Usage

Queue an offline action:
```javascript
await window.offlineHandler.queueAction('add_item', itemData, 5);
```

Submit form with offline support:
```javascript
await submitFormWithOffline(form, '/api/items/', 'add_item',
    (result) => showSuccess('Saved!'),
    (error) => showError(error)
);
```

Search offline data:
```javascript
const results = await searchItemsOffline('aspirin');
```

### API Endpoints
- `GET /api/health/` - Health check for connectivity
- `GET /api/data/initial/` - Download initial data for offline cache
- `POST /api/inventory/sync/` - Sync inventory changes
- `POST /api/sales/sync/` - Sync sales
- `POST /api/customers/sync/` - Sync customers
- Additional sync endpoints for all data types

### Action Types
Common action types for queuing:
- Inventory: `add_item`, `update_item`, `delete_item`
- Sales: `add_sale`, `add_receipt`, `add_dispensing`
- Customers: `add_customer`, `update_customer`
- Cart: `add_to_cart`, `update_cart`, `remove_from_cart`
- Wholesale: `add_wholesale_item`, `add_wholesale_sale`

### Documentation
See `OFFLINE_FUNCTIONALITY_GUIDE.md` for comprehensive documentation including:
- Detailed API reference
- Integration examples
- Best practices
- Troubleshooting guide
- Performance considerations

### Testing Offline Mode
1. Open Chrome DevTools (F12)
2. Go to Network tab
3. Select "Offline" from throttling dropdown
4. Test application functionality
5. Go back online and verify sync

## Production Deployment

When `DEBUG=False`, security settings auto-enable:
- XSS filter
- Content type nosniff
- HSTS with subdomains (1 year)
- SSL redirect
- Secure cookies (session and CSRF)
- X-Frame-Options: DENY

Always run `python manage.py collectstatic` before deploying.
