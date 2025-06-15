/**
 * Chat Interface Enhancements
 * Additional features for better user experience
 */

class ChatEnhancements {
    constructor() {
        this.init();
    }

    init() {
        this.addMessageAnimations();
        this.addSoundToggle();
        this.addKeyboardShortcuts();
        this.addMessageTimestamps();
        this.addUserAvatars();
    }

    addMessageAnimations() {
        // Add stagger animation for existing messages
        const messages = document.querySelectorAll('.message-item');
        messages.forEach((message, index) => {
            message.style.animationDelay = `${index * 0.1}s`;
        });
    }

    addSoundToggle() {
        // Add sound toggle button
        const chatHeader = document.querySelector('.card-header');
        if (chatHeader && !document.getElementById('sound-toggle')) {
            const soundToggle = document.createElement('button');
            soundToggle.id = 'sound-toggle';
            soundToggle.className = 'btn btn-sm btn-outline-light ml-2';
            soundToggle.innerHTML = '<i class="fas fa-volume-up"></i>';
            soundToggle.title = 'Toggle notification sounds';
            
            soundToggle.addEventListener('click', () => {
                const isEnabled = localStorage.getItem('chatSoundsEnabled') !== 'false';
                localStorage.setItem('chatSoundsEnabled', !isEnabled);
                soundToggle.innerHTML = isEnabled ? 
                    '<i class="fas fa-volume-mute"></i>' : 
                    '<i class="fas fa-volume-up"></i>';
                soundToggle.title = isEnabled ? 
                    'Enable notification sounds' : 
                    'Disable notification sounds';
            });
            
            chatHeader.appendChild(soundToggle);
        }
    }

    addKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Enter to send message
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                const messageForm = document.getElementById('quick-message-form');
                if (messageForm) {
                    messageForm.dispatchEvent(new Event('submit'));
                }
            }
            
            // Escape to clear message input
            if (e.key === 'Escape') {
                const messageInput = document.getElementById('message-input');
                if (messageInput && messageInput === document.activeElement) {
                    messageInput.value = '';
                    messageInput.blur();
                }
            }
        });
    }

    addMessageTimestamps() {
        // Add relative timestamps that update
        setInterval(() => {
            document.querySelectorAll('[data-timestamp]').forEach(element => {
                const timestamp = element.getAttribute('data-timestamp');
                if (timestamp) {
                    element.textContent = this.getRelativeTime(new Date(timestamp));
                }
            });
        }, 60000); // Update every minute
    }

    addUserAvatars() {
        // Add colored avatars for users without profile pictures
        document.querySelectorAll('.message-item').forEach(message => {
            const senderName = message.querySelector('.font-weight-bold');
            if (senderName && !message.querySelector('.user-avatar')) {
                const avatar = document.createElement('div');
                avatar.className = 'user-avatar';
                avatar.style.cssText = `
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    background: ${this.getAvatarColor(senderName.textContent)};
                    color: white;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    font-size: 14px;
                    margin-right: 10px;
                    flex-shrink: 0;
                `;
                avatar.textContent = senderName.textContent.charAt(0).toUpperCase();
                
                const messageContent = message.querySelector('.d-inline-block');
                if (messageContent && !message.classList.contains('text-right')) {
                    const wrapper = document.createElement('div');
                    wrapper.className = 'd-flex align-items-start';
                    messageContent.parentNode.insertBefore(wrapper, messageContent);
                    wrapper.appendChild(avatar);
                    wrapper.appendChild(messageContent);
                }
            }
        });
    }

    getAvatarColor(name) {
        const colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'
        ];
        let hash = 0;
        for (let i = 0; i < name.length; i++) {
            hash = name.charCodeAt(i) + ((hash << 5) - hash);
        }
        return colors[Math.abs(hash) % colors.length];
    }

    getRelativeTime(date) {
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) return 'just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
        
        return date.toLocaleDateString();
    }

    // Message effects
    addMessageEffect(messageElement, effect = 'bounce') {
        switch (effect) {
            case 'bounce':
                messageElement.style.animation = 'bounce 0.6s ease';
                break;
            case 'shake':
                messageElement.style.animation = 'shake 0.5s ease';
                break;
            case 'glow':
                messageElement.style.boxShadow = '0 0 20px rgba(0, 123, 255, 0.6)';
                setTimeout(() => {
                    messageElement.style.boxShadow = '';
                }, 2000);
                break;
        }
    }

    // Emoji reactions (placeholder for future implementation)
    addEmojiReactions() {
        document.querySelectorAll('.message-bubble').forEach(bubble => {
            if (!bubble.querySelector('.emoji-reactions')) {
                bubble.addEventListener('dblclick', (e) => {
                    // Add heart reaction on double-click
                    this.addReaction(bubble, '❤️');
                });
            }
        });
    }

    addReaction(messageElement, emoji) {
        let reactionsContainer = messageElement.querySelector('.emoji-reactions');
        if (!reactionsContainer) {
            reactionsContainer = document.createElement('div');
            reactionsContainer.className = 'emoji-reactions mt-1';
            messageElement.appendChild(reactionsContainer);
        }
        
        const reaction = document.createElement('span');
        reaction.className = 'emoji-reaction';
        reaction.textContent = emoji;
        reaction.style.cssText = `
            display: inline-block;
            padding: 2px 6px;
            background: rgba(0, 0, 0, 0.1);
            border-radius: 12px;
            margin-right: 4px;
            font-size: 12px;
            animation: bounceIn 0.3s ease;
        `;
        
        reactionsContainer.appendChild(reaction);
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes bounce {
        0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
        40% { transform: translateY(-10px); }
        60% { transform: translateY(-5px); }
    }
    
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
        20%, 40%, 60%, 80% { transform: translateX(5px); }
    }
    
    @keyframes bounceIn {
        0% { transform: scale(0); opacity: 0; }
        50% { transform: scale(1.2); opacity: 1; }
        100% { transform: scale(1); opacity: 1; }
    }
    
    .user-avatar {
        transition: transform 0.2s ease;
    }
    
    .user-avatar:hover {
        transform: scale(1.1);
    }
    
    .emoji-reaction {
        cursor: pointer;
        transition: transform 0.2s ease;
    }
    
    .emoji-reaction:hover {
        transform: scale(1.2);
    }
`;
document.head.appendChild(style);

// Initialize enhancements when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.chatEnhancements = new ChatEnhancements();
});

// Export for use in other scripts
window.ChatEnhancements = ChatEnhancements;
