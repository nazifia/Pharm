"""
User-specific cart utilities to ensure cart isolation between users.
"""

from django.db.models import Sum, Q
from .models import Cart
from userauth.session_utils import (
    get_user_customer_id, set_user_customer_id, clear_user_customer_id,
    get_user_payment_data, set_user_payment_data
)
import logging

logger = logging.getLogger(__name__)


def get_user_cart_items(user, cart_type='retail'):
    """
    Get cart items for a specific user.

    Args:
        user: The user object
        cart_type: 'retail' or 'wholesale'

    Returns:
        QuerySet: Cart items for the user
    """
    if cart_type == 'wholesale':
        # Import here to avoid circular imports
        from wholesale.models import WholesaleCart
        return WholesaleCart.objects.filter(user=user).select_related('item')
    else:
        return Cart.objects.filter(user=user).select_related('item')


def get_user_cart_summary(user, cart_type='retail'):
    """
    Get cart summary for a specific user.
    
    Args:
        user: The user object
        cart_type: 'retail' or 'wholesale'
        
    Returns:
        dict: Cart summary with totals
    """
    cart_items = get_user_cart_items(user, cart_type)
    
    total_price = 0
    total_discount = 0
    item_count = 0
    
    for cart_item in cart_items:
        total_price += cart_item.subtotal
        total_discount += getattr(cart_item, 'discount_amount', 0)
        item_count += cart_item.quantity
    
    final_total = total_price - total_discount
    
    return {
        'cart_items': cart_items,
        'total_price': total_price,
        'total_discount': total_discount,
        'final_total': final_total,
        'item_count': item_count,
        'cart_items_count': cart_items.count()
    }


def clear_user_cart(user, cart_type='retail'):
    """
    Clear all cart items for a specific user.
    
    Args:
        user: The user object
        cart_type: 'retail' or 'wholesale'
        
    Returns:
        int: Number of items cleared
    """
    try:
        if cart_type == 'wholesale':
            from wholesale.models import WholesaleCart
            cart_items = WholesaleCart.objects.filter(user=user)
        else:
            cart_items = Cart.objects.filter(user=user)

        count = cart_items.count()
        cart_items.delete()

        logger.info(f"Cleared {count} {cart_type} cart items for user {user.username}")
        return count

    except Exception as e:
        logger.error(f"Error clearing cart for user {user.username}: {e}")
        return 0


def add_item_to_user_cart(user, item, quantity, unit=None, cart_type='retail', price=None):
    """
    Add an item to a user's cart.
    
    Args:
        user: The user object
        item: The item to add
        quantity: Quantity to add
        unit: Unit type
        cart_type: 'retail' or 'wholesale'
        price: Override price (optional)
        
    Returns:
        tuple: (cart_item, created)
    """
    try:
        if cart_type == 'wholesale':
            from wholesale.models import WholesaleCart
            cart_item, created = WholesaleCart.objects.get_or_create(
                user=user,
                item=item,
                unit=unit,
                defaults={
                    'quantity': quantity,
                    'price': price or item.price
                }
            )
        else:
            cart_item, created = Cart.objects.get_or_create(
                user=user,
                item=item,
                unit=unit,
                defaults={
                    'quantity': quantity,
                    'price': price or item.price
                }
            )
        
        if not created:
            cart_item.quantity += quantity
        
        # Always update the price to match the current item price
        cart_item.price = price or item.price
        cart_item.save()
        
        logger.info(f"Added {quantity} of {item.name} to {user.username}'s {cart_type} cart")
        return cart_item, created
        
    except Exception as e:
        logger.error(f"Error adding item to cart for user {user.username}: {e}")
        return None, False


def remove_item_from_user_cart(user, item_id, cart_type='retail'):
    """
    Remove an item from a user's cart.
    
    Args:
        user: The user object
        item_id: ID of the cart item to remove
        cart_type: 'retail' or 'wholesale'
        
    Returns:
        bool: True if removed successfully
    """
    try:
        if cart_type == 'wholesale':
            from wholesale.models import WholesaleCart
            cart_item = WholesaleCart.objects.get(id=item_id, user=user)
        else:
            cart_item = Cart.objects.get(id=item_id, user=user)

        cart_item.delete()
        logger.info(f"Removed cart item {item_id} from {user.username}'s {cart_type} cart")
        return True

    except Exception as e:
        # Handle both Cart.DoesNotExist and WholesaleCart.DoesNotExist
        if 'DoesNotExist' in str(type(e)):
            logger.warning(f"Cart item {item_id} not found for user {user.username}")
            return False
        logger.error(f"Error removing cart item for user {user.username}: {e}")
        return False


