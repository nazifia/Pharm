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


def get_customer_session_key(user, customer_id, key, customer_type='retail'):
    """
    Generate a customer-specific session key for isolated cart sessions.

    Args:
        user: The user object
        customer_id: The customer ID
        key: The session key
        customer_type: 'retail' or 'wholesale'

    Returns:
        str: A customer-specific session key
    """
    return f"user_{user.id}_{customer_type}_customer_{customer_id}_{key}"


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


def set_customer_session_data(request, customer_id, key, value, customer_type='retail'):
    """
    Set customer-specific session data for isolated cart sessions.

    Args:
        request: The request object
        customer_id: The customer ID
        key: The session key
        value: The value to store
        customer_type: 'retail' or 'wholesale'
    """
    if not request.user.is_authenticated:
        return

    try:
        # Ensure customer_data namespace exists
        if 'customer_data' not in request.session:
            request.session['customer_data'] = {}

        # Store data with customer-specific key
        customer_key = get_customer_session_key(request.user, customer_id, key, customer_type)
        request.session['customer_data'][customer_key] = value
        request.session.modified = True

    except Exception as e:
        logger.error(f"Error setting customer session data: {e}")


def get_customer_session_data(request, customer_id, key, default=None, customer_type='retail'):
    """
    Get customer-specific session data.

    Args:
        request: The request object
        customer_id: The customer ID
        key: The session key
        default: Default value if key doesn't exist
        customer_type: 'retail' or 'wholesale'

    Returns:
        The stored value or default
    """
    if not request.user.is_authenticated:
        return default

    try:
        customer_data = request.session.get('customer_data', {})
        customer_key = get_customer_session_key(request.user, customer_id, key, customer_type)
        return customer_data.get(customer_key, default)

    except Exception as e:
        logger.error(f"Error getting customer session data: {e}")
        return default


def delete_customer_session_data(request, customer_id, key, customer_type='retail'):
    """
    Delete customer-specific session data.

    Args:
        request: The request object
        customer_id: The customer ID
        key: The session key
        customer_type: 'retail' or 'wholesale'
    """
    if not request.user.is_authenticated:
        return

    try:
        customer_data = request.session.get('customer_data', {})
        customer_key = get_customer_session_key(request.user, customer_id, key, customer_type)
        if customer_key in customer_data:
            del customer_data[customer_key]
            request.session['customer_data'] = customer_data
            request.session.modified = True

    except Exception as e:
        logger.error(f"Error deleting customer session data: {e}")


def clear_customer_session_data(request, customer_id, customer_type='retail'):
    """
    Clear all session data for a specific customer.

    Args:
        request: The request object
        customer_id: The customer ID
        customer_type: 'retail' or 'wholesale'
    """
    if not request.user.is_authenticated:
        return

    try:
        customer_data = request.session.get('customer_data', {})
        customer_prefix = f"user_{request.user.id}_{customer_type}_customer_{customer_id}_"

        # Remove all keys that belong to this customer
        keys_to_remove = [key for key in customer_data.keys() if key.startswith(customer_prefix)]
        for key in keys_to_remove:
            del customer_data[key]

        request.session['customer_data'] = customer_data
        request.session.modified = True

    except Exception as e:
        logger.error(f"Error clearing customer session data: {e}")


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


def set_active_customer(request, customer_id, customer_type='retail'):
    """
    Set the active customer for the current session.

    Args:
        request: The request object
        customer_id: The customer ID
        customer_type: 'retail' or 'wholesale'
    """
    set_user_session_data(request, f'active_{customer_type}_customer', customer_id)


def get_active_customer(request, customer_type='retail'):
    """
    Get the active customer for the current session.

    Args:
        request: The request object
        customer_type: 'retail' or 'wholesale'

    Returns:
        The customer ID or None
    """
    return get_user_session_data(request, f'active_{customer_type}_customer')


def clear_active_customer(request, customer_type='retail'):
    """
    Clear the active customer for the current session.

    Args:
        request: The request object
        customer_type: 'retail' or 'wholesale'
    """
    delete_user_session_data(request, f'active_{customer_type}_customer')


def get_customer_cart_context(request, customer_id, customer_type='retail'):
    """
    Get all cart-related session data for a specific customer.

    Args:
        request: The request object
        customer_id: The customer ID
        customer_type: 'retail' or 'wholesale'

    Returns:
        dict: Customer's cart context data
    """
    return {
        'payment_method': get_customer_session_data(request, customer_id, 'payment_method', customer_type=customer_type),
        'payment_status': get_customer_session_data(request, customer_id, 'payment_status', customer_type=customer_type),
        'buyer_address': get_customer_session_data(request, customer_id, 'buyer_address', customer_type=customer_type),
        'total_price': get_customer_session_data(request, customer_id, 'total_price', customer_type=customer_type),
        'total_discount': get_customer_session_data(request, customer_id, 'total_discount', customer_type=customer_type),
    }


def set_customer_cart_context(request, customer_id, context_data, customer_type='retail'):
    """
    Set cart-related session data for a specific customer.

    Args:
        request: The request object
        customer_id: The customer ID
        context_data: dict of cart context data
        customer_type: 'retail' or 'wholesale'
    """
    for key, value in context_data.items():
        if value is not None:
            set_customer_session_data(request, customer_id, key, value, customer_type)


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
