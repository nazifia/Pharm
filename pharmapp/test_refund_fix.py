#!/usr/bin/env python
"""
Test script to verify that refunds are only processed when receipts exist,
not when items are just selected and then cart is cleared.

This test demonstrates the fix for the issue where refunds were made
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

from customer.models import Customer, Wallet, TransactionHistory
from store.models import Item, Cart, Sales, Receipt
from store.views import select_items, clear_cart, receipt
from userauth.models import User

def setup_test_data():
    """Create test user, customer, and item"""
    print("Setting up test data...")
    
    # Create test user
    User = get_user_model()
    user, created = User.objects.get_or_create(
        mobile='1234567890123',  # Unique mobile number
        defaults={
            'username': 'testuser_refund',
            'email': 'test_refund@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Create test customer
    customer, created = Customer.objects.get_or_create(
        name='Test Customer Refund',
        defaults={
            'phone': '1234567890',
            'address': 'Test Address'
        }
    )
    
    # Ensure customer has a wallet
    wallet, created = Wallet.objects.get_or_create(
        customer=customer,
        defaults={'balance': Decimal('1000.00')}
    )
    
    # Create test item
    item, created = Item.objects.get_or_create(
        name='Test Medicine Refund',
        defaults={
            'brand': 'Test Brand',
            'price': Decimal('100.00'),
            'cost': Decimal('50.00'),
            'stock': 100,
            'unit': 'Tab'
        }
    )
    
    return user, customer, item, wallet

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

def test_refund_fix():
    """Test that refunds are only processed when receipts exist"""
    print("\n" + "="*60)
    print("TESTING REFUND FIX")
    print("="*60)
    
    user, customer, item, wallet = setup_test_data()
    
    # Clear any existing data
    TransactionHistory.objects.filter(customer=customer).delete()
    Cart.objects.filter(user=user).delete()
    Sales.objects.filter(user=user, customer=customer).delete()
    Receipt.objects.filter(sales__customer=customer).delete()
    
    # Reset wallet balance
    initial_balance = Decimal('1000.00')
    wallet.balance = initial_balance
    wallet.save()
    
    print(f"\nInitial wallet balance: ₦{wallet.balance}")
    print(f"Initial transaction history count: {TransactionHistory.objects.filter(customer=customer).count()}")
    
    # Test 1: Select items (add to cart) but don't generate receipt, then clear cart
    print("\n1. Testing cart clearing without receipt generation...")
    
    request_data = {
        'action': 'purchase',
        'item_ids': [str(item.id)],
        'quantities': ['2'],
        'units': ['Tab'],
        'payment_method': 'Wallet',
        'status': 'Paid'
    }
    
    request = create_mock_request(user, 'POST', request_data)
    
    try:
        # Select items (add to cart)
        response = select_items(request, customer.id)
        print(f"   - Items selected successfully")
        print(f"   - Cart items count: {Cart.objects.filter(user=user).count()}")
        
        # Check wallet balance after selection (should be unchanged)
        wallet.refresh_from_db()
        print(f"   - Wallet balance after selection: ₦{wallet.balance}")
        
        # Clear cart without generating receipt
        request = create_mock_request(user, 'POST', {'action': 'clear'})
        response = clear_cart(request)
        
        # Check wallet balance after cart clear (should still be unchanged)
        wallet.refresh_from_db()
        print(f"   - Wallet balance after cart clear: ₦{wallet.balance}")
        print(f"   - Transaction history count after cart clear: {TransactionHistory.objects.filter(customer=customer).count()}")
        
        balance_after_clear_no_receipt = wallet.balance
        history_count_after_clear_no_receipt = TransactionHistory.objects.filter(customer=customer).count()
        
    except Exception as e:
        print(f"   - Error during test 1: {e}")
        return False
    
    # Test 2: Select items, generate receipt, then clear cart
    print("\n2. Testing cart clearing WITH receipt generation...")
    
    try:
        # Add items to cart again
        request = create_mock_request(user, 'POST', request_data)
        response = select_items(request, customer.id)
        print(f"   - Items selected again")
        
        # Generate receipt (this should deduct from wallet)
        receipt_data = {
            'buyer_name': customer.name,
            'buyer_address': customer.address,
            'payment_method': 'Wallet',
            'status': 'Paid'
        }
        
        request = create_mock_request(user, 'POST', receipt_data)
        # Set customer in session for receipt function
        from userauth.session_utils import set_user_customer_id
        set_user_customer_id(request, customer.id)
        response = receipt(request)
        
        # Check wallet balance after receipt (should be deducted)
        wallet.refresh_from_db()
        print(f"   - Wallet balance after receipt: ₦{wallet.balance}")
        
        balance_after_receipt = wallet.balance
        
        # Now clear cart (this should refund to wallet)
        request = create_mock_request(user, 'POST', {'action': 'clear'})
        response = clear_cart(request)
        
        # Check wallet balance after cart clear (should be refunded)
        wallet.refresh_from_db()
        print(f"   - Wallet balance after cart clear with receipt: ₦{wallet.balance}")
        print(f"   - Transaction history count after cart clear with receipt: {TransactionHistory.objects.filter(customer=customer).count()}")
        
        balance_after_clear_with_receipt = wallet.balance
        history_count_after_clear_with_receipt = TransactionHistory.objects.filter(customer=customer).count()
        
    except Exception as e:
        print(f"   - Error during test 2: {e}")
        return False
    
    # Verify the fix
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    
    success = True
    
    # Test 1 verification: No refund when no receipt
    if balance_after_clear_no_receipt == initial_balance:
        print("✅ PASS: No refund processed when cart cleared without receipt")
    else:
        print(f"❌ FAIL: Refund processed when no receipt existed (balance changed from ₦{initial_balance} to ₦{balance_after_clear_no_receipt})")
        success = False
    
    if history_count_after_clear_no_receipt == 0:
        print("✅ PASS: No transaction history created when cart cleared without receipt")
    else:
        print("❌ FAIL: Transaction history created when cart cleared without receipt")
        success = False
    
    # Test 2 verification: Refund when receipt exists
    if balance_after_receipt < initial_balance:
        print("✅ PASS: Wallet deducted when receipt was generated")
    else:
        print("❌ FAIL: Wallet not deducted when receipt was generated")
        success = False
    
    if balance_after_clear_with_receipt == initial_balance:
        print("✅ PASS: Wallet refunded when cart cleared after receipt generation")
    else:
        print(f"❌ FAIL: Wallet not properly refunded (expected ₦{initial_balance}, got ₦{balance_after_clear_with_receipt})")
        success = False
    
    if history_count_after_clear_with_receipt > 0:
        print("✅ PASS: Transaction history created when cart cleared after receipt generation")
    else:
        print("❌ FAIL: No transaction history created when cart cleared after receipt generation")
        success = False
    
    if success:
        print("\n🎉 ALL TESTS PASSED! The refund fix is working correctly.")
        print("   - No refunds processed when no receipt exists")
        print("   - Refunds only processed when receipts exist")
        print("   - Transaction history accurately reflects refund operations")
    else:
        print("\n❌ SOME TESTS FAILED! The fix may need additional work.")
    
    return success

if __name__ == '__main__':
    test_refund_fix()
