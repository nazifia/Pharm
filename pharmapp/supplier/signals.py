"""
Signal handlers for automatic barcode transfer from procurement to inventory items.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from supplier.models import ProcurementItem, WholesaleProcurementItem
from store.models import Item, WholesaleItem


@receiver(post_save, sender=ProcurementItem)
def transfer_barcode_to_retail_item(sender, instance, created, **kwargs):
    """
    When a ProcurementItem is saved with a barcode, attempt to update
    the corresponding retail Item if it exists.

    Only processes completed procurements to avoid premature updates.
    """
    if not instance.barcode:
        return

    # Only process for completed procurements
    if not instance.procurement or instance.procurement.status != 'completed':
        return

    try:
        # Find matching retail items by name, brand, dosage_form (case-insensitive)
        items = Item.objects.filter(
            name__iexact=instance.item_name,
            brand__iexact=instance.brand,
            dosage_form=instance.dosage_form
        )

        for item in items:
            # Only update if item doesn't have a barcode
            if not item.barcode:
                item.barcode = instance.barcode
                item.save(update_fields=['barcode'])
                print(f"[Signal] Transferred barcode {instance.barcode} to retail item {item.name}")

    except Exception as e:
        print(f"[Signal] Error transferring barcode to retail item: {e}")


@receiver(post_save, sender=WholesaleProcurementItem)
def transfer_barcode_to_wholesale_item(sender, instance, created, **kwargs):
    """
    When a WholesaleProcurementItem is saved with a barcode, attempt to update
    the corresponding WholesaleItem if it exists.

    Only processes completed procurements to avoid premature updates.
    """
    if not instance.barcode:
        return

    # Only process for completed procurements
    if not instance.procurement or instance.procurement.status != 'completed':
        return

    try:
        # Find matching wholesale items by name, brand, dosage_form (case-insensitive)
        items = WholesaleItem.objects.filter(
            name__iexact=instance.item_name,
            brand__iexact=instance.brand,
            dosage_form=instance.dosage_form
        )

        for item in items:
            # Only update if item doesn't have a barcode
            if not item.barcode:
                item.barcode = instance.barcode
                item.save(update_fields=['barcode'])
                print(f"[Signal] Transferred barcode {instance.barcode} to wholesale item {item.name}")

    except Exception as e:
        print(f"[Signal] Error transferring barcode to wholesale item: {e}")
