# Enhanced Privilege Management System - User Guide

## Overview

The Enhanced Privilege Management System provides a comprehensive UI for admin/superuser to assign and manage user privileges/permissions. This system combines role-based permissions with individual permission overrides for maximum flexibility.

## Access Requirements

**Who can use this system:**
- ✅ Admin users (user_type = 'Admin')
- ✅ Superusers (is_superuser = True)

**How to access:**
1. Login as an admin/superuser
2. Navigate to **Administration** → **User Privileges** in the sidebar menu
3. Or go directly to `/privilege-management/`

## Key Features

### 🎯 **Individual Permission Management**
- Select any user from the dropdown
- View their current permissions with source indicators
- Grant or revoke individual permissions
- Override role-based permissions for specific users

### 🔍 **Advanced Search & Filtering**
- **Search**: Type in the search box to find specific permissions
- **Filter by Status**:
  - **All**: Show all permissions
  - **Granted**: Show only granted permissions
  - **Revoked**: Show only revoked permissions

### 🚀 **Quick Actions**
- **Select All Permissions**: Grant all available permissions
- **Clear All Permissions**: Revoke all permissions
- **Role Templates**: Apply permission sets for specific roles:
  - Admin Template
  - Manager Template
  - Pharmacist Template
  - Pharm-Tech Template
  - Salesperson Template

### 👥 **Bulk Permission Management**
- Select multiple users at once
- Grant or revoke a specific permission for all selected users
- Efficient for managing permissions across teams

### 📊 **Real-time Statistics**
- Total number of user roles
- Total active users
- Number of available permissions
- Custom permission assignments

## How to Use

### Step 1: Select a User
1. Use the **Select User** dropdown to choose a user
2. Click **Load User Permissions** or the dropdown will auto-load
3. The system will display the user's current permissions

### Step 2: Manage Individual Permissions
1. View the permissions grid with checkboxes
2. **Green badges** = Role-based permissions
3. **Blue badges** = Individual grants
4. **Orange badges** = Individual revocations
5. Check/uncheck boxes to grant/revoke permissions
6. Click **Save Permissions** to apply changes

### Step 3: Use Quick Actions (Optional)
- **Apply Role Template**: Instantly apply a role's permission set
- **Select/Clear All**: Bulk select or deselect all permissions
- **Search**: Find specific permissions quickly
- **Filter**: View only granted or revoked permissions

### Step 4: Bulk Management (Optional)
1. Click **Bulk Permission Management**
2. Select multiple users (hold Ctrl/Cmd)
3. Choose a permission to grant or revoke
4. Select action (Grant/Revoke)
5. Click **Apply Changes**

## Permission System Logic

### Role-Based Permissions
Each user role has default permissions:
- **Admin**: 24 permissions (full access)
- **Manager**: 19 permissions (operational management)
- **Pharmacist**: 11 permissions (pharmacy operations)
- **Pharm-Tech**: 10 permissions (technical support)
- **Salesperson**: 5 permissions (sales only)

### Individual Permission Overrides
- Individual permissions **override** role-based permissions
- You can grant additional permissions to any user
- You can revoke role-based permissions from specific users
- Changes are tracked with timestamps and admin notes

### Permission Sources
- **Role**: Permission comes from user's role
- **Individual**: Permission granted individually
- **Revoked**: Role permission revoked individually

## Available Permissions

### User Management
- `manage_users`: Create, edit, delete users
- `edit_user_profiles`: Modify user profiles
- `view_activity_logs`: Access system activity logs

### Financial Management
- `view_financial_reports`: Access financial data
- `manage_expenses`: Handle expense management
- `view_reports`: Access system reports

### Inventory Management
- `manage_inventory`: Stock management
- `perform_stock_check`: Stock verification
- `transfer_stock`: Move stock between locations
- `adjust_prices`: Modify item prices

### Sales & Customer Management
- `process_sales`: Handle sales transactions
- `manage_customers`: Customer management
- `process_returns`: Handle returns
- `approve_returns`: Approve return requests
- `process_split_payments`: Handle split payments
- `override_payment_status`: Override payment status

### Pharmacy Operations
- `dispense_medication`: Medication dispensing
- `approve_procurement`: Approve purchases
- `pause_resume_procurement`: Control procurement
- `manage_suppliers`: Supplier management

### System Administration
- `access_admin_panel`: Django admin access
- `manage_system_settings`: System configuration
- `manage_payment_methods`: Payment method setup
- `search_items`: Advanced search capabilities

## Security Features

### Access Control
- Only admin/superuser can access the privilege management system
- All permission changes are logged with timestamps
- User activity is tracked and auditable

### Permission Validation
- System validates all permission assignments
- Prevents unauthorized access attempts
- Maintains data integrity

### Activity Logging
- All permission changes are logged
- Includes who made the change and when
- Tracks both individual and bulk operations

## Best Practices

### 1. Use Role Templates First
- Start with appropriate role template
- Make individual adjustments as needed
- Avoid giving excessive permissions

### 2. Regular Permission Audits
- Review user permissions periodically
- Remove unnecessary permissions
- Use activity logs to track changes

### 3. Bulk Operations
- Use bulk management for team-wide changes
- Test with a few users before bulk operations
- Document major permission changes

### 4. Permission Documentation
- Keep notes on why specific permissions were granted
- Document any deviations from role standards
- Maintain permission change records

## Troubleshooting

### User Can't Access Feature
1. Check if user has required permission
2. Verify permission is granted (not revoked)
3. Check if role-based permission exists
4. Look for individual permission overrides

### Permission Changes Not Taking Effect
1. Ensure changes were saved
2. User may need to logout/login
3. Check for browser cache issues
4. Verify permission was granted correctly

### Bulk Operations Failed
1. Check if all selected users exist
2. Verify permission name is correct
3. Ensure admin has necessary privileges
4. Check system logs for errors

## API Endpoints

For developers and advanced users:

- `GET /api/user-permissions/<user_id>/` - Get user permissions
- `GET /api/users/` - Get all users for bulk operations
- `POST /bulk-permission-management/` - Execute bulk permission changes
- `GET /privilege-management/` - Main privilege management interface

## Support

If you encounter issues with the privilege management system:

1. Check the activity logs for error messages
2. Verify your admin privileges
3. Contact system administrator
4. Review this documentation for proper usage

---

**Last Updated**: 2025-07-18  
**Version**: Enhanced v2.0  
**Compatible with**: Django-based Pharmacy Management System
