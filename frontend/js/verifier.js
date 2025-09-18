class FrontendVerifier {
    constructor() {
        this.verificationQueue = [];
        this.isVerifying = false;
        this.trustedKeys = [];
        this.loadTrustedKeys();
    }

    async loadTrustedKeys() {
        try {
            const response = await fetch('/api/trusted_keys');
            const data = await response.json();
            this.trustedKeys = data.keys;
            console.log(`Loaded ${this.trustedKeys.length} trusted keys`);
        } catch (error) {
            console.error('Error loading trusted keys:', error);
        }
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
                // First, try client-side verification if we have trusted keys
                if (this.trustedKeys.length > 0) {
                    const data = await this.fetchIpfsData(ipfsHash);
                    if (data && data.signature) {
                        // In a real implementation, we would use WebCrypto API here
                        // For now, we'll use the placeholder implementation
                        const isVerified = await this.verifySignatureClientSide(data);
                        if (isVerified) {
                            this.updateVerificationStatus(ipfsHash, 'verified');
                            continue; // Skip backend verification if client-side succeeded
                        }
                    }
                }
                
                // Fall back to backend verification
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

    async fetchIpfsData(ipfsHash) {
        try {
            // Fetch data from IPFS via backend API
            const response = await fetch(`/api/verify`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ ipfs_hash: ipfsHash })
            });
            
            const result = await response.json();
            if (result.verified === undefined) {
                // This is the raw data response
                return { ipfs_hash: ipfsHash, signature: result.signature, data: result.data };
            }
            return null;
        } catch (error) {
            console.error('Error fetching IPFS data:', error);
            return null;
        }
    }

    async verifySignatureClientSide(data) {
        try {
            // Extract signature and data without signature
            const signature = data.signature;
            const dataCopy = { ...data };
            delete dataCopy.signature;
            
            // Check if we have trusted keys
            if (!this.trustedKeys || this.trustedKeys.length === 0) {
                console.log('No trusted keys available for verification');
                return false;
            }
            
            // For each trusted key, try to verify the signature
            for (const publicKey of this.trustedKeys) {
                const isValid = await verifySignatureWithWebCrypto(dataCopy, signature, publicKey);
                if (isValid) {
                    return true;
                }
            }
            
            return false;
        } catch (error) {
            console.error('Client-side signature verification failed:', error);
            return false;
        }
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

// Helper function to sort object keys
function sortKeys(key, value) {
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
        return Object.keys(value).sort().reduce((result, sortedKey) => {
            result[sortedKey] = value[sortedKey];
            return result;
        }, {});
    }
    return value;
}

// WebCrypto verification implementation
async function verifySignatureWithWebCrypto(data, signatureB64, publicKeyPem) {
    try {
        // Remove signature from data for verification
        const dataCopy = { ...data };
        delete dataCopy.signature;
        
        // Convert data to JSON string for verification
        const json_data = new TextEncoder().encode(JSON.stringify(dataCopy, sortKeys));
        
        // Decode signature
        const signature = base64ToUint8Array(signatureB64);
        
        // Load public key
        const publicKey = await crypto.subtle.importKey(
            'spki',
            pemToUint8Array(publicKeyPem),
            {
                name: 'RSASSA-PKCS1-v1_5',
                hash: { name: 'SHA-256' }
            },
            false,
            ['verify']
        );
        
        // Verify signature
        const isValid = await crypto.subtle.verify(
            {
                name: 'RSASSA-PKCS1-v1_5'
            },
            publicKey,
            signature,
            json_data
        );
        
        return isValid;
    } catch (error) {
        console.error('WebCrypto signature verification failed:', error);
        return false;
    }
}

// Helper function to convert Base64 string to Uint8Array
function base64ToUint8Array(base64) {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes;
}

// Helper function to convert PEM to Uint8Array
function pemToUint8Array(pem) {
    // Remove header, footer, and newlines
    const pemHeader = "-----BEGIN PUBLIC KEY-----";
    const pemFooter = "-----END PUBLIC KEY-----";
    const pemContents = pem.substring(pemHeader.length, pem.length - pemFooter.length).replace(/\n/g, '');
    
    // Convert from Base64 to Uint8Array
    return base64ToUint8Array(pemContents);
}

// Initialize verifier when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.frontendVerifier = new FrontendVerifier();
    
    // Verify all content on page load
    window.frontendVerifier.verifyAllDisplayedContent();
});