from django.db import connections
from django.conf import settings
import requests
import threading
from django.shortcuts import render

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
        self._thread_local = threading.local()
        
    def __call__(self, request):
        # Check internet connectivity
        self._thread_local.is_online = self._check_connectivity()
        
        # Set the appropriate database
        self._set_database()
        
        # Store connection status in request
        request.is_online = self._thread_local.is_online
        
        response = self.get_response(request)
        
        # Add connection status headers
        response['X-Connection-Status'] = 'online' if self._thread_local.is_online else 'offline'
        
        return response
    
    def _check_connectivity(self):
        try:
            requests.get('https://8.8.8.8', timeout=1)
            return True
        except requests.RequestException:
            return False
    
    def _set_database(self):
        # Set the current database on the thread local
        self._thread_local.current_database = 'default' if self._thread_local.is_online else 'offline'

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


