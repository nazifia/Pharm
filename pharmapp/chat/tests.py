from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from chat.models import ChatRoom, ChatMessage, UserChatStatus, MessageReadStatus
import json

User = get_user_model()

class ChatModelTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='testuser1',
            mobile='1234567890',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            mobile='0987654321',
            password='testpass123'
        )

    def test_direct_room_creation(self):
        """Test creating a direct message room between two users"""
        room, created = ChatRoom.get_or_create_direct_room(self.user1, self.user2)
        
        self.assertTrue(created)
        self.assertEqual(room.room_type, 'direct')
        self.assertEqual(room.participants.count(), 2)
        self.assertIn(self.user1, room.participants.all())
        self.assertIn(self.user2, room.participants.all())

    def test_direct_room_get_existing(self):
        """Test getting an existing direct message room"""
        room1, created1 = ChatRoom.get_or_create_direct_room(self.user1, self.user2)
        room2, created2 = ChatRoom.get_or_create_direct_room(self.user2, self.user1)
        
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(room1.id, room2.id)

    def test_chat_message_creation(self):
        """Test creating a chat message"""
        room, _ = ChatRoom.get_or_create_direct_room(self.user1, self.user2)
        
        message = ChatMessage.objects.create(
            room=room,
            sender=self.user1,
            message="Hello, this is a test message!",
            receiver=self.user2  # Legacy field
        )
        
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.room, room)
        self.assertEqual(message.message, "Hello, this is a test message!")
        self.assertEqual(message.message_type, 'text')
        self.assertEqual(message.status, 'sent')

    def test_message_read_status(self):
        """Test message read status functionality"""
        room, _ = ChatRoom.get_or_create_direct_room(self.user1, self.user2)
        
        message = ChatMessage.objects.create(
            room=room,
            sender=self.user1,
            message="Test message",
            receiver=self.user2
        )
        
        # Initially not read
        self.assertFalse(message.is_read_by(self.user2))
        
        # Mark as read
        message.mark_as_read(self.user2)
        
        # Should be read now
        self.assertTrue(message.is_read_by(self.user2))
        
        # Check read status object was created
        read_status = MessageReadStatus.objects.get(message=message, user=self.user2)
        self.assertIsNotNone(read_status.read_at)

    def test_user_chat_status(self):
        """Test user chat status functionality"""
        status, created = UserChatStatus.objects.get_or_create(
            user=self.user1,
            defaults={'is_online': True}
        )
        
        self.assertTrue(created)
        self.assertTrue(status.is_online)
        self.assertIsNotNone(status.last_seen)

class ChatViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='testuser1',
            mobile='1234567890',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            mobile='0987654321',
            password='testpass123'
        )

    def test_chat_view_requires_login(self):
        """Test that chat view requires authentication"""
        response = self.client.get(reverse('chat:chat_view_default'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_chat_view_authenticated(self):
        """Test chat view for authenticated user"""
        self.client.login(mobile='1234567890', password='testpass123')
        response = self.client.get(reverse('chat:chat_view_default'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chat')

    def test_chat_with_specific_user(self):
        """Test chat view with a specific user"""
        self.client.login(mobile='1234567890', password='testpass123')
        response = self.client.get(reverse('chat:chat_view', args=[self.user2.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user2.username)

    def test_unread_messages_count_api(self):
        """Test unread messages count API"""
        self.client.login(mobile='1234567890', password='testpass123')
        
        # Create a message from user2 to user1
        room, _ = ChatRoom.get_or_create_direct_room(self.user1, self.user2)
        ChatMessage.objects.create(
            room=room,
            sender=self.user2,
            receiver=self.user1,
            message="Unread message",
            is_read=False
        )
        
        response = self.client.get(reverse('chat:unread_messages_count'))
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertGreaterEqual(data['unread_count'], 1)

    def test_online_users_api(self):
        """Test online users API"""
        self.client.login(mobile='1234567890', password='testpass123')
        
        # Create online status for user2
        UserChatStatus.objects.create(
            user=self.user2,
            is_online=True,
            last_seen=timezone.now()
        )
        
        response = self.client.get(reverse('chat:get_online_users'))
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('online_users', data)

    def test_ajax_message_send(self):
        """Test sending message via AJAX"""
        self.client.login(mobile='1234567890', password='testpass123')
        
        # Create a room first
        room, _ = ChatRoom.get_or_create_direct_room(self.user1, self.user2)
        
        response = self.client.post(
            reverse('chat:chat_view_default'),
            data=json.dumps({
                'message': 'Test AJAX message',
                'room_id': str(room.id)
            }),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data.get('success'))
        
        # Verify message was created
        message = ChatMessage.objects.filter(
            room=room,
            sender=self.user1,
            message='Test AJAX message'
        ).first()
        self.assertIsNotNone(message)

class ChatFormTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='testuser1',
            mobile='1234567890',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            mobile='0987654321',
            password='testpass123'
        )

    def test_chat_message_form_valid(self):
        """Test ChatMessageForm with valid data"""
        from chat.forms import ChatMessageForm
        
        form_data = {
            'receiver': self.user2.id,
            'message': 'Test message content'
        }
        
        form = ChatMessageForm(data=form_data, user=self.user1)
        self.assertTrue(form.is_valid())

    def test_chat_message_form_invalid(self):
        """Test ChatMessageForm with invalid data"""
        from chat.forms import ChatMessageForm
        
        form_data = {
            'receiver': '',
            'message': ''
        }
        
        form = ChatMessageForm(data=form_data, user=self.user1)
        self.assertFalse(form.is_valid())

    def test_quick_message_form(self):
        """Test QuickMessageForm"""
        from chat.forms import QuickMessageForm
        
        form_data = {'message': 'Quick test message'}
        form = QuickMessageForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Test empty message
        form_data = {'message': ''}
        form = QuickMessageForm(data=form_data)
        self.assertFalse(form.is_valid())

class ChatIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='testuser1',
            mobile='1234567890',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            mobile='0987654321',
            password='testpass123'
        )

    def test_full_chat_workflow(self):
        """Test complete chat workflow"""
        # Login as user1
        self.client.login(mobile='1234567890', password='testpass123')
        
        # Access chat page
        response = self.client.get(reverse('chat:chat_view_default'))
        self.assertEqual(response.status_code, 200)
        
        # Start chat with user2
        response = self.client.get(reverse('chat:chat_view', args=[self.user2.id]))
        self.assertEqual(response.status_code, 200)
        
        # Send a message
        response = self.client.post(
            reverse('chat:send_message'),
            data={
                'receiver': self.user2.id,
                'message': 'Hello from integration test!'
            }
        )
        self.assertEqual(response.status_code, 302)  # Redirect after successful send
        
        # Verify message was created
        message = ChatMessage.objects.filter(
            sender=self.user1,
            receiver=self.user2,
            message='Hello from integration test!'
        ).first()
        self.assertIsNotNone(message)
        
        # Check unread count for user2
        self.client.login(mobile='0987654321', password='testpass123')
        response = self.client.get(reverse('chat:unread_messages_count'))
        data = json.loads(response.content)
        self.assertGreaterEqual(data['unread_count'], 1)
