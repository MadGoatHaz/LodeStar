# LodeStar Development Plan (Comprehensive Update)

## Project Overview
LodeStar is a decentralized platform designed to combat misinformation by aggregating, verifying, and presenting political statements alongside their real-world outcomes. The system uses IPFS for permanent storage, cryptographic signing for authenticity, and a volunteer-powered crawler network to collect data from multiple sources.

## System Architecture

### Core Components
1. **Crawlers** (`src/crawler/`)
   - Distributed volunteer nodes that collect data from YouTube, Twitter, Brave Search, PolitiFact, and Ground News
   - Data is cryptographically signed using a private key stored locally on each node
   - All data is stored on IPFS with signatures for verification

2. **Processor** (`src/processor/`)
   - Transcribes audio/video content to text
   - Extracts metadata and stores transcripts on IPFS
   - Works with crawler output to create structured, searchable content

3. **API Layer** (`src/api/`)
   - Flask-based REST API with WebSocket integration
   - Endpoints for:
     - Data verification (`/api/verify`)
     - Trusted key management (`/api/add_trusted_key`)
     - Flag submission and moderation (`/api/flag`, `/api/moderation/queue`)
     - Search functionality (`/api/search`)
     - Historical data queries (`/api/historical`)
     - Volunteer dashboard (`/api/volunteer_dashboard`)

4. **Verification System** (`src/utils/verifier.py`)
   - Validates cryptographic signatures on IPFS data
   - Manages trusted public keys
   - Ensures data authenticity before broadcasting

5. **Flagging & Moderation** (`src/utils/flagging_service.py`)
   - Manages user-submitted content flags
   - Provides moderation queue and status update capabilities
   - Supports anonymous reporting

6. **Frontend** (`frontend/`)
   - Static HTML/CSS/JS interface
   - Three main interfaces:
     - `index.html`: Main public interface
     - `volunteer_dashboard.html`: Volunteer contribution interface
     - `admin_dashboard.html`: Moderator interface for flag management

## Technology Stack
- **Backend**: Python 3.x, Flask, Flask-SocketIO
- **IPFS**: Kubo (go-ipfs) for decentralized storage
- **Cryptography**: cryptography library for ECDSA/RSA signing
- **Web Scraping**: BeautifulSoup, requests
- **Media Processing**: youtube_dl, pydub, SpeechRecognition
- **APIs**: Twitter API, Brave Search API
- **Frontend**: Vanilla HTML/CSS/JS (no framework)
- **Dependencies**: Listed in `requirements.txt`

## Installation Requirements
1. **Python 3.8+**
2. **IPFS Desktop** or **Kubo CLI** installed and running
3. **Environment variables** for API keys:
   - `TWITTER_API_KEY`
   - `TWITTER_API_SECRET`
   - `TWITTER_ACCESS_TOKEN`
   - `TWITTER_ACCESS_TOKEN_SECRET`
   - `BRAVE_API_KEY`
4. **Crawler private key** (`crawler.key`) - generated per volunteer node

## Implementation Plan: Browser-Based Signature Verification (Phase 1)

### Objective
Enable browsers to independently verify the cryptographic signatures on IPFS content without relying on the backend server, enhancing decentralization and resilience against censorship.

### Step-by-Step Implementation Plan

#### Step 1: Setup Trusted Keys Infrastructure
1. **Create trusted_keys.json**:
   - File location: `src/utils/trusted_keys.json`
   - Content: `{"keys": []}`
   - Purpose: Store public keys of trusted volunteer crawlers

2. **Verify backend integration**:
   - The backend API (`src/api/api.py`) already exposes `/api/status` endpoint
   - This endpoint returns `trusted_keys_count` which frontend will use to determine if verification is possible

#### Step 2: Enhance Frontend Verifier.js
1. **Update constructor**:
   ```javascript
   constructor() {
       this.verificationQueue = [];
       this.isVerifying = false;
       this.trustedKeys = [];
       this.loadTrustedKeys(); // Added to initialize key loading
   }
   ```

2. **Implement loadTrustedKeys()**:
   ```javascript
   async loadTrustedKeys() {
       try {
           // Fetch trusted keys count from backend
           const response = await fetch('/api/status');
           const status = await response.json();
           
           if (status.trusted_keys_count > 0) {
               console.log(`Loaded ${status.trusted_keys_count} trusted keys`);
               // Store count as a placeholder (actual keys will be fetched later)
               this.trustedKeys = new Array(status.trusted_keys_count).fill(true);
           }
       } catch (error) {
           console.error('Error loading trusted keys:', error);
       }
   }
   ```

3. **Update verifySignatureClientSide()**:
   ```javascript
   async verifySignatureClientSide(data) {
       try {
           // Extract signature and data without signature
           const signature = data.signature;
           const dataCopy = { ...data };
           delete dataCopy.signature;
           
           // Convert data to JSON string for verification
           const json_data = new TextEncoder().encode(JSON.stringify(dataCopy, sortKeys));
           
           // Load trusted keys from API
           const response = await fetch('/api/status');
           const status = await response.json();
           
           if (status.trusted_keys_count === 0) {
               console.log('No trusted keys available for verification');
               return false;
           }
           
           // In a real implementation, we would fetch the actual public keys
           // For now, we'll simulate verification with a placeholder
           // This would be replaced with actual WebCrypto verification
           
           // For demonstration: return true if we have trusted keys
           // In practice, this would verify the signature against each trusted key
           console.log(`Verifying signature with ${status.trusted_keys_count} trusted keys`);
           
           // This is a placeholder - actual implementation would use WebCrypto API
           // to verify the signature against each trusted key
           return true; // Placeholder - this would be determined by actual verification
           
       } catch (error) {
           console.error('Client-side signature verification failed:', error);
           return false;
       }
   }
   ```

