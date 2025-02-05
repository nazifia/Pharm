from django.db import models
from django.utils import timezone
from userauth.models import User
from store.models import Formulation
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete




# Create your models here.
DOSAGE_FORM = [
    ('Tablet', 'Tablet'),
    ('Capsule', 'Capsule'),
    ('Cream', 'Cream'),
    ('Consumable', 'Consumable'),
    ('Injection', 'Injection'),
    ('Infusion', 'Infusion'),
    ('Inhaler', 'Inhaler'),
    ('Suspension', 'Suspension'),
    ('Syrup', 'Syrup'),
    ('Eye-drop', 'Eye-drop'),
    ('Ear-drop', 'Ear-drop'),
    ('Eye-ointment', 'Eye-ointment'),
    ('Rectal', 'Rectal'),
    ('Vaginal', 'Vaginal'),
]


UNIT = [
    ('Amp', 'Amp'),
    ('Bottle', 'Bottle'),
    ('Tab', 'Tab'),
    ('Tin', 'Tin'),
    ('Caps', 'Caps'),
    ('Card', 'Card'),
    ('Carton', 'Carton'),
    ('Pack', 'Pack'),
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
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f'Procurement {self.supplier.name}'

    def calculate_total(self):
        """Calculate and update the total cost of the procurement."""
        self.total = sum(item.subtotal for item in self.items.all())
        self.save(update_fields=['total'])  # Ensure only 'total' field is updated


class ProcurementItem(models.Model):
    procurement = models.ForeignKey(Procurement, related_name='items', on_delete=models.CASCADE)
    item_name = models.CharField(max_length=255)
    dosage_form = models.CharField(max_length=255, choices=DOSAGE_FORM, default='dosage_form')
    brand = models.CharField(max_length=225, null=True, blank=True, default='None')
    unit = models.CharField(max_length=100, choices=UNIT)
    quantity = models.PositiveIntegerField(default=0)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False)  # Subtotal should not be editable.

    def save(self, *args, **kwargs):
        if self.cost_price is None or self.quantity is None:
            raise ValueError("Both cost_price and quantity must be provided to calculate subtotal.")
        
        # Calculate subtotal
        self.subtotal = self.cost_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.item_name} - {self.procurement.id}'


# Signals to update total in Procurement after changes in ProcurementItem
@receiver(post_save, sender=ProcurementItem)
def update_procurement_total(sender, instance, created, **kwargs):
    """Recalculate the procurement total after adding or updating an item."""
    instance.procurement.calculate_total()

@receiver(pre_delete, sender=ProcurementItem)
def update_procurement_total_on_delete(sender, instance, **kwargs):
    """Recalculate the procurement total after an item is deleted."""
    instance.procurement.calculate_total()



class WholesaleProcurement(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f'Procurement {self.supplier.name}'

    def calculate_total(self):
        """Calculate and update the total cost of the procurement."""
        self.total = sum(item.subtotal for item in self.items.all())
        self.save(update_fields=['total'])  # Ensure only 'total' field is updated


class WholesaleProcurementItem(models.Model):
    procurement = models.ForeignKey(WholesaleProcurement, related_name='items', on_delete=models.CASCADE)
    item_name = models.CharField(max_length=255)
    dosage_form = models.CharField(max_length=255, choices=DOSAGE_FORM, default='dosage_form')
    brand = models.CharField(max_length=225, null=True, blank=True, default='None')
    unit = models.CharField(max_length=100, choices=UNIT)
    quantity = models.PositiveIntegerField(default=0)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False)  # Subtotal should not be editable.

    def save(self, *args, **kwargs):
        if self.cost_price is None or self.quantity is None:
            raise ValueError("Both cost_price and quantity must be provided to calculate subtotal.")
        
        # Calculate subtotal
        self.subtotal = self.cost_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.item_name} - {self.procurement.id}'


# Signals to update total in Procurement after changes in ProcurementItem
@receiver(post_save, sender=WholesaleProcurementItem)
def update_procurement_total(sender, instance, created, **kwargs):
    """Recalculate the procurement total after adding or updating an item."""
    instance.procurement.calculate_total()

@receiver(pre_delete, sender=WholesaleProcurementItem)
def update_procurement_total_on_delete(sender, instance, **kwargs):
    """Recalculate the procurement total after an item is deleted."""
    instance.procurement.calculate_total()
