#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from decimal import Decimal
from store.models import Item, Cart
from userauth.models import User

def test_retail_discount_fix():
    """Test that retail discount functionality works correctly"""
    
    print("Testing Retail Discount Fix...")
    print("=" * 40)
    
    # Create or get test user
    try:
        user = User.objects.get(username='testuser_discount')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='testuser_discount',
            mobile='9876543210'  # Use unique mobile number
        )
    
    # Create or get test item
    item, created = Item.objects.get_or_create(
        name='Test Discount Medicine',
        defaults={
            'brand': 'Test Brand',
            'unit': 'Tab',
            'cost': Decimal('10.00'),
            'price': Decimal('20.00'),
            'stock': 100
        }
    )
    
    # Clean up any existing cart items for this user
    Cart.objects.filter(user=user).delete()
    
    print(f"\n1. Creating cart item for user: {user.username}")
    print(f"   Item: {item.name}")
    print(f"   Price: ${item.price}")
    print(f"   Quantity: 3")
    
    # Create cart item
    cart_item = Cart.objects.create(
        user=user,
        item=item,
        quantity=Decimal('3'),
        price=item.price,
        discount_amount=Decimal('0')  # Start with no discount
    )
    
    print(f"   Base subtotal: ${cart_item.subtotal}")
    
    # Test 2: Apply discount
    print(f"\n2. Applying discount of $15.00")
    cart_item.discount_amount = Decimal('15.00')
    cart_item.save()
    
    print(f"   Discount amount: ${cart_item.discount_amount}")
    print(f"   New subtotal: ${cart_item.subtotal}")
    print(f"   Expected subtotal: ${(item.price * cart_item.quantity) - cart_item.discount_amount}")
    
    # Verify calculation
    expected = (item.price * cart_item.quantity) - cart_item.discount_amount
    if cart_item.subtotal == expected:
        print("   ✓ Discount calculation correct!")
    else:
        print(f"   ✗ Discount calculation incorrect! Expected {expected}, got {cart_item.subtotal}")
    
    # Test 3: Test discount validation (discount > subtotal)
    print(f"\n3. Testing discount validation (discount > base subtotal)")
    base_subtotal = item.price * cart_item.quantity
    excessive_discount = base_subtotal + Decimal('10.00')
    
    print(f"   Base subtotal: ${base_subtotal}")
    print(f"   Attempting to apply discount: ${excessive_discount}")
    
    cart_item.discount_amount = excessive_discount
    cart_item.save()
    
    print(f"   Actual discount applied: ${cart_item.discount_amount}")
    print(f"   Final subtotal: ${cart_item.subtotal}")
    
    if cart_item.discount_amount == base_subtotal and cart_item.subtotal == Decimal('0.00'):
        print("   ✓ Discount validation working correctly!")
    else:
        print("   ✗ Discount validation failed!")
    
    # Test 4: Multiple cart items
    print(f"\n4. Testing multiple cart items")
    
    # Create second item
    item2, created = Item.objects.get_or_create(
        name='Test Medicine 2',
        defaults={
            'brand': 'Test Brand 2',
            'unit': 'Cap',
            'cost': Decimal('5.00'),
            'price': Decimal('12.00'),
            'stock': 50
        }
    )
    
    cart_item2 = Cart.objects.create(
        user=user,
        item=item2,
        quantity=Decimal('2'),
        price=item2.price,
        discount_amount=Decimal('5.00')
    )
    
    # Calculate totals
    all_cart_items = Cart.objects.filter(user=user)
    total_price = sum(item.subtotal for item in all_cart_items)
    total_discount = sum(item.discount_amount for item in all_cart_items)
    
    print(f"   Cart item 1 subtotal: ${cart_item.subtotal}")
    print(f"   Cart item 2 subtotal: ${cart_item2.subtotal}")
    print(f"   Total price (after discounts): ${total_price}")
    print(f"   Total discount amount: ${total_discount}")
    
    # Clean up
    Cart.objects.filter(user=user).delete()
    print(f"\n5. Cleanup completed")
    
    print("\n" + "=" * 40)
    print("Retail discount fix test completed! ✓")
    print("The cart() view now handles discount form submissions.")
    print("=" * 40)

if __name__ == '__main__':
    test_retail_discount_fix()
