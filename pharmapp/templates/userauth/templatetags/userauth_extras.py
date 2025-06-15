from django import template

register = template.Library()

@register.filter(name='format_permission')
def format_permission(value):
    """
    Convert permission code to readable format.
    Example: 'can_add_user' -> 'Can add user'
    """
    if not value:
        return ''
    return value.replace('_', ' ').capitalize()
