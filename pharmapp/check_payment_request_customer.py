#!/usr/bin/env python
"""
Diagnostic script to check payment request customer data.
Run with: python manage.py shell < check_payment_request_customer.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from store.models import PaymentRequest, WholesaleReceipt
from customer.models import WholesaleCustomer

print("\n" + "="*80)
print("PAYMENT REQUEST CUSTOMER DIAGNOSTIC")
print("="*80 + "\n")

# Check recent wholesale payment requests
print("Recent Wholesale Payment Requests:")
print("-" * 80)
payment_requests = PaymentRequest.objects.filter(payment_type='wholesale').order_by('-created_at')[:10]

for pr in payment_requests:
    print(f"\nPayment Request ID: {pr.request_id}")
    print(f"  Status: {pr.status}")
    print(f"  Dispenser: {pr.dispenser.username}")
    print(f"  Total Amount: ₦{pr.total_amount}")
    print(f"  Wholesale Customer: {pr.wholesale_customer.name if pr.wholesale_customer else 'NONE (Walk-in)'}")
    if pr.wholesale_customer:
        print(f"    Customer ID: {pr.wholesale_customer.id}")
        print(f"    Customer Phone: {pr.wholesale_customer.phone}")
    print(f"  Created: {pr.created_at}")
    
    # Check if receipt exists
    if pr.wholesale_receipt:
        print(f"  Receipt ID: {pr.wholesale_receipt.receipt_id}")
        print(f"  Receipt Customer: {pr.wholesale_receipt.wholesale_customer.name if pr.wholesale_receipt.wholesale_customer else 'NONE'}")
        print(f"  Receipt Buyer Name: {pr.wholesale_receipt.buyer_name}")

print("\n" + "="*80)
print("Recent Wholesale Receipts:")
print("-" * 80)
receipts = WholesaleReceipt.objects.all().order_by('-date')[:10]

for receipt in receipts:
    print(f"\nReceipt ID: {receipt.receipt_id}")
    print(f"  Wholesale Customer: {receipt.wholesale_customer.name if receipt.wholesale_customer else 'NONE (Walk-in)'}")
    print(f"  Buyer Name: {receipt.buyer_name}")
    print(f"  Total Amount: ₦{receipt.total_amount}")
    print(f"  Payment Method: {receipt.payment_method}")
    print(f"  Date: {receipt.date}")
    if receipt.sales:
        print(f"  Sales Customer: {receipt.sales.wholesale_customer.name if receipt.sales.wholesale_customer else 'NONE'}")

print("\n" + "="*80)
print("All Wholesale Customers:")
print("-" * 80)
customers = WholesaleCustomer.objects.all()
for customer in customers:
    print(f"  ID: {customer.id} - Name: {customer.name} - Phone: {customer.phone}")

print("\n" + "="*80)
print("DIAGNOSTIC COMPLETE")
print("="*80 + "\n")

