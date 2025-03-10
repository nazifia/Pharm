import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Copies capacitor_index.html to staticfiles/index.html'

    def handle(self, *args, **options):
        source = os.path.join(settings.BASE_DIR, 'templates', 'capacitor_index.html')
        dest = os.path.join(settings.STATIC_ROOT, 'index.html')
        
        if os.path.exists(source):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(source, dest)
            self.stdout.write(self.style.SUCCESS('Successfully copied index.html'))
        else:
            self.stdout.write(self.style.ERROR(f'Source file not found: {source}'))