from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.db.models.signals import post_save, pre_save
from django.contrib.auth.models import AbstractUser


USER_TYPE = [
    ('Admin', 'Admin'),
    ('Manager', 'Manager'),
    ('Pharmacist', 'Pharmacist'),
    ('Pharm-Tech', 'Pharm-Tech'),
    ('Salesperson', 'Salesperson'),
]

# Create your models here.
class User(AbstractUser):
    username = models.CharField(max_length=200, null=True, blank=True)
    mobile = models.CharField(max_length=20, unique=True)

    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username if self.username else self.mobile



@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # If the user is a superuser, set the user_type to 'Admin'
    if instance.is_superuser and instance.profile.user_type != 'Admin':
        instance.profile.user_type = 'Admin'

    instance.profile.save()



class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='uploads/images/', blank=True, null=True)
    full_name = models.CharField(max_length=200, blank=True, null=True)
    user_type = models.CharField(max_length=200, choices=USER_TYPE, blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} {self.user_type}'


class ActivityLog(models.Model):
    """
    Model to track user activities in the system.
    Stores detailed information about user actions for auditing and monitoring.
    """
    ACTION_TYPES = [
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
        ('EXPORT', 'Export'),
        ('IMPORT', 'Import'),
        ('TRANSFER', 'Transfer'),
        ('PAYMENT', 'Payment'),
        ('OTHER', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=255)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, default='OTHER')
    target_model = models.CharField(max_length=100, blank=True, null=True, help_text="The model affected by this action")
    target_id = models.CharField(max_length=100, blank=True, null=True, help_text="The ID of the affected object")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['action_type']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.action_type} - {self.action} - {self.timestamp}"

    @classmethod
    def log_activity(cls, user, action, action_type='OTHER', target_model=None, target_id=None,
                    ip_address=None, user_agent=None):
        """
        Helper method to create activity log entries.
        """
        return cls.objects.create(
            user=user,
            action=action,
            action_type=action_type,
            target_model=target_model,
            target_id=target_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
