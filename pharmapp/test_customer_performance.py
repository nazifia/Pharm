#!/usr/bin/env python
"""
Test script for customer performance functionality
"""
import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from store.views import get_monthly_customer_performance, get_yearly_customer_performance
from customer.models import Customer, WholesaleCustomer
from store.models import Sales, SalesItem, WholesaleSalesItem, Item, WholesaleItem, Formulation
from userauth.models import User
from django.utils import timezone

def test_customer_performance():
    """Test customer performance functions"""
    print("Testing Customer Performance Functions...")
    print("=" * 50)
    
    try:
        # Test monthly customer performance
        print("\n1. Testing Monthly Customer Performance:")
        monthly_data = get_monthly_customer_performance()
        print(f"   - Found {len(monthly_data)} months of data")
        
        for month, data in monthly_data[:3]:  # Show first 3 months
            print(f"   - {month.strftime('%B %Y')}: {data['total_customers']} customers, ₦{data['month_total']}")
            if data['retail_customers']:
                print(f"     * Retail customers: {len(data['retail_customers'])}")
            if data['wholesale_customers']:
                print(f"     * Wholesale customers: {len(data['wholesale_customers'])}")
        
        # Test yearly customer performance
        print("\n2. Testing Yearly Customer Performance:")
        yearly_data = get_yearly_customer_performance()
        print(f"   - Found {len(yearly_data)} years of data")
        
        for year, data in yearly_data[:3]:  # Show first 3 years
            print(f"   - {year.strftime('%Y')}: {data['total_customers']} customers, ₦{data['year_total']}")
            if data['retail_customers']:
                print(f"     * Retail customers: {len(data['retail_customers'])}")
            if data['wholesale_customers']:
                print(f"     * Wholesale customers: {len(data['wholesale_customers'])}")
        
        # Test with date range
        print("\n3. Testing with Date Range (Last 30 days):")
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        monthly_data_filtered = get_monthly_customer_performance(start_date, end_date)
        print(f"   - Found {len(monthly_data_filtered)} months in last 30 days")
        
        # Test database queries
        print("\n4. Testing Database Queries:")
        total_customers = Customer.objects.count()
        total_wholesale_customers = WholesaleCustomer.objects.count()
        total_sales = Sales.objects.count()
        total_wholesale_sales = Sales.objects.filter(wholesale_sales_items__isnull=False).count()
        
        print(f"   - Total retail customers: {total_customers}")
        print(f"   - Total wholesale customers: {total_wholesale_customers}")
        print(f"   - Total retail sales: {total_sales}")
        print(f"   - Total wholesale sales: {total_wholesale_sales}")
        
        print("\n✅ All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_sample_data():
    """Test with sample data if no real data exists"""
    print("\n5. Testing Sample Data Creation:")
    
    try:
        # Check if we have any customers
        if Customer.objects.count() == 0:
            print("   - No customers found, creating sample data...")
            
            # Create a test user
            test_user, created = User.objects.get_or_create(
                username='test_customer_user',
                defaults={
                    'email': 'test@example.com',
                    'first_name': 'Test',
                    'last_name': 'Customer'
                }
            )
            
            # Create a test customer
            test_customer, created = Customer.objects.get_or_create(
                name='Test Customer',
                defaults={
                    'user': test_user,
                    'phone': '1234567890',
                    'address': 'Test Address'
                }
            )
            
            print(f"   - Created test customer: {test_customer.name}")
        else:
            print(f"   - Found {Customer.objects.count()} existing customers")
            
        # Check if we have any items
        if Item.objects.count() == 0:
            print("   - No items found, creating sample item...")
            
            # Create a test formulation
            test_formulation, created = Formulation.objects.get_or_create(
                name='Test Formulation'
            )
            
            # Create a test item
            test_item, created = Item.objects.get_or_create(
                name='Test Medicine',
                defaults={
                    'cost': Decimal('10.00'),
                    'price': Decimal('15.00'),
                    'quantity': 100,
                    'formulation': test_formulation
                }
            )
            
            print(f"   - Created test item: {test_item.name}")
        else:
            print(f"   - Found {Item.objects.count()} existing items")
            
        print("   ✅ Sample data check completed")
        return True
        
    except Exception as e:
        print(f"   ❌ Sample data creation failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Customer Performance Test Suite")
    print("=" * 50)
    
    # Run tests
    test_sample_data()
    test_customer_performance()
    
    print("\n" + "=" * 50)
    print("Test suite completed!")
