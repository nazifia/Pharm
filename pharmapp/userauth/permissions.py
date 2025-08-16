"""
Permission utility functions for the pharmacy management system.
These functions define role-based access control for different user types.
"""

from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def is_admin(user):
    """Check if user is an Admin"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile and user.profile.user_type == 'Admin'

def is_manager(user):
    """Check if user is a Manager"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile and user.profile.user_type == 'Manager'

def is_pharmacist(user):
    """Check if user is a Pharmacist"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile and user.profile.user_type == 'Pharmacist'

def is_pharm_tech(user):
    """Check if user is a Pharmacy Technician"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile and user.profile.user_type == 'Pharm-Tech'

def is_salesperson(user):
    """Check if user is a Salesperson"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile and user.profile.user_type == 'Salesperson'

# Combined role checks
def is_admin_or_manager(user):
    """Check if user is an Admin or Manager"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile and user.profile.user_type in ['Admin', 'Manager']

def is_admin_or_pharmacist(user):
    """Check if user is an Admin or Pharmacist"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile and user.profile.user_type in ['Admin', 'Pharmacist']

def is_pharmacist_or_pharm_tech(user):
    """Check if user is a Pharmacist or Pharmacy Technician"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile and user.profile.user_type in ['Pharmacist', 'Pharm-Tech']

def is_admin_or_manager_or_pharmacist(user):
    """Check if user is an Admin, Manager, or Pharmacist"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile and user.profile.user_type in ['Admin', 'Manager', 'Pharmacist']

def can_dispense_medication(user):
    """Check if user can dispense medication"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Pharmacist']

def can_manage_inventory(user):
    """Check if user can manage inventory"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager', 'Pharm-Tech']

def can_delete_stock_check_reports(user):
    """Check if user can delete stock check reports - restricted to superusers, admins, and managers only"""
    return user.is_authenticated and (
        user.is_superuser or
        (hasattr(user, 'profile') and user.profile and user.profile.user_type in ['Admin', 'Manager'])
    )

def can_process_sales(user):
    """Check if user can process sales"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager', 'Pharmacist', 'Pharm-Tech', 'Salesperson']

def can_view_reports(user):
    """Check if user can view reports"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager']

def can_manage_users(user):
    """Check if user can manage users"""
    return user.is_authenticated and user.profile.user_type == 'Admin'

def can_approve_procurement(user):
    """Check if user can approve procurement"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager']

def can_manage_customers(user):
    """Check if user can manage customers"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager', 'Pharmacist']

def can_manage_suppliers(user):
    """Check if user can manage suppliers"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager']

def can_add_expenses(user):
    """Check if user can add expenses - allows all authenticated users"""
    if not user.is_authenticated:
        return False

    # Allow superusers regardless of profile
    if user.is_superuser:
        return True

    # Ensure user has a profile
    if not hasattr(user, 'profile') or not user.profile:
        # Create a default profile for users without one
        from userauth.models import Profile
        Profile.objects.get_or_create(user=user, defaults={
            'full_name': user.username or user.mobile,
            'user_type': 'Salesperson'  # Default role
        })
        # Refresh the user object to get the new profile
        user.refresh_from_db()

    # Ensure user_type is set
    if not user.profile.user_type:
        user.profile.user_type = 'Salesperson'
        user.profile.save()

    # Allow all authenticated users with profiles to add expenses
    return True

def can_manage_expenses(user):
    """Check if user can edit and delete expenses"""
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profile') and user.profile and user.profile.user_type in ['Admin', 'Manager']))

def can_add_expense_categories(user):
    """Check if user can add expense categories - allows all authenticated users"""
    if not user.is_authenticated:
        return False

    # Allow superusers regardless of profile
    if user.is_superuser:
        return True

    # Ensure user has a profile
    if not hasattr(user, 'profile') or not user.profile:
        # Create a default profile for users without one
        from userauth.models import Profile
        Profile.objects.get_or_create(user=user, defaults={
            'full_name': user.username or user.mobile,
            'user_type': 'Salesperson'  # Default role
        })
        # Refresh the user object to get the new profile
        user.refresh_from_db()

    # Ensure user_type is set
    if not user.profile.user_type:
        user.profile.user_type = 'Salesperson'
        user.profile.save()

    # Allow all authenticated users with profiles to add expense categories
    return True

def can_manage_expense_categories(user):
    """Check if user can edit and delete expense categories"""
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profile') and user.profile and user.profile.user_type in ['Admin', 'Manager']))

def can_adjust_prices(user):
    """Check if user can adjust prices"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager']

def can_process_returns(user):
    """Check if user can process returns"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager', 'Pharmacist']

