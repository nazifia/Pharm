#!/usr/bin/env python
"""
Test script to check if the dispensing log stats API is working correctly
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
import json

User = get_user_model()

def test_dispensing_stats_api():
    print("Testing Dispensing Log Stats API")
    print("=" * 40)
    
    # Create a test client
    client = Client()
    
    # Get a regular user to test with (not superuser)
    users = User.objects.all()
    if not users.exists():
        print("❌ No users found in database")
        return

    # Try to find a regular user (not superuser)
    regular_user = None
    for user in users:
        if not user.is_superuser and hasattr(user, 'profile') and user.profile:
            if user.profile.user_type in ['Pharmacist', 'Pharm-Tech', 'Salesperson']:
                regular_user = user
                break

    if regular_user:
        user = regular_user
        print(f"Testing with regular user: {user.username} ({user.profile.user_type})")
    else:
        user = users.first()
        print(f"Testing with user: {user.username} (no regular user found)")
    
    # Try to login the user
    client.force_login(user)
    print("✅ User logged in")
    
    # Test the stats API endpoint
    try:
        response = client.get(reverse('store:dispensing_log_stats'))
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("✅ API returned JSON data")
                print("Response data keys:", list(data.keys()))
                
                # Check if it's for regular or privileged user
                if 'context' in data and data['context'].get('user_restricted'):
                    print("👤 Regular user response")
                    print("Expected keys: total_items_dispensed, unique_items, daily_total_sales")
                    print("Full data:", data)  # Debug: show all data

                    if 'daily_total_sales' in data:
                        print(f"✅ daily_total_sales: {data['daily_total_sales']}")
                    else:
                        print("❌ daily_total_sales missing")

                else:
                    print("👑 Privileged user response")
                    print("Expected keys: total_items_dispensed, unique_items, monthly_total_sales")

                    if 'monthly_total_sales' in data:
                        print(f"✅ monthly_total_sales: {data['monthly_total_sales']}")
                    else:
                        print("❌ monthly_total_sales missing")
                
                # Check common fields
                common_fields = ['total_items_dispensed', 'unique_items', 'is_filtered']
                for field in common_fields:
                    if field in data:
                        print(f"✅ {field}: {data[field]}")
                    else:
                        print(f"❌ {field} missing")
                        
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON: {e}")
                print("Response content:", response.content[:200])
                
        else:
            print(f"❌ API returned status {response.status_code}")
            print("Response content:", response.content[:200])
            
    except Exception as e:
        print(f"❌ Error calling API: {e}")
    
    # Test with different user types
    print("\n" + "=" * 40)
    print("Testing with different user types:")
    
    for user in users[:3]:  # Test first 3 users
        try:
            client.force_login(user)
            response = client.get(reverse('store:dispensing_log_stats'))
            
            if response.status_code == 200:
                data = response.json()
                user_type = "Regular" if data.get('context', {}).get('user_restricted') else "Privileged"
                role = user.profile.user_type if hasattr(user, 'profile') and user.profile else "Unknown"
                print(f"User: {user.username} ({role}) -> {user_type}")
            else:
                print(f"User: {user.username} -> Error {response.status_code}")
                
        except Exception as e:
            print(f"User: {user.username} -> Exception: {e}")

if __name__ == "__main__":
    test_dispensing_stats_api()
