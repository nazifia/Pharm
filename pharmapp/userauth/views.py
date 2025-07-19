from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from userauth.models import *
from django.contrib.auth.decorators import user_passes_test, login_required
from .forms import *
from store.views import is_admin
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import random
import json
from .permissions import role_required


@login_required
@role_required(['Admin'])
def generate_test_logs(request):
    """Generate test activity logs for demonstration purposes"""
    if request.method == 'POST':
        # Get the number of logs to generate
        num_logs = int(request.POST.get('num_logs', 10))

        # Get all users
        users = User.objects.all()
        if not users.exists():
            messages.error(request, "No users found to generate logs for.")
            return redirect('userauth:activity_dashboard')

        # Sample actions with action types
        actions = [
            {"action": "GET /store/", "action_type": "VIEW", "target_model": "Store"},
            {"action": "GET /dashboard/", "action_type": "VIEW", "target_model": "Dashboard"},
            {"action": "POST /cart/add/", "action_type": "CREATE", "target_model": "Cart"},
            {"action": "GET /receipts/", "action_type": "VIEW", "target_model": "Receipt"},
            {"action": "POST /item/edit/", "action_type": "UPDATE", "target_model": "Item"},
            {"action": "GET /customers/", "action_type": "VIEW", "target_model": "Customer"},
            {"action": "POST /procurement/add/", "action_type": "CREATE", "target_model": "Procurement"},
            {"action": "GET /wholesale/", "action_type": "VIEW", "target_model": "Wholesale"},
            {"action": "POST /transfer/multiple/", "action_type": "TRANSFER", "target_model": "StoreItem"},
            {"action": "GET /expenses/", "action_type": "VIEW", "target_model": "Expense"},
            {"action": "POST /login/", "action_type": "LOGIN", "target_model": "User"},
            {"action": "POST /logout/", "action_type": "LOGOUT", "target_model": "User"},
            {"action": "POST /item/delete/", "action_type": "DELETE", "target_model": "Item"},
            {"action": "POST /payment/process/", "action_type": "PAYMENT", "target_model": "Receipt"},
            {"action": "GET /reports/export/", "action_type": "EXPORT", "target_model": "Report"}
        ]

        # Sample IP addresses
        ip_addresses = [
            "192.168.1.1",
            "192.168.1.2",
            "192.168.1.3",
            "10.0.0.1",
            "10.0.0.2",
            "172.16.0.1"
        ]

        # Sample user agents
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        ]

        # Generate random logs
        logs_created = 0
        for _ in range(num_logs):
            # Random user
            user = random.choice(users)
            # Random action
            action_data = random.choice(actions)
            # Random timestamp within the last 30 days
            random_days = random.randint(0, 30)
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            timestamp = timezone.now() - timezone.timedelta(
                days=random_days,
                hours=random_hours,
                minutes=random_minutes
            )
            # Random target ID (if applicable)
            target_id = str(random.randint(1, 100)) if random.random() > 0.3 else None
            # Random IP address
            ip_address = random.choice(ip_addresses)
            # Random user agent
            user_agent = random.choice(user_agents)

            # Create the log using the helper method
            ActivityLog.log_activity(
                user=user,
                action=action_data["action"],
                action_type=action_data["action_type"],
                target_model=action_data["target_model"],
                target_id=target_id,
                ip_address=ip_address,
                user_agent=user_agent
            )

            # Override timestamp for historical data
            log = ActivityLog.objects.latest('id')
            log.timestamp = timestamp
            log.save()

            logs_created += 1

        messages.success(request, f"Successfully generated {logs_created} test activity logs.")
        return redirect('userauth:activity_dashboard')

    return render(request, 'userauth/generate_test_logs.html')


@login_required
def activity_dashboard(request):
    """View for the activity log dashboard"""
    # Check if user has permission to view activity logs
    if not request.user.has_permission('view_activity_logs'):
        messages.error(request, 'You do not have permission to view activity logs.')
        return redirect('store:index')
    # Get statistics
    total_logs = ActivityLog.objects.count()

    # Today's logs
    today = timezone.now().date()
    today_logs = ActivityLog.objects.filter(timestamp__date=today).count()

    # Active users (users with activity in the last 7 days)
    last_week = today - timezone.timedelta(days=7)
    active_users = User.objects.filter(activities__timestamp__gte=last_week).distinct().count()

    # Recent logs (last 50)
    recent_logs = ActivityLog.objects.select_related('user').order_by('-timestamp')[:50]

    context = {
        'total_logs': total_logs,
        'today_logs': today_logs,
        'active_users': active_users,
        'recent_logs': recent_logs,
    }

    return render(request, 'userauth/activity_dashboard.html', context)


