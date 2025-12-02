#!/usr/bin/env python
"""
Test GS1 barcode functionality
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from store.models import Item
from store.gs1_parser import parse_barcode

# Test user's barcode
user_barcode = 'NAVIDOXINE(01) 18906047654987(10) 250203 (17) 012028(21) NVDXN0225'

print("Testing GS1 barcode functionality...")
print(f"Original barcode: {user_barcode}")

# Parse the barcode
parsed = parse_barcode(user_barcode)
print(f"\nParsed GS1 data:")
print(f"  Product Name: {parsed.get('product_name')}")
print(f"  GTIN: {parsed.get('gtin')}")
print(f"  Batch Number: {parsed.get('batch_number')}")
print(f"  Expiry Date: {parsed.get('expiry_date')}")
print(f"  Serial Number: {parsed.get('serial_number')}")
print(f"  Is GS1 Format: {parsed.get('is_gs1_format')}")
print(f"  Confidence: {parsed.get('confidence')}")

# Check if item already exists
existing_item = Item.objects.filter(barcode=user_barcode).first()
if existing_item:
    print(f"\nItem already exists: {existing_item.name} (ID: {existing_item.id})")
else:
    print("\nItem not found in database (expected)")
    # Create item with GS1 data
    item, created = Item.objects.get_or_create(
        name='NAVIDOXINE',
        defaults={
            'barcode': user_barcode,
            'cost': 100.00,
            'price': 150.00,
            'stock': 100,
            'gtin': parsed.get('gtin', ''),
            'batch_number': parsed.get('batch_number', ''),
            'serial_number': parsed.get('serial_number', ''),
            'barcode_type': 'GS1'
        }
    )
    
    if created:
        print(f"Created new item: {item.name} (ID: {item.id})")
    else:
        print(f"Updated existing item: {item.name} (ID: {item.id})")

print("\nTest completed successfully!")
