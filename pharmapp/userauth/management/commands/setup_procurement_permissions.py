from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from userauth.models import UserPermission, Profile

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup procurement permissions for existing users based on their roles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update permissions even if they already exist',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Setup permissions for a specific user (username)',
        )

    def handle(self, *args, **options):
        force = options['force']
        specific_user = options['user']

        self.stdout.write(self.style.SUCCESS('Setting up procurement permissions...'))

        # Define role-based procurement permissions
        role_permissions = {
            'Admin': [
                'manage_retail_procurement',
                'manage_wholesale_procurement', 
                'view_procurement_history'
            ],
            'Manager': [
                'manage_retail_procurement',
                'manage_wholesale_procurement',
                'view_procurement_history'
            ],
            'Pharmacist': [
                'manage_retail_procurement',
                'view_procurement_history'
            ],
            'Pharm-Tech': [
                'view_procurement_history'
            ],
            'Wholesale Manager': [
                'manage_wholesale_procurement',
                'view_procurement_history'
            ],
            'Wholesale Operator': [
                'manage_wholesale_procurement',
                'view_procurement_history'
            ],
            'Salesperson': [],  # No procurement permissions by default
            'Wholesale Salesperson': []  # No procurement permissions by default
        }

        # Get users to process
        if specific_user:
            try:
                users = [User.objects.get(username=specific_user)]
                self.stdout.write(f'Processing user: {specific_user}')
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User "{specific_user}" not found')
                )
                return
        else:
            users = User.objects.select_related('profile').filter(is_active=True)
            self.stdout.write(f'Processing {users.count()} active users')

        updated_count = 0
        created_count = 0

        for user in users:
            # Ensure user has a profile
            if not hasattr(user, 'profile') or not user.profile:
                Profile.objects.get_or_create(
                    user=user,
                    defaults={
                        'full_name': user.username,
                        'user_type': 'Salesperson'
                    }
                )
                user.refresh_from_db()

            user_type = user.profile.user_type
            permissions_to_grant = role_permissions.get(user_type, [])

            self.stdout.write(f'Processing {user.username} ({user_type})')

            for permission in permissions_to_grant:
                user_permission, created = UserPermission.objects.get_or_create(
                    user=user,
                    permission=permission,
                    defaults={
                        'granted': True,
                        'granted_by': None,  # System assignment
                        'notes': f'Auto-assigned based on role: {user_type}'
                    }
                )

                if created:
                    created_count += 1
                    self.stdout.write(
                        f'  ✓ Granted: {permission}'
                    )
                elif not user_permission.granted or force:
                    if force or not user_permission.granted:
                        user_permission.granted = True
                        user_permission.notes = f'Auto-assigned based on role: {user_type} (updated)'
                        user_permission.save()
                        updated_count += 1
                        self.stdout.write(
                            f'  ✓ Updated: {permission}'
                        )
                else:
                    self.stdout.write(
                        f'  - Already has: {permission}'
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Created {created_count} new permissions, '
                f'updated {updated_count} existing permissions.'
            )
        )

        # Show summary of current permissions
        self.stdout.write('\n' + '='*50)
        self.stdout.write('CURRENT PROCUREMENT PERMISSIONS SUMMARY:')
        self.stdout.write('='*50)

        for user in users:
            user_permissions = user.get_permissions()
            procurement_perms = [p for p in user_permissions if 'procurement' in p]
            
            if procurement_perms:
                self.stdout.write(f'{user.username} ({user.profile.user_type}):')
                for perm in procurement_perms:
                    self.stdout.write(f'  - {perm}')
            else:
                self.stdout.write(f'{user.username} ({user.profile.user_type}): No procurement permissions')
