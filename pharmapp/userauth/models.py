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
    ('Wholesale Manager', 'Wholesale Manager'),
    ('Wholesale Operator', 'Wholesale Operator'),
    ('Wholesale Salesperson', 'Wholesale Salesperson'),
]

# Define specific permissions for each user type
USER_PERMISSIONS = {
    'Admin': [
        'manage_users', 'view_financial_reports', 'manage_system_settings',
        'access_admin_panel', 'manage_inventory', 'dispense_medication',
        'process_sales', 'view_reports', 'approve_procurement', 'manage_suppliers',
        'manage_expenses', 'adjust_prices', 'process_returns', 'approve_returns',
        'transfer_stock', 'view_activity_logs', 'edit_user_profiles',
        'manage_payment_methods', 'process_split_payments', 'override_payment_status',
        'pause_resume_procurement', 'search_items',
        # All-access permissions for Admins
        'operate_all', 'manage_all_customers', 'manage_all_procurement',
        'manage_all_stock_checks', 'manage_all_expiry'
    ],
    'Manager': [
        'view_financial_reports', 'manage_inventory', 'process_sales', 'view_reports',
        'approve_procurement', 'manage_suppliers', 'manage_expenses', 'adjust_prices',
        'process_returns', 'approve_returns', 'transfer_stock', 'view_activity_logs',
        'manage_payment_methods', 'process_split_payments', 'override_payment_status',
        'pause_resume_procurement', 'search_items',
        # All-access permissions for Managers
        'operate_all', 'manage_all_customers', 'manage_all_procurement',
        'manage_all_stock_checks', 'manage_all_expiry'
    ],
    'Pharmacist': [
        'manage_inventory', 'dispense_medication', 'process_sales', 'adjust_prices',
        'process_returns', 'transfer_stock', 'view_sales_history', 'view_procurement_history',
        'process_split_payments', 'search_items',
        # Retail-only permissions by default
        'operate_retail', 'manage_retail_customers', 'manage_retail_procurement',
        'manage_retail_stock_checks', 'manage_retail_expiry'
    ],
    'Pharm-Tech': [
        'manage_inventory', 'process_sales', 'process_returns', 'transfer_stock',
        'view_sales_history', 'perform_stock_check', 'process_split_payments', 'search_items',
        # Retail-only permissions by default (removed procurement permissions only)
        'operate_retail', 'manage_retail_customers', 'manage_retail_stock_checks', 'manage_retail_expiry'
    ],
    'Salesperson': [
        'process_sales', 'view_sales_history', 'process_split_payments', 'search_items',
        # Retail-only permissions by default
        'operate_retail', 'manage_retail_customers', 'manage_retail_expiry'
    ],
    'Wholesale Manager': [
        'view_financial_reports', 'manage_inventory', 'process_sales', 'view_reports',
        'approve_procurement', 'manage_suppliers', 'manage_expenses', 'adjust_prices',
        'process_returns', 'approve_returns', 'transfer_stock', 'view_activity_logs',
        'manage_payment_methods', 'process_split_payments', 'override_payment_status',
        'pause_resume_procurement', 'search_items',
        # Wholesale-only permissions
        'operate_wholesale', 'manage_wholesale_customers', 'manage_wholesale_procurement',
        'manage_wholesale_stock_checks', 'manage_wholesale_expiry'
    ],
    'Wholesale Operator': [
        'manage_inventory', 'process_sales', 'adjust_prices', 'process_returns',
        'transfer_stock', 'view_sales_history', 'view_procurement_history',
        'process_split_payments', 'search_items',
        # Wholesale-only permissions
        'operate_wholesale', 'manage_wholesale_customers', 'manage_wholesale_procurement',
        'manage_wholesale_stock_checks', 'manage_wholesale_expiry'
    ],
    'Wholesale Salesperson': [
        'process_sales', 'view_sales_history', 'process_split_payments', 'search_items',
        # Wholesale-only permissions
        'operate_wholesale', 'manage_wholesale_customers', 'manage_wholesale_expiry'
    ]
}

