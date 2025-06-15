import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import ChatRoom, ChatMessage, UserChatStatus
import uuid

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Get room_id from URL
        self.room_id = self.scope['url_route']['kwargs'].get('room_id')
        self.user_id = self.scope['url_route']['kwargs'].get('user_id')
        
        if self.room_id:
            # Direct room connection
            self.room_group_name = f'chat_{self.room_id}'
        elif self.user_id:
            # Create or get direct room between users
            try:
                other_user = await self.get_user_by_id(int(self.user_id))
                room = await self.get_or_create_direct_room(self.user, other_user)
                self.room_id = str(room.id)
                self.room_group_name = f'chat_{self.room_id}'
            except (ValueError, User.DoesNotExist):
                await self.close()
                return
        else:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Update user online status
        await self.update_user_online_status(True)
        
        await self.accept()
        
        # Notify others that user is online
        await self.channel_layer.group_send(
            'online_users',
            {
                'type': 'user_status_update',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_online': True
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        
        if hasattr(self, 'user') and self.user.is_authenticated:
            # Update user offline status
            await self.update_user_online_status(False)
            
            # Notify others that user is offline
            await self.channel_layer.group_send(
                'online_users',
                {
                    'type': 'user_status_update',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'is_online': False
                }
            )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'chat_message')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(text_data_json)
            elif message_type == 'typing':
                await self.handle_typing_status(text_data_json)
            elif message_type == 'mark_read':
                await self.handle_mark_read(text_data_json)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON'
            }))

    async def handle_chat_message(self, data):
        message_text = data['message']
        
        if not message_text.strip():
            return
        
        # Save message to database
        room = await self.get_room_by_id(self.room_id)
        message = await self.create_message(room, self.user, message_text)
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': str(message.id),
                    'message': message.message,
                    'sender_id': message.sender.id,
                    'sender_username': message.sender.username,
                    'timestamp': message.timestamp.isoformat(),
                    'message_type': message.message_type,
                    'status': message.status
                }
            }
        )

    async def handle_typing_status(self, data):
        is_typing = data.get('is_typing', False)
        
        # Send typing status to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_status',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': is_typing
            }
        )

    async def handle_mark_read(self, data):
        message_ids = data.get('message_ids', [])
        
        # Mark messages as read
        await self.mark_messages_read(message_ids, self.user)
        
        # Notify sender about read status
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'messages_read',
                'message_ids': message_ids,
                'reader_id': self.user.id
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message
        }))

    async def typing_status(self, event):
        # Don't send typing status to the user who is typing
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing_status',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))

    async def messages_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'message_ids': event['message_ids'],
            'reader_id': event['reader_id']
        }))

    # Database operations
    @database_sync_to_async
    def get_user_by_id(self, user_id):
        return User.objects.get(id=user_id)

    @database_sync_to_async
    def get_or_create_direct_room(self, user1, user2):
        room, created = ChatRoom.get_or_create_direct_room(user1, user2)
        return room

    @database_sync_to_async
    def get_room_by_id(self, room_id):
        return ChatRoom.objects.get(id=room_id)

    @database_sync_to_async
    def create_message(self, room, sender, message_text):
        message = ChatMessage.objects.create(
            room=room,
            sender=sender,
            message=message_text,
            message_type='text'
        )
        
        # Set legacy receiver field for backward compatibility
        if room.room_type == 'direct':
            other_participant = room.participants.exclude(id=sender.id).first()
            message.receiver = other_participant
            message.save()
        
        # Update room timestamp
        room.updated_at = timezone.now()
        room.save()
        
        return message

    @database_sync_to_async
    def update_user_online_status(self, is_online):
        user_status, created = UserChatStatus.objects.get_or_create(
            user=self.user,
            defaults={'is_online': is_online, 'last_seen': timezone.now()}
        )
        user_status.is_online = is_online
        user_status.last_seen = timezone.now()
        user_status.save()

    @database_sync_to_async
    def mark_messages_read(self, message_ids, user):
        ChatMessage.objects.filter(
            id__in=message_ids,
            room__participants=user
        ).exclude(sender=user).update(status='read')


class OnlineStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Join online users group
        await self.channel_layer.group_add(
            'online_users',
            self.channel_name
        )
        
        await self.accept()
        
        # Send current online users
        online_users = await self.get_online_users()
        await self.send(text_data=json.dumps({
            'type': 'online_users_list',
            'users': online_users
        }))

    async def disconnect(self, close_code):
        # Leave online users group
        await self.channel_layer.group_discard(
            'online_users',
            self.channel_name
        )

    async def user_status_update(self, event):
        # Send user status update to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'user_status_update',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_online': event['is_online']
        }))

    @database_sync_to_async
    def get_online_users(self):
        online_statuses = UserChatStatus.objects.filter(is_online=True).select_related('user')
        return [
            {
                'id': status.user.id,
                'username': status.user.username,
                'last_seen': status.last_seen.isoformat() if status.last_seen else None
            }
            for status in online_statuses
        ]
