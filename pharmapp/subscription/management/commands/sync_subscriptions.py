"""
Management command: sync subscription statuses and fire expiry notifications.

Run daily via cron:
    python manage.py sync_subscriptions

Or via Windows Task Scheduler / systemd timer.
"""
from datetime import date

from django.core.management.base import BaseCommand

from subscription.models import Subscription


class Command(BaseCommand):
    help = 'Sync subscription statuses and create expiry notifications.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would change without saving.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        subscriptions = list(Subscription.objects.all())

        if not subscriptions:
            self.stdout.write(self.style.WARNING('No subscriptions found.'))
            return

        changed = 0
        for sub in subscriptions:
            old_status = sub.status
            if dry_run:
                # Compute what status would be without saving
                today = date.today()
                if sub.end_date >= today:
                    new_status = 'trial' if sub.status == 'trial' else 'active'
                elif sub.grace_end_date >= today:
                    new_status = 'grace'
                else:
                    new_status = 'expired'
                if new_status != old_status:
                    self.stdout.write(
                        f'  {sub.pharmacy_name}: {old_status} → {new_status} (dry run)'
                    )
                    changed += 1
            else:
                sub.sync_status()
                if sub.status != old_status:
                    changed += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  {sub.pharmacy_name}: {old_status} → {sub.status}')
                    )

        if not dry_run:
            self._send_expiring_soon_notification(subscriptions)

        label = 'dry run' if dry_run else 'updated'
        self.stdout.write(
            self.style.SUCCESS(
                f'Done. Checked {len(subscriptions)} subscription(s); {changed} status(es) {label}.'
            )
        )

    def _send_expiring_soon_notification(self, subscriptions):
        """
        Create a system notification when any active subscription is expiring soon.
        Deduplicates: at most one such notification per calendar day.
        """
        try:
            from store.models import Notification
        except ImportError:
            return

        today = date.today()
        for sub in subscriptions:
            if not sub.is_expiring_soon:
                continue

            already_notified = Notification.objects.filter(
                notification_type='system_message',
                title__startswith='Subscription Expiring',
                created_at__date=today,
            ).exists()

            if already_notified:
                continue

            Notification.objects.create(
                user=None,
                notification_type='system_message',
                priority='high',
                title=f'Subscription Expiring in {sub.days_remaining} Day(s)',
                message=(
                    f'The subscription for {sub.pharmacy_name} expires on {sub.end_date}. '
                    f'Renew before {sub.end_date} to avoid service disruption. '
                    f'After expiry there is a {sub.grace_period_days}-day grace period.'
                ),
            )
            self.stdout.write(
                self.style.WARNING(
                    f'  Expiry alert created for {sub.pharmacy_name} ({sub.days_remaining} days left).'
                )
            )
