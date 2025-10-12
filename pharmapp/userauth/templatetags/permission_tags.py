from django import template
from django.contrib.auth import get_user_model

register = template.Library()
User = get_user_model()


@register.filter
def has_permission(user, permission):
    """
    Template filter to check if a user has a specific permission.
    Usage: {% if user|has_permission:"view_financial_reports" %}
    """
    if not user or not user.is_authenticated:
        return False
    
    return user.has_permission(permission)


@register.filter
def is_admin(user):
    """
    Template filter to check if a user is an admin.
    Usage: {% if user|is_admin %}
    """
    if not user or not user.is_authenticated:
        return False

    return (hasattr(user, 'profile') and
            user.profile and
            user.profile.user_type == 'Admin') or user.is_superuser

@register.filter
def can_approve_stock_check(user):
    """
    Template filter to check if a user can approve stock checks.
    Usage: {% if user|can_approve_stock_check %}
    """
    if not user or not user.is_authenticated:
        return False

    return (user.is_superuser or
            (hasattr(user, 'profile') and
             user.profile and
             user.profile.user_type in ['Admin', 'Manager']))


@register.filter
def is_cashier(user):
    """
    Template filter to check if a user is a cashier.
    Usage: {% if user|is_cashier %}
    """
    if not user or not user.is_authenticated:
        return False

    # Check if user has a cashier profile
    return hasattr(user, 'cashier')


@register.filter
def can_process_payments(user):
    """
    Template filter to check if a user can process payments (cashier functionality).
    Usage: {% if user|can_process_payments %}
    """
    if not user or not user.is_authenticated:
        return False

    return (user.is_superuser or
            (hasattr(user, 'profile') and
             user.profile and
             user.profile.user_type in ['Admin', 'Manager', 'Cashier']) or
            hasattr(user, 'cashier'))


@register.filter
def can_view_financial_data(user):
    """
    Template filter to check if a user can view financial data.
    Usage: {% if user|can_view_financial_data %}
    """
    if not user or not user.is_authenticated:
        return False

    # Use the new permission function for purchase and stock values
    from userauth.permissions import can_view_purchase_and_stock_values
    return can_view_purchase_and_stock_values(user)


@register.simple_tag
def user_has_permission(user, permission):
    """
    Template tag to check if a user has a specific permission.
    Usage: {% user_has_permission user "view_financial_reports" as can_view %}
    """
    if not user or not user.is_authenticated:
        return False

    return user.has_permission(permission)


@register.filter
def can_operate_retail(user):
    """
    Template filter to check if a user can operate retail functionality.
    Usage: {% if user|can_operate_retail %}
    """
    if not user or not user.is_authenticated:
        return False

    from userauth.permissions import can_operate_retail
    return can_operate_retail(user)


@register.filter
def can_operate_wholesale(user):
    """
    Template filter to check if a user can operate wholesale functionality.
    Usage: {% if user|can_operate_wholesale %}
    """
    if not user or not user.is_authenticated:
        return False

    from userauth.permissions import can_operate_wholesale
    return can_operate_wholesale(user)


@register.filter
def can_operate_all(user):
    """
    Template filter to check if a user can operate both retail and wholesale functionality.
    Usage: {% if user|can_operate_all %}
    """
    if not user or not user.is_authenticated:
        return False

    from userauth.permissions import can_operate_all
    return can_operate_all(user)


# Customer Management Template Tags
@register.filter
def can_manage_retail_customers(user):
    """Template filter for retail customer management permissions"""
    if not user or not user.is_authenticated:
        return False
    from userauth.permissions import can_manage_retail_customers
    return can_manage_retail_customers(user)

@register.filter
def can_manage_wholesale_customers(user):
    """Template filter for wholesale customer management permissions"""
    if not user or not user.is_authenticated:
        return False
    from userauth.permissions import can_manage_wholesale_customers
    return can_manage_wholesale_customers(user)

@register.filter
def can_manage_all_customers(user):
    """Template filter for all customer management permissions"""
    if not user or not user.is_authenticated:
        return False
    from userauth.permissions import can_manage_all_customers
    return can_manage_all_customers(user)


# Procurement Management Template Tags
@register.filter
def can_manage_retail_procurement(user):
    """Template filter for retail procurement management permissions"""
    if not user or not user.is_authenticated:
        return False
    from userauth.permissions import can_manage_retail_procurement
    return can_manage_retail_procurement(user)

@register.filter
def can_manage_wholesale_procurement(user):
    """Template filter for wholesale procurement management permissions"""
    if not user or not user.is_authenticated:
        return False
    from userauth.permissions import can_manage_wholesale_procurement
    return can_manage_wholesale_procurement(user)

