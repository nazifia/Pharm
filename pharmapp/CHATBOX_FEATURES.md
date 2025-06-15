# Enhanced Chatbox Features

## Overview
The pharmacy application now includes a comprehensive chat system that allows registered users to communicate with each other in real-time. The chatbox is integrated throughout the application and provides both a full-page interface and a floating widget.

## Features

### 1. **Real-time Messaging**
- Instant message delivery between registered users
- AJAX-powered messaging without page refreshes
- Message status indicators (sent, delivered, read)
- Typing indicators to show when someone is typing

### 2. **User Interface Components**

#### Full Chat Interface (`/chat/`)
- **Sidebar with three sections:**
  - Online Users: Shows currently active users
  - Recent Chats: Displays recent conversations with unread counts
  - All Users: Complete list of registered users
- **Main Chat Area:**
  - Message history with timestamps
  - File attachment support
  - Message status indicators
  - Typing indicators
  - Real-time message updates

#### Floating Chat Widget
- **Always accessible** from any page for authenticated users
- **Minimizable** chat window
- **Unread message badge** on the chat toggle button
- **User search** functionality
- **Quick messaging** interface

### 3. **Enhanced Models**

#### ChatRoom
- Supports both direct messages and group chats
- UUID-based identification for security
- Participant management
- Automatic room creation for direct messages

#### ChatMessage
- Enhanced message types (text, file, image, system)
- Message status tracking
- File attachment support
- Reply-to functionality
- Edit timestamps

#### UserChatStatus
- Online/offline status tracking
- Typing indicators
- Last seen timestamps

#### MessageReadStatus
- Individual read receipts
- Read timestamp tracking

### 4. **API Endpoints**
- `/chat/api/unread-count/` - Get unread message count
- `/chat/api/typing/` - Set typing status
- `/chat/api/typing/<room_id>/` - Get typing users in a room
- `/chat/api/online-users/` - Get list of online users

### 5. **User Permissions Integration**
The chat system respects the existing user role system:
- All authenticated users can access chat
- Admin users have full access to chat administration
- Role-based restrictions can be easily added

### 6. **Responsive Design**
- Mobile-friendly interface
- Adaptive layouts for different screen sizes
- Touch-friendly controls
- Optimized for both desktop and mobile use

## Technical Implementation

### Backend (Django)
- **Models**: Enhanced chat models with relationships
- **Views**: AJAX-enabled views for real-time functionality
- **URLs**: RESTful URL patterns for chat operations
- **Admin**: Django admin integration for chat management

### Frontend
- **HTML/CSS**: Bootstrap-based responsive design
- **JavaScript**: Vanilla JS for real-time features
- **AJAX**: For seamless message sending and receiving
- **CSS Animations**: Smooth transitions and loading states

### Database
- **SQLite**: Default database with proper indexing
- **Migrations**: Automatic database schema updates
- **Backward Compatibility**: Legacy message support

## Usage Instructions

### For Users
1. **Access Chat**: Click the "Chat" link in the navigation bar
2. **Start Conversation**: Select a user from the sidebar
3. **Send Messages**: Type in the message input and press Enter or click Send
4. **File Sharing**: Click the paperclip icon to attach files
5. **Floating Widget**: Use the floating chat button on any page for quick access

### For Administrators
1. **Admin Panel**: Access chat management through Django admin
2. **User Management**: Monitor chat activity and user status
3. **Message Moderation**: View and manage chat messages
4. **Room Management**: Create and manage chat rooms

## Security Features
- **Authentication Required**: Only registered users can access chat
- **CSRF Protection**: All forms include CSRF tokens
- **Input Validation**: Message content is validated and sanitized
- **File Upload Security**: File type restrictions and validation
- **Permission Checks**: User permissions are verified for all operations

## Performance Optimizations
- **Pagination**: Message history is paginated for better performance
- **Caching**: User status and online indicators are cached
- **Efficient Queries**: Optimized database queries with select_related and prefetch_related
- **AJAX Updates**: Only necessary data is transferred

## Browser Compatibility
- **Modern Browsers**: Chrome, Firefox, Safari, Edge
- **Mobile Browsers**: iOS Safari, Chrome Mobile, Samsung Internet
- **Progressive Enhancement**: Basic functionality works without JavaScript

## Future Enhancements
- **WebSocket Support**: Real-time updates using Django Channels
- **Push Notifications**: Browser notifications for new messages
- **Message Encryption**: End-to-end encryption for sensitive communications
- **Voice Messages**: Audio message support
- **Video Calls**: Integration with WebRTC for video calling
- **Message Search**: Full-text search across chat history
- **Message Reactions**: Emoji reactions to messages
- **Group Chat Management**: Advanced group chat features

## Troubleshooting

### Common Issues
1. **Messages not sending**: Check network connection and authentication
2. **Floating widget not appearing**: Ensure user is authenticated
3. **Typing indicators not working**: Check JavaScript console for errors
4. **File uploads failing**: Verify file size and type restrictions

### Debug Mode
Enable Django debug mode to see detailed error messages:
```python
DEBUG = True
```

### Logging
Chat activities are logged for debugging:
- Message sending/receiving
- User online status changes
- File upload attempts
- Error conditions

## Configuration

### Settings
Add to Django settings for customization:
```python
# Chat settings
CHAT_MESSAGE_MAX_LENGTH = 1000
CHAT_FILE_UPLOAD_MAX_SIZE = 10 * 1024 * 1024  # 10MB
CHAT_ALLOWED_FILE_TYPES = ['image/*', 'application/pdf', '.doc', '.docx', '.txt']
CHAT_ONLINE_TIMEOUT = 300  # 5 minutes
```

### URL Configuration
The chat URLs are included in the main URL configuration:
```python
path('chat/', include('chat.urls')),
```

## Support
For technical support or feature requests, contact the development team or create an issue in the project repository.
