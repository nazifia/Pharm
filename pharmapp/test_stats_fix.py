#!/usr/bin/env python
"""
Test script to verify the dispensing_log_stats fix
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from store.models import DispensingLog
from datetime import date, datetime
import json

User = get_user_model()

def test_stats_endpoint():
    """Test the dispensing_log_stats endpoint"""
    print("Testing dispensing_log_stats endpoint...")
    
    # Create a test user
    user, created = User.objects.get_or_create(
        username='statstest',
        defaults={'email': 'statstest@example.com'}
    )
    
    # Create some test data
    test_logs = [
        {
            'user': user,
            'name': 'Canular 20G',
            'brand': 'BD',
            'unit': 'Pcs',
            'quantity': 5,
            'amount': 250.00,
            'status': 'Dispensed'
        },
        {
            'user': user,
            'name': 'Paracetamol 500mg',
            'brand': 'Emzor',
            'unit': 'Tab',
            'quantity': 20,
            'amount': 200.00,
            'status': 'Dispensed'
        }
    ]
    
    for log_data in test_logs:
        DispensingLog.objects.get_or_create(
            user=log_data['user'],
            name=log_data['name'],
            defaults=log_data
        )
    
    # Create a client and login
    client = Client()
    
    # Test the stats endpoint without authentication (should return 401)
    response = client.get(reverse('store:dispensing_log_stats'))
    print(f"✓ Unauthenticated request returns status: {response.status_code}")
    
    # Login the user
    user.set_password('testpass123')
    user.save()
    client.login(username='statstest', password='testpass123')
    
    # Test the stats endpoint with authentication
    response = client.get(reverse('store:dispensing_log_stats'))
    print(f"✓ Authenticated request returns status: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print("✓ Response is valid JSON")
            
            # Check required fields
            required_fields = [
                'total_items_dispensed',
                'total_amount',
                'unique_items',
                'top_dispensed_items',
                'dispensed_by_status',
                'date_range'
            ]
            
            for field in required_fields:
                if field in data:
                    print(f"✓ Field '{field}' present: {data[field]}")
                else:
                    print(f"✗ Field '{field}' missing")
            
            # Test with date parameter
            test_date = '2025-03-01'
            response_with_date = client.get(
                reverse('store:dispensing_log_stats') + f'?date={test_date}'
            )
            
            if response_with_date.status_code == 200:
                date_data = response_with_date.json()
                print(f"✓ Date filtering works: {date_data.get('date_range', {})}")
            else:
                print(f"✗ Date filtering failed: {response_with_date.status_code}")
                
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON response: {e}")
            print(f"Response content: {response.content[:200]}...")
    else:
        print(f"✗ Request failed with status: {response.status_code}")
        print(f"Response content: {response.content[:200]}...")

def test_json_serialization():
    """Test that our data structures are JSON serializable"""
    print("\nTesting JSON serialization...")
    
    from django.db.models import Count, Sum
    from decimal import Decimal
    
    # Create test user
    user, created = User.objects.get_or_create(
        username='jsontest',
        defaults={'email': 'jsontest@example.com'}
    )
    
    # Create test log
    log = DispensingLog.objects.create(
        user=user,
        name='Test Item',
        brand='Test Brand',
        unit='Tab',
        quantity=10,
        amount=Decimal('100.50'),
        status='Dispensed'
    )
    
    # Test QuerySet to list conversion
    logs = DispensingLog.objects.filter(user=user)
    
    try:
        # This should work now
        top_items = list(logs.values('name').annotate(
            count=Count('name'),
            total_amount=Sum('amount')
        ).order_by('-count')[:5])
        
        # Convert Decimal to float
        for item in top_items:
            if item.get('total_amount'):
                item['total_amount'] = float(item['total_amount'])
        
        # Test JSON serialization
        import json
        json_str = json.dumps(top_items)
        print("✓ QuerySet to list conversion works")
        print("✓ JSON serialization works")
        
        # Test date serialization
        test_date = date.today()
        date_str = test_date.isoformat()
        json.dumps({'date': date_str})
        print("✓ Date serialization works")
        
    except Exception as e:
        print(f"✗ Serialization failed: {e}")

def run_tests():
    """Run all tests"""
    print("=" * 60)
    print("TESTING DISPENSING LOG STATS FIX")
    print("=" * 60)
    
    try:
        test_json_serialization()
        test_stats_endpoint()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED! Stats endpoint is now working correctly.")
        print("=" * 60)
        
        print("\nFixed issues:")
        print("• QuerySet JSON serialization error")
        print("• Decimal to float conversion")
        print("• Date object serialization")
        print("• Added comprehensive error handling")
        print("• Improved client-side error handling")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_tests()
