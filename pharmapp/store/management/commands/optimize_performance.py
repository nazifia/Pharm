from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection
from django.conf import settings
import time


class Command(BaseCommand):
    help = 'Optimize application performance by clearing cache and analyzing database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear the application cache',
        )
        parser.add_argument(
            '--analyze-db',
            action='store_true',
            help='Run database analysis for query optimization',
        )
        parser.add_argument(
            '--vacuum-db',
            action='store_true',
            help='Vacuum the database to reclaim space',
        )

    def handle(self, *args, **options):
        start_time = time.time()
        
        if options['clear_cache']:
            self.clear_cache()
            
        if options['analyze_db']:
            self.analyze_database()
            
        if options['vacuum_db']:
            self.vacuum_database()
            
        # If no specific option provided, run all optimizations
        if not any(options.values()):
            self.clear_cache()
            self.analyze_database()
            
        end_time = time.time()
        self.stdout.write(
            self.style.SUCCESS(f'Performance optimization completed in {end_time - start_time:.2f} seconds')
        )

    def clear_cache(self):
        """Clear the application cache"""
        self.stdout.write('Clearing application cache...')
        try:
            cache.clear()
            self.stdout.write(self.style.SUCCESS('✓ Cache cleared successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Failed to clear cache: {e}'))

    def analyze_database(self):
        """Run database analysis for query optimization"""
        self.stdout.write('Analyzing database tables for optimization...')
        
        tables_to_analyze = [
            'store_item',
            'store_cart',
            'store_receipt',
            'store_dispensinglog',
            'store_customer',
            'store_wallet',
            'wholesale_wholesaleitem',
            'wholesale_wholesalecart',
            'wholesale_wholesalereceipt',
        ]
        
        try:
            with connection.cursor() as cursor:
                for table in tables_to_analyze:
                    try:
                        cursor.execute(f'ANALYZE {table};')
                        self.stdout.write(f'  ✓ Analyzed {table}')
                    except Exception as e:
                        self.stdout.write(f'  ✗ Failed to analyze {table}: {e}')
            
            self.stdout.write(self.style.SUCCESS('✓ Database analysis completed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Database analysis failed: {e}'))

    def vacuum_database(self):
        """Vacuum the database to reclaim space"""
        self.stdout.write('Vacuuming database...')
        try:
            with connection.cursor() as cursor:
                cursor.execute('VACUUM;')
            self.stdout.write(self.style.SUCCESS('✓ Database vacuum completed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Database vacuum failed: {e}'))
