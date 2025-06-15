from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Max
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django import forms
import json
from .models import ChatMessage, ChatRoom, UserChatStatus, MessageReadStatus
from .forms import ChatMessageForm

User = get_user_model()

@login_required
def chat_view(request, receiver_id=None, room_id=None):
    """Enhanced chat view supporting both direct messages and rooms"""
    # Get or create user chat status
    user_status, created = UserChatStatus.objects.get_or_create(
        user=request.user,
        defaults={'is_online': True, 'last_seen': timezone.now()}
    )
    user_status.is_online = True
    user_status.last_seen = timezone.now()
    user_status.save()

    # Get all users for the sidebar
    users = User.objects.exclude(id=request.user.id).select_related('chat_status')

    # Get user's chat rooms with latest message info
    user_rooms = ChatRoom.objects.filter(
        participants=request.user
    ).annotate(
        latest_message_time=Max('messages__timestamp'),
        unread_count=Count('messages', filter=Q(
            messages__timestamp__gt=request.user.last_login or timezone.now()
        ) & ~Q(messages__sender=request.user))
    ).order_by('-latest_message_time')

    selected_room = None
    selected_user = None
    messages = []

    # Handle room selection
    if room_id:
        selected_room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    elif receiver_id:
        selected_user = get_object_or_404(User, id=receiver_id)
        selected_room, created = ChatRoom.get_or_create_direct_room(request.user, selected_user)

    if selected_room:
        # Get messages with pagination
        messages_queryset = selected_room.messages.select_related('sender').prefetch_related('read_statuses')
        paginator = Paginator(messages_queryset, 50)  # 50 messages per page
        page_number = request.GET.get('page', 1)
        messages_page = paginator.get_page(page_number)
        messages = messages_page.object_list

        # Mark messages as read
        unread_messages = selected_room.messages.exclude(sender=request.user).exclude(
            read_statuses__user=request.user
        )
        for message in unread_messages:
            message.mark_as_read(request.user)

        # Update legacy is_read field for backward compatibility
        ChatMessage.objects.filter(
            room=selected_room,
            sender__in=selected_room.participants.exclude(id=request.user.id),
            is_read=False
        ).update(is_read=True)

    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.method == 'POST':
            return handle_ajax_message_send(request, selected_room)
        else:
            return JsonResponse({
                'messages': [serialize_message(msg) for msg in messages],
                'room_id': str(selected_room.id) if selected_room else None,
            })

    # Handle form submission
    if request.method == 'POST' and selected_room:
        form = ChatMessageForm(request.POST, request.FILES)
        if form.is_valid():
            chat_message = form.save(commit=False)
            chat_message.sender = request.user
            chat_message.room = selected_room
            # Set legacy receiver field for backward compatibility
            if selected_room.room_type == 'direct':
                other_participant = selected_room.participants.exclude(id=request.user.id).first()
                chat_message.receiver = other_participant
            chat_message.save()

            # Update room's updated_at timestamp
            selected_room.updated_at = timezone.now()
            selected_room.save()

            return redirect('chat:room_chat', room_id=selected_room.id)
    else:
        form = ChatMessageForm()

    context = {
        'users': users,
        'user_rooms': user_rooms,
        'selected_room': selected_room,
        'selected_user': selected_user,
        'messages': messages,
        'form': form,
    }
    return render(request, 'chat/chat_interface.html', context)

def serialize_message(message):
    """Serialize a message for JSON response"""
    return {
        'id': str(message.id),
        'sender': message.sender.username,
        'sender_id': message.sender.id,
        'message': message.message,
        'timestamp': message.timestamp.isoformat(),
        'message_type': message.message_type,
        'status': message.status,
        'is_read': message.is_read,
        'file_url': message.file_attachment.url if message.file_attachment else None,
    }

