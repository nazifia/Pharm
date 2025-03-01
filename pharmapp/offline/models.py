from django.db import models
from django.utils import timezone

class OfflineAction(models.Model):
    ACTION_TYPES = (
        ('add_customer', 'Add Customer'),
        ('register_sale', 'Register Sale'),
        ('update_stock', 'Update Stock'),
        ('wholesale_purchase', 'Wholesale Purchase'),
        ('add_wholesale_customer', 'Add Wholesale Customer'),
    )
    
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    data = models.JSONField()  # Store the action data as JSON
    timestamp = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.action_type} - {self.timestamp}"
from django.db import models


