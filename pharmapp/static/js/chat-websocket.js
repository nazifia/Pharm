/**
 * WebSocket Chat Implementation
 * Provides real-time messaging and online status functionality
 */

class ChatWebSocket {
    constructor() {
        this.chatSocket = null;
        this.onlineSocket = null;
        this.currentRoomId = null;
        this.currentUserId = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.typingTimer = null;
        this.typingTimeout = 3000; // 3 seconds
        
        this.init();
    }

    init() {
        // Initialize online status WebSocket
        this.initOnlineStatusSocket();
        
        // Bind event listeners
        this.bindEventListeners();
    }

    initOnlineStatusSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/online/`;
        
        this.onlineSocket = new WebSocket(wsUrl);
        
        this.onlineSocket.onopen = () => {
            console.log('Online status WebSocket connected');
            this.reconnectAttempts = 0;
        };
        
        this.onlineSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleOnlineStatusMessage(data);
        };
        
        this.onlineSocket.onclose = () => {
            console.log('Online status WebSocket disconnected');
            this.reconnectOnlineSocket();
        };
        
        this.onlineSocket.onerror = (error) => {
            console.error('Online status WebSocket error:', error);
        };
    }

    initChatSocket(roomId, userId = null) {
        if (this.chatSocket) {
            this.chatSocket.close();
        }
        
        this.currentRoomId = roomId;
        this.currentUserId = userId;
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let wsUrl;
        
        if (roomId) {
            wsUrl = `${protocol}//${window.location.host}/ws/chat/room/${roomId}/`;
        } else if (userId) {
            wsUrl = `${protocol}//${window.location.host}/ws/chat/user/${userId}/`;
        } else {
            console.error('No room ID or user ID provided');
            return;
        }
        
        this.chatSocket = new WebSocket(wsUrl);
        
        this.chatSocket.onopen = () => {
            console.log('Chat WebSocket connected');
            this.reconnectAttempts = 0;
        };
        
        this.chatSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleChatMessage(data);
        };
        
        this.chatSocket.onclose = () => {
            console.log('Chat WebSocket disconnected');
            this.reconnectChatSocket();
        };
        
        this.chatSocket.onerror = (error) => {
            console.error('Chat WebSocket error:', error);
        };
    }

    sendMessage(message) {
        if (this.chatSocket && this.chatSocket.readyState === WebSocket.OPEN) {
            this.chatSocket.send(JSON.stringify({
                'type': 'chat_message',
                'message': message
            }));
        } else {
            console.error('Chat WebSocket is not connected');
        }
    }

    sendTypingStatus(isTyping) {
        if (this.chatSocket && this.chatSocket.readyState === WebSocket.OPEN) {
            this.chatSocket.send(JSON.stringify({
                'type': 'typing',
                'is_typing': isTyping
            }));
        }
    }

    markMessagesRead(messageIds) {
        if (this.chatSocket && this.chatSocket.readyState === WebSocket.OPEN) {
            this.chatSocket.send(JSON.stringify({
                'type': 'mark_read',
                'message_ids': messageIds
            }));
        }
    }

    handleChatMessage(data) {
        switch (data.type) {
            case 'chat_message':
                this.displayMessage(data.message);
                this.playNotificationSound();
                break;
            case 'typing_status':
                this.updateTypingIndicator(data);
                break;
            case 'messages_read':
                this.updateMessageReadStatus(data);
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    handleOnlineStatusMessage(data) {
        switch (data.type) {
            case 'online_users_list':
                this.updateOnlineUsersList(data.users);
                break;
            case 'user_status_update':
                this.updateUserOnlineStatus(data);
                break;
            default:
                console.log('Unknown online status message type:', data.type);
        }
    }

    displayMessage(message) {
        const messagesContainer = document.getElementById('chat-messages-container');
        if (!messagesContainer) return;

        const messageDiv = document.createElement('div');
        const isOwn = message.sender_id === parseInt(document.body.dataset.userId);
        
        messageDiv.className = `message-item mb-3 ${isOwn ? 'text-right' : ''}`;
        messageDiv.setAttribute('data-message-id', message.id);
        
        const timestamp = new Date(message.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        messageDiv.innerHTML = `
            <div class="message-bubble ${isOwn ? 'own-message' : 'other-message'}">
                <div class="message-content">${this.escapeHtml(message.message)}</div>
                <div class="message-meta">
                    <small class="text-muted">
                        ${!isOwn ? message.sender_username + ' • ' : ''}${timestamp}
                        ${isOwn ? '<span class="message-status" data-status="' + message.status + '">✓</span>' : ''}
                    </small>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Update unread count
        this.updateUnreadCount();
    }

    updateTypingIndicator(data) {
        const typingContainer = document.getElementById('typing-indicator');
        if (!typingContainer) return;
        
        if (data.is_typing) {
            typingContainer.innerHTML = `<small class="text-muted">${data.username} is typing...</small>`;
            typingContainer.style.display = 'block';
        } else {
            typingContainer.style.display = 'none';
        }
    }

    updateMessageReadStatus(data) {
        data.message_ids.forEach(messageId => {
            const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
            if (messageElement) {
                const statusElement = messageElement.querySelector('.message-status');
                if (statusElement) {
                    statusElement.textContent = '✓✓';
                    statusElement.classList.add('read');
                }
            }
        });
    }

    updateOnlineUsersList(users) {
        const onlineUsersContainer = document.getElementById('online-users-list');
        if (!onlineUsersContainer) return;
        
        onlineUsersContainer.innerHTML = '';
        
        users.forEach(user => {
            const userElement = document.createElement('div');
            userElement.className = 'online-user-item d-flex align-items-center mb-2';
            userElement.innerHTML = `
                <div class="online-indicator"></div>
                <span class="ml-2">${this.escapeHtml(user.username)}</span>
            `;
            onlineUsersContainer.appendChild(userElement);
        });
        
        // Update online count
        const onlineCountElement = document.getElementById('online-count');
        if (onlineCountElement) {
            onlineCountElement.textContent = users.length;
        }
    }

    updateUserOnlineStatus(data) {
        // Update individual user status in the UI
        const userElements = document.querySelectorAll(`[data-user-id="${data.user_id}"]`);
        userElements.forEach(element => {
            const indicator = element.querySelector('.online-indicator');
            if (indicator) {
                indicator.classList.toggle('online', data.is_online);
                indicator.classList.toggle('offline', !data.is_online);
            }
        });
        
        // Update online users list
        if (data.is_online) {
            // Add user to online list if not already there
            const onlineUsersContainer = document.getElementById('online-users-list');
            if (onlineUsersContainer && !onlineUsersContainer.querySelector(`[data-user-id="${data.user_id}"]`)) {
                const userElement = document.createElement('div');
                userElement.className = 'online-user-item d-flex align-items-center mb-2';
                userElement.setAttribute('data-user-id', data.user_id);
                userElement.innerHTML = `
                    <div class="online-indicator online"></div>
                    <span class="ml-2">${this.escapeHtml(data.username)}</span>
                `;
                onlineUsersContainer.appendChild(userElement);
            }
        } else {
            // Remove user from online list
            const userElement = document.querySelector(`#online-users-list [data-user-id="${data.user_id}"]`);
            if (userElement) {
                userElement.remove();
            }
        }
    }

    bindEventListeners() {
        // Message form submission
        const messageForm = document.getElementById('quick-message-form');
        if (messageForm) {
            messageForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const messageInput = document.getElementById('message-input');
                const message = messageInput.value.trim();
                
                if (message) {
                    this.sendMessage(message);
                    messageInput.value = '';
                    this.sendTypingStatus(false);
                }
            });
        }
        
        // Typing indicator
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.addEventListener('input', () => {
                this.sendTypingStatus(true);
                
                // Clear previous timer
                if (this.typingTimer) {
                    clearTimeout(this.typingTimer);
                }
                
                // Set new timer to stop typing indicator
                this.typingTimer = setTimeout(() => {
                    this.sendTypingStatus(false);
                }, this.typingTimeout);
            });
            
            messageInput.addEventListener('blur', () => {
                this.sendTypingStatus(false);
            });
        }
    }

    reconnectChatSocket() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect chat socket (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.initChatSocket(this.currentRoomId, this.currentUserId);
            }, this.reconnectDelay * this.reconnectAttempts);
        }
    }

    reconnectOnlineSocket() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect online socket (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.initOnlineStatusSocket();
            }, this.reconnectDelay * this.reconnectAttempts);
        }
    }

    playNotificationSound() {
        // Create a simple notification sound
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.1);
    }

    updateUnreadCount() {
        // Update unread message count in the UI
        const unreadIndicator = document.getElementById('unread-chat-indicator');
        if (unreadIndicator) {
            // This would typically fetch from an API or maintain a local count
            // For now, we'll just show the indicator
            unreadIndicator.style.display = 'inline';
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    disconnect() {
        if (this.chatSocket) {
            this.chatSocket.close();
        }
        if (this.onlineSocket) {
            this.onlineSocket.close();
        }
    }
}

// Initialize WebSocket when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.chatWebSocket = new ChatWebSocket();
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (window.chatWebSocket) {
        window.chatWebSocket.disconnect();
    }
});
