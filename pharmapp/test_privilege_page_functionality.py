#!/usr/bin/env python
"""
Test script for Privilege Management Page Functionality
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.urls import reverse
from userauth.models import USER_PERMISSIONS, UserPermission

User = get_user_model()

def test_privilege_page_functionality():
    """Test the privilege management page functionality"""
    print("🧪 Testing Privilege Management Page Functionality...")
    
    try:
        # Test URL resolution
        original_url = reverse('userauth:privilege_management_view')
        enhanced_url = reverse('userauth:enhanced_privilege_management_view')
        
        print(f"✅ Original Privilege Management URL: {original_url}")
        print(f"✅ Enhanced Privilege Management URL: {enhanced_url}")
        
        # Test API endpoints
        user_permissions_api = reverse('userauth:user_permissions_api', kwargs={'user_id': 1})
        users_api = reverse('userauth:get_all_users_api')
        
        print(f"✅ User Permissions API: {user_permissions_api}")
        print(f"✅ Users API: {users_api}")
        
        # Test user data
        users = User.objects.select_related('profile').all()
        print(f"✅ Total users in database: {users.count()}")
        
        for user in users[:3]:  # Test first 3 users
            if hasattr(user, 'profile') and user.profile:
                print(f"   - {user.username}: {user.profile.full_name} ({user.profile.user_type})")
                
                # Test permissions for this user
                role_permissions = user.get_role_permissions()
                individual_permissions = user.get_individual_permissions()
                
                print(f"     Role permissions: {len(role_permissions)}")
                print(f"     Individual permissions: {len(individual_permissions)}")
                
                # Test specific user (AMIR)
                if user.username == 'ameer':
                    print(f"\n🔍 Detailed test for AMIR (ameer):")
                    print(f"   Role permissions: {role_permissions}")
                    print(f"   Individual permissions: {individual_permissions}")
                    
                    # Simulate API response
                    all_possible_permissions = set().union(*USER_PERMISSIONS.values()) if USER_PERMISSIONS else set()
                    user_permissions = {}
                    for permission in all_possible_permissions:
                        if permission in individual_permissions:
                            user_permissions[permission] = individual_permissions[permission]
                        else:
                            user_permissions[permission] = permission in role_permissions
                    
                    granted_permissions = [p for p, granted in user_permissions.items() if granted]
                    print(f"   Total granted permissions: {len(granted_permissions)}")
                    print(f"   Granted permissions: {granted_permissions}")
            else:
                print(f"   - {user.username}: No profile")
        
        # Test USER_PERMISSIONS constant
        print(f"\n✅ USER_PERMISSIONS roles: {list(USER_PERMISSIONS.keys())}")
        
        # Test Pharmacist role specifically
        pharmacist_permissions = USER_PERMISSIONS.get('Pharmacist', [])
        print(f"✅ Pharmacist role permissions ({len(pharmacist_permissions)}): {pharmacist_permissions}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_permission_categorization():
    """Test permission categorization logic"""
    print("\n🧪 Testing Permission Categorization Logic...")
    
    try:
        # Get AMIR user
        amir_user = User.objects.select_related('profile').get(username='ameer')
        
        # Role templates (same as in JavaScript)
        role_templates = {
            'Admin': ['manage_users', 'view_financial_reports', 'manage_system_settings', 'access_admin_panel', 'manage_inventory', 'dispense_medication', 'process_sales', 'view_reports', 'approve_procurement', 'manage_customers', 'manage_suppliers', 'manage_expenses', 'adjust_prices', 'process_returns', 'approve_returns', 'transfer_stock', 'view_activity_logs', 'perform_stock_check', 'edit_user_profiles', 'manage_payment_methods', 'process_split_payments', 'override_payment_status', 'pause_resume_procurement', 'search_items'],
            'Manager': ['manage_inventory', 'dispense_medication', 'process_sales', 'view_reports', 'approve_procurement', 'manage_customers', 'manage_suppliers', 'manage_expenses', 'adjust_prices', 'process_returns', 'approve_returns', 'transfer_stock', 'view_activity_logs', 'perform_stock_check', 'manage_payment_methods', 'process_split_payments', 'override_payment_status', 'pause_resume_procurement', 'search_items'],
            'Pharmacist': ['manage_inventory', 'dispense_medication', 'process_sales', 'manage_customers', 'adjust_prices', 'process_returns', 'transfer_stock', 'view_sales_history', 'view_procurement_history', 'process_split_payments', 'search_items'],
            'Pharm-Tech': ['manage_inventory', 'process_sales', 'manage_customers', 'process_returns', 'transfer_stock', 'view_sales_history', 'view_procurement_history', 'perform_stock_check', 'process_split_payments', 'search_items'],
            'Salesperson': ['process_sales', 'manage_customers', 'view_sales_history', 'process_split_payments', 'search_items']
        }
        
        # Get user permissions
        role_permissions = amir_user.get_role_permissions()
        individual_permissions = amir_user.get_individual_permissions()
        
        # Simulate API response
        all_possible_permissions = set().union(*USER_PERMISSIONS.values()) if USER_PERMISSIONS else set()
        permissions = {}
        for permission in all_possible_permissions:
            if permission in individual_permissions:
                permissions[permission] = individual_permissions[permission]
            else:
                permissions[permission] = permission in role_permissions
        
        # Categorize permissions (same logic as JavaScript)
        user_type = amir_user.profile.user_type if hasattr(amir_user, 'profile') else 'Unknown'
        role_template_permissions = role_templates.get(user_type, [])
        
        all_granted_permissions = []
        role_based_permissions = []
        individually_granted_permissions = []
        individually_revoked_permissions = []
        
        for permission, is_granted in permissions.items():
            is_role_permission = permission in role_template_permissions
            
            if is_granted:
                all_granted_permissions.append(permission)
                if is_role_permission:
                    role_based_permissions.append(permission)
                else:
                    individually_granted_permissions.append(permission)
            elif is_role_permission:
                individually_revoked_permissions.append(permission)
        
        print(f"✅ User: {amir_user.profile.full_name} ({user_type})")
        print(f"✅ All granted permissions ({len(all_granted_permissions)}): {all_granted_permissions}")
        print(f"✅ Role-based permissions ({len(role_based_permissions)}): {role_based_permissions}")
        print(f"✅ Individually granted ({len(individually_granted_permissions)}): {individually_granted_permissions}")
        print(f"✅ Individually revoked ({len(individually_revoked_permissions)}): {individually_revoked_permissions}")
        
        # Summary statistics
        total_granted = len(all_granted_permissions)
        total_revoked = len(individually_revoked_permissions)
        from_role = len(role_based_permissions)
        individual = len(individually_granted_permissions)
        
        print(f"\n📊 Summary Statistics:")
        print(f"   Total Active: {total_granted}")
        print(f"   From Role: {from_role}")
        print(f"   Individual: {individual}")
        print(f"   Revoked: {total_revoked}")
        
        return True
        
    except Exception as e:
        print(f"❌ Categorization test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Privilege Management Page Test Suite")
    print("=" * 60)
    
    # Test basic functionality
    if test_privilege_page_functionality():
        print("\n✅ Basic functionality test passed")
    else:
        print("\n❌ Basic functionality test failed")
    
    # Test permission categorization
    if test_permission_categorization():
        print("\n✅ Permission categorization test passed")
    else:
        print("\n❌ Permission categorization test failed")
    
    print("\n" + "=" * 60)
    print("🏁 Test completed")
    
    print("\n📋 Expected Results for AMIR (Pharmacist):")
    print("   - Should show 2 active permissions")
    print("   - Should show 1 role-based permission (view_sales_history)")
    print("   - Should show 1 individually granted permission (view_financial_reports)")
    print("   - Should show ~10 individually revoked permissions")

if __name__ == '__main__':
    main()
