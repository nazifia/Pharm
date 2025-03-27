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
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt









# Create your views here.
@login_required
@user_passes_test(is_admin)
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



