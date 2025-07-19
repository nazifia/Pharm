#!/usr/bin/env python3
"""
Test web access for activity logs
"""

import os
import sys
import django

# Setup Django first
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

# Now import Django components
from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from userauth.views import activity_dashboard

User = get_user_model()


def test_activity_dashboard_view():
    """Test the activity dashboard view directly"""
    print("=" * 60)
    print("TESTING ACTIVITY DASHBOARD VIEW DIRECTLY")
    print("=" * 60)
    
    try:
        # Get user ameer
        ameer = User.objects.get(username='ameer')
        print(f"✓ Testing with user: {ameer.username}")
        
        # Create a request factory
        factory = RequestFactory()
        request = factory.get('/activity/')
        
        # Add session middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # Add authentication middleware
        auth_middleware = AuthenticationMiddleware(lambda x: None)
        auth_middleware.process_request(request)
        
        # Set the user
        request.user = ameer
        
        # Test the permission check
        print(f"User has permission: {ameer.has_permission('view_activity_logs')}")
        
        # Call the view
        try:
            response = activity_dashboard(request)
            print(f"✓ View executed successfully")
            print(f"Response status: {response.status_code if hasattr(response, 'status_code') else 'No status code'}")
            
            if hasattr(response, 'content'):
                content_preview = str(response.content)[:200]
                print(f"Content preview: {content_preview}...")
            
            return True
            
        except Exception as e:
            print(f"❌ Error calling view: {str(e)}")
            return False
            
    except User.DoesNotExist:
        print("❌ User 'ameer' not found")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False


def test_url_resolution():
    """Test URL resolution"""
    print(f"\n🔗 Testing URL Resolution:")
    
    try:
        url = reverse('userauth:activity_dashboard')
        print(f"✓ Activity dashboard URL: {url}")
        return True
    except Exception as e:
        print(f"❌ URL resolution failed: {str(e)}")
        return False


def main():
    """Main function"""
    print("Testing Activity Log Access for User 'ameer'\n")
    
    url_ok = test_url_resolution()
    view_ok = test_activity_dashboard_view()
    
    print("\n" + "=" * 60)
    if url_ok and view_ok:
        print("✅ ALL TESTS PASSED!")
        print("User 'ameer' should be able to access activity logs.")
    else:
        print("❌ SOME TESTS FAILED!")
        print("There may be issues with the activity log access.")
    print("=" * 60)


if __name__ == '__main__':
    main()
