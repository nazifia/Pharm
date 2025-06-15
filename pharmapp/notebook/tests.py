from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import Note, NoteCategory, NoteShare

User = get_user_model()


class NoteModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = NoteCategory.objects.create(
            name='Test Category',
            description='Test category description',
            color='#ff0000'
        )

    def test_note_creation(self):
        note = Note.objects.create(
            title='Test Note',
            content='This is a test note content.',
            user=self.user,
            category=self.category,
            priority='high'
        )
        self.assertEqual(note.title, 'Test Note')
        self.assertEqual(note.user, self.user)
        self.assertEqual(note.category, self.category)
        self.assertEqual(note.priority, 'high')
        self.assertFalse(note.is_pinned)
        self.assertFalse(note.is_archived)

    def test_note_str_method(self):
        note = Note.objects.create(
            title='Test Note',
            content='Test content',
            user=self.user
        )
        expected_str = f"Test Note - {self.user.username}"
        self.assertEqual(str(note), expected_str)

    def test_get_tags_list(self):
        note = Note.objects.create(
            title='Test Note',
            content='Test content',
            user=self.user,
            tags='work, important, meeting'
        )
        expected_tags = ['work', 'important', 'meeting']
        self.assertEqual(note.get_tags_list(), expected_tags)

    def test_is_overdue(self):
        # Test overdue reminder
        past_date = timezone.now() - timedelta(days=1)
        note = Note.objects.create(
            title='Overdue Note',
            content='Test content',
            user=self.user,
            reminder_date=past_date
        )
        self.assertTrue(note.is_overdue())

        # Test future reminder
        future_date = timezone.now() + timedelta(days=1)
        note2 = Note.objects.create(
            title='Future Note',
            content='Test content',
            user=self.user,
            reminder_date=future_date
        )
        self.assertFalse(note2.is_overdue())

    def test_get_priority_badge_class(self):
        note = Note.objects.create(
            title='Test Note',
            content='Test content',
            user=self.user,
            priority='urgent'
        )
        self.assertEqual(note.get_priority_badge_class(), 'badge-danger')


class NoteCategoryModelTest(TestCase):
    def test_category_creation(self):
        category = NoteCategory.objects.create(
            name='Work',
            description='Work-related notes',
            color='#007bff'
        )
        self.assertEqual(category.name, 'Work')
        self.assertEqual(category.description, 'Work-related notes')
        self.assertEqual(category.color, '#007bff')

    def test_category_str_method(self):
        category = NoteCategory.objects.create(name='Personal')
        self.assertEqual(str(category), 'Personal')


class NotebookViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = NoteCategory.objects.create(
            name='Test Category',
            color='#007bff'
        )
        self.note = Note.objects.create(
            title='Test Note',
            content='This is a test note.',
            user=self.user,
            category=self.category
        )

    def test_dashboard_view_requires_login(self):
        response = self.client.get(reverse('notebook:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_view_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('notebook:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Notebook Dashboard')

    def test_note_list_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('notebook:note_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Note')

    def test_note_detail_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('notebook:note_detail', kwargs={'pk': self.note.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Note')
        self.assertContains(response, 'This is a test note.')

    def test_note_create_view_get(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('notebook:note_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New Note')

    def test_note_create_view_post(self):
        self.client.login(username='testuser', password='testpass123')
        data = {
            'title': 'New Test Note',
            'content': 'This is a new test note content.',
            'priority': 'medium'
        }
        response = self.client.post(reverse('notebook:note_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        
        # Check if note was created
        new_note = Note.objects.get(title='New Test Note')
        self.assertEqual(new_note.user, self.user)
        self.assertEqual(new_note.content, 'This is a new test note content.')

    def test_note_edit_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('notebook:note_edit', kwargs={'pk': self.note.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Note')

    def test_note_delete_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('notebook:note_delete', kwargs={'pk': self.note.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirm Deletion')

    def test_note_pin_toggle(self):
        self.client.login(username='testuser', password='testpass123')
        self.assertFalse(self.note.is_pinned)
        
        response = self.client.get(reverse('notebook:note_pin', kwargs={'pk': self.note.pk}))
        self.assertEqual(response.status_code, 302)
        
        self.note.refresh_from_db()
        self.assertTrue(self.note.is_pinned)

    def test_note_archive_toggle(self):
        self.client.login(username='testuser', password='testpass123')
        self.assertFalse(self.note.is_archived)
        
        response = self.client.get(reverse('notebook:note_archive', kwargs={'pk': self.note.pk}))
        self.assertEqual(response.status_code, 302)
        
        self.note.refresh_from_db()
        self.assertTrue(self.note.is_archived)

    def test_category_list_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('notebook:category_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Category')

    def test_category_create_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('notebook:category_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New Category')

    def test_user_can_only_see_own_notes(self):
        # Create another user and note
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        other_note = Note.objects.create(
            title='Other User Note',
            content='This note belongs to another user.',
            user=other_user
        )
        
        # Login as first user
        self.client.login(username='testuser', password='testpass123')
        
        # Try to access other user's note
        response = self.client.get(reverse('notebook:note_detail', kwargs={'pk': other_note.pk}))
        self.assertEqual(response.status_code, 302)  # Should redirect due to permission denied

    def test_search_functionality(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Create additional notes for testing search
        Note.objects.create(
            title='Python Programming',
            content='Learning Python is fun',
            user=self.user
        )
        Note.objects.create(
            title='Django Framework',
            content='Django makes web development easier',
            user=self.user
        )
        
        # Test search by title
        response = self.client.get(reverse('notebook:note_list'), {'query': 'Python'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python Programming')
        self.assertNotContains(response, 'Django Framework')
        
        # Test search by content
        response = self.client.get(reverse('notebook:note_list'), {'query': 'Django'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django Framework')
