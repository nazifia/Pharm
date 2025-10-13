# Cashier Name Display Implementation

## Overview
This document describes the implementation of cashier name display throughout the pharmacy management system. The cashier's name is now displayed on receipts, payment requests, and other relevant pages.

## Changes Made

### 1. Database Models (pharmapp/store/models.py)

#### Receipt Model
Added `cashier` field to track which cashier processed the receipt:
```python
class Receipt(models.Model):
    # ... existing fields ...
    cashier = models.ForeignKey('Cashier', on_delete=models.SET_NULL, null=True, blank=True, 
                                related_name='receipts', 
                                help_text="Cashier who processed this receipt")
```

#### WholesaleReceipt Model
Added `cashier` field to track which cashier processed the wholesale receipt:
```python
class WholesaleReceipt(models.Model):
    # ... existing fields ...
    cashier = models.ForeignKey('Cashier', on_delete=models.SET_NULL, null=True, blank=True, 
                                related_name='wholesale_receipts', 
                                help_text="Cashier who processed this wholesale receipt")
```

### 2. Database Migration
Created and applied migration: `0064_add_cashier_to_receipts.py`
- Adds `cashier` field to `Receipt` model
- Adds `cashier` field to `WholesaleReceipt` model
- Fields are nullable for backward compatibility

### 3. View Updates

#### Retail Complete Payment Request (pharmapp/store/views.py)
Updated `complete_payment_request` view to set cashier when creating receipt:
```python
# Get cashier object if user is a cashier
cashier = None
if hasattr(request.user, 'cashier'):
    cashier = request.user.cashier

receipt = Receipt.objects.create(
    # ... other fields ...
    cashier=cashier,
    # ... other fields ...
)
```

#### Wholesale Complete Payment Request (pharmapp/wholesale/views.py)
Updated `complete_payment_request` view to set cashier when creating wholesale receipt:
```python
# Get cashier object if user is a cashier
cashier = None
if hasattr(request.user, 'cashier'):
    cashier = request.user.cashier

receipt = WholesaleReceipt.objects.create(
    # ... other fields ...
    cashier=cashier,
    # ... other fields ...
)
```

### 4. Template Updates

#### Retail Receipt (pharmapp/templates/store/receipt.html)
Added cashier name display after sales person:
```html
<p>Sales Person: {% if sales.user %}{{ sales.user.username|title }}{% else %}{{ user.username|title }}{% endif %}</p>
{% if receipt.cashier %}
<p>Cashier: {{ receipt.cashier.name|title }}</p>
{% endif %}
```

#### Wholesale Receipt (pharmapp/templates/wholesale/wholesale_receipt.html)
Added cashier name display after sales person:
```html
<p>Sales Person: {% if sales.user %}{{ sales.user.username|title }}{% else %}{{ user.username|title }}{% endif %}</p>
{% if receipt.cashier %}
<p>Cashier: {{ receipt.cashier.name|title }}</p>
{% endif %}
```

#### Receipt Detail Partial (pharmapp/templates/partials/receipt_detail.html)
Added cashier name display:
```html
<p><strong>Sales Person:</strong> {% if sales.user %}{{ sales.user.username|title }}{% else %}{{ user.username|title }}{% endif %}</p>
{% if receipt.cashier %}
<p><strong>Cashier:</strong> {{ receipt.cashier.name|title }}</p>
{% endif %}
```

#### Retail Payment Requests (pharmapp/templates/store/payment_requests.html)
Added "Cashier" column to the payment requests table:
```html
<thead>
    <tr>
        <th>Request ID</th>
        <th>Date</th>
        <th>Customer</th>
        <th>Total Amount</th>
        <th>Status</th>
        <th>Cashier</th>  <!-- NEW COLUMN -->
        <th>Notes</th>
        <th>Actions</th>
    </tr>
</thead>
<tbody>
    <td>
        {% if request.cashier %}
            {{ request.cashier.name }}
        {% elif request.status == 'completed' %}
            <span class="text-muted">N/A</span>
        {% else %}
            <span class="text-muted">-</span>
        {% endif %}
    </td>
</tbody>
```

#### Wholesale Payment Requests (pharmapp/templates/wholesale/wholesale_payment_requests.html)
Added "Cashier" column to the wholesale payment requests table:
```html
<thead>
    <tr>
        <th>Request ID</th>
        <th>Date</th>
        <th>Status</th>
        <th>Total Amount</th>
        <th>Customer</th>
        <th>Cashier</th>  <!-- NEW COLUMN -->
        <th>Items Count</th>
        <th>Actions</th>
    </tr>
</thead>
<tbody>
    <td>
        {% if request.cashier %}
            {{ request.cashier.name }}
        {% elif request.status == 'completed' %}
            <span class="text-muted">N/A</span>
        {% else %}
            <span class="text-muted">-</span>
        {% endif %}
    </td>
</tbody>
```

## How It Works

### Payment Request Flow
1. **Dispenser creates payment request** → PaymentRequest created with status='pending'
2. **Cashier accepts request** → Cashier assigned to PaymentRequest (in `accept_payment_request` view)
3. **Cashier completes payment** → Receipt created with cashier field set
4. **Receipt displays cashier name** → Shows both sales person (dispenser) and cashier

### Direct Sales Flow (without payment request)
1. **Dispenser creates sale directly** → Receipt created without cashier field
2. **Receipt displays only sales person** → Cashier field is null, so only dispenser shown

## Benefits

1. **Accountability**: Track which cashier processed each transaction
2. **Audit Trail**: Complete record of who was involved in each sale
3. **Performance Tracking**: Can analyze cashier performance and transaction counts
4. **Transparency**: Clear distinction between dispenser and cashier roles

## Display Logic

- **Sales Person**: Always displayed (the user who created the sale/dispensed items)
- **Cashier**: Only displayed if present (when payment was processed through cashier dashboard)
- **Payment Requests**: Shows assigned cashier or "-" for pending, "N/A" for completed without cashier

## Database Schema

```
Receipt:
- id (PK)
- customer (FK to Customer)
- sales (FK to Sales)
- cashier (FK to Cashier) [NEW]
- buyer_name
- buyer_address
- total_amount
- date
- receipt_id
- payment_method
- status
- ... other fields ...

WholesaleReceipt:
- id (PK)
- wholesale_customer (FK to WholesaleCustomer)
- sales (FK to Sales)
- cashier (FK to Cashier) [NEW]
- buyer_name
- buyer_address
- total_amount
- date
- receipt_id
- payment_method
- status
- ... other fields ...

PaymentRequest:
- id (PK)
- request_id
- dispenser (FK to User)
- cashier (FK to Cashier) [EXISTING]
- customer (FK to Customer)
- wholesale_customer (FK to WholesaleCustomer)
- payment_type
- total_amount
- status
- ... other fields ...
```

## Testing Checklist

- [x] Migration created and applied successfully
- [ ] Retail payment request flow shows cashier name on receipt
- [ ] Wholesale payment request flow shows cashier name on receipt
- [ ] Payment request lists show cashier names
- [ ] Receipts without cashier (direct sales) still work correctly
- [ ] Cashier dashboard displays cashier name
- [ ] Receipt detail pages show cashier information

## Future Enhancements

1. Add cashier performance reports
2. Add cashier-specific sales analytics
3. Add cashier shift management
4. Add cashier transaction history
5. Add cashier commission calculations

