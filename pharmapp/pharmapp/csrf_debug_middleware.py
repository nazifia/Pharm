import logging
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)


class CSRFDebugMiddleware:
    """
    Middleware to provide better debugging information for CSRF failures
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """Handle CSRF exceptions and provide better error messages"""
        if isinstance(exception, PermissionDenied) and 'CSRF' in str(exception):
            logger.error(
                f"CSRF verification failed for {request.method} {request.path} "
                f"from IP {request.META.get('REMOTE_ADDR')} "
                f"User: {request.user if request.user.is_authenticated else 'Anonymous'} "
                f"Headers: {dict(request.headers)}"
            )
            # Return a more informative error response
            return JsonResponse({
                'error': 'CSRF verification failed',
                'path': request.path,
                'method': request.method,
                'message': 'Please ensure your form includes a valid CSRF token'
            }, status=403)
