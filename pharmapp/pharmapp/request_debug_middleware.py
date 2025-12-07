import logging

logger = logging.getLogger(__name__)


class RequestDebugMiddleware:
    """
    Middleware to debug unexpected POST requests to user details page
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log all POST requests to user details
        if request.method == 'POST' and '/users/details/' in request.path:
            logger.warning(
                f"Unexpected POST request to {request.path}\n"
                f"Headers: {dict(request.headers)}\n"
                f"Body: {request.body}\n"
                f"Referer: {request.META.get('HTTP_REFERER', 'No referer')}\n"
                f"User Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}"
            )
        
        response = self.get_response(request)
        return response
