from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def multiply(value, arg):
    try:
        return value * arg
    except (ValueError, TypeError):
        return value

@register.filter
def split(value, arg):
    """Split a string into a list on the specified delimiter"""
    return value.split(arg)

@register.filter
def replace(value, args):
    """
    Replace occurrences of a substring in a string.
    Usage: {{ value|replace:"old,new" }}
    """
    if not args:
        return value

    if ',' not in args:
        # If no comma, treat as replacing with empty string
        return str(value).replace(args, '')

    old, new = args.split(',', 1)
    return str(value).replace(old, new)

@register.filter
def format_permission(value):
    """
    Format permission names for display.
    Replaces underscores with spaces and capitalizes.
    """
    return str(value).replace('_', ' ').title()

@register.filter
def has_permission(user, permission):
    """
    Check if user has a specific permission.
    Usage: {% if user|has_permission:"manage_users" %}
    """
    if hasattr(user, 'has_permission'):
        return user.has_permission(permission)
    return False

@register.filter
def get_user_role(user):
    """
    Get the user's role/user_type.
    """
    if hasattr(user, 'profile') and user.profile:
        return user.profile.user_type
    return None