from .models import Subscription


def subscription_context(request):
    if not request.user.is_authenticated:
        return {}
    sub = Subscription.get_current()
    if sub is None:
        sub = Subscription.objects.order_by('-end_date').first()
    return {
        'subscription': sub,
        'subscription_is_active': sub.is_active if sub else False,
        'subscription_days_remaining': sub.days_remaining if sub else 0,
        'subscription_expiring_soon': sub.is_expiring_soon if sub else False,
        'subscription_in_grace': sub.is_in_grace_period if sub else False,
    }
