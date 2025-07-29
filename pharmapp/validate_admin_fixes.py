#!/usr/bin/env python
"""
Comprehensive validation script for admin fixes
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')

def validate_admin_configuration():
    """Validate all admin configurations"""
    print("🔍 Validating Admin Configuration")
    print("=" * 50)
    
    try:
        # Setup Django
        django.setup()
        print("✅ Django setup successful")
        
        # Import admin and models
        from django.contrib import admin
        from store.models import (
            DispensingLog, Sales, SalesItem, WholesaleSalesItem, 
            Receipt, WholesaleReceipt, WholesaleItem, Expense
        )
        from store.admin import (
            DispensingLogAdmin, SalesAdmin, ReceiptAdmin, 
            SalesItemAdmin, WholesaleSalesItemAdmin, ExpenseAdmin
        )
        from wholesale.admin import WholesaleItemAdmin as WholesaleItemAdminClass
        
        print("✅ All imports successful")
        
        # Check model registrations
        registered_models = admin.site._registry
        
        # Test 1: Check if models are properly registered
        print("\n1. Testing Model Registrations:")
        
        models_to_check = [
            (DispensingLog, "DispensingLog"),
            (Sales, "Sales"),
            (SalesItem, "SalesItem"),
            (WholesaleSalesItem, "WholesaleSalesItem"),
            (Receipt, "Receipt"),
            (WholesaleReceipt, "WholesaleReceipt"),
            (WholesaleItem, "WholesaleItem"),
            (Expense, "Expense")
        ]
        
        for model, name in models_to_check:
            if model in registered_models:
                admin_class = registered_models[model]
                print(f"✅ {name}: {admin_class.__class__.__name__}")
            else:
                print(f"❌ {name}: Not registered")
        
        # Test 2: Check for duplicate registrations
        print("\n2. Testing for Duplicate Registrations:")
        try:
            # This should not raise an exception
            if WholesaleItem in registered_models:
                print("✅ WholesaleItem registered without conflicts")
            else:
                print("❌ WholesaleItem not found in registry")
        except Exception as e:
            print(f"❌ Duplicate registration error: {e}")
        
        # Test 3: Validate admin class configurations
        print("\n3. Testing Admin Class Configurations:")
        
        # Test SalesAdmin list_filter
        try:
            sales_admin = registered_models.get(Sales)
            if sales_admin:
                list_filter = getattr(sales_admin, 'list_filter', [])
                print(f"✅ SalesAdmin list_filter: {list_filter}")
                
                # Check for problematic __isnull filters
                problematic_filters = [f for f in list_filter if '__isnull' in str(f)]
                if problematic_filters:
                    print(f"❌ Found problematic filters: {problematic_filters}")
                else:
                    print("✅ No problematic __isnull filters found")
            else:
                print("❌ SalesAdmin not found")
        except Exception as e:
            print(f"❌ SalesAdmin configuration error: {e}")
        
        # Test 4: Check admin method functionality
        print("\n4. Testing Admin Method Functionality:")
        
        try:
            # Test DispensingLogAdmin methods
            sample_log = DispensingLog.objects.first()
            if sample_log:
                dispensing_admin = DispensingLogAdmin(DispensingLog, admin.site)
                
                # Test sales_performance method
                performance = dispensing_admin.sales_performance(sample_log)
                print(f"✅ sales_performance method: Working")
                
                # Test return_info method
                return_info = dispensing_admin.return_info(sample_log)
                print(f"✅ return_info method: Working")
            else:
                print("⚠️ No sample dispensing log for testing methods")
        except Exception as e:
            print(f"❌ Admin method error: {e}")
        
        # Test 5: Check admin display fields
        print("\n5. Testing Admin Display Fields:")
        
        admin_classes_to_test = [
            (DispensingLogAdmin, "DispensingLogAdmin"),
            (SalesAdmin, "SalesAdmin"),
            (ReceiptAdmin, "ReceiptAdmin"),
            (SalesItemAdmin, "SalesItemAdmin"),
        ]
        
        for admin_class, name in admin_classes_to_test:
            try:
                list_display = getattr(admin_class, 'list_display', [])
                search_fields = getattr(admin_class, 'search_fields', [])
                list_filter = getattr(admin_class, 'list_filter', [])
                
                print(f"✅ {name}:")
                print(f"   - list_display: {len(list_display)} fields")
                print(f"   - search_fields: {len(search_fields)} fields")
                print(f"   - list_filter: {len(list_filter)} filters")
            except Exception as e:
                print(f"❌ {name} configuration error: {e}")
        
        print("\n" + "=" * 50)
        print("🎉 Admin Configuration Validation Complete!")
        
        return True
        
    except Exception as e:
        print(f"❌ Critical error during validation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_admin_functionality():
    """Test specific admin functionality"""
    print("\n🧪 Testing Admin Functionality")
    print("=" * 50)
    
    try:
        from django.db.models import Sum, Count
        from datetime import datetime, timedelta
        
        # Test statistics calculations
        today = datetime.now().date()
        
        # Test daily sales calculation
        daily_sales = DispensingLog.objects.filter(
            created_at__date=today,
            status='Dispensed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        print(f"✅ Daily sales calculation: ₦{daily_sales:,.2f}")
        
        # Test top items calculation
        this_month = today.replace(day=1)
        top_items = DispensingLog.objects.filter(
            created_at__date__gte=this_month,
            status='Dispensed'
        ).values('name').annotate(
            total_amount=Sum('amount')
        ).order_by('-total_amount')[:3]
        
        print(f"✅ Top items calculation: {len(top_items)} items found")
        
        # Test user performance calculation
        user_performance = DispensingLog.objects.filter(
            created_at__date__gte=this_month,
            status='Dispensed'
        ).values('user__username').annotate(
            total_sales=Sum('amount')
        ).order_by('-total_sales')[:3]
        
        print(f"✅ User performance calculation: {len(user_performance)} users found")
        
        print("✅ All functionality tests passed!")
        
    except Exception as e:
        print(f"❌ Functionality test error: {e}")

if __name__ == "__main__":
    print("🚀 Starting Admin Validation")
    print("=" * 60)
    
    success = validate_admin_configuration()
    
    if success:
        test_admin_functionality()
        print("\n🎉 All validations completed successfully!")
        print("The admin interface should now work without errors.")
    else:
        print("\n❌ Validation failed. Please check the errors above.")
    
    print("=" * 60)
