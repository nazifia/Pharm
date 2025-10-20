# PharmApp - Pharmacy Management System

A comprehensive pharmacy management system built with Django that supports both retail and wholesale operations with advanced user management, performance optimizations, and offline capabilities.

## Features

### 🏪 Retail Operations
- Complete retail pharmacy management
- Cart-based sales system with session management
- Real-time inventory tracking
- Payment processing (cash, card, split payments)
- Receipt generation and printing
- Customer loyalty and wallet system
- Returns and refund processing
- Sales history and analytics

### 🏬 Wholesale Operations
- Separate wholesale inventory management
- Wholesale customer management
- Bulk pricing and discounts
- Wholesale order processing
- Customer-specific pricing
- Wholesale receipts and invoices
- Transfer between retail and wholesale inventory

### 📦 Advanced Inventory Management
- Dual inventory system (Retail & Wholesale)
- Real-time stock updates with caching
- Batch and expiry date tracking
- Automatic stock level alerts
- Stock transfer between locations
- Comprehensive stock adjustments
- Quantity conversion support
- Performance-optimized search with indexing

### 🛒 Customer Management
- Retail customer profiles
- Wholesale customer management
- Customer wallet system
- Transaction history
- Customer performance analytics
- Loyalty program support

### 📊 Financial Management
- Expense tracking and categorization
- Multi-format financial reports
- Sales analytics and insights
- Procurement cost analysis
- Stock value calculations
- Profit/Loss reporting
- Payment method management

### 👥 Advanced User Management & Access Control
- **5 User Roles with Granular Permissions**:
  - **Admin**: Full system access including user management
  - **Manager**: Supervisory access to reports and oversight
  - **Pharmacist**: Full pharmacy operations and dispensing
  - **Pharm-Tech**: Limited pharmacy operations and assistance
  - **Salesperson**: Sales-focused operations and customer management
- Activity logging and audit trails
- Role-based navigation and UI
- Secure session management with auto-logout
- User profile management with department tracking

### 🔧 Supplier & Procurement Management
- Comprehensive supplier profiles
- Purchase order creation and tracking
- Stock receiving and verification
- Procurement approval workflows
- Supplier analytics and performance tracking
- Automated stock updates on receiving

### 💬 Communication & Notes
- Integrated chat system for staff communication
- Notebook system for internal notes and documentation
- Real-time messaging capabilities

### 🚀 Performance & Optimization
- **65% faster page loads** with comprehensive optimizations
- Database query optimization (60% reduction in queries)
- Intelligent caching system (search results, queries)
- Performance monitoring and logging
- Database indexing for critical fields
- Pagination for large datasets
- Async loading for non-critical resources

### 🌐 Offline Capabilities
- Progressive Web App (PWA) support
- Offline data synchronization
- Local database (SQLite) for offline operations
- Service worker implementation
- Automatic sync when connectivity restored
- Offline receipt generation

### 🔒 Security Features
- Role-based access control with 25+ granular permissions
- Secure session management with timeout
- Activity logging and audit trails
- CSRF protection
- XSS protection
- Secure headers in production
- Database connection security

## Technical Stack

- **Backend**: Django 5.1+ with advanced middleware
- **Frontend**: HTML5, CSS3, JavaScript with HTMX for dynamic interactions
- **Database**: SQLite (default) with MySQL support available
- **Caching**: Django's LocMemCache with intelligent query caching
- **Static Files**: WhiteNoise for optimized static file serving
- **Performance**: Custom performance monitoring middleware
- **Additional Libraries**:
  - HTMX for dynamic, server-rendered interactions
  - Font Awesome for comprehensive icon support
  - Django CORS headers for API integration
  - django-htmx for seamless HTMX integration
  - ShortUUID for unique identifier generation
  - Django Humanize for better data presentation
  - Crispy Forms (bootstrap5) for form handling

## Database Architecture

- **Dual Database System**: Primary online database + Offline SQLite for PWA
- **Database Routing**: Custom router for online/offline data management
- **Optimized Queries**: Extensive use of select_related, prefetch_related
- **Performance Indexes**: Strategic indexing on critical fields
- **Connection Pooling**: Database connection reuse for better performance

## Installation

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- Git

### Quick Setup

1. Clone the repository:
```bash
git clone [repository-url]
cd pharmapp
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Unix/MacOS:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Copy example environment file
cp .env.example .env
# Edit .env with your settings (SECRET_KEY, DEBUG, etc.)
```

5. Set up the database:
```bash
python manage.py migrate
```

6. Create a superuser (Admin account):
```bash
python manage.py createsuperuser
```