@login_required
@role_required(['Admin'])
def permissions_management(request):
    """View for the permissions management page"""
    return render(request, 'userauth/permissions_management.html')







# Create your views here.
@login_required
@role_required(['Admin'])
def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Create the user first
                user = form.save(commit=False)
                user.username = form.cleaned_data['username']
                user.mobile = form.cleaned_data['mobile']
                user.email = form.cleaned_data.get('email', '')
                user.save()

                # The profile should be created by the signal, but let's ensure it exists
                # and update it with the form data
                profile, created = Profile.objects.get_or_create(user=user)
                profile.full_name = form.cleaned_data['full_name']
                profile.user_type = form.cleaned_data['user_type']
                profile.department = form.cleaned_data.get('department', '')

                # Handle employee_id carefully - only set if it's not empty
                employee_id = form.cleaned_data.get('employee_id', '').strip() if form.cleaned_data.get('employee_id') else None
                profile.employee_id = employee_id if employee_id else None

                profile.hire_date = form.cleaned_data.get('hire_date')
                profile.save()

                # Log the activity
                ActivityLog.log_activity(
                    user=request.user,
                    action=f"Created new user: {user.username} ({profile.user_type})",
                    action_type='CREATE',
                    target_model='User',
                    target_id=str(user.id)
                )

                messages.success(request, f'User {user.username} created successfully with role {profile.user_type}.')
                return redirect('userauth:user_list')
            except Exception as e:
                # Handle specific database constraint errors
                error_message = str(e)
                if 'UNIQUE constraint failed: userauth_profile.employee_id' in error_message:
                    messages.error(request, 'This employee ID is already taken. Please choose a different employee ID or leave it blank.')
                elif 'UNIQUE constraint failed' in error_message:
                    messages.error(request, 'A user with this information already exists. Please check your input.')
                else:
                    messages.error(request, f'Error creating user: {error_message}')

                # Log the error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"User registration error: {error_message}", exc_info=True)
    else:
        form = UserRegistrationForm()

    context = {
        'form': form,
        'title': 'Register New User'
    }
    return render(request, 'userauth/register.html', context)



@login_required
def edit_user_profile(request):
    user = request.user
    profile = user.profile  # Ensure this doesn't raise RelatedObjectDoesNotExist

    if request.method == 'POST':
        # Get form data
        full_name = request.POST.get('full_name')
        username = request.POST.get('username')
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        image = request.FILES.get('image')

        # Update image if provided
        if image:
            profile.image = image

        # Update password securely
        if password:
            if check_password(password, user.password):  # Ensure old password is correct
                messages.error(request, 'The new password cannot match the old password.')
            else:
                user.set_password(password)
                user.save()
                messages.success(request, 'Password updated successfully. Please log in again.')
                return redirect('store:index')  # Redirect to login after password change

        # Check if username is already taken by another user
        if username != user.username and User.objects.filter(username=username).exists():
            messages.error(request, 'This username is already taken.')
            return redirect(reverse('userauth:profile'))

        # Update other fields
        profile.full_name = full_name
        user.username = username
        user.mobile = mobile

        try:
            user.save()
            profile.save()
            messages.success(request, 'Profile updated successfully.')
        except ValidationError as e:
            messages.error(request, f'Error: {e}')

        return redirect(reverse('userauth:profile'))

    return render(request, 'userauth/profile.html', {'profile': profile})


