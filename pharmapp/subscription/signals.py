from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Subscription

_STATUS_PRIORITY = {
    'grace': 'high',
    'expired': 'critical',
    'active': 'medium',
    'trial': 'low',
}

_STATUS_MESSAGES = {
    'grace': (
        'Subscription in Grace Period',
        'Subscription has expired and entered the grace period. Renew immediately to avoid lockout.',
    ),
    'expired': (
        'Subscription Expired',
        'Subscription has expired. All non-admin users are locked out. Renew to restore access.',
    ),
    'active': (
        'Subscription Renewed',
        'Subscription is now active. Access restored for all users.',
    ),
}


@receiver(pre_save, sender=Subscription)
def _capture_old_status(sender, instance, **kwargs):
    """Snapshot status before save so post_save can detect transitions."""
    if instance.pk:
        try:
            instance._pre_save_status = Subscription.objects.get(pk=instance.pk).status
        except Subscription.DoesNotExist:
            instance._pre_save_status = None
    else:
        instance._pre_save_status = None


@receiver(post_save, sender=Subscription)
def _notify_on_status_change(sender, instance, created, **kwargs):
    """Create a system-wide Notification whenever subscription status transitions."""
    if created:
        return

    old_status = getattr(instance, '_pre_save_status', None)
    if old_status is None or old_status == instance.status:
        return

    if instance.status not in _STATUS_MESSAGES:
        return

    try:
        from store.models import Notification
        title, message = _STATUS_MESSAGES[instance.status]
        Notification.objects.create(
            user=None,
            notification_type='system_message',
            priority=_STATUS_PRIORITY.get(instance.status, 'medium'),
            title=title,
            message=message,
        )
    except Exception:
        pass
