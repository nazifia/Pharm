# PharmApp - Pharmacy Management System

## Project Overview
PharmApp is a comprehensive pharmacy management system built with Django that supports both retail and wholesale operations. It provides functionality for inventory management, sales processing, customer management, supplier management, and financial reporting.

## App Structure and Functionality

### 1. Store App
**Purpose**: Manages retail pharmacy operations

**Key Features**:
- **Inventory Management**
  - Add, edit, and delete retail items
  - Track stock levels with low stock alerts
  - Manage item expiry dates
  - Adjust stock levels

- **Sales Processing**
  - Cart functionality for item selection
  - Generate receipts with payment methods (cash, transfer, split payment)
  - Support for registered customers and walk-in customers
  - Customer wallet management

- **Financial Reporting**
  - Daily and monthly sales reports
  - Sales by user reports
  - Expense tracking and reporting

- **Stock Transfers**
  - Transfer items between retail and wholesale inventory
  - Request and approve transfers

- **Procurement**
  - Create and manage procurement orders
  - Receive items from suppliers
  - Track procurement history

### 2. Wholesale App
**Purpose**: Manages wholesale pharmacy operations

**Key Features**:
- **Inventory Management**
  - Add, edit, and delete wholesale items
  - Track wholesale stock levels
  - Manage wholesale item expiry dates

- **Sales Processing**
  - Wholesale cart functionality
  - Generate wholesale receipts
  - Support for wholesale customers

- **Customer Management**
  - Register and manage wholesale customers
  - Wholesale customer wallet management

- **Stock Transfers**
  - Request items from retail inventory
  - Approve transfer requests

### 3. Customer App
**Purpose**: Manages customer information and relationships

**Key Features**:
- **Customer Management**
  - Store customer information (name, phone, address)
  - Track customer purchase history
  - Manage customer wallets for both retail and wholesale

- **Wallet System**
  - Add funds to customer wallets
  - Track wallet balances
  - Support payments from wallet balance

### 4. Supplier App
**Purpose**: Manages supplier information and relationships

**Key Features**:
- **Supplier Management**
  - Store supplier information (name, phone, contact info)
  - Link suppliers to procurement orders

### 5. UserAuth App
**Purpose**: Manages user authentication and authorization

**Key Features**:
- **User Management**
  - User registration and authentication
  - Role-based access control (Admin, Manager, Pharmacist, Pharm-Tech, Salesperson)
  - User profile management

- **Activity Logging**
  - Track user actions in the system
  - Generate activity reports

### 6. API App
**Purpose**: Provides API endpoints for data synchronization

**Key Features**:
- **Data Synchronization**
  - Sync inventory data
  - Sync sales data
  - Sync customer data
  - Sync supplier data
  - Sync wholesale data

## Key Models

### Store App
- **Item**: Retail inventory items with properties like name, dosage form, brand, unit, cost, price, markup, stock, expiry date
- **StoreItem**: Items received from suppliers before being added to inventory
- **Sales**: Records of sales transactions
- **SalesItem**: Individual items in a sales transaction
- **Receipt**: Sales receipts with payment information
- **Cart**: Temporary storage for items being purchased
- **TransferRequest**: Requests to transfer items between retail and wholesale
- **Expense**: Store expenses with categories

### Wholesale App
- **WholesaleItem**: Wholesale inventory items
- **WholesaleSales**: Records of wholesale sales transactions
- **WholesaleSalesItem**: Individual items in a wholesale sales transaction
- **WholesaleReceipt**: Wholesale sales receipts
- **WholesaleCart**: Temporary storage for wholesale items being purchased

### Customer App
- **Customer**: Retail customers with name, phone, address
- **Wallet**: Customer wallet for retail purchases
- **WholesaleCustomer**: Wholesale customers
- **WholesaleCustomerWallet**: Wallet for wholesale customers

### Supplier App
- **Supplier**: Suppliers with name, phone, contact info
- **Procurement**: Records of procurement transactions
- **ProcurementItem**: Individual items in a procurement transaction

### UserAuth App
- **User**: Custom user model with mobile number as username
- **Profile**: User profile with user type and additional information
- **ActivityLog**: Records of user actions in the system

## Key Workflows

1. **Retail Sales Process**:
   - Add items to cart
   - Select payment method (cash, transfer, wallet, split)
   - Generate receipt
   - Update inventory

2. **Wholesale Sales Process**:
   - Add wholesale items to cart
   - Select payment method
   - Generate wholesale receipt
   - Update wholesale inventory

3. **Procurement Process**:
   - Create procurement order
   - Add items to procurement
   - Complete procurement
   - Move items to store inventory

4. **Stock Transfer Process**:
   - Create transfer request
   - Approve/reject request
   - Transfer items between inventories

5. **Stock Check and Adjustment**:
   - Create stock check
   - Compare expected vs actual quantities
   - Adjust stock levels

6. **Financial Reporting**:
   - Generate daily sales reports
   - Generate monthly sales reports
   - Track expenses
   - Calculate profits

## User Roles and Permissions

1. **Admin**:
   - Full access to all system features
   - User management
   - System configuration

2. **Manager**:
   - Access to financial reports
   - Approve/reject transfers
   - Manage procurement
   - Manage expenses

3. **Pharmacist**:
   - Dispense medications
   - Manage inventory
   - Process sales
   - View reports

4. **Pharm-Tech**:
   - Process sales
   - Basic inventory management
   - Customer management

5. **Salesperson**:
   - Process sales
   - Basic customer management

## Technical Implementation

- **Backend**: Django web framework
- **Database**: SQLite (default)
- **Frontend**: HTML, CSS, JavaScript with HTMX for dynamic interactions
- **Authentication**: Django's built-in authentication system with custom User model
- **PDF Generation**: HTML2PDF.js for receipt generation
- **Offline Support**: Service Worker implementation (planned feature)
