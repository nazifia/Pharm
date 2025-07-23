"""
Notification service for managing system notifications
"""
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Notification, Item, WholesaleItem, StoreSettings, WholesaleSettings

User = get_user_model()


class NotificationService:
    """Service class for managing notifications"""
    
    @staticmethod
    def create_notification(notification_type, title, message, user=None, priority='medium', 
                          related_item=None, related_wholesale_item=None):
        """Create a new notification"""
        return Notification.objects.create(
            user=user,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            related_item=related_item,
            related_wholesale_item=related_wholesale_item
        )
    
    @staticmethod
    def create_low_stock_notification(item, is_wholesale=False):
        """Create a low stock notification for an item"""
        if is_wholesale:
            title = f"Low Stock Alert: {item.name}"
            message = f"Wholesale item '{item.name}' is running low on stock. Current stock: {item.stock} {item.unit}"
            return NotificationService.create_notification(
                notification_type='low_stock',
                title=title,
                message=message,
                priority='high',
                related_wholesale_item=item
            )
        else:
            title = f"Low Stock Alert: {item.name}"
            message = f"Retail item '{item.name}' is running low on stock. Current stock: {item.stock} {item.unit}"
            return NotificationService.create_notification(
                notification_type='low_stock',
                title=title,
                message=message,
                priority='high',
                related_item=item
            )
    
    @staticmethod
    def create_out_of_stock_notification(item, is_wholesale=False):
        """Create an out of stock notification for an item"""
        if is_wholesale:
            title = f"Out of Stock: {item.name}"
            message = f"Wholesale item '{item.name}' is completely out of stock!"
            return NotificationService.create_notification(
                notification_type='out_of_stock',
                title=title,
                message=message,
                priority='critical',
                related_wholesale_item=item
            )
        else:
            title = f"Out of Stock: {item.name}"
            message = f"Retail item '{item.name}' is completely out of stock!"
            return NotificationService.create_notification(
                notification_type='out_of_stock',
                title=title,
                message=message,
                priority='critical',
                related_item=item
            )
    
    @staticmethod
    def check_and_create_stock_notifications():
        """Check all items and create notifications for low/out of stock items"""
        notifications_created = 0
        
        # Get settings
        store_settings = StoreSettings.get_settings()
        wholesale_settings = WholesaleSettings.get_settings()
        
        # Check retail items
        retail_items = Item.objects.all()
        for item in retail_items:
            # Skip if notification already exists for this item in the last 24 hours
            recent_notification = Notification.objects.filter(
                related_item=item,
                notification_type__in=['low_stock', 'out_of_stock'],
                created_at__gte=timezone.now() - timezone.timedelta(hours=24)
            ).exists()
            
            if recent_notification:
                continue
            
            if item.stock == 0:
                NotificationService.create_out_of_stock_notification(item, is_wholesale=False)
                notifications_created += 1
            elif item.stock <= store_settings.low_stock_threshold:
                NotificationService.create_low_stock_notification(item, is_wholesale=False)
                notifications_created += 1
        
        # Check wholesale items
        wholesale_items = WholesaleItem.objects.all()
        for item in wholesale_items:
            # Skip if notification already exists for this item in the last 24 hours
            recent_notification = Notification.objects.filter(
                related_wholesale_item=item,
                notification_type__in=['low_stock', 'out_of_stock'],
                created_at__gte=timezone.now() - timezone.timedelta(hours=24)
            ).exists()
            
            if recent_notification:
                continue
            
            if item.stock == 0:
                NotificationService.create_out_of_stock_notification(item, is_wholesale=True)
                notifications_created += 1
            elif item.stock <= wholesale_settings.low_stock_threshold:
                NotificationService.create_low_stock_notification(item, is_wholesale=True)
                notifications_created += 1
        
        return notifications_created
    
    @staticmethod
    def get_unread_notifications(user=None):
        """Get unread notifications for a user or system-wide"""
        queryset = Notification.objects.filter(is_read=False, is_dismissed=False)
        if user:
            queryset = queryset.filter(user__in=[user, None])  # User-specific or system-wide
        else:
            queryset = queryset.filter(user=None)  # Only system-wide
        return queryset
    
    @staticmethod
    def get_unread_count(user=None):
        """Get count of unread notifications"""
        return NotificationService.get_unread_notifications(user).count()
    
    @staticmethod
    def mark_all_as_read(user=None):
        """Mark all notifications as read for a user"""
        queryset = Notification.objects.filter(is_read=False, is_dismissed=False)
        if user:
            queryset = queryset.filter(user__in=[user, None])
        else:
            queryset = queryset.filter(user=None)
        
        updated = queryset.update(is_read=True, read_at=timezone.now())
        return updated
    
    @staticmethod
    def dismiss_old_notifications(days=30):
        """Dismiss notifications older than specified days"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        old_notifications = Notification.objects.filter(
            created_at__lt=cutoff_date,
            is_dismissed=False
        )
        updated = old_notifications.update(is_dismissed=True, dismissed_at=timezone.now())
        return updated
    
    @staticmethod
    def create_system_message(title, message, priority='medium'):
        """Create a system-wide message notification"""
        return NotificationService.create_notification(
            notification_type='system_message',
            title=title,
            message=message,
            priority=priority
        )


def check_stock_and_notify():
    """Convenience function to check stock and create notifications"""
    return NotificationService.check_and_create_stock_notifications()
