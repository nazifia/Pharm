from django.contrib.auth.hashers import check_password, make_password
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
from django.db import models
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
    """View for the activity log dashboard with search functionality"""
    # Check if user has permission to view activity logs
    if not request.user.has_permission('view_activity_logs'):
        messages.error(request, 'You do not have permission to view activity logs.')
        return redirect('store:index')

    from .forms import ActivityLogSearchForm
    from utils.date_utils import filter_queryset_by_date, filter_queryset_by_date_range

    # Permission check: Admins can see all users, others can only see their own data
    can_view_all_users = request.user.profile.user_type in ['Admin']

    # Get base queryset based on permissions
    if can_view_all_users:
        logs = ActivityLog.objects.select_related('user').all()
        user_queryset = User.objects.all()
    else:
        # Regular users can only see their own activity logs
        logs = ActivityLog.objects.select_related('user').filter(user=request.user)
        user_queryset = User.objects.filter(id=request.user.id)

    # Initialize search form with user queryset
    search_form = ActivityLogSearchForm(request.GET, user_queryset=user_queryset)

    # Apply filters based on search parameters
    if search_form.is_valid():
        # Filter by search query (action or username)
        search_query = search_form.cleaned_data.get('search_query')
        if search_query:
            logs = logs.filter(
                models.Q(action__icontains=search_query) |
                models.Q(user__username__icontains=search_query) |
                models.Q(user__profile__full_name__icontains=search_query)
            )

        # Filter by date - prioritize single date over date range
        date_filter = search_form.cleaned_data.get('date')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')

        if date_filter:
            # Single date filter takes priority
            logs = logs.filter(timestamp__date=date_filter)
        elif date_from or date_to:
            # Use date range if no single date is specified
            if date_from:
                logs = logs.filter(timestamp__date__gte=date_from)
            if date_to:
                logs = logs.filter(timestamp__date__lte=date_to)

        # Filter by action type
        action_type_filter = search_form.cleaned_data.get('action_type')
        if action_type_filter:
            logs = logs.filter(action_type=action_type_filter)

        # Filter by user (only for admins)
        user_filter = search_form.cleaned_data.get('user')
        if user_filter:
            if can_view_all_users:
                logs = logs.filter(user=user_filter)

    # Order by most recent first
    logs = logs.order_by('-timestamp')

    # Get statistics (based on filtered logs)
    total_logs = logs.count()

    # Calculate meaningful statistics based on search criteria
    today = timezone.now().date()

    # Check if we have date filters applied
    has_date_filter = False
    filtered_date_label = "Today's Activities"

    if search_form.is_valid():
        date_filter = search_form.cleaned_data.get('date')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')

        if date_filter:
            # Single date filter - show activities for that specific date
            today_logs = logs.filter(timestamp__date=date_filter).count()
            filtered_date_label = f"Activities on {date_filter.strftime('%Y-%m-%d')}"
            has_date_filter = True
        elif date_from or date_to:
            # Date range filter - show total activities in the range
            today_logs = logs.count()  # All logs in the filtered range
            if date_from and date_to:
                filtered_date_label = f"Activities from {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}"
            elif date_from:
                filtered_date_label = f"Activities from {date_from.strftime('%Y-%m-%d')} onwards"
            elif date_to:
                filtered_date_label = f"Activities up to {date_to.strftime('%Y-%m-%d')}"
            has_date_filter = True
        else:
            # No date filter - show today's activities from all logs
            today_logs = logs.filter(timestamp__date=today).count()
    else:
        # Form not valid or no filters - show today's activities
        today_logs = logs.filter(timestamp__date=today).count()

    # Active users calculation
    if has_date_filter:
        # If date filter is applied, count unique users in the filtered results
        active_users = logs.values('user').distinct().count()
    else:
        # No date filter - show users active in the last 7 days
        last_week = today - timezone.timedelta(days=7)
        active_users = logs.filter(timestamp__gte=last_week).values('user').distinct().count()

    # Limit to 50 most recent for display
    recent_logs = logs[:50]

    context = {
        'total_logs': total_logs,
        'today_logs': today_logs,
        'active_users': active_users,
        'recent_logs': recent_logs,
        'search_form': search_form,
        'can_view_all_users': can_view_all_users,
        'filtered_date_label': filtered_date_label,
        'has_date_filter': has_date_filter,
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
@require_http_methods(["GET"])
def user_details(request, user_id):
    """View for displaying detailed user information"""
    try:
        user = User.objects.select_related('profile').get(id=user_id)

        # Get user's activity logs - optimized with select_related for better performance
        recent_activities = ActivityLog.objects.filter(
            user=user
        ).select_related('user').order_by('-timestamp')[:10]

        # Check if user has cashier record and get cashier info
        cashier_info = None
        if user.profile.user_type == 'Cashier':
            try:
                cashier_info = user.cashier
            except:
                # Create cashier record if it doesn't exist
                from store.models import Cashier
                cashier_info = Cashier.objects.create(
                    user=user,
                    name=user.profile.full_name or user.username,
                    is_active=True
                )

        context = {
            'user': user,
            'recent_activities': recent_activities,
            'permissions': user.get_permissions(),
            'cashier_info': cashier_info,
            'title': f'User Details - {user.username}'
        }

        return render(request, 'userauth/user_details.html', context)

    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('userauth:user_list')


@login_required
@role_required(['Admin'])
def toggle_cashier_status(request, user_id):
    """Toggle cashier status for a user (activate/deactivate cashier record)"""
    try:
        user = User.objects.get(id=user_id)
        
        if user.profile.user_type != 'Cashier':
            messages.error(request, 'User must be assigned Cashier role first.')
            return redirect('userauth:user_details', user_id=user_id)
        
        from store.models import Cashier
        
        # Get or create cashier record
        cashier, created = Cashier.objects.get_or_create(
            user=user,
            defaults={
                'name': user.profile.full_name or user.username,
                'is_active': True
            }
        )
        
        # Toggle status
        cashier.is_active = not cashier.is_active
        cashier.save()
        
        status_text = 'activated' if cashier.is_active else 'deactivated'
        messages.success(request, f'Cashier account for {user.username} has been {status_text}.')
        
        # Log the activity
        ActivityLog.log_activity(
            user=request.user,
            action=f"Cashier account {status_text} for user: {user.username}",
            action_type='UPDATE',
            target_model='Cashier',
            target_id=str(cashier.id)
        )
        
        # If HTMX request, return updated status info
        if request.headers.get('HX-Request'):
            return render(request, 'userauth/partials/cashier_status.html', {
                'user': user,
                'cashier_info': cashier
            })
            
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
    
    return redirect('userauth:user_details', user_id=user_id)


@login_required
@role_required(['Admin'])
def assign_cashier_role(request, user_id):
    """Assign cashier role to a user"""
    try:
        user = User.objects.get(id=user_id)
        
        if user.profile.user_type != 'Cashier':
            # Update profile
            user.profile.user_type = 'Cashier'
            user.profile.save()
            
            # Create cashier record if it doesn't exist
            from store.models import Cashier
            cashier, created = Cashier.objects.get_or_create(
                user=user,
                defaults={
                    'name': user.profile.full_name or user.username,
                    'is_active': True
                }
            )
            
            messages.success(request, f'{user.username} has been assigned the Cashier role.')
            
            # Log the activity
            ActivityLog.log_activity(
                user=request.user,
                action=f"Assigned cashier role to user: {user.username}",
                action_type='UPDATE',
                target_model='User',
                target_id=str(user.id)
            )
            
            if created:
                ActivityLog.log_activity(
                    user=request.user,
                    action=f"Created cashier record for user: {user.username}",
                    action_type='CREATE',
                    target_model='Cashier',
                    target_id=str(cashier.id)
                )
        else:
            messages.info(request, f'{user.username} already has the Cashier role.')
        
        return redirect('userauth:user_details', user_id=user_id)
        
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


# Cashier Management Views
@login_required
@role_required(['Admin', 'Manager'])
def cashier_management_api(request):
    """API endpoint for cashier management operations"""
    if request.method == 'GET':
        # Get all cashiers with their user information
        cashiers = Cashier.objects.select_related('user').select_related('user__profile').all()
        cashier_data = []
        
        for cashier in cashiers:
            cashier_data.append({
                'id': cashier.id,
                'cashier_id': cashier.cashier_id,
                'name': cashier.name,
                'user': {
                    'id': cashier.user.id,
                    'username': cashier.user.username,
                    'full_name': cashier.user.profile.full_name if hasattr(cashier.user, 'profile') else cashier.user.username
                },
                'cashier_type': cashier.cashier_type,
                'is_active': cashier.is_active,
                'created_at': cashier.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return JsonResponse({
            'success': True,
            'cashiers': cashier_data
        })
    
    elif request.method == 'POST':
        # Create new cashier
        try:
            data = json.loads(request.body)
            user = User.objects.get(id=data['user_id'])
            
            # Check if user already has cashier profile
            if Cashier.objects.filter(user=user).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'User already has a cashier profile'
                })
            
            cashier = Cashier.objects.create(
                user=user,
                name=data['name'],
                cashier_type=data['cashier_type'],
                is_active=data.get('is_active', True)
            )

            return JsonResponse({
                'success': True,
                'cashier': {
                    'id': cashier.id,
                    'cashier_id': cashier.cashier_id,
                    'name': cashier.name,
                    'user': {
                        'id': cashier.user.id,
                        'username': cashier.user.username,
                        'full_name': cashier.user.profile.full_name if hasattr(cashier.user, 'profile') else cashier.user.username
                    },
                    'cashier_type': cashier.cashier_type,
                    'is_active': cashier.is_active,
                    'created_at': cashier.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
@role_required(['Admin', 'Manager'])
def available_users_api(request):
    """API endpoint to get users available for cashier assignment"""
    if request.method == 'GET':
        from django.db.models import Q
        
        # Get users who can be cashiers and don't have cashier profile yet
        users = User.objects.filter(
            Q(profile__user_type='Cashier') | 
            Q(profile__user_type='Manager') | 
            Q(profile__user_type='Admin')
        ).exclude(
            id__in=Cashier.objects.values_list('user_id', flat=True)
        ).select_related('profile')
        
        user_data = []
        for user in users:
            user_data.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.profile.full_name if hasattr(user, 'profile') else user.username,
                'user_type': user.profile.user_type if hasattr(user, 'profile') else 'Unknown',
                'email': user.email,
                'mobile': user.mobile
            })
        
        return JsonResponse({
            'success': True,
            'users': user_data
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
@role_required(['Admin', 'Manager'])
def update_cashier_api(request, cashier_id):
    """API endpoint to update existing cashier"""
    if request.method == 'PUT':
        try:
            cashier = Cashier.objects.get(id=cashier_id)
            data = json.loads(request.body)
            
            # Update cashier fields
            if 'name' in data:
                cashier.name = data['name']
            if 'cashier_type' in data:
                cashier.cashier_type = data['cashier_type']
            if 'is_active' in data:
                cashier.is_active = data['is_active']
            
            cashier.save()

            return JsonResponse({
                'success': True,
                'cashier': {
                    'id': cashier.id,
                    'cashier_id': cashier.cashier_id,
                    'name': cashier.name,
                    'user': {
                        'id': cashier.user.id,
                        'username': cashier.user.username,
                        'full_name': cashier.user.profile.full_name if hasattr(cashier.user, 'profile') else cashier.user.username
                    },
                    'cashier_type': cashier.cashier_type,
                    'is_active': cashier.is_active,
                    'created_at': cashier.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
            })
            
        except Cashier.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Cashier not found'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    elif request.method == 'DELETE':
        try:
            cashier = Cashier.objects.get(id=cashier_id)
            cashier.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Cashier deleted successfully'
            })
            
        except Cashier.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Cashier not found'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


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
    """API endpoint to get users available for cashier assignment"""
    if request.method == 'GET':
        from django.db.models import Q
        
        # Get users who can be cashiers and don't have cashier profile yet
        users = User.objects.filter(
            Q(profile__user_type='Cashier') | 
            Q(profile__user_type='Manager') | 
            Q(profile__user_type='Admin')
        ).exclude(
            id__in=Cashier.objects.values_list('user_id', flat=True)
        ).select_related('profile')
        
        user_data = []
        for user in users:
            user_data.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.profile.full_name if hasattr(user, 'profile') else user.username,
                'user_type': user.profile.user_type if hasattr(user, 'profile') else 'Unknown',
                'email': user.email,
                'mobile': user.mobile
            })
        
        return JsonResponse({
            'success': True,
            'users': user_data
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


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


@login_required
@role_required(['Admin', 'Manager'])
def change_user_password(request, user_id):
    """View for changing a user's password"""
    try:
        user_to_change = User.objects.get(id=user_id)
        
        # Prevent users from changing their own password through this interface
        if user_to_change == request.user:
            messages.error(request, 'You cannot change your own password through this interface. Please use the profile page.')
            return redirect('userauth:user_details', user_id=user_id)
        
        if request.method == 'POST':
            form = PasswordChangeForm(request.POST, user=user_to_change)
            if form.is_valid():
                # Store the old password hash before changing
                old_password_hash = user_to_change.password
                
                # Change the password
                new_password = form.cleaned_data['new_password']
                user_to_change.set_password(new_password)
                user_to_change.save()
                
                # Get client information for audit
                ip_address = request.META.get('REMOTE_ADDR')
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                
                # Check if user was actually updated in database
                try:
                    updated_user = User.objects.get(id=user_to_change.id)
                    # Force a refresh to ensure we have the latest data
                    updated_user.refresh_from_db()
                    print(f"DEBUG: User password check - Updated user: {updated_user.username}, password check: {updated_user.check_password('newsecurepass456')}")
                    
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
                    print(f"DEBUG: Password changed successfully for user: {user_to_change.id}")
                    print(f"DEBUG: User {user_to_change.username} password before: {old_password_hash}")
                    print(f"DEBUG: User {user_to_change.username} password after: {updated_user.check_password('newsecurepass456')}")
                    
                    # For HTMX requests, return a response that will close the modal
                    if request.headers.get('HX-Request'):
                        from django.http import HttpResponse
                        response = HttpResponse()
                        response['HX-Trigger'] = 'passwordChanged'
                        response['HX-Redirect'] = f'/users/{user_id}/'
                        return response
                    
                    return redirect('userauth:user_details', user_id=user_id)
                except Exception as e:
                    messages.error(request, f'Error updating password: {str(e)}')
                    # Fall through to form rendering
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
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('userauth:user_list')


@login_required
@role_required(['Admin', 'Manager'])
def password_change_history(request, user_id):
    """View to display password change history for a user"""
    try:
        user = User.objects.get(id=user_id)
        
        # Get password change history for this user
        password_changes = PasswordChangeHistory.objects.filter(
            user=user
        ).select_related('changed_by').order_by('-timestamp')
        
        # Ensure we have a list to avoid QuerySet issues
        password_changes = list(password_changes)
        
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

