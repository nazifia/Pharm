#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from store.models import DispensingLog
from userauth.models import User
from customer.models import Customer, TransactionHistory
from django.urls import reverse

def test_enhanced_features():
    """Test the enhanced dispensing features"""
    
    print("Testing Enhanced Dispensing Features...")
    print("=" * 50)
    
    # Test 1: Check if new URL patterns work
    print("\n1. Testing URL patterns...")
    try:
        from django.urls import reverse
        
        # Test user dispensing summary URLs
        summary_url = reverse('store:user_dispensing_summary')
        details_url = reverse('store:user_dispensing_details')
        print(f"✓ User dispensing summary URL: {summary_url}")
        print(f"✓ User dispensing details URL: {details_url}")
        
        # Test user-specific details URL
        user = User.objects.first()
        if user:
            user_details_url = reverse('store:user_dispensing_details_user', args=[user.id])
            print(f"✓ User-specific details URL: {user_details_url}")
        
    except Exception as e:
        print(f"✗ URL pattern error: {e}")
    
    # Test 2: Check dispensing log data
    print("\n2. Testing dispensing log data...")
    try:
        total_logs = DispensingLog.objects.count()
        dispensed_logs = DispensingLog.objects.filter(status='Dispensed').count()
        returned_logs = DispensingLog.objects.filter(status='Returned').count()
        
        print(f"✓ Total dispensing logs: {total_logs}")
        print(f"✓ Dispensed logs: {dispensed_logs}")
        print(f"✓ Returned logs: {returned_logs}")
        
        # Test has_returns property
        if dispensed_logs > 0:
            sample_log = DispensingLog.objects.filter(status='Dispensed').first()
            print(f"✓ Sample dispensed log has_returns: {sample_log.has_returns}")
        
    except Exception as e:
        print(f"✗ Dispensing log error: {e}")
    
    # Test 3: Check transaction history functionality
    print("\n3. Testing transaction history...")
    try:
        total_transactions = TransactionHistory.objects.count()
        refund_transactions = TransactionHistory.objects.filter(transaction_type='refund').count()
        
        print(f"✓ Total transaction history records: {total_transactions}")
        print(f"✓ Refund transactions: {refund_transactions}")
        
    except Exception as e:
        print(f"✗ Transaction history error: {e}")
    
    # Test 4: Check user data for dispensing summary
    print("\n4. Testing user dispensing data...")
    try:
        users_with_logs = User.objects.filter(dispensinglog__isnull=False).distinct().count()
        print(f"✓ Users with dispensing logs: {users_with_logs}")
        
        if users_with_logs > 0:
            sample_user = User.objects.filter(dispensinglog__isnull=False).first()
            user_logs = DispensingLog.objects.filter(user=sample_user).count()
            print(f"✓ Sample user ({sample_user.username}) has {user_logs} logs")
        
    except Exception as e:
        print(f"✗ User dispensing data error: {e}")
    
    # Test 5: Check customer and wallet data
    print("\n5. Testing customer and wallet data...")
    try:
        total_customers = Customer.objects.count()
        customers_with_wallets = Customer.objects.filter(wallet__isnull=False).count()
        
        print(f"✓ Total customers: {total_customers}")
        print(f"✓ Customers with wallets: {customers_with_wallets}")
        
    except Exception as e:
        print(f"✗ Customer/wallet data error: {e}")
    
    print("\n" + "=" * 50)
    print("Enhanced features test completed!")
    print("\nNext steps:")
    print("1. Access the user dispensing summary at: /user_dispensing_summary/")
    print("2. Click 'View All Details' to see the detailed breakdown")
    print("3. Click 'View Details' for individual users")
    print("4. Test return functionality to verify transaction history creation")
    print("5. Test cart clearing to verify wallet refund logic")

if __name__ == '__main__':
    test_enhanced_features()
