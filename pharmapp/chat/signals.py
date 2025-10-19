from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from .models import UserChatStatus


@receiver(user_logged_in)
def set_user_online_on_login(sender, request, user, **kwargs):
    """
    Signal handler to set user chat status to online when user logs in
    """
    try:
        user_chat_status, created = UserChatStatus.objects.get_or_create(
            user=user,
            defaults={'is_online': True, 'last_seen': timezone.now()}
        )
        user_chat_status.is_online = True
        user_chat_status.last_seen = timezone.now()
        user_chat_status.save()
    except Exception:
        # Silently handle any errors to avoid breaking login process
        pass


@receiver(user_logged_out)
def set_user_offline_on_logout(sender, request, user, **kwargs):
    """
    Signal handler to set user chat status to offline when user logs out
    """
    try:
        user_chat_status = UserChatStatus.objects.filter(user=user).first()
        if user_chat_status:
            user_chat_status.is_online = False
            user_chat_status.last_seen = timezone.now()
            user_chat_status.save()
    except Exception:
        # Silently handle any errors to avoid breaking logout process
        pass
