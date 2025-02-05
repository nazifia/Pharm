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
    
    form = UserRegistrationForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        full_name = form.cleaned_data['full_name']
        email = form.cleaned_data['email']
        mobile = form.cleaned_data['mobile']
        password = form.cleaned_data['password1']
        user_type = form.cleaned_data['user_type']
        
        user = authenticate(mobile=mobile, password=password, user_type=user_type)
        login(request, user)
        
        messages.success(request, 'Account successfully created.')
        profile = Profile.objects.create(user=user, full_name=full_name)
        
        if user_type == 'Admin':
            profile.user_type = 'Admin'
        elif user_type == 'Pharmacist':
            profile.user_type = 'Pharmacist'
        else:
            profile.user_type = 'Pharm-tech'
        profile.save()
        
        next_url = request.GET.get('next', 'store:index')
        return redirect(next_url)
    context ={
        'form': form,
    }
    return render(request, 'userauth/register.html', context)



@login_required
def edit_user_profile(request):
    user = request.user
    profile = user.profile  # Ensure this doesn't raise RelatedObjectDoesNotExist

    if request.method == 'POST':
        # Get form data
        full_name = request.POST.get('full_name')
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

        # Update other fields
        profile.full_name = full_name
        user.mobile = mobile

        try:
            user.save()
            profile.save()
            messages.success(request, 'Profile updated successfully.')
        except ValidationError as e:
            messages.error(request, f'Error: {e}')

        return redirect(reverse('userauth:profile'))  # Replace with actual profile page URL

    return render(request, 'userauth/profile.html', {'profile': profile})



