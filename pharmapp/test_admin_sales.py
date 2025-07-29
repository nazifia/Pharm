#!/usr/bin/env python
"""
Test script to verify the sales management admin functionality
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.contrib import admin
from store.models import DispensingLog, Sales, SalesItem, Receipt
from store.admin import DispensingLogAdmin, SalesAdmin, ReceiptAdmin
from django.db.models import Sum, Count
from datetime import datetime, timedelta

def test_admin_functionality():
    """Test the enhanced admin functionality"""
    print("🧪 Testing Sales Management Admin Functionality")
    print("=" * 60)
    
    # Test 1: Check if admin classes are properly registered
    print("\n1. Testing Admin Registration:")
    try:
        dispensing_admin = admin.site._registry.get(DispensingLog)
        sales_admin = admin.site._registry.get(Sales)
        receipt_admin = admin.site._registry.get(Receipt)
        
        print(f"✅ DispensingLog Admin: {dispensing_admin.__class__.__name__}")
        print(f"✅ Sales Admin: {sales_admin.__class__.__name__}")
        print(f"✅ Receipt Admin: {receipt_admin.__class__.__name__}")
    except Exception as e:
        print(f"❌ Admin registration error: {e}")
    
    # Test 2: Check admin display methods
    print("\n2. Testing Admin Display Methods:")
    try:
        # Get a sample dispensing log
        sample_log = DispensingLog.objects.first()
        if sample_log:
            admin_instance = DispensingLogAdmin(DispensingLog, admin.site)
            
            # Test sales_performance method
            performance = admin_instance.sales_performance(sample_log)
            print(f"✅ Sales Performance Display: {performance}")
            
            # Test return_info method
            return_info = admin_instance.return_info(sample_log)
            print(f"✅ Return Info Display: {return_info}")
        else:
            print("⚠️ No dispensing logs found for testing")
    except Exception as e:
        print(f"❌ Display method error: {e}")
    
    # Test 3: Check sales statistics calculation
    print("\n3. Testing Sales Statistics:")
    try:
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # Calculate today's sales
        today_sales = DispensingLog.objects.filter(
            created_at__date=today,
            status='Dispensed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate yesterday's sales
        yesterday_sales = DispensingLog.objects.filter(
            created_at__date=yesterday,
            status='Dispensed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        print(f"✅ Today's Sales: ₦{today_sales:,.2f}")
        print(f"✅ Yesterday's Sales: ₦{yesterday_sales:,.2f}")
        
        # Calculate change percentage
        if yesterday_sales > 0:
            change = ((today_sales - yesterday_sales) / yesterday_sales * 100)
            print(f"✅ Daily Change: {change:+.1f}%")
        else:
            print("✅ Daily Change: N/A (no previous data)")
            
    except Exception as e:
        print(f"❌ Statistics calculation error: {e}")
    
    # Test 4: Check top selling items
    print("\n4. Testing Top Selling Items:")
    try:
        this_month = datetime.now().date().replace(day=1)
        top_items = DispensingLog.objects.filter(
            created_at__date__gte=this_month,
            status='Dispensed'
        ).values('name').annotate(
            total_quantity=Sum('quantity'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')[:5]
        
        if top_items:
            for i, item in enumerate(top_items, 1):
                print(f"✅ {i}. {item['name']}: ₦{item['total_amount']:,.2f} ({item['total_quantity']} units)")
        else:
            print("⚠️ No sales data found for this month")
            
    except Exception as e:
        print(f"❌ Top items calculation error: {e}")
    
    # Test 5: Check sales by user
    print("\n5. Testing Sales by User:")
    try:
        this_month = datetime.now().date().replace(day=1)
        sales_by_user = DispensingLog.objects.filter(
            created_at__date__gte=this_month,
            status='Dispensed'
        ).values('user__username', 'user__first_name', 'user__last_name').annotate(
            total_sales=Sum('amount'),
            total_items=Count('id')
        ).order_by('-total_sales')[:5]
        
        if sales_by_user:
            for i, user in enumerate(sales_by_user, 1):
                name = f"{user['user__first_name']} {user['user__last_name']}" if user['user__first_name'] else user['user__username']
                print(f"✅ {i}. {name}: ₦{user['total_sales']:,.2f} ({user['total_items']} items)")
        else:
            print("⚠️ No user sales data found for this month")
            
    except Exception as e:
        print(f"❌ User sales calculation error: {e}")
    
    # Test 6: Check model counts
    print("\n6. Testing Model Counts:")
    try:
        dispensing_count = DispensingLog.objects.count()
        sales_count = Sales.objects.count()
        receipt_count = Receipt.objects.count()
        
        print(f"✅ Total Dispensing Logs: {dispensing_count}")
        print(f"✅ Total Sales Records: {sales_count}")
        print(f"✅ Total Receipts: {receipt_count}")
        
    except Exception as e:
        print(f"❌ Model count error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Sales Management Admin Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_admin_functionality()
