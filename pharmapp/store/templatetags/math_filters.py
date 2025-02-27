from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """
    Multiplies the value by the argument.
    Usage: {{ value|mul:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''
