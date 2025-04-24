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

        # Sample actions
        actions = [
            "GET /store/",
            "GET /dashboard/",
            "POST /cart/add/",
            "GET /receipts/",
            "POST /item/edit/",
            "GET /customers/",
            "POST /procurement/add/",
            "GET /wholesale/",
            "POST /transfer/multiple/",
            "GET /expenses/"
        ]

        # Generate random logs
        logs_created = 0
        for _ in range(num_logs):
            # Random user
            user = random.choice(users)
            # Random action
            action = random.choice(actions)
            # Random timestamp within the last 30 days
            random_days = random.randint(0, 30)
            random_hours = random.randint(0, 23)
            random_minutes = random.randint(0, 59)
            timestamp = timezone.now() - timezone.timedelta(
                days=random_days,
                hours=random_hours,
                minutes=random_minutes
            )

            # Create the log
            ActivityLog.objects.create(
                user=user,
                action=action,
                timestamp=timestamp
            )
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
    active_users = User.objects.filter(activitylog__timestamp__gte=last_week).distinct().count()

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
                profile.save()

                messages.success(request, 'User account created successfully.')
                return redirect('userauth:register')
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



