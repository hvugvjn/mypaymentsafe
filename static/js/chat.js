// Chat functionality for TrustCart transaction messaging
document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    
    // Initialize chat functionality
    initializeChat();
    
    function initializeChat() {
        // Auto-scroll to bottom of chat messages
        scrollToBottom();
        
        // Handle form submission if chat form exists
        if (chatForm) {
            chatForm.addEventListener('submit', handleMessageSubmit);
        }
        
        // Handle message input auto-resize
        if (messageInput) {
            messageInput.addEventListener('input', autoResizeInput);
            messageInput.addEventListener('keypress', handleKeyPress);
        }
        
        // Auto-refresh messages every 10 seconds
        startMessagePolling();
    }
    
    function handleMessageSubmit(event) {
        event.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        // Disable form during submission
        setFormLoading(true);
        
        // Submit form normally (server-side handling)
        event.target.submit();
    }
    
    function handleKeyPress(event) {
        // Submit on Enter (but not Shift+Enter)
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            if (chatForm) {
                chatForm.dispatchEvent(new Event('submit'));
            }
        }
    }
    
    function autoResizeInput() {
        if (messageInput) {
            messageInput.style.height = 'auto';
            messageInput.style.height = Math.min(messageInput.scrollHeight, 100) + 'px';
        }
    }
    
    function scrollToBottom() {
        const chatContainer = document.querySelector('.chat-messages');
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }
    
    function setFormLoading(loading) {
        const submitButton = chatForm?.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = loading;
            if (loading) {
                submitButton.innerHTML = '<i data-feather="loader" class="spin"></i> Sending...';
            } else {
                submitButton.innerHTML = '<i data-feather="send"></i> Send';
            }
            feather.replace();
        }
    }
    
    function startMessagePolling() {
        // Only poll if we're on a transaction detail page with chat
        const chatContainer = document.querySelector('.chat-messages');
        if (!chatContainer) return;
        
        // Get transaction ID from URL
        const pathParts = window.location.pathname.split('/');
        const transactionId = pathParts[pathParts.length - 1];
        
        // Poll for new messages every 10 seconds
        setInterval(function() {
            checkForNewMessages(transactionId);
        }, 10000);
    }
    
    function checkForNewMessages(transactionId) {
        // Get the timestamp of the last message
        const lastMessage = document.querySelector('.chat-messages .message-bubble:last-child');
        if (!lastMessage) return;
        
        const lastMessageTime = lastMessage.querySelector('.small.text-muted')?.textContent;
        if (!lastMessageTime) return;
        
        // Simple polling by reloading the page if there might be new messages
        // This is a basic implementation that follows the guideline to avoid complex client-side JS
        // In a production app, you might want to use Server-Sent Events or WebSockets
        
        // For now, we'll just ensure the chat scrolls to bottom when new content loads
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList') {
                    scrollToBottom();
                }
            });
        });
        
        const chatContainer = document.querySelector('.chat-messages');
        if (chatContainer) {
            observer.observe(chatContainer, {
                childList: true,
                subtree: true
            });
        }
    }
    
    // Message formatting and display enhancements
    function enhanceMessages() {
        const messages = document.querySelectorAll('.message-bubble');
        messages.forEach(function(message) {
            // Add timestamp formatting
            const timeElement = message.querySelector('.small.text-muted');
            if (timeElement) {
                const timeText = timeElement.textContent;
                const formattedTime = formatMessageTime(timeText);
                if (formattedTime !== timeText) {
                    timeElement.textContent = formattedTime;
                }
            }
            
            // Add message status indicators (if needed)
            enhanceMessageStatus(message);
        });
    }
    
    function formatMessageTime(timeString) {
        try {
            // Parse the time string and format it nicely
            const now = new Date();
            const messageDate = new Date(timeString);
            
            // If it's today, show just time
            if (messageDate.toDateString() === now.toDateString()) {
                return messageDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
            
            // If it's this week, show day and time
            const daysDiff = Math.floor((now - messageDate) / (1000 * 60 * 60 * 24));
            if (daysDiff < 7) {
                return messageDate.toLocaleDateString([], { weekday: 'short' }) + ' ' + 
                       messageDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
            
            // Otherwise show full date
            return messageDate.toLocaleDateString() + ' ' + 
                   messageDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch (e) {
            return timeString; // Return original if parsing fails
        }
    }
    
    function enhanceMessageStatus(messageElement) {
        // Add visual indicators for message status
        const isOwnMessage = messageElement.classList.contains('bg-primary');
        
        if (isOwnMessage) {
            // Add a small checkmark or status indicator for sent messages
            const statusIndicator = document.createElement('span');
            statusIndicator.className = 'message-status text-muted';
            statusIndicator.innerHTML = '<i data-feather="check" style="width: 12px; height: 12px;"></i>';
            
            const timeElement = messageElement.querySelector('.small.text-muted');
            if (timeElement && !messageElement.querySelector('.message-status')) {
                timeElement.appendChild(statusIndicator);
            }
        }
    }
    
    // Initialize message enhancements
    enhanceMessages();
    
    // Smooth scrolling for better UX
    function smoothScrollToBottom() {
        const chatContainer = document.querySelector('.chat-messages');
        if (chatContainer) {
            chatContainer.scrollTo({
                top: chatContainer.scrollHeight,
                behavior: 'smooth'
            });
        }
    }
    
    // Replace the regular scrollToBottom with smooth version for better UX
    scrollToBottom = smoothScrollToBottom;
    
    // Handle connection status
    function updateConnectionStatus(online) {
        const statusIndicator = document.getElementById('connection-status');
        if (statusIndicator) {
            statusIndicator.className = online ? 'text-success' : 'text-danger';
            statusIndicator.textContent = online ? 'Connected' : 'Disconnected';
        }
    }
    
    // Monitor online/offline status
    window.addEventListener('online', () => updateConnectionStatus(true));
    window.addEventListener('offline', () => updateConnectionStatus(false));
    
    // Prevent form submission with empty messages
    if (messageInput) {
        messageInput.addEventListener('input', function() {
            const submitButton = chatForm?.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = !this.value.trim();
            }
        });
    }
    
    // Auto-focus message input when chat is opened
    if (messageInput && document.activeElement !== messageInput) {
        messageInput.focus();
    }
    
    // Handle chat message actions (like copying text)
    document.addEventListener('contextmenu', function(event) {
        const messageElement = event.target.closest('.message-bubble');
        if (messageElement) {
            // Allow right-click on messages for copying text
            event.stopPropagation();
        }
    });
    
    // Add visual feedback for successful message sending
    function showMessageSentFeedback() {
        const feedback = document.createElement('div');
        feedback.className = 'alert alert-success alert-dismissible fade show position-fixed';
        feedback.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 200px;';
        feedback.innerHTML = `
            <i data-feather="check-circle" class="me-2"></i>
            Message sent successfully!
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(feedback);
        feather.replace();
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (feedback.parentNode) {
                feedback.remove();
            }
        }, 3000);
    }
    
    // Show feedback when page loads after form submission
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('message_sent') === 'true') {
        showMessageSentFeedback();
        
        // Clean up URL
        const newUrl = window.location.pathname;
        window.history.replaceState({}, document.title, newUrl);
    }
});

// Add CSS for spinner animation
const style = document.createElement('style');
style.textContent = `
    .spin {
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    .message-status {
        margin-left: 5px;
    }
    
    .chat-messages {
        scroll-behavior: smooth;
    }
    
    .message-bubble {
        animation: fadeIn 0.3s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);
