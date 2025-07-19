#!/usr/bin/env python
"""
Debug script for API endpoint
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

def debug_api():
    """Debug the API endpoint"""
    print("🔍 Debugging API Endpoint...")
    
    try:
        # Test URL resolution
        print("Testing URL resolution...")
        
        # Get AMIR user
        user = User.objects.get(username='ameer')
        print(f"User ID: {user.id}")
        
        # Test URL reverse
        url = reverse('userauth:user_permissions_api', kwargs={'user_id': user.id})
        print(f"Resolved URL: {url}")
        
        # Test the view function directly
        from userauth.views import user_permissions_api
        print("View function imported successfully")
        
        # Create a mock request
        from django.http import HttpRequest
        request = HttpRequest()
        request.method = 'GET'
        request.user = User.objects.get(username='superuser')  # Admin user
        
        # Call the view function directly
        response = user_permissions_api(request, user.id)
        print(f"Direct view call status: {response.status_code}")
        print(f"Response content: {response.content.decode()[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    debug_api()
