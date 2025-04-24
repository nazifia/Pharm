from django.core.management.base import BaseCommand
from userauth.models import User, Profile

class Command(BaseCommand):
    help = 'Updates all superusers to have Admin user_type'

    def handle(self, *args, **options):
        # Get all superusers
        superusers = User.objects.filter(is_superuser=True)
        
        if not superusers.exists():
            self.stdout.write(self.style.WARNING('No superusers found in the system.'))
            return
        
        updated_count = 0
        for user in superusers:
            try:
                # Check if the user has a profile
                if hasattr(user, 'profile'):
                    # Update the user_type if it's not already 'Admin'
                    if user.profile.user_type != 'Admin':
                        user.profile.user_type = 'Admin'
                        user.profile.save()
                        updated_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Updated user {user.username} to Admin user_type'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'User {user.username} already has Admin user_type'))
                else:
                    # Create a profile for the user if it doesn't exist
                    Profile.objects.create(user=user, user_type='Admin')
                    updated_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Created Admin profile for user {user.username}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error updating user {user.username}: {str(e)}'))
        
        if updated_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} superusers to have Admin privileges'))
        else:
            self.stdout.write(self.style.SUCCESS('All superusers already have Admin privileges'))
