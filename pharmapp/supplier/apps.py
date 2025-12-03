from django.apps import AppConfig


class SupplierConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'supplier'

    def ready(self):
        """Import signal handlers when the app is ready."""
        import supplier.signals  # noqa: F401
