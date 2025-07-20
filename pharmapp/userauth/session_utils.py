"""
User-specific session utilities to ensure session data isolation between users.
"""

import logging

logger = logging.getLogger(__name__)


def get_user_session_key(user, key):
    """
    Generate a user-specific session key to prevent data leakage.
    
    Args:
        user: The user object
        key: The session key
        
    Returns:
        str: A user-specific session key
    """
    return f"user_{user.id}_{key}"


def set_user_session_data(request, key, value):
    """
    Set user-specific session data.
    
    Args:
        request: The request object
        key: The session key
        value: The value to store
    """
    if not request.user.is_authenticated:
        return
    
    try:
        # Ensure user_data namespace exists
        if 'user_data' not in request.session:
            request.session['user_data'] = {}
        
        # Store data with user-specific key
        user_key = get_user_session_key(request.user, key)
        request.session['user_data'][user_key] = value
        request.session.modified = True
        
    except Exception as e:
        logger.error(f"Error setting user session data: {e}")


def get_user_session_data(request, key, default=None):
    """
    Get user-specific session data.
    
    Args:
        request: The request object
        key: The session key
        default: Default value if key doesn't exist
        
    Returns:
        The stored value or default
    """
    if not request.user.is_authenticated:
        return default
    
    try:
        user_data = request.session.get('user_data', {})
        user_key = get_user_session_key(request.user, key)
        return user_data.get(user_key, default)
        
    except Exception as e:
        logger.error(f"Error getting user session data: {e}")
        return default


def delete_user_session_data(request, key):
    """
    Delete user-specific session data.
    
    Args:
        request: The request object
        key: The session key
    """
    if not request.user.is_authenticated:
        return
    
    try:
        user_data = request.session.get('user_data', {})
        user_key = get_user_session_key(request.user, key)
        if user_key in user_data:
            del user_data[user_key]
            request.session['user_data'] = user_data
            request.session.modified = True
            
    except Exception as e:
        logger.error(f"Error deleting user session data: {e}")


def clear_user_session_data(request):
    """
    Clear all user-specific session data.
    
    Args:
        request: The request object
    """
    if not request.user.is_authenticated:
        return
    
    try:
        user_data = request.session.get('user_data', {})
        user_prefix = f"user_{request.user.id}_"
        
        # Remove all keys that belong to this user
        keys_to_remove = [key for key in user_data.keys() if key.startswith(user_prefix)]
        for key in keys_to_remove:
            del user_data[key]
        
        request.session['user_data'] = user_data
        request.session.modified = True
        
    except Exception as e:
        logger.error(f"Error clearing user session data: {e}")


def get_user_cart_session_data(request):
    """
    Get user-specific cart session data.
    
    Args:
        request: The request object
        
    Returns:
        dict: Cart session data for the user
    """
    return {
        'customer_id': get_user_session_data(request, 'customer_id'),
        'payment_method': get_user_session_data(request, 'payment_method'),
        'payment_status': get_user_session_data(request, 'payment_status'),
        'cart_type': get_user_session_data(request, 'cart_type', 'retail'),
    }


def set_user_cart_session_data(request, **kwargs):
    """
    Set user-specific cart session data.
    
    Args:
        request: The request object
        **kwargs: Cart data to store
    """
    for key, value in kwargs.items():
        set_user_session_data(request, key, value)


def get_user_customer_id(request):
    """
    Get the customer ID for the current user's session.
    
    Args:
        request: The request object
        
    Returns:
        int or None: Customer ID if set, None otherwise
    """
    return get_user_session_data(request, 'customer_id')


def set_user_customer_id(request, customer_id):
    """
    Set the customer ID for the current user's session.
    
    Args:
        request: The request object
        customer_id: The customer ID to store
    """
    set_user_session_data(request, 'customer_id', customer_id)


def clear_user_customer_id(request):
    """
    Clear the customer ID for the current user's session.
    
    Args:
        request: The request object
    """
    delete_user_session_data(request, 'customer_id')


def get_user_payment_data(request):
    """
    Get payment data for the current user's session.
    
    Args:
        request: The request object
        
    Returns:
        dict: Payment data
    """
    return {
        'payment_method': get_user_session_data(request, 'payment_method'),
        'payment_status': get_user_session_data(request, 'payment_status'),
    }


def set_user_payment_data(request, payment_method=None, payment_status=None):
    """
    Set payment data for the current user's session.
    
    Args:
        request: The request object
        payment_method: Payment method to store
        payment_status: Payment status to store
    """
    if payment_method is not None:
        set_user_session_data(request, 'payment_method', payment_method)
    if payment_status is not None:
        set_user_session_data(request, 'payment_status', payment_status)


class UserSessionManager:
    """
    Context manager for user-specific session operations.
    """
    
    def __init__(self, request):
        self.request = request
    
    def set(self, key, value):
        """Set user-specific session data."""
        return set_user_session_data(self.request, key, value)
    
    def get(self, key, default=None):
        """Get user-specific session data."""
        return get_user_session_data(self.request, key, default)
    
    def delete(self, key):
        """Delete user-specific session data."""
        return delete_user_session_data(self.request, key)
    
    def clear(self):
        """Clear all user-specific session data."""
        return clear_user_session_data(self.request)


def get_user_session_manager(request):
    """
    Get a session manager for the current user.
    
    Args:
        request: The request object
        
    Returns:
        UserSessionManager: A session manager instance
    """
    return UserSessionManager(request)


# Example usage:
# 
# # User-specific session data
# set_user_session_data(request, 'customer_id', customer.id)
# customer_id = get_user_session_data(request, 'customer_id')
# 
# # Cart-specific session data
# set_user_cart_session_data(request, customer_id=customer.id, payment_method='Cash')
# cart_data = get_user_cart_session_data(request)
# 
# # Using session manager
# session_manager = get_user_session_manager(request)
# session_manager.set('cart_items', cart_data)
# cart_data = session_manager.get('cart_items', [])
