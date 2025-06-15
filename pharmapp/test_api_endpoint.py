#!/usr/bin/env python
"""
Test script to verify the API endpoint works
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
from userauth.models import Profile

User = get_user_model()

def test_api_endpoint():
    """Test the API endpoint"""
    print("🧪 Testing API Endpoint")
    print("=" * 30)
    
    # Create a test client
    client = Client()
    
    # Get or create an admin user
    admin_user, created = User.objects.get_or_create(
        username='api_test_admin',
        defaults={
            'mobile': '9998887777',
            'email': 'api_admin@test.com',
            'is_active': True
        }
    )
    if created:
        admin_user.set_password('testpass123')
        admin_user.save()
        print(f"✅ Created admin user: {admin_user.username}")
    
    # Ensure admin has profile
    admin_profile, created = Profile.objects.get_or_create(
        user=admin_user,
        defaults={
            'full_name': 'API Test Admin',
            'user_type': 'Admin'
        }
    )
    
    # Get or create a test user
    test_user, created = User.objects.get_or_create(
        username='api_test_user',
        defaults={
            'mobile': '8887776666',
            'email': 'api_user@test.com',
            'is_active': True
        }
    )
    if created:
        test_user.set_password('testpass123')
        test_user.save()
        print(f"✅ Created test user: {test_user.username}")
    
    # Ensure test user has profile
    test_profile, created = Profile.objects.get_or_create(
        user=test_user,
        defaults={
            'full_name': 'API Test User',
            'user_type': 'Salesperson'
        }
    )
    
    # Login as admin
    login_success = client.login(username='api_test_admin', password='testpass123')
    print(f"Admin login successful: {login_success}")
    
    if not login_success:
        print("❌ Failed to login as admin")
        return
    
    # Test the API endpoint
    url = f'/api/user-permissions/{test_user.id}/'
    print(f"Testing URL: {url}")
    
    response = client.get(url)
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        import json
        data = json.loads(response.content)
        print(f"✅ API endpoint working!")
        print(f"Response data keys: {list(data.keys())}")
        if 'user' in data:
            print(f"User data: {data['user']}")
        if 'permissions' in data:
            print(f"Number of permissions: {len(data['permissions'])}")
    else:
        print(f"❌ API endpoint failed with status {response.status_code}")
        print(f"Response content: {response.content.decode()}")
    
    # Cleanup
    print("\n🧹 Cleaning up test data...")
    if created:
        admin_user.delete()
        test_user.delete()
        print("   Test users cleaned up")

if __name__ == '__main__':
    try:
        test_api_endpoint()
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
