#!/usr/bin/env python
"""
Test script for cart session cleanup functionality.
This script tests the cart session cleanup logic for both registered and walk-in customers.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from store.models import Cart, Item, WholesaleCart
from customer.models import Customer, WholesaleCustomer
from store.cart_utils import (
    clear_user_cart_session,
    is_cart_empty,
    auto_cleanup_empty_cart_session,
    cleanup_cart_session_after_receipt,
    remove_item_from_user_cart
)
from userauth.session_utils import set_user_customer_id, get_user_customer_id

User = get_user_model()

def create_test_request(user):
    """Create a test request with session middleware."""
    factory = RequestFactory()
    request = factory.get('/')
    request.user = user
    
    # Add session middleware
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    
    return request

def test_cart_session_cleanup():
    """Test cart session cleanup functionality."""
    print("=== Testing Cart Session Cleanup ===\n")
    
    # Create test user
    try:
        user = User.objects.get(username='test_cart_user')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='test_cart_user',
            email='test@example.com',
            password='testpass123'
        )
    
    # Create test item
    item, created = Item.objects.get_or_create(
        name='Test Medicine',
        defaults={
            'price': 10.00,
            'stock': 100,
            'unit': 'Tab'
        }
    )
    
    # Create test customer
    customer, created = Customer.objects.get_or_create(
        name='Test Customer',
        defaults={
            'phone': '1234567890',
            'address': 'Test Address'
        }
    )
    
    request = create_test_request(user)
    
    print("1. Testing empty cart detection...")
    # Test empty cart detection
    assert is_cart_empty(user, 'retail') == True
    print("✓ Empty cart detected correctly")
    
    print("\n2. Testing cart with items...")
    # Add item to cart
    cart_item = Cart.objects.create(
        user=user,
        item=item,
        quantity=2,
        price=item.price
    )
    assert is_cart_empty(user, 'retail') == False
    print("✓ Non-empty cart detected correctly")
    
    print("\n3. Testing session setup...")
    # Set customer in session
    set_user_customer_id(request, customer.id)
    assert get_user_customer_id(request) == customer.id
    print("✓ Customer session set correctly")
    
    print("\n4. Testing cart session cleanup...")
    # Test comprehensive cleanup
    cleanup_summary = clear_user_cart_session(request, 'retail')
    print(f"Cleanup summary: {cleanup_summary}")
    assert cleanup_summary['status'] == 'success'
    assert cleanup_summary['cart_items_cleared'] == 1
    assert cleanup_summary['customer_cleared'] == True
    print("✓ Cart session cleanup successful")
    
    print("\n5. Testing auto cleanup on empty cart...")
    # Add item back and test auto cleanup
    cart_item = Cart.objects.create(
        user=user,
        item=item,
        quantity=1,
        price=item.price
    )
    set_user_customer_id(request, customer.id)
    
    # Remove item and test auto cleanup
    result = remove_item_from_user_cart(user, cart_item.id, 'retail', request)
    print(f"Remove item result: {result}")
    assert result['success'] == True
    assert result['cleanup_performed'] == True
    print("✓ Auto cleanup on empty cart successful")
    
    print("\n6. Testing receipt cleanup...")
    # Add item and test receipt cleanup
    cart_item = Cart.objects.create(
        user=user,
        item=item,
        quantity=1,
        price=item.price
    )
    set_user_customer_id(request, customer.id)
    
    cleanup_summary = cleanup_cart_session_after_receipt(request, 'retail')
    print(f"Receipt cleanup summary: {cleanup_summary}")
    assert cleanup_summary['status'] == 'success'
    print("✓ Receipt cleanup successful")
    
    print("\n=== All Tests Passed! ===")

def test_wholesale_cart_cleanup():
    """Test wholesale cart session cleanup."""
    print("\n=== Testing Wholesale Cart Session Cleanup ===\n")

    # Use existing user to avoid database constraint issues
    try:
        user = User.objects.get(username='test_cart_user')
    except User.DoesNotExist:
        print("Skipping wholesale test - no test user available")
        return

    request = create_test_request(user)

    print("1. Testing wholesale empty cart detection...")
    assert is_cart_empty(user, 'wholesale') == True
    print("✓ Empty wholesale cart detected correctly")

    print("\n2. Testing wholesale auto cleanup...")
    cleanup_summary = auto_cleanup_empty_cart_session(request, 'wholesale')
    if cleanup_summary:
        print(f"Auto cleanup summary: {cleanup_summary}")
        assert cleanup_summary['status'] == 'success'
    else:
        print("No cleanup needed - cart already empty")
    print("✓ Wholesale auto cleanup works correctly")

    print("\n=== Wholesale Tests Passed! ===")

if __name__ == '__main__':
    try:
        test_cart_session_cleanup()
        test_wholesale_cart_cleanup()
        print("\n🎉 All cart session cleanup tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
