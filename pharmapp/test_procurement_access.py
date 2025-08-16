#!/usr/bin/env python
"""
Test script to verify procurement access permissions are working correctly.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from userauth.middleware import RoleBasedAccessMiddleware
from userauth.permissions import (
    can_manage_retail_procurement, 
    can_manage_wholesale_procurement, 
    can_view_procurement_history
)

User = get_user_model()

def test_procurement_permissions():
    """Test procurement permissions for different users"""
    print("=" * 60)
    print("PROCUREMENT PERMISSION TEST")
    print("=" * 60)
    
    # Get test users
    try:
        admin_user = User.objects.get(username='superuser')
        pharmacist_user = User.objects.get(username='ameer')
        pharm_tech_user = User.objects.get(username='PHARM-T')
        salesperson_user = User.objects.get(username='test_cart_user')
    except User.DoesNotExist as e:
        print(f"Error: {e}")
        return
    
    users = [
        ('Admin', admin_user),
        ('Pharmacist', pharmacist_user), 
        ('Pharm-Tech', pharm_tech_user),
        ('Salesperson', salesperson_user)
    ]
    
    print("\n1. PERMISSION FUNCTION TESTS:")
    print("-" * 40)
    
    for role, user in users:
        print(f"\n{role} ({user.username}):")
        print(f"  ✓ can_manage_retail_procurement: {can_manage_retail_procurement(user)}")
        print(f"  ✓ can_manage_wholesale_procurement: {can_manage_wholesale_procurement(user)}")
        print(f"  ✓ can_view_procurement_history: {can_view_procurement_history(user)}")
    
    print("\n2. MIDDLEWARE ACCESS TEST:")
    print("-" * 40)
    
    # Test middleware access for procurement URLs
    factory = RequestFactory()
    middleware = RoleBasedAccessMiddleware(lambda request: None)
    
    test_urls = [
        ('/store/add_procurement/', 'store:add_procurement'),
        ('/store/procurement_list/', 'store:procurement_list'),
    ]
    
    for url_path, url_name in test_urls:
        print(f"\nTesting URL: {url_path}")
        
        for role, user in users:
            request = factory.get(url_path)
            request.user = user
            request.session = {}
            
            # Mock the URL resolution
            class MockResolverMatch:
                def __init__(self, url_name):
                    parts = url_name.split(':')
                    if len(parts) == 2:
                        self.namespace = parts[0]
                        self.url_name = parts[1]
                    else:
                        self.namespace = None
                        self.url_name = parts[0]
            
            request.resolver_match = MockResolverMatch(url_name)
            
            # Check if URL is in middleware restrictions
            role_required_urls = middleware.role_required_urls
            
            if url_name in role_required_urls:
                allowed_roles = role_required_urls[url_name]
                user_role = user.profile.user_type if hasattr(user, 'profile') and user.profile else 'Unknown'
                access_granted = user_role in allowed_roles
                status = "✅ ALLOWED" if access_granted else "❌ BLOCKED"
                print(f"  {role}: {status} (middleware check)")
            else:
                print(f"  {role}: ✅ ALLOWED (no middleware restriction)")

def test_individual_permissions():
    """Test individual permission assignments"""
    print("\n3. INDIVIDUAL PERMISSION ASSIGNMENTS:")
    print("-" * 40)
    
    try:
        pharmacist_user = User.objects.get(username='ameer')
        
        print(f"\nPharmacist ({pharmacist_user.username}) permissions:")
        
        # Get role-based permissions
        role_perms = pharmacist_user.get_role_permissions()
        print(f"Role-based permissions: {len(role_perms)} permissions")
        
        # Get individual permissions
        individual_perms = pharmacist_user.custom_permissions.filter(granted=True)
        print(f"Individual permissions: {individual_perms.count()} permissions")
        
        # Get effective permissions
        effective_perms = pharmacist_user.get_permissions()
        print(f"Effective permissions: {len(effective_perms)} permissions")
        
        # Check specific procurement permissions
        procurement_perms = [p for p in effective_perms if 'procurement' in p]
        print(f"\nProcurement-related permissions:")
        for perm in procurement_perms:
            print(f"  ✓ {perm}")
            
    except User.DoesNotExist:
        print("Pharmacist user 'ameer' not found")

if __name__ == '__main__':
    test_procurement_permissions()
    test_individual_permissions()
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)
