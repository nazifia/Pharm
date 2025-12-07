# PharmApp Presentation Note

## Overview
PharmApp is a comprehensive **dual-mode Django pharmacy management system** designed specifically for pharmaceutical operations in Africa/Lagos timezone, supporting both **retail and wholesale operations** with robust offline-sync capabilities.

## Core Features

### 1. Dual-Store Architecture
- **Retail Operations**: Full pharmacy management for customer-facing operations
- **Wholesale Operations**: Parallel structure for bulk pharmaceutical sales
- **Transfer System**: Seamless item movement between retail and wholesale with approval workflow
- **Shared Models**: Unified user management, notifications, and activity tracking

### 2. Advanced Authentication & Permissions
- **Mobile Number Authentication**: Uses phone numbers instead of usernames
- **Role-Based Access Control**: 9 distinct user roles (Admin, Manager, Pharmacist, etc.)
- **Permission Granularity**: Fine-grained permissions for retail/wholesale separation
- **Session Security**: 20-minute auto-logout with anti-hijacking protection

### 3. Comprehensive Business Workflows
- **Dispenser → Cashier Flow**: Complete medication dispensing workflow
- **Procurement Management**: Full purchasing with markup calculations and expiry tracking
- **Stock Management**: Physical counts, adjustments, and discrepancy tracking
- **Digital Wallet System**: Customer wallets with transaction history and negative balance tracking
- **Split Payment Support**: Multiple payment methods per transaction (Cash/Wallet/Transfer)

### 4. Offline-First Architecture
- **Service Worker**: Offline caching and background sync
- **IndexedDB**: Client-side data persistence
- **Queue-Based Actions**: Offline operations with automatic retry
- **Automatic Sync**: Bidirectional synchronization when connection restored

### 5. Performance Optimizations
- **Permission Caching**: 50-75% reduction in permission check overhead
- **Selective Activity Logging**: 40-60% reduction in database writes
- **Database Query Optimization**: Database-level filtering and calculations
- **Connection Pooling**: Improved database performance

## Technical Specifications

### Architecture
- **Framework**: Django 5.1.5 with Python 3.12.10
- **Database**: Dual database setup (SQLite default, MySQL support)
- **Frontend**: HTML/CSS with HTMX for dynamic interactions
- **Mobile Integration**: Capacitor-based offline support

### Security Features
- 10-layer security middleware stack
- CORS support for mobile apps
- Session validation and IP tracking
- Production-ready security settings when DEBUG=False

### Mobile App Integration
- REST API endpoints for data synchronization
- Comprehensive offline functionality
- Background sync with conflict resolution
- Action queue with priority levels

## Key Differentiators

1. **Regional Adaptation**: Specifically designed for African pharmaceutical operations
2. **Dual Operations**: Seamless retail and wholesale management in one system
3. **Offline Resilience**: Full functionality during internet outages
4. **Comprehensive Auditing**: Complete activity logging and transaction tracking
5. **Scalable Architecture**: Performance optimizations for high-volume operations

## Deployment Options
- **Development**: Local SQLite database with runserver
- **Production**: MySQL with comprehensive security settings
- **Cloud**: PythonAnywhere deployment guide included
- **Mobile**: Offline-first with sync capabilities

## Business Value
- **Operational Efficiency**: Streamlined pharmacy workflows
- **Inventory Control**: Real-time stock tracking and expiry management
- **Financial Management**: Comprehensive sales, procurement, and wallet tracking
- **User Management**: Role-based access with detailed permissions
- **Connectivity Independence**: Operations continue during internet outages

PharmApp represents a complete pharmacy management solution tailored for African markets with modern web technologies, offline capabilities, and comprehensive business workflow support.
