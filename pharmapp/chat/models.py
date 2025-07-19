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
        ('voice', 'Voice Message'),
        ('video', 'Video'),
        ('location', 'Location'),
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

    # Advanced chat features
    is_pinned = models.BooleanField(default=False)
    is_forwarded = models.BooleanField(default=False)
    forwarded_from = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='forwards')
    voice_duration = models.IntegerField(blank=True, null=True, help_text="Duration in seconds for voice messages")
    location_lat = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    location_lng = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    location_address = models.CharField(max_length=255, blank=True, null=True)
    is_deleted = models.BooleanField(default=False)

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

class MessageReaction(models.Model):
    """Model for message reactions (like, love, laugh, etc.)"""
    REACTION_TYPES = [
        ('👍', 'Like'),
        ('❤️', 'Love'),
        ('😂', 'Laugh'),
        ('😮', 'Wow'),
        ('😢', 'Sad'),
        ('😡', 'Angry'),
        ('👏', 'Clap'),
        ('🔥', 'Fire'),
    ]

    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction = models.CharField(max_length=10, choices=REACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'user', 'reaction']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} reacted {self.reaction} to message {self.message.id}"


class ChatTheme(models.Model):
    """Model for chat themes and customization"""
    name = models.CharField(max_length=100)
    primary_color = models.CharField(max_length=7, default='#007bff')  # Hex color
    secondary_color = models.CharField(max_length=7, default='#6c757d')
    background_color = models.CharField(max_length=7, default='#ffffff')
    text_color = models.CharField(max_length=7, default='#000000')
    bubble_color_sent = models.CharField(max_length=7, default='#007bff')
    bubble_color_received = models.CharField(max_length=7, default='#e9ecef')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserChatPreferences(models.Model):
    """User chat preferences and settings"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_preferences')
    theme = models.ForeignKey(ChatTheme, on_delete=models.SET_NULL, null=True, blank=True)
    notification_sound = models.BooleanField(default=True)
    show_online_status = models.BooleanField(default=True)
    auto_download_media = models.BooleanField(default=True)
    font_size = models.CharField(max_length=10, choices=[('small', 'Small'), ('medium', 'Medium'), ('large', 'Large')], default='medium')
    enter_to_send = models.BooleanField(default=True)
    show_typing_indicator = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}'s chat preferences"


class UserChatStatus(models.Model):
    """Track user online status and typing indicators"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_status')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    typing_in_room = models.ForeignKey(ChatRoom, on_delete=models.SET_NULL, blank=True, null=True)
    typing_since = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}"