def update_cart_item_quantity(user, item_id, quantity, cart_type='retail'):
    """
    Update the quantity of a cart item for a user.
    
    Args:
        user: The user object
        item_id: ID of the cart item
        quantity: New quantity
        cart_type: 'retail' or 'wholesale'
        
    Returns:
        bool: True if updated successfully
    """
    try:
        if cart_type == 'wholesale':
            from wholesale.models import WholesaleCart
            cart_item = WholesaleCart.objects.get(id=item_id, user=user)
        else:
            cart_item = Cart.objects.get(id=item_id, user=user)

        cart_item.quantity = quantity
        cart_item.save()

        logger.info(f"Updated cart item {item_id} quantity to {quantity} for user {user.username}")
        return True

    except Exception as e:
        # Handle both Cart.DoesNotExist and WholesaleCart.DoesNotExist
        if 'DoesNotExist' in str(type(e)):
            logger.warning(f"Cart item {item_id} not found for user {user.username}")
            return False
        logger.error(f"Error updating cart item for user {user.username}: {e}")
        return False


def get_user_cart_for_checkout(request, cart_type='retail'):
    """
    Get user's cart data prepared for checkout.
    
    Args:
        request: The request object
        cart_type: 'retail' or 'wholesale'
        
    Returns:
        dict: Cart data with customer and payment info
    """
    if not request.user.is_authenticated:
        return None
    
    cart_summary = get_user_cart_summary(request.user, cart_type)
    
    # Get customer from user-specific session
    customer_id = get_user_customer_id(request)
    customer = None
    if customer_id:
        try:
            from customer.models import Customer
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            # Clear invalid customer ID
            clear_user_customer_id(request)
    
    # Get payment data from user-specific session
    payment_data = get_user_payment_data(request)
    
    return {
        **cart_summary,
        'customer': customer,
        'customer_id': customer_id,
        'payment_method': payment_data.get('payment_method'),
        'payment_status': payment_data.get('payment_status'),
    }


def set_user_cart_customer(request, customer_id):
    """
    Set the customer for the user's cart session.
    
    Args:
        request: The request object
        customer_id: Customer ID to set
    """
    set_user_customer_id(request, customer_id)


def clear_user_cart_customer(request):
    """
    Clear the customer from the user's cart session.
    
    Args:
        request: The request object
    """
    clear_user_customer_id(request)


def set_user_cart_payment_info(request, payment_method=None, payment_status=None):
    """
    Set payment information for the user's cart session.
    
    Args:
        request: The request object
        payment_method: Payment method
        payment_status: Payment status
    """
    set_user_payment_data(request, payment_method=payment_method, payment_status=payment_status)


class UserCartManager:
    """
    Context manager for user-specific cart operations.
    """
    
    def __init__(self, user, cart_type='retail'):
        self.user = user
        self.cart_type = cart_type
    
    def get_items(self):
        """Get cart items for this user."""
        return get_user_cart_items(self.user, self.cart_type)
    
    def get_summary(self):
        """Get cart summary for this user."""
        return get_user_cart_summary(self.user, self.cart_type)
    
    def add_item(self, item, quantity, unit=None, price=None):
        """Add item to cart."""
        return add_item_to_user_cart(self.user, item, quantity, unit, self.cart_type, price)
    
    def remove_item(self, item_id):
        """Remove item from cart."""
        return remove_item_from_user_cart(self.user, item_id, self.cart_type)
    
    def update_quantity(self, item_id, quantity):
        """Update item quantity."""
        return update_cart_item_quantity(self.user, item_id, quantity, self.cart_type)
    
    def clear(self):
        """Clear all cart items."""
        return clear_user_cart(self.user, self.cart_type)


def get_user_cart_manager(user, cart_type='retail'):
    """
    Get a cart manager for a specific user.
    
    Args:
        user: The user object
        cart_type: 'retail' or 'wholesale'
        
    Returns:
        UserCartManager: A cart manager instance
    """
    return UserCartManager(user, cart_type)


# Example usage:
# 
# # Get user's cart items
# cart_items = get_user_cart_items(request.user)
# 
# # Get cart summary
# summary = get_user_cart_summary(request.user)
# 
# # Add item to cart
# add_item_to_user_cart(request.user, item, quantity=2)
# 
# # Using cart manager
# cart_manager = get_user_cart_manager(request.user)
# cart_manager.add_item(item, quantity=1)
# summary = cart_manager.get_summary()
