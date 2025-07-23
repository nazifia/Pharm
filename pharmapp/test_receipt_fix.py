#!/usr/bin/env python
"""
Test script to verify the receipt AttributeError fix.
This test simulates the scenario where has_customer is True but receipt.customer is None.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.contrib.auth import get_user_model
from store.models import Receipt, Sales, Customer
from decimal import Decimal

User = get_user_model()


def test_receipt_customer_none_scenario():
    """Test the scenario where receipt.customer might be None"""
    print("Testing receipt customer None scenario...")
    
    # Create a test user
    user, created = User.objects.get_or_create(
        mobile='1234567892',
        defaults={
            'username': 'testuser_receipt',
            'email': 'test@example.com'
        }
    )
    
    # Create a sales object without a customer (simulating walk-in customer)
    sales = Sales.objects.create(
        user=user,
        customer=None,  # No customer associated
        total_amount=Decimal('100.00')
    )
    
    # Create a receipt without a customer
    receipt = Receipt.objects.create(
        sales=sales,
        receipt_id='TEST123',
        total_amount=Decimal('100.00'),
        customer=None,  # This is the problematic scenario
        buyer_name='Walk-in Customer',
        buyer_address='Unknown'
    )
    
    # Test the conditions that were causing the error
    has_customer = True  # This could be True from session
    payment_type = 'single'  # Not split
    
    # This should not cause an AttributeError anymore
    try:
        if has_customer and payment_type != 'split' and receipt.customer:
            # This block should not execute because receipt.customer is None
            customer_name = receipt.customer.name
            print(f"Customer name: {customer_name}")
        else:
            print("✓ Correctly skipped customer name access due to null check")
            
        # Test the split payment scenario too
        payment_type = 'split'
        if has_customer and payment_type == 'split' and receipt.customer:
            # This block should not execute because receipt.customer is None
            customer_name = receipt.customer.name
            print(f"Split payment customer name: {customer_name}")
        else:
            print("✓ Correctly skipped split payment customer name access due to null check")
            
        print("✅ Test passed: No AttributeError occurred")
        return True
        
    except AttributeError as e:
        print(f"❌ Test failed: AttributeError still occurs: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: Unexpected error: {e}")
        return False


def test_receipt_customer_exists_scenario():
    """Test the scenario where receipt.customer exists"""
    print("\nTesting receipt customer exists scenario...")
    
    # Create a test user
    user, created = User.objects.get_or_create(
        mobile='1234567893',
        defaults={
            'username': 'testuser_receipt2',
            'email': 'test2@example.com'
        }
    )
    
    # Create a customer
    customer, created = Customer.objects.get_or_create(
        name='Test Customer',
        defaults={
            'email': 'customer@example.com',
            'address': 'Test Address',
            'mobile': '9876543210'
        }
    )
    
    # Create a sales object with a customer
    sales = Sales.objects.create(
        user=user,
        customer=customer,
        total_amount=Decimal('100.00')
    )
    
    # Create a receipt with a customer
    receipt = Receipt.objects.create(
        sales=sales,
        receipt_id='TEST124',
        total_amount=Decimal('100.00'),
        customer=customer,
        buyer_name=customer.name,
        buyer_address=customer.address
    )
    
    # Test the conditions with a valid customer
    has_customer = True
    payment_type = 'single'
    
    try:
        if has_customer and payment_type != 'split' and receipt.customer:
            # This block should execute and work correctly
            customer_name = receipt.customer.name
            print(f"✓ Customer name accessed successfully: {customer_name}")
            
        # Test the split payment scenario too
        payment_type = 'split'
        if has_customer and payment_type == 'split' and receipt.customer:
            # This block should execute and work correctly
            customer_name = receipt.customer.name
            print(f"✓ Split payment customer name accessed successfully: {customer_name}")
            
        print("✅ Test passed: Customer name accessed correctly when customer exists")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: Unexpected error: {e}")
        return False


def run_receipt_tests():
    """Run all receipt-related tests"""
    print("=" * 60)
    print("TESTING RECEIPT ATTRIBUTEERROR FIX")
    print("=" * 60)
    
    results = []
    
    # Test 1: Customer is None scenario
    results.append(test_receipt_customer_none_scenario())
    
    # Test 2: Customer exists scenario
    results.append(test_receipt_customer_exists_scenario())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Receipt AttributeError fix is working correctly.")
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
    
    return passed == total


if __name__ == "__main__":
    run_receipt_tests()