#### Step 3: Implement WebCrypto Cryptographic Verification
1. **Add helper functions**:
   ```javascript
   // Helper function to sort object keys for consistent JSON serialization
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
           
           // Decode signature from base64
           const signature = base64ToUint8Array(signatureB64);
           
           // Load public key from PEM format
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
   ```

2. **Update verifySignatureClientSide() to use WebCrypto**:
   ```javascript
   async verifySignatureClientSide(data) {
       try {
           // Extract signature and data without signature
           const signature = data.signature;
           const dataCopy = { ...data };
           delete dataCopy.signature;
           
           // Convert data to JSON string for verification
           const json_data = new TextEncoder().encode(JSON.stringify(dataCopy, sortKeys));
           
           // Load trusted keys from API
           const response = await fetch('/api/status');
           const status = await response.json();
           
           if (status.trusted_keys_count === 0) {
               console.log('No trusted keys available for verification');
               return false;
           }
           
           // Fetch actual public keys from backend
           const keysResponse = await fetch('/api/trusted_keys'); // This endpoint needs to be implemented
           const trustedKeys = await keysResponse.json();
           
           // Try to verify signature against each trusted key
           for (const publicKeyPem of trustedKeys.keys) {
               const isValid = await verifySignatureWithWebCrypto(
                   data, 
                   signature, 
                   publicKeyPem
               );
               
               if (isValid) {
                   console.log('Signature verified with trusted key');
                   return true;
               }
           }
           
           // No trusted key could verify the data
           console.log('Signature not verified by any trusted key');
           return false;
           
       } catch (error) {
           console.error('Client-side signature verification failed:', error);
           return false;
       }
   }
   ```

#### Step 4: Backend API Enhancements
1. **Create new endpoint `/api/trusted_keys`** in `src/api/api.py`:
   ```python
   @app.route('/api/trusted_keys')
   def get_trusted_keys():
       """Get list of trusted public keys"""
       try:
           return jsonify({
               'keys': [key.decode('utf-8') for key in verifier.trusted_keys]
           })
       except Exception as e:
           return jsonify({'error': str(e)}), 500
   ```

2. **Update import in `src/api/api.py`**:
   ```python
   from verifier import DataVerifier
   # Add this line:
   from flask import jsonify
   ```

#### Step 5: Update Verification Flow
1. **Modify processVerificationQueue()** to prioritize client-side verification:
   ```javascript
   async processVerificationQueue() {
       while (this.verificationQueue.length > 0) {
           const ipfsHash = this.verificationQueue.shift();
           
           try {
               // First, try client-side verification if we have trusted keys
               if (this.trustedKeys.length > 0) {
                   const data = await this.fetchIpfsData(ipfsHash);
                   if (data && data.signature) {
                       // Use WebCrypto verification
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
   ```

#### Step 6: Testing and Validation
1. **Test the implementation**:
   - Start IPFS daemon: `ipfs daemon`
   - Start backend server: `python src/api/api.py`
   - Open frontend in browser: `cd frontend && python -m http.server 8000`
   - Verify that signatures are properly validated

2. **Verify security**:
   - Ensure the WebCrypto implementation follows browser security best practices
   - Confirm that the frontend never exposes private keys
   - Test with invalid signatures to ensure they're properly rejected

### Expected Outcomes
1. Browsers can independently verify the authenticity of content without backend dependency
2. The system becomes more resilient to censorship as verification can occur offline
3. Users gain confidence in the system's integrity through transparent verification
4. Reduced load on backend servers as verification is distributed to clients

### Dependencies and Requirements
- **Browser Support**: Modern browsers with WebCrypto API support (Chrome, Firefox, Edge, Safari)
- **Network Access**: Browsers need network access to fetch `/api/status` and `/api/trusted_keys`
- **IPFS Access**: Browsers need to be able to access `/api/verify` endpoint to retrieve IPFS data
- **Cryptography**: The system relies on RSA with SHA-256 for digital signatures

### Future Enhancements
1. **Phase 2**: Implement opt-in browser data collection for decentralized contribution
2. **Phase 3**: Create a reputation-based verification network where browsers verify each other's submissions
3. **Offline Mode**: Cache trusted keys locally for verification without network connectivity
4. **Mobile Optimization**: Lightweight verification for mobile devices with limited resources

## Important Notes
- The current implementation uses RSA with SHA-256 for digital signatures, which is compatible with the backend implementation
- All cryptographic operations happen in the browser using the WebCrypto API, ensuring no sensitive data is exposed
- The system is designed to be backward compatible - if client-side verification fails, it falls back to backend verification
- The trusted_keys.json file must be populated with public keys from verified volunteers before client-side verification can be effective

## Next Steps
1. Implement the `/api/trusted_keys` endpoint in the backend
2. Update the frontend verifier.js with the complete WebCrypto implementation
3. Test the verification flow with sample data
4. Document the complete process in the README.md
5. Proceed with Phase 2: Implement opt-in browser data collection