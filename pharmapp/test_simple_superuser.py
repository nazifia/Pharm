#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def test_simple_superuser():
    """Simple test of superuser direct access"""
    print("=== SIMPLE SUPERUSER ACCESS TEST ===")
    
    # Get all superusers
    superusers = User.objects.filter(is_superuser=True)
    print(f"Found {superusers.count()} superusers:")
    
    for user in superusers:
        print(f"  - Username: {user.username}")
        print(f"    Direct has_permission test: {user.has_permission('any_permission')}")
        print(f"    is_superuser: {user.is_superuser}")
        print(f"    is_staff: {user.is_staff}")
        print(f"    is_active: {user.is_active}")
        
        # Check if user has profile
        if hasattr(user, 'profile') and user.profile:
            print(f"    Profile user_type: {user.profile.user_type}")
        else:
            print(f"    No profile found")
        print()

if __name__ == "__main__":
    test_simple_superuser()
