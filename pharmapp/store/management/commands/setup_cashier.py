from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from store.models import Cashier

User = get_user_model()

class Command(BaseCommand):
    help = 'Set up a user as a cashier'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the user to make a cashier')
        parser.add_argument('--name', type=str, help='Cashier display name (defaults to username)')
        parser.add_argument('--list', action='store_true', help='List all existing cashiers')

    def handle(self, *args, **options):
        if options['list']:
            self.list_cashiers()
            return

        username = options['username']
        cashier_name = options.get('name', username)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" does not exist.')
            )
            return

        # Check if user is already a cashier
        if hasattr(user, 'cashier'):
            self.stdout.write(
                self.style.WARNING(f'User "{username}" is already a cashier.')
            )
            self.stdout.write(f'  Cashier ID: {user.cashier.cashier_id}')
            self.stdout.write(f'  Name: {user.cashier.name}')
            self.stdout.write(f'  Active: {user.cashier.is_active}')
            return

        # Create cashier profile
        cashier = Cashier.objects.create(
            user=user,
            name=cashier_name,
            is_active=True
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created cashier profile for "{username}":\n'
                f'  Cashier ID: {cashier.cashier_id}\n'
                f'  Name: {cashier.name}\n'
                f'  Active: {cashier.is_active}'
            )
        )

    def list_cashiers(self):
        cashiers = Cashier.objects.select_related('user').all()
        
        if not cashiers.exists():
            self.stdout.write(
                self.style.WARNING('No cashiers found in the system.')
            )
            return

        self.stdout.write(self.style.SUCCESS('Existing Cashiers:'))
        for cashier in cashiers:
            status = "Active" if cashier.is_active else "Inactive"
            self.stdout.write(
                f'  • {cashier.user.username} ({cashier.cashier_id}) - {cashier.name} - [{status}]'
            )