def can_approve_returns(user):
    """Check if user can approve returns"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager']

def can_transfer_stock(user):
    """Check if user can transfer stock"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager', 'Pharm-Tech']

def can_view_activity_logs(user):
    """Check if user can view activity logs"""
    return user.is_authenticated and user.has_permission('view_activity_logs')

def can_perform_stock_check(user):
    """Check if user can perform stock checks"""
    return user.is_authenticated

def can_approve_stock_check(user):
    """Check if user can approve and adjust stock checks"""
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profile') and user.profile and user.profile.user_type in ['Admin', 'Manager']))

def can_view_financial_reports(user):
    """Check if user can view financial reports"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager']

def can_edit_user_profiles(user):
    """Check if user can edit user profiles"""
    return user.is_authenticated and user.profile.user_type == 'Admin'

def can_access_admin_panel(user):
    """Check if user can access the admin panel"""
    return user.is_authenticated and user.profile.user_type == 'Admin'

def can_manage_system_settings(user):
    """Check if user can manage system settings"""
    return user.is_authenticated and user.profile.user_type == 'Admin'

def can_view_sales_history(user):
    """Check if user can view sales history"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager', 'Pharmacist', 'Pharm-Tech', 'Salesperson']

def can_view_procurement_history(user):
    """Check if user can view procurement history"""
    return user.is_authenticated and user.has_permission('view_procurement_history')

