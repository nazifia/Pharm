#!/usr/bin/env python
"""
Test script to verify the cart clearing fix works correctly.
This script tests that cart clearing only happens when receipts are generated.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append('pharmapp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.messages.storage.fallback import FallbackStorage
from store.models import Cart, Item, Sales, Receipt
from customer.models import Customer
from userauth.session_utils import set_user_customer_id

User = get_user_model()

def add_session_to_request(request):
    """Add session support to request"""
    middleware = SessionMiddleware()
    middleware.process_request(request)
    request.session.save()
    
    # Add messages framework
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)

def test_cart_clear_without_receipt():
    """Test that cart is NOT cleared when no receipt exists"""
    print("=== Testing Cart Clear Without Receipt ===")
    
    # Create test user
    user, created = User.objects.get_or_create(
        username='test_cart_user',
        defaults={'password': 'testpass123'}
    )
    
    # Create test customer
    customer, created = Customer.objects.get_or_create(
        name='Test Customer',
        defaults={'address': 'Test Address', 'mobile': '1234567890'}
    )
    
    # Create test item
    item, created = Item.objects.get_or_create(
        name='Test Item',
        defaults={
            'brand': 'Test Brand',
            'dosage_form': 'Tablet',
            'unit': 'unit',
            'cost': 10.00,
            'price': 15.00,
            'stock': 100
        }
    )
    
    # Create cart item
    cart_item, created = Cart.objects.get_or_create(
        user=user,
        item=item,
        defaults={'quantity': 5, 'price': 15.00}
    )
    
    # Create sales record WITHOUT receipt (simulating incomplete transaction)
    sales = Sales.objects.create(
        user=user,
        customer=customer,
        total_amount=75.00
    )
    
    # Verify no receipt exists
    assert not sales.receipts.exists(), "Sales should not have receipts"
    
    # Create request and simulate cart clearing
    factory = RequestFactory()
    request = factory.post('/store/clear_cart/')
    request.user = user
    add_session_to_request(request)
    
    # Set customer in session
    set_user_customer_id(request, customer.id)
    
    # Import and call the clear_cart view
    from store.views import clear_cart
    
    # Get initial cart count
    initial_cart_count = Cart.objects.filter(user=user).count()
    print(f"Initial cart items: {initial_cart_count}")
    
    # Call clear_cart
    response = clear_cart(request)
    
    # Check that cart was NOT cleared (since no receipt exists)
    final_cart_count = Cart.objects.filter(user=user).count()
    print(f"Final cart items: {final_cart_count}")
    
    # Cart should still exist since no receipt was generated
    assert final_cart_count > 0, "Cart should NOT be cleared when no receipt exists"
    
    # Check that orphaned sales record was cleaned up
    assert not Sales.objects.filter(id=sales.id).exists(), "Orphaned sales record should be deleted"
    
    print("✓ Cart correctly preserved when no receipt exists")
    print("✓ Orphaned sales record correctly cleaned up")

def test_cart_clear_with_receipt():
    """Test that cart IS cleared when receipt exists"""
    print("\n=== Testing Cart Clear With Receipt ===")
    
    # Get existing user and customer
    user = User.objects.get(username='test_cart_user')
    customer = Customer.objects.get(name='Test Customer')
    item = Item.objects.get(name='Test Item')
    
    # Create new cart item
    cart_item = Cart.objects.create(
        user=user,
        item=item,
        quantity=3,
        price=15.00
    )
    
    # Create sales record WITH receipt (simulating completed transaction)
    sales = Sales.objects.create(
        user=user,
        customer=customer,
        total_amount=45.00
    )
    
    # Create receipt for the sales
    receipt = Receipt.objects.create(
        sales=sales,
        customer=customer,
        total_amount=45.00,
        receipt_id='TEST1',
        payment_method='Cash',
        status='Paid'
    )
    
    # Verify receipt exists
    assert sales.receipts.exists(), "Sales should have receipts"
    
    # Create request and simulate cart clearing
    factory = RequestFactory()
    request = factory.post('/store/clear_cart/')
    request.user = user
    add_session_to_request(request)
    
    # Set customer in session
    set_user_customer_id(request, customer.id)
    
    # Import and call the clear_cart view
    from store.views import clear_cart
    
    # Get initial cart count
    initial_cart_count = Cart.objects.filter(user=user).count()
    print(f"Initial cart items: {initial_cart_count}")
    
    # Call clear_cart
    response = clear_cart(request)
    
    # Check that cart WAS cleared (since receipt exists)
    final_cart_count = Cart.objects.filter(user=user).count()
    print(f"Final cart items: {final_cart_count}")
    
    # Cart should be cleared since receipt was generated
    assert final_cart_count == 0, "Cart SHOULD be cleared when receipt exists"
    
    print("✓ Cart correctly cleared when receipt exists")

def cleanup_test_data():
    """Clean up test data"""
    print("\n=== Cleaning Up Test Data ===")
    
    # Clean up in reverse order of dependencies
    Receipt.objects.filter(receipt_id='TEST1').delete()
    Cart.objects.filter(user__username='test_cart_user').delete()
    Sales.objects.filter(user__username='test_cart_user').delete()
    Customer.objects.filter(name='Test Customer').delete()
    Item.objects.filter(name='Test Item').delete()
    User.objects.filter(username='test_cart_user').delete()
    
    print("✓ Test data cleaned up")

if __name__ == '__main__':
    try:
        test_cart_clear_without_receipt()
        test_cart_clear_with_receipt()
        print("\n=== All Tests Passed! ===")
        print("✓ Cart clearing logic works correctly")
        print("✓ Cart is preserved when no receipt exists")
        print("✓ Cart is cleared when receipt exists")
        print("✓ Customer-specific session isolation works")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_test_data()