# Create your models here.
class User(AbstractUser):
    username = models.CharField(max_length=200, null=True, blank=True)
    mobile = models.CharField(max_length=20, unique=True)

    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username if self.username else self.mobile

    def has_permission(self, permission):
        """Check if user has a specific permission based on their role and individual permissions"""
        if not hasattr(self, 'profile') or not self.profile:
            # Create a default profile if none exists
            Profile.objects.get_or_create(user=self, defaults={
                'full_name': self.username or self.mobile,
                'user_type': 'Salesperson'  # Default role
            })
            # Refresh to get the new profile
            self.refresh_from_db()

        if not self.profile.user_type:
            return False

        # Check role-based permissions first
        user_permissions = USER_PERMISSIONS.get(self.profile.user_type, [])
        has_role_permission = permission in user_permissions

        # Check individual permissions (these can override role permissions)
        try:
            custom_permission = self.custom_permissions.get(permission=permission)
            # Individual permission overrides role permission
            return custom_permission.granted
        except UserPermission.DoesNotExist:
            # No individual permission set, use role-based permission
            return has_role_permission

    def get_permissions(self):
        """Get all effective permissions for the user (role-based + individual)"""
        if not hasattr(self, 'profile') or not self.profile.user_type:
            return []

        # Start with role-based permissions
        role_permissions = set(USER_PERMISSIONS.get(self.profile.user_type, []))

        # Apply individual permission overrides
        for custom_perm in self.custom_permissions.all():
            if custom_perm.granted:
                role_permissions.add(custom_perm.permission)
            else:
                role_permissions.discard(custom_perm.permission)

        return list(role_permissions)

    def get_role_permissions(self):
        """Get only role-based permissions"""
        if not hasattr(self, 'profile') or not self.profile.user_type:
            return []
        return USER_PERMISSIONS.get(self.profile.user_type, [])

    def get_individual_permissions(self):
        """Get individual permission assignments"""
        return {
            perm.permission: perm.granted
            for perm in self.custom_permissions.all()
        }



@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance, defaults={
            'full_name': instance.username or instance.mobile,
            'user_type': 'Salesperson'  # Default role for new users
        })

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Ensure profile exists before trying to access it
    if hasattr(instance, 'profile'):
        # If the user is a superuser, set the user_type to 'Admin'
        if instance.is_superuser and instance.profile.user_type != 'Admin':
            instance.profile.user_type = 'Admin'
            instance.profile.save()



class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='uploads/images/', blank=True, null=True)
    full_name = models.CharField(max_length=200, blank=True, null=True)
    user_type = models.CharField(max_length=200, choices=USER_TYPE, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True, help_text="Department or section")
    employee_id = models.CharField(max_length=50, blank=True, null=True, unique=True, help_text="Employee ID number")
    hire_date = models.DateField(blank=True, null=True, help_text="Date of employment")
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f'{self.user.username} ({self.user_type})'

    def get_role_permissions(self):
        """Get permissions for this user's role"""
        return USER_PERMISSIONS.get(self.user_type, [])

    def has_permission(self, permission):
        """Check if this profile's user type has a specific permission"""
        return permission in self.get_role_permissions()

    class Meta:
        ordering = ['-created_at']


class UserPermission(models.Model):
    """Model to store individual user permissions beyond role-based permissions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_permissions')
    permission = models.CharField(max_length=100, help_text="Permission name")
    granted = models.BooleanField(default=True, help_text="Whether permission is granted or revoked")
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='permissions_granted')
    granted_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True, help_text="Optional notes about this permission assignment")

    class Meta:
        unique_together = ['user', 'permission']
        ordering = ['-granted_at']

    def __str__(self):
        status = "Granted" if self.granted else "Revoked"
        return f'{self.user.username} - {self.permission} ({status})'


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
