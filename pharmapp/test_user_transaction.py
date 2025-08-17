#!/usr/bin/env python
"""
Test script to verify that user field is properly added to TransactionHistory

This script tests the functionality of the user column in transaction history
to ensure that new transactions properly record which user performed them.

Usage:
    python test_user_transaction.py

Expected Output:
    - Creates a test user and customer if they don't exist
    - Adds funds to the customer's wallet
    - Verifies that the transaction includes the user information
    - Displays success message if user field is properly populated
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from customer.models import TransactionHistory, Customer, Wallet
from userauth.models import User
from decimal import Decimal

def test_user_transaction():
    """Test that new transactions include user information"""
    
    print("=" * 60)
    print("TESTING USER FIELD IN TRANSACTION HISTORY")
    print("=" * 60)
    
    # Get or create a test user
    test_user, created = User.objects.get_or_create(
        username='test_transaction_user',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'mobile': '1234567890'  # Add mobile field to avoid constraint error
        }
    )
    
    if created:
        test_user.set_password('testpass123')
        test_user.save()
        print(f"✅ Created test user: {test_user.username}")
    else:
        print(f"✅ Using existing test user: {test_user.username}")
    
    # Get or create a test customer
    test_customer, created = Customer.objects.get_or_create(
        name='Test Customer',
        defaults={
            'phone': '1234567890',
            'address': 'Test Address'
        }
    )
    
    if created:
        print(f"✅ Created test customer: {test_customer.name}")
    else:
        print(f"✅ Using existing test customer: {test_customer.name}")
    
    # Get the customer's wallet
    wallet = test_customer.wallet
    
    # Test adding funds with user
    print(f"\n📊 Before adding funds - Wallet balance: ₦{wallet.balance}")
    
    # Add funds using the updated method that includes user
    test_amount = Decimal('100.00')
    wallet.add_funds(test_amount, user=test_user)
    
    print(f"📊 After adding funds - Wallet balance: ₦{wallet.balance}")
    
    # Check the latest transaction
    latest_transaction = TransactionHistory.objects.filter(
        customer=test_customer
    ).order_by('-date').first()
    
    print(f"\n📋 Latest transaction details:")
    if latest_transaction:
        print(f"   Type: {latest_transaction.transaction_type}")
        print(f"   Amount: ₦{latest_transaction.amount}")
        print(f"   User: {latest_transaction.user.username if latest_transaction.user else 'None'}")
        print(f"   Description: {latest_transaction.description}")
        print(f"   Date: {latest_transaction.date}")
        
        if latest_transaction.user:
            print(f"\n✅ SUCCESS: User field is properly populated!")
            print(f"   Transaction performed by: {latest_transaction.user.username}")
        else:
            print(f"\n❌ ERROR: User field is not populated!")
            return False
    else:
        print(f"\n❌ ERROR: No transaction found!")
        return False
    
    # Additional verification - check transaction counts
    total_transactions = TransactionHistory.objects.count()
    transactions_with_users = TransactionHistory.objects.filter(user__isnull=False).count()
    transactions_without_users = TransactionHistory.objects.filter(user__isnull=True).count()
    
    print(f"\n📈 Transaction Statistics:")
    print(f"   Total transactions: {total_transactions}")
    print(f"   Transactions with users: {transactions_with_users}")
    print(f"   Transactions without users: {transactions_without_users}")
    
    print(f"\n✅ Test completed successfully!")
    print(f"   The user column functionality is working correctly.")
    print("=" * 60)
    
    return True

def cleanup_test_data():
    """Optional: Clean up test data created by this script"""
    try:
        # Remove test user
        test_user = User.objects.get(username='test_transaction_user')
        test_user.delete()
        print("🧹 Cleaned up test user")
        
        # Remove test customer (this will also remove associated wallet and transactions)
        test_customer = Customer.objects.get(name='Test Customer')
        test_customer.delete()
        print("🧹 Cleaned up test customer and associated data")
        
    except (User.DoesNotExist, Customer.DoesNotExist):
        print("🧹 No test data to clean up")

if __name__ == '__main__':
    # Run the test
    success = test_user_transaction()
    
    # Uncomment the line below if you want to clean up test data after running
    # cleanup_test_data()
    
    if success:
        print("\n🎉 All tests passed! User column functionality is working correctly.")
    else:
        print("\n❌ Tests failed! Please check the implementation.")
        sys.exit(1)
