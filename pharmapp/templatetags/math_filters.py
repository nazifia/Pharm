from django import template
from decimal import Decimal
import decimal

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError, decimal.InvalidOperation):
        return Decimal('0')

@register.filter(name='mul')
def mul(value, arg):
    """Alias for multiply filter"""
    return multiply(value, arg)
