#!/usr/bin/env python
"""
Test script for the User Management System
This script tests the core functionality of the user management system.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from userauth.models import Profile, USER_PERMISSIONS
from userauth.forms import UserRegistrationForm, UserEditForm, UserSearchForm

User = get_user_model()

def test_user_model_enhancements():
    """Test the enhanced User model functionality"""
    print("Testing User Model Enhancements...")

    # Create a test user
    user = User.objects.create_user(
        username='testuser',
        mobile='1234567890',
        password='testpass123'
    )

    # Get or update the automatically created profile
    profile = user.profile
    profile.full_name = 'Test User'
    profile.user_type = 'Pharmacist'
    profile.department = 'Pharmacy'
    profile.employee_id = 'EMP001'
    profile.save()

    # Test permission checking
    assert user.has_permission('manage_inventory'), "Pharmacist should have inventory management permission"
    assert user.has_permission('dispense_medication'), "Pharmacist should have dispensing permission"
    assert not user.has_permission('manage_users'), "Pharmacist should not have user management permission"

    # Test permission retrieval
    permissions = user.get_permissions()
    expected_permissions = USER_PERMISSIONS.get('Pharmacist', [])
    assert set(permissions) == set(expected_permissions), "Permission mismatch for Pharmacist role"

    print("✓ User model enhancements working correctly")

def test_profile_model():
    """Test the enhanced Profile model"""
    print("Testing Profile Model...")

    user = User.objects.create_user(
        username='profiletest',
        mobile='9876543210',
        password='testpass123'
    )

    profile = user.profile
    profile.full_name = 'Profile Test User'
    profile.user_type = 'Manager'
    profile.department = 'Operations'
    profile.employee_id = 'EMP002'
    profile.save()

    # Test profile methods
    role_permissions = profile.get_role_permissions()
    assert 'view_financial_reports' in role_permissions, "Manager should have financial report access"
    assert profile.has_permission('manage_inventory'), "Manager should have inventory permission"

    print("✓ Profile model working correctly")

def test_user_forms():
    """Test the enhanced user forms"""
    print("Testing User Forms...")

    # Test UserRegistrationForm
    form_data = {
        'full_name': 'New User',
        'username': 'newuser',
        'mobile': '5555555555',
        'email': 'newuser@example.com',
        'user_type': 'Pharm-Tech',
        'department': 'Pharmacy',
        'employee_id': 'EMP003',
        'password1': 'complexpass123',
        'password2': 'complexpass123'
    }

    form = UserRegistrationForm(data=form_data)
    assert form.is_valid(), f"Registration form should be valid. Errors: {form.errors}"

    # Test UserSearchForm
    search_form = UserSearchForm(data={
        'search_query': 'test',
        'user_type': 'Pharmacist',
        'status': 'active'
    })
    assert search_form.is_valid(), "Search form should be valid"

    print("✓ User forms working correctly")

def test_permission_system():
    """Test the permission system"""
    print("Testing Permission System...")

    # Test all user types
    for user_type, expected_permissions in USER_PERMISSIONS.items():
        user = User.objects.create_user(
            username=f'test_{user_type.lower()}',
            mobile=f'111{hash(user_type) % 10000:04d}',
            password='testpass123'
        )

        profile = user.profile
        profile.full_name = f'Test {user_type}'
        profile.user_type = user_type
        profile.department = 'Test Department'
        profile.save()

        # Test that user has all expected permissions
        for permission in expected_permissions:
            assert user.has_permission(permission), f"{user_type} should have {permission} permission"

        # Test that user doesn't have permissions from other roles
        all_permissions = set()
        for perms in USER_PERMISSIONS.values():
            all_permissions.update(perms)

        unexpected_permissions = all_permissions - set(expected_permissions)
        for permission in unexpected_permissions:
            assert not user.has_permission(permission), f"{user_type} should not have {permission} permission"

    print("✓ Permission system working correctly")

def test_url_patterns():
    """Test that all URL patterns are properly configured"""
    print("Testing URL Patterns...")

    urls_to_test = [
        'userauth:user_list',
        'userauth:register',
        'userauth:privilege_management_view',
        'userauth:bulk_user_actions',
    ]

    for url_name in urls_to_test:
        try:
            url = reverse(url_name)
            print(f"✓ URL {url_name} resolves to: {url}")
        except Exception as e:
            print(f"✗ URL {url_name} failed to resolve: {e}")
            raise

    print("✓ URL patterns configured correctly")

def test_template_context():
    """Test that context processors work correctly"""
    print("Testing Template Context...")

    # Create admin user
    admin_user = User.objects.create_user(
        username='admin_test',
        mobile='9999999999',
        password='testpass123'
    )

    profile = admin_user.profile
    profile.full_name = 'Admin Test User'
    profile.user_type = 'Admin'
    profile.save()

    # Test context processor
    from userauth.context_processors import user_roles
    from django.http import HttpRequest

    request = HttpRequest()
    request.user = admin_user

    context = user_roles(request)

    assert context['is_admin'] == True, "Admin user should have is_admin = True"
    assert context['can_manage_users'] == True, "Admin should be able to manage users"
    assert context['user_role'] == 'Admin', "User role should be Admin"

    print("✓ Template context working correctly")

def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("PHARMACY USER MANAGEMENT SYSTEM TESTS")
    print("=" * 50)

    try:
        test_user_model_enhancements()
        test_profile_model()
        test_user_forms()
        test_permission_system()
        test_url_patterns()
        test_template_context()

        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED!")
        print("The User Management System is working correctly.")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

def print_system_summary():
    """Print a summary of the implemented system"""
    print("\n" + "=" * 60)
    print("USER MANAGEMENT SYSTEM IMPLEMENTATION SUMMARY")
    print("=" * 60)

    print("\n📋 FEATURES IMPLEMENTED:")
    print("• Enhanced User and Profile models with additional fields")
    print("• Comprehensive permission system with role-based access")
    print("• User management interface with CRUD operations")
    print("• Search and filtering functionality")
    print("• Bulk user operations (activate, deactivate, delete)")
    print("• Privilege management interface")
    print("• User details page with activity history")
    print("• Enhanced registration and edit forms")
    print("• Permission decorators for view protection")
    print("• Context processors for template permissions")
    print("• Navigation integration with role-based visibility")
    print("• 403 error handling with helpful information")

    print("\n👥 USER ROLES:")
    for role, permissions in USER_PERMISSIONS.items():
        print(f"• {role}: {len(permissions)} permissions")

    print("\n🔗 AVAILABLE URLS:")
    print("• /users/ - User management dashboard")
    print("• /register/ - User registration")
    print("• /users/details/<id>/ - User details")
    print("• /privilege-management/ - Privilege management")
    print("• /users/bulk-actions/ - Bulk operations")

    print("\n🛡️ SECURITY FEATURES:")
    print("• Role-based access control")
    print("• Permission validation at view level")
    print("• Template-level permission checks")
    print("• Activity logging for all user actions")
    print("• Automatic superuser privilege assignment")

    print("\n📱 UI COMPONENTS:")
    print("• Enhanced user list with search/filter")
    print("• User creation and editing forms")
    print("• Privilege management interface")
    print("• User details with permissions overview")
    print("• Bulk action controls")
    print("• Navigation integration")

if __name__ == '__main__':
    # Clean up any existing test data
    User.objects.filter(username__startswith='test').delete()
    User.objects.filter(username__contains='_test').delete()

    # Run tests
    success = run_all_tests()

    # Print summary
    print_system_summary()

    if success:
        print(f"\n🎉 User Management System successfully implemented!")
        print("You can now:")
        print("1. Navigate to /users/ to manage users")
        print("2. Create new users with specific roles")
        print("3. Manage user privileges and permissions")
        print("4. Monitor user activity through logs")
        print("5. Use role-based access control throughout the system")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
        sys.exit(1)
