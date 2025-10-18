import time
import logging
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware:
    """
    Middleware to monitor and log performance metrics
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Record start time
        start_time = time.time()
        request.start_time = start_time
        
        # Process request
        response = self.get_response(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Log slow requests (over 1 second)
        if response_time > 1.0:
            logger.warning(
                f"Slow request: {request.method} {request.path} took {response_time:.2f}s"
            )
        
        # Add performance headers
        response['X-Response-Time'] = f"{response_time:.3f}s"
        
        # Update performance metrics
        self.update_performance_metrics(response_time)
        
        return response
    
    def update_performance_metrics(self, response_time):
        """Update performance metrics in cache"""
        try:
            cache_key = 'response_times'
            times = cache.get(cache_key, [])
            
            # Keep only last 100 response times
            times.append(response_time)
            if len(times) > 100:
                times = times[-100:]
            
            cache.set(cache_key, times, 300)  # Cache for 5 minutes
        except Exception as e:
            logger.error(f"Failed to update performance metrics: {e}")


class QueryCountMiddleware:
    """
    Middleware to count database queries for performance monitoring
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings
        from django.db import connection
        
        # Reset query count
        initial_queries = len(connection.queries) if settings.DEBUG else 0
        
        # Process request
        response = self.get_response(request)
        
        # Count queries
        if settings.DEBUG:
            query_count = len(connection.queries) - initial_queries
            response['X-DB-Queries'] = str(query_count)
            
            # Log if too many queries
            if query_count > 50:
                logger.warning(
                    f"High query count: {request.method} {request.path} executed {query_count} queries"
                )
        
        return response
