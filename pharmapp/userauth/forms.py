from django import forms
from django.contrib.auth.hashers import check_password
from . models import User, Profile, ActivityLog, PasswordChangeHistory
from django.contrib.auth.forms import UserCreationForm
from store.models import Cashier

USER_TYPE = (
    ('Admin', 'Admin'),
    ('Manager', 'Manager'),
    ('Pharmacist', 'Pharmacist'),
    ('Pharm-Tech', 'Pharm-Tech'),
    ('Salesperson', 'Salesperson'),
    ('Cashier', 'Cashier'),
    ('Wholesale Manager', 'Wholesale Manager'),
    ('Wholesale Operator', 'Wholesale Operator'),
    ('Wholesale Salesperson', 'Wholesale Salesperson'),
    # ('Supplier', 'Supplier'),
    # ('Customer', 'Customer')
)


class UserRegistrationForm(UserCreationForm):
    full_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}), required=True)
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}), required=True)
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}), required=False)
    mobile = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number'}), required=True)
    user_type = forms.ChoiceField(choices=USER_TYPE, widget=forms.Select(attrs={'class': 'form-control'}), required=True)
    department = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'}), required=False)
    employee_id = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter unique employee ID (optional)'}), required=False)
    hire_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}), required=False)
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}), required=True)
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}), required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'mobile', 'password1', 'password2')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if User.objects.filter(mobile=mobile).exists():
            raise forms.ValidationError("This mobile number is already registered.")
        return mobile

    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id')
        if employee_id:
            # Strip whitespace and check if it's not empty
            employee_id = employee_id.strip()
            if not employee_id:
                # If it's empty after stripping, return None
                return None

            # Check if this employee_id already exists
            if Profile.objects.filter(employee_id=employee_id).exists():
                raise forms.ValidationError("This employee ID is already taken. Please choose a different one.")

        return employee_id if employee_id else None




class LoginForm(forms.Form):
    mobile = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number'}), required=True)
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}), required=True)

    class Meta:
        model = User
        fields = ('mobile', 'password1')


class UserEditForm(forms.ModelForm):
    """Form for editing users"""
    full_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}), required=True)
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}), required=True)
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}), required=False)
    mobile = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number'}), required=True)
    user_type = forms.ChoiceField(choices=USER_TYPE, widget=forms.Select(attrs={'class': 'form-control'}), required=True)
    department = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'}), required=False)
    employee_id = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter unique employee ID (optional)'}), required=False)
    hire_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}), required=False)
    is_active = forms.BooleanField(widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}), required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'mobile', 'is_active')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        # Check if username exists but exclude the current instance
        if User.objects.filter(username=username).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        # Check if mobile exists but exclude the current instance
        if User.objects.filter(mobile=mobile).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("This mobile number is already registered.")
        return mobile

    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id')
        if employee_id:
            # Strip whitespace and check if it's not empty
            employee_id = employee_id.strip()
            if not employee_id:
                # If it's empty after stripping, return None
                return None

            # Check if employee_id exists but exclude the current instance's profile
            existing_profile = Profile.objects.filter(employee_id=employee_id).exclude(user=self.instance).first()
            if existing_profile:
                raise forms.ValidationError("This employee ID is already taken. Please choose a different one.")

        return employee_id if employee_id else None


class PrivilegeManagementForm(forms.Form):
    """Form for managing user privileges"""
    user = forms.ModelChoiceField(
        queryset=User.objects.select_related('profile').all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        help_text="Select a user to manage their privileges"
    )

    def __init__(self, *args, **kwargs):
        selected_user = kwargs.pop('selected_user', None)
        super().__init__(*args, **kwargs)
        # Add permission checkboxes dynamically
        from .models import USER_PERMISSIONS, UserPermission

        all_permissions = set()
        for role_permissions in USER_PERMISSIONS.values():
            all_permissions.update(role_permissions)

        # Get current user permissions if a user is selected
        current_permissions = {}
        if selected_user:
            # Get role-based permissions
            role_permissions = set(selected_user.get_role_permissions())

            # Get individual permission overrides
            individual_permissions = selected_user.get_individual_permissions()

            # Combine them - individual permissions override role permissions
            for permission in all_permissions:
                if permission in individual_permissions:
                    current_permissions[permission] = individual_permissions[permission]
                else:
                    current_permissions[permission] = permission in role_permissions

        for permission in sorted(all_permissions):
            initial_value = current_permissions.get(permission, False) if selected_user else False
            self.fields[f'permission_{permission}'] = forms.BooleanField(
                label=permission.replace('_', ' ').title(),
                required=False,
                initial=initial_value,
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
            )


