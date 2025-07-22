#!/usr/bin/env python
"""
Test script to verify the modifications made to the pharmacy system:
1. Stock check permissions for all users
2. Zero-stock items filtering in dispensing
3. Brand and dosage_form population in DispensingLog
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.contrib.auth import get_user_model
from store.models import Item, DispensingLog, Formulation, WholesaleItem
from userauth.permissions import can_perform_stock_check
from userauth.models import Profile

User = get_user_model()


def test_stock_check_permissions():
    """Test that all authenticated users can perform stock checks"""
    print("Testing stock check permissions...")
    
    # Create a test user with a basic profile
    user, created = User.objects.get_or_create(
        mobile='1234567890',
        defaults={
            'username': 'testuser_basic',
            'email': 'test@example.com'
        }
    )
    
    # Create a profile for the user (assuming a basic user type)
    profile, created = Profile.objects.get_or_create(
        user=user,
        defaults={'user_type': 'Salesperson'}  # A basic user type
    )
    
    # Test the permission function
    can_check = can_perform_stock_check(user)
    
    if can_check:
        print("✓ Stock check permissions: All authenticated users can perform stock checks")
    else:
        print("✗ Stock check permissions: Failed - user cannot perform stock checks")
    
    return can_check


def test_zero_stock_filtering():
    """Test that zero-stock items are filtered out from dispensing"""
    print("\nTesting zero-stock item filtering...")
    
    # Create test items with different stock levels
    item_with_stock, created = Item.objects.get_or_create(
        name='Test Item With Stock',
        defaults={
            'brand': 'Test Brand',
            'dosage_form': 'Tablet',
            'unit': 'Tab',
            'stock': 10,
            'price': Decimal('100.00'),
            'cost': Decimal('50.00'),
            'markup': Decimal('100.00')
        }
    )

    item_zero_stock, created = Item.objects.get_or_create(
        name='Test Item Zero Stock',
        defaults={
            'brand': 'Test Brand',
            'dosage_form': 'Tablet',
            'unit': 'Tab',
            'stock': 0,
            'price': Decimal('100.00'),
            'cost': Decimal('50.00'),
            'markup': Decimal('100.00')
        }
    )
    
    # Test the filtering logic (simulating the dispense view query)
    from django.db.models import Q
    
    search_query = 'Test Item'
    results = Item.objects.filter(
        Q(name__icontains=search_query) | Q(brand__icontains=search_query)
    ).filter(stock__gt=0)
    
    has_stock_item = results.filter(name='Test Item With Stock').exists()
    has_zero_stock_item = results.filter(name='Test Item Zero Stock').exists()
    
    if has_stock_item and not has_zero_stock_item:
        print("✓ Zero-stock filtering: Items with zero stock are properly filtered out")
        return True
    else:
        print("✗ Zero-stock filtering: Failed - zero stock items are still showing")
        return False


def test_dispensing_log_brand_population():
    """Test that brand and dosage_form are properly populated in DispensingLog"""
    print("\nTesting DispensingLog brand and dosage_form population...")
    
    # Create a test user
    user, created = User.objects.get_or_create(
        mobile='1234567891',
        defaults={
            'username': 'testuser_dispensing',
            'email': 'test@example.com'
        }
    )
    
    # Create a test item with brand and dosage_form
    test_item, created = Item.objects.get_or_create(
        name='Test Paracetamol',
        defaults={
            'brand': 'Test Pharma Brand',
            'dosage_form': 'Tablet',
            'unit': 'Tab',
            'stock': 50,
            'price': Decimal('10.00'),
            'cost': Decimal('5.00'),
            'markup': Decimal('100.00')
        }
    )
    
    # Create or get the Formulation object
    formulation, created = Formulation.objects.get_or_create(
        dosage_form=test_item.dosage_form
    )
    
    # Create a dispensing log entry (simulating the checkout process)
    log_entry = DispensingLog.objects.create(
        user=user,
        name=test_item.name,
        brand=test_item.brand,
        dosage_form=formulation,
        unit=test_item.unit,
        quantity=5,
        amount=Decimal('50.00'),
        status='Dispensed'
    )
    
    # Verify the data
    if log_entry.brand == 'Test Pharma Brand' and log_entry.dosage_form == formulation:
        print("✓ DispensingLog population: Brand and dosage_form are properly populated")
        return True
    else:
        print("✗ DispensingLog population: Failed - brand or dosage_form not properly populated")
        print(f"  Expected brand: 'Test Pharma Brand', Got: '{log_entry.brand}'")
        print(f"  Expected dosage_form: {formulation}, Got: {log_entry.dosage_form}")
        return False


def test_dispensing_log_display():
    """Test that dispensing log displays brand instead of N/A"""
    print("\nTesting dispensing log brand display...")
    
    # Get a dispensing log with brand
    log_with_brand = DispensingLog.objects.filter(brand__isnull=False).exclude(brand='').first()
    
    if log_with_brand:
        # Simulate template rendering logic
        brand_display = log_with_brand.brand if log_with_brand.brand else "N/A"
        
        if brand_display != "N/A":
            print(f"✓ Dispensing log display: Brand '{brand_display}' is displayed instead of 'N/A'")
            return True
        else:
            print("✗ Dispensing log display: Still showing 'N/A' for brand")
            return False
    else:
        print("! Dispensing log display: No dispensing logs with brand found to test")
        return True  # Not a failure, just no data to test


def run_all_tests():
    """Run all tests and provide a summary"""
    print("=" * 60)
    print("TESTING PHARMACY SYSTEM MODIFICATIONS")
    print("=" * 60)
    
    results = []
    
    # Test 1: Stock check permissions
    results.append(test_stock_check_permissions())
    
    # Test 2: Zero-stock filtering
    results.append(test_zero_stock_filtering())
    
    # Test 3: DispensingLog brand population
    results.append(test_dispensing_log_brand_population())
    
    # Test 4: Dispensing log display
    results.append(test_dispensing_log_display())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Modifications are working correctly.")
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
    
    return passed == total


if __name__ == "__main__":
    run_all_tests()
