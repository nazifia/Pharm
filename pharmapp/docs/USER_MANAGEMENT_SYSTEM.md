# User Management System Documentation

## Overview

This document describes the comprehensive user management system with privilege/access control functionality implemented for the pharmacy management system.

## User Types and Roles

The system supports five distinct user types, each with specific permissions and access levels:

### 1. Admin
- **Full system access** including user management, financial reports, system settings
- **Permissions**: All available permissions in the system
- **Key Capabilities**:
  - Manage users (create, edit, delete, activate/deactivate)
  - Access all financial and operational reports
  - Manage system settings and configurations
  - View and manage activity logs
  - Override payment statuses and manage split payments
  - Full inventory and procurement management

### 2. Manager
- **Supervisory access** to reports, inventory management, user oversight (excluding user creation/deletion)
- **Permissions**: All except user management and system settings
- **Key Capabilities**:
  - View financial reports and analytics
  - Manage inventory and approve procurement
  - Oversee sales operations and customer management
  - Manage suppliers and expenses
  - Process returns and approve transactions

### 3. Pharmacist
- **Full pharmacy operations** including dispensing, inventory management
- **Permissions**: Pharmacy-focused operations
- **Key Capabilities**:
  - Dispense medications and manage prescriptions
  - Full inventory management and stock transfers
  - Process sales and manage customers
  - Adjust prices and process returns
  - View sales and procurement history

### 4. Pharm-Tech (Pharmacy Technician)
- **Limited pharmacy operations** including basic dispensing, inventory viewing
- **Permissions**: Restricted pharmacy operations
- **Key Capabilities**:
  - Assist with inventory management
  - Process basic sales transactions
  - Manage customer information
  - Process returns and transfers
  - Perform stock checks

### 5. Salesperson
- **Sales operations** including customer management, basic inventory viewing
- **Permissions**: Sales-focused operations
- **Key Capabilities**:
  - Process sales transactions
  - Manage customer relationships
  - View sales history and reports
  - Handle split payments
  - Basic item search functionality

## Permission System

### Core Permissions

The system implements a granular permission system with the following categories:

#### User Management
- `manage_users`: Create, edit, delete user accounts
- `edit_user_profiles`: Modify user profile information
- `view_activity_logs`: Access system activity logs

#### Financial Operations
- `view_financial_reports`: Access financial reports and analytics
- `manage_expenses`: Handle expense tracking and management
- `manage_payment_methods`: Configure payment options
- `process_split_payments`: Handle multiple payment methods
- `override_payment_status`: Modify payment statuses

#### Inventory Management
- `manage_inventory`: Full inventory control
- `dispense_medication`: Medication dispensing rights
- `adjust_prices`: Modify item pricing
- `transfer_stock`: Move items between locations
- `perform_stock_check`: Conduct inventory audits

#### Sales Operations
- `process_sales`: Handle sales transactions
- `process_returns`: Manage return transactions
- `approve_returns`: Authorize return requests
- `manage_customers`: Customer relationship management

#### Procurement
- `approve_procurement`: Authorize procurement requests
- `manage_suppliers`: Supplier relationship management
- `pause_resume_procurement`: Control procurement processes

#### System Administration
- `access_admin_panel`: Django admin interface access
- `manage_system_settings`: System configuration rights
- `search_items`: Advanced search capabilities

## User Interface Components

### 1. User Management Dashboard
- **Location**: `/users/`
- **Features**:
  - Comprehensive user listing with search and filtering
  - Bulk operations (activate, deactivate, delete)
  - User creation and editing
  - Role-based access indicators

### 2. User Details Page
- **Location**: `/users/details/<user_id>/`
- **Features**:
  - Complete user profile information
  - Permission overview
  - Recent activity history
  - Quick action buttons

### 3. Privilege Management Interface
- **Location**: `/privilege-management/`
- **Features**:
  - Role-based permission templates
  - Individual permission assignment
  - Permission visualization
  - Quick role application

### 4. User Registration Form
- **Location**: `/register/`
- **Enhanced Fields**:
  - Basic information (name, username, mobile, email)
  - Role assignment
  - Department and employee ID
  - Hire date tracking

