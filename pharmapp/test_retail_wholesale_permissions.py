#!/usr/bin/env python
"""
Test script to verify retail/wholesale permission separation works correctly
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
from userauth.permissions import (
    can_operate_retail, can_operate_wholesale, can_operate_all,
    can_manage_retail_customers, can_manage_wholesale_customers, can_manage_all_customers,
    can_manage_retail_procurement, can_manage_wholesale_procurement, can_manage_all_procurement,
    can_manage_retail_stock_checks, can_manage_wholesale_stock_checks, can_manage_all_stock_checks,
    can_manage_retail_expiry, can_manage_wholesale_expiry, can_manage_all_expiry
)

User = get_user_model()

def test_retail_wholesale_permissions():
    print("Testing Retail/Wholesale Permission Separation")
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
        
        # Check individual permissions
        has_operate_all = user.has_permission('operate_all') if hasattr(user, 'has_permission') else False
        has_operate_retail = user.has_permission('operate_retail') if hasattr(user, 'has_permission') else False
        has_operate_wholesale = user.has_permission('operate_wholesale') if hasattr(user, 'has_permission') else False
        
        print(f"  - Has 'operate_all': {has_operate_all}")
        print(f"  - Has 'operate_retail': {has_operate_retail}")
        print(f"  - Has 'operate_wholesale': {has_operate_wholesale}")
        
        # Test permission functions
        can_retail = can_operate_retail(user)
        can_wholesale = can_operate_wholesale(user)
        can_all = can_operate_all(user)

        # Test customer management permissions
        can_retail_customers = can_manage_retail_customers(user)
        can_wholesale_customers = can_manage_wholesale_customers(user)
        can_all_customers = can_manage_all_customers(user)

        # Test procurement management permissions
        can_retail_procurement = can_manage_retail_procurement(user)
        can_wholesale_procurement = can_manage_wholesale_procurement(user)
        can_all_procurement = can_manage_all_procurement(user)

        # Test stock check management permissions
        can_retail_stock = can_manage_retail_stock_checks(user)
        can_wholesale_stock = can_manage_wholesale_stock_checks(user)
        can_all_stock = can_manage_all_stock_checks(user)

        # Test expiry management permissions
        can_retail_expiry = can_manage_retail_expiry(user)
        can_wholesale_expiry = can_manage_wholesale_expiry(user)
        can_all_expiry = can_manage_all_expiry(user)

        print(f"  - Can operate retail: {can_retail}")
        print(f"  - Can operate wholesale: {can_wholesale}")
        print(f"  - Can operate all: {can_all}")
        print(f"  - Can manage retail customers: {can_retail_customers}")
        print(f"  - Can manage wholesale customers: {can_wholesale_customers}")
        print(f"  - Can manage all customers: {can_all_customers}")
        print(f"  - Can manage retail procurement: {can_retail_procurement}")
        print(f"  - Can manage wholesale procurement: {can_wholesale_procurement}")
        print(f"  - Can manage all procurement: {can_all_procurement}")
        print(f"  - Can manage retail stock checks: {can_retail_stock}")
        print(f"  - Can manage wholesale stock checks: {can_wholesale_stock}")
        print(f"  - Can manage all stock checks: {can_all_stock}")
        print(f"  - Can manage retail expiry: {can_retail_expiry}")
        print(f"  - Can manage wholesale expiry: {can_wholesale_expiry}")
        print(f"  - Can manage all expiry: {can_all_expiry}")
        
        # Validate logic
        print("  - Logic Validation:")
        
        if can_all:
            if can_retail and can_wholesale:
                print("    ✅ CORRECT: User with 'operate_all' can access both")
            else:
                print("    ❌ ERROR: User with 'operate_all' should access both")
        elif can_retail and can_wholesale:
            print("    ❌ ERROR: User should not have both retail and wholesale without 'operate_all'")
        elif can_retail and not can_wholesale:
            print("    ✅ CORRECT: Retail-only access")
        elif can_wholesale and not can_retail:
            print("    ✅ CORRECT: Wholesale-only access")
        elif not can_retail and not can_wholesale:
            print("    ⚠️  WARNING: User has no retail or wholesale access")
        
        # Expected behavior based on user type
        if hasattr(user, 'profile') and user.profile:
            user_type = user.profile.user_type
            if user_type in ['Admin', 'Manager']:
                expected = "Should have 'operate_all' permission"
            else:
                expected = "Should have either 'operate_retail' OR 'operate_wholesale' (not both)"
        elif user.is_superuser:
            expected = "Should have 'operate_all' permission"
        else:
            expected = "Should have specific permissions assigned"
        
        print(f"  - Expected: {expected}")

if __name__ == "__main__":
    test_retail_wholesale_permissions()
