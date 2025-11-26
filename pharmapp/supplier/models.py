from decimal import Decimal
import decimal
from django.db import models
from django.utils import timezone
from userauth.models import User
from store.models import Item, StoreItem, WholesaleItem
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete




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
    ('Drops', 'Drops'),
    ('Tab', 'Tab'),
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





class Supplier(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, blank=True, null=True)
    contact_info = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Procurement(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('completed', 'Completed'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')

    def __str__(self):
        return f'Procurement {self.supplier.name}'



    def calculate_total(self):
        """Calculate and update the total cost of the procurement."""
        self.total = sum(item.subtotal for item in self.items.all())
        self.save(update_fields=['total'])



class ProcurementItem(models.Model):
    procurement = models.ForeignKey(Procurement, related_name='items', on_delete=models.CASCADE)
    item_name = models.CharField(max_length=255)
    dosage_form = models.CharField(max_length=255, choices=DOSAGE_FORM, default='dosage_form')
    brand = models.CharField(max_length=225, null=True, blank=True, default='None')
    unit = models.CharField(max_length=100, choices=UNIT)
    quantity = models.PositiveIntegerField(default=0)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    markup = models.FloatField(choices=MARKUP_CHOICES, default=0)
    expiry_date = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    barcode = models.CharField(max_length=200, blank=True, null=True, help_text="Barcode for this item")

    def save(self, *args, **kwargs):
        # Set default values for empty fields
        if not self.brand:
            self.brand = 'None'

        if self.cost_price is None or self.quantity is None:
            raise ValueError("Both cost_price and quantity must be provided to calculate subtotal.")

        # Calculate subtotal
        self.subtotal = self.cost_price * self.quantity

        # Check if we should move to store
        move_to_store = kwargs.pop('move_to_store', True) if 'move_to_store' in kwargs else True
        commit = kwargs.pop('commit', True) if 'commit' in kwargs else True

        if commit:
            super().save(*args, **kwargs)

            # Move item to store after procurement is completed if requested
            if move_to_store and self.procurement and self.procurement.status == 'completed':
                self.move_to_store()

    def move_to_store(self):
        """Move the procured item to the store after procurement."""
        # Calculate subtotal for the store item
        subtotal = self.cost_price * self.quantity

        # Check if the item already exists in the store
        existing_items = StoreItem.objects.filter(
            name=self.item_name,
            brand=self.brand,
            dosage_form=self.dosage_form,
            unit=self.unit,
            cost_price=self.cost_price
        )

        if existing_items.exists():
            # Use the existing item
            store_item = existing_items.first()
            store_item.stock += self.quantity

            # Only update expiry date if the new one is later than the existing one
            if self.expiry_date and (not store_item.expiry_date or self.expiry_date > store_item.expiry_date):
                store_item.expiry_date = self.expiry_date

            store_item.save()
        else:
            # Create a new item
            StoreItem.objects.create(
                name=self.item_name,
                brand=self.brand,
                dosage_form=self.dosage_form,
                unit=self.unit,
                stock=self.quantity,
                cost_price=self.cost_price,
                subtotal=subtotal,
                expiry_date=self.expiry_date
            )

    def __str__(self):
        return f'{self.item_name} - {self.procurement.id}'





# Wholesale Procurement Models
class WholesaleProcurement(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('completed', 'Completed'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')

    def __str__(self):
        return f'Procurement {self.supplier.name}'

    def calculate_total(self):
        """Calculate and update the total cost of the procurement."""
        self.total = sum(item.subtotal for item in self.items.all())
        self.save(update_fields=['total'])


class WholesaleProcurementItem(models.Model):
    procurement = models.ForeignKey(WholesaleProcurement, related_name='items', on_delete=models.CASCADE)
    item_name = models.CharField(max_length=255)
    dosage_form = models.CharField(max_length=255, choices=DOSAGE_FORM, default='dosage_form')
    brand = models.CharField(max_length=225, null=True, blank=True, default='None')
    unit = models.CharField(max_length=100, choices=UNIT)
    quantity = models.PositiveIntegerField(default=0)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    markup = models.FloatField(choices=MARKUP_CHOICES, default=0)
    expiry_date = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    barcode = models.CharField(max_length=200, blank=True, null=True, help_text="Barcode for this item")

    def save(self, *args, **kwargs):
        # Set default values for empty fields
        if not self.brand:
            self.brand = 'None'

        if self.cost_price is None or self.quantity is None:
            raise ValueError("Both cost_price and quantity must be provided to calculate subtotal.")

        # Calculate subtotal
        self.subtotal = self.cost_price * self.quantity

        # Check if we should move to store
        move_to_store = kwargs.pop('move_to_store', True) if 'move_to_store' in kwargs else True
        commit = kwargs.pop('commit', True) if 'commit' in kwargs else True

        if commit:
            super().save(*args, **kwargs)

            # Move item to store after procurement is completed if requested
            if move_to_store and self.procurement and self.procurement.status == 'completed':
                self.move_to_store()

    def move_to_store(self):
        """Move the procured item to the store after procurement."""
        # Calculate subtotal for the store item
        subtotal = self.cost_price * self.quantity

        # Check if the item already exists in the store
        existing_items = StoreItem.objects.filter(
            name=self.item_name,
            brand=self.brand,
            dosage_form=self.dosage_form,
            unit=self.unit,
            cost_price=self.cost_price
        )

        if existing_items.exists():
            # Use the existing item
            store_item = existing_items.first()
            store_item.stock += self.quantity

            # Only update expiry date if the new one is later than the existing one
            if self.expiry_date and (not store_item.expiry_date or self.expiry_date > store_item.expiry_date):
                store_item.expiry_date = self.expiry_date

            store_item.save()
            print(f"Successfully updated store item: {self.item_name}, new stock: {store_item.stock}")
        else:
            # Create a new item
            try:
                # Create the store item
                store_item = StoreItem.objects.create(
                    name=self.item_name,
                    brand=self.brand,
                    dosage_form=self.dosage_form,
                    unit=self.unit,
                    stock=self.quantity,
                    cost_price=self.cost_price,
                    subtotal=subtotal,
                    expiry_date=self.expiry_date,
                    supplier=self.procurement.supplier if hasattr(self.procurement, 'supplier') else None
                )
                print(f"Successfully created store item: {self.item_name}, stock: {store_item.stock}")
            except Exception as e:
                print(f"Error creating store item: {e}")

    def __str__(self):
        return f'{self.item_name} - {self.procurement.id}'


# Signals to update procurement totals
@receiver(post_save, sender=ProcurementItem)
def update_procurement_total(sender, instance, created, **kwargs):
    instance.procurement.calculate_total()

@receiver(pre_delete, sender=ProcurementItem)
def update_procurement_total_on_delete(sender, instance, **kwargs):
    instance.procurement.calculate_total()

# Wholesale Procurement signal handlers
@receiver(post_save, sender=WholesaleProcurementItem)
def update_wholesale_procurement_total(sender, instance, created, **kwargs):
    instance.procurement.calculate_total()

@receiver(pre_delete, sender=WholesaleProcurementItem)
def update_wholesale_procurement_total_on_delete(sender, instance, **kwargs):
    instance.procurement.calculate_total()