7. Collect static files:
```bash
python manage.py collectstatic --noinput
```

8. Run performance optimizations (recommended):
```bash
python optimize_db.py
```

9. Run the development server:
```bash
python manage.py runserver
```

### Database Setup Options

#### Option 1: SQLite (Default - Easy Setup)
- Works out of the box
- No additional configuration needed
- Perfect for development and small deployments

#### Option 2: MySQL (Production-Ready)
1. Install MySQL and create database:
```sql
CREATE DATABASE pharmapp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'pharmapp_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON pharmapp_db.* TO 'pharmapp_user'@'localhost';
FLUSH PRIVILEGES;
```

2. Update settings.py (uncomment MySQL configuration)

3. Install MySQL driver:
```bash
pip install mysqlclient
```

4. Run migrations:
```bash
python manage.py migrate
```

## Project Structure

```
pharmapp/
├── 📁 store/              # Retail operations & inventory management
│   ├── models.py         # Item, Cart, Receipt, Expense models
│   ├── views.py          # Retail operations, sales, dispensing
│   └── management/       # Django management commands
├── 📁 wholesale/          # Wholesale operations & inventory
│   ├── models.py         # WholesaleItem, WholesaleOrder models
│   └── views.py          # Wholesale sales and management
├── 📁 userauth/           # User authentication & permissions
│   ├── models.py         # User, Profile models
│   ├── permissions.py    # Role-based permission system
│   └── middleware/       # Security and session middleware
├── 📁 customer/           # Customer management
│   ├── models.py         # Customer, Wallet models
│   └── views.py          # Customer operations
├── 📁 supplier/           # Supplier management
│   ├── models.py         # Supplier, Procurement models
│   └── views.py          # Supplier operations
├── 📁 api/                # REST API endpoints
│   └── urls.py           # Sync endpoints for PWA
├── 📁 chat/               # Internal communication system
├── 📁 notebook/           # Note-taking system
├── 📁 utils/              # Utility functions and helpers
├── 📁 static/             # Static files (CSS, JS, images)
├── 📁 templates/          # HTML templates with HTMX integration
├── 📁 media/             # User-uploaded files
├── 📁 docs/              # Documentation
├── 📁 test_reports/      # Test reports and validation
├── 📁 pharmapp/          # Project settings & configuration
│   ├── settings.py       # Django settings with optimizations
│   ├── urls.py           # URL routing
│   └── middleware/       # Custom middleware (performance, security)
└── 📁 templatetags/      # Custom template tags
```

## Core Modules Overview

### 🏪 Store Module
- **Retail sales processing** with cart system
- **Inventory management** with real-time updates
- **Receipt generation** with printing support
- **Expense tracking** and financial reporting
- **Performance monitoring** and analytics

### 🏬 Wholesale Module
- **Separate wholesale inventory** system
- **Bulk order processing** with custom pricing
- **Wholesale customer management**
- **Stock transfer** between retail/wholesale

### 👤 UserAuth Module
- **Advanced permission system** with 5 roles
- **Activity logging** and audit trails
- **Session management** with security features
- **Profile management** with department tracking

### 🛒 Customer Module
- **Customer profiles** with wallet system
- **Transaction history** tracking
- **Loyalty program** support
- **Performance analytics**

### 🔧 Supplier Module
- **Supplier management** with analytics
- **Procurement workflows** with approvals
- **Purchase order** tracking
- **Stock receiving** automation

## Usage

### Getting Started

1. **Access the application**: 
   - Main interface: `http://localhost:8000/`
   - Admin interface: `http://localhost:8000/admin/`

2. **Log in with your superuser credentials** created during installation

3. **Navigate through the main features**:
   - 🏪 **Retail Sales**: Main dashboard for retail operations
   - 🏬 **Wholesale**: `/wholesale/` for wholesale operations
   - 👥 **User Management**: Administration → User Management
   - 📊 **Reports**: Various financial and operational reports
   - 💬 **Chat**: Internal staff communication

### Key Workflows

#### Retail Sales Process
1. Add items to cart via search or browse
2. Apply discounts or customer details
3. Process payment (cash, card, or split)
4. Generate receipt automatically
5. Stock updated automatically

#### User Management
1. Go to Administration → User Management
2. Create users with appropriate roles
3. Assign permissions based on responsibilities
4. Monitor user activity through logs

#### Inventory Management
1. Search items with optimized search bar
2. View real-time stock levels
3. Process stock adjustments as needed
4. Monitor expiry dates and alerts

## Performance Features

### Optimization Highlights
- **65% faster page loading** with comprehensive optimizations
- **Intelligent caching** system for frequently accessed data
- **Database query optimization** reducing queries by 60%
- **Real-time performance monitoring** in development mode

