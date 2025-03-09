# from django.db import models
# from django.utils import timezone
# from shortuuid.django_fields import ShortUUIDField

# class WholesaleReceipt(models.Model):
#     PAYMENT_METHODS = [
#         ('Cash', 'Cash'),
#         ('Transfer', 'Transfer'),
#         ('Wallet', 'Wallet'),
#     ]
    
#     STATUS_CHOICES = [
#         ('Paid', 'Paid'),
#         ('Unpaid', 'Unpaid'),
#     ]

#     receipt_id = ShortUUIDField(unique=True, length=10, prefix="WRID:", max_length=20)
#     sales = models.OneToOneField('wholesale.WholesaleSales', on_delete=models.CASCADE, related_name='receipt')
#     wholesale_customer = models.ForeignKey('customer.WholesaleCustomer', on_delete=models.SET_NULL, null=True, blank=True)
#     total_amount = models.DecimalField(max_digits=10, decimal_places=2)
#     buyer_name = models.CharField(max_length=255, null=True, blank=True)
#     buyer_address = models.TextField(null=True, blank=True)
#     date = models.DateTimeField(default=timezone.now)
#     payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='Cash')
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Paid')
#     printed = models.BooleanField(default=False)
    
#     # New fields for returns
#     has_returns = models.BooleanField(default=False)
#     return_notes = models.TextField(blank=True, null=True)
#     last_modified = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ['-date']

#     def __str__(self):
#         return f"Wholesale Receipt {self.receipt_id} - {self.buyer_name or 'Unknown'}"

#     def save(self, *args, **kwargs):
#         if not self.buyer_name and self.wholesale_customer:
#             self.buyer_name = self.wholesale_customer.name
#         super().save(*args, **kwargs)
# # Create your models here.
