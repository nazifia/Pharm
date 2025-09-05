#!/usr/bin/env python
"""
Simple test to verify the main refund fix: 
No refunds should be processed when no receipt is generated.
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
        mobile='9876543210123',  # Unique mobile number
        defaults={
            'username': 'testuser_simple',
            'email': 'test_simple@example.com',
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Create test customer
    customer, created = Customer.objects.get_or_create(
        name='Test Customer Simple',
        defaults={
            'phone': '9876543210',
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
        name='Test Medicine Simple',
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

def test_main_refund_fix():
    """Test that NO refunds are processed when NO receipt exists"""
    print("\n" + "="*60)
    print("TESTING MAIN REFUND FIX")
    print("="*60)
    
    user, customer, item, wallet = setup_test_data()
    
    # Clear any existing data
    TransactionHistory.objects.filter(customer=customer).delete()
    Cart.objects.filter(user=user).delete()
    Sales.objects.filter(user=user, customer=customer).delete()
    
    # Reset wallet balance
    initial_balance = Decimal('1000.00')
    wallet.balance = initial_balance
    wallet.save()
    
    print(f"\nInitial wallet balance: ₦{wallet.balance}")
    print(f"Initial transaction history count: {TransactionHistory.objects.filter(customer=customer).count()}")
    
    # Test: Select items (add to cart) but don't generate receipt, then clear cart
    print("\n🔍 Testing: Cart clearing without receipt generation...")
    
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
        # Step 1: Select items (add to cart)
        response = select_items(request, customer.id)
        print(f"   ✓ Items selected successfully")
        print(f"   ✓ Cart items count: {Cart.objects.filter(user=user).count()}")
        
        # Check wallet balance after selection (should be unchanged)
        wallet.refresh_from_db()
        print(f"   ✓ Wallet balance after selection: ₦{wallet.balance}")
        
        # Step 2: Clear cart without generating receipt
        request = create_mock_request(user, 'POST', {'action': 'clear'})
        response = clear_cart(request)
        
        # Check wallet balance after cart clear (should still be unchanged)
        wallet.refresh_from_db()
        print(f"   ✓ Wallet balance after cart clear: ₦{wallet.balance}")
        print(f"   ✓ Transaction history count after cart clear: {TransactionHistory.objects.filter(customer=customer).count()}")
        
        balance_after_clear = wallet.balance
        history_count_after_clear = TransactionHistory.objects.filter(customer=customer).count()
        
    except Exception as e:
        print(f"   ❌ Error during test: {e}")
        return False
    
    # Verify the main fix
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    
    success = True
    
    # Main test: No refund when no receipt
    if balance_after_clear == initial_balance:
        print("✅ PASS: No refund processed when cart cleared without receipt")
        print(f"   💰 Wallet balance remained at ₦{initial_balance} (correct)")
    else:
        print(f"❌ FAIL: Refund processed when no receipt existed")
        print(f"   💰 Wallet balance changed from ₦{initial_balance} to ₦{balance_after_clear} (incorrect)")
        success = False
    
    if history_count_after_clear == 0:
        print("✅ PASS: No transaction history created when cart cleared without receipt")
        print(f"   📝 Transaction history count: {history_count_after_clear} (correct)")
    else:
        print("❌ FAIL: Transaction history created when cart cleared without receipt")
        print(f"   📝 Transaction history count: {history_count_after_clear} (incorrect)")
        success = False
    
    if success:
        print("\n🎉 MAIN FIX VERIFIED! The refund fix is working correctly.")
        print("   ✅ No refunds processed when no receipt exists")
        print("   ✅ No transaction history created when no receipt exists")
        print("   ✅ Customer wallet balance preserved when cart cleared without receipt")
        print("\n📋 Summary: Items can be selected and cart cleared without any financial impact")
        print("   when no receipt is generated - exactly as requested!")
    else:
        print("\n❌ MAIN FIX FAILED! The fix needs additional work.")
    
    return success

if __name__ == '__main__':
    test_main_refund_fix()
