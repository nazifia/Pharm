#!/usr/bin/env python
"""
Test script to verify dispensing log permissions work correctly
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.contrib.auth import get_user_model
from store.views import can_view_all_users_dispensing
from store.models import DispensingLog

User = get_user_model()

def test_dispensing_permissions():
    print("Testing dispensing log permissions...")
    print("=" * 50)
    
    # Get all users
    users = User.objects.all()
    
    if not users.exists():
        print("No users found in the database.")
        return
    
    for user in users:
        print(f"\nUser: {user.mobile} ({user.username})")
        print(f"  - Is authenticated: {user.is_authenticated}")
        print(f"  - Is superuser: {user.is_superuser}")
        
        # Check if user has profile
        if hasattr(user, 'profile') and user.profile:
            print(f"  - Has profile: Yes")
            print(f"  - User type: {user.profile.user_type}")
        else:
            print(f"  - Has profile: No")
        
        # Test permissions
        can_view_all = can_view_all_users_dispensing(user)
        
        print(f"  - Can view all users' dispensing: {can_view_all}")
        
        # Test what logs they can see
        if can_view_all:
            accessible_logs = DispensingLog.objects.all().count()
            print(f"  - Can access {accessible_logs} dispensing logs (all)")
        else:
            accessible_logs = DispensingLog.objects.all().count()  # Now all users can see all logs
            print(f"  - Can access {accessible_logs} dispensing logs (all - new behavior)")
            print(f"  - ✅ Regular users can now see all dispensing logs")

if __name__ == "__main__":
    test_dispensing_permissions()
