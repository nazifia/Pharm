from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/room/(?P<room_id>[0-9a-f-]+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/chat/user/(?P<user_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/chat/online/$', consumers.OnlineStatusConsumer.as_asgi()),
]
