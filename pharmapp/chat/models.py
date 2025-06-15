from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()

class ChatRoom(models.Model):
    """Model for chat rooms - supports both direct messages and group chats"""
    ROOM_TYPES = [
        ('direct', 'Direct Message'),
        ('group', 'Group Chat'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)  # For group chats
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='direct')
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.room_type == 'direct':
            participants = list(self.participants.all())
            if len(participants) == 2:
                return f"Chat between {participants[0].username} and {participants[1].username}"
            return f"Direct chat ({len(participants)} participants)"
        return self.name or f"Group chat {self.id}"

    @classmethod
    def get_or_create_direct_room(cls, user1, user2):
        """Get or create a direct message room between two users"""
        # Check if a direct room already exists between these users
        existing_room = cls.objects.filter(
            room_type='direct',
            participants=user1
        ).filter(participants=user2).first()

        if existing_room:
            return existing_room, False

        # Create new room
        room = cls.objects.create(room_type='direct')
        room.participants.add(user1, user2)
        return room, True

    class Meta:
        ordering = ['-updated_at']

class ChatMessage(models.Model):
    """Enhanced chat message model"""
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('file', 'File'),
        ('image', 'Image'),
        ('system', 'System Message'),
    ]

    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message = models.TextField(blank=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    file_attachment = models.FileField(upload_to='chat_files/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    edited_at = models.DateTimeField(blank=True, null=True)
    reply_to = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='replies')

    # Legacy fields for backward compatibility
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.sender.username} in {self.room}: {self.message[:20]}'

    def mark_as_read(self, user):
        """Mark message as read by a specific user"""
        MessageReadStatus.objects.get_or_create(
            message=self,
            user=user,
            defaults={'read_at': timezone.now()}
        )

    def is_read_by(self, user):
        """Check if message is read by a specific user"""
        return MessageReadStatus.objects.filter(message=self, user=user).exists()

    class Meta:
        ordering = ['timestamp']

class MessageReadStatus(models.Model):
    """Track read status of messages by users"""
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='read_statuses')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'user']

class UserChatStatus(models.Model):
    """Track user online status and typing indicators"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_status')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    typing_in_room = models.ForeignKey(ChatRoom, on_delete=models.SET_NULL, blank=True, null=True)
    typing_since = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}"