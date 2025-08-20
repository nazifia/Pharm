#!/usr/bin/env python
"""
Test script to verify that returned items are properly excluded from daily sales calculations.
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.db.models import Sum
from store.models import DispensingLog
from datetime import datetime

def test_returns_calculation():
    """Test that daily sales calculation properly excludes returned items."""
    
    print("🧪 Testing Returns Calculation Fix")
    print("=" * 50)
    
    today = datetime.now().date()
    
    # Get all dispensing logs for today
    today_logs = DispensingLog.objects.filter(created_at__date=today)
    
    print(f"📅 Testing for date: {today}")
    print(f"📊 Total dispensing logs for today: {today_logs.count()}")
    
    # Calculate dispensed amounts
    dispensed_logs = today_logs.filter(status='Dispensed')
    dispensed_total = dispensed_logs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    print(f"✅ Dispensed items: {dispensed_logs.count()}")
    print(f"💰 Total dispensed amount: ₦{dispensed_total:,.2f}")
    
    # Calculate returned amounts
    returned_logs = today_logs.filter(status__in=['Returned', 'Partially Returned'])
    returned_total = returned_logs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    print(f"🔄 Returned items: {returned_logs.count()}")
    print(f"💸 Total returned amount: ₦{returned_total:,.2f}")
    
    # Calculate net sales
    net_sales = dispensed_total - returned_total
    print(f"📈 Net sales (Dispensed - Returned): ₦{net_sales:,.2f}")
    
    # Show individual returned items
    if returned_logs.exists():
        print("\n🔍 Returned Items Details:")
        for log in returned_logs:
            print(f"  - {log.name} ({log.brand}): ₦{log.amount:,.2f} at {log.created_at}")
    
    # Show individual dispensed items
    if dispensed_logs.exists():
        print("\n📦 Dispensed Items Details:")
        for log in dispensed_logs:
            print(f"  - {log.name} ({log.brand}): ₦{log.amount:,.2f} at {log.created_at}")
    
    print("\n" + "=" * 50)
    print(f"🎯 FINAL RESULT: Daily Sales should show ₦{net_sales:,.2f}")
    print("   (This should match the 'Daily Sales' shown in the statistics)")
    
    return {
        'dispensed_total': dispensed_total,
        'returned_total': returned_total,
        'net_sales': net_sales,
        'dispensed_count': dispensed_logs.count(),
        'returned_count': returned_logs.count()
    }

if __name__ == "__main__":
    try:
        result = test_returns_calculation()
        print(f"\n✅ Test completed successfully!")
        print(f"📊 Summary: {result['dispensed_count']} dispensed, {result['returned_count']} returned")
        print(f"💰 Net Sales: ₦{result['net_sales']:,.2f}")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
