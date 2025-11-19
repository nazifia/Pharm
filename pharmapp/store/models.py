from django.utils.dateparse import parse_date
from django.utils import timezone
from decimal import Decimal
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete
from customer.models import Customer, WholesaleCustomer, TransactionHistory
from datetime import datetime
from shortuuid.django_fields import ShortUUIDField
from userauth.models import User





# Create your models here.
DOSAGE_FORM = [
    ('Tablet', 'Tablet'),
    ('Capsule', 'Capsule'),
    ('Cream', 'Cream'),
    ('Consumable', 'Consumable'),
    ('Galenical', 'Galenical'),
    ('Injection', 'Injection'),
    ('Infusion', 'Infusion'),
    ('Inhaler', 'Inhaler'),
    ('Suspension', 'Suspension'),
    ('Syrup', 'Syrup'),
    ('Drops', 'Drops'),
    ('Solution', 'Solution'),
    ('Eye-drop', 'Eye-drop'),
    ('Ear-drop', 'Ear-drop'),
    ('Eye-ointment', 'Eye-ointment'),
    ('Rectal', 'Rectal'),
    ('Vaginal', 'Vaginal'),
    ('Detergent', 'Detergent'),
    ('Drinks', 'Drinks'),
    ('Paste', 'Paste'),
    ('Patch', 'Patch'),
    ('Table-water', 'Table-water'),
    ('Food-item', 'Food-item'),
    ('Sweets', 'Sweets'),
    ('Soaps', 'Soaps'),
    ('Biscuits', 'Biscuits'),

]


UNIT = [
    ('Amp', 'Amp'),
    ('Bottle', 'Bottle'),
    ('Tab', 'Tab'),
    ('Drops', 'Drops'),
    ('Tin', 'Tin'),
    ('Can', 'Can'),
    ('Caps', 'Caps'),
    ('Card', 'Card'),
    ('Carton', 'Carton'),
    ('Pack', 'Pack'),
    ('Sachets', 'Sachets'),
    ('Pcs', 'Pcs'),
    ('Roll', 'Roll'),
    ('Vail', 'Vail'),
    ('1L', '1L'),
    ('2L', '2L'),
    ('4L', '4L'),
]

MARKUP_CHOICES = [
        (0, 'No markup'),
        (2.5, '2.5% markup'),
        (5, '5% markup'),
        (7.5, '7.5% markup'),
        (10, '10% markup'),
        (12.5, '12.5% markup'),
        (15, '15% markup'),
        (17.5, '17.5% markup'),
        (20, '20% markup'),
        (22.5, '22.5% markup'),
        (25, '25% markup'),
        (27.5, '27.5% markup'),
        (30, '30% markup'),
        (32.5, '32.5% markup'),
        (35, '35% markup'),
        (37.5, '37.5% markup'),
        (40, '40% markup'),
        (42.5, '42.5% markup'),
        (45, '45% markup'),
        (47.5, '47.5% markup'),
        (50, '50% markup'),
        (57.5, '57.5% markup'),
        (60, '60% markup'),
        (62.5, '62.5% markup'),
        (65, '65% markup'),
        (67.5, '67.5% markup'),
        (70, '70% markup'),
        (72., '72.% markup'),
        (75, '75% markup'),
        (77.5, '77.5% markup'),
        (80, '80% markup'),
        (82.5, '82.% markup'),
        (85, '85% markup'),
        (87.5, '87.5% markup'),
        (90, '90% markup'),
        (92., '92.% markup'),
        (95, '95% markup'),
        (97.5, '97.5% markup'),
        (100, '100% markup'),
    ]


STATUS_CHOICES = [
        ('Returned', 'Returned'),
        ('Partially Returned', 'Partially Returned'),
        ('Dispensed', 'Dispensed'),
    ]

class Formulation(models.Model):
    dosage_form = models.CharField(max_length=200, choices=DOSAGE_FORM, null=True, blank=True, default='DosageForm')

    def __str__(self):
        return self.dosage_form


