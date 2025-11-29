"""
No-Cache Middleware for PharmApp
Prevents caching of all HTML pages to ensure fresh data on navigation
"""

class NoCacheMiddleware:
    """
    Middleware to add cache-control headers to all HTML responses
    to prevent browser and proxy caching of dynamic pages.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only apply to HTML responses (not static files, API responses, etc.)
        content_type = response.get('Content-Type', '')

        if 'text/html' in content_type:
            # Add aggressive no-cache headers to all HTML pages
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

            # Add ETag with timestamp to force revalidation
            import time
            response['ETag'] = f'"{int(time.time())}"'

            # Prevent caching in proxies
            response['Vary'] = 'Accept-Encoding, Cookie'

        return response
