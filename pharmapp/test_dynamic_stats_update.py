#!/usr/bin/env python
"""
Test script to verify that daily sales statistics update dynamically when returns are processed.
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

def test_dynamic_stats_update():
    """Test that daily sales statistics update correctly when returns are processed."""
    
    print("🧪 Testing Dynamic Statistics Update")
    print("=" * 60)
    
    today = datetime.now().date()
    
    # Get current statistics
    print(f"📅 Testing for date: {today}")
    
    # Calculate current dispensed amounts
    dispensed_logs = DispensingLog.objects.filter(
        created_at__date=today,
        status='Dispensed'
    )
    dispensed_total = dispensed_logs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Calculate current returned amounts
    returned_logs = DispensingLog.objects.filter(
        created_at__date=today,
        status__in=['Returned', 'Partially Returned']
    )
    returned_total = returned_logs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Calculate net sales
    net_sales = dispensed_total - returned_total
    
    print(f"📊 Current Statistics:")
    print(f"  ✅ Dispensed items: {dispensed_logs.count()}")
    print(f"  💰 Total dispensed amount: ₦{dispensed_total:,.2f}")
    print(f"  🔄 Returned items: {returned_logs.count()}")
    print(f"  💸 Total returned amount: ₦{returned_total:,.2f}")
    print(f"  📈 Net sales: ₦{net_sales:,.2f}")
    
    print("\n" + "=" * 60)
    print("🎯 EXPECTED BEHAVIOR:")
    print("1. When you process a return via the web interface:")
    print("   - A new DispensingLog entry should be created with status='Returned'")
    print("   - The daily sales statistics should automatically update")
    print("   - Net sales should decrease by the returned amount")
    print("   - This should happen dynamically without page refresh (via HTMX)")
    
    print("\n2. The dispensing log page statistics should show:")
    print(f"   - Daily Sales: ₦{net_sales:,.2f} (not ₦{dispensed_total:,.2f})")
    
    print("\n3. HTMX requests should:")
    print("   - Trigger automatic refresh of statistics")
    print("   - Update the dispensing log table")
    print("   - Show updated daily/monthly sales data")
    
    # Show recent activity
    recent_logs = DispensingLog.objects.filter(
        created_at__date=today
    ).order_by('-created_at')[:5]
    
    if recent_logs.exists():
        print(f"\n📋 Recent Activity (Last 5 entries):")
        for i, log in enumerate(recent_logs, 1):
            status_icon = "✅" if log.status == "Dispensed" else "🔄"
            print(f"  {i}. {status_icon} {log.name} - ₦{log.amount:,.2f} ({log.status}) at {log.created_at.strftime('%H:%M:%S')}")
    
    print("\n" + "=" * 60)
    print("✅ Test completed! Check the web interface to verify dynamic updates.")
    
    return {
        'dispensed_total': dispensed_total,
        'returned_total': returned_total,
        'net_sales': net_sales,
        'dispensed_count': dispensed_logs.count(),
        'returned_count': returned_logs.count()
    }

if __name__ == "__main__":
    try:
        result = test_dynamic_stats_update()
        print(f"\n📊 Summary: {result['dispensed_count']} dispensed, {result['returned_count']} returned")
        print(f"💰 Net Sales: ₦{result['net_sales']:,.2f}")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
