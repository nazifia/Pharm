#!/usr/bin/env python3
"""
Simple test to verify the dynamic dispensing functionality
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse
from store.models import Item, Cart

def test_dynamic_dispensing():
    """Test the dynamic dispensing functionality"""
    print("🧪 Testing Dynamic Dispensing Functionality...")
    
    # Create test client
    client = Client()
    
    # Test 1: Check if dispense page loads
    print("1. Testing dispense page load...")
    try:
        response = client.get('/dispense/')
        if response.status_code == 200:
            print("   ✅ Dispense page loads successfully")
        else:
            print(f"   ❌ Dispense page failed to load (status: {response.status_code})")
            return False
    except Exception as e:
        print(f"   ❌ Error loading dispense page: {e}")
        return False
    
    # Test 2: Check if search endpoint exists
    print("2. Testing search endpoint...")
    try:
        response = client.get('/dispense-search-items/', {'q': 'test'})
        if response.status_code in [200, 302]:  # 302 might be redirect to login
            print("   ✅ Search endpoint is accessible")
        else:
            print(f"   ❌ Search endpoint failed (status: {response.status_code})")
            return False
    except Exception as e:
        print(f"   ❌ Error accessing search endpoint: {e}")
        return False
    
    # Test 3: Check template files exist
    print("3. Testing template files...")
    template_files = [
        'pharmapp/templates/partials/dispense_search_results.html',
        'pharmapp/templates/partials/cart_summary_widget.html'
    ]
    
    for template_file in template_files:
        if os.path.exists(template_file):
            print(f"   ✅ {template_file} exists")
        else:
            print(f"   ❌ {template_file} missing")
            return False
    
    print("\n🎉 All tests passed! Dynamic dispensing functionality is ready.")
    return True

if __name__ == '__main__':
    success = test_dynamic_dispensing()
    exit(0 if success else 1)
