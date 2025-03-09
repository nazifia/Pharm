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