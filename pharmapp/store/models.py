from django.utils.dateparse import parse_date
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
    name = models.CharField(max_length=200)
    dosage_form = models.CharField(max_length=200, blank=True, null=True)  # Removed choices to allow any value
    brand = models.CharField(max_length=200, blank=True, null=True)
    unit = models.CharField(max_length=200, blank=True, null=True)  # Removed choices to allow any value
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    markup = models.DecimalField(max_digits=6, decimal_places=2, default=0, choices=MARKUP_CHOICES)
    stock = models.PositiveIntegerField(default=0, null=True, blank=True)
    low_stock_threshold = models.PositiveIntegerField(default=0, null=True, blank=True)
    exp_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return f'{self.name} {self.brand} {self.unit} {self.cost} {self.price} {self.markup} {self.stock} {self.exp_date}'

    def save(self, *args, **kwargs):
        if not self.price or self.price == self.cost + (self.cost * Decimal(self.markup) / Decimal("100")):
            self.price = self.cost + (self.cost * Decimal(self.markup) / Decimal("100"))
        super().save(*args, **kwargs)





class WholesaleItem(models.Model):
    name = models.CharField(max_length=200)
    dosage_form = models.CharField(max_length=200, blank=True, null=True)  # Removed choices to allow any value
    brand = models.CharField(max_length=200, blank=True, null=True)
    unit = models.CharField(max_length=200, blank=True, null=True)  # Removed choices to allow any value
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    markup = models.DecimalField(max_digits=6, decimal_places=2, default=0, choices=MARKUP_CHOICES)
    stock = models.DecimalField(max_digits=6, decimal_places=2, default=0, null=True, blank=True)
    low_stock_threshold = models.DecimalField(max_digits=6, decimal_places=2, default=0, null=True, blank=True)
    exp_date = models.DateField(null=True, blank=True)
    class Meta:
        ordering = ('name',)

    def __str__(self):
        return f'{self.name} {self.brand} {self.unit} {self.cost} {self.price} {self.markup} {self.stock} {self.exp_date}'

    def save(self, *args, **kwargs):
        # Check if the price was provided; if not, calculate based on the markup
        if not self.price or self.price == self.cost + (Decimal(self.cost) * Decimal(self.markup) / 100):
            self.price = self.cost + (Decimal(self.cost) * Decimal(self.markup) / 100)
        super().save(*args, **kwargs)


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    dosage_form = models.ForeignKey(Formulation, on_delete=models.CASCADE, blank=True, null=True)
    brand = models.CharField(max_length=200, blank=True, null=True)
    unit = models.CharField(max_length=200, choices=UNIT, blank=True, null=True)
    quantity = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cart_id = ShortUUIDField(unique=True, length=5, max_length=50, prefix='CID: ', alphabet='1234567890')

    def __str__(self):
        return f'{self.cart_id} {self.user}'

    @property
    def calculate_subtotal(self):
        return self.price * self.quantity

    def save(self, *args, **kwargs):
        # Always recalculate subtotal before saving
        self.subtotal = self.calculate_subtotal
        super().save(*args, **kwargs)



class WholesaleCart(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    item = models.ForeignKey(WholesaleItem, on_delete=models.CASCADE)
    dosage_form = models.ForeignKey(Formulation, on_delete=models.CASCADE, blank=True, null=True)
    brand = models.CharField(max_length=200, blank=True, null=True)
    unit = models.CharField(max_length=200, choices=UNIT, blank=True, null=True)
    quantity = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cart_id = ShortUUIDField(unique=True, length=5, max_length=50, prefix='CID: ', alphabet='1234567890')

    def __str__(self):
        return f'{self.cart_id} {self.user}'

    @property
    def calculate_subtotal(self):
        return self.price * self.quantity

    def save(self, *args, **kwargs):
        # Always recalculate subtotal before saving
        self.subtotal = self.calculate_subtotal
        super().save(*args, **kwargs)



class DispensingLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    dosage_form = models.ForeignKey(Formulation, on_delete=models.CASCADE, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=10, choices=UNIT, null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Dispensed')
    created_at = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f'{self.user.username} - {self.name} {self.dosage_form} {self.brand} ({self.quantity} {self.unit} {self.status})'



# Ensure Sales is defined before Receipt
class Sales(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    wholesale_customer = models.ForeignKey(WholesaleCustomer, on_delete=models.CASCADE, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date = models.DateField(default=datetime.now)

    def __str__(self):
        return f'{self.user} - {self.customer.name if self.customer else "WALK-IN CUSTOMER"} - {self.total_amount}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.customer:
            TransactionHistory.objects.create(
                customer=self.customer,
                transaction_type='purchase',
                amount=self.total_amount,
                description='Items purchased'
            )
            # Removed automatic receipt creation to prevent double receipts

    def calculate_total_amount(self):
        self.total_amount = sum(item.price * item.quantity for item in self.sales_items.all())
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

    def __str__(self):
        name = self.customer.name if self.customer else "WALK-IN CUSTOMER"
        return f"Receipt {self.receipt_id} - {name} - {self.total_amount} on {self.date}"

    @property
    def is_split_payment(self):
        return self.payment_method == 'Split' and hasattr(self, 'receipt_payments') and self.receipt_payments.exists()


# Concrete implementation of Payment for retail receipts
class ReceiptPayment(Payment):
    receipt = models.ForeignKey('Receipt', on_delete=models.CASCADE, related_name='receipt_payments')

    class Meta:
        verbose_name = 'Receipt Payment'
        verbose_name_plural = 'Receipt Payments'

class WholesaleReceipt(models.Model):
    wholesale_customer = models.ForeignKey(WholesaleCustomer, on_delete=models.CASCADE, null=True, blank=True)
    sales = models.ForeignKey(Sales, on_delete=models.CASCADE, related_name='wholesale_receipts', null=True, blank=True)
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

    def __str__(self):
        name = self.wholesale_customer.name if self.wholesale_customer else "WALK-IN CUSTOMER"
        return f"WholesaleReceipt {self.receipt_id} - {name} - {self.total_amount} on {self.date}"

    @property
    def is_split_payment(self):
        return self.payment_method == 'Split' and hasattr(self, 'wholesale_receipt_payments') and self.wholesale_receipt_payments.exists()

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

    def __str__(self):
        return f'{self.item.name} - {self.quantity} at {self.price}'

    @property
    def subtotal(self):
        return self.price * self.quantity



class WholesaleSalesItem(models.Model):
    sales = models.ForeignKey(Sales, on_delete=models.CASCADE, related_name='wholesale_sales_items')
    item = models.ForeignKey(WholesaleItem, on_delete=models.CASCADE)
    dosage_form = models.ForeignKey(Formulation, on_delete=models.CASCADE, blank=True, null=True)
    brand = models.CharField(max_length=225, null=True, blank=True, default='None')
    unit = models.CharField(max_length=10, choices=UNIT, default='unit')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.item.name} - {self.quantity} at {self.price}'

    @property
    def subtotal(self):
        return self.price * self.quantity



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
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_at')
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
    expected_quantity = models.PositiveIntegerField()
    actual_quantity = models.PositiveIntegerField()
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
    expected_quantity = models.PositiveIntegerField()
    actual_quantity = models.PositiveIntegerField()
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
    requested_quantity = models.PositiveIntegerField(
        help_text="Quantity originally requested.",
        default=0
    )
    approved_quantity = models.PositiveIntegerField(
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
