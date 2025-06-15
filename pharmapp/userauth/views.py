from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from userauth.models import *
from django.contrib.auth.decorators import user_passes_test, login_required
from .forms import *
from store.views import is_admin
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import random
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
@role_required(['Admin', 'Manager'])
def activity_dashboard(request):
    """View for the activity log dashboard"""
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
                user = form.save(commit=False)
                # Now we'll use the provided username instead of mobile
                user.username = form.cleaned_data['username']
                user.mobile = form.cleaned_data['mobile']
                user.save()

                # Create or update profile
                profile = Profile.objects.get_or_create(user=user)[0]
                profile.full_name = form.cleaned_data['full_name']
                profile.user_type = form.cleaned_data['user_type']
                profile.department = form.cleaned_data.get('department', '')
                profile.employee_id = form.cleaned_data.get('employee_id', '')
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
                messages.error(request, f'Error creating user: {str(e)}')
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

