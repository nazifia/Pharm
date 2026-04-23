import json
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect


EXEMPT_PREFIXES = (
    '/store/index/',
    '/store/logout_user/',
    '/subscription/',   # all subscription pages exempt (expired wall, status, setup)
    '/admin/',
    '/static/',
    '/media/',
    '/api/health/',
    '/sw.js',
    '/favicon.ico',
)

# API paths return JSON instead of HTML redirect
API_PREFIXES = ('/api/',)


class SubscriptionMiddleware:
    """
    Blocks non-superuser access when no active subscription exists.
    Superusers always pass through so the owner can always log in.
    API paths receive a 402 JSON response instead of an HTML redirect.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_check(request):
            from .models import Subscription
            sub = Subscription.get_current()
            if sub:
                sub.sync_status()
                if not sub.is_active:
                    return self._block(request)
            else:
                any_sub = Subscription.objects.order_by('-end_date').first()
                if any_sub:
                    any_sub.sync_status()
                return self._block(request)
        return self.get_response(request)

    def _should_check(self, request):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            bypass_mobile = getattr(settings, 'SUBSCRIPTION_BYPASS_MOBILE', None)
            if bypass_mobile is None or getattr(request.user, 'mobile', None) == bypass_mobile:
                return False
        if any(request.path.startswith(p) for p in EXEMPT_PREFIXES):
            return False
        return True

    def _block(self, request):
        if any(request.path.startswith(p) for p in API_PREFIXES):
            return JsonResponse(
                {'error': 'subscription_expired', 'detail': 'Annual subscription has expired. Renew to restore access.'},
                status=402,
            )
        return redirect('subscription:expired')
