from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string


def permission_required(permission_name, redirect_url=None):
    """
    Decorator to check if user has a specific permission based on their role.
    
    Args:
        permission_name (str): The permission to check for
        redirect_url (str): URL to redirect to if permission denied (optional)
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            # Check if user has the required permission
            if hasattr(request.user, 'has_permission') and request.user.has_permission(permission_name):
                return view_func(request, *args, **kwargs)
            
            # If user doesn't have permission
            messages.error(request, f'You do not have permission to {permission_name.replace("_", " ")}.')
            
            if redirect_url:
                return redirect(redirect_url)
            else:
                # Return a 403 Forbidden response
                return HttpResponseForbidden(
                    render_to_string('403.html', {'permission': permission_name}, request=request)
                )
        
        return _wrapped_view
    return decorator


def role_required(allowed_roles, redirect_url=None):
    """
    Decorator to check if user has one of the allowed roles.
    
    Args:
        allowed_roles (list): List of allowed user types/roles
        redirect_url (str): URL to redirect to if access denied (optional)
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            # Check if user has profile and user_type
            if not hasattr(request.user, 'profile') or not request.user.profile.user_type:
                messages.error(request, 'Your account does not have a valid user type assigned.')
                return redirect('userauth:login')
            
            # Check if user's role is in allowed roles
            if request.user.profile.user_type in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            # If user doesn't have required role
            messages.error(request, f'Access denied. Required role: {", ".join(allowed_roles)}')
            
            if redirect_url:
                return redirect(redirect_url)
            else:
                return HttpResponseForbidden(
                    render_to_string('403.html', {
                        'required_roles': allowed_roles,
                        'user_role': request.user.profile.user_type
                    }, request=request)
                )
        
        return _wrapped_view
    return decorator


def admin_required(view_func):
    """
    Decorator to require Admin role.
    """
    return role_required(['Admin'])(view_func)


def manager_or_admin_required(view_func):
    """
    Decorator to require Manager or Admin role.
    """
    return role_required(['Admin', 'Manager'])(view_func)


def pharmacist_or_above_required(view_func):
    """
    Decorator to require Pharmacist, Manager, or Admin role.
    """
    return role_required(['Admin', 'Manager', 'Pharmacist'])(view_func)


def staff_required(view_func):
    """
    Decorator to require any staff role (excludes guests).
    """
    return role_required(['Admin', 'Manager', 'Pharmacist', 'Pharm-Tech', 'Salesperson'])(view_func)


class PermissionMixin:
    """
    Mixin for class-based views to check permissions.
    """
    required_permission = None
    required_roles = None
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return redirect('userauth:login')
        
        # Check role requirements
        if self.required_roles:
            if not hasattr(request.user, 'profile') or not request.user.profile.user_type:
                messages.error(request, 'Your account does not have a valid user type assigned.')
                return redirect('userauth:login')
            
            if request.user.profile.user_type not in self.required_roles:
                messages.error(request, f'Access denied. Required role: {", ".join(self.required_roles)}')
                return HttpResponseForbidden(
                    render_to_string('403.html', {
                        'required_roles': self.required_roles,
                        'user_role': request.user.profile.user_type
                    }, request=request)
                )
        
        # Check permission requirements
        if self.required_permission:
            if not (hasattr(request.user, 'has_permission') and request.user.has_permission(self.required_permission)):
                messages.error(request, f'You do not have permission to {self.required_permission.replace("_", " ")}.')
                return HttpResponseForbidden(
                    render_to_string('403.html', {'permission': self.required_permission}, request=request)
                )
        
        return super().dispatch(request, *args, **kwargs)


def superuser_required(view_func):
    """
    Decorator to require superuser status.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        messages.error(request, 'Superuser access required.')
        return HttpResponseForbidden(
            render_to_string('403.html', {'superuser_required': True}, request=request)
        )
    
    return _wrapped_view


def check_user_permissions(user, required_permissions):
    """
    Helper function to check if a user has all required permissions.
    
    Args:
        user: User object
        required_permissions (list): List of required permissions
    
    Returns:
        bool: True if user has all permissions, False otherwise
    """
    if not hasattr(user, 'has_permission'):
        return False
    
    for permission in required_permissions:
        if not user.has_permission(permission):
            return False
    
    return True


def get_user_permissions_context(user):
    """
    Helper function to get user permissions for template context.
    
    Args:
        user: User object
    
    Returns:
        dict: Dictionary containing user permissions and role info
    """
    context = {
        'user_permissions': [],
        'user_role': None,
        'is_admin': False,
        'is_manager': False,
        'is_pharmacist': False,
        'is_staff': False
    }
    
    if hasattr(user, 'profile') and user.profile.user_type:
        context['user_role'] = user.profile.user_type
        context['user_permissions'] = user.get_permissions()
        context['is_admin'] = user.profile.user_type == 'Admin'
        context['is_manager'] = user.profile.user_type in ['Admin', 'Manager']
        context['is_pharmacist'] = user.profile.user_type in ['Admin', 'Manager', 'Pharmacist']
        context['is_staff'] = user.profile.user_type in ['Admin', 'Manager', 'Pharmacist', 'Pharm-Tech', 'Salesperson']
    
    return context