# Stock Check Management Template Tags
@register.filter
def can_manage_retail_stock_checks(user):
    """Template filter for retail stock check management permissions"""
    if not user or not user.is_authenticated:
        return False
    from userauth.permissions import can_manage_retail_stock_checks
    return can_manage_retail_stock_checks(user)

@register.filter
def can_manage_wholesale_stock_checks(user):
    """Template filter for wholesale stock check management permissions"""
    if not user or not user.is_authenticated:
        return False
    from userauth.permissions import can_manage_wholesale_stock_checks
    return can_manage_wholesale_stock_checks(user)

# Expiry Management Template Tags
@register.filter
def can_manage_retail_expiry(user):
    """Template filter for retail expiry management permissions"""
    if not user or not user.is_authenticated:
        return False
    from userauth.permissions import can_manage_retail_expiry
    return can_manage_retail_expiry(user)

@register.filter
def can_manage_wholesale_expiry(user):
    """Template filter for wholesale expiry management permissions"""
    if not user or not user.is_authenticated:
        return False
    from userauth.permissions import can_manage_wholesale_expiry
    return can_manage_wholesale_expiry(user)


@register.simple_tag
def user_role(user):
    """
    Template tag to get user's role.
    Usage: {% user_role user as role %}
    """
    if not user or not user.is_authenticated:
        return None
    
    if hasattr(user, 'profile') and user.profile:
        return user.profile.user_type
    
    return None


@register.filter
def can_access_payment_requests(user):
    """
    Template filter to check if a user can access payment requests.
    Usage: {% if user|can_access_payment_requests %}
    """
    if not user or not user.is_authenticated:
        return False

    return (hasattr(user, 'profile') and
            user.profile and
            user.profile.user_type in ['Admin', 'Manager', 'Pharmacist', 'Salesperson'])


@register.filter
def can_access_cashier_dashboard(user):
    """
    Template filter to check if a user can access cashier dashboard.
    Usage: {% if user|can_access_cashier_dashboard %}
    """
    if not user or not user.is_authenticated:
        return False

    return user.is_superuser or (hasattr(user, 'profile') and
                               user.profile and
                               user.profile.user_type in ['Admin', 'Manager'])


@register.filter
def can_access_payment_requests(user):
    """
    Template filter to check if a user can access payment requests.
    Usage: {% if user|can_access_payment_requests %}
    """
    if not user or not user.is_authenticated:
        return False

    return (hasattr(user, 'profile') and
            user.profile and
            user.profile.user_type in ['Admin', 'Manager', 'Pharmacist', 'Salesperson'])


@register.filter
def can_access_cashier_dashboard(user):
    """
    Template filter to check if a user can access cashier dashboard.
    Usage: {% if user|can_access_cashier_dashboard %}
    """
    if not user or not user.is_authenticated:
        return False

    return (user.is_superuser or
            (hasattr(user, 'profile') and
             user.profile and
             user.profile.user_type in ['Admin', 'Manager']))


@register.filter
def is_cashier(user):
    """
    Template filter to check if a user is a cashier.
    Usage: {% if user|is_cashier %}
    """
    if not user or not user.is_authenticated:
        return False

    # Check if user has a cashier profile
    return hasattr(user, 'cashier')


@register.filter
def can_process_payments(user):
    """
    Template filter to check if a user can process payments (cashier functionality).
    Usage: {% if user|can_process_payments %}
    """
    if not user or not user.is_authenticated:
        return False

    return (user.is_superuser or
            (hasattr(user, 'profile') and
             user.profile and
             user.profile.user_type in ['Admin', 'Manager', 'Cashier']) or
            hasattr(user, 'cashier'))


@register.filter
def can_delete_items(user):
    """
    Template filter to check if a user can delete items.
    Usage: {% if user|can_delete_items %}
    """
    if not user or not user.is_authenticated:
        return False

    return (hasattr(user, 'profile') and
            user.profile and
            user.profile.user_type in ['Admin', 'Manager'])


@register.filter
def can_access_payment_requests(user):
    """
    Template filter to check if a user can access payment requests.
    Usage: {% if user|can_access_payment_requests %}
    """
    if not user or not user.is_authenticated:
        return False

    return (hasattr(user, 'profile') and
            user.profile and
            user.profile.user_type in ['Admin', 'Manager', 'Pharmacist', 'Salesperson'])


