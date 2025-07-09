// Real-time notifications using Server-Sent Events
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is authenticated
    const notificationDropdown = document.getElementById('notificationDropdown');
    if (!notificationDropdown) return;

    const notificationCount = document.querySelector('.notification-count');
    const notificationList = document.querySelector('.notification-list');
    
    // Initialize EventSource for real-time notifications
    if (typeof(EventSource) !== "undefined") {
        const eventSource = new EventSource("/notifications/stream");
        
        eventSource.onmessage = function(event) {
            try {
                const notification = JSON.parse(event.data);
                handleNewNotification(notification);
            } catch (error) {
                console.error('Error parsing notification:', error);
            }
        };
        
        eventSource.onerror = function(event) {
            console.log("Notification stream error:", event);
            // Reconnect after 5 seconds
            setTimeout(() => {
                // Disabled auto-reload to prevent unwanted page refreshes
                // if (eventSource.readyState === EventSource.CLOSED) {
                //     location.reload(); // Reload page to restart connection
                // }
            }, 5000);
        };
    }
    
    function handleNewNotification(notification) {
        // Update notification count
        updateNotificationCount();
        
        // Add to dropdown list
        addNotificationToDropdown(notification);
        
        // Show toast notification
        showToastNotification(notification);
        
        // Play notification sound (optional)
        playNotificationSound();
    }
    
    function updateNotificationCount() {
        // Get current count and increment
        let count = parseInt(notificationCount.textContent) || 0;
        count++;
        
        notificationCount.textContent = count;
        notificationCount.style.display = 'flex';
        
        // Add pulsing animation
        notificationCount.classList.add('animate-pulse');
        setTimeout(() => {
            notificationCount.classList.remove('animate-pulse');
        }, 1000);
    }
    
    function addNotificationToDropdown(notification) {
        // Remove "no notifications" message if present
        const noNotifications = notificationList.querySelector('.dropdown-item-text');
        if (noNotifications && noNotifications.textContent.includes('No new notifications')) {
            noNotifications.remove();
        }
        
        // Create notification item
        const notificationItem = document.createElement('li');
        notificationItem.innerHTML = `
            <div class="dropdown-item notification-item" data-notification-id="${notification.id}">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <strong class="text-primary">${notification.title}</strong>
                        <p class="mb-1 small">${notification.message}</p>
                        <small class="text-muted">${formatDate(notification.created_at)}</small>
                    </div>
                    <button class="btn btn-sm btn-outline-secondary ms-2 mark-read-btn" onclick="markNotificationRead(${notification.id})">
                        <i data-feather="x" style="width: 12px; height: 12px;"></i>
                    </button>
                </div>
            </div>
        `;
        
        // Insert at the beginning
        notificationList.insertBefore(notificationItem, notificationList.firstChild);
        
        // Replace feather icons
        feather.replace();
        
        // Limit to 10 notifications in dropdown
        const notifications = notificationList.querySelectorAll('.notification-item');
        if (notifications.length > 10) {
            notifications[notifications.length - 1].remove();
        }
    }
    
    function showToastNotification(notification) {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast
        const toastId = 'toast-' + Date.now();
        const toastElement = document.createElement('div');
        toastElement.id = toastId;
        toastElement.className = 'toast show';
        toastElement.setAttribute('role', 'alert');
        toastElement.innerHTML = `
            <div class="toast-header bg-primary text-white">
                <i data-feather="bell" class="me-2" style="width: 16px; height: 16px;"></i>
                <strong class="me-auto">${notification.title}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${notification.message}
            </div>
        `;
        
        toastContainer.appendChild(toastElement);
        feather.replace();
        
        // Initialize Bootstrap toast
        const toast = new bootstrap.Toast(toastElement, {
            delay: 5000,
            autohide: true
        });
        
        toast.show();
        
        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', function() {
            toastElement.remove();
        });
    }
    
    function playNotificationSound() {
        // Create a subtle notification sound
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.1);
            
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.2);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.2);
        } catch (error) {
            // Silently fail if audio context is not supported
            console.log('Audio notification not supported');
        }
    }
    
    function formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
        return date.toLocaleDateString();
    }
});

// Global function to mark notification as read
function markNotificationRead(notificationId) {
    fetch(`/notifications/mark-read/${notificationId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remove notification from dropdown
            const notificationElement = document.querySelector(`[data-notification-id="${notificationId}"]`);
            if (notificationElement) {
                notificationElement.closest('li').remove();
            }
            
            // Update count
            const notificationCount = document.querySelector('.notification-count');
            let count = parseInt(notificationCount.textContent) || 0;
            count = Math.max(0, count - 1);
            
            if (count === 0) {
                notificationCount.style.display = 'none';
                
                // Add "no notifications" message if dropdown is empty
                const notificationList = document.querySelector('.notification-list');
                if (notificationList.children.length === 0) {
                    notificationList.innerHTML = '<li><span class="dropdown-item-text text-muted">No new notifications</span></li>';
                }
            } else {
                notificationCount.textContent = count;
            }
        }
    })
    .catch(error => {
        console.error('Error marking notification as read:', error);
    });
}

// Add CSS for pulse animation
const style = document.createElement('style');
style.textContent = `
    .animate-pulse {
        animation: pulse 1s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
`;
document.head.appendChild(style);