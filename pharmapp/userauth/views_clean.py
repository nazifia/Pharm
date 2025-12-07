from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.urls import reverse
from userauth.models import *
from .forms import *
from store.views import is_admin

# Cache utility functions for search optimization
def get_search_cache_key(model_name, query, user_id=None):
    """Generate cache key for search queries"""
    if user_id:
        return f"{model_name}_{user_id}_{str(query)}"

from django.core.cache import cache

# Import required models for transfer functionality
from .models import TransferRequest, WholesaleItem

# Import GS1 barcode parser
from .gs1_parser import parse_barcode, is_gs1_barcode

# Import ActivityLog for audit trail
from userauth.models import ActivityLog

# Import HTML library for rendering tables
import json
from django.core.serializers.json import DjangoJSONEncoder

# Import datetime for timezone handling
from django.utils import timezone
from datetime import datetime, timedelta

# Cache utility functions for search optimization
def get_search_cache_key(model_name, query, user_id=None):
    """Generate cache key for search queries"""
    if user_id:
        return f"{model_name}_{user_id}_{str(query)}"

def is_password_change_allowed(request, user_to_change):
    """Check if user is allowed to change password of user_to_change"""
    # Superusers can always change passwords
    if request.user.is_superuser:
        return True
    
    # Admins and Managers can change passwords
    if hasattr(request.user, 'profile') and request.user.profile.user_type in ['Admin', 'Manager']:
        return True
    
    # Check if user has the specific permission
    return user_to_change.has_permission('manage_user_passwords')

def change_user_password(request, user_id):
    """Main password change view for authorized users"""
    if not is_password_change_allowed(request, user_to_change):
        messages.error(request, 'You do not have permission to change passwords.')
        return redirect('userauth:user_list')
    
    try:
        user_to_change = User.objects.get(id=user_id)
        if not user_to_change:
            messages.error(request, 'User not found.')
            return redirect('userauth:user_list')
        
        if request.method == 'POST':
            form = PasswordChangeForm(request.POST, user=user_to_change)
            if form.is_valid():
                # Store old password hash before changing
                old_password_hash = user_to_change.password
                
                # Change the password
                new_password = form.cleaned_data['new_password']
                user_to_change.set_password(new_password)
                user_to_change.save()
                
                # Get client information for audit
                ip_address = get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                
                # Log the password change in history
                PasswordChangeHistory.log_password_change(
                    user=user_to_change,
                    changed_by=request.user,
                    old_password_hash=old_password_hash,
                    change_reason=form.cleaned_data['change_reason'],
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Log the activity in the main activity log
                ActivityLog.log_activity(
                    user=request.user,
                    action=f"Changed password for user: {user_to_change.username}",
                    action_type='UPDATE',
                    target_model='User',
                    target_id=str(user_to_change.id),
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                messages.success(request, f'Password for {user_to_change.username} has been changed successfully.')
                
                print(f"DEBUG: User {user_to_change.username} password before: {old_password_hash}")
                print(f"DEBUG: User {user_to_change.username} password after: {user_to_change.check_password('newsecurepass456')}")
                
                return redirect('userauth:user_details', user_id=user_id)
        else:
            form = PasswordChangeForm(user=user_to_change)
        
        context = {
            'form': form,
            'user_to_change': user_to_change,
            'title': f'Change Password - {user_to_change.username}'
        }
        
        # If it's an HTMX request, return just the form
        if request.headers.get('HX-Request'):
            return render(request, 'userauth/partials/password_change_form.html', context)
        
        return render(request, 'userauth/change_user_password.html', context)
        
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('userauth:user_list')
    
    except Exception as e:
        # Log error for debugging
        logging.error(f"Error changing password: {str(e)}")
        messages.error(request, f'Error changing password for user ID {user_id}: {str(e)}')
        return redirect('userauth:user_list')


@login_required
@role_required(['Admin', 'Manager'])
def password_change_history(request, user_id):
    """View password change history for a user"""
    if not request.user.has_permission('view_activity_logs'):
        messages.error(request, 'You do not have permission to view password history.')
        return redirect('userauth:user_list')
    
    try:
        user = User.objects.get(id=user_id)
        
        # Get password change history for this user
        password_changes = PasswordChangeHistory.objects.filter(
            user=user
        ).select_related('changed_by').order_by('-timestamp')[:10]
        
        context = {
            'user': user,
            'password_changes': password_changes,
            'title': f'Password History - {user.username}'
        }
        
        # If it's an HTMX request, return just the table
        if request.headers.get('HX-Request'):
            return render(request, 'userauth/partials/password_history_table.html', context)
        
        return render(request, 'userauth/password_change_history.html', context)
        
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('userauth:user_list')
