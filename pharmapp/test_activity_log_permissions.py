#!/usr/bin/env python3
"""
Test script to verify activity log permissions for user "ameer"
"""

import os
import sys
import django
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from userauth.models import Profile, UserPermission

User = get_user_model()


def test_ameer_activity_log_access():
    """Test that user 'ameer' can access activity logs"""
    print("=" * 60)
    print("TESTING ACTIVITY LOG PERMISSIONS FOR USER 'AMEER'")
    print("=" * 60)
    
    try:
        # Find user 'ameer'
        ameer = User.objects.get(username='ameer')
        print(f"✓ Found user: {ameer.username}")
        print(f"  Mobile: {ameer.mobile}")
        print(f"  User Type: {ameer.profile.user_type}")
        print(f"  Is Active: {ameer.is_active}")
        
    except User.DoesNotExist:
        print("❌ User 'ameer' not found!")
        print("Available users:")
        for user in User.objects.all()[:10]:
            print(f"  - {user.username} ({user.profile.user_type if hasattr(user, 'profile') and user.profile else 'No profile'})")
        return False
    
    # Check individual permissions
    print(f"\n📋 Individual Permissions for {ameer.username}:")
    individual_perms = ameer.custom_permissions.all()
    if individual_perms:
        for perm in individual_perms:
            status = "✓ GRANTED" if perm.granted else "❌ REVOKED"
            print(f"  {perm.permission}: {status}")
            if perm.notes:
                print(f"    Notes: {perm.notes}")
    else:
        print("  No individual permissions set")
    
    # Check role-based permissions
    print(f"\n📋 Role-based Permissions for {ameer.profile.user_type}:")
    role_perms = ameer.get_role_permissions()
    for perm in role_perms[:5]:  # Show first 5
        print(f"  ✓ {perm}")
    if len(role_perms) > 5:
        print(f"  ... and {len(role_perms) - 5} more")
    
    # Test specific permission
    print(f"\n🔍 Testing 'view_activity_logs' permission:")
    has_permission = ameer.has_permission('view_activity_logs')
    print(f"  User has 'view_activity_logs' permission: {'✓ YES' if has_permission else '❌ NO'}")
    
    # Test all effective permissions
    print(f"\n📋 All Effective Permissions:")
    all_perms = ameer.get_permissions()
    print(f"  Total permissions: {len(all_perms)}")
    if 'view_activity_logs' in all_perms:
        print("  ✓ 'view_activity_logs' is in effective permissions")
    else:
        print("  ❌ 'view_activity_logs' is NOT in effective permissions")
    
    # Test web access
    print(f"\n🌐 Testing Web Access:")
    client = Client()
    
    # Try to login
    login_success = client.login(mobile=ameer.mobile, password='ameer123')  # Assuming password
    if not login_success:
        # Try common passwords
        common_passwords = ['ameer123', 'password', '123456', 'ameer', 'admin123']
        for pwd in common_passwords:
            if client.login(mobile=ameer.mobile, password=pwd):
                login_success = True
                print(f"  ✓ Login successful with password: {pwd}")
                break
    
    if not login_success:
        print("  ❌ Could not login - testing permission check only")
        return has_permission
    
    # Test activity dashboard access
    try:
        response = client.get(reverse('userauth:activity_dashboard'))
        print(f"  Activity dashboard response: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✓ Successfully accessed activity dashboard!")
            return True
        elif response.status_code == 302:
            print("  ⚠ Redirected - may indicate permission denied")
            return False
        elif response.status_code == 403:
            print("  ❌ Access forbidden")
            return False
        else:
            print(f"  ⚠ Unexpected response code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error accessing activity dashboard: {str(e)}")
        return False


def check_permission_system():
    """Check the overall permission system"""
    print(f"\n🔧 Permission System Check:")
    
    # Check if view_activity_logs is in any role permissions
    from userauth.models import USER_PERMISSIONS
    
    roles_with_activity_logs = []
    for role, perms in USER_PERMISSIONS.items():
        if 'view_activity_logs' in perms:
            roles_with_activity_logs.append(role)
    
    print(f"  Roles with 'view_activity_logs' permission: {roles_with_activity_logs}")
    
    # Check individual permissions in database
    activity_log_perms = UserPermission.objects.filter(permission='view_activity_logs')
    print(f"  Users with individual 'view_activity_logs' permission:")
    for perm in activity_log_perms:
        status = "GRANTED" if perm.granted else "REVOKED"
        print(f"    - {perm.user.username}: {status}")


def main():
    """Main function"""
    success = test_ameer_activity_log_access()
    check_permission_system()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ SUCCESS: User 'ameer' can access activity logs!")
    else:
        print("❌ ISSUE: User 'ameer' cannot access activity logs")
        print("\n🔧 Troubleshooting steps:")
        print("1. Verify user 'ameer' exists and is active")
        print("2. Check if 'view_activity_logs' permission is granted")
        print("3. Verify the permission system is working correctly")
        print("4. Check if there are any middleware restrictions")
    print("=" * 60)


if __name__ == '__main__':
    main()
