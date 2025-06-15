from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from userauth.models import Profile

User = get_user_model()


class Command(BaseCommand):
    help = 'Create profiles for users who don\'t have them'

    def handle(self, *args, **options):
        users_without_profiles = []
        
        for user in User.objects.all():
            if not hasattr(user, 'profile') or not user.profile:
                users_without_profiles.append(user)
        
        if not users_without_profiles:
            self.stdout.write(
                self.style.SUCCESS('All users already have profiles.')
            )
            return
        
        self.stdout.write(
            f'Found {len(users_without_profiles)} users without profiles.'
        )
        
        created_count = 0
        for user in users_without_profiles:
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': user.username or user.mobile,
                    'user_type': 'Salesperson'  # Default role
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    f'Created profile for user: {user.mobile} ({user.username})'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} profiles.'
            )
        )
