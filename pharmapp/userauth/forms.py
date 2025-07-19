from django import forms
from . models import User, Profile
from django.contrib.auth.forms import UserCreationForm

USER_TYPE = (
    ('Admin', 'Admin'),
    ('Manager', 'Manager'),
    ('Pharmacist', 'Pharmacist'),
    ('Pharm-Tech', 'Pharm-Tech'),
    ('Salesperson', 'Salesperson'),
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