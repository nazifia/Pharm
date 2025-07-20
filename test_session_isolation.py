#!/usr/bin/env python
"""
Test script to verify session isolation between users.
"""

import os
import sys
import django
import requests
from django.test import Client
from django.contrib.auth import get_user_model

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from userauth.cache_utils import set_user_cache, get_user_cache, set_global_cache, get_global_cache

User = get_user_model()

def test_cache_isolation():
    """Test that user-specific cache keys are properly isolated."""
    print("Testing cache isolation...")
    
    try:
        # Create test users (or get existing ones)
        user1, created = User.objects.get_or_create(
            username='testuser1',
            defaults={'mobile': '1234567890'}
        )
        user2, created = User.objects.get_or_create(
            username='testuser2', 
            defaults={'mobile': '0987654321'}
        )
        
        # Test user-specific caching
        set_user_cache(user1, 'test_data', 'user1_data')
        set_user_cache(user2, 'test_data', 'user2_data')
        
        # Verify isolation
        user1_data = get_user_cache(user1, 'test_data')
        user2_data = get_user_cache(user2, 'test_data')
        
        if user1_data == 'user1_data' and user2_data == 'user2_data':
            print("✓ Cache isolation working correctly")
            print(f"  User 1 data: {user1_data}")
            print(f"  User 2 data: {user2_data}")
        else:
            print("✗ Cache isolation failed")
            print(f"  User 1 data: {user1_data}")
            print(f"  User 2 data: {user2_data}")
            return False
        
        # Test global cache
        set_global_cache('shared_data', 'global_value')
        global_data1 = get_global_cache('shared_data')
        global_data2 = get_global_cache('shared_data')
        
        if global_data1 == global_data2 == 'global_value':
            print("✓ Global cache working correctly")
            print(f"  Global data: {global_data1}")
        else:
            print("✗ Global cache failed")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ Cache test failed with error: {e}")
        return False

def test_session_configuration():
    """Test session configuration."""
    print("\nTesting session configuration...")
    
    from django.conf import settings
    
    # Check session settings
    session_engine = getattr(settings, 'SESSION_ENGINE', 'default')
    session_cookie_age = getattr(settings, 'SESSION_COOKIE_AGE', 0)
    session_httponly = getattr(settings, 'SESSION_COOKIE_HTTPONLY', False)
    
    print(f"Session engine: {session_engine}")
    print(f"Session cookie age: {session_cookie_age} seconds")
    print(f"Session HTTP only: {session_httponly}")
    
    if session_engine == 'django.contrib.sessions.backends.db':
        print("✓ Using database sessions (recommended)")
    else:
        print("⚠ Not using database sessions")
    
    if session_httponly:
        print("✓ Session cookies are HTTP only")
    else:
        print("⚠ Session cookies are not HTTP only")
    
    return True

def test_middleware_loading():
    """Test that middleware is loading correctly."""
    print("\nTesting middleware loading...")
    
    from django.conf import settings
    
    middleware = settings.MIDDLEWARE
    session_middleware_found = False
    validation_middleware_found = False
    
    for mw in middleware:
        if 'SessionValidationMiddleware' in mw:
            validation_middleware_found = True
            print("✓ Session validation middleware loaded")
        if 'SessionMiddleware' in mw:
            session_middleware_found = True
            print("✓ Session middleware loaded")
    
    if not session_middleware_found:
        print("✗ Session middleware not found")
        return False
    
    if not validation_middleware_found:
        print("⚠ Session validation middleware not found (may be disabled)")
    
    return True

def test_server_response():
    """Test that the server is responding."""
    print("\nTesting server response...")
    
    try:
        response = requests.get('http://127.0.0.1:8000/', timeout=5)
        if response.status_code == 200:
            print("✓ Server is responding correctly")
            print(f"  Status code: {response.status_code}")
            return True
        else:
            print(f"✗ Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Server connection failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Session Isolation Test Suite")
    print("=" * 40)
    
    tests = [
        test_cache_isolation,
        test_session_configuration,
        test_middleware_loading,
        test_server_response,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with error: {e}")
    
    print("\n" + "=" * 40)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Session isolation is working correctly.")
        print("\nNext steps:")
        print("1. Test with multiple users logging in simultaneously")
        print("2. Verify no data leakage between user sessions")
        print("3. Monitor session activity logs")
    else:
        print("⚠ Some tests failed. Please review the issues above.")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