@login_required
@role_required(['Admin'])
def user_list(request):
    """View for listing all users with management options"""
    from .forms import UserSearchForm
    from django.db.models import Q

    users = User.objects.select_related('profile').all()
    search_form = UserSearchForm(request.GET)

    # Apply search filters
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search_query')
        user_type = search_form.cleaned_data.get('user_type')
        status = search_form.cleaned_data.get('status')

        if search_query:
            users = users.filter(
                Q(username__icontains=search_query) |
                Q(profile__full_name__icontains=search_query) |
                Q(mobile__icontains=search_query) |
                Q(profile__employee_id__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        if user_type:
            users = users.filter(profile__user_type=user_type)

        if status:
            is_active = status == 'active'
            users = users.filter(is_active=is_active)

    context = {
        'users': users,
        'search_form': search_form,
        'title': 'User Management'
    }

    return render(request, 'userauth/user_list.html', context)


@login_required
@role_required(['Admin'])
def edit_user(request, user_id):
    """View for editing a user"""
    try:
        user_to_edit = User.objects.get(id=user_id)
        profile = user_to_edit.profile
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('userauth:user_list')

    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user_to_edit)
        if form.is_valid():
            try:
                # Update user
                user = form.save(commit=False)
                user.save()

                # Update profile
                profile.full_name = form.cleaned_data['full_name']
                profile.user_type = form.cleaned_data['user_type']
                profile.department = form.cleaned_data.get('department', '')
                profile.employee_id = form.cleaned_data.get('employee_id', '')
                profile.hire_date = form.cleaned_data.get('hire_date')
                profile.save()

                # Log the activity
                ActivityLog.log_activity(
                    user=request.user,
                    action=f"Updated user: {user.username}",
                    action_type='UPDATE',
                    target_model='User',
                    target_id=str(user.id)
                )

                messages.success(request, 'User updated successfully.')

                # If it's an HTMX request, return a partial response
                if request.headers.get('HX-Request'):
                    return render(request, 'userauth/partials/user_row.html', {'user': user})

                return redirect('userauth:user_list')
            except Exception as e:
                messages.error(request, f'Error updating user: {str(e)}')
    else:
        # Pre-populate the form with user data
        initial_data = {
            'username': user_to_edit.username,
            'mobile': user_to_edit.mobile,
            'email': user_to_edit.email,
            'full_name': profile.full_name,
            'user_type': profile.user_type,
            'department': profile.department,
            'employee_id': profile.employee_id,
            'hire_date': profile.hire_date,
            'is_active': user_to_edit.is_active
        }
        form = UserEditForm(initial=initial_data)

    context = {
        'form': form,
        'user_to_edit': user_to_edit
    }

    # If it's an HTMX request, return just the form
    if request.headers.get('HX-Request'):
        return render(request, 'userauth/partials/edit_user_form.html', context)

    return render(request, 'userauth/edit_user.html', context)


@login_required
@role_required(['Admin'])
def delete_user(request, user_id):
    """View for deleting a user"""
    try:
        user_to_delete = User.objects.get(id=user_id)

        # Don't allow deleting yourself
        if user_to_delete == request.user:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('userauth:user_list')

        username = user_to_delete.username

        # Log the activity before deletion
        ActivityLog.log_activity(
            user=request.user,
            action=f"Deleted user: {username}",
            action_type='DELETE',
            target_model='User',
            target_id=str(user_id)
        )

        # Delete the user
        user_to_delete.delete()

        messages.success(request, f'User {username} deleted successfully.')
    except User.DoesNotExist:
        messages.error(request, 'User not found.')

    return redirect('userauth:user_list')


@login_required
@role_required(['Admin'])
def toggle_user_status(request, user_id):
    """View for activating/deactivating a user"""
    try:
        user_to_toggle = User.objects.get(id=user_id)

        # Don't allow deactivating yourself
        if user_to_toggle == request.user:
            messages.error(request, 'You cannot deactivate your own account.')
            return redirect('userauth:user_list')

        # Toggle the is_active status
        user_to_toggle.is_active = not user_to_toggle.is_active
        user_to_toggle.save()

        status = 'activated' if user_to_toggle.is_active else 'deactivated'

        # Log the activity
        ActivityLog.log_activity(
            user=request.user,
            action=f"User {user_to_toggle.username} {status}",
            action_type='UPDATE',
            target_model='User',
            target_id=str(user_id)
        )

        messages.success(request, f'User {user_to_toggle.username} {status} successfully.')

        # If it's an HTMX request, return just the updated row
        if request.headers.get('HX-Request'):
            return render(request, 'userauth/partials/user_row.html', {'user': user_to_toggle})

    except User.DoesNotExist:
        messages.error(request, 'User not found.')

    return redirect('userauth:user_list')


@login_required
@role_required(['Admin'])
def user_details(request, user_id):
    """View for displaying detailed user information"""
    try:
        user = User.objects.select_related('profile').get(id=user_id)

        # Get user's activity logs
        recent_activities = ActivityLog.objects.filter(user=user).order_by('-timestamp')[:10]

        context = {
            'user': user,
            'recent_activities': recent_activities,
            'permissions': user.get_permissions(),
            'title': f'User Details - {user.username}'
        }

        return render(request, 'userauth/user_details.html', context)

    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('userauth:user_list')


@login_required
@role_required(['Admin'])
def privilege_management_view(request):
    """View for managing user privileges"""
    from .forms import PrivilegeManagementForm
    from .models import USER_PERMISSIONS, UserPermission

    if request.method == 'POST':
        form = PrivilegeManagementForm(request.POST)

        # Get selected user from hidden field if form user field is empty
        selected_user_id = request.POST.get('selected_user_id')
        selected_user = None

        if form.is_valid() and form.cleaned_data.get('user'):
            selected_user = form.cleaned_data['user']
        elif selected_user_id:
            try:
                selected_user = User.objects.get(id=selected_user_id)
            except User.DoesNotExist:
                messages.error(request, 'Selected user not found.')
                return redirect('userauth:privilege_management_view')

        if selected_user:
            # Process permission assignments
            permissions_updated = []
            permissions_removed = []

            # Get all available permissions
            all_permissions = set()
            for role_permissions in USER_PERMISSIONS.values():
                all_permissions.update(role_permissions)

            # Process each permission checkbox - get from POST data directly since form might not have all fields
            for permission in all_permissions:
                field_name = f'permission_{permission}'
                is_granted = request.POST.get(field_name) == 'on'  # Checkbox value

                # Get or create the permission record
                user_permission, created = UserPermission.objects.get_or_create(
                    user=selected_user,
                    permission=permission,
                    defaults={
                        'granted': is_granted,
                        'granted_by': request.user,
                        'notes': f'Permission {"granted" if is_granted else "revoked"} by {request.user.username}'
                    }
                )

                # Update existing permission if it changed
                if not created and user_permission.granted != is_granted:
                    user_permission.granted = is_granted
                    user_permission.granted_by = request.user
                    user_permission.granted_at = timezone.now()
                    user_permission.notes = f'Permission {"granted" if is_granted else "revoked"} by {request.user.username}'
                    user_permission.save()

                    if is_granted:
                        permissions_updated.append(permission)
                    else:
                        permissions_removed.append(permission)
                elif created:
                    if is_granted:
                        permissions_updated.append(permission)
                    else:
                        permissions_removed.append(permission)

            # Create success message
            message_parts = []
            if permissions_updated:
                message_parts.append(f"Granted permissions: {', '.join(permissions_updated)}")
            if permissions_removed:
                message_parts.append(f"Revoked permissions: {', '.join(permissions_removed)}")

            if message_parts:
                messages.success(request, f'Permissions updated for {selected_user.username}. ' + '; '.join(message_parts))
            else:
                messages.info(request, f'No permission changes made for {selected_user.username}.')

            # Log the activity
            ActivityLog.log_activity(
                user=request.user,
                action=f"Updated privileges for user: {selected_user.username}",
                action_type='UPDATE',
                target_model='User',
                target_id=str(selected_user.id)
            )
        else:
            messages.error(request, 'Please select a user to manage permissions.')
    else:
        # Check if a user_id is provided in GET parameters for pre-selection
        selected_user_id = request.GET.get('user_id')
        selected_user = None
        if selected_user_id:
            try:
                selected_user = User.objects.get(id=selected_user_id)
                form = PrivilegeManagementForm(selected_user=selected_user)
            except User.DoesNotExist:
                form = PrivilegeManagementForm()
        else:
            form = PrivilegeManagementForm()

    context = {
        'form': form,
        'user_permissions': USER_PERMISSIONS,
        'title': 'Privilege Management',
        'selected_user': selected_user if 'selected_user' in locals() else None
    }

    return render(request, 'userauth/privilege_management.html', context)


@login_required
@role_required(['Admin'])
def enhanced_privilege_management_view(request):
    """Enhanced privilege management view with advanced features"""
    from .models import USER_PERMISSIONS, UserPermission

    # Get all users with their profiles
    users = User.objects.select_related('profile').all()

    # Calculate statistics
    total_users = users.count()
    total_permissions = len(set().union(*USER_PERMISSIONS.values()))
    active_roles = len([role for role, perms in USER_PERMISSIONS.items() if perms])
    custom_permissions = UserPermission.objects.count()

    context = {
        'users': users,
        'user_permissions': USER_PERMISSIONS,
        'total_users': total_users,
        'total_permissions': total_permissions,
        'active_roles': active_roles,
        'custom_permissions': custom_permissions,
        'title': 'Enhanced Privilege Management'
    }

    return render(request, 'userauth/enhanced_privilege_management.html', context)


@login_required
@role_required(['Admin'])
def user_permissions_api(request, user_id):
    """API endpoint to get user permissions"""
    try:
        user = get_object_or_404(User, id=user_id)

        # Get user's effective permissions
        user_permissions = {}
        role_permissions = user.get_role_permissions()
        individual_permissions = user.get_individual_permissions()

        # Combine role and individual permissions
        all_possible_permissions = set().union(*USER_PERMISSIONS.values()) if USER_PERMISSIONS else set()
        for permission in all_possible_permissions:
            # Check individual permission first, then role permission
            if permission in individual_permissions:
                user_permissions[permission] = individual_permissions[permission]
            else:
                user_permissions[permission] = permission in role_permissions

        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"User permissions API - User: {user.username}, Role: {user.profile.user_type if hasattr(user, 'profile') else 'None'}")
        logger.info(f"Role permissions: {role_permissions}")
        logger.info(f"Individual permissions: {individual_permissions}")
        logger.info(f"Final permissions: {user_permissions}")

        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.profile.full_name if hasattr(user, 'profile') else '',
                'user_type': user.profile.user_type if hasattr(user, 'profile') else ''
            },
            'permissions': user_permissions
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@role_required(['Admin'])
@require_http_methods(["POST"])
def save_user_permissions_api(request):
    """API endpoint to save user permissions"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        permissions = data.get('permissions', {})

        if not user_id:
            return JsonResponse({'success': False, 'error': 'User ID required'})

        user = get_object_or_404(User, id=user_id)

        # Get user's role permissions for comparison
        role_permissions = set(user.get_role_permissions())

        # Process each permission
        for permission, granted in permissions.items():
            is_role_permission = permission in role_permissions

            # Only create individual permission if it differs from role permission
            if granted != is_role_permission:
                UserPermission.objects.update_or_create(
                    user=user,
                    permission=permission,
                    defaults={
                        'granted': granted,
                        'granted_by': request.user,
                        'notes': f'Individual permission override by {request.user.username}'
                    }
                )
            else:
                # Remove individual permission if it matches role permission
                UserPermission.objects.filter(user=user, permission=permission).delete()

        # Log the activity
        ActivityLog.log_activity(
            user=request.user,
            action=f"Updated permissions for user: {user.username}",
            action_type='UPDATE',
            target_model='User',
            target_id=str(user.id)
        )

        return JsonResponse({'success': True})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@role_required(['Admin'])
@require_http_methods(["POST"])
def bulk_operations_api(request):
    """API endpoint for bulk user operations"""
    try:
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        role_template = data.get('role_template')
        status_change = data.get('status_change')

        if not user_ids:
            return JsonResponse({'success': False, 'error': 'No users selected'})

        users = User.objects.filter(id__in=user_ids)
        affected_users = 0

        for user in users:
            # Apply role template
            if role_template and role_template in USER_PERMISSIONS:
                # Clear existing individual permissions
                UserPermission.objects.filter(user=user).delete()

                # Update user role
                if hasattr(user, 'profile'):
                    user.profile.user_type = role_template
                    user.profile.save()
                    affected_users += 1

            # Apply status change
            if status_change:
                if status_change == 'activate':
                    user.is_active = True
                elif status_change == 'deactivate':
                    user.is_active = False
                user.save()
                affected_users += 1

        # Log the activity
        ActivityLog.log_activity(
            user=request.user,
            action=f"Bulk operations applied to {affected_users} users",
            action_type='BULK_UPDATE',
            target_model='User',
            target_id='bulk'
        )

        return JsonResponse({
            'success': True,
            'affected_users': affected_users
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@role_required(['Admin'])
def permission_matrix_api(request):
    """API endpoint to get permission matrix data"""
    try:
        users = User.objects.select_related('profile').filter(is_active=True)
        all_permissions = sorted(set().union(*USER_PERMISSIONS.values()))

        matrix_data = {
            'permissions': all_permissions,
            'users': []
        }

        for user in users:
            user_permissions = user.get_permissions()
            matrix_data['users'].append({
                'id': user.id,
                'name': user.profile.full_name if hasattr(user, 'profile') and user.profile.full_name else user.username,
                'role': user.profile.user_type if hasattr(user, 'profile') else 'Unknown',
                'permissions': user_permissions
            })

        return JsonResponse({
            'success': True,
            'matrix': matrix_data
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@role_required(['Admin'])
def privilege_statistics_api(request):
    """API endpoint to get privilege management statistics"""
    try:
        # Basic counts
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        inactive_users = total_users - active_users

        # Permission statistics
        all_permissions = set().union(*USER_PERMISSIONS.values()) if USER_PERMISSIONS else set()
        total_permissions = len(all_permissions)
        active_roles = len([role for role, perms in USER_PERMISSIONS.items() if perms])
        custom_permissions = UserPermission.objects.count()

        # Permission grants and revokes
        granted_permissions = UserPermission.objects.filter(granted=True).count()
        revoked_permissions = UserPermission.objects.filter(granted=False).count()

        # Recent activity
        from datetime import timedelta
        recent_date = timezone.now() - timedelta(days=7)
        recent_permission_changes = UserPermission.objects.filter(granted_at__gte=recent_date).count()

        # Role distribution
        role_distribution = {}
        for user in User.objects.select_related('profile').all():
            role = user.profile.user_type if hasattr(user, 'profile') and user.profile.user_type else 'Unknown'
            role_distribution[role] = role_distribution.get(role, 0) + 1

        return JsonResponse({
            'success': True,
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'total_permissions': total_permissions,
            'active_roles': active_roles,
            'custom_permissions': custom_permissions,
            'granted_permissions': granted_permissions,
            'revoked_permissions': revoked_permissions,
            'recent_permission_changes': recent_permission_changes,
            'role_distribution': role_distribution
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@role_required(['Admin'])
@require_http_methods(["POST"])
def revoke_user_permission_api(request):
    """API endpoint to revoke specific user permission"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        permission = data.get('permission')

        if not user_id or not permission:
            return JsonResponse({'success': False, 'error': 'User ID and permission required'})

        user = get_object_or_404(User, id=user_id)

        # Create or update permission record to revoke
        user_permission, created = UserPermission.objects.get_or_create(
            user=user,
            permission=permission,
            defaults={
                'granted': False,
                'granted_by': request.user,
                'notes': f'Permission revoked by {request.user.username}'
            }
        )

        if not created and user_permission.granted:
            user_permission.granted = False
            user_permission.granted_by = request.user
            user_permission.granted_at = timezone.now()
            user_permission.notes = f'Permission revoked by {request.user.username}'
            user_permission.save()

        # Log the activity
        ActivityLog.log_activity(
            user=request.user,
            action=f"Revoked permission '{permission}' from user: {user.username}",
            action_type='REVOKE',
            target_model='User',
            target_id=str(user.id)
        )

        return JsonResponse({
            'success': True,
            'message': f'Permission "{permission}" revoked from {user.username}'
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@role_required(['Admin'])
@require_http_methods(["POST"])
def grant_user_permission_api(request):
    """API endpoint to grant specific user permission"""
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        permission = data.get('permission')

        if not user_id or not permission:
            return JsonResponse({'success': False, 'error': 'User ID and permission required'})

        user = get_object_or_404(User, id=user_id)

        # Create or update permission record to grant
        user_permission, created = UserPermission.objects.get_or_create(
            user=user,
            permission=permission,
            defaults={
                'granted': True,
                'granted_by': request.user,
                'notes': f'Permission granted by {request.user.username}'
            }
        )

        if not created and not user_permission.granted:
            user_permission.granted = True
            user_permission.granted_by = request.user
            user_permission.granted_at = timezone.now()
            user_permission.notes = f'Permission granted by {request.user.username}'
            user_permission.save()

        # Log the activity
        ActivityLog.log_activity(
            user=request.user,
            action=f"Granted permission '{permission}' to user: {user.username}",
            action_type='GRANT',
            target_model='User',
            target_id=str(user.id)
        )

        return JsonResponse({
            'success': True,
            'message': f'Permission "{permission}" granted to {user.username}'
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@role_required(['Admin'])
def all_permissions_api(request):
    """API endpoint to get all available permissions"""
    try:
        all_permissions = {}

        # Organize permissions by category
        categories = {
            'User Management': ['manage_users', 'edit_user_profiles', 'access_admin_panel'],
            'Inventory Management': ['manage_inventory', 'perform_stock_check', 'transfer_stock', 'adjust_prices'],
            'Sales Management': ['process_sales', 'process_returns', 'process_split_payments', 'manage_customers'],
            'Reports & Analytics': ['view_reports', 'view_financial_reports', 'view_activity_logs', 'view_sales_history'],
            'System Administration': ['manage_system_settings', 'manage_payment_methods', 'override_payment_status'],
            'Procurement': ['approve_procurement', 'manage_suppliers', 'manage_expenses', 'pause_resume_procurement'],
            'Pharmacy Operations': ['dispense_medication', 'approve_returns', 'search_items']
        }

        for category, permissions in categories.items():
            all_permissions[category] = []
            for permission in permissions:
                # Get permission description
                description = permission.replace('_', ' ').title()
                all_permissions[category].append({
                    'id': permission,
                    'name': description,
                    'description': f"Allows user to {description.lower()}"
                })

        return JsonResponse({
            'success': True,
            'permissions': all_permissions
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@role_required(['Admin'])
def export_permissions_api(request):
    """API endpoint to export permissions data as CSV"""
    try:
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="permissions_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

        writer = csv.writer(response)

        # Write header
        all_permissions = sorted(set().union(*USER_PERMISSIONS.values()))
        header = ['User ID', 'Username', 'Full Name', 'Role', 'Status'] + all_permissions
        writer.writerow(header)

        # Write user data
        users = User.objects.select_related('profile').all()
        for user in users:
            user_permissions = user.get_permissions()
            row = [
                user.id,
                user.username,
                user.profile.full_name if hasattr(user, 'profile') and user.profile.full_name else '',
                user.profile.user_type if hasattr(user, 'profile') else '',
                'Active' if user.is_active else 'Inactive'
            ]

            # Add permission columns
            for permission in all_permissions:
                row.append('Yes' if permission in user_permissions else 'No')

            writer.writerow(row)

        return response

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@role_required(['Admin'])
def user_audit_trail_api(request, user_id):
    """API endpoint to get user audit trail"""
    try:
        user = get_object_or_404(User, id=user_id)

        # Get recent activity logs for this user
        recent_activities = ActivityLog.objects.filter(
            target_model='User',
            target_id=str(user.id)
        ).order_by('-timestamp')[:50]

        # Get permission changes
        permission_changes = UserPermission.objects.filter(
            user=user
        ).select_related('granted_by').order_by('-granted_at')[:20]

        activities = []
        for activity in recent_activities:
            activities.append({
                'timestamp': activity.timestamp.isoformat(),
                'action': activity.action,
                'action_type': activity.action_type,
                'performed_by': activity.user.username if activity.user else 'System'
            })

        permissions = []
        for perm in permission_changes:
            permissions.append({
                'timestamp': perm.granted_at.isoformat(),
                'permission': perm.permission,
                'granted': perm.granted,
                'granted_by': perm.granted_by.username if perm.granted_by else 'System',
                'notes': perm.notes
            })

        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.profile.full_name if hasattr(user, 'profile') else ''
            },
            'activities': activities,
            'permission_changes': permissions
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@role_required(['Admin'])
def get_user_permissions(request, user_id):
    """AJAX endpoint to get user permissions"""
    try:
        user = User.objects.get(id=user_id)

        # Get all available permissions
        all_permissions = set()
        for role_permissions in USER_PERMISSIONS.values():
            all_permissions.update(role_permissions)

        # Get role-based permissions
        role_permissions = set(user.get_role_permissions())

        # Get individual permission overrides
        individual_permissions = user.get_individual_permissions()

        # Build response data
        permissions_data = {}
        for permission in all_permissions:
            if permission in individual_permissions:
                # Individual permission overrides role permission
                permissions_data[permission] = {
                    'granted': individual_permissions[permission],
                    'source': 'individual',
                    'role_based': permission in role_permissions
                }
            else:
                # Use role-based permission
                permissions_data[permission] = {
                    'granted': permission in role_permissions,
                    'source': 'role',
                    'role_based': permission in role_permissions
                }

        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.profile.full_name,
                'user_type': user.profile.user_type
            },
            'permissions': permissions_data
        })

    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@role_required(['Admin'])
def bulk_user_actions(request):
    """View for performing bulk actions on users"""
    if request.method == 'POST':
        action = request.POST.get('action')
        user_ids = request.POST.getlist('user_ids')

        if not user_ids:
            messages.error(request, 'No users selected.')
            return redirect('userauth:user_list')

        users = User.objects.filter(id__in=user_ids).exclude(id=request.user.id)

        if action == 'activate':
            users.update(is_active=True)
            messages.success(request, f'Activated {users.count()} users.')

            # Log the activity
            ActivityLog.log_activity(
                user=request.user,
                action=f"Bulk activated {users.count()} users",
                action_type='UPDATE',
                target_model='User'
            )

        elif action == 'deactivate':
            users.update(is_active=False)
            messages.success(request, f'Deactivated {users.count()} users.')

            # Log the activity
            ActivityLog.log_activity(
                user=request.user,
                action=f"Bulk deactivated {users.count()} users",
                action_type='UPDATE',
                target_model='User'
            )

        elif action == 'delete':
            count = users.count()
            usernames = list(users.values_list('username', flat=True))
            users.delete()
            messages.success(request, f'Deleted {count} users.')

            # Log the activity
            ActivityLog.log_activity(
                user=request.user,
                action=f"Bulk deleted users: {', '.join(usernames)}",
                action_type='DELETE',
                target_model='User'
            )

    return redirect('userauth:user_list')


@login_required
@role_required(['Admin'])
def get_all_users_api(request):
    """API endpoint to get all users for bulk operations"""
    try:
        users = User.objects.select_related('profile').filter(is_active=True).exclude(id=request.user.id)
        users_data = []

        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.profile.full_name if hasattr(user, 'profile') and user.profile else user.username,
                'user_type': user.profile.user_type if hasattr(user, 'profile') and user.profile else 'Unknown'
            })

        return JsonResponse({
            'success': True,
            'users': users_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@role_required(['Admin'])
def bulk_permission_management(request):
    """API endpoint for bulk permission management"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})

    try:
        import json

        user_ids = json.loads(request.POST.get('users', '[]'))
        permission = request.POST.get('permission')
        action = request.POST.get('action')  # 'grant' or 'revoke'

        if not user_ids or not permission or not action:
            return JsonResponse({'success': False, 'error': 'Missing required parameters'})

        if action not in ['grant', 'revoke']:
            return JsonResponse({'success': False, 'error': 'Invalid action'})

        affected_users = 0
        errors = []

        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)

                # Get or create the permission record
                user_permission, created = UserPermission.objects.get_or_create(
                    user=user,
                    permission=permission,
                    defaults={
                        'granted': action == 'grant',
                        'granted_by': request.user,
                        'notes': f'Bulk {action} by {request.user.username}'
                    }
                )

                # Update existing permission if it changed
                if not created:
                    if user_permission.granted != (action == 'grant'):
                        user_permission.granted = (action == 'grant')
                        user_permission.granted_by = request.user
                        user_permission.granted_at = timezone.now()
                        user_permission.notes = f'Bulk {action} by {request.user.username}'
                        user_permission.save()
                        affected_users += 1
                elif created:
                    affected_users += 1

            except User.DoesNotExist:
                errors.append(f'User with ID {user_id} not found')
            except Exception as e:
                errors.append(f'Error processing user {user_id}: {str(e)}')

        # Log the activity
        ActivityLog.log_activity(
            user=request.user,
            action=f"Bulk {action} permission '{permission}' for {affected_users} users",
            action_type='UPDATE',
            target_model='UserPermission',
            target_id='bulk'
        )

        response_data = {
            'success': True,
            'affected_users': affected_users,
            'permission': permission,
            'action': action
        }

        if errors:
            response_data['errors'] = errors

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

