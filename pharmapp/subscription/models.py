import uuid
from datetime import date, timedelta
from django.db import models
from django.conf import settings


ANNUAL_PRICE = getattr(settings, 'SUBSCRIPTION_ANNUAL_PRICE', 150000)
GRACE_PERIOD_DAYS = getattr(settings, 'SUBSCRIPTION_GRACE_PERIOD_DAYS', 7)
TRIAL_DAYS = getattr(settings, 'SUBSCRIPTION_TRIAL_DAYS', 30)
RENEWAL_WARNING_DAYS = getattr(settings, 'SUBSCRIPTION_RENEWAL_WARNING_DAYS', 30)


def get_annual_price():
    """Return live annual price from DB config, falling back to settings constant."""
    try:
        config = SubscriptionConfig.objects.first()
        if config:
            return config.annual_price
    except Exception:
        pass
    return ANNUAL_PRICE


def generate_license_key():
    return uuid.uuid4().hex.upper()[:20]


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('expired', 'Expired'),
    ]

    pharmacy_name = models.CharField(max_length=200)
    contact_mobile = models.CharField(max_length=20, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    start_date = models.DateField()
    end_date = models.DateField()
    grace_period_days = models.IntegerField(default=GRACE_PERIOD_DAYS)
    license_key = models.CharField(max_length=50, unique=True, default=generate_license_key)
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='activated_subscriptions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        ordering = ['-end_date']

    def __str__(self):
        return f"{self.pharmacy_name} — {self.get_status_display()} (expires {self.end_date})"

    # ── computed properties ──────────────────────────────────────────────────

    @property
    def is_active(self):
        today = date.today()
        if self.status in ('active', 'trial') and self.end_date >= today:
            return True
        if self.status == 'grace':
            return (self.end_date + timedelta(days=self.grace_period_days)) >= today
        return False

    @property
    def days_remaining(self):
        return max((self.end_date - date.today()).days, 0)

    @property
    def grace_end_date(self):
        return self.end_date + timedelta(days=self.grace_period_days)

    @property
    def is_in_grace_period(self):
        today = date.today()
        return self.end_date < today and self.grace_end_date >= today

    @property
    def is_expiring_soon(self):
        return 0 < self.days_remaining <= RENEWAL_WARNING_DAYS

    # ── methods ─────────────────────────────────────────────────────────────

    def sync_status(self):
        """Recalculate and persist status. Returns True if status changed."""
        today = date.today()
        if self.end_date >= today:
            new_status = 'trial' if self.status == 'trial' else 'active'
        elif self.grace_end_date >= today:
            new_status = 'grace'
        else:
            new_status = 'expired'

        if new_status != self.status:
            self.status = new_status
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False

    def renew(self, recorded_by, amount, payment_method, reference='', notes=''):
        today = date.today()
        period_start = max(self.end_date + timedelta(days=1), today)
        period_end = period_start + timedelta(days=364)

        PaymentRecord.objects.create(
            subscription=self,
            amount=amount,
            payment_date=today,
            payment_method=payment_method,
            reference=reference,
            period_start=period_start,
            period_end=period_end,
            recorded_by=recorded_by,
            notes=notes,
        )

        self.end_date = period_end
        self.status = 'active'
        self.save(update_fields=['end_date', 'status', 'updated_at'])

    @classmethod
    def get_current(cls):
        return (
            cls.objects
            .filter(status__in=['trial', 'active', 'grace'])
            .order_by('-end_date')
            .first()
        )

    @classmethod
    def setup_trial(cls, pharmacy_name, contact_mobile, activated_by=None):
        today = date.today()
        return cls.objects.create(
            pharmacy_name=pharmacy_name,
            contact_mobile=contact_mobile,
            status='trial',
            start_date=today,
            end_date=today + timedelta(days=TRIAL_DAYS),
            activated_by=activated_by,
        )


class PaymentRecord(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('pos', 'POS'),
        ('online', 'Online'),
        ('other', 'Other'),
    ]

    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES)
    reference = models.CharField(max_length=100, blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_payments',
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"₦{self.amount:,.0f} on {self.payment_date} [{self.payment_method}]"


class SubscriptionConfig(models.Model):
    """Singleton model — only one row should exist."""
    annual_price = models.DecimalField(max_digits=12, decimal_places=2, default=ANNUAL_PRICE)
    enforcement_enabled = models.BooleanField(
        default=True,
        help_text=(
            'When OFF, subscription checks are completely skipped — all users can access '
            'the system regardless of subscription status. Turn OFF only for maintenance '
            'or testing. Changes take effect immediately.'
        ),
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='subscription_config_updates',
    )

    class Meta:
        verbose_name = 'Subscription Config'

    def __str__(self):
        enforcement = 'ENFORCED' if self.enforcement_enabled else 'DISABLED'
        return f"Annual Price: ₦{self.annual_price:,.0f} | Enforcement: {enforcement}"

    @classmethod
    def get_or_create_default(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={'annual_price': ANNUAL_PRICE, 'enforcement_enabled': True},
        )
        return obj

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Bust cached enforcement flag so middleware picks up change immediately.
        from django.core.cache import cache
        cache.delete('subscription_enforcement_enabled')