def can_manage_items(user):
    """Check if user can add and edit items"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager']

def can_view_purchase_and_stock_values(user):
    """Check if user can view purchase and stock values (cost, procurement data)"""
    # Only admins can view by default, managers need specific permission
    if user.is_authenticated and user.profile.user_type == 'Admin':
        return True
    elif user.is_authenticated and user.profile.user_type == 'Manager':
        # Check if manager has been granted specific permission
        return user.has_permission('view_purchase_stock_values')
    return False



def can_operate_retail(user):
    """
    Check if user can operate retail functionality.
    Users can access retail if they have 'operate_all' permission OR
    if they have 'operate_retail' but NOT 'operate_wholesale' (mutual exclusivity).
    """
    if not user.is_authenticated:
        return False

    # If user has operate_all permission, they can access retail
    if user.has_permission('operate_all'):
        return True

    # If user has operate_retail but NOT operate_wholesale, they can access retail
    if user.has_permission('operate_retail') and not user.has_permission('operate_wholesale'):
        return True

    return False

def can_operate_wholesale(user):
    """
    Check if user can operate wholesale functionality.
    Users can access wholesale if they have 'operate_all' permission OR
    if they have 'operate_wholesale' but NOT 'operate_retail' (mutual exclusivity).
    """
    if not user.is_authenticated:
        return False

    # If user has operate_all permission, they can access wholesale
    if user.has_permission('operate_all'):
        return True

    # If user has operate_wholesale but NOT operate_retail, they can access wholesale
    if user.has_permission('operate_wholesale') and not user.has_permission('operate_retail'):
        return True

    return False

def can_operate_all(user):
    """Check if user can operate both retail and wholesale functionality"""
    if not user.is_authenticated:
        return False

    return user.has_permission('operate_all')

# Customer Management Permissions
def can_manage_retail_customers(user):
    """Check if user can manage retail customers only"""
    if not user.is_authenticated:
        return False

    # If user has manage_all_customers permission, they can manage retail customers
    if user.has_permission('manage_all_customers'):
        return True

    # If user has manage_retail_customers but NOT manage_wholesale_customers, they can manage retail customers
    if user.has_permission('manage_retail_customers') and not user.has_permission('manage_wholesale_customers'):
        return True

    return False

def can_manage_wholesale_customers(user):
    """Check if user can manage wholesale customers only"""
    if not user.is_authenticated:
        return False

    # If user has manage_all_customers permission, they can manage wholesale customers
    if user.has_permission('manage_all_customers'):
        return True

    # If user has manage_wholesale_customers but NOT manage_retail_customers, they can manage wholesale customers
    if user.has_permission('manage_wholesale_customers') and not user.has_permission('manage_retail_customers'):
        return True

    return False

def can_manage_all_customers(user):
    """Check if user can manage both retail and wholesale customers"""
    if not user.is_authenticated:
        return False

    return user.has_permission('manage_all_customers')

# Procurement Management Permissions
def can_manage_retail_procurement(user):
    """Check if user can manage retail procurement only"""
    if not user.is_authenticated:
        return False

    # If user has manage_all_procurement permission, they can manage retail procurement
    if user.has_permission('manage_all_procurement'):
        return True

    # If user has manage_retail_procurement but NOT manage_wholesale_procurement, they can manage retail procurement
    if user.has_permission('manage_retail_procurement') and not user.has_permission('manage_wholesale_procurement'):
        return True

    return False

def can_manage_wholesale_procurement(user):
    """Check if user can manage wholesale procurement only"""
    if not user.is_authenticated:
        return False

    # If user has manage_all_procurement permission, they can manage wholesale procurement
    if user.has_permission('manage_all_procurement'):
        return True

    # If user has manage_wholesale_procurement but NOT manage_retail_procurement, they can manage wholesale procurement
    if user.has_permission('manage_wholesale_procurement') and not user.has_permission('manage_retail_procurement'):
        return True

    return False

def can_manage_all_procurement(user):
    """Check if user can manage both retail and wholesale procurement"""
    if not user.is_authenticated:
        return False

    return user.has_permission('manage_all_procurement')

# Stock Check Management Permissions
def can_manage_retail_stock_checks(user):
    """Check if user can manage retail stock checks only"""
    if not user.is_authenticated:
        return False

    # If user has manage_all_stock_checks permission, they can manage retail stock checks
    if user.has_permission('manage_all_stock_checks'):
        return True

    # If user has manage_retail_stock_checks but NOT manage_wholesale_stock_checks, they can manage retail stock checks
    if user.has_permission('manage_retail_stock_checks') and not user.has_permission('manage_wholesale_stock_checks'):
        return True

    return False

def can_manage_wholesale_stock_checks(user):
    """Check if user can manage wholesale stock checks only"""
    if not user.is_authenticated:
        return False

    # If user has manage_all_stock_checks permission, they can manage wholesale stock checks
    if user.has_permission('manage_all_stock_checks'):
        return True

    # If user has manage_wholesale_stock_checks but NOT manage_retail_stock_checks, they can manage wholesale stock checks
    if user.has_permission('manage_wholesale_stock_checks') and not user.has_permission('manage_retail_stock_checks'):
        return True

    return False

def can_manage_all_stock_checks(user):
    """Check if user can manage both retail and wholesale stock checks"""
    if not user.is_authenticated:
        return False

    return user.has_permission('manage_all_stock_checks')

# Expiry Date Management Permissions
def can_manage_retail_expiry(user):
    """Check if user can manage retail expiry dates only"""
    if not user.is_authenticated:
        return False

    # If user has manage_all_expiry permission, they can manage retail expiry
    if user.has_permission('manage_all_expiry'):
        return True

    # If user has manage_retail_expiry but NOT manage_wholesale_expiry, they can manage retail expiry
    if user.has_permission('manage_retail_expiry') and not user.has_permission('manage_wholesale_expiry'):
        return True

    return False

def can_manage_wholesale_expiry(user):
    """Check if user can manage wholesale expiry dates only"""
    if not user.is_authenticated:
        return False

    # If user has manage_all_expiry permission, they can manage wholesale expiry
    if user.has_permission('manage_all_expiry'):
        return True

    # If user has manage_wholesale_expiry but NOT manage_retail_expiry, they can manage wholesale expiry
    if user.has_permission('manage_wholesale_expiry') and not user.has_permission('manage_retail_expiry'):
        return True

    return False

def can_manage_all_expiry(user):
    """Check if user can manage both retail and wholesale expiry dates"""
    if not user.is_authenticated:
        return False

    return user.has_permission('manage_all_expiry')

def can_manage_payment_methods(user):
    """Check if user can manage payment methods"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager']

def can_process_split_payments(user):
    """Check if user can process split payments"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager', 'Pharmacist', 'Pharm-Tech', 'Salesperson']

def can_override_payment_status(user):
    """Check if user can override payment status"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager']

def can_pause_resume_procurement(user):
    """Check if user can pause or resume procurement"""
    return user.is_authenticated and user.profile.user_type in ['Admin', 'Manager', 'Pharm-Tech']

def can_search_items(user):
    """Check if user can search items"""
    return user.is_authenticated


# Role-based access control decorator
def role_required(allowed_roles):
    """
    Decorator for views that checks whether a user has a particular role.
    Usage: @role_required(['Admin', 'Manager'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Please log in to access this page.")
                return redirect('store:index')

            # Check if user has a profile
            if not hasattr(request.user, 'profile') or not request.user.profile:
                # Create a default profile for users without one
                from userauth.models import Profile
                Profile.objects.get_or_create(user=request.user, defaults={
                    'full_name': request.user.username or request.user.mobile,
                    'user_type': 'Salesperson'  # Default role
                })
                # Refresh the user object to get the new profile
                request.user.refresh_from_db()

            if request.user.profile.user_type in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, f"Access denied. You need to be a {', '.join(allowed_roles)} to access this page.")
                return redirect('store:dashboard')
        return _wrapped_view
    return decorator
