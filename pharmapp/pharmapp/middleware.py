import time
import threading
import requests
from django.conf import settings
from django.core.cache import cache


class OfflineMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Service-Worker-Allowed'] = '/'
        return response

    def process_template_response(self, request, response):
        if hasattr(response, 'context_data'):
            response.context_data['offline_enabled'] = True
        return response


class ConnectionDetectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.last_check = 0
        self.cached_status = True
        self._checking = False

    def __call__(self, request):
        current_time = time.time()
        # Fire background check when interval elapsed — never block the request
        if current_time - self.last_check > 30 and not self._checking:
            self._checking = True
            threading.Thread(target=self._check_connectivity, daemon=True).start()

        is_online = self.cached_status
        request.is_online = is_online
        request.current_database = 'default' if is_online else 'offline'

        response = self.get_response(request)
        response['X-Connection-Status'] = 'online' if is_online else 'offline'
        return response

    def _check_connectivity(self):
        try:
            r = requests.get('https://httpbin.org/status/200', timeout=2)
            self.cached_status = r.status_code == 200
        except Exception:
            self.cached_status = False
        finally:
            self.last_check = time.time()
            cache.set('connection_status', self.cached_status, 30)
            self._checking = False

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


