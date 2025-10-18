#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from customer.models import Customer

print("=== Customer Database Check ===")
print(f"Total customers: {Customer.objects.count()}")

if Customer.objects.exists():
    print("\nFirst 5 customers:")
    for i, customer in enumerate(Customer.objects.all()[:5], 1):
        print(f"{i}. {customer.name} - {customer.phone} - {customer.address}")
        if hasattr(customer, 'wallet'):
            print(f"   Wallet Balance: {customer.wallet.balance}")
        else:
            print("   No wallet found")
else:
    print("\nNo customers found in database!")
    print("You may need to register some customers first.")
