from django.core.cache import cache
from django.conf import settings
import time


def performance_metrics(request):
    """
    Add performance metrics to template context
    """
    # Get or set performance stats
    cache_key = 'performance_stats'
    stats = cache.get(cache_key, {
        'page_loads': 0,
        'avg_response_time': 0,
        'cache_hits': 0,
        'cache_misses': 0,
    })
    
    # Update page load counter
    stats['page_loads'] += 1
    
    # Calculate approximate response time (this is a simplified metric)
    if hasattr(request, 'start_time'):
        response_time = time.time() - request.start_time
        stats['avg_response_time'] = (stats['avg_response_time'] + response_time) / 2
    
    # Update cache every 10 page loads
    if stats['page_loads'] % 10 == 0:
        cache.set(cache_key, stats, 300)  # Cache for 5 minutes
    
    return {
        'performance_debug': settings.DEBUG,
        'performance_stats': stats,
    }
