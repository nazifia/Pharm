"""
Cache utilities for user-specific caching to ensure session isolation.
"""

from django.core.cache import cache
from django.contrib.auth import get_user_model
import hashlib

User = get_user_model()


def get_user_cache_key(user, key_suffix):
    """
    Generate a user-specific cache key to prevent data leakage between users.
    
    Args:
        user: The user object or user ID
        key_suffix: The specific cache key suffix
        
    Returns:
        str: A unique cache key for the user
    """
    if hasattr(user, 'id'):
        user_id = user.id
    else:
        user_id = user
    
    # Create a hash to ensure consistent key length and avoid special characters
    user_hash = hashlib.md5(f"user_{user_id}".encode()).hexdigest()[:8]
    return f"user_{user_hash}_{key_suffix}"


def set_user_cache(user, key_suffix, value, timeout=None):
    """
    Set a cache value for a specific user.
    
    Args:
        user: The user object or user ID
        key_suffix: The specific cache key suffix
        value: The value to cache
        timeout: Cache timeout in seconds (None for default)
    """
    cache_key = get_user_cache_key(user, key_suffix)
    cache.set(cache_key, value, timeout)


def get_user_cache(user, key_suffix, default=None):
    """
    Get a cache value for a specific user.
    
    Args:
        user: The user object or user ID
        key_suffix: The specific cache key suffix
        default: Default value if key doesn't exist
        
    Returns:
        The cached value or default
    """
    cache_key = get_user_cache_key(user, key_suffix)
    return cache.get(cache_key, default)


def delete_user_cache(user, key_suffix):
    """
    Delete a cache value for a specific user.
    
    Args:
        user: The user object or user ID
        key_suffix: The specific cache key suffix
    """
    cache_key = get_user_cache_key(user, key_suffix)
    cache.delete(cache_key)


def clear_user_cache(user):
    """
    Clear all cache entries for a specific user.
    Note: This is a best-effort operation and may not clear all entries
    depending on the cache backend.
    
    Args:
        user: The user object or user ID
    """
    if hasattr(user, 'id'):
        user_id = user.id
    else:
        user_id = user
    
    user_hash = hashlib.md5(f"user_{user_id}".encode()).hexdigest()[:8]
    pattern = f"user_{user_hash}_*"
    
    # Note: This pattern-based deletion works with some cache backends
    # For production, consider using Redis with pattern deletion support
    try:
        # Try to get all keys (works with some backends)
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern(pattern)
        else:
            # Fallback: manually track and delete known keys
            # This would require maintaining a list of user cache keys
            pass
    except AttributeError:
        # Cache backend doesn't support pattern deletion
        pass


def set_global_cache(key, value, timeout=None):
    """
    Set a global cache value (not user-specific).
    Use this for data that should be shared across all users.
    
    Args:
        key: The cache key
        value: The value to cache
        timeout: Cache timeout in seconds (None for default)
    """
    global_key = f"global_{key}"
    cache.set(global_key, value, timeout)


def get_global_cache(key, default=None):
    """
    Get a global cache value (not user-specific).
    
    Args:
        key: The cache key
        default: Default value if key doesn't exist
        
    Returns:
        The cached value or default
    """
    global_key = f"global_{key}"
    return cache.get(global_key, default)


def delete_global_cache(key):
    """
    Delete a global cache value.
    
    Args:
        key: The cache key
    """
    global_key = f"global_{key}"
    cache.delete(global_key)


class UserCacheManager:
    """
    Context manager for user-specific caching operations.
    """
    
    def __init__(self, user):
        self.user = user
    
    def set(self, key, value, timeout=None):
        """Set a user-specific cache value."""
        return set_user_cache(self.user, key, value, timeout)
    
    def get(self, key, default=None):
        """Get a user-specific cache value."""
        return get_user_cache(self.user, key, default)
    
    def delete(self, key):
        """Delete a user-specific cache value."""
        return delete_user_cache(self.user, key)
    
    def clear(self):
        """Clear all cache entries for this user."""
        return clear_user_cache(self.user)


def get_user_cache_manager(user):
    """
    Get a cache manager for a specific user.
    
    Args:
        user: The user object or user ID
        
    Returns:
        UserCacheManager: A cache manager instance for the user
    """
    return UserCacheManager(user)


# Example usage:
# 
# # User-specific caching
# set_user_cache(request.user, 'preferences', user_preferences)
# preferences = get_user_cache(request.user, 'preferences', {})
# 
# # Global caching
# set_global_cache('marquee_text', 'Welcome to our pharmacy!')
# marquee = get_global_cache('marquee_text', 'Default message')
# 
# # Using cache manager
# user_cache = get_user_cache_manager(request.user)
# user_cache.set('cart_items', cart_data)
# cart_data = user_cache.get('cart_items', [])