class UserSearchForm(forms.Form):
    """Form for searching users"""
    search_query = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by username, full name, mobile, or employee ID...'
        }),
        required=False
    )
    user_type = forms.ChoiceField(
        choices=[('', 'All User Types')] + list(USER_TYPE),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses'), ('active', 'Active'), ('inactive', 'Inactive')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )


class ActivityLogSearchForm(forms.Form):
    """Form for searching and filtering activity logs"""
    search_query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by action or username...',
            'autocomplete': 'off'
        }),
        label='Search'
    )
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'style': 'background-color: rgb(196, 253, 253);'
        }),
        label='Date'
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'style': 'background-color: rgb(196, 253, 253);'
        }),
        label='From Date'
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'style': 'background-color: rgb(196, 253, 253);'
        }),
        label='To Date'
    )
    action_type = forms.ChoiceField(
        choices=[('', 'All Action Types')] + ActivityLog.ACTION_TYPES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Action Type'
    )
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='User',
        empty_label='All Users'
    )

    def __init__(self, *args, **kwargs):
        user_queryset = kwargs.pop('user_queryset', None)
        super().__init__(*args, **kwargs)

        if user_queryset is not None:
            self.fields['user'].queryset = user_queryset


class CashierManagementForm(forms.ModelForm):
    """Form for managing cashier assignments and types"""
    
    class Meta:
        model = Cashier
        fields = ['user', 'name', 'cashier_type', 'is_active']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter cashier name'}),
            'cashier_type': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter users to only show those without cashier profiles and those with Cashier role
        from django.db.models import Q
        
        # Get users with Cashier user_type or those who can be cashiers
        user_queryset = User.objects.filter(
            Q(profile__user_type='Cashier') | 
            Q(profile__user_type='Manager') | 
            Q(profile__user_type='Admin')
        ).exclude(
            id__in=Cashier.objects.values_list('user_id', flat=True)
        ).distinct()
        
        self.fields['user'].queryset = user_queryset
        self.fields['user'].empty_label = "Select a user for cashier assignment"
        
        # If editing existing cashier, exclude current user from queryset
        if self.instance and self.instance.pk:
            current_user = self.instance.user
            user_queryset = User.objects.filter(
                Q(profile__user_type='Cashier') | 
                Q(profile__user_type='Manager') | 
                Q(profile__user_type='Admin')
            ).exclude(
                id__in=Cashier.objects.exclude(pk=self.instance.pk).values_list('user_id', flat=True)
            ).distinct()
            self.fields['user'].queryset = user_queryset


class CashierSearchForm(forms.Form):
    """Form for searching cashiers"""
    
    search_term = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name or ID...'
        })
    )
    
    cashier_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Cashier.CASHIER_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    is_active = forms.ChoiceField(
        choices=[
            ('', 'All Status'),
            ('True', 'Active'),
            ('False', 'Inactive')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class PasswordChangeForm(forms.Form):
    """Form for changing user passwords by authorized personnel"""
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
            'autocomplete': 'new-password'
        }),
        required=True,
        min_length=8,
        help_text="Password must be at least 8 characters long"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password'
        }),
        required=True
    )
    change_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Please provide a reason for this password change',
            'rows': 3
        }),
        required=True,
        help_text="This reason will be logged for audit purposes"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_new_password(self):
        """Validate new password strength"""
        password = self.cleaned_data.get('new_password')
        
        # Check minimum length (already enforced by min_length)
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        
        # Check for complexity (at least one letter and one number)
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        if not has_letter or not has_number:
            raise forms.ValidationError("Password must contain at least one letter and one number.")
        
        # Check if password is too common (basic check)
        common_passwords = ['password', '123456', 'qwerty', 'admin', 'letmein', 'welcome']
        if password.lower() in common_passwords:
            raise forms.ValidationError("This password is too common. Please choose a more secure password.")
        
        # Check if password contains username or mobile
        if self.user and self.user.username:
            if self.user.username.lower() in password.lower():
                raise forms.ValidationError("Password cannot contain your username.")
        
        if self.user and self.user.mobile:
            if self.user.mobile in password:
                raise forms.ValidationError("Password cannot contain your mobile number.")
        
        return password
    
    def clean_confirm_password(self):
        """Validate password confirmation"""
        password = self.cleaned_data.get('new_password')
        confirm_password = self.cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        
        return confirm_password
    
    def clean(self):
        """Overall form validation"""
        cleaned_data = super().clean()
        
        # Ensure user is provided
        if not self.user:
            raise forms.ValidationError("User must be specified for password change.")
        
        # Check if new password is same as current password
        if self.user and check_password(cleaned_data.get('new_password'), self.user.password):
            raise forms.ValidationError("New password cannot be the same as the current password.")
        
        return cleaned_data