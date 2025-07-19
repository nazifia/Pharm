from django.core.management.base import BaseCommand
from userauth.models import Profile


class Command(BaseCommand):
    help = 'Clean up empty or whitespace-only employee IDs'

    def handle(self, *args, **options):
        # Find profiles with empty or whitespace-only employee_ids
        problematic_profiles = []
        
        for profile in Profile.objects.all():
            if profile.employee_id is not None:
                # Check if employee_id is empty or only whitespace
                if not profile.employee_id.strip():
                    problematic_profiles.append(profile)
        
        if not problematic_profiles:
            self.stdout.write(
                self.style.SUCCESS('No problematic employee IDs found.')
            )
            return
        
        self.stdout.write(
            f'Found {len(problematic_profiles)} profiles with empty/whitespace employee IDs.'
        )
        
        # Clean up the problematic entries
        cleaned_count = 0
        for profile in problematic_profiles:
            old_value = repr(profile.employee_id)
            profile.employee_id = None
            profile.save()
            cleaned_count += 1
            self.stdout.write(
                f'Cleaned profile for user: {profile.user.username} (was: {old_value}, now: None)'
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully cleaned {cleaned_count} employee ID entries.')
        )
