from django.utils.deprecation import MiddlewareMixin
from .models import ActivityLog, User  # Import User from our models
from django.contrib.auth import logout
from django.conf import settings
from django.utils import timezone
from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.http import HttpResponseForbidden
from django.contrib import messages



class ActivityMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Only log for authenticated users
        if request.user.is_authenticated:
            # Skip logging for static and media files
            if not (request.path.startswith('/static/') or request.path.startswith('/media/')):
                # Create a more descriptive action
                action = f"{request.method} {request.path}"
                # Add query parameters if they exist, but exclude sensitive data
                if request.GET and 'password' not in request.GET:
                    action += f" Params: {dict(request.GET)}"
                # Create the activity log
                ActivityLog.objects.create(user=request.user, action=action)
        return None



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



class RoleBasedAccessMiddleware:
    """Middleware to enforce role-based access control"""
    def __init__(self, get_response):
        self.get_response = get_response
        # URL patterns that require specific roles
        self.role_required_urls = {
            # Admin-only URLs
            'userauth:register': ['Admin'],
            'userauth:activity_dashboard': ['Admin', 'Manager'],
            'admin:index': ['Admin'],
            'store:create_stock_check': ['Admin', 'Manager', 'Pharm-Tech'],
            'wholesale:create_wholesale_stock_check': ['Admin', 'Manager', 'Pharm-Tech'],

            # Financial management
            'store:expense_list': ['Admin', 'Manager'],
            'store:add_expense': ['Admin', 'Manager'],
            'store:daily_sales': ['Admin', 'Manager'],
            'store:monthly_sales': ['Admin', 'Manager'],

            # Procurement management
            'store:add_procurement': ['Admin', 'Manager', 'Pharm-Tech'],
            'store:procurement_list': ['Admin', 'Manager', 'Pharm-Tech'],
            'store:register_supplier_view': ['Admin', 'Manager'],
            'store:supplier_list': ['Admin', 'Manager'],

            # Inventory management
            'store:transfer_multiple_store_items': ['Admin', 'Manager', 'Pharm-Tech'],
            'wholesale:transfer_multiple_wholesale_items': ['Admin', 'Manager', 'Pharm-Tech'],
        }

    def __call__(self, request):
        # Skip middleware for unauthenticated users (they'll be redirected to login)
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Get the current URL name
        try:
            current_url_name = resolve(request.path_info).url_name
            namespace = resolve(request.path_info).namespace
            if namespace:
                current_url = f"{namespace}:{current_url_name}"
            else:
                current_url = current_url_name
        except:
            # If URL can't be resolved, just continue
            return self.get_response(request)

        # Check if this URL has role restrictions
        if current_url in self.role_required_urls:
            allowed_roles = self.role_required_urls[current_url]
            user_role = request.user.profile.user_type

            if user_role not in allowed_roles:
                messages.error(request, f"Access denied. You need to be a {', '.join(allowed_roles)} to access this page.")
                # Redirect to dashboard or previous page
                return redirect('store:dashboard')

        response = self.get_response(request)
        return response


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