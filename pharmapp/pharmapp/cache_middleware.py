from django.core.cache import cache
from django.http import JsonResponse
import hashlib
import time
import json


class SmartCacheMiddleware:
    """
    Middleware to cache responses for frequently accessed API endpoints
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Endpoints to cache with their TTL (in seconds)
        self.cache_config = {
            '/api/health/': 60,  # Cache health check for 1 minute
            '/store/notifications/count/': 30,  # Cache notifications for 30 seconds
            '/chat/api/unread-count/': 15,  # Cache unread count for 15 seconds
        }
    
    def __call__(self, request):
        # Only cache GET requests for specific endpoints
        if request.method == 'GET' and request.path in self.cache_config:
            cache_key = self._get_cache_key(request)
            cached_response = cache.get(cache_key)
            
            if cached_response:
                return cached_response
        
        # Process the request
        response = self.get_response(request)
        
        # Cache the response if it meets criteria
        if (
            request.method == 'GET' 
            and request.path in self.cache_config 
            and response.status_code == 200
            and isinstance(response, JsonResponse)
        ):
            cache_key = self._get_cache_key(request)
            cache.set(cache_key, response, self.cache_config[request.path])
        
        return response
    
    def _get_cache_key(self, request):
        """Generate a cache key for the request"""
        # Check if user is available (authentication middleware might not have run yet)
        try:
            user_id = request.user.id if hasattr(request, 'user') and request.user.is_authenticated else 'anonymous'
        except AttributeError:
            user_id = 'anonymous'
        
        path_hash = hashlib.md5(request.path.encode()).hexdigest()
        return f'response_cache:{request.path}:{user_id}:{path_hash}'
