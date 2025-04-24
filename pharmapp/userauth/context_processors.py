"""
Context processors for the userauth app.
These provide user role information to all templates.
"""

from .permissions import (
    is_admin, is_manager, is_pharmacist, is_pharm_tech, is_salesperson,
    can_dispense_medication, can_manage_inventory, can_process_sales,
    can_view_reports, can_manage_users, can_approve_procurement,
    can_manage_customers, can_manage_suppliers, can_manage_expenses,
    can_adjust_prices, can_process_returns, can_approve_returns,
    can_transfer_stock, can_view_activity_logs
)

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
            
            # Permission checks
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
            
            # User role for display
            'user_role': user.profile.user_type,
        })
    
    return context
