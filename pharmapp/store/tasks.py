from celery import shared_task
from django.db import transaction
from .models import SyncLog
import logging

logger = logging.getLogger(__name__)

@shared_task
def sync_databases():
    try:
        with transaction.atomic():
            # Get all unsynced records
            unsynced_records = SyncLog.objects.filter(synced=False)
            
            for record in unsynced_records:
                try:
                    # Apply changes to online database
                    record.apply_changes()
                    record.synced = True
                    record.save()
                except Exception as e:
                    logger.error(f"Failed to sync record {record.id}: {str(e)}")
                    record.retry_count += 1
                    record.save()
                    
            return f"Synced {unsynced_records.count()} records"
    except Exception as e:
        logger.error(f"Sync failed: {str(e)}")
        raise