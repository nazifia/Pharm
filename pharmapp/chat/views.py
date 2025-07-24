from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
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
        message_type = data.get('message_type', 'text')
        reply_to_id = data.get('reply_to')

        if not room_id:
            return JsonResponse({'error': 'Room ID required'}, status=400)

        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)

        # Handle reply
        reply_to = None
        if reply_to_id:
            try:
                reply_to = ChatMessage.objects.get(id=reply_to_id, room=room)
            except ChatMessage.DoesNotExist:
                pass

        # Create message
        message = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            message=message_text,
            message_type=message_type,
            reply_to=reply_to
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
        'edited_at': message.edited_at.isoformat() if message.edited_at else None,
        'voice_duration': message.voice_duration,
        'is_pinned': message.is_pinned,
        'is_forwarded': message.is_forwarded,
        'location_lat': str(message.location_lat) if message.location_lat else None,
        'location_lng': str(message.location_lng) if message.location_lng else None,
        'location_address': message.location_address,
        'reply_to': {
            'id': str(message.reply_to.id),
            'message': message.reply_to.message,
            'sender': message.reply_to.sender.username
        } if message.reply_to else None
    }


@login_required
@require_http_methods(["POST"])
def add_reaction_api(request):
    """Add reaction to a message"""
    try:
        data = json.loads(request.body)
        message_id = data.get('message_id')
        reaction = data.get('reaction')

        if not message_id or not reaction:
            return JsonResponse({'error': 'Message ID and reaction required'}, status=400)

        message = get_object_or_404(ChatMessage, id=message_id)

        # Check if user is participant in the room
        if not message.room.participants.filter(id=request.user.id).exists():
            return JsonResponse({'error': 'Access denied'}, status=403)

        from .models import MessageReaction

        # Toggle reaction (add if not exists, remove if exists)
        reaction_obj, created = MessageReaction.objects.get_or_create(
            message=message,
            user=request.user,
            reaction=reaction
        )

        if not created:
            reaction_obj.delete()

        # Get all reactions for this message
        reactions = {}
        for r in message.reactions.all():
            if r.reaction not in reactions:
                reactions[r.reaction] = []
            reactions[r.reaction].append(r.user.username)

        return JsonResponse({
            'success': True,
            'reactions': reactions
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def upload_file_api(request):
    """Upload file for chat"""
    try:
        room_id = request.POST.get('room_id')
        message_type = request.POST.get('message_type', 'file')
        file = request.FILES.get('file')

        if not room_id or not file:
            return JsonResponse({'error': 'Room ID and file required'}, status=400)

        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)

        # Validate file type and size
        max_size = 10 * 1024 * 1024  # 10MB
        if file.size > max_size:
            return JsonResponse({'error': 'File too large. Maximum size is 10MB.'}, status=400)

        # Create message with file
        message = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            message=request.POST.get('caption', ''),
            message_type=message_type,
            file_attachment=file
        )

        # Update room timestamp
        room.updated_at = timezone.now()
        room.save()

        return JsonResponse({
            'success': True,
            'message': serialize_message_enhanced(message)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def bulk_message_view(request):
    """View for sending bulk messages to all users (superusers/managers only)"""
    from userauth.permissions import can_manage_users

    if not can_manage_users(request.user):
        messages.error(request, 'You do not have permission to send bulk messages.')
        return redirect('chat:chat_view_default')

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        if message_text:
            # Get all active users except the sender
            all_users = User.objects.filter(is_active=True).exclude(id=request.user.id)

            # Create individual direct rooms and send messages to each user
            sent_count = 0
            for user in all_users:
                try:
                    # Get or create direct room with each user
                    room, created = ChatRoom.get_or_create_direct_room(request.user, user)

                    # Create message in the room
                    ChatMessage.objects.create(
                        room=room,
                        sender=request.user,
                        message=f"📢 BROADCAST MESSAGE:\n\n{message_text}",
                        message_type='text',
                        receiver=user  # Legacy field
                    )

                    # Update room timestamp
                    room.updated_at = timezone.now()
                    room.save()

                    sent_count += 1
                except Exception as e:
                    print(f"Error sending message to {user.username}: {e}")

            messages.success(request, f'Bulk message sent to {sent_count} users successfully.')
            return redirect('chat:bulk_message')

    # Get all active users for display
    all_users = User.objects.filter(is_active=True).exclude(id=request.user.id)

    return render(request, 'chat/bulk_message.html', {
        'all_users': all_users,
        'user_count': all_users.count()
    })


@login_required
@require_http_methods(["POST"])
def upload_voice_api(request):
    """Upload voice message"""
    try:
        room_id = request.POST.get('room_id')
        voice_file = request.FILES.get('voice_file')
        duration = request.POST.get('duration', 0)

        if not room_id or not voice_file:
            return JsonResponse({'error': 'Room ID and voice file required'}, status=400)

        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)

        # Create voice message
        message = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            message='',
            message_type='voice',
            file_attachment=voice_file,
            voice_duration=int(duration) if duration else None
        )

        # Update room timestamp
        room.updated_at = timezone.now()
        room.save()

        return JsonResponse({
            'success': True,
            'message': serialize_message_enhanced(message)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)