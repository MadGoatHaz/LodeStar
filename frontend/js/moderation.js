class ModerationInterface {
    constructor() {
        this.flaggingEndpoint = '/api/flag';
        this.votingEndpoint = '/api/vote';
        this.userSession = this.generateUserSession();
    }

    generateUserSession() {
        // Generate anonymous user session
        let userId = localStorage.getItem('lodestar_user_id');
        if (!userId) {
            userId = 'anon_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('lodestar_user_id', userId);
        }
        return userId;
    }

    flagContent(ipfsHash, reason, description = '') {
        // Submit flag for content
        const flagData = {
            ipfs_hash: ipfsHash,
            reason: reason,
            description: description,
            user_id: this.userSession
        };

        return fetch(this.flaggingEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(flagData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                this.showFlagNotification('Content flagged successfully');
                return data;
            } else {
                this.showFlagNotification('Error: ' + data.error, 'error');
                return data;
            }
        })
        .catch(error => {
            console.error('Flagging error:', error);
            this.showFlagNotification('Network error occurred', 'error');
        });
    }

    showFlagNotification(message, type = 'success') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `flag-notification ${type}`;
        notification.textContent = message;
        
        // Style the notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '15px 20px',
            borderRadius: '4px',
            color: 'white',
            fontWeight: 'bold',
            zIndex: '10000',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
            backgroundColor: type === 'error' ? '#ef4444' : '#10b981',
            transform: 'translateX(100%)',
            transition: 'transform 0.3s ease'
        });
        
        // Add to document
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 10);
        
        // Remove after delay
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }

    addFlagButtonToContent(cardElement) {
        // Add flag button to content card
        const flagButton = document.createElement('button');
        flagButton.className = 'flag-button';
        flagButton.innerHTML = '🚩 Flag';
        flagButton.title = 'Flag this content for review';
        
        // Style the button
        Object.assign(flagButton.style, {
            position: 'absolute',
            top: '10px',
            right: '10px',
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid #ef4444',
            color: '#ef4444',
            borderRadius: '4px',
            padding: '5px 10px',
            cursor: 'pointer',
            fontSize: '12px',
            fontWeight: 'bold'
        });
        
        // Add hover effect
        flagButton.addEventListener('mouseenter', () => {
            flagButton.style.background = 'rgba(239, 68, 68, 0.2)';
        });
        
        flagButton.addEventListener('mouseleave', () => {
            flagButton.style.background = 'rgba(239, 68, 68, 0.1)';
        });
        
        // Add click handler
        flagButton.addEventListener('click', (e) => {
            e.stopPropagation();
            this.showFlagDialog(cardElement);
        });
        
        // Add to card
        cardElement.style.position = 'relative';
        cardElement.appendChild(flagButton);
    }

    showFlagDialog(cardElement) {
        // Get IPFS hash from card
        const ipfsHash = cardElement.getAttribute('data-ipfs-hash');
        
        // Create flag dialog
        const dialog = document.createElement('div');
        dialog.className = 'flag-dialog';
        
        // Style the dialog
        Object.assign(dialog.style, {
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            background: 'white',
            padding: '20px',
            borderRadius: '8px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
            zIndex: '10001',
            minWidth: '300px',
            maxWidth: '500px'
        });
        
        // Create backdrop
        const backdrop = document.createElement('div');
        Object.assign(backdrop.style, {
            position: 'fixed',
            top: '0',
            left: '0',
            width: '100%',
            height: '100%',
            background: 'rgba(0,0,0,0.5)',
            zIndex: '10000'
        });
        
        // Dialog content
        dialog.innerHTML = `
            <h3 style="margin-top: 0; color: #1f2937;">Flag Content for Review</h3>
            <p style="color: #6b7280; margin-bottom: 15px;">Why are you flagging this content?</p>
            
            <div style="margin-bottom: 15px;">
                <select id="flag-reason" style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;">
                    <option value="inappropriate">Inappropriate Content</option>
                    <option value="misleading">Misleading Information</option>
                    <option value="duplicate">Duplicate Content</option>
                    <option value="other">Other</option>
                </select>
            </div>
            
            <div style="margin-bottom: 20px;">
                <textarea id="flag-description" placeholder="Additional details (optional)" 
                    style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px; height: 80px;"></textarea>
            </div>
            
            <div style="display: flex; justify-content: flex-end; gap: 10px;">
                <button id="cancel-flag" style="padding: 8px 16px; border: 1px solid #d1d5db; border-radius: 4px; background: white; cursor: pointer;">
                    Cancel
                </button>
                <button id="submit-flag" style="padding: 8px 16px; border: 1px solid #ef4444; border-radius: 4px; background: #ef4444; color: white; cursor: pointer;">
                    Submit Flag
                </button>
            </div>
        `;
        
        // Add to document
        document.body.appendChild(backdrop);
        document.body.appendChild(dialog);
        
        // Focus the reason select
        dialog.querySelector('#flag-reason').focus();
        
        // Add event handlers
        dialog.querySelector('#cancel-flag').addEventListener('click', () => {
            backdrop.remove();
            dialog.remove();
        });
        
        backdrop.addEventListener('click', () => {
            backdrop.remove();
            dialog.remove();
        });
        
        dialog.querySelector('#submit-flag').addEventListener('click', () => {
            const reason = dialog.querySelector('#flag-reason').value;
            const description = dialog.querySelector('#flag-description').value;
            
            this.flagContent(ipfsHash, reason, description).then(() => {
                backdrop.remove();
                dialog.remove();
            });
        });
        
        // Close on Escape key
        const closeHandler = (e) => {
            if (e.key === 'Escape') {
                backdrop.remove();
                dialog.remove();
                document.removeEventListener('keydown', closeHandler);
            }
        };
        document.addEventListener('keydown', closeHandler);
    }

    initializeFlagButtons() {
        // Add flag buttons to existing content
        const contentCards = document.querySelectorAll('.truth-card');
        contentCards.forEach(card => {
            this.addFlagButtonToContent(card);
        });
        
        // Listen for new content added by real-time updates
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.classList && node.classList.contains('truth-card')) {
                        this.addFlagButtonToContent(node);
                    }
                });
            });
        });
        
        // Observe the content container
        const contentContainer = document.getElementById('truth-feed');
        if (contentContainer) {
            observer.observe(contentContainer, { childList: true, subtree: true });
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.moderationInterface = new ModerationInterface();
    window.moderationInterface.initializeFlagButtons();
});