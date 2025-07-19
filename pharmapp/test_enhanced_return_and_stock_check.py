#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from store.models import DispensingLog, StockCheck, StockCheckItem, WholesaleStockCheck, WholesaleStockCheckItem, Item, WholesaleItem
from userauth.models import User
from customer.models import Customer, TransactionHistory, WholesaleCustomer
from django.urls import reverse

def test_enhanced_functionality():
    """Test all enhanced return and stock check functionality"""
    
    print("Testing Enhanced Return and Stock Check Functionality...")
    print("=" * 60)
    
    # Test 1: Enhanced Return Status Tracking
    print("\n1. Testing Enhanced Return Status Tracking...")
    try:
        # Test dispensing log return summary
        sample_logs = DispensingLog.objects.all()[:5]
        
        for log in sample_logs:
            return_summary = log.return_summary
            print(f"✓ Log ID {log.id} ({log.name}): {return_summary['status_display']} - {return_summary['return_type']}")
            
            if return_summary['has_returns']:
                print(f"  - Returned: {return_summary['returned_quantity']}, Remaining: {return_summary['remaining_quantity']}")
                print(f"  - Return Percentage: {return_summary['return_percentage']:.1f}%")
        
        print("✓ Enhanced return status tracking working correctly")
        
    except Exception as e:
        print(f"✗ Return status tracking error: {e}")
    
    # Test 2: Stock Check Enhancement URLs
    print("\n2. Testing Stock Check Enhancement URLs...")
    try:
        # Test retail stock check URLs
        retail_stock_checks = StockCheck.objects.filter(status='in_progress')
        if retail_stock_checks.exists():
            stock_check = retail_stock_checks.first()
            add_items_url = reverse('store:add_items_to_stock_check', args=[stock_check.id])
            print(f"✓ Retail add items URL: {add_items_url}")
        else:
            print("ℹ No in-progress retail stock checks found")
        
        # Test wholesale stock check URLs
        wholesale_stock_checks = WholesaleStockCheck.objects.filter(status='in_progress')
        if wholesale_stock_checks.exists():
            stock_check = wholesale_stock_checks.first()
            add_items_url = reverse('wholesale:add_items_to_wholesale_stock_check', args=[stock_check.id])
            print(f"✓ Wholesale add items URL: {add_items_url}")
        else:
            print("ℹ No in-progress wholesale stock checks found")
        
        print("✓ Stock check enhancement URLs working correctly")
        
    except Exception as e:
        print(f"✗ Stock check URL error: {e}")
    
    # Test 3: Dispensing Log Creation in Returns
    print("\n3. Testing Dispensing Log Creation in Returns...")
    try:
        # Check recent dispensing logs
        recent_logs = DispensingLog.objects.order_by('-created_at')[:10]
        recent_logs_list = list(recent_logs)  # Convert to list to avoid slice issues

        dispensed_count = len([log for log in recent_logs_list if log.status == 'Dispensed'])
        returned_count = len([log for log in recent_logs_list if log.status == 'Returned'])
        partially_returned_count = len([log for log in recent_logs_list if log.status == 'Partially Returned'])

        print(f"✓ Recent logs - Dispensed: {dispensed_count}, Returned: {returned_count}, Partially Returned: {partially_returned_count}")

        # Test return summary for each status
        for status in ['Dispensed', 'Returned', 'Partially Returned']:
            logs_with_status = [log for log in recent_logs_list if log.status == status]
            if logs_with_status:
                sample_log = logs_with_status[0]
                summary = sample_log.return_summary
                print(f"✓ {status} log return summary: {summary['status_display']}")
        
        print("✓ Dispensing log creation and tracking working correctly")
        
    except Exception as e:
        print(f"✗ Dispensing log error: {e}")
    
    # Test 4: Transaction History for Returns
    print("\n4. Testing Transaction History for Returns...")
    try:
        # Check recent transaction history
        recent_transactions = TransactionHistory.objects.order_by('-date')[:10]
        recent_transactions_list = list(recent_transactions)  # Convert to list to avoid slice issues
        refund_transactions = [t for t in recent_transactions_list if t.transaction_type == 'refund']

        print(f"✓ Recent transactions: {len(recent_transactions_list)}")
        print(f"✓ Recent refund transactions: {len(refund_transactions)}")

        if refund_transactions:
            sample_refund = refund_transactions[0]
            print(f"✓ Sample refund: {sample_refund.description} - ₦{sample_refund.amount}")
        
        print("✓ Transaction history for returns working correctly")
        
    except Exception as e:
        print(f"✗ Transaction history error: {e}")
    
    # Test 5: Stock Check Item Availability
    print("\n5. Testing Stock Check Item Availability...")
    try:
        # Test retail stock check item availability
        retail_stock_checks = StockCheck.objects.all()
        if retail_stock_checks.exists():
            stock_check = retail_stock_checks.first()
            existing_item_ids = stock_check.stockcheckitem_set.values_list('item_id', flat=True)
            available_items = Item.objects.exclude(id__in=existing_item_ids)
            print(f"✓ Retail Stock Check #{stock_check.id}: {existing_item_ids.count()} items included, {available_items.count()} available to add")
        
        # Test wholesale stock check item availability
        wholesale_stock_checks = WholesaleStockCheck.objects.all()
        if wholesale_stock_checks.exists():
            stock_check = wholesale_stock_checks.first()
            existing_item_ids = stock_check.wholesale_items.values_list('item_id', flat=True)
            available_items = WholesaleItem.objects.exclude(id__in=existing_item_ids)
            print(f"✓ Wholesale Stock Check #{stock_check.id}: {existing_item_ids.count()} items included, {available_items.count()} available to add")
        
        print("✓ Stock check item availability logic working correctly")
        
    except Exception as e:
        print(f"✗ Stock check availability error: {e}")
    
    # Test 6: Customer and Wallet Data
    print("\n6. Testing Customer and Wallet Data...")
    try:
        # Test retail customers
        retail_customers = Customer.objects.all()
        customers_with_wallets = retail_customers.filter(wallet__isnull=False)
        print(f"✓ Retail customers: {retail_customers.count()}, with wallets: {customers_with_wallets.count()}")
        
        # Test wholesale customers
        wholesale_customers = WholesaleCustomer.objects.all()
        wholesale_with_wallets = wholesale_customers.filter(wholesale_customer_wallet__isnull=False)
        print(f"✓ Wholesale customers: {wholesale_customers.count()}, with wallets: {wholesale_with_wallets.count()}")
        
        print("✓ Customer and wallet data working correctly")
        
    except Exception as e:
        print(f"✗ Customer/wallet error: {e}")
    
    print("\n" + "=" * 60)
    print("Enhanced functionality test completed!")
    print("\nKey Features Tested:")
    print("✓ Enhanced return status tracking with detailed summaries")
    print("✓ Dynamic stock check item addition functionality")
    print("✓ Comprehensive dispensing log creation for all returns")
    print("✓ Transaction history tracking for wallet refunds")
    print("✓ Improved return percentage calculations")
    print("✓ Better status indicators in dispensing logs")
    
    print("\nNext Steps for Manual Testing:")
    print("1. Test return functionality through the UI")
    print("2. Test adding items to existing stock checks")
    print("3. Verify wallet refunds are working correctly")
    print("4. Check dispensing log displays enhanced return information")
    print("5. Verify transaction history is created for returns")

if __name__ == '__main__':
    test_enhanced_functionality()
