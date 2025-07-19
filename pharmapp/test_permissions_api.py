#!/usr/bin/env python
"""
Test script for User Permissions API
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.contrib.auth import get_user_model
from userauth.models import USER_PERMISSIONS, UserPermission

User = get_user_model()

def test_permissions_api():
    """Test the user permissions API functionality"""
    print("🧪 Testing User Permissions API...")
    
    try:
        # Get a test user
        users = User.objects.select_related('profile').all()
        if not users:
            print("❌ No users found in database")
            return False
        
        test_user = users.first()
        print(f"📋 Testing with user: {test_user.username}")
        
        if hasattr(test_user, 'profile') and test_user.profile:
            print(f"👤 User profile: {test_user.profile.full_name} ({test_user.profile.user_type})")
        else:
            print("⚠️ User has no profile")
        
        # Test role permissions
        role_permissions = test_user.get_role_permissions()
        print(f"🏷️ Role permissions ({len(role_permissions)}): {role_permissions}")
        
        # Test individual permissions
        individual_permissions = test_user.get_individual_permissions()
        print(f"👤 Individual permissions ({len(individual_permissions)}): {individual_permissions}")
        
        # Test USER_PERMISSIONS constant
        print(f"📚 USER_PERMISSIONS keys: {list(USER_PERMISSIONS.keys())}")
        
        if hasattr(test_user, 'profile') and test_user.profile and test_user.profile.user_type:
            user_type = test_user.profile.user_type
            if user_type in USER_PERMISSIONS:
                expected_permissions = USER_PERMISSIONS[user_type]
                print(f"✅ Expected permissions for {user_type} ({len(expected_permissions)}): {expected_permissions}")
            else:
                print(f"❌ User type '{user_type}' not found in USER_PERMISSIONS")
        
        # Test the API logic
        all_possible_permissions = set().union(*USER_PERMISSIONS.values()) if USER_PERMISSIONS else set()
        print(f"🔍 All possible permissions ({len(all_possible_permissions)}): {sorted(all_possible_permissions)}")
        
        # Simulate API response
        user_permissions = {}
        for permission in all_possible_permissions:
            if permission in individual_permissions:
                user_permissions[permission] = individual_permissions[permission]
            else:
                user_permissions[permission] = permission in role_permissions
        
        granted_permissions = [p for p, granted in user_permissions.items() if granted]
        print(f"✅ Final granted permissions ({len(granted_permissions)}): {granted_permissions}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_specific_user(username):
    """Test permissions for a specific user"""
    try:
        user = User.objects.select_related('profile').get(username=username)
        print(f"\n🔍 Testing specific user: {username}")
        
        # Check profile
        if hasattr(user, 'profile') and user.profile:
            print(f"Profile: {user.profile.full_name} ({user.profile.user_type})")
        else:
            print("No profile found")
            return
        
        # Get permissions
        role_perms = user.get_role_permissions()
        individual_perms = user.get_individual_permissions()
        
        print(f"Role permissions: {role_perms}")
        print(f"Individual permissions: {individual_perms}")
        
        # Check if user has any permissions
        if not role_perms and not individual_perms:
            print("⚠️ User has no permissions!")
        else:
            print("✅ User has permissions")
            
    except User.DoesNotExist:
        print(f"❌ User '{username}' not found")
    except Exception as e:
        print(f"❌ Error testing user: {str(e)}")

def main():
    """Run all tests"""
    print("🚀 User Permissions API Test Suite")
    print("=" * 50)
    
    # Test general API functionality
    if test_permissions_api():
        print("\n✅ General API test passed")
    else:
        print("\n❌ General API test failed")
    
    # Test specific users
    print("\n" + "=" * 50)
    print("Testing specific users:")
    
    users = User.objects.select_related('profile').all()[:3]  # Test first 3 users
    for user in users:
        test_specific_user(user.username)
    
    print("\n" + "=" * 50)
    print("🏁 Test completed")

if __name__ == '__main__':
    main()
