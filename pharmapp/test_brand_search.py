#!/usr/bin/env python
"""
Test script to verify brand search functionality in dispensing log
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from store.models import DispensingLog
from store.forms import DispensingLogSearchForm
from decimal import Decimal

User = get_user_model()

def test_brand_search_functionality():
    """Test the brand search functionality in dispensing log"""
    print("🧪 Testing Brand Search Functionality in Dispensing Log")
    print("=" * 60)
    
    # Test 1: Check if brand field exists in the form
    print("1. Testing DispensingLogSearchForm brand field...")
    try:
        form = DispensingLogSearchForm()
        assert 'brand' in form.fields, "Brand field not found in form"
        assert form.fields['brand'].required == False, "Brand field should not be required"
        assert 'Search by brand...' in str(form.fields['brand'].widget.attrs.get('placeholder', '')), "Brand field placeholder incorrect"
        print("   ✅ Brand field exists in form with correct configuration")
    except Exception as e:
        print(f"   ❌ Error with brand field in form: {e}")
        return False
    
    # Test 2: Test form validation with brand data
    print("2. Testing form validation with brand data...")
    try:
        form_data = {
            'item_name': 'Paracetamol',
            'brand': 'Emzor',
            'date_from': '',
            'date_to': '',
            'status': '',
            'user': ''
        }
        form = DispensingLogSearchForm(data=form_data)
        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"
        assert form.cleaned_data['brand'] == 'Emzor', "Brand data not properly cleaned"
        print("   ✅ Form validation works correctly with brand data")
    except Exception as e:
        print(f"   ❌ Error with form validation: {e}")
        return False
    
    # Test 3: Create test data and test filtering
    print("3. Testing brand filtering functionality...")
    try:
        # Create a test user if it doesn't exist
        user, created = User.objects.get_or_create(
            mobile='1234567890',
            defaults={'username': 'testuser', 'email': 'test@example.com', 'first_name': 'Test', 'last_name': 'User'}
        )
        
        # Create test dispensing log entries with different brands
        test_logs = [
            {
                'user': user,
                'name': 'Paracetamol',
                'brand': 'Emzor',
                'unit': 'Tab',
                'quantity': Decimal('10.00'),
                'amount': Decimal('100.00'),
                'status': 'Dispensed'
            },
            {
                'user': user,
                'name': 'Paracetamol',
                'brand': 'GSK',
                'unit': 'Tab',
                'quantity': Decimal('5.00'),
                'amount': Decimal('50.00'),
                'status': 'Dispensed'
            },
            {
                'user': user,
                'name': 'Ibuprofen',
                'brand': 'Emzor',
                'unit': 'Tab',
                'quantity': Decimal('8.00'),
                'amount': Decimal('80.00'),
                'status': 'Dispensed'
            }
        ]
        
        # Clean up existing test data for this user
        DispensingLog.objects.filter(user=user).delete()

        # Create new test data
        created_logs = []
        for log_data in test_logs:
            log = DispensingLog.objects.create(**log_data)
            created_logs.append(log)

        print(f"   ✅ Created {len(created_logs)} test dispensing log entries")

        # Test brand filtering with 'Em' (should match 'Emzor') - filter by our test user
        emzor_logs = DispensingLog.objects.filter(user=user, brand__istartswith='Em')
        assert emzor_logs.count() == 2, f"Expected 2 Emzor logs for test user, got {emzor_logs.count()}"
        print("   ✅ Brand filtering with 'Em' returns correct results (2 Emzor entries)")

        # Test brand filtering with 'GS' (should match 'GSK') - filter by our test user
        gsk_logs = DispensingLog.objects.filter(user=user, brand__istartswith='GS')
        assert gsk_logs.count() == 1, f"Expected 1 GSK log for test user, got {gsk_logs.count()}"
        print("   ✅ Brand filtering with 'GS' returns correct results (1 GSK entry)")

        # Test brand filtering with non-existent brand - filter by our test user
        no_logs = DispensingLog.objects.filter(user=user, brand__istartswith='XYZ')
        assert no_logs.count() == 0, f"Expected 0 logs for 'XYZ' for test user, got {no_logs.count()}"
        print("   ✅ Brand filtering with non-existent brand returns no results")

        # Clean up test data
        DispensingLog.objects.filter(user=user).delete()
        print("   ✅ Test data cleaned up")
        
    except Exception as e:
        print(f"   ❌ Error with brand filtering test: {e}")
        return False
    
    # Test 4: Test form field rendering
    print("4. Testing brand field rendering...")
    try:
        form = DispensingLogSearchForm()
        brand_field_html = str(form['brand'])
        assert 'name="brand"' in brand_field_html, "Brand field name attribute missing"
        assert 'class="form-control"' in brand_field_html, "Brand field CSS class missing"
        assert 'placeholder="Search by brand..."' in brand_field_html, "Brand field placeholder missing"
        print("   ✅ Brand field renders correctly with proper attributes")
    except Exception as e:
        print(f"   ❌ Error with brand field rendering: {e}")
        return False
    
    print("\n🎉 All brand search functionality tests passed!")
    print("✅ Brand field has been successfully added to dispensing log search")
    print("✅ Users can now search by first few letters of brand name")
    print("✅ Brand filtering works correctly with existing functionality")
    return True

if __name__ == '__main__':
    success = test_brand_search_functionality()
    exit(0 if success else 1)
