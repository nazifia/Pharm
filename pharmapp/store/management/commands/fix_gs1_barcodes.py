"""
Management command to fix existing items with GS1 barcodes
Parses GS1 barcodes and extracts GTIN, batch number, and serial number into separate fields
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from store.models import Item, WholesaleItem
from store.gs1_parser import parse_barcode, is_gs1_barcode
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Parse GS1 barcodes and update item fields (gtin, batch_number, serial_number)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            choices=['retail', 'wholesale', 'both'],
            default='both',
            help='Which items to process: retail, wholesale, or both'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )

    def handle(self, *args, **options):
        mode = options['mode']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))

        # Process retail items
        if mode in ['retail', 'both']:
            self.stdout.write(self.style.MIGRATE_HEADING('\nProcessing Retail Items...'))
            retail_updated = self.process_items(Item, dry_run)
            self.stdout.write(self.style.SUCCESS(f'[OK] Retail: {retail_updated} items updated'))

        # Process wholesale items
        if mode in ['wholesale', 'both']:
            self.stdout.write(self.style.MIGRATE_HEADING('\nProcessing Wholesale Items...'))
            wholesale_updated = self.process_items(WholesaleItem, dry_run)
            self.stdout.write(self.style.SUCCESS(f'[OK] Wholesale: {wholesale_updated} items updated'))

        self.stdout.write(self.style.SUCCESS('\n[OK] Processing complete!'))

    def process_items(self, ItemModel, dry_run=False):
        """Process items and update GS1 barcode components"""
        updated_count = 0

        # Find items with barcodes that look like GS1 format
        items_with_barcodes = ItemModel.objects.filter(barcode__isnull=False).exclude(barcode='')

        self.stdout.write(f'Found {items_with_barcodes.count()} items with barcodes')

        for item in items_with_barcodes:
            if is_gs1_barcode(item.barcode):
                # Parse the GS1 barcode
                parsed = parse_barcode(item.barcode)

                gtin = parsed.get('gtin', '')
                batch_number = parsed.get('batch_number', '')
                serial_number = parsed.get('serial_number', '')

                # Check if we need to update
                needs_update = False
                updates = []

                if gtin and not item.gtin:
                    item.gtin = gtin
                    needs_update = True
                    updates.append(f'gtin={gtin}')

                if batch_number and not item.batch_number:
                    item.batch_number = batch_number
                    needs_update = True
                    updates.append(f'batch={batch_number}')

                if serial_number and not item.serial_number:
                    item.serial_number = serial_number
                    needs_update = True
                    updates.append(f'serial={serial_number}')

                if needs_update and (not item.barcode_type or item.barcode_type == 'OTHER'):
                    item.barcode_type = 'GS1'
                    updates.append('type=GS1')

                if needs_update:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  > {item.name} (ID: {item.id}): {", ".join(updates)}'
                        )
                    )

                    if not dry_run:
                        try:
                            with transaction.atomic():
                                item.save(update_fields=['gtin', 'batch_number', 'serial_number', 'barcode_type'])
                                updated_count += 1
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'    [ERROR] Error updating {item.name}: {str(e)}')
                            )
                            logger.error(f'Error updating item {item.id}: {e}', exc_info=True)
                    else:
                        updated_count += 1

        return updated_count
