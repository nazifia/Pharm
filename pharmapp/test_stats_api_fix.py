#!/usr/bin/env python
"""
Test script to verify that the dispensing_log_stats API returns correct net sales.
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from django.db.models import Sum
from store.models import DispensingLog
from store.views import dispensing_log_stats
from datetime import datetime

def test_stats_api_fix():
    """Test that the dispensing_log_stats API returns correct net sales."""
    
    print("🧪 Testing Statistics API Fix")
    print("=" * 60)
    
    today = datetime.now().date()
    
    # Calculate expected values manually
    dispensed_logs = DispensingLog.objects.filter(
        created_at__date=today,
        status='Dispensed'
    )
    dispensed_total = dispensed_logs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    returned_logs = DispensingLog.objects.filter(
        created_at__date=today,
        status__in=['Returned', 'Partially Returned']
    )
    returned_total = returned_logs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    expected_net_sales = dispensed_total - returned_total
    
    print(f"📅 Testing for date: {today}")
    print(f"📊 Expected Calculation:")
    print(f"  ✅ Dispensed: ₦{dispensed_total:,.2f}")
    print(f"  🔄 Returned: ₦{returned_total:,.2f}")
    print(f"  📈 Expected Net Sales: ₦{expected_net_sales:,.2f}")
    
    # Test the API
    try:
        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/dispensing_log_stats/')
        
        # Get a user for the request (assuming superuser exists)
        try:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.first()
            request.user = user
        except:
            print("❌ No users found in database")
            return
        
        # Call the stats view
        response = dispensing_log_stats(request)
        
        if response.status_code == 200:
            import json
            stats_data = json.loads(response.content)
            
            api_daily_sales = stats_data.get('daily_total_sales', 0)
            
            print(f"\n🔍 API Response:")
            print(f"  📊 API Daily Sales: ₦{api_daily_sales:,.2f}")
            print(f"  📈 Expected Net Sales: ₦{float(expected_net_sales):,.2f}")
            
            # Check if they match
            if abs(api_daily_sales - float(expected_net_sales)) < 0.01:  # Allow for small floating point differences
                print(f"  ✅ MATCH! API returns correct net sales")
                success = True
            else:
                print(f"  ❌ MISMATCH! API should return ₦{float(expected_net_sales):,.2f} but returns ₦{api_daily_sales:,.2f}")
                success = False
            
            # Show other stats for context
            print(f"\n📋 Other API Stats:")
            print(f"  📦 Total Items: {stats_data.get('total_items_dispensed', 0)}")
            print(f"  🔢 Unique Items: {stats_data.get('unique_items', 0)}")
            
        else:
            print(f"❌ API request failed with status {response.status_code}")
            success = False
            
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Statistics API Fix SUCCESSFUL!")
        print("   The dispensing log page should now show correct net sales.")
    else:
        print("❌ Statistics API Fix FAILED!")
        print("   The dispensing log page may still show incorrect sales totals.")
    
    return success

if __name__ == "__main__":
    test_stats_api_fix()
