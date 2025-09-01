class FrontendVerifier {
    constructor() {
        this.verificationQueue = [];
        this.isVerifying = false;
    }

    async verifyData(ipfsHash) {
        try {
            // Add to verification queue
            this.verificationQueue.push(ipfsHash);
            
            // Start verification process if not already running
            if (!this.isVerifying) {
                this.isVerifying = true;
                await this.processVerificationQueue();
            }
            
            return true;
        } catch (error) {
            console.error('Error adding to verification queue:', error);
            return false;
        }
    }

    async processVerificationQueue() {
        while (this.verificationQueue.length > 0) {
            const ipfsHash = this.verificationQueue.shift();
            
            try {
                // Call backend verification endpoint
                const response = await fetch('/api/verify', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ ipfs_hash: ipfsHash })
                });
                
                const result = await response.json();
                
                if (result.verified) {
                    // Update UI to show verified status
                    this.updateVerificationStatus(ipfsHash, 'verified');
                } else {
                    // Update UI to show unverified status
                    this.updateVerificationStatus(ipfsHash, 'unverified');
                }
            } catch (error) {
                console.error('Verification failed for', ipfsHash, error);
                this.updateVerificationStatus(ipfsHash, 'error');
            }
        }
        
        this.isVerifying = false;
    }

    updateVerificationStatus(ipfsHash, status) {
        // Update the UI elements for this IPFS hash
        const elements = document.querySelectorAll(`[data-ipfs-hash="${ipfsHash}"]`);
        elements.forEach(element => {
            element.classList.remove('status-pending', 'status-verified', 'status-unverified', 'status-error');
            element.classList.add(`status-${status}`);
            
            // Update status text
            const statusElement = element.querySelector('.verification-status');
            if (statusElement) {
                statusElement.textContent = this.getStatusText(status);
            }
        });
    }

    getStatusText(status) {
        switch (status) {
            case 'verified': return 'Verified';
            case 'unverified': return 'Unverified';
            case 'error': return 'Verification Error';
            default: return 'Pending Verification';
        }
    }

    async verifyAllDisplayedContent() {
        // Find all IPFS hashes currently displayed
        const contentElements = document.querySelectorAll('[data-ipfs-hash]');
        const hashes = Array.from(contentElements).map(el => el.getAttribute('data-ipfs-hash'));
        
        // Verify each hash
        for (const hash of hashes) {
            await this.verifyData(hash);
        }
    }
}

// Initialize verifier when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.frontendVerifier = new FrontendVerifier();
    
    // Verify all content on page load
    window.frontendVerifier.verifyAllDisplayedContent();
});