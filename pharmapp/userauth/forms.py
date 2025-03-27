from django import forms
from . models import User
from django.contrib.auth.forms import UserCreationForm

USER_TYPE = (
    ('Admin', 'Admin'),
    ('Pharmacist', 'Pharmacist'),
    ('Pharm-Tech', 'Pharm-Tech'),
    # ('Supplier', 'Supplier'),
    # ('Customer', 'Customer')
)


class UserRegistrationForm(UserCreationForm):
    full_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}), required=True)
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}), required=True)
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}), required=False)
    mobile = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number'}), required=True)
    user_type = forms.ChoiceField(choices=USER_TYPE, widget=forms.Select(attrs={'class': 'form-control'}), required=True)
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}), required=True)
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}), required=True)
    
    class Meta:
        model = User
        fields = ('full_name', 'username', 'email', 'mobile', 'user_type', 'password1', 'password2')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username
    



class LoginForm(forms.Form):
    mobile = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number'}), required=True)
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}), required=True)
    
    class Meta:
        model = User
        fields = ('mobile', 'password1')
