/**
 * Real-time Chat Implementation using Enhanced AJAX Polling
 * Provides near real-time messaging and online status functionality
 */

class RealtimeChat {
    constructor() {
        this.currentRoomId = null;
        this.lastMessageId = null;
        this.pollInterval = null;
        this.onlineStatusInterval = null;
        this.typingTimer = null;
        this.isTyping = false;
        this.pollFrequency = 2000; // Poll every 2 seconds for messages
        this.onlineCheckFrequency = 10000; // Check online status every 10 seconds
        this.typingTimeout = 3000; // Stop typing indicator after 3 seconds
        this.messageSound = null;
        
        this.init();
    }

    init() {
        this.bindEventListeners();
        this.initializeAudio();
        this.startOnlineStatusPolling();
        this.showConnectionStatus();

        // Get current room ID if on chat page
        const roomIdElement = document.getElementById('room-id');
        if (roomIdElement) {
            this.currentRoomId = roomIdElement.value;
            this.startMessagePolling();
        }
    }

    initializeAudio() {
        // Create audio context for notification sounds
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
            console.log('Audio context not supported');
        }
    }

    startMessagePolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
        
        if (!this.currentRoomId) return;
        
        // Initial load
        this.fetchNewMessages();
        
        // Start polling
        this.pollInterval = setInterval(() => {
            this.fetchNewMessages();
        }, this.pollFrequency);
    }

    stopMessagePolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    startOnlineStatusPolling() {
        if (this.onlineStatusInterval) {
            clearInterval(this.onlineStatusInterval);
        }
        
        // Initial load
        this.fetchOnlineUsers();
        
        // Start polling
        this.onlineStatusInterval = setInterval(() => {
            this.fetchOnlineUsers();
        }, this.onlineCheckFrequency);
    }

    fetchNewMessages() {
        if (!this.currentRoomId) return;
        
        const url = new URL('/chat/api/get-new-messages/', window.location.origin);
        url.searchParams.append('room_id', this.currentRoomId);
        if (this.lastMessageId) {
            url.searchParams.append('after_id', this.lastMessageId);
        }
        
        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.messages && data.messages.length > 0) {
                data.messages.forEach(message => {
                    this.displayMessage(message);
                    this.lastMessageId = message.id;
                });
                
                // Play notification sound for new messages
                if (data.messages.some(msg => msg.sender_id !== parseInt(document.body.dataset.userId))) {
                    this.playNotificationSound();
                }
                
                // Scroll to bottom
                this.scrollToBottom();
            }
            
            // Update typing indicators
            if (data.typing_users) {
                this.updateTypingIndicators(data.typing_users);
            }
        })
        .catch(error => {
            console.error('Error fetching new messages:', error);
        });
    }

    fetchOnlineUsers() {
        fetch('/chat/api/online-users/', {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.updateOnlineUsersList(data.online_users);
            }
        })
        .catch(error => {
            console.error('Error fetching online users:', error);
        });
    }

    sendMessage(message) {
        if (!this.currentRoomId || !message.trim()) return;
        
        fetch('/chat/api/send-message/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                room_id: this.currentRoomId,
                message: message
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Message will appear via polling
                this.setTypingStatus(false);
                
                // Immediately fetch new messages to show sent message
                setTimeout(() => this.fetchNewMessages(), 100);
            } else {
                console.error('Error sending message:', data.error);
                alert('Failed to send message. Please try again.');
            }
        })
        .catch(error => {
            console.error('Error sending message:', error);
            alert('Failed to send message. Please check your connection.');
        });
    }

    setTypingStatus(isTyping) {
        if (!this.currentRoomId) return;
        
        fetch('/chat/api/set-typing/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                room_id: this.currentRoomId,
                is_typing: isTyping
            })
        })
        .catch(error => {
            console.error('Error setting typing status:', error);
        });
    }

    displayMessage(message) {
        const messagesContainer = document.getElementById('chat-messages-container');
        if (!messagesContainer) return;

        // Check if message already exists
        if (document.querySelector(`[data-message-id="${message.id}"]`)) {
            return;
        }

        const messageDiv = document.createElement('div');
        const isOwn = message.sender_id === parseInt(document.body.dataset.userId);
        
        messageDiv.className = `message-item mb-3 ${isOwn ? 'text-right' : ''}`;
        messageDiv.setAttribute('data-message-id', message.id);
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateY(20px)';
        
        const timestamp = new Date(message.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        messageDiv.innerHTML = `
            <div class="d-inline-block p-2 rounded ${isOwn ? 'bg-primary text-white' : 'bg-light'}" style="max-width: 75%;">
                ${!isOwn ? `<small class="font-weight-bold text-muted d-block">${this.escapeHtml(message.sender_username)}</small>` : ''}
                <div>${this.escapeHtml(message.message)}</div>
                <div class="d-flex justify-content-between align-items-center mt-1">
                    <small class="${isOwn ? 'text-light' : 'text-muted'}">${timestamp}</small>
                    ${isOwn ? `<small class="text-light message-status" data-status="${message.status}">
                        ${message.status === 'read' ? '<i class="fas fa-check-double"></i>' : 
                          message.status === 'delivered' ? '<i class="fas fa-check"></i>' : 
                          '<i class="far fa-clock"></i>'}
                    </small>` : ''}
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        
        // Animate message appearance
        setTimeout(() => {
            messageDiv.style.transition = 'all 0.3s ease-out';
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
        }, 10);
    }

    updateOnlineUsersList(onlineUsers) {
        const onlineUsersContainer = document.getElementById('online-users-list');
        const onlineCountElement = document.getElementById('online-count');
        
        if (!onlineUsersContainer) return;
        
        onlineUsersContainer.innerHTML = '';
        
        if (onlineUsers.length === 0) {
            onlineUsersContainer.innerHTML = '<div class="text-center text-muted p-2">No users online</div>';
        } else {
            onlineUsers.forEach(user => {
                const userElement = document.createElement('div');
                userElement.className = 'online-user-item d-flex align-items-center p-2 border-bottom';
                userElement.setAttribute('data-user-id', user.id);
                userElement.innerHTML = `
                    <div class="online-indicator online"></div>
                    <span class="ml-2">${this.escapeHtml(user.username)}</span>
                    <small class="ml-auto text-muted">${user.last_seen ? this.timeAgo(user.last_seen) : 'now'}</small>
                `;
                onlineUsersContainer.appendChild(userElement);
            });
        }
        
        // Update online count
        if (onlineCountElement) {
            onlineCountElement.textContent = onlineUsers.length;
        }
        
        // Update individual user indicators throughout the page
        this.updateUserIndicators(onlineUsers);
    }

    updateUserIndicators(onlineUsers) {
        const onlineUserIds = onlineUsers.map(user => user.id);
        
        // Update all user status indicators
        document.querySelectorAll('[data-user-id]').forEach(element => {
            const userId = parseInt(element.getAttribute('data-user-id'));
            const indicator = element.querySelector('.online-indicator, .user-status-indicator');
            
            if (indicator) {
                if (onlineUserIds.includes(userId)) {
                    indicator.classList.add('online');
                    indicator.classList.remove('offline');
                } else {
                    indicator.classList.add('offline');
                    indicator.classList.remove('online');
                }
            }
        });
    }

    updateTypingIndicators(typingUsers) {
        const typingIndicator = document.getElementById('typing-indicator');
        if (!typingIndicator) return;
        
        const currentUserId = parseInt(document.body.dataset.userId);
        const otherTypingUsers = typingUsers.filter(user => user.id !== currentUserId);
        
        if (otherTypingUsers.length > 0) {
            const usernames = otherTypingUsers.map(user => user.username).join(', ');
            typingIndicator.innerHTML = `<small class="text-muted"><i class="fas fa-ellipsis-h"></i> ${usernames} ${otherTypingUsers.length === 1 ? 'is' : 'are'} typing...</small>`;
            typingIndicator.style.display = 'block';
        } else {
            typingIndicator.style.display = 'none';
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
                }
            });
        }
        
        // Typing indicator
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.addEventListener('input', () => {
                if (!this.isTyping) {
                    this.setTypingStatus(true);
                    this.isTyping = true;
                }
                
                // Clear previous timer
                if (this.typingTimer) {
                    clearTimeout(this.typingTimer);
                }
                
                // Set new timer to stop typing indicator
                this.typingTimer = setTimeout(() => {
                    this.setTypingStatus(false);
                    this.isTyping = false;
                }, this.typingTimeout);
            });
            
            messageInput.addEventListener('blur', () => {
                this.setTypingStatus(false);
                this.isTyping = false;
            });
        }
        
        // Handle page visibility changes to adjust polling frequency
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Reduce polling frequency when page is not visible
                this.pollFrequency = 10000; // 10 seconds
            } else {
                // Increase polling frequency when page is visible
                this.pollFrequency = 2000; // 2 seconds
                // Immediately fetch new messages when page becomes visible
                this.fetchNewMessages();
            }
            
            // Restart polling with new frequency
            if (this.currentRoomId) {
                this.startMessagePolling();
            }
        });
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('chat-messages-container');
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    playNotificationSound() {
        if (!this.audioContext) return;
        
        try {
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.3, this.audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.1);
            
            oscillator.start(this.audioContext.currentTime);
            oscillator.stop(this.audioContext.currentTime + 0.1);
        } catch (e) {
            console.log('Could not play notification sound');
        }
    }

    timeAgo(dateString) {
        const now = new Date();
        const date = new Date(dateString);
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) return 'now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        return `${Math.floor(diffInSeconds / 86400)}d ago`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    switchRoom(roomId) {
        this.stopMessagePolling();
        this.currentRoomId = roomId;
        this.lastMessageId = null;
        
        if (roomId) {
            this.startMessagePolling();
        }
    }

    showConnectionStatus() {
        const statusElement = document.getElementById('chat-connection-status');
        if (statusElement) {
            statusElement.style.display = 'block';
            statusElement.className = 'connection-status connected';
            statusElement.innerHTML = '<i class="fas fa-wifi"></i> Real-time Chat Active';

            // Hide after 3 seconds
            setTimeout(() => {
                statusElement.style.display = 'none';
            }, 3000);
        }
    }

    showDisconnectedStatus() {
        const statusElement = document.getElementById('chat-connection-status');
        if (statusElement) {
            statusElement.style.display = 'block';
            statusElement.className = 'connection-status disconnected';
            statusElement.innerHTML = '<i class="fas fa-wifi-slash"></i> Connection Lost';
        }
    }

    destroy() {
        this.stopMessagePolling();
        if (this.onlineStatusInterval) {
            clearInterval(this.onlineStatusInterval);
        }
        if (this.typingTimer) {
            clearTimeout(this.typingTimer);
        }

        // Show disconnected status
        this.showDisconnectedStatus();
    }
}

// Initialize real-time chat when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.realtimeChat = new RealtimeChat();
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (window.realtimeChat) {
        window.realtimeChat.destroy();
    }
});
