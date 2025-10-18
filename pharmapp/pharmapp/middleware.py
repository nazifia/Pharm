from django.db import connections
from django.conf import settings
import requests
import threading
from django.shortcuts import render
from django.core.cache import cache

class OfflineMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add offline detection headers
        response['Service-Worker-Allowed'] = '/'
        
        return response

    def process_template_response(self, request, response):
        # Add offline context to all template responses
        if hasattr(response, 'context_data'):
            response.context_data['offline_enabled'] = True
        return response

class ConnectionDetectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.last_check = 0
        self.cached_status = True

    def __call__(self, request):
        import time
        
        # Cache connectivity status for 30 seconds to avoid excessive checks
        current_time = time.time()
        if current_time - self.last_check > 30:
            is_online = self._check_connectivity()
            self.cached_status = is_online
            self.last_check = current_time
            
            # Cache status in Django cache as well
            cache.set('connection_status', is_online, 30)
        else:
            # Use cached status
            is_online = self.cached_status

        # Store connection status in request (request-scoped, not thread-local)
        request.is_online = is_online
        request.current_database = 'default' if is_online else 'offline'

        response = self.get_response(request)

        # Add connection status headers
        response['X-Connection-Status'] = 'online' if is_online else 'offline'

        return response

    def _check_connectivity(self):
        """
        Check internet connectivity with improved error handling and caching.
        """
        try:
            # Use a very fast connectivity check
            response = requests.get('https://httpbin.org/status/200', timeout=0.5)
            return response.status_code == 200
        except requests.RequestException:
            # If external check fails, assume offline
            return False
        except Exception:
            # For any other errors, assume offline
            return False

class SyncMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Trigger sync if online
        if getattr(request, 'is_online', False):
            self._trigger_sync(request)
        
        return response
    
    def _trigger_sync(self, request):
        try:
            from .tasks import sync_databases
            sync_databases.delay()  # Assuming you're using Celery
        except ImportError:
            # Fallback to synchronous sync if Celery is not configured
            self._sync_databases()
    
    def _sync_databases(self):
        """
        Synchronous database sync for when Celery is not available
        """
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # Add your sync logic here
                pass
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Sync failed: {str(e)}")


