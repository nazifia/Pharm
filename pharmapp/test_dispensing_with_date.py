#!/usr/bin/env python
"""
Test script to check dispensing logs with specific date filtering
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from store.models import DispensingLog
from datetime import date, timedelta
import json

User = get_user_model()

def test_dispensing_with_date():
    print("Testing Dispensing Log with Date Filtering")
    print("=" * 50)
    
    # Check what dispensing logs exist
    logs = DispensingLog.objects.all().order_by('-created_at')
    print(f"Total dispensing logs in database: {logs.count()}")
    
    if logs.exists():
        print("\nRecent dispensing logs:")
        for log in logs[:5]:  # Show first 5
            print(f"  - {log.user.username}: {log.name} (₦{log.amount}) - {log.created_at.date()} - {log.status}")
    
    # Check for logs from July 28, 2025 (as shown in screenshot)
    july_28 = date(2025, 7, 28)
    july_28_logs = DispensingLog.objects.filter(created_at__date=july_28, status='Dispensed')
    print(f"\nDispensing logs from July 28, 2025: {july_28_logs.count()}")
    
    if july_28_logs.exists():
        total_amount_july_28 = sum(log.amount for log in july_28_logs)
        print(f"Total amount for July 28: ₦{total_amount_july_28}")
        
        for log in july_28_logs:
            print(f"  - {log.user.username}: {log.name} (₦{log.amount})")
    
    # Test API with date filtering for July 28
    client = Client()
    
    # Find the user 'ameer' from the screenshot
    try:
        ameer_user = User.objects.get(username='ameer')
        client.force_login(ameer_user)
        
        print(f"\n🧪 Testing API with user 'ameer' for July 28, 2025:")
        
        # Test with date filtering
        response = client.get(reverse('store:dispensing_log_stats'), {
            'date_from': '2025-07-28',
            'date_to': '2025-07-28'
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Response for July 28:")
            print(f"   - total_items_dispensed: {data.get('total_items_dispensed')}")
            print(f"   - unique_items: {data.get('unique_items')}")
            print(f"   - daily_total_sales: {data.get('daily_total_sales')}")
            print(f"   - is_filtered: {data.get('is_filtered')}")
            print(f"   - period: {data.get('context', {}).get('period')}")
        else:
            print(f"❌ API Error: {response.status_code}")
            
    except User.DoesNotExist:
        print("❌ User 'ameer' not found")
    
    # Test with today's date (should be 0)
    print(f"\n🧪 Testing API with today's date ({date.today()}):")
    
    try:
        response = client.get(reverse('store:dispensing_log_stats'))
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Response for today:")
            print(f"   - total_items_dispensed: {data.get('total_items_dispensed')}")
            print(f"   - unique_items: {data.get('unique_items')}")
            print(f"   - daily_total_sales: {data.get('daily_total_sales')}")
            print(f"   - is_filtered: {data.get('is_filtered')}")
            print(f"   - period: {data.get('context', {}).get('period')}")
        else:
            print(f"❌ API Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n" + "=" * 50)
    print("Summary:")
    print("- The screenshot shows data from July 28, 2025")
    print("- Today's date is July 29, 2025")
    print("- That's why daily sales shows 0 for today")
    print("- The API should show correct values when filtered by July 28")

if __name__ == "__main__":
    test_dispensing_with_date()
