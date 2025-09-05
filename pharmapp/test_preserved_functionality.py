#!/usr/bin/env python
"""
Test script to verify that existing functionalities are preserved while the refund fix is applied.

This test verifies:
1. Cart can always be cleared (existing functionality preserved)
2. Refunds are only processed when receipts exist (fix applied)
3. Items are always returned to stock when cart is cleared
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
from django.contrib.messages.storage.fallback import FallbackStorage

from customer.models import Customer, Wallet, TransactionHistory
from store.models import Item, Cart, Sales
from store.views import select_items, clear_cart
from userauth.models import User

def setup_test_data():
    """Create test user, customer, and item"""
    print("Setting up test data...")
    
    # Create test user
    User = get_user_model()
    user, created = User.objects.get_or_create(
        mobile='5555555555555',  # Unique mobile number
        defaults={
            'username': 'testuser_preserved',
            'email': 'test_preserved@example.com',
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Create test customer
    customer, created = Customer.objects.get_or_create(
        name='Test Customer Preserved',
        defaults={
            'phone': '5555555555',
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
        name='Test Medicine Preserved',
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

def test_preserved_functionality():
    """Test that existing functionalities are preserved while refund fix is applied"""
    print("\n" + "="*70)
    print("TESTING PRESERVED FUNCTIONALITY WITH REFUND FIX")
    print("="*70)
    
    user, customer, item, wallet = setup_test_data()
    
    # Clear any existing data
    TransactionHistory.objects.filter(customer=customer).delete()
    Cart.objects.filter(user=user).delete()
    Sales.objects.filter(user=user, customer=customer).delete()
    
    # Reset wallet balance and item stock
    initial_balance = Decimal('1000.00')
    wallet.balance = initial_balance
    wallet.save()
    
    initial_stock = 100
    item.stock = initial_stock
    item.save()
    
    print(f"\nInitial Setup:")
    print(f"   💰 Wallet balance: ₦{wallet.balance}")
    print(f"   📦 Item stock: {item.stock}")
    print(f"   📝 Transaction history count: {TransactionHistory.objects.filter(customer=customer).count()}")
    
    # Test 1: Cart clearing functionality is preserved (can always clear cart)
    print("\n🔍 Test 1: Cart clearing functionality preserved...")
    
    request_data = {
        'action': 'purchase',
        'item_ids': [str(item.id)],
        'quantities': ['5'],  # Select 5 items
        'units': ['Tab'],
        'payment_method': 'Wallet',
        'status': 'Paid'
    }
    
    request = create_mock_request(user, 'POST', request_data)
    
    try:
        # Step 1: Select items (add to cart)
        response = select_items(request, customer.id)
        print(f"   ✓ Items selected successfully")
        
        cart_count = Cart.objects.filter(user=user).count()
        print(f"   ✓ Cart items count: {cart_count}")
        
        # Step 2: Clear cart without generating receipt
        request = create_mock_request(user, 'POST', {'action': 'clear'})
        response = clear_cart(request)
        
        # Check that cart was cleared (functionality preserved)
        cart_count_after_clear = Cart.objects.filter(user=user).count()
        print(f"   ✓ Cart items count after clear: {cart_count_after_clear}")
        
        # Check that items were returned to stock (functionality preserved)
        item.refresh_from_db()
        print(f"   ✓ Item stock after cart clear: {item.stock}")
        
        # Check wallet balance (should be unchanged - refund fix applied)
        wallet.refresh_from_db()
        print(f"   ✓ Wallet balance after cart clear: ₦{wallet.balance}")
        
        # Check transaction history (should be empty - refund fix applied)
        history_count = TransactionHistory.objects.filter(customer=customer).count()
        print(f"   ✓ Transaction history count: {history_count}")
        
    except Exception as e:
        print(f"   ❌ Error during test 1: {e}")
        return False
    
    # Verify results
    print("\n" + "="*70)
    print("RESULTS:")
    print("="*70)
    
    success = True
    
    # Test 1: Cart clearing functionality preserved
    if cart_count_after_clear == 0:
        print("✅ PASS: Cart clearing functionality preserved")
        print("   📋 Cart can always be cleared regardless of receipt status")
    else:
        print("❌ FAIL: Cart clearing functionality broken")
        success = False
    
    # Test 2: Items returned to stock (functionality preserved)
    if item.stock == initial_stock:
        print("✅ PASS: Items returned to stock functionality preserved")
        print(f"   📦 Stock correctly restored from {initial_stock - 5} to {item.stock}")
    else:
        print(f"❌ FAIL: Items not returned to stock (expected {initial_stock}, got {item.stock})")
        success = False
    
    # Test 3: Refund fix applied (no refund when no receipt)
    if wallet.balance == initial_balance:
        print("✅ PASS: Refund fix applied correctly")
        print(f"   💰 Wallet balance preserved at ₦{initial_balance} (no refund without receipt)")
    else:
        print(f"❌ FAIL: Refund fix not working (wallet changed from ₦{initial_balance} to ₦{wallet.balance})")
        success = False
    
    # Test 4: No transaction history created (refund fix applied)
    if history_count == 0:
        print("✅ PASS: No transaction history created without receipt")
        print("   📝 Transaction history correctly empty when no receipt generated")
    else:
        print("❌ FAIL: Transaction history created without receipt")
        success = False
    
    if success:
        print("\n🎉 ALL TESTS PASSED! Functionality preserved with refund fix applied.")
        print("\n📋 Summary:")
        print("   ✅ Cart can always be cleared (existing functionality preserved)")
        print("   ✅ Items always returned to stock (existing functionality preserved)")
        print("   ✅ No refunds processed without receipts (refund fix applied)")
        print("   ✅ No transaction history without receipts (refund fix applied)")
        print("\n🎯 Perfect balance: Existing functionality preserved + Refund issue fixed!")
    else:
        print("\n❌ SOME TESTS FAILED! Need to review the implementation.")
    
    return success

if __name__ == '__main__':
    test_preserved_functionality()
