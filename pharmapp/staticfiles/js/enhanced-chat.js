/**
 * Enhanced Chat System with Advanced Features
 * Includes voice messages, reactions, file sharing, and more
 */

class EnhancedChat {
    constructor() {
        this.currentRoomId = null;
        this.currentReplyTo = null;
        this.currentMessageForReaction = null;
        this.isRecording = false;
        this.mediaRecorder = null;
        this.recordingStartTime = null;
        this.recordingTimer = null;
        this.typingTimer = null;
        this.isTyping = false;
        this.lastMessageId = null;
        this.pollInterval = null;
        this.emojiPicker = null;
        
        this.init();
    }

    init() {
        this.bindEventListeners();
        this.initializeEmojiPicker();
        this.startMessagePolling();
        this.loadUserPreferences();
        
        // Get current room ID
        const roomIdElement = document.getElementById('room-id');
        if (roomIdElement) {
            this.currentRoomId = roomIdElement.value;
        }
    }

    bindEventListeners() {
        // Message input events
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
            messageInput.addEventListener('input', () => this.handleTyping());
            messageInput.addEventListener('paste', (e) => this.handlePaste(e));
        }

        // File input events
        document.getElementById('image-input')?.addEventListener('change', (e) => this.handleFileSelect(e, 'image'));
        document.getElementById('file-input')?.addEventListener('change', (e) => this.handleFileSelect(e, 'file'));

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleGlobalKeyDown(e));

        // Visibility change for read receipts
        document.addEventListener('visibilitychange', () => this.handleVisibilityChange());
    }

    handleKeyDown(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        } else if (event.key === 'Escape') {
            this.cancelReply();
            this.hideEmojiPicker();
        }
    }

    handleGlobalKeyDown(event) {
        // Ctrl/Cmd + F for search
        if ((event.ctrlKey || event.metaKey) && event.key === 'f') {
            event.preventDefault();
            this.toggleChatSearch();
        }
        
        // Ctrl/Cmd + R for reply to last message
        if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
            event.preventDefault();
            this.replyToLastMessage();
        }
    }

    handleTyping() {
        if (!this.isTyping) {
            this.isTyping = true;
            this.sendTypingStatus(true);
        }

        clearTimeout(this.typingTimer);
        this.typingTimer = setTimeout(() => {
            this.isTyping = false;
            this.sendTypingStatus(false);
        }, 3000);
    }

    handlePaste(event) {
        const items = event.clipboardData.items;
        
        for (let item of items) {
            if (item.type.indexOf('image') !== -1) {
                event.preventDefault();
                const file = item.getAsFile();
                this.uploadFile(file, 'image');
                break;
            }
        }
    }

    sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();
        
        if (!message && !this.currentReplyTo) return;
        
        const messageData = {
            room_id: this.currentRoomId,
            message: message,
            message_type: 'text',
            reply_to: this.currentReplyTo
        };

        this.sendMessageToServer(messageData);
        
        input.value = '';
        input.style.height = 'auto';
        this.cancelReply();
        this.hideEmojiPicker();
    }

    sendMessageToServer(messageData) {
        fetch('/chat/api/send-message/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(messageData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.addMessageToUI(data.message);
                this.scrollToBottom();
                this.playNotificationSound();
            } else {
                this.showError('Failed to send message: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error sending message:', error);
            this.showError('Failed to send message. Please try again.');
        });
    }

    replyToMessage(messageId, messageText, senderName) {
        this.currentReplyTo = messageId;
        document.getElementById('reply-username').textContent = senderName;
        document.getElementById('reply-message').textContent = messageText;
        document.getElementById('reply-preview').style.display = 'flex';
        document.getElementById('message-input').focus();
    }

    cancelReply() {
        this.currentReplyTo = null;
        document.getElementById('reply-preview').style.display = 'none';
    }

    replyToLastMessage() {
        const messages = document.querySelectorAll('.message-wrapper.received');
        if (messages.length > 0) {
            const lastMessage = messages[messages.length - 1];
            const messageId = lastMessage.dataset.messageId;
            const messageText = lastMessage.querySelector('.message-content p')?.textContent || '';
            const senderName = 'User'; // Get from data attribute or API
            this.replyToMessage(messageId, messageText, senderName);
        }
    }

    // Reaction System
    showReactionPicker(messageId) {
        this.currentMessageForReaction = messageId;
        const modal = new bootstrap.Modal(document.getElementById('reactionModal'));
        modal.show();
    }

    addReaction(emoji) {
        if (!this.currentMessageForReaction) return;

        fetch('/chat/api/add-reaction/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                message_id: this.currentMessageForReaction,
                reaction: emoji
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.updateMessageReactions(this.currentMessageForReaction, data.reactions);
            }
        })
        .catch(error => console.error('Error adding reaction:', error));

        bootstrap.Modal.getInstance(document.getElementById('reactionModal')).hide();
        this.currentMessageForReaction = null;
    }

    updateMessageReactions(messageId, reactions) {
        const reactionsContainer = document.getElementById(`reactions-${messageId}`);
        if (!reactionsContainer) return;

        reactionsContainer.innerHTML = '';
        
        Object.entries(reactions).forEach(([emoji, users]) => {
            if (users.length > 0) {
                const reactionElement = document.createElement('span');
                reactionElement.className = 'reaction-badge';
                reactionElement.innerHTML = `${emoji} ${users.length}`;
                reactionElement.title = users.join(', ');
                reactionsContainer.appendChild(reactionElement);
            }
        });
    }

    // File Handling
    selectFile(type) {
        const input = document.getElementById(`${type}-input`);
        input.click();
        this.hideAttachmentMenu();
    }

    handleFileSelect(event, type) {
        const file = event.target.files[0];
        if (file) {
            this.uploadFile(file, type);
        }
        event.target.value = ''; // Reset input
    }

    uploadFile(file, type) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('room_id', this.currentRoomId);
        formData.append('message_type', type);

        // Show upload progress
        this.showUploadProgress(file.name);

        fetch('/chat/api/upload-file/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            this.hideUploadProgress();
            if (data.success) {
                this.addMessageToUI(data.message);
                this.scrollToBottom();
            } else {
                this.showError('Failed to upload file: ' + data.error);
            }
        })
        .catch(error => {
            this.hideUploadProgress();
            console.error('Error uploading file:', error);
            this.showError('Failed to upload file. Please try again.');
        });
    }

    // Voice Recording
    async startVoiceRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            this.recordingStartTime = Date.now();
            
            const audioChunks = [];
            this.mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                this.uploadVoiceMessage(audioBlob);
                stream.getTracks().forEach(track => track.stop());
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            this.showRecordingInterface();
            this.startRecordingTimer();
            this.hideAttachmentMenu();

        } catch (error) {
            console.error('Error starting voice recording:', error);
            this.showError('Could not access microphone. Please check permissions.');
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            this.hideRecordingInterface();
            this.stopRecordingTimer();
        }
    }

    cancelRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            this.hideRecordingInterface();
            this.stopRecordingTimer();
        }
    }

    uploadVoiceMessage(audioBlob) {
        const formData = new FormData();
        formData.append('voice_file', audioBlob, 'voice_message.wav');
        formData.append('room_id', this.currentRoomId);
        formData.append('message_type', 'voice');
        formData.append('duration', Math.floor((Date.now() - this.recordingStartTime) / 1000));

        fetch('/chat/api/upload-voice/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.addMessageToUI(data.message);
                this.scrollToBottom();
            } else {
                this.showError('Failed to send voice message: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error uploading voice message:', error);
            this.showError('Failed to send voice message. Please try again.');
        });
    }

    // UI Helper Methods
    showRecordingInterface() {
        document.getElementById('voice-recording').style.display = 'flex';
        document.getElementById('message-input-area').style.display = 'none';
    }

    hideRecordingInterface() {
        document.getElementById('voice-recording').style.display = 'none';
        document.getElementById('message-input-area').style.display = 'flex';
    }

    startRecordingTimer() {
        this.recordingTimer = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            document.getElementById('recording-time').textContent = 
                `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
    }

    stopRecordingTimer() {
        if (this.recordingTimer) {
            clearInterval(this.recordingTimer);
            this.recordingTimer = null;
        }
    }

    toggleAttachmentMenu() {
        const menu = document.getElementById('attachment-menu');
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    }

    hideAttachmentMenu() {
        document.getElementById('attachment-menu').style.display = 'none';
    }

    toggleChatSearch() {
        const searchDiv = document.getElementById('chat-search');
        searchDiv.style.display = searchDiv.style.display === 'none' ? 'block' : 'none';
        if (searchDiv.style.display === 'block') {
            document.getElementById('search-input').focus();
        }
    }

    searchMessages() {
        const query = document.getElementById('search-input').value.trim();
        if (!query) return;

        // Highlight matching messages
        const messages = document.querySelectorAll('.message-content p');
        messages.forEach(message => {
            const text = message.textContent;
            if (text.toLowerCase().includes(query.toLowerCase())) {
                message.innerHTML = text.replace(
                    new RegExp(query, 'gi'),
                    `<mark>$&</mark>`
                );
                message.closest('.message-wrapper').scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    }

    // Utility Methods
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    scrollToBottom() {
        const container = document.getElementById('messages-container');
        container.scrollTop = container.scrollHeight;
    }

    showError(message) {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = 'toast-notification error';
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    playNotificationSound() {
        // Play notification sound if enabled
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.volume = 0.3;
        audio.play().catch(() => {}); // Ignore errors
    }

    addMessageToUI(message) {
        // Add new message to the UI
        const messagesList = document.getElementById('messages-list');
        const messageElement = this.createMessageElement(message);
        messagesList.appendChild(messageElement);
    }

    createMessageElement(message) {
        // Create message DOM element
        const wrapper = document.createElement('div');
        wrapper.className = `message-wrapper ${message.sender_id === window.currentUserId ? 'sent' : 'received'}`;
        wrapper.dataset.messageId = message.id;
        
        // Message content will be built based on message type
        wrapper.innerHTML = this.buildMessageHTML(message);
        
        return wrapper;
    }

    buildMessageHTML(message) {
        // Build message HTML based on type
        // This would be a comprehensive function to build different message types
        return `<div class="message-bubble">
            <div class="message-content">
                <p>${message.message}</p>
            </div>
            <div class="message-meta">
                <span class="message-time">${new Date(message.timestamp).toLocaleTimeString()}</span>
            </div>
        </div>`;
    }

    // Initialize emoji picker and other features
    initializeEmojiPicker() {
        // Initialize emoji picker library if available
        // This would integrate with a library like emoji-js or similar
    }

    loadUserPreferences() {
        // Load user chat preferences
        fetch('/chat/api/user-preferences/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.applyUserPreferences(data.preferences);
                }
            })
            .catch(error => console.error('Error loading preferences:', error));
    }

    applyUserPreferences(preferences) {
        // Apply user preferences to the chat interface
        if (preferences.theme) {
            this.applyTheme(preferences.theme);
        }
        
        if (preferences.font_size) {
            this.applyFontSize(preferences.font_size);
        }
    }

    startMessagePolling() {
        // Start polling for new messages
        this.pollInterval = setInterval(() => {
            this.fetchNewMessages();
        }, 2000);
    }

    fetchNewMessages() {
        if (!this.currentRoomId) return;

        fetch(`/chat/api/get-new-messages/?room_id=${this.currentRoomId}&last_message_id=${this.lastMessageId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.messages.length > 0) {
                    data.messages.forEach(message => {
                        this.addMessageToUI(message);
                        this.lastMessageId = message.id;
                    });
                    this.scrollToBottom();
                }
            })
            .catch(error => console.error('Error fetching messages:', error));
    }

    sendTypingStatus(isTyping) {
        if (!this.currentRoomId) return;

        fetch('/chat/api/typing/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                room_id: this.currentRoomId,
                is_typing: isTyping
            })
        })
        .catch(error => console.error('Error sending typing status:', error));
    }

    handleVisibilityChange() {
        if (!document.hidden) {
            // Mark messages as read when user returns to tab
            this.markMessagesAsRead();
        }
    }

    markMessagesAsRead() {
        // Mark all visible messages as read
        const unreadMessages = document.querySelectorAll('.message-wrapper.received[data-unread="true"]');
        const messageIds = Array.from(unreadMessages).map(msg => msg.dataset.messageId);
        
        if (messageIds.length > 0) {
            fetch('/chat/api/mark-read/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    message_ids: messageIds
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    unreadMessages.forEach(msg => {
                        msg.removeAttribute('data-unread');
                    });
                }
            })
            .catch(error => console.error('Error marking messages as read:', error));
        }
    }
}

