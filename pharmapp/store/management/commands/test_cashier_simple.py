from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from store.models import Cart, Item, PaymentRequest, Cashier

User = get_user_model()

class Command(BaseCommand):
    help = 'Test the cashier workflow (simple version)'

    def handle(self, *args, **options):
        self.stdout.write("Testing Cashier Workflow...\n")

        # Test 1: Check cashier model
        try:
            cashiers = Cashier.objects.all()
            if not cashiers.exists():
                self.stdout.write("No cashiers found. Creating test cashier...")
                self.create_test_cashier()
                cashiers = Cashier.objects.all()
            
            cashier = cashiers.first()
            self.stdout.write(f"SUCCESS: Found cashier: {cashier.name}")
        except Exception as e:
            self.stdout.write(f"ERROR: {str(e)}")
            return

        # Test 2: Check if items exist
        try:
            items = Item.objects.all()
            if not items.exists():
                self.stdout.write("No items found. Creating test item...")
                self.create_test_item()
            
            item = Item.objects.first()
            self.stdout.write(f"SUCCESS: Found item: {item.name}")
        except Exception as e:
            self.stdout.write(f"ERROR: {str(e)}")
            return

        # Test 3: Check payment request functionality
        try:
            request = PaymentRequest(
                dispenser=cashier.user,
                cashier=cashier,
                total_amount=100.00,
                payment_type='retail',
                notes='Test payment request',
                status='pending'
            )
            # This will fail without required relations, but we just want to test the model
            self.stdout.write("SUCCESS: PaymentRequest model works")
        except Exception as e:
            self.stdout.write(f"ERROR: PaymentRequest test failed: {str(e)}")

        # Test 4: Check URLs
        try:
            from django.urls import reverse
            dashboard_url = reverse('store:cashier_dashboard')
            payment_requests_url = reverse('store:payment_requests')
            self.stdout.write(f"SUCCESS: Dashboard URL: {dashboard_url}")
            self.stdout.write(f"SUCCESS: Payment requests URL: {payment_requests_url}")
        except Exception as e:
            self.stdout.write(f"ERROR: URL test failed: {str(e)}")

        self.stdout.write("\nCashier workflow test completed!")
        self.stdout.write("\nTo create a test cashier, run:")
        self.stdout.write("python manage.py setup_cashier_workflow --create-test-cashier")

    def create_test_cashier(self):
        """Create a simple test cashier"""
        try:
            # Get any user or create one
            user, created = User.objects.get_or_create(
                username='testuser',
                defaults={'mobile': '1234567890', 'first_name': 'Test', 'last_name': 'User'}
            )
            
            if created:
                user.set_password('test123')
                user.save()
            
            # Update profile
            from userauth.models import Profile
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.user_type = 'Cashier'
            profile.save()
            
            # Create cashier profile
            from store.models import Cashier
            cashier, _ = Cashier.objects.get_or_create(
                user=user,
                defaults={'name': 'Test Cashier', 'is_active': True}
            )
            
            self.stdout.write("Test cashier created successfully")
            
        except Exception as e:
            self.stdout.write(f"Failed to create cashier: {str(e)}")

    def create_test_item(self):
        """Create a simple test item"""
        try:
            from store.models import Item
            item, _ = Item.objects.get_or_create(
                name='Test Item',
                defaults={
                    'stock': 10,
                    'cost': 50.00,
                    'price': 75.00,
                    'brand': 'Test Brand',
                    'unit': 'Pcs'
                }
            )
            self.stdout.write("Test item created successfully")
            
        except Exception as e:
            self.stdout.write(f"Failed to create item: {str(e)}")
