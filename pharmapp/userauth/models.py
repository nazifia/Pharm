from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.db.models.signals import post_save
from django.contrib.auth.models import AbstractUser


USER_TYPE = [
    ('Admin', 'Admin'),
    ('Pharmacist', 'Pharmacist'),
    ('Pharm-Tech', 'Pharm-Tech'),
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
    instance.profile.save()



class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='uploads/images/', blank=True, null=True)
    full_name = models.CharField(max_length=200, blank=True, null=True)
    user_type = models.CharField(max_length=200, choices=USER_TYPE, blank=True, null=True)
    
    def __str__(self):
        return f'{self.user.username} {self.user_type}'


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"
