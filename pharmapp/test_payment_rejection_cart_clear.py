#!/usr/bin/env python3
"""
Test script to verify that payment request rejection clears the cart.
Run this script in the Django context using: python manage.py shell < test_payment_rejection_cart_clear.py
"""

import os
import sys
import django
from decimal import Decimal

# Add project root to path
sys.path.append('/path/to/your/project')  # Update with actual path

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.contrib.auth.models import User
from store.models import Cart, WholesaleCart, PaymentRequest, Item, WholesaleItem
from customer.models import Customer, WholesaleCustomer
from django.test import RequestFactory
from store.views import reject_payment_request
from wholesale.views import reject_wholesale_payment_request


def test_retail_payment_rejection_cart_clear():
    """Test that retail payment request rejection clears the cart"""
    print("\n=== Testing Retail Payment Request Rejection ===")
    
    try:
        # Create a test user (dispenser)
        test_user, created = User.objects.get_or_create(
            username='test_dispenser',
            defaults={'email': 'test@example.com'}
        )
        if created:
            test_user.set_password('testpass123')
            test_user.save()
        
        # Create test item
        test_item, created = Item.objects.get_or_create(
            name='Test Medicine',
            defaults={
                'brand': 'Test Brand',
                'stock': 100,
                'price': Decimal('10.00'),
                'cost': Decimal('5.00')
            }
        )
        
        # Create cart items for the test user
        cart_items_to_clear = []
        for i in range(3):
            cart_item, created = Cart.objects.get_or_create(
                user=test_user,
                item=test_item,
                defaults={
                    'quantity': 2,
                    'price': test_item.price,
                    'unit': 'pcs'
                }
            )
            cart_items_to_clear.append(cart_item)
        
        initial_cart_count = Cart.objects.filter(user=test_user).count()
        print(f"Initial cart count for user {test_user.username}: {initial_cart_count}")
        
        # Create a payment request
        from store.models import PaymentRequest, PaymentRequestItem
        
        payment_request = PaymentRequest.objects.create(
            dispenser=test_user,
            payment_type='retail',
            total_amount=Decimal('60.00'),
            status='pending'
        )
        
        # Create payment request items
        for cart_item in cart_items_to_clear:
            PaymentRequestItem.objects.create(
                payment_request=payment_request,
                item_name=cart_item.item.name,
                brand=cart_item.brand,
                dosage_form='',  # Simplified for test
                unit=cart_item.unit,
                quantity=cart_item.quantity,
                unit_price=cart_item.price,
                discount_amount=Decimal('0.00'),
                subtotal=cart_item.subtotal,
                retail_item=cart_item.item
            )
        
        # Create a request factory and simulate request
        factory = RequestFactory()
        request = factory.post(f'/reject_payment_request/{payment_request.request_id}/')
        request.user = test_user
        
        # Call the reject function
        response = reject_payment_request(request, payment_request.request_id)
        
        # Check if cart was cleared
        final_cart_count = Cart.objects.filter(user=test_user).count()
        print(f"Final cart count after rejection: {final_cart_count}")
        
        if final_cart_count == 0:
            print("✅ SUCCESS: Retail cart was cleared after payment request rejection")
            return True
        else:
            print("❌ FAILURE: Retail cart was not cleared after payment request rejection")
            return False
            
    except Exception as e:
        print(f"❌ ERROR in retail test: {e}")
        return False
    
    finally:
        # Cleanup
        try:
            Cart.objects.filter(user=test_user).delete()
            payment_request.delete()
            print("🧹 Cleanup completed for retail test")
        except:
            pass


def test_wholesale_payment_rejection_cart_clear():
    """Test that wholesale payment request rejection clears the cart"""
    print("\n=== Testing Wholesale Payment Request Rejection ===")
    
    try:
        # Create a test user (dispenser)
        test_user, created = User.objects.get_or_create(
            username='test_wholesale_dispenser',
            defaults={'email': 'wholesale@example.com'}
        )
        if created:
            test_user.set_password('testpass123')
            test_user.save()
        
        # Create wholesale test item
        test_item, created = WholesaleItem.objects.get_or_create(
            name='Test Wholesale Medicine',
            defaults={
                'brand': 'Test Wholesale Brand',
                'stock': 100,
                'price': Decimal('50.00'),
                'cost': Decimal('25.00'),
                'unit': 'box'
            }
        )
        
        # Create wholesale cart items for the test user
        cart_items_to_clear = []
        for i in range(2):
            cart_item, created = WholesaleCart.objects.get_or_create(
                user=test_user,
                item=test_item,
                defaults={
                    'quantity': Decimal('5.0'),
                    'price': test_item.price
                }
            )
            cart_items_to_clear.append(cart_item)
        
        initial_cart_count = WholesaleCart.objects.filter(user=test_user).count()
        print(f"Initial wholesale cart count for user {test_user.username}: {initial_cart_count}")
        
        # Create a wholesale payment request
        from store.models import PaymentRequest, PaymentRequestItem
        
        payment_request = PaymentRequest.objects.create(
            dispenser=test_user,
            payment_type='wholesale',
            total_amount=Decimal('500.00'),
            status='pending'
        )
        
        # Create payment request items
        for cart_item in cart_items_to_clear:
            PaymentRequestItem.objects.create(
                payment_request=payment_request,
                item_name=cart_item.item.name,
                brand=cart_item.brand,
                dosage_form='',  # Simplified for test
                unit=cart_item.unit,
                quantity=cart_item.quantity,
                unit_price=cart_item.price,
                discount_amount=Decimal('0.00'),
                subtotal=cart_item.subtotal,
                wholesale_item=cart_item.item
            )
        
        # Create a request factory and simulate request
        factory = RequestFactory()
        request = factory.post(f'/reject_wholesale_payment_request/{payment_request.request_id}/')
        request.user = test_user
        
        # Call the reject function
        response = reject_wholesale_payment_request(request, payment_request.request_id)
        
        # Check if wholesale cart was cleared
        final_cart_count = WholesaleCart.objects.filter(user=test_user).count()
        print(f"Final wholesale cart count after rejection: {final_cart_count}")
        
        if final_cart_count == 0:
            print("✅ SUCCESS: Wholesale cart was cleared after payment request rejection")
            return True
        else:
            print("❌ FAILURE: Wholesale cart was not cleared after payment request rejection")
            return False
            
    except Exception as e:
        print(f"❌ ERROR in wholesale test: {e}")
        return False
    
    finally:
        # Cleanup
        try:
            WholesaleCart.objects.filter(user=test_user).delete()
            payment_request.delete()
            print("🧹 Cleanup completed for wholesale test")
        except:
            pass


def main():
    """Run both tests"""
    print("🧪 Testing Payment Request Rejection with Cart Clearing\n")
    
    retail_success = test_retail_payment_rejection_cart_clear()
    wholesale_success = test_wholesale_payment_rejection_cart_clear()
    
    print(f"\n{'='*50}")
    print("SUMMARY:")
    print(f"Retail test: {'✅ PASSED' if retail_success else '❌ FAILED'}")
    print(f"Wholesale test: {'✅ PASSED' if wholesale_success else '❌ FAILED'}")
    
    if retail_success and wholesale_success:
        print("🎉 All tests passed! Payment request rejection now properly clears carts.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
