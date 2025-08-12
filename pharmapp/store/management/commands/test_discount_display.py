from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from store.models import DispensingLog, Item, Cart
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Test discount display in dispensing log'

    def handle(self, *args, **options):
        self.stdout.write("Testing discount display in dispensing log...")
        
        # Get a user
        user = User.objects.first()
        if not user:
            self.stdout.write("✗ No users found")
            return
        
        # Get an item
        item = Item.objects.first()
        if not item:
            self.stdout.write("✗ No items found")
            return
        
        self.stdout.write(f"✓ Using user: {user.username}")
        self.stdout.write(f"✓ Using item: {item.name} (Price: ₦{item.price})")
        
        # Create a test dispensing log entry with discount
        test_log = DispensingLog.objects.create(
            user=user,
            name=item.name,
            brand=item.brand,
            unit=item.unit,
            quantity=Decimal('2.00'),
            amount=Decimal('180.00'),  # Discounted amount (₦100 * 2 - ₦20 discount)
            discount_amount=Decimal('20.00'),  # ₦20 discount
            status='Dispensed'
        )
        
        self.stdout.write(f"✓ Created test dispensing log entry:")
        self.stdout.write(f"  - Quantity: {test_log.quantity}")
        self.stdout.write(f"  - Amount (discounted): ₦{test_log.amount}")
        self.stdout.write(f"  - Discount Amount: ₦{test_log.discount_amount}")
        self.stdout.write(f"  - Original Amount: ₦{test_log.original_amount}")
        self.stdout.write(f"  - Rate per unit (discounted): ₦{test_log.rate_per_unit}")
        self.stdout.write(f"  - Original rate per unit: ₦{test_log.original_rate_per_unit}")
        
        # Test the properties
        expected_original = test_log.amount + test_log.discount_amount
        expected_rate = test_log.amount / test_log.quantity
        expected_original_rate = expected_original / test_log.quantity
        
        self.stdout.write(f"\n✓ Property calculations:")
        self.stdout.write(f"  - Original amount calculation: ₦{expected_original}")
        self.stdout.write(f"  - Rate per unit calculation: ₦{expected_rate}")
        self.stdout.write(f"  - Original rate calculation: ₦{expected_original_rate}")
        
        # Clean up
        test_log.delete()
        self.stdout.write(f"\n✓ Test entry cleaned up")
        
        # Check recent dispensing logs for discount data
        recent_logs = DispensingLog.objects.filter(discount_amount__gt=0).order_by('-created_at')[:5]
        
        if recent_logs.exists():
            self.stdout.write(f"\n✓ Found {recent_logs.count()} recent logs with discounts:")
            for log in recent_logs:
                self.stdout.write(f"  - {log.name}: ₦{log.amount} (discount: ₦{log.discount_amount})")
        else:
            self.stdout.write(f"\n✗ No recent logs with discounts found")
        
        self.stdout.write(self.style.SUCCESS("Discount display test completed!"))
