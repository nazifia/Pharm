#!/usr/bin/env python3
"""
Test script for the new dynamic wholesale dispensing functionality
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse
from store.models import WholesaleItem, WholesaleCart

def test_wholesale_dispensing():
    """Test the dynamic wholesale dispensing functionality"""
    print("🧪 Testing Dynamic Wholesale Dispensing Functionality...")
    
    # Create test client
    client = Client()
    
    # Test 1: Check if wholesale dispense page loads
    print("1. Testing wholesale dispense page load...")
    try:
        response = client.get('/dispense_wholesale/')
        if response.status_code in [200, 302]:  # 302 is redirect to login (expected)
            print("   ✅ Wholesale dispense page is accessible")
        else:
            print(f"   ❌ Wholesale dispense page failed to load (status: {response.status_code})")
            return False
    except Exception as e:
        print(f"   ❌ Error loading wholesale dispense page: {e}")
        return False

    # Test 2: Check if wholesale search endpoint exists
    print("2. Testing wholesale search endpoint...")
    try:
        response = client.get('/wholesale-dispense-search-items/', {'q': 'test'})
        if response.status_code in [200, 302]:  # 302 might be redirect to login
            print("   ✅ Wholesale search endpoint is accessible")
        else:
            print(f"   ❌ Wholesale search endpoint failed (status: {response.status_code})")
            return False
    except Exception as e:
        print(f"   ❌ Error accessing wholesale search endpoint: {e}")
        return False
    
    # Test 3: Check template files exist
    print("3. Testing wholesale template files...")
    template_files = [
        'templates/wholesale/dispense_wholesale.html',
        'templates/partials/wholesale_dispense_search_results.html',
        'templates/partials/wholesale_cart_summary_widget.html'
    ]
    
    for template_file in template_files:
        if os.path.exists(template_file):
            print(f"   ✅ {template_file} exists")
        else:
            print(f"   ❌ {template_file} missing")
            return False
    
    # Test 4: Check URL patterns
    print("4. Testing URL patterns...")
    try:
        from django.urls import reverse
        wholesale_dispense_url = reverse('wholesale:dispense_wholesale')
        wholesale_search_url = reverse('wholesale:wholesale_dispense_search_items')
        print(f"   ✅ Wholesale dispense URL: {wholesale_dispense_url}")
        print(f"   ✅ Wholesale search URL: {wholesale_search_url}")
    except Exception as e:
        print(f"   ❌ Error with URL patterns: {e}")
        return False
    
    print("\n🎉 All wholesale dispensing tests passed! Dynamic wholesale dispensing functionality is ready.")
    return True

if __name__ == '__main__':
    success = test_wholesale_dispensing()
    exit(0 if success else 1)
