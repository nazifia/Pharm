from django.contrib import admin
from .models import ChatRoom, ChatMessage, UserChatStatus, MessageReadStatus

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'room_type', 'get_participants', 'created_at', 'updated_at']
    list_filter = ['room_type', 'created_at']
    search_fields = ['name', 'participants__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    filter_horizontal = ['participants']
    
    def get_participants(self, obj):
        return ", ".join([user.username for user in obj.participants.all()])
    get_participants.short_description = 'Participants'

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender', 'get_room_name', 'message_preview', 'message_type', 'status', 'timestamp']
    list_filter = ['message_type', 'status', 'timestamp', 'room__room_type']
    search_fields = ['message', 'sender__username', 'room__name']
    readonly_fields = ['id', 'timestamp', 'edited_at']
    raw_id_fields = ['sender', 'room', 'receiver', 'reply_to']
    
    def get_room_name(self, obj):
        return str(obj.room)
    get_room_name.short_description = 'Room'
    
    def message_preview(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'

@admin.register(UserChatStatus)
class UserChatStatusAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_online', 'last_seen', 'typing_in_room', 'typing_since']
    list_filter = ['is_online', 'last_seen']
    search_fields = ['user__username']
    readonly_fields = ['last_seen', 'typing_since']
    raw_id_fields = ['user', 'typing_in_room']

@admin.register(MessageReadStatus)
class MessageReadStatusAdmin(admin.ModelAdmin):
    list_display = ['message', 'user', 'read_at']
    list_filter = ['read_at']
    search_fields = ['message__message', 'user__username']
    readonly_fields = ['read_at']
    raw_id_fields = ['message', 'user']
