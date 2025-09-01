class RealTimeUpdater {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.contentContainer = null;
        this.notificationSound = null;
        this.preferences = {
            enableNotifications: true,
            notificationSound: true,
            autoScroll: true
        };
    }

    init() {
        // Initialize WebSocket connection
        this.connect();
        
        // Get content container
        this.contentContainer = document.getElementById('truth-feed');
        
        // Set up preference controls
        this.setupPreferenceControls();
        
        // Set up notification sound
        this.setupNotificationSound();
    }

    connect() {
        // Connect to WebSocket server
        this.socket = io('http://localhost:5001');
        
        // Set up event handlers
        this.socket.on('connect', () => {
            console.log('Connected to real-time server');
            this.isConnected = true;
            this.updateConnectionStatus('connected');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from real-time server');
            this.isConnected = false;
            this.updateConnectionStatus('disconnected');
        });
        
        this.socket.on('content_update', (data) => {
            this.handleContentUpdate(data);
        });
        
        this.socket.on('status', (data) => {
            console.log('Server status:', data.msg);
        });
        
        // Handle connection errors
        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            this.updateConnectionStatus('disconnected');
        });
    }

    handleContentUpdate(data) {
        // Remove loading indicator if present
        const loadingIndicator = this.contentContainer.querySelector('div[style*="text-align: center"]');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
        
        // Create new content card
        const newCard = this.createContentCard(data);
        
        // Add to top of content feed
        if (this.contentContainer.firstChild) {
            this.contentContainer.insertBefore(newCard, this.contentContainer.firstChild);
        } else {
            this.contentContainer.appendChild(newCard);
        }
        
        // Show notification if enabled
        if (this.preferences.enableNotifications) {
            this.showNotification(data);
        }
        
        // Play sound if enabled
        if (this.preferences.notificationSound) {
            this.playNotificationSound();
        }
        
        // Scroll to top if auto-scroll enabled
        if (this.preferences.autoScroll) {
            newCard.scrollIntoView({ behavior: 'smooth' });
        }
    }

    createContentCard(data) {
        const card = document.createElement('div');
        card.className = 'truth-card';
        card.setAttribute('data-ipfs-hash', data.ipfs_hash);
        
        // Determine status class based on content type
        let statusClass = 'status-verified';
        let statusText = 'Verified Truth';
        
        if (data.type === 'contradicted' || data.type === 'politifact' || data.type === 'groundnews') {
            statusClass = 'status-contradicted';
            statusText = 'Fact Check';
        }
        
        // Format content based on type
        let content = data.summary || data.content || '';
        if (data.type === 'politifact') {
            content = `${data.claim || ''} - Rating: ${data.rating || 'Unknown'}`;
        } else if (data.type === 'tweet') {
            content = data.text || '';
        }
        
        card.innerHTML = `
            <div class="truth-header">
                <h2 class="truth-title">${this.escapeHtml(data.title || 'Untitled')}</h2>
                <span class="truth-status ${statusClass}">${statusText}</span>
            </div>
            <div class="truth-content">
                <p>${this.escapeHtml(content)}</p>
            </div>
            <div class="action-section">
                <span class="action-label">Source:</span>
                <span class="action-content">${this.escapeHtml(data.source || 'Unknown')}</span>
            </div>
            <div class="source">IPFS: ${data.ipfs_hash} | ${new Date(data.timestamp * 1000).toLocaleString()}</div>
            <div class="methodology">
                Real-time verified content from ${data.type || 'unknown'} source
            </div>
        `;
        
        return card;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(data) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'realtime-notification';
        notification.innerHTML = `
            <div class="notification-content">
                <strong>New Content:</strong> ${this.escapeHtml(data.title || 'Untitled')}
            </div>
        `;
        
        // Add to document
        document.body.appendChild(notification);
        
        // Remove after delay
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    playNotificationSound() {
        if (this.notificationSound) {
            this.notificationSound.play().catch(e => {
                console.log('Sound playback failed:', e);
            });
        }
    }

    setupNotificationSound() {
        // Try to load notification sound
        try {
            this.notificationSound = new Audio('/sounds/notification.mp3');
        } catch (e) {
            console.log('Could not load notification sound');
        }
    }

    setupPreferenceControls() {
        // Set up preference controls if they exist in the UI
        const notificationToggle = document.getElementById('notification-toggle');
        const soundToggle = document.getElementById('sound-toggle');
        const autoscrollToggle = document.getElementById('autoscroll-toggle');
        
        if (notificationToggle) {
            notificationToggle.addEventListener('change', (e) => {
                this.preferences.enableNotifications = e.target.checked;
            });
        }
        
        if (soundToggle) {
            soundToggle.addEventListener('change', (e) => {
                this.preferences.notificationSound = e.target.checked;
            });
        }
        
        if (autoscrollToggle) {
            autoscrollToggle.addEventListener('change', (e) => {
                this.preferences.autoScroll = e.target.checked;
            });
        }
    }

    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = status === 'connected' ? 'Connected' : 'Disconnected';
            statusElement.className = `connection-status ${status}`;
        }
    }

    subscribeToPreferences(preferences) {
        // Send preferences to server
        if (this.socket) {
            this.socket.emit('subscribe_preferences', preferences);
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.realTimeUpdater = new RealTimeUpdater();
    window.realTimeUpdater.init();
});