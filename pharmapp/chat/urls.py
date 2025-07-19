from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Main chat views
    path('', views.chat_view, name='chat_view_default'),
    path('user/<int:receiver_id>/', views.chat_view, name='chat_view'),
    path('room/<uuid:room_id>/', views.chat_view, name='room_chat'),

    # Legacy support
    path('<int:receiver_id>/', views.chat_view, name='chat_view_legacy'),
    path('send/', views.send_message_view, name='send_message'),

    # API endpoints
    path('api/unread-count/', views.unread_messages_count, name='unread_messages_count'),
    path('api/typing/', views.set_typing_status, name='set_typing_status'),
    path('api/typing/<uuid:room_id>/', views.get_typing_users, name='get_typing_users'),
    path('api/online-users/', views.get_online_users, name='get_online_users'),

    # Enhanced chat API endpoints
    path('api/add-reaction/', views.add_reaction_api, name='add_reaction_api'),
    path('api/upload-file/', views.upload_file_api, name='upload_file_api'),
    path('api/upload-voice/', views.upload_voice_api, name='upload_voice_api'),

    # Real-time chat API endpoints
    path('api/get-new-messages/', views.get_new_messages_api, name='get_new_messages_api'),
    path('api/send-message/', views.send_message_api, name='send_message_api'),
    path('api/set-typing/', views.set_typing_status_api, name='set_typing_status_api'),
]