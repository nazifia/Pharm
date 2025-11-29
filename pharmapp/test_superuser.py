#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def test_superuser_access():
    """Test superuser access permissions"""
    print("=== SUPERUSER ACCESS TEST ===")
    
    # Get all superusers
    superusers = User.objects.filter(is_superuser=True)
    print(f"Found {superusers.count()} superusers:")
    
    for user in superusers:
        print(f"  - Username: {user.username}")
        print(f"    is_superuser: {user.is_superuser}")
        print(f"    is_staff: {user.is_staff}")
        print(f"    is_active: {user.is_active}")
        
        # Check if user has profile
        if hasattr(user, 'profile') and user.profile:
            print(f"    Profile user_type: {user.profile.user_type}")
        else:
            print(f"    No profile found")
            
        # Test permission functions
        try:
            from userauth.permissions import (
                is_admin, is_manager, is_pharmacist, 
                can_view_financial_reports,
                can_process_payments, can_access_payment_requests
            )
            
            print(f"    is_admin: {is_admin(user)}")
            print(f"    is_manager: {is_manager(user)}")
            print(f"    is_pharmacist: {is_pharmacist(user)}")
            print(f"    can_view_financial_reports: {can_view_financial_reports(user)}")
            print(f"    can_process_payments: {can_process_payments(user)}")
            print(f"    can_access_payment_requests: {can_access_payment_requests(user)}")
            
        except Exception as e:
            print(f"    Error testing permissions: {e}")
            
        # Test template filters
        try:
            from userauth.templatetags.permission_tags import (
                has_permission, can_process_payments as can_process_payments_tag,
                can_access_payment_requests as can_access_payment_requests_tag
            )
            
            print(f"    Template - has_permission view_reports: {has_permission(user, 'view_reports')}")
            print(f"    Template - can_process_payments_tag: {can_process_payments_tag(user)}")
            print(f"    Template - can_access_payment_requests_tag: {can_access_payment_requests_tag(user)}")
            
        except Exception as e:
            print(f"    Error testing template tags: {e}")
            
        print()

if __name__ == "__main__":
    test_superuser_access()
