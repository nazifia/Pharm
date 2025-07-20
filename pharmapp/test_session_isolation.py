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


def test_cart_isolation():
    """Test that cart items are properly isolated between users."""
    print("\nTesting cart isolation...")

    try:
        from store.models import Cart, Item
        from store.cart_utils import get_user_cart_items, add_item_to_user_cart, clear_user_cart

        # Create test users
        user1, created = User.objects.get_or_create(
            username='cartuser1',
            defaults={'mobile': '1111111111'}
        )
        user2, created = User.objects.get_or_create(
            username='cartuser2',
            defaults={'mobile': '2222222222'}
        )

        # Clear any existing cart items for these users
        clear_user_cart(user1)
        clear_user_cart(user2)

        # Create a test item if it doesn't exist
        from decimal import Decimal
        test_item, created = Item.objects.get_or_create(
            name='Test Medicine',
            defaults={
                'price': Decimal('100.00'),
                'cost': Decimal('50.00'),
                'stock': 100,
                'unit': 'Tab'
            }
        )

        # Add items to each user's cart
        add_item_to_user_cart(user1, test_item, quantity=5, unit='Tab')
        add_item_to_user_cart(user2, test_item, quantity=3, unit='Tab')

        # Verify cart isolation
        user1_cart = get_user_cart_items(user1)
        user2_cart = get_user_cart_items(user2)

        user1_count = user1_cart.count()
        user2_count = user2_cart.count()

        if user1_count == 1 and user2_count == 1:
            user1_quantity = user1_cart.first().quantity
            user2_quantity = user2_cart.first().quantity

            if user1_quantity == 5 and user2_quantity == 3:
                print("✓ Cart isolation working correctly")
                print(f"  User 1 cart: {user1_count} items, quantity: {user1_quantity}")
                print(f"  User 2 cart: {user2_count} items, quantity: {user2_quantity}")
            else:
                print("✗ Cart quantities incorrect")
                print(f"  User 1 quantity: {user1_quantity} (expected 5)")
                print(f"  User 2 quantity: {user2_quantity} (expected 3)")
                return False
        else:
            print("✗ Cart isolation failed")
            print(f"  User 1 cart count: {user1_count}")
            print(f"  User 2 cart count: {user2_count}")
            return False

        # Test that users can't see each other's cart items
        all_cart_items = Cart.objects.all()
        user1_visible_items = Cart.objects.filter(user=user1)
        user2_visible_items = Cart.objects.filter(user=user2)

        if (user1_visible_items.count() == 1 and
            user2_visible_items.count() == 1 and
            all_cart_items.count() >= 2):
            print("✓ Cart access control working correctly")
        else:
            print("✗ Cart access control failed")
            return False

        # Clean up
        clear_user_cart(user1)
        clear_user_cart(user2)

        return True

    except Exception as e:
        print(f"✗ Cart isolation test failed with error: {e}")
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

def test_user_session_utilities():
    """Test user session utilities."""
    print("\nTesting user session utilities...")

    try:
        from userauth.session_utils import get_user_session_key, UserSessionManager
        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser

        # Create test users
        user1, created = User.objects.get_or_create(
            username='sessionuser1',
            defaults={'mobile': '3333333333'}
        )
        user2, created = User.objects.get_or_create(
            username='sessionuser2',
            defaults={'mobile': '4444444444'}
        )

        # Test session key generation
        key1 = get_user_session_key(user1, 'test_key')
        key2 = get_user_session_key(user2, 'test_key')

        if key1 != key2:
            print("✓ User session keys are properly isolated")
            print(f"  User 1 key: {key1}")
            print(f"  User 2 key: {key2}")
        else:
            print("✗ User session keys are not isolated")
            return False

        # Test session manager
        factory = RequestFactory()
        request = factory.get('/')
        request.user = user1
        request.session = {}

        session_manager = UserSessionManager(request)
        if session_manager:
            print("✓ User session manager created successfully")
        else:
            print("✗ User session manager creation failed")
            return False

        return True

    except Exception as e:
        print(f"✗ User session utilities test failed with error: {e}")
        return False

def main():
    """Run all tests."""
    print("Session Isolation Test Suite")
    print("=" * 40)
    
    tests = [
        test_cache_isolation,
        test_cart_isolation,
        test_session_configuration,
        test_middleware_loading,
        test_user_session_utilities,
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