def handle_ajax_message_send(request, room):
    """Handle AJAX message sending"""
    try:
        data = json.loads(request.body)
        message_text = data.get('message', '').strip()
        room_id = data.get('room_id')
        receiver_id = data.get('receiver_id')

        if not message_text:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)

        # If no room provided, try to get/create one
        if not room:
            if room_id:
                try:
                    room = ChatRoom.objects.get(id=room_id, participants=request.user)
                except ChatRoom.DoesNotExist:
                    return JsonResponse({'error': 'Room not found'}, status=404)
            elif receiver_id:
                try:
                    receiver = User.objects.get(id=receiver_id)
                    room, created = ChatRoom.get_or_create_direct_room(request.user, receiver)
                except User.DoesNotExist:
                    return JsonResponse({'error': 'Receiver not found'}, status=404)
            else:
                return JsonResponse({'error': 'No room or receiver specified'}, status=400)

        # Create message
        message = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            message=message_text,
            message_type='text'
        )

        # Set legacy receiver field for backward compatibility
        if room.room_type == 'direct':
            other_participant = room.participants.exclude(id=request.user.id).first()
            message.receiver = other_participant
            message.save()

        # Update room timestamp
        room.updated_at = timezone.now()
        room.save()

        return JsonResponse({
            'success': True,
            'message': serialize_message(message)
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def send_message_view(request):
    """Legacy send message view for backward compatibility"""
    if request.method == 'POST':
        form = ChatMessageForm(request.POST, request.FILES)
        if form.is_valid():
            receiver = form.cleaned_data.get('receiver')
            if receiver:
                # Get or create direct room
                room, created = ChatRoom.get_or_create_direct_room(request.user, receiver)

                chat_message = form.save(commit=False)
                chat_message.sender = request.user
                chat_message.room = room
                chat_message.receiver = receiver  # Legacy field
                chat_message.save()

                # Update room timestamp
                room.updated_at = timezone.now()
                room.save()

                return redirect('chat:room_chat', room_id=room.id)

    return redirect('chat:chat_view_default')

@login_required
def unread_messages_count(request):
    """Get unread messages count for the current user"""
    if request.user.is_authenticated:
        # Count unread messages in all rooms the user participates in
        unread_count = ChatMessage.objects.filter(
            room__participants=request.user
        ).exclude(sender=request.user).exclude(
            read_statuses__user=request.user
        ).count()

        # Also count legacy unread messages for backward compatibility
        legacy_unread = ChatMessage.objects.filter(
            receiver=request.user,
            is_read=False
        ).count()

        total_unread = max(unread_count, legacy_unread)

        return JsonResponse({'unread_count': total_unread})
    return JsonResponse({'unread_count': 0})

@login_required
@require_http_methods(["POST"])
def set_typing_status(request):
    """Set typing status for a user in a room"""
    try:
        data = json.loads(request.body)
        room_id = data.get('room_id')
        is_typing = data.get('is_typing', False)

        if room_id:
            room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
            user_status, created = UserChatStatus.objects.get_or_create(
                user=request.user,
                defaults={'is_online': True}
            )

            if is_typing:
                user_status.typing_in_room = room
                user_status.typing_since = timezone.now()
            else:
                user_status.typing_in_room = None
                user_status.typing_since = None

            user_status.save()

            return JsonResponse({'success': True})

        return JsonResponse({'error': 'Room ID required'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_typing_users(request, room_id):
    """Get users currently typing in a room"""
    try:
        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)

        # Get users typing in this room (excluding current user)
        typing_users = UserChatStatus.objects.filter(
            typing_in_room=room,
            typing_since__gte=timezone.now() - timezone.timedelta(seconds=10)  # 10 seconds timeout
        ).exclude(user=request.user).select_related('user')

        typing_usernames = [status.user.username for status in typing_users]

        return JsonResponse({
            'typing_users': typing_usernames,
            'count': len(typing_usernames)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_online_users(request):
    """Get list of online users"""
    try:
        # Users online in the last 5 minutes
        online_threshold = timezone.now() - timezone.timedelta(minutes=5)
        online_users = UserChatStatus.objects.filter(
            is_online=True,
            last_seen__gte=online_threshold
        ).exclude(user=request.user).select_related('user')

        users_data = [{
            'id': status.user.id,
            'username': status.user.username,
            'last_seen': status.last_seen.isoformat(),
            'is_online': status.is_online
        } for status in online_users]

        return JsonResponse({'online_users': users_data})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Real-time Chat API Views
@login_required
def get_new_messages_api(request):
    """Get new messages for real-time chat polling"""
    try:
        room_id = request.GET.get('room_id')
        after_id = request.GET.get('after_id')

        if not room_id:
            return JsonResponse({'error': 'Room ID required'}, status=400)

        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)

        # Get messages after the specified ID
        messages_query = room.messages.select_related('sender').order_by('timestamp')

        if after_id:
            messages_query = messages_query.filter(id__gt=after_id)
        else:
            # If no after_id, get last 20 messages
            messages_query = messages_query[:20]

        messages = list(messages_query)

        # Get typing users
        typing_users = UserChatStatus.objects.filter(
            typing_in_room=room,
            typing_since__gte=timezone.now() - timezone.timedelta(seconds=10)
        ).exclude(user=request.user).select_related('user')

        typing_data = [{
            'id': status.user.id,
            'username': status.user.username
        } for status in typing_users]

        # Mark new messages as read
        if messages:
            for message in messages:
                if message.sender != request.user:
                    message.mark_as_read(request.user)

        return JsonResponse({
            'success': True,
            'messages': [serialize_message_enhanced(msg) for msg in messages],
            'typing_users': typing_data
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def send_message_api(request):
    """Send message via API for real-time chat"""
    try:
        data = json.loads(request.body)
        room_id = data.get('room_id')
        message_text = data.get('message', '').strip()

        if not room_id or not message_text:
            return JsonResponse({'error': 'Room ID and message required'}, status=400)

        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)

        # Create message
        message = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            message=message_text,
            message_type='text'
        )

        # Set legacy receiver field for backward compatibility
        if room.room_type == 'direct':
            other_participant = room.participants.exclude(id=request.user.id).first()
            message.receiver = other_participant
            message.save()

        # Update room timestamp
        room.updated_at = timezone.now()
        room.save()

        return JsonResponse({
            'success': True,
            'message': serialize_message_enhanced(message)
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_online_users_api(request):
    """Get online users for real-time status updates"""
    try:
        # Update current user's online status
        user_status, created = UserChatStatus.objects.get_or_create(
            user=request.user,
            defaults={'is_online': True, 'last_seen': timezone.now()}
        )
        user_status.is_online = True
        user_status.last_seen = timezone.now()
        user_status.save()

        # Get online users (last seen within 2 minutes)
        online_threshold = timezone.now() - timezone.timedelta(minutes=2)
        online_users = UserChatStatus.objects.filter(
            is_online=True,
            last_seen__gte=online_threshold
        ).exclude(user=request.user).select_related('user')

        users_data = [{
            'id': status.user.id,
            'username': status.user.username,
            'last_seen': status.last_seen.isoformat(),
            'is_online': True
        } for status in online_users]

        return JsonResponse({
            'success': True,
            'online_users': users_data
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def set_typing_status_api(request):
    """Set typing status for real-time chat"""
    try:
        data = json.loads(request.body)
        room_id = data.get('room_id')
        is_typing = data.get('is_typing', False)

        if not room_id:
            return JsonResponse({'error': 'Room ID required'}, status=400)

        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
        user_status, created = UserChatStatus.objects.get_or_create(
            user=request.user,
            defaults={'is_online': True}
        )

        if is_typing:
            user_status.typing_in_room = room
            user_status.typing_since = timezone.now()
        else:
            user_status.typing_in_room = None
            user_status.typing_since = None

        user_status.save()

        return JsonResponse({'success': True})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def serialize_message_enhanced(message):
    """Enhanced message serialization for real-time chat"""
    return {
        'id': str(message.id),
        'sender_username': message.sender.username,
        'sender_id': message.sender.id,
        'message': message.message,
        'timestamp': message.timestamp.isoformat(),
        'message_type': message.message_type,
        'status': message.status,
        'is_read': message.is_read,
        'file_url': message.file_attachment.url if message.file_attachment else None,
    }