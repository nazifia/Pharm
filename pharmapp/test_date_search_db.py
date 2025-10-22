#!/usr/bin/env python
"""
Test script to verify date search functionality with database queries
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

# Now import Django-dependent modules
from django.utils import timezone
from django.utils.dateparse import parse_date
from store.models import PaymentRequest

def test_database_date_filtering():
    """Test the date filtering with actual database queries"""
    print("Testing database date filtering...")
    
    # Get total count
    total_requests = PaymentRequest.objects.count()
    print(f"\nTotal payment requests in database: {total_requests}")
    
    if total_requests == 0:
        print("No payment requests found. Creating test data...")
        # Create a test payment request if none exist
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            test_user = User.objects.first()
            if test_user:
                PaymentRequest.objects.create(
                    request_id=f"TEST-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    dispenser=test_user,
                    total_amount=100.00,
                    payment_type='retail',
                    status='pending'
                )
                print("Test payment request created.")
                total_requests = PaymentRequest.objects.count()
            else:
                print("No users found in database.")
                return
        except Exception as e:
            print(f"Error creating test data: {e}")
            return
    
    # Test date range filtering
    print("\nTesting date range filtering:")
    
    # Get today's date
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    
    print(f"Today: {today}")
    print(f"Yesterday: {yesterday}")
    print(f"Tomorrow: {tomorrow}")
    
    # Test filtering by today
    start_datetime = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    end_datetime = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
    
    today_requests = PaymentRequest.objects.filter(
        created_at__gte=start_datetime,
        created_at__lte=end_datetime
    )
    
    print(f"\nRequests created today: {today_requests.count()}")
    
    # Test filtering by date range (last 7 days)
    week_ago = today - timedelta(days=7)
    week_start = timezone.make_aware(timezone.datetime.combine(week_ago, timezone.datetime.min.time()))
    week_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))
    
    week_requests = PaymentRequest.objects.filter(
        created_at__gte=week_start,
        created_at__lte=week_end
    )
    
    print(f"Requests created in last 7 days: {week_requests.count()}")
    
    # Show sample of filtered requests
    if week_requests.exists():
        print("\nSample requests from last 7 days:")
        for req in week_requests[:3]:
            print(f"  - {req.request_id}: {req.created_at} (Status: {req.status})")
    
    print("\nDatabase date filtering test completed!")

if __name__ == '__main__':
    test_database_date_filtering()
