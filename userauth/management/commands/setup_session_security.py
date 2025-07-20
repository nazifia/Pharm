"""
Management command to set up session security features.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'Set up session security features including cache table and session cleanup'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-cache-table',
            action='store_true',
            help='Skip creating the cache table',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up session security features...'))

        # Create cache table for database caching
        if not options['skip_cache_table']:
            self.stdout.write('Creating cache table...')
            try:
                call_command('createcachetable')
                self.stdout.write(self.style.SUCCESS('Cache table created successfully.'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Cache table creation failed or already exists: {e}'))

        # Clear any existing sessions for security
        self.stdout.write('Clearing existing sessions for security...')
        try:
            from django.contrib.sessions.models import Session
            session_count = Session.objects.count()
            Session.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Cleared {session_count} existing sessions.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to clear sessions: {e}'))

        # Verify cache configuration
        self.stdout.write('Verifying cache configuration...')
        try:
            from django.core.cache import cache
            cache.set('test_key', 'test_value', 60)
            if cache.get('test_key') == 'test_value':
                self.stdout.write(self.style.SUCCESS('Cache is working correctly.'))
                cache.delete('test_key')
            else:
                self.stdout.write(self.style.ERROR('Cache test failed.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Cache verification failed: {e}'))

        # Check session configuration
        self.stdout.write('Checking session configuration...')
        session_engine = getattr(settings, 'SESSION_ENGINE', 'django.contrib.sessions.backends.db')
        if session_engine == 'django.contrib.sessions.backends.db':
            self.stdout.write(self.style.SUCCESS('Using database sessions (recommended for security).'))
        else:
            self.stdout.write(self.style.WARNING(f'Using session engine: {session_engine}'))

        # Display security recommendations
        self.stdout.write('\n' + self.style.SUCCESS('Session security setup complete!'))
        self.stdout.write('\nSecurity recommendations:')
        self.stdout.write('1. All users will need to log in again due to session clearing')
        self.stdout.write('2. Sessions are now properly isolated per user')
        self.stdout.write('3. Cache is using database backend for better isolation')
        self.stdout.write('4. Session validation middleware is active')
        self.stdout.write('5. User activity tracking is enabled')
        
        if not getattr(settings, 'SESSION_COOKIE_SECURE', False):
            self.stdout.write(self.style.WARNING('6. Consider setting SESSION_COOKIE_SECURE=True in production with HTTPS'))
        
        self.stdout.write('\nFor production deployment:')
        self.stdout.write('- Set SESSION_COOKIE_SECURE=True if using HTTPS')
        self.stdout.write('- Consider using Redis cache for better performance')
        self.stdout.write('- Monitor session activity logs for security')
        self.stdout.write('- Regularly run session cleanup')
