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
    """
    Middleware to automatically log user activities.
    Records detailed information about user actions for auditing and monitoring.
    """
    def process_request(self, request):
        # Only log for authenticated users
        if request.user.is_authenticated:
            # Skip logging for static and media files
            if not (request.path.startswith('/static/') or request.path.startswith('/media/')):
                # Determine action type based on request method
                if request.method == 'GET':
                    action_type = 'VIEW'
                elif request.method == 'POST':
                    if 'delete' in request.path.lower():
                        action_type = 'DELETE'
                    elif 'create' in request.path.lower() or 'add' in request.path.lower():
                        action_type = 'CREATE'
                    elif 'edit' in request.path.lower() or 'update' in request.path.lower():
                        action_type = 'UPDATE'
                    elif 'login' in request.path.lower():
                        action_type = 'LOGIN'
                    elif 'logout' in request.path.lower():
                        action_type = 'LOGOUT'
                    elif 'transfer' in request.path.lower():
                        action_type = 'TRANSFER'
                    elif 'payment' in request.path.lower() or 'receipt' in request.path.lower():
                        action_type = 'PAYMENT'
                    elif 'export' in request.path.lower():
                        action_type = 'EXPORT'
                    elif 'import' in request.path.lower():
                        action_type = 'IMPORT'
                    else:
                        action_type = 'OTHER'
                else:
                    action_type = 'OTHER'

                # Create a more descriptive action
                action = f"{request.method} {request.path}"

                # Add query parameters if they exist, but exclude sensitive data
                if request.GET and not any(param in request.GET for param in ['password', 'token', 'key']):
                    action += f" Params: {dict(request.GET)}"

                # Try to determine target model from URL
                target_model = None
                target_id = None

                # Extract model name from URL path segments
                path_parts = request.path.strip('/').split('/')
                if len(path_parts) > 1:
                    # Try to identify model name from URL
                    model_candidates = ['user', 'customer', 'supplier', 'item', 'product',
                                       'receipt', 'expense', 'procurement', 'stock']
                    for part in path_parts:
                        for candidate in model_candidates:
                            if candidate in part.lower():
                                target_model = candidate.capitalize()
                                break
                        if target_model:
                            break

                # Try to extract ID from URL if it's a numeric segment
                for part in path_parts:
                    if part.isdigit():
                        target_id = part
                        break

                # Get IP address and user agent
                ip_address = self._get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')

                # Create the activity log using the helper method
                ActivityLog.log_activity(
                    user=request.user,
                    action=action,
                    action_type=action_type,
                    target_model=target_model,
                    target_id=target_id,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
        return None

    def _get_client_ip(self, request):
        """Get the client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip



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
    """
    Middleware to enforce role-based access control.
    Restricts access to specific URLs based on user roles.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # URL patterns that require specific roles
        self.role_required_urls = {
            # User Management
            'userauth:register': ['Admin'],
            # Note: activity_dashboard now uses permission-based checking in the view
            'userauth:permissions_management': ['Admin'],
            'userauth:generate_test_logs': ['Admin'],
            'userauth:user_list': ['Admin'],
            'userauth:edit_user': ['Admin'],
            'userauth:delete_user': ['Admin'],
            'userauth:toggle_user_status': ['Admin'],
            'admin:index': ['Admin'],
            'admin:app_list': ['Admin'],

            # Stock Management - Now accessible to all authenticated users
            # 'store:create_stock_check': ['Admin', 'Manager', 'Pharm-Tech'],
            # 'store:update_stock_check': ['Admin', 'Manager', 'Pharm-Tech'],
            # 'store:list_stock_checks': ['Admin', 'Manager', 'Pharm-Tech'],
            # 'wholesale:create_wholesale_stock_check': ['Admin', 'Manager', 'Pharm-Tech'],
            # 'wholesale:update_wholesale_stock_check': ['Admin', 'Manager', 'Pharm-Tech'],
            # 'wholesale:list_wholesale_stock_checks': ['Admin', 'Manager', 'Pharm-Tech'],

            # Financial Management
            # Note: expense_list and add_expense are now accessible to all authenticated users
            # Only edit and delete operations are restricted to Admin/Manager
            'store:edit_expense_form': ['Admin', 'Manager'],
            'store:update_expense': ['Admin', 'Manager'],
            'store:delete_expense': ['Admin', 'Manager'],
            'store:daily_sales': ['Admin', 'Manager'],
            'store:monthly_sales': ['Admin', 'Manager'],
            'store:sales_by_payment_method': ['Admin', 'Manager'],

            # Procurement Management - Now handled by permission-based decorators in views
            # 'store:add_procurement': ['Admin', 'Manager', 'Pharm-Tech'],
            # 'store:procurement_list': ['Admin', 'Manager', 'Pharm-Tech'],
            'store:edit_procurement': ['Admin', 'Manager'],
            'store:delete_procurement': ['Admin', 'Manager'],

            # Supplier Management
            'store:register_supplier_view': ['Admin', 'Manager'],
            'store:supplier_list': ['Admin', 'Manager', 'Pharm-Tech'],
            'store:edit_supplier': ['Admin', 'Manager'],
            'store:delete_supplier': ['Admin', 'Manager'],

            # Customer Management
            'store:register_customer_view': ['Admin', 'Manager', 'Pharmacist', 'Pharm-Tech'],
            'store:customer_list': ['Admin', 'Manager', 'Pharmacist', 'Pharm-Tech', 'Salesperson'],
            'store:edit_customer': ['Admin', 'Manager', 'Pharmacist'],
            'store:delete_customer': ['Admin', 'Manager'],

            # Inventory Management
            'store:delete_item': ['Admin', 'Manager'],
            'wholesale:delete_wholesale_item': ['Admin', 'Manager'],
            'store:transfer_multiple_store_items': ['Admin', 'Manager', 'Pharm-Tech'],
            'wholesale:transfer_multiple_wholesale_items': ['Admin', 'Manager', 'Pharm-Tech'],
            'store:adjust_prices': ['Admin', 'Manager'],

            # Sales Management
            'store:generate_receipt': ['Admin', 'Manager', 'Pharmacist', 'Pharm-Tech', 'Salesperson'],
            'store:receipt_list': ['Admin', 'Manager', 'Pharmacist', 'Pharm-Tech', 'Salesperson'],
            'wholesale:generate_wholesale_receipt': ['Admin', 'Manager', 'Pharmacist', 'Pharm-Tech', 'Salesperson'],
            'wholesale:wholesale_receipt_list': ['Admin', 'Manager', 'Pharmacist', 'Pharm-Tech', 'Salesperson'],

            # Dispensing
            'store:dispense_medication': ['Admin', 'Pharmacist'],
            'store:dispensing_log': ['Admin', 'Manager', 'Pharmacist'],
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

            # Check if user has a profile
            if not hasattr(request.user, 'profile') or not request.user.profile:
                # Create a default profile for users without one
                from userauth.models import Profile
                Profile.objects.get_or_create(user=request.user, defaults={
                    'full_name': request.user.username or request.user.mobile,
                    'user_type': 'Salesperson'  # Default role
                })
                # Refresh the user object to get the new profile
                request.user.refresh_from_db()

            # Superusers have access to everything
            if not request.user.is_superuser:
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
            # Check for auto-logout based on inactivity
            last_activity_str = request.session.get('last_activity')
            if last_activity_str:
                try:
                    # Parse the last activity with timezone
                    last_activity = timezone.datetime.fromisoformat(last_activity_str)
                    idle_duration = timezone.now() - last_activity
                    if idle_duration.total_seconds() > settings.AUTO_LOGOUT_DELAY * 60:  # Convert minutes to seconds
                        # Log the auto-logout for security monitoring
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(f"Auto-logout triggered for user {request.user.username} after {idle_duration.total_seconds()} seconds of inactivity")

                        logout(request)
                        # Clear session data for security
                        request.session.flush()
                except ValueError:
                    # Handle any parsing errors gracefully
                    request.session.pop('last_activity', None)

            # Save the current time with timezone in ISO format (only for authenticated users)
            request.session['last_activity'] = timezone.now().isoformat()

        response = self.get_response(request)
        return response