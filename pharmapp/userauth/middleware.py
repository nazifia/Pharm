from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import User
from .models import ActivityLog
from django.contrib.auth import logout
from django.conf import settings
from django.utils import timezone



class ActivityMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.user.is_authenticated:
            action = f"{request.method} {request.path}"
            ActivityLog.objects.create(user=request.user, action=action)
            
            
            
# class AutoLogoutMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         response = self.get_response(request)
#         if request.user.is_authenticated:
#             last_activity_str = request.session.get('last_activity')
#             if last_activity_str:
#                 last_activity = timezone.datetime.strptime(last_activity_str, '%Y-%m-%d %H:%M:%S.%f%z')
#                 idle_duration = timezone.now() - last_activity
#                 if idle_duration.seconds > settings.AUTO_LOGOUT_DELAY * 420:
#                     logout(request)
#             request.session['last_activity'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S.%f%z')
#         return response



class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity_str = request.session.get('last_activity')
            if last_activity_str:
                try:
                    # Parse the last activity with timezone
                    last_activity = timezone.datetime.fromisoformat(last_activity_str)
                    idle_duration = timezone.now() - last_activity
                    if idle_duration.total_seconds() > settings.AUTO_LOGOUT_DELAY * 420:
                        logout(request)
                except ValueError:
                    # Handle any parsing errors gracefully
                    request.session.pop('last_activity', None)

            # Save the current time with timezone in ISO format
            request.session['last_activity'] = timezone.now().isoformat()

        response = self.get_response(request)
        return response