## Technical Implementation

### Models

#### Enhanced User Model
```python
class User(AbstractUser):
    # Custom fields for pharmacy system
    mobile = models.CharField(max_length=20, unique=True)
    
    def has_permission(self, permission):
        # Check role-based permissions
    
    def get_permissions(self):
        # Return all user permissions
```

#### Enhanced Profile Model
```python
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(choices=USER_TYPE)
    department = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=50, unique=True)
    hire_date = models.DateField()
    # Additional tracking fields
```

### Permission Decorators

#### Role-Based Access Control
```python
@role_required(['Admin', 'Manager'])
def sensitive_view(request):
    # View accessible only to Admins and Managers

@permission_required('manage_users')
def user_management_view(request):
    # View requiring specific permission
```

#### Available Decorators
- `@admin_required`: Admin access only
- `@manager_or_admin_required`: Manager or Admin access
- `@pharmacist_or_above_required`: Pharmacist, Manager, or Admin
- `@staff_required`: Any staff member
- `@permission_required(permission_name)`: Specific permission check

### Context Processors

The system provides template context processors that make user permissions available in all templates:

```python
# Available in all templates
{{ user_role }}              # Current user's role
{{ user_permissions }}       # List of user permissions
{{ can_manage_users }}       # Boolean permission checks
{{ is_admin }}              # Role checks
```

## Security Features

### 1. Automatic Role Assignment
- Superusers automatically receive Admin privileges
- New users require explicit role assignment
- Profile creation is automatic on user creation

### 2. Permission Validation
- All sensitive views protected by decorators
- Template-level permission checks
- Database-level permission validation

### 3. Activity Logging
- All user management actions logged
- Permission changes tracked
- Login/logout events recorded

### 4. Access Control
- 403 error pages with helpful information
- Graceful permission denial handling
- Redirect to appropriate pages

## Navigation Integration

The user management system is integrated into the main navigation:

- **Administration Section**: Contains all user management links
- **Role-Based Visibility**: Menu items appear based on user permissions
- **Quick Access**: Direct links to common operations

## Usage Examples

### Creating a New User
1. Navigate to Administration → Add New User
2. Fill in required information (name, username, mobile)
3. Select appropriate user type/role
4. Optionally add department and employee ID
5. Set hire date if applicable
6. Submit form to create user

### Managing User Privileges
1. Navigate to Administration → User Privileges
2. Select user from dropdown
3. View current role-based permissions
4. Apply role template or customize individual permissions
5. Save changes

### Bulk User Operations
1. Navigate to Administration → User Management
2. Use search/filter to find specific users
3. Select users using checkboxes
4. Choose bulk action (activate, deactivate, delete)
5. Confirm operation

## Best Practices

### 1. Role Assignment
- Assign the minimum required role for user's responsibilities
- Regularly review user roles and permissions
- Use role templates for consistent permission assignment

### 2. Security
- Regularly audit user accounts and permissions
- Deactivate accounts for inactive employees
- Monitor activity logs for suspicious behavior

### 3. Maintenance
- Keep user information up to date
- Remove unnecessary user accounts
- Document permission changes

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   - Check user's role assignment
   - Verify required permissions for the action
   - Ensure user account is active

2. **Navigation Items Not Visible**
   - Confirm user has required permissions
   - Check context processor configuration
   - Verify template permission checks

3. **User Creation Failures**
   - Ensure unique username and mobile number
   - Check required field validation
   - Verify employee ID uniqueness

## Future Enhancements

### Planned Features
- Advanced permission groups
- Time-based access controls
- Multi-factor authentication
- Advanced audit trails
- Role hierarchy management

### Integration Opportunities
- LDAP/Active Directory integration
- Single sign-on (SSO) support
- API-based user management
- Mobile app integration

## Support and Maintenance

For technical support or questions about the user management system:
1. Check this documentation first
2. Review activity logs for error details
3. Contact system administrator
4. Refer to Django documentation for advanced configurations

---

*This documentation is part of the Pharmacy Management System and should be kept up to date with system changes.*
