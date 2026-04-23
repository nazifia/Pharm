from django.apps import AppConfig


class SubscriptionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'subscription'
    verbose_name = 'Subscription'

    def ready(self):
        import subscription.signals  # noqa: F401 — wire signals
