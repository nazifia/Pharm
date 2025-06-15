from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class MobileBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using their mobile number.
    """
    
    def authenticate(self, request, username=None, password=None, mobile=None, **kwargs):
        # Handle both mobile and username parameters
        if mobile is None and username is not None:
            mobile = username
        
        if mobile is None or password is None:
            return None
        
        try:
            # Try to find user by mobile number
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user
            User().set_password(password)
            return None
        
        # Check if the password is correct
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None
    
    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        
        return user if self.user_can_authenticate(user) else None