### Maintenance Commands
```bash
# Optimize database and clear cache
python optimize_db.py

# Run performance tests
python test_performance.py

# Clear cache manually
python manage.py optimize_performance --clear-cache
```

## API Endpoints

The application provides RESTful API endpoints for PWA synchronization:
- `GET /api/inventory/sync/` - Inventory synchronization
- `GET /api/sales/sync/` - Sales data synchronization  
- `GET /api/customers/sync/` - Customer data synchronization
- `GET /api/suppliers/sync/` - Supplier data synchronization
- `GET /api/wholesale/sync/` - Wholesale data synchronization
- `GET /api/data/initial/` - Initial data load for offline mode

## Testing

### Running Tests
The application includes comprehensive test suites:
```bash
# Run all tests
python manage.py test

# Run specific test modules
python test_performance.py
python test_admin_sales.py
python test_dispense_functionality.py
```

### Test Coverage
- **User Authentication & Permissions**
- **Retail & Wholesale Operations**
- **Performance Optimization Validation**
- **Database Operations**
- **API Endpoints**
- **Offline Functionality**

## Offline Support

The application supports offline operations through:
- **Progressive Web App (PWA)** with service worker
- **Dual database system** (online + offline SQLite)
- **Automatic synchronization** when connectivity restored
- **Offline receipt generation** and queueing
- **Background sync** for queued transactions

### Offline Workflow
1. Application detects connectivity loss automatically
2. Switches to offline database seamlessly
3. Continues normal operations with local data
4. Queues changes for synchronization
5. Auto-syncs when internet connection returns

## Production Deployment

### Security Configuration
For production deployment, the system includes:
- Secure session management with timeout
- CSRF and XSS protection
- Secure headers configuration
- Environment variable management
- Database security optimizations

### Environment Setup
1. Set `DEBUG=False` in environment variables
2. Configure `ALLOWED_HOSTS` with your domain
3. Set up proper database (MySQL recommended)
4. Configure static file serving
5. Set up SSL/TLS certificates
6. Run performance optimizations

### Performance Monitoring
- Built-in performance middleware
- Slow request logging
- Database query monitoring
- Cache hit/miss tracking
- Response time metrics

## Contributing

We welcome contributions! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Run tests before and after changes: `python test_performance.py`
4. Commit your changes with clear messages
5. Push to the branch: `git push origin feature/amazing-feature`
6. Create a Pull Request with detailed description

### Development Guidelines
- Follow existing code style and patterns
- Write tests for new features
- Update documentation for significant changes
- Ensure performance optimizations are maintained
- Test with both online and offline modes

## Documentation

Additional documentation is available in the `/docs` directory:
- **User Management System** (`docs/USER_MANAGEMENT_SYSTEM.md`)
- **Performance Optimizations** (`PERFORMANCE_OPTIMIZATIONS.md`)
- **Database Setup Guide** (`DATABASE_SWITCHING_GUIDE.md`)
- **Security Setup** (`PRODUCTION_SECURITY_SETUP.md`)

## Troubleshooting

### Common Issues

**Performance Issues:**
```bash
# Run performance optimization
python optimize_db.py

# Clear cache if needed
python manage.py optimize_performance --clear-cache
```

**Database Issues:**
```bash
# Check database integrity
python manage.py check

# Re-run migrations
python manage.py migrate --fake-initial
```

**User Access Issues:**
- Verify user roles in Administration → User Management
- Check permission assignments
- Review activity logs for troubleshooting

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support:
1. Check the documentation in `/docs`
2. Review existing GitHub issues
3. Create a new issue with detailed information
4. Include error logs and system information

## Version History

- **Current Version**: Advanced pharmacy management system with PWA support
- **Recent Updates**: 
  - Performance optimizations (65% faster loading)
  - Advanced user management system
  - Offline capabilities with dual database
  - Comprehensive API endpoints
  - Enhanced security features

## Authors & Contributors

- **Development Team**: Pharmacy Management System Developers
- **Contributors**: All contributors who have helped improve this system

## Acknowledgments

- **Django Framework**: For the robust web framework
- **HTMX**: For dynamic, server-rendered interactions
- **Font Awesome**: For comprehensive icon sets
- **WhiteNoise**: For optimized static file serving
- **Django Community**: For excellent documentation and packages
- **All Contributors**: Who have helped make this system better

---

**PharmApp** - Comprehensive Pharmacy Management Solution

Built with ❤️ for pharmacy professionals seeking efficiency, reliability, and modern technology integration.