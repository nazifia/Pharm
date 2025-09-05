#!/usr/bin/env python
"""
Test script to verify that ItemSelectionHistory entries are only created when receipts are generated,
not when items are just selected and then cart is cleared.

This test demonstrates the fix for the issue where items appeared in customer transaction history
even when no receipt was generated.
"""

import os
import sys
import django
from decimal import Decimal

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.messages.storage.fallback import FallbackStorage

from customer.models import Customer
from store.models import Item, Cart, ItemSelectionHistory
from store.views import select_items, clear_cart, receipt
from userauth.models import User

def setup_test_data():
    """Create test user, customer, and item"""
    print("Setting up test data...")
    
    # Create test user
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Create test customer
    customer, created = Customer.objects.get_or_create(
        name='Test Customer',
        defaults={
            'phone': '1234567890',
            'address': 'Test Address'
        }
    )
    
    # Create test item
    item, created = Item.objects.get_or_create(
        name='Test Medicine',
        defaults={
            'brand': 'Test Brand',
            'price': Decimal('100.00'),
            'cost': Decimal('50.00'),
            'stock': 100,
            'unit': 'Tab'
        }
    )
    
    return user, customer, item

def create_mock_request(user, method='POST', data=None):
    """Create a mock request with session and messages"""
    factory = RequestFactory()
    
    if method == 'POST':
        request = factory.post('/', data or {})
    else:
        request = factory.get('/')
    
    request.user = user
    
    # Add session
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    
    # Add messages
    setattr(request, '_messages', FallbackStorage(request))
    
    return request

def test_transaction_history_fix():
    """Test that ItemSelectionHistory is only created when receipts are generated"""
    print("\n" + "="*60)
    print("TESTING TRANSACTION HISTORY FIX")
    print("="*60)
    
    user, customer, item = setup_test_data()
    
    # Clear any existing data
    ItemSelectionHistory.objects.filter(customer=customer).delete()
    Cart.objects.filter(user=user).delete()
    
    print(f"\nInitial ItemSelectionHistory count: {ItemSelectionHistory.objects.filter(customer=customer).count()}")
    
    # Test 1: Select items (add to cart) but don't generate receipt
    print("\n1. Testing item selection without receipt generation...")
    
    request_data = {
        'action': 'purchase',
        'item_ids': [str(item.id)],
        'quantities': ['2'],
        'units': ['Tab'],
        'payment_method': 'Cash',
        'status': 'Paid'
    }
    
    request = create_mock_request(user, 'POST', request_data)
    
    try:
        response = select_items(request, customer.id)
        print(f"   - Items selected successfully")
        print(f"   - Cart items count: {Cart.objects.filter(user=user).count()}")
        print(f"   - ItemSelectionHistory count after selection: {ItemSelectionHistory.objects.filter(customer=customer).count()}")
        
        # This should be 0 after the fix (previously would have been 1)
        history_count_after_selection = ItemSelectionHistory.objects.filter(customer=customer).count()
        
    except Exception as e:
        print(f"   - Error during item selection: {e}")
        return False
    
    # Test 2: Clear cart without generating receipt
    print("\n2. Testing cart clearing without receipt...")
    
    request = create_mock_request(user, 'POST', {'action': 'clear'})
    
    try:
        response = clear_cart(request)
        print(f"   - Cart cleared successfully")
        print(f"   - Cart items count after clear: {Cart.objects.filter(user=user).count()}")
        print(f"   - ItemSelectionHistory count after cart clear: {ItemSelectionHistory.objects.filter(customer=customer).count()}")
        
        # This should still be 0 after the fix
        history_count_after_clear = ItemSelectionHistory.objects.filter(customer=customer).count()
        
    except Exception as e:
        print(f"   - Error during cart clearing: {e}")
        return False
    
    # Test 3: Select items again and generate receipt
    print("\n3. Testing item selection WITH receipt generation...")
    
    # Add items to cart again
    request = create_mock_request(user, 'POST', request_data)
    
    try:
        response = select_items(request, customer.id)
        print(f"   - Items selected again")
        print(f"   - Cart items count: {Cart.objects.filter(user=user).count()}")
        
        # Now generate receipt
        receipt_data = {
            'buyer_name': customer.name,
            'buyer_address': customer.address,
            'payment_method': 'Cash',
            'status': 'Paid'
        }

        request = create_mock_request(user, 'POST', receipt_data)
        # Set customer in session for receipt function
        from userauth.session_utils import set_user_customer_id
        set_user_customer_id(request, customer.id)
        response = receipt(request)
        
        print(f"   - Receipt generated successfully")
        print(f"   - Cart items count after receipt: {Cart.objects.filter(user=user).count()}")
        print(f"   - ItemSelectionHistory count after receipt: {ItemSelectionHistory.objects.filter(customer=customer).count()}")
        
        # This should be 1 after the fix (only created when receipt is generated)
        history_count_after_receipt = ItemSelectionHistory.objects.filter(customer=customer).count()
        
    except Exception as e:
        print(f"   - Error during receipt generation: {e}")
        return False
    
    # Verify the fix
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    
    success = True
    
    if history_count_after_selection == 0:
        print("✅ PASS: No ItemSelectionHistory created when items are just selected")
    else:
        print("❌ FAIL: ItemSelectionHistory was created when items were selected (should be 0)")
        success = False
    
    if history_count_after_clear == 0:
        print("✅ PASS: No ItemSelectionHistory remains after cart is cleared")
    else:
        print("❌ FAIL: ItemSelectionHistory exists after cart clear (should be 0)")
        success = False
    
    if history_count_after_receipt == 1:
        print("✅ PASS: ItemSelectionHistory created only when receipt is generated")
    else:
        print("❌ FAIL: ItemSelectionHistory not created when receipt is generated (should be 1)")
        success = False
    
    if success:
        print("\n🎉 ALL TESTS PASSED! The transaction history fix is working correctly.")
        print("   - Items only appear in customer history when receipts are actually generated")
        print("   - Cleared/reversed carts no longer leave orphaned transaction history entries")
    else:
        print("\n❌ SOME TESTS FAILED! The fix may need additional work.")
    
    return success

if __name__ == '__main__':
    test_transaction_history_fix()
