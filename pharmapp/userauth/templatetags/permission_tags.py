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