class Item(models.Model):
    name = models.CharField(max_length=200, db_index=True)  # Add index for faster search
    dosage_form = models.CharField(max_length=200, blank=True, null=True, db_index=True)  # Add index for search
    brand = models.CharField(max_length=200, blank=True, null=True, db_index=True)  # Add index for search
    unit = models.CharField(max_length=200, blank=True, null=True)  # Removed choices to allow any value
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    markup = models.DecimalField(max_digits=6, decimal_places=2, default=0, choices=MARKUP_CHOICES)
    stock = models.PositiveIntegerField(default=0, null=True, blank=True)
    low_stock_threshold = models.PositiveIntegerField(default=0, null=True, blank=True)
    exp_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ('name',)
        indexes = [
            models.Index(fields=['name', 'brand']),  # Composite index for name+brand searches
            models.Index(fields=['name', 'dosage_form']),  # Composite index for name+dosage searches
        ]

    def __str__(self):
        return f'{self.name} {self.brand} {self.unit} {self.cost} {self.price} {self.markup} {self.stock} {self.exp_date}'

    def save(self, *args, **kwargs):
        if not self.price or self.price == self.cost + (self.cost * Decimal(self.markup) / Decimal("100")):
            self.price = self.cost + (self.cost * Decimal(self.markup) / Decimal("100"))
        super().save(*args, **kwargs)





class WholesaleItem(models.Model):
    name = models.CharField(max_length=200, db_index=True)  # Add index for faster search
    dosage_form = models.CharField(max_length=200, blank=True, null=True, db_index=True)  # Add index for search
    brand = models.CharField(max_length=200, blank=True, null=True, db_index=True)  # Add index for search
    unit = models.CharField(max_length=200, blank=True, null=True)  # Removed choices to allow any value
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    markup = models.DecimalField(max_digits=6, decimal_places=2, default=0, choices=MARKUP_CHOICES)
    stock = models.DecimalField(max_digits=6, decimal_places=2, default=0, null=True, blank=True)
    low_stock_threshold = models.DecimalField(max_digits=6, decimal_places=2, default=0, null=True, blank=True)
    exp_date = models.DateField(null=True, blank=True)
    class Meta:
        ordering = ('name',)
        indexes = [
            models.Index(fields=['name', 'brand']),  # Composite index for name+brand searches
            models.Index(fields=['name', 'dosage_form']),  # Composite index for name+dosage searches
        ]

    def __str__(self):
        return f'{self.name} {self.brand} {self.unit} {self.cost} {self.price} {self.markup} {self.stock} {self.exp_date}'

    def save(self, *args, **kwargs):
        # Check if the price was provided; if not, calculate based on the markup
        if not self.price or self.price == self.cost + (Decimal(self.cost) * Decimal(self.markup) / 100):
            self.price = self.cost + (Decimal(self.cost) * Decimal(self.markup) / 100)
        super().save(*args, **kwargs)


