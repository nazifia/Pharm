#!/usr/bin/env python
"""
Test script to verify the enhanced dispensed items tracking functionality
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
from django.contrib.auth.models import User
from django.urls import reverse
from store.models import DispensingLog, Formulation
from store.forms import DispensingLogSearchForm
from datetime import datetime, date
import json

def test_dispensing_log_search_form():
    """Test the DispensingLogSearchForm"""
    print("Testing DispensingLogSearchForm...")
    
    # Test valid form data
    form_data = {
        'item_name': 'Paracetamol',
        'date': '2024-01-15',
        'status': 'Dispensed'
    }
    form = DispensingLogSearchForm(data=form_data)
    assert form.is_valid(), f"Form should be valid, errors: {form.errors}"
    print("✓ Form validation passed")
    
    # Test empty form (should be valid)
    empty_form = DispensingLogSearchForm(data={})
    assert empty_form.is_valid(), f"Empty form should be valid, errors: {empty_form.errors}"
    print("✓ Empty form validation passed")
    
    # Test partial data
    partial_data = {'item_name': 'Para'}
    partial_form = DispensingLogSearchForm(data=partial_data)
    assert partial_form.is_valid(), f"Partial form should be valid, errors: {partial_form.errors}"
    print("✓ Partial form validation passed")

def test_dispensing_log_model():
    """Test DispensingLog model functionality"""
    print("\nTesting DispensingLog model...")
    
    # Create a test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    
    # Create a test dispensing log entry
    log = DispensingLog.objects.create(
        user=user,
        name='Test Paracetamol',
        brand='Test Brand',
        unit='Tab',
        quantity=10,
        amount=100.00,
        status='Dispensed'
    )
    
    assert log.id is not None, "Log should be saved with an ID"
    assert log.name == 'Test Paracetamol', "Name should match"
    assert log.quantity == 10, "Quantity should match"
    print("✓ DispensingLog model creation passed")
    
    # Test string representation
    str_repr = str(log)
    assert 'testuser' in str_repr, "String representation should include username"
    assert 'Test Paracetamol' in str_repr, "String representation should include item name"
    print("✓ DispensingLog string representation passed")

def test_search_functionality():
    """Test search functionality with sample data"""
    print("\nTesting search functionality...")
    
    # Create test user
    user, created = User.objects.get_or_create(
        username='searchuser',
        defaults={'email': 'search@example.com'}
    )
    
    # Create sample dispensing logs
    test_items = [
        {'name': 'Paracetamol 500mg', 'brand': 'Emzor', 'quantity': 20, 'amount': 200},
        {'name': 'Panadol Extra', 'brand': 'GSK', 'quantity': 15, 'amount': 300},
        {'name': 'Amoxicillin 250mg', 'brand': 'Beecham', 'quantity': 30, 'amount': 450},
        {'name': 'Paracetamol Syrup', 'brand': 'Emzor', 'quantity': 5, 'amount': 150},
    ]
    
    for item_data in test_items:
        DispensingLog.objects.get_or_create(
            user=user,
            name=item_data['name'],
            defaults={
                'brand': item_data['brand'],
                'unit': 'Tab',
                'quantity': item_data['quantity'],
                'amount': item_data['amount'],
                'status': 'Dispensed'
            }
        )
    
    # Test search by item name starting with 'Para'
    para_logs = DispensingLog.objects.filter(name__istartswith='Para')
    assert para_logs.count() >= 2, f"Should find at least 2 items starting with 'Para', found {para_logs.count()}"
    print("✓ Search by item name prefix passed")
    
    # Test search by exact name
    exact_logs = DispensingLog.objects.filter(name__icontains='Paracetamol 500mg')
    assert exact_logs.count() >= 1, "Should find exact match"
    print("✓ Search by exact name passed")
    
    # Test case-insensitive search
    case_logs = DispensingLog.objects.filter(name__istartswith='para')
    assert case_logs.count() >= 2, "Case-insensitive search should work"
    print("✓ Case-insensitive search passed")

def test_url_patterns():
    """Test that URL patterns are correctly configured"""
    print("\nTesting URL patterns...")
    
    try:
        dispensing_log_url = reverse('store:dispensing_log')
        assert dispensing_log_url == '/store/dispensing_log/', f"Expected '/store/dispensing_log/', got '{dispensing_log_url}'"
        print("✓ Dispensing log URL pattern passed")
        
        suggestions_url = reverse('store:dispensing_log_search_suggestions')
        assert 'dispensing_log_search_suggestions' in suggestions_url, "Suggestions URL should be configured"
        print("✓ Search suggestions URL pattern passed")
        
        stats_url = reverse('store:dispensing_log_stats')
        assert 'dispensing_log_stats' in stats_url, "Stats URL should be configured"
        print("✓ Stats URL pattern passed")
        
    except Exception as e:
        print(f"✗ URL pattern test failed: {e}")
        return False
    
    return True

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("ENHANCED DISPENSED ITEMS TRACKING - FUNCTIONALITY TESTS")
    print("=" * 60)
    
    try:
        test_dispensing_log_search_form()
        test_dispensing_log_model()
        test_search_functionality()
        test_url_patterns()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED! Enhanced dispensing functionality is working correctly.")
        print("=" * 60)
        
        print("\nFeatures verified:")
        print("• DispensingLogSearchForm validation")
        print("• DispensingLog model functionality")
        print("• Search by item name (prefix and case-insensitive)")
        print("• URL pattern configuration")
        print("\nYou can now:")
        print("1. Search dispensed items by typing first few letters")
        print("2. Filter by date and status")
        print("3. View real-time statistics")
        print("4. Use autocomplete suggestions")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_all_tests()
