from django import template

register = template.Library()

@register.filter(name='test_filter')
def test_filter(value):
    return str(value)

@register.filter(name='calculate_period_total')
def calculate_period_total(histories):
    if not histories:
        return 0
    return sum(history.subtotal for history in histories)


