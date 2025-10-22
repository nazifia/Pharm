#!/usr/bin/env python
"""
Test script to verify date search functionality improvements
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.dateparse import parse_date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

def test_date_filtering():
    """Test the date filtering logic"""
    print("Testing date search functionality improvements...")
    
    # Test 1: Date parsing
    test_dates = ['2024-01-01', '2024-12-31', '', None]
    print("\n1. Testing date parsing:")
    for date_str in test_dates:
        try:
            if date_str:
                parsed = parse_date(date_str)
                print(f"   '{date_str}' -> {parsed}")
            else:
                print(f"   '{date_str}' -> None (empty string)")
        except (ValueError, TypeError) as e:
            print(f"   '{date_str}' -> Error: {e}")
    
    # Test 2: DateTime range creation
    print("\n2. Testing datetime range creation:")
    test_date = parse_date('2024-06-15')
    
    # Start of day
    start_datetime = timezone.make_aware(timezone.datetime.combine(test_date, timezone.datetime.min.time()))
    print(f"   Start datetime: {start_datetime}")
    
    # End of day
    end_datetime = timezone.make_aware(timezone.datetime.combine(test_date, timezone.datetime.max.time()))
    print(f"   End datetime: {end_datetime}")
    
    # Test 3: Check timezone awareness
    print("\n3. Testing timezone awareness:")
    print(f"   Start datetime is timezone aware: {timezone.is_aware(start_datetime)}")
    print(f"   End datetime is timezone aware: {timezone.is_aware(end_datetime)}")
    
    print("\nDate search functionality test completed!")

if __name__ == '__main__':
    test_date_filtering()
