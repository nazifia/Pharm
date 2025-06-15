#!/usr/bin/env python
"""
Basic test script for chat functionality
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.contrib.auth import get_user_model
from chat.models import ChatRoom, ChatMessage, UserChatStatus
from django.utils import timezone

User = get_user_model()

def test_basic_chat_functionality():
    """Test basic chat functionality"""
    print("🧪 Testing Basic Chat Functionality...")
    
    # Create test users
    try:
        user1 = User.objects.create_user(
            username='testuser1',
            mobile='1111111111',
            password='testpass123'
        )
        print("✓ Created test user 1")
    except Exception as e:
        user1 = User.objects.get(mobile='1111111111')
        print(f"✓ Using existing test user 1")
    
    try:
        user2 = User.objects.create_user(
            username='testuser2',
            mobile='2222222222',
            password='testpass123'
        )
        print("✓ Created test user 2")
    except Exception as e:
        user2 = User.objects.get(mobile='2222222222')
        print(f"✓ Using existing test user 2")
    
    # Test room creation
    room, created = ChatRoom.get_or_create_direct_room(user1, user2)
    if created:
        print("✓ Created new chat room")
    else:
        print("✓ Using existing chat room")
    
    print(f"  Room ID: {room.id}")
    print(f"  Room type: {room.room_type}")
    print(f"  Participants: {[u.username for u in room.participants.all()]}")
    
    # Test message creation
    message = ChatMessage.objects.create(
        room=room,
        sender=user1,
        receiver=user2,
        message="Hello from test script!",
        message_type='text'
    )
    print("✓ Created test message")
    print(f"  Message ID: {message.id}")
    print(f"  Message: {message.message}")
    print(f"  Sender: {message.sender.username}")
    
    # Test user status
    status, created = UserChatStatus.objects.get_or_create(
        user=user1,
        defaults={'is_online': True, 'last_seen': timezone.now()}
    )
    if created:
        print("✓ Created user status")
    else:
        print("✓ Updated user status")
    
    # Test message read status
    message.mark_as_read(user2)
    print("✓ Marked message as read")
    
    is_read = message.is_read_by(user2)
    print(f"  Message read by user2: {is_read}")
    
    # Test unread count
    unread_count = ChatMessage.objects.filter(
        room__participants=user2,
        is_read=False
    ).exclude(sender=user2).count()
    print(f"  Unread messages for user2: {unread_count}")
    
    print("✅ Basic chat functionality test completed successfully!")
    return True

def test_models_import():
    """Test that all models can be imported"""
    print("📦 Testing Model Imports...")
    
    try:
        from chat.models import ChatRoom, ChatMessage, UserChatStatus, MessageReadStatus
        print("✓ All chat models imported successfully")
        
        from chat.forms import ChatMessageForm, QuickMessageForm
        print("✓ All chat forms imported successfully")
        
        from chat.views import chat_view, unread_messages_count
        print("✓ All chat views imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_url_patterns():
    """Test URL patterns"""
    print("🔗 Testing URL Patterns...")
    
    try:
        from django.urls import reverse
        
        urls_to_test = [
            'chat:chat_view_default',
            'chat:unread_messages_count',
            'chat:get_online_users',
        ]
        
        for url_name in urls_to_test:
            try:
                url = reverse(url_name)
                print(f"  ✓ {url_name} -> {url}")
            except Exception as e:
                print(f"  ❌ {url_name} failed: {e}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ URL test error: {e}")
        return False

def cleanup_test_data():
    """Clean up test data"""
    print("🧹 Cleaning up test data...")
    
    try:
        # Delete test users and related data
        User.objects.filter(mobile__in=['1111111111', '2222222222']).delete()
        print("✓ Test data cleaned up")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

def main():
    """Main test function"""
    print("🚀 Starting Chat System Tests...")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Test 1: Model imports
    if not test_models_import():
        all_tests_passed = False
    
    print()
    
    # Test 2: URL patterns
    if not test_url_patterns():
        all_tests_passed = False
    
    print()
    
    # Test 3: Basic functionality
    if not test_basic_chat_functionality():
        all_tests_passed = False
    
    print()
    
    # Cleanup
    cleanup_test_data()
    
    print("=" * 50)
    if all_tests_passed:
        print("🎉 All tests passed! Chat system is working correctly.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return all_tests_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
