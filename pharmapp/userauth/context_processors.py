"""
Context processors for the userauth app.
These provide user role information to all templates.
"""

from .permissions import (
    # User type checks
    is_admin, is_manager, is_pharmacist, is_pharm_tech, is_salesperson,
    is_admin_or_manager, is_admin_or_pharmacist, is_pharmacist_or_pharm_tech,
    is_admin_or_manager_or_pharmacist,

    # Permission checks
    can_dispense_medication, can_manage_inventory, can_process_sales,
    can_view_reports, can_manage_users, can_approve_procurement,
    can_manage_customers, can_manage_suppliers, can_manage_expenses,
    can_adjust_prices, can_process_returns, can_approve_returns,
    can_transfer_stock, can_view_activity_logs, can_perform_stock_check,
    can_view_financial_reports, can_edit_user_profiles, can_access_admin_panel,
    can_manage_system_settings, can_view_sales_history, can_view_procurement_history,
    can_manage_payment_methods, can_process_split_payments, can_override_payment_status,
    can_pause_resume_procurement, can_search_items,
    
    # Role-specific checks
    can_dispense_items, is_cashier
)

try:
    from .decorators import get_user_permissions_context
except ImportError:
    # Fallback if decorators module is not available
    def get_user_permissions_context(user):
        return {
            'user_permissions': [],
            'user_role': getattr(user.profile, 'user_type', None) if hasattr(user, 'profile') else None,
            'is_admin': False,
            'is_manager': False,
            'is_pharmacist': False,
            'is_staff': False
        }

def user_roles(request):
    """
    Add user role information to the template context.
    This makes role-based checks available in all templates.
    """
    context = {}

    if request.user.is_authenticated:
        user = request.user
        context.update({
            # User type checks
            'is_admin': is_admin(user),
            'is_manager': is_manager(user),
            'is_pharmacist': is_pharmacist(user),
            'is_pharm_tech': is_pharm_tech(user),
            'is_salesperson': is_salesperson(user),
            'is_admin_or_manager': is_admin_or_manager(user),
            'is_admin_or_pharmacist': is_admin_or_pharmacist(user),
            'is_pharmacist_or_pharm_tech': is_pharmacist_or_pharm_tech(user),
            'is_admin_or_manager_or_pharmacist': is_admin_or_manager_or_pharmacist(user),

            # Basic permission checks
            'can_dispense_medication': can_dispense_medication(user),
            'can_manage_inventory': can_manage_inventory(user),
            'can_process_sales': can_process_sales(user),
            'can_view_reports': can_view_reports(user),
            'can_manage_users': can_manage_users(user),
            'can_approve_procurement': can_approve_procurement(user),
            'can_manage_customers': can_manage_customers(user),
            'can_manage_suppliers': can_manage_suppliers(user),
            'can_manage_expenses': can_manage_expenses(user),
            'can_adjust_prices': can_adjust_prices(user),
            'can_process_returns': can_process_returns(user),
            'can_approve_returns': can_approve_returns(user),
            'can_transfer_stock': can_transfer_stock(user),
            'can_view_activity_logs': can_view_activity_logs(user),

            # Advanced permission checks
            'can_perform_stock_check': can_perform_stock_check(user),
            'can_view_financial_reports': can_view_financial_reports(user),
            'can_edit_user_profiles': can_edit_user_profiles(user),
            'can_access_admin_panel': can_access_admin_panel(user),
            'can_manage_system_settings': can_manage_system_settings(user),
            'can_view_sales_history': can_view_sales_history(user),
            'can_view_procurement_history': can_view_procurement_history(user),
            'can_manage_payment_methods': can_manage_payment_methods(user),
            'can_process_split_payments': can_process_split_payments(user),
            'can_override_payment_status': can_override_payment_status(user),
            'can_pause_resume_procurement': can_pause_resume_procurement(user),
            'can_search_items': can_search_items(user),

            # Role-specific checks
            'can_dispense_items': can_dispense_items(user),
            'is_cashier': is_cashier(user),

            # User role for display
            'user_role': user.profile.user_type if hasattr(user, 'profile') else None,
        })

        # Add new permission system context
        try:
            new_permissions_context = get_user_permissions_context(user)
            context.update(new_permissions_context)
        except:
            # Fallback if new permission system is not available
            pass

    return context
