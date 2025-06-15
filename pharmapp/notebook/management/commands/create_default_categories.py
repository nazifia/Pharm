from django.core.management.base import BaseCommand
from notebook.models import NoteCategory


class Command(BaseCommand):
    help = 'Create default note categories for the notebook app'

    def handle(self, *args, **options):
        default_categories = [
            {
                'name': 'General',
                'description': 'General notes and miscellaneous information',
                'color': '#6c757d'
            },
            {
                'name': 'Work',
                'description': 'Work-related notes, tasks, and reminders',
                'color': '#007bff'
            },
            {
                'name': 'Personal',
                'description': 'Personal notes and private thoughts',
                'color': '#28a745'
            },
            {
                'name': 'Important',
                'description': 'High-priority notes that need attention',
                'color': '#dc3545'
            },
            {
                'name': 'Ideas',
                'description': 'Creative ideas and brainstorming notes',
                'color': '#ffc107'
            },
            {
                'name': 'Meeting Notes',
                'description': 'Notes from meetings and discussions',
                'color': '#17a2b8'
            },
            {
                'name': 'Pharmacy',
                'description': 'Pharmacy-related notes and procedures',
                'color': '#6f42c1'
            },
            {
                'name': 'Training',
                'description': 'Training materials and learning notes',
                'color': '#fd7e14'
            }
        ]

        created_count = 0
        for category_data in default_categories:
            category, created = NoteCategory.objects.get_or_create(
                name=category_data['name'],
                defaults={
                    'description': category_data['description'],
                    'color': category_data['color']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {category.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Category already exists: {category.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {len(default_categories)} categories. '
                f'{created_count} new categories created.'
            )
        )
