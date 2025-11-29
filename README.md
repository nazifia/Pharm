# PharmApp - Pharmacy Management System

A comprehensive Django-based pharmacy management system supporting both retail and wholesale operations with offline-first capabilities, designed specifically for pharmaceutical operations in Africa/Lagos timezone.

## 🚀 Features

### Core Functionality
- **Dual-Mode Operations**: Separate retail and wholesale workflows
- **Role-Based Access Control**: 9 distinct user roles with granular permissions
- **Mobile-First Authentication**: Phone number based login system
- **Offline-First Architecture**: Continue working without internet connection
- **Real-time Sync**: Automatic data synchronization when online
- **Comprehensive Inventory Management**: Stock tracking, expiry monitoring, low-stock alerts
- **Digital Wallet System**: Customer wallets for both retail and wholesale
- **Multi-Payment Support**: Cash, Transfer, Wallet with split payments
- **Barcode Scanning**: Hardware and software scanner integration
- **Advanced Reporting**: Sales, inventory, and financial reports

### Business Workflows

#### 1. Dispenser → Cashier Workflow
- Dispenser adds items to cart and sends to cashier
- PaymentRequest created linking dispenser and cashier
- Cashier accepts/rejects requests and processes payments
- Automatic receipt generation and inventory updates

#### 2. Procurement Management
- Create and manage procurement orders
- Automatic cost calculation with markup support
- Item distribution to retail/wholesale inventory
- Supplier management and analytics

#### 3. Stock Management
- Physical stock checks with discrepancy tracking
- Automated stock adjustments
- Low stock notifications
- Expiry date monitoring

#### 4. Customer & Wallet System
- Digital wallet for each customer
- Transaction history tracking
- Negative balance monitoring
- Split payment support across multiple methods

## 🛠️ Technology Stack

- **Backend**: Django 5.1.5 with Python 3.12+
- **Database**: SQLite (default) with MySQL support
- **Frontend**: Bootstrap 5 with Crispy Forms
- **Real-time**: HTMX for dynamic interactions
- **Offline**: Service Worker with IndexedDB
- **API**: RESTful endpoints for mobile app sync
- **Security**: Role-based permissions, session validation, CORS support

## 📱 Mobile Integration

PharmApp includes comprehensive offline-first capabilities:
- Service Worker for caching and background sync
- IndexedDB for client-side data storage
- Automatic sync when connectivity restored
- Capacitor-ready for mobile app deployment

## 🏗️ System Architecture

### Django Apps Structure
- **store** - Retail pharmacy operations
- **wholesale** - Wholesale operations (parallel to retail)
- **userauth** - Custom authentication with role-based permissions
- **customer** - Customer management with wallet system
- **supplier** - Supplier management and procurement
- **chat** - Internal communication system
- **notebook** - Note-taking and knowledge management
- **api** - REST endpoints for offline-sync

### Database Configuration
- Dual database setup: Main (default) + Offline (SQLite)
- Connection pooling for performance
- Comprehensive indexing for fast searches
- Atomic transactions for data integrity

## 🔐 Security Features

- 20-minute auto-logout on inactivity
- Session hijacking prevention
- IP and user agent tracking
- Role-based URL access control
- XSS and CSRF protection
- Secure cookie configuration
- Activity logging for audit trails

## 📊 Performance Optimizations

- Database query monitoring (>50 query warning)
- Response time tracking (>1s warning)
- Search result caching (5 minutes)
- Select/prefetch related optimization
- Connection pooling (60s reuse)

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- pip
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pharmapp
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Database setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**
   ```bash
   python manage.py collectstatic --noinput
   ```

8. **Run the development server**
   ```bash
   python manage.py runserver
   ```

### Default Configuration
- **URL**: http://127.0.0.1:8000
- **Admin**: http://127.0.0.1:8000/admin
- **Timezone**: Africa/Lagos
- **Session Timeout**: 20 minutes

## 👥 User Roles & Permissions

### Retail Roles
1. **Admin** - Full system access
2. **Manager** - Financial reports, inventory, procurement approval
3. **Pharmacist** - Medication dispensing, inventory, sales
4. **Pharm-Tech** - Inventory, sales, stock checks
5. **Salesperson** - Basic sales operations
6. **Cashier** - Payment processing only

### Wholesale Roles
7. **Wholesale Manager** - Wholesale-specific admin
8. **Wholesale Operator** - Wholesale inventory and sales
9. **Wholesale Salesperson** - Wholesale sales

### Permission Checking
```python
# Always use these methods
user.has_permission('permission_name')
user.get_permissions()
user.get_role_permissions()
```

## 📱 Mobile App Integration

### API Endpoints
- `GET /api/health/` - Connectivity check
- `GET /api/data/initial/` - Initial offline data
- `POST /api/inventory/sync/` - Inventory sync
- `POST /api/sales/sync/` - Sales sync
- `POST /api/customers/sync/` - Customer sync

### Offline Usage
```javascript
// Queue offline action
await window.offlineHandler.queueAction('add_item', itemData, 5);

// Submit form with offline support
await submitFormWithOffline(form, '/api/items/', 'add_item',
    (result) => showSuccess('Saved!'),
    (error) => showError(error)
);
```

## 🔧 Development Commands

### Database Management
```bash
# Migrate specific app
python manage.py migrate store
python manage.py migrate wholesale

# Django shell
python manage.py shell
```

### Testing
```bash
# Run all tests
python manage.py test

# Test specific app
python manage.py test store
python manage.py test wholesale
```

### Static Files
```bash
# Collect static for production
python manage.py collectstatic --noinput
```

## 🌐 Production Deployment

### Security Settings
When `DEBUG=False`, automatically enables:
- XSS filter
- Content type nosniff
- HSTS with subdomains
- SSL redirect
- Secure cookies
- X-Frame-Options: DENY

### MySQL Configuration
Uncomment MySQL settings in `pharmapp/settings.py` and configure `.env`:
```
DB_NAME=pharmapp_db
DB_USER=pharmapp_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
```

## 📋 Important Notes

### Authentication
- Uses **mobile number** authentication, not username
- Always authenticate with phone number
- Superusers bypass all permission checks

### Inventory Quantities
- All stock quantities use **DecimalField**, not integers
- Supports fractional quantities for medications
- Automatic low stock threshold monitoring

### Session Management
- 20-minute auto-logout
- Session validation on every request
- IP change detection
- User agent tracking

### Offline Database
- Separate SQLite database for offline operations
- Automatic sync when online
- Atomic transactions ensure data integrity

## 📚 Documentation

- [Claude Development Guide](CLAUDE.md) - Comprehensive development documentation
- [Offline Functionality Guide](OFFLINE_FUNCTIONALITY_GUIDE.md) - Detailed offline features
- [Performance Optimizations](PERFORMANCE_OPTIMIZATIONS.md) - Performance tuning guide
- [Database Switching Guide](DATABASE_SWITCHING_GUIDE.md) - MySQL setup instructions
- [Hardware Scanner Guide](HARDWARE_SCANNER_GUIDE.md) - Barcode scanner integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python manage.py test`
5. Submit a pull request

## 📄 License

This project is proprietary and confidential.

## 🆘 Support

For technical support and questions, refer to the development documentation in `CLAUDE.md` or the implementation guides in the repository.

---

**PharmApp** - Modern Pharmacy Management for Africa 🌍