class Cart(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('sent_to_cashier', 'Sent to Cashier'),
        ('processed', 'Processed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    dosage_form = models.ForeignKey(Formulation, on_delete=models.CASCADE, blank=True, null=True)
    brand = models.CharField(max_length=200, blank=True, null=True)
    unit = models.CharField(max_length=200, choices=UNIT, blank=True, null=True)
    quantity = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Discount amount to be subtracted from subtotal")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    cart_id = ShortUUIDField(unique=True, length=5, max_length=50, prefix='CID: ', alphabet='1234567890')

    def __str__(self):
        return f'{self.cart_id} {self.user}'

    @property
    def calculate_subtotal(self):
        base_subtotal = self.price * self.quantity
        discounted_subtotal = base_subtotal - self.discount_amount
        # Ensure subtotal doesn't go below 0
        return max(discounted_subtotal, Decimal('0.00'))

    def save(self, *args, **kwargs):
        # Validate discount amount doesn't exceed base subtotal
        base_subtotal = self.price * self.quantity
        if self.discount_amount > base_subtotal:
            self.discount_amount = base_subtotal

        # Always recalculate subtotal before saving
        self.subtotal = self.calculate_subtotal
        super().save(*args, **kwargs)



class WholesaleCart(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('sent_to_cashier', 'Sent to Cashier'),
        ('processed', 'Processed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    item = models.ForeignKey(WholesaleItem, on_delete=models.CASCADE)
    dosage_form = models.ForeignKey(Formulation, on_delete=models.CASCADE, blank=True, null=True)
    brand = models.CharField(max_length=200, blank=True, null=True)
    unit = models.CharField(max_length=200, choices=UNIT, blank=True, null=True)
    quantity = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Discount amount to be subtracted from subtotal")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    cart_id = ShortUUIDField(unique=True, length=5, max_length=50, prefix='CID: ', alphabet='1234567890')

    def __str__(self):
        return f'{self.cart_id} {self.user}'

    @property
    def calculate_subtotal(self):
        base_subtotal = self.price * self.quantity
        discounted_subtotal = base_subtotal - self.discount_amount
        # Ensure subtotal doesn't go below 0
        return max(discounted_subtotal, Decimal('0.00'))

    def save(self, *args, **kwargs):
        # Validate discount amount doesn't exceed base subtotal
        base_subtotal = self.price * self.quantity
        if self.discount_amount > base_subtotal:
            self.discount_amount = base_subtotal

        # Always recalculate subtotal before saving
        self.subtotal = self.calculate_subtotal
        super().save(*args, **kwargs)



class DispensingLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)  # Add index for user filtering
    name = models.CharField(max_length=100, db_index=True)  # Add index for name search
    dosage_form = models.ForeignKey(Formulation, on_delete=models.CASCADE, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True, db_index=True)  # Add index for brand search
    unit = models.CharField(max_length=10, choices=UNIT, null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Discount amount applied to this dispensed item")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Dispensed', db_index=True)  # Add index for status filtering
    created_at = models.DateTimeField(default=datetime.now, db_index=True)  # Add index for date filtering

    class Meta:
        indexes = [
            models.Index(fields=['-created_at']),  # Index for ordering by creation date (descending)
            models.Index(fields=['name', 'status']),  # Composite index for name+status searches
            models.Index(fields=['user', '-created_at']),  # Composite index for user+date filtering
            models.Index(fields=['status', '-created_at']),  # Composite index for status+date filtering
        ]

    def __str__(self):
        return f'{self.user.username} - {self.name} {self.dosage_form} {self.brand} ({self.quantity} {self.unit} {self.status})'

    @property
    def original_amount(self):
        """Calculate the original amount before discount"""
        return self.amount + self.discount_amount

    @property
    def discounted_amount(self):
        """Calculate the final amount after discount"""
        return self.amount

    @property
    def rate_per_unit(self):
        """Calculate the rate per unit (discounted price per unit)"""
        if self.quantity > 0:
            return self.discounted_amount / self.quantity
        return Decimal('0.00')

    @property
    def original_rate_per_unit(self):
        """Calculate the original rate per unit (before discount)"""
        if self.quantity > 0:
            return self.original_amount / self.quantity
        return Decimal('0.00')

    @property
    def has_returns(self):
        """Check if this dispensed item has any returns"""
        # If this entry itself has been marked as returned/partially returned
        if self.status in ['Returned', 'Partially Returned']:
            return True

        # If this is a dispensed item, check for separate return entries
        if self.status == 'Dispensed':
            # Look for return entries with the same item name (more flexible matching)
            return DispensingLog.objects.filter(
                name=self.name,
                status__in=['Returned', 'Partially Returned']
            ).exists()

        return False

    @property
    def related_returns(self):
        """Get all return entries for this dispensed item"""
        if self.status == 'Dispensed':
            # Look for separate return entries with the same item name
            return DispensingLog.objects.filter(
                name=self.name,
                status__in=['Returned', 'Partially Returned']
            ).order_by('created_at')
        else:
            return DispensingLog.objects.none()

    @property
    def total_returned_quantity(self):
        """Get total quantity returned for this dispensed item"""
        if self.status == 'Returned':
            # This entry itself was fully returned
            return self.quantity
        elif self.status == 'Partially Returned':
            # This entry was partially returned - we need to calculate the returned amount
            # For now, we'll show that it has returns but can't calculate exact amount
            # without additional tracking
            return self.quantity  # This is the remaining quantity, not returned quantity
        else:
            # This is a dispensed item, check for separate return entries
            return sum(log.quantity for log in self.related_returns)

    @property
    def return_summary(self):
        """Get a comprehensive return summary for this dispensed item"""
        if self.status == 'Returned':
            return {
                'has_returns': True,
                'return_type': 'fully_returned',
                'returned_quantity': self.quantity,
                'remaining_quantity': 0,
                'return_percentage': 100,
                'status_display': 'Fully returned'
            }
        elif self.status == 'Partially Returned':
            return {
                'has_returns': True,
                'return_type': 'partially_returned',
                'returned_quantity': 0,  # Would need additional tracking to calculate
                'remaining_quantity': self.quantity,
                'return_percentage': 0,  # Would need additional tracking to calculate
                'status_display': 'Partially returned'
            }
        elif self.status == 'Dispensed':
            related_returns = self.related_returns
            if related_returns.exists():
                total_returned = sum(log.quantity for log in related_returns)
                return_percentage = (total_returned / self.quantity * 100) if self.quantity > 0 else 0
                return {
                    'has_returns': True,
                    'return_type': 'separate_returns',
                    'returned_quantity': total_returned,
                    'remaining_quantity': self.quantity - total_returned,
                    'return_percentage': return_percentage,
                    'status_display': f'{total_returned} returned'
                }
            else:
                return {
                    'has_returns': False,
                    'return_type': 'no_returns',
                    'returned_quantity': 0,
                    'remaining_quantity': self.quantity,
                    'return_percentage': 0,
                    'status_display': 'No returns'
                }
        else:
            return {
                'has_returns': False,
                'return_type': 'unknown',
                'returned_quantity': 0,
                'remaining_quantity': self.quantity,
                'return_percentage': 0,
                'status_display': 'Unknown status'
            }



# Ensure Sales is defined before Receipt
class Sales(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    wholesale_customer = models.ForeignKey(WholesaleCustomer, on_delete=models.CASCADE, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date = models.DateField(default=datetime.now)
    # Return tracking fields
    is_returned = models.BooleanField(default=False, help_text="Indicates if this sale has been returned")
    return_date = models.DateTimeField(null=True, blank=True, help_text="Date when the sale was returned")
    return_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total amount returned")
    return_processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_returns', help_text="User who processed the return")

    def __str__(self):
        return f'{self.user} - {self.customer.name if self.customer else "WALK-IN CUSTOMER"} - {self.total_amount}'

    def save(self, *args, **kwargs):
        # Removed automatic transaction history creation to prevent duplicates
        # Transaction history will be created during payment processing
        super().save(*args, **kwargs)

    def calculate_total_amount(self):
        # Calculate total using discounted amounts (subtotal property includes discount)
        self.total_amount = sum(item.subtotal for item in self.sales_items.all())
        self.save()




# Payment model for tracking individual payments
class Payment(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=[
        ('Cash', 'Cash'),
        ('Wallet', 'Wallet'),
        ('Transfer', 'Transfer'),
    ])
    status = models.CharField(max_length=20, choices=[
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
    ], default='Paid')
    date = models.DateTimeField(default=datetime.now)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.payment_method} payment of {self.amount} ({self.status})"

# Create your models here.
class Receipt(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    sales = models.ForeignKey(Sales, on_delete=models.CASCADE, related_name='receipts', null=True, blank=True)
    cashier = models.ForeignKey('Cashier', on_delete=models.SET_NULL, null=True, blank=True, related_name='receipts', help_text="Cashier who processed this receipt")
    buyer_name = models.CharField(max_length=255, blank=True, null=True)
    buyer_address = models.CharField(max_length=255, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.0'))
    date = models.DateTimeField(default=datetime.now)
    receipt_id = ShortUUIDField(unique=True, length=5, max_length=50, alphabet='1234567890')
    printed = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=20, choices=[
        ('Cash', 'Cash'),
        ('Wallet', 'Wallet'),
        ('Transfer', 'Transfer'),
        ('Split', 'Split Payment'),
    ], default='Cash')
    status = models.CharField(max_length=20, choices=[
        ('Paid', 'Paid'),
        ('Partially Paid', 'Partially Paid'),
        ('Unpaid', 'Unpaid'),
    ], default='Paid')
    wallet_went_negative = models.BooleanField(default=False, help_text="Indicates if customer's wallet went negative during this transaction")
    # Return tracking fields
    is_returned = models.BooleanField(default=False, help_text="Indicates if this receipt has been returned")
    return_date = models.DateTimeField(null=True, blank=True, help_text="Date when the receipt was returned")
    return_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total amount returned")
    return_processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_receipt_returns', help_text="User who processed the return")

    def __str__(self):
        name = self.customer.name if self.customer else "WALK-IN CUSTOMER"
        return f"Receipt {self.receipt_id} - {name} - {self.total_amount} on {self.date}"

    @property
    def is_split_payment(self):
        return self.payment_method == 'Split' and hasattr(self, 'receipt_payments') and self.receipt_payments.exists()

    @property
    def calculated_status(self):
        """Calculate the actual payment status based on payment records for split payments"""
        if self.payment_method == 'Split' and hasattr(self, 'receipt_payments'):
            payments = self.receipt_payments.all()
            if not payments.exists():
                return self.status  # Return stored status if no payment records

            total_paid = sum(payment.amount for payment in payments if payment.status == 'Paid')

            if total_paid >= self.total_amount:
                return 'Paid'
            elif total_paid > 0:
                return 'Partially Paid'
            else:
                return 'Unpaid'
        else:
            return self.status  # Return stored status for non-split payments


# Concrete implementation of Payment for retail receipts
class ReceiptPayment(Payment):
    receipt = models.ForeignKey('Receipt', on_delete=models.CASCADE, related_name='receipt_payments')

    class Meta:
        verbose_name = 'Receipt Payment'
        verbose_name_plural = 'Receipt Payments'

class WholesaleReceipt(models.Model):
    wholesale_customer = models.ForeignKey(WholesaleCustomer, on_delete=models.CASCADE, null=True, blank=True)
    sales = models.ForeignKey(Sales, on_delete=models.CASCADE, related_name='wholesale_receipts', null=True, blank=True)
    cashier = models.ForeignKey('Cashier', on_delete=models.SET_NULL, null=True, blank=True, related_name='wholesale_receipts', help_text="Cashier who processed this wholesale receipt")
    buyer_name = models.CharField(max_length=255, blank=True, null=True)
    buyer_address = models.CharField(max_length=255, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.0'))
    date = models.DateTimeField(default=datetime.now)
    receipt_id = ShortUUIDField(unique=True, length=5, max_length=50, alphabet='1234567890')
    # printed = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=20, choices=[
        ('Cash', 'Cash'),
        ('Wallet', 'Wallet'),
        ('Transfer', 'Transfer'),
        ('Split', 'Split Payment'),
    ], default='Cash')
    status = models.CharField(max_length=20, choices=[
        ('Paid', 'Paid'),
        ('Partially Paid', 'Partially Paid'),
        ('Unpaid', 'Unpaid'),
    ], default='Paid')
    wallet_went_negative = models.BooleanField(default=False, help_text="Indicates if customer's wallet went negative during this transaction")
    # Return tracking fields
    is_returned = models.BooleanField(default=False, help_text="Indicates if this wholesale receipt has been returned")
    return_date = models.DateTimeField(null=True, blank=True, help_text="Date when the wholesale receipt was returned")
    return_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total amount returned")
    return_processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_wholesale_returns', help_text="User who processed the return")

    def __str__(self):
        name = self.wholesale_customer.name if self.wholesale_customer else "WALK-IN CUSTOMER"
        return f"WholesaleReceipt {self.receipt_id} - {name} - {self.total_amount} on {self.date}"

    @property
    def is_split_payment(self):
        return self.payment_method == 'Split' and hasattr(self, 'wholesale_receipt_payments') and self.wholesale_receipt_payments.exists()

    @property
    def calculated_status(self):
        """Calculate the actual payment status based on payment records for split payments"""
        if self.payment_method == 'Split' and hasattr(self, 'wholesale_receipt_payments'):
            payments = self.wholesale_receipt_payments.all()
            if not payments.exists():
                return self.status  # Return stored status if no payment records

            total_paid = sum(payment.amount for payment in payments if payment.status == 'Paid')

            if total_paid >= self.total_amount:
                return 'Paid'
            elif total_paid > 0:
                return 'Partially Paid'
            else:
                return 'Unpaid'
        else:
            return self.status  # Return stored status for non-split payments

# Concrete implementation of Payment for wholesale receipts
class WholesaleReceiptPayment(Payment):
    receipt = models.ForeignKey(WholesaleReceipt, on_delete=models.CASCADE, related_name='wholesale_receipt_payments')

    class Meta:
        verbose_name = 'Wholesale Receipt Payment'
        verbose_name_plural = 'Wholesale Receipt Payments'




class SalesItem(models.Model):
    sales = models.ForeignKey(Sales, on_delete=models.CASCADE, related_name='sales_items')
    unit = models.CharField(max_length=10, choices=UNIT, default='unit')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    dosage_form = models.ForeignKey(Formulation, on_delete=models.CASCADE, blank=True, null=True)
    brand = models.CharField(max_length=225, null=True, blank=True, default='None')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Discount amount applied to this item")

    def __str__(self):
        return f'{self.item.name} - {self.quantity} at {self.price}'

    @property
    def subtotal(self):
        base_subtotal = self.price * self.quantity
        discounted_subtotal = base_subtotal - self.discount_amount
        # Ensure subtotal doesn't go below 0
        return max(discounted_subtotal, Decimal('0.00'))



class WholesaleSalesItem(models.Model):
    sales = models.ForeignKey(Sales, on_delete=models.CASCADE, related_name='wholesale_sales_items')
    item = models.ForeignKey(WholesaleItem, on_delete=models.CASCADE)
    dosage_form = models.ForeignKey(Formulation, on_delete=models.CASCADE, blank=True, null=True)
    brand = models.CharField(max_length=225, null=True, blank=True, default='None')
    unit = models.CharField(max_length=10, choices=UNIT, default='unit')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Discount amount applied to this item")

    def __str__(self):
        return f'{self.item.name} - {self.quantity} at {self.price}'

    @property
    def subtotal(self):
        base_subtotal = self.price * self.quantity
        discounted_subtotal = base_subtotal - self.discount_amount
        # Ensure subtotal doesn't go below 0
        return max(discounted_subtotal, Decimal('0.00'))



class ItemSelectionHistory(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    action = models.CharField(max_length=20, choices=[('purchase', 'Purchase'), ('return', 'Return')])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f'{self.customer.name} - {self.item.name} ({self.action})'





class WholesaleSelectionHistory(models.Model):
    wholesale_customer = models.ForeignKey(WholesaleCustomer, on_delete=models.CASCADE, null=True, blank=True)
    item = models.ForeignKey(WholesaleItem, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    action = models.CharField(max_length=20, choices=[('purchase', 'Purchase'), ('return', 'Return')])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f'{self.wholesale_customer.name} - {self.item.name} ({self.action})'



# Suppliers Model Definition
class Supplier(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, blank=True, null=True)
    contact_info = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name




# Store model that receives items from suppliers
class StoreItem(models.Model):
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255, null=True, blank=True, default='None')
    dosage_form = models.CharField(max_length=255, default='dosage_form')  # Removed choices to allow any value
    unit = models.CharField(max_length=100)  # Removed choices to allow any value
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    expiry_date = models.DateField(null=True, blank=True)
    date = models.DateField(default=datetime.now)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.brand}) - {self.stock} in stock"

    def update_stock(self, quantity):
        """Increase stock when new items are procured."""
        self.stock += quantity
        self.save()

    def reduce_stock(self, quantity):
        """Reduce stock when items are sold or dispensed."""
        if self.stock >= quantity:
            self.stock -= quantity
            self.save()
        else:
            raise ValueError("Not enough stock available")





# Retail stock check Models
class StockCheck(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    id = models.AutoField(primary_key=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_stock_checks')
    date = models.DateTimeField(default=datetime.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def total_discrepancy(self):
        return sum(item.discrepancy() for item in self.stockcheckitem_set.all())

    def __str__(self):
        return f"Stock Check #{self.id} - {self.date}"

class StockCheckItem(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('adjusted', 'Adjusted'),
    ]

    stock_check = models.ForeignKey(StockCheck, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    expected_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actual_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_at = models.DateTimeField(null=True, blank=True)


    def discrepancy(self):
        return self.actual_quantity - self.expected_quantity

    def __str__(self):
        return f"{self.item.name} - Stock Check #{self.stock_check.id}"



import logging

logger = logging.getLogger(__name__)

class StockAdjustment(models.Model):
    ADJUSTMENT_TYPES = [
        ('manual', 'Manual Adjustment'),
        ('stock_check', 'Stock Check Adjustment'),
        ('transfer', 'Transfer Adjustment'),
        ('other', 'Other'),
    ]

    # Make item field nullable to allow for migration
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='stock_adjustments', null=True, blank=True)
    stock_check_item = models.OneToOneField(StockCheckItem, on_delete=models.CASCADE, null=True, blank=True)
    old_quantity = models.PositiveIntegerField(default=0)
    new_quantity = models.PositiveIntegerField(default=0)
    adjusted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    adjusted_at = models.DateTimeField(auto_now_add=True)
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPES, default='manual')
    notes = models.TextField(blank=True, null=True)

    def apply_adjustment(self):
        """Update item stock based on the adjustment"""
        item = self.item
        logger.info(f"Applying adjustment: {self.new_quantity} for item {item.name} (ID: {item.id})")
        item.stock = self.new_quantity
        item.save(update_fields=['stock'])
        logger.info(f"Stock updated: New stock quantity = {item.stock}")



# Wholesale Stock check Models
class WholesaleStockCheck(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    id = models.AutoField(primary_key=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wholesale_items')
    date = models.DateTimeField(default=datetime.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def total_discrepancy(self):
        return sum(item.discrepancy() for item in self.wholesale_items.all())

    def __str__(self):
        return f"Stock Check #{self.id} - {self.date}"

class WholesaleStockCheckItem(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('adjusted', 'Adjusted'),
    ]

    stock_check = models.ForeignKey(WholesaleStockCheck, on_delete=models.CASCADE, related_name='wholesale_items')
    item = models.ForeignKey(WholesaleItem, on_delete=models.CASCADE, related_name='wholesale_item')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    expected_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actual_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_at = models.DateTimeField(null=True, blank=True)


    def discrepancy(self):
        return self.actual_quantity - self.expected_quantity

    def __str__(self):
        return f"{self.item.name} - Stock Check #{self.stock_check.id}"




import logging

logger = logging.getLogger(__name__)

class WholesaleStockAdjustment(models.Model):
    ADJUSTMENT_TYPES = [
        ('manual', 'Manual Adjustment'),
        ('stock_check', 'Stock Check Adjustment'),
        ('transfer', 'Transfer Adjustment'),
        ('other', 'Other'),
    ]

    # Make item field nullable to allow for migration
    item = models.ForeignKey(WholesaleItem, on_delete=models.CASCADE, related_name='stock_adjustments', null=True, blank=True)
    stock_check_item = models.OneToOneField(WholesaleStockCheckItem, on_delete=models.CASCADE, null=True, blank=True)
    old_quantity = models.PositiveIntegerField(default=0)
    new_quantity = models.PositiveIntegerField(default=0)
    adjusted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    adjusted_at = models.DateTimeField(auto_now_add=True)
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPES, default='manual')
    notes = models.TextField(blank=True, null=True)

    def apply_adjustment(self):
        """Update item stock based on the adjustment"""
        item = self.item
        logger.info(f"Applying adjustment: {self.new_quantity} for item {item.name} (ID: {item.id})")
        item.stock = self.new_quantity
        item.save(update_fields=['stock'])
        logger.info(f"Stock updated: New stock quantity = {item.stock}")




# INTER-STORE TRANSFER MODEL AND LOGIC
class TransferRequest(models.Model):
    # When the request is initiated by wholesale, the retail_item field is set
    # (i.e. the item held by retail that should be transferred).
    # For a request initiated by retail, the wholesale_item field would be set.
    wholesale_item = models.ForeignKey(
        'WholesaleItem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Set when request originates from retail (to wholesale)."
    )
    retail_item = models.ForeignKey(
        'Item',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Set when request originates from wholesale (to retail)."
    )
    requested_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Quantity originally requested.",
        default=0
    )
    approved_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True, blank=True,
        help_text="Quantity approved (may be adjusted)."
    )
    from_wholesale = models.BooleanField(
        default=False,
        help_text="True if request initiated by wholesale (targeting retail's stock), False if by retail."
    )
    status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("received", "Received")],
        default="pending"
    )
    created_at = models.DateTimeField(default=datetime.now)

    def __str__(self):
        if self.from_wholesale:
            source = self.retail_item  # wholesale-initiated: retail is source
        else:
            source = self.wholesale_item
        return f"{source.name if source else 'Unknown'}: {self.requested_quantity} ({self.get_status_display()})"



# EXPENSE TRACKING MODELS
class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = 'Expense Categories'

    def __str__(self):
        return self.name


class Expense(models.Model):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=datetime.now)
    description = models.TextField(blank=True, null=True)


    def __str__(self):
        return f"{self.category.name} - {self.amount} - {self.date}"


class MonthlyReport(models.Model):
    month = models.DateField()
    total_sales = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def calculate_net_profit(self):
        self.net_profit = self.total_sales - self.total_expenses
        self.save()


class StoreSettings(models.Model):
    low_stock_threshold = models.PositiveIntegerField(default=10)

    class Meta:
        verbose_name = 'Store Settings'
        verbose_name_plural = 'Store Settings'

    def save(self, *args, **kwargs):
        if not self.pk and StoreSettings.objects.exists():
            # If you're trying to create a new settings instance but one already exists,
            # update the existing instance instead
            return StoreSettings.objects.first()
        return super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings


class WholesaleSettings(models.Model):
    low_stock_threshold = models.PositiveIntegerField(default=10)

    class Meta:
        verbose_name = 'Wholesale Settings'
        verbose_name_plural = 'Wholesale Settings'

    def save(self, *args, **kwargs):
        if not self.pk and WholesaleSettings.objects.exists():
            return WholesaleSettings.objects.first()
        return super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings


# Cashier/Billing-Point/Pay-Point Models
class Cashier(models.Model):
    """Model for cashier/billing-point/pay-point users"""
    CASHIER_TYPE_CHOICES = [
        ('retail', 'Retail Only'),
        ('wholesale', 'Wholesale Only'),
        ('both', 'Retail & Wholesale'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    cashier_id = ShortUUIDField(unique=True, length=8, max_length=50, prefix='CSH:', alphabet='1234567890')
    name = models.CharField(max_length=200)
    cashier_type = models.CharField(max_length=20, choices=CASHIER_TYPE_CHOICES, default='both')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=datetime.now)
    
    def __str__(self):
        return f"{self.name} ({self.cashier_id}) - {self.get_cashier_type_display()}"
    
    def can_handle_retail(self):
        """Check if cashier can handle retail operations"""
        return self.cashier_type in ['retail', 'both']
    
    def can_handle_wholesale(self):
        """Check if cashier can handle wholesale operations"""
        return self.cashier_type in ['wholesale', 'both']


class PaymentRequest(models.Model):
    """Model for payment requests sent to cashier/billing-point/pay-point"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale'),
    ]
    
    request_id = ShortUUIDField(unique=True, length=8, max_length=50, prefix='PRQ:', alphabet='1234567890')
    dispenser = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_requests')
    cashier = models.ForeignKey(Cashier, on_delete=models.CASCADE, related_name='received_requests', null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    wholesale_customer = models.ForeignKey(WholesaleCustomer, on_delete=models.CASCADE, null=True, blank=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Payment processing
    receipt = models.ForeignKey('Receipt', on_delete=models.CASCADE, null=True, blank=True, related_name='payment_request')
    wholesale_receipt = models.ForeignKey('WholesaleReceipt', on_delete=models.CASCADE, null=True, blank=True, related_name='payment_request')
    
    def __str__(self):
        return f"Payment Request {self.request_id} - {self.get_status_display()}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['dispenser', '-created_at']),
            models.Index(fields=['cashier', '-created_at']),
        ]


class PaymentRequestItem(models.Model):
    """Items included in a payment request"""
    payment_request = models.ForeignKey(PaymentRequest, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=200)
    brand = models.CharField(max_length=200, blank=True, null=True)
    dosage_form = models.CharField(max_length=200, blank=True, null=True)
    unit = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Link to original item for reference
    retail_item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)
    wholesale_item = models.ForeignKey(WholesaleItem, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.item_name} - {self.quantity} {self.unit}"


class Notification(models.Model):
    """System notifications for users"""
    NOTIFICATION_TYPES = [
        ('low_stock', 'Low Stock Alert'),
        ('out_of_stock', 'Out of Stock Alert'),
        ('expiry_alert', 'Expiry Alert'),
        ('system_message', 'System Message'),
        ('procurement_alert', 'Procurement Alert'),
        ('payment_request', 'Payment Request'),
    ]

    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                           help_text="Leave blank for system-wide notifications")
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    title = models.CharField(max_length=200)
    message = models.TextField()

    # Related objects
    related_item = models.ForeignKey(Item, on_delete=models.CASCADE, null=True, blank=True)
    related_wholesale_item = models.ForeignKey(WholesaleItem, on_delete=models.CASCADE, null=True, blank=True)
    related_payment_request = models.ForeignKey(PaymentRequest, on_delete=models.CASCADE, null=True, blank=True)

    # Status fields
    is_read = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'is_dismissed']),
            models.Index(fields=['notification_type', 'created_at']),
        ]

    def __str__(self):
        user_str = f"for {self.user.username}" if self.user else "system-wide"
        return f"{self.get_notification_type_display()} {user_str}: {self.title}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def dismiss(self):
        """Dismiss notification"""
        if not self.is_dismissed:
            self.is_dismissed = True
            self.dismissed_at = timezone.now()
            self.save(update_fields=['is_dismissed', 'dismissed_at'])