// Initialize enhanced chat when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.enhancedChat = new EnhancedChat();
});

// Global functions for template usage
function replyToMessage(messageId, messageText, senderName) {
    window.enhancedChat?.replyToMessage(messageId, messageText, senderName);
}

function showReactionPicker(messageId) {
    window.enhancedChat?.showReactionPicker(messageId);
}

function addReaction(emoji) {
    window.enhancedChat?.addReaction(emoji);
}

function selectFile(type) {
    window.enhancedChat?.selectFile(type);
}

function startVoiceRecording() {
    window.enhancedChat?.startVoiceRecording();
}

function stopRecording() {
    window.enhancedChat?.stopRecording();
}

function cancelRecording() {
    window.enhancedChat?.cancelRecording();
}

function toggleAttachmentMenu() {
    window.enhancedChat?.toggleAttachmentMenu();
}

function toggleChatSearch() {
    window.enhancedChat?.toggleChatSearch();
}

function searchMessages() {
    window.enhancedChat?.searchMessages();
}

function sendMessage() {
    window.enhancedChat?.sendMessage();
}

function cancelReply() {
    window.enhancedChat?.cancelReply();
}

function openImageModal(src) {
    document.getElementById('modal-image').src = src;
    new bootstrap.Modal(document.getElementById('imageModal')).show();
}
