from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from .models import ANNUAL_PRICE, Subscription, PaymentRecord, SubscriptionConfig, generate_license_key


# ── Inline ────────────────────────────────────────────────────────────────────

class PaymentRecordInline(admin.TabularInline):
    model = PaymentRecord
    extra = 1
    readonly_fields = ('created_at',)
    fields = (
        'payment_date', 'amount', 'payment_method', 'reference',
        'period_start', 'period_end', 'recorded_by', 'notes', 'created_at',
    )

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields


# ── Renewal form ──────────────────────────────────────────────────────────────

class RenewSubscriptionForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10, decimal_places=2,
        min_value=Decimal('1'),
        label='Amount (₦)',
        initial=ANNUAL_PRICE,
    )
    payment_method = forms.ChoiceField(choices=PaymentRecord.PAYMENT_METHOD_CHOICES)
    reference = forms.CharField(max_length=100, required=False, label='Reference / Receipt No.')
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)


# ── SubscriptionAdmin ─────────────────────────────────────────────────────────

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'pharmacy_name', 'contact_mobile', 'status_badge',
        'start_date', 'end_date', 'days_left', 'active_check', 'license_key',
    )
    list_filter = ('status',)
    search_fields = ('pharmacy_name', 'contact_mobile', 'license_key')
    readonly_fields = (
        'license_key', 'created_at', 'updated_at',
        'days_left', 'active_check', 'grace_end_date_display',
    )
    inlines = [PaymentRecordInline]
    actions = ['action_sync_status', 'action_extend_one_year', 'action_regenerate_license']

    fieldsets = (
        ('Pharmacy', {
            'fields': ('pharmacy_name', 'contact_mobile', 'activated_by'),
        }),
        ('Subscription Period', {
            'fields': ('status', 'start_date', 'end_date', 'grace_period_days'),
        }),
        ('Computed Status', {
            'fields': ('days_left', 'active_check', 'grace_end_date_display'),
            'classes': ('collapse',),
        }),
        ('License', {
            'fields': ('license_key',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    # ── list display helpers ─────────────────────────────────────────────────

    def days_left(self, obj):
        return obj.days_remaining
    days_left.short_description = 'Days Left'

    def active_check(self, obj):
        return obj.is_active
    active_check.boolean = True
    active_check.short_description = 'Active?'

    def grace_end_date_display(self, obj):
        return obj.grace_end_date
    grace_end_date_display.short_description = 'Grace End Date'

    def status_badge(self, obj):
        colors = {
            'trial': '#2196F3',
            'active': '#4CAF50',
            'grace': '#FF9800',
            'expired': '#F44336',
        }
        color = colors.get(obj.status, '#9E9E9E')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color, obj.get_status_display(),
        )
    status_badge.short_description = 'Status'

    # ── save hook ────────────────────────────────────────────────────────────

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.sync_status()

    # ── permission guard ─────────────────────────────────────────────────────

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    # ── custom URLs ──────────────────────────────────────────────────────────

    def get_urls(self):
        custom = [
            path(
                '<int:pk>/renew/',
                self.admin_site.admin_view(self.renew_view),
                name='subscription_subscription_renew',
            ),
        ]
        return custom + super().get_urls()

    def renew_view(self, request, pk):
        sub = Subscription.objects.get(pk=pk)
        if request.method == 'POST':
            form = RenewSubscriptionForm(request.POST)
            if form.is_valid():
                sub.renew(
                    recorded_by=request.user,
                    amount=form.cleaned_data['amount'],
                    payment_method=form.cleaned_data['payment_method'],
                    reference=form.cleaned_data['reference'],
                    notes=form.cleaned_data['notes'],
                )
                messages.success(
                    request,
                    f'Subscription renewed. New end date: {sub.end_date}.',
                )
                return redirect(
                    reverse('admin:subscription_subscription_change', args=[pk])
                )
        else:
            form = RenewSubscriptionForm()

        context = {
            **self.admin_site.each_context(request),
            'title': f'Renew: {sub.pharmacy_name}',
            'sub': sub,
            'form': form,
            'opts': self.model._meta,
        }
        return render(request, 'admin/subscription/renew.html', context)

    # ── change-list link ─────────────────────────────────────────────────────

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['renew_url'] = reverse(
            'admin:subscription_subscription_renew', args=[object_id]
        )
        return super().change_view(request, object_id, form_url, extra_context)

    # ── actions ──────────────────────────────────────────────────────────────

    @admin.action(description='Sync status based on current date')
    def action_sync_status(self, request, queryset):
        count = 0
        for sub in queryset:
            old = sub.status
            sub.sync_status()
            if sub.status != old:
                count += 1
        self.message_user(request, f'Synced {queryset.count()} subscription(s); {count} status(es) changed.')

    @admin.action(description='Extend selected subscriptions by 1 year')
    def action_extend_one_year(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, 'Superuser only.', level=messages.ERROR)
            return
        for sub in queryset:
            sub.end_date = sub.end_date + timedelta(days=365)
            if sub.status == 'expired':
                sub.status = 'active'
            sub.save(update_fields=['end_date', 'status', 'updated_at'])
        self.message_user(request, f'Extended {queryset.count()} subscription(s) by 1 year.')

    @admin.action(description='Regenerate license key (superuser only)')
    def action_regenerate_license(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, 'Superuser only.', level=messages.ERROR)
            return
        for sub in queryset:
            sub.license_key = generate_license_key()
            sub.save(update_fields=['license_key', 'updated_at'])
        self.message_user(request, f'Regenerated license key for {queryset.count()} subscription(s).')


# ── PaymentRecordAdmin ────────────────────────────────────────────────────────

@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = (
        'subscription', 'amount', 'payment_date', 'payment_method',
        'reference', 'period_start', 'period_end', 'recorded_by',
    )
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('subscription__pharmacy_name', 'reference')
    readonly_fields = ('created_at',)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(SubscriptionConfig)
class SubscriptionConfigAdmin(admin.ModelAdmin):
    list_display = ('annual_price', 'updated_at', 'updated_by')
    readonly_fields = ('updated_at', 'updated_by')

    def has_add_permission(self, request):
        return request.user.is_superuser and not SubscriptionConfig.objects.exists()

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False
