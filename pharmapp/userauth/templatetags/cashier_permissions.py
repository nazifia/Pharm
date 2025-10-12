from django import template

register = template.Library()

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
