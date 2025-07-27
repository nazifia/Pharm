#!/usr/bin/env python
"""
Test script to verify expense permissions work correctly
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
from userauth.permissions import can_add_expenses, can_manage_expenses

User = get_user_model()

def test_expense_permissions():
    print("Testing expense permissions...")
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
        can_add = can_add_expenses(user)
        can_manage = can_manage_expenses(user)
        
        print(f"  - Can add expenses: {can_add}")
        print(f"  - Can manage expenses: {can_manage}")
        
        if not can_add:
            print(f"  - ❌ ERROR: User should be able to add expenses!")
        else:
            print(f"  - ✅ User can add expenses")

if __name__ == "__main__":
    test_expense_permissions()
