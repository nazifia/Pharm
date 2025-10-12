from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from store.models import Cashier

User = get_user_model()

class Command(BaseCommand):
    help = 'Set up the cashier workflow and create test data'

    def add_arguments(self, parser):
        parser.add_argument('--create-test-cashier', action='store_true', 
                          help='Create a test cashier user')
        parser.add_argument('--username', type=str, 
                          help='Username to make a cashier')

    def handle(self, *args, **options):
        if options['create_test_cashier']:
            self.create_test_cashier()
        elif options['username']:
            self.make_user_cashier(options['username'])
        else:
            self.stdout.write("Use --create-test-cashier to create a test cashier or --username <username> to make an existing user a cashier.")

    def create_test_cashier(self):
        """Create a test cashier user"""
        try:
            # Create or get the test user
            username = 'test_cashier'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'mobile': '+12345678901',
                    'first_name': 'Test',
                    'last_name': 'Cashier',
                }
            )
            
            if created:
                # Set a password for the new user
                user.set_password('cashier123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created test user: {username}'))
            else:
                self.stdout.write(f'Using existing user: {username}')

            # Set profile to cashier
            from userauth.models import Profile
            
            try:
                profile = user.profile
            except Profile.DoesNotExist:
                profile = Profile.objects.create(user=user)
            
            profile.user_type = 'Cashier'
            profile.full_name = 'Test Cashier'
            profile.save()
            
            # Create cashier profile
            cashier, created = Cashier.objects.get_or_create(
                user=user,
                defaults={
                    'name': 'Test Cashier',
                    'is_active': True,
                }
            )
            
            self.stdout.write(self.style.SUCCESS(
                f'Successfully set up cashier {username}:\n'
                f'  - User Type: Cashier\n'
                f'  - Cashier ID: {cashier.cashier_id}\n'
                f'  - Name: {cashier.name}\n'
                f'  - Active: {cashier.is_active}\n'
                f'  - Password: cashier123'
            ))
            
            self.stdout.write(self.style.WARNING(
                '\nYou can now:\n'
                f'1. Log in as {username} with password: cashier123\n'
                f'2. Access the cashier dashboard at /store/cashier_dashboard/\n'
                f'3. View payment requests at /store/payment_requests/\n'
            ))
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating test cashier: {str(e)}')
            )

    def make_user_cashier(self, username):
        """Make an existing user a cashier"""
        try:
            user = User.objects.get(username=username)
            
            # Set profile to cashier
            from userauth.models import Profile
            
            try:
                profile = user.profile
            except Profile.DoesNotExist:
                profile = Profile.objects.create(user=user)
            
            profile.user_type = 'Cashier'
            profile.save()
            
            # Create cashier profile
            cashier, created = Cashier.objects.get_or_create(
                user=user,
                defaults={
                    'name': f'{user.get_full_name() or user.username}',
                    'is_active': True,
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully created cashier profile for {username}: {cashier.cashier_id}'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'User {username} is already a cashier: {cashier.cashier_id}'
                ))
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" does not exist.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error setting up cashier: {str(e)}')
            )
