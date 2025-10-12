from django.core.management.base import BaseCommand
import os

class Command(BaseCommand):
    help = 'Fix Django template syntax error in base.html'

    def handle(self, *args, **options):
        # Path to the base.html file
        base_template_path = os.path.join('templates', 'partials', 'base.html')
        
        try:
            # Read the file
            with open(base_template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace the problematic syntax
            old_line1 = "{% if user.profile.user_type in ['Admin', 'Manager', 'Pharmacist', 'Salesperson'] %}"
            new_line1 = "{% if user.profile.user_type == 'Admin' or user.profile.user_type == 'Manager' or user.profile.user_type == 'Pharmacist' or user.profile.user_type == 'Salesperson' %}"
            
            # Replace the problematic line
            content = content.replace(old_line1, new_line1)
            
            # Write back the file
            with open(base_template_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.stdout.write(
                self.style.SUCCESS('Successfully fixed template syntax error in base.html')
            )
            
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR('base.html file not found')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error fixing template: {str(e)}')
            )
