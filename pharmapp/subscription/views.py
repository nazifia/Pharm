from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from django.conf import settings as django_settings
from .models import ANNUAL_PRICE, TRIAL_DAYS, PaymentRecord, Subscription, SubscriptionConfig


# ── helpers ──────────────────────────────────────────────────────────────────

def _superuser_only(request):
    return request.user.is_authenticated and request.user.is_superuser


def _admin_or_manager(request):
    if not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    return request.user.has_permission('manage_subscription') or getattr(
        request.user.profile, 'user_type', ''
    ) in ('Admin', 'Manager')


# ── views ─────────────────────────────────────────────────────────────────────

@login_required
def subscription_status(request):
    if not _admin_or_manager(request):
        messages.error(request, 'Access denied.')
        return redirect('store:dashboard')

    sub = Subscription.objects.order_by('-end_date').first()
    payments = sub.payments.all() if sub else []
    config = SubscriptionConfig.get_or_create_default()
    return render(request, 'subscription/status.html', {
        'sub': sub,
        'payments': payments,
        'annual_price': config.annual_price,
    })


def expired_view(request):
    sub = Subscription.objects.order_by('-end_date').first()
    return render(request, 'subscription/expired.html', {
        'sub': sub,
        'is_superuser': request.user.is_authenticated and request.user.is_superuser,
    })


@login_required
def setup_trial(request):
    if not request.user.is_superuser:
        messages.error(request, 'Superuser access required.')
        return redirect('store:dashboard')

    if Subscription.objects.exists():
        messages.info(request, 'Subscription already configured.')
        return redirect('subscription:status')

    if request.method == 'POST':
        pharmacy_name = request.POST.get('pharmacy_name', '').strip()
        contact_mobile = request.POST.get('contact_mobile', '').strip()
        if not pharmacy_name or not contact_mobile:
            messages.error(request, 'Pharmacy name and contact mobile required.')
        else:
            Subscription.setup_trial(pharmacy_name, contact_mobile, activated_by=request.user)
            messages.success(request, 'Trial subscription activated.')
            return redirect('subscription:status')

    config = SubscriptionConfig.get_or_create_default()
    return render(request, 'subscription/setup.html', {
        'trial_days': TRIAL_DAYS,
        'annual_price': config.annual_price,
    })


@login_required
@require_POST
def record_payment(request):
    if not request.user.is_superuser:
        messages.error(request, 'Superuser access required.')
        return redirect('subscription:status')

    sub = Subscription.objects.order_by('-end_date').first()
    if not sub:
        messages.error(request, 'No subscription found. Set up a trial first.')
        return redirect('subscription:setup')

    try:
        amount = Decimal(request.POST.get('amount', '0'))
        if amount <= 0:
            raise InvalidOperation
    except InvalidOperation:
        messages.error(request, 'Invalid amount.')
        return redirect('subscription:status')

    payment_method = request.POST.get('payment_method', 'cash')
    reference = request.POST.get('reference', '').strip()
    notes = request.POST.get('notes', '').strip()

    sub.renew(
        recorded_by=request.user,
        amount=amount,
        payment_method=payment_method,
        reference=reference,
        notes=notes,
    )
    messages.success(
        request,
        f'Payment of ₦{amount:,.0f} recorded. Subscription extended to {sub.end_date}.'
    )
    return redirect('subscription:status')
