from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from userauth.models import Profile

User = get_user_model()


class Command(BaseCommand):
    help = 'Create profiles for users who don\'t have them and fix missing user_types'

    def handle(self, *args, **options):
        users_without_profiles = []
        users_without_user_type = []

        for user in User.objects.all():
            if not hasattr(user, 'profile') or not user.profile:
                users_without_profiles.append(user)
            elif not user.profile.user_type:
                users_without_user_type.append(user)

        # Fix users without profiles
        created_count = 0
        if users_without_profiles:
            self.stdout.write(
                f'Found {len(users_without_profiles)} users without profiles.'
            )

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

        # Fix users with profiles but no user_type
        fixed_user_type_count = 0
        if users_without_user_type:
            self.stdout.write(
                f'Found {len(users_without_user_type)} users without user_type.'
            )

            for user in users_without_user_type:
                user.profile.user_type = 'Salesperson'
                user.profile.save()
                fixed_user_type_count += 1
                self.stdout.write(
                    f'Set user_type for user: {user.mobile} ({user.username})'
                )

        if not users_without_profiles and not users_without_user_type:
            self.stdout.write(
                self.style.SUCCESS('All users already have proper profiles with user_types.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created {created_count} profiles and fixed {fixed_user_type_count} user_types.'
                )
            )
