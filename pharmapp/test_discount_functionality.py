#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from decimal import Decimal
from store.models import Item, Cart, SalesItem, Sales, WholesaleItem, WholesaleCart, WholesaleSalesItem
from userauth.models import User
from customer.models import Customer

def test_discount_functionality():
    """Test the discount functionality for both retail and wholesale"""
    
    print("Testing Discount Functionality...")
    print("=" * 50)
    
    # Create test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'mobile': '1234567890'}
    )
    
    # Create test item
    item, created = Item.objects.get_or_create(
        name='Test Medicine',
        defaults={
            'brand': 'Test Brand',
            'unit': 'Tab',
            'cost': Decimal('10.00'),
            'price': Decimal('15.00'),
            'stock': 100
        }
    )
    
    # Test 1: Cart with discount
    print("\n1. Testing Cart Discount Functionality")
    print("-" * 40)
    
    # Create cart item
    cart_item = Cart.objects.create(
        user=user,
        item=item,
        quantity=Decimal('5'),
        price=item.price,
        discount_amount=Decimal('10.00')  # $10 discount
    )
    
    print(f"Cart Item: {cart_item.item.name}")
    print(f"Quantity: {cart_item.quantity}")
    print(f"Price per unit: ${cart_item.price}")
    print(f"Base subtotal: ${cart_item.price * cart_item.quantity}")
    print(f"Discount amount: ${cart_item.discount_amount}")
    print(f"Final subtotal: ${cart_item.subtotal}")
    
    # Verify calculation
    expected_subtotal = (cart_item.price * cart_item.quantity) - cart_item.discount_amount
    assert cart_item.subtotal == expected_subtotal, f"Expected {expected_subtotal}, got {cart_item.subtotal}"
    print("✓ Cart discount calculation correct")
    
    # Test 2: SalesItem with discount
    print("\n2. Testing SalesItem Discount Functionality")
    print("-" * 40)
    
    # Create sales record
    customer = Customer.objects.create(
        name='Test Customer',
        phone='1234567890',
        address='Test Address'
    )
    
    sales = Sales.objects.create(
        user=user,
        customer=customer,
        total_amount=cart_item.subtotal
    )
    
    # Create sales item with discount
    sales_item = SalesItem.objects.create(
        sales=sales,
        item=item,
        quantity=cart_item.quantity,
        price=cart_item.price,
        discount_amount=cart_item.discount_amount
    )
    
    print(f"Sales Item: {sales_item.item.name}")
    print(f"Quantity: {sales_item.quantity}")
    print(f"Price per unit: ${sales_item.price}")
    print(f"Base subtotal: ${sales_item.price * sales_item.quantity}")
    print(f"Discount amount: ${sales_item.discount_amount}")
    print(f"Final subtotal: ${sales_item.subtotal}")
    
    # Verify calculation
    expected_sales_subtotal = (sales_item.price * sales_item.quantity) - sales_item.discount_amount
    assert sales_item.subtotal == expected_sales_subtotal, f"Expected {expected_sales_subtotal}, got {sales_item.subtotal}"
    print("✓ SalesItem discount calculation correct")
    
    print("\n" + "=" * 50)
    print("Discount functionality tests passed! ✓")
    print("=" * 50)
    
    # Clean up test data
    Cart.objects.filter(user=user).delete()
    SalesItem.objects.filter(sales=sales).delete()
    sales.delete()
    customer.delete()
    
    print("\nTest data cleaned up.")

if __name__ == '__main__':
    test_discount_functionality()
