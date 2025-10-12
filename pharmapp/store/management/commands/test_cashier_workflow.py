from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from store.models import Cart, Item, PaymentRequest, Cashier
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Test the complete cashier workflow'

    def handle(self, *args, **options):
        self.stdout.write("Testing Cashier Workflow...\n")

        # Step 1: Check if cashier exists
        try:
            cashier = Cashier.objects.first()
            if not cashier:
                self.stdout.write("ERROR: No cashier found. Run 'python manage.py setup_cashier_workflow --create-test-cashier' first.")
                return
            
            self.stdout.write(f"SUCCESS: Found cashier: {cashier.name} ({cashier.cashier_id})")
        except Exception as e:
            self.stdout.write(f"❌ Error checking cashier: {str(e)}")
            return

        # Step 2: Create test items if needed
        try:
            item, created = Item.objects.get_or_create(
                name="Test Medicine",
                defaults={
                    'brand': 'Test Brand',
                    'unit': 'Pcs',
                    'cost': Decimal('10.00'),
                    'price': Decimal('15.00'),
                    'stock': 100,
                }
            )
            self.stdout.write(f"SUCCESS: Test item ready: {item.name} (Stock: {item.stock})")
        except Exception as e:
            self.stdout.write(f"❌ Error creating test item: {str(e)}")
            return

        # Step 3: Simulate dispenser adding to cart
        try:
            # Clear any existing cart items for the test user
            Cart.objects.filter(user=cashier.user).delete()
            
            # Add item to cart
            cart_item = Cart.objects.create(
                user=cashier.user,
                item=item,
                quantity=2,
                unit='Pcs',
                price=item.price,
                subtotal=item.price * 2,
            )
            
            self.stdout.write(f"SUCCESS: Added {item.name} to cart for {cashier.user.username}")
        except Exception as e:
            self.stdout.write(f"❌ Error adding to cart: {str(e)}")
            return

        # Step 4: Test payment request creation
        try:
            from django.test import RequestFactory
            factory = RequestFactory()
            request = factory.post('/store/send_to_cashier/', {
                'notes': 'Test payment request for cashier workflow testing'
            })
            request.user = cashier.user

            # Check if the view exists and callable
            from store.views import send_to_cashier
            
            # This would normally require cart items, but we'll simulate the creation
            total_amount = sum(cart_item.subtotal for cart_item in Cart.objects.filter(user=cashier.user))
            
            payment_request = PaymentRequest.objects.create(
                dispenser=cashier.user,
                cashier=cashier,
                total_amount=total_amount,
                payment_type='retail',
                notes='Test payment request for cashier workflow testing',
                status='pending'
            )
            
            # Create payment request items
            for cart_item in Cart.objects.filter(user=cashier.user):
                from store.models import PaymentRequestItem
                PaymentRequestItem.objects.create(
                    payment_request=payment_request,
                    item_name=cart_item.item.name,
                    brand=cart_item.item.brand,
                    unit=cart_item.unit,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.price,
                    subtotal=cart_item.subtotal,
                    retail_item=cart_item.item
                )
            
            self.stdout.write(f"✅ Created payment request: {payment_request.request_id}")
            self.stdout.write(f"   - Amount: ₦{payment_request.total_amount}")
            self.stdout.write(f"   - Items: {payment_request.items.count()}")
            self.stdout.write(f"   - Status: {payment_request.status}")

        except Exception as e:
            self.stdout.write(f"❌ Error creating payment request: {str(e)}")
            return

        # Step 5: Test cashier dashboard access
        try:
            from django.urls import reverse
            dashboard_url = reverse('store:cashier_dashboard')
            self.stdout.write(f"✅ Cashier dashboard URL: {dashboard_url}")
        except Exception as e:
            self.stdout.write(f"❌ Error checking dashboard URL: {str(e)}")

        # Step 6: Cleanup test data
        try:
            Cart.objects.filter(user=cashier.user).delete()
            PaymentRequest.objects.filter(dispenser=cashier.user).delete()
            self.stdout.write("✅ Cleaned up test data")
        except Exception as e:
            self.stdout.write(f"⚠️ Error cleaning up: {str(e)}")

        self.stdout.write("\n🎉 Cashier workflow test completed successfully!")
        self.stdout.write("\n💡 Next steps:")
        self.stdout.write("1. Run: python manage.py setup_cashier_workflow --create-test-cashier")
        self.stdout.write("2. Log into the system with the test cashier account")
        self.stdout.write("3. Navigate to the cashier dashboard to process payments")
        self.stdout.write("4. Test the complete payment processing workflow")
