from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError, decimal.InvalidOperation):
        return Decimal('0')
