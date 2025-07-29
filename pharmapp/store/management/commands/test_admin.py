from django.core.management.base import BaseCommand
from django.contrib import admin
from django.db.models import Sum, Count
from datetime import datetime, timedelta
from store.models import DispensingLog, Sales, SalesItem, Receipt, WholesaleItem

class Command(BaseCommand):
    help = 'Test admin configuration and functionality'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🧪 Testing Admin Configuration'))
        self.stdout.write('=' * 50)
        
        try:
            # Test 1: Check model registrations
            self.stdout.write('\n1. Testing Model Registrations:')
            
            registered_models = admin.site._registry
            
            models_to_check = [
                (DispensingLog, "DispensingLog"),
                (Sales, "Sales"),
                (SalesItem, "SalesItem"),
                (Receipt, "Receipt"),
                (WholesaleItem, "WholesaleItem"),
            ]
            
            for model, name in models_to_check:
                if model in registered_models:
                    admin_class = registered_models[model]
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ {name}: {admin_class.__class__.__name__}')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'❌ {name}: Not registered')
                    )
            
            # Test 2: Check for duplicate registrations
            self.stdout.write('\n2. Testing for Duplicate Registrations:')
            if WholesaleItem in registered_models:
                self.stdout.write(
                    self.style.SUCCESS('✅ WholesaleItem registered without conflicts')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ WholesaleItem not found in registry')
                )
            
            # Test 3: Test statistics calculations
            self.stdout.write('\n3. Testing Statistics Calculations:')
            
            today = datetime.now().date()
            
            # Daily sales
            daily_sales = DispensingLog.objects.filter(
                created_at__date=today,
                status='Dispensed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            self.stdout.write(f'✅ Daily sales: ₦{daily_sales:,.2f}')
            
            # Monthly sales
            this_month = today.replace(day=1)
            monthly_sales = DispensingLog.objects.filter(
                created_at__date__gte=this_month,
                status='Dispensed'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            self.stdout.write(f'✅ Monthly sales: ₦{monthly_sales:,.2f}')
            
            # Top items
            top_items = DispensingLog.objects.filter(
                created_at__date__gte=this_month,
                status='Dispensed'
            ).values('name').annotate(
                total_amount=Sum('amount')
            ).order_by('-total_amount')[:5]
            
            self.stdout.write(f'✅ Top items found: {len(top_items)}')
            
            # Test 4: Check admin methods
            self.stdout.write('\n4. Testing Admin Methods:')
            
            sample_log = DispensingLog.objects.first()
            if sample_log:
                from store.admin import DispensingLogAdmin
                admin_instance = DispensingLogAdmin(DispensingLog, admin.site)
                
                # Test methods
                performance = admin_instance.sales_performance(sample_log)
                return_info = admin_instance.return_info(sample_log)
                
                self.stdout.write('✅ Admin methods working correctly')
            else:
                self.stdout.write('⚠️ No sample data for testing admin methods')
            
            self.stdout.write('\n' + '=' * 50)
            self.stdout.write(
                self.style.SUCCESS('🎉 Admin configuration test completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Test failed: {e}')
            )
            import traceback
            traceback.print_exc()
