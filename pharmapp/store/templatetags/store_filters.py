from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()

@register.filter
def multiply(value, arg):
    """
    Multiply two values with Decimal precision.

    Usage in templates:
        {{ item.cost_price|multiply:item.stock }}

    Args:
        value: First operand (Decimal, int, float, or string)
        arg: Second operand (Decimal, int, float, or string)

    Returns:
        Decimal: Product of the two values
        int: 0 if calculation fails
    """
    try:
        # Convert both to Decimal for precision
        val_decimal = Decimal(str(value))
        arg_decimal = Decimal(str(arg))
        return val_decimal * arg_decimal
    except (ValueError, TypeError, AttributeError, InvalidOperation):
        # Return 0 on any error (prevents template crashes)
        return 0

@register.filter
def format_currency(value):
    """
    Format a number as Nigerian Naira currency.

    Usage:
        {{ value|format_currency }}

    Returns:
        str: Formatted currency string (e.g., "₦1,234.56")
    """
    try:
        val = Decimal(str(value))
        # Format with thousand separators and 2 decimal places
        formatted = "{:,.2f}".format(val)
        return f"₦{formatted}"
    except (ValueError, TypeError, AttributeError, InvalidOperation):
        return "₦0.00"