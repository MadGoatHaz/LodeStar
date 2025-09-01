class MobileInterface {
    constructor() {
        this.isMobile = this.detectMobile();
        this.init();
    }

    detectMobile() {
        // Simple mobile detection
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    init() {
        if (this.isMobile) {
            this.setupMobileOptimizations();
            this.setupTouchGestures();
            this.setupOfflineSupport();
        }
    }

    setupMobileOptimizations() {
        // Add mobile-specific classes to body
        document.body.classList.add('mobile-device');
        
        // Optimize viewport
        let viewport = document.querySelector('meta[name="viewport"]');
        if (!viewport) {
            viewport = document.createElement('meta');
            viewport.name = 'viewport';
            document.head.appendChild(viewport);
        }
        viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes';
        
        // Add mobile CSS
        this.addMobileCSS();
    }

    addMobileCSS() {
        // Add mobile-specific styles
        const style = document.createElement('style');
        style.textContent = `
            /* Enhanced mobile styles */
            .mobile-device .truth-card {
                transition: none; /* Disable transitions for better performance */
            }
            
            .mobile-device .truth-card:hover {
                transform: none; /* Disable hover effects on mobile */
                box-shadow: var(--shadow);
            }
            
            /* Larger touch targets */
            .mobile-device .filter-btn,
            .mobile-device .flag-button {
                min-height: 48px;
                min-width: 48px;
            }
            
            /* Improved scrolling */
            .mobile-device .truth-feed {
                -webkit-overflow-scrolling: touch;
            }
            
            /* Prevent zoom on input focus */
            .mobile-device input:focus,
            .mobile-device textarea:focus,
            .mobile-device select:focus {
                font-size: 16px; /* Prevent iOS zoom */
            }
        `;
        document.head.appendChild(style);
    }

    setupTouchGestures() {
        // Add touch event listeners for enhanced mobile interaction
        let touchStartX = 0;
        let touchEndX = 0;
        
        // Add touch start listener
        document.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
        }, false);
        
        // Add touch end listener
        document.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            this.handleSwipeGesture();
        }, false);
        
        // Prevent zoom on double tap
        let lastTouchEnd = 0;
        document.addEventListener('touchend', (event) => {
            const now = (new Date()).getTime();
            if (now - lastTouchEnd <= 300) {
                event.preventDefault();
            }
            lastTouchEnd = now;
        }, false);
    }

    handleSwipeGesture() {
        const swipeThreshold = 50; // Minimum swipe distance
        
        if (touchStartX - touchEndX > swipeThreshold) {
            // Swipe left - next action
            this.swipeLeft();
        } else if (touchEndX - touchStartX > swipeThreshold) {
            // Swipe right - previous action
            this.swipeRight();
        }
    }

    swipeLeft() {
        // Handle swipe left gesture
        console.log('Swipe left detected');
        // TODO: Implement swipe navigation or actions
    }

    swipeRight() {
        // Handle swipe right gesture
        console.log('Swipe right detected');
        // TODO: Implement swipe navigation or actions
    }

    setupOfflineSupport() {
        // Register service worker for offline support
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js')
                    .then((registration) => {
                        console.log('ServiceWorker registration successful with scope: ', registration.scope);
                    })
                    .catch((error) => {
                        console.log('ServiceWorker registration failed: ', error);
                    });
            });
        }
        
        // Handle offline/online events
        window.addEventListener('offline', () => {
            this.showOfflineNotification();
        });
        
        window.addEventListener('online', () => {
            this.showOnlineNotification();
        });
    }

    showOfflineNotification() {
        // Show offline notification
        const notification = document.createElement('div');
        notification.className = 'offline-notification';
        notification.textContent = 'You are currently offline. Content may not be up to date.';
        
        // Style the notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '0',
            left: '0',
            width: '100%',
            background: '#f59e0b',
            color: 'white',
            padding: '10px',
            textAlign: 'center',
            zIndex: '9999',
            fontSize: '0.9rem'
        });
        
        document.body.appendChild(notification);
        
        // Remove after delay
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    showOnlineNotification() {
        // Show online notification
        const notification = document.createElement('div');
        notification.className = 'online-notification';
        notification.textContent = 'You are now online.';
        
        // Style the notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '0',
            left: '0',
            width: '100%',
            background: '#10b981',
            color: 'white',
            padding: '10px',
            textAlign: 'center',
            zIndex: '9999',
            fontSize: '0.9rem'
        });
        
        document.body.appendChild(notification);
        
        // Remove after delay
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    setupPullToRefresh() {
        // Implement pull-to-refresh functionality
        let startY = 0;
        let currentY = 0;
        const refreshThreshold = 100;
        
        const content = document.querySelector('.truth-feed');
        if (!content) return;
        
        content.addEventListener('touchstart', (e) => {
            startY = e.touches[0].pageY;
        });
        
        content.addEventListener('touchmove', (e) => {
            currentY = e.touches[0].pageY;
            const diff = currentY - startY;
            
            if (diff > 0 && window.scrollY === 0) {
                // Pulling down at top of page
                content.style.transform = `translateY(${Math.min(diff / 2, refreshThreshold)}px)`;
            }
        });
        
        content.addEventListener('touchend', (e) => {
            const diff = currentY - startY;
            
            if (diff > refreshThreshold) {
                this.refreshContent();
            }
            
            // Reset position
            content.style.transform = 'translateY(0)';
        });
    }

    refreshContent() {
        // Refresh content function
        console.log('Refreshing content...');
        
        // Show refresh indicator
        const refreshIndicator = document.createElement('div');
        refreshIndicator.className = 'refresh-indicator';
        refreshIndicator.textContent = 'Refreshing...';
        
        Object.assign(refreshIndicator.style, {
            position: 'fixed',
            top: '10px',
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(37, 99, 235, 0.9)',
            color: 'white',
            padding: '8px 16px',
            borderRadius: '20px',
            zIndex: '10000',
            fontSize: '0.9rem'
        });
        
        document.body.appendChild(refreshIndicator);
        
        // Simulate refresh
        setTimeout(() => {
            refreshIndicator.remove();
            // TODO: Actually refresh content
        }, 1000);
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.mobileInterface = new MobileInterface();
});