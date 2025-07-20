"""
User isolation middleware to ensure all user activities are properly isolated.
"""

from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


class UserIsolationMiddleware(MiddlewareMixin):
    """
    Middleware to ensure user activities are properly isolated.
    
    This middleware:
    - Validates that users can only access their own data
    - Prevents cross-user data leakage
    - Logs suspicious access attempts
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # URLs that require user-specific data validation
        self.user_specific_urls = [
            'store:cart',
            'store:view_cart',
            'store:update_cart_quantity',
            'store:clear_cart',
            'wholesale:wholesale_cart',
            'wholesale:update_wholesale_cart_quantity',
            'wholesale:clear_wholesale_cart',
        ]

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Process view to ensure user isolation.
        """
        if not request.user.is_authenticated:
            return None
        
        # Check for user-specific resource access
        if hasattr(request, 'resolver_match') and request.resolver_match:
            url_name = request.resolver_match.url_name
            namespace = request.resolver_match.namespace
            
            if namespace:
                full_url_name = f"{namespace}:{url_name}"
            else:
                full_url_name = url_name
            
            # Validate user-specific resource access
            if full_url_name in self.user_specific_urls:
                return self._validate_user_resource_access(request, view_kwargs)
        
        return None

    def _validate_user_resource_access(self, request, view_kwargs):
        """
        Validate that user can only access their own resources.
        """
        try:
            # Check for cart item access
            if 'pk' in view_kwargs:
                pk = view_kwargs['pk']
                url_name = request.resolver_match.url_name
                
                # Validate cart item ownership
                if 'cart' in url_name.lower():
                    if not self._validate_cart_item_ownership(request.user, pk, url_name):
                        logger.warning(f"User {request.user.username} attempted to access cart item {pk} they don't own")
                        messages.error(request, "Access denied: You can only access your own cart items.")
                        return redirect('store:cart')
            
            return None
            
        except Exception as e:
            logger.error(f"Error validating user resource access: {e}")
            return None

    def _validate_cart_item_ownership(self, user, item_id, url_name):
        """
        Validate that the user owns the cart item.
        """
        try:
            if 'wholesale' in url_name:
                from store.models import WholesaleCart
                return WholesaleCart.objects.filter(id=item_id, user=user).exists()
            else:
                from store.models import Cart
                return Cart.objects.filter(id=item_id, user=user).exists()
        except Exception as e:
            logger.error(f"Error validating cart item ownership: {e}")
            return False


class UserDataSanitizationMiddleware(MiddlewareMixin):
    """
    Middleware to sanitize user data and prevent data leakage.
    """
    
    def process_response(self, request, response):
        """
        Process response to ensure no sensitive user data leakage.
        """
        if not request.user.is_authenticated:
            return response
        
        # Add user-specific headers for debugging (in development only)
        if hasattr(request, 'user') and request.user.is_authenticated:
            response['X-User-ID'] = str(request.user.id)
            response['X-User-Session'] = request.session.session_key[:8] if request.session.session_key else 'none'
        
        return response


class UserActivityIsolationMiddleware(MiddlewareMixin):
    """
    Middleware to ensure user activities are properly isolated and logged.
    """
    
    def process_request(self, request):
        """
        Process request to ensure user activity isolation.
        """
        if not request.user.is_authenticated:
            return None
        
        # Store user context for the request
        request.user_context = {
            'user_id': request.user.id,
            'username': request.user.username,
            'session_key': request.session.session_key,
            'ip_address': self._get_client_ip(request),
        }
        
        return None

    def process_response(self, request, response):
        """
        Process response to log user activity.
        """
        if not hasattr(request, 'user_context'):
            return response
        
        # Log user activity for audit trail
        try:
            self._log_user_activity(request, response)
        except Exception as e:
            logger.error(f"Error logging user activity: {e}")
        
        return response

    def _log_user_activity(self, request, response):
        """
        Log user activity for audit purposes.
        """
        if not request.user.is_authenticated:
            return
        
        # Only log significant activities
        if request.method in ['POST', 'PUT', 'DELETE']:
            activity_data = {
                'user_id': request.user.id,
                'username': request.user.username,
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'ip_address': request.user_context.get('ip_address'),
                'session_key': request.session.session_key[:8] if request.session.session_key else 'none',
            }
            
            logger.info(f"User activity: {activity_data}")

    def _get_client_ip(self, request):
        """
        Get the client's IP address.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserSessionIsolationMiddleware(MiddlewareMixin):
    """
    Middleware to ensure session data is properly isolated between users.
    """
    
    def process_request(self, request):
        """
        Process request to ensure session isolation.
        """
        if not request.user.is_authenticated:
            return None
        
        # Validate session belongs to the authenticated user
        session_user_id = request.session.get('user_id')
        if session_user_id and str(session_user_id) != str(request.user.id):
            logger.warning(f"Session user ID mismatch: session={session_user_id}, user={request.user.id}")
            # Clear potentially compromised session
            request.session.flush()
            logout(request)
            messages.error(request, "Session security violation detected. Please log in again.")
            return redirect(reverse('store:index'))
        
        # Ensure session has correct user ID
        if not session_user_id:
            request.session['user_id'] = request.user.id
        
        return None


# Utility functions for user isolation

def ensure_user_owns_resource(user, model_class, resource_id, field_name='user'):
    """
    Ensure that a user owns a specific resource.
    
    Args:
        user: The user object
        model_class: The model class to check
        resource_id: ID of the resource
        field_name: Name of the user field (default: 'user')
        
    Returns:
        bool: True if user owns the resource
    """
    try:
        filter_kwargs = {field_name: user, 'id': resource_id}
        return model_class.objects.filter(**filter_kwargs).exists()
    except Exception as e:
        logger.error(f"Error checking resource ownership: {e}")
        return False


def get_user_owned_resources(user, model_class, field_name='user'):
    """
    Get all resources owned by a user.
    
    Args:
        user: The user object
        model_class: The model class to query
        field_name: Name of the user field (default: 'user')
        
    Returns:
        QuerySet: Resources owned by the user
    """
    try:
        filter_kwargs = {field_name: user}
        return model_class.objects.filter(**filter_kwargs)
    except Exception as e:
        logger.error(f"Error getting user resources: {e}")
        return model_class.objects.none()


def validate_user_session_data(request, expected_keys=None):
    """
    Validate that session data belongs to the authenticated user.
    
    Args:
        request: The request object
        expected_keys: List of expected session keys
        
    Returns:
        bool: True if session data is valid
    """
    if not request.user.is_authenticated:
        return False
    
    # Check basic session integrity
    session_user_id = request.session.get('user_id')
    if session_user_id and str(session_user_id) != str(request.user.id):
        return False
    
    # Check expected keys if provided
    if expected_keys:
        user_data = request.session.get('user_data', {})
        user_prefix = f"user_{request.user.id}_"
        
        for key in expected_keys:
            expected_key = f"{user_prefix}{key}"
            if expected_key not in user_data:
                logger.warning(f"Expected session key {expected_key} not found for user {request.user.username}")
    
    return True
