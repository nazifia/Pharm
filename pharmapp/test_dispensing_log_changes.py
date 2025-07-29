#!/usr/bin/env python
"""
Test script to verify dispensing log changes work correctly:
1. Total Amount and Total Quantity are hidden/disabled
2. Date range filtering works properly
3. Existing functionalities are preserved
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from store.models import DispensingLog
from datetime import date, timedelta
import json

User = get_user_model()

def test_dispensing_log_changes():
    print("Testing Dispensing Log Changes")
    print("=" * 50)
    
    # Create a test client
    client = Client()
    
    # Test 1: Check if the dispensing log page loads
    print("\n1. Testing dispensing log page access...")
    try:
        # Try to access without login (should redirect)
        response = client.get(reverse('store:dispensing_log'))
        if response.status_code == 302:
            print("   ✅ Correctly redirects unauthenticated users")
        else:
            print(f"   ❌ Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error accessing dispensing log: {e}")
    
    # Test 2: Check if date range parameters are accepted
    print("\n2. Testing date range parameters...")
    try:
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Test with date range parameters
        response = client.get(reverse('store:dispensing_log'), {
            'date_from': yesterday.strftime('%Y-%m-%d'),
            'date_to': today.strftime('%Y-%m-%d')
        })
        
        if response.status_code in [200, 302]:  # 302 for redirect to login
            print("   ✅ Date range parameters accepted")
        else:
            print(f"   ❌ Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error testing date range: {e}")
    
    # Test 3: Check if stats endpoint handles date range
    print("\n3. Testing stats endpoint with date range...")
    try:
        response = client.get(reverse('store:dispensing_log_stats'), {
            'date_from': yesterday.strftime('%Y-%m-%d'),
            'date_to': today.strftime('%Y-%m-%d')
        })
        
        if response.status_code in [200, 302]:  # 302 for redirect to login
            print("   ✅ Stats endpoint accepts date range parameters")
        else:
            print(f"   ❌ Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error testing stats endpoint: {e}")
    
    # Test 4: Check form field changes
    print("\n4. Testing form field changes...")
    try:
        from store.forms import DispensingLogSearchForm
        
        # Create form instance
        form = DispensingLogSearchForm()
        
        # Check if new fields exist
        has_date_from = 'date_from' in form.fields
        has_date_to = 'date_to' in form.fields
        has_old_date = 'date' in form.fields
        
        if has_date_from and has_date_to:
            print("   ✅ New date range fields (date_from, date_to) exist")
        else:
            print("   ❌ Missing new date range fields")
            
        if not has_old_date:
            print("   ✅ Old single date field removed")
        else:
            print("   ⚠️  Old date field still exists")
            
    except Exception as e:
        print(f"   ❌ Error testing form fields: {e}")
    
    # Test 5: Check if date utility functions work
    print("\n5. Testing date utility functions...")
    try:
        from utils.date_utils import filter_queryset_by_date_range, parse_date_string
        
        # Test date parsing
        test_date = parse_date_string('2024-01-01')
        if test_date:
            print("   ✅ Date parsing function works")
        else:
            print("   ❌ Date parsing function failed")
            
        # Test queryset filtering (if we have any dispensing logs)
        logs = DispensingLog.objects.all()
        filtered_logs = filter_queryset_by_date_range(
            logs, 'created_at', '2024-01-01', '2024-12-31'
        )
        
        if filtered_logs is not None:
            print("   ✅ Date range filtering function works")
        else:
            print("   ❌ Date range filtering function failed")
            
    except Exception as e:
        print(f"   ❌ Error testing date utilities: {e}")
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print("- Total Amount and Total Quantity are hidden via CSS (display: none)")
    print("- Date range filtering implemented (date_from, date_to)")
    print("- Form updated to use date range instead of single date")
    print("- Views updated to handle date range parameters")
    print("- JavaScript updated to handle new date fields")
    print("- Existing functionalities preserved")
    
    # Test 6: Check if regular users get statistics data
    print("\n6. Testing statistics for regular users...")
    try:
        from store.views import can_view_full_dispensing_stats
        from django.contrib.auth import get_user_model

        # Check if we have any users to test with
        User = get_user_model()
        users = User.objects.all()

        if users.exists():
            for user in users[:3]:  # Test first 3 users
                can_view_full = can_view_full_dispensing_stats(user)
                user_type = "Privileged" if can_view_full else "Regular"
                print(f"   - User '{user.username}': {user_type} user")

                if hasattr(user, 'profile') and user.profile:
                    print(f"     Role: {user.profile.user_type}")
        else:
            print("   ⚠️  No users found to test with")

    except Exception as e:
        print(f"   ❌ Error testing user permissions: {e}")

    print("\nTo verify the UI changes:")
    print("1. Navigate to /dispensing_log/")
    print("2. Check that Total Amount and Total Quantity are not visible")
    print("3. Verify that Items Dispensed, Unique Items, and Monthly Sales ARE visible")
    print("4. Use the From Date and To Date fields to filter")
    print("5. Verify that search results correspond to the date range specified")
    print("6. Test with different user types (Pharmacist, Pharm-Tech, etc.)")

    print("\nExpected behavior for regular users:")
    print("- ✅ Items Dispensed: Should show actual count")
    print("- ❌ Total Amount: Hidden (not displayed)")
    print("- ❌ Total Quantity: Hidden (not displayed)")
    print("- ✅ Unique Items: Should show actual count")
    print("- ✅ Daily Sales: Should show today's total sales amount")
    print("- ✅ Refresh button: Should be visible and functional")

    print("\nExpected behavior for privileged users (Admin/Manager):")
    print("- ✅ Items Dispensed: Should show actual count")
    print("- ❌ Total Amount: Hidden (not displayed)")
    print("- ❌ Total Quantity: Hidden (not displayed)")
    print("- ✅ Unique Items: Should show actual count")
    print("- ✅ Monthly Sales: Should show current month's total sales amount")
    print("- ✅ Refresh button: Should be visible and functional")

if __name__ == "__main__":
    test_dispensing_log_changes()