@register.filter
def can_access_payment_requests(user):
    """
    Template filter to check if a user can access payment requests.
    Usage: {% if user|can_access_payment_requests %}
    """
    if not user or not user.is_authenticated:
        return False

    return (hasattr(user, 'profile') and
            user.profile and
            user.profile.user_type in ['Admin', 'Manager', 'Pharmacist', 'Salesperson'])


@register.filter
def can_access_cashier_dashboard(user):
    """
    Template filter to check if a user can access cashier dashboard.
    Usage: {% if user|can_access_cashier_dashboard %}
    """
    if not user or not user.is_authenticated:
        return False

    return (user.is_superuser or
            (hasattr(user, 'profile') and
             user.profile and
             user.profile.user_type in ['Admin', 'Manager']))


@register.filter
def is_cashier(user):
    """
    Template filter to check if a user is a cashier.
    Usage: {% if user|is_cashier %}
    """
    if not user or not user.is_authenticated:
        return False

    # Check if user has a cashier profile
    return hasattr(user, 'cashier')


@register.filter
def can_process_payments(user):
    """
    Template filter to check if a user can process payments (cashier functionality).
    Usage: {% if user|can_process_payments %}
    """
    if not user or not user.is_authenticated:
        return False

    return (user.is_superuser or
            (hasattr(user, 'profile') and
             user.profile and
             user.profile.user_type in ['Admin', 'Manager', 'Cashier']) or
            hasattr(user, 'cashier'))


@register.filter
def can_access_payment_requests(user):
    """
    Template filter to check if a user can access payment requests.
    Usage: {% if user|can_access_payment_requests %}
    """
    if not user or not user.is_authenticated:
        return False

    return (hasattr(user, 'profile') and
            user.profile and
            user.profile.user_type in ['Admin', 'Manager', 'Pharmacist', 'Salesperson'])


@register.filter
def can_access_cashier_dashboard(user):
    """
    Template filter to check if a user can access cashier dashboard.
    Usage: {% if user|can_access_cashier_dashboard %}
    """
    if not user or not user.is_authenticated:
        return False

    return (user.is_superuser or
            (hasattr(user, 'profile') and
             user.profile and
             user.profile.user_type in ['Admin', 'Manager']))


@register.filter
def is_cashier(user):
    """
    Template filter to check if a user is a cashier.
    Usage: {% if user|is_cashier %}
    """
    if not user or not user.is_authenticated:
        return False

    # Check if user has a cashier profile
    return hasattr(user, 'cashier')


@register.filter
def can_process_payments(user):
    """
    Template filter to check if a user can process payments (cashier functionality).
    Usage: {% if user|can_process_payments %}
    """
    if not user or not user.is_authenticated:
        return False

    return (user.is_superuser or
            (hasattr(user, 'profile') and
             user.profile and
             user.profile.user_type in ['Admin', 'Manager', 'Cashier']) or
            hasattr(user, 'cashier'))


@register.inclusion_tag('userauth/partials/permission_check.html')
def check_permission(user, permission, content=""):
    """
    Inclusion tag for conditional content based on permissions.
    Usage: {% check_permission user "view_financial_reports" %}Content here{% endcheck_permission %}
    """
    return {
        'has_permission': user.has_permission(permission) if user and user.is_authenticated else False,
        'content': content
    }


@register.filter
def can_access_payment_requests(user):
    """
    Template filter to check if a user can access payment requests.
    Usage: {% if user|can_access_payment_requests %}
    """
    if not user or not user.is_authenticated:
        return False

    return (hasattr(user, 'profile') and
            user.profile and
            user.profile.user_type in ['Admin', 'Manager', 'Pharmacist', 'Salesperson'])


@register.filter
def can_access_cashier_dashboard(user):
    """
    Template filter to check if a user can access cashier dashboard.
    Usage: {% if user|can_access_cashier_dashboard %}
    """
    if not user or not user.is_authenticated:
        return False

    return (user.is_superuser or
            (hasattr(user, 'profile') and
             user.profile and
             user.profile.user_type in ['Admin', 'Manager']))


@register.filter
def is_cashier(user):
    """
    Template filter to check if a user is a cashier.
    Usage: {% if user|is_cashier %}
    """
    if not user or not user.is_authenticated:
        return False

    # Check if user has a cashier profile
    return hasattr(user, 'cashier')


@register.filter
def can_process_payments(user):
    """
    Template filter to check if a user can process payments (cashier functionality).
    Usage: {% if user|can_process_payments %}
    """
    if not user or not user.is_authenticated:
        return False

    return (user.is_superuser or
            (hasattr(user, 'profile') and
             user.profile and
             user.profile.user_type in ['Admin', 'Manager', 'Cashier']) or
            hasattr(user, 'cashier'))
