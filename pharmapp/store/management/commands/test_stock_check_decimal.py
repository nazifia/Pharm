from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from store.models import Item, StockCheck, StockCheckItem, WholesaleItem, WholesaleStockCheck, WholesaleStockCheckItem
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Test stock check decimal functionality'

    def handle(self, *args, **options):
        self.stdout.write("🧪 Testing stock check decimal functionality...")
        
        # Get or create a test user
        user = User.objects.first()
        if not user:
            self.stdout.write("❌ No users found. Please create a user first.")
            return
        
        self.stdout.write(f"👤 Using user: {user.username}")
        
        # Test 1: Create a test item with decimal stock
        test_item, created = Item.objects.get_or_create(
            name="Test Decimal Item",
            defaults={
                'brand': 'Test Brand',
                'dosage_form': 'Tablet',
                'unit': 'Tab',
                'cost': Decimal('10.50'),
                'price': Decimal('15.75'),
                'stock': 25,  # This will be converted to decimal in stock check
            }
        )
        
        if created:
            self.stdout.write(f"✅ Created test item: {test_item.name}")
        else:
            self.stdout.write(f"✅ Using existing test item: {test_item.name}")
        
        # Test 2: Create a stock check with decimal quantities
        stock_check = StockCheck.objects.create(
            created_by=user,
            status='in_progress'
        )
        
        stock_check_item = StockCheckItem.objects.create(
            stock_check=stock_check,
            item=test_item,
            expected_quantity=Decimal('25.50'),  # Decimal expected quantity
            actual_quantity=Decimal('23.75'),    # Decimal actual quantity
            status='pending'
        )
        
        self.stdout.write(f"✅ Created stock check #{stock_check.id}")
        self.stdout.write(f"  📦 Item: {stock_check_item.item.name}")
        self.stdout.write(f"  📊 Expected Qty: {stock_check_item.expected_quantity}")
        self.stdout.write(f"  📊 Actual Qty: {stock_check_item.actual_quantity}")
        self.stdout.write(f"  📊 Discrepancy: {stock_check_item.discrepancy()}")
        
        # Test 3: Test decimal calculations
        discrepancy = stock_check_item.discrepancy()
        expected_discrepancy = Decimal('23.75') - Decimal('25.50')
        
        if discrepancy == expected_discrepancy:
            self.stdout.write(f"✅ Discrepancy calculation correct: {discrepancy}")
        else:
            self.stdout.write(f"❌ Discrepancy calculation incorrect. Expected: {expected_discrepancy}, Got: {discrepancy}")
        
        # Test 4: Test wholesale decimal functionality
        test_wholesale_item, created = WholesaleItem.objects.get_or_create(
            name="Test Wholesale Decimal Item",
            defaults={
                'brand': 'Test Wholesale Brand',
                'dosage_form': 'Capsule',
                'unit': 'Caps',
                'cost': Decimal('8.25'),
                'price': Decimal('12.50'),
                'stock': Decimal('15.25'),  # Already decimal
            }
        )
        
        if created:
            self.stdout.write(f"✅ Created test wholesale item: {test_wholesale_item.name}")
        else:
            self.stdout.write(f"✅ Using existing test wholesale item: {test_wholesale_item.name}")
        
        wholesale_stock_check = WholesaleStockCheck.objects.create(
            created_by=user,
            status='in_progress'
        )
        
        wholesale_stock_check_item = WholesaleStockCheckItem.objects.create(
            stock_check=wholesale_stock_check,
            item=test_wholesale_item,
            expected_quantity=Decimal('15.25'),
            actual_quantity=Decimal('14.75'),
            status='pending'
        )
        
        self.stdout.write(f"✅ Created wholesale stock check #{wholesale_stock_check.id}")
        self.stdout.write(f"  📦 Item: {wholesale_stock_check_item.item.name}")
        self.stdout.write(f"  📊 Expected Qty: {wholesale_stock_check_item.expected_quantity}")
        self.stdout.write(f"  📊 Actual Qty: {wholesale_stock_check_item.actual_quantity}")
        self.stdout.write(f"  📊 Discrepancy: {wholesale_stock_check_item.discrepancy()}")
        
        # Test 5: Test total discrepancy calculation
        total_discrepancy = stock_check.total_discrepancy()
        wholesale_total_discrepancy = wholesale_stock_check.total_discrepancy()
        
        self.stdout.write(f"✅ Retail total discrepancy: {total_discrepancy}")
        self.stdout.write(f"✅ Wholesale total discrepancy: {wholesale_total_discrepancy}")
        
        # Test 6: Test field types
        self.stdout.write("\n🔍 Field Type Verification:")
        self.stdout.write(f"  StockCheckItem.expected_quantity type: {type(stock_check_item.expected_quantity)}")
        self.stdout.write(f"  StockCheckItem.actual_quantity type: {type(stock_check_item.actual_quantity)}")
        self.stdout.write(f"  WholesaleStockCheckItem.expected_quantity type: {type(wholesale_stock_check_item.expected_quantity)}")
        self.stdout.write(f"  WholesaleStockCheckItem.actual_quantity type: {type(wholesale_stock_check_item.actual_quantity)}")
        
        # Clean up test data
        stock_check.delete()
        wholesale_stock_check.delete()
        if created:
            test_item.delete()
            test_wholesale_item.delete()
        
        self.stdout.write("\n🧹 Test data cleaned up")
        
        self.stdout.write(self.style.SUCCESS("\n🎉 Stock check decimal functionality test completed!"))
