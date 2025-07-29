#!/usr/bin/env python
"""
Test script to verify dispensing log statistics permissions work correctly
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
from store.views import can_view_all_users_dispensing, can_view_full_dispensing_stats

User = get_user_model()

def test_dispensing_stats_permissions():
    print("Testing dispensing log statistics permissions...")
    print("=" * 60)
    
    # Get all users
    users = User.objects.all()
    
    if not users.exists():
        print("No users found in the database.")
        return
    
    for user in users:
        print(f"\nUser: {user.username}")
        
        # Check if user has profile
        if hasattr(user, 'profile') and user.profile:
            print(f"  - User Type: {user.profile.user_type}")
        else:
            print(f"  - User Type: No profile")
        
        print(f"  - Is Superuser: {user.is_superuser}")
        print(f"  - Is Staff: {user.is_staff}")
        
        # Test permissions
        can_view_all = can_view_all_users_dispensing(user)
        can_view_full = can_view_full_dispensing_stats(user)
        
        print(f"  - Can view all users' dispensing: {can_view_all}")
        print(f"  - Can view full statistics: {can_view_full}")
        
        # Determine what they should see
        if can_view_full:
            print(f"  - ✅ Should see: ALL detailed statistics (monthly totals)")
        else:
            print(f"  - ⚠️  Should see: DAILY total sales only")
        
        # Expected behavior based on user type
        if hasattr(user, 'profile') and user.profile:
            user_type = user.profile.user_type
            if user_type in ['Admin', 'Manager']:
                expected = "Full statistics"
            elif user_type in ['Pharmacist', 'Pharm-Tech', 'Salesperson']:
                expected = "Daily total only"
            else:
                expected = "Daily total only (default)"
        elif user.is_superuser:
            expected = "Full statistics"
        else:
            expected = "Daily total only (default)"
        
        print(f"  - Expected behavior: {expected}")

if __name__ == "__main__":
    test_dispensing_stats_permissions